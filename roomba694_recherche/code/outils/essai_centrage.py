# essai_centrage.py — essaie centrage.py dans des passages simulés, sans le robot.
#
# Usage : python essai_centrage.py [couloir|porte|tout] [--graines 5] [--dessin FICHIER.png] [--detail]
#
# Deux mondes :
#   couloir  le couloir du 2026-11-14 tel que les regards de côté l'ont mesuré (journal_wifi.md § 45) : 95 cm de large,
#            puis 84, 73 et 68 cm (une paroi avance de 11 cm, l'autre de 11 puis de 5 cm), et plus loin une ouverture
#            sur un côté. Le robot y fait 3,9 m.
#   porte    une porte de 62 cm dans une cloison de 12 cm, comme la porte H12, abordée depuis une pièce sans paroi
#            proche. Le robot fait 1,8 m et la traverse.
# Pour chaque monde, le robot part décalé de côté et avec un cap faux (ce qu'il croit n'est pas ce qui est), et on
# compare : tout droit sans regarder, centrage à pas fixe de 40 cm, centrage à pas qui s'allonge.
# Ce que le bilan donne : les contacts, le jeu le plus petit entre le robot et une paroi pendant le trajet, le nombre
# d'arrêts, la durée simulée, l'écart au milieu à l'arrivée, et le cap par rapport aux murs que le robot a trouvé.
#
# Le simulateur n'est pas le vrai robot (simulateur.py le dit en tête) : il dit si la logique tient, pas si le capteur
# verra bien un vrai montant de porte. Les vraies lectures du 2026-11-14 ont déjà montré une différence : une paroi
# proche s'entend très en biais, ce que le simulateur ne fait pas. Les décisions du programme sur ces lectures-là sont
# rejouées par data_analysis/v_rejeu_centrage.py (journal_wifi.md § 47).
import argparse
import math
import sys

import numpy as np

import centrage
import simulateur as sim


def monde_couloir():
    """Le robot va vers les x croissants ; sa gauche est en haut (y grand)."""
    bas = [(0, 0), (1500, 0), (1500, 110), (1750, 110), (1750, 155), (3300, 155), (3300, -1500), (4100, -1500), (4100, 155), (6000, 155)]
    haut = [(6000, 839), (1300, 839), (1300, 946), (0, 946)]
    pts = bas + haut + [(0, 0)]
    murs = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]
    return dict(murs=murs, depart=(500.0, 473.0, 0.0), etendue=(0, -1500, 6000, 946)), 3900.0


def monde_porte():
    """Une pièce de 4 m sur 3 m coupée par une cloison de 12 cm d'épaisseur, avec une porte de 62 cm."""
    murs = [((0, 0), (4000, 0)), ((4000, 0), (4000, 3000)), ((4000, 3000), (0, 3000)), ((0, 3000), (0, 0))]
    murs += sim.rect(1500, 0, 1620, 1000)
    murs += sim.rect(1500, 1620, 1620, 3000)
    return dict(murs=murs, depart=(600.0, 1310.0, 0.0), etendue=(0, 0, 4000, 3000)), 1800.0


MONDES = {"couloir": monde_couloir, "porte": monde_porte}


def jeu_mini(monde, trace):
    """plus petite distance entre le bord du robot et une paroi le long du trajet vrai (mm)"""
    return min(float(monde.dist_murs(np.array(p))[0].min()) - sim.RAYON for p in trace)


def milieu(monde, x, y):
    """écart du point au milieu du passage, mesuré de bas en haut à cet endroit (mm, positif vers le haut)"""
    P = np.array([x, y])
    h = b = None
    for A, B in zip(monde.A, monde.B):
        if abs(B[0] - A[0]) < 1e-6 or not (min(A[0], B[0]) <= x <= max(A[0], B[0])):
            continue
        yy = A[1] + (B[1] - A[1]) * (x - A[0]) / (B[0] - A[0])
        if yy > y and (h is None or yy < h):
            h = yy
        if yy < y and (b is None or yy > b):
            b = yy
    if h is None or b is None or h - b > 1300:
        return None
    return y - (h + b) / 2.0


