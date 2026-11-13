# carto.py — une carte faite de murs en lignes, sur laquelle chaque tour sur place recale la position du robot.
#
# Idée (rapport « sensor exploitation ideas », idée 2) : un mur lisse renvoie l'écho de son point le plus proche, donc un
# palier d'un tour sur place donne la distance du robot à ce mur, à un centimètre près, quelle que soit la largeur du
# faisceau. Un mur déjà connu, revu d'une nouvelle station, dit donc où est la station le long de la normale du mur ;
# deux murs à angle droit la fixent dans le plan. La direction des paliers, elle, ne donne le cap qu'à ±5° au mieux.
#
# Ce que le module offre :
#   - paliers() et paliers_souples() : les paliers d'un tour (tolérance fixe, ou qui grandit avec la distance) ;
#   - apparier() : le décalage réel entre deux tours faits presque au même endroit ; c'est ce dont explorer3.py se sert
#     pour recaler le robot quand il repasse par une station connue ;
#   - Carte.ajouter() : recalage d'une station, à son arrivée, sur les murs déjà connus (essayé le 2026-11-10 : ne suffit
#     pas seul, journal_wifi.md § 26) ;
#   - Carte.ajuster() : après coup (i_recalage.py), toutes les stations et tous les murs repris ensemble (moindres carrés).
#
# Repères : « odo » = celui du cerveau (x, y en mm, cap en degrés cumulés) ; « carte » = celui de la première station,
# dans lequel les murs sont fixes. Un mur est une droite n(phi)·X = rho, phi étant la direction de sa normale vue de
# l'intérieur (du robot vers le mur) et rho sa distance à l'origine le long de cette normale.
import math

import numpy as np
from scipy.optimize import least_squares

DX = 27.0              # mm : le devant du capteur de distance est en avant du centre du robot (contact du 2026-11-10)
TOL_PALIER = 25.0      # mm : écart toléré à l'intérieur d'un palier
PAS_CODEUR = 0.4446    # mm de roue par pas de codeur
VOIE_ROUES = 235.0     # mm entre les deux roues


def ecart_angle(a):
    """angle ramené entre -180 et 180 degrés"""
    return (a + 180.0) % 360.0 - 180.0


def patinage(a, b, k_gyro=1.0):
    """Entre deux lignes du journal du cerveau : ce qu'une roue a tourné de plus que le sol n'a défilé sous elle, en mm
    (positif : la roue droite, négatif : la gauche ; 0 s'il n'y a rien de net).

    Les deux codeurs disent de combien le robot a tourné (différence des deux roues) ; le gyroscope le dit aussi, sans
    les roues. Quand une roue patine, les codeurs comptent une rotation que le gyroscope ne voit pas. Le 2026-11-13,
    dans la pièce centrale, la roue droite a ainsi tourné 43 puis 35 cm de trop en deux avances : le robot a pivoté de
    58° et de 47°, et le chemin compté par le cerveau (la moyenne des deux roues) était trop long de 21 et de 17 cm
    (journal_wifi.md § 43). Ne vaut que roues dans le même sens (avance ou recul), et avec un gyroscope qui compte
    aussi les rotations lentes (firmware v9 et suivants). Seuil : 40 mm/s d'écart, soit 2 mm par ligne à 20 lignes par
    seconde ; sur les 160 m roulés ce jour-là il ne retire, hors des deux vrais patinages, que 0,05 % du chemin."""
    try:
        dg = (((b["enc_g"] - a["enc_g"]) + 32768) % 65536 - 32768) * PAS_CODEUR
        dd = (((b["enc_d"] - a["enc_d"]) + 32768) % 65536 - 32768) * PAS_CODEUR
        dc = b["cap_pos"] - a["cap_pos"]
        dt = (b["ms"] - a["ms"]) / 1000.0
    except (KeyError, TypeError):
        return 0.0
    if dg * dd <= 0 or abs(dg) > 60 or abs(dd) > 60 or abs(dc) > 30:
        return 0.0
    if not 0.0 < dt <= 1.0:
        dt = 0.05
    delta = (dd - dg) - math.radians(k_gyro * dc) * VOIE_ROUES
    return delta if abs(delta) > max(2.0, 40.0 * dt) else 0.0


