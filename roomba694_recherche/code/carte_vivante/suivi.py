# suivi.py — de ce qu'écrit l'enregistreur à ce que la carte vivante dessine.
#
# Entrées, toutes lues dans des fichiers (rien n'est demandé ni envoyé au robot) :
#   - les lignes du journal du cerveau (NOM_capteurs.csv, 20 par seconde) : position x, y, cap dans le repère du
#     cerveau, capteur de distance, pare-chocs, capteurs optiques ;
#   - des « ancres » : à tel instant, le robot était à tel endroit du plan. Elles viennent des programmes de
#     navigation (tour sur place jugé par le filtre de localiser.py, départ donné à explorer3.py, ligne POSE= de
#     passage.py) ; sources.py les tire de leurs fichiers.
# Sortie : la position du robot dans le repère du plan à chaque ligne, et des objets à dessiner (tracé, calages,
# contacts, objets frôlés, destinations, journal), chacun avec un numéro de version : la page ne redemande que ce
# qui a changé.
#
# Position affichée = dernière ancre + déplacement compté depuis par le cerveau, comme le font Estime.suivre
# d'explorer3.py et relance.py : chaque petit déplacement du cerveau est tourné de (cap du plan − cap du cerveau), et
# le cap du cerveau est multiplié par l'échelle du gyroscope (1,0045).
#
# Quand une nouvelle ancre arrive (fin d'un tour sur place), l'écart entre la position tenue jusque-là et celle de
# l'ancre est la correction. Elle est gardée (« avant », « corr ») pour que la page la montre, et répartie sur le
# tronçon roulé depuis l'ancre précédente, au prorata du chemin : le tracé passé se redresse et aboutit à la position
# calée. Un tronçon corrigé est dit « calé » ; le dernier, qui n'a pas encore de calage au bout, reste « à l'estime ».
#
# Si le cerveau redémarre ou si sa position est remise à zéro, son repère change : c'est une « rupture ». La position
# est alors inconnue jusqu'à l'ancre suivante ; ce qui a été roulé entre la rupture et cette ancre est placé après
# coup, en remontant le trajet à l'envers (« rétro »).
import bisect
import datetime
import math
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(ICI, "..", "outils")))
import grille as grille_mod  # noqa: E402   (les mêmes noms de cases que carte_grille.py)

K_GYRO = 1.0045                 # échelle du gyroscope du cerveau (journal_wifi.md § 31)
DX_CAPTEUR = 27.0               # mm : le capteur de distance est en avant du centre du robot
RAYON = 170.0                   # mm : rayon du robot
PAS_MM, PAS_DEG = 20.0, 2.0     # une ligne du journal est gardée pour le tracé tous les 2 cm ou 2°
N_TRONCON = 80                  # points par morceau de tracé envoyé à la page
SEUIL_PROCHE = 200              # signal d'un capteur optique du pare-chocs au-dessus duquel un objet est « frôlé »
ANGLES_OPTIQUES = (62.0, 36.0, 12.0, -12.0, -36.0, -62.0)     # G, AvG, CG, CD, AvD, D ; degrés, positif à gauche
CHAMPS_OPTIQUES = ("lb_g", "lb_avg", "lb_cg", "lb_cd", "lb_avd", "lb_d")
CHAMPS_VIDE = ("vide_g", "vide_avg", "vide_avd", "vide_d")
# une ligne du journal, une fois lue : un n-uplet
T_, X_, Y_, C_, US_, PG_, PD_, MODE_, MS_, LB_, ROUE_, MV_, MA_, VIDE_ = range(14)
SOURCES_MESUREES = ("filtre", "plan")       # ancres issues d'une mesure (tour sur place posé sur le plan)


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
            return (g("pc_s"), g("x_mm"), g("y_mm"), g("cap_pos"), g("us_mm", -1.0), int(g("pc_g")), int(g("pc_d")), int(g("mode")),
                    g("ms"), tuple(int(g(c)) for c in CHAMPS_OPTIQUES), int(g("roue_g")) | int(g("roue_d")), g("mv"), g("ma"),
                    min(g(c, 9999.0) for c in CHAMPS_VIDE))
        except ValueError:
            return None


