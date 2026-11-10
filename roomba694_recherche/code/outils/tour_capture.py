# tour_capture.py — lit le « tour sur place » du robot (firmware roomba694_wifi, fichier tour.ino) et le dessine.
#
# Pendant un tour sur place, le robot tourne sur lui-même et le capteur de distance, droit devant, mesure une distance
# tous les 3° environ. Chaque mur vu de face donne un palier (un creux à fond plat) dans la courbe distance / direction :
# la hauteur du palier est la distance du mur, son milieu la direction du mur.
#
# Usage :
#   python roomba694_recherche/code/outils/tour_capture.py ADRESSE [DOSSIER]        lit et dessine le dernier tour
#   python roomba694_recherche/code/outils/tour_capture.py ADRESSE [DOSSIER] --go   LANCE un tour, puis le dessine
# ATTENTION : --go fait tourner le robot sur lui-même (mode Safe requis, robot au sol, rien autour, aucun câble).
# Sans --go, le script ne fait que lire : aucun ordre n'est envoyé au robot.
# Sorties dans DOSSIER (par défaut roomba694_recherche/mesures) : tour_AAAAMMJJ_HHMMSS.csv et .png.
# Dépendances : Python 3, numpy, matplotlib.
import json
import os
import statistics
import sys
import time
import urllib.request

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def get(base, path, timeout=5):
    with urllib.request.urlopen(base + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def paliers(deg, cm, tol_cm=3.0, largeur_min=10.0, n_min=4):
    """Suites de mesures voisines à distance presque constante : candidats « mur vu de face ».
    Renvoie une liste de (direction du milieu, distance médiane, largeur en degrés, nombre de mesures)."""
    out, i, n = [], 0, len(deg)
    while i < n:
        if cm[i] <= 0:
            i += 1
            continue
        j, vals = i, [cm[i]]
        while j + 1 < n and cm[j + 1] > 0 and deg[j + 1] - deg[j] < 12 and abs(cm[j + 1] - statistics.median(vals)) <= tol_cm + 0.01 * vals[0]:
            j += 1
            vals.append(cm[j])
        if deg[j] - deg[i] >= largeur_min and len(vals) >= n_min:
            out.append(((deg[i] + deg[j]) / 2, statistics.median(vals), deg[j] - deg[i], len(vals)))
        i = j + 1
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    go = "--go" in sys.argv
    if not args:
        print(__doc__ or "usage : tour_capture.py ADRESSE [DOSSIER] [--go]")
        return 2
    base = "http://" + args[0]
    dossier = args[1] if len(args) > 1 else os.path.join("roomba694_recherche", "mesures")
    os.makedirs(dossier, exist_ok=True)

    if go:
        t = get(base, "/api/tour?go=1")
        if t["etat"] == 4:
            print("Tour refusé par le robot :", t["raison"])
            return 1
        print("Tour lancé :", t["texte"])
        fin = time.time() + 50
        dernier = -1
        while time.time() < fin:
            time.sleep(0.5)
            try:
                t = get(base, "/api/tour")
            except Exception as e:  # la carte peut manquer une réponse pendant la rotation
                print("  pas de réponse :", e)
                continue
            if int(t["tourne"] // 45) != dernier:
                dernier = int(t["tourne"] // 45)
                print(f"  {t['texte']} : {t['tourne']:.0f}°, {t['n']} mesures")
            if t["etat"] in (3, 4):
                break
    else:
        t = get(base, "/api/tour")

    print(f"État : {t['texte']} ; rotation {t['tourne']:.0f}° en {t['duree_ms'] / 1000:.1f} s ; {t['n']} mesures ; raison : {t['raison'] or '-'}")
    pts = sorted(t["points"])
    if len(pts) < 5:
        print("Pas assez de mesures pour un dessin.")
        return 1
    deg = [p[0] / 10.0 for p in pts]
    cm = [p[1] / 10.0 for p in pts]          # 0 = rien à portée

    nom = os.path.join(dossier, time.strftime("tour_%Y%m%d_%H%M%S"))
    with open(nom + ".csv", "w", encoding="utf-8") as f:
        f.write("direction_deg,distance_cm\n")
        for d, c in zip(deg, cm):
            f.write(f"{d:.1f},{c:.1f}\n")

    pal = paliers(deg, cm)
    vus = [(d, c) for d, c in zip(deg, cm) if c > 0]
    rien = [d for d, c in zip(deg, cm) if c <= 0]
    portee = max(100.0, min(400.0, max(c for _, c in vus) * 1.1)) if vus else 400.0

    fig = plt.figure(figsize=(12, 5.4))
    fig.suptitle(f"Tour sur place du {time.strftime('%Y-%m-%d %H:%M')} : {t['tourne']:.0f}° en {t['duree_ms'] / 1000:.1f} s, {t['n']} mesures"
                 + ("" if t["etat"] == 3 else f"  (INTERROMPU : {t['raison']})"), fontsize=12, weight="bold")

    a1 = fig.add_subplot(1, 2, 1, projection="polar")
    a1.set_theta_zero_location("N")          # 0° = direction du robot au départ, en haut
    a1.set_theta_direction(1)                # positif = vers la gauche (sens anti-horaire)
    if vus:
        coul = ["#d62728" if d >= 360 else "#1f77b4" for d, _ in vus]
        a1.scatter(np.radians([d for d, _ in vus]), [c for _, c in vus], s=14, c=coul)
    if rien:
        a1.scatter(np.radians(rien), [portee] * len(rien), s=10, c="#bbbbbb", marker="x")
    a1.set_ylim(0, portee)
    a1.set_title("Vue de dessus : le robot est au centre, il regardait vers le haut au départ\n"
                 "(bleu : premier tour ; rouge : recouvrement après 360° ; croix grises : rien à portée)", fontsize=9)

    a2 = fig.add_subplot(1, 2, 2)
    if vus:
        a2.plot([d for d, _ in vus], [c for _, c in vus], ".", color="#1f77b4", ms=6)
    if rien:
        a2.plot(rien, [portee * 0.98] * len(rien), "x", color="#bbbbbb", ms=5)
    a2.axvspan(360, max(380, deg[-1]), color="#d62728", alpha=0.08)
    for k, (d0, c0, larg, nb) in enumerate(sorted(pal, key=lambda p: -p[2])[:8]):
        a2.annotate(f"{c0:.0f} cm\nvers {d0:.0f}°", (d0, c0), xytext=(d0, c0 + portee * 0.12), ha="center", fontsize=9, color="#d62728",
                    arrowprops=dict(arrowstyle="->", color="#d62728"))
    a2.set_xlim(-5, max(385, deg[-1] + 5))
    a2.set_ylim(0, portee * 1.25)            # de la place au-dessus pour les étiquettes des paliers
    a2.set_xticks(range(0, 361, 45))
    a2.set_xlabel("direction du capteur depuis le départ (degrés, positif = vers la gauche)")
    a2.set_ylabel("distance mesurée (cm)")
    a2.set_title("Paliers repérés automatiquement (à vérifier) : un mur vu de face donne un palier", fontsize=9)
    a2.grid(alpha=0.3)
    fig.text(0.5, 0.01, "Distances mesurées depuis le capteur, qui n'est pas au centre du robot : le décalage n'est pas encore corrigé.",
             ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.03, 1, 0.94))
    fig.savefig(nom + ".png", dpi=130)
    print("Fichiers :", nom + ".csv", "et", nom + ".png")
    for d0, c0, larg, nb in sorted(pal):
        print(f"  palier : {c0:.0f} cm vers {d0:.0f}° (largeur {larg:.0f}°, {nb} mesures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
