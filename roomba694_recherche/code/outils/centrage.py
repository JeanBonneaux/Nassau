# centrage.py — se centrer seul dans un passage étroit, au capteur de distance.
#
# Pourquoi : le 2026-11-14, sur 22,9 minutes de trajet, dix ont été passées dans trois passages menés pas à pas par
# l'assistant avec passage.py (la porte H12 deux fois, le couloir entre J15 et J17, qui ne laisse que 68 cm). Dans le
# couloir, chaque arrêt coûtait 12 s de rotation et de lecture, et 15 à 25 s de réflexion de l'assistant entre deux
# ordres. Ce module enchaîne les mêmes gestes sans attendre personne (journal_wifi.md § 47).
#
# La méthode, à chaque arrêt :
#   1. un regard à gauche du passage (robot tourné de 90°, capteur immobile une seconde) : distance de la paroi ;
#   2. un demi-tour PAR L'AVANT jusqu'à regarder à droite, capteur en marche : c'est « l'éventail », qui montre ce
#      qu'il y a devant ;
#   3. un regard à droite ; puis retour vers l'avant.
#   Les trois rotations s'annulent (+90°, −180°, +90°) : l'erreur d'échelle du gyroscope ne s'accumule pas d'un arrêt à
#   l'autre. Le 14, les regards faits à la main tournaient toujours dans le même sens (un tour complet par arrêt, huit
#   tours dans le couloir) ; selon l'échelle retenue, la position tenue à l'estime changeait de 42 cm sur 4 m.
#   4. Dans un couloir (une paroi de côté à moins de 70 cm) : le milieu se lit sur les deux regards de côté. Un écho
#      de l'éventail ne déplace ce milieu que s'il est entier (ni coupé ni masqué par un autre) et plus près de la
#      ligne que la paroi du même côté ; et jamais jusqu'à moins de 8 cm d'une paroi mesurée.
#   5. Devant une porte (aucune paroi de côté) : c'est la trouée de l'éventail qui commande, c'est-à-dire la suite de
#      lectures lointaines entre ses deux bords. Le robot se décale vers son milieu, s'approche, regarde de près, puis
#      franchit d'une traite.
#   6. Le robot rejoint le milieu en biais pendant l'avance suivante (20° au plus), ou par un pas de côté quand ce qui
#      resserre le passage est trop près.
#   7. Deux arrêts de suite disent de combien chaque paroi s'est rapprochée ou éloignée : c'est le cap du robot par
#      rapport aux murs, à un degré près sur 40 cm. Il sert à avancer droit, et il est affiché à la fin (CAP_MURS).
#   8. Le pas s'allonge (de 40 à 80 cm) quand le robot est au milieu, que la largeur ne change pas et que ce cap est
#      confirmé ; il revient à 40 cm dès que quelque chose change.
#
# Ce qui a été vérifié, et sur quoi (journal_wifi.md § 47) :
#   - en simulation (essai_centrage.py) : un couloir qui passe de 95 à 68 cm et une porte de 62 cm, 45 départs décalés
#     et de travers pour chacun, aucun contact ;
#   - sur les mesures du robot du 2026-11-14 (data_analysis/v_rejeu_centrage.py) : les décisions rejouées sur les sept
#     arrêts du couloir et sur les deux arrêts devant la porte H12 retrouvent ce qui avait été fait à la main ;
#   - sur le robot lui-même : rien encore.
# Ce que ces mesures ont appris, et que le simulateur ne disait pas : une paroi proche s'entend très en biais (à 45 cm,
# jusqu'à 80° de sa perpendiculaire, la distance lue glissant de 44 à 62 cm) ; la direction d'un écho est donc floue à
# 15° près alors que sa distance est juste ; et la lecture écrite dans le journal a 0,15 s de retard pendant une
# rotation.
#
# Ce que le capteur ne voit pas : un bord de table (le capteur passe dessous ou dessus), un tissu, un chant de porte
# vu sur quelques degrés seulement. Le pare-chocs reste la vraie sécurité : au premier contact, tout s'arrête et
# l'ordre rend la main. Rien n'est décidé d'après le plan : seulement d'après ce que le capteur mesure sur place.
#
# Trois morceaux :
#   Mobile    le robot mené à l'estime depuis une pose connue (mêmes gestes pour Pilote et pour le robot simulé) ;
#   Centreur  les décisions, sans robot : se nourrit des distances lues et du chemin fait, rend le prochain geste ;
#   centrer() la boucle qui relie les deux.
import math
import time

import carto