def essai(nom, decalage, cap_faux, graine, mode, k_vrai=1.0045, muet=True):
    """mode : « droit » (sans regarder), « fixe » (pas de 40 cm) ou « souple » (pas qui s'allonge)"""
    d, dist = MONDES[nom]()
    x, y, c = d["depart"]
    d["depart"] = (x, y + decalage, c + cap_faux)                 # le robot croit être au cap c, au milieu
    monde = sim.Monde(**d)
    robot = sim.RobotSimule(monde, graine=graine, echelle_gyro=k_vrai, firmware=10)
    lignes = []
    m = centrage.Mobile(robot, x, y, c, k_gyro=1.0045, dire=lignes.append)
    t0 = robot.t
    if mode == "droit":
        fait, fin = 0.0, "distance faite"
        while fait < dist - 30:
            r = m.avancer(min(800.0, dist - fait), 100)
            if "refus" in r or r.get("alarme") or "distance" not in str(r.get("raison")):
                fin = str(r.get("refus") or r.get("alarme") or r.get("raison"))
                break
            fait += r["avance_mm"]
        res = {"fin": fin, "ok": fin == "distance faite", "arrets": [], "biais": 0.0, "n_biais": 0, "duree": robot.t - t0}
    else:
        res = centrage.centrer(m, c, dist, pas_max=400.0 if mode == "fixe" else 800.0, dire=lignes.append)
    e = milieu(monde, robot.x, robot.y)
    out = {"fin": res["fin"], "ok": res["ok"], "contacts": len(robot.contacts), "jeu": jeu_mini(monde, robot.trace), "arrets": len(res["arrets"]),
           "duree": res["duree"], "ecart_fin": e, "biais": res["biais"], "n_biais": res["n_biais"], "avance": robot.x - x,
           "cap_fin": math.degrees(robot.th), "trace": list(robot.trace), "monde": monde, "lignes": lignes, "res": res}
    if not muet:
        for t in lignes:
            print("   ", t)
    return out


