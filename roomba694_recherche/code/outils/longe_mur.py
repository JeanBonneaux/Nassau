# longe_mur.py — longer un mur SANS S'ARRÊTER : le capteur de distance tourné d'un côté lit le mur, et le PC retouche le cap
# de l'avance en cours (firmware v17, /api/mouv?retouche=1). Les capteurs optiques du robot gardent l'avant et le flanc.
#
# Pour la demande de vitesse de l'utilisateur du 2026-11-21 (notes/P_capteurs_en_direct.md § 9) : jusqu'ici une avance
# s'arrêtait au bout de 2 m au plus et toute correction de route demandait un arrêt.
#
#   python longe_mur.py [ADRESSE] --prefixe CHEMIN/NOM --cote g|d --distance MM [--vitesse 100] [--ecart MM]
#                       [--opt 100] [--flanc 100] [--horizon 500] [--marge 450] [--lent N]
#       pendant qu'enregistreur.py tourne (le firmware arrête les roues si la console TCP se ferme).
#
# Déroulement :
#   1. capteur devant : la place libre est lue ; il faut la distance demandée plus la marge (ou « rien à portée ») ;
#   2. le capteur tourne lentement du côté choisi ; 1,5 s de lectures à l'arrêt donnent l'écart au mur ; sans mur à moins
#      de 2 m de ce côté, rien ne bouge ;
#   3. une avance courte est lancée (--horizon), avec le ralentissement sur les capteurs optiques de devant (--opt) ;
#   4. tant que la distance n'est pas faite, à chaque lecture de l'état : la lecture de côté va au suivi
#      (suivi_lateral.SuiviLateral, un seul côté, écart imposé), qui rend un cap et une vitesse ; le capteur optique du
#      flanc, du côté du mur, ajoute un écart de sécurité s'il lit --flanc ou plus ; la retouche (cap, vitesse, et le but
#      repoussé de --horizon au-delà du chemin fait) part cinq fois par seconde au plus ;
#   5. à la fin : lectures à l'arrêt, capteur ramené devant lentement, résumé.
# Si le PC ou le Wi-Fi s'arrête, l'avance va au bout de son horizon (50 cm par défaut) et s'arrête d'elle-même.
# --ecart : lecture du capteur à tenir (mm) ; par défaut celle du départ. C'est la lecture brute, pas la distance du centre
# du robot au mur (le capteur est à quelques centimètres de l'axe du robot quand il est tourné).
# ATTENTION : capteur tourné, RIEN NE REGARDE DEVANT que les capteurs optiques (qui ralentissent) et le pare-chocs (qui
# arrête). La place devant est vérifiée avant de tourner le capteur.
# Ce que l'outil envoie : /api/radar (mode, angle, butee, lent), /api/mouv?av=…&v=…&opt=…, /api/mouv?retouche=1&…,
# et /api/mouv?stop=1 en cas d'arrêt. Fichier écrit : PREFIXE_longe.jsonl ; résumé à l'écran.
import argparse
import json
import math
import statistics
import sys
import time
import urllib.request

