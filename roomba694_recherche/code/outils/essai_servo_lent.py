# essai_servo_lent.py — premier essai du capteur de distance tourné au-delà de 30° (firmware v15), ROBOT IMMOBILE.
#
# Demande de l'utilisateur du 2026-11-21 : « on peut aussi essayer le capteur de distance qui tourne de 90 degrés. Pas
# besoin de photo, fais-le. L'important, c'est que si ça tourne, ça doit tourner très doucement. » Les fils du capteur
# sont courts (la butée de 30° avait été posée pour cela le 9 novembre) : l'essai avance donc par paliers, lentement, en
# vérifiant à chaque lecture que le capteur répond toujours et que la carte n'a pas redémarré.
#
#   python essai_servo_lent.py [ADRESSE] --prefixe CHEMIN/NOM [--paliers 45,60,75,90] [--cotes gd] [--lent 3]
#                              [--pas 5] [--tenue 3] [--garder-butee] [--tour FICHIER_essai11_tourN.json]
#   python essai_servo_lent.py [ADRESSE] --verifier          # lecture seule : dit si tout est prêt, n'envoie rien
#   python essai_servo_lent.py [ADRESSE] --retour            # ramène le capteur devant (lentement) et remet la butée à 30°
#
# Ce que l'outil envoie, et rien d'autre : /api/radar?lent=N, /api/radar?butee=N, /api/radar?mode=fixe&angle=N.
# Aucun ordre de roues. Le firmware fait lui-même la rotation lente (un degré à la fois) ; l'outil ne demande jamais plus
# de --pas degrés d'un coup, de sorte que s'il est interrompu le capteur s'arrête au plus --pas degrés plus loin.
#
# Déroulement, pour chaque côté (g = gauche, angles positifs ; d = droite) et chaque palier :
#   1. la butée est relevée au palier (pas plus) ;
#   2. le capteur y va par bonds de --pas degrés, à --lent degrés par seconde ; chaque lecture est écrite ;
#   3. il y reste --tenue secondes : médiane et dispersion des distances lues ;
#   puis retour devant, lentement, avant de passer à l'autre côté.
# Arrêt immédiat (retour lent devant, butée remise à 30°) si : le capteur ne réagit plus (« absent » : fil arraché ?),
# la carte a redémarré (baisse de tension : servo en butée mécanique ?), ou le cerveau ne répond plus pendant 4 s.
# Fichier écrit : PREFIXE_servo.jsonl (une ligne par lecture) ; résumé à l'écran.
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

p = argparse.ArgumentParser(description="Essai du capteur de distance tourné jusqu'à 90°, lentement, robot immobile (firmware v15).")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe", help="préfixe des fichiers écrits (mesures/NOM_DATE_HEURE)")
p.add_argument("--paliers", default="45,60,75,90")
p.add_argument("--cotes", default="gd", help="g, d ou gd : côtés essayés, dans cet ordre")
p.add_argument("--lent", type=int, default=3, help="vitesse de la rotation lente, degrés par seconde (1 à 10)")
p.add_argument("--pas", type=int, default=5, help="degrés demandés d'un coup, au plus")
p.add_argument("--tenue", type=float, default=3.0, help="secondes passées à chaque palier")
p.add_argument("--garder-butee", action="store_true", help="laisser la butée au dernier palier atteint au lieu de la remettre à 30°")
p.add_argument("--tour", help="fichier _essai11_tourN.json d'un tour sur place fait au même endroit : pour comparer")
p.add_argument("--verifier", action="store_true")
p.add_argument("--retour", action="store_true")
a = p.parse_args()

ZONE = 30   # RADAR_ZONE_VIVE du firmware


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def heure():
    t = time.time()
    return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % int((t % 1) * 1000))


class Arret(Exception):
    pass


journal = None
ms_carte = None      # dernière horloge de la carte : si elle recule, la carte a redémarré
defauts0 = None


