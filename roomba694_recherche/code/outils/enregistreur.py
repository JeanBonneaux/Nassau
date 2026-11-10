# enregistreur.py — enregistre une séance entière du firmware roomba694_wifi, tout sur l'horloge du PC.
#
# Trois sources, écrites au fil de l'eau (rien n'est perdu si l'outil est interrompu) :
#   1. la console TCP (port 23) : chaque ligne reçue, datée                      -> NOM_console.txt
#      - les lignes « csv,... » du journal du firmware (touche j, 5 par seconde)  -> NOM_capteurs.csv
#      - les réponses à la touche e (infrarouge de la base, courants des moteurs,
#        roulette avant, surintensités : valeurs visibles seulement par la console) -> NOM_e.csv
#   2. /api/state, relu toutes les --etat secondes (courants des roues, capteur de
#      distance, position, ordres en cours)                                        -> NOM_etat.jsonl
#
# L'outil n'envoie au robot que les touches demandées (--touches, --fin, --csv, --e). Aucune touche de roues
# n'est envoyée si on ne l'écrit pas soi-même dans --touches.
# Attention : le firmware arrête les roues et un tour sur place quand le client TCP se déconnecte ; ne pas
# arrêter l'outil pendant un tour sur place.
#
# Usage : python enregistreur.py [ADRESSE] [--nom pilotage] [--duree 600] [--dossier ../../mesures]
#                                [--csv] [--etat 0.5] [--e 1] [--touches "s b"] [--fin "s x"] [--attente 1.5]
#   ex. : python enregistreur.py 192.168.18.25 --nom pilotage --duree 900 --csv --e 1
# Arrêt propre avant la fin : créer le fichier NOM_STOP (son chemin est affiché au démarrage), ou Ctrl+C.
# Tant que le robot ne répond pas au cerveau, /api/state n'est relu que toutes les 2 s et la touche e n'est pas envoyée.
import argparse
import datetime
import json
import os
import re
import socket
import sys
import threading
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ICI = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser(description="Enregistre console, journal CSV, touche e et /api/state du firmware roomba694_wifi.")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--nom", default="seance", help="début du nom des fichiers")
p.add_argument("--duree", type=float, default=600.0, help="durée maximale en secondes")
p.add_argument("--dossier", default=os.path.normpath(os.path.join(ICI, "..", "..", "mesures")))
p.add_argument("--csv", action="store_true", help="active le journal CSV du firmware (touche j) pendant l'enregistrement")
p.add_argument("--etat", type=float, default=0.5, help="période de lecture de /api/state en secondes (0 = jamais)")
p.add_argument("--e", type=float, default=0.0, help="période d'envoi de la touche e en secondes (0 = jamais)")
p.add_argument("--touches", default="", help="touches envoyées au début, séparées par des espaces")
p.add_argument("--fin", default="", help="touches envoyées à la fin, séparées par des espaces")
p.add_argument("--attente", type=float, default=1.5, help="secondes entre deux touches de --touches et de --fin")
p.add_argument("--note", default="", help="texte libre écrit en tête du fichier console")
a = p.parse_args()

os.makedirs(a.dossier, exist_ok=True)
stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
base = os.path.join(a.dossier, f"{a.nom}_{stamp}")
stop_path = base + "_STOP"
t0 = time.time()
fini = threading.Event()
verrou = threading.Lock()
compte = {"console": 0, "csv": 0, "e": 0, "etat": 0, "etat_err": 0}
robot_repond = threading.Event()   # levé par la lecture de /api/state quand le robot vient de répondre au cerveau


def heure(t):
    return datetime.datetime.fromtimestamp(t).strftime("%H:%M:%S.%f")[:-3]


def get_json(chemin, timeout=2.5):
    with urllib.request.urlopen(f"http://{a.adresse}{chemin}", timeout=timeout) as r:
        return json.load(r)


f_console = open(base + "_console.txt", "w", encoding="utf-8", newline="\n")
f_console.write(f"# {os.path.basename(base)} — carte {a.adresse} — début {heure(t0)} le {datetime.date.today()}\n")
if a.note:
    f_console.write(f"# {a.note}\n")
f_console.write("# colonnes : secondes PC (epoch) <tab> heure PC <tab> ligne reçue ; « >> » = touche envoyée par l'outil\n")
f_csv = None        # ouvert à la première ligne d'en-tête « csv,ms,... »
f_e = None          # ouvert à la première réponse complète à la touche e
E_COLS = ["pc_s", "pc_g", "pc_d", "roue_g", "roue_d", "vide_g", "vide_avg", "vide_avd", "vide_d",
          "lb_g", "lb_avg", "lb_cg", "lb_cd", "lb_avd", "lb_d", "btn_clean", "btn_spot", "btn_dock",
          "mur", "mur_signal", "mur_virtuel", "ir_dessus", "ir_gauche", "ir_droite", "salete", "roulette",
          "base", "cur_g", "cur_d", "cur_brosse", "cur_lat", "surint"]
