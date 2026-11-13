# explorer3.py — exploration complète : le PC choisit lui-même les stations, passe les portes, revient par des trajets
# déjà faits, corrige sa position en repassant par une station connue, et s'arrête quand il ne reste rien à voir.
#
# S'utilise pendant qu'enregistreur.py tourne (voir pilote.py). Le robot doit être réveillé, en mode Safe, capteur de
# distance en mode fixe droit devant. Le repère de la carte est la position du robot au lancement (station 0, cap 0).
#
# Ce qui change par rapport à explorer.py :
#   1. La position est tenue sur le PC à partir du journal : le cap du cerveau est multiplié par l'échelle du gyroscope
#      (--k-gyro, 1,0015 mesuré le 2026-11-10). Cette échelle est ensuite ajustée en route par les murs : quand le
#      robot longe un mur vu de deux stations de suite, la distance à ce mur ne doit changer que de ce que dit le
#      trajet ; l'écart donne l'erreur de cap. Chaque mesure est bruitée ; toutes ensemble donnent l'échelle, et à
#      chaque ajustement tout le trajet et toutes les stations sont recalculés.
#   2. Les obstacles ne sont plus tous les échos : chaque palier d'un tour devient UN point (le milieu du palier, là où
#      est ce qui renvoie l'écho) ; d'un même objet vu de plusieurs stations, seul le point vu du plus près est gardé.
#      Un palier large tourné vers un axe de la pièce est un mur : sa ligne est retenue, avec le pied de la
#      perpendiculaire, seul endroit où le mur est sûr. Autour d'un pied franc (palier de 25° au moins) le mur est tenu
#      pour plein sur 2 m, autour d'un pied faible sur 50 cm, jamais au-delà d'une arête posée sur sa ligne ni d'un
#      endroit où une station a vu au travers.
#   3. Une station « regarde » le sol jusqu'à 1,8 m, là où son tour a vu au moins jusque-là et où aucun mur plein ne
#      s'interpose. Une nouvelle station n'est proposée que si elle promet au moins 0,6 m² de sol jamais regardé, au bout
#      d'un trajet de 50 à 90 cm dans une direction où le capteur voit loin (« vu ») ou ne voit rien que rien n'explique
#      (« inconnu », essayé en dernier). Un trajet ne s'approche pas d'un mur tenu pour plein.
#   4. Deux arêtes (ou deux pieds faibles) sur la même ligne de mur, à 60 à 130 cm l'une de l'autre, sans mur franc entre
#      elles : une porte possible. Le robot va se placer devant (station « porte »), d'où il voit au travers.
#   5. La prochaine station est choisie parmi TOUTES les stations déjà faites : sol à voir divisé par le temps pour y
#      aller ; le robot s'y rend par l'arbre des trajets déjà faits.
#   6. Un trajet arrêté (obstacle vu devant, pare-chocs) n'est pas perdu : si le robot a assez avancé, il fait son tour
#      là où il est. Le point de contact devient un obstacle.
#   7. Quand le robot repasse par une ancienne station après --recalage-m mètres, il y refait un tour : la comparaison
#      des deux tours (carto.apparier) donne son vrai décalage, et la position est corrigée.
#   8. Fin : plus rien à voir (après une seconde passe où les murs sont tenus pour pleins sur 1 m seulement), ou limite
#      de stations, de durée, d'échecs, de batterie ; retour à la station 0 par l'arbre et tour final, qui mesure la
#      dérive restante.
# Mis au point sans le robot dans simulateur.py (essai_explorer3.py) et rejoué sur les tours enregistrés
# (data_analysis/j_rejeu_exploration.py) ; journal_wifi.md § 26.
#
# Sécurités : celles de pilote.py (contrôles avant et pendant chaque saut de 1,4 s au plus) et celles du firmware (arrêt
# 1,5 s après le dernier ordre, arrêt sur pare-chocs, arrêt automatique du capteur de distance). Sortie du mode Safe,
# roue levée, vide sous un capteur ou journal muet : arrêt net, le robot reste où il est. Code infrarouge 161 (champ de
# la base) : le trajet s'arrête et l'endroit devient zone interdite.
#
# Avec le plan de l'appartement (--plan IMAGE --px-par-m N --depart-plan U,V,CAP ; voir plan.py) :
#   - le repère de la carte est celui du plan ; après chaque tour sur place la station est recalée sur le plan (position
#     et cap) : le cap ne glisse plus, la carte reste alignée, et les tours de recalage deviennent inutiles ;
#   - on peut diriger le robot : le fichier PREFIXE_CIBLES.json, {"serie": 1, "cibles": [[u, v], ...]} en pixels du plan,
#     lui fait rejoindre ces points l'un après l'autre par un chemin tracé dans le sol libre du plan (au milieu des
#     portes), avec un tour sur place tous les 90 cm au plus. Un nouveau numéro de série remplace les cibles en cours.
#     Sans cible, il explore de lui-même comme avant.
#
# Pour finir avant la fin : créer un fichier vide PREFIXE_RENTRE (le robot finit son étape et revient au départ) ou
# PREFIXE_ARRET (il s'arrête où il est, à la fin du saut en cours). Bouton CLEAN du robot : arrêt immédiat.
#
# Usage : python explorer3.py [--stations 40] [--minutes 45] [--vitesse 75] [--vide-min 150] [--interdit "x,y,rayon;..."]
#                             [--k-gyro 1.0015] [--recalage-m 12] [--sans-retour] -- ADRESSE PREFIXE
#         python explorer3.py --simulation appartement [--graine 1] -- sim PREFIXE      (essai sans robot, simulateur.py)
# Écrit PREFIXE_stations.json, lisible par h_carte_stations.py et i_recalage.py (« depart » y est la position tenue par
# le PC sans les recalages ; « pose » la position dans la carte, recalages compris).
import argparse
import json
import math
import os
import sys
import time
import urllib.error

import numpy as np

import carto
from pilote import Pilote

DX = carto.DX
RAYON = 170.0                      # mm, rayon du robot
V_CERVEAU = 135                    # mm/s demandés au plus quand le cerveau exécute lui-même l'avance (firmware v10) : à 150 les roues
                                   # sont à leur plafond (146 à 150 mm/s réels) et la tenue de cap ne peut plus que freiner une
                                   # roue (2026-11-13 : 3,5° d'écart en route à 150 demandés, 1 à 2° à 125 et 135 ; journal § 35)
PAS = (900.0, 700.0, 500.0)        # longueurs de trajet essayées, de la plus longue à la plus courte
GARDE = {"mur": 230.0, "arete": 230.0, "echo": 200.0, "contact": 260.0, "devant": 230.0, "sombre": 260.0}
ARRET_NET = ("Safe", "roue levée", "journal", "capteur de distance", "arrêt demandé")
CASE = 100.0                       # mm, pas de la grille des endroits déjà regardés
DEMI_GRILLE = 250                  # la grille couvre 25 m de part et d'autre du départ
PORTEE_VUE = 1800.0                # mm : une station « regarde » le sol jusqu'à cette distance
GAIN_MIN = 0.6                     # m² jamais regardés qu'une nouvelle station doit promettre
_k = int(PORTEE_VUE / CASE)
DISQUE_VUE = np.array([(i, j) for i in range(-_k, _k + 1) for j in range(-_k, _k + 1) if math.hypot(i, j) * CASE <= PORTEE_VUE], int)


def ecart(a):
    return (a + 180.0) % 360.0 - 180.0


class Estime:
    """Position tenue par le PC d'après le journal du cerveau. Repère : la position du robot à la première ligne lue."""

    def __init__(self, k):
        self.k = k
        self.i = None
        self.X = self.Y = self.C = 0.0       # dans la carte : cap × échelle du gyroscope, recalages compris
        self.bx = self.by = 0.0              # la même sans les recalages : sert d'« odométrie » à l'ajustement après coup
        self.chemin = 0.0                    # mm parcourus
        self.rot = 0.0                       # rotation nette comptée par le cerveau depuis le départ, degrés
        self.i0 = None                       # numéro de la première ligne du journal utilisée
        self.recalages = []                  # (numéro de ligne, dx, dy) : corrections de position déjà faites

    def suivre(self, lignes):
        if self.i is None:
            if lignes:
                self.i = self.i0 = len(lignes) - 1
            return
        while self.i + 1 < len(lignes):
            a, b = lignes[self.i], lignes[self.i + 1]
            dx, dy, dc = b["x_mm"] - a["x_mm"], b["y_mm"] - a["y_mm"], b["cap_pos"] - a["cap_pos"]
            if abs(dx) > 500 or abs(dy) > 500 or abs(dc) > 300 or b["ms"] < a["ms"] - 1000:
                raise RuntimeError("journal : la position du cerveau a sauté (cerveau redémarré ou position remise à zéro)")
            e = math.radians(self.C - a["cap_pos"])              # ce qu'il faut ajouter au cap du cerveau
            ex, ey = math.cos(e) * dx - math.sin(e) * dy, math.sin(e) * dx + math.cos(e) * dy
            self.X += ex
            self.Y += ey
            self.bx += ex
            self.by += ey
            self.C += self.k * dc
            self.rot += dc
            self.chemin += math.hypot(dx, dy)
            self.i += 1

    def decaler(self, ex, ey):
        """recalage : la position tenue par le PC est déplacée de (ex, ey) à partir de maintenant"""
        self.X += ex
        self.Y += ey
        self.recalages.append((self.i, ex, ey))

    def recalculer(self, lignes, k):
        """Refait tout le trajet depuis la première ligne avec l'échelle k du gyroscope, recalages compris. Renvoie la
        position à chaque ligne (X, Y, C), puis la même sans les recalages (Xb, Yb), à lire avec le numéro de ligne moins i0."""
        seg = lignes[self.i0:self.i + 1]
        x = np.array([l["x_mm"] for l in seg], float)
        y = np.array([l["y_mm"] for l in seg], float)
        c = np.array([l["cap_pos"] for l in seg], float)
        C = k * (c - c[0])
        e = np.radians(C[:-1] - c[:-1])
        dx, dy = np.diff(x), np.diff(y)
        X = np.r_[0.0, np.cumsum(np.cos(e) * dx - np.sin(e) * dy)]
        Y = np.r_[0.0, np.cumsum(np.sin(e) * dx + np.cos(e) * dy)]
        self.bx, self.by = float(X[-1]), float(Y[-1])
        Xb, Yb = X.copy(), Y.copy()
        for i, ex, ey in self.recalages:
            X[i - self.i0:] += ex
            Y[i - self.i0:] += ey
        self.k, self.X, self.Y, self.C = k, float(X[-1]), float(Y[-1]), float(C[-1])
        return X, Y, C, Xb, Yb


