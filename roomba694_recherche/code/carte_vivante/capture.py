# capture.py — une image de la carte vivante telle qu'un téléphone la montre, pour l'envoyer ou la garder.
#
#   python capture.py [--url http://127.0.0.1:8694/] [--sortie FICHIER.png] [--largeur 390] [--hauteur 844] [--attente 5]
#
# Ouvre la page dans Edge (ou Chrome) sans fenêtre, dans un cadre de la taille d'un téléphone, attend quelques secondes
# et enregistre l'image. La page montre le plan de l'appartement : par défaut l'image va dans plan_lidar/carte_vivante/,
# hors dépôt ; ne pas la ranger ailleurs dans le dépôt. Le serveur (serveur.py) doit tourner.
import argparse
import datetime
import os
import subprocess
import sys
import tempfile
import time

from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
PRIVE = os.path.normpath(os.path.join(ICI, "..", "..", "plan_lidar", "carte_vivante"))
NAVIGATEURS = (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe", r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
               r"C:\Program Files\Google\Chrome\Application\chrome.exe")
p_ = argparse.ArgumentParser()
p_.add_argument("--url", default="http://127.0.0.1:8694/")
p_.add_argument("--sortie", default="")
p_.add_argument("--largeur", type=int, default=390)
p_.add_argument("--hauteur", type=int, default=844)
p_.add_argument("--attente", type=float, default=5.0, help="secondes laissées à la page avant l'image")
p_.add_argument("--finesse", type=int, default=2, help="pixels d'image par pixel de téléphone")
a = p_.parse_args()
nav = next((n for n in NAVIGATEURS if os.path.exists(n)), None)
if nav is None:
    sys.exit("ni Edge ni Chrome trouvé sur ce PC")
sortie = a.sortie or os.path.join(PRIVE, "carte_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".png")
os.makedirs(os.path.dirname(os.path.abspath(sortie)), exist_ok=True)
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    # un navigateur sans fenêtre refuse les fenêtres étroites : la page est mise dans un cadre de la taille du téléphone
    cadre = os.path.join(tmp, "cadre.html")
    with open(cadre, "w", encoding="utf-8") as f:
        f.write(f'<!doctype html><body style="margin:0;background:#fff"><iframe src="{a.url}" style="border:0;display:block;'
                f'width:{a.largeur}px;height:{a.hauteur}px"></iframe>')
    brut = os.path.join(tmp, "brut.png")
    subprocess.run([nav, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", f"--user-data-dir={os.path.join(tmp, 'profil')}",
                    f"--window-size={max(a.largeur + 40, 620)},{a.hauteur + 40}", f"--force-device-scale-factor={a.finesse}",
                    f"--virtual-time-budget={int(a.attente * 1000)}", f"--screenshot={brut}", "file:///" + cadre.replace("\\", "/")],
                   check=False, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # le lanceur du navigateur rend la main tout de suite : l'image arrive une à quelques secondes plus tard
    fin, taille = time.time() + a.attente + 60.0, -1
    while time.time() < fin:
        time.sleep(0.4)
        if os.path.exists(brut):
            t = os.path.getsize(brut)
            if t > 0 and t == taille:
                break
            taille = t
    if not os.path.exists(brut):
        sys.exit("le navigateur n'a pas rendu d'image")
    with Image.open(brut) as im:
        im.crop((0, 0, a.largeur * a.finesse, a.hauteur * a.finesse)).save(sortie)
print("image :", sortie)
