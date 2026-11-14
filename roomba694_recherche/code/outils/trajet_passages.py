# trajet_passages.py — fabrique, à partir des passages d'explorer3.py guidés par le plan, le fichier de trajet que
# carte_grille.py sait dessiner (--global) : tours sur place, trajet roulé, contacts, position finale.
#
# Chaque tour sur place donne la position du robot sur le plan (pose) et celle que le cerveau comptait au même instant
# (depart_cerveau). Entre deux tours, le trajet est celui que le cerveau a compté (colonnes x_mm, y_mm du journal),
# tourné et posé sur le tour qui précède. Rien n'est lissé : un saut à l'arrivée sur un tour montre de combien ce tour
# a corrigé la position (ou, comme le 2026-11-14 dans la cuisine, ce que le cerveau a roulé sans le compter pendant
# une de ses absences).
#
# Usage : python trajet_passages.py SORTIE.json PREFIXE LETTRES [--note TEXTE] [--k-gyro 1.0045] [--px-par-m 53]
#                                   [--hauteur 434]
#   LETTRES : lettres des passages dans l'ordre, séparées par des virgules (a,b) ; « - » pour le passage sans lettre
# Le fichier écrit ne contient que des pixels du plan ; à ranger avec le plan (plan_lidar/), hors du dépôt.
import argparse
import csv
import datetime
import json
import math
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("sortie")
p_.add_argument("prefixe")
p_.add_argument("lettres")
p_.add_argument("--note", default="")
p_.add_argument("--k-gyro", type=float, default=1.0045)
p_.add_argument("--px-par-m", type=float, default=53.0)
p_.add_argument("--hauteur", type=float, default=434.0)
a = p_.parse_args()
S, H = a.px_par_m / 1000.0, a.hauteur

with open(a.prefixe + "_capteurs.csv", encoding="utf-8") as f:
    L = [(float(r["pc_s"]), float(r["x_mm"]), float(r["y_mm"]), float(r["cap_pos"])) for r in csv.DictReader(f)]


def px(X, Y):
    return round(X * S, 1), round(H - Y * S, 1)


tours, trajet, contacts = [], [], []
ancre, i0, fin = None, 0, None                       # ancre : (X, Y, C, bx, by, bc) du dernier tour ; i0 : sa ligne du journal
for lettre in a.lettres.split(","):
    nom = a.prefixe + ("" if lettre == "-" else "_" + lettre) + "_stations.json"
    with open(nom, encoding="utf-8") as f:
        J = json.load(f)
    for st in J["stations"]:
        X, Y, C = st["pose"]
        bx, by, bc = st["depart_cerveau"]
        # la ligne du journal où le cerveau comptait cette position : le début du tour
        i1 = next((i for i in range(i0, len(L)) if abs(L[i][1] - bx) <= 1.5 and abs(L[i][2] - by) <= 1.5 and abs(L[i][3] - bc) <= 0.4), None)
        if i1 is None:
            raise SystemExit(f"tour {lettre}{st['nom']} : aucune ligne du journal ne correspond à sa position de départ")
        if ancre is not None:                        # le trajet compté depuis le tour d'avant, posé sur lui
            aX, aY, aC, ax, ay, ac = ancre
            t = math.radians(aC - ac)
            for pc, x, y, c in L[i0:i1 + 1]:
                u, v = px(aX + math.cos(t) * (x - ax) - math.sin(t) * (y - ay), aY + math.sin(t) * (x - ax) + math.cos(t) * (y - ay))
                if not trajet or math.hypot(u - trajet[-1][0], v - trajet[-1][1]) >= 0.8:
                    trajet.append([u, v, round((aC + (c - ac) * a.k_gyro) % 360.0, 1), 0, round(pc, 3)])
        u, v = px(X, Y)
        saut = math.hypot(u - trajet[-1][0], v - trajet[-1][1]) / S if trajet else 0.0
        trajet.append([u, v, round(C % 360.0, 1), 0, round(L[i1][0], 3)])
        tours.append({"passage": lettre, "nom": st["nom"], "genre": st.get("genre", ""), "u": u, "v": v, "heure": st.get("heure", ""),
                      "saut_mm": round(saut)})
        ancre, i0 = (X, Y, C, bx, by, bc), i1
    for c in J.get("contacts", []):
        u, v = px(c[0], c[1])
        contacts.append([u, v, str(c[2]) if len(c) > 2 else "contact", ""])
# après le dernier tour : ce que le cerveau a encore compté
aX, aY, aC, ax, ay, ac = ancre
t = math.radians(aC - ac)
for pc, x, y, c in L[i0:]:
    u, v = px(aX + math.cos(t) * (x - ax) - math.sin(t) * (y - ay), aY + math.sin(t) * (x - ax) + math.cos(t) * (y - ay))
    if math.hypot(u - trajet[-1][0], v - trajet[-1][1]) >= 0.8:
        trajet.append([u, v, round((aC + (c - ac) * a.k_gyro) % 360.0, 1), 0, round(pc, 3)])
    fin = [u, v, round((aC + (c - ac) * a.k_gyro) % 360.0, 1)]
with open(a.sortie, "w", encoding="utf-8") as f:
    json.dump({"px_par_m": a.px_par_m, "n": 0, "graine": 0, "inverse": False, "vraisemblance": 0.0, "note": a.note,
               "tours": tours, "trajet": trajet, "contacts": contacts, "fin": fin}, f, ensure_ascii=False)
metres = sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(trajet, trajet[1:])) / a.px_par_m
print(f"{len(tours)} tours, {len(trajet)} points de trajet ({metres:.1f} m), {len(contacts)} contact(s) ; fin au pixel ({fin[0]:.0f}, {fin[1]:.0f}), cap {fin[2]:.0f}°")
for q in tours:
    h = datetime.datetime.strptime(q["heure"], "%H:%M:%S").strftime("%H h %M") if q["heure"] else ""
    print(f"  tour {q['passage']}{q['nom']} ({q['genre']}) au pixel ({q['u']:.0f}, {q['v']:.0f}) {h} ; saut à l'arrivée : {q['saut_mm']} mm")
print("écrit :", a.sortie)
