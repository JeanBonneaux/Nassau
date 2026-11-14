# suivi.py — de ce qu'écrit l'enregistreur à ce que la carte vivante dessine.
#
# Entrées, toutes lues dans des fichiers (rien n'est demandé ni envoyé au robot) :
#   - les lignes du journal du cerveau (NOM_capteurs.csv, 20 par seconde) : position x, y, cap dans le repère du
#     cerveau, compteurs des roues, capteur de distance, pare-chocs, capteurs optiques, récepteurs infrarouges ;
#   - des « ancres » : à tel instant, le robot était à tel endroit du plan. Elles viennent des programmes de
#     navigation (tour sur place jugé par le filtre de localiser.py et recalé sur les repères, départ donné à
#     explorer3.py, ligne POSE= de passage.py ou de balise_base.py) et de la base de recharge (robot posé dessus) ;
#     sources.py les tire des fichiers.
# Sortie : la position du robot dans le repère du plan à chaque ligne, et des objets à dessiner (tracé, calages,
# contacts, objets frôlés, patinages, signal de la base, destinations, journal), chacun avec un numéro de version :
# la page ne redemande que ce qui a changé.
#
# Position affichée = dernière ancre + déplacement compté depuis par le cerveau, comme le font Estime.suivre
# d'explorer3.py et relance.py : chaque petit déplacement du cerveau est tourné de (cap du plan − cap du cerveau), et
# le cap du cerveau est multiplié par l'échelle du gyroscope (1,0045). Quand une roue patine (les compteurs annoncent
# une rotation que le gyroscope ne voit pas), le chemin compté en trop est retiré, par le même calcul que la
# navigation (carto.patinage, firmware v9 et suivants ; journal_wifi.md § 43 et § 44).
#
# Quand une nouvelle ancre arrive (fin d'un tour sur place), l'écart entre la position tenue jusque-là et celle de
# l'ancre est la correction. Elle est gardée (« avant », « corr ») pour que la page la montre, et répartie sur le
# tronçon roulé depuis l'ancre précédente, au prorata du chemin : le tracé passé se redresse et aboutit à la position
# calée. Un tronçon corrigé est dit « calé » ; le dernier, qui n'a pas encore de calage au bout, reste « à l'estime ».
#
# La position devient inconnue dans quatre cas, jusqu'à l'ancre suivante ; ce qui a été roulé entre-temps est placé
# après coup, en remontant le trajet à l'envers (« rétro ») :
#   - « rupture » : le cerveau redémarre ou sa position est remise à zéro, son repère change ;
#   - robot soulevé (les deux roues en l'air plus d'une seconde) : quelqu'un le porte ;
#   - robot tourné à la main : son cap change de 8° ou plus en moins de 5 s alors que les compteurs de ses roues ne
#     bougent pas (le 2026-11-14 à 9 h 34, robot posé sur sa base à la main sans que ses roues se lèvent) ;
#   - robot qui quitte sa base : sur sa base alimentée il ignore les ordres de roues, c'est donc qu'on l'en a tiré à la
#     main, et le cerveau compte mal un robot poussé à la main (position.ino).
import bisect
import collections
import datetime
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(ICI, "..", "outils")))
import grille as grille_mod  # noqa: E402   (les mêmes noms de cases que carte_grille.py)

try:
    import carto as carto_mod  # noqa: E402   (le patinage d'une roue, calculé comme le fait la navigation)
except Exception:                               # numpy ou scipy absents : la carte s'en passe, le patinage n'est pas retiré
    carto_mod = None

K_GYRO = 1.0045                 # échelle du gyroscope du cerveau (journal_wifi.md § 31)
DX_CAPTEUR = 27.0               # mm : le capteur de distance est en avant du centre du robot
RAYON = 170.0                   # mm : rayon du robot
RAYON_IR = 126.0                # mm : le récepteur infrarouge du dessus est à l'avant, à cette distance du centre (§ 39)
PAS_MM, PAS_DEG = 20.0, 2.0     # une ligne du journal est gardée pour le tracé tous les 2 cm ou 2°
N_TRONCON = 80                  # points par morceau de tracé envoyé à la page
SEUIL_PROCHE = 200              # signal d'un capteur optique du pare-chocs au-dessus duquel un objet est « frôlé »
PATINAGE_MIN = 60.0             # mm de roue en trop à partir desquels un patinage est signalé (seuil de t_patinage.py)
PORTE_S = 1.0                   # secondes : les deux roues en l'air plus longtemps que cela, le robot est porté
TOURNE_DEG, TOURNE_S = 8.0, 5.0  # cap qui change d'autant, en moins de ce temps, roues immobiles : le robot est tourné à la main
ANGLES_OPTIQUES = (62.0, 36.0, 12.0, -12.0, -36.0, -62.0)     # G, AvG, CG, CD, AvD, D ; degrés, positif à gauche
CHAMPS_OPTIQUES = ("lb_g", "lb_avg", "lb_cg", "lb_cd", "lb_avd", "lb_d")
CHAMPS_VIDE = ("vide_g", "vide_avg", "vide_avd", "vide_d")
# une ligne du journal, une fois lue : un n-uplet (ROUE_ : 1 = roue gauche levée, 2 = droite, 3 = les deux ;
# IR_ : codes reçus par les récepteurs du dessus, avant gauche, avant droit ; EG_, ED_ : compteurs des roues)
T_, X_, Y_, C_, US_, PG_, PD_, MODE_, MS_, LB_, ROUE_, MV_, MA_, VIDE_, IR_, EG_, ED_ = range(17)
# ancres issues d'une mesure : tour sur place posé sur le plan, robot posé sur sa base
SOURCES_MESUREES = ("filtre", "plan", "base")