RAYON = 170.0            # mm, rayon du robot
DX = 27.0                # mm : le devant du capteur de distance est en avant du centre du robot
PRES = 700.0             # mm du centre : une paroi ou un obstacle plus proche que cela, de côté, compte pour le centrage
PORTEE_COTE = 1200.0     # mm : au-delà, un regard de côté ne dit plus rien de la paroi (porte ouverte, pièce)
PORTEE_AVANT = 1500.0    # mm : au-delà, ce que montre l'éventail ne concerne pas l'avance qui vient
GARDE_SEULE = 300.0      # mm du centre : distance gardée d'une paroi seule quand aucune largeur n'a encore été mesurée
GARDE_ECHO = 350.0       # mm du centre : distance gardée d'un obstacle que seul l'éventail a placé (sa direction est moins sûre)
GARDE_PAROI = RAYON + 80.0         # mm du centre : jamais plus près d'une paroi mesurée de côté, quoi que dise l'éventail
ACCORD_PORTE = 60.0      # mm : écart au-delà duquel on signale que les deux lectures d'une porte divergent (ses bords
                         #      placés, et le milieu de sa trouée) ; un dixième de sa distance si c'est plus
LOIN = 1500.0            # mm : une lecture plus longue, ou pas de lecture, compte comme « rien devant » dans l'éventail
RETARD_LECTURE = 0.15    # s : âge de la lecture du capteur de distance portée par une ligne du journal (voir Mobile.balayer)
CONE_MIN = 8.0           # degrés : le capteur entend un objet au moins jusque-là de part et d'autre de sa direction (le
                         #          14, devant la porte H12, un bord à 45 cm s'entendait jusqu'à 20° de sa direction)
TROUEE_MIN = 200.0       # mm : largeur de trouée en dessous de laquelle le robot ne franchit pas
LARGEUR_MIN = 2 * RAYON + 60.0     # mm : en dessous, le robot ne tente pas le passage (3 cm de chaque côté)
ANGLE_MAX = 20.0         # degrés : biais le plus fort pour rejoindre le milieu en avançant
TOL_PARALLELE = 3.0      # degrés : au-delà, les deux parois ne racontent pas le même cap (la largeur change)
GAIN_BIAIS = 0.6         # part d'une nouvelle mesure du cap par rapport aux murs dans l'estimation
AU_MILIEU = 30.0         # mm : en deçà, le robot est tenu pour centré
V_ROTATION = 100         # mm/s aux roues pour se tourner vers un regard (le cerveau n'accepte pas plus pour une rotation)
EVENTAIL = 75.0          # degrés de part et d'autre de l'axe : ce que l'éventail garde
ARRETS_MAX = 40          # garde-fou : un passage ne demande jamais autant d'arrêts


def ecart(a):
    """angle ramené entre -180 et 180 degrés"""
    return (a + 180.0) % 360.0 - 180.0


