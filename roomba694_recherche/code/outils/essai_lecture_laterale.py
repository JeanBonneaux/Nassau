# essai_lecture_laterale.py — ce que le capteur de distance lit DE CÔTÉ PENDANT QUE LE ROBOT AVANCE (firmware v15).
#
# Premier essai en roulant du capteur tourné à 90° (2026-11-21), pour la demande de vitesse de l'utilisateur : savoir si
# un mur lu de côté donne, en roulant, une distance assez régulière pour le longer sans s'arrêter (note P § 9).
#
#   python essai_lecture_laterale.py [ADRESSE] --prefixe CHEMIN/NOM --cote g|d [--distance 800] [--vitesse 100]
#                                    [--marge 450] [--lent 3] [--pas 5]
#       pendant qu'enregistreur.py tourne (le firmware arrête les roues si la console TCP se ferme).
#
# Déroulement :
#   1. capteur devant : la place libre devant est lue ; il faut distance + marge, sinon rien ne bouge ;
#   2. le capteur tourne lentement à 90° du côté choisi (butée relevée à 90°) ; 2 s de lectures à l'arrêt ;
#   3. /api/mouv?av=DISTANCE&v=VITESSE : une avance ordinaire du cerveau, cap tenu au gyroscope ;
#      pendant l'avance, /api/state est relu une dizaine de fois par seconde : distance de côté, chemin fait, cap ;
#   4. 2 s de lectures à l'arrêt, puis le capteur revient devant lentement et la butée est remise à 30°.
# ATTENTION : pendant l'avance, capteur tourné, RIEN NE SURVEILLE L'AVANT que le pare-chocs du robot (réflexe du
# firmware). La place devant est vérifiée juste avant de tourner le capteur ; l'avance est bornée et s'arrête seule.
# Ce que l'outil envoie : /api/radar (mode, angle, butee, lent), /api/mouv?av=…&v=…, et /api/mouv?stop=1 si l'avance
# dure trop. Arrêt et retour du capteur si celui-ci ne réagit plus ou si la carte redémarre.
# Fichier écrit : PREFIXE_lateral.jsonl (une ligne par lecture) ; résumé à l'écran : pente de la distance le long du
# chemin (l'angle du robot par rapport au mur), dispersion autour de cette droite, cadence des lectures.
import argparse
import json
import math
import statistics
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser(description="Lecture du capteur de distance tourné de côté pendant une avance (firmware v15).")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe", required=True)
p.add_argument("--cote", choices=["g", "d"], required=True)
p.add_argument("--distance", type=int, default=800, help="mm")
p.add_argument("--vitesse", type=int, default=100, help="mm/s")
p.add_argument("--marge", type=int, default=450, help="place qui doit rester devant après l'avance, mm")
p.add_argument("--lent", type=int, default=3)
p.add_argument("--pas", type=int, default=5)
a = p.parse_args()
ZONE = 30
ANGLE = 90 if a.cote == "g" else -90
MODE_SAFE = 3


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def heure():
    t = time.time()
    return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % int((t % 1) * 1000))


class Arret(Exception):
    pass


journal = open(a.prefixe + "_lateral.jsonl", "a", encoding="utf-8")
ms_carte = None


def lire(etape, **quoi):
    global ms_carte
    t_fin = time.time() + 4.0
    while True:
        try:
            e = get("/api/state")
            break
        except Exception as x:
            if time.time() > t_fin:
                raise Arret("le cerveau ne répond plus depuis 4 s (%s)" % type(x).__name__)
            time.sleep(0.2)
    ra, po, mv, rb = e.get("radar", {}), e.get("pose", {}), e.get("mouv", {}), e.get("robot", {})
    ligne = dict(t=time.time(), h=heure(), etape=etape, ms=e.get("ms"), servo=ra.get("servo"), mm=ra.get("mm"), a=ra.get("a"),
                 mm_age=ra.get("mm_age"), absent=ra.get("absent"), fait_mm=mv.get("fait_mm"), mouv=mv.get("etat"),
                 x=po.get("x"), y=po.get("y"), cap=po.get("cap"), dist=po.get("dist"), roule=e.get("driving"),
                 pc=rb.get("bump"), cur=rb.get("cur"), lb=rb.get("light"))
    ligne.update(quoi)
    journal.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    journal.flush()
    if ms_carte is not None and e.get("ms", 0) + 2000 < ms_carte:
        raise Arret("la carte a redémarré (%s)" % e.get("rst"))
    ms_carte = e.get("ms", ms_carte)
    if ra.get("absent"):
        raise Arret("le capteur de distance ne réagit plus")
    return e


def aller(angle, etape):
    e = lire(etape)
    cur = e["radar"]["servo"]
    while cur != angle:
        bond = max(-a.pas, min(a.pas, angle - cur))
        vise = cur + bond
        if abs(vise) <= ZONE and (abs(cur) > ZONE or abs(angle) > ZONE):     # traversée de la zone de ±30° d'une traite, au pas lent
            vise = (1 if angle > 0 else -1) * min(abs(angle), ZONE + a.pas) if abs(angle) > ZONE else angle
        get("/api/radar?mode=fixe&angle=%d" % vise)
        limite = time.time() + abs(vise - cur) / max(1, a.lent) + 5.0
        while True:
            time.sleep(0.2)
            e = lire(etape, vise=vise)
            cur = e["radar"]["servo"]
            if cur == vise:
                break
            if time.time() > limite:
                raise Arret("le capteur n'arrive pas à %d° (il est à %d°)" % (vise, cur))
    return e


