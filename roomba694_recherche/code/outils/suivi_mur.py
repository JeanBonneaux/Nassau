# suivi_mur.py — longer UN mur sans s'arrêter, capteur de distance tourné d'un côté : le mur est suivi comme une DROITE
# posée dans un repère local, et non plus par la seule pente de la distance.
#
# Écrit le 2026-11-21 (session de navigation, journal_wifi.md § 72) après le premier mur longé (§ 71) : vers 1,05 m le mur
# reculait de 11 cm EN PENTE (11 cm sur 15 cm de chemin) et le robot a tourné vers lui de 16°. Le suivi d'avant
# (suivi_lateral.SuiviLateral, prototype de l'audit prévu pour deux côtés) ne coupait une paroi que sur un saut de 30 mm
# entre deux lectures : une pente passait dessous, entrait dans le calcul de l'axe du mur et le faisait tourner de 14°,
# qui s'ajoutaient à la correction d'écart.
#
# Principe :
#   - à chaque lecture, le point de la paroi est placé dans un repère local tenu à l'estime (chemin des roues, cap du
#     gyroscope), en comptant que le capteur est en avant du centre du robot (avance_capteur) ;
#   - « le mur » est la droite qui passe par les points récents (fenetre). Un point est comparé À CETTE DROITE, pas à la
#     lecture d'avant : une pente ne passe plus dessous ;
#       . à moins de `saut` de la droite : c'est le mur, le point s'y ajoute ;
#       . ailleurs, c'est une AUTRE PAROI, mise en observation ; le mur, lui, reste où il était ;
#           - plus PRÈS (une avancée : montant, meuble) : dès la deuxième lecture le robot règle son écart sur elle,
#             s'en écarter ne peut pas attendre ;
#           - plus LOIN (un renfoncement, le mur qui recule) : le robot garde la droite du mur, à l'estime ;
#           - plus loin de plus de `ouverture`, ou rien à portée (porte, fin du mur) : pareil, et rien n'est observé ;
#       . si les lectures reviennent sur la droite du mur, l'autre paroi est oubliée (c'était un cadre de porte, un
#         meuble, ou du bruit) ; si elle tient en ligne droite sur `adopte` mm, c'est elle qui devient le mur ;
#   - l'axe du mur n'est relu que sur une droite d'au moins `pente_min` mm, et il rejoint cette lecture doucement
#     (lissage_axe, en mm de chemin) : une marche de moins de `saut` ne le fait bouger que de 2 ou 3° ;
#   - le cap demandé est l'axe du mur, corrigé vers la distance voulue (gain, cap_max). La somme ne peut plus s'emballer.
#
# Usage (une fois par lecture NOUVELLE du capteur, une dizaine de fois par seconde) :
#     s = SuiviMur("g" ou "d", consigne_mm)
#     cap_vise, vitesse = s.pas(chemin_mm, cap_deg, lecture_mm)     # lecture None : rien à portée
# chemin et cap sont ceux de l'avance en cours (fait_mm, fait_deg du cerveau : cap positif vers la gauche).
# Essais sans le robot : essai_profil_mur.py (parois dessinées, dont celle du § 71) et essai_longe_mur.py --suivi mur.
import math