from suivi_lateral import SuiviLateral
from suivi_mur import SuiviMur

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser(description="Longer un mur sans s'arrêter, capteur de distance tourné de côté (firmware v17).")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe", required=True)
p.add_argument("--cote", choices=["g", "d"], required=True)
p.add_argument("--distance", type=int, required=True, help="mm à parcourir")
p.add_argument("--vitesse", type=int, default=100, help="mm/s au plus (150 est le plafond du projet)")
p.add_argument("--ecart", type=int, default=0, help="lecture du capteur à tenir, mm (0 : celle du départ)")
p.add_argument("--opt", type=int, default=100, help="seuil des capteurs optiques de devant (0 : pas de ralentissement)")
p.add_argument("--flanc", type=int, default=100, help="seuil du capteur optique du flanc, côté mur (0 : pas de garde)")
p.add_argument("--horizon", type=int, default=500, help="mm : le but est tenu à cette distance devant le robot")
p.add_argument("--marge", type=int, default=450, help="place qui doit rester devant après le trajet, mm")
p.add_argument("--mur-max", type=int, default=2000, help="mm : à l'arrêt, le mur doit être lu à moins que cela, sinon rien ne bouge (le 2026-11-21 un tour sur place avait fait croire à un mur qui n'y était pas)")
p.add_argument("--ouverture", type=int, default=250, help="mm : un mur lu plus loin que la consigne de cette valeur est tenu pour une ouverture")
p.add_argument("--lent", type=int, default=0, help="vitesse de rotation du capteur, degrés par seconde (0 : celle déjà réglée)")
p.add_argument("--pas", type=int, default=5)
p.add_argument("--fenetre", type=float, default=600.0, help="longueur de chemin sur laquelle la pente du mur est lue, mm")
p.add_argument("--mediane", type=int, default=5)
p.add_argument("--pente-min", type=float, default=400.0, help="mm de paroi qu'il faut avoir longés avant d'en lire la pente (l'axe du mur)")
p.add_argument("--gain", type=float, default=1.0, help="radians de correction de cap par mètre d'écart")
p.add_argument("--cap-max", type=float, default=10.0, help="correction de cap la plus forte, degrés")
p.add_argument("--suivi", choices=["mur", "lateral"], default="mur", help="mur : le suivi par droite (suivi_mur.py, journal § 72) ; lateral : celui du premier mur longé (journal § 71), qui tournait de 16° devant un recul du mur en pente")
p.add_argument("--saut", type=float, default=30.0, help="suivi « mur » : mm d'écart à la droite du mur au-delà desquels une lecture est une autre paroi")
p.add_argument("--adopte", type=float, default=400.0, help="suivi « mur » : mm sur lesquels une autre paroi doit tenir en ligne droite avant de devenir le mur")
p.add_argument("--avance-capteur", type=float, default=130.0, help="suivi « mur » : mm du centre du robot à l'axe du servo, vers l'avant (estimé, pas mesuré à la règle)")
a = p.parse_args()
ZONE = 30
ANGLE = 90 if a.cote == "g" else -90
I_FLANC = 0 if a.cote == "g" else 5          # capteurs optiques : G, avG, cG, cD, avD, D
MODE_SAFE = 3
PORTEE_MUR = 2000                            # au-delà, ce n'est pas un mur à longer


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def heure():
    t = time.time()
    return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % int((t % 1) * 1000))


class Arret(Exception):
    pass


journal = open(a.prefixe + "_longe.jsonl", "a", encoding="utf-8")
ms_carte = None
lent_regle = None


def lire(etape, **quoi):
    global ms_carte
    t_fin = time.time() + 3.0
    while True:
        try:
            e = get("/api/state")
            break
        except Exception as x:
            if time.time() > t_fin:
                raise Arret("le cerveau ne répond plus depuis 3 s (%s)" % type(x).__name__)
            time.sleep(0.15)
    ra, po, mv, rb = e.get("radar", {}), e.get("pose", {}), e.get("mouv", {}), e.get("robot", {})
    ligne = dict(t=time.time(), h=heure(), etape=etape, ms=e.get("ms"), servo=ra.get("servo"), mm=ra.get("mm"), a=ra.get("a"),
                 mm_age=ra.get("mm_age"), absent=ra.get("absent"), fait_mm=mv.get("fait_mm"), fait_deg=mv.get("fait_deg"),
                 mouv=mv.get("etat"), but=mv.get("but"), cap_vise=mv.get("cap_vise"), ret=mv.get("ret"), opt=mv.get("opt"),
                 x=po.get("x"), y=po.get("y"), cap=po.get("cap"), roule=e.get("driving"), pc=rb.get("bump"), lb=rb.get("light"),
                 robot_ok=rb.get("ok"), robot_age=rb.get("age"))
    ligne.update(quoi)
    journal.write(json.dumps(ligne, ensure_ascii=False) + "\n")
    journal.flush()
    if ms_carte is not None and e.get("ms", 0) + 2000 < ms_carte:
        raise Arret("la carte a redémarré (%s)" % e.get("rst"))
    ms_carte = e.get("ms", ms_carte)
    if ra.get("absent"):
        raise Arret("le capteur de distance ne réagit plus")
    return e


