# position_capture.py — enregistre la position et le tracé du robot (firmware v4 et suivants, /api/pose), et les
# obstacles vus par le capteur de distance s'il y en a (firmware v5, /api/carte). Ne commande rien au robot.
# Usage : python roomba694_recherche/code/outils/position_capture.py ADRESSE [DOSSIER]
# Écrit position_AAAAMMJJ_HHMMSS.csv (une ligne par point du tracé, en mm) et .png (vue de dessus : haut = avant du
# robot au départ, gauche = gauche), et affiche le chemin parcouru et l'écart entre la fin et le départ.
import csv
import json
import math
import os
import sys
import time
import urllib.request

if len(sys.argv) < 2:
    sys.exit("usage : python position_capture.py ADRESSE [DOSSIER]")
adr = sys.argv[1]
dossier = sys.argv[2] if len(sys.argv) > 2 else "."


def get(path):
    with urllib.request.urlopen(f"http://{adr}{path}", timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


p = get("/api/pose")
pts = [tuple(q) for q in p["points"]] + [(p["x"], p["y"])]
obst = []
try:
    total, frm = None, 0
    while total is None or frm < total:
        c = get(f"/api/carte?gen={0 if total is None else c['gen']}&from={frm}")
        if total is None:
            frm = c["from"]
        obst += [tuple(q) for q in c["points"]]
        total = c["total"]
        frm += len(c["points"])
        if not c["points"]:
            break
except Exception:
    pass                                           # firmware sans carte des obstacles

nom = os.path.join(dossier, "position_" + time.strftime("%Y%m%d_%H%M%S"))
with open(nom + ".csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["type", "x_mm", "y_mm"])
    for x, y in pts:
        w.writerow(["trace", x, y])
    for x, y in obst:
        w.writerow(["obstacle", x, y])

ecart = math.hypot(p["x"], p["y"])
print(f"{len(pts)} points de tracé, {len(obst)} obstacles ; chemin parcouru {p['dist'] / 1000:.2f} m ; "
      f"position x {p['x']} mm, y {p['y']} mm, cap {p['cap']}° (roues seules : {p['cap_roues']}°) ; "
      f"écart au départ {ecart:.0f} mm" + (f", soit {100 * ecart / p['dist']:.1f} % du chemin" if p["dist"] else ""))
print(f"robot soulevé {p['leves']} fois, {p['sauts']} déplacement(s) non compté(s)")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(6.4, 6.4))
if obst:
    ax.scatter([-y / 10 for x, y in obst], [x / 10 for x, y in obst], s=9, color="#eb6834", label="obstacles vus par le capteur")
ax.plot([-y / 10 for x, y in pts], [x / 10 for x, y in pts], color="#2a78d6", lw=2, label="tracé du robot")
ax.plot(0, 0, "o", mfc="none", mec="#52514e", ms=9, label="départ")
ax.plot(-p["y"] / 10, p["x"] / 10, "o", color="#1baf7a", ms=9, label="robot")
ax.set_aspect("equal")
ax.grid(True, color="#e1e0d9")
ax.set_xlabel("vers la gauche  ←   cm   →  vers la droite")
ax.set_ylabel("vers l'avant du départ (cm)")
ax.set_title(f"Position du robot, {time.strftime('%Y-%m-%d %H:%M')} : {p['dist'] / 1000:.2f} m parcourus, écart au départ {ecart / 10:.0f} cm", fontsize=10)
ax.legend(loc="best", fontsize=8)
fig.tight_layout()
fig.savefig(nom + ".png", dpi=110)
print("fichiers :", nom + ".csv", nom + ".png")
