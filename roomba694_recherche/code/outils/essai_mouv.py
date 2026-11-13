# essai_mouv.py — essais des mouvements exécutés par le cerveau (firmware v10, /api/mouv), un mouvement à la fois.
#
# S'utilise pendant qu'enregistreur.py tourne (comme pilote.py), robot en mode Safe, capteur de distance en mode fixe :
#   python code/outils/essai_mouv.py ADRESSE PREFIXE rot=30 rot=-30 av=100 av=500
#   python code/outils/essai_mouv.py ADRESSE PREFIXE --pilote av=500      passe par Pilote.avance et Pilote.tourne,
#                                                                         comme le fait explorer3.py
# Un mouvement s'écrit rot=DEG (positif : à gauche), av=MM (négatif : recul) ou av=MM,cap=DEG (changement de cap en
# roulant). --v fixe la vitesse des roues en mm/s.
#
# Pour chaque mouvement le programme affiche ce que le cerveau annonce (/api/mouv), puis ce que montre le journal de
# l'enregistreur entre le départ et l'arrêt complet : rotation au gyroscope, chemin aux compteurs des roues, écart en
# travers, vitesse la plus forte, durée, dépassement. Il s'arrête au premier mouvement refusé ou interrompu.
#
# Ce programme n'ajoute aucune sécurité à celles du cerveau, sauf l'arrêt (stop) sur une alarme du journal
# (pare-chocs, roue levée, sortie du mode Safe, capteur optique très fort pendant une avance).
import argparse
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilote import Pilote, MM_PAR_PAS, ENTRAXE_MM, w16      # noqa: E402


def mesure(seg, rotation, but, cap_rel):
    """Ce que le journal montre d'un mouvement. seg : lignes du départ (robot arrêté) à l'arrêt complet."""
    a, b = seg[0], seg[-1]
    dg = w16(b["enc_g"] - a["enc_g"]) * MM_PAR_PAS
    dd = w16(b["enc_d"] - a["enc_d"]) * MM_PAR_PAS
    caps = [l["cap_pos"] - a["cap_pos"] for l in seg]
    c = math.radians(a["cap_pos"])
    dx, dy = b["x_mm"] - a["x_mm"], b["y_mm"] - a["y_mm"]
    bouge = [k for k in range(1, len(seg)) if seg[k]["enc_g"] != seg[k - 1]["enc_g"] or seg[k]["enc_d"] != seg[k - 1]["enc_d"]]
    v_max = 0.0
    for k in range(1, len(seg)):
        dt = (seg[k]["ms"] - seg[k - 1]["ms"]) / 1000.0
        if dt > 0.005:
            pas = (w16(seg[k]["enc_g"] - seg[k - 1]["enc_g"]) + w16(seg[k]["enc_d"] - seg[k - 1]["enc_d"])) / 2.0
            v_max = max(v_max, abs(pas) * MM_PAR_PAS / dt)
    r = {
        "lignes": len(seg),
        "duree_s": round((seg[bouge[-1]]["ms"] - seg[bouge[0] - 1]["ms"]) / 1000.0, 2) if bouge else 0.0,
        "rot_gyro": round(caps[-1], 1),
        "rot_roues": round(math.degrees((dd - dg) / ENTRAXE_MM), 1),
        "chemin_roues_mm": round((dg + dd) / 2.0, 1),
        "le_long_mm": round(dx * math.cos(c) + dy * math.sin(c), 1),
        "en_travers_mm": round(-dx * math.sin(c) + dy * math.cos(c), 1),          # positif : à gauche du cap de départ
        "v_max_mm_s": round(v_max, 0),
        "rot_max_dps": round(max(abs(l["rot_dps"]) for l in seg), 1),
        "us_avant": a["us_mm"], "us_apres": b["us_mm"],
    }
    if rotation:
        r["erreur_deg"] = round(caps[-1] - but, 1)
        extreme = max(caps) if but > 0 else min(caps)
        r["depassement_deg"] = round(max(0.0, abs(extreme) - abs(but)), 1)
    else:
        r["erreur_mm"] = round(abs((dg + dd) / 2.0) - abs(but), 1)
        r["cap_final_deg"] = round(caps[-1] - cap_rel, 1)                           # écart au cap demandé, à l'arrêt
        r["cap_ecart_max_deg"] = round(max(abs(x) for x in caps), 1) if abs(cap_rel) < 0.5 else None
    return r


