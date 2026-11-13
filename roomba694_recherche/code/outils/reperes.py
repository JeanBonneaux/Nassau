# reperes.py — se recaler sur les endroits déjà vus : les « repères ».
#
# Constat du 2026-11-13 (journal_wifi.md § 38) : le filtre de localiser.py pose chaque tour sur place sur le plan à 6 cm
# près en médiane, mais un tour sur six est décalé de 10 à 23 cm, là où le plan ne ressemble pas à ce que le robot voit
# (objet absent du plan, battant de porte). Or deux tours faits presque au même endroit se comparent directement
# (carto.apparier : les mêmes parois vues dans les mêmes directions), à 2 ou 3 cm près, sans le plan.
#
# Un repère = un tour sur place déjà fait : sa position sur le plan, son cap de départ, ses paliers. Ce module
#   - fabrique le fichier des repères à partir des fichiers *_stations.json d'explorer3.py : les tours voisins sont
#     comparés deux à deux, et la position de chacun est corrigée pour que l'ensemble soit cohérent (les tours d'un même
#     endroit gardent en moyenne la position que le filtre leur donnait) ;
#   - pendant un trajet, recale un nouveau tour sur les repères voisins (classe Reperes, utilisée par explorer3.py
#     avec --reperes FICHIER).
#
# Fabrication : python reperes.py SORTIE.json FICHIER_stations.json [FICHIER_stations.json ...] [--sans NOM,NOM]
# Ne sont écrits que les tours confirmés : deux voisins au moins, position corrigée de 12 cm au plus.
#   --tout : garder aussi les tours sans voisin, pour refaire en sens inverse un trajet qu'on vient de faire. Essayé le
#            2026-11-13 (journal_wifi.md § 41) : aucun de ces tours seuls n'a servi au retour, parce qu'un repère seul
#            doit être comparé sur quatre parois (classe Reperes) et que les tours du retour n'en partageaient que trois.
#   --sans : tours à laisser de côté (étiquettes affichées par le programme), par exemple ceux faits pendant que
#            quelque chose d'inhabituel était là
import json
import math
import os
import re
import sys

import numpy as np

import carto

RAYON = 350.0          # mm : deux tours plus proches que cela se comparent


def paliers(mesures):
    m = np.array(mesures, float)
    return [(float(a), float(d), float(l), int(n)) for a, d, l, n in carto.paliers_souples(m[:, 0] / 10.0, m[:, 1])]


def etiquette(fichier, nom):
    b = os.path.basename(fichier)
    m = re.search("^([a-z]+)([0-9]+)_.*_([a-z0-9]+)_stations[.]json$", b)
    return (f"{m.group(1)[0]}{m.group(2)}{m.group(3)}{nom}" if m else f"{b[:10]}{nom}")


def comparer(A, B):
    """décalage de B par rapport à A d'après leurs paliers (mm, repère du plan), ou None"""
    r = carto.apparier(A["pal"], A["c"], B["pal"], B["c"])
    if r is None or r[3] != 2 or len(r[2]) < 3:
        return None
    return r[0], r[1], len(r[2])


def construire(fichiers, sans=()):
    T = []
    for f in fichiers:
        for st in json.load(open(f, encoding="utf-8")).get("stations", []):
            if st.get("mesures") and st.get("pose"):
                nom = etiquette(f, st["nom"])
                if nom not in sans:
                    T.append({"nom": nom, "x": float(st["pose"][0]), "y": float(st["pose"][1]), "c": float(st["pose"][2]) % 360.0, "pal": paliers(st["mesures"])})
    paires = []
    for i in range(len(T)):
        for j in range(i + 1, len(T)):
            if math.hypot(T[j]["x"] - T[i]["x"], T[j]["y"] - T[i]["y"]) <= RAYON:
                r = comparer(T[i], T[j])
                if r is not None:
                    paires.append((i, j, (T[j]["x"] - T[i]["x"]) - r[0], (T[j]["y"] - T[i]["y"]) - r[1]))
    # erreur de chaque tour : e_j - e_i = écart de la paire. Moindres carrés pondérés (les paires qui s'écartent comptent
    # moins) ; par groupe de tours reliés entre eux, la moyenne des erreurs est nulle (solution de norme minimale).
    idx = sorted({k for p in paires for k in p[:2]})
    pos = {k: n for n, k in enumerate(idx)}
    ex = ey = np.zeros(len(idx))
    if paires:
        A = np.zeros((len(paires), len(idx)))
        bx, by = np.zeros(len(paires)), np.zeros(len(paires))
        for n, (i, j, dx, dy) in enumerate(paires):
            A[n, pos[j]], A[n, pos[i]], bx[n], by[n] = 1.0, -1.0, dx, dy
        w = np.ones(len(paires))
        for _ in range(8):
            ex, *_ = np.linalg.lstsq(A * w[:, None], bx * w, rcond=None)
            ey, *_ = np.linalg.lstsq(A * w[:, None], by * w, rcond=None)
            w = 1.0 / np.maximum(1.0, np.hypot(A @ ex - bx, A @ ey - by) / 40.0)
    for k, t in enumerate(T):
        e = (float(ex[pos[k]]), float(ey[pos[k]])) if k in pos else (0.0, 0.0)
        t["x0"], t["y0"] = t["x"], t["y"]
        t["x"], t["y"] = t["x"] - e[0], t["y"] - e[1]
        t["corrige"] = round(math.hypot(*e))
        t["voisins"] = sum(1 for p in paires if k in p[:2])
    return T, paires


