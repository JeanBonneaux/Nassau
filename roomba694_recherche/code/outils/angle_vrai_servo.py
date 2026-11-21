# angle_vrai_servo.py — de combien le capteur de distance tourne-t-il VRAIMENT quand on commande un angle au servo ?
#
# Pourquoi : le 2026-11-21, « 90° » commandés ne faisaient qu'une soixantaine de degrés (journal_wifi.md § 65). Un ordre
# n'est pas une position : cet outil la mesure, sans règle et sans connaître la pièce.
#
# L'idée. Au même endroit, robot immobile, on a deux façons de regarder autour de soi :
#   - un tour sur place (c'est le robot qui tourne, capteur devant) : la direction de chaque mesure est celle du gyroscope ;
#   - un balayage du servo (c'est le capteur qui tourne) : la direction est celle qu'on a commandée.
# Si le capteur tourne bien de l'angle commandé, les deux profils se superposent. Sinon on cherche le décalage c et les
# rapports kg (à gauche) et kd (à droite) tels que « direction vraie = c + k × angle commandé » fasse le mieux retomber le
# balayage sur le tour.
#
#   python angle_vrai_servo.py [ADRESSE] --prefixe CHEMIN/NOM --tour FICHIER_tourK.json [--lent 5] [--max 90]
#       fait le balayage (0 -> +max -> -max -> 0, lentement), l'écrit dans PREFIXE_balayage.jsonl, puis compare.
#   python angle_vrai_servo.py --relire PREFIXE --tour FICHIER_tourK.json
#       refait seulement la comparaison.
# Le fichier du tour est celui qu'écrit tour_et_profil (clés « tour » : réponse de /api/tour, et « cap_fin »).
# Ce que l'outil envoie : /api/radar (lent, butee, mode=fixe, doux=1, angle). Aucun ordre de roues. Arrêt et retour du
# capteur devant si celui-ci ne réagit plus ou si la carte redémarre. La butée et la vitesse sont remises comme avant.
# Limites : il faut un décor varié autour du robot (dans une pièce nue et ronde tout se superpose) ; le capteur entend
# dans un cône large, les deux profils ne sont donc jamais identiques ; le résultat vaut à 3 ou 4° près.
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

p = argparse.ArgumentParser(description="Angle vrai du capteur de distance pour un angle commandé au servo.")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe")
p.add_argument("--relire")
p.add_argument("--tour", required=True)
p.add_argument("--lent", type=int, default=5)
p.add_argument("--max", type=int, default=90)
a = p.parse_args()
ZONE = 30


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def heure():
    return time.strftime("%H:%M:%S")


class Arret(Exception):
    pass


def balayer(prefixe):
    e = get("/api/state")
    if e.get("driving") or e["tour"]["etat"] in (1, 2) or e["mouv"]["etat"] == 1:
        print("Le robot bouge : rien n'est envoyé.")
        sys.exit(1)
    avant = {"butee": e["radar"].get("butee", 30), "lent": e["radar"].get("lent", 5)}
    ms0 = e["ms"]
    journal = open(prefixe + "_balayage.jsonl", "a", encoding="utf-8")
    code = 0
    try:
        get("/api/radar?lent=%d" % a.lent)
        get("/api/radar?butee=%d" % a.max)
        for cible in (0, a.max, -a.max, 0):
            get("/api/radar?mode=fixe&doux=1&angle=%d" % cible)
            limite = time.time() + 2.0 * a.max / max(1, a.lent) + 15.0
            while True:
                time.sleep(0.07)
                try:
                    e = get("/api/state")
                except Exception:
                    if time.time() > limite:
                        raise Arret("le cerveau ne répond plus")
                    continue
                ra = e["radar"]
                journal.write(json.dumps(dict(t=time.time(), ms=e["ms"], servo=ra["servo"], cible=ra["cible"], a=ra["a"], mm=ra["mm"],
                                              mm_age=ra["mm_age"], absent=ra["absent"], cap=e["pose"]["cap"]), ensure_ascii=False) + "\n")
                if e["ms"] + 2000 < ms0:
                    raise Arret("la carte a redémarré")
                ms0 = e["ms"]
                if ra["absent"]:
                    raise Arret("le capteur de distance ne réagit plus")
                if ra["servo"] == cible and ra["cible"] == cible:
                    break
                if time.time() > limite:
                    raise Arret("le capteur n'arrive pas à %d° (il est à %d°)" % (cible, ra["servo"]))
            print("%s  capteur à %+d° (commandés)" % (heure(), cible))
    except Arret as x:
        code = 2
        print("%s  ARRÊT : %s. Retour du capteur devant." % (heure(), x))
    finally:
        journal.close()
        try:
            get("/api/radar?mode=fixe&doux=1&angle=0")
            t_fin = time.time() + 2.0 * a.max / max(1, a.lent) + 10.0
            while time.time() < t_fin and get("/api/state")["radar"]["servo"] != 0:
                time.sleep(0.3)
            get("/api/radar?butee=%d" % avant["butee"])
            get("/api/radar?lent=%d" % avant["lent"])
            ra = get("/api/state")["radar"]
            print("%s  capteur à %d°, butée remise à %d°, vitesse à %d°/s." % (heure(), ra["servo"], ra.get("butee", -1), ra.get("lent", -1)))
        except Exception as x:
            print("%s  LE RETOUR DU CAPTEUR N'A PAS PU ÊTRE VÉRIFIÉ (%s)." % (heure(), type(x).__name__))
    return code


