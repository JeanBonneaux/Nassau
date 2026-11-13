# simulateur.py — un robot simulé dans un appartement dessiné, pour essayer explorer3.py sans le vrai robot.
#
# Ce n'est pas un modèle fidèle du Roomba : c'est un banc d'essai pour la LOGIQUE de l'exploration (choix des stations,
# retours en arrière, contacts, recalages, fin). Il imite ce que les mesures du 2026-11-10 ont montré :
#   - le capteur de distance voit un mur lisse seulement près de la perpendiculaire (l'écho vient du pied de la
#     perpendiculaire), une arête ou un pied de table de plus près et de moins loin, un coin rentrant de loin ; un mur vu
#     de biais ne renvoie rien ; portée 4,2 m ; les 20° de fin de tour sont lus deux fois ;
#   - les capteurs optiques ne préviennent pas avant un contact (150 au plus contre la paroi du § 22) : c'est le
#     pare-chocs qui arrête le robot, et le cerveau coupe alors les roues (réflexe du firmware v6) ;
#   - le cerveau compte un peu trop peu de rotation (échelle du gyroscope), le robot tire un peu à gauche, les roues
#     comptent la distance à quelques millièmes près ; en reculant contre un obstacle les roues patinent sans que rien
#     ne le signale ;
#   - un tapis donne un signal bas sous les capteurs de vide sans gêner le mode Safe.
#
# RobotSimule a les mêmes méthodes que pilote.Pilote (frais, saut, etat, touche, vitesse, get pour /api/tour), avec une
# horloge simulée : explorer3.py l'utilise à la place du vrai robot quand on lui donne --simulation NOM_DU_MONDE.
import json
import math
import random

import numpy as np

from pilote import Pilote

RAYON = 170.0          # mm, rayon du robot
DX = 27.0              # mm, capteur de distance en avant du centre
PORTEE = 4200.0        # mm


def rect(x0, y0, x1, y1):
    """les quatre faces d'un rectangle (mur épais, meuble plein)"""
    return [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]


def monde_appartement():
    """Un couloir de 1,9 m, un séjour ouvert sur 1,5 m, une cuisine, une chambre, une salle de bain et un bureau derrière
    des portes de 75 à 80 cm ; murs de 10 cm ; un canapé, un lit, une table et ses chaises (pieds fins), un tapis."""
    m = []
    m += [((0, 0), (9000, 0)), ((9000, 0), (9000, 7000)), ((9000, 7000), (0, 7000)), ((0, 7000), (0, 0))]      # enveloppe
    for x0, x1 in ((0, 1500), (3000, 5000), (5800, 9000)):                  # mur bas du couloir : ouverture du séjour, porte de la cuisine
        m += rect(x0, 2900, x1, 3000)
    m += rect(4500, 0, 4600, 2900)                                          # séjour | cuisine
    for x0, x1 in ((0, 1200), (2000, 4500), (5250, 6100)):                  # mur haut du couloir : portes de la chambre et de la salle de bain
        m += rect(x0, 4900, x1, 5000)
    m += rect(3500, 5000, 3600, 7000)                                       # chambre | salle de bain
    m += rect(6000, 3000, 6100, 3500)                                       # fond du couloir : porte du bureau
    m += rect(6000, 4300, 6100, 4900)
    m += rect(6000, 5000, 6100, 7000)                                       # salle de bain | bureau
    m += rect(300, 300, 2300, 1200)                                         # canapé
    m += rect(200, 5400, 1700, 6900)                                        # lit
    m += rect(8300, 4200, 8900, 5600)                                       # bureau (meuble)
    m += rect(3700, 6500, 4400, 6950)                                       # meuble de salle de bain
    poteaux = []
    for cx, cy in ((7000, 1300),):                                          # table de cuisine : quatre pieds, et quatre chaises
        poteaux += [(cx - 400, cy - 300, 25), (cx + 400, cy - 300, 25), (cx - 400, cy + 300, 25), (cx + 400, cy + 300, 25)]
        for sx, sy in ((-650, 0), (650, 0), (0, -550), (0, 550)):
            poteaux += [(cx + sx - 150, cy + sy - 150, 15), (cx + sx + 150, cy + sy - 150, 15), (cx + sx - 150, cy + sy + 150, 15), (cx + sx + 150, cy + sy + 150, 15)]
    return dict(murs=m, poteaux=poteaux, tapis=[(2600, 500, 4200, 2300)], base=(60, 3950), depart=(1200, 3950, 0.0),
                etendue=(0, 0, 9000, 7000))