class Station:
    def __init__(self, nom, pose, d, r, parent, genre, ligne=0):
        self.nom, self.parent, self.genre, self.ligne = nom, parent, genre, ligne
        self.d, self.r = np.asarray(d, float), np.asarray(r, float)
        self.bloques = []                                         # directions qui ont échoué depuis cette station
        self.porte = None                                         # direction de la porte, pour une station « porte »
        self.tapis = False
        self.chemin = 0.0                                         # chemin parcouru par le robot quand il a fait cette station, mm
        self.pal = carto.paliers(self.d, self.r)                  # paliers stricts, pour comparer deux tours (carto.apparier)
        self.souples = carto.paliers_souples(self.d, self.r)      # paliers tolérants, pour décider ce qui est un mur
        self.murs_vus, self.aretes = [], []                       # remplis par Exploration.refaire_les_murs (il faut les axes)
        self.reposer(pose)

    def reposer(self, pose):
        """place la station (x, y, cap) dans la carte : tout ce qui dépend de sa position est refait"""
        self.pose = tuple(float(v) for v in pose)
        self.x, self.y = self.pose[0], self.pose[1]
        self.th = self.pose[2] + self.d                           # direction de chaque mesure, dans la carte (degrés)
        # un point par palier (là où est ce qui renvoie l'écho), un point par groupe de mesures voisines, un par écho isolé
        self.paliers, self.echos, self.petits = [], [], []
        pris = np.zeros(len(self.d), bool)
        for mid, dist, larg, nb in self.souples:
            pris |= (np.abs(ecart(self.d - mid)) <= larg / 2 + 0.01) & (np.abs(self.r + DX - dist) <= max(35.0, 0.015 * dist)) & (self.r > 0)
            a = math.radians(self.pose[2] + mid)
            self.paliers.append((self.pose[2] + mid, dist, larg, nb, (self.x + dist * math.cos(a), self.y + dist * math.sin(a))))
        reste = [int(k) for k in np.where((self.r > 0) & ~pris & (self.d < 360.0))[0]]
        while reste:                                              # deux ou trois mesures voisines à la même distance : une arête vue de loin
            g = [reste.pop(0)]
            while reste and reste[0] == g[-1] + 1 and abs(self.r[reste[0]] - self.r[g[-1]]) <= 30:
                g.append(reste.pop(0))
            a = math.radians(float(np.mean(self.th[g])))
            pt = (self.x + (float(np.median(self.r[g])) + DX) * math.cos(a), self.y + (float(np.median(self.r[g])) + DX) * math.sin(a))
            (self.petits if len(g) >= 2 else self.echos).append(pt)
        # distance lue dans chaque direction de la carte, degré par degré (0 = rien à portée)
        m = self.d < 360.0
        ang, rr = self.th[m] % 360.0, self.r[m]
        o = np.argsort(ang)
        ang, rr = ang[o], rr[o]
        deg = np.arange(360) + 0.5
        i1 = np.searchsorted(ang, deg) % len(ang)
        i0 = (i1 - 1) % len(ang)
        k = np.where(np.abs(ecart(ang[i1] - deg)) < np.abs(ecart(ang[i0] - deg)), i1, i0)
        self.profil = np.where(rr[k] > 0, rr[k] + DX, 0.0)

    def vue(self, phi, demi=6.0):
        """ce que le tour a vu dans la direction phi : (classe, distance libre). « vu » : la plupart des mesures ont un
        écho, la distance libre est le plus court ; « inconnu » : presque aucune mesure n'a d'écho."""
        m = (np.abs(ecart(self.th - phi)) <= demi) & (self.d < 360.0)
        r = self.r[m]
        if len(r) < 2:
            return None, 0.0
        nz = r[r > 0] + DX
        if len(nz) >= 0.6 * len(r):
            return "vu", float(nz.min())
        return "inconnu", (float(nz.min()) if len(nz) else 1e9)


class Mur:
    """Une ligne de mur : n·X = rho, n étant la direction dans laquelle les stations la voient. Le mur n'est sûr qu'aux
    pieds des perpendiculaires ; on le suppose plein de part et d'autre de chaque pied jusqu'à 2 m, sauf au-delà d'une
    arête posée sur sa ligne (bord d'ouverture, fin du mur) ou d'un endroit où une station a vu au travers."""

    def __init__(self, phi, rho):
        self.phi, self.rho = phi, rho
        self.pieds, self.aretes, self.ouverts = [], [], []        # abscisses le long du mur
        self.forts = []                                           # pour chaque pied : palier franc (25° au moins) ?
        self.vus = []                                             # les paliers qui ont donné ces pieds
        self.n = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
        self.t = (-self.n[1], self.n[0])
        self.pleins = []                                          # intervalles (début, fin) où le mur est tenu pour plein

    def absc(self, x, y):
        return self.t[0] * x + self.t[1] * y

    def cote(self, x, y):
        """distance signée à la ligne : négative du côté d'où le mur a été vu"""
        return self.n[0] * x + self.n[1] * y - self.rho

    def calculer_pleins(self, franc=600.0, faible=250.0):
        """Un pied franc (palier de 25° au moins) vaut pour 2 m de mur de chaque côté ; un pied faible pour 50 cm
        seulement, car une arête vue de face (le montant d'une porte) ressemble à un bout de mur. En seconde passe
        (quand il ne reste plus rien à voir), l'exploration réduit ces portées : 1 m et 25 cm."""
        iv = []
        for f, fort in zip(self.pieds, self.forts):
            portee = franc if fort else faible
            lo, hi = f - portee, f + portee
            for q in self.aretes:
                if q < f - 150:
                    lo = max(lo, q)
                elif q > f + 150:
                    hi = min(hi, q)
            for q in self.ouverts:
                if q < f:
                    lo = max(lo, min(f - 150, q + 250))
                else:
                    hi = min(hi, max(f + 150, q - 250))
            iv.append((lo, hi))
        iv.sort()
        self.pleins = []
        for lo, hi in iv:
            if self.pleins and lo <= self.pleins[-1][1]:
                self.pleins[-1] = (self.pleins[-1][0], max(hi, self.pleins[-1][1]))
            else:
                self.pleins.append((lo, hi))

    def plein(self, q):
        return any(lo <= q <= hi for lo, hi in self.pleins)


