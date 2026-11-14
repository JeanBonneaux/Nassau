# essai_suivi_lateral.py — essaie suivi_lateral.py dans le couloir simulé d'essai_centrage.py, sans le robot.
#
# Audit du 2026-11-14 (notes/I_audit_regard_neuf.md). Usage : python essai_suivi_lateral.py [--graines 5] [--detail]
#
# Même couloir, mêmes 75 départs que l'essai du centrage par arrêts (décalé de -15, 0 ou +15 cm, cap faux de -6 à
# +6°, 5 tirages) : 95 cm de large, puis 84, 73 et 68 cm, puis une ouverture sur un côté ; 3,9 m à faire.
# Trois façons de lire les côtés en roulant :
#   deux capteurs, cerveau     deux capteurs de distance fixes (faisceau étroit, portée 1,3 m, bruit de 5 mm), lus 20
#                              fois par seconde, le cerveau retouchant lui-même le cap : aucun retard ;
#   deux capteurs, PC          les mêmes, mais c'est le PC qui retouche le cap 5 fois par seconde, avec 0,25 s de retard
#                              (lecture, Wi-Fi, ordre) ;
#   servo jusqu'à 90°          le capteur à ultrasons d'aujourd'hui sur un servo qui irait à 90° de chaque côté :
#                              gauche, devant, droite, devant…, une lecture toutes les 0,35 s (chaque côté toutes les
#                              1,4 s), retouche par le PC.
# Le robot simulé suit un cap visé comme le fait le cerveau pendant une avance (simulateur.RobotSimule.avance,
# firmware 10 : 13 °/s au plus, puis 1 °/s par degré d'écart) ; ici le cap visé change en route, ce que le firmware
# d'aujourd'hui ne permet pas.
#
# Le simulateur est plus indulgent que la réalité : un vrai capteur à faisceau étroit lit mal une surface sombre ou
# brillante, un vrai mur a des plinthes et des cadres de porte. Ce que cet essai dit : la logique tient et le temps
# gagné est de cet ordre ; il ne dit pas ce que lira un vrai capteur.
import argparse
import math
import random
import sys

import numpy as np

import simulateur as sim
from essai_centrage import monde_couloir, jeu_mini, milieu
from suivi_lateral import SuiviLateral


def rayon(monde, P, theta, portee=1300.0):
    """distance du point P à la première paroi dans la direction theta (radians), ou None au-delà de la portée"""
    r = np.array([math.cos(theta), math.sin(theta)])
    den = r[0] * monde.D[:, 1] - r[1] * monde.D[:, 0]
    ap = monde.A - P
    with np.errstate(divide="ignore", invalid="ignore"):
        t = (ap[:, 0] * monde.D[:, 1] - ap[:, 1] * monde.D[:, 0]) / den          # le long du rayon
        u = (ap[:, 0] * r[1] - ap[:, 1] * r[0]) / den                             # le long du mur
    ok = (np.abs(den) > 1e-9) & (t > 1.0) & (u >= 0.0) & (u <= 1.0)
    if not ok.any():
        return None
    d = float(t[ok].min())
    return d if d <= portee else None


def capteur_etroit(monde, P, theta, rng, bruit=5.0):
    """capteur de distance à faisceau étroit : la paroi la plus proche dans un cône de ±10°, à quelques millimètres près"""
    v = [rayon(monde, P, theta + math.radians(a)) for a in (-10.0, -5.0, 0.0, 5.0, 10.0)]
    v = [x for x in v if x is not None]
    if not v:
        return None
    return max(30.0, min(v) + rng.gauss(0.0, bruit))


