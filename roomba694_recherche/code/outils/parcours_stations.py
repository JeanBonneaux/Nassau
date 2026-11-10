# parcours_stations.py — conduit le robot de point en point par petits sauts, et fait un tour sur place à chaque point.
#
# S'utilise pendant qu'enregistreur.py tourne (voir pilote.py). Les points sont donnés en millimètres dans le repère de
# position du cerveau (x vers l'avant du robot à la remise à zéro, y vers sa gauche ; touche 0 pour remettre à zéro).
# Pour chaque point : le robot se tourne vers lui (sauts de rotation, le gyroscope sert de juge), avance par sauts
# d'1,3 s au plus en se réorientant si besoin, s'arrête à moins de `tolerance` mm, puis fait un tour sur place
# (le tour du firmware, touche t : il a ses propres arrêts). La position vient du cerveau (compteurs des roues et
# gyroscope) : elle dérive, c'est justement ce que la carte doit ensuite corriger.
#
# Sécurités : celles de pilote.py avant et pendant chaque saut, plus celles du firmware (arrêt 1,5 s après le dernier
# ordre, arrêt sur pare-chocs de la v6, arrêt automatique du capteur de distance). Le parcours s'arrête à la première
# alarme ou au premier refus, et le robot reste où il est.
#
# Usage : python parcours_stations.py [--vitesse 75] [--tolerance 30] [--sans-tour] -- ADRESSE PREFIXE "x1,y1;x2,y2;..."
#   PREFIXE = chemin des fichiers de l'enregistreur en cours, sans le suffixe (ex. mesures/carre_20261110_135624)
#   Le « -- » avant ADRESSE est nécessaire dès qu'une coordonnée est négative (sinon elle est prise pour une option).
# Écrit PREFIXE_stations.json : pour chaque station, la position au départ du tour et ses mesures [dixièmes de degré, mm].
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
p_.add_argument("points")
p_.add_argument("--vitesse", type=int, default=75, help="réglage de vitesse pendant le parcours (mm/s demandés)")
p_.add_argument("--tolerance", type=float, default=30.0, help="distance au point à laquelle on s'arrête, mm")
p_.add_argument("--sans-tour", action="store_true", help="ne pas faire de tour sur place aux points")
a = p_.parse_args()

cibles = [tuple(float(v) for v in c.split(",")) for c in a.points.split(";") if c.strip()]
p = Pilote(a.adresse, a.prefixe)
journal = {"cibles": cibles, "vitesse": a.vitesse, "stations": [], "sauts": [], "fin": None}
# vitesses réelles mesurées le 2026-11-10 : réglage + 21 mm/s environ jusqu'à 125 ; roues écartées de 235 mm
V_REELLE = a.vitesse + 21.0
ROT_DPS = 2 * V_REELLE / 235.0 * 57.29578


def dire(*x):
    print(*x, flush=True)


def tourner_vers(cap_cible, tol=4.0, essais=8):
    """Sauts de rotation jusqu'au cap voulu (cap cumulé du cerveau, degrés). Renvoie (réussi, raison)."""
    for _ in range(essais):
        l = p.frais()
        if l is None:
            return False, "plus de lignes du journal"
        err = cap_cible - l["cap_pos"]
        if abs(err) <= tol:
            return True, None
        r = p.saut("4" if err > 0 else "6", min(1.3, max(0.10, abs(err) / ROT_DPS - 0.04)))
        r["but"] = f"rotation de {err:+.1f}°"
        journal["sauts"].append(r)
        if "refus" in r:
            return False, "rotation refusée : " + r["refus"]
        if r.get("alarme"):
            return False, "alarme pendant une rotation : " + r["alarme"]
        time.sleep(0.35)
    l = p.frais()
    return (l is not None and abs(cap_cible - l["cap_pos"]) <= tol + 2), "cap non atteint"