class Suivi:
    def __init__(self, px_par_m=53.0, largeur=1214, hauteur=434, k_gyro=K_GYRO):
        self.s = px_par_m / 1000.0               # pixels du plan par millimètre
        self.W, self.H = largeur, hauteur
        self.gr = grille_mod.Grille(px_par_m, largeur, hauteur)
        self.k = k_gyro
        self.R, self.Tt = [], []                 # lignes du journal ; leurs heures (pour chercher par dichotomie)
        self.L, self.Rc = [], []                 # chemin et rotation cumulés, repère du cerveau
        self.est, self.cor = [], []              # position sur le plan : à l'estime depuis l'ancre ; corrigée après coup
        self.ech = []                            # numéros des lignes gardées pour le tracé
        self._ref = None                         # (chemin, cap, pare-chocs) de la dernière ligne gardée
        self.bornes = []                         # ancres et ruptures, triées par numéro de ligne puis par heure
        self.par_cle = {}
        self.n_cal = 0
        self._P = self._pb = None                # position sur le plan et dans le cerveau à la dernière ligne (tronçon ouvert)
        self.V = 0                               # numéro de version : augmente à chaque objet publié
        self.obj = {}                            # clé -> (version, données ou None si l'objet a disparu)
        self.n_troncons = 0
        self._seg_troncons = []                  # numéro du tronçon de chaque morceau publié
        self.contacts = []                       # [numéro de ligne, côté]
        self.proches = []                        # (numéro de ligne, numéro du capteur optique, signal)
        self._dernier_proche = {}
        self.evts = {}                           # clé -> événement du journal donné par les sources
        self.etat = {}                           # dernier /api/state lu par l'enregistreur (tour en cours, batterie)

    # ------------------------------------------------------------ petits outils
    def px(self, X, Y):
        return round(X * self.s, 1), round(self.H - Y * self.s, 1)

    def _pas(self, P, a, b):
        """position sur le plan après que le cerveau est passé de sa position a à sa position b"""
        dx, dy, dc = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        e = math.radians(P[2] - a[2])                     # ce qu'il faut ajouter au cap du cerveau
        c, s = math.cos(e), math.sin(e)
        return P[0] + c * dx - s * dy, P[1] + s * dx + c * dy, P[2] + self.k * dc

    def _pas_arriere(self, P, b, a):
        """l'inverse : P est la position sur le plan quand le cerveau est en b ; où était le robot quand il était en a ?"""
        dx, dy, dc = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        C = P[2] - self.k * dc
        e = math.radians(C - a[2])
        c, s = math.cos(e), math.sin(e)
        return P[0] - (c * dx - s * dy), P[1] - (s * dx + c * dy), C

    def _publier(self, cle, d):
        vieux = self.obj.get(cle)
        if vieux is not None and vieux[1] == d:
            return
        self.V += 1
        self.obj[cle] = (self.V, d)

    def pose_ligne(self, i):
        return self.cor[i] or self.est[i]

    # ------------------------------------------------------------ les lignes du journal
    def ajouter_lignes(self, lignes):
        n0, s_min = len(self.R), len(self.bornes)
        for r in lignes:
            i = len(self.R)
            neuf = True
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
                else:
                    neuf = False
                    self.L.append(self.L[-1] + math.hypot(r[X_] - a[X_], r[Y_] - a[Y_]))
                    self.Rc.append(self.Rc[-1] + abs(r[C_] - a[C_]))
            else:
                self.L.append(0.0)
                self.Rc.append(0.0)
            self.R.append(r)
            self.Tt.append(r[T_])
            b = (r[X_], r[Y_], r[C_])
            if self._P is not None:
                self._P = self._pas(self._P, self._pb, b)
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
        if len(self.R) > n0:
            self._refaire_troncons(s_min)
            self._objets()

    def _contact(self, i, a, r):
        """pare-chocs qui vient de s'enfoncer pendant que le robot bougeait : un contact"""
        touche, touchait = r[PG_] or r[PD_], a[PG_] or a[PD_]
        if touche and not touchait:
            j = bisect.bisect_left(self.Tt, r[T_] - 1.0)
            if self.L[i] - self.L[j] >= 5.0 or self.Rc[i] - self.Rc[j] >= 3.0:        # sur la base le pare-chocs est enfoncé sans que rien ne bouge
                self.contacts.append([i, "gauche" if not r[PD_] else "droit" if not r[PG_] else "devant"])
        elif touche and self.contacts and r[PG_] and r[PD_] and r[T_] - self.Tt[self.contacts[-1][0]] < 0.3:
            self.contacts[-1][1] = "devant"                       # les deux côtés à 0,3 s d'écart : contact de face

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
            k = 0
            while k < len(self.bornes) and (self.bornes[k]["i"], self.bornes[k]["t"]) <= (i, a["t"]):
                k += 1
            self.bornes.insert(k, a)
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

    def _calculer(self, s_min=0):
        """Recalcule la position sur le plan des lignes à partir du tronçon numéro s_min. Le tronçon s va de la borne
        s − 1 à la borne s (du début du journal pour s = 0, jusqu'à sa fin pour le dernier)."""
        B, R, n = self.bornes, self.R, len(self.R)
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
                    P = self._pas(P, pb, b)
                    pb = b
                    self.est[i], self.cor[i] = P, None
                if fa:                                            # l'ancre suivante ferme le tronçon : la correction
                    E = self._pas(P, pb, fa["b"])
                    dC = ecart(fa["C"] - E[2])
                    fa["Cd"] = E[2] + dC
                    fa["avant"] = E
                    fa["corr"] = (fa["X"] - E[0], fa["Y"] - E[1], dC)
                    d = math.hypot(fa["corr"][0], fa["corr"][1])
                    # une mesure (tour sur place) corrige le trajet qui y mène ; une position seulement redonnée par la
                    # navigation ne le corrige que si elle en est proche : au-delà, c'est un repositionnement
                    fa["repartie"] = fa["src"] in SOURCES_MESUREES or (d <= 250.0 and abs(dC) <= 20.0)
                    if fa["repartie"] and i1 > i0:
                        self._repartir(i0, i1, da["t"], fa["corr"])
                elif fin is None:
                    self._P, self._pb = P, pb
            elif fa:                                              # pas d'ancre avant : on remonte le trajet depuis celle-ci
                fa["Cd"], fa["avant"], fa["corr"], fa["repartie"] = fa["C"], None, None, False
                P, pb = (fa["X"], fa["Y"], fa["Cd"]), fa["b"]
                for i in range(i1 - 1, i0 - 1, -1):
                    r = R[i]
                    b = (r[X_], r[Y_], r[C_])
                    P = self._pas_arriere(P, pb, b)
                    pb = b
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
            u, v = self.px(b["X"], b["Y"])
            case = self.gr.nom(u, v)
            info = b.get("info") or {}
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
                x = f"Tour sur place en {case} : "
                if b.get("avant") is None:
                    x += "position calée sur le plan"
                elif mm < 20.0 and abs(dc) < 1.0:
                    x += f"position confirmée à {max(1, round(mm / 10.0))} cm près"
                else:
                    x += f"position corrigée de {fr(mm / 10.0, 0)} cm {vers(d['dir'])} et de {fr(abs(dc))}°"
                if info.get("note") is not None and info["note"] < 0.6:
                    x += f" — calage incertain (note {fr(info['note'], 2)})"
                g = "cal"
            else:
                qui = {"depart": "Position de départ donnée par la navigation", "annonce": "Position de départ donnée par la navigation",
                       "pose": "Position donnée par passage.py (à l'estime)", "manuel": "Position donnée à la main",
                       "report": "Position reprise de l'enregistrement précédent (à l'estime)"}.get(b["src"], "Position donnée")
                x = f"{qui} : {case}, tourné {vers(d['cap'])}"
                if b.get("avant") is not None:
                    x += f" ({fr(mm / 10.0, 0)} cm et {fr(abs(dc))}° d'écart avec la position suivie jusque-là)"
                g = "pos"
            jr.append({"t": b["t"], "g": g, "x": x, "u": u, "v": v})
        for q, (i, cote) in enumerate(self.contacts):
            P = self.pose_ligne(i)
            if P is None:
                self._publier(f"ct/{q}", None)
                continue
            ang = math.radians(P[2] + {"gauche": 50.0, "droit": -50.0}.get(cote, 0.0))
            u, v = self.px(P[0] + 200.0 * math.cos(ang), P[1] + 200.0 * math.sin(ang))
            case = self.gr.nom(*self.px(P[0], P[1]))
            self._publier(f"ct/{q}", {"t": round(self.Tt[i], 2), "h": heure_de(self.Tt[i]), "u": u, "v": v, "cote": cote, "case": case})
            jr.append({"t": self.Tt[i], "g": "contact", "u": u, "v": v,
                       "x": f"Contact du pare-chocs {'de face' if cote == 'devant' else cote} en {case}"})
        pr = []
        for i, q, val in self.proches:
            P = self.pose_ligne(i)
            if P is not None:
                ang = math.radians(P[2] + ANGLES_OPTIQUES[q])
                u, v = self.px(P[0] + (RAYON + 40.0) * math.cos(ang), P[1] + (RAYON + 40.0) * math.sin(ang))
                pr.append([u, v, val])
        self._publier("proches", pr)
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
        tour = (self.etat.get("tour") in (1, 2)) and abs(r[T_] - self.etat.get("t", 0.0)) < 3.0
        d["act"] = ("tour" if tour and abs(w) > 5 else "avance" if v > 15 else "recule" if v < -15 else "tourne" if abs(w) > 8 else "arret")
        if self.etat.get("q") is not None:
            d["q"], d["qmax"] = self.etat["q"], self.etat.get("qmax")
        if P is None:
            d["pourquoi"] = "rupture" if (self.bornes and self.bornes[-1]["type"] == "rupture") else "aucun calage"
            return d
        u, v = self.px(P[0], P[1])
        d.update({"u": u, "v": v, "cap": round(P[2] % 360.0, 1), "case": self.gr.nom(u, v)})
        a = self.bornes[-1]
        i0 = max(0, a["i"] - 1)
        info = a.get("info") or {}
        d["src"] = {"src": a["src"], "n": a["n"], "h": heure_de(a["t"]), "depuis_s": round(r[T_] - a["t"]), "mm": round(self.L[i] - self.L[min(i, i0)]),
                    "deg": round(self.Rc[i] - self.Rc[min(i, i0)]), "note": info.get("note"), "nom": info.get("nom")}
        return d

    def depuis(self, v):
        return {c: d for c, (ver, d) in self.obj.items() if ver > v}