def part_roulee(a, b, k_gyro=1.0):
    """Part du chemin compté par le cerveau entre deux lignes du journal qui a vraiment été parcourue : 1 en temps
    normal, moins quand une roue patine (le cerveau compte la moyenne des deux roues : on retire la moitié de ce que
    la roue qui patine a tourné de trop)."""
    delta = patinage(a, b, k_gyro)
    if delta == 0.0:
        return 1.0
    d = abs((((b["enc_g"] - a["enc_g"]) + 32768) % 65536 - 32768) + (((b["enc_d"] - a["enc_d"]) + 32768) % 65536 - 32768)) * PAS_CODEUR / 2.0
    return max(0.0, d - abs(delta) / 2.0) / d if d > 0 else 1.0


def paliers(d, r):
    """Paliers d'un tour : liste de (direction du milieu en degrés depuis le départ du tour, distance en mm du centre du
    robot, largeur en degrés, nombre de mesures). d : directions en degrés, r : distances en mm (0 = rien à portée)."""
    d, r = np.asarray(d, float), np.asarray(r, float)
    m = d < 360.0                                   # les 20° lus deux fois ne comptent qu'une fois
    d, r = d[m], r[m]
    n = len(d)
    coupe = [k for k in range(n) if r[k] <= 0 or abs(r[k] - r[k - 1]) > 60]
    k0 = coupe[0] if coupe else 0                   # on démarre sur une rupture pour ne pas couper un palier à 0°
    d = np.r_[d[k0:], d[:k0] + 360.0]
    r = np.r_[r[k0:], r[:k0]]
    out, i = [], 0
    while i < n:
        if r[i] <= 0:
            i += 1
            continue
        j = i
        while j + 1 < n and r[j + 1] > 0 and abs(r[j + 1] - np.median(r[i:j + 1])) <= TOL_PALIER and d[j + 1] - d[j] < 9:
            j += 1
        if j - i + 1 >= 4:
            v = np.sort(r[i:j + 1])
            q = len(v) // 4
            out.append((((d[i] + d[j]) / 2) % 360.0, float(np.median(v[q:len(v) - q])) + DX, float(d[j] - d[i]), j - i + 1))
        i = j + 1
    return out


def paliers_souples(d, r, tol_mm=30.0, tol_rel=0.012, trous=1):
    """Comme paliers(), pour décider ce qui est un mur pendant une exploration : la tolérance grandit avec la distance
    (1,2 % de la distance, 30 mm au moins) et une mesure isolée qui s'écarte ou qui manque ne coupe pas le palier.
    Un mur à 3 ou 4 m donne en vrai un palier de 35 à 45° dont les lectures bougent de quelques centimètres (tours du
    2026-11-10) : paliers() le coupait en morceaux de moins de 15°."""
    d, r = np.asarray(d, float), np.asarray(r, float)
    m = d < 360.0
    d, r = d[m], r[m]
    n = len(d)
    coupe = [k for k in range(n) if r[k] <= 0 or abs(r[k] - r[k - 1]) > 60]
    k0 = coupe[0] if coupe else 0
    d = np.r_[d[k0:], d[:k0] + 360.0]
    r = np.r_[r[k0:], r[:k0]]
    out, i = [], 0
    while i < n:
        if r[i] <= 0:
            i += 1
            continue
        membres, manque, k = [i], 0, i + 1
        while k < n and d[k] - d[k - 1] < 9:
            med = float(np.median(r[membres]))
            if r[k] > 0 and abs(r[k] - med) <= max(tol_mm, tol_rel * med):
                membres.append(k)
                manque = 0
            else:
                manque += 1
                if manque > trous:
                    break
            k += 1
        if len(membres) >= 4:
            v = np.sort(r[membres])
            q = len(v) // 4
            out.append((((d[membres[0]] + d[membres[-1]]) / 2) % 360.0, float(np.median(v[q:len(v) - q])) + DX,
                        float(d[membres[-1]] - d[membres[0]]), len(membres)))
        i = membres[-1] + 1
    return out