def monde_deux_pieces():
    """Deux pièces de 3 m sur 3,5 m reliées par une porte de 80 cm, un meuble dans chacune : le plus petit essai utile."""
    m = [((0, 0), (6100, 0)), ((6100, 0), (6100, 3500)), ((6100, 3500), (0, 3500)), ((0, 3500), (0, 0))]
    m += rect(3000, 0, 3100, 1300)
    m += rect(3000, 2100, 3100, 3500)
    m += rect(200, 2500, 1400, 3300)
    m += rect(4800, 200, 5900, 900)
    return dict(murs=m, poteaux=[(4500, 2600, 25)], tapis=[(3600, 1200, 5200, 2600)], base=None, depart=(1500, 1400, 30.0),
                etendue=(0, 0, 6100, 3500))


def monde_couloir():
    """Un couloir en L de 1,8 m de large avec une alcôve : pour les retours en arrière."""
    m = [((0, 0), (6000, 0)), ((6000, 0), (6000, 5000)), ((6000, 5000), (4200, 5000)), ((4200, 5000), (4200, 1800)),
         ((4200, 1800), (2600, 1800)), ((2600, 1800), (2600, 3000)), ((2600, 3000), (1400, 3000)), ((1400, 3000), (1400, 1800)),
         ((1400, 1800), (0, 1800)), ((0, 1800), (0, 0))]
    return dict(murs=m, poteaux=[], tapis=[], base=None, depart=(700, 900, 0.0), etendue=(0, 0, 6000, 5000))


MONDES = {"appartement": monde_appartement, "deux_pieces": monde_deux_pieces, "couloir": monde_couloir}


def dessiner_plan(monde, fichier, px_par_m=50.0, marge=40):
    """Le plan d'un monde simulé, en image, comme celui qu'un LiDAR donnerait : murs en traits sombres, sol blanc.
    Renvoie la fonction qui passe d'un point du monde (mm) à un pixel du plan."""
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = monde.etendue
    s = px_par_m / 1000.0
    W, H = int((x1 - x0) * s) + 2 * marge, int((y1 - y0) * s) + 2 * marge

    def px(x, y):
        return marge + (x - x0) * s, marge + (y1 - y) * s

    im = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(im)
    for a, b in zip(monde.A, monde.B):
        d.line([px(*a), px(*b)], fill=40, width=4)
    for x, y, r in monde.poteaux:
        u, v = px(x, y)
        d.ellipse([u - 2, v - 2, u + 2, v + 2], fill=150)
    im.save(fichier)
    return px


