# passage.py — mouvements à l'estime et regards au capteur de distance autour d'un passage étroit.
#
# Écrit le 2026-11-13 pour franchir les 47 cm laissés entre le battant de la porte H12 et un bout de mur
# (journal_wifi.md § 36) : là, le plan ne disait pas où étaient les bords ce jour-là, et le pilote d'explorer3.py
# aurait suivi le trait vert tracé à la main, droit sur le bord du battant. La méthode :
#   1. s'arrêter à 60 cm du passage et regarder au capteur, cap par cap (ordre voir=) : un bord fin (chant de porte)
#      ne renvoie un écho que dans l'axe, à 4° près ; un bout de mur se voit sur 40° ; l'ouverture donne une lecture lointaine ;
#   2. placer les deux bords par rapport au robot (cap et distance de l'écho le plus court de chacun) ;
#   3. se mettre dans l'axe du passage (ordre va=), regarder encore, puis passer lentement en ligne droite (va= à 50 mm/s).
#
# S'utilise pendant qu'enregistreur.py tourne, robot en mode Safe, capteur de distance en mode fixe, firmware v10 :
#   python code/outils/passage.py ADRESSE PREFIXE U,V,CAP ordre [ordre ...]
#     U,V,CAP : pixel du plan et cap du robot au départ (ce que donne relance.py, ou la ligne POSE= d'un appel précédent)
#     va=U,V[,vitesse]   tourne vers ce pixel du plan puis avance jusqu'à lui (vitesse demandée en mm/s, 100 par défaut)
#     cap=DEG            tourne vers ce cap du plan
#     av=MM[,vitesse]    avance de MM en tenant le cap actuel
#     re=MM              recule de MM (15 cm au plus), par exemple après un contact
#     voir=c1/c2/...     tourne vers chaque cap et lit le capteur de distance pendant une seconde
# La position est suivie à l'estime, d'après les compteurs et le gyroscope du cerveau lus dans le journal : bonne à
# 1 ou 2 cm sur un mètre, mais elle ne se recale pas sur le plan. La dernière ligne affichée, POSE=U,V,CAP, se redonne
# telle quelle à l'appel suivant. Les contrôles sont ceux de Pilote.avance et Pilote.tourne (pare-chocs, roues, mode
# Safe, sol sombre, obstacle à moins de 30 cm devant) ; les capteurs optiques n'arrêtent pas l'avance (un passage
# étroit les excite des deux côtés). La série s'arrête au premier ordre refusé ou interrompu.
import math
import sys
import time

import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilote import Pilote  # noqa: E402

K_GYRO = 1.0045                 # échelle du gyroscope du cerveau (journal_wifi.md § 31)
S = 0.053                       # pixels du plan par millimètre

if len(sys.argv) < 5:
    sys.exit("usage : python passage.py ADRESSE PREFIXE U,V,CAP ordre [ordre ...]")
p = Pilote(sys.argv[1], sys.argv[2])
u0, v0, cap0 = (float(x) for x in sys.argv[3].split(","))
p.lire()
l0 = p.frais()
if l0 is None:
    sys.exit("aucune ligne récente du journal : l'enregistreur tourne-t-il ? le robot répond-il ?")
ref = dict(l0)


def pose():
    """pixel du plan, cap du plan et dernière ligne du journal"""
    l = p.frais() or p.lignes[-1]
    dx, dy = l["x_mm"] - ref["x_mm"], l["y_mm"] - ref["y_mm"]
    a = math.radians(cap0 - ref["cap_pos"])                 # du repère du cerveau à celui du plan
    X, Y = dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a)
    return u0 + X * S, v0 - Y * S, (cap0 + (l["cap_pos"] - ref["cap_pos"]) * K_GYRO) % 360.0, l


def tourner_vers(cap):
    """Renvoie l'écart de cap qui reste (moins d'un degré : le cerveau refuse les rotations plus petites), ou None."""
    for _ in range(3):
        d = (cap - pose()[2] + 180.0) % 360.0 - 180.0
        if abs(d) < 1.0:
            return d
        r = p.tourne(d, vide_min=150)
        if "refus" in r or r.get("alarme"):
            print("   rotation refusée ou alarme :", r.get("refus") or r.get("alarme"))
            return None
        time.sleep(0.3)
    return (cap - pose()[2] + 180.0) % 360.0 - 180.0


