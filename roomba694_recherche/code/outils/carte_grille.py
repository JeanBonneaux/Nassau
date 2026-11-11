# carte_grille.py — la carte quadrillée de l'appartement : le plan, des cases de 50 cm nommées comme aux échecs
# (grille.py), et ce que le robot a relevé lui-même (trajet roulé, tours sur place, tapis, obstacles touchés).
#
# Usage : python carte_grille.py PLAN.png SORTIE_DIR [--px-par-m 53] [--zones IMAGE] [--base U,V]
#                                [--global "F1.json;F2.json"] [--reperes FICHIER.json] [--nom carte_grille]
#                                [--robot-heure "19 h 10"]
#   --zones   : le plan où l'utilisateur a marqué en rouge les pièces inaccessibles
#   --global  : résultats de data_analysis/l_localisation_globale.py (tours, trajet, contacts, position finale) ;
#               le robot est dessiné à la position finale du dernier fichier
#   --reperes : liste JSON de {"u":, "v":, "texte":} — remarques numérotées portées sur la carte
# Écrit NOM.png (vue d'ensemble) et NOM_1.png, NOM_2.png, NOM_3.png (trois agrandissements, le nom de chaque case écrit
# dans son coin). Le plan est une donnée privée : SORTIE_DIR doit être hors du dépôt (plan_lidar/).
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grille as grille_mod  # noqa: E402
import plan as plan_mod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("plan")
p_.add_argument("sortie")
p_.add_argument("--px-par-m", type=float, default=53.0)
p_.add_argument("--zones", default="")
p_.add_argument("--base", default="")
p_.add_argument("--global", dest="glob", default="")
p_.add_argument("--reperes", default="")
p_.add_argument("--nom", default="carte_grille")
p_.add_argument("--robot-heure", default="")
a = p_.parse_args()
PL = plan_mod.Plan(a.plan, a.px_par_m)
GR = grille_mod.Grille(a.px_par_m, PL.W, PL.H)
c, s = GR.c, PL.s
zones = []
if a.zones:                                          # les pièces barrées de rouge par l'utilisateur
    Z = np.asarray(Image.open(a.zones).convert("RGB")).astype(int)
    rouge = (Z[..., 0] > Z[..., 1] + 60) & (Z[..., 0] > Z[..., 2] + 60)
    lab, n = ndimage.label(ndimage.binary_dilation(rouge, iterations=3))
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        if len(xs) >= 400:
            zones.append((int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1))
donnees = []
for f in a.glob.split(";"):
    if f.strip():
        with open(f, encoding="utf-8") as fh:
            donnees.append(json.load(fh))
reperes = []
if a.reperes:
    with open(a.reperes, encoding="utf-8") as fh:
        reperes = json.load(fh)
base = tuple(float(v) for v in a.base.split(",")) if a.base else None
robot = donnees[-1]["fin"] if donnees else None

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle

SURF, ENCRE, DOUX = "#fcfcfb", "#0b0b0b", "#52514e"
BLEU, ORANGE, VERT, ROUGE, VIOLET, GRILLE = "#2a78d6", "#eb6834", "#1a8f4c", "#d03b3b", "#7a5cc4", "#3b6fb5"
n_tours = sum(len(D["tours"]) for D in donnees)
metres = 0.0
for D in donnees:
    T = np.array([[p[0], p[1]] for p in D["trajet"]])
    metres += float(np.sum(np.hypot(np.diff(T[:, 0]), np.diff(T[:, 1])))) / a.px_par_m