def groupes(eventail, saut_mm=60.0, trou_deg=8.0):
    """Les échos d'un éventail, regroupés. eventail : liste de (direction en degrés par rapport à l'axe du passage,
    positive vers la gauche ; lecture du capteur en mm, 0 = rien), dans l'ordre du balayage. Renvoie une liste de
    dictionnaires : dir (direction du milieu), mm (distance du centre du robot, médiane), larg (largeur en degrés),
    n (lectures), a et b (première et dernière direction), coupe, sur.

    Ce qu'un groupe dit et ne dit pas. Le capteur entend un objet dans un cône, large : sur le robot, le 14, un coin
    à 60 cm s'entendait sur 50°, et une paroi à 45 cm jusqu'à 80° de sa perpendiculaire. La distance est juste à
    quelques millimètres ; la direction n'est que le milieu de ce qu'on a entendu. Quand un groupe est coupé par un
    autre plus proche (qui le masque) ou par le bord de l'éventail, son milieu n'est plus celui de l'objet : au premier
    essai en simulation, un coin a ainsi été placé 30 cm trop près de l'axe, et le robot a fait un pas de côté pour
    rien. « sur » ne vaut donc que pour un groupe entier, sans voisin plus proche collé à lui : celui-là seul sert à
    placer un obstacle. Les autres disent seulement « quelque chose est à telle distance, quelque part par là ». Un
    groupe de moins de 2,5° de large est écarté : une lecture isolée ne prouve rien."""
    out, cour = [], []
    bords = (eventail[0][0], eventail[-1][0]) if eventail else (0.0, 0.0)

    def fermer():
        if len(cour) >= 2 and abs(cour[-1][0] - cour[0][0]) >= 2.5:
            d = sorted(u for _, u in cour)
            lo, hi = min(cour[0][0], cour[-1][0]), max(cour[0][0], cour[-1][0])
            out.append({"dir": (lo + hi) / 2.0, "mm": d[len(d) // 2] + DX, "larg": hi - lo, "n": len(cour), "a": lo, "b": hi,
                        "coupe": min(abs(lo - x) for x in bords) < 4.0 or min(abs(hi - x) for x in bords) < 4.0})

    for a, u in eventail:
        if u <= 0:
            continue
        if cour and (abs(u - cour[-1][1]) > saut_mm or abs(a - cour[-1][0]) > trou_deg):
            fermer()
            cour = []
        cour.append((a, u))
    fermer()
    for q in out:
        masque = any(o is not q and o["mm"] < q["mm"] - 40.0 and max(q["a"] - o["b"], o["a"] - q["b"]) <= 6.0 for o in out)
        q["sur"] = not q["coupe"] and not masque
    return out


def trouee(eventail, larg_min=12.0):
    """La trouée de l'éventail la plus proche de l'axe : une suite de lectures lointaines (rien, ou plus de LOIN) d'au
    moins larg_min degrés. C'est une seconde lecture d'une porte, indépendante de la direction prêtée à chaque écho :
    elle ne se sert que de l'endroit où les lectures deviennent lointaines. Renvoie None, ou un dictionnaire : a et b
    (bords de la trouée, en degrés depuis l'axe, a à droite et b à gauche ; None si la trouée va jusqu'au bord de
    l'éventail), dir (milieu), larg, mm_a et mm_b (lecture proche juste au-delà de chaque bord, du centre du robot).

    Mesuré le 2026-11-14 devant la porte H12, sur les rotations faites à la main (journal_wifi.md § 47) : la trouée
    allait de 90° à 120° de cap, milieu 105° ; le robot est passé sans contact au cap 100 à 103°. Les échos des deux
    bords, eux, s'étalaient sur 30° et plus, avec une distance qui glissait de 42 à 54 cm d'un côté : leur milieu ne
    disait pas où était le bord."""
    ev = sorted(((a, u) for a, u in eventail), key=lambda q: q[0])
    if len(ev) < 4:
        return None
    lointain = [u <= 0 or u > LOIN for _, u in ev]
    meilleur = None
    i = 0
    while i < len(ev):
        if not lointain[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(ev) and lointain[j + 1]:
            j += 1
        a = (ev[i - 1][0] + ev[i][0]) / 2.0 if i > 0 else None
        b = (ev[j][0] + ev[j + 1][0]) / 2.0 if j + 1 < len(ev) else None
        lo, hi = ev[i][0] if a is None else a, ev[j][0] if b is None else b
        if hi - lo >= larg_min:
            pres_a = sorted(u for _, u in ev[max(0, i - 3):i])
            pres_b = sorted(u for _, u in ev[j + 1:j + 4])
            t = {"a": a, "b": b, "dir": (lo + hi) / 2.0, "larg": hi - lo,
                 "mm_a": pres_a[len(pres_a) // 2] + DX if pres_a else None, "mm_b": pres_b[len(pres_b) // 2] + DX if pres_b else None}
            if lo <= 0.0 <= hi:
                dist = 0.0
            else:
                dist = min(abs(lo), abs(hi))
            if meilleur is None or dist < meilleur[0]:
                meilleur = (dist, t)
        i = j + 1
    return meilleur[1] if meilleur else None


class Mobile:
    """Le robot mené à l'estime depuis une pose connue. x, y en mm et cap en degrés dans le repère du plan (x vers la
    droite, y vers le haut, cap 0 = vers la droite, 90 = vers le haut). La position suit le journal du cerveau ligne à
    ligne : chaque pas compté par le cerveau est tourné du cap corrigé de l'échelle du gyroscope, comme le fait
    explorer3.Estime, et le chemin d'une roue qui patine est retiré (carto.part_roulee)."""

    def __init__(self, p, x_mm, y_mm, cap_deg, k_gyro=1.0045, dire=print):
        self.p = p
        self.k = k_gyro
        self.dire = dire
        self.dormir = getattr(p, "dormir", time.sleep)
        self.maintenant = getattr(p, "maintenant", time.time)
        p.lire()
        if p.frais() is None:
            raise RuntimeError("aucune ligne récente du journal : l'enregistreur tourne-t-il ? le robot répond-il ?")
        self.i = len(p.lignes) - 1
        self.X, self.Y, self.C = float(x_mm), float(y_mm), float(cap_deg)
        self.chemin = self.patine = 0.0
        self.caps = {self.i: self.C}             # cap du plan à chaque ligne du journal suivie (pour l'éventail)

    def suivre(self):
        L = self.p.lignes
        while self.i + 1 < len(L):
            a, b = L[self.i], L[self.i + 1]
            dx, dy, dc = b["x_mm"] - a["x_mm"], b["y_mm"] - a["y_mm"], b["cap_pos"] - a["cap_pos"]
            if abs(dx) > 500 or abs(dy) > 500 or abs(dc) > 300:
                raise RuntimeError("journal : la position du cerveau a sauté (cerveau redémarré ou position remise à zéro)")
            if dx or dy:
                f = carto.part_roulee(a, b, self.k)
                if f < 1.0:
                    self.patine += (1.0 - f) * math.hypot(dx, dy)
                    dx, dy = dx * f, dy * f
            e = math.radians(self.C - a["cap_pos"])              # ce qu'il faut ajouter au cap du cerveau
            self.X += math.cos(e) * dx - math.sin(e) * dy
            self.Y += math.sin(e) * dx + math.cos(e) * dy
            self.C += self.k * dc
            self.chemin += math.hypot(dx, dy)
            self.i += 1
            self.caps[self.i] = self.C

    def pose(self):
        """(x, y, cap, dernière ligne du journal)"""
        l = self.p.frais() or self.p.lignes[-1]
        self.suivre()
        return self.X, self.Y, self.C % 360.0, l

    def tourner_vers(self, cap, sens=0, v=None, tol=1.0):
        """Tourne vers ce cap du plan. sens : +1 impose de tourner à gauche, −1 à droite, 0 prend le plus court.
        v : vitesse des roues demandée (de 50 à 100 mm/s ; rien : celle du cerveau, 75). Renvoie l'écart qui reste
        (moins d'un degré : le cerveau refuse les rotations plus petites), ou None si la rotation est refusée ou
        interrompue."""
        kw = {"v_roues": v} if v else {}
        for essai in range(3):
            d = ecart(cap - self.pose()[2])
            if essai == 0 and sens and d * sens < 0 and abs(d) > 90.0:
                d += 360.0 * sens                                # le grand côté, parce que c'est lui qu'on veut balayer
            if abs(d) < tol:
                return d
            r = self.p.tourne(d / self.k, vide_min=150, **kw)
            if "refus" in r or r.get("alarme"):
                self.dire(f"   rotation refusée ou interrompue : {r.get('refus') or r.get('alarme')}")
                return None
            self.dormir(0.3)
        return ecart(cap - self.pose()[2])

    def lectures(self, duree):
        """les lignes du journal reçues pendant `duree` secondes, robot immobile"""
        n0 = len(self.p.lignes)
        fin = self.maintenant() + duree
        while self.maintenant() < fin:
            self.p.frais(age_max=0.3, attente=0.3)
            self.dormir(0.05)
        self.suivre()
        return self.p.lignes[n0:]

    def regard(self, cap, sens=0, duree=0.8):
        """Tourne vers ce cap et lit le capteur de distance, robot immobile. Renvoie None si la rotation est refusée,
        sinon un dictionnaire : mm (distance du centre du robot, médiane ; None s'il n'y a rien à portée), min, max,
        n (lectures utiles)."""
        if self.tourner_vers(cap, sens=sens, v=V_ROTATION) is None:
            return None
        self.dormir(0.3)
        L = self.lectures(duree)
        us = sorted(l["us_mm"] for l in L if l["us_mm"] > 0)
        if len(us) < max(3, len(L) // 2):
            return {"mm": None, "n": len(us)}
        return {"mm": us[len(us) // 2] + DX, "min": us[0] + DX, "max": us[-1] + DX, "n": len(us)}

    def balayer(self, cap, sens, v=75):
        """Tourne vers ce cap dans le sens donné en gardant ce que lit le capteur de distance. Renvoie la liste
        (cap du plan, lecture en mm) dans l'ordre du balayage, ou None si la rotation est refusée.

        La lecture portée par une ligne du journal n'est pas celle de l'instant : le cerveau y écrit la médiane de ses
        trois dernières mesures, faites dix fois par seconde (radar.ino, radarFrontMm). Elle date donc de 0,15 s
        environ, et le cap est reculé d'autant. Mesuré sur les rotations du 2026-11-14 devant la porte H12 : une même
        lecture arrivait 6 à 7° plus tard pendant une rotation à 45 °/s que robot immobile, soit 0,13 à 0,16 s.
        Autre effet de cette médiane : un écho qui ne tient qu'une mesure (un chant de porte, vu sur 4° seulement)
        n'apparaît pas du tout. Pour un éventail fin il faudrait la mesure brute dans le journal (firmware à venir)."""
        self.pose()
        i0 = self.i
        if self.tourner_vers(cap, sens=sens, v=v) is None:
            return None
        self.suivre()
        L = self.p.lignes
        return [(self.caps[i] - L[i].get("rot_dps", 0.0) * self.k * RETARD_LECTURE, L[i]["us_mm"]) for i in range(i0 + 1, self.i + 1)
                if abs(L[i].get("rot_dps", 0.0)) > 3.0]

    def avancer(self, dist, vitesse=100, cap_rel=0.0, marge_mm=300):
        """Pilote.avance avec les réglages de passage.py : les capteurs optiques n'arrêtent pas l'avance (un passage
        étroit les excite des deux côtés) ; arrêt sur le pare-chocs, le sol sombre, un obstacle devant."""
        self.p.vitesse(int(vitesse))
        self.dormir(0.1)
        r = self.p.avance(dist, marge_mm=marge_mm, lb_repos=1500, lb_max=3000, vide_min=150, vide_stop=150, cap_rel=cap_rel)
        self.dormir(0.4)
        self.pose()
        return r


class Centreur:
    """Les décisions du centrage, sans robot. Repère du passage : s le long de l'axe supposé, t vers la gauche.
    À chaque arrêt on lui donne la position à l'estime, les deux regards de côté et les groupes de l'éventail ; il
    rend le prochain geste."""

    def __init__(self, pas=400.0, pas_max=800.0):
        self.pas0, self.pas_max = float(pas), float(pas_max)
        self.pas = float(pas)
        self.biais = 0.0                 # cap vrai du robot par rapport aux murs, moins le cap qu'il croit avoir (degrés)
        self.n_biais = 0                 # nombre de mesures de ce biais
        self.confirme = False            # la dernière mesure s'accorde avec l'estimation d'avant, à 2° près
        self.demi = None                 # demi-largeur du passage au dernier arrêt où les deux parois étaient proches
        self.prec = None                 # arrêt précédent

    # ------------------------------------------------------------ cap par rapport aux murs
    def _biais(self, s, t, g, d, notes):
        """met à jour le biais d'après ce que chaque paroi a bougé depuis l'arrêt précédent ; renvoie la mesure ou None"""
        p = self.prec
        if p is None:
            return None
        ds, dt = s - p["s"], t - p["t"]
        chemin = math.hypot(ds, dt)
        if chemin < 150.0:
            return None
        psi = math.degrees(math.atan2(dt, ds))                  # direction du trajet d'après l'estime
        mes = []
        if g is not None and p["g"] is not None and abs(g - p["g"]) < 250.0:
            mes.append(math.degrees(math.asin(max(-1.0, min(1.0, -(g - p["g"]) / chemin)))) - psi)
        if d is not None and p["d"] is not None and abs(d - p["d"]) < 250.0:
            mes.append(math.degrees(math.asin(max(-1.0, min(1.0, (d - p["d"]) / chemin)))) - psi)
        b = None
        if len(mes) == 2 and abs(mes[0] - mes[1]) <= TOL_PARALLELE:
            b = (mes[0] + mes[1]) / 2.0
        elif mes:
            # une seule paroi, ou deux qui ne s'accordent pas (la largeur change) : on ne garde une mesure que si elle
            # ressemble à ce qu'on savait déjà ; sans rien savoir, une paroi seule est crue si elle reste raisonnable
            if self.n_biais:
                proches = [m for m in mes if abs(m - self.biais) <= 2.5]
            else:
                proches = [m for m in mes if abs(m) <= 8.0] if len(mes) == 1 else []
            if len(mes) == 2:
                notes.append(f"les deux parois ne disent pas le même cap ({mes[0]:+.1f}° et {mes[1]:+.1f}°) : la largeur change")
            if proches:
                b = min(proches, key=lambda m: abs(m - self.biais))
        if b is None:
            self.confirme = False
            return None
        self.confirme = self.n_biais >= 1 and abs(b - self.biais) <= 2.0
        self.biais = b if self.n_biais == 0 else self.biais + GAIN_BIAIS * (b - self.biais)
        self.n_biais += 1
        return b

    # ------------------------------------------------------------ un arrêt
    def arret(self, s, t, g, d, gr=(), reste=1e9, trou=None):
        """s, t : position à l'estime dans le repère du passage (mm). g, d : distance du centre du robot à la paroi de
        gauche et de droite (None : rien à portée). gr : groupes de l'éventail (directions comptées depuis l'axe
        supposé). reste : chemin qui reste à faire le long de l'axe. trou : la trouée de l'éventail (trouee()).
        Renvoie un dictionnaire :
          geste   « avance », « côté » (pas de côté) ou « fin »
          cap     pour une avance : direction à prendre par rapport à l'axe supposé (degrés, positif à gauche)
          dist    longueur de l'avance, ou du pas de côté (positif à gauche)
          ecart   de combien le robot est à gauche (+) ou à droite (−) du milieu du passage ; None : rien pour le dire
          largeur du passage là où il est le plus étroit (None si un seul côté est connu)
          raison  pour une fin
          notes   ce qu'il y a à dire"""
        notes = []
        g = g if g is not None and g <= PORTEE_COTE else None
        d = d if d is not None and d <= PORTEE_COTE else None
        b_mes = self._biais(s, t, g, d, notes)

        # ce que l'éventail montre devant, dans le repère des murs (l'axe supposé est tourné du biais déjà connu)
        surs, flous = [], []
        for q in gr:
            a = q["dir"] + self.biais
            if abs(a) > 60.0 or q["mm"] > PORTEE_AVANT:
                continue
            if q["sur"]:                                         # x, y, direction, distance, « c'est peut-être une face »
                surs.append((q["mm"] * math.cos(math.radians(a)), q["mm"] * math.sin(math.radians(a)), a, q["mm"], q["larg"] >= 25.0))
            else:
                # direction incertaine : l'objet est quelque part dans le secteur entendu, mais pas à ses bouts (le
                # capteur l'entend encore CONE_MIN plus loin que lui, de chaque côté) ; on élargit ensuite de l'angle
                # sous lequel se voit le demi-robot à cette distance
                lo, hi = q["a"] + CONE_MIN, q["b"] - CONE_MIN
                if lo > hi:
                    lo = hi = q["dir"]
                marge = math.degrees(math.asin(min(1.0, (RAYON + 40.0) / q["mm"])))
                flous.append((lo + self.biais - marge, hi + self.biais + marge, q["mm"]))
        # bornes du passage : les parois de côté, si elles sont proches
        Gw = g if g is not None and g <= PRES else None
        Dw = -d if d is not None and d <= PRES else None
        # ce qui resserre le passage devant : un obstacle placé plus près de la ligne que la paroi du même côté (de 4 cm
        # au moins) ; on prend ce qui dépasse le plus près, à gauche et à droite, à moins de 30 cm l'un de l'autre en avant
        serre = [(x, y) for x, y, _, _, _ in surs if abs(y) <= PRES
                 and ((y > 0 and (Gw is None or y < Gw - 40.0)) or (y <= 0 and (Dw is None or y > Dw + 40.0)))]
        if serre:
            x_min = min(x for x, _ in serre)
            serre = [(x, y) for x, y in serre if x <= x_min + 300.0]
        G = ([Gw] if Gw is not None else []) + [y for _, y in serre if y > 0]
        D = ([Dw] if Dw is not None else []) + [y for _, y in serre if y <= 0]
        largeur = None
        if G and D:
            largeur = min(G) - max(D)
            cible = (min(G) + max(D)) / 2.0                      # où aller, compté vers la gauche depuis le robot
            if g is not None and d is not None and g <= PRES and d <= PRES:
                self.demi = (g + d) / 2.0
        elif G:
            if Gw is not None and min(G) >= Gw:                  # la paroi de gauche seule : garder la ligne
                cible = Gw - self.demi if self.demi else min(0.0, Gw - GARDE_SEULE)
            else:                                                # un obstacle placé par l'éventail seul : passer au large
                cible = min(0.0, min(G) - GARDE_ECHO)
        elif D:
            if Dw is not None and max(D) <= Dw:
                cible = Dw + self.demi if self.demi else max(0.0, Dw + GARDE_SEULE)
            else:
                cible = max(0.0, max(D) + GARDE_ECHO)
        else:
            cible = None
        # quoi que dise l'éventail, ne jamais viser à moins de 8 cm (au flanc) d'une paroi mesurée de côté
        if cible is not None and (Gw is not None or Dw is not None):
            haut = Gw - GARDE_PAROI if Gw is not None else 1e9
            bas = Dw + GARDE_PAROI if Dw is not None else -1e9
            if bas > haut:                                       # moins de 50 cm entre les deux parois : leur milieu
                bas = haut = (Gw + Dw) / 2.0
            if not bas <= cible <= haut:
                notes.append(f"cible ramenée de {cible:+.0f} à {min(haut, max(bas, cible)):+.0f} mm : jamais à moins de 8 cm d'une paroi mesurée de côté")
                cible = min(haut, max(bas, cible))
        c = cible or 0.0
        ouvert = None                                            # largeur de la trouée, quand c'est elle qui place la porte
        # la porte qui vient : ce qui, une fois le robot sur sa ligne, passera à moins de 25 cm de son flanc. Devant elle
        # le robot s'arrête, regarde de près, se met dans l'axe, puis franchit d'une traite.
        x_porte = min((x for x, y in serre if abs(y - c) <= RAYON + 250.0), default=None)
        # Sans paroi de côté, rien ne dit si l'éventail a bien placé les bords. C'est alors la trouée qui commande :
        # devant la porte H12, le 2026-11-14, son milieu disait de se décaler de 12 à 17 cm à l'endroit où le robot était
        # 14 cm trop à l'est, et de 4 ou 5 cm là d'où il est passé sans toucher ; les bords placés par leurs échos, eux,
        # disaient 26 cm (journal_wifi.md § 47). Les bords placés ne servent plus ici qu'à signaler un désaccord.
        if Gw is None and Dw is None:
            t_ok = (trou is not None and trou["a"] is not None and trou["b"] is not None and trou["mm_a"] is not None
                    and trou["mm_b"] is not None and max(trou["mm_a"], trou["mm_b"]) <= PORTEE_COTE and abs(trou["dir"] + self.biais) <= 40.0)
            if t_ok:
                ta, tb = math.radians(trou["a"] + self.biais), math.radians(trou["b"] + self.biais)
                x_t = min(trou["mm_a"] * math.cos(ta), trou["mm_b"] * math.cos(tb))
                c_t = x_t * math.tan((ta + tb) / 2.0)
                if x_porte is not None and G and D and abs(c_t - c) > max(ACCORD_PORTE, 0.1 * x_t):
                    notes.append(f"les échos des bords placent le milieu à {c:+.0f} mm, la trouée à {c_t:+.0f} mm : la trouée est crue")
                ouvert = x_t * (math.tan(tb) - math.tan(ta))
                x_porte, cible, c, largeur = x_t, c_t, c_t, None
                notes.append(f"porte lue sur la trouée : bord le plus proche à {x_t:.0f} mm, milieu à {c_t:+.0f} mm de la ligne, trouée large de {ouvert:.0f} mm")
            elif x_porte is not None and G and D:
                x_porte = None                                   # des bords placés, pas de trouée nette : on ne s'y fie pas
                cible, c, largeur = None, 0.0, None
                notes.append("des échos de bords devant, mais pas de trouée nette : ils ne sont pas crus")
        rep = {"ecart": None if cible is None else -cible, "largeur": largeur, "biais": self.biais, "biais_mesure": b_mes,
               "notes": notes, "g": g, "d": d, "x_porte": x_porte}
        stable = (self.prec is not None and largeur is not None and self.prec.get("largeur") is not None
                  and abs(largeur - self.prec["largeur"]) <= 40.0)
        self.prec = {"s": s, "t": t, "g": g, "d": d, "largeur": largeur}

        if reste <= 30.0:
            return dict(rep, geste="fin", raison="distance faite")
        if largeur is not None and largeur < LARGEUR_MIN:
            return dict(rep, geste="fin", raison=f"passage de {largeur:.0f} mm : trop étroit pour le robot ({2 * RAYON:.0f} mm)")

        # longueur du pas : il s'allonge quand tout est calme, il revient au pas de base dès que quelque chose change
        if x_porte is None and stable and self.confirme and abs(c) <= 40.0:
            self.pas = min(self.pas_max, self.pas * 2.0)
        elif cible is None and x_porte is None:
            self.pas = min(self.pas_max, self.pas0 * 2.0)        # rien de proche : pas de raison de s'arrêter souvent
        else:
            self.pas = self.pas0
        a = min(self.pas, reste)

        if x_porte is not None:
            approche = x_porte - RAYON - 250.0                   # s'arrêter le pare-chocs à 25 cm de ce qui dépasse
            if abs(c) <= AU_MILIEU and approche <= 150.0:
                if ouvert is not None and ouvert < TROUEE_MIN:
                    return dict(rep, geste="fin", raison=f"dans l'axe d'une trouée de {ouvert:.0f} mm seulement à {x_porte:.0f} mm : trop étroite pour franchir sans voir mieux")
                a = min(max(a, x_porte + RAYON + 150.0), 1000.0, reste)            # dans l'axe et tout près : on franchit d'une traite
                notes.append(f"dans l'axe du passage qui est à {x_porte:.0f} mm : franchissement")
            elif approche >= 150.0:
                a = min(a, approche)                             # s'approcher en rejoignant l'axe, puis regarder de près
            else:
                return dict(rep, geste="côté", dist=c)           # trop près pour rejoindre l'axe en biais
        psi = math.degrees(math.atan2(c, a))                     # direction à prendre, dans le repère des murs
        if abs(psi) > ANGLE_MAX:
            psi = math.copysign(ANGLE_MAX, psi)
        # chemin libre dans cette direction : un obstacle sûr sur la bande que le robot va balayer, ou un groupe dont
        # la direction est incertaine et dont le secteur couvre la direction prise
        libre = 1e9
        cp, sp = math.cos(math.radians(psi)), math.sin(math.radians(psi))
        for x, y, vers, mm, face in surs:
            le_long, de_cote = x * cp + y * sp, -x * sp + y * cp
            if le_long > 0 and abs(de_cote) < RAYON + 40.0 and le_long - RAYON - 150.0 < libre:
                libre = le_long - RAYON - 150.0
                notes.append(f"obstacle sur le chemin à {le_long:.0f} mm, {abs(de_cote):.0f} mm à {'gauche' if de_cote > 0 else 'droite'} de la ligne")
            cf = math.cos(math.radians(vers - psi))
            if face and cf > 0.5 and (mm - RAYON) / cf - 100.0 < libre:    # si c'est une face vue de biais, elle barre le chemin plus loin
                libre = (mm - RAYON) / cf - 100.0
                notes.append(f"écho large à {mm:.0f} mm vers {vers:+.0f}° : si c'est une paroi, elle coupe le chemin à {mm / cf:.0f} mm")
        for lo, hi, mm in flous:
            if lo <= psi <= hi and mm - RAYON - 150.0 < libre:
                libre = mm - RAYON - 150.0
                notes.append(f"quelque chose à {mm:.0f} mm dans la direction prise")
        if libre < a / cp:
            if libre < 60.0:
                return dict(rep, geste="fin", raison="obstacle devant : " + "; ".join(notes))
            self.pas = self.pas0
            return dict(rep, geste="avance", cap=psi - self.biais, dist=libre)
        return dict(rep, geste="avance", cap=psi - self.biais, dist=a / cp)


def centrer(m, axe, dist, pas=400.0, pas_max=800.0, vitesse=100, v_eventail=75, dire=print):
    """Mène le robot sur `dist` mm le long d'un passage dont l'axe est le cap `axe` du plan, en se centrant à chaque
    arrêt. m : Mobile. Renvoie un dictionnaire : fin (raison de l'arrêt), ok (distance faite), arrets (un dictionnaire
    par arrêt), biais et n_biais (cap du robot par rapport aux murs et nombre de mesures), duree (secondes)."""
    t0 = m.maintenant()
    X0, Y0, _, _ = m.pose()
    ca, sa = math.cos(math.radians(axe)), math.sin(math.radians(axe))

    def ici():
        X, Y, C, l = m.pose()
        return (X - X0) * ca + (Y - Y0) * sa, -(X - X0) * sa + (Y - Y0) * ca, C, l

    c = Centreur(pas, pas_max)
    res = {"arrets": [], "fin": None, "ok": False}
    try:
        _boucle(m, c, res, axe, dist, vitesse, v_eventail, dire, ici, t0)
    except OSError as err:                                       # liaison coupée : le cerveau finit seul son geste, qui est borné
        res["fin"] = f"liaison avec le cerveau perdue ({err})"
        res["sans_retour"] = True
    if not res.get("sans_retour") and not str(res["fin"]).startswith("arrêt sur alarme"):
        try:
            m.tourner_vers(axe - c.biais, v=V_ROTATION)          # le robot finit dans l'axe des murs, tel qu'il l'a mesuré
        except OSError as err:
            res["fin"] = f"{res['fin']} ; puis liaison perdue ({err})"
    res.update(biais=c.biais, n_biais=c.n_biais, confirme=c.confirme, duree=m.maintenant() - t0)
    return res


def _boucle(m, c, res, axe, dist, vitesse, v_eventail, dire, ici, t0):
    """les arrêts successifs de centrer() ; remplit res"""
    surplace = 0
    while True:
        rg = m.regard(axe + 90.0)
        ev = m.balayer(axe - 90.0, sens=-1, v=v_eventail) if rg is not None else None
        rd = m.regard(axe - 90.0) if ev is not None else None
        if rd is None:
            res["fin"] = "rotation refusée ou interrompue pendant les regards"
            res["sans_retour"] = True
            break
        s, t, C, l = ici()
        rel = [(ecart(cap - axe), us) for cap, us in ev if abs(ecart(cap - axe)) <= EVENTAIL]
        gr = groupes(rel)
        trou = trouee(rel)
        dec = c.arret(s, t, rg["mm"], rd["mm"], gr, reste=dist - s, trou=trou)
        dec.update(s=s, t=t, groupes=gr, trou=trou, heure=m.maintenant() - t0)
        res["arrets"].append(dec)
        txt = (f"arrêt {len(res['arrets'])} à {s / 1000:.2f} m : "
               f"{'rien' if dec['g'] is None else format(dec['g'], '.0f') + ' mm'} à gauche, "
               f"{'rien' if dec['d'] is None else format(dec['d'], '.0f') + ' mm'} à droite")
        if dec["largeur"] is not None:
            txt += f", passage de {dec['largeur']:.0f} mm"
        if dec["ecart"] is not None:
            txt += f" ; robot {abs(dec['ecart']):.0f} mm à {'gauche' if dec['ecart'] > 0 else 'droite'} du milieu"
        if c.n_biais:
            txt += f" ; cap par rapport aux murs {c.biais:+.1f}° ({c.n_biais} mesure{'s' if c.n_biais > 1 else ''})"
        dire(txt)
        for q in gr:
            if abs(q["dir"]) <= 60.0 and q["mm"] <= PORTEE_AVANT:
                dire(f"   devant : écho à {q['mm']:.0f} mm vers {q['dir']:+.0f}°, large de {q['larg']:.0f}°"
                     + (" (placé)" if q["sur"] else " (direction incertaine)"))
        if trou is not None and trou["a"] is not None and trou["b"] is not None:
            dire(f"   devant : trouée de {trou['a']:+.0f}° à {trou['b']:+.0f}° (milieu {trou['dir']:+.0f}°), bords à {trou['mm_a']:.0f} et {trou['mm_b']:.0f} mm")
        for n in dec["notes"]:
            dire("   " + n)
        if dec["geste"] == "fin":
            res["fin"] = dec["raison"]
            res["ok"] = dec["raison"] == "distance faite"
            break
        if len(res["arrets"]) >= ARRETS_MAX:
            res["fin"] = f"{ARRETS_MAX} arrêts sans arriver au bout"
            break
        if dec["geste"] == "côté":
            dire(f"   pas de côté de {abs(dec['dist']):.0f} mm vers la {'gauche' if dec['dist'] > 0 else 'droite'}")
            if m.tourner_vers(axe - c.biais + math.copysign(90.0, dec["dist"]), v=V_ROTATION) is None:
                res["fin"] = "rotation refusée avant un pas de côté"
                break
            r = m.avancer(abs(dec["dist"]), min(vitesse, 60))
        else:
            cap = axe + dec["cap"]
            reste_cap = m.tourner_vers(cap, v=V_ROTATION)
            if reste_cap is None:
                res["fin"] = "rotation refusée avant une avance"
                break
            dire(f"   avance de {dec['dist']:.0f} mm au cap {cap % 360.0:.1f}°")
            r = m.avancer(dec["dist"], vitesse, cap_rel=reste_cap if abs(reste_cap) >= 0.5 else 0.0)
        if "refus" in r:
            res["fin"] = "avance refusée : " + r["refus"]
            break
        if r.get("alarme"):
            res["fin"] = "arrêt sur alarme : " + str(r["alarme"])
            break
        fait = r.get("avance_mm") or 0.0
        if "distance" not in str(r.get("raison")):
            dire(f"   avance arrêtée après {fait:.0f} mm : {r.get('raison')}")
        surplace = surplace + 1 if fait < 30.0 else 0
        if surplace >= 2:
            res["fin"] = "le robot n'avance plus : " + str(r.get("raison"))
            break
