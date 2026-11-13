# serveur.py — la « carte vivante » du Roomba 694 : une page qui montre le plan quadrillé de l'appartement et le
# robot qui s'y déplace, pendant un essai (en direct) ou d'après un enregistrement (en rejeu).
#
#   python serveur.py                         suit l'enregistrement le plus récent de mesures/ (en direct)
#   python serveur.py --rejeu NOM             rejoue mesures/NOM_capteurs.csv et les fichiers de navigation du même nom
#                     [--vitesse 8] [--debut HH:MM:SS] [--pause]
# puis ouvrir http://127.0.0.1:8694 sur ce PC.
#
# Ce serveur ne fait que lire des fichiers : il n'envoie rien au robot ni au cerveau, et rien hors de ce PC. Il
# n'écoute que sur 127.0.0.1 ; l'option --ouvert le rend visible des autres appareils du réseau de la maison (le
# téléphone), ce qui montre le plan de l'appartement à tout appareil de ce réseau : à ne faire qu'avec l'accord de
# l'utilisateur. Le plan reste dans plan_lidar/ (hors dépôt) ; la page le demande au serveur, il n'est copié nulle part.
import argparse
import datetime
import ipaddress
import json
import os
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(ICI, "..", ".."))
sys.path.insert(0, ICI)
import sources  # noqa: E402
import suivi as suivi_mod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p_ = argparse.ArgumentParser(description="Carte vivante du Roomba 694 : serveur local, lecture seule.")
p_.add_argument("--rejeu", default="", help="nom ou chemin d'un enregistrement (sans _capteurs.csv) à rejouer ; sans cette option : en direct")
p_.add_argument("--vitesse", type=float, default=8.0, help="rejeu : secondes d'enregistrement par seconde")
p_.add_argument("--debut", default="", help="rejeu : heure de départ, HH:MM:SS")
p_.add_argument("--pause", action="store_true", help="rejeu : démarrer en pause")
p_.add_argument("--prefixe", default="", help="direct : suivre cet enregistrement-là au lieu du plus récent")
p_.add_argument("--mesures", default=os.path.join(RACINE, "mesures"))
p_.add_argument("--plan", default=os.path.join(RACINE, "plan_lidar", "plan_lidar.png"))
p_.add_argument("--zones", default=os.path.join(RACINE, "plan_lidar", "plan_lidar_zones.jpg"), help="le plan où les pièces inaccessibles sont barrées de rouge")
p_.add_argument("--px-par-m", type=float, default=53.0)
p_.add_argument("--base", default="442,27", help="pixel de la base de recharge sur le plan")
p_.add_argument("--port", type=int, default=8694)
p_.add_argument("--ouvert", action="store_true", help="écouter aussi sur l'adresse de ce PC sur le réseau de la maison (accord de l'utilisateur requis), pour le téléphone")
p_.add_argument("--cerveau", default="192.168.18.25", help="adresse du cerveau : sert seulement à trouver la carte réseau de la maison pour --ouvert, rien ne lui est envoyé")
a = p_.parse_args()


def chemin_enregistrement(nom):
    nom = nom[:-len("_capteurs.csv")] if nom.endswith("_capteurs.csv") else nom
    for c in (nom, os.path.join(a.mesures, nom)):
        if os.path.exists(c + "_capteurs.csv"):
            return os.path.abspath(c)
    raise SystemExit(f"enregistrement introuvable : {nom}_capteurs.csv")


# ---------------------------------------------------------------- le plan et le décor fixe
try:
    with open(a.plan, "rb") as f:
        PLAN = f.read()
except OSError as err:
    raise SystemExit(f"plan introuvable ({err}) : il est attendu dans plan_lidar/, hors dépôt")
from PIL import Image  # noqa: E402

with Image.open(a.plan) as im:
    W, H = im.size
GR = suivi_mod.grille_mod.Grille(a.px_par_m, W, H)
zones = []
try:                                                              # les pièces barrées de rouge, comme dans carte_grille.py
    import numpy as np
    from scipy import ndimage
    Z = np.asarray(Image.open(a.zones).convert("RGB")).astype(int)
    rouge = (Z[..., 0] > Z[..., 1] + 60) & (Z[..., 0] > Z[..., 2] + 60)
    lab, n = ndimage.label(ndimage.binary_dilation(rouge, iterations=3))
    for k in range(1, n + 1):
        ys, xs = np.where(lab == k)
        if len(xs) >= 400:
            zones.append([int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1])
