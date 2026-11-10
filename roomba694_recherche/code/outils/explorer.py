# explorer.py — le PC explore : un tour sur place, le choix de la prochaine station dans l'espace libre vu par ce
# tour, le trajet par petits sauts, un nouveau tour, et ainsi de suite ; puis le retour par le même chemin.
#
# S'utilise pendant qu'enregistreur.py tourne (voir pilote.py et parcours_stations.py). Le robot doit être réveillé, en
# mode Safe, capteur de distance en mode fixe ; la position du cerveau sert de repère (touche 0 pour la remettre à zéro).
#
# Choix de la prochaine station, à `pas` mm de la station courante :
#   - la direction doit être libre d'après le tour : rien à moins de pas + 500 mm dans un cône de ±25° (une mesure
#     « rien à portée » prend la valeur médiane de ses voisines à ±15°, ou 2,5 m si elle n'a pas de voisine) ;
#   - le point visé doit être à plus de 420 mm de tout écho déjà vu (rayon du robot + 25 cm), hors des zones
#     interdites (--interdit, par exemple autour de la base), et à plus de 550 mm des stations déjà faites ;
#   - parmi les points possibles, on prend celui qui s'éloigne le plus des stations déjà faites.
# Chaque station garde en mémoire celle d'où le robot est venu : pour revenir en arrière (plus rien de libre, échec d'un
# trajet, retour final), le robot ne refait que des trajets qu'il a déjà faits.
# Si un trajet échoue (refus d'un saut, alarme), le robot recule de quelques centimètres s'il a touché, revient à la
# station d'où il partait, et cette direction n'est plus proposée.
#
# Sécurités : celles de pilote.py (contrôles avant et pendant chaque saut) et celles du firmware (arrêt 1,5 s après le
# dernier ordre, arrêt sur pare-chocs, arrêt automatique du capteur de distance, tour sur place avec ses propres arrêts).
# L'exploration s'arrête au nombre de stations demandé, s'il n'y a plus de direction libre, après trois échecs, ou si la
# batterie passe sous le seuil. Sortie du mode Safe, roue levée ou liaison perdue : arrêt immédiat, le robot reste où il est.
#
# Usage : python explorer.py [--stations 8] [--pas 800] [--vitesse 75] [--tour-v 30] [--interdit "x,y,rayon;..."]
#                            [--sans-retour] -- ADRESSE PREFIXE
# Écrit PREFIXE_stations.json (même forme que parcours_stations.py, lisible par h_carte_stations.py).
import argparse
import json
import math
import sys
import time

from pilote import Pilote

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p_ = argparse.ArgumentParser()
p_.add_argument("adresse")
p_.add_argument("prefixe")
p_.add_argument("--stations", type=int, default=8, help="nombre de stations au plus, celle de départ comprise")
p_.add_argument("--pas", type=float, default=800.0, help="distance entre deux stations, mm")
p_.add_argument("--vitesse", type=int, default=75, help="réglage de vitesse des sauts (mm/s demandés)")
p_.add_argument("--tour-v", type=int, default=30, help="vitesse de roues demandée pour les tours sur place (20 à 62 ; firmware v8)")
p_.add_argument("--interdit", default="", help="zones interdites aux stations : x,y,rayon en mm, séparées par des points-virgules")
p_.add_argument("--sans-retour", action="store_true", help="ne pas revenir au point de départ à la fin")
p_.add_argument("--batterie-min", type=int, default=1300, help="charge en mAh sous laquelle on arrête")
a = p_.parse_args()

p = Pilote(a.adresse, a.prefixe)
interdits = [tuple(float(v) for v in z.split(",")) for z in a.interdit.split(";") if z.strip()]
journal = {"mode": "exploration", "pas": a.pas, "vitesse": a.vitesse, "interdits": interdits, "stations": [], "sauts": [],
           "choix": [], "echecs": [], "parents": {}, "fin": None}