def avancer(dist, vitesse, reste_cap=0.0):
    p.vitesse(vitesse)
    time.sleep(0.1)
    r = p.avance(dist, marge_mm=300, lb_repos=1500, lb_max=3000, vide_min=150, vide_stop=150, cap_rel=reste_cap)
    time.sleep(0.4)
    u, v, c, l = pose()
    if "refus" in r:
        print(f"   avance refusée : {r['refus']}")
        return False
    print(f"   avance de {r.get('avance_mm')} mm pour {dist:.0f} demandés, raison « {r.get('raison')} », alarme {r.get('alarme')}, "
          f"capteurs optiques jusqu'à {r.get('lb_max'):.0f}, sol {r.get('vide_min'):.0f} ; robot en ({u:.1f}, {v:.1f}), cap {c:.1f}°, devant {l['us_mm']:.0f} mm")
    return not r.get("alarme") and "distance" in str(r.get("raison"))


ok = True
try:
    for ordre in sys.argv[4:]:
        nom, val = ordre.split("=", 1)
        if not ok:
            print("ordre non exécuté :", ordre)
            continue
        if nom == "cap":
            d = tourner_vers(float(val))
            u, v, c, l = pose()
            print(f"cap {float(val):.1f}° demandé : cap {c:.1f}°, devant {l['us_mm']:.0f} mm")
            ok = d is not None
        elif nom == "voir":
            for cap in [float(x) for x in val.split("/")]:
                if tourner_vers(cap) is None:
                    ok = False
                    break
                time.sleep(0.5)
                p.lire()
                n0 = len(p.lignes)
                time.sleep(1.2)
                p.lire()
                us = sorted(l["us_mm"] for l in p.lignes[n0:])
                if us:
                    print(f"   regard au cap {pose()[2]:6.1f}° : médiane {us[len(us) // 2]:5.0f} mm (de {us[0]:.0f} à {us[-1]:.0f}), "
                          f"soit {us[len(us) // 2] + 27:.0f} mm du centre du robot")
        elif nom in ("va", "av"):
            f = [float(x) for x in val.split(",")]
            u, v, c, l = pose()
            if nom == "va":
                dx, dy = (f[0] - u) / S, -(f[1] - v) / S
                dist, cap = math.hypot(dx, dy), math.degrees(math.atan2(dy, dx)) % 360.0
                vit = f[2] if len(f) > 2 else 100
                d = tourner_vers(cap)
                if d is None:
                    ok = False
                    continue
            else:
                dist, vit, d = f[0], (f[1] if len(f) > 1 else 100), 0.0
            print(f"{ordre} : {dist:.0f} mm au cap {pose()[2]:.1f}° (reste de cap {d:+.1f}°), {vit:.0f} mm/s demandés")
            ok = avancer(dist, int(vit), reste_cap=d if abs(d) >= 0.5 else 0.0)
        elif nom == "re":
            # recul court après un contact (touche 2 du firmware, comme explorer3.py) : 15 cm au plus par ordre
            mm = min(150.0, float(val))
            fait = 0.0
            while fait < mm - 20.0 and ok:
                p.lire()
                l0 = p.frais()
                r = p.saut("2", min(1.2, max(0.3, (mm - fait) / 130.0)), lb_repos=5000, lb_max=5000, vide_min=150)
                time.sleep(0.4)
                p.lire()
                l1 = p.frais()
                if "refus" in r or l0 is None or l1 is None:
                    print("   recul refusé :", r.get("refus"))
                    ok = False
                    break
                pas = math.hypot(l1["x_mm"] - l0["x_mm"], l1["y_mm"] - l0["y_mm"])
                fait += pas
                if pas < 5.0:
                    break
            u, v, c, l = pose()
            print(f"{ordre} : recul de {fait:.0f} mm ; robot en ({u:.1f}, {v:.1f}), cap {c:.1f}°, pare-chocs {int(l['pc_g'])}{int(l['pc_d'])}")
        else:
            sys.exit(f"ordre inconnu : {ordre}")
finally:
    p.vitesse(150)
u, v, c, l = pose()
e = p.etat()
print(f"fin : mode {e['robot']['mode']}, roues en marche {e['driving']}, pare-chocs {int(l['pc_g'])}{int(l['pc_d'])}, devant {l['us_mm']:.0f} mm")
print(f"POSE={u:.1f},{v:.1f},{c:.1f}")