def comparer(prefixe):
    # 1. le balayage : médiane des lectures fraîches par angle commandé
    par = {}
    for li in open(prefixe + "_balayage.jsonl", encoding="utf-8"):
        l = json.loads(li)
        if l.get("mm_age") is None or l["mm_age"] > 300 or l.get("mm") is None or l["mm"] < 0:
            continue
        par.setdefault(l["a"], set()).add((l["mm"], round((l["ms"] - l["mm_age"]) / 20.0)))
    servo = {}
    for ang, s in par.items():
        v = [mm for mm, _ in s]
        vus = [x for x in v if x > 0]
        servo[ang] = statistics.median(vus) if len(vus) * 2 >= len(v) else 0          # 0 : rien à portée
    # 2. le tour : profil par degré de direction vraie, dans le repère du cap à la fin du tour (celui du robot maintenant)
    d = json.load(open(a.tour, encoding="utf-8"))
    cap0, capf = d["tour"]["depart"][2], d["cap_fin"]
    pts = sorted((((cap0 + x / 10.0 - capf + 180.0) % 360.0) - 180.0, mm) for x, mm in d["tour"]["points"])

    def tour(direction):
        c = sorted((abs((ang - direction + 180.0) % 360.0 - 180.0), mm) for ang, mm in pts)
        proches = [mm for da, mm in c if da <= 3.0] or [c[0][1]]
        vus = [x for x in proches if x > 0]
        return statistics.median(vus) if len(vus) * 2 >= len(proches) else 0

    table = {k: tour(k) for k in range(-180, 181)}

    def ecart(c, k, cote):
        e = []
        for ang, mm in servo.items():
            if (cote > 0 and ang <= 0) or (cote < 0 and ang >= 0):
                continue
            vrai = int(round(c + k * ang))
            t = table.get(max(-180, min(180, vrai)), 0)
            if mm == 0 and t == 0:
                e.append(0.0)
            elif mm == 0 or t == 0:
                e.append(600.0)                      # l'un voit, l'autre non
            else:
                e.append(min(600.0, abs(mm - t)))
        return (statistics.mean(e), sum(1 for x in e if x < 80) / len(e)) if e else (9999.0, 0.0)

    print("Balayage : %d angles commandés lus, de %+d à %+d°. Tour : %d mesures." % (len(servo), min(servo), max(servo), len(pts)))
    print("  commandé | lu par le servo | lu par le tour dans la même direction (si le capteur tourne bien de l'angle commandé)")
    for ang in range(-a.max, a.max + 1, 15):
        if ang in servo:
            print("    %+4d°  |  %5s mm       |  %5s mm" % (ang, int(servo[ang]) or "rien", int(table[ang]) or "rien"))
    base_g, base_d = ecart(0, 1.0, +1), ecart(0, 1.0, -1)
    print("Si vrai = commandé : à gauche %.0f %% des angles à moins de 8 cm du tour (écart moyen %.0f mm) ; à droite %.0f %% (%.0f mm)." % (
        100 * base_g[1], base_g[0], 100 * base_d[1], base_d[0]))
    meilleur = None
    for c in range(-25, 26):
        g = min((ecart(c, k / 100.0, +1) + (k / 100.0,) for k in range(40, 131, 2)), key=lambda r: (r[0], -r[1]))
        dr = min((ecart(c, k / 100.0, -1) + (k / 100.0,) for k in range(40, 131, 2)), key=lambda r: (r[0], -r[1]))
        tot = g[0] + dr[0]
        if meilleur is None or tot < meilleur[0]:
            meilleur = (tot, c, g, dr)
    _, c, g, dr = meilleur
    print("Meilleur ajustement : décalage %+d° (le « devant » du capteur est tourné de %d° vers la %s) ;" % (c, abs(c), "gauche" if c > 0 else "droite"))
    print("   à gauche : %.2f° vrais par degré commandé -> %d° commandés font %+.0f° vrais (%.0f %% des angles à moins de 8 cm, écart moyen %.0f mm)" % (
        g[2], a.max, c + g[2] * a.max, 100 * g[1], g[0]))
    print("   à droite : %.2f° vrais par degré commandé -> %d° commandés font %+.0f° vrais (%.0f %% des angles à moins de 8 cm, écart moyen %.0f mm)" % (
        dr[2], -a.max, c - dr[2] * a.max, 100 * dr[1], dr[0]))
    # sensibilité : la plage de k qui reste à moins de 15 % du meilleur écart
    for nom, cote, best in (("gauche", +1, g), ("droite", -1, dr)):
        ok = [k / 100.0 for k in range(40, 131, 2) if ecart(c, k / 100.0, cote)[0] <= best[0] * 1.15 + 5.0]
        print("   %s : l'ajustement reste presque aussi bon pour un rapport de %.2f à %.2f" % (nom, min(ok), max(ok)))
    json.dump({"decalage": c, "k_gauche": g[2], "k_droite": dr[2], "servo": {str(k): v for k, v in sorted(servo.items())},
               "tour": {str(k): v for k, v in table.items()}}, open(prefixe + "_angle_vrai.json", "w", encoding="utf-8"), ensure_ascii=False)
    return 0


if a.relire:
    sys.exit(comparer(a.relire))
if not a.prefixe:
    p.error("--prefixe ou --relire")
code = balayer(a.prefixe)
if code == 0:
    comparer(a.prefixe)
sys.exit(code)
