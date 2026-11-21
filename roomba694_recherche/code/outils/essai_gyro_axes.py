# essai_gyro_axes.py — les trois axes du gyroscope pendant un tour sur place (essai 11 de la note O, note P § 8.1).
#
# La question : le facteur du gyroscope (1,0035 à 1,0056 selon les jours) vient-il de la carte, montée penchée de 5 à 6° ?
# Le cerveau ne compte la rotation que sur l'axe le plus vertical de la carte. Si la carte est penchée, pendant un tour
# sur place les deux autres axes lisent une petite part de la rotation, dans le rapport que donne l'accéléromètre au repos
# (X/Z = ax/az, Y/Z = ay/az). S'ils restent à zéro, l'explication est fausse.
#
#   python essai_gyro_axes.py [ADRESSE] --prefixe CHEMIN/NOM [--tours 2] [--periode 0.5]
#       pendant qu'enregistreur.py tourne : la touche g écrit ses lignes sur la console, et c'est l'enregistreur qui les
#       garde, datées, dans NOM_console.txt. PREFIXE = le préfixe de cet enregistrement (sans « _console.txt »).
#   python essai_gyro_axes.py --depouille CHEMIN/NOM
#       relit NOM_console.txt et NOM_essai11.jsonl, rien n'est envoyé.
#
# Ce que l'outil envoie : la touche g (lecture seule : elle n'appelle que printImu() et n'arrête ni un tour ni une avance),
# /api/tour?go=1 (un tour sur place ordinaire : 380° vers la gauche, roues à 62 mm/s), et la touche 5 (arrêt) si un tour
# dure plus de 60 s. Rien d'autre. Avant chaque tour il vérifie : robot qui répond, mode Safe, roues à l'arrêt, pare-chocs
# libre, roues au sol ; sinon il n'envoie rien et le dit.
# Une requête perdue (Wi-Fi) ne l'arrête pas : le tour est mené par le cerveau, qui s'arrête seul à 380°.
import argparse
import json
import math
import re
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser(description="Essai 11 : les trois axes du gyroscope pendant un tour sur place.")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe", help="préfixe de l'enregistrement en cours (mesures/NOM_DATE_HEURE)")
p.add_argument("--tours", type=int, default=2)
p.add_argument("--periode", type=float, default=0.5, help="secondes entre deux touches g pendant la rotation")
p.add_argument("--depouille", help="préfixe d'un enregistrement à relire ; rien n'est envoyé")
a = p.parse_args()

MODE_SAFE = 3   # valeur lue sur ce 694 en mode Safe (OI_MODE_SAFE_LU du firmware)


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def etat():
    try:
        return json.loads(get("/api/state"))
    except Exception as x:   # requête perdue : on continue
        return {"_erreur": "%s %s" % (type(x).__name__, str(x)[:80])}


def touche(c):
    try:
        get("/api/cmd?c=" + c)
        return True
    except Exception:
        return False


def heure(t=None):
    t = time.time() if t is None else t
    return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % int((t % 1) * 1000))


def mener():
    journal = open(a.prefixe + "_essai11.jsonl", "a", encoding="utf-8")

    def note(quoi, **k):
        k.update(t=time.time(), h=heure(), quoi=quoi)
        journal.write(json.dumps(k, ensure_ascii=False) + "\n")
        journal.flush()

    for n in range(1, a.tours + 1):
        e = etat()
        rb = e.get("robot", {})
        refus = None
        if "_erreur" in e:
            refus = "le cerveau ne répond pas (%s)" % e["_erreur"]
        elif not rb.get("ok"):
            refus = "le robot ne répond pas au cerveau"
        elif rb.get("mode") != MODE_SAFE:
            refus = "le robot n'est pas en mode Safe (mode lu %s)" % rb.get("mode")
        elif e.get("driving"):
            refus = "les roues tournent déjà"
        elif any(rb.get("bump", [0, 0])):
            refus = "le pare-chocs est enfoncé"
        elif any(rb.get("drop", [0, 0])):
            refus = "une roue est soulevée"
        elif e.get("tour", {}).get("etat") in (1, 2) or e.get("mouv", {}).get("etat") in (1, 2):
            refus = "un tour ou un mouvement est déjà en cours"
        if refus:
            print("%s  tour %d NON LANCÉ : %s. Rien n'a été envoyé." % (heure(), n, refus))
            note("refus", tour=n, raison=refus)
            return 1
        acc = e.get("imu", {}).get("acc")
        print("%s  tour %d : au repos, accéléromètre %s, batterie %s mAh" % (heure(), n, acc, rb.get("q")))
        note("repos", tour=n, acc=acc, imu=e.get("imu"), pose=e.get("pose"))
        touche("g")
        time.sleep(0.6)
        try:
            get("/api/tour?go=1")
        except Exception as x:
            print("%s  tour %d : l'ordre de tour n'est pas passé (%s)." % (heure(), n, type(x).__name__))
            note("ordre_perdu", tour=n)
            return 1
        note("ordre_tour", tour=n)
        t0 = time.time()
        vu_actif = False
        dernier = {}
        nb_g = 0
        while True:
            time.sleep(a.periode)
            if touche("g"):
                nb_g += 1
            e = etat()
            tr = e.get("tour", {})
            if tr:
                dernier = e
            et = tr.get("etat")
            if et in (1, 2):
                vu_actif = True
            note("pendant", tour=n, etat=et, tourne=tr.get("tourne"), rate=e.get("imu", {}).get("rate"),
                 roule=e.get("driving"), err=e.get("_erreur"))
            if vu_actif and et in (0, 3, 4):
                break
            if not vu_actif and time.time() - t0 > 6:   # jamais parti : refusé par le cerveau
                break
            if time.time() - t0 > 60:
                print("%s  tour %d : plus de 60 s, j'envoie l'arrêt (touche 5)." % (heure(), n))
                touche("5")
                note("arret_force", tour=n)
                break
        time.sleep(0.7)
        touche("g")
        time.sleep(0.5)
        try:
            tj = json.loads(get("/api/tour", timeout=6))
        except Exception as x:
            tj = {"_erreur": type(x).__name__}
        for cle in ("sta", "ap", "host"):   # jamais le nom du réseau de la maison dans un fichier de mesures
            dernier.pop(cle, None)
        with open("%s_essai11_tour%d.json" % (a.prefixe, n), "w", encoding="utf-8") as f:
            json.dump({"t_fin": time.time(), "tour": tj, "etat": dernier}, f, ensure_ascii=False)
        print("%s  tour %d : %s, %s° comptés, %s mesures du capteur de distance, %d touches g ; raison : %s" % (
            heure(), n, tj.get("texte"), tj.get("tourne"), tj.get("n"), nb_g, tj.get("raison") or "aucune"))
        note("fin", tour=n, texte=tj.get("texte"), tourne=tj.get("tourne"), n=tj.get("n"), raison=tj.get("raison"), nb_g=nb_g)
        if tj.get("etat") != 3:
            print("%s  tour %d pas terminé normalement : je m'arrête là." % (heure(), n))
            return 1
        time.sleep(3.0)
    journal.close()
    return 0