def lire(ecrire=True, **quoi):
    """Une lecture de /api/state, écrite au journal. Lève Arret si la carte a redémarré ou si le capteur ne réagit plus."""
    global ms_carte
    t_fin = time.time() + 4.0
    while True:
        try:
            e = get("/api/state")
            break
        except Exception as x:
            if time.time() > t_fin:
                raise Arret("le cerveau ne répond plus depuis 4 s (%s)" % type(x).__name__)
            time.sleep(0.3)
    ra = e.get("radar", {})
    ligne = dict(t=time.time(), h=heure(), ms=e.get("ms"), servo=ra.get("servo"), cible=ra.get("cible"), mm=ra.get("mm"),
                 a=ra.get("a"), mm_age=ra.get("mm_age"), absent=ra.get("absent"), butee=ra.get("butee"), lent=ra.get("lent"),
                 mode=ra.get("mode"), cap=e.get("pose", {}).get("cap"), yaw=e.get("imu", {}).get("yaw"),
                 roule=e.get("driving"), mv=e.get("robot", {}).get("v"), rst=e.get("rst"))
    ligne.update(quoi)
    if ecrire and journal:
        journal.write(json.dumps(ligne, ensure_ascii=False) + "\n")
        journal.flush()
    if ms_carte is not None and e.get("ms", 0) + 2000 < ms_carte:
        raise Arret("la carte a redémarré (%s) : le capteur revient devant de lui-même, lentement" % e.get("rst"))
    ms_carte = e.get("ms", ms_carte)
    if ra.get("absent"):
        raise Arret("le capteur de distance ne réagit plus (un fil a-t-il lâché ?)")
    return e


def aller(angle, etape):
    """Demande l'angle (un bond de --pas degrés au plus à la fois) et suit le capteur jusqu'à ce qu'il y soit."""
    e = lire(etape=etape)
    cur = e["radar"]["servo"]
    while cur != angle:
        bond = max(-a.pas, min(a.pas, angle - cur))
        vise = cur + bond
        get("/api/radar?mode=fixe&angle=%d" % vise)
        limite = time.time() + abs(bond) / max(1, a.lent) + 4.0
        while True:
            time.sleep(0.2)
            e = lire(etape=etape, vise=vise)
            cur = e["radar"]["servo"]
            if cur == vise:
                break
            if time.time() > limite:
                raise Arret("le capteur n'arrive pas à %d° (il est à %d°)" % (vise, cur))
    return e


def tenir(angle, etape):
    """Reste --tenue secondes à l'angle et résume les distances lues là."""
    mm, t_fin, vu = [], time.time() + a.tenue, set()
    while time.time() < t_fin:
        time.sleep(0.12)
        e = lire(etape=etape, palier=angle)
        ra = e["radar"]
        cle = (ra.get("mm"), e.get("ms", 0) - ra.get("mm_age", 0))   # une même mesure relue ne compte qu'une fois
        if ra.get("a") == angle and ra.get("mm_age", 9999) < 400 and cle not in vu:
            vu.add(cle)
            mm.append(ra.get("mm"))
    return mm


def resume(angle, mm, profil, cap):
    vus = [x for x in mm if x and x > 0]
    rien = sum(1 for x in mm if x == 0)
    txt = "%s  palier %+4d° : %2d lectures" % (heure(), angle, len(mm))
    if vus:
        txt += ", médiane %4d mm (de %d à %d)" % (statistics.median(vus), min(vus), max(vus))
    if rien:
        txt += ", %d fois « rien à portée »" % rien
    if profil is not None and cap is not None:
        d = au_tour(profil, cap + angle)
        if d is not None:
            txt += " | le tour sur place lisait %d mm dans cette direction" % d
    print(txt)


def charger_tour(chemin):
    """Profil d'un tour sur place : liste (direction dans le repère de la position, mm)."""
    j = json.load(open(chemin, encoding="utf-8"))["tour"]
    cap0 = j["depart"][2]
    return [((cap0 + d10 / 10.0) % 360.0, mm) for d10, mm in j["points"] if mm > 0]


def au_tour(profil, direction):
    direction %= 360.0
    proches = [(min(abs(d - direction), 360.0 - abs(d - direction)), mm) for d, mm in profil]
    proches = sorted(x for x in proches if x[0] <= 3.0)
    return int(statistics.median([mm for _, mm in proches])) if proches else None