def dessiner(fichier, col0, col1, k, dans_cases, titre):
    u0, u1 = (col0 - 1) * c, min(float(PL.W), col1 * c)
    ml, mr, mt, mb = 50, 50, 84, 44
    Wf, Hf = (u1 - u0) * k + ml + mr, PL.H * k + mt + mb
    fig = plt.figure(figsize=(Wf / 100.0, Hf / 100.0), dpi=100, facecolor=SURF)
    ax = fig.add_axes([ml / Wf, mb / Hf, (u1 - u0) * k / Wf, PL.H * k / Hf])
    e = k / 2.2                                                     # échelle des traits et des marques
    ax.imshow(255 - (255 - PL.G) * 0.8, cmap="gray", vmin=0, vmax=255, interpolation="bilinear", zorder=0)
    for x0, y0, x1, y1 in zones:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=(0.82, 0.23, 0.23, 0.10), edgecolor=(0.82, 0.23, 0.23, 0.75), lw=1.3, zorder=1))
        if u0 + 45 <= (x0 + x1) / 2 <= u1 - 45:                  # l'étiquette seulement si elle tient dans le cadre
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, "inaccessible", ha="center", va="center", fontsize=11, color=DOUX, zorder=7, clip_on=True)
    # le quadrillage
    for j in range(GR.n_col + 1):
        x = min(j * c, PL.W - 0.5)
        fort = j % 5 == 0
        ax.plot([x, x], [0, PL.H], "-", color=GRILLE, lw=1.0 if fort else 0.5, alpha=0.55 if fort else 0.30, zorder=2)
    for i in range(GR.n_lig + 1):
        y = min(i * c, PL.H - 0.5)
        fort = i % 5 == 0
        ax.plot([0, PL.W], [y, y], "-", color=GRILLE, lw=1.0 if fort else 0.5, alpha=0.55 if fort else 0.30, zorder=2)
    fb = 10 if k < 2.6 else 13
    for j in range(col0 - 1, min(col1, GR.n_col)):
        x = (j * c + min((j + 1) * c, PL.W)) / 2
        ax.text(x, -7 / k, str(j + 1), ha="center", va="bottom", fontsize=fb, color=ENCRE, fontweight="bold", clip_on=False)
        ax.text(x, PL.H + 7 / k, str(j + 1), ha="center", va="top", fontsize=fb, color=ENCRE, fontweight="bold", clip_on=False)
    for i in range(GR.n_lig):
        y0, y1 = i * c, min((i + 1) * c, PL.H)
        if y1 - y0 < 0.45 * c:
            continue
        ax.text(u0 - 10 / k, (y0 + y1) / 2, grille_mod.LETTRES[i], ha="right", va="center", fontsize=fb + 2, color=ENCRE, fontweight="bold", clip_on=False)
        ax.text(u1 + 10 / k, (y0 + y1) / 2, grille_mod.LETTRES[i], ha="left", va="center", fontsize=fb + 2, color=ENCRE, fontweight="bold", clip_on=False)
    if dans_cases:                                                  # le nom de chaque case, dans son coin
        for i in range(GR.n_lig):
            for j in range(col0 - 1, min(col1, GR.n_col)):
                x0, y0 = j * c, i * c
                x1, y1 = min(float(PL.W), x0 + c), min(float(PL.H), y0 + c)
                if y1 - y0 < 0.45 * c or PL.interieur[int(y0):int(math.ceil(y1)), int(x0):int(math.ceil(x1))].mean() < 0.2:
                    continue
                ax.text(x0 + 0.07 * c, y0 + 0.06 * c, f"{grille_mod.LETTRES[i]}{j + 1}", ha="left", va="top", fontsize=7.5, color="#1f3d66", alpha=0.62, zorder=3)
    # ce que le robot a relevé
    for D in donnees:
        T = np.array([[p[0], p[1], p[3]] for p in D["trajet"]])
        sur_tapis = [[T[q, :2], T[q + 1, :2]] for q in range(len(T) - 1) if T[q, 2] and T[q + 1, 2]]
        if sur_tapis:
            ax.add_collection(LineCollection(sur_tapis, colors=VIOLET, linewidths=7.0 * e, alpha=0.30, zorder=3, capstyle="round"))
        ax.plot(T[:, 0], T[:, 1], "-", color=BLEU, lw=1.2 * e, alpha=0.9, zorder=4)
        ax.plot([q["u"] for q in D["tours"]], [q["v"] for q in D["tours"]], "o", color=BLEU, ms=3.6 * e, mfc=SURF, mew=1.0 * e, zorder=5)
        for cu, cv, cote, t in D["contacts"]:
            ax.plot(cu, cv, "x", color=ROUGE, ms=7 * e, mew=2.2 * e, zorder=6)
    if base and u0 <= base[0] <= u1 - 30:
        ax.plot(base[0], base[1], "s", color=VERT, ms=9 * e, mec=SURF, mew=1.2, zorder=8)
        ax.text(base[0] + 8, base[1] - 1, "base", ha="left", va="center", fontsize=9 + 2 * (k > 2.6), color=ENCRE, zorder=8,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none", alpha=0.85))
    if robot and u0 + 20 <= robot[0] <= u1 - 20:
        r = 170.0 * s
        ax.add_patch(Circle((robot[0], robot[1]), r, facecolor=ORANGE, edgecolor=SURF, lw=1.5, alpha=0.95, zorder=9))
        t = math.radians(robot[2])
        ax.annotate("", xy=(robot[0] + 2.1 * r * math.cos(t), robot[1] - 2.1 * r * math.sin(t)), xytext=(robot[0], robot[1]),
                    arrowprops=dict(arrowstyle="-|>", color=ENCRE, lw=1.6 * e), zorder=10)
        ax.text(robot[0], robot[1] + r + 3, "robot" + (f" ({a.robot_heure})" if a.robot_heure else ""), ha="center", va="top", fontsize=9 + 2 * (k > 2.6), color=ENCRE, zorder=10,
                bbox=dict(boxstyle="round,pad=0.15", fc=SURF, ec="none", alpha=0.85))
    for n_, rp in enumerate(reperes, 1):
        if not u0 + 4 <= rp["u"] <= u1 - 4:                      # hors du cadre de cet agrandissement
            continue
        ax.plot(rp["u"], rp["v"], "o", color=ENCRE, ms=13 * e, mfc=SURF, mew=1.4, zorder=11)
        ax.text(rp["u"], rp["v"], str(n_), ha="center", va="center", fontsize=8.5 * e, color=ENCRE, fontweight="bold", zorder=12)
    # la légende, dans le coin vide du plan (en bas à droite), si ce coin est dans le cadre
    lx0, ly0, lx1, ly1 = PL.W - 408.0, 262.0, PL.W - 6.0, PL.H - 6.0
    if u0 <= lx0 and lx1 <= u1 and (donnees or reperes):
        ax.add_patch(FancyBboxPatch((lx0, ly0), lx1 - lx0, ly1 - ly0, boxstyle="round,pad=0,rounding_size=4", facecolor=SURF, edgecolor="#c9c8c4", lw=1.0, alpha=0.96, zorder=20))
        fl = 9.5 if k < 2.6 else 12
        pas = (ly1 - ly0 - 12.0) / 9.0
        y = ly0 + 6.0 + pas / 2
        x = lx0 + 10.0
        lignes = [("trait", f"trajet roulé par le robot ({metres:.0f} m)"), ("rond", f"tours sur place ({n_tours})"), ("tapis", "tapis ou sol sombre sous le robot"),
                  ("croix", "obstacle touché (pare-chocs)"), ("base", "base de recharge"), ("robot", "robot" + (f" à {a.robot_heure}" if a.robot_heure else "")),
                  ("zone", "pièces inaccessibles (ton dessin)")]
        for genre, texte in lignes:
            if genre == "trait":
                ax.plot([x, x + 16], [y, y], "-", color=BLEU, lw=1.6 * e, zorder=21)
            elif genre == "rond":
                ax.plot(x + 8, y, "o", color=BLEU, ms=4.5 * e, mfc=SURF, mew=1.2 * e, zorder=21)
            elif genre == "tapis":
                ax.plot([x, x + 16], [y, y], "-", color=VIOLET, lw=7.0 * e, alpha=0.30, solid_capstyle="round", zorder=21)
            elif genre == "croix":
                ax.plot(x + 8, y, "x", color=ROUGE, ms=7 * e, mew=2.2 * e, zorder=21)
            elif genre == "base":
                ax.plot(x + 8, y, "s", color=VERT, ms=8 * e, mec=SURF, zorder=21)
            elif genre == "robot":
                ax.plot(x + 8, y, "o", color=ORANGE, ms=10 * e, mec=SURF, zorder=21)
            elif genre == "zone":
                ax.add_patch(Rectangle((x, y - 4.5), 16, 9, facecolor=(0.82, 0.23, 0.23, 0.10), edgecolor=(0.82, 0.23, 0.23, 0.75), lw=1.0, zorder=21))
            ax.text(x + 24, y, texte, ha="left", va="center", fontsize=fl, color=ENCRE, zorder=21)
            y += pas
        ax.plot([x, x + a.px_par_m], [y + 2, y + 2], "-", color=ENCRE, lw=2.2 * e, zorder=21)
        for q in (0.0, 0.5, 1.0):
            ax.plot([x + q * a.px_par_m] * 2, [y - 1.5, y + 5.5], "-", color=ENCRE, lw=1.2 * e, zorder=21)
        ax.text(x + a.px_par_m + 8, y + 2, "1 m = 2 cases", ha="left", va="center", fontsize=fl, color=ENCRE, zorder=21)
        # les directions
        bx, by = x + 142.0, y + 6.0
        for dx, dy, mot, ha, va in ((1, 0, "droite", "left", "center"), (-1, 0, "gauche", "right", "center"), (0, -1, "haut", "center", "bottom"), (0, 1, "bas", "center", "top")):
            ax.annotate("", xy=(bx + 11 * dx, by + 9 * dy), xytext=(bx, by), arrowprops=dict(arrowstyle="-|>", color=DOUX, lw=1.2 * e), zorder=21)
            ax.text(bx + 14 * dx, by + 11.5 * dy, mot, ha=ha, va=va, fontsize=fl - 1, color=DOUX, zorder=21)
        # les remarques numérotées
        x2 = lx0 + 212.0
        y = ly0 + 6.0 + pas / 2
        for n_, rp in enumerate(reperes, 1):
            ax.plot(x2 + 6, y, "o", color=ENCRE, ms=12 * e, mfc=SURF, mew=1.2, zorder=21)
            ax.text(x2 + 6, y, str(n_), ha="center", va="center", fontsize=8 * e, color=ENCRE, fontweight="bold", zorder=22)
            lignes_t = rp["texte"].split("\n")
            for q, lt in enumerate(lignes_t):
                ax.text(x2 + 17, y + q * pas * 0.82, lt, ha="left", va="center", fontsize=fl - 0.5, color=ENCRE, zorder=21)
            y += pas * (0.82 * len(lignes_t) + 0.42)
    ax.set_xlim(u0, u1)
    ax.set_ylim(PL.H, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    for cote in ("top", "right", "left", "bottom"):
        ax.spines[cote].set_color("#8a8a86")
        ax.spines[cote].set_linewidth(0.8)
    fig.text(ml / Wf, 1 - 26 / Hf, titre, ha="left", va="center", fontsize=13 if k < 2.6 else 14, color=ENCRE, fontweight="bold")
    exemple = GR.nom(robot[0], robot[1]) if robot else "K20"
    fig.text(ml / Wf, 1 - 48 / Hf, f"Une case = 50 cm. Nom d'une case : la lettre de sa ligne puis le numéro de sa colonne — par exemple {exemple}"
             + (", où est le robot." if robot else "."), ha="left", va="center", fontsize=10.5 if k < 2.6 else 11.5, color=DOUX)
    fig.savefig(fichier, dpi=100, facecolor=SURF)
    plt.close(fig)
    print("dessin :", fichier)


os.makedirs(a.sortie, exist_ok=True)
dessiner(os.path.join(a.sortie, a.nom + ".png"), 1, GR.n_col, 2.2, False, "Carte quadrillée de l'appartement — vue d'ensemble")
tiers = [(1, 18), (15, 32), (29, GR.n_col)]
for n_, (c0, c1) in enumerate(tiers, 1):
    dessiner(os.path.join(a.sortie, f"{a.nom}_{n_}.png"), c0, c1, 3.0, True, f"Carte quadrillée — agrandissement {n_}/3 : colonnes {c0} à {c1}")
if base:
    print("base :", GR.nom(*base))
if robot:
    print("robot :", GR.nom(robot[0], robot[1]), "tourné vers", grille_mod.mot_du_cap(robot[2]), f"(cap {robot[2]:.0f}°)")
for n_, rp in enumerate(reperes, 1):
    print(f"repère {n_} : {GR.nom(rp['u'], rp['v'])} — " + rp["texte"].replace("\n", " "))
for D in donnees:
    cases = []
    for q in D["tours"]:
        nm = GR.nom(q["u"], q["v"])
        if not cases or cases[-1] != nm:
            cases.append(nm)
    print("cases des tours sur place :", " ".join(cases))
