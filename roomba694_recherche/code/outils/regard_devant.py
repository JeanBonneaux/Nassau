# regard_devant.py — robot IMMOBILE : le capteur de distance regarde lentement à plusieurs angles et dit ce qu'il lit à
# chacun. Sert avant d'entrer dans un passage étroit, quand l'écho lu droit devant peut venir d'une arête sur le côté.
#
#   python regard_devant.py [ADRESSE] [--angles -30,-20,-10,0,10,20,30] [--pause 1.2] [--sortie FICHIER.json]
#
# N'envoie que /api/radar (mode fixe, mouvement lent « doux », angle) ; aucune commande de roues. Au-delà de ±30° le
# firmware impose de toute façon sa vitesse lente (réglage « lent », un degré à la fois). Le capteur revient à 0° à la fin.
# Écrit le 2026-11-21 (journal_wifi.md § 73) : après un demi-tour dans le couloir, le capteur lisait 83 cm droit devant,
# là où le robot venait de rouler.
import argparse
import json
import statistics
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser()
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--angles", default="-30,-20,-10,0,10,20,30", help="degrés, positif à gauche")
p.add_argument("--pause", type=float, default=1.2, help="secondes de lecture à chaque angle")
p.add_argument("--sortie", default="")
a = p.parse_args()


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


e = get("/api/state")
if e.get("driving") or e["mouv"]["etat"] == 1 or e["tour"]["etat"] in (1, 2):
    sys.exit("le robot bouge : rien n'est envoyé")
lent = max(1, e["radar"].get("lent", 3))
R = []
try:
    for ang in [int(x) for x in a.angles.split(",")]:
        get("/api/radar?mode=fixe&doux=1&angle=%d" % ang)
        limite = time.time() + 200.0 / lent + 5.0
        while time.time() < limite:
            time.sleep(0.15)
            ra = get("/api/state")["radar"]
            if ra["servo"] == ang:
                break
        else:
            print("le capteur n'arrive pas à %d°" % ang)
            break
        time.sleep(0.4)
        M, vus, t_fin = [], set(), time.time() + a.pause
        while time.time() < t_fin:
            time.sleep(0.07)
            s = get("/api/state")
            ra = s["radar"]
            if ra.get("a") == ang and ra.get("mm_age", 9999) < 400:
                tm = round((s["ms"] - ra["mm_age"]) / 20.0)
                if tm not in vus:
                    vus.add(tm)
                    M.append(ra["mm"])
        bons = [m for m in M if m > 0]
        R.append({"angle": ang, "lectures": M})
        print("  %+4d° : %s  (%d lectures : %s)" % (
            ang, ("médiane %4d mm, de %d à %d" % (statistics.median(bons), min(bons), max(bons))) if bons else "rien à portée",
            len(M), " ".join(str(m) for m in M)))
finally:
    try:
        get("/api/radar?mode=fixe&doux=1&angle=0")
        limite = time.time() + 200.0 / lent + 5.0
        while time.time() < limite:
            time.sleep(0.3)
            if get("/api/state")["radar"]["servo"] == 0:
                break
        print("capteur revenu à %d°" % get("/api/state")["radar"]["servo"])
    except Exception as x:
        print("LE RETOUR DU CAPTEUR N'A PAS PU ÊTRE VÉRIFIÉ (%s)" % type(x).__name__)
if a.sortie:
    json.dump({"t": time.time(), "regards": R}, open(a.sortie, "w", encoding="utf-8"))