def dessiner(fichier, cas):
    """les trajets vrais de quelques essais, posés sur le passage simulé"""
    from PIL import Image, ImageDraw, ImageFont
    try:
        police = ImageFont.truetype("arial.ttf", 17)
        petite = ImageFont.truetype("arial.ttf", 14)
    except OSError:
        police = petite = ImageFont.load_default()
    s = 0.22                                                      # pixels par millimètre
    bandes = []
    for titre, essais in cas:
        monde = essais[0][1]["monde"]
        x0, y0, x1, y1 = monde.etendue
        y0 = max(y0, min(p[1] for _, e, _ in essais for p in e["trace"]) - 700)
        y1 = min(y1, max(p[1] for _, e, _ in essais for p in e["trace"]) + 700)
        bandes.append((titre, essais, monde, x0, y0, x1, y1))
    W = int(max(b[5] - b[3] for b in bandes) * s) + 60
    H = sum(int((b[6] - b[4]) * s) + 95 for b in bandes) + 20
    im = Image.new("RGB", (W, H), (252, 252, 250))
    dr = ImageDraw.Draw(im)
    haut = 15
    for titre, essais, monde, x0, y0, x1, y1 in bandes:
        dr.text((30, haut), titre, fill=(30, 30, 30), font=police)
        base = haut + 30

        def px(x, y):
            return 30 + (x - x0) * s, base + (y1 - y) * s

        hb = int((y1 - y0) * s)
        dr.rectangle([30, base, 30 + (x1 - x0) * s, base + hb], fill=(255, 255, 255))
        for A, B in zip(monde.A, monde.B):
            if max(A[1], B[1]) < y0 or min(A[1], B[1]) > y1:
                continue
            a = px(A[0], min(max(A[1], y0), y1))
            b = px(B[0], min(max(B[1], y0), y1))
            dr.line([a, b], fill=(40, 40, 40), width=4)
        lx = 30
        for nom, e, coul in essais:
            pts = [px(*p) for p in e["trace"]]
            if len(pts) > 1:
                dr.line(pts, fill=coul, width=3)
            for a in e["res"]["arrets"]:                          # où le robot s'est arrêté pour regarder
                pass
            u, v = px(*e["trace"][-1])
            r = sim.RAYON * s
            dr.ellipse([u - r, v - r, u + r, v + r], outline=coul, width=2)
            u, v = px(*e["trace"][0])
            dr.ellipse([u - r, v - r, u + r, v + r], outline=(150, 150, 150), width=1)
            txt = f"{nom} : {e['contacts']} contact{'s' if e['contacts'] > 1 else ''}, jeu {e['jeu'] / 10:.0f} cm, {e['duree']:.0f} s"
            dr.line([lx, base + hb + 22, lx + 26, base + hb + 22], fill=coul, width=4)
            dr.text((lx + 32, base + hb + 13), txt, fill=(60, 60, 60), font=petite)
            lx += 40 + int(dr.textlength(txt, font=petite)) + 30
        haut = base + hb + 65
    im.save(fichier)


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    q = argparse.ArgumentParser()
    q.add_argument("monde", nargs="?", default="tout")
    q.add_argument("--graines", type=int, default=5)
    q.add_argument("--dessin", default="")
    q.add_argument("--detail", action="store_true", help="affiche ce que le robot dit pendant le premier essai de chaque monde")
    a = q.parse_args()
    noms = list(MONDES) if a.monde == "tout" else [a.monde]
    cas_dessin = []
    for nom in noms:
        print(f"=== {nom} ===")
        departs = [(dy, dc) for dy in (-150.0, 0.0, 150.0) for dc in (-6.0, -3.0, 0.0, 3.0, 6.0)]
        for mode in ("droit", "fixe", "souple"):
            R = [essai(nom, dy, dc, g, mode) for dy, dc in departs for g in range(1, a.graines + 1)]
            ok = [r for r in R if r["ok"] and not r["contacts"]]
            ec = [abs(r["ecart_fin"]) for r in ok if r["ecart_fin"] is not None]
            print(f"{mode:7s} : {len(R)} essais, {len(ok)} sans contact jusqu'au bout, {sum(1 for r in R if r['contacts'])} avec contact, "
                  f"{sum(1 for r in R if not r['ok'] and not r['contacts'])} arrêtés avant la fin sans contact")
            if ok:
                print(f"          sans contact : jeu le plus petit {min(r['jeu'] for r in ok):.0f} mm (médiane {np.median([r['jeu'] for r in ok]):.0f}), "
                      f"{np.median([r['arrets'] for r in ok]):.0f} arrêts, {np.median([r['duree'] for r in ok]):.0f} s (de {min(r['duree'] for r in ok):.0f} à {max(r['duree'] for r in ok):.0f})"
                      + (f", écart au milieu à l'arrivée {np.median(ec):.0f} mm en médiane, {max(ec):.0f} au pire" if ec else ""))
            if mode != "droit":
                err = [r["biais"] - dc for r, (dy, dc) in zip(R, [d for d in departs for _ in range(a.graines)]) if r["n_biais"] >= 2]
                if err:
                    print(f"          cap par rapport aux murs : erreur médiane {np.median(np.abs(err)):.1f}°, au pire {np.max(np.abs(err)):.1f}° ({len(err)} essais avec deux mesures ou plus)")
            for r in R:
                if not r["ok"] or r["contacts"]:
                    print(f"          - arrêt : {r['fin']} ; {r['contacts']} contact(s), {r['avance']:.0f} mm faits")
                    break
        if a.detail:
            print("--- ce que dit le robot, départ 15 cm à droite et cap faux de +6° ---")
            essai(nom, -150.0, 6.0, 1, "souple", muet=False)
        dy, cote = (-150.0, "droite") if nom == "couloir" else (150.0, "gauche")
        cas_dessin.append((f"{'couloir simulé' if nom == 'couloir' else 'porte simulée'} : départ 15 cm à {cote} du milieu, cap faux de 6° vers la gauche",
                           [("tout droit sans regarder", essai(nom, dy, 6.0, 1, "droit"), (200, 60, 50)),
                            ("centrage, pas qui s'allonge", essai(nom, dy, 6.0, 1, "souple"), (30, 110, 200))]))
    if a.dessin:
        dessiner(a.dessin, cas_dessin)
        print("dessin :", a.dessin)


if __name__ == "__main__":
    main()
