# essai_cadence.py — la vitesse réelle des roues dépend-elle du rythme auquel on répète l'ordre de roues ?
#
# Constat du 2026-11-13 (journal_wifi.md § 35) : quand le cerveau redonne l'ordre de roues 20 fois par seconde
# (/api/mouv, firmware v10), les roues tournent environ 22 mm/s plus vite que demandé ; avec un ordre toutes les 0,5 s
# (les flèches du pilote) elles tournent à la vitesse demandée. Ce programme mesure la vitesse réelle pour plusieurs
# rythmes, avec la flèche « 8 » envoyée par le PC : aucun changement du firmware n'est nécessaire.
#
# S'utilise pendant qu'enregistreur.py tourne, robot en mode Safe, capteur de distance en mode fixe, de la place devant
# (chaque essai avance de vitesse × durée, soit 10 à 20 cm à 50 mm/s) :
#   python code/outils/essai_cadence.py ADRESSE PREFIXE --v 50 --periodes 0.5,0.2,0.1,0.05 --duree 2
# Les sécurités du firmware (réflexe pare-chocs, arrêt du capteur de distance, arrêt 1,5 s après le dernier ordre)
# restent seules juges ; le programme arrête aussi les roues sur une alarme du journal.
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilote import Pilote, MM_PAR_PAS, w16      # noqa: E402


def mediane(v):
    v = sorted(v)
    return v[len(v) // 2] if v else float("nan")


def main():
    ap = argparse.ArgumentParser(description="Vitesse réelle des roues selon le rythme des ordres")
    ap.add_argument("adresse")
    ap.add_argument("prefixe")
    ap.add_argument("--v", type=int, default=50, help="vitesse demandée, mm/s")
    ap.add_argument("--periodes", default="0.5,0.2,0.1,0.05", help="secondes entre deux ordres, séparées par des virgules")
    ap.add_argument("--duree", type=float, default=2.0, help="durée de chaque essai, secondes")
    ap.add_argument("--v-fin", type=int, default=150, help="vitesse remise à la fin")
    a = ap.parse_args()

    p = Pilote(a.adresse, a.prefixe)
    p.vitesse(a.v)
    try:
        for periode in [float(x) for x in a.periodes.split(",")]:
            l0 = p.frais()
            if l0 is None:
                sys.exit("Aucune ligne récente du journal.")
            refus = p.controle(l0, avance=True, marge_mm=int(a.v * a.duree * 1.5 + 450), vide_min=150)
            if refus:
                print(f"période {periode} s : pas de départ — {refus}")
                break
            i0 = len(p.lignes) - 1
            t0 = time.time()
            n, alarme, vu, prochain = 0, None, i0, t0
            while time.time() - t0 < a.duree and not alarme:
                if time.time() >= prochain:
                    p.touche("8")
                    n += 1
                    prochain += periode
                p.lire()
                for l in p.lignes[vu + 1:]:
                    alarme = Pilote.alarme(l, lb_max=400)
                    if alarme:
                        break
                vu = len(p.lignes) - 1
                time.sleep(0.005)
            p.touche("5")
            p.immobile()
            time.sleep(0.6)
            p.lire()
            seg = p.lignes[i0:]
            # vitesse de chaque roue par fenêtres de 0,2 s, entre 0,5 s après le départ et 0,3 s avant l'arrêt
            t_dep = next((l["ms"] for k, l in enumerate(seg[1:], 1) if l["enc_g"] != seg[k - 1]["enc_g"]), seg[0]["ms"])
            vg, vd = [], []
            for k in range(4, len(seg), 4):
                l, q = seg[k], seg[k - 4]
                dt = (l["ms"] - q["ms"]) / 1000.0
                if 0.15 < dt < 0.4 and q["ms"] - t_dep > 500 and l["ms"] - t_dep < (a.duree - 0.3) * 1000:
                    vg.append(w16(l["enc_g"] - q["enc_g"]) * MM_PAR_PAS / dt)
                    vd.append(w16(l["enc_d"] - q["enc_d"]) * MM_PAR_PAS / dt)
            chemin = (w16(seg[-1]["enc_g"] - seg[0]["enc_g"]) + w16(seg[-1]["enc_d"] - seg[0]["enc_d"])) / 2.0 * MM_PAR_PAS
            print(f"ordre tous les {periode:.2f} s ({n} ordres en {a.duree:.1f} s, {n / a.duree:.1f} par seconde) : roue gauche "
                  f"{mediane(vg):.0f} mm/s, droite {mediane(vd):.0f} mm/s pour {a.v} demandés ; chemin {chemin:.0f} mm, "
                  f"cap {seg[-1]['cap_pos'] - seg[0]['cap_pos']:+.1f}°" + (f" ; ALARME {alarme}" if alarme else ""))
            if alarme:
                break
            time.sleep(1.0)
    finally:
        p.touche("5")
        p.vitesse(a.v_fin)


if __name__ == "__main__":
    main()