except Exception as err:                                          # pas de fichier, pas de scipy : la carte s'en passe
    print("zones inaccessibles non dessinées :", err, flush=True)
DECOR = {"W": W, "H": H, "px_par_m": a.px_par_m, "case": GR.c, "lettres": suivi_mod.grille_mod.LETTRES, "n_col": GR.n_col, "n_lig": GR.n_lig,
         "base": [float(x) for x in a.base.split(",")] if a.base else None, "zones": zones,
         "rayon": suivi_mod.RAYON * a.px_par_m / 1000.0, "dx_capteur": suivi_mod.DX_CAPTEUR * a.px_par_m / 1000.0}


def fabrique():
    su = suivi_mod.Suivi(a.px_par_m, W, H)
    su.fixer("decor", DECOR)
    return su


# ---------------------------------------------------------------- la source : direct ou rejeu
verrou = threading.Lock()
if a.rejeu:
    debut = None
    SOURCE = sources.Rejeu(chemin_enregistrement(a.rejeu), fabrique, vitesse=a.vitesse, pause=a.pause)
    if a.debut:
        SOURCE.aller(sources.t_heure(a.debut, SOURCE.T0))
else:
    SOURCE = sources.Direct(a.mesures, fabrique, prefixe=chemin_enregistrement(a.prefixe) if a.prefixe else None)


def boucle():
    derniere_erreur = ""
    while True:
        t = time.time()
        try:
            with verrou:
                SOURCE.tick(t)
        except Exception as err:                                  # un fichier illisible un instant ne doit pas arrêter la carte
            texte = f"{type(err).__name__} : {err}"
            if texte != derniere_erreur:
                print(datetime.datetime.now().strftime("%H:%M:%S"), "erreur de lecture :", texte, flush=True)
                derniere_erreur = texte
        time.sleep(max(0.01, 0.1 - (time.time() - t)))


MEMOIRE = sources.Memoire(a.mesures, lambda: suivi_mod.Suivi(a.px_par_m, W, H), os.path.join(RACINE, "plan_lidar", "carte_vivante", "memoire_obstacles.json"))


def memoire():
    """Dans un fil à part, au lancement puis à chaque nouvel enregistrement : ce que le robot a touché ou frôlé lors des
    essais précédents est remis sur la carte (le premier calcul prend quelques secondes, les suivants sont gardés)."""
    faite = None
    while True:
        with verrou:
            e, prefixe = SOURCE.epoque, SOURCE.prefixe
        if prefixe and (e, prefixe) != faite:
            try:
                anciens = MEMOIRE.calculer(prefixe)
                with verrou:
                    if SOURCE.epoque == e:
                        SOURCE.suivi.fixer("anciens", anciens)
                        faite = (e, prefixe)
            except Exception as err:
                print(datetime.datetime.now().strftime("%H:%M:%S"), "mémoire des obstacles non calculée :", type(err).__name__, err, flush=True)
                faite = (e, prefixe)
        time.sleep(1.0)


