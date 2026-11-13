# localiser.py — où est le robot sur le plan, à chaque instant : filtre à particules, pendant que le robot roule.
#
# Ce que les passages du 2026-11-10 ont appris (journal § 28 à § 31) :
#   - le suivi « un tour sur place, une position, une seule hypothèse » dérive : 17 cm et 9° d'erreur médiane, jusqu'à
#     63 cm et 27° ;
#   - le gyroscope du cerveau compte 0,1 à 0,7 % de trop peu selon les passages (0,45 % le soir du 10) : plus d'un degré
#     perdu à chaque tour sur place, 111° sur la soirée ; et il ne compte rien sous 0,3 °/s (zone morte) ;
#   - entre deux tours, le trajet compté par le cerveau est bon : 2° et 1 % d'écart sur 39 avances droites ;
#   - juger chaque lecture du capteur de distance une à une donne un cap faux (le faisceau est plus large que le modèle) ;
#     juger un tour entier par ses paliers, avec plusieurs hypothèses, donne 6,7 cm et 1,8° en temps réel.
# D'où ce filtre :
#   - chaque hypothèse (position, cap, erreur d'échelle du gyroscope, erreur d'échelle des roues) avance à chaque ligne
#     du journal (20 par seconde) avec ce que le cerveau compte ; quand le gyroscope se tait alors que le robot roule,
#     la rotation lente est prise sur les roues ;
#   - une hypothèse ne traverse pas un mur ; un appui du pare-chocs doit tomber près de quelque chose ;
#   - à la fin de chaque tour sur place, les paliers du tour jugent les hypothèses (même note que plan.Plan.localiser).
# Entre deux tours la position est donc tenue par le trajet compté, avec le bon cap ; un tour la resserre.
#
# Repère : celui du plan (plan.py), en millimètres, x vers la droite de l'image, y vers le haut ; cap en degrés, 0 = droite.
# Usage dans un programme :
#     f = Filtre(plan.Plan(IMAGE, 53))
#     f.demarrer(u, v, cap)                   # pixel et cap connus à 15 cm et 8° près (ou f.demarrer_dans(...))
#     f.suivre(lignes_du_journal)             # à chaque fois que de nouvelles lignes arrivent
#     f.debut_tour()                          # juste avant de lancer un tour sur place
#     f.tour(angles_deg, distances_mm)        # à la fin du tour, avec ses mesures (angles comptés depuis le début du tour)
#     e = f.estimation()                      # e["u"], e["v"], e["cap"], e["etalement_mm"], e["etalement_cap"], e["note"]
# Essai sur les enregistrements : research_notes/…/data_analysis/m_rejeu_filtre.py.
import math

import numpy as np

import carto

DX = carto.DX             # le capteur de distance est 27 mm en avant du centre du robot