e_row = {}
RE = {
    "pc": re.compile(r"Pare-chocs : droit (\d+), gauche (\d+) \| Roue levée : droite (\d+), gauche (\d+)"),
    "vide": re.compile(r"Vide \(signaux\) : gauche (\d+), avant gauche (\d+), avant droit (\d+), droit (\d+)"),
    "lb": re.compile(r"Capteurs optiques du pare-chocs \(G, AvG, CG, CD, AvD, D\) : (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)"),
    "btn": re.compile(r"Boutons : CLEAN (\d+), SPOT (\d+), DOCK (\d+) \| mur (\d+) \(signal (\d+)\), mur virtuel (\d+)"),
    "ir": re.compile(r"Infrarouge reçu : dessus (\d+), gauche (\d+), droite (\d+) \| saleté (\d+) \| roulette avant (\d+) \| sur la base : (oui|non)"),
    "mot": re.compile(r"Moteurs \(mA\) : roue gauche (-?\d+), roue droite (-?\d+), brosse (-?\d+), brosse latérale (-?\d+) \| surintensités \(bits\) (\d+)"),
}


# Le nom du réseau Wi-Fi de la maison ne doit pas se retrouver dans les fichiers (ils partent sur GitHub).
RE_RESEAU = re.compile(r"([Rr]éseau de la maison « )[^»]*( »)")


def ecrire_console(t, texte):
    texte = RE_RESEAU.sub(r"\1…\2", texte)
    with verrou:
        f_console.write(f"{t:.3f}\t{heure(t)}\t{texte}\n")
        f_console.flush()
        compte["console"] += 1


def traiter_ligne(t, ligne):
    """Une ligne de la console : rangée telle quelle, puis triée (journal CSV, réponse à la touche e)."""
    global f_csv, f_e, e_row
    ecrire_console(t, ligne)
    if ligne.startswith("csv,ms,"):
        if f_csv is None:
            f_csv = open(base + "_capteurs.csv", "w", encoding="utf-8", newline="\n")
            f_csv.write("pc_s," + ligne[4:] + "\n")
        return
    if ligne.startswith("csv,"):
        if f_csv is None:     # journal déjà actif avant l'outil : en-tête du firmware v5, écrit d'office
            f_csv = open(base + "_capteurs.csv", "w", encoding="utf-8", newline="\n")
            f_csv.write("pc_s,ms,enc_g,enc_d,pc_g,pc_d,roue_g,roue_d,vide_g,vide_avg,vide_avd,vide_d,lb_g,lb_avg,lb_cg,"
                        "lb_cd,lb_avd,lb_d,mv,ma,mode,cap_deg,rot_dps,us_mm,x_mm,y_mm,cap_pos\n")
        f_csv.write(f"{t:.3f},{ligne[4:]}\n")
        f_csv.flush()
        compte["csv"] += 1
        return
    m = RE["pc"].search(ligne)
    if m:
        e_row = {"pc_s": f"{t:.3f}", "pc_d": m[1], "pc_g": m[2], "roue_d": m[3], "roue_g": m[4]}
        return
    m = RE["vide"].search(ligne)
    if m:
        e_row.update(vide_g=m[1], vide_avg=m[2], vide_avd=m[3], vide_d=m[4])
        return
    m = RE["lb"].search(ligne)
    if m:
        e_row.update(lb_g=m[1], lb_avg=m[2], lb_cg=m[3], lb_cd=m[4], lb_avd=m[5], lb_d=m[6])
        return
    m = RE["btn"].search(ligne)
    if m:
        e_row.update(btn_clean=m[1], btn_spot=m[2], btn_dock=m[3], mur=m[4], mur_signal=m[5], mur_virtuel=m[6])
        return
    m = RE["ir"].search(ligne)
    if m:
        e_row.update(ir_dessus=m[1], ir_gauche=m[2], ir_droite=m[3], salete=m[4], roulette=m[5],
                     base="1" if m[6] == "oui" else "0")
        return
    m = RE["mot"].search(ligne)
    if m and "pc_s" in e_row:
        e_row.update(cur_g=m[1], cur_d=m[2], cur_brosse=m[3], cur_lat=m[4], surint=m[5])
        if f_e is None:
            f_e = open(base + "_e.csv", "w", encoding="utf-8", newline="\n")
            f_e.write(",".join(E_COLS) + "\n")
        f_e.write(",".join(str(e_row.get(c, "")) for c in E_COLS) + "\n")
        f_e.flush()
        compte["e"] += 1
        e_row = {}


