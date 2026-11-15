# relance.py — prépare la suite d'un passage d'explorer3.py guidé par le plan : range les fichiers du passage qui vient
# de finir sous une lettre (PREFIXE_LETTRE_stations.json, PREFIXE_LETTRE_explorer3.txt) et calcule où est le robot sur
# le plan, d'après son dernier tour sur place (déjà dans le repère du plan) et ce que le cerveau a compté depuis.
# Affiche la valeur à donner à --depart-plan.
#
# Usage : python relance.py ADRESSE PREFIXE LETTRE [--px-par-m 53] [--hauteur 434] [--k-gyro 1.0045]
import argparse
import json
import math
import os
import time
import urllib.request


def ranger(src, dst):
    """Range un fichier du passage sous sa lettre. Sous Windows le renommage échoue tant qu'un autre programme tient le
    fichier ouvert (un outil qui le suit en direct, le temps d'une lecture) : cinq secondes d'essais, puis un message
    clair. La commande peut être relancée telle quelle : elle reprend là où elle s'est arrêtée."""
    for _ in range(25):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            time.sleep(0.2)
    raise SystemExit(f"{os.path.basename(src)} : un autre programme garde ce fichier ouvert, impossible de le ranger sous le nom "
                     f"{os.path.basename(dst)}. Relancer cette commande quand il l'aura lâché.")


p_ = argparse.ArgumentParser()
p_.add_argument("adresse")
p_.add_argument("prefixe")
p_.add_argument("lettre")
p_.add_argument("--px-par-m", type=float, default=53.0)
p_.add_argument("--hauteur", type=float, default=434.0, help="hauteur de l'image du plan, pixels")
p_.add_argument("--k-gyro", type=float, default=1.0045)
a = p_.parse_args()
for suffixe in ("_stations.json", "_explorer3.txt"):
    if os.path.exists(a.prefixe + suffixe):
        ranger(a.prefixe + suffixe, a.prefixe + "_" + a.lettre + suffixe)
with open(a.prefixe + "_" + a.lettre + "_stations.json", encoding="utf-8") as f:
    J = json.load(f)
st = J["stations"][-1]
X, Y, C = st["pose"]
bx, by, bc = st["depart_cerveau"]
e = json.loads(urllib.request.urlopen(f"http://{a.adresse}/api/state", timeout=5).read().decode("utf-8", "replace"))
x, y, c = e["pose"]["x"], e["pose"]["y"], e["pose"]["cap"]
ang = math.radians(C - bc)
Xn = X + math.cos(ang) * (x - bx) - math.sin(ang) * (y - by)
Yn = Y + math.sin(ang) * (x - bx) + math.cos(ang) * (y - by)
s = a.px_par_m / 1000.0
r = e["robot"]
print(f"robot : mode {r.get('mode')}, pare-chocs {r.get('bump')}, roues levées {r.get('drop')}, batterie {r.get('q')} mAh, devant {e['radar']['front_mm']} mm ;"
      f" dernier tour {st['nom']} au pixel ({X * s:.0f}, {a.hauteur - Y * s:.0f}), robot à {math.hypot(x - bx, y - by):.0f} mm de lui")
print(f"DEPART={Xn * s:.1f},{a.hauteur - Yn * s:.1f},{(C + (c - bc) * a.k_gyro) % 360:.1f}")