def direct(p, requete, rotation, recul):
    """Envoie la requête au cerveau et attend la fin du mouvement. Renvoie (réponse du cerveau, lignes, alarme du PC)."""
    if p.frais() is None:
        return {"etat": 3, "raison": "aucune ligne récente du journal (enregistreur arrêté ? robot muet ?)"}, None, None
    i0 = len(p.lignes) - 1
    m = json.loads(p.get("/api/mouv?" + requete))
    if m.get("etat") != 1:
        return m, None, None
    t0 = time.time()
    vu, alarme = i0, None
    while time.time() - t0 < 70.0:
        p.lire()
        for l in p.lignes[vu + 1:]:
            alarme = Pilote.alarme(l, lb_max=5000 if rotation else 400, recul=recul)
            if alarme:
                break
        vu = len(p.lignes) - 1
        if alarme:
            p.get("/api/mouv?stop=1")
            break
        m = json.loads(p.get("/api/mouv"))
        if m.get("etat") != 1:
            break
        time.sleep(0.1)
    else:
        p.get("/api/mouv?stop=1")
    p.immobile()
    time.sleep(0.5)
    p.lire()
    return json.loads(p.get("/api/mouv")), p.lignes[i0:], alarme


def main():
    ap = argparse.ArgumentParser(description="Essais des mouvements exécutés par le cerveau (firmware v10)")
    ap.add_argument("adresse")
    ap.add_argument("prefixe", help="préfixe des fichiers de l'enregistreur en cours (mesures/NOM_date_heure)")
    ap.add_argument("mouvements", nargs="+", help="rot=DEG, av=MM ou av=MM,cap=DEG")
    ap.add_argument("--pilote", action="store_true", help="passer par Pilote.avance et Pilote.tourne (contrôles du PC en plus)")
    ap.add_argument("--v", type=int, default=0, help="vitesse des roues en mm/s (défaut : celle du cerveau)")
    ap.add_argument("--marge", type=int, default=400, help="avec --pilote : obstacle devant à moins de tant de mm = arrêt")
    ap.add_argument("--pause", type=float, default=1.5, help="secondes entre deux mouvements")
    a = ap.parse_args()

    p = Pilote(a.adresse, a.prefixe)
    p.lire()
    if not p.sait_mouv():
        sys.exit("Le cerveau ne propose pas /api/mouv (firmware antérieur à la v10).")
    for texte in a.mouvements:
        champs = dict(c.split("=", 1) for c in texte.split(","))
        rotation = "rot" in champs
        but = float(champs["rot"] if rotation else champs["av"])
        cap_rel = float(champs.get("cap", 0.0))
        l0 = p.frais()
        if l0 is None:
            sys.exit("Aucune ligne récente du journal : l'enregistreur tourne-t-il ? le robot répond-il ?")
        i0 = len(p.lignes) - 1
        if a.pilote:
            if rotation:
                r = p.tourne(but, vide_min=150)
            elif but < 0:
                sys.exit("--pilote : pas de recul (Pilote.saut s'en charge).")
            else:
                r = p.avance(but, marge_mm=a.marge, vide_min=150, cap_rel=cap_rel)
            if "refus" in r:
                print(f"{texte} : REFUSÉ — {r['refus']}")
                break
            time.sleep(0.5)
            p.lire()
            seg = p.lignes[i0:]
            m = json.loads(p.get("/api/mouv"))
            alarme = r.get("alarme")
            print(f"{texte} par le pilote : raison « {r.get('raison')} », alarme {alarme}, {r.get('avance_mm')} mm, {r.get('rot_gyro')}°, "
                  f"ordre de {r.get('duree_ordre')} s")
        else:
            requete = texte.replace(",", "&") + (f"&v={a.v}" if a.v else "")
            m, seg, alarme = direct(p, requete, rotation, (not rotation) and but < 0)
            if seg is None:
                print(f"{texte} : REFUSÉ — {m.get('raison')}")
                break
        print(f"{texte} : cerveau « {m.get('texte')} », {m.get('raison')} ; annonce {m.get('fait_mm')} mm, {m.get('fait_deg')}°, "
              f"{m.get('duree_ms', 0) / 1000.0:.2f} s, roues à {m.get('v')} mm/s au plus" + (f" ; ALARME du PC : {alarme}" if alarme else ""))
        print("    journal :", json.dumps(mesure(seg, rotation, but, cap_rel), ensure_ascii=False))
        if m.get("etat") != 2 or alarme:
            print("    mouvement non terminé normalement : arrêt des essais.")
            break
        time.sleep(a.pause)
    e = p.etat()
    print(f"fin : mode lu {e['robot']['mode']}, roues en marche {e['driving']}, capteur de distance {e['radar'].get('front_mm')} mm, "
          f"position du cerveau x {e['pose']['x']} y {e['pose']['y']} cap {e['pose']['cap']}")


if __name__ == "__main__":
    main()