def ecart(a):
    return (a + 180.0) % 360.0 - 180.0


def heure_de(t):
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S")


VERS = {"droite": "la droite", "gauche": "la gauche", "haut": "le haut", "bas": "le bas", "haut-droite": "le haut et la droite",
        "haut-gauche": "le haut et la gauche", "bas-droite": "le bas et la droite", "bas-gauche": "le bas et la gauche"}


def vers(cap):
    """« vers le haut et la droite » : la direction sur le plan, dans les mots de la carte quadrillée"""
    return "vers " + VERS[grille_mod.mot_du_cap(cap)]


def fr(x, n=1):
    """nombre à la française : virgule décimale"""
    return f"{x:.{n}f}".replace(".", ",")


class LecteurCsv:
    """lit les lignes de NOM_capteurs.csv d'après les noms de colonnes de son en-tête"""

    def __init__(self):
        self.ix, self.n = None, 0

    def entete(self, texte):
        cols = texte.strip().split(",")
        if "pc_s" not in cols or "x_mm" not in cols or "cap_pos" not in cols:
            return False
        self.ix, self.n = {c: k for k, c in enumerate(cols)}, len(cols)
        return True

    def ligne(self, texte):
        f = texte.split(",")
        if self.ix is None or len(f) != self.n:
            return None
        ix = self.ix
        try:
            def g(c, defaut=0.0):
                return float(f[ix[c]]) if c in ix else defaut
            codeurs = "enc_g" in ix and "enc_d" in ix
            return (g("pc_s"), g("x_mm"), g("y_mm"), g("cap_pos"), g("us_mm", -1.0), int(g("pc_g")), int(g("pc_d")), int(g("mode")),
                    g("ms"), tuple(int(g(c)) for c in CHAMPS_OPTIQUES), (1 if g("roue_g") else 0) | (2 if g("roue_d") else 0), g("mv"), g("ma"),
                    min(g(c, 9999.0) for c in CHAMPS_VIDE), (int(g("ir_dessus")), int(g("ir_g")), int(g("ir_d"))),
                    int(g("enc_g")) if codeurs else None, int(g("enc_d")) if codeurs else None)
        except ValueError:
            return None