class Exploration:
    def __init__(self, p, a):
        self.p, self.a = p, a
        self.dormir = getattr(p, "dormir", time.sleep)
        self.maintenant = getattr(p, "maintenant", time.time)
        self.est = Estime(a.k_gyro)
        self.v_reelle = min(a.vitesse + 21.0, 147.0)           # mesuré le 2026-11-10 : réglage + 21 mm/s, 147 au plus
        self.v_reglee = a.vitesse
        self.filtre, self.i_filtre = None, 0                   # localisation à plusieurs hypothèses (localiser.py), avec le plan
        self.rot_dps = 2 * self.v_reelle / 235.0 * 57.29578
        self.stations = []                                     # toutes, dans l'ordre (les tours de recalage aussi)
        self.noeuds = []                                       # stations de l'arbre (pas les tours de recalage)
        self.murs, self.axe = [], None
        self.contacts = []                                     # (x, y, genre)
        self.interdits = [tuple(float(v) for v in z.split(",")) for z in a.interdit.split(";") if z.strip()]
        self.portes = []                                       # portes repérées : dictionnaires
        self.echecs = 0
        self.dernier_recalage = 0.0                            # chemin parcouru au dernier essai de recalage, mm
        self.dernier_fix = 0.0                                 # chemin parcouru au dernier recalage accepté, mm
        self.cap_mes = []                                      # mesures de cap par les murs : (rotation nette, erreur du cap brut, poids)
        # Longueur de mur tenue pour pleine autour d'un pied franc, d'un pied faible. En simulation 2 m et 50 cm allaient
        # bien ; dans le vrai appartement (2026-11-10, 18 h 18) quatorze lignes de murs et de meubles ainsi prolongées se
        # croisaient dans le couloir, et le programme a conclu qu'il n'y avait plus rien à voir après dix stations.
        self.portees = (600.0, 250.0)
        self.pannes = 0                                        # requêtes au cerveau restées sans réponse
        self.plan = None                                       # le plan de l'appartement, s'il est donné (plan.py)
        self.cibles, self.serie = [], None                     # points du plan à rejoindre, donnés de l'extérieur
        if getattr(a, "plan", ""):
            import plan as plan_mod
            self.plan = plan_mod.Plan(a.plan, a.px_par_m)
            if getattr(a, "plan_passe", ""):                     # image du plan où l'utilisateur a tracé en vert par où on passe
                from PIL import Image
                Z = np.asarray(Image.open(a.plan_passe).convert("RGB")).astype(int)
                self.plan.passe_main |= (Z[..., 1] > Z[..., 0] + 40) & (Z[..., 1] > Z[..., 2] + 40)
            for f_ in getattr(a, "plan_roule", "").split(";"):   # trajets déjà roulés (fichiers de l_localisation_globale.py) : sol sûr
                if f_.strip():
                    with open(f_, encoding="utf-8") as fh:
                        roule = json.load(fh).get("trajet", [])
                    self.plan.ouvrir([(p[0], p[1]) for p in roule], rayon_mm=150.0)
        self.t0 = self.maintenant()
        self.j = {"mode": "exploration3", "k_gyro": a.k_gyro, "pas": list(PAS), "vitesse": a.vitesse, "vide_min": a.vide_min,
                  "interdits": self.interdits, "stations": [], "sauts": [], "choix": [], "echecs": [], "contacts": [],
                  "recalages": [], "caps": [], "portes": [], "parents": {}, "fin": None}

    # ------------------------------------------------------------ le plan de l'appartement
    def vers_px(self, x, y):
        return x * self.plan.s, self.plan.H - y * self.plan.s

    def vers_mm(self, u, v):
        return u / self.plan.s, (self.plan.H - v) / self.plan.s

    def caler_sur_le_plan(self, st, premier=False):
        """Recale la station qui vient d'être faite sur le plan ; corrige la position et le cap tenus par le PC."""
        u, v = self.vers_px(st.x, st.y)
        pal = [(psi - st.pose[2], dist, larg) for psi, dist, larg, nb, pt in st.paliers]
        R = int(round((600.0 if premier else 300.0) * self.plan.s))
        u1, v1, c1, note, note0 = self.plan.localiser(pal, u, v, st.pose[2], R=R, d_cap=(25.0 if premier else 10.0), retenue=(0.05 if premier else 0.25))
        x1, y1 = self.vers_mm(u1, v1)
        dx, dy, dc = x1 - st.x, y1 - st.y, c1 - st.pose[2]
        info = {"station": st.nom, "note_avant": round(note0, 2), "note": round(note, 2), "dx": round(dx), "dy": round(dy), "dcap": round(dc, 1), "garde": False}
        if note >= 0.45 and len(pal) >= 3:
            self.est.decaler(dx, dy)
            self.est.C += dc
            st.reposer((x1, y1, c1))
            self.j["stations"][-1]["pose"] = [round(x1, 1), round(y1, 1), round(c1, 2)]
            info["garde"] = True
            # ce que le robot voit l'emporte sur le trait tracé à la main : un mur du plan vu d'ici referme le passage
            info["murs_confirmes"] = sum(self.plan.confirmer(*self.vers_px(x1 + (dist + DX) * math.cos(math.radians(c1 + ang)),
                                                                           y1 + (dist + DX) * math.sin(math.radians(c1 + ang))))
                                         for ang, dist, larg in pal)
        self.j.setdefault("plan", []).append(info)
        self.dire(f"    sur le plan : {'recalée de' if info['garde'] else 'pas recalée (note trop basse) ; écart proposé'} ({dx:+.0f}, {dy:+.0f}) mm et {dc:+.1f}° ; note {note0:.2f} -> {note:.2f}")

    def caler_par_le_filtre(self, st):
        """Le tour qui vient de finir juge les hypothèses du filtre ; la position et le cap tenus par le PC sont remplacés
        par ceux du filtre. Rejoué sur la soirée du 2026-11-10 : 6 cm et 2° d'erreur médiane, contre 17 cm et 9° pour
        caler_sur_le_plan (une seule hypothèse, fenêtre de 30 cm et 10°)."""
        e = self.filtre.tour(st.d, st.r)
        dx, dy, dc = e["x"] - self.est.X, e["y"] - self.est.Y, ecart(e["cap"] - self.est.C)
        self.est.decaler(dx, dy)
        self.est.C += dc
        c1 = st.pose[2] + ecart(e["cap_debut"] - st.pose[2])
        st.reposer((e["x"], e["y"], c1))
        self.j["stations"][-1]["pose"] = [round(e["x"], 1), round(e["y"], 1), round(c1, 2)]
        info = {"station": st.nom, "filtre": True, "note": round(e["note"], 2), "dx": round(dx), "dy": round(dy), "dcap": round(dc, 1),
                "etalement_mm": round(e["etalement_mm"]), "etalement_cap": round(e["etalement_cap"], 1), "echelle_gyro": round(e["echelle_gyro"], 4), "garde": True}
        info["murs_confirmes"] = sum(self.plan.confirmer(*self.vers_px(pt[0], pt[1])) for psi, dist, larg, nb, pt in st.paliers)
        self.j.setdefault("plan", []).append(info)
        self.dire(f"    filtre : position corrigée de ({dx:+.0f}, {dy:+.0f}) mm et {dc:+.1f}° ; note {e['note']:.2f}, étalement {e['etalement_mm']:.0f} mm"
                  f" et {e['etalement_cap']:.1f}°, gyroscope × {e['echelle_gyro']:.4f}")

    def lire_cibles(self):
        try:
            with open(self.a.prefixe + "_CIBLES.json", encoding="utf-8") as f:
                J = json.load(f)
        except (OSError, ValueError):
            return
        if J.get("serie") != self.serie:
            self.serie = J.get("serie")
            self.cibles = [tuple(float(v) for v in c[:2]) for c in J.get("cibles", [])]
            self.dire(f"cibles reçues (série {self.serie}) : {[(round(u), round(v)) for u, v in self.cibles]}")

    def vers_cible(self, ici):
        """Rejoint la première cible par un chemin tracé sur le plan. Renvoie la station où est le robot, ou None après
        un arrêt net. La cible est retirée de la liste, atteinte ou non."""
        cible = self.cibles[0]
        dernier_tour = (ici.x, ici.y)
        essai, attentes = 0, 0
        while essai < 3:
            essai += 1
            l, q = self.pose()
            if l is None:
                return None
            ch = self.plan.chemin(self.vers_px(q[0], q[1]), cible)
            if ch is None:
                self.dire(f"  cible ({cible[0]:.0f}, {cible[1]:.0f}) : pas de chemin dans le sol libre du plan depuis ici, cible laissée")
                self.cibles.pop(0)
                return ici
            jalons = self.plan.jalons(ch, 900.0)[1:]
            self.dire(f"  vers la cible ({cible[0]:.0f}, {cible[1]:.0f}) du plan : {len(jalons)} étapes" + (f" (essai {essai}, en contournant l'obstacle)" if essai > 1 else ""))
            arrive = True
            for ju, jv in jalons:
                serie = self.serie
                self.lire_cibles()
                if self.serie != serie or self.demande():
                    return ici                                   # nouvelles consignes : on s'arrête à cette station
                x, y = self.vers_mm(ju, jv)
                if math.hypot(x - ici.x, y - ici.y) < 250:
                    continue
                phi = math.degrees(math.atan2(y - ici.y, x - ici.x)) % 360.0
                # En conduite d'un seul tenant, un point de passage est tenu pour atteint à 10 cm près (6 cm pour le dernier) :
                # le 2026-11-13, avec 3 cm exigés, le robot faisait un quart de tour et quelques centimètres à chaque point
                # (29 rotations pour 7,5 m, 36 % du temps à tourner). L'étape suivante part de là où il est vraiment.
                if getattr(self.a, "fluide", False):
                    tol = 60.0 if (ju, jv) == tuple(jalons[-1]) else 100.0
                else:
                    tol = 30.0
                ok, raison = self.aller_a(x, y, tolerance=tol, connu=True)      # chemin tracé sur le plan : 40 cm libres devant suffisent
                if not ok:
                    l, q = self.pose()
                    if l is not None:                             # l'obstacle rencontré est porté sur le plan : le prochain chemin le contourne
                        ca, sa = math.cos(math.radians(q[2])), math.sin(math.radians(q[2]))
                        d_obs = (l["us_mm"] + DX) if ("obstacle à" in str(raison) and l["us_mm"] > 0) else 220.0
                        ou, ov = self.vers_px(q[0] + d_obs * ca, q[1] + d_obs * sa)
                        deja_roule = (0 <= int(round(ov)) < self.plan.H and 0 <= int(round(ou)) < self.plan.W
                                      and bool(self.plan.passe[int(round(ov)), int(round(ou))]))
                        if deja_roule and attentes < 2:
                            # quelque chose sur un sol où le robot est déjà passé (un chat, une personne, le 2026-11-10 dans
                            # le couloir) : on attend et on réessaie, sans le noter sur le plan ni chercher un détour
                            attentes += 1
                            essai -= 1
                            if "pare-chocs" in str(raison):
                                # un contact : on ne reste pas appuyé contre ce qu'on a touché (8,8 s le 2026-11-13 en D14) ;
                                # le recul et le tour sur place d'apres_echec, juste après, laissent le temps de s'écarter
                                self.dire(f"    contact sur un passage déjà roulé ({raison}) : recul tout de suite, puis nouvel essai")
                            else:
                                self.dire(f"    quelque chose sur un passage déjà roulé ({raison}) : attente de 8 s, puis nouvel essai")
                                self.dormir(8.0)
                        else:
                            self.plan.fermer(ou, ov)
                    ici, compte = self.apres_echec(ici, {"phi": phi, "genre": "cible"}, raison)
                    if ici is None:
                        return None
                    self.echecs += 1 if compte else 0
                    dernier_tour = (ici.x, ici.y)
                    arrive = False
                    break
                l, q = self.pose()
                if l is None:
                    return None
                dernier_jalon = (ju, jv) == tuple(jalons[-1])
                court = math.hypot(q[0] - dernier_tour[0], q[1] - dernier_tour[1]) < getattr(self.a, "tour_tous_les", 600.0)
                if court and (not dernier_jalon or (len(self.cibles) > 1 and getattr(self.a, "enchainer", False))):
                    continue                                     # étape courte, ou destination de passage : pas de tour ici, on enchaîne
                st, raison = self.faire_un_tour(str(len(self.noeuds)), ici, "station")
                if st is None:
                    self.dire(f"  tour impossible : {raison}")
                    return None
                self.dire(f"station {st.nom} (vers une cible) en ({st.x:.0f}, {st.y:.0f}) : {len(st.pal)} paliers" + (", sur un tapis" if st.tapis else ""))
                ici = st
                dernier_tour = (st.x, st.y)
                self.sauver()
            if arrive:
                self.dire(f"  cible ({cible[0]:.0f}, {cible[1]:.0f}) atteinte")
                self.cibles.pop(0)
                return ici
        self.dire(f"  cible ({cible[0]:.0f}, {cible[1]:.0f}) laissée après trois essais")
        self.cibles.pop(0)
        return ici

    # ------------------------------------------------------------ petits outils
    def dire(self, *x):
        print(f"[{(self.maintenant() - self.t0) / 60:5.1f} min]", *x, flush=True)

    def sauver(self):
        self.j["contacts"] = [[round(c[0]), round(c[1]), c[2]] for c in self.contacts]
        self.j["portes"] = [{k: (v if not isinstance(v, tuple) else [round(q) for q in v]) for k, v in d.items() if k != "depuis"} for d in self.portes]
        with open(self.a.prefixe + "_stations.json", "w", encoding="utf-8") as f:
            json.dump(self.j, f, ensure_ascii=False)

    def demande(self):
        """Fin demandée de l'extérieur, par un fichier vide : PREFIXE_RENTRE (finir l'étape en cours puis revenir au
        départ) ou PREFIXE_ARRET (s'arrêter sur place à la fin du saut en cours, sans revenir)."""
        if os.path.exists(self.a.prefixe + "_ARRET"):
            return "arrêt"
        if os.path.exists(self.a.prefixe + "_RENTRE"):
            return "retour"
        return None

    def pose(self):
        """ligne fraîche du journal et position dans la carte ; (None, None) si le journal est muet plus de 12 s"""
        for _ in range(4):
            l = self.p.frais()
            if l is not None:
                break
        if l is None:
            return None, None
        self.est.suivre(self.p.lignes)
        if self.filtre is not None:                             # les hypothèses avancent avec les mêmes lignes
            self.filtre.suivre(self.p.lignes[self.i_filtre:])
            self.i_filtre = len(self.p.lignes)
        return l, (self.est.X, self.est.Y, self.est.C)

    def lire(self, chemin):
        """requête au cerveau, reprise deux fois si la liaison flanche (lectures et demandes sans danger à répéter)"""
        for essai in range(3):
            try:
                return self.p.get(chemin)
            except (OSError, urllib.error.URLError) as err:
                self.pannes += 1
                self.dire(f"  liaison : « {chemin} » sans réponse ({err}), essai {essai + 1}")
                self.dormir(1.0)
        raise RuntimeError("liaison : le cerveau ne répond plus")

    def saut(self, touche, duree, **k):
        """Pilote.saut ; si la liaison flanche pendant le saut, le firmware arrête les roues de lui-même 1,5 s après le
        dernier ordre : on attend, on redemande l'arrêt, et le trajet reprend d'après la position lue dans le journal."""
        try:
            return self.p.saut(touche, duree, **k)
        except (OSError, urllib.error.URLError) as err:
            self.pannes += 1
            self.dire(f"  liaison : saut « {touche} » interrompu ({err})")
            if self.pannes > 12:
                raise RuntimeError("liaison : trop d'ordres perdus")
            self.dormir(2.0)
            try:
                self.p.touche("5")
            except (OSError, urllib.error.URLError):
                pass
            self.p.immobile()
            return {"touche": touche, "liaison": str(err), "alarme": None}

    def regler_vitesse(self, v):
        """vitesse des roues pour l'ordre qui suit ; ne redemande rien au cerveau si elle n'a pas changé"""
        v = int(max(50, min(150, v)))
        if v != self.v_reglee:
            self.p.vitesse(v)
            self.v_reglee = v
            self.dormir(0.05)
        self.v_reelle = min(v + 21.0, 147.0)
        self.rot_dps = 2 * self.v_reelle / 235.0 * 57.29578

    def tourner(self, angle):
        """Pilote.tourne, avec la même reprise que saut() si la liaison flanche"""
        try:
            return self.p.tourne(angle, vide_min=self.a.vide_min, vide_stop=self.a.vide_min)
        except (OSError, urllib.error.URLError) as err:
            self.pannes += 1
            self.dire(f"  liaison : rotation interrompue ({err})")
            if self.pannes > 12:
                raise RuntimeError("liaison : trop d'ordres perdus")
            self.dormir(2.0)
            try:
                self.p.touche("5")
            except (OSError, urllib.error.URLError):
                pass
            self.p.immobile()
            return {"touche": "4", "liaison": str(err), "alarme": None}

    def avancer(self, dist, **k):
        """Pilote.avance, avec la même reprise que saut() si la liaison flanche"""
        try:
            return self.p.avance(dist, **k)
        except (OSError, urllib.error.URLError) as err:
            self.pannes += 1
            self.dire(f"  liaison : avance interrompue ({err})")
            if self.pannes > 12:
                raise RuntimeError("liaison : trop d'ordres perdus")
            self.dormir(2.0)
            try:
                self.p.touche("5")
            except (OSError, urllib.error.URLError):
                pass
            self.p.immobile()
            return {"touche": "8", "liaison": str(err), "alarme": None}

    # ------------------------------------------------------------ mouvements
    def tourner_vers(self, cap_cible, tol=4.0, essais=8):
        self.regler_vitesse(min(self.a.vitesse, 75))            # les rotations restent lentes : à 150 mm/s un saut de 0,1 s fait déjà 7°
        for _ in range(essais):
            l, q = self.pose()
            if l is None:
                return False, "plus de lignes du journal"
            err = cap_cible - q[2]
            if abs(err) <= tol:
                return True, None
            if getattr(self.a, "fluide", False) and (abs(err) > 12.0 or self.p.sait_mouv()):   # d'un seul tenant ; sans le firmware v10, les petites retouches restent des sauts courts
                r = self.tourner(err)
            else:
                r = self.saut("4" if err > 0 else "6", min(1.3, max(0.10, abs(err) / self.rot_dps - 0.04)), lb_repos=5000, lb_max=5000,
                              vide_min=self.a.vide_min, vide_stop=self.a.vide_min)
            r["but"] = f"rotation de {err:+.1f}°"
            self.j["sauts"].append(r)
            if "refus" in r:
                return False, "rotation refusée : " + r["refus"]
            if r.get("alarme"):
                return False, "alarme pendant une rotation : " + r["alarme"]
            self.dormir(0.3)
        l, q = self.pose()
        return (l is not None and abs(cap_cible - q[2]) <= tol + 2), "cap non atteint"

    def aller_a(self, xt, yt, tolerance=30.0, connu=False):
        """Va au point (xt, yt) de la carte par sauts. Renvoie (réussi, raison). connu : trajet déjà fait (retour par
        l'arbre) ; le capteur de distance n'y exige que 40 cm libres devant, au lieu de 60."""
        for _ in range(30):
            if self.demande() == "arrêt":
                return False, "arrêt demandé (fichier _ARRET)"
            l, q = self.pose()
            if l is None:
                return False, "plus de lignes du journal"
            dx, dy = xt - q[0], yt - q[1]
            d = math.hypot(dx, dy)
            if d <= tolerance:
                return True, None
            fluide = getattr(self.a, "fluide", False)
            d_trait = min(d - 8.0, 1500.0)
            # Le robot tire d'un côté en roulant (2 à 13° par mètre le 2026-11-13) : en conduite d'un seul tenant on vise
            # de l'autre côté, de la moitié de ce qu'il va tourner, pour que l'arc finisse sur le point au lieu de
            # s'arrêter tous les 40 cm pour se redresser. La dérive est mesurée sur les avances précédentes.
            derive = getattr(self, "derive", 0.0) if (fluide and not getattr(self.a, "sans_visee", False)) else 0.0
            # Firmware v10 : le cerveau tient le cap lui-même et sait le changer en roulant. Plus de visée à côté, et le
            # robot ne s'arrête pour pivoter que si le point est à plus de 15° de son axe. Avec 35° (jusqu'au 2026-11-13),
            # un virage de 22° pris en roulant a décalé le robot de 6 à 9 cm dans la porte H12 : contact avec un montant
            # (journal_wifi.md § 36) ; et l'arrivée à côté du point demandait ensuite une rotation de plus (§ 35).
            cerveau = fluide and self.p.sait_mouv()
            if cerveau:
                derive = 0.0
            a_cote = max(-4.0, min(4.0, 0.5 * derive * max(0.0, d_trait)))      # 4° au plus : le capteur de distance doit continuer de regarder le chemin
            err = ecart(math.degrees(math.atan2(dy, dx)) - a_cote - q[2])
            if abs(err) > ((15.0 if d > 250 else 12.0) if cerveau else (4.0 if d > 120 else 8.0)):
                ok, raison = self.tourner_vers(q[2] + err)
                if not ok:
                    return False, raison
                continue
            i0 = len(self.p.lignes)
            self.regler_vitesse(min(self.a.vitesse, V_CERVEAU) if cerveau else self.a.vitesse)
            if getattr(self.a, "fluide", False):                # d'un seul tenant jusqu'au point, ou jusqu'à ce que le cap ait tourné de 5°
                r = self.avancer(d_trait, marge_mm=400.0 if connu else 600.0, cap_tol=max(5.0, abs(derive) * d_trait + 4.0),
                                 vide_min=self.a.vide_min, vide_stop=self.a.vide_min, cap_rel=(err if cerveau else 0.0))
                if r.get("avance_mm", 0.0) >= 300.0 and "rot_gyro" in r:
                    self.derive = max(-0.012, min(0.012, 0.7 * derive + 0.3 * r["rot_gyro"] / r["avance_mm"]))
            else:
                r = self.saut("8", min(1.3, max(0.2, (d - 8) / (self.v_reelle + 6))), marge_mm=min(400.0 if connu else 600.0, d + 220.0),
                              vide_min=self.a.vide_min, vide_stop=self.a.vide_min)
            r["but"] = f"avance vers ({xt:.0f}, {yt:.0f}), reste {d:.0f} mm"
            self.j["sauts"].append(r)
            if "refus" in r:
                return False, "avance refusée : " + r["refus"]
            if r.get("alarme"):
                return False, "alarme pendant une avance : " + r["alarme"]
            if any(int(m.get("ir_dessus", 0)) == 161 for m in self.p.lignes[i0:]) and self.vers_la_base():
                return False, "base proche (champ infrarouge 161)"
            self.dormir(0.05 if getattr(self.a, "fluide", False) else 0.3)
        return False, "trop de sauts"

    def vers_la_base(self):
        """Le robot roule-t-il vers sa base ? Sans base donnée sur le plan (--base-plan), on répond oui par prudence : le
        champ infrarouge 161 arrête alors toute avance. Avec la base, un départ depuis la base reste possible."""
        b = getattr(self.a, "base_plan", "")
        if not b or self.plan is None:
            return True
        bu, bv = (float(v) for v in b.split(","))
        bx, by = self.vers_mm(bu, bv)
        c = math.radians(self.est.C)
        return (bx - self.est.X) * math.cos(c) + (by - self.est.Y) * math.sin(c) > 0.0

    def faire_un_tour(self, nom, parent, genre):
        """Tour sur place du firmware. Renvoie (station, raison) ; station vaut None en cas d'échec."""
        l0, q0 = self.pose()
        if l0 is None:
            return None, "plus de lignes du journal"
        if self.filtre is not None:
            self.filtre.debut_tour()
        brut0 = (self.est.bx, self.est.by, self.est.C)
        rot0, ligne0 = self.est.rot, self.est.i
        a_k0 = self.a.k_gyro
        # Le zéro du gyroscope glisse pendant que la carte chauffe (2026-11-10 : 10 ° par minute au repos une demi-heure
        # après l'allumage, puis une vingtaine de degrés perdus en dix minutes d'exploration). Le robot est immobile
        # avant chaque tour : on en profite pour refaire ce zéro (touche z, une seconde). La position ne saute pas.
        if not getattr(self.a, "sans_z", False):                 # le tour du firmware refait lui-même ce zéro à son départ (tour.ino)
            self.lire("/api/cmd?c=z")
            self.dormir(1.4)
        t = json.loads(self.lire(f"/api/tour?go=1&v={self.a.tour_v}"))
        if t.get("etat") not in (1, 2):
            return None, "tour refusé : " + str(t.get("raison", t.get("texte")))
        fin = self.maintenant() + 70
        while self.maintenant() < fin:
            self.dormir(0.5)
            t = json.loads(self.lire("/api/tour"))
            if t.get("etat") not in (1, 2):
                break
        self.p.immobile()
        l1, q1 = self.pose()
        if t.get("etat") != 3 or (t.get("n") or 0) < 50:
            return None, f"tour arrêté : {t.get('raison')}"
        m = np.array(t["points"], float)
        st = Station(nom, q0, m[:, 0] / 10.0, m[:, 1], parent, genre, ligne=ligne0)
        sol = [l0[k] for k in ("vide_g", "vide_avg", "vide_avd", "vide_d")]
        st.tapis = min(sol) < 2000
        st.chemin = self.est.chemin
        self.stations.append(st)
        self.j["stations"].append({
            "nom": nom, "genre": genre, "de": parent.nom if parent else None, "heure": time.strftime("%H:%M:%S"),
            "etat": t.get("texte"), "raison": t.get("raison"), "tourne": t.get("tourne"), "n": t.get("n"), "roues": t.get("roues"),
            "duree_ms": t.get("duree_ms"), "depart": [round(brut0[0], 1), round(brut0[1], 1), round(brut0[2], 2)],
            "pose": [round(q0[0], 1), round(q0[1], 1), round(q0[2], 2)], "depart_cerveau": t.get("depart"), "mesures": t.get("points"),
            "avant": {k: l0[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm", "vide_g", "vide_avg", "vide_avd", "vide_d")},
            "apres": {k: l1[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm")} if l1 else None, "tapis": bool(st.tapis)})
        if self.plan is not None:
            if self.filtre is not None:
                self.caler_par_le_filtre(st)
            else:
                self.caler_sur_le_plan(st, premier=not self.noeuds and not getattr(self.a, "depart_sur", False))
            if parent is not None and genre not in ("recalage", "retour"):
                self.plan.ouvrir([self.vers_px(parent.x, parent.y), self.vers_px(st.x, st.y)])      # le robot vient d'y passer : c'est libre
        if genre not in ("recalage", "retour"):
            self.noeuds.append(st)
            if parent is not None:
                self.j["parents"][nom] = parent.nom
            self.refaire_les_murs()
            # la mesure de cap par les murs ne vaut que si le robot est parti de la station précédente juste après son
            # tour : sinon l'endroit d'où il part n'est connu qu'à quelques centimètres près, et la mesure est faussée
            eps = self.boussole(st) if self.plan is None and len(self.stations) >= 2 and self.stations[-2] is parent else None
            if eps is not None and abs(rot0) >= 300:
                # Une mesure seule est bruitée (±1,5° en simulation) : on ne corrige pas le cap avec elle. Toutes les
                # mesures servent ensemble à ajuster l'échelle du gyroscope : l'erreur du cap brut est proportionnelle à
                # la rotation nette. L'échelle de départ compte comme une mesure de plus (± 0,0005) ; une mesure qui
                # s'écarte de plus de 3° des autres pèse moins.
                self.cap_mes.append((rot0, a_k0 * rot0 - q0[2] + eps[0]))
                note = {"station": nom, "ecart_deg": round(eps[0], 2), "murs": eps[1], "k_gyro": round(self.est.k, 5)}
                pente = 0.0
                for _ in range(4):
                    num = den = 0.0
                    for r, u in self.cap_mes:
                        w = min(1.0, 3.0 / max(1e-9, abs(u - pente * r)))
                        num += w * u * r
                        den += w * r * r
                    pente = num / ((2.0 / 0.0005) ** 2 + den)
                k_neuf = a_k0 - pente
                if abs(k_neuf - self.est.k) >= 0.00005:
                    self.pose()                                   # journal à jour avant de tout recalculer
                    X, Y, C, Xb, Yb = self.est.recalculer(self.p.lignes, k_neuf)
                    for s_, js in zip(self.stations, self.j["stations"]):     # toute la carte suit la nouvelle échelle
                        i = s_.ligne - self.est.i0
                        s_.reposer((X[i], Y[i], C[i]))
                        js["pose"] = [round(X[i], 1), round(Y[i], 1), round(C[i], 2)]
                        js["depart"] = [round(Xb[i], 1), round(Yb[i], 1), round(C[i], 2)]
                    note.update({"k_gyro": round(k_neuf, 5), "cap_corrige_deg": round(st.pose[2] - q0[2], 2)})
                    self.refaire_les_murs()
                self.j["caps"].append(note)
        return st, None

    def boussole(self, st):
        """Erreur de cap du PC d'après les murs, entre la station d'où le robot vient et celle-ci : si le robot a longé
        un mur vu des deux stations, la distance à ce mur n'a dû changer que de ce que dit le trajet ; l'écart, divisé
        par la distance parcourue le long du mur, est l'erreur de cap (10 mm sur 0,9 m : 0,6°). Renvoie (degrés, nombre
        de murs) ou None."""
        A = st.parent
        if A is None:
            return None
        dx, dy = st.x - A.x, st.y - A.y
        mes = []
        for m in self.murs:
            va = [v for v in m.vus if v["s"] is A]
            vb = [v for v in m.vus if v["s"] is st]
            le_long = m.t[0] * dx + m.t[1] * dy
            if not va or not vb or abs(le_long) < 350:
                continue
            ecart_mm = vb[0]["vu"][1] - va[0]["vu"][1] + (m.n[0] * dx + m.n[1] * dy)
            if abs(ecart_mm) <= 60:
                mes.append((-math.degrees(ecart_mm / le_long), abs(le_long) * (2.0 if va[0]["fort"] and vb[0]["fort"] else 1.0)))
        if not mes:
            return None
        return float(np.average([e for e, w in mes], weights=[w for e, w in mes])), len(mes)

    # ------------------------------------------------------------ ce que la carte sait
    def refaire_les_murs(self):
        """lignes de murs à partir des paliers larges tournés vers un axe de la pièce ; arêtes, endroits ouverts, portes"""
        th, w = [], []
        for s in self.noeuds:
            for psi, dist, larg, nb, pt in s.paliers:
                if larg >= 15.0 and nb >= 5:
                    th.append(psi)
                    w.append(larg / (dist / 1000.0) ** 1.5)       # un mur est plus proche que les coins qui le bordent
        if th and (self.axe is None or len(self.noeuds) <= 3):   # ensuite les axes sont gardés : ils servent de référence au cap
            th, w = np.array(th), np.array(w)
            phis = np.arange(0, 90, 0.5)
            self.axe = float(phis[int(np.argmax([np.sum(w * np.exp(-0.5 * ((((th - q + 45) % 90) - 45) / 8.0) ** 2)) for q in phis]))])
        self.murs = []
        for s in self.noeuds:
            s.murs_vus, s.aretes, s.sur_mur = [], list(s.petits), []
            for psi, dist, larg, nb, pt in s.paliers:
                e = (((psi - self.axe + 45.0) % 90.0) - 45.0) if self.axe is not None else 99.0
                if not (larg >= 15.0 and nb >= 5 and abs(e) <= 16.0):
                    s.aretes.append(pt)                           # palier étroit ou de travers : un objet, une arête
                    continue
                phi = (psi - e) % 360.0
                n = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
                rho = n[0] * s.x + n[1] * s.y + dist
                mur = next((m for m in self.murs if abs(ecart(m.phi - phi)) < 20 and abs(m.rho - rho) <= 100), None)
                if mur is None:
                    mur = Mur(phi, rho)
                    self.murs.append(mur)
                pied = (s.x + dist * n[0], s.y + dist * n[1])
                mur.vus.append({"q": mur.absc(*pied), "fort": larg >= 25.0, "s": s, "pt": pt, "vu": (phi, dist, pied)})
        # une station qui regarde un mur de face et voit plus loin que lui, ou rien : le mur est ouvert devant elle
        for m in self.murs:
            qs = [v["q"] for v in m.vus]
            for s in self.noeuds:
                c = m.cote(s.x, s.y)
                q = m.absc(s.x, s.y)
                if c > -150 or -c > 3500 or not (min(qs) - 2500 < q < max(qs) + 2500):
                    continue
                face = (np.abs(ecart(s.th - m.phi)) <= 8.0) & (s.d < 360.0)
                if int(((s.r[face] == 0) | (s.r[face] + DX >= -c + 300)).sum()) >= 3:
                    m.ouverts.append(q)
            # un pied faible là où le mur est ouvert : c'était le montant d'une porte vu de face, pas un bout de mur
            for v in list(m.vus):
                if not v["fort"] and any(abs(v["q"] - o) <= 300 for o in m.ouverts):
                    m.vus.remove(v)
                    v["s"].aretes.append(v["pt"])
        self.murs = [m for m in self.murs if m.vus]
        for m in self.murs:
            m.pieds, m.forts = [v["q"] for v in m.vus], [v["fort"] for v in m.vus]
            for v in m.vus:
                v["s"].murs_vus.append(v["vu"])
                v["s"].sur_mur.append(m)
        for m in self.murs:
            for s in self.noeuds:
                if m.cote(s.x, s.y) > -150:
                    continue                                     # station sur la ligne ou de l'autre côté
                for pt in s.aretes:                              # arêtes posées sur la ligne du mur
                    if abs(m.cote(*pt)) <= 100:
                        q = m.absc(*pt)
                        if all(abs(q - f) > 200 for f in m.pieds) and min(m.pieds) - 2500 < q < max(m.pieds) + 2500:
                            m.aretes.append(q)
            m.aretes.sort()
            m.calculer_pleins(*self.portees)
        self.chercher_les_portes()

    def chercher_les_portes(self):
        for m in self.murs:
            # repères : les arêtes posées sur la ligne et les pieds faibles (un montant vu de face ressemble à un bout de mur)
            reperes = sorted(m.aretes + [f for f, fort in zip(m.pieds, m.forts) if not fort])
            francs = [f for f, fort in zip(m.pieds, m.forts) if fort]
            if not francs:
                continue                                         # aucun palier franc sur cette ligne : des meubles, pas un mur
            ar = []
            for q in reperes:                                    # le même repère vu de plusieurs stations : un seul
                if not ar or q - ar[-1] > 150:
                    ar.append(q)
            for qa, qb in zip(ar, ar[1:]):
                if not (600 <= qb - qa <= 1300) or any(qa - 100 < f < qb + 100 for f in francs) or any(qa + 150 < o < qb - 150 for o in m.ouverts):
                    continue
                qc = (qa + qb) / 2
                centre = (m.rho * m.n[0] + qc * m.t[0], m.rho * m.n[1] + qc * m.t[1])
                devant = (centre[0] - 550 * m.n[0], centre[1] - 550 * m.n[1])
                if any(math.hypot(centre[0] - d["centre"][0], centre[1] - d["centre"][1]) < 400 for d in self.portes):
                    continue
                d = {"centre": centre, "devant": devant, "dir": m.phi, "largeur": round(qb - qa), "etat": "à faire"}
                self.portes.append(d)
                self.dire(f"  porte possible : {qb - qa:.0f} mm de large vers ({centre[0]:.0f}, {centre[1]:.0f}), direction {m.phi:.0f}°")

    def obstacles(self):
        """Points à éviter : (x, y, garde). Un même objet vu de plusieurs stations donne des points décalés de 10 à 20 cm
        (l'écho est placé au milieu du palier, à quelques degrés près) : parmi les points à moins de 30 cm les uns des
        autres, seul celui qui a été vu du plus près est gardé. Sans cela les montants d'une porte, vus de loin par
        d'autres stations, finissent par boucher le passage sur la carte."""
        surs, vus = [], []
        for s in self.noeuds:
            for phi, dist, pied in s.murs_vus:
                t = (-math.sin(math.radians(phi)), math.cos(math.radians(phi)))
                surs += [(pied[0] + k * 120 * t[0], pied[1] + k * 120 * t[1], GARDE["mur"]) for k in (-1, 0, 1)]
            vus += [(math.hypot(x - s.x, y - s.y), x, y, GARDE["arete"]) for x, y in s.aretes]
            vus += [(math.hypot(x - s.x, y - s.y), x, y, GARDE["echo"]) for x, y in s.echos]
        surs += [(x, y, GARDE.get(g, 230.0)) for x, y, g in self.contacts]
        gardes = list(surs)
        if vus:
            vus.sort()
            V = np.array([(x, y) for _, x, y, _ in vus], float)
            S_ = np.array([(x, y) for x, y, _ in surs], float).reshape(-1, 2)
            pris = np.zeros(len(vus), bool)
            for i, (portee, x, y, g) in enumerate(vus):
                if len(S_) and np.min(np.hypot(S_[:, 0] - x, S_[:, 1] - y)) < 300:
                    continue                                     # un mur ou un contact est déjà là
                if pris[:i].any() and np.min(np.hypot(V[:i][pris[:i], 0] - x, V[:i][pris[:i], 1] - y)) < 300:
                    continue                                     # le même objet, déjà vu de plus près
                pris[i] = True
                gardes.append((x, y, g))
        return np.array(gardes, float).reshape(-1, 3)

    def trajet_libre(self, O, S, x1, y1):
        """Aucun obstacle connu à moins de sa garde du trajet de la station S au point (x1, y1). Un point que la station
        S contredit (son propre tour lit, dans cette direction, au moins 20 cm plus loin que lui) ne compte pas : ce
        qu'elle voit d'ici prime sur ce que d'autres stations ont cru voir de plus loin."""
        if not len(O):
            return True
        x0, y0 = S.x, S.y
        L = math.hypot(x1 - x0, y1 - y0)
        u = ((x1 - x0) / L, (y1 - y0) / L)
        wx, wy = O[:, 0] - x0, O[:, 1] - y0
        t = wx * u[0] + wy * u[1]
        d0 = np.hypot(wx, wy)
        d = np.where(t <= 0, d0, np.where(t >= L, np.hypot(O[:, 0] - x1, O[:, 1] - y1), np.abs(wx * u[1] - wy * u[0])))
        derriere = (d0 < 280) & (t < 0.35 * d0)                 # tout près du départ et pas devant : le robot s'en éloigne
        contredit = S.profil[(np.degrees(np.arctan2(wy, wx)) % 360.0).astype(int) % 360] > d0 + 200.0
        gene = ((d < O[:, 2]) | (np.hypot(O[:, 0] - x1, O[:, 1] - y1) < O[:, 2] + 70.0)) & ~derriere & ~contredit
        return not gene.any()                                    # à l'arrivée, 70 mm de plus : le robot y tourne sur place

    def mur_touche(self, S, x1, y1):
        """vrai si le trajet de la station S au point (x1, y1) s'approche d'un mur tenu pour plein"""
        for m in self.murs:
            a0, a1 = m.cote(S.x, S.y), m.cote(x1, y1)
            if a0 > -50 or a1 < -(RAYON + 60):
                continue                                         # station sur la ligne ou derrière ; ou trajet qui reste à distance
            f = min(1.0, -a0 / (a1 - a0)) if a1 > a0 else 1.0
            if m.plein(m.absc(S.x + f * (x1 - S.x), S.y + f * (y1 - S.y))):
                return True
        return False

    def premier_mur(self, S, phi):
        """distance, le long de la direction phi depuis la station S, de la première ligne de mur tenue pour pleine"""
        u = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
        best = 1e9
        for m in self.murs:
            a0 = m.cote(S.x, S.y)
            vers = m.n[0] * u[0] + m.n[1] * u[1]
            if a0 > -50 or vers < 0.15:
                continue
            D = -a0 / vers
            if D < best and m.plein(m.absc(S.x + D * u[0], S.y + D * u[1])):
                best = D
        return best

    def cache(self, x, y, X, Y):
        """pour chaque point (X, Y) : vrai si un mur tenu pour plein le sépare du point (x, y)"""
        out = np.zeros(len(X), bool)
        for m in self.murs:
            a0 = m.cote(x, y)
            if abs(a0) < 50 or not m.pleins:
                continue
            a1 = m.n[0] * X + m.n[1] * Y - m.rho
            traverse = (a0 * a1 < 0) & (np.abs(a1) > 20)
            if not traverse.any():
                continue
            f = a0 / (a0 - a1[traverse])
            q = m.t[0] * (x + f * (X[traverse] - x)) + m.t[1] * (y + f * (Y[traverse] - y))
            dans = np.zeros(len(q), bool)
            for lo, hi in m.pleins:
                dans |= (q >= lo) & (q <= hi)
            idx = np.where(traverse)[0]
            out[idx[dans]] = True
        return out

    def premiers_murs(self, S):
        """pour chaque degré de direction depuis la station S : distance de la première ligne de mur tenue pour pleine"""
        ang = np.radians(np.arange(360) + 0.5)
        ux, uy = np.cos(ang), np.sin(ang)
        best = np.full(360, 1e9)
        for m in self.murs:
            a0 = m.cote(S.x, S.y)
            if a0 > -50 or not m.pleins:
                continue
            vers = m.n[0] * ux + m.n[1] * uy
            ok = vers > 0.15
            D = np.where(ok, -a0 / np.where(ok, vers, 1.0), 1e9)
            q = m.t[0] * (S.x + D * ux) + m.t[1] * (S.y + D * uy)
            dans = np.zeros(360, bool)
            for lo, hi in m.pleins:
                dans |= (q >= lo) & (q <= hi)
            best = np.where(ok & dans & (D < best), D, best)
        return best

    def surveiller(self):
        """Grille des endroits déjà regardés : à moins de PORTEE_VUE d'une station, sans mur plein entre les deux, et
        dans une direction où le tour a vu au moins jusque-là. Une direction sans écho ne dit rien de sûr : elle compte
        jusqu'au mur connu qu'elle longe de biais s'il y en a un, sinon jusqu'à 90 cm seulement, pour que ce qui est
        derrière reste « à voir »."""
        self.vu = np.zeros((2 * DEMI_GRILLE, 2 * DEMI_GRILLE), bool)
        for s in self.noeuds:
            ix0, iy0 = int(round(s.x / CASE)), int(round(s.y / CASE))
            X, Y = (ix0 + DISQUE_VUE[:, 0]) * CASE, (iy0 + DISQUE_VUE[:, 1]) * CASE
            dist = np.hypot(X - s.x, Y - s.y)
            murs = self.premiers_murs(s)
            portee = np.where(s.profil > 0, s.profil + 150.0, np.where(murs < 1e8, murs, 900.0))
            deg = (np.degrees(np.arctan2(Y - s.y, X - s.x)) % 360.0).astype(int) % 360
            ok = ((dist <= portee[deg]) | (dist < 400)) & ~self.cache(s.x, s.y, X, Y)
            self.vu[iy0 + DISQUE_VUE[ok, 1] + DEMI_GRILLE, ix0 + DISQUE_VUE[ok, 0] + DEMI_GRILLE] = True

    def gain(self, x, y):
        """surface (m²) jamais regardée qu'une station posée en (x, y) pourrait voir"""
        ix0, iy0 = int(round(x / CASE)), int(round(y / CASE))
        libre = ~self.vu[iy0 + DISQUE_VUE[:, 1] + DEMI_GRILLE, ix0 + DISQUE_VUE[:, 0] + DEMI_GRILLE]
        if not libre.any():
            return 0.0
        X, Y = (ix0 + DISQUE_VUE[libre, 0]) * CASE, (iy0 + DISQUE_VUE[libre, 1]) * CASE
        return float((~self.cache(x, y, X, Y)).sum()) * (CASE / 1000.0) ** 2

    def chemin_arbre(self, a, b):
        """stations à parcourir de a à b par l'arbre (a exclue, b incluse) et longueur en mm"""
        def ancetres(s):
            out = [s]
            while out[-1].parent is not None:
                out.append(out[-1].parent)
            return out
        ca, cb = ancetres(a), ancetres(b)
        commun = next(s for s in ca if s in cb)
        route = ca[1:ca.index(commun) + 1] + list(reversed(cb[:cb.index(commun)]))
        pts = [a] + route
        return route, sum(math.hypot(u.x - v.x, u.y - v.y) for u, v in zip(pts, pts[1:]))

    def candidats(self, ici):
        O = self.obstacles()
        self.surveiller()
        out = []
        k = int((PORTEE_VUE + PAS[0]) / CASE)
        for S in self.noeuds:
            ix0, iy0 = int(round(S.x / CASE)) + DEMI_GRILLE, int(round(S.y / CASE)) + DEMI_GRILLE
            if (~self.vu[iy0 - k:iy0 + k + 1, ix0 - k:ix0 + k + 1]).sum() * (CASE / 1000.0) ** 2 < GAIN_MIN:
                continue                                         # tout est déjà regardé autour de cette station
            _, d_arbre = self.chemin_arbre(ici, S)
            for phi in range(0, 360, 5):
                if any(abs(ecart(phi - b)) < 20 for b in S.bloques):
                    continue
                classe, f = S.vue(phi)
                if classe is None:
                    continue
                D = self.premier_mur(S, phi)
                if classe == "inconnu" and D < 4200:
                    continue                                     # rien derrière : un mur connu vu de biais
                for L in PAS:
                    if f < L + 300:
                        continue
                    x1, y1 = S.x + L * math.cos(math.radians(phi)), S.y + L * math.sin(math.radians(phi))
                    if any(math.hypot(x1 - s.x, y1 - s.y) < 450 for s in self.noeuds if s is not S):
                        continue
                    if any(math.hypot(x1 - zx, y1 - zy) < zr for zx, zy, zr in self.interdits):
                        continue
                    if not self.trajet_libre(O, S, x1, y1) or self.mur_touche(S, x1, y1):
                        continue
                    g = self.gain(x1, y1)
                    if g < GAIN_MIN:
                        break                                    # plus près de la station, il y a encore moins à voir
                    poids = 1.0 if classe == "vu" else 0.5
                    if S.porte is not None and abs(ecart(phi - S.porte)) <= 25:
                        poids *= 3.0                              # devant une porte : la passer d'abord
                    out.append({"score": poids * g / (30.0 + 0.025 * (d_arbre + L)), "S": S, "phi": phi, "L": L, "x": x1, "y": y1,
                                "classe": classe, "libre": f, "gain": g, "genre": "station"})
                    break
        for d in self.portes:                                   # se placer devant une porte repérée
            if d["etat"] != "à faire":
                continue
            x1, y1 = d["devant"]
            if any(math.hypot(x1 - s.x, y1 - s.y) < 300 for s in self.noeuds):
                d["etat"] = "vue d'une station"
                continue
            for S in sorted(self.noeuds, key=lambda s: math.hypot(x1 - s.x, y1 - s.y))[:4]:
                L = math.hypot(x1 - S.x, y1 - S.y)
                phi = math.degrees(math.atan2(y1 - S.y, x1 - S.x)) % 360.0
                if L > 1400 or any(abs(ecart(phi - b)) < 20 for b in S.bloques) or not self.trajet_libre(O, S, x1, y1):
                    continue
                _, d_arbre = self.chemin_arbre(ici, S)
                g = max(self.gain(x1, y1), 2.0)
                out.append({"score": 2.0 * g / (30.0 + 0.025 * (d_arbre + L)), "S": S, "phi": phi, "L": L, "x": x1, "y": y1, "classe": "porte",
                            "libre": 0.0, "gain": g, "genre": "porte", "porte": d})
                break
        out.sort(key=lambda c: -c["score"])
        return out


    # ------------------------------------------------------------ recalage en repassant par une station connue
    def recaler(self, S, genre="recalage"):
        st, raison = self.faire_un_tour(f"r{len(self.j['recalages']) + 1}-{S.nom}", S, genre)
        if st is None:
            return None, raison
        if self.plan is not None:                                # le tour vient d'être recalé sur le plan : rien de plus à faire
            self.dernier_recalage = self.dernier_fix = self.est.chemin
            return st, None
        res = carto.apparier(S.pal, S.pose[2], st.pal, st.pose[2])
        note = {"station": S.nom, "tour": st.nom, "chemin_mm": round(self.est.chemin - self.dernier_recalage),
                "croyance": [round(st.x - S.x), round(st.y - S.y)], "mesure": None, "corrige": False}
        # Sur le robot (2026-11-10), deux tours faits au même endroit donnent un décalage faux de 5 cm, et une fois de
        # 18 cm avec deux parois seulement : la mesure n'est donc crue que si trois parois au moins s'accordent dans
        # deux directions, elle est refusée si elle s'écarte de plus de trois fois ce que la dérive et son propre bruit
        # (4 cm) expliquent, et elle ne corrige la position qu'en proportion de la confiance qu'elle mérite.
        chemin = self.est.chemin - S.chemin                      # ce que le robot a roulé depuis qu'il a fait cette station
        self.dernier_recalage = self.est.chemin                   # prochain essai dans --recalage-m mètres, réussi ou non
        if res is not None and len(res[2]) >= 3 and res[3] == 2 and max(q[3] for q in res[2]) >= 20.0:
            dx, dy, paires, rang = res
            ex, ey = (S.x + dx) - st.x, (S.y + dy) - st.y            # ce qu'il faudrait ajouter à la position tenue par le PC
            derive = 20.0 + 0.012 * chemin
            note.update({"mesure": [round(dx), round(dy)], "parois": len(paires), "rang": rang, "ecart_mm": round(math.hypot(ex, ey))})
            if math.hypot(ex, ey) > 3.0 * math.hypot(derive, 40.0):
                self.dire(f"  recalage sur la station {S.nom} : les parois disent ({dx:+.0f}, {dy:+.0f}) mm, soit {math.hypot(ex, ey):.0f} mm d'écart :"
                          f" trop pour {chemin / 1000:.1f} m parcourus, mesure refusée, position gardée")
            else:
                poids = derive ** 2 / (derive ** 2 + 40.0 ** 2)
                ex, ey = poids * ex, poids * ey
                self.est.decaler(ex, ey)
                self.dernier_fix = self.est.chemin
                note.update({"corrige": True, "correction": [round(ex), round(ey)], "poids": round(poids, 2)})
                self.dire(f"  recalage sur la station {S.nom} : le PC se croyait à ({st.x - S.x:+.0f}, {st.y - S.y:+.0f}) mm d'elle, les parois disent"
                          f" ({dx:+.0f}, {dy:+.0f}) mm ({len(paires)} parois) ; position corrigée de ({ex:+.0f}, {ey:+.0f}) mm (poids {poids:.2f})")
        else:
            self.dire(f"  recalage sur la station {S.nom} : pas assez de parois communes, position gardée")
        self.j["recalages"].append(note)
        return st, None

    def aller_station(self, ici, cible):
        """Par l'arbre, de station en station ; recale en chemin si le robot a beaucoup roulé. Renvoie (station atteinte,
        raison). Un trajet refusé par le capteur de distance tout près de la station visée (elle est près d'un obstacle)
        compte comme arrivé. Un trajet qui échoue autrement est retenté une fois, après un recalage sur la station
        précédente : c'est le plus souvent la position qui a glissé."""
        route, _ = self.chemin_arbre(ici, cible)
        for s in route:
            for essai in (1, 2):
                ok, raison = self.aller_a(s.x, s.y, tolerance=50.0, connu=True)
                if ok:
                    break
                l, q = self.pose()
                if l is None or any(m in str(raison) for m in ARRET_NET):
                    return None, f"trajet vers la station {s.nom} impossible : {raison}"
                if "obstacle à" in str(raison) and math.hypot(q[0] - s.x, q[1] - s.y) <= 220:
                    ok = True                                    # la station est là, à moins de 22 cm, contre un obstacle
                    break
                if "pare-chocs" in str(raison) or "sol sombre" in str(raison):
                    for _ in range(2):
                        r = self.saut("2", 0.9, lb_repos=5000, lb_max=5000, vide_min=self.a.vide_min)
                        r["but"] = "recul après un contact ou un bord sombre"
                        self.j["sauts"].append(r)
                        self.dormir(0.4)
                if essai == 2:
                    ok2, r2 = self.aller_a(ici.x, ici.y, tolerance=60.0, connu=True)
                    if not ok2:
                        return None, f"trajet vers la station {s.nom} impossible ({raison}), et retour à la station {ici.nom} impossible ({r2}) : robot arrêté entre les deux"
                    return ici, f"trajet vers la station {s.nom} impossible : {raison}"
                self.dire(f"  trajet vers la station {s.nom} arrêté ({raison}) : retour à la station {ici.nom}, recalage, puis second essai")
                ok2, r2 = self.aller_a(ici.x, ici.y, tolerance=60.0, connu=True)
                if not ok2:
                    return None, f"trajet vers la station {s.nom} impossible ({raison}), et retour à la station {ici.nom} impossible ({r2}) : robot arrêté entre les deux"
                st, r3 = self.recaler(ici)
                if st is None:
                    return ici, f"trajet vers la station {s.nom} impossible ({raison}), puis tour de recalage impossible ({r3})"
            ici = s
            if self.plan is None and self.est.chemin - self.dernier_recalage >= self.a.recalage_m * 1000.0:
                st, raison = self.recaler(s)
                if st is None:
                    return ici, "tour de recalage impossible : " + str(raison)
        return ici, None

    # ------------------------------------------------------------ après un trajet arrêté
    def apres_echec(self, S, c, raison):
        """Renvoie (station où est le robot, à compter comme échec ?) ; station None = arrêt net."""
        l, q = self.pose()
        self.j["echecs"].append({"depuis": S.nom, "direction": c["phi"], "raison": raison, "position": [round(q[0]), round(q[1])] if q else None})
        self.dire(f"    arrêté : {raison}" + (f" ; robot en ({q[0]:.0f}, {q[1]:.0f})" if q else ""))
        S.bloques.append(c["phi"])
        if c["genre"] == "porte":
            c["porte"]["etat"] = "inaccessible"
        if l is None or any(m in str(raison) for m in ARRET_NET):
            return None, True
        ca, sa = math.cos(math.radians(q[2])), math.sin(math.radians(q[2]))
        if "pare-chocs" in str(raison):
            gauche, droit = "gauche" in str(raison), "droit" in str(raison)
            cote = math.radians(q[2] + (50.0 if gauche and not droit else -50.0 if droit and not gauche else 0.0))
            self.contacts.append((q[0] + 200 * math.cos(cote), q[1] + 200 * math.sin(cote), "contact"))
            for _ in range(2):                                    # 17 cm : assez pour tourner, et pour revenir ici plus tard sans alerter le capteur
                r = self.saut("2", 0.9, lb_repos=5000, lb_max=5000, vide_min=self.a.vide_min)
                r["but"] = "recul après un contact"
                self.j["sauts"].append(r)
                self.dormir(0.4)
            l, q = self.pose()
            if l is None:
                return None, True
        elif "sol sombre" in str(raison):
            # bord sombre (tapis) : le robot le prendrait pour un vide et quitterait le mode Safe ; c'est un obstacle
            self.contacts.append((q[0] + 180 * ca, q[1] + 180 * sa, "sombre"))
            for _ in range(2):
                r = self.saut("2", 0.9, lb_repos=5000, lb_max=5000, vide_min=self.a.vide_min)
                r["but"] = "recul après un bord sombre"
                self.j["sauts"].append(r)
                self.dormir(0.4)
            l, q = self.pose()
            if l is None:
                return None, True
        elif "obstacle à" in str(raison) and l["us_mm"] > 0:
            self.contacts.append((q[0] + (l["us_mm"] + DX) * ca, q[1] + (l["us_mm"] + DX) * sa, "devant"))
        elif "base proche" in str(raison):
            self.interdits.append((q[0] + 350 * ca, q[1] + 350 * sa, 550.0))
            self.j["interdits"] = self.interdits
        avance = math.hypot(q[0] - S.x, q[1] - S.y)
        loin = min(math.hypot(q[0] - s.x, q[1] - s.y) for s in self.noeuds)
        if avance >= 350 and loin >= 400 and "base proche" not in str(raison):
            st, r2 = self.faire_un_tour(str(len(self.noeuds)), S, "arrêt")
            if st is not None:
                self.dire(f"station {st.nom} (là où le robot s'est arrêté) en ({st.x:.0f}, {st.y:.0f}), {len(st.pal)} paliers")
                return st, False
        ok, r2 = self.aller_a(S.x, S.y, tolerance=60.0, connu=True)
        if not ok:
            self.dire(f"    retour à la station {S.nom} impossible : {r2}")
            return None, True
        return S, True

    # ------------------------------------------------------------ la boucle
    def explorer(self):
        a = self.a
        l, q = self.pose()
        if l is None:
            raise SystemExit("aucune ligne récente du journal : l'enregistreur tourne-t-il, le robot répond-il ?")
        self.p.vitesse(a.vitesse)
        self.dormir(0.3)
        if self.plan is not None:                                # la carte est celle du plan : le robot y est posé d'après --depart-plan
            u, v, cap = (float(x) for x in a.depart_plan.split(","))
            self.est.X, self.est.Y = self.vers_mm(u, v)
            self.est.bx, self.est.by, self.est.C = self.est.X, self.est.Y, cap
            if not getattr(a, "sans_filtre", False):
                import localiser
                sur = getattr(a, "depart_sur", False)
                # À partir du firmware v9 le gyroscope compte aussi les rotations lentes quand le robot roule : le filtre
                # ne doit plus les reprendre sur les roues (elles seraient comptées deux fois).
                try:
                    ver = str(json.loads(self.lire("/api/state")).get("ver", ""))
                    n_ver = int("".join(c for c in ver.split()[0] if c.isdigit()) or 8)
                except (ValueError, IndexError, RuntimeError):
                    n_ver = 8
                self.filtre = localiser.Filtre(self.plan, n=getattr(a, "filtre_n", 8000), k_gyro=a.k_gyro, roues_si_muet=n_ver < 9)
                self.filtre.demarrer(u, v, cap, sigma_mm=100.0 if sur else 250.0, sigma_cap=6.0 if sur else 15.0)
                self.i_filtre = max(0, len(self.p.lignes) - 1)
                self.dire(f"localisation : filtre à {self.filtre.n} hypothèses autour du pixel ({u:.0f}, {v:.0f}), cap {cap:.0f}°")
        ici, raison = self.faire_un_tour("0", None, "départ")
        if ici is None:
            raise SystemExit("premier tour impossible : " + str(raison))
        self.dire(f"station 0 : {len(ici.pal)} paliers, {len(self.murs)} lignes de murs, axes de la pièce {self.axe}°")
        self.sauver()
        while self.j["fin"] is None:
            if len(self.noeuds) - 1 >= a.stations:
                self.j["fin"] = "nombre de stations atteint"
            elif (self.maintenant() - self.t0) / 60.0 >= a.minutes:
                self.j["fin"] = "durée atteinte"
            elif self.echecs >= a.echecs_max:
                self.j["fin"] = f"{self.echecs} trajets arrêtés"
            elif json.loads(self.lire("/api/state"))["robot"]["q"] < a.batterie_min:
                self.j["fin"] = "batterie basse"
            if self.demande() == "arrêt":
                self.j["fin"] = "arrêt demandé (fichier _ARRET)"
                ici = None
            elif self.demande() == "retour":
                self.j["fin"] = "retour demandé (fichier _RENTRE)"
            if self.j["fin"]:
                break
            if self.plan is not None:
                self.lire_cibles()
                if self.cibles:
                    ici = self.vers_cible(ici)
                    if ici is None:
                        self.j["fin"] = "arrêt pendant un trajet vers une cible"
                        break
                    self.sauver()
                    continue
                if getattr(a, "cibles_seules", False) and self.serie is not None:
                    self.j["fin"] = "destinations faites"      # un trajet demandé, pas une exploration : on s'arrête là
                    break
            cands = self.candidats(ici)
            if not cands and self.portees[0] > 300.0:
                # seconde passe : on fait moins confiance aux murs (une porte a pu être prise pour un mur plein)
                self.portees = (300.0, 150.0)
                self.dire("plus rien à voir avec des murs tenus pour pleins sur 60 cm : seconde passe, pleins sur 30 cm seulement")
                self.refaire_les_murs()
                cands = self.candidats(ici)
            if not cands:
                self.j["fin"] = "plus rien à voir"
                break
            c = cands[0]
            self.j["choix"].append({"de": ici.nom, "depuis": c["S"].nom, "direction": c["phi"], "longueur": round(c["L"]), "classe": c["classe"],
                                    "gain_m2": round(c["gain"], 2), "score": round(c["score"], 4), "candidats": len(cands)})
            if c["S"] is not ici:
                ici, raison = self.aller_station(ici, c["S"])
                if raison:
                    self.dire("  " + raison)
                    if ici is None:
                        self.j["fin"] = "arrêt : " + raison
                        break
                    self.echecs += 1
                    c["S"].bloques.append(c["phi"])               # on ne sait pas y retourner : ne plus la proposer tout de suite
                    continue
            S = ici
            self.dire(f"  depuis la station {S.nom} : direction {c['phi']:.0f}° ({c['classe']}" + (f", libre sur {c['libre'] / 10:.0f} cm" if c["classe"] == "vu" else "")
                      + f"), {c['L']:.0f} mm, vers ({c['x']:.0f}, {c['y']:.0f}), {c['gain']:.1f} m² à voir ; {len(cands)} candidats")
            ok, raison = self.aller_a(c["x"], c["y"])
            if ok:
                genre = c["genre"]
                st, raison = self.faire_un_tour(str(len(self.noeuds)), S, genre)
                if st is None:
                    self.j["fin"] = "tour impossible : " + str(raison)
                    ici = None
                    break
                if genre == "porte":
                    st.porte = c["porte"]["dir"]
                    c["porte"]["etat"] = "station " + st.nom
                self.dire(f"station {st.nom}" + (" (devant une porte)" if genre == "porte" else "") + f" en ({st.x:.0f}, {st.y:.0f}) : {len(st.pal)} paliers"
                          + (", sur un tapis" if st.tapis else "") + f" ; {len(self.murs)} lignes de murs")
                ici = st
            else:
                ici, compte = self.apres_echec(S, c, raison)
                if ici is None:
                    self.j["fin"] = "arrêt : " + str(raison)
                    break
                if compte:
                    self.echecs += 1
            self.sauver()
        # retour à la station 0 par l'arbre, puis tour final : il mesure la dérive qui reste
        if not a.sans_retour and ici is not None:
            ici, raison = self.aller_station(ici, self.noeuds[0])
            if raison and ici is not None and ici is not self.noeuds[0]:      # second essai, depuis la dernière station atteinte
                self.dire("  " + raison + " ; second essai de retour")
                ici, raison = self.aller_station(ici, self.noeuds[0])
            if raison:
                self.j["fin"] += " ; retour interrompu : " + raison
            else:
                st, raison = self.recaler(self.noeuds[0], genre="retour")
                self.j["fin"] += " ; retour au départ fait" + ("" if st else " sans tour final : " + str(raison))
        return ici


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    p_ = argparse.ArgumentParser()
    p_.add_argument("adresse")
    p_.add_argument("prefixe")
    p_.add_argument("--stations", type=int, default=40, help="nombre de stations nouvelles au plus")
    p_.add_argument("--minutes", type=float, default=45.0, help="durée au plus, minutes")
    p_.add_argument("--vitesse", type=int, default=75, help="réglage de vitesse des sauts (mm/s demandés)")
    p_.add_argument("--tour-v", type=int, default=30, help="vitesse de roues des tours sur place (20 à 62)")
    p_.add_argument("--vide-min", type=float, default=500.0, help="signal des capteurs de vide sous lequel le robot n'avance pas et s'arrête (500 : tapis permis, bords sombres évités ; 1500 : arrêt devant tout tapis)")
    p_.add_argument("--interdit", default="", help="zones interdites : x,y,rayon en mm dans le repère du départ, séparées par des points-virgules")
    p_.add_argument("--k-gyro", type=float, default=1.0015, help="échelle du gyroscope : rotation vraie / rotation comptée par le cerveau")
    p_.add_argument("--recalage-m", type=float, default=12.0, help="mètres parcourus entre deux recalages sur une station connue")
    p_.add_argument("--echecs-max", type=int, default=12, help="nombre de trajets arrêtés sans station au bout avant d'abandonner")
    p_.add_argument("--batterie-min", type=int, default=1000, help="charge en mAh sous laquelle on rentre")
    p_.add_argument("--sans-retour", action="store_true", help="ne pas revenir au point de départ à la fin")
    p_.add_argument("--plan", default="", help="image du plan de l'appartement (plan.py) : carte dans le repère du plan, recalage sur le plan, cibles")
    p_.add_argument("--px-par-m", type=float, default=53.0, help="échelle du plan, pixels par mètre")
    p_.add_argument("--plan-passe", default="", help="avec --plan : la même image où un trait vert montre par où on passe (portes ouvertes aujourd'hui)")
    p_.add_argument("--depart-plan", default="", help="avec --plan : U,V,CAP, pixel du plan où est le robot et direction de son avant (degrés, 0 = droite, 90 = haut)")
    p_.add_argument("--depart-sur", action="store_true", help="avec --plan : la position de départ est sûre à 10 cm et 5° près (premier tour cherché dans 30 cm et 10° au lieu de 60 cm et 25°)")
    p_.add_argument("--plan-roule", default="", help="avec --plan : fichiers JSON de l_localisation_globale.py, séparés par des points-virgules ; les trajets déjà roulés y sont tenus pour du sol sûr")
    p_.add_argument("--base-plan", default="", help="avec --plan : U,V, pixel de la base ; le champ infrarouge de la base n'arrête alors que les avances vers elle")
    p_.add_argument("--sans-filtre", action="store_true", help="avec --plan : ancien recalage à une seule hypothèse (caler_sur_le_plan) au lieu du filtre de localiser.py")
    p_.add_argument("--filtre-n", type=int, default=8000, help="nombre d'hypothèses du filtre")
    p_.add_argument("--fluide", action="store_true", help="avances d'un seul tenant (Pilote.avance) au lieu de sauts de 1,3 s")
    p_.add_argument("--tour-tous-les", type=float, default=600.0, help="vers une destination : distance en mm entre deux tours sur place (600 ; 1800 avec le filtre)")
    p_.add_argument("--sans-visee", action="store_true", help="avec --fluide : ne pas viser à côté du point pour compenser la dérive du robot")
    p_.add_argument("--enchainer", action="store_true", help="pas de tour sur place aux destinations de passage si le dernier tour est proche (essai : en simulation le robot reste parfois coincé ensuite)")
    p_.add_argument("--sans-z", action="store_true", help="ne pas envoyer z avant chaque tour (le tour du firmware refait déjà le zéro du gyroscope)")
    p_.add_argument("--cibles-seules", action="store_true", help="avec --plan : s'arrêter quand les destinations données sont faites, sans explorer ensuite")
    p_.add_argument("--simulation", default="", help="nom d'un monde de simulateur.py : essai sans robot")
    p_.add_argument("--graine", type=int, default=1, help="simulation : graine du hasard")
    a = p_.parse_args()
    if a.simulation:
        import simulateur
        p = simulateur.RobotSimule(simulateur.Monde(**simulateur.MONDES[a.simulation]()), graine=a.graine, vitesse=a.vitesse)
    else:
        p = Pilote(a.adresse, a.prefixe)
    ex = Exploration(p, a)
    try:
        ex.explorer()
    finally:
        try:
            p.touche("5")
            p.vitesse(150)
        except Exception as err:
            print("réglages de fin non envoyés :", err, flush=True)
        ex.sauver()
        e = p.etat()
        ex.dire(f"fin : {ex.j['fin']} | mode {e['robot']['mode']} | roues {'en marche' if e['driving'] else 'arrêtées'} | pare-chocs {e['robot']['bump']}"
                f" | {len(ex.noeuds)} stations, {len(ex.j['recalages'])} recalages, {len(ex.j['caps'])} corrections de cap (échelle du gyroscope {ex.est.k:.4f}), {len(ex.j['sauts'])} sauts, {len(ex.j['echecs'])} trajets arrêtés,"
                f" {len(ex.contacts)} obstacles touchés ou vus devant | {ex.est.chemin / 1000:.1f} m | batterie {e['robot']['q']} mAh")
    return ex, p


if __name__ == "__main__":
    main()
