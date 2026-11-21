# paliers_roues.py — à quelles vitesses tournent VRAIMENT les roues du robot pour une vitesse demandée ?
#
#   python paliers_roues.py [DOSSIER_MESURES] [--depuis AAAAMMJJ] [--detail]
#
# Trouvé le 2026-11-21 (journal_wifi.md § 74) : pendant un trajet à 150 mm/s demandés, le robot a gardé 5° d'écart à son
# cap visé pendant dix secondes, les deux roues tournant exactement à la même vitesse. Les compteurs des roues montrent
# que le robot ne prend que des vitesses par paliers (3, 4 ou 5 pas de codeur par période de 15,6 ms : 85, 114, 142 mm/s).
# Une correction de cap qui ne fait pas changer une roue de palier ne fait donc rien.
#
# Cet outil relit les enregistrements (NOM_console.txt : « Mouvement N : avance de X mm à V mm/s au plus », et
# NOM_capteurs.csv : compteurs des deux roues, 20 lignes par seconde) et donne, pour chaque vitesse demandée, les
# vitesses mesurées de chaque roue au milieu de l'avance. Lecture seule ; rien n'est envoyé au robot.
import argparse
import collections
import csv
import glob
import os
import re
import statistics
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PAS_MM = 0.4446
ICI = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser()
p.add_argument("dossier", nargs="?", default=os.path.normpath(os.path.join(ICI, "..", "..", "mesures")))
p.add_argument("--depuis", default="20261113", help="premier jour lu (AAAAMMJJ)")
p.add_argument("--detail", action="store_true", help="une ligne par avance")
a = p.parse_args()

RE_AV = re.compile(r"^(\d+\.\d+)\t\S+\tMouvement (\d+) : avance de (\d+) mm à (\d+) mm/s au plus, cap tenu à ([+-][\d.]+)°")
RE_FIN = re.compile(r"^(\d+\.\d+)\t\S+\tMouvement (\d+) : (-?\d+) mm pour")


def w16(d):
    d &= 0xFFFF
    return d - 65536 if d >= 32768 else d


par_v = collections.defaultdict(list)          # vitesse demandée -> [(roue lente, roue rapide, écart, nom)]
for cons in sorted(glob.glob(os.path.join(glob.escape(a.dossier), "*_console.txt"))):
    m = re.search(r"_(\d{8})_\d{6}_console\.txt$", cons)
    if not m or m[1] < a.depuis:
        continue
    capteurs = cons[:-len("_console.txt")] + "_capteurs.csv"
    if not os.path.exists(capteurs):
        continue
    departs, fins = {}, {}
    with open(cons, encoding="utf-8", errors="replace") as f:
        for x in f:
            q = RE_AV.match(x)
            if q:
                departs[int(q[2])] = (float(q[1]), int(q[3]), int(q[4]))
                continue
            q = RE_FIN.match(x)
            if q and int(q[2]) in departs and int(q[2]) not in fins:
                fins[int(q[2])] = float(q[1])
    if not departs:
        continue
    with open(capteurs, encoding="utf-8", errors="replace") as f:
        L = [(float(l["pc_s"]), int(l["ms"]), int(l["enc_g"]), int(l["enc_d"])) for l in csv.DictReader(f)
             if l.get("pc_s") and l.get("enc_g") not in (None, "")]
    for n, (t0, dist, v) in departs.items():
        t1 = fins.get(n)
        if t1 is None or t1 - t0 < 2.5:
            continue
        S = [l for l in L if t0 + 1.0 <= l[0] <= t1 - 0.8]       # le milieu de l'avance : ni le départ ni le ralentissement
        if len(S) < 12 or S[-1][1] <= S[0][1]:
            continue
        dt = (S[-1][1] - S[0][1]) / 1000.0
        vg = w16(S[-1][2] - S[0][2]) * PAS_MM / dt
        vd = w16(S[-1][3] - S[0][3]) * PAS_MM / dt
        par_v[v].append((min(vg, vd), max(vg, vd), vd - vg, os.path.basename(cons)[:-len("_console.txt")], n))
        if a.detail:
            print("%-40s mouvement %4d : %4d mm à %3d mm/s demandés ; roue G %6.1f, roue D %6.1f mm/s" % (
                os.path.basename(cons)[:-len("_console.txt")], n, dist, v, vg, vd))

print("vitesse demandée | avances | roue la plus lente (médiane) | roue la plus rapide (médiane) | moyenne des deux | en pas par 15,6 ms")
for v in sorted(par_v):
    R = par_v[v]
    lente = statistics.median(r[0] for r in R)
    rapide = statistics.median(r[1] for r in R)
    moy = statistics.median((r[0] + r[1]) / 2 for r in R)
    print("   %3d mm/s      | %5d   | %6.1f mm/s                  | %6.1f mm/s                   | %6.1f mm/s      | %.2f" % (
        v, len(R), lente, rapide, moy, moy / (PAS_MM / 0.015625)))