def lire_console(sock):
    tampon = b""
    while not fini.is_set():
        try:
            morceau = sock.recv(4096)
        except socket.timeout:
            continue
        except OSError as err:
            ecrire_console(time.time(), f"## liaison TCP perdue : {err}")
            break
        if not morceau:
            ecrire_console(time.time(), "## la carte a fermé la console TCP")
            break
        t = time.time()
        tampon += morceau
        while b"\n" in tampon:
            brut, tampon = tampon.split(b"\n", 1)
            traiter_ligne(t, brut.decode("utf-8", errors="replace").rstrip("\r"))
    if tampon.strip():
        traiter_ligne(time.time(), tampon.decode("utf-8", errors="replace").strip())


def lire_etat():
    with open(base + "_etat.jsonl", "w", encoding="utf-8", newline="\n") as f:
        prochain = time.time()
        while not fini.is_set():
            t = time.time()
            try:
                s = get_json("/api/state")
                if isinstance(s.get("sta"), dict) and "saved" in s["sta"]:
                    s["sta"]["saved"] = "…"      # nom du réseau de la maison : jamais dans les fichiers
                f.write(json.dumps({"pc_s": round(t, 3), "pc_fin_s": round(time.time(), 3), "etat": s},
                                   ensure_ascii=False, separators=(",", ":")) + "\n")
                compte["etat"] += 1
                if s["robot"]["ok"] and s["robot"]["age"] < 1500:
                    robot_repond.set()
                else:
                    robot_repond.clear()
            except Exception as err:
                f.write(json.dumps({"pc_s": round(t, 3), "erreur": str(err)}, ensure_ascii=False) + "\n")
                compte["etat_err"] += 1
                robot_repond.clear()
            f.flush()
            # robot muet (endormi, liaison fermée) : une lecture toutes les 2 s suffit, le fichier reste petit
            prochain = max(prochain + (a.etat if robot_repond.is_set() else max(a.etat, 2.0)), time.time())
            fini.wait(max(0.02, prochain - time.time()))


def envoyer(sock, touche):
    ecrire_console(time.time(), f">> {touche}")
    sock.sendall((touche + "\n").encode("utf-8"))


def attendre(secondes):
    """Attend, en surveillant le fichier d'arrêt. Renvoie False si l'arrêt est demandé."""
    fin = time.time() + secondes
    while time.time() < fin:
        if os.path.exists(stop_path) or fini.is_set():
            return False
        time.sleep(0.05)
    return True


sock = socket.create_connection((a.adresse, 23), timeout=5)
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.settimeout(0.5)
fils = [threading.Thread(target=lire_console, args=(sock,), daemon=True)]
if a.etat > 0:
    fils.append(threading.Thread(target=lire_etat, daemon=True))
for th in fils:
    th.start()

print(f"Enregistrement : {base}_*.  Durée maximale {a.duree:.0f} s.", flush=True)
print(f"Arrêt propre : créer le fichier {stop_path}", flush=True)
csv_lance = False
try:
    attendre(0.8)   # message d'accueil de la console
    if a.csv:
        try:
            deja = bool(get_json("/api/state").get("csv"))
        except Exception:
            deja = False
        if not deja:
            envoyer(sock, "j")
            csv_lance = True
            attendre(0.5)
    continuer = True
    for touche in a.touches.split():
        envoyer(sock, touche)
        continuer = attendre(a.attente)
        if not continuer:
            break
    prochain_e = time.time()
    while continuer and time.time() - t0 < a.duree and fils[0].is_alive():
        if a.e > 0 and time.time() >= prochain_e:
            # la touche e interroge le robot : inutile, et lent pour la carte, tant qu'il ne répond pas
            if robot_repond.is_set() or a.etat <= 0:
                envoyer(sock, "e")
            prochain_e = max(prochain_e + a.e, time.time())
        continuer = attendre(0.05)
except KeyboardInterrupt:
    ecrire_console(time.time(), "## arrêt demandé au clavier")
finally:
    try:
        if csv_lance:
            envoyer(sock, "j")
            time.sleep(0.5)
        for touche in a.fin.split():
            envoyer(sock, touche)
            time.sleep(a.attente)
        time.sleep(0.5)
    except OSError as err:
        ecrire_console(time.time(), f"## touches de fin non envoyées : {err}")
    fini.set()
    for th in fils:
        th.join(timeout=4)
    try:
        sock.close()
    except OSError:
        pass
    duree = time.time() - t0
    ecrire_console(time.time(), f"## fin de l'enregistrement après {duree:.1f} s")
    for f in (f_console, f_csv, f_e):
        if f is not None:
            f.close()
    if os.path.exists(stop_path):
        os.remove(stop_path)
    print(f"Terminé après {duree:.1f} s : {compte['console']} lignes de console, {compte['csv']} lignes du journal CSV"
          f" ({compte['csv'] / duree:.1f} par seconde), {compte['e']} réponses à la touche e,"
          f" {compte['etat']} lectures de /api/state ({compte['etat_err']} en échec).", flush=True)
    print(f"Fichiers : {base}_console.txt" + (", _capteurs.csv" if compte["csv"] else "")
          + (", _e.csv" if compte["e"] else "") + (", _etat.jsonl" if a.etat > 0 else ""), flush=True)
