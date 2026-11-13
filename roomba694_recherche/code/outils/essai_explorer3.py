# essai_explorer3.py — lance explorer3.py dans un monde de simulateur.py, mesure ce qu'il a exploré et dessine le résultat.
#
# Usage : python essai_explorer3.py MONDE DOSSIER_DE_SORTIE [--graine 1] [--stations 40] [--minutes 60] [--sans-dessin]
# Écrit DOSSIER/sim_MONDE_GRAINE_stations.json et DOSSIER/sim_MONDE_GRAINE.png ; imprime le bilan :
# part du sol accessible vue d'au moins une station, nombre de stations, contacts, durée simulée, erreur de position finale.
import argparse
import collections
import math
import os
import sys
import types

import numpy as np

import explorer3
import simulateur as sim


def accessible(monde, pas=100.0):
    """cases où le centre du robot peut se tenir, atteignables depuis le départ (remplissage de proche en proche)"""
    x0, y0, x1, y1 = monde.etendue
    nx, ny = int((x1 - x0) / pas), int((y1 - y0) / pas)
    libre = np.zeros((ny, nx), bool)
    for iy in range(ny):
        for ix in range(nx):
            libre[iy, ix] = monde.libre(np.array([x0 + (ix + 0.5) * pas, y0 + (iy + 0.5) * pas]), marge=20.0)
    vu = np.zeros_like(libre)
    d = (int((monde.depart[0] - x0) / pas), int((monde.depart[1] - y0) / pas))
    file = collections.deque([d])
    vu[d[1], d[0]] = True
    while file:
        ix, iy = file.popleft()
        for jx, jy in ((ix + 1, iy), (ix - 1, iy), (ix, iy + 1), (ix, iy - 1)):
            if 0 <= jx < nx and 0 <= jy < ny and libre[jy, jx] and not vu[jy, jx]:
                vu[jy, jx] = True
                file.append((jx, jy))
    return vu, pas


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    q = argparse.ArgumentParser()
    q.add_argument("monde")
    q.add_argument("dossier")
    q.add_argument("--graine", type=int, default=1)
    q.add_argument("--stations", type=int, default=40)
    q.add_argument("--minutes", type=float, default=60.0)
    q.add_argument("--recalage-m", type=float, default=12.0)
    q.add_argument("--k-gyro", type=float, default=1.0015)
    q.add_argument("--k-vrai", type=float, default=1.0015, help="échelle vraie du gyroscope simulé")
    q.add_argument("--sans-dessin", action="store_true")
    q.add_argument("--plan", action="store_true", help="donner au programme le plan du monde simulé (carte dans le repère du plan)")
    q.add_argument("--cibles", default="", help="avec --plan : points du monde à rejoindre, x,y en mm séparés par des points-virgules")
    q.add_argument("--erreur-depart", default="0,0,0", help="avec --plan : erreur sur la position de départ donnée au programme, dx,dy en mm et cap en degrés")
    q.add_argument("--muet", action="store_true")
    q.add_argument("--fluide", action="store_true", help="avances d'un seul tenant")
    q.add_argument("--sans-filtre", action="store_true", help="avec --plan : ancien recalage à une seule hypothèse")
    q.add_argument("--vitesse", type=int, default=75)
    q.add_argument("--tour-v", type=int, default=30)
    q.add_argument("--tour-tous-les", type=float, default=600.0)
    q.add_argument("--sans-z", action="store_true")
    q.add_argument("--cibles-seules", action="store_true")
    b = q.parse_args()
    monde = sim.Monde(**sim.MONDES[b.monde]())
    robot = sim.RobotSimule(monde, graine=b.graine, echelle_gyro=b.k_vrai)
    prefixe = os.path.join(b.dossier, f"sim_{b.monde}_{b.graine}")
    robot.reglage = b.vitesse
    a = types.SimpleNamespace(adresse="sim", prefixe=prefixe, stations=b.stations, minutes=b.minutes, vitesse=b.vitesse, tour_v=b.tour_v, vide_min=150.0,
                              interdit="", k_gyro=b.k_gyro, recalage_m=b.recalage_m, echecs_max=12, batterie_min=1000, sans_retour=b.cibles_seules,
                              fluide=b.fluide, sans_filtre=b.sans_filtre, tour_tous_les=b.tour_tous_les, sans_z=b.sans_z, cibles_seules=b.cibles_seules, filtre_n=6000)
    a.plan, a.px_par_m, a.depart_plan = "", 50.0, ""
    if b.plan:
        import json as json_
        a.plan = prefixe + "_plan.png"
        px = sim.dessiner_plan(monde, a.plan, a.px_par_m)
        ex_, ey_, ec_ = (float(v) for v in b.erreur_depart.split(","))
        u, v = px(monde.depart[0] + ex_, monde.depart[1] + ey_)
        a.depart_plan = f"{u:.1f},{v:.1f},{monde.depart[2] + ec_:.1f}"
        if os.path.exists(prefixe + "_CIBLES.json"):
            os.remove(prefixe + "_CIBLES.json")
        if b.cibles:
            with open(prefixe + "_CIBLES.json", "w", encoding="utf-8") as f:
                json_.dump({"serie": 1, "cibles": [list(px(*(float(v) for v in c.split(",")))) for c in b.cibles.split(";")]}, f)
    ex = explorer3.Exploration(robot, a)
    if b.muet:
        ex.dire = lambda *x: None
    try:
        ex.explorer()
    finally:
        ex.sauver()
    # ------------------------------------------------------------ bilan
    acc, pas = accessible(monde)
    x0, y0 = monde.etendue[0], monde.etendue[1]
    vues = np.zeros_like(acc)
    iy, ix = np.where(acc)
    for k in range(len(ix)):
        P = np.array([x0 + (ix[k] + 0.5) * pas, y0 + (iy[k] + 0.5) * pas])
        for sx, sy, _ in robot.tours_vrais:
            if math.hypot(P[0] - sx, P[1] - sy) <= 2500 and monde.visible(np.array([sx, sy]), P):
                vues[iy[k], ix[k]] = True
                break
    # position finale : vraie, et tenue par le PC ramenée dans le monde
    c0, s0 = math.cos(math.radians(monde.depart[2])), math.sin(math.radians(monde.depart[2]))
    def vers_monde(x, y):
        if b.plan:                                               # la carte du programme est dans le repère du plan
            u, v = ex.vers_px(x, y)
            return monde.etendue[0] + (u - 40) / ex.plan.s, monde.etendue[3] - (v - 40) / ex.plan.s
        return monde.depart[0] + c0 * x - s0 * y, monde.depart[1] + s0 * x + c0 * y
    fx, fy = vers_monde(ex.est.X, ex.est.Y)
    err = math.hypot(fx - robot.x, fy - robot.y)
    # erreur de position à chaque tour sur place : place tenue par le programme après le tour, contre la place vraie
    e_tours = []
    for st_j, vrai in zip(ex.j["stations"], robot.tours_vrais):
        if "pose" in st_j:
            wx, wy = vers_monde(st_j["pose"][0], st_j["pose"][1])
            e_tours.append(math.hypot(wx - vrai[0], wy - vrai[1]))
    if e_tours:
        print(f"TOURS {b.monde} graine {b.graine} : {len(e_tours)} tours sur place ; erreur de position après un tour : médiane {np.median(e_tours):.0f} mm, pire {max(e_tours):.0f} mm ;"
              f" {ex.est.chemin / 1000:.1f} m en {(robot.t - 1000) / 60:.1f} min, soit {ex.est.chemin / max(1.0, robot.t - 1000):.0f} mm/s en moyenne")
    err_cap = ((ex.est.C + (0.0 if b.plan else monde.depart[2]) - math.degrees(robot.th) + 180) % 360) - 180
    print(f"BILAN {b.monde} graine {b.graine} : fin « {ex.j['fin']} » ; {len(ex.noeuds)} stations, {len(ex.j['recalages'])} recalages,"
          f" {len(robot.contacts)} contacts vrais, {len(ex.j['echecs'])} trajets arrêtés ; sol accessible vu : {100.0 * vues.sum() / max(1, acc.sum()):.0f} %"
          f" ({acc.sum() * pas * pas / 1e6:.1f} m²) ; {ex.est.chemin / 1000:.1f} m en {(robot.t - 1000) / 60:.0f} min ;"
          f" erreur finale de position {err:.0f} mm, de cap {err_cap:+.1f}° ({len(ex.j['caps'])} corrections de cap, échelle finale {ex.est.k:.4f}) ; retour à {math.hypot(robot.x - monde.depart[0], robot.y - monde.depart[1]):.0f} mm du départ")
    if b.sans_dessin:
        return
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(11, 8.5), facecolor="#fcfcfb")
    ax.set_facecolor("#fcfcfb")
    ax.imshow(np.where(acc, np.where(vues, 0.92, 0.75), 1.0), extent=(monde.etendue[0], monde.etendue[2], monde.etendue[1], monde.etendue[3]),
              origin="lower", cmap="gray", vmin=0, vmax=1, zorder=0)
    for x0_, y0_, x1_, y1_ in monde.tapis:
        ax.add_patch(plt.Rectangle((x0_, y0_), x1_ - x0_, y1_ - y0_, fc="#eb6834", alpha=0.12, ec="none", zorder=1))
    for A, B in zip(monde.A, monde.B):
        ax.plot([A[0], B[0]], [A[1], B[1]], color="#0b0b0b", lw=1.6, zorder=3)
    for x, y, r in monde.poteaux:
        ax.add_patch(plt.Circle((x, y), r, color="#0b0b0b", zorder=3))
    tr = np.array(robot.trace)
    ax.plot(tr[:, 0], tr[:, 1], color="#2a78d6", lw=0.8, alpha=0.8, zorder=4)
    for s in ex.noeuds:                                          # stations là où le PC croit qu'elles sont
        wx, wy = vers_monde(s.x, s.y)
        coul = {"porte": "#1a8f4c", "arrêt": "#d03b3b"}.get(s.genre, "#52514e")
        ax.add_patch(plt.Circle((wx, wy), 170, fill=False, ec=coul, lw=1.4, zorder=5))
        ax.text(wx, wy, s.nom, ha="center", va="center", fontsize=7, zorder=6)
        if s.parent is not None:
            px, py = vers_monde(s.parent.x, s.parent.y)
            ax.plot([px, wx], [py, wy], color="#898781", lw=0.6, ls=":", zorder=4)
    for sx, sy, _ in robot.tours_vrais:
        ax.plot(sx, sy, "+", color="#2a78d6", ms=5, zorder=6)
    for cx, cy in robot.contacts:
        ax.plot(cx, cy, "x", color="#d03b3b", ms=7, mew=1.8, zorder=7)
    for d in ex.portes:
        wx, wy = vers_monde(*d["centre"])
        ax.plot(wx, wy, "s", color="#1a8f4c", ms=7, mfc="none", mew=1.6, zorder=7)
    for m in ex.murs:                                           # lignes de murs retenues, entre leurs pieds extrêmes
        for qa, qb in ((min(m.pieds) - 120, max(m.pieds) + 120),):
            a_ = vers_monde(m.rho * m.n[0] + qa * m.t[0], m.rho * m.n[1] + qa * m.t[1])
            b_ = vers_monde(m.rho * m.n[0] + qb * m.t[0], m.rho * m.n[1] + qb * m.t[1])
            ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color="#eb6834", lw=2.2, alpha=0.7, zorder=4)
    ax.set_aspect("equal")
    ax.set_title(f"{b.monde}, graine {b.graine} : {len(ex.noeuds)} stations, {len(robot.contacts)} contacts, sol vu {100.0 * vues.sum() / max(1, acc.sum()):.0f} %, "
                 f"{(robot.t - 1000) / 60:.0f} min — fin : {ex.j['fin']}", loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(prefixe + ".png", dpi=110, facecolor="#fcfcfb")
    print("dessin :", prefixe + ".png")


if __name__ == "__main__":
    main()
