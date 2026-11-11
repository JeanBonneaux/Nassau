# attendre.py — attend, sans rien envoyer au robot, qu'une exploration avance ou se termine.
#
# Rend la main dès que le fichier PREFIXE_stations.json compte plus de --stations stations, que le journal d'explorer3
# contient sa ligne « fin : », ou que --secondes se sont écoulées ; affiche alors les dernières lignes du journal.
# Avec --cerveau ADRESSE : attend seulement que le cerveau réponde sur le réseau.
#
# Usage : python attendre.py PREFIXE [--journal FICHIER] [--stations N] [--secondes 480]
#         python attendre.py --cerveau 192.168.18.25 [--secondes 540]
import argparse
import json
import os
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser()
p_.add_argument("prefixe", nargs="?", default="")
p_.add_argument("--journal", default="")
p_.add_argument("--stations", type=int, default=0)
p_.add_argument("--secondes", type=float, default=480.0)
p_.add_argument("--cerveau", default="")
a = p_.parse_args()
t0 = time.time()
if a.cerveau:
    while time.time() - t0 < a.secondes:
        try:
            with urllib.request.urlopen(f"http://{a.cerveau}/api/state", timeout=3) as r:
                e = json.loads(r.read().decode("utf-8", errors="replace"))
            print(f"le cerveau répond après {time.time() - t0:.0f} s : {e.get('ver')} ; raison du démarrage : {e.get('rst')} ; robot : {'répond' if e['robot'].get('ok') else 'ne répond pas'}")
            sys.exit(0)
        except Exception:
            time.sleep(4)
    print(f"le cerveau ne répond toujours pas après {a.secondes:.0f} s")
    sys.exit(1)


def lire_journal():
    try:
        with open(a.journal, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


raison = "temps écoulé"
while time.time() - t0 < a.secondes:
    n = -1
    try:
        with open(a.prefixe + "_stations.json", encoding="utf-8") as f:
            n = len(json.load(f)["stations"])
    except (OSError, ValueError, KeyError):
        pass
    txt = lire_journal()
    if "] fin :" in txt or "Traceback" in txt:
        raison = "exploration terminée" if "] fin :" in txt else "erreur dans le programme"
        break
    if n > a.stations:
        raison = f"{n} tours sur place enregistrés"
        break
    time.sleep(3)
print(f"--- {raison} après {time.time() - t0:.0f} s ; dernières lignes du journal :")
print("\n".join(lire_journal().splitlines()[-14:]))