def aller(angle, etape):
    e = lire(etape)
    cur = e["radar"]["servo"]
    while cur != angle:
        bond = max(-a.pas, min(a.pas, angle - cur))
        vise = cur + bond
        if abs(vise) <= ZONE and (abs(cur) > ZONE or abs(angle) > ZONE):     # traversée de la zone de ±30° d'une traite, au pas lent
            vise = (1 if angle > 0 else -1) * min(abs(angle), ZONE + a.pas) if abs(angle) > ZONE else angle
        get("/api/radar?mode=fixe&doux=1&angle=%d" % vise)
        limite = time.time() + abs(vise - cur) / max(1, lent_regle or 3) + 5.0
        while True:
            time.sleep(0.15)
            e = lire(etape, vise=vise)
            cur = e["radar"]["servo"]
            if cur == vise:
                break
            if time.time() > limite:
                raise Arret("le capteur n'arrive pas à %d° (il est à %d°)" % (vise, cur))
    return e


def lectures(etape, duree, angle):
    M, vus, t_fin = [], set(), time.time() + duree
    while time.time() < t_fin:
        time.sleep(0.08)
        e = lire(etape)
        ra = e["radar"]
        if ra.get("a") == angle and ra.get("mm_age", 9999) < 500:
            tm = round((e["ms"] - ra["mm_age"]) / 20.0)
            if tm not in vus:
                vus.add(tm)
                M.append(ra["mm"])
    return M