def lectures(etape, duree, angle):
    """mesures distinctes du capteur à l'angle voulu pendant duree secondes : liste (instant de la mesure en ms de la carte, mm)"""
    M, vus, t_fin = [], set(), time.time() + duree
    while time.time() < t_fin:
        time.sleep(0.08)
        e = lire(etape)
        ra = e["radar"]
        if ra.get("a") == angle and ra.get("mm_age", 9999) < 500:
            tm = round((e["ms"] - ra["mm_age"]) / 20.0)          # une même mesure relue ne compte qu'une fois
            if tm not in vus:
                vus.add(tm)
                M.append((e["ms"] - ra["mm_age"], ra["mm"]))
    return M


def resume_fixe(nom, M):
    v = [mm for _, mm in M if mm > 0]
    rien = sum(1 for _, mm in M if mm == 0)
    if v:
        print("%s  %s : %d lectures, médiane %d mm (de %d à %d)%s" % (heure(), nom, len(M), statistics.median(v), min(v), max(v),
                                                                     (", %d fois rien à portée" % rien) if rien else ""))
    else:
        print("%s  %s : %d lectures, rien à portée" % (heure(), nom, len(M)))
    return statistics.median(v) if v else None


def compteurs():
    r = get("/api/radar")
    return {k: r.get(k, 0) for k in ("mesures", "sans_echo", "defauts")}


