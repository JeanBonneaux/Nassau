# essai_profil_mur.py — le suivi d'UN mur essayé sans le robot sur des parois dessinées : la paroi réelle du 2026-11-21
# (journal_wifi.md § 71 : le mur recule de 11 cm en pente), la même prise dans l'autre sens, une marche nette, un
# renfoncement, une avancée, une porte, un mur qui tourne, de petites marches, un départ de travers.
#
#   python essai_profil_mur.py [--suivi mur|lateral|les-deux] [--graines 5] [--vitesse 100] [--bruit 20] [--detail NOM]
#
# Pourquoi cet essai en plus de essai_longe_mur.py : le simulateur du couloir rend un écho net (la paroi la plus proche
# dans le cône), il ne sait pas dessiner une paroi qui recule en pente comme celle que le vrai capteur a lue. Ici la
# paroi est donnée par ce que le capteur LIT le long du mur : une fonction du chemin. Le robot est simulé simplement :
#   - il tient le cap visé comme le cerveau le fait pendant une avance (proportionnel : KP degrés par seconde par degré
#     d'erreur, mesuré 1,5 à 1,7 sur l'enregistrement du § 71), avec un petit défaut constant (il tire d'un côté) ;
#   - le capteur est à AVANCE mm en avant du centre, tourné du côté du mur, lu dix fois par seconde, bruit gaussien ;
#   - le PC retouche le cap cinq fois par seconde, avec un quart de seconde de retard (lecture, Wi-Fi, ordre).
# C'est plus indulgent que l'appartement ; cela dit si la logique tient et compare deux suivis sur les mêmes parois.
import argparse
import math
import random
import statistics
import sys

from suivi_lateral import SuiviLateral
from suivi_mur import SuiviMur

RAYON = 170.0
AVANCE = 130.0
LOIN = 3000.0            # « rien à portée » : une ouverture


def pente(x, x0, x1, y0, y1):
    if x <= x0:
        return y0
    if x >= x1:
        return y1
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