class Monde:
    def __init__(self, murs, poteaux=(), tapis=(), base=None, depart=(0.0, 0.0, 0.0), etendue=None):
        self.A = np.array([s[0] for s in murs], float)
        self.B = np.array([s[1] for s in murs], float)
        self.D = self.B - self.A
        self.L2 = (self.D ** 2).sum(1)
        self.poteaux = np.array(poteaux, float).reshape(-1, 3)
        self.tapis = list(tapis)
        self.base = base
        self.depart = depart
        self.etendue = etendue
        # extrémités : chaque point, avec les directions des murs qui en partent ou qui y passent, et leurs indices.
        # Vu d'un secteur de moins de 150° entre deux de ces directions, le point est un coin rentrant (écho fort) ;
        # sinon c'est une arête (écho faible).
        pts = {}
        for i, (a, b) in enumerate(murs):
            for p_, autre in ((a, b), (b, a)):
                e = pts.setdefault((round(p_[0]), round(p_[1])), {"dirs": [], "murs": set()})
                e["dirs"].append(math.atan2(autre[1] - p_[1], autre[0] - p_[0]))
                e["murs"].add(i)
        for k, e in pts.items():
            E = np.array(k, float)
            t = ((E - self.A) * self.D).sum(1) / np.maximum(self.L2, 1e-9)
            C = self.A + self.D * np.clip(t, 0.0, 1.0)[:, None]
            for j in np.where((np.hypot(*(C - E).T) < 1.0) & (t > 1e-6) & (t < 1 - 1e-6))[0]:      # un mur qui passe par ce point
                a = math.atan2(self.D[j, 1], self.D[j, 0])
                e["dirs"] += [a, a + math.pi]
                e["murs"].add(int(j))
        self.coins = [(np.array(k, float), np.sort(np.array(e["dirs"]) % (2 * math.pi)), tuple(e["murs"])) for k, e in pts.items()]

    # ------------------------------------------------------------ géométrie
    def visible(self, P, Q, sauf=()):
        """vrai si rien ne coupe le segment P -> Q (les murs dont l'indice est dans `sauf` ne comptent pas)"""
        r = Q - P
        den = r[0] * self.D[:, 1] - r[1] * self.D[:, 0]
        ap = self.A - P
        with np.errstate(divide="ignore", invalid="ignore"):
            s = (ap[:, 0] * self.D[:, 1] - ap[:, 1] * self.D[:, 0]) / den
            t = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den
        coupe = (np.abs(den) > 1e-9) & (s > 1e-6) & (s < 1 - 2e-3) & (t >= -1e-9) & (t <= 1 + 1e-9)
        for i in sauf:
            coupe[i] = False
        return not coupe.any()

    def dist_murs(self, P):
        """distance du point P à chaque mur, et point le plus proche"""
        t = np.clip(((P - self.A) * self.D).sum(1) / np.maximum(self.L2, 1e-9), 0.0, 1.0)
        C = self.A + self.D * t[:, None]
        return np.hypot(*(C - P).T), C

    def libre(self, P, marge=0.0):
        """vrai si un disque de la taille du robot posé en P ne touche rien"""
        d, _ = self.dist_murs(P)
        if d.min() < RAYON + marge:
            return False
        if len(self.poteaux) and (np.hypot(self.poteaux[:, 0] - P[0], self.poteaux[:, 1] - P[1]) - self.poteaux[:, 2]).min() < RAYON + marge:
            return False
        return True

    def contact(self, P):
        """direction (radians) du contact le plus proche si le disque du robot en P touche quelque chose, sinon None"""
        d, C = self.dist_murs(P)
        k = int(np.argmin(d))
        best = (d[k] - RAYON, C[k]) if d[k] < RAYON else None
        if len(self.poteaux):
            dp = np.hypot(self.poteaux[:, 0] - P[0], self.poteaux[:, 1] - P[1]) - self.poteaux[:, 2]
            j = int(np.argmin(dp))
            if dp[j] < RAYON and (best is None or dp[j] - RAYON < best[0]):
                best = (dp[j] - RAYON, self.poteaux[j, :2])
        if best is None:
            return None
        return math.atan2(best[1][1] - P[1], best[1][0] - P[0])

    def sur_tapis(self, P):
        return any(x0 <= P[0] <= x1 and y0 <= P[1] <= y1 for x0, y0, x1, y1 in self.tapis)

    # ------------------------------------------------------------ capteur de distance
    def sonar(self, P, theta, bruit=4.0, rng=random):
        """distance lue par le capteur placé en P et tourné vers theta (radians) ; 0 = rien à portée"""
        cands = []
        # 1. murs lisses : l'écho vient du pied de la perpendiculaire, si le capteur regarde à peu près vers lui
        t = ((P - self.A) * self.D).sum(1) / np.maximum(self.L2, 1e-9)
        F = self.A + self.D * t[:, None]
        v = F - P
        d = np.hypot(v[:, 0], v[:, 1])
        ang = np.abs((np.arctan2(v[:, 1], v[:, 0]) - theta + math.pi) % (2 * math.pi) - math.pi)
        ouv = np.radians(np.clip(24.0 - 3.5 * d / 1000.0, 10.0, 22.0))
        for i in np.where((t > 0.0) & (t < 1.0) & (d > 20) & (d < PORTEE) & (ang <= ouv))[0]:
            cands.append((d[i], F[i], (i,)))
        # 2. extrémités : arête (écho faible, de près) ou coin rentrant (écho fort, de loin)
        for E, dirs, murs_du_coin in self.coins:
            w = E - P
            de = math.hypot(w[0], w[1])
            if de < 20 or de > PORTEE:
                continue
            a = abs((math.atan2(w[1], w[0]) - theta + math.pi) % (2 * math.pi) - math.pi)
            vers_p = math.atan2(-w[1], -w[0]) % (2 * math.pi)             # direction du coin vers le capteur
            k = int(np.searchsorted(dirs, vers_p))
            secteur = (dirs[k % len(dirs)] - dirs[k - 1]) % (2 * math.pi) if len(dirs) > 1 else 2 * math.pi
            if secteur == 0.0:
                secteur = 2 * math.pi
            if secteur < math.radians(150):                                  # coin rentrant
                if a <= math.radians(min(22.0, max(10.0, 24.0 - 3.5 * de / 1000.0))):
                    cands.append((de, E, murs_du_coin))
            elif de < 2500 and a <= math.radians(min(10.0, max(3.0, 13.0 - 5.0 * de / 1000.0))):
                cands.append((de, E, murs_du_coin))
        # 3. pieds de table et de chaise : comme une arête
        for x, y, r in self.poteaux:
            w = np.array([x, y]) - P
            de = math.hypot(w[0], w[1]) - r
            if de < 20 or de > 2500:
                continue
            a = abs((math.atan2(w[1], w[0]) - theta + math.pi) % (2 * math.pi) - math.pi)
            if a <= math.radians(min(10.0, max(3.0, 13.0 - 5.0 * de / 1000.0))):
                cands.append((de, np.array([x, y]) - w / max(1.0, math.hypot(w[0], w[1])) * r, ()))
        for de, Q, sauf in sorted(cands, key=lambda c: c[0]):
            if self.visible(P, Q, sauf):
                return max(20.0, de + rng.gauss(0.0, bruit))
        return 0.0


