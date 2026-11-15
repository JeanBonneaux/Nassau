# etat_cerveau.py — à lancer avant de piloter : la voie est-elle libre, et dans quel état sont le cerveau et le robot ?
# Lecture seule : une demande de /api/state au plus, rien n'est envoyé au robot.
#
#   python etat_cerveau.py [ADRESSE]            ADRESSE = 192.168.18.25 par défaut (ADRESSE:PORT pour un essai sur le PC)
#
# 1. Le veilleur de la session de revue (data_analysis/rv_matin.py, journal § 55) tient à jour
#    mesures/matin_dernier.txt. Tant que sa première ligne dit « en cours », il installe un firmware ou écoute le
#    robot : cet outil n'interroge alors PAS le cerveau et dit d'attendre.
# 2. Une lecture de /api/state : version, dernier redémarrage, robot, roues, mouvement en cours, sonde (firmware v13),
#    gyroscope, capteur de distance, position.
# 3. Une conclusion : ce qui s'oppose au pilotage, puis ce qu'il faut savoir avant de partir.
# Le nom du réseau de la maison n'est jamais affiché : le bloc « sta » n'est pas imprimé et le nom est masqué ailleurs.
# Code de sortie : 0 = rien ne s'oppose au pilotage ; 1 = quelque chose s'y oppose ; 2 = le cerveau ne répond pas.
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

ICI = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser(description="État du cerveau et du robot avant de piloter (lecture seule).")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--veilleur", default=os.path.normpath(os.path.join(ICI, "..", "..", "mesures", "matin_dernier.txt")),
               help="fichier d'état du veilleur")
a = p.parse_args()

bloque, a_savoir = [], []

# 1. le veilleur
ligne, age_h = "", None
try:
    with open(a.veilleur, encoding="utf-8") as f:
        ligne = f.readline().strip()
    age_h = (time.time() - os.path.getmtime(a.veilleur)) / 3600.0
except OSError:
    pass
en_cours = False
if not ligne:
    print("Veilleur : pas de fichier d'état (%s)." % os.path.basename(a.veilleur))
else:
    print("Veilleur : %s   (écrit il y a %s)" % (ligne, "%.0f min" % (age_h * 60) if age_h < 2 else "%.1f h" % age_h))
    en_cours = "en cours" in ligne and age_h < 1.0
    if "en cours" in ligne and not en_cours:
        a_savoir.append("le veilleur dit « en cours » depuis plus d'une heure : il s'est sans doute arrêté en route, l'écrire à la session de revue")
if en_cours:
    print("CONCLUSION : attendre. Le veilleur travaille (dix minutes au plus) ; le cerveau n'a pas été interrogé.")
    sys.exit(1)

# 2. le cerveau
t0 = time.time()
try:
    with urllib.request.urlopen("http://%s/api/state" % a.adresse, timeout=6) as r:
        brut = r.read().decode("utf-8", "replace")
    s = json.loads(brut)
except (OSError, ValueError) as err:
    print("Cerveau : pas de réponse de %s (%s)." % (a.adresse, type(err).__name__))
    print("CONCLUSION : le cerveau ne répond pas (éteint, ou hors du réseau).")
    sys.exit(2)
reseau = str((s.get("sta") or {}).get("saved") or "")


def propre(x):
    return x.replace(reseau, "…") if isinstance(x, str) and len(reseau) >= 2 else x


def bloc(nom):
    v = s.get(nom)
    return v if isinstance(v, dict) else {}


print("Cerveau : %s, réponse en %.2f s" % (time.strftime("%H:%M:%S"), time.time() - t0))
for k, v in s.items():
    if not isinstance(v, (dict, list)):
        print("   %s = %s" % (k, propre(v)))
for nom, v in s.items():
    if nom != "sta" and isinstance(v, dict):
        print("   %s : %s" % (nom, {k: propre(x) for k, x in v.items() if not isinstance(x, (dict, list))}))
print("   sta : connecté au réseau de la maison = %s" % bloc("sta").get("on"))

# 3. la conclusion
ver = str(s.get("ver", "?")).split(" ")[0]
num = int("".join(c for c in ver if c.isdigit()) or 0)
robot, sonde, imu, radar = bloc("robot"), bloc("sonde"), bloc("imu"), bloc("radar")
if "en attente" in ligne and age_h is not None and age_h < 24:
    a_savoir.append("le veilleur dit encore « en attente » alors que le cerveau répond : relancer cet outil dans 30 s ; "
                    "si la ligne ne change pas, le veilleur ne tourne pas, l'écrire à la session de revue")
if s.get("driving") or bloc("mouv").get("etat") == 1 or bloc("tour").get("etat") in (1, 2):
    bloque.append("quelque chose roule déjà (roues, mouvement ou tour sur place en cours)")
if sonde.get("suspend"):
    bloque.append("une sonde est en cours ou vient de finir : la lecture des capteurs est suspendue")
if sonde.get("douteux"):
    bloque.append("liaison douteuse après une sonde : l'écrire à la session de revue, ne rien envoyer au robot")
if imu and not imu.get("ok"):
    bloque.append("le gyroscope ne répond pas")
if imu.get("cal"):
    bloque.append("le gyroscope cherche son zéro : laisser le robot immobile")
if num and num < 12:
    a_savoir.append("firmware %s : les corrections de la v12 n'y sont pas" % ver)
if not robot.get("ok"):
    a_savoir.append("le robot ne répond pas au cerveau (endormi ou liaison fermée) : w, puis s, attendre 3 s")
else:
    mode = robot.get("mode")
    a_savoir.append("robot réveillé, mode lu %s (%s)" % (mode, {2: "passif", 3: "Safe"}.get(mode, "?")))
if robot.get("base") or robot.get("chg"):
    a_savoir.append("le robot est sur sa base ou en charge : il y ignore les ordres de roues, il faut le tirer à la main")
if radar and not radar.get("securite"):
    a_savoir.append("l'arrêt automatique du capteur de distance est coupé")
if bloc("console").get("perdus"):
    a_savoir.append("la console du cerveau a perdu %s caractères depuis son démarrage" % bloc("console").get("perdus"))
print("Firmware %s, allumé depuis %.0f s, dernier redémarrage : %s" % (ver, s.get("ms", 0) / 1000.0, propre(s.get("rst", "?"))))
for t in a_savoir:
    print("À savoir : " + t)
if bloque:
    for t in bloque:
        print("S'OPPOSE AU PILOTAGE : " + t)
    print("CONCLUSION : ne pas piloter pour l'instant.")
    sys.exit(1)
print("CONCLUSION : rien ne s'oppose au pilotage du côté du cerveau.")
