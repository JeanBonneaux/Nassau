# suivi_lateral.py — se centrer dans un passage SANS S'ARRÊTER, avec des distances lues de côté pendant que le robot roule.
#
# PROTOTYPE de l'audit du 2026-11-14 (notes/I_audit_regard_neuf.md). Essayé en simulation seulement
# (essai_suivi_lateral.py) : rien de ce fichier n'a roulé sur le robot, et le robot d'aujourd'hui ne peut pas s'en
# servir tel quel. Il suppose deux choses qui n'existent pas encore :
#   1. une distance de côté lue en roulant, à gauche et à droite : deux petits capteurs de distance fixes tournés vers
#      les côtés, ou le capteur actuel sur un servo qui irait jusqu'à 90° de chaque côté (changement de montage, à
#      décider par l'utilisateur : la butée de 30° a été fixée à sa demande) ;
#   2. un ordre du cerveau pour retoucher le cap visé pendant une avance (aujourd'hui /api/mouv refuse tout ordre
#      tant qu'un mouvement est en cours : changement de firmware).
#
# Pourquoi : le 2026-11-14, le couloir de J20 à J12 (3,9 m) a pris 319 s, dont 30 s à avancer ; le centrage par arrêts
# de centrage.py en prendrait 169 en simulation. À chaque arrêt le robot pivote pour regarder à gauche puis à droite,
# parce que son seul capteur regarde devant. Avec une distance de côté lue en roulant, le même réglage se fait sans
# arrêt : c'est le suivi de mur des robots du commerce.
#
# Principe, en deux boucles :
#   - le gyroscope tient le cap d'un instant à l'autre (le cerveau le fait déjà pendant une avance) ;
#   - les murs disent, plus lentement, deux choses : où est le milieu (différence des deux distances), et dans quelle
#     direction va vraiment le passage (une distance de côté qui grandit quand le robot avance : il s'en écarte ;
#     la pente donne l'angle, sans dépendre de l'échelle du gyroscope).
# Le cap demandé est l'axe du passage, corrigé de quelques degrés vers le milieu.
#
# Ce qui déplace le milieu, et ce qui ne le déplace pas :
#   - le passage se resserre (un rebord, un meuble) : le milieu suit, tout de suite ;
#   - un côté s'ouvre (porte, renfoncement, fin d'un mur) : le milieu ne suit pas ; le robot garde l'autre mur à la
#     distance qu'il avait, jusqu'à ce que le côté ouvert se referme ou se montre être un vrai mur (une droite sans
#     saut sur 50 cm). Un faisceau qui frôle l'arête d'une ouverture donne des lectures qui grandissent peu à peu :
#     la largeur de référence n'est donc retenue que sur des parois « posées » (une droite sans saut de chaque côté).
#
# Usage dans un programme (une fois par lecture, 5 à 20 fois par seconde) :
#     s = SuiviLateral(cap_de_l_axe)
#     cap_vise, vitesse = s.pas(chemin_mm, cap_du_gyroscope, gauche_mm, droite_mm)   # None pour un côté sans lecture
import math