class Filtre:
    def __init__(self, plan, n=20000, graine=1, k_gyro=1.0045, temperature=0.2, roues_si_muet=True,
                 trajet=(20.0, 0.04, 80.0, 0.15, 0.85), caps=(3.0, 8.0, 20.0, 0.70, 0.95)):
        # trajet : ce qu'on ignore du chemin roulé entre deux tours sur place : (mm, part du chemin) pour le cas courant,
        #          (mm, part du chemin) pour le cas rare (glissement, plan faux), et la part du cas courant ;
        # caps   : la même chose pour le cap : trois écarts-types en degrés et les parts cumulées des deux premiers.
        self.pl, self.s, self.H, self.W = plan, plan.s, plan.H, plan.W
        self.n = int(n)
        self.rng = np.random.default_rng(graine)
        self.k = k_gyro
        self.temp = temperature
        self.roues_si_muet = roues_si_muet
        self.trajet, self.caps = tuple(trajet), tuple(caps)
        self.A, self.mur, self.Cs = plan.A.astype(np.float32), plan.mur, plan.Cs.astype(np.float32)
        self.Dc = (plan.D_chose / plan.s).astype(np.float32)        # distance au mur ou au meuble le plus proche, mm
        self.X = None
        self.ligne = None                                           # dernière ligne du journal intégrée
        self.ref = None                                             # position du cerveau au dernier contrôle des murs
        self.cap_tour = None                                        # cap du cerveau au début du tour en cours
        self.note = 0.0                                             # note du dernier tour à la place retenue
        self.chemin = 0.0
        self.chemin_tour = 0.0                                      # chemin roulé au dernier tour sur place
        self.n_tours = 0

    # ------------------------------------------------------------ départ
    def _etat(self, X, Y, C):
        n = self.n
        self.X, self.Y, self.C = X.astype(np.float32), Y.astype(np.float32), C.astype(np.float32)
        self.kg = self.rng.normal(0.0, 0.002, n).astype(np.float32)       # erreur d'échelle du gyroscope
        self.es = self.rng.normal(0.0, 0.01, n).astype(np.float32)        # erreur d'échelle des roues (glissement)
        self.lw = np.zeros(n, np.float64)
        self.dans_mur = np.zeros(n, bool)
        self.ligne, self.ref, self.cap_tour = None, None, None

    def demarrer(self, u, v, cap, sigma_mm=150.0, sigma_cap=8.0):
        """le robot est près du pixel (u, v), tourné vers cap, à sigma_mm et sigma_cap près"""
        n = self.n
        self._etat(u / self.s + self.rng.normal(0, sigma_mm, n), (self.H - v) / self.s + self.rng.normal(0, sigma_mm, n),
                   cap + self.rng.normal(0, sigma_cap, n))

    def demarrer_dans(self, u0, v0, u1, v1, cap=0.0, tol_cap=180.0):
        """le robot est quelque part dans le rectangle de pixels donné, cap connu à tol_cap près (180 : inconnu)"""
        n = self.n
        sol = self.pl.interieur[int(v0):int(v1) + 1, int(u0):int(u1) + 1] & (self.pl.D_mur[int(v0):int(v1) + 1, int(u0):int(u1) + 1] >= 170.0 * self.s)
        ok = np.argwhere(sol)
        if len(ok) == 0:
            raise ValueError("aucun sol libre dans ce rectangle")
        k = self.rng.integers(0, len(ok), n)
        self._etat((int(u0) + ok[k, 1] + self.rng.uniform(-0.5, 0.5, n)) / self.s, (self.H - (int(v0) + ok[k, 0] + self.rng.uniform(-0.5, 0.5, n))) / self.s,
                   cap + self.rng.uniform(-tol_cap, tol_cap, n))

    # ------------------------------------------------------------ lecture du plan pour toutes les hypothèses
    def _lire(self, img, X, Y, dehors=0.0):
        ui = np.rint(X * self.s).astype(np.int32)
        vi = np.rint(self.H - Y * self.s).astype(np.int32)
        ok = (ui >= 0) & (ui < self.W) & (vi >= 0) & (vi < self.H)
        return np.where(ok, img[np.clip(vi, 0, self.H - 1), np.clip(ui, 0, self.W - 1)], dehors)

    # ------------------------------------------------------------ le trajet compté par le cerveau, ligne après ligne
    def suivre(self, lignes):
        for l in lignes:
            self._une_ligne(l)

    def _une_ligne(self, b):
        a, self.ligne = self.ligne, b
        if a is None or self.X is None:
            return
        dx, dy, dc = b["x_mm"] - a["x_mm"], b["y_mm"] - a["y_mm"], b["cap_pos"] - a["cap_pos"]
        if abs(dx) > 400 or abs(dy) > 400 or abs(dc) > 200:
            return                                                   # saut du journal (cerveau redémarré) : rien à en tirer
        n = self.n
        if dx or dy or dc:
            ca = math.radians(a["cap_pos"])
            av, lat = math.cos(ca) * dx + math.sin(ca) * dy, -math.sin(ca) * dx + math.cos(ca) * dy
            muet = dc == 0 and abs(b.get("rot_dps", 1.0)) < 0.3 and abs(a.get("rot_dps", 1.0)) < 0.3
            if not muet:                                             # (dc nul sans être muet : le journal n'écrit le cap qu'à 0,1° près)
                rot = (self.k + self.kg) * dc + self.rng.normal(0, 0.02 + 0.02 * abs(dc), n)
            elif self.roues_si_muet and not (b.get("pc_g", 0) or b.get("pc_d", 0)):
                # gyroscope muet (moins de 0,3 °/s) alors que le robot roule : la rotation lente vient des roues
                dg = ((b.get("enc_g", 0) - a.get("enc_g", 0) + 32768) % 65536) - 32768
                dd = ((b.get("enc_d", 0) - a.get("enc_d", 0) + 32768) % 65536) - 32768
                rot = (dd - dg) * 0.4446 / 235.0 * 57.29578 + self.rng.normal(0, 0.05, n)
            else:
                rot = self.rng.normal(0, 0.02, n)
            cm = np.radians(self.C + 0.5 * rot)
            avn = av * (1.0 + self.es) + self.rng.normal(0, 0.4 + 0.03 * abs(av), n)
            latn = lat + self.rng.normal(0, 0.3 + 0.02 * abs(av), n)
            self.X = (self.X + np.cos(cm) * avn - np.sin(cm) * latn).astype(np.float32)
            self.Y = (self.Y + np.sin(cm) * avn + np.cos(cm) * latn).astype(np.float32)
            self.C = (self.C + rot).astype(np.float32)
            self.chemin += math.hypot(dx, dy)
        # pare-chocs qui vient de s'enfoncer : il y a quelque chose là
        if (b.get("pc_g", 0) or b.get("pc_d", 0)) and not (a.get("pc_g", 0) or a.get("pc_d", 0)):
            cote = 40.0 if (b.get("pc_g", 0) and not b.get("pc_d", 0)) else -40.0 if (b.get("pc_d", 0) and not b.get("pc_g", 0)) else 0.0
            t = np.radians(self.C + cote)
            dd = self._lire(self.Dc, self.X + 190.0 * np.cos(t), self.Y + 190.0 * np.sin(t), dehors=400.0)
            self.lw += np.log(0.3 + 0.7 * np.exp(-0.5 * (dd / 130.0) ** 2))
        # tous les 3 cm roulés : une hypothèse qui entre dans un mur du plan perd beaucoup, une fois (le plan a aussi des
        # traits sombres qui ne sont pas des murs : une porte dessinée ouverte, une traînée du relevé dans le couloir)
        if self.ref is None or math.hypot(b["x_mm"] - self.ref[0], b["y_mm"] - self.ref[1]) >= 30.0:
            self.ref = (b["x_mm"], b["y_mm"])
            dans = self._lire(self.mur, self.X, self.Y, dehors=True).astype(bool)
            self.lw += np.where(dans & ~self.dans_mur, math.log(0.08), 0.0)
            self.dans_mur = dans

    # ------------------------------------------------------------ un tour sur place
    def debut_tour(self):
        """à appeler juste avant de lancer un tour sur place : retient le cap du cerveau à cet instant"""
        self.cap_tour = self.ligne["cap_pos"] if self.ligne is not None else None

    def tour(self, angles, distances):
        """Le tour qui vient de finir juge les hypothèses. angles : degrés depuis le début du tour ; distances : mm (0 = rien).
        Renvoie l'estimation, avec en plus le cap qu'avait le robot au début du tour (« cap_debut »)."""
        S = carto.paliers_souples(np.asarray(angles, float), np.asarray(distances, float))
        pal = [(mid, dist, larg) for mid, dist, larg, nb in S]
        tourne = (self.ligne["cap_pos"] - self.cap_tour) if (self.cap_tour is not None and self.ligne is not None) else 0.0
        # Ce qu'on ne sait pas du trajet depuis le tour précédent : glissement, cap. Large exprès : le rejeu de la soirée du
        # 2026-11-10 est deux fois plus juste ainsi (6,7 cm) qu'avec un trajet tenu pour sûr à 1° près (11 cm), parce que
        # le plan lui-même n'est juste qu'à 10 ou 20 cm d'une pièce à l'autre et que c'est sur le plan qu'on se repère.
        n = self.n
        L = self.chemin - self.chemin_tour
        self.chemin_tour = self.chemin
        tir = self.rng.random(n)
        t0, t1, t2, t3, tp = self.trajet
        sig = np.where(tir < tp, t0 + t1 * L, t2 + t3 * L)
        self.X = (self.X + self.rng.normal(0, 1.0, n) * sig).astype(np.float32)
        self.Y = (self.Y + self.rng.normal(0, 1.0, n) * sig).astype(np.float32)
        tir = self.rng.random(n)
        c0_, c1_, c2_, p0_, p1_ = self.caps
        self.C = (self.C + self.rng.normal(0, 1.0, n) * np.where(tir < p0_, c0_, np.where(tir < p1_, c1_, c2_))).astype(np.float32)
        c0 = self.C - (self.k + self.kg) * tourne                    # cap de chaque hypothèse au début du tour
        if pal:
            nt = self._note(pal, self.X, self.Y, c0)
            self.lw += nt / self.temp
        self._reprendre()
        self.n_tours += 1
        e = self.estimation()
        e["cap_debut"] = (e["cap"] - e["echelle_gyro"] * tourne) % 360.0
        if pal:
            self.note = float(self._note(pal, np.array([e["x"]], np.float32), np.array([e["y"]], np.float32), np.array([e["cap_debut"]], np.float32))[0])
        e["note"] = self.note
        e["paliers"] = len(pal)
        return e

    def _note(self, pal, X, Y, C):
        ang = np.radians(np.array([p[0] for p in pal], np.float32))
        dist = np.array([p[1] for p in pal], np.float32)
        w = np.array([2.0 if p[2] >= 25 else 1.0 if p[2] >= 15 else 0.5 for p in pal], np.float32)
        c = np.radians(C).astype(np.float32)[:, None]
        t = c + ang[None, :]
        a_ = self._lire(self.A, X[:, None] + dist[None, :] * np.cos(t), Y[:, None] + dist[None, :] * np.sin(t))
        sc = (a_ * w[None, :]).sum(1) / w.sum()
        ra, rd = [], []
        for k in range(len(dist)):                                   # rayons libres : du robot vers le palier, sans les 25 derniers cm
            m = max(2, int((dist[k] - 250.0) / 100.0))
            f = np.arange(1, m) / m * max(0.0, dist[k] - 250.0)
            ra.append(np.full(len(f), ang[k]))
            rd.append(f)
        ra, rd = np.concatenate(ra).astype(np.float32), np.concatenate(rd).astype(np.float32)
        if len(rd):
            tr = c + ra[None, :]
            m_ = self._lire(self.mur, X[:, None] + rd[None, :] * np.cos(tr), Y[:, None] + rd[None, :] * np.sin(tr))
            sc = sc - 1.5 * m_.mean(1)
        return sc - self._lire(self.Cs, X, Y, dehors=2.0)

    def _reprendre(self):
        """rééchantillonnage après un tour"""
        n = self.n
        w = np.exp(self.lw - self.lw.max())
        p = w / w.sum()
        idx = np.minimum(np.searchsorted(np.cumsum(p), (self.rng.random() + np.arange(n)) / n), n - 1)
        self.X = (self.X[idx] + self.rng.normal(0, 12.0, n)).astype(np.float32)
        self.Y = (self.Y[idx] + self.rng.normal(0, 12.0, n)).astype(np.float32)
        self.C = ((self.C[idx] + self.rng.normal(0, 0.8, n)) % 360.0).astype(np.float32)
        self.dans_mur = self.dans_mur[idx]
        self.kg = (self.kg[idx] + self.rng.normal(0, 0.0002, n)).astype(np.float32)
        self.es = (self.es[idx] + self.rng.normal(0, 0.001, n)).astype(np.float32)
        self.lw = np.zeros(n, np.float64)

    # ------------------------------------------------------------ le résultat
    def estimation(self):
        w = np.exp(self.lw - self.lw.max())
        w = w / w.sum()
        # la place retenue : le centre du gros du nuage (médianes), pas la moyenne, pour ne pas tomber entre deux groupes
        o = np.argsort(self.X)
        x = float(self.X[o][min(self.n - 1, np.searchsorted(np.cumsum(w[o]), 0.5))])
        o = np.argsort(self.Y)
        y = float(self.Y[o][min(self.n - 1, np.searchsorted(np.cumsum(w[o]), 0.5))])
        cr = np.radians(self.C)
        sn, cs = float((w * np.sin(cr)).sum()), float((w * np.cos(cr)).sum())
        cap = math.degrees(math.atan2(sn, cs)) % 360.0
        etal = math.sqrt(float((w * ((self.X - x) ** 2 + (self.Y - y) ** 2)).sum()))
        etal_cap = math.degrees(math.sqrt(max(0.0, -2.0 * math.log(max(1e-9, min(1.0, math.hypot(sn, cs)))))))
        return {"x": x, "y": y, "cap": cap, "u": x * self.s, "v": self.H - y * self.s, "etalement_mm": etal, "etalement_cap": etal_cap,
                "note": self.note, "echelle_gyro": self.k + float((w * self.kg).sum()), "echelle_roues": 1.0 + float((w * self.es).sum())}