def aller_a(xt, yt):
    """Va au point (xt, yt) par sauts. Renvoie (réussi, raison, distance restante)."""
    for _ in range(16):
        l = p.frais()
        if l is None:
            return False, "plus de lignes du journal", None
        dx, dy = xt - l["x_mm"], yt - l["y_mm"]
        d = math.hypot(dx, dy)
        if d <= a.tolerance:
            return True, None, d
        err = (math.degrees(math.atan2(dy, dx)) - l["cap_pos"] + 180) % 360 - 180
        if abs(err) > (4.0 if d > 120 else 8.0):
            ok, raison = tourner_vers(l["cap_pos"] + err)
            if not ok:
                return False, raison, d
            continue
        duree = min(1.3, max(0.2, (d - 8) / (V_REELLE + 6)))
        r = p.saut("8", duree, marge_mm=min(600.0, d + 250.0))
        r["but"] = f"avance vers ({xt:.0f}, {yt:.0f}), reste {d:.0f} mm"
        journal["sauts"].append(r)
        if "refus" in r:
            return False, "avance refusée : " + r["refus"], d
        if r.get("alarme"):
            return False, "alarme pendant une avance : " + r["alarme"], d
        time.sleep(0.35)
    l = p.frais()
    d = math.hypot(xt - l["x_mm"], yt - l["y_mm"]) if l else None
    return (d is not None and d <= 2 * a.tolerance), "trop de sauts", d


def faire_un_tour(nom):
    """Lance le tour sur place du firmware, attend sa fin, range ses mesures. Renvoie (réussi, raison)."""
    l0 = p.frais()
    t = json.loads(p.get("/api/tour?go=1"))
    if t.get("etat") not in (1, 2):
        return False, "tour refusé : " + str(t.get("raison", t.get("texte")))
    fin = time.time() + 45
    while time.time() < fin:
        time.sleep(0.5)
        t = json.loads(p.get("/api/tour"))
        if t.get("etat") not in (1, 2):
            break
    p.immobile()
    l1 = p.frais()
    st = {"nom": nom, "heure": time.strftime("%H:%M:%S"), "etat": t.get("texte"), "raison": t.get("raison"),
          "tourne": t.get("tourne"), "n": t.get("n"), "depart": t.get("depart"), "mesures": t.get("mesures") or t.get("points"),
          "avant": {k: l0[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm")} if l0 else None,
          "apres": {k: l1[k] for k in ("x_mm", "y_mm", "cap_pos", "us_mm")} if l1 else None}
    journal["stations"].append(st)
    ok = t.get("etat") == 3 and (t.get("n") or 0) > 50
    return ok, None if ok else f"tour arrêté : {t.get('raison')}"


def sauver():
    with open(a.prefixe + "_stations.json", "w", encoding="utf-8") as f:
        json.dump(journal, f, ensure_ascii=False)


try:
    if p.frais(attente=6) is None:
        raise SystemExit("aucune ligne récente du journal : l'enregistreur tourne-t-il, le robot répond-il ?")
    p.vitesse(a.vitesse)
    time.sleep(0.3)
    for k, (xt, yt) in enumerate(cibles):
        l = p.frais()
        dire(f"--- point {k + 1}/{len(cibles)} : ({xt:.0f}, {yt:.0f}) ; robot en ({l['x_mm']:.0f}, {l['y_mm']:.0f}), cap {l['cap_pos']:.1f}°")
        ok, raison, reste = aller_a(xt, yt)
        l = p.frais()
        dire(f"    arrivé en ({l['x_mm']:.0f}, {l['y_mm']:.0f}), à {reste if reste is None else round(reste)} mm du point"
             f" ; devant {l['us_mm']:.0f} mm" + ("" if ok else f" ; ARRÊT : {raison}"))
        if not ok:
            journal["fin"] = f"point {k + 1} : {raison}"
            break
        if not a.sans_tour:
            ok, raison = faire_un_tour(f"point {k + 1}")
            s = journal["stations"][-1] if journal["stations"] else {}
            dire(f"    tour : {s.get('tourne')}° , {s.get('n')} mesures" + ("" if ok else f" ; ARRÊT : {raison}"))
            if not ok:
                journal["fin"] = f"point {k + 1} : {raison}"
                break
        sauver()
    else:
        journal["fin"] = "parcours terminé"
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
         f" {len(journal['stations'])} tours | batterie {e['robot']['q']} mAh")
