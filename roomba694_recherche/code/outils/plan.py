# plan.py — le plan de l'appartement (image vue de dessus issue d'un LiDAR) comme carte de référence.
#
# Sert à deux choses :
#   - poser sur le plan un tour sur place du robot : Plan.localiser() cherche, autour d'une position supposée, la position
#     et le cap pour lesquels les paliers du tour tombent sur des murs ou des meubles du plan et les rayons libres ne
#     traversent aucun mur. C'est ce qui permet d'aligner une carte station par station (data_analysis/k_plan_lidar.py)
#     au lieu de la poser d'un bloc alors que le cap du robot a glissé en route ;
#   - trouver un chemin dans le sol libre du plan entre deux points : Plan.chemin(), qui passe au milieu des portes.
#
# Repère : les pixels de l'image (u vers la droite, v vers le bas). Un cap sur le plan est en degrés, 0 = vers la droite
# de l'image, 90 = vers le haut. L'échelle est en pixels par mètre (54 ± 2 pour le plan du 2026-11-10).
# Le plan lui-même est une donnée privée, gardée hors du dépôt (dossier plan_lidar/).
import math

import numpy as np
from PIL import Image
from scipy import ndimage


class Plan:
    def __init__(self, image, px_par_m):
        self.G = np.asarray(Image.open(image).convert("L")).astype(float)
        self.H, self.W = self.G.shape
        self.px_par_m = float(px_par_m)
        self.s = self.px_par_m / 1000.0                      # pixels par millimètre
        self.mur = self.G < 110                              # traits sombres et épais
        self.chose = self.G < 200                            # murs et meubles
        bouche = ndimage.binary_dilation(self.chose, iterations=5)
        lab, _ = ndimage.label(~bouche)
        bords = set(np.unique(np.r_[lab[0, :], lab[-1, :], lab[:, 0], lab[:, -1]])) - {0}
        self.interieur = ~np.isin(lab, list(bords))
        self.libre = self.interieur & (self.G >= 225)        # sol libre de l'appartement
        self.D_chose = ndimage.distance_transform_edt(~self.chose)
        self.D_mur = ndimage.distance_transform_edt(~self.mur)
        self.A = np.exp(-0.5 * (self.D_chose / max(1.2, 60.0 * self.s)) ** 2)     # proche d'un mur ou d'un meuble : 1
        self.murf = self.mur.astype(float)
        self.Cs = (self.D_mur < 170.0 * self.s).astype(float)                    # trop près d'un mur pour le centre du robot
        self.passe = np.zeros((self.H, self.W), bool)                            # là où le robot est déjà passé : libre, quoi que dise le plan
        self.ferme = np.zeros((self.H, self.W), bool)                            # obstacles rencontrés par le robot
        self.passe_main = np.zeros((self.H, self.W), bool)                       # passages tracés à la main sur le plan : indicatifs
        # Un pas hors des voies déjà roulées coûte ce nombre de pas sur une voie. 1 : aucune préférence (une voie ouvre un
        # passage, sans plus). Avec 3, essayé le 2026-11-13, le chemin repasse où le robot est déjà passé tant que le
        # détour ne triple pas la distance, et ses lignes droites ne quittent plus les voies : boucle de 8,6 m sans
        # contact, mais à 32 mm/s au lieu de 43 à 45 (deux fois plus de petits trajets), et de D12 à C9 le chemin faisait
        # 3,7 m au lieu de 1,7. Le contact qui avait motivé cette préférence (§ 41) venait en fait d'une roue qui patinait
        # (§ 43). Gardé comme réglage (explorer3.py --voies-fortes 3), pas comme conduite par défaut.
        self.hors_voie = 1.0

    def confirmer(self, u, v, pres_mm=80.0, rayon_mm=160.0):
        """Le robot voit quelque chose à cet endroit. Si le plan y montre un mur (à 8 cm près), ce mur est bien là
        aujourd'hui : un passage tracé à la main par-dessus est refermé (le trait vert du 2026-11-10 entrait dans une
        pièce à travers son mur, à 1 m de la vraie porte). Les trajets roulés par le robot, eux, restent ouverts.
        Renvoie 1 si un mur a été confirmé."""
        ui, vi = int(round(u)), int(round(v))
        if not (0 <= vi < self.H and 0 <= ui < self.W) or self.D_mur[vi, ui] > pres_mm * self.s:
            return 0
        r = max(2, int(round(rayon_mm * self.s)))
        a0, a1, b0, b1 = max(0, vi - r), min(self.H, vi + r + 1), max(0, ui - r), min(self.W, ui + r + 1)
        yy, xx = np.mgrid[a0:a1, b0:b1]
        self.passe_main[a0:a1, b0:b1] &= ~((xx - ui) ** 2 + (yy - vi) ** 2 <= r * r)
        return 1

    def ouvrir(self, points, rayon_mm=200.0):
        """Le robot a roulé en ligne droite d'un point au suivant (pixels) : ce couloir est libre, même si le plan y
        montre un trait sombre (porte ouverte le jour du relevé, traînée)."""
        r = max(2, int(round(rayon_mm * self.s)))
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        disque = (xx * xx + yy * yy) <= r * r
        for (u0, v0), (u1, v1) in zip(points, points[1:]):
            n = int(max(2, math.hypot(u1 - u0, v1 - v0)))
            for u, v in zip(np.linspace(u0, u1, n), np.linspace(v0, v1, n)):
                a, b = int(round(v)) - r, int(round(u)) - r
                if a >= 0 and b >= 0 and a + 2 * r + 1 <= self.H and b + 2 * r + 1 <= self.W:
                    self.passe[a:a + 2 * r + 1, b:b + 2 * r + 1] |= disque

    # ------------------------------------------------------------ un tour sur place posé sur le plan
    def _cumul(self, img, u, v, w, R):
        out = np.zeros((2 * R + 1, 2 * R + 1))
        ui, vi = np.round(u).astype(int), np.round(v).astype(int)
        for k in range(len(ui)):
            a, b = vi[k] - R, ui[k] - R
            if a < 0 or b < 0 or a + 2 * R + 1 > self.H or b + 2 * R + 1 > self.W:
                continue
            out += (w[k] if w is not None else 1.0) * img[a:a + 2 * R + 1, b:b + 2 * R + 1]
        return out

    def localiser(self, paliers, u, v, cap, R=14, d_cap=12.0, pas_cap=1.0, retenue=0.25):
        """Position et cap d'un tour sur place sur le plan.
        paliers : liste de (direction en degrés depuis l'avant du robot au départ du tour, distance en mm, largeur en degrés).
        (u, v, cap) : position supposée en pixels et cap supposé de l'avant du robot sur le plan.
        Cherche dans ±R pixels et ±d_cap degrés. retenue : ce que coûte de s'éloigner de la position supposée (un tour
        qui ne voit qu'un mur ne doit pas glisser le long de ce mur). Renvoie (u, v, cap, note, note à la position supposée)."""
        if not paliers:
            return u, v, cap, 0.0, 0.0
        ang = np.array([p[0] for p in paliers], float)
        dist = np.array([p[1] for p in paliers], float)
        w = np.array([2.0 if p[2] >= 25 else 1.0 if p[2] >= 15 else 0.5 for p in paliers])
        du = np.arange(-R, R + 1)
        cout = retenue * (du[None, :] ** 2 + du[:, None] ** 2) / float(R * R)
        v0, u0 = int(round(v)), int(round(u))
        if v0 - R < 0 or u0 - R < 0 or v0 + R + 1 > self.H or u0 + R + 1 > self.W:
            return u, v, cap, 0.0, 0.0                            # trop près du bord de l'image pour chercher
        pres_mur = self.Cs[v0 - R:v0 + R + 1, u0 - R:u0 + R + 1]
        best, note0 = None, None
        for dc in np.arange(-d_cap, d_cap + 1e-6, pas_cap):
            t = np.radians(cap + dc + ang)
            pu, pv = u + self.s * dist * np.cos(t), v - self.s * dist * np.sin(t)
            ru, rv = [], []
            for k in range(len(dist)):                            # rayons libres : de la station vers le palier, sans les 25 derniers cm
                n = max(2, int((dist[k] - 250.0) / 100.0))
                f = np.arange(1, n) / n * max(0.0, dist[k] - 250.0)
                ru.append(u + self.s * f * math.cos(t[k]))
                rv.append(v - self.s * f * math.sin(t[k]))
            ru, rv = np.concatenate(ru), np.concatenate(rv)
            sc = self._cumul(self.A, pu, pv, w, R) / w.sum() - 1.5 * self._cumul(self.murf, ru, rv, None, R) / max(1, len(ru)) - 1.0 * pres_mur
            if abs(dc) < 1e-9:
                note0 = float(sc[R, R])
            sc = sc - cout - retenue * (dc / d_cap) ** 2
            i = np.unravel_index(np.argmax(sc), sc.shape)
            if best is None or sc[i] > best[0]:
                best = (float(sc[i]), u + i[1] - R, v + i[0] - R, cap + dc)
        if best is None:
            return u, v, cap, 0.0, 0.0
        return best[1], best[2], best[3], best[0], (note0 if note0 is not None else 0.0)

    # ------------------------------------------------------------ chemin dans le sol libre
    def chemin(self, depart, arrivee, garde_mm=230.0):
        """Chemin dans le sol libre du plan, de depart à arrivee (pixels), qui reste au large des murs et des meubles et
        passe au milieu des portes. Renvoie la liste des pixels du chemin, ou None s'il n'y en a pas."""
        from skimage.graph import route_through_array
        # Seuls les murs (traits sombres) sont infranchissables, avec leur garde. Le gris (meubles, traînées du relevé
        # dans les couloirs) coûte d'autant plus cher qu'il est sombre : le chemin préfère le sol blanc, mais une
        # traînée claire ne ferme pas un couloir (le premier essai, qui interdisait tout le gris, coupait l'appartement
        # en morceaux).
        g = garde_mm * self.s
        sombre = (255.0 - self.G) / 255.0
        proche = 4.0 * np.clip((3.0 * g - self.D_mur) / (2.0 * g), 0.0, 1.0)      # près d'un mur : plus cher
        cout = self.hors_voie * (1.0 + 300.0 * sombre ** 3 + proche)
        cout[self.D_mur < 0.6 * g] = 1e6
        cout[self.passe] = 1.0                                   # là où le robot a roulé : libre, quoi que dise le plan
        # Le trait tracé à la main ouvre un passage (même à travers un trait sombre : porte fermée le jour du relevé),
        # mais il ne dit pas à quelle distance des murs passer : la distance aux murs continue de compter. Jusqu'au
        # 2026-11-13 le trait valait du sol libre partout, et le chemin le suivait jusque contre un montant de porte et
        # sur le chant d'un battant (journal_wifi.md § 36).
        main = self.passe_main & ~self.passe
        cout[main] = self.hors_voie * (1.0 + proche[main])
        cout[self.ferme] = 1e6
        a, b = (int(round(depart[1])), int(round(depart[0]))), (int(round(arrivee[1])), int(round(arrivee[0])))
        # Le robot est là où il est : autour de lui, tout est franchissable, même si le plan ou un obstacle noté tout près
        # dit le contraire (position connue à 10 cm près). Sans cela, un robot arrêté près d'un mur n'a plus aucun chemin.
        r = int(round(g)) + 2
        yy, xx = np.ogrid[-r:r + 1, -r:r + 1]
        v0, u0 = max(r, min(self.H - r - 1, a[0])), max(r, min(self.W - r - 1, a[1]))
        zone = cout[v0 - r:v0 + r + 1, u0 - r:u0 + r + 1]
        zone[(xx * xx + yy * yy <= r * r) & (zone >= 1e6)] = 20.0
        if cout[b] >= 1e6:                                       # arrivée dans un mur ou sa garde : le point permis le plus proche
            ok = np.argwhere(cout[max(0, b[0] - 15):b[0] + 16, max(0, b[1] - 15):b[1] + 16] < 1e6)
            if len(ok) == 0:
                return None
            k = np.argmin(np.hypot(ok[:, 0] - min(15, b[0]), ok[:, 1] - min(15, b[1])))
            b = (max(0, b[0] - 15) + int(ok[k, 0]), max(0, b[1] - 15) + int(ok[k, 1]))
        try:
            idx, total = route_through_array(cout, a, b, fully_connected=True, geometric=True)
        except Exception:
            return None
        if total >= 1e6:
            return None
        return [(c, r) for r, c in idx]

    def jalons(self, chemin, pas_mm=900.0, mini_mm=450.0):
        """Points d'un chemin à rejoindre l'un après l'autre en ligne droite : le plus loin possible à chaque fois
        (pas_mm au plus à vol d'oiseau, sans traverser un mur), mais jamais à moins de mini_mm du précédent le long du
        chemin, pour ne pas hacher le trajet là où le chemin frôle un mur."""
        if not chemin:
            return []
        out, i = [chemin[0]], 0
        pas, mini = pas_mm * self.s, mini_mm * self.s
        # Avec une préférence pour les voies (hors_voie > 1) : longueur de chemin hors des voies déjà roulées, cumulée le
        # long du chemin ; une ligne droite entre deux points du chemin n'est alors prise que si elle n'ajoute pas de
        # trajet hors voie (6 cm de tolérance), pour ne pas couper les virages d'une voie.
        hv = [0.0]
        for (u0, v0), (u1, v1) in zip(chemin, chemin[1:]):
            dehors = not (self.passe[int(v0), int(u0)] and self.passe[int(v1), int(u1)])
            hv.append(hv[-1] + (math.hypot(u1 - u0, v1 - v0) if dehors else 0.0))
        while i < len(chemin) - 1:
            j = None
            for k in range(len(chemin) - 1, i, -1):
                if (math.hypot(chemin[k][0] - chemin[i][0], chemin[k][1] - chemin[i][1]) <= pas and self._visible(chemin[i], chemin[k])
                        and (self.hors_voie <= 1.0 or self._hors_voie(chemin[i], chemin[k]) <= hv[k] - hv[i] + 60.0 * self.s)):
                    j = k
                    break
            if j is None or (j < len(chemin) - 1 and math.hypot(chemin[j][0] - chemin[i][0], chemin[j][1] - chemin[i][1]) < mini):
                acc, j = 0.0, i
                while j < len(chemin) - 1 and acc < mini:
                    acc += math.hypot(chemin[j + 1][0] - chemin[j][0], chemin[j + 1][1] - chemin[j][1])
                    j += 1
            out.append(chemin[j])
            i = j
        return out

    def _hors_voie(self, a, b):
        """longueur du segment a-b qui n'est pas sur une voie déjà roulée, en pixels"""
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        n = int(max(2, d))
        us, vs = np.linspace(a[0], b[0], n).round().astype(int), np.linspace(a[1], b[1], n).round().astype(int)
        return float((~self.passe[vs, us]).sum()) * d / n

    def _visible(self, a, b):
        """Le segment a-b laisse au centre du robot 17 cm (son rayon) jusqu'au premier trait sombre ; là où le robot est
        déjà passé, tout est tenu pour libre ; sous le trait tracé à la main, le segment peut traverser un trait sombre
        (25 cm au plus), pas le longer. Jusqu'au 2026-11-13 il suffisait de 9 cm : un raccourci en ligne droite pouvait
        frôler un montant de porte (journal_wifi.md § 36 et § 38)."""
        n = int(max(2, math.hypot(b[0] - a[0], b[1] - a[1])))
        us, vs = np.linspace(a[0], b[0], n).round().astype(int), np.linspace(a[1], b[1], n).round().astype(int)
        if self.ferme[vs, us].any():                                 # un obstacle trouvé par le robot : jamais de raccourci dessus
            return False
        pres = (self.D_mur[vs, us] < 170.0 * self.s) & ~self.passe[vs, us]
        if not pres.any():
            return True
        pas = math.hypot(b[0] - a[0], b[1] - a[1]) / max(1, n - 1)           # pixels entre deux points du segment
        return bool(np.all(self.passe_main[vs, us][pres]) and pres.sum() * pas <= 250.0 * self.s)

    def fermer(self, u, v, rayon_mm=250.0):
        """un obstacle rencontré par le robot à cet endroit du plan : les prochains chemins le contournent"""
        r = max(2, int(round(rayon_mm * self.s)))
        yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
        a, b = int(round(v)) - r, int(round(u)) - r
        if a >= 0 and b >= 0 and a + 2 * r + 1 <= self.H and b + 2 * r + 1 <= self.W:
            self.ferme[a:a + 2 * r + 1, b:b + 2 * r + 1] |= (xx * xx + yy * yy) <= r * r