# Chaque paroi : distance du mur à la ligne de marche (mm) en fonction du chemin le long du mur (mm).
PAROIS = {
    "droit":            lambda x: 433.0,
    "recul en pente":   lambda x: pente(x, 980, 1150, 433.0, 543.0),              # la paroi du § 71
    "avancée en pente": lambda x: pente(x, 980, 1150, 543.0, 433.0),              # la même, prise dans l'autre sens
    "recul net":        lambda x: 433.0 if x < 1000 else 543.0,
    "avancée nette":    lambda x: 543.0 if x < 1000 else 433.0,
    "renfoncement":     lambda x: 543.0 if 1000 <= x < 1400 else 433.0,           # un cadre de porte de 40 cm
    "bosse":            lambda x: 373.0 if 1000 <= x < 1300 else 433.0,           # un meuble de 6 cm sur 30 cm
    "porte":            lambda x: LOIN if 1000 <= x < 1800 else 433.0,            # une ouverture de 80 cm
    "mur qui s'écarte": lambda x: 433.0 + max(0.0, x - 1000) * math.tan(math.radians(8.0)),
    "mur qui se rapproche": lambda x: 433.0 - min(200.0, max(0.0, x - 1000) * math.tan(math.radians(8.0))),
    "petites marches":  lambda x: 433.0 + (20.0 if int(x // 300) % 2 else 0.0),   # plinthes, cadres : 2 cm tous les 30 cm
}


class Ancien:
    """Le suivi du § 71 : SuiviLateral avec un seul côté, et la règle de l'ouverture de longe_mur.py."""

    def __init__(self, cote, consigne, v_max, gain=1.0):
        self.cote = cote
        self.s = SuiviLateral(axe=0.0, gain=gain, cap_max=10.0, fenetre=600.0, portee=2000.0, v_max=v_max, v_serre=min(80, v_max),
                              rayon=150.0, mediane=5, pente_min=400.0)
        self.s.pose = (consigne, consigne)
        self.ref, self.ouvert = float(consigne), False

    @property
    def axe(self):
        return self.s.axe

    def pas(self, s, cap, lecture):
        if lecture is not None:
            if self.ouvert:
                if lecture - self.ref <= 125.0:
                    self.ouvert = False
                else:
                    lecture = None
            elif lecture - self.ref > 250.0:
                self.ouvert, lecture = True, None
            if lecture is not None:
                self.ref = 0.7 * self.ref + 0.3 * lecture
        g, d = (lecture, None) if self.cote == "g" else (None, lecture)
        cv, v = self.s.pas(s, cap, g, d)
        if lecture is None:
            cv = self.s.axe
        return cv, v


def essai(nom, quel, cote="d", v_max=100, bruit=20.0, graine=1, cap_faux=0.0, decalage=0.0, longueur=3000.0, kp=1.6, tire=0.6,
          gain=1.0, detail=False, options=None):
    """cap_faux : degrés dont le robot est tourné par rapport au mur au départ (il croit être à 0) ; decalage : mm dont il
    est plus loin du mur que la consigne au départ. Renvoie les chiffres du trajet."""
    W = PAROIS[nom]
    rng = random.Random(1000 * graine + 7)
    signe = 1.0 if cote == "g" else -1.0
    consigne = 433.0
    if quel == "mur":
        suivi = SuiviMur(cote, consigne, gain=gain, v_max=v_max, v_serre=min(80, v_max), **(options or {}))
        suivi.amorce(W(AVANCE) + decalage + rng.gauss(0.0, 3.0))        # la lecture à l'arrêt, avant de partir
    else:
        suivi = Ancien(cote, consigne, v_max, gain=gain)
    # le robot : x le long du mur, y vers la gauche ; le mur est à y = signe * W(x) ; ligne de marche voulue : y = 0
    x, y, th = 0.0, -signe * decalage, math.radians(cap_faux)
    dt = 0.02
    t = chemin = 0.0
    cap_vise, v = 0.0, float(v_max)
    file_cmd = []
    t_lec = t_cmd = -1e9
    neuf = None
    pire_cap = pire_ecart = 0.0
    jeu = 1e9
    ecarts = []
    fin = "distance faite"
    while x < longueur:
        cap = math.degrees(th) - cap_faux + rng.gauss(0.0, 0.05)        # cap compté depuis le départ de l'avance
        if t - t_lec >= 0.1 - 1e-9:                                       # le capteur, dix fois par seconde
            t_lec = t
            sx, sy = x + AVANCE * math.cos(th), y + AVANCE * math.sin(th)
            w = W(sx)
            lec = (w - signe * sy) + rng.gauss(0.0, bruit) if w < LOIN else None
            neuf = (chemin, cap, lec if (lec is None or 20.0 < lec <= 2000.0) else None)
        if neuf is not None and t - t_cmd >= 0.2 - 1e-9:                  # le PC : cinq retouches par seconde, 0,25 s de retard
            pass
        if neuf is not None:
            cv, vv = suivi.pas(*neuf)
            neuf = None
            if t - t_cmd >= 0.2 - 1e-9:
                t_cmd = t
                file_cmd.append((t + 0.25, max(-40.0, min(40.0, cv)), vv))
        while file_cmd and file_cmd[0][0] <= t + 1e-9:
            _, cap_vise, v = file_cmd.pop(0)
        err = cap_vise - cap - tire
        th += math.radians(max(-20.0, min(20.0, kp * err)) * dt)
        vr = min(v * 1.08, 160.0)
        x += vr * dt * math.cos(th)
        y += vr * dt * math.sin(th)
        chemin += vr * dt
        t += dt
        # le jeu entre le bord du robot et la paroi, et les chiffres
        j = min(math.hypot(u, W(x + u) - signe * y) for u in range(-170, 171, 10)) - RAYON
        jeu = min(jeu, j)
        if j <= 0.0:
            fin = "contact"
            break
        pire_cap = max(pire_cap, abs(math.degrees(th)))
        e = (W(x) - signe * y) - consigne if W(x) < LOIN else None
        if e is not None and x > 500.0:
            ecarts.append(e)
        if detail and int(chemin / 100) != int((chemin - vr * dt) / 100):
            print("      %5.0f mm : paroi à %5.0f, écart %+5.0f mm, axe retenu %+5.1f°, cap visé %+5.1f°, cap vrai %+5.1f°%s" % (
                x, W(x) - signe * y, (e if e is not None else float("nan")), suivi.axe, cap_vise, math.degrees(th),
                (" [%s]" % suivi.etat) if quel == "mur" else ""))
    return {"fin": fin, "pire_cap": pire_cap, "jeu": jeu, "duree": t, "y_fin": signe * y, "cap_fin": math.degrees(th),
            "ecart_fin": (W(x) - signe * y) - consigne, "axe": suivi.axe}


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    q = argparse.ArgumentParser()
    q.add_argument("--suivi", choices=["mur", "lateral", "les-deux"], default="les-deux")
    q.add_argument("--graines", type=int, default=5)
    q.add_argument("--vitesse", type=int, default=100)
    q.add_argument("--bruit", type=float, default=20.0)
    q.add_argument("--gain", type=float, default=1.0)
    q.add_argument("--cote", choices=["g", "d"], default="d")
    q.add_argument("--detail", default=None, help="nom d'une paroi : son déroulé pas à pas")
    q.add_argument("--departs", action="store_true", help="aussi des départs de travers (±6°) et décalés (±10 cm)")
    a = q.parse_args()
    quels = ["lateral", "mur"] if a.suivi == "les-deux" else [a.suivi]
    noms = {"lateral": "suivi du § 71", "mur": "suivi par droite"}
    print("=== un mur à %s, consigne 433 mm, %d mm/s, bruit %d mm, %d tirages par paroi ; 3 m ===" % (
        "droite" if a.cote == "d" else "gauche", a.vitesse, a.bruit, a.graines))
    departs = [(0.0, 0.0)]
    if a.departs:
        departs = [(c, d) for c in (-6.0, 0.0, 6.0) for d in (-100.0, 0.0, 100.0)]
    for nom in PAROIS:
        for quel in quels:
            R = [essai(nom, quel, cote=a.cote, v_max=a.vitesse, bruit=a.bruit, graine=g, cap_faux=c, decalage=d, gain=a.gain)
                 for g in range(1, a.graines + 1) for c, d in departs]
            ok = [r for r in R if r["fin"] == "distance faite"]
            print("%-22s %-16s : %2d sur %2d sans contact ; cap le plus fort %4.1f° (médiane %4.1f°) ; jeu le plus petit %4.0f mm ; "
                  "à la fin : écart %+4.0f mm, cap %+5.1f°, axe retenu %+5.1f°" % (
                      nom, noms[quel], len(ok), len(R), max(r["pire_cap"] for r in R), statistics.median(r["pire_cap"] for r in R),
                      min(r["jeu"] for r in R), statistics.median(r["ecart_fin"] for r in R),
                      statistics.median(r["cap_fin"] for r in R), statistics.median(r["axe"] for r in R)))
    if a.detail:
        for quel in quels:
            print("--- déroulé : %s, %s ---" % (a.detail, noms[quel]))
            essai(a.detail, quel, cote=a.cote, v_max=a.vitesse, bruit=a.bruit, graine=1, gain=a.gain, detail=True)


if __name__ == "__main__":
    main()
