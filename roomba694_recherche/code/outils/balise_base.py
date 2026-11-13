# balise_base.py — se repérer par rapport à la base du robot, d'après ses faisceaux infrarouges, en un tour sur place.
#
# La base émet deux faisceaux : « rouge » (code 168) d'un côté de son axe, « vert » (164) de l'autre ; dans un couloir
# étroit le long de l'axe le robot reçoit les deux (172). Portée mesurée le 2026-11-13 : 2 m (journal_wifi.md § 38).
# Deux sortes de récepteurs sur le robot (journal, colonnes ir_dessus, ir_g, ir_d) :
#   - ceux de l'avant (ir_g, ir_d) ne voient la base que si le robot lui fait face, à 20° près : le milieu des caps où
#     ils la voient donne la direction de la base ;
#   - celui du dessus est à l'avant du robot, à une quinzaine de centimètres de son centre, et ne voit pas vers l'arrière :
#     quand le robot tourne sur place, il décrit un cercle et traverse les faisceaux. En tournant vers la gauche à
#     partir de « face à la base », il va vers la gauche : rouge, puis les deux, puis vert. Les caps où le code change
#     disent de combien l'axe de la base est à gauche ou à droite du centre du robot.
#
# S'utilise pendant qu'enregistreur.py tourne, robot en mode Safe, capteur de distance en mode fixe :
#   python code/outils/balise_base.py ADRESSE PREFIXE [--pose U,V,CAP] [--rayon 150] [--tour-v 60]
#     --pose  : pixel du plan et cap du robot au départ (comme passage.py) ; les directions sont alors données aussi
#               dans le repère du plan, et la dernière ligne POSE=U,V,CAP se redonne à passage.py
#     --rayon : distance du récepteur du dessus au centre du robot, mm
# Le robot ne fait que tourner sur place (tour du firmware, 380°). Affiche : la direction de la base, le code reçu par
# tranches de 10° autour de cette direction, les caps où le code change, et l'écart de l'axe de la base par rapport au
# centre du robot (positif : l'axe passe à gauche du robot quand il fait face à la base).
import argparse
import collections
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pilote import Pilote  # noqa: E402

K_GYRO = 1.0045
NOMS = {168: "rouge", 164: "vert", 172: "les deux", 161: "champ proche", 165: "vert+champ", 169: "rouge+champ", 173: "tout"}


def ecart(a):
    return (a + 180.0) % 360.0 - 180.0


def moyenne_caps(caps):
    s = sum(math.sin(math.radians(c)) for c in caps)
    c = sum(math.cos(math.radians(c)) for c in caps)
    return math.degrees(math.atan2(s, c)) % 360.0


def seuil(phis_bas, phis_haut):
    """cap qui sépare le mieux deux groupes (le premier attendu en dessous), ou None s'il manque un groupe"""
    if not phis_bas or not phis_haut:
        return None
    cands = sorted(phis_bas + phis_haut)
    best = None
    for i in range(len(cands) - 1):
        t = 0.5 * (cands[i] + cands[i + 1])
        err = sum(1 for p in phis_bas if p > t) + sum(1 for p in phis_haut if p < t)
        if best is None or err < best[0]:
            best = (err, t)
    return best[1]