V_REELLE = a.vitesse + 21.0                      # mesuré le 2026-11-10 : réglage + 21 mm/s environ
ROT_DPS = 2 * V_REELLE / 235.0 * 57.29578
DX = 27.0                                        # capteur de distance en avant du centre du robot, mm
echos = []                                       # tous les échos vus, dans le repère du cerveau : (x, y)
parent = {}                                      # nom d'une station -> station d'où le robot y est venu
bloques = {}                                     # nom d'une station -> directions qui ont échoué depuis elle
ARRET_NET = ("Safe", "roue levée", "journal")    # raisons après lesquelles on ne tente plus aucun mouvement


def dire(*x):
    print(*x, flush=True)


def sauver():
    with open(a.prefixe + "_stations.json", "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False)


def tourner_vers(cap_cible, tol=4.0, essais=8):
    """Sauts de rotation jusqu'au cap voulu. Le robot est rond et tourne sur place : les capteurs optiques ne bloquent pas."""
    for _ in range(essais):
        l = p.frais()
        if l is None:
            return False, "plus de lignes du journal"
        err = cap_cible - l["cap_pos"]
        if abs(err) <= tol:
            return True, None
        r = p.saut("4" if err > 0 else "6", min(1.3, max(0.10, abs(err) / ROT_DPS - 0.04)), lb_repos=5000, lb_max=5000)
        r["but"] = f"rotation de {err:+.1f}°"
        journal["sauts"].append(r)
        if "refus" in r:
            return False, "rotation refusée : " + r["refus"]
        if r.get("alarme"):
            return False, "alarme pendant une rotation : " + r["alarme"]
        time.sleep(0.3)
    l = p.frais()
    return (l is not None and abs(cap_cible - l["cap_pos"]) <= tol + 2), "cap non atteint"


def aller_a(xt, yt, tolerance=30.0):
    """Va au point (xt, yt) par sauts. Renvoie (réussi, raison)."""
    for _ in range(24):
        l = p.frais()
        if l is None:
            return False, "plus de lignes du journal"
        dx, dy = xt - l["x_mm"], yt - l["y_mm"]
        d = math.hypot(dx, dy)
        if d <= tolerance:
            return True, None
        err = (math.degrees(math.atan2(dy, dx)) - l["cap_pos"] + 180) % 360 - 180
        if abs(err) > (4.0 if d > 120 else 8.0):
            ok, raison = tourner_vers(l["cap_pos"] + err)
            if not ok:
                return False, raison
            continue
        r = p.saut("8", min(1.3, max(0.2, (d - 8) / (V_REELLE + 6))), marge_mm=min(600.0, d + 250.0))
        r["but"] = f"avance vers ({xt:.0f}, {yt:.0f}), reste {d:.0f} mm"
        journal["sauts"].append(r)
        if "refus" in r:
            return False, "avance refusée : " + r["refus"]
        if r.get("alarme"):
            return False, "alarme pendant une avance : " + r["alarme"]
        time.sleep(0.3)
    return False, "trop de sauts"


def faire_un_tour(nom):
    """Tour sur place du firmware à la vitesse --tour-v. Renvoie (station, raison) ; station vaut None en cas d'échec."""
    l0 = p.frais()
    t = json.loads(p.get(f"/api/tour?go=1&v={a.tour_v}"))
    if t.get("etat") not in (1, 2):
        return None, "tour refusé : " + str(t.get("raison", t.get("texte")))
    fin = time.time() + 70
    while time.time() < fin:
        time.sleep(0.5)
        t = json.loads(p.get("/api/tour"))
        if t.get("etat") not in (1, 2):
            break
    p.immobile()
    l1 = p.frais()
    st = {"nom": nom, "heure": time.strftime("%H:%M:%S"), "etat": t.get("texte"), "raison": t.get("raison"), "tourne": t.get("tourne"),
          "n": t.get("n"), "roues": t.get("roues"), "duree_ms": t.get("duree_ms"), "depart": t.get("depart"), "mesures": t.get("points"),
          "avant": {k: l0[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm")} if l0 else None,
          "apres": {k: l1[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm")} if l1 else None}
    if t.get("etat") != 3 or (t.get("n") or 0) < 50:
        return None, f"tour arrêté : {t.get('raison')}"
    journal["stations"].append(st)
    x0, y0, c0 = st["depart"]
    for d10, mm in st["mesures"]:
        if mm > 0:
            ang = math.radians(c0 + d10 / 10.0)
            echos.append((x0 + (mm + DX) * math.cos(ang), y0 + (mm + DX) * math.sin(ang)))
    return st, None


def profil(st):
    """Distance libre vue par un tour, par direction du monde (tous les 10°), en mm."""
    c0 = st["depart"][2]
    ang = [(c0 + d10 / 10.0) % 360.0 for d10, mm in st["mesures"]]
    r = [float(mm) for d10, mm in st["mesures"]]
    plein = []
    for i, ri in enumerate(r):
        if ri > 0:
            plein.append(ri + DX)
            continue
        vois = sorted(r[k] for k in range(len(r)) if r[k] > 0 and abs((ang[k] - ang[i] + 180) % 360 - 180) <= 15)
        plein.append((vois[len(vois) // 2] + DX) if vois else 2500.0)
    libre = {}
    for phi in range(0, 360, 10):
        v = [plein[k] for k in range(len(r)) if abs((ang[k] - phi + 180) % 360 - 180) <= 25]
        libre[phi] = min(v) if v else 0.0
    return libre


def choisir(st, note=True):
    """Prochaine station depuis la station st : (x, y, direction, distance libre) ou None."""
    x0, y0 = st["depart"][0], st["depart"][1]
    libre = profil(st)
    faits = [(s["depart"][0], s["depart"][1]) for s in journal["stations"]]
    meilleurs = []
    for phi, f in libre.items():
        if f < a.pas + 500 or any(abs((phi - b + 180) % 360 - 180) < 35 for b in bloques[st["nom"]]):
            continue
        cx, cy = x0 + a.pas * math.cos(math.radians(phi)), y0 + a.pas * math.sin(math.radians(phi))
        if any(math.hypot(cx - ex, cy - ey) < 420 for ex, ey in echos):
            continue
        if any(math.hypot(cx - zx, cy - zy) < zr for zx, zy, zr in interdits):
            continue
        eloigne = min(math.hypot(cx - fx, cy - fy) for fx, fy in faits)
        if eloigne < 550:
            continue
        meilleurs.append((eloigne + 0.2 * min(f, 2500.0), cx, cy, phi, f))
    if not meilleurs:
        return None
    meilleurs.sort(reverse=True)
    if note:
        journal["choix"].append({"depuis": st["nom"], "candidats": [[round(m[1]), round(m[2]), m[3], round(m[4])] for m in meilleurs[:6]]})
    return meilleurs[0][1:]


def remonter(depuis, jusqu_a_libre):
    """Revient de station en station vers le départ, par les trajets déjà faits. Si jusqu_a_libre, s'arrête à la première
    station qui a encore une direction libre. Renvoie (station atteinte ou None, raison)."""
    s = depuis
    while True:
        if jusqu_a_libre and choisir(s, note=False) is not None:
            return s, None
        par = parent.get(s["nom"])
        if par is None:
            return (None, "plus de direction libre") if jusqu_a_libre else (s, None)
        ok, raison = aller_a(par["depart"][0], par["depart"][1], tolerance=50.0)
        if not ok:
            return None, "retour vers la station " + par["nom"] + " impossible : " + str(raison)
        s = par


echec_total = 0
courant = None
try:
    if p.frais(attente=6) is None:
        raise SystemExit("aucune ligne récente du journal : l'enregistreur tourne-t-il, le robot répond-il ?")
    p.vitesse(a.vitesse)
    time.sleep(0.3)
    st, raison = faire_un_tour("0")
    if st is None:
        raise SystemExit("premier tour impossible : " + str(raison))
    dire(f"station 0 en ({st['depart'][0]:.0f}, {st['depart'][1]:.0f}) : tour de {st['tourne']}° en {st['duree_ms'] / 1000:.0f} s, {st['n']} mesures")
    bloques["0"] = []
    courant = st
    while journal["fin"] is None:
        if len(journal["stations"]) >= a.stations:
            journal["fin"] = "nombre de stations atteint"
            break
        if echec_total >= 3:
            journal["fin"] = "trois échecs"
            break
        e = p.etat()
        if e["robot"]["q"] < a.batterie_min:
            journal["fin"] = f"batterie à {e['robot']['q']} mAh"
            break
        c = choisir(courant)
        if c is None:
            dire(f"  plus rien de libre depuis la station {courant['nom']} : retour en arrière")
            s, raison = remonter(courant, jusqu_a_libre=True)
            if s is None:
                journal["fin"] = raison
                if raison == "plus de direction libre":
                    courant = journal["stations"][0]      # remonter() a ramené le robot à la station 0
                else:
                    courant = None
                break
            courant = s
            continue
        cx, cy, phi, f = c
        dire(f"  depuis la station {courant['nom']} : direction {phi}° libre sur {f / 10:.0f} cm, prochaine station visée en ({cx:.0f}, {cy:.0f})")
        ok, raison = aller_a(cx, cy)
        if not ok:
            echec_total += 1
            l = p.frais()
            journal["echecs"].append({"depuis": courant["nom"], "direction": phi, "raison": raison,
                                      "position": [l["x_mm"], l["y_mm"]] if l else None})
            dire(f"    ÉCHEC : {raison}" + (f" ; robot en ({l['x_mm']:.0f}, {l['y_mm']:.0f})" if l else ""))
            bloques[courant["nom"]].append(phi)
            if l is None or any(m in str(raison) for m in ARRET_NET):
                journal["fin"] = "arrêt : " + str(raison)
                courant = None
                break
            if "pare-chocs" in str(raison):
                r = p.saut("2", 0.9, lb_repos=5000, lb_max=5000)
                r["but"] = "recul après un contact"
                journal["sauts"].append(r)
                time.sleep(0.4)
            ok, raison2 = aller_a(courant["depart"][0], courant["depart"][1], tolerance=60.0)
            if not ok:
                journal["fin"] = "retour à la station impossible après un échec : " + str(raison2)
                courant = None
                break
            continue
        nom = str(len(journal["stations"]))
        st, raison = faire_un_tour(nom)
        if st is None:
            journal["fin"] = "tour impossible : " + str(raison)
            courant = None
            break
        bloques[nom] = []
        parent[nom] = courant
        journal["parents"][nom] = courant["nom"]
        dire(f"station {nom} en ({st['depart'][0]:.0f}, {st['depart'][1]:.0f}) : tour de {st['tourne']}° en {st['duree_ms'] / 1000:.0f} s, {st['n']} mesures")
        courant = st
        sauver()
    # retour au point de départ par les trajets déjà faits, puis un dernier tour (sauf après un arrêt net)
    if not a.sans_retour and courant is not None:
        s, raison = remonter(courant, jusqu_a_libre=False)
        if s is None:
            journal["fin"] += " ; retour interrompu : " + str(raison)
        else:
            st, raison = faire_un_tour("retour")
            journal["fin"] += " ; retour au départ fait" + ("" if st else " sans tour final : " + str(raison))
            if st:
                dire(f"retour au départ en ({st['depart'][0]:.0f}, {st['depart'][1]:.0f}) : tour de {st['tourne']}°, {st['n']} mesures")
finally:
    try:
        p.touche("5")
        p.vitesse(150)
    except Exception as err:
        dire("réglages de fin non envoyés :", err)
    sauver()
    e = p.etat()
    dire(f"fin : {journal['fin']} | mode {e['robot']['mode']} | roues {'en marche' if e['driving'] else 'arrêtées'} | pare-chocs {e['robot']['bump']}"
         f" | position ({e['pose']['x']}, {e['pose']['y']}), cap {e['pose']['cap']}° | réflexe {e['reflexe']} | {len(journal['sauts'])} sauts,"
         f" {len(journal['stations'])} tours, {len(journal['echecs'])} échecs | batterie {e['robot']['q']} mAh")