def essai(decalage, cap_faux, graine, mode, k_vrai=1.0045, detail=False, bruit=5.0, pertes=0.0, retard_plus=0.0):
    # bruit : écart-type des capteurs à faisceau étroit (mm) ; pertes : part des lectures de côté qui manquent ;
    # retard_plus : retard ajouté à celui du mode (s)
    d, dist = monde_couloir()
    x, y, c = d["depart"]
    d["depart"] = (x, y + decalage, c + cap_faux)
    monde = sim.Monde(**d)
    robot = sim.RobotSimule(monde, graine=graine, echelle_gyro=k_vrai, firmware=10)
    rng = random.Random(1000 + graine)
    # le robot croit regarder dans l'axe (cap compté 0) ; avec le servo, les lectures de côté sont rares (une de chaque
    # côté toutes les 1,4 s) : trois suffisent pour une pente, et le robot roule à 60 mm/s tant que l'axe n'est pas lu
    suivi = SuiviLateral(axe=0.0, n_min=3, v_depart=60, v_max=90, mediane=1) if mode == "servo" else SuiviLateral(axe=0.0)
    dt = 0.05
    periode, retard = {"cerveau": (0.05, 0.0), "pc": (0.2, 0.25), "servo": (0.2, 0.25)}[mode]
    retard += retard_plus
    t0 = robot.t
    file_cmd = []                                    # (instant d'effet, cap visé, vitesse)
    cap_vise, v = 0.0, 100.0
    chemin = 0.0
    t_ctrl = -1e9
    g = dr = None                                    # dernières lectures de côté
    t_g = t_d = -1e9
    if mode == "servo":                              # avant de partir : un regard de chaque côté, robot immobile (0,7 s)
        cap = np.array([robot.x, robot.y]) + sim.DX * np.array([math.cos(robot.th), math.sin(robot.th)])
        r = monde.sonar(cap, robot.th + math.pi / 2, rng=robot.rng)
        g, t_g = (r if r > 0 else None), robot.t
        r = monde.sonar(cap, robot.th - math.pi / 2, rng=robot.rng)
        dr, t_d = (r if r > 0 else None), robot.t
        robot.dormir(0.7)
    seq, i_seq, t_seq = ("g", "f", "d", "f"), 0, robot.t
    contact = False
    fin = "distance faite"
    while chemin < dist:
        maintenant = robot.t
        P = np.array([robot.x, robot.y])
        # lectures de côté
        if mode in ("cerveau", "pc"):
            if rng.random() >= pertes:
                g, t_g = capteur_etroit(monde, P, robot.th + math.pi / 2, rng, bruit), maintenant
            if rng.random() >= pertes:
                dr, t_d = capteur_etroit(monde, P, robot.th - math.pi / 2, rng, bruit), maintenant
        else:
            if maintenant - t_seq >= 0.35:           # le servo vient d'arriver : une lecture, puis il repart
                quoi = seq[i_seq % 4]
                cap = P + sim.DX * np.array([math.cos(robot.th), math.sin(robot.th)])
                if quoi == "g":
                    r = monde.sonar(cap, robot.th + math.pi / 2, rng=robot.rng)
                    if rng.random() >= pertes:
                        g, t_g = (r if r > 0 else None), maintenant
                elif quoi == "d":
                    r = monde.sonar(cap, robot.th - math.pi / 2, rng=robot.rng)
                    if rng.random() >= pertes:
                        dr, t_d = (r if r > 0 else None), maintenant
                else:
                    r = monde.sonar(cap, robot.th, rng=robot.rng)
                    if 0 < r < 300:
                        fin = f"obstacle à {r:.0f} mm devant"
                        break
                i_seq += 1
                t_seq = maintenant
        # décision
        if maintenant - t_ctrl >= periode - 1e-9:
            t_ctrl = maintenant
            vieux = 2.0 if mode == "servo" else 0.06     # une lecture trop vieille ne compte plus (le suivi lisse lui-même)
            gg = g if maintenant - t_g < vieux else None
            dd = dr if maintenant - t_d < vieux else None
            cv, vv = suivi.pas(chemin, robot.bcap, gg, dd)
            file_cmd.append((maintenant + retard, cv, vv))
        while file_cmd and file_cmd[0][0] <= maintenant + 1e-9:
            _, cap_vise, v = file_cmd.pop(0)
        # le cerveau tient le cap visé (même modèle que simulateur.RobotSimule.avance, firmware 10)
        ecart_cap = cap_vise - robot.bcap
        derive = max(-13.0 * dt, min(13.0 * dt, ecart_cap * 1.0 * dt)) + robot.rng.gauss(0.0, 0.02)
        robot._tourner(math.radians(derive))
        vr = min(v + 11.0, 147.0)
        ds = (vr - 117.5 * abs(math.radians(derive)) / dt) * dt
        P2 = np.array([robot.x + ds * math.cos(robot.th), robot.y + ds * math.sin(robot.th)])
        if monde.contact(P2) is not None:
            robot.contacts.append((float(P2[0]), float(P2[1])))
            contact = True
            fin = "pare-chocs"
            break
        robot._avancer(ds)
        chemin += ds
        robot.dormir(dt)
        if detail and int(chemin / 250) != int((chemin - ds) / 250):
            print(f"      {chemin:5.0f} mm : gauche {g if g is None else round(g)}, droite {dr if dr is None else round(dr)}, écart au milieu {suivi.y:+5.0f} mm, "
                  f"axe {suivi.axe:+5.1f}°, cap visé {cap_vise:+5.1f}°, cap compté {robot.bcap:+5.1f}°, cap vrai {math.degrees(robot.th):+5.1f}°")
    e = milieu(monde, robot.x, robot.y)
    return {"ok": fin == "distance faite", "fin": fin, "contacts": int(contact), "jeu": jeu_mini(monde, robot.trace), "duree": robot.t - t0,
            "ecart_fin": e, "axe": suivi.axe, "cap_faux": cap_faux, "avance": robot.x - x}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    q = argparse.ArgumentParser()
    q.add_argument("--graines", type=int, default=5)
    q.add_argument("--detail", action="store_true")
    q.add_argument("--bruit", type=float, default=5.0, help="écart-type des capteurs à faisceau étroit, mm")
    q.add_argument("--pertes", type=float, default=0.0, help="part des lectures de côté qui manquent (0 à 1)")
    q.add_argument("--retard", type=float, default=0.0, help="retard ajouté entre une lecture et son effet, secondes")
    a = q.parse_args()
    departs = [(dy, dc) for dy in (-150.0, 0.0, 150.0) for dc in (-6.0, -3.0, 0.0, 3.0, 6.0)]
    print("=== couloir simulé (95, 84, 73 puis 68 cm, puis une ouverture d'un côté), 3,9 m, sans arrêt ===")
    print(f"    capteurs à faisceau étroit : bruit {a.bruit:.0f} mm ; lectures de côté perdues : {100 * a.pertes:.0f} % ; retard ajouté : {a.retard:.2f} s")
    for mode, nom in (("cerveau", "deux capteurs de côté, retouche par le cerveau"), ("pc", "deux capteurs de côté, retouche par le PC   "),
                      ("servo", "capteur actuel sur un servo jusqu'à 90°      ")):
        R = [essai(dy, dc, g, mode, bruit=a.bruit, pertes=a.pertes, retard_plus=a.retard) for dy, dc in departs for g in range(1, a.graines + 1)]
        ok = [r for r in R if r["ok"] and not r["contacts"]]
        ec = [abs(r["ecart_fin"]) for r in ok if r["ecart_fin"] is not None]
        print(f"{nom} : {len(R)} essais, {len(ok)} sans contact jusqu'au bout, {sum(r['contacts'] for r in R)} avec contact, "
              f"{sum(1 for r in R if not r['ok'] and not r['contacts'])} arrêtés avant la fin sans contact")
        if ok:
            # cap par rapport aux murs : le robot croyait regarder dans l'axe (0) alors qu'il était tourné de cap_faux ;
            # l'axe trouvé, compté comme le gyroscope, doit donc valoir -cap_faux
            err = [abs(r["axe"] + r["cap_faux"]) for r in ok]
            print(f"      jeu le plus petit {min(r['jeu'] for r in ok):.0f} mm (médiane {np.median([r['jeu'] for r in ok]):.0f}) ; "
                  f"durée {np.median([r['duree'] for r in ok]):.0f} s (de {min(r['duree'] for r in ok):.0f} à {max(r['duree'] for r in ok):.0f}) ; "
                  f"écart au milieu à l'arrivée {np.median(ec):.0f} mm en médiane, {max(ec):.0f} au pire ; "
                  f"axe du passage retrouvé à {np.median(err):.1f}° près en médiane, {max(err):.1f}° au pire")
        for r in R:
            if not r["ok"] or r["contacts"]:
                print(f"      - arrêt : {r['fin']} après {r['avance']:.0f} mm")
                break
    if a.detail:
        print("--- déroulé d'un essai : deux capteurs, PC, départ 15 cm à droite, cap faux de +6° ---")
        essai(-150.0, 6.0, 1, "pc", detail=True)


if __name__ == "__main__":
    main()