class Suivi:
    def __init__(self, px_par_m=53.0, largeur=1214, hauteur=434, k_gyro=K_GYRO):
        self.s = px_par_m / 1000.0               # pixels du plan par millimètre
        self.W, self.H = largeur, hauteur
        self.gr = grille_mod.Grille(px_par_m, largeur, hauteur)
        self.k = k_gyro
        self.R, self.Tt = [], []                 # lignes du journal ; leurs heures (pour chercher par dichotomie)
        self.L, self.Rc = [], []                 # chemin (patinage retiré) et rotation cumulés, repère du cerveau
        self.F = []                              # part du chemin compté vraiment roulée entre la ligne d'avant et celle-ci (1 sauf patinage)
        self.est, self.cor = [], []              # position sur le plan : à l'estime depuis l'ancre ; corrigée après coup
        self.ech = []                            # numéros des lignes gardées pour le tracé
        self._ref = None                         # (chemin, cap, pare-chocs) de la dernière ligne gardée
        self.bornes = []                         # ancres, ruptures et déplacements à la main, triés par numéro de ligne puis par heure
        self.par_cle = {}
        self._cles_portes = set()
        self.n_cal = 0
        self._P = self._pb = None                # position sur le plan et dans le cerveau à la dernière ligne (tronçon ouvert)
        self.V = 0                               # numéro de version : augmente à chaque objet publié
        self.obj = {}                            # clé -> (version, données ou None si l'objet a disparu)
        self.n_troncons = 0
        self._seg_troncons = []                  # numéro du tronçon de chaque morceau publié
        self.contacts = []                       # [numéro de ligne, côté]
        self.proches = []                        # (numéro de ligne, numéro du capteur optique, signal)
        self._dernier_proche = {}
        self.firmware = None                     # numéro de version du firmware du cerveau, lu dans son état
        self.patinage = False                    # retirer le patinage du chemin compté ? (firmware v9 et suivants, comme explorer3.py)
        self.patine = []                         # épisodes : [ligne de début, ligne de fin, mm de roue en trop (+ : droite), mm retirés, heure, clos]
        self.ir = []                             # (numéro de ligne, code reçu de la base par le récepteur du dessus)
        self._ir_ref = None
        self._leve = None                        # [numéro de ligne, heure, déjà signalé] depuis que les deux roues sont en l'air
        self._fige = None                        # [compteur gauche, compteur droit, (heure, cap, ligne) des 5 dernières secondes, déjà signalé] depuis que les roues ne tournent plus
        self._t_porte = None                     # heure du dernier déplacement à la main signalé (un seul par geste : 30 s)
        self.pose_base = None                    # (X, Y, C) du robot posé sur sa base, mm et degrés du plan ; None : base inconnue
        self.evts = {}                           # clé -> événement du journal donné par les sources
        self.etat = {}                           # dernier /api/state lu par l'enregistreur (tour en cours, batterie, base)

    # ------------------------------------------------------------ petits outils
    def px(self, X, Y):
        return round(X * self.s, 1), round(self.H - Y * self.s, 1)

    def _pas(self, P, a, b, f=1.0):
        """position sur le plan après que le cerveau est passé de sa position a à sa position b (f : part vraiment roulée)"""
        dx, dy, dc = (b[0] - a[0]) * f, (b[1] - a[1]) * f, b[2] - a[2]
        e = math.radians(P[2] - a[2])                     # ce qu'il faut ajouter au cap du cerveau
        c, s = math.cos(e), math.sin(e)
        return P[0] + c * dx - s * dy, P[1] + s * dx + c * dy, P[2] + self.k * dc

    def _pas_arriere(self, P, b, a, f=1.0):
        """l'inverse : P est la position sur le plan quand le cerveau est en b ; où était le robot quand il était en a ?"""
        dx, dy, dc = (b[0] - a[0]) * f, (b[1] - a[1]) * f, b[2] - a[2]
        C = P[2] - self.k * dc
        e = math.radians(C - a[2])
        c, s = math.cos(e), math.sin(e)
        return P[0] - (c * dx - s * dy), P[1] - (s * dx + c * dy), C

    def _part(self, a, r):
        """(part vraiment roulée du chemin compté, mm de roue en trop) entre deux lignes : (1, 0) sauf quand une roue patine"""
        if not self.patinage or r[EG_] is None or a[EG_] is None:
            return 1.0, 0.0
        da = {"enc_g": a[EG_], "enc_d": a[ED_], "cap_pos": a[C_], "ms": a[MS_]}
        db = {"enc_g": r[EG_], "enc_d": r[ED_], "cap_pos": r[C_], "ms": r[MS_]}
        delta = carto_mod.patinage(da, db, self.k)
        if delta == 0.0:
            return 1.0, 0.0
        return carto_mod.part_roulee(da, db, self.k), delta

    def _publier(self, cle, d):
        vieux = self.obj.get(cle)
        if (vieux[1] if vieux is not None else None) == d:
            return
        self.V += 1
        self.obj[cle] = (self.V, d)

    def _inserer(self, b):
        """range une borne à sa place (par numéro de ligne, puis par heure) ; renvoie son rang"""
        k = 0
        while k < len(self.bornes) and (self.bornes[k]["i"], self.bornes[k]["t"]) <= (b["i"], b["t"]):
            k += 1
        self.bornes.insert(k, b)
        return k

    def pose_ligne(self, i):
        return self.cor[i] or self.est[i]

    def point_contact(self, i, cote):
        """Pixel du plan touché par le pare-chocs à la ligne i (à 20 cm du centre, du côté touché), ou None si la position
        n'est pas connue ou si c'est la base elle-même que le robot touche en s'y posant."""
        P = self.pose_ligne(i)
        if P is None:
            return None
        ang = math.radians(P[2] + {"gauche": 50.0, "droit": -50.0}.get(cote, 0.0))
        X, Y = P[0] + 200.0 * math.cos(ang), P[1] + 200.0 * math.sin(ang)
        if self.pose_base is not None and math.hypot(X - self.pose_base[0], Y - self.pose_base[1]) < 250.0:
            return None
        return self.px(X, Y)

    # ------------------------------------------------------------ les lignes du journal
    def ajouter_lignes(self, lignes):
        n0, s_min = len(self.R), len(self.bornes)
        portes = []
        for r in lignes:
            i = len(self.R)
            neuf = True
            f = 1.0
            if i:
                a = self.R[-1]
                dt = r[T_] - a[T_]
                if dt < -1.0:
                    continue                                      # ligne plus vieille que la précédente : ignorée
                dms = r[MS_] - a[MS_]
                meme_demarrage = dms > -1000.0 and abs(dms / 1000.0 - dt) < max(5.0, 0.02 * abs(dt))
                saut = abs(r[X_] - a[X_]) > 500 or abs(r[Y_] - a[Y_]) > 500 or abs(r[C_] - a[C_]) > 300
                if not meme_demarrage or (saut and dt < 3.0) or abs(r[C_] - a[C_]) > 3000:
                    # cerveau redémarré, ou position remise à zéro : l'ancien repère est perdu
                    self.bornes.append({"type": "rupture", "i": i, "t": r[T_], "cle": f"rupture|{i}"})
                    self.L.append(self.L[-1])
                    self.Rc.append(self.Rc[-1])
                    self._P = self._pb = None
                    self._fige = None
                    if self.patine:
                        self.patine[-1][5] = True
                else:
                    neuf = False
                    f, delta = self._part(a, r)
                    d = math.hypot(r[X_] - a[X_], r[Y_] - a[Y_])
                    self.L.append(self.L[-1] + f * d)
                    self.Rc.append(self.Rc[-1] + abs(r[C_] - a[C_]))
                    if delta:
                        self._patiner(i, r[T_], delta, (1.0 - f) * d)
            else:
                self.L.append(0.0)
                self.Rc.append(0.0)
            self.R.append(r)
            self.Tt.append(r[T_])
            self.F.append(f)
            b = (r[X_], r[Y_], r[C_])
            if self._P is not None:
                self._P = self._pas(self._P, self._pb, b, f)
                self._pb = b
            self.est.append(self._P)
            self.cor.append(None)
            pc = (r[PG_], r[PD_])
            if (neuf or self._ref is None or self.L[i] - self._ref[0] >= PAS_MM or abs(r[C_] - self._ref[1]) >= PAS_DEG
                    or pc != self._ref[2]):
                self.ech.append(i)
                self._ref = (self.L[i], r[C_], pc)
            if not neuf:
                self._contact(i, a, r)
            for q in range(6):                                    # objet tout près d'un capteur optique du pare-chocs
                if r[LB_][q] >= SEUIL_PROCHE:
                    ref = self._dernier_proche.get(q)
                    if ref is None or math.hypot(r[X_] - ref[0], r[Y_] - ref[1]) >= 40.0 or abs(r[C_] - ref[2]) >= 8.0:
                        self._dernier_proche[q] = b
                        self.proches.append((i, q, r[LB_][q]))
            code = r[IR_][0]                                      # signal de la base reçu par le récepteur du dessus
            if code:
                ref = self._ir_ref
                if ref is None or code != ref[3] or math.hypot(r[X_] - ref[0], r[Y_] - ref[1]) >= 30.0 or abs(r[C_] - ref[2]) >= 8.0:
                    self._ir_ref = (r[X_], r[Y_], r[C_], code)
                    self.ir.append((i, code))
            if r[ROUE_] == 3:                                     # les deux roues en l'air : au bout d'une seconde, le robot est porté
                if self._leve is None:
                    self._leve = [i, r[T_], False]
                elif not self._leve[2] and r[T_] - self._leve[1] >= PORTE_S:
                    self._leve[2] = True
                    if self._t_porte is None or r[T_] - self._t_porte >= 30.0:
                        self._t_porte = r[T_]
                        portes.append((self._leve[0], self._leve[1], "soulevé"))
            else:
                self._leve = None
            if r[EG_] is not None:                                # le cap change et les roues ne tournent pas : on le tourne à la main
                fg = self._fige
                if fg is None or abs(r[EG_] - fg[0]) > 2 or abs(r[ED_] - fg[1]) > 2:
                    self._fige = fg = [r[EG_], r[ED_], collections.deque(), False]
                q = fg[2]
                q.append((r[T_], r[C_], i))
                while r[T_] - q[0][0] > TOURNE_S:
                    q.popleft()
                if not fg[3] and self._leve is None and abs(r[C_] - q[0][1]) >= TOURNE_DEG:
                    fg[3] = True
                    if self._t_porte is None or r[T_] - self._t_porte >= 30.0:
                        self._t_porte = r[T_]
                        # le début du geste : la dernière ligne où le cap n'avait pas encore bougé d'un degré
                        k = next((n for n in range(len(q) - 1, -1, -1) if abs(q[n][1] - q[0][1]) < 1.0), 0)
                        portes.append((q[k][2] + 1, q[k][0], "tourné"))
        if len(self.R) > n0:
            if portes:
                k_min = None
                for i0, t0, cause in portes:
                    self._cles_portes.add(f"porte|{i0}")
                    k = self._inserer({"type": "porte", "i": i0, "t": t0, "cle": f"porte|{i0}", "cause": cause})
                    k_min = k if k_min is None else min(k_min, k)
                s_min = min(s_min, k_min)
                self._calculer(k_min)
            self._refaire_troncons(s_min)
            self._objets()

    def _contact(self, i, a, r):
        """Pare-chocs qui vient de s'enfoncer pendant que le cerveau conduisait le robot : un contact. En mode passif
        (2), c'est le robot qui se conduit seul vers sa base, ou quelqu'un qui le pousse : son pare-chocs s'enfonce
        plusieurs fois pendant l'accostage (cinq fois le 2026-11-14 à 9 h 34) et le cerveau compte mal ce trajet-là ;
        ce ne sont pas des obstacles."""
        if r[MODE_] < 3:
            return
        touche, touchait = r[PG_] or r[PD_], a[PG_] or a[PD_]
        if touche and not touchait:
            j = bisect.bisect_left(self.Tt, r[T_] - 1.0)
            if self.L[i] - self.L[j] >= 5.0 or self.Rc[i] - self.Rc[j] >= 3.0:        # sur la base le pare-chocs est enfoncé sans que rien ne bouge
                self.contacts.append([i, "gauche" if not r[PD_] else "droit" if not r[PG_] else "devant"])
        elif touche and self.contacts and r[PG_] and r[PD_] and r[T_] - self.Tt[self.contacts[-1][0]] < 0.3:
            self.contacts[-1][1] = "devant"                       # les deux côtés à 0,3 s d'écart : contact de face

    def _patiner(self, i, t, delta, retire):
        """une roue a tourné de delta mm de plus que le sol n'a défilé sous elle, à la ligne i : épisode en cours ou nouveau"""
        ep = self.patine[-1] if self.patine else None
        if ep is None or ep[5] or t - ep[4] > 1.0:
            ep = [i, i, 0.0, 0.0, t, False]
            self.patine.append(ep)
        ep[1], ep[2], ep[3], ep[4] = i, ep[2] + delta, ep[3] + retire, t

    def fixer_firmware(self, n):
        """Numéro de version du firmware du cerveau, lu dans son état. À partir de la v9 le gyroscope compte aussi les
        rotations lentes : le patinage d'une roue se voit et il est retiré du chemin compté, comme dans explorer3.py."""
        if n is None or n == self.firmware:
            return
        self.firmware = n
        actif = n >= 9 and carto_mod is not None
        if actif != self.patinage:
            self.patinage = actif
            if self.R:                                            # des lignes étaient déjà là : chemin et positions sont refaits
                self.patine, self.F, L = [], [1.0] * len(self.R), [0.0]
                ruptures = {b["i"] for b in self.bornes if b["type"] == "rupture"}
                for i in range(1, len(self.R)):
                    a, r = self.R[i - 1], self.R[i]
                    if i in ruptures:
                        L.append(L[-1])
                        if self.patine:
                            self.patine[-1][5] = True
                        continue
                    f, delta = self._part(a, r)
                    d = math.hypot(r[X_] - a[X_], r[Y_] - a[Y_])
                    L.append(L[-1] + f * d)
                    self.F[i] = f
                    if delta:
                        self._patiner(i, r[T_], delta, (1.0 - f) * d)
                self.L = L
                self._calculer(0)
                self._refaire_troncons(0)
                self._objets()

    # ------------------------------------------------------------ les ancres
    def poser(self, ancres):
        """Ajoute ou met à jour des ancres : dictionnaires avec « cle », « t », « src », « X », « Y », « C » (mm et degrés
        du plan), « b » (position du cerveau au même instant, ou None : celle de la dernière ligne), « info »."""
        s_min = None
        for a in ancres:
            a = dict(a)
            if a.get("b") is not None:
                a["b"] = tuple(float(x) for x in a["b"])
            elif not self.R:
                continue                                          # aucune ligne encore : on ne sait pas où est le cerveau
            vieux = self.par_cle.get(a["cle"])
            if vieux is not None:
                if all(vieux.get(c) == a.get(c) for c in ("t", "src", "X", "Y", "C", "info")) and (a.get("b") is None or a["b"] == vieux["b"]):
                    continue
                k = self.bornes.index(vieux)
                self.bornes.pop(k)
                a["n"] = vieux["n"]
                s_min = k if s_min is None else min(s_min, k)
            else:
                self.n_cal += 1
                a["n"] = self.n_cal
            a["type"] = "ancre"
            i = a["i"] = bisect.bisect_right(self.Tt, a["t"])
            if a.get("b") is None:
                r = self.R[max(0, i - 1)]
                a["b"] = (r[X_], r[Y_], r[C_])
            a["Cd"] = a["C"]
            k = self._inserer(a)
            self.par_cle[a["cle"]] = a
            s_min = k if s_min is None else min(s_min, k)
        if s_min is None:
            return False
        self._calculer(s_min)
        self._refaire_troncons(s_min)
        self._objets()
        return True

    def retirer(self, cles):
        """retire des ancres qui n'ont plus lieu d'être (un départ annoncé au pixel près, remplacé par le départ exact)"""
        s_min = None
        for c in cles:
            a = self.par_cle.pop(c, None)
            if a is None:
                continue
            k = self.bornes.index(a)
            self.bornes.pop(k)
            self._publier(f"cal/{a['n']}", None)
            s_min = k if s_min is None else min(s_min, k)
        if s_min is None:
            return False
        self._calculer(s_min)
        self._refaire_troncons(s_min)
        self._objets()
        return True

    def deplacer(self, t, cle, cause):
        """Le robot a été déplacé à la main à l'heure t (tiré de sa base) : sa position n'est plus connue jusqu'à
        l'ancre suivante. Renvoie True si c'est nouveau."""
        if cle in self._cles_portes or not self.R:
            return False
        self._cles_portes.add(cle)
        for b in self.bornes:                                     # le même geste déjà vu autrement (robot tourné en le tirant) : on garde la cause la plus parlante
            if b["type"] == "porte" and abs(b["t"] - t) < 30.0:
                if b["cause"] != cause:
                    b["cause"] = cause
                    self._objets()
                return False
        self._t_porte = t if self._t_porte is None else max(self._t_porte, t)
        k = self._inserer({"type": "porte", "i": bisect.bisect_right(self.Tt, t), "t": t, "cle": cle, "cause": cause})
        self._calculer(k)
        self._refaire_troncons(k)
        self._objets()
        return True

    def _calculer(self, s_min=0):
        """Recalcule la position sur le plan des lignes à partir du tronçon numéro s_min. Le tronçon s va de la borne
        s − 1 à la borne s (du début du journal pour s = 0, jusqu'à sa fin pour le dernier)."""
        B, R, F, n = self.bornes, self.R, self.F, len(self.R)
        for s in range(max(0, s_min), len(B) + 1):
            deb = B[s - 1] if s > 0 else None
            fin = B[s] if s < len(B) else None
            i0, i1 = (deb["i"] if deb else 0), (fin["i"] if fin else n)
            da = deb if deb and deb["type"] == "ancre" else None
            fa = fin if fin and fin["type"] == "ancre" else None
            if da:                                                # de l'ancre vers la suite : à l'estime
                P, pb = (da["X"], da["Y"], da["Cd"]), da["b"]
                for i in range(i0, i1):
                    r = R[i]
                    b = (r[X_], r[Y_], r[C_])
                    P = self._pas(P, pb, b, F[i])
                    pb = b
                    self.est[i], self.cor[i] = P, None
                if fa:                                            # l'ancre suivante ferme le tronçon : la correction
                    E = self._pas(P, pb, fa["b"])
                    dC = ecart(fa["C"] - E[2])
                    fa["Cd"] = E[2] + dC
                    fa["avant"] = E
                    fa["corr"] = (fa["X"] - E[0], fa["Y"] - E[1], dC)
                    d = math.hypot(fa["corr"][0], fa["corr"][1])
                    # une mesure (tour sur place, base) corrige le trajet qui y mène ; une position seulement redonnée par
                    # la navigation ne le corrige que si elle en est proche : au-delà, c'est un repositionnement
                    fa["repartie"] = fa["src"] in SOURCES_MESUREES or (d <= 250.0 and abs(dC) <= 20.0)
                    if fa["repartie"] and i1 > i0:
                        self._repartir(i0, i1, da["t"], fa["corr"])
                elif fin is None:
                    self._P, self._pb = P, pb
            elif fa:                                              # pas d'ancre avant : on remonte le trajet depuis celle-ci
                fa["Cd"], fa["avant"], fa["corr"], fa["repartie"] = fa["C"], None, None, False
                P, pb, f = (fa["X"], fa["Y"], fa["Cd"]), fa["b"], 1.0
                for i in range(i1 - 1, i0 - 1, -1):
                    r = R[i]
                    b = (r[X_], r[Y_], r[C_])
                    P = self._pas_arriere(P, pb, b, f)
                    pb, f = b, F[i]                               # le pas d'avant est celui qui a mené à la ligne i
                    self.est[i], self.cor[i] = P, None
            else:                                                 # ni avant ni après : position inconnue
                for i in range(i0, i1):
                    self.est[i] = self.cor[i] = None
                if fin is None:
                    self._P = self._pb = None

    def _repartir(self, i0, i1, t0, corr):
        """répartit la correction sur les lignes i0 à i1 − 1 : au prorata du chemin roulé, sinon de la rotation, sinon du temps"""
        L0 = self.L[i0 - 1] if i0 > 0 else 0.0
        R0 = self.Rc[i0 - 1] if i0 > 0 else 0.0
        Lt, Rt, Tt = self.L[i1 - 1] - L0, self.Rc[i1 - 1] - R0, self.Tt[i1 - 1] - t0
        for i in range(i0, i1):
            if Lt >= 50.0:
                w = (self.L[i] - L0) / Lt
            elif Rt >= 5.0:
                w = (self.Rc[i] - R0) / Rt
            elif Tt > 0:
                w = (self.Tt[i] - t0) / Tt
            else:
                w = 1.0
            w = max(0.0, min(1.0, w))
            E = self.est[i]
            self.cor[i] = (E[0] + w * corr[0], E[1] + w * corr[1], E[2] + w * corr[2])

    # ------------------------------------------------------------ le tracé, par morceaux
    def _point(self, P, us):
        u, v = self.px(P[0], P[1])
        return [u, v, round(P[2] % 360.0, 1), int(us)]

    def _refaire_troncons(self, s_min):
        B = self.bornes
        garde = 0
        while garde < len(self._seg_troncons) and self._seg_troncons[garde] < s_min:
            garde += 1
        del self._seg_troncons[garde:]
        k = garde
        for s in range(max(0, s_min), len(B) + 1):
            deb = B[s - 1] if s > 0 else None
            fin = B[s] if s < len(B) else None
            i0, i1 = (deb["i"] if deb else 0), (fin["i"] if fin else len(self.R))
            da = deb if deb and deb["type"] == "ancre" else None
            fa = fin if fin and fin["type"] == "ancre" else None
            if i1 <= i0 or not (da or fa):
                continue
            etat = ("cale" if (fa and fa.get("repartie")) else "estime") if da else "retro"
            pts = [self._point((da["X"], da["Y"], da["Cd"]), -1)] if da else []
            for i in self.ech[bisect.bisect_left(self.ech, i0):bisect.bisect_left(self.ech, i1)]:
                P = self.cor[i] or self.est[i]
                if P is not None:
                    pts.append(self._point(P, self.R[i][US_]))
            if fa and etat != "estime":
                pts.append(self._point((fa["X"], fa["Y"], fa["Cd"]), -1))
            if len(pts) < 2:
                continue
            q = 0
            while q < len(pts) - 1:
                self._publier(f"t/{k}", {"e": etat, "p": pts[q:q + N_TRONCON + 1]})       # un point commun avec le morceau suivant
                self._seg_troncons.append(s)
                k += 1
                q += N_TRONCON
        for q in range(k, self.n_troncons):
            self._publier(f"t/{q}", None)
        self.n_troncons = k

    # ------------------------------------------------------------ les autres objets
    def _objets(self):
        jr = []
        for b in self.bornes:
            if b["type"] == "rupture":
                jr.append({"t": b["t"], "g": "alerte", "x": "Le cerveau a redémarré ou sa position a été remise à zéro : "
                           "position inconnue jusqu'au prochain calage"})
                continue
            if b["type"] == "porte":                              # déplacé à la main : là où il a été vu pour la dernière fois
                P = self.pose_ligne(b["i"] - 1) if b["i"] > 0 else None
                d = {"t": round(b["t"], 2), "h": heure_de(b["t"]), "cause": b["cause"]}
                e = {"t": b["t"], "g": "alerte"}
                x = {"soulevé": "Robot soulevé (ses deux roues en l'air)", "tourné": "Robot tourné à la main (son cap change, ses roues ne tournent pas)",
                     "base": "Le robot a quitté sa base, tiré à la main"}[b["cause"]]
                if P is not None:
                    u, v = self.px(P[0], P[1])
                    d.update({"u": u, "v": v, "cap": round(P[2] % 360.0, 1), "case": self.gr.nom(u, v)})
                    e.update({"u": u, "v": v})
                    if b["cause"] != "base":
                        x += f" en {d['case']}"
                x += " : position inconnue jusqu'au prochain calage"
                self._publier(f"pd/{b['cle']}", d)
                jr.append(dict(e, x=x))
                continue
            u, v = self.px(b["X"], b["Y"])
            case = self.gr.nom(u, v)
            info = b.get("info") or {}
            rep = info.get("rep") or {}
            d = {"t": round(b["t"], 2), "h": heure_de(b["t"]), "src": b["src"], "u": u, "v": v, "cap": round(b["Cd"] % 360.0, 1),
                 "case": case, "info": info, "muet": b["src"] not in SOURCES_MESUREES}
            mm = dc = 0.0
            if b.get("avant") is not None:
                au, av = self.px(b["avant"][0], b["avant"][1])
                mm, dc = math.hypot(b["corr"][0], b["corr"][1]), b["corr"][2]
                d.update({"av": [au, av, round(b["avant"][2] % 360.0, 1)], "d": round(mm), "cm": int(f"{mm / 10.0:.0f}"), "dc": round(dc, 1), "rep": bool(b["repartie"]),
                          "dir": round(math.degrees(math.atan2(b["corr"][1], b["corr"][0])) % 360.0)})
                if mm >= 30.0 or abs(dc) >= 3.0:
                    d["muet"] = False
            elif b["src"] not in SOURCES_MESUREES:
                d["muet"] = False                                  # première position connue : à dire
            self._publier(f"cal/{b['n']}", d)
            if d["muet"]:
                continue
            if b["src"] in SOURCES_MESUREES:
                if b["src"] == "base":
                    x = f"Robot posé sur sa base, en {case} : "
                else:
                    x = f"Tour sur place en {case}" + (f", calé sur {rep['n']} repères" if rep.get("n") else "") + " : "
                if b.get("avant") is None:
                    x += "position sûre" if b["src"] == "base" else "position calée sur le plan"
                elif mm < 20.0:
                    x += f"position confirmée à {max(1, round(mm / 10.0))} cm près" + (f", cap corrigé de {fr(abs(dc))}°" if abs(dc) >= 1.0 else "")
                else:
                    x += f"position corrigée de {fr(mm / 10.0, 0)} cm {vers(d['dir'])} et de {fr(abs(dc))}°"
                if rep.get("cap") is not None:
                    x += f" (cap repris sur les repères : {fr(rep['cap'])}°)"
                if b["src"] != "base" and not rep.get("n") and info.get("note") is not None and info["note"] < 0.6:
                    x += f" — calage incertain (note {fr(info['note'], 2)})"
                g = "cal"
            else:
                qui = {"depart": "Position de départ donnée par la navigation", "annonce": "Position de départ donnée par la navigation",
                       "pose": f"Position donnée par {info.get('nom') or 'passage.py'} (à l'estime)", "manuel": "Position donnée à la main",
                       "report": "Position reprise de l'enregistrement précédent (à l'estime)"}.get(b["src"], "Position donnée")
                x = f"{qui} : {case}, tourné {vers(d['cap'])}"
                if b.get("avant") is not None:
                    x += f" ({fr(mm / 10.0, 0)} cm et {fr(abs(dc))}° d'écart avec la position suivie jusque-là)"
                g = "pos"
            jr.append({"t": b["t"], "g": g, "x": x, "u": u, "v": v})
        for q, (i, cote) in enumerate(self.contacts):
            uv = self.point_contact(i, cote)
            if uv is None:
                self._publier(f"ct/{q}", None)
                continue
            (u, v), P = uv, self.pose_ligne(i)
            case = self.gr.nom(*self.px(P[0], P[1]))
            self._publier(f"ct/{q}", {"t": round(self.Tt[i], 2), "h": heure_de(self.Tt[i]), "u": u, "v": v, "cote": cote, "case": case})
            jr.append({"t": self.Tt[i], "g": "contact", "u": u, "v": v,
                       "x": f"Contact du pare-chocs {'de face' if cote == 'devant' else cote} en {case}"})
        for q, ep in enumerate(self.patine):                      # une roue qui tourne plus que le sol ne défile sous elle
            if abs(ep[2]) < PATINAGE_MIN:
                continue
            P = self.pose_ligne(ep[0])
            if P is None:
                self._publier(f"pt/{q}", None)
                continue
            u, v = self.px(P[0], P[1])
            case, cote, t = self.gr.nom(u, v), ("droite" if ep[2] > 0 else "gauche"), self.Tt[ep[0]]
            self._publier(f"pt/{q}", {"t": round(t, 2), "h": heure_de(t), "u": u, "v": v, "case": case, "cote": cote,
                                      "mm": round(abs(ep[2])), "retire": round(ep[3]), "s": round(self.Tt[ep[1]] - t, 1)})
            jr.append({"t": t, "g": "alerte", "u": u, "v": v,
                       "x": f"Roue {cote} qui patine en {case} : {fr(abs(ep[2]) / 10.0, 0)} cm de trop, {fr(ep[3] / 10.0, 0)} cm retirés du trajet compté"})
        pr = []
        for i, q, val in self.proches:
            P = self.pose_ligne(i)
            if P is not None:
                ang = math.radians(P[2] + ANGLES_OPTIQUES[q])
                u, v = self.px(P[0] + (RAYON + 40.0) * math.cos(ang), P[1] + (RAYON + 40.0) * math.sin(ang))
                pr.append([u, v, val])
        self._publier("proches", pr)
        ir = []
        for i, code in self.ir:                                   # là où était le récepteur du dessus quand il a reçu la base
            P = self.pose_ligne(i)
            if P is not None:
                ang = math.radians(P[2])
                u, v = self.px(P[0] + RAYON_IR * math.cos(ang), P[1] + RAYON_IR * math.sin(ang))
                ir.append([u, v, code])
        self._publier("ir", ir)
        jr.extend(self.evts.values())
        jr.sort(key=lambda e: e["t"])
        self._publier("journal", [dict(e, t=round(e["t"], 2), h=heure_de(e["t"])) for e in jr[-150:]])

    def fixer_evts(self, evts):
        if evts != self.evts:
            self.evts = dict(evts)
            self._objets()

    def fixer(self, cle, d):
        """publie tel quel un objet tenu par les sources (destinations, obstacles relevés par la navigation, séance)"""
        self._publier(cle, d)

    # ------------------------------------------------------------ le robot, à l'instant
    def robot(self, maintenant):
        if not self.R:
            return {"connu": False, "pourquoi": "aucune ligne du journal"}
        i = len(self.R) - 1
        r, P = self.R[i], self.est[i]
        d = {"t": round(r[T_], 2), "h": heure_de(r[T_]), "age": round(maintenant - r[T_], 1), "us": int(r[US_]), "pc": [r[PG_], r[PD_]],
             "mode": r[MODE_], "roue": r[ROUE_], "lb": list(r[LB_]), "mv": int(r[MV_]), "ma": int(r[MA_]), "connu": P is not None}
        j = bisect.bisect_left(self.Tt, r[T_] - 0.5)
        v = w = 0.0
        if j < i and r[T_] - self.Tt[j] > 0.15:
            a = self.R[j]
            dt = r[T_] - a[T_]
            ca = math.radians(a[C_])
            v = (math.cos(ca) * (r[X_] - a[X_]) + math.sin(ca) * (r[Y_] - a[Y_])) / dt
            w = (r[C_] - a[C_]) / dt
        d["vit"], d["rot"] = round(v), round(w, 1)
        frais = abs(r[T_] - self.etat.get("t", 0.0)) < 5.0
        tour = (self.etat.get("tour") in (1, 2)) and abs(r[T_] - self.etat.get("t", 0.0)) < 3.0
        d["act"] = ("tour" if tour and abs(w) > 5 else "avance" if v > 15 else "recule" if v < -15 else "tourne" if abs(w) > 8 else "arret")
        if self.etat.get("q") is not None:
            d["q"], d["qmax"] = self.etat["q"], self.etat.get("qmax")
        if frais and self.etat.get("base") is not None:
            d["base"], d["chg"] = bool(self.etat["base"]), self.etat.get("chg")
        ir = [0, 0, 0]                                            # un code n'arrive qu'une ligne sur deux : on regarde une seconde
        j = i
        while j >= 0 and r[T_] - self.Tt[j] <= 1.0:
            for q in range(3):
                ir[q] = ir[q] or self.R[j][IR_][q]
            j -= 1
        if any(ir):
            d["ir"] = ir
        ep = self.patine[-1] if self.patine else None
        if ep is not None and not ep[5] and r[T_] - ep[4] <= 0.6 and abs(ep[2]) >= 20.0:
            d["patine"] = round(ep[2])                            # une roue patine en ce moment (positif : la droite)
        if P is None:
            b = self.bornes[-1] if self.bornes else None
            d["pourquoi"] = b["type"] if b is not None and b["type"] in ("rupture", "porte") else "aucun calage"
            if b is not None and b["type"] == "porte":
                d["cause"] = b["cause"]
            k = b["i"] - 1 if b is not None and b["type"] != "ancre" else -1
            Pd = self.pose_ligne(k) if 0 <= k < len(self.R) else None
            if Pd is not None:                                    # là où il a été vu pour la dernière fois
                u, v = self.px(Pd[0], Pd[1])
                d["dernier"] = {"u": u, "v": v, "cap": round(Pd[2] % 360.0, 1), "case": self.gr.nom(u, v), "h": heure_de(self.Tt[k])}
            return d
        u, v = self.px(P[0], P[1])
        d.update({"u": u, "v": v, "cap": round(P[2] % 360.0, 1), "case": self.gr.nom(u, v)})
        a = self.bornes[-1]
        i0 = max(0, a["i"] - 1)
        info = a.get("info") or {}
        d["src"] = {"src": a["src"], "n": a["n"], "h": heure_de(a["t"]), "depuis_s": round(r[T_] - a["t"]), "mm": round(self.L[i] - self.L[min(i, i0)]),
                    "deg": round(self.Rc[i] - self.Rc[min(i, i0)]), "note": info.get("note"), "nom": info.get("nom"),
                    "rep": (info.get("rep") or {}).get("n")}
        return d

    def depuis(self, v):
        return {c: d for c, (ver, d) in self.obj.items() if ver > v}