def reponse_suite(e_client, v_client):
    with verrou:
        su = SOURCE.suivi
        maintenant = SOURCE.horloge(time.time())
        h = {"mode": SOURCE.mode, "t": round(maintenant, 2), "h": suivi_mod.heure_de(maintenant)}
        if SOURCE.mode == "rejeu":
            h.update({"vitesse": SOURCE.vitesse, "pause": SOURCE.pause, "t0": SOURCE.T0, "t1": SOURCE.T1})
        d = {"e": SOURCE.epoque, "v": su.V, "nt": su.n_troncons, "robot": su.robot(maintenant), "horloge": h,
             "obj": su.depuis(v_client if e_client == SOURCE.epoque else 0)}
        return json.dumps(d, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------- le serveur
def adresse_maison():
    """L'adresse de ce PC sur le réseau de la maison : celle de la carte réseau par laquelle il rejoindrait le cerveau.
    Rien n'est envoyé au cerveau : une prise UDP « connectée » ne fait que choisir la route."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect((a.cerveau, 80))
        return s.getsockname()[0]
    finally:
        s.close()


# Avec --ouvert, le serveur écoute en plus sur cette adresse-là seulement (pas sur toutes les cartes réseau du PC) et ne
# sert que des appareils d'un réseau privé : le plan ne sort pas de la maison.
MAISON = None
if a.ouvert:
    try:
        MAISON = ipaddress.ip_address(adresse_maison())
    except (OSError, ValueError) as err:
        raise SystemExit(f"--ouvert : adresse de ce PC sur le réseau de la maison introuvable ({err})")
    if MAISON.is_loopback or not MAISON.is_private:
        raise SystemExit(f"--ouvert : {MAISON} n'est pas une adresse de réseau privé ; le serveur n'est pas ouvert")
HOTES = {"127.0.0.1", "localhost"} | ({str(MAISON)} if MAISON else set())
CSP = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'"


PIXEL = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")


class Page(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "CarteVivante"

    def log_message(self, *args):
        pass

    def envoyer(self, code, type_, corps, cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", type_)
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Referrer-Policy", "no-referrer")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        # une page d'un autre site ne doit pas pouvoir lire le plan en visant ce serveur sous un autre nom
        hote = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        try:
            client = ipaddress.ip_address(self.client_address[0])
            permis = client.is_loopback or (MAISON is not None and client.is_private)      # ce PC, ou un appareil de la maison
        except ValueError:
            permis = False
        if not permis or hote not in HOTES or self.headers.get("Origin") not in (None, f"http://{self.headers.get('Host')}"):
            return self.envoyer(403, "text/plain; charset=utf-8", "refusé".encode("utf-8"))
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                with open(os.path.join(ICI, "page.html"), "rb") as f:
                    return self.envoyer(200, "text/html; charset=utf-8", f.read())
            if u.path == "/plan.png":
                return self.envoyer(200, "image/png", PLAN, cache="private, max-age=3600")
            if u.path == "/api/attendre":                         # pour capture.py : une image d'un pixel, rendue après N secondes
                time.sleep(max(0.0, min(20.0, float(q.get("s", ["3"])[0]))))
                return self.envoyer(200, "image/gif", PIXEL)
            if u.path == "/api/suite":
                return self.envoyer(200, "application/json; charset=utf-8", reponse_suite(int(q.get("e", ["-1"])[0]), int(q.get("v", ["0"])[0])))
            if u.path == "/api/rejeu" and SOURCE.mode == "rejeu":
                with verrou:
                    if "vitesse" in q:
                        SOURCE.vitesse = max(0.25, min(240.0, float(q["vitesse"][0])))
                    if "pause" in q:
                        SOURCE.pause = q["pause"][0] == "1"
                    if "aller" in q:                              # fraction de l'enregistrement, de 0 à 1
                        SOURCE.aller(SOURCE.T0 + max(0.0, min(1.0, float(q["aller"][0]))) * (SOURCE.T1 - SOURCE.T0))
                return self.envoyer(200, "application/json; charset=utf-8", b"{}")
        except (ValueError, OSError) as err:
            return self.envoyer(400, "text/plain; charset=utf-8", str(err).encode("utf-8"))
        self.envoyer(404, "text/plain; charset=utf-8", "inconnu".encode("utf-8"))


if __name__ == "__main__":
    threading.Thread(target=boucle, daemon=True).start()
    threading.Thread(target=memoire, daemon=True).start()
    serveurs = []
    for hote in ["127.0.0.1"] + ([str(MAISON)] if MAISON else []):
        srv = ThreadingHTTPServer((hote, a.port), Page)
        srv.daemon_threads = True
        serveurs.append(srv)
    for srv in serveurs[1:]:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    quoi = f"rejeu de {os.path.basename(SOURCE.prefixe)} (× {a.vitesse:g})" if a.rejeu else f"en direct, dossier {a.mesures}"
    print(f"Carte vivante : {quoi}", flush=True)
    print(f"Sur ce PC : http://127.0.0.1:{a.port}", flush=True)
    if MAISON:
        print(f"Sur le téléphone, relié au même Wi-Fi que ce PC : http://{MAISON}:{a.port}", flush=True)
    try:
        serveurs[0].serve_forever()
    except KeyboardInterrupt:
        pass
