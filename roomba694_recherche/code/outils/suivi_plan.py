# suivi_plan.py — dessine sur le plan de l'appartement où en est une exploration d'explorer3.py.
#
# Lit PREFIXE_stations.json (réécrit par explorer3.py après chaque station) et pose les stations sur le plan, d'après
# l'endroit du plan d'où le robot est parti. Sert à suivre le robot de loin pendant qu'il explore ; le résultat n'est
# qu'aussi juste que ce point de départ (à quelques dizaines de centimètres près tant que la carte n'a pas été recalée
# sur le plan par data_analysis/k_plan_lidar.py).
#
# Le plan est une donnée privée : il est dans plan_lidar/, que le dépôt ignore, et le dessin y va aussi.
#
# Usage : python suivi_plan.py PLAN.png PREFIXE_stations.json --depart U,V,ANGLE [--px-par-m 54] [--sortie FICHIER.png]
#   --depart U,V,ANGLE : pixel du plan où était le robot au lancement, et direction de son avant sur le plan
#                        (degrés, 0 = vers la droite de l'image, 90 = vers le haut)
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("plan")
p_.add_argument("stations")
p_.add_argument("--depart", required=True)
p_.add_argument("--px-par-m", type=float, default=54.0)
p_.add_argument("--sortie", default="")
a = p_.parse_args()
u0, v0, ang = (float(v) for v in a.depart.split(","))
s = a.px_par_m / 1000.0
c, si = math.cos(math.radians(ang)), math.sin(math.radians(ang))


def px(x, y):
    return u0 + s * (x * c - y * si), v0 - s * (x * si + y * c)


with open(a.stations, encoding="utf-8") as f:
    J = json.load(f)
G = np.asarray(Image.open(a.plan).convert("L")).astype(float)
H, W = G.shape
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF, ENCRE, BLEU, ORANGE, VERT, ROUGE = "#fcfcfb", "#0b0b0b", "#2a78d6", "#eb6834", "#1a8f4c", "#d03b3b"
fig, ax = plt.subplots(figsize=(15.5, 6.4), facecolor=SURF)
ax.imshow(255 - (255 - G) * 0.55, cmap="gray", vmin=0, vmax=255, zorder=0)
par_nom = {st["nom"]: st for st in J["stations"]}
noeuds = [st for st in J["stations"] if st.get("genre") not in ("recalage", "retour")]
for st in noeuds:                                   # ce que chaque tour a vu
    m = np.array(st["mesures"], float)
    ok = (m[:, 1] > 0) & (m[:, 0] < 3600)
    t = np.radians(st["pose"][2] + m[ok, 0] / 10.0)
    ax.plot(*px(st["pose"][0] + (m[ok, 1] + 27.0) * np.cos(t), st["pose"][1] + (m[ok, 1] + 27.0) * np.sin(t)), ".", color=BLEU, ms=2.4, alpha=0.4, zorder=2)
for st in noeuds:                                   # l'arbre des trajets
    par = par_nom.get(st.get("de"))
    if par:
        (ua, va), (ub, vb) = px(*par["pose"][:2]), px(*st["pose"][:2])
        ax.plot([ua, ub], [va, vb], "-", color=BLEU, lw=1.4, alpha=0.8, zorder=3)
for st in noeuds:
    u, v = px(*st["pose"][:2])
    coul = VERT if st.get("genre") == "porte" else ROUGE if st.get("genre") == "arrêt" else BLEU
    ax.plot(u, v, "o", color=coul, ms=11, mfc=SURF, mew=1.8, zorder=5)
    ax.text(u, v, st["nom"], color=ENCRE, fontsize=7, ha="center", va="center", zorder=6)
for x, y, g in J.get("contacts", []):
    ax.plot(*px(x, y), "x", color=ROUGE, ms=8, mew=2, zorder=6)
if noeuds:
    u, v = px(*noeuds[-1]["pose"][:2])
    ax.plot(u, v, "o", color=ORANGE, ms=17, mfc="none", mew=2.4, zorder=7)
ax.plot([W * 0.80, W * 0.80 + a.px_par_m], [H * 0.93, H * 0.93], "-", color=ENCRE, lw=3)
ax.text(W * 0.80 + a.px_par_m / 2, H * 0.93 - 8, "1 m", color=ENCRE, fontsize=10, ha="center", va="bottom")
fin = J.get("fin")
ax.set_title(f"Exploration : {len(noeuds)} stations, {len(J.get('recalages', []))} recalages, {len(J.get('contacts', []))} obstacles touchés ou vus devant"
             + (f" — fin : {fin}" if fin else " — en cours (cercle orange : dernière station)"), color=ENCRE, loc="left", fontsize=11)
ax.set_xlim(0, W)
ax.set_ylim(H, 0)
ax.set_xticks([])
ax.set_yticks([])
for cote in ("top", "right", "left", "bottom"):
    ax.spines[cote].set_visible(False)
fig.tight_layout()
sortie = a.sortie or os.path.join(os.path.dirname(os.path.abspath(a.plan)), "suivi_" + os.path.basename(a.stations).replace("_stations.json", "") + ".png")
fig.savefig(sortie, facecolor=SURF, dpi=100)
print("dessin :", sortie)