def apparier(pal_a, cap_a, pal_b, cap_b, larg_min=12.0, porte_deg=20.0, porte_mm=300.0, tol_mm=40.0):
    """Deux tours faits presque au même endroit : de combien le robot est-il décalé au second par rapport au premier ?
    Un palier large vu dans la même direction (à porte_deg près) par les deux tours est la même paroi ; la différence des
    deux distances est le décalage le long de cette direction. Renvoie (dx, dy, paires gardées, rang) dans le repère où
    les caps sont comptés, ou None s'il n'y a pas au moins deux paires d'accord. Les paires qui s'écartent de la
    solution de plus de tol_mm sont écartées une à une (paliers d'objets, mauvaises paires)."""
    paires, pris = [], set()
    for (mid_a, da, la, na) in sorted(pal_a, key=lambda p: -p[2]):
        if la < larg_min:
            continue
        ta = cap_a + mid_a
        cands = [(abs(ecart_angle(cap_b + mid_b - ta)), k) for k, (mid_b, db, lb, nb) in enumerate(pal_b)
                 if k not in pris and lb >= larg_min and abs(db - da) < porte_mm]
        cands = [c for c in cands if c[0] <= porte_deg]
        if not cands:
            continue
        e, k = min(cands)
        pris.add(k)
        tb = cap_b + pal_b[k][0]
        t = math.radians(ta + ecart_angle(tb - ta) / 2.0)          # direction moyenne des deux paliers
        paires.append((math.cos(t), math.sin(t), da - pal_b[k][1], min(la, pal_b[k][2])))
    while len(paires) >= 2:
        G = np.array([[p[0], p[1]] for p in paires])
        h = np.array([p[2] for p in paires])
        _, sv, vt = np.linalg.svd(G, full_matrices=False)
        rang = 2 if (len(sv) > 1 and sv[1] >= 0.6) else 1           # parois presque parallèles entre elles : une seule direction
        if rang == 2:
            sol, *_ = np.linalg.lstsq(G, h, rcond=None)
        else:                                                        # le décalage n'est connu que le long de cette direction
            u = vt[0]
            g = G @ u
            sol = u * float((g @ h) / (g @ g))
        res = G @ sol - h
        pire = int(np.argmax(np.abs(res)))
        if abs(res[pire]) <= tol_mm:
            return float(sol[0]), float(sol[1]), paires, rang
        paires.pop(pire)
    return None


class Station:
    def __init__(self, nom, odo, d, r, heure=None, tapis=False):
        self.nom = nom
        self.odo = tuple(float(v) for v in odo)     # position annoncée par le cerveau au départ du tour : x, y, cap
        self.pose = self.odo                        # position dans la carte, corrigée
        self.d = np.asarray(d, float)
        self.r = np.asarray(r, float)
        self.heure = heure                          # secondes depuis minuit, si connue
        self.tapis = tapis
        self.paliers = paliers(self.d, self.r)
        self.mur = [None] * len(self.paliers)       # mur auquel chaque palier est rattaché
        self.correction = (0.0, 0.0, 0.0)           # ce que le recalage a changé à la position prédite : dx, dy, dcap

    def echos(self):
        """points vus par le capteur, posés sur son axe, dans la carte"""
        m = self.r > 0
        a = np.radians(self.pose[2] + self.d[m])
        return self.pose[0] + (self.r[m] + DX) * np.cos(a), self.pose[1] + (self.r[m] + DX) * np.sin(a)


