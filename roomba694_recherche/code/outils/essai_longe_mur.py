# essai_longe_mur.py — longer UN mur sans s'arrêter, avec le capteur de distance fixé à 90° d'un côté : essai en
# simulation, sans le robot. Préparé le 2026-11-21 pour la demande de vitesse de l'utilisateur (« ça devrait être notre
# focus principal de pouvoir l'accélérer, peut-être en pensant à la façon de voir les murs de côté »).
#
#   python essai_longe_mur.py [--graines 5] [--detail]
#
# Pourquoi un essai de plus : celui de l'audit (essai_suivi_lateral.py) suppose soit deux capteurs de côté, soit un
# servo rapide qui regarde à gauche, devant, à droite, devant… Le firmware v15 fait autre chose : au-delà de 30° le
# servo ne tourne qu'à 5° par seconde (18 s pour aller à 90°). En roulant, le capteur reste donc tourné d'UN côté, et
# il y lit le mur dix fois par seconde. Rien ne regarde devant : c'est le pare-chocs qui protège l'avant.
#
# Même couloir simulé que l'audit (essai_centrage.monde_couloir : 95 cm de large, puis 84, 73 et 68, une ouverture de
# 80 cm du côté droit ; 3,9 m), mêmes 75 départs (décalé de -15, 0 ou +15 cm, cap faux de -6 à +6°, 5 tirages), même
# robot simulé (il suit un cap visé comme le cerveau le fait pendant une avance), même logique de suivi
# (suivi_lateral.SuiviLateral, avec un seul côté).
# Ce qui est comparé :
#   - le côté suivi : la gauche (mur continu, un décrochement de 11 cm) ou la droite (deux décrochements, puis une
#     ouverture de 80 cm où le mur disparaît) ;
#   - qui retouche le cap : le PC (5 fois par seconde, 0,25 s de retard : lecture, Wi-Fi, ordre) ou le cerveau (à
#     chaque lecture, sans retard) ;
#   - la vitesse : 100, 130 ou 147 mm/s (150 est le plafond des règles du projet).
# Le robot longe le mur à la distance qu'il avait au départ, sauf --cible MM (distance du centre du robot au mur).
#
# Comme l'essai de l'audit, celui-ci est plus indulgent que la réalité (vrais murs : plinthes, cadres de porte, objets
# posés). Il dit si la logique tient avec un seul côté lu à 10 Hz et quel temps on peut espérer ; il ne dit pas ce que
# lira le vrai capteur. Il suppose aussi un ordre que le firmware n'a pas encore : retoucher le cap visé pendant une avance.
import argparse
import math
import random
import sys

import numpy as np

import simulateur as sim
from essai_centrage import monde_couloir, jeu_mini
from suivi_lateral import SuiviLateral