class SuiviMur:
    def __init__(self, cote, consigne, axe=0.0, gain=1.0, gain_pres=None, cap_max=10.0, fenetre=600.0, pente_min=400.0,
                 saut=30.0, ouverture=250.0, adopte=400.0, avance_capteur=130.0, portee=2000.0, v_max=130, v_serre=80,
                 jeu_serre=90.0, rayon=150.0, mediane=5, lissage_axe=150.0, courte=200.0, n_min=4):
        # cote      : "g" ou "d", le côté du mur
        # consigne  : distance du capteur au mur à tenir, mm (la lecture du capteur quand le robot roule le long du mur)
        # axe       : cap du mur tel qu'on le croit, degrés, dans le compte du cap donné à pas() ; le mur le corrige
        # gain      : radians de correction de cap par mètre d'écart ; gain_pres : le même quand le robot est trop près
        # cap_max   : correction de cap la plus forte, degrés
        # fenetre   : longueur de chemin (mm) des points gardés pour la droite du mur
        # pente_min : longueur de droite (mm) qu'il faut pour relire l'axe du mur
        # saut      : écart à la droite (mm) au-delà duquel un point n'est plus « le mur » (30 mm : trois fois le bruit
        #             d'une lecture lissée, 10 mm en roulant le 2026-11-21)
        # ouverture : au-delà de cet écart (mm) une paroi plus loin n'est jamais observée
        # adopte    : longueur (mm) sur laquelle une autre paroi doit tenir en ligne droite avant de devenir le mur
        # avance_capteur : mm du centre du robot à l'axe du servo, vers l'avant (11 à 18 cm estimés le 2026-11-21, pas
        #             mesuré à la règle ; ne joue que quand le robot tourne : 2 mm par degré pour 130)
        # rayon, jeu_serre, v_max, v_serre : la vitesse tombe à v_serre quand (distance - rayon) passe sous jeu_serre
        # mediane   : la lecture est d'abord lissée par la médiane de ses dernières valeurs
        # lissage_axe : longueur de chemin (mm) sur laquelle l'axe retenu rejoint l'axe lu
        # courte    : en dessous de cette longueur (mm) un bout de paroi est comparé à l'axe retenu, pas à sa propre pente
        self.signe = 1.0 if cote == "g" else -1.0
        self.consigne, self.axe = float(consigne), float(axe)
        self.gain, self.gain_pres, self.cap_max = gain, (gain if gain_pres is None else gain_pres), cap_max
        self.fenetre, self.pente_min, self.saut, self.ouverture, self.adopte = fenetre, pente_min, saut, ouverture, adopte
        self.L, self.portee = float(avance_capteur), portee
        self.v_max, self.v_serre, self.jeu_serre, self.rayon = v_max, v_serre, jeu_serre, rayon
        self.mediane, self.lissage_axe, self.courte, self.n_min = max(1, int(mediane)), lissage_axe, courte, n_min
        self.x = self.y = 0.0                  # estime du centre du robot, mm (x : cap 0, y : vers la gauche)
        self.s = self.cap = None
        self.brut = []                         # dernières lectures brutes
        self.seg = []                          # points du mur : (chemin, x, y)
        self.cand = []                         # points d'une autre paroi, en observation
        self.etat = "depart"                   # "mur", "pres" (avancée), "loin" (renfoncement, recul), "ouvert"
        self.n_bon = 0
        self.n_axe = 0
        self.dist = None                       # distance du capteur à la droite sur laquelle l'écart est réglé, mm
        self.ecart = 0.0                       # dist - consigne
        self.tenu_mm = 0.0                     # chemin fait sur la droite du mur gardée à l'estime
        self.n_pres = self.n_loin = self.n_adopte = self.n_ouvert = 0

    # ------------------------------------------------------------------ outils
    def amorce(self, lecture_arret):
        """La distance lue à l'arrêt avant de partir (médiane d'une quinzaine de lectures) : elle remplit la médiane
        glissante, pour que les premiers points du mur ne soient pas des lectures isolées. Sans elle, en simulation,
        trois premières lectures hautes de suite ont donné un premier axe faux de 7°."""
        if lecture_arret is not None and 0 < lecture_arret <= self.portee:
            self.brut = [float(lecture_arret)] * self.mediane

    def _lisser(self, lecture):
        v = lecture if (lecture is not None and 0 < lecture <= self.portee) else None
        if self.mediane <= 1:
            return v
        self.brut.append(v)
        del self.brut[:-self.mediane]
        bons = sorted(x for x in self.brut if x is not None)
        if 2 * len(bons) <= len(self.brut):
            return None
        return bons[len(bons) // 2] if len(bons) % 2 else (bons[len(bons) // 2 - 1] + bons[len(bons) // 2]) / 2.0

    def _droite(self, pts, s):
        """(pente, x0, y0, posée) : la droite d'un bout de paroi, vue depuis le chemin s. Assez longue pour donner l'axe
        du mur (posée) : sa propre droite. Assez longue pour avoir une pente (courte), et pas prolongée à plus de 10 cm
        de son dernier point : sa propre droite aussi. Sinon l'axe retenu, passant par ses derniers points."""
        n = len(pts)
        long_ = pts[-1][0] - pts[0][0]
        if n >= self.n_min and (long_ >= self.pente_min or (long_ >= self.courte and s - pts[-1][0] <= 100.0)):
            mx = sum(p[1] for p in pts) / n
            my = sum(p[2] for p in pts) / n
            den = sum((p[1] - mx) ** 2 for p in pts)
            if den > 0:
                return sum((p[1] - mx) * (p[2] - my) for p in pts) / den, mx, my, long_ >= self.pente_min
        fin = [p for p in pts if pts[-1][0] - p[0] <= 120.0]
        return (math.tan(math.radians(self.axe)), sum(p[1] for p in fin) / len(fin), sum(p[2] for p in fin) / len(fin), False)

    def _plus_loin(self, droite, px, py):
        """de combien le point est plus loin du robot que la droite, mm (négatif : plus près)"""
        m, x0, y0 = droite[:3]
        return self.signe * (py - (y0 + m * (px - x0))) * math.cos(math.atan(m))

    # ------------------------------------------------------------------ une lecture
    def pas(self, s, cap, lecture):
        """s : chemin roulé (mm) ; cap : cap du gyroscope (degrés, positif à gauche) ; lecture : distance lue de côté (mm)
        ou None. Renvoie (cap à viser, vitesse en mm/s)."""
        if self.s is None:
            self.s, self.cap = s, cap
        ds = s - self.s
        cm = math.radians((cap + self.cap) / 2.0)
        self.x += ds * math.cos(cm)
        self.y += ds * math.sin(cm)
        self.s, self.cap = s, cap
        th = math.radians(cap)
        sx, sy = self.x + self.L * math.cos(th), self.y + self.L * math.sin(th)         # le capteur
        d = self._lisser(lecture)
        P = None
        if d is not None:
            a = math.radians(self.axe)                                                   # le capteur entend la paroi au plus près
            P = (s, sx - self.signe * d * math.sin(a), sy + self.signe * d * math.cos(a))
        avant = self.etat
        if not self.seg:
            if P is None:                                                                # aucun mur vu jusqu'ici : tout droit
                self.etat = "ouvert"
                return self.axe, self.v_max
            self.seg, etat = [P], "mur"
        else:
            r = None if P is None else self._plus_loin(self._droite(self.seg, s), P[1], P[2])
            if r is not None and abs(r) <= self.saut:
                etat = "mur"
                self.seg.append(P)
                while s - self.seg[0][0] > self.fenetre:
                    self.seg.pop(0)
                self.n_bon += 1
                if self.n_bon >= 2:
                    self.cand = []
            else:
                self.n_bon = 0
                if r is None or r > self.ouverture:
                    etat, self.cand = "ouvert", []
                else:
                    etat = "pres" if r < 0 else "loin"
                    if self.cand and abs(self._plus_loin(self._droite(self.cand, s), P[1], P[2])) > self.saut:
                        self.cand = []             # l'autre paroi n'est pas une droite : on recommence à la regarder
                    self.cand.append(P)
                    if len(self.cand) >= self.n_min and self.cand[-1][0] - self.cand[0][0] >= self.adopte:
                        self.seg, self.cand, etat = self.cand, [], "mur"
                        self.n_adopte += 1
        if etat != avant:
            self.n_pres += etat == "pres"
            self.n_loin += etat == "loin"
            self.n_ouvert += etat == "ouvert"
        if etat in ("loin", "ouvert"):
            self.tenu_mm += max(0.0, ds)
        self.etat = etat
        # l'axe du mur : seulement sur une droite posée, et doucement
        mur = self._droite(self.seg, s)
        if etat == "mur" and mur[3]:
            mes = math.degrees(math.atan(mur[0]))
            self.axe += (1.0 - math.exp(-max(0.0, ds) / self.lissage_axe)) * (mes - self.axe)
            self.n_axe += 1
        # la droite sur laquelle l'écart est réglé : le mur, ou l'avancée dès qu'elle est lue deux fois de suite
        m, x0, y0 = (self._droite(self.cand, s) if (etat == "pres" and len(self.cand) >= 2) else mur)[:3]
        self.dist = self.signe * ((y0 + m * (sx - x0)) - sy) * math.cos(math.atan(m))
        self.ecart = self.dist - self.consigne
        g = self.gain if self.ecart >= 0 else self.gain_pres
        corr = max(-self.cap_max, min(self.cap_max, self.signe * math.degrees(g * self.ecart / 1000.0)))
        v = self.v_serre if (self.dist - self.rayon) < self.jeu_serre else self.v_max
        return self.axe + corr, v