def revenir(etape="retour"):
    """Capteur devant (le firmware le ramène lentement d'un bout à l'autre), puis butée remise à 30°."""
    try:
        get("/api/radar?mode=fixe&angle=0")
        limite = time.time() + 90.0 / max(1, a.lent) + 15.0
        while time.time() < limite:
            time.sleep(0.3)
            try:
                e = get("/api/state")
            except Exception:
                continue
            ra = e.get("radar", {})
            if journal:
                journal.write(json.dumps(dict(t=time.time(), h=heure(), servo=ra.get("servo"), mm=ra.get("mm"), a=ra.get("a"),
                                              absent=ra.get("absent"), etape=etape), ensure_ascii=False) + "\n")
                journal.flush()
            if ra.get("servo") == 0:
                break
        if not a.garder_butee:
            get("/api/radar?butee=%d" % ZONE)
        e = get("/api/state")
        print("%s  capteur à %d°, butée à %d°." % (heure(), e["radar"]["servo"], e["radar"].get("butee", -1)))
    except Exception as x:
        print("%s  LE RETOUR N'A PAS PU ÊTRE VÉRIFIÉ (%s) : relire l'état avant toute autre chose." % (heure(), type(x).__name__))


def pret():
    e = get("/api/state")
    ra, rb = e.get("radar", {}), e.get("robot", {})
    ver = str(e.get("ver", ""))
    print("Cerveau : %s, allumé depuis %.0f s (%s)" % (ver, e.get("ms", 0) / 1000.0, e.get("rst")))
    print("Capteur de distance : mode %s, vers %s°, cible %s°, butée %s°, lent %s°/s, présent %s, absent %s, dernière lecture %s mm" % (
        ra.get("mode"), ra.get("servo"), ra.get("cible"), ra.get("butee"), ra.get("lent"), ra.get("present"), ra.get("absent"), ra.get("mm")))
    print("Robot : répond %s, mode %s, roule %s, tour %s, mouvement %s" % (
        rb.get("ok"), rb.get("mode"), e.get("driving"), e.get("tour", {}).get("etat"), e.get("mouv", {}).get("etat")))
    refus = []
    if not ver.startswith("v15"):
        refus.append("le firmware n'est pas la v15 (%s) : l'essai ne peut pas se faire" % ver.split(" ")[0])
    if "cible" not in ra:
        refus.append("le cerveau ne donne pas la direction visée (« cible ») : firmware trop ancien")
    if e.get("driving") or e.get("tour", {}).get("etat") in (1, 2) or e.get("mouv", {}).get("etat") == 1:
        refus.append("le robot bouge : l'essai se fait robot immobile")
    if ra.get("absent"):
        refus.append("le capteur de distance ne réagit pas")
    for r in refus:
        print("S'OPPOSE À L'ESSAI : " + r)
    if not refus:
        print("Rien ne s'oppose à l'essai.")
    return e, not refus


if a.verifier:
    sys.exit(0 if pret()[1] else 1)

if a.retour:
    revenir()
    sys.exit(0)

if not a.prefixe:
    p.error("--prefixe est requis (ou --verifier, ou --retour)")
paliers = [int(x) for x in a.paliers.split(",") if x.strip()]
if any(x <= ZONE or x > 90 for x in paliers) or paliers != sorted(paliers):
    p.error("--paliers : des angles croissants entre 31 et 90")
if not (1 <= a.lent <= 10) or not (1 <= a.pas <= 15):
    p.error("--lent de 1 à 10, --pas de 1 à 15")

e0, ok = pret()
if not ok:
    sys.exit(1)
profil = charger_tour(a.tour) if a.tour else None
journal = open(a.prefixe + "_servo.jsonl", "a", encoding="utf-8")
code = 0
try:
    get("/api/radar?lent=%d" % a.lent)
    get("/api/radar?mode=fixe&angle=0")
    time.sleep(1.5)
    e = aller(0, "depart")
    cap = e.get("pose", {}).get("cap")
    resume(0, tenir(0, "devant"), profil, cap)
    for cote in a.cotes:
        signe = 1 if cote == "g" else -1
        print("%s  côté %s" % (heure(), "gauche" if signe > 0 else "droit"))
        for pal in paliers:
            get("/api/radar?butee=%d" % pal)
            aller(signe * pal, "aller")
            resume(signe * pal, tenir(signe * pal, "palier"), profil, cap)
        aller(0, "retour")
        resume(0, tenir(0, "devant"), profil, cap)
    print("%s  essai terminé sans arrêt." % heure())
except Arret as x:
    code = 2
    print("%s  ARRÊT : %s. Retour du capteur devant." % (heure(), x))
except KeyboardInterrupt:
    code = 3
    print("%s  interrompu. Retour du capteur devant." % heure())
except Exception as x:
    code = 4
    print("%s  ARRÊT sur une erreur de l'outil (%s : %s). Retour du capteur devant." % (heure(), type(x).__name__, str(x)[:100]))
finally:
    revenir()
    journal.close()
sys.exit(code)