class Mur:
    def __init__(self, phi, rho):
        self.phi, self.rho = float(phi), float(rho)
        self.obs = []                               # (station, indice du palier)

    def normale(self):
        return np.array([math.cos(math.radians(self.phi)), math.sin(math.radians(self.phi))])

    def stations(self):
        return sorted({s.nom for s, k in self.obs})

    def pieds(self):
        """point du mur donné par chaque palier (pied de la perpendiculaire), dans la carte"""
        n = self.normale()
        return np.array([[s.pose[0] + s.paliers[k][1] * n[0], s.pose[1] + s.paliers[k][1] * n[1]] for s, k in self.obs])


class Carte:
    def __init__(self, axe=None):
        self.stations = []
        self.murs = []
        self.axe = axe                              # direction principale de la pièce (degrés, entre 0 et 90), ou None
        self.axe_fixe = axe is not None             # axe imposé par l'appelant : il n'est pas revoté
        self.T = (0.0, 0.0, 0.0)                    # passage odo -> carte : rotation de T[2] degrés puis translation (T[0], T[1])

    # ------------------------------------------------------------ changements de repère
    def vers_carte(self, x, y, cap=None):
        c, s = math.cos(math.radians(self.T[2])), math.sin(math.radians(self.T[2]))
        X, Y = self.T[0] + c * x - s * y, self.T[1] + s * x + c * y
        return (X, Y) if cap is None else (X, Y, cap + self.T[2])

    def vers_odo(self, X, Y):
        c, s = math.cos(math.radians(self.T[2])), math.sin(math.radians(self.T[2]))
        dx, dy = X - self.T[0], Y - self.T[1]
        return c * dx + s * dy, -s * dx + c * dy

    def _poser_T(self, st):
        """T tel que la position odo de la station tombe sur sa position dans la carte"""
        t = st.pose[2] - st.odo[2]
        c, s = math.cos(math.radians(t)), math.sin(math.radians(t))
        self.T = (st.pose[0] - (c * st.odo[0] - s * st.odo[1]), st.pose[1] - (s * st.odo[0] + c * st.odo[1]), t)

    # ------------------------------------------------------------ axes de la pièce
    def voter_axe(self):
        th, w = [], []
        for st in self.stations:
            for mid, dist, larg, nb in st.paliers:
                if larg >= 15.0:                    # seuls les paliers larges votent : ce sont eux qui viennent de murs
                    th.append(st.pose[2] + mid)
                    w.append(nb)
        if not th:
            return
        th, w = np.array(th), np.array(w, float)
        phis = np.arange(0, 90, 0.5)
        score = [np.sum(w * np.exp(-0.5 * ((((th - p + 45) % 90) - 45) / 8.0) ** 2)) for p in phis]
        self.axe = float(phis[int(np.argmax(score))])

    def _sur_axe(self, phi, tol=14.0):
        """direction ramenée sur l'axe de la pièce le plus proche, si elle en est à moins de tol degrés"""
        if self.axe is None:
            return phi
        e = ((phi - self.axe + 45.0) % 90.0) - 45.0
        return phi - e if abs(e) <= tol else phi

    # ------------------------------------------------------------ rattachement des paliers aux murs
    def _est_mur(self, st, k, larg_min=15.0, nb_min=5, tol_axe=16.0):
        """Un palier compte comme un mur s'il est large (surface plane vue de face) et tourné vers un axe de la pièce.
        Les paliers étroits viennent d'objets ou d'arêtes : ils donnent la même distance sous plusieurs caps sans être
        des murs (piège du 2026-11-10, journal § 22), et ne servent ni à recaler ni à dessiner."""
        mid, dist, larg, nb = st.paliers[k]
        if larg < larg_min or nb < nb_min:
            return False
        if self.axe is None:
            return True
        return abs((((st.pose[2] + mid) - self.axe + 45.0) % 90.0) - 45.0) <= tol_axe

    def _rattacher(self, st, porte_mm=80.0, porte_deg=25.0, marge_mm=50.0):
        """Rattache chaque palier « mur » de la station au mur connu qu'il prolonge. La porte est étroite : deux parois
        parallèles à 15 cm l'une de l'autre (un meuble devant un mur) ne doivent pas être confondues ; si deux murs
        connus conviennent presque aussi bien, le palier n'est rattaché à aucun."""
        n_lies = 0
        for k, (mid, dist, larg, nb) in enumerate(st.paliers):
            st.mur[k] = None
            if not self._est_mur(st, k):
                continue
            psi = st.pose[2] + mid
            cands = []
            for mur in self.murs:
                if abs(ecart_angle(psi - mur.phi)) > porte_deg:
                    continue
                n = mur.normale()
                e = abs(n[0] * st.pose[0] + n[1] * st.pose[1] + dist - mur.rho)
                if e <= porte_mm:
                    cands.append((e, mur))
            cands.sort(key=lambda c: c[0])
            if cands and (len(cands) == 1 or cands[1][0] - cands[0][0] >= marge_mm):
                st.mur[k] = cands[0][1]
                n_lies += 1
        return n_lies

    @staticmethod
    def _sigma(larg):
        """incertitudes d'un palier selon sa largeur : distance au mur (mm), direction (degrés)"""
        return (15.0 if larg >= 15 else 30.0), (10.0 if larg >= 25 else 16.0)

    # ------------------------------------------------------------ ajout d'une station, recalage en ligne
    def ajouter(self, nom, odo, d, r, heure=None, tapis=False, chemin_mm=None):
        """Ajoute un tour sur place et recale sa station sur les murs connus. Renvoie la station."""
        st = Station(nom, odo, d, r, heure, tapis)
        if not self.stations:
            st.pose = st.odo
            self.stations.append(st)
            self.voter_axe()
            self._nouveaux_murs(st)
            self._poser_T(st)
            return st
        prec = self.stations[-1]
        pred = self.vers_carte(*st.odo)                                   # où le cerveau croit être, vu dans la carte
        if chemin_mm is None:
            chemin_mm = math.hypot(st.odo[0] - prec.odo[0], st.odo[1] - prec.odo[1]) * 1.2 + 100.0
        dt_min = max(0.5, ((st.heure - prec.heure) / 60.0) if (st.heure and prec.heure) else 1.0)
        s_xy, s_cap = 20.0 + 0.015 * chemin_mm, 2.0 + 0.5 * dt_min
        st.pose = pred
        for _ in range(3):                                                # rattacher, résoudre, recommencer
            n_lies = self._rattacher(st)
            if n_lies == 0:
                break

            def res(p):
                out = [(p[0] - pred[0]) / s_xy, (p[1] - pred[1]) / s_xy, (p[2] - pred[2]) / s_cap]
                for k, (mid, dist, larg, nb) in enumerate(st.paliers):
                    mur = st.mur[k]
                    if mur is None:
                        continue
                    n = mur.normale()
                    sd, sa = self._sigma(larg)
                    out.append((mur.rho - (n[0] * p[0] + n[1] * p[1]) - dist) / sd)
                    out.append(ecart_angle(p[2] + mid - mur.phi) / sa)
                return np.array(out)

            sol = least_squares(res, np.array(st.pose, float), loss="soft_l1", f_scale=1.5)
            st.pose = tuple(float(v) for v in sol.x)
        st.correction = (st.pose[0] - pred[0], st.pose[1] - pred[1], st.pose[2] - pred[2])
        self.stations.append(st)
        if len(self.stations) <= 3 and not self.axe_fixe:
            self.voter_axe()                        # les axes de la pièce se précisent avec les premières stations
        self._rattacher(st)
        for k, mur in enumerate(st.mur):
            if mur is not None:
                mur.obs.append((st, k))
        self._nouveaux_murs(st)
        self._poser_T(st)
        return st

    def _nouveaux_murs(self, st):
        for k, (mid, dist, larg, nb) in enumerate(st.paliers):
            if st.mur[k] is not None or not self._est_mur(st, k):
                continue
            phi = self._sur_axe(st.pose[2] + mid, tol=16.5) % 360.0
            n = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
            rho = n[0] * st.pose[0] + n[1] * st.pose[1] + dist
            # un mur connu presque au même endroit (palier resté ambigu) : on n'en crée pas un second
            if any(abs(ecart_angle(phi - m.phi)) < 20 and abs(rho - m.rho) < 80 for m in self.murs):
                continue
            n = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
            mur = Mur(phi, n[0] * st.pose[0] + n[1] * st.pose[1] + dist)
            mur.obs.append((st, k))
            st.mur[k] = mur
            self.murs.append(mur)

    # ------------------------------------------------------------ ajustement d'ensemble, après coup
    def revisites(self, rayon_mm=150.0):
        """Paires de stations que le cerveau croit au même endroit (à rayon_mm près), avec le décalage réel que donnent
        leurs paliers larges (apparier). Chaque paire est une « fermeture de boucle » : elle dit de combien le cerveau
        s'est trompé entre les deux passages. Renvoie une liste de (station a, station b, dx, dy, paires, rang)."""
        out = []
        for i, a in enumerate(self.stations):
            for b in self.stations[i + 1:]:
                if math.hypot(a.odo[0] - b.odo[0], a.odo[1] - b.odo[1]) > rayon_mm:
                    continue
                r = apparier(a.paliers, a.odo[2], b.paliers, b.odo[2])
                if r is not None and len(r[2]) >= 2 and max(p[3] for p in r[2]) >= 20.0:    # au moins deux parois, dont une bien large
                    out.append((a, b, r[0], r[1], r[2], r[3]))
        return out

    def ajuster(self, tours=3, manhattan_deg=3.0):
        """Reprend toutes les stations (sauf la première) et tous les murs vus d'au moins deux stations, ensemble.
        Renvoie un dictionnaire de chiffres avant et après."""
        avant = self.bilan()
        boucles = self.revisites()
        self.boucles = boucles
        for _ in range(tours):
            murs = [m for m in self.murs if len(m.stations()) >= 2]
            if not murs:
                break
            idx_m = {id(m): i for i, m in enumerate(murs)}
            libres = self.stations[1:]
            idx_s = {id(s): i for i, s in enumerate(libres)}
            x0 = np.r_[np.array([s.pose for s in libres], float).ravel(), np.array([[m.phi, m.rho] for m in murs], float).ravel()]
            ns = len(libres)
            # murs proches d'un axe de la pièce au départ : eux seuls reçoivent le rappel vers l'axe (liste fixée avant de résoudre)
            pres_axe = {id(m): self.axe is not None and abs(((m.phi - self.axe + 45.0) % 90.0) - 45.0) < 15.0 for m in murs}

            def pose(x, s):
                if id(s) not in idx_s:
                    return s.pose
                i = idx_s[id(s)]
                return x[3 * i], x[3 * i + 1], x[3 * i + 2]

            def res(x):
                out = []
                # 1. le cerveau : déplacement et rotation d'une station à la suivante
                for a, b in zip(self.stations, self.stations[1:]):
                    pa, pb = pose(x, a), pose(x, b)
                    ca, sa = math.cos(math.radians(a.odo[2])), math.sin(math.radians(a.odo[2]))
                    dxo, dyo = b.odo[0] - a.odo[0], b.odo[1] - a.odo[1]
                    lx, ly = ca * dxo + sa * dyo, -sa * dxo + ca * dyo                 # déplacement vu de la station a (odo)
                    cm, sm = math.cos(math.radians(pa[2])), math.sin(math.radians(pa[2]))
                    ex, ey = pb[0] - pa[0], pb[1] - pa[1]
                    mx, my = cm * ex + sm * ey, -sm * ex + cm * ey                     # le même, dans la carte
                    chemin = math.hypot(dxo, dyo) * 1.2 + 100.0
                    dt_min = max(0.5, ((b.heure - a.heure) / 60.0) if (a.heure and b.heure) else 1.0)
                    s_xy, s_cap = 20.0 + 0.015 * chemin, 2.0 + 0.5 * dt_min
                    out += [(mx - lx) / s_xy, (my - ly) / s_xy, ((pb[2] - pa[2]) - (b.odo[2] - a.odo[2])) / s_cap]
                # 1 bis. les retours au même endroit : le décalage réel entre les deux passages, paroi par paroi.
                # Les directions des parois ont été relevées avec les caps du cerveau : elles sont tournées de la
                # correction de cap de la station a pour être exprimées dans la carte.
                for a, b, dx_, dy_, paires, rang in boucles:
                    pa, pb = pose(x, a), pose(x, b)
                    ta = math.radians(pa[2] - a.odo[2])
                    ct, st_ = math.cos(ta), math.sin(ta)
                    for nx, ny, dd, larg in paires:
                        mx_, my_ = ct * nx - st_ * ny, st_ * nx + ct * ny
                        out.append((mx_ * (pb[0] - pa[0]) + my_ * (pb[1] - pa[1]) - dd) / 15.0)
                # 2. les murs : distance et direction de chaque palier
                for m in murs:
                    j = ns * 3 + 2 * idx_m[id(m)]
                    phi, rho = x[j], x[j + 1]
                    n0, n1 = math.cos(math.radians(phi)), math.sin(math.radians(phi))
                    for s, k in m.obs:
                        p = pose(x, s)
                        mid, dist, larg, nb = s.paliers[k]
                        sd, sa_ = self._sigma(larg)
                        out.append((rho - (n0 * p[0] + n1 * p[1]) - dist) / sd)
                        out.append(ecart_angle(p[2] + mid - phi) / sa_)
                    # 3. la pièce est à angles droits : chaque mur proche d'un axe y est doucement ramené
                    if pres_axe[id(m)]:
                        out.append((((phi - self.axe + 45.0) % 90.0) - 45.0) / manhattan_deg)
                return np.array(out)

            sol = least_squares(res, x0, loss="soft_l1", f_scale=1.5)
            for s in libres:
                i = idx_s[id(s)]
                s.pose = (float(sol.x[3 * i]), float(sol.x[3 * i + 1]), float(sol.x[3 * i + 2]))
            for m in murs:
                j = ns * 3 + 2 * idx_m[id(m)]
                m.phi, m.rho = float(sol.x[j]) % 360.0, float(sol.x[j + 1])
            # les murs vus d'une seule station suivent leur station ; puis on rattache de nouveau tous les paliers
            for m in self.murs:
                m.obs = []
            for s in self.stations:
                self._rattacher(s)
                for k, m in enumerate(s.mur):
                    if m is not None:
                        m.obs.append((s, k))
            self.murs = [m for m in self.murs if m.obs]
            for s in self.stations:
                self._nouveaux_murs(s)
            self._fusionner()
        self._poser_T(self.stations[-1])
        return {"avant": avant, "apres": self.bilan()}

    def _fusionner(self, mm=80.0, deg=12.0):
        """deux murs de même direction et de même position n'en font qu'un"""
        garde = []
        for m in sorted(self.murs, key=lambda m: -len(m.obs)):
            for g in garde:
                if abs(ecart_angle(m.phi - g.phi)) < deg and abs(m.rho - g.rho) < mm:
                    for s, k in m.obs:
                        g.obs.append((s, k))
                        s.mur[k] = g
                    break
            else:
                garde.append(m)
        self.murs = garde

    # ------------------------------------------------------------ chiffres
    def bilan(self):
        """accord entre stations sur la position des murs vus d'au moins deux stations"""
        ecarts, n_murs = [], 0
        for m in self.murs:
            if len(m.stations()) < 2:
                continue
            n_murs += 1
            n = m.normale()
            rho = [n[0] * s.pose[0] + n[1] * s.pose[1] + s.paliers[k][1] for s, k in m.obs]
            ecarts += [v - float(np.mean(rho)) for v in rho]
        e = np.array(ecarts) if ecarts else np.array([0.0])
        return {"murs_partages": n_murs, "observations": len(ecarts), "ecart_type_mm": float(e.std()), "pire_mm": float(np.abs(e).max())}
