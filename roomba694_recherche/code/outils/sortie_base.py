# sortie_base.py — fait sortir le robot de sa base en marche arrière, par sauts courts surveillés depuis le PC.
#
# Sur sa base le robot a le nez vers le mur, le pare-chocs enfoncé et les capteurs de vide levés : il ne peut partir
# qu'en reculant tout droit (en mode Safe, un vide vu en marche arrière droite ne coupe pas les moteurs). Le programme
# passe en mode Safe si le robot n'y est pas, recule par sauts de 1,2 s au plus, et s'arrête au premier signe anormal :
# mode Safe perdu, roue levée, ordre refusé. Il s'arrête de lui-même quand le robot a reculé de la distance voulue.
# enregistreur.py doit tourner (le pilote lit son journal).
#
# Usage : python sortie_base.py ADRESSE PREFIXE [--distance 450] [--duree 1.2] [--vitesse 75] [--reculs 8]
import argparse
import sys
import time

from pilote import Pilote

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("adresse")
p_.add_argument("prefixe")
p_.add_argument("--distance", type=float, default=450.0, help="recul total voulu, mm")
p_.add_argument("--duree", type=float, default=1.2, help="durée d'un saut, s (1,4 au plus)")
p_.add_argument("--vitesse", type=int, default=75)
p_.add_argument("--reculs", type=int, default=8, help="nombre de sauts au plus")
a = p_.parse_args()
p = Pilote(a.adresse, a.prefixe)


def etat():
    e = p.etat()
    r = e["robot"]
    return r, f"mode {r.get('mode')} | sur la base {r.get('base')} | pare-chocs {r.get('bump')} | roues levées {r.get('drop')} | vide {r.get('cliff')} | devant {e['radar'].get('front_mm')} mm"


r, s = etat()
print("avant :", s)
if not r.get("ok"):
    raise SystemExit("le robot ne répond pas : rien n'est fait")
if r.get("mode") != 3:
    p.touche("f")
    time.sleep(1.2)
    r, s = etat()
    print("après f :", s)
    if r.get("mode") != 3:
        raise SystemExit("le mode Safe n'est pas obtenu sur la base : rien n'est fait")
p.vitesse(a.vitesse)
time.sleep(0.3)
total = 0.0
for k in range(a.reculs):
    res = p.saut("2", a.duree, lb_repos=5000, lb_max=5000, vide_min=0, vide_stop=0)
    if "refus" in res:
        print(f"saut {k + 1} refusé : {res['refus']}")
        break
    total += abs(res.get("avance_mm", 0.0))
    r, s = etat()
    print(f"saut {k + 1} : {res.get('avance_mm')} mm, rotation {res.get('rot_gyro')}° ; total {total:.0f} mm ; {s}" + (f" ; ALARME : {res['alarme']}" if res.get("alarme") else ""))
    if res.get("alarme") or r.get("mode") != 3:
        print("arrêt : " + (res.get("alarme") or "le robot a quitté le mode Safe"))
        break
    if total >= a.distance:
        break
    time.sleep(0.3)
r, s = etat()
print(f"fin : recul de {total:.0f} mm ; {s}")