code = 0
capteur_tourne = False
parti = False
try:
    e = lire("depart")
    rb = e["robot"]
    refus = None
    if "ret" not in e.get("mouv", {}):
        refus = "le firmware n'a pas la retouche d'une avance en cours (il faut la v17) : %s" % str(e.get("ver", "?")).split(" ")[0]
    elif not rb.get("ok") or rb.get("mode") != MODE_SAFE:
        refus = "le robot ne répond pas ou n'est pas en mode Safe (mode lu %s)" % rb.get("mode")
    elif e.get("driving") or e["tour"]["etat"] in (1, 2) or e["mouv"]["etat"] == 1:
        refus = "le robot bouge déjà"
    elif any(rb.get("bump", [0, 0])) or any(rb.get("drop", [0, 0])):
        refus = "pare-chocs enfoncé ou roue levée"
    elif not (50 <= a.vitesse <= 150) or not (200 <= a.distance <= 10000) or not (200 <= a.horizon <= 1500):
        refus = "vitesse de 50 à 150 mm/s, distance de 200 à 10 000 mm, horizon de 200 à 1 500 mm"
    if refus:
        print("%s  RIEN N'EST ENVOYÉ : %s." % (heure(), refus))
        sys.exit(1)
    lent_regle = a.lent or e["radar"].get("lent", 3)
    if a.lent:
        get("/api/radar?lent=%d" % a.lent)
    # 1. la place devant
    get("/api/radar?mode=fixe&doux=1&angle=0")
    time.sleep(1.2)
    aller(0, "devant")
    D = lectures("devant", 1.5, 0)
    if len(D) < 4:
        print("%s  PAS ASSEZ DE LECTURES DEVANT (%d) : rien ne bouge." % (heure(), len(D)))
        sys.exit(1)
    vus = [x for x in D if x > 0]
    libre = min(vus) if len(vus) * 2 >= len(D) else 4000
    if libre - a.distance < a.marge:
        print("%s  PAS ASSEZ DE PLACE DEVANT : %d mm lus, il en faut %d (trajet de %d + marge de %d). Rien ne bouge." % (
            heure(), libre, a.distance + a.marge, a.distance, a.marge))
        sys.exit(1)
    print("%s  devant : %s ; trajet de %d mm, il restera %s." % (
        heure(), ("%d mm" % libre) if libre < 4000 else "rien à portée", a.distance,
        ("%d mm" % (libre - a.distance)) if libre < 4000 else "plus de %d mm" % (4000 - a.distance)))
    # 2. le capteur de côté, et le mur
    get("/api/radar?butee=90")
    capteur_tourne = True
    aller(ANGLE, "rotation")
    A0 = lectures("cote_arret_avant", 1.5, ANGLE)
    vus = [x for x in A0 if 0 < x <= PORTEE_MUR]
    if len(vus) < 4 or len(vus) * 2 < len(A0):
        raise Arret("pas de mur à moins de %d mm de ce côté (%d lectures utiles sur %d)" % (PORTEE_MUR, len(vus), len(A0)))
    d0 = statistics.median(vus)
    if d0 > a.mur_max or max(vus) - min(vus) > 120:
        raise Arret("ce que le capteur lit de ce côté ne ressemble pas au mur attendu : %d mm (de %d à %d), pour %d mm au plus et 120 mm de dispersion" % (
            d0, min(vus), max(vus), a.mur_max))
    ecart = a.ecart or d0
    print("%s  mur lu à %d mm (de %d à %d) ; écart à tenir : %d mm ; vitesse %d mm/s ; optique devant %s, flanc %s." % (
        heure(), d0, min(vus), max(vus), ecart, a.vitesse, a.opt or "sans", a.flanc or "sans"))
    if a.suivi == "mur":
        suivi = SuiviMur(a.cote, ecart, gain=a.gain, cap_max=a.cap_max, fenetre=a.fenetre, pente_min=a.pente_min, saut=a.saut,
                         ouverture=a.ouverture, adopte=a.adopte, avance_capteur=a.avance_capteur, portee=PORTEE_MUR,
                         v_max=a.vitesse, v_serre=min(80, a.vitesse), rayon=150.0, mediane=a.mediane)
        suivi.amorce(d0)
    else:
        suivi = SuiviLateral(axe=0.0, gain=a.gain, cap_max=a.cap_max, fenetre=a.fenetre, portee=PORTEE_MUR, v_max=a.vitesse,
                             v_serre=min(80, a.vitesse), rayon=150.0, mediane=a.mediane, pente_min=a.pente_min)
        suivi.pose = (ecart, ecart)
    # 3. le départ
    r = get("/api/mouv?av=%d&v=%d%s" % (min(a.horizon, a.distance), a.vitesse, ("&opt=%d" % a.opt) if a.opt else ""))
    if r.get("etat") != 1:
        raise Arret("avance refusée par le cerveau : %s" % r.get("raison"))
    parti = True
    print("%s  parti : capteur à %d°, but tenu %d mm devant." % (heure(), ANGLE, a.horizon))
    # 4. la boucle
    t0 = time.time()
    vus_m, R = set(), []                    # R : (chemin, lecture, cap, cap visé)
    prec, v_est = None, 0.0
    cap_vise, v_vise = 0.0, float(a.vitesse)
    t_ret, n_ret, n_flanc, perdu_mm, s_prec = 0.0, 0, 0, 0.0, 0.0
    ref, ouvert, n_ouvert = float(d0), False, 0      # règle de l'ouverture
    limite = a.distance / 40.0 + 15.0
    fin = None
    while True:
        time.sleep(0.03)
        if a.suivi == "mur":                 # ce que le suivi retenait à la lecture d'avant : où il croit le mur, et son axe
            e = lire("longe", cv=round(cap_vise, 1), vv=round(v_vise), et=suivi.etat, ax=round(suivi.axe, 1),
                     di=None if suivi.dist is None else round(suivi.dist))
        else:
            e = lire("longe", cv=round(cap_vise, 1), vv=round(v_vise))
        mv, ra, rb = e["mouv"], e["radar"], e["robot"]
        now = time.time()
        s = mv["fait_mm"]
        if prec is not None and now > prec[0]:
            v_est = (s - prec[1]) / (now - prec[0])
        prec = (now, s)
        if mv["etat"] != 1:
            break
        if not rb.get("ok") or rb.get("age", 0) > 800:
            raise Arret("le robot ne répond plus au cerveau")
        lecture = None
        if ra.get("a") == ANGLE and ra.get("mm_age", 9999) < 400:
            tm = round((e["ms"] - ra["mm_age"]) / 20.0)
            if tm not in vus_m and a.suivi == "mur":
                # Le suivi par droite fait lui-même la part du mur, d'une avancée, d'un renfoncement et d'une ouverture.
                vus_m.add(tm)
                lecture = ra["mm"] if 0 < ra["mm"] <= PORTEE_MUR else None
                s_m = s - v_est * ra["mm_age"] / 1000.0
                cap_vise, v_vise = suivi.pas(s_m, mv["fait_deg"], lecture)
                R.append((s_m, ra["mm"], mv["fait_deg"], cap_vise))
            elif tm not in vus_m:
                vus_m.add(tm)
                lecture = ra["mm"] if 0 < ra["mm"] <= PORTEE_MUR else None
                # Un mur qui RECULE D'UN COUP de plus de --ouverture est une ouverture (porte, fin du mur) : avec un seul
                # côté, le suivre ferait tourner le robot dedans. On tient alors l'axe du mur ; il redevient un mur
                # quand il revient à moins de la moitié de cette valeur de sa place d'avant. Un robot qui part loin de
                # la consigne n'est pas dans ce cas : rien n'a reculé d'un coup (défaut vu en simulation le 2026-11-21).
                if lecture is not None:
                    if ouvert:
                        if lecture - ref <= a.ouverture / 2.0:
                            ouvert = False
                        else:
                            lecture = None
                    elif ref is not None and lecture - ref > a.ouverture:
                        ouvert = True
                        n_ouvert += 1
                        lecture = None
                    if lecture is not None:
                        ref = lecture if ref is None else 0.7 * ref + 0.3 * lecture
                s_m = s - v_est * ra["mm_age"] / 1000.0
                g, d = (lecture, None) if a.cote == "g" else (None, lecture)
                cap_vise, v_vise = suivi.pas(s_m, mv["fait_deg"], g, d)
                if lecture is None:
                    cap_vise = suivi.axe         # mur perdu ou ouverture : tout droit dans l'axe du mur, sans correction d'écart
                    perdu_mm += max(0.0, s - s_prec)
                R.append((s_m, ra["mm"], mv["fait_deg"], cap_vise))
                s_prec = s
        garde = 0.0
        if a.flanc and rb.get("light") and rb["light"][I_FLANC] >= a.flanc:      # le flanc serre le mur : on s'en écarte de 4°
            garde = -4.0 if a.cote == "g" else 4.0
            n_flanc += 1
        if now - t_ret >= 0.2:
            t_ret = now
            c = max(-40.0, min(40.0, cap_vise + garde))
            try:
                rr = get("/api/mouv?retouche=1&cap=%.1f&jusqua=%d&v=%d" % (c, min(a.distance, int(s) + a.horizon), int(v_vise)), timeout=1.5)
                if rr.get("retouche") == "prise":
                    n_ret += 1
            except Exception:
                pass                         # une retouche perdue : l'avance continue vers son but, la suivante la rattrape
        if now - t0 > limite:
            fin = "durée dépassée"
            get("/api/mouv?stop=1")
            break
    mj = get("/api/mouv")
    duree = time.time() - t0
    e = lire("apres")
    print("%s  fin : %s, %s mm faits pour %d demandés en %.1f s (%.0f mm/s en moyenne) ; raison : %s ; cap %+.1f° ; pare-chocs %s" % (
        heure(), mj.get("texte"), mj.get("fait_mm"), a.distance, mj.get("duree_ms", 0) / 1000.0,
        (mj.get("fait_mm") or 0) / max(0.1, mj.get("duree_ms", 1) / 1000.0), fin or mj.get("raison") or "aucune",
        mj.get("fait_deg", 0.0), e["robot"]["bump"]))
    print("              retouches prises : %d (le cerveau en compte %s) ; optique devant : plus forte lecture %s, %s ordre(s) ralenti(s) ; garde du flanc : %d fois" % (
        n_ret, mj.get("retouches"), mj.get("opt_max"), mj.get("opt_ralentis"), n_flanc))
    V = [(s_, mm) for s_, mm, _, _ in R if 0 < mm <= PORTEE_MUR]
    if V:
        ec = [mm - ecart for _, mm in V]
        print("              mur lu %d fois sur %d lectures (une tous les %.0f mm) : médiane %d mm, de %d à %d ; écart à la consigne : médian %+d mm, pire %+d mm, écart-type %.0f mm" % (
            len(V), len(R), (mj.get("fait_mm") or 0) / max(1, len(R)), statistics.median([mm for _, mm in V]), min(mm for _, mm in V),
            max(mm for _, mm in V), statistics.median(ec), max(ec, key=abs), statistics.pstdev(ec)))
        if a.suivi == "mur":
            print("              autres parois : %d avancée(s), %d recul(s) ou renfoncement(s), %d ouverture(s), %d prise(s) pour le mur ; "
                  "%.0f mm faits sur la droite du mur gardée à l'estime ; axe du mur trouvé à %+.1f° du cap de départ ; dernier cap visé %+.1f°" % (
                      suivi.n_pres, suivi.n_loin, suivi.n_ouvert, suivi.n_adopte, suivi.tenu_mm, suivi.axe, cap_vise))
        else:
            print("              mur perdu sur %.0f mm de chemin (%d ouverture(s)) ; axe du mur trouvé à %+.1f° du cap de départ ; dernier cap visé %+.1f°" % (
                perdu_mm, n_ouvert, suivi.axe, cap_vise))
    A1 = lectures("cote_arret_apres", 1.2, ANGLE)
    v1 = [x for x in A1 if x > 0]
    if v1:
        print("%s  à l'arrêt : mur lu à %d mm (consigne %d)." % (heure(), statistics.median(v1), ecart))
except Arret as x:
    code = 2
    print("%s  ARRÊT : %s." % (heure(), x))
    if parti:
        try:
            get("/api/mouv?stop=1")
        except Exception:
            pass
except KeyboardInterrupt:
    code = 3
    print("%s  interrompu." % heure())
    try:
        get("/api/mouv?stop=1")
    except Exception:
        pass
finally:
    if capteur_tourne:
        try:
            get("/api/radar?mode=fixe&doux=1&angle=0")
            limite = time.time() + 95.0 / max(1, lent_regle or 3) + 10.0
            while time.time() < limite:
                time.sleep(0.4)
                try:
                    if get("/api/state")["radar"]["servo"] == 0:
                        break
                except Exception:
                    continue
            time.sleep(1.0)
            ra = get("/api/state")["radar"]
            print("%s  capteur à %d° ; devant : %s mm." % (heure(), ra["servo"], ra.get("front_mm")))
        except Exception as x:
            print("%s  LE RETOUR DU CAPTEUR N'A PAS PU ÊTRE VÉRIFIÉ (%s)." % (heure(), type(x).__name__))
    journal.close()
sys.exit(code)