def main():
    ap = argparse.ArgumentParser(description="Direction et axe de la base d'après ses faisceaux, en un tour sur place")
    ap.add_argument("adresse")
    ap.add_argument("prefixe")
    ap.add_argument("--pose", default="", help="U,V,CAP du robot sur le plan au départ")
    ap.add_argument("--rayon", type=float, default=150.0)
    ap.add_argument("--tour-v", type=int, default=60)
    a = ap.parse_args()

    p = Pilote(a.adresse, a.prefixe)
    p.lire()
    l0 = p.frais()
    if l0 is None:
        sys.exit("aucune ligne récente du journal : l'enregistreur tourne-t-il ? le robot répond-il ?")
    i0 = len(p.lignes) - 1
    t = json.loads(p.get(f"/api/tour?go=1&v={a.tour_v}"))
    if t.get("etat") not in (1, 2):
        sys.exit("tour refusé : " + str(t.get("raison", t.get("texte"))))
    fin = time.time() + 70
    while time.time() < fin:
        time.sleep(0.5)
        t = json.loads(p.get("/api/tour"))
        if t.get("etat") not in (1, 2):
            break
    p.immobile()
    time.sleep(0.3)
    p.lire()
    seg = p.lignes[i0:]
    tourne = seg[-1]["cap_pos"] - seg[0]["cap_pos"]
    print(f"tour : {t.get('texte')}, {tourne:.0f}° en {len(seg)} lignes ; codes du dessus : "
          + (", ".join(f"{NOMS.get(int(c), int(c))} {n}" for c, n in collections.Counter(l['ir_dessus'] for l in seg if l['ir_dessus']).most_common()) or "aucun")
          + " ; avant : " + (", ".join(f"{NOMS.get(int(c), int(c))} {n}" for c, n in collections.Counter(max(l['ir_g'], l['ir_d']) for l in seg if l['ir_g'] or l['ir_d']).most_common()) or "aucun"))

    def plan(cap_cerveau):
        if not a.pose:
            return None
        return (float(a.pose.split(",")[2]) + (cap_cerveau - seg[0]["cap_pos"]) * K_GYRO) % 360.0

    # direction de la base : milieu des caps où les récepteurs avant la voient
    devant = [l["cap_pos"] % 360.0 for l in seg if l["ir_g"] or l["ir_d"]]
    if devant:
        face = moyenne_caps(devant)
        larg = max(abs(ecart(c - face)) for c in devant)
        print(f"récepteurs avant : base vue sur {len(devant)} lignes, de {-larg:+.0f}° à {larg:+.0f}° autour du cap du cerveau {face:.1f}°"
              + (f", soit le cap {plan(face + 360.0 * round((seg[0]['cap_pos'] - face) / 360.0)):.1f}° du plan" if a.pose else ""))
    else:
        face = None
        print("récepteurs avant : la base n'est vue dans aucune direction")
    dessus = [(l["cap_pos"], int(l["ir_dessus"])) for l in seg if l["ir_dessus"]]
    if face is None and dessus:
        # sans les récepteurs avant : milieu des caps où le récepteur du dessus reçoit quelque chose (moins précis)
        face = moyenne_caps([c % 360.0 for c, _ in dessus])
        print(f"direction approchée d'après le récepteur du dessus : cap du cerveau {face:.1f}°")
    if face is not None:
        par = collections.defaultdict(collections.Counter)
        for l in seg:
            par[int(ecart(l["cap_pos"] - face) // 10) * 10][int(l["ir_dessus"])] += 1
        print("récepteur du dessus, selon l'écart à la direction de la base (positif : robot tourné à gauche) :")
        for b in sorted(par):
            if sum(v for k, v in par[b].items() if k):
                print(f"   {b:+4d}° à {b + 10:+4d}° : " + ", ".join(f"{NOMS.get(k, k)} {v}" for k, v in sorted(par[b].items()) if k) + f" (sur {sum(par[b].values())} lignes)")
        phi = {c: [ecart(cap - face) for cap, code in dessus if code == c] for c in (168, 172, 164)}
        s1 = seuil(phi[168], phi[172]) if phi[172] else seuil(phi[168], phi[164])
        s2 = seuil(phi[172], phi[164]) if phi[172] else s1
        r = a.rayon
        if phi[172]:
            g = r * math.sin(math.radians(s1)) if s1 is not None else None          # bord du couloir côté rouge (à droite face à la base)
            d = r * math.sin(math.radians(s2)) if s2 is not None else None          # bord côté vert
            print("couloir « rouge et vert » : " + (f"commence à {s1:+.0f}°" if s1 is not None else "début non vu (pas de rouge)")
                  + ", " + (f"finit à {s2:+.0f}°" if s2 is not None else "fin non vue (pas de vert)"))
            if g is not None and d is not None:
                print(f"AXE de la base à {0.5 * (g + d):+.0f} mm du centre du robot (positif : à gauche quand il fait face à la base) ; couloir large de {d - g:.0f} mm ici")
            elif g is not None:
                print(f"bord rouge du couloir à {g:+.0f} mm (positif : à gauche) ; l'axe est encore 2 à 5 cm plus à gauche")
            elif d is not None:
                print(f"bord vert du couloir à {d:+.0f} mm (positif : à gauche) ; l'axe est encore 2 à 5 cm plus à droite")
        elif phi[168] and phi[164] and s1 is not None:
            print(f"rouge puis vert sans couloir vu : limite à {s1:+.0f}°, soit l'AXE à {r * math.sin(math.radians(s1)):+.0f} mm (positif : à gauche)")
        elif phi[168]:
            print("rouge seulement : le robot est du côté rouge, l'axe de la base passe à sa GAUCHE (quand il lui fait face), à plus de " f"{r:.0f} mm ou hors de vue")
        elif phi[164]:
            print("vert seulement : le robot est du côté vert, l'axe de la base passe à sa DROITE (quand il lui fait face), à plus de " f"{r:.0f} mm ou hors de vue")
        # distance vue par le capteur de distance quand le robot regardait la base
        us = sorted(l["us_mm"] for l in seg if abs(ecart(l["cap_pos"] - face)) < 4.0 and l["us_mm"] > 0)
        if us:
            print(f"capteur de distance dans cette direction : {us[len(us) // 2]:.0f} mm (de {us[0]:.0f} à {us[-1]:.0f})")
    else:
        print("aucun code reçu pendant le tour : le robot est hors des faisceaux (à plus de 2 m, ou trop de côté)")
    e = p.etat()
    print(f"fin : mode {e['robot']['mode']}, roues en marche {e['driving']}, cap du cerveau {seg[-1]['cap_pos']:.1f}°")
    if a.pose:
        u, v, c = (float(x) for x in a.pose.split(","))
        print(f"POSE={u:.1f},{v:.1f},{plan(seg[-1]['cap_pos']):.1f}")


if __name__ == "__main__":
    main()