class SuiviLateral:
    def __init__(self, axe, gain=1.0, cap_max=10.0, fenetre=300.0, portee=1300.0, v_max=130, v_serre=80, jeu_serre=90.0, rayon=170.0,
                 elargi=40.0, n_min=4, v_depart=None, mediane=5, pente_min=120.0):
        # axe     : cap du passage tel qu'on le croit (degrés, même compte que le gyroscope) ; les murs le corrigent
        # gain    : radians de correction de cap par mètre d'écart au milieu
        # cap_max : correction de cap la plus forte, degrés
        # fenetre : longueur de chemin (mm) sur laquelle la pente d'un mur est lue
        # portee  : au-delà, une lecture de côté ne compte pas (ouverture, pièce)
        # elargi  : demi-largeur gagnée d'un coup (mm) au-delà de laquelle un côté est tenu pour ouvert
        # n_min   : nombre de lectures qu'il faut pour lire la pente d'un mur (4 ; 3 quand les lectures sont rares)
        # v_depart: vitesse tant que l'axe du passage n'a pas été lu une première fois sur les murs (None : v_max)
        # mediane : chaque côté est lissé par la médiane de ses dernières lectures (5 pour un capteur lu 20 fois par
        #           seconde : 0,25 s, soit 3 cm de chemin ; 1 quand les lectures sont rares). Sans ce lissage, un bruit
        #           de 15 mm fait prendre des écarts de lecture pour des rebords (essai_suivi_lateral.py --bruit 15)
        self.axe, self.gain, self.cap_max, self.fenetre, self.portee = float(axe), gain, cap_max, fenetre, portee
        self.v_max, self.v_serre, self.jeu_serre, self.rayon, self.elargi = v_max, v_serre, jeu_serre, rayon, elargi
        self.n_min, self.v_depart, self.mediane = n_min, v_depart, max(1, int(mediane))
        # pente_min : longueur de chemin (mm) qu'il faut avoir roulée le long d'une paroi avant d'en lire la pente. Ajouté le
        # 2026-11-21 (session de navigation, journal_wifi.md § 70), valeur d'origine gardée par défaut : sur le robot, avec un
        # bruit de 20 mm par lecture, 120 mm ne suffisent pas ; la première pente lue sur 18 cm a donné un axe faux de 11°.
        self.pente_min = float(pente_min)
        self.bg, self.bd = [], []              # dernières lectures brutes de chaque côté
        self.hg, self.hd = [], []              # (chemin, cap, distance) récents de chaque côté, sans saut
        self.y = 0.0                           # écart au milieu, mm, positif vers la gauche
        self.pose = None                       # dernière lecture sur parois posées : (gauche, droite)
        self.ouvert = None                     # (côté tenu pour ouvert, chemin à cet instant)
        self.n_axe = 0

    def _pente(self, h):
        """(pente de la distance le long du chemin, cap moyen) sur les points gardés, ou None s'ils ne font pas 12 cm"""
        if len(h) < self.n_min or h[-1][0] - h[0][0] < self.pente_min:
            return None
        n = len(h)
        ms = sum(p[0] for p in h) / n
        md = sum(p[2] for p in h) / n
        den = sum((p[0] - ms) ** 2 for p in h)
        if den <= 0:
            return None
        return sum((p[0] - ms) * (p[2] - md) for p in h) / den, sum(p[1] for p in h) / n

    def _lisser(self, b, dist):
        """médiane des dernières lectures d'un côté ; None si plus de la moitié manquent ou sont hors de portée"""
        if self.mediane <= 1:
            return dist
        b.append(dist if (dist is not None and 0 < dist <= self.portee) else None)
        del b[:-self.mediane]
        v = sorted(x for x in b if x is not None)
        if 2 * len(v) <= len(b):
            return None
        return v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2.0

    def _ranger(self, h, s, cap, dist):
        if dist is None or not (0 < dist <= self.portee):
            del h[:]
            return False
        if h and abs(dist - h[-1][2]) > 30.0:          # la paroi avance ou recule d'un coup (rebord, meuble) : nouvelle droite
            del h[:]
        h.append((s, cap, dist))
        while h and s - h[0][0] > self.fenetre:
            h.pop(0)
        return True

    def pas(self, s, cap, gauche, droite):
        """s : chemin roulé (mm) ; cap : cap du gyroscope (degrés) ; gauche, droite : distance du centre du robot à la
        paroi de chaque côté (mm), ou None. Renvoie (cap à viser, vitesse en mm/s)."""
        gauche, droite = self._lisser(self.bg, gauche), self._lisser(self.bd, droite)
        vg = self._ranger(self.hg, s, cap, gauche)
        vd = self._ranger(self.hd, s, cap, droite)
        suivi = None                                   # côté suivi seul, s'il y en a un
        if vg and vd:
            demi = (gauche + droite) / 2.0
            if self.pose is not None and demi > (self.pose[0] + self.pose[1]) / 2.0 + self.elargi:
                # plus large d'un coup : un côté s'est ouvert, celui qui a le plus reculé
                if self.ouvert is None:
                    self.ouvert = ("g" if (gauche - self.pose[0]) > (droite - self.pose[1]) else "d", s)
                h = self.hg if self.ouvert[0] == "g" else self.hd
                if s - self.ouvert[1] > 500.0 and h and s - h[0][0] >= self.fenetre - 60.0:
                    self.ouvert = None                 # il tient en ligne droite depuis 50 cm : le passage est plus large, voilà tout
                else:
                    suivi = "d" if self.ouvert[0] == "g" else "g"
            else:
                self.ouvert = None
        elif vg or vd:
            suivi = "g" if vg else "d"
        # 1. où est le milieu
        if suivi is None and vg and vd:
            if self.pose is None or (self._pente(self.hg) is not None and self._pente(self.hd) is not None):
                self.pose = (gauche, droite)
            self.y = (droite - gauche) / 2.0
        elif suivi is not None and self.pose is not None:
            # un seul mur : il reste à la distance qu'il avait sur la dernière lecture posée
            y0 = (self.pose[1] - self.pose[0]) / 2.0
            self.y = y0 + (self.pose[0] - gauche) if suivi == "g" else y0 - (self.pose[1] - droite)
        elif suivi is not None:
            self.y = 0.0                               # jamais vu les deux côtés : on longe ce mur à la distance du départ
            self.pose = (gauche, gauche) if suivi == "g" else (droite, droite)
        # 2. où va le passage : pente de chaque mur encore suivi
        caps = []
        for cote, h, signe in (("g", self.hg, -1.0), ("d", self.hd, 1.0)):
            if suivi is not None and cote != suivi:
                continue
            p = self._pente(h)
            if p is not None:
                psi = math.degrees(math.atan(signe * p[0]))        # cap du robot par rapport au mur, positif à gauche
                caps.append(p[1] - psi)
        if caps:
            mes = sum(caps) / len(caps)
            self.axe += (0.5 if self.n_axe == 0 else 0.15) * (mes - self.axe)
            self.n_axe += 1
        # 3. le cap demandé : l'axe, corrigé vers le milieu
        corr = max(-self.cap_max, min(self.cap_max, -math.degrees(self.gain * self.y / 1000.0)))
        jeu = min([d - self.rayon for d, v in ((gauche, vg), (droite, vd)) if v] or [1e9])
        v = self.v_serre if jeu < self.jeu_serre else self.v_max
        if self.n_axe == 0 and self.v_depart:
            v = min(v, self.v_depart)
        return self.axe + corr, v