code = 0
capteur_tourne = False
try:
    e = lire("depart")
    rb = e["robot"]
    refus = None
    try:
        version = int(str(e.get("ver", "v0")).split(" ")[0].lstrip("v"))
    except ValueError:
        version = 0
    if version < 15:
        refus = "le firmware est plus ancien que la v15 (%s)" % str(e.get("ver", "?")).split(" ")[0]
    elif not rb.get("ok") or rb.get("mode") != MODE_SAFE:
        refus = "le robot ne répond pas ou n'est pas en mode Safe (mode lu %s)" % rb.get("mode")
    elif e.get("driving") or e["tour"]["etat"] in (1, 2) or e["mouv"]["etat"] == 1:
        refus = "le robot bouge déjà"
    elif any(rb.get("bump", [0, 0])) or any(rb.get("drop", [0, 0])):
        refus = "pare-chocs enfoncé ou roue levée"
    if refus:
        print("%s  RIEN N'EST ENVOYÉ : %s." % (heure(), refus))
        sys.exit(1)
    # 1. la place devant
    get("/api/radar?lent=%d" % a.lent)
    get("/api/radar?mode=fixe&angle=0")
    time.sleep(1.5)
    aller(0, "devant")
    D = lectures("devant", 2.0, 0)
    devant = resume_fixe("devant", D)
    if len(D) < 5:                                       # pas de lecture ne veut pas dire « libre »
        print("%s  PAS ASSEZ DE LECTURES DEVANT (%d en 2 s) : rien ne bouge." % (heure(), len(D)))
        sys.exit(1)
    libre = 4000 if devant is None else min(mm for _, mm in D if mm > 0)
    if libre - a.distance < a.marge:
        print("%s  PAS ASSEZ DE PLACE DEVANT : %d mm lus, il en faut %d (avance de %d + marge de %d). Rien ne bouge." % (
            heure(), libre, a.distance + a.marge, a.distance, a.marge))
        sys.exit(1)
    print("%s  place devant : %d mm ; après une avance de %d mm il restera %d mm devant le capteur." % (heure(), libre, a.distance, libre - a.distance))
    c0 = compteurs()
    # 2. le capteur de côté
    get("/api/radar?butee=90")
    capteur_tourne = True
    aller(ANGLE, "rotation")
    A0 = lectures("cote_arret_avant", 2.0, ANGLE)
    d_avant = resume_fixe("de côté, à l'arrêt, avant l'avance", A0)
    e = lire("avant_avance")
    cap0, dist0 = e["pose"]["cap"], e["pose"]["dist"]
    # 3. l'avance
    r = get("/api/mouv?av=%d&v=%d" % (a.distance, a.vitesse))
    if r.get("etat") != 1:
        raise Arret("avance refusée par le cerveau : %s" % r.get("raison"))
    print("%s  avance de %d mm à %d mm/s : partie (capteur à %d°, pare-chocs seul devant)." % (heure(), a.distance, a.vitesse, ANGLE))
    R, vus = [], set()                                   # (chemin au moment de la mesure, mm, cap)
    t0 = time.time()
    prec = None                                          # (t PC, fait_mm) de la lecture d'avant, pour la vitesse
    v_est = 0.0
    limite = a.distance / max(20, a.vitesse) + 10.0
    while True:
        time.sleep(0.05)
        e = lire("avance")
        mv, ra = e["mouv"], e["radar"]
        now = time.time()
        if prec is not None and now > prec[0]:
            v_est = (mv["fait_mm"] - prec[1]) / (now - prec[0])
        prec = (now, mv["fait_mm"])
        if ra.get("a") == ANGLE and ra.get("mm_age", 9999) < 500:
            tm = round((e["ms"] - ra["mm_age"]) / 20.0)
            if tm not in vus:
                vus.add(tm)
                R.append((mv["fait_mm"] - v_est * ra["mm_age"] / 1000.0, ra["mm"], e["pose"]["cap"], e["ms"] - ra["mm_age"]))
        if mv["etat"] != 1:
            break
        if now - t0 > limite:
            get("/api/mouv?stop=1")
            print("%s  avance trop longue : arrêt demandé." % heure())
            break
    mj = get("/api/mouv")
    e = lire("apres_avance")
    print("%s  avance : %s, %s mm faits pour %d demandés en %.1f s, raison : %s ; cap %+.1f° par rapport au départ ; pare-chocs %s" % (
        heure(), mj.get("texte"), mj.get("fait_mm"), a.distance, mj.get("duree_ms", 0) / 1000.0, mj.get("raison") or "aucune",
        e["pose"]["cap"] - cap0, e["robot"]["bump"]))
    # 4. à l'arrêt, puis retour du capteur
    A1 = lectures("cote_arret_apres", 2.0, ANGLE)
    d_apres = resume_fixe("de côté, à l'arrêt, après l'avance", A1)
    c1 = compteurs()
    print("%s  compteurs du capteur depuis le départ : %d mesures, %d sans écho, %d SANS RÉACTION" % (
        heure(), c1["mesures"] - c0["mesures"], c1["sans_echo"] - c0["sans_echo"], c1["defauts"] - c0["defauts"]))
    # résumé de l'avance
    V = [(s, mm, cap) for s, mm, cap, _ in R if mm > 0]
    rien = sum(1 for _, mm, _, _ in R if mm == 0)
    print("%s  pendant l'avance : %d lectures distinctes de côté (%d sans rien à portée), soit %.1f par seconde et une tous les %.0f mm" % (
        heure(), len(R), rien, len(R) / max(0.1, mj.get("duree_ms", 0) / 1000.0), (mj.get("fait_mm") or 0) / max(1, len(R))))
    if len(V) >= 8:
        n = len(V)
        ms_, md = sum(s for s, _, _ in V) / n, sum(mm for _, mm, _ in V) / n
        den = sum((s - ms_) ** 2 for s, _, _ in V)
        pente = sum((s - ms_) * (mm - md) for s, mm, _ in V) / den
        res = [mm - (md + pente * (s - ms_)) for s, mm, _ in V]
        et = math.sqrt(sum(x * x for x in res) / (n - 2))
        med = statistics.median(sorted(abs(x) for x in res))
        ang = math.degrees(math.atan(pente))
        print("              distance de côté : de %d mm au début à %d mm à la fin (droite ajustée), pente %+.1f mm par mètre" % (
            md + pente * (V[0][0] - ms_), md + pente * (V[-1][0] - ms_), 1000.0 * pente))
        print("              => le robot %s du mur de %.1f° ; écart des lectures à cette droite : %.0f mm (écart-type), %.0f mm (médian), pire %.0f mm" % (
            "s'écarte" if pente > 0 else "se rapproche", abs(ang), et, med, max(abs(x) for x in res)))
        print("              incertitude sur cet angle : ± %.2f° (d'après la dispersion et la longueur du trajet)" % math.degrees(et / math.sqrt(den)))
        if d_avant and d_apres:
            print("              à l'arrêt : %d mm avant, %d mm après (différence %+d mm ; la droite donne %+d mm)" % (
                d_avant, d_apres, d_apres - d_avant, pente * (V[-1][0] - V[0][0])))
except Arret as x:
    code = 2
    print("%s  ARRÊT : %s." % (heure(), x))
    try:
        get("/api/mouv?stop=1")
    except Exception:
        pass
except KeyboardInterrupt:
    code = 3
    print("%s  interrompu." % heure())
    try:
        get("/api/mouv?stop=1")
    except Exception:
        pass
finally:
    if capteur_tourne:
        try:
            get("/api/radar?mode=fixe&angle=0")          # le firmware le ramène devant, lentement, d'un bout à l'autre
            limite = time.time() + 95.0 / max(1, a.lent) + 10.0
            while time.time() < limite:
                time.sleep(0.4)
                try:
                    if get("/api/state")["radar"]["servo"] == 0:
                        break
                except Exception:
                    continue
            get("/api/radar?butee=%d" % ZONE)
            time.sleep(1.2)
            ra = get("/api/state")["radar"]
            print("%s  capteur à %d°, butée à %d° ; devant : %s mm." % (heure(), ra["servo"], ra.get("butee", -1), ra.get("front_mm")))
        except Exception as x:
            print("%s  LE RETOUR DU CAPTEUR N'A PAS PU ÊTRE VÉRIFIÉ (%s)." % (heure(), type(x).__name__))
    journal.close()
sys.exit(code)
