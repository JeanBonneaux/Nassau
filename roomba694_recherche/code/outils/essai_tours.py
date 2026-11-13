# essai_tours.py — plusieurs tours sur place au même endroit, à des vitesses différentes, pour savoir si un tour
# rapide voit aussi bien qu'un tour lent ; et premier essai du filtre de localiser.py sur le vrai robot.
#
# Le robot ne fait que tourner sur place (tour du firmware, /api/tour?go=1&v=N, 20 à 62 mm/s). Pour chaque tour : sa
# durée, ses paliers, et où le filtre place le robot sur le plan. À la fin, les tours sont comparés entre eux degré par
# degré (le meilleur décalage donne de combien le robot avait tourné entre deux départs ; l'écart médian dit s'ils
# voient la même chose). enregistreur.py doit tourner ; robot en mode Safe, capteur de distance en mode fixe.
#
# Usage : python essai_tours.py ADRESSE PREFIXE --plan PLAN.png --depart U,V,CAP [--px-par-m 53] [--vitesses 30,60]
#                [--flou 250,15]
import argparse
import json
import math
import sys
import time

import numpy as np

import carto
import grille
import localiser
import plan as plan_mod
from pilote import Pilote

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("adresse")
p_.add_argument("prefixe")
p_.add_argument("--plan", required=True)
p_.add_argument("--px-par-m", type=float, default=53.0)
p_.add_argument("--depart", required=True, help="U,V,CAP : pixel du plan et cap supposés du robot")
p_.add_argument("--flou", default="250,15", help="incertitude du départ : mm, degrés")
p_.add_argument("--vitesses", default="30,60")
p_.add_argument("--k-gyro", type=float, default=1.0045)
a = p_.parse_args()
PL = plan_mod.Plan(a.plan, a.px_par_m)
GR = grille.Grille(a.px_par_m, PL.W, PL.H)
u0, v0, c0 = (float(x) for x in a.depart.split(","))
sm, sc = (float(x) for x in a.flou.split(","))
p = Pilote(a.adresse, a.prefixe)
if p.frais() is None:
    raise SystemExit("aucune ligne récente du journal : l'enregistreur tourne-t-il ?")
F = localiser.Filtre(PL, n=20000, k_gyro=a.k_gyro)
F.demarrer(u0, v0, c0, sigma_mm=sm, sigma_cap=sc)
vu = len(p.lignes) - 1
F.suivre(p.lignes[vu:])
tours = []
for v in [int(x) for x in a.vitesses.split(",")]:
    p.lire()
    F.suivre(p.lignes[vu + 1:])
    vu = len(p.lignes) - 1
    cap_avant = p.lignes[-1]["cap_pos"]
    F.debut_tour()
    t0 = time.time()
    t = json.loads(p.get(f"/api/tour?go=1&v={v}"))
    if t.get("etat") not in (1, 2):
        print(f"tour à {v} mm/s refusé : {t.get('raison', t.get('texte'))}")
        break
    while time.time() - t0 < 70:
        time.sleep(0.5)
        t = json.loads(p.get("/api/tour"))
        if t.get("etat") not in (1, 2):
            break
    duree = time.time() - t0
    p.immobile()
    p.lire()
    F.suivre(p.lignes[vu + 1:])
    vu = len(p.lignes) - 1
    if t.get("etat") != 3 or not t.get("points"):
        print(f"tour à {v} mm/s arrêté : {t.get('raison')}")
        break
    m = np.array(t["points"], float)
    e = F.tour(m[:, 0] / 10.0, m[:, 1])
    pal = carto.paliers_souples(m[:, 0] / 10.0, m[:, 1])
    tours.append({"v": v, "duree_s": round(duree, 1), "duree_rotation_ms": t.get("duree_ms"), "n": int(len(m)), "cap_cerveau_avant": cap_avant,
                  "cap_cerveau_apres": p.lignes[-1]["cap_pos"], "points": t["points"],
                  "paliers": [[round(float(x), 1) for x in q[:3]] + [int(q[3])] for q in pal],
                  "filtre": {k: round(float(e[k]), 2) for k in ("u", "v", "cap", "cap_debut", "etalement_mm", "etalement_cap", "note", "echelle_gyro")}})
    print(f"tour à {v} mm/s : {duree:.1f} s en tout, {len(m)} mesures, {len(pal)} paliers ; filtre : case {GR.nom(e['u'], e['v'])}, pixel ({e['u']:.0f}, {e['v']:.0f}),"
          f" cap au début du tour {e['cap_debut']:.0f}° ({grille.mot_du_cap(e['cap_debut'])}), note {e['note']:.2f}, étalement {e['etalement_mm']:.0f} mm et {e['etalement_cap']:.1f}°")
    print("    paliers (direction depuis le début du tour, distance mm, largeur °) : " + " ".join(f"{q[0]:.0f}°:{q[1]:.0f}/{q[2]:.0f}" for q in pal))
    time.sleep(1.0)


def profil(pts):
    m = np.array(pts, float)
    ang, r = m[:, 0] / 10.0, m[:, 1]
    ok = (r > 0) & (ang < 360.0)
    g = np.arange(0.0, 360.0, 1.0)
    return np.minimum(r[ok][np.abs(((ang[ok][None, :] - g[:, None]) + 180) % 360 - 180).argmin(1)], 3000.0)


for i in range(1, len(tours)):
    A, B = profil(tours[0]["points"]), profil(tours[i]["points"])
    cout = np.array([np.median(np.abs(np.roll(B, d) - A)) for d in range(360)])
    d = int(np.argmin(cout))
    attendu = (tours[i]["cap_cerveau_avant"] - tours[0]["cap_cerveau_avant"]) % 360.0
    print(f"tour à {tours[i]['v']} mm/s comparé au tour à {tours[0]['v']} mm/s : même paysage à {cout[d]:.0f} mm près (médiane ; {np.mean(cout):.0f} mm en moyenne pour un décalage quelconque),"
          f" décalage trouvé {d}°, attendu {attendu:.0f}° d'après le gyroscope")
with open(a.prefixe + "_essai_tours.json", "w", encoding="utf-8") as f:
    json.dump({"depart": [u0, v0, c0], "tours": tours}, f, ensure_ascii=False)
print("écrit :", a.prefixe + "_essai_tours.json")