def essai(decalage, cap_faux, graine, cote, qui, v_max, cible=None, k_vrai=1.0045, pertes=0.0, retard_plus=0.0, detail=False):
    d, dist = monde_couloir()
    x, y, c = d["depart"]
    d["depart"] = (x, y + decalage, c + cap_faux)
    monde = sim.Monde(**d)
    robot = sim.RobotSimule(monde, graine=graine, echelle_gyro=k_vrai, firmware=10)
    rng = random.Random(2000 + graine)
    suivi = SuiviLateral(axe=0.0, mediane=3, v_max=v_max, v_serre=min(80, v_max))
    if cible is not None:
        suivi.pose = (cible, cible)
    signe = 1.0 if cote == "g" else -1.0
    dt = 0.05
    periode, retard = {"cerveau": (0.1, 0.0), "pc": (0.2, 0.25)}[qui]
    retard += retard_plus
    t0 = robot.t
    file_cmd = []
    cap_vise, v = 0.0, min(100.0, v_max)
    chemin = 0.0
    t_ctrl = t_lec = -1e9
    lec = None
    contact = False
    fin = "distance faite"
    perdu_mm = 0.0                                   # chemin fait sans lecture du mur (ouverture)
    while chemin < dist:
        maintenant = robot.t
        P = np.array([robot.x, robot.y])
        if maintenant - t_lec >= 0.1 - 1e-9:         # le capteur, fixé à 90°, mesure dix fois par seconde
            cap = P + sim.DX * np.array([math.cos(robot.th), math.sin(robot.th)])
            r = monde.sonar(cap, robot.th + signe * math.pi / 2, rng=robot.rng)
            if rng.random() >= pertes:
                lec, t_lec = (r if r > 0 else None), maintenant
            else:
                t_lec = maintenant - 0.0             # lecture perdue : la précédente vieillit
        if maintenant - t_ctrl >= periode - 1e-9:
            t_ctrl = maintenant
            vue = lec if maintenant - t_lec < 0.35 else None
            gg, dd = (vue, None) if cote == "g" else (None, vue)
            cv, vv = suivi.pas(chemin, robot.bcap, gg, dd)
            file_cmd.append((maintenant + retard, cv, vv))
        while file_cmd and file_cmd[0][0] <= maintenant + 1e-9:
            _, cap_vise, v = file_cmd.pop(0)
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
        if lec is None or maintenant - t_lec >= 0.35:
            perdu_mm += ds
        robot.dormir(dt)
        if detail and int(chemin / 250) != int((chemin - ds) / 250):
            print(f"      {chemin:5.0f} mm : mur lu à {lec if lec is None else round(lec)}, écart {suivi.y:+5.0f} mm, axe {suivi.axe:+5.1f}°, "
                  f"cap visé {cap_vise:+5.1f}°, cap compté {robot.bcap:+5.1f}°, cap vrai {math.degrees(robot.th):+5.1f}°, y vrai {robot.y:5.0f}")
    return {"ok": fin == "distance faite", "fin": fin, "contacts": int(contact), "jeu": jeu_mini(monde, robot.trace), "duree": robot.t - t0,
            "axe": suivi.axe, "cap_faux": cap_faux, "avance": robot.x - x, "y_fin": robot.y, "perdu": perdu_mm}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    q = argparse.ArgumentParser()
    q.add_argument("--graines", type=int, default=5)
    q.add_argument("--detail", action="store_true")
    q.add_argument("--pertes", type=float, default=0.0, help="part des lectures du mur qui manquent (0 à 1)")
    q.add_argument("--retard", type=float, default=0.0, help="retard ajouté entre une lecture et son effet, secondes")
    q.add_argument("--cible", type=float, default=None, help="distance du centre du robot au mur à tenir, mm (sinon celle du départ)")
    a = q.parse_args()
    departs = [(dy, dc) for dy in (-150.0, 0.0, 150.0) for dc in (-6.0, -3.0, 0.0, 3.0, 6.0)]
    print("=== couloir simulé (95, 84, 73 puis 68 cm ; ouverture de 80 cm à droite), 3,9 m, sans arrêt, UN mur lu de côté à 10 Hz ===")
    print(f"    lectures perdues : {100 * a.pertes:.0f} % ; retard ajouté : {a.retard:.2f} s ; distance tenue : "
          + ("celle du départ" if a.cible is None else f"{a.cible:.0f} mm"))
    for cote, nom_c in (("g", "mur de gauche"), ("d", "mur de droite")):
        for qui, nom_q in (("pc", "retouche par le PC     "), ("cerveau", "retouche par le cerveau")):
            for v_max in (100, 130, 147):
                R = [essai(dy, dc, g, cote, qui, v_max, cible=a.cible, pertes=a.pertes, retard_plus=a.retard)
                     for dy, dc in departs for g in range(1, a.graines + 1)]
                ok = [r for r in R if r["ok"] and not r["contacts"]]
                txt = f"{nom_c}, {nom_q}, {v_max:3d} mm/s : {len(ok):2d} sur {len(R)} sans contact"
                if ok:
                    err = [abs(r["axe"] + r["cap_faux"]) for r in ok]
                    txt += (f" ; durée {np.median([r['duree'] for r in ok]):4.0f} s ; jeu le plus petit {min(r['jeu'] for r in ok):4.0f} mm "
                            f"(médiane {np.median([r['jeu'] for r in ok]):3.0f}) ; axe retrouvé à {np.median(err):.1f}° près (pire {max(err):.1f}°)")
                rate = [r for r in R if not r["ok"] or r["contacts"]]
                if rate:
                    txt += f" ; premier échec : {rate[0]['fin']} après {rate[0]['avance']:.0f} mm"
                print(txt)
    if a.detail:
        print("--- déroulé : mur de droite, PC, 130 mm/s, départ 15 cm à gauche, cap faux de +6° ---")
        essai(150.0, 6.0, 1, "d", "pc", 130, cible=a.cible, detail=True)


if __name__ == "__main__":
    main()