class RobotSimule(Pilote):
    """Le robot et son cerveau, simulés. Mêmes méthodes que Pilote ; l'horloge avance toute seule (maintenant, dormir)."""

    def __init__(self, monde, graine=1, echelle_gyro=1.0015, vitesse=75):
        self.rng = random.Random(graine)
        self.monde = monde
        self.k_vrai = echelle_gyro                 # rotation vraie = k × rotation comptée par le cerveau
        self.x, self.y = float(monde.depart[0]), float(monde.depart[1])
        self.th = math.radians(monde.depart[2])    # cap vrai
        self.bx = self.by = self.bcap = 0.0        # position du cerveau (son repère part de zéro, comme après un redémarrage)
        self.t = 1000.0                            # horloge, secondes
        self.reglage = vitesse
        self.err_roues = 1.0 + self.rng.gauss(0.0, 0.003)
        self.pc = [0, 0]
        self.verrou = False
        self.mode = 3
        self.enc = [0.0, 0.0]
        self.lignes = []
        self.tour = {"etat": 0}
        self.reflexe = {"arrets": 0, "refus": 0, "verrou": False, "cause": ""}
        self.trace = [(self.x, self.y)]            # chemin vrai, pour les dessins
        self.contacts = []                         # contacts vrais : (x, y)
        self.tours_vrais = []                      # position vraie à chaque tour sur place : (x, y, cap en radians)
        self.q = 1800.0
        self._ligne()

    # ------------------------------------------------------------ horloge
    def maintenant(self):
        return self.t

    def dormir(self, s):
        self.t += s
        self.q -= 0.2 * s / 3.6

    # ------------------------------------------------------------ lignes du journal
    def _ligne(self):
        P = np.array([self.x, self.y])
        capteur = P + DX * np.array([math.cos(self.th), math.sin(self.th)])
        us = self.monde.sonar(capteur, self.th, rng=self.rng)
        sol = 1100.0 + 300.0 * self.rng.random() if self.monde.sur_tapis(P) else 2600.0 + 60.0 * self.rng.random()
        ir = 0
        if self.monde.base is not None:
            db = math.hypot(self.monde.base[0] - self.x, self.monde.base[1] - self.y)
            if db < 450:
                ir = 161
            elif db < 3000 and self.monde.visible(P, np.array(self.monde.base, float)):
                ir = 168
        l = {"pc_s": self.t, "ms": self.t * 1000.0, "enc_g": round(self.enc[0]), "enc_d": round(self.enc[1]),
             "pc_g": self.pc[0], "pc_d": self.pc[1], "roue_g": 0, "roue_d": 0,
             "vide_g": sol, "vide_avg": sol, "vide_avd": sol, "vide_d": sol,
             "lb_g": 20, "lb_avg": 16, "lb_cg": 36, "lb_cd": 10, "lb_avd": 44, "lb_d": 16,
             "mv": 15300, "ma": -180, "mode": self.mode, "cap_deg": self.bcap % 360.0, "rot_dps": getattr(self, "rot_dps", 0.0), "us_mm": float(round(us)),
             "x_mm": round(self.bx), "y_mm": round(self.by), "cap_pos": round(self.bcap, 1),
             "ir_dessus": ir, "ir_g": 0, "ir_d": 0, "cur_g": 0, "cur_d": 0}
        self.lignes.append(l)
        return l

    def lire(self):
        return 0

    def frais(self, age_max=0.7, attente=3.0):
        self.dormir(0.05)
        return self._ligne()

    def immobile(self, attente=3.0, lignes=7):
        self.dormir(0.35)
        return True

    # ------------------------------------------------------------ mouvements élémentaires
    def _tourner(self, dth_vrai):
        """rotation vraie de dth_vrai radians ; le cerveau en compte un peu moins"""
        self.th += dth_vrai
        self.bcap += math.degrees(dth_vrai) / self.k_vrai
        self.enc[0] -= math.degrees(dth_vrai) * 4.613          # 235 mm d'entraxe, 0,4446 mm par pas : 4,6 pas par degré et par roue
        self.enc[1] += math.degrees(dth_vrai) * 4.613

    def _avancer(self, ds, bloque=False):
        """ds mm le long du cap vrai (négatif : recul). bloque : les roues tournent mais le robot ne bouge pas."""
        if not bloque:
            self.x += ds * math.cos(self.th)
            self.y += ds * math.sin(self.th)
            self.trace.append((self.x, self.y))
        do = ds * self.err_roues
        b = math.radians(self.bcap)
        self.bx += do * math.cos(b)
        self.by += do * math.sin(b)
        self.enc[0] += do / 0.4446
        self.enc[1] += do / 0.4446

    # ------------------------------------------------------------ un saut, comme Pilote.saut
    def saut(self, touche, duree, marge_mm=600, lb_repos=150, lb_max=400, vide_min=1500, vide_stop=0):
        duree = min(duree, 1.4)
        l0 = self._ligne()
        recul = (touche == "2")
        refus = self.controle(l0, avance=(touche == "8"), marge_mm=marge_mm, lb_repos=lb_repos, vide_min=vide_min, recul=recul)
        if refus:
            return {"refus": refus}
        if touche in "846" and (self.verrou or self.pc[0] or self.pc[1]):       # le firmware refuse l'ordre
            self.reflexe["refus"] += 1
            self.dormir(duree + 0.4)
            return {"touche": touche, "duree_ordre": duree, "alarme": None, "avance_mm": 0.0, "rot_gyro": 0.0, "rot_roues": 0.0,
                    "us_avant": l0["us_mm"], "us_apres": l0["us_mm"], "lb_max": 44, "vide_min": l0["vide_g"], "lignes": 2}
        x0, y0, cap0 = self.bx, self.by, self.bcap
        v = self.reglage + 21.0
        alarme = None
        dt = 0.05
        n = max(1, int(round((duree - 0.06) / dt)))
        if touche == "2":
            self.verrou = False
        for _ in range(n):
            if touche == "8":
                self._tourner(math.radians(0.004 * v * dt) * (1.0 + self.rng.gauss(0.0, 0.5)))     # tire à gauche : 4° par mètre
                ds = v * dt
                P2 = np.array([self.x + ds * math.cos(self.th), self.y + ds * math.sin(self.th)])
                c = self.monde.contact(P2)
                if c is not None:
                    rel = (c - self.th + math.pi) % (2 * math.pi) - math.pi
                    if abs(rel) < math.radians(100):
                        self.pc = [1 if rel > -0.35 else 0, 1 if rel < 0.35 else 0]
                        self.verrou = True
                        self.reflexe["arrets"] += 1
                        self.contacts.append((float(P2[0]), float(P2[1])))
                        alarme = "pare-chocs " + ("gauche" if self.pc[0] else "") + (" droit" if self.pc[1] else "")
                        break
                self._avancer(ds)
            elif touche == "2":
                self._tourner(math.radians(0.3 * dt / 0.12))                                         # 3 à 4° à gauche par saut de 1,3 s
                ds = -(v - 8.0) * dt
                P2 = np.array([self.x + ds * math.cos(self.th), self.y + ds * math.sin(self.th)])
                self._avancer(ds, bloque=self.monde.contact(P2) is not None)                           # rien ne regarde derrière
                if self.monde.contact(np.array([self.x, self.y])) is None:
                    self.pc = [0, 0]
            else:
                self._tourner(math.radians((1 if touche == "4" else -1) * 2 * v / 235.0 * 57.29578 * dt) * (1.0 + self.rng.gauss(0.0, 0.03)))
        self.dormir(duree + 0.4)
        l1 = self._ligne()
        return {"touche": touche, "duree_ordre": round(duree, 2), "alarme": alarme,
                "avance_mm": round(math.hypot(self.bx - x0, self.by - y0) * (-1 if recul else 1), 1),
                "rot_roues": round(self.bcap - cap0, 2), "rot_gyro": round(self.bcap - cap0, 2),
                "us_avant": l0["us_mm"], "us_apres": l1["us_mm"], "lb_max": 44, "vide_min": min(l0["vide_g"], l1["vide_g"]),
                "ma_min": -300, "lignes": n, "t0": l0["pc_s"], "t1": l1["pc_s"]}

    # ------------------------------------------------------------ une avance d'un seul tenant, comme Pilote.avance
    def avance(self, dist_mm, marge_mm=400, cap_tol=5.0, lb_repos=150, lb_max=400, vide_min=1500, vide_stop=0, duree_max=25.0):
        l0 = self._ligne()
        refus = self.controle(l0, avance=True, marge_mm=min(marge_mm, dist_mm + 220.0), lb_repos=lb_repos, vide_min=vide_min)
        if refus:
            return {"refus": refus}
        if self.verrou or self.pc[0] or self.pc[1]:                 # le firmware refuse l'ordre
            self.reflexe["refus"] += 1
            self.dormir(0.6)
            return {"touche": "8", "duree_ordre": 0.6, "alarme": None, "raison": "refus du firmware", "avance_mm": 0.0, "rot_gyro": 0.0,
                    "us_avant": l0["us_mm"], "us_apres": l0["us_mm"], "lb_max": 44, "vide_min": l0["vide_g"], "lignes": 2}
        x0, y0, cap0, t0 = self.bx, self.by, self.bcap, self.t
        v = min(self.reglage + 21.0, 147.0)                          # vitesses réelles mesurées le 2026-11-10
        dt = 0.05
        alarme = raison = None
        l = l0
        while not (alarme or raison):
            derive = 0.004 * v * dt * (1.0 + self.rng.gauss(0.0, 0.5))                                   # tire à gauche : 4° par mètre
            self._tourner(math.radians(derive))
            self.rot_dps = derive / dt
            ds = v * dt
            P2 = np.array([self.x + ds * math.cos(self.th), self.y + ds * math.sin(self.th)])
            c = self.monde.contact(P2)
            if c is not None:
                rel = (c - self.th + math.pi) % (2 * math.pi) - math.pi
                if abs(rel) < math.radians(100):
                    self.pc = [1 if rel > -0.35 else 0, 1 if rel < 0.35 else 0]
                    self.verrou = True
                    self.reflexe["arrets"] += 1
                    self.contacts.append((float(P2[0]), float(P2[1])))
                    alarme = "pare-chocs " + ("gauche" if self.pc[0] else "") + (" droit" if self.pc[1] else "")
                    break
            self._avancer(ds)
            self.dormir(dt)
            l = self._ligne()
            self.rot_dps = 0.0
            alarme = self.alarme(l, lb_max=lb_max, vide_stop=vide_stop)
            fait = math.hypot(self.bx - x0, self.by - y0)
            if alarme:
                break
            if fait >= dist_mm - 18.0:
                raison = "distance"
            elif abs(self.bcap - cap0) > cap_tol:
                raison = "cap"
            elif 0 < l["us_mm"] < min(marge_mm, dist_mm - fait + 220.0):
                raison = f"obstacle à {l['us_mm']:.0f} mm devant"
            elif self.t - t0 > duree_max:
                raison = "durée"
        if not alarme:                                               # le temps que l'ordre d'arrêt arrive
            P2 = np.array([self.x + 0.1 * v * math.cos(self.th), self.y + 0.1 * v * math.sin(self.th)])
            if self.monde.contact(P2) is None:
                self._avancer(0.1 * v)
        self.dormir(0.4)
        l1 = self._ligne()
        return {"touche": "8", "duree_ordre": round(self.t - t0, 2), "alarme": alarme, "raison": raison,
                "avance_mm": round(math.hypot(self.bx - x0, self.by - y0), 1), "rot_gyro": round(self.bcap - cap0, 2),
                "us_avant": l0["us_mm"], "us_apres": l1["us_mm"], "lb_max": 44, "vide_min": min(l0["vide_g"], l1["vide_g"]),
                "lignes": int((self.t - t0) / dt), "t0": l0["pc_s"], "t1": l1["pc_s"]}

    # ------------------------------------------------------------ liaison avec le cerveau
    def touche(self, c):
        if c == "5" and not (self.pc[0] or self.pc[1]):
            self.verrou = False
        return "ok"

    def vitesse(self, v):
        self.reglage = int(v)
        return "ok"

    def etat(self):
        self.reflexe["verrou"] = self.verrou
        return {"driving": False, "speed": self.reglage,
                "robot": {"ok": True, "q": int(self.q), "qmax": 2068, "mode": self.mode, "bump": list(self.pc), "base": False},
                "pose": {"x": round(self.bx), "y": round(self.by), "cap": round(self.bcap, 1)}, "reflexe": dict(self.reflexe)}

    def get(self, chemin, timeout=3.0):
        if chemin.startswith("/api/tour?go=1"):
            v_tour = 30.0
            if "&v=" in chemin:
                v_tour = max(20.0, min(150.0, float(chemin.split("&v=")[1].split("&")[0])))
            self._tour_sur_place(v_tour)
            return json.dumps({"etat": 2, "texte": "rotation"})
        if chemin.startswith("/api/tour"):
            return json.dumps(self.tour)
        if chemin.startswith("/api/state"):
            return json.dumps(self.etat())
        return "{}"

    def _tour_sur_place(self, v_tour=30.0):
        if self.pc[0] or self.pc[1] or self.verrou:
            self.tour = {"etat": 4, "texte": "interrompu", "raison": "pare-chocs enfoncé", "n": 0}
            return
        depart = [round(self.bx), round(self.by), round(self.bcap, 1)]
        self.tours_vrais.append((self.x, self.y, self.th))
        th0 = self.th
        pts = []
        duree = 17.0 * 30.0 / v_tour                             # 380° en 17 s à 30 mm/s ; le capteur mesure 9 fois par seconde
        n = int(150 * 30.0 / v_tour) + self.rng.randrange(6)
        for i in range(n):
            d_cerveau = 380.0 * i / (n - 1)                     # angle compté par le cerveau depuis le départ du tour
            th = th0 + math.radians(d_cerveau * self.k_vrai)
            capteur = np.array([self.x + DX * math.cos(th), self.y + DX * math.sin(th)])
            pts.append([int(round(d_cerveau * 10)), int(round(self.monde.sonar(capteur, th, rng=self.rng)))])
        for _ in range(19):                                      # le journal continue pendant le tour
            self._tourner(math.radians(20.0 * self.k_vrai))
            self.dormir(duree / 19)
            self._ligne()
        self.x += self.rng.gauss(0.0, 3.0)
        self.y += self.rng.gauss(0.0, 3.0)
        self._ligne()
        self.tour = {"etat": 3, "texte": "terminé", "raison": "tour complet", "tourne": 380, "n": n, "roues": 30,
                     "duree_ms": int(duree * 1000), "depart": depart, "points": pts}