class Reperes:
    def __init__(self, fichier):
        with open(fichier, encoding="utf-8") as f:
            self.R = json.load(f)["reperes"]
        for r in self.R:
            r["pal"] = [tuple(p) for p in r["pal"]]

    def caler(self, x, y, cap_debut, pal, sans=()):
        """Le tour qui vient d'être fait près de (x, y), cap de départ cap_debut, paliers pal : où est-il d'après les
        repères voisins ? Renvoie (X, Y, nombre de repères d'accord, noms) ou None. Il faut deux repères d'accord à 6 cm
        près, ou un seul comparé sur quatre parois au moins."""
        ici = {"x": x, "y": y, "c": cap_debut % 360.0, "pal": pal}
        cands = []
        for r in self.R:
            if r["nom"] in sans or math.hypot(r["x"] - x, r["y"] - y) > RAYON + 150.0:
                continue
            d = comparer(r, ici)
            if d is not None and math.hypot(d[0], d[1]) <= RAYON + 150.0:
                cands.append((r["x"] + d[0], r["y"] + d[1], d[2], r["nom"]))
        if not cands:
            return None
        mx, my = float(np.median([c[0] for c in cands])), float(np.median([c[1] for c in cands]))
        bons = [c for c in cands if math.hypot(c[0] - mx, c[1] - my) <= 60.0]
        if len(bons) >= 2 or (len(bons) == 1 and len(cands) == 1 and bons[0][2] >= 4):
            return float(np.mean([c[0] for c in bons])), float(np.mean([c[1] for c in bons])), len(bons), [c[3] for c in bons]
        return None

    def cap(self, x, y, cap_debut, pal, rayon=250.0, larg_min=15.0):
        """Le cap lu sur les repères : du même endroit, les mêmes parois se voient dans les mêmes directions. Pour
        chaque repère à moins de `rayon` de (x, y), chaque paroi large est appariée à la paroi du tour vue à la même
        distance (à 120 mm près) et dans une direction voisine (à 20° près) ; l'écart de direction est l'erreur du cap.
        Renvoie (écart médian, premier quartile, troisième quartile, nombre de parois, nombre de repères), en degrés
        (positif : le cap donné est trop grand), ou None s'il y a moins de 6 parois.
        Mesuré le 2026-11-13 (journal_wifi.md § 44) : juste à 3° près en général, assez pour voir une erreur de 5° ou
        plus après un robot reposé à la main ; trop bruité pour corriger le cap à chaque tour."""
        ecarts, n_rep = [], 0
        for r in self.R:
            if math.hypot(r["x"] - x, r["y"] - y) > rayon:
                continue
            n_rep += 1
            for (ma, da, la, na) in r["pal"]:
                if la < larg_min:
                    continue
                c = [(abs(_ecart(cap_debut + mb - (r["c"] + ma))), _ecart(cap_debut + mb - (r["c"] + ma)))
                     for (mb, db, lb, nb) in pal if lb >= larg_min and abs(db - da) < 120.0]
                c = [q for q in c if q[0] <= 20.0]
                if c:
                    ecarts.append(min(c)[1])
        if len(ecarts) < 6:
            return None
        q1, med, q3 = (float(v) for v in np.percentile(ecarts, [25, 50, 75]))
        return med, q1, q3, len(ecarts), n_rep


def _ecart(a):
    return (a + 180.0) % 360.0 - 180.0


def main():
    argv = list(sys.argv[1:])
    sans = ()
    if "--sans" in argv:
        i = argv.index("--sans")
        sans = tuple(argv[i + 1].split(","))
        del argv[i:i + 2]
    tout = "--tout" in argv              # garder aussi les tours sans voisin (pour refaire en sens inverse un trajet tout juste fait)
    if tout:
        argv.remove("--tout")
    if len(argv) < 2:
        sys.exit("usage : python reperes.py SORTIE.json FICHIER_stations.json [...] [--sans NOM,NOM] [--tout]")
    T, paires = construire(argv[1:], sans)
    # Ne sont gardés que les tours confirmés : comparés à deux voisins au moins, et dont la position n'a pas dû être
    # corrigée de plus de 12 cm (au-delà, le tour ou ses voisins sont douteux : mieux vaut ne pas se caler dessus).
    gardes = [t for t in T if (t["voisins"] >= 2 and t["corrige"] <= 120) or tout]
    with open(argv[0], "w", encoding="utf-8") as f:
        json.dump({"reperes": [{"nom": t["nom"], "x": round(t["x"], 1), "y": round(t["y"], 1), "c": round(t["c"], 2), "pal": t["pal"],
                                "corrige_mm": t["corrige"], "voisins": t["voisins"]} for t in gardes]}, f, ensure_ascii=False)
    print(f"{len(gardes)} repères gardés sur {len(T)} tours (écartés : " + (", ".join(f"{t['nom']} ({t['corrige']} mm, {t['voisins']} voisins)" for t in T if t not in gardes) or "aucun") + ")")
    c = sorted(t["corrige"] for t in T if t["voisins"])
    print(f"{len(T)} repères, {len(paires)} paires de tours voisins comparées ; {sum(1 for t in T if not t['voisins'])} repères sans voisin")
    if c:
        print(f"correction de position des repères qui ont des voisins : médiane {c[len(c) // 2]} mm, neuf dixièmes sous {c[int(0.9 * (len(c) - 1))]} mm, la plus grande {c[-1]} mm")
        print("les plus corrigés : " + ", ".join(f"{t['nom']} ({t['corrige']} mm)" for t in sorted(T, key=lambda t: -t["corrige"])[:8]))
    print("écrit :", argv[0])


if __name__ == "__main__":
    main()