RE_G = re.compile(r"Acc.l.rom.tre \(g\) : X (-?[\d.]+)\s+Y (-?[\d.]+)\s+Z (-?[\d.]+)\s+\| gyroscope \(./s\) : X (-?[\d.]+)\s+Y (-?[\d.]+)\s+Z (-?[\d.]+)")


def moy(v):
    return sum(v) / len(v) if v else float("nan")


def ecart(v):
    if len(v) < 2:
        return float("nan")
    m = moy(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def depouiller(prefixe):
    lignes = []
    with open(prefixe + "_console.txt", encoding="utf-8", errors="replace") as f:
        for li in f:
            m = RE_G.search(li)
            if not m:
                continue
            try:
                t = float(li.split("\t", 1)[0])
            except ValueError:
                continue
            lignes.append((t,) + tuple(float(x) for x in m.groups()))
    if not lignes:
        print("Aucune ligne « gyroscope (°/s) » dans %s_console.txt." % prefixe)
        return 1
    repos = [l for l in lignes if abs(l[6]) < 2.0 and abs(l[4]) < 2.0 and abs(l[5]) < 2.0]
    rot = [l for l in lignes if abs(l[6]) > 20.0]
    print("Lignes de la touche g : %d, dont %d au repos et %d pendant la rotation (|Z| > 20 °/s)." % (len(lignes), len(repos), len(rot)))
    if repos:
        ax, ay, az = moy([l[1] for l in repos]), moy([l[2] for l in repos]), moy([l[3] for l in repos])
        na = math.sqrt(ax * ax + ay * ay + az * az)
        pench = math.degrees(math.atan2(math.hypot(ax, ay), abs(az)))
        print("Au repos : accéléromètre X %.3f  Y %.3f  Z %.3f g (norme %.3f) -> carte penchée de %.1f° ;" % (ax, ay, az, na, pench))
        print("           gyroscope X %.2f  Y %.2f  Z %.2f °/s (doit être près de zéro)." % (
            moy([l[4] for l in repos]), moy([l[5] for l in repos]), moy([l[6] for l in repos])))
        print("           si la carte penchée explique le facteur : X/Z attendu %+.3f, Y/Z attendu %+.3f, facteur attendu %.4f" % (
            ax / az, ay / az, na / abs(az)))
    if rot:
        gx, gy, gz = [l[4] for l in rot], [l[5] for l in rot], [l[6] for l in rot]
        mx, my, mz = moy(gx), moy(gy), moy(gz)
        print("En rotation : gyroscope X %.2f ± %.2f   Y %.2f ± %.2f   Z %.2f ± %.2f °/s (moyenne ± écart-type, %d lectures)" % (
            mx, ecart(gx), my, ecart(gy), mz, ecart(gz), len(rot)))
        rx = [x / z for x, z in zip(gx, gz)]
        ry = [y / z for y, z in zip(gy, gz)]
        n = len(rot)
        print("              X/Z mesuré %+.4f ± %.4f, Y/Z mesuré %+.4f ± %.4f (± = incertitude de la moyenne)" % (
            moy(rx), ecart(rx) / math.sqrt(n), moy(ry), ecart(ry) / math.sqrt(n)))
        tot = [math.sqrt(x * x + y * y + z * z) / abs(z) for x, y, z in zip(gx, gy, gz)]
        print("              rotation totale / rotation comptée sur Z : %.4f ± %.4f  (c'est le facteur que la carte penchée donnerait)" % (
            moy(tot), ecart(tot) / math.sqrt(n)))
        if repos:
            pv = [(x * ax + y * ay + z * az) / na / z for x, y, z in zip(gx, gy, gz)]
            print("              rotation autour de la verticale mesurée / rotation comptée sur Z : %.4f ± %.4f" % (
                moy(pv), ecart(pv) / math.sqrt(n)))
    return 0


if a.depouille:
    sys.exit(depouiller(a.depouille))
if not a.prefixe:
    p.error("--prefixe est requis (ou --depouille)")
code = mener()
sys.exit(code)
