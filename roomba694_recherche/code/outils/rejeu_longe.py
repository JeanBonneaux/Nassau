# rejeu_longe.py — redonne à un suivi les lectures d'un trajet enregistré par longe_mur.py (PREFIXE_longe.jsonl), sans le
# robot, et montre le cap qu'il aurait demandé à côté de celui qui a été demandé ce jour-là.
#
#   python rejeu_longe.py CHEMIN/NOM_longe.jsonl [--cote g|d] [--ecart MM] [--suivi mur|lateral] [--depuis MM] [--tout]
#
# À lire avec prudence : le robot a roulé sous les ordres du suivi du jour. Dès que le suivi rejoué aurait demandé autre
# chose, le robot aurait été ailleurs et les lectures suivantes auraient été différentes. Le rejeu dit ce que le suivi
# COMPREND des mêmes lectures (où est le mur, quel est son axe, quelle autre paroi il voit), pas le trajet qu'il aurait
# fait ; pour cela : essai_profil_mur.py.
import argparse
import json
import statistics
import sys

from suivi_lateral import SuiviLateral
from suivi_mur import SuiviMur

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser()
p.add_argument("fichier")
p.add_argument("--cote", choices=["g", "d"], default=None, help="par défaut : lu dans l'enregistrement (angle du capteur)")
p.add_argument("--ecart", type=float, default=0.0, help="consigne, mm (0 : la médiane des lectures à l'arrêt avant le départ)")
p.add_argument("--suivi", choices=["mur", "lateral"], default="mur")
p.add_argument("--depuis", type=float, default=0.0, help="n'afficher qu'à partir de ce chemin, mm")
p.add_argument("--tout", action="store_true", help="une ligne par lecture (sinon une tous les 50 mm environ)")
p.add_argument("--gain", type=float, default=1.0)
p.add_argument("--saut", type=float, default=30.0)
p.add_argument("--adopte", type=float, default=400.0)
p.add_argument("--avance-capteur", type=float, default=130.0)
a = p.parse_args()

L = [json.loads(x) for x in open(a.fichier, encoding="utf-8") if x.strip()]
avant = [e for e in L if e.get("etape") == "cote_arret_avant" and e.get("a") in (90, -90) and (e.get("mm") or 0) > 0]
longe = [e for e in L if e.get("etape") == "longe"]
if not longe:
    sys.exit("pas de phase « longe » dans ce fichier")
angle = next((e["a"] for e in longe if e.get("a") in (90, -90)), -90)
cote = a.cote or ("g" if angle > 0 else "d")
d0 = statistics.median(e["mm"] for e in avant) if avant else None
ecart = a.ecart or d0 or statistics.median(e["mm"] for e in longe[:5])
print("mur à %s ; lecture à l'arrêt : %s mm ; consigne : %.0f mm ; suivi rejoué : %s" % (
    "gauche" if cote == "g" else "droite", d0, ecart, a.suivi))
if a.suivi == "mur":
    suivi = SuiviMur(cote, ecart, gain=a.gain, saut=a.saut, adopte=a.adopte, avance_capteur=a.avance_capteur)
    suivi.amorce(d0)
else:
    suivi = SuiviLateral(axe=0.0, gain=a.gain, cap_max=10.0, fenetre=600.0, portee=2000.0, v_max=100, v_serre=80, rayon=150.0,
                         mediane=5, pente_min=400.0)
    suivi.pose = (ecart, ecart)
vus, prec, v_est, dernier = set(), None, 0.0, -1e9
pire = 0.0
for e in longe:
    s = e["fait_mm"]
    if prec is not None and e["t"] > prec[0]:
        v_est = (s - prec[1]) / (e["t"] - prec[0])
    prec = (e["t"], s)
    if e.get("a") != angle or (e.get("mm_age") or 9999) >= 400:
        continue
    tm = round((e["ms"] - e["mm_age"]) / 20.0)
    if tm in vus:
        continue
    vus.add(tm)
    lec = e["mm"] if 0 < e["mm"] <= 2000 else None
    s_m = s - v_est * e["mm_age"] / 1000.0
    cap = e.get("fait_deg") or 0.0
    if a.suivi == "mur":
        cv, _ = suivi.pas(s_m, cap, lec)
        plus = " ; mur à %4.0f mm, %-6s" % (suivi.dist, suivi.etat)
    else:
        g, d = (lec, None) if cote == "g" else (None, lec)
        cv, _ = suivi.pas(s_m, cap, g, d)
        plus = ""
    if s_m >= a.depuis:
        pire = max(pire, abs(cv))
        if a.tout or s_m - dernier >= 50.0:
            dernier = s_m
            print("  %5.0f mm : lu %5s ; cap du robot %+6.1f° ; demandé ce jour-là %+6.1f° ; rejoué %+6.1f° (axe %+5.1f°)%s" % (
                s_m, lec, cap, e.get("cv") or 0.0, cv, suivi.axe, plus))
print("cap le plus fort demandé par le suivi rejoué : %.1f°" % pire)
if a.suivi == "mur":
    print("autres parois vues : %d avancée(s), %d recul(s) ou renfoncement(s), %d ouverture(s), %d prise(s) pour le mur ; %.0f mm tenus à l'estime" % (
        suivi.n_pres, suivi.n_loin, suivi.n_ouvert, suivi.n_adopte, suivi.tenu_mm))
