# essai_retouche.py — premier essai en mouvement de la retouche d'une avance en cours (firmware v17).
#
#   python essai_retouche.py [ADRESSE] --prefixe CHEMIN/NOM [--depart 300] [--jusqua 600] [--cap -8] [--v1 100] [--v2 80]
#                            [--opt 100] [--marge 450]
#       pendant qu'enregistreur.py tourne (le firmware arrête les roues si la console TCP se ferme).
#
# Déroulement : capteur de distance devant (il faut la distance finale plus la marge de libre) ; une avance de --depart mm
# est lancée ; dès que le robot a fait 120 mm, UNE retouche : but repoussé à --jusqua mm, cap déplacé de --cap degrés
# (positif = vers la gauche), vitesse ramenée à --v2 ; la même retouche est envoyée une seconde fois 0,3 s plus tard,
# pour vérifier qu'une requête rejouée ne change rien. On attend la fin et on compare.
# Ce qu'on doit voir : le robot ne s'arrête pas à --depart mm (aucun creux de vitesse), il finit à --jusqua mm, tourné
# de --cap degrés, et le cerveau compte deux retouches.
# Le capteur de distance reste devant : l'arrêt automatique devant un obstacle joue comme pour toute avance.
import argparse
import json
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

p = argparse.ArgumentParser(description="Essai de la retouche d'une avance en cours (firmware v17).")
p.add_argument("adresse", nargs="?", default="192.168.18.25")
p.add_argument("--prefixe", required=True)
p.add_argument("--depart", type=int, default=300)
p.add_argument("--jusqua", type=int, default=600)
p.add_argument("--cap", type=float, default=-8.0)
p.add_argument("--v1", type=int, default=100)
p.add_argument("--v2", type=int, default=80)
p.add_argument("--opt", type=int, default=100)
p.add_argument("--marge", type=int, default=450)
a = p.parse_args()


def get(chemin, timeout=3.0):
    with urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def heure():
    t = time.time()
    return time.strftime("%H:%M:%S", time.localtime(t)) + (".%03d" % int((t % 1) * 1000))


e = get("/api/state")
rb = e["robot"]
refus = None
if "ret" not in e.get("mouv", {}):
    refus = "le firmware n'a pas la retouche (il faut la v17)"
elif not rb.get("ok") or rb.get("mode") != 3:
    refus = "le robot ne répond pas ou n'est pas en mode Safe (mode lu %s)" % rb.get("mode")
elif e.get("driving") or e["tour"]["etat"] in (1, 2) or e["mouv"]["etat"] == 1:
    refus = "le robot bouge déjà"
elif any(rb.get("bump", [0, 0])) or any(rb.get("drop", [0, 0])):
    refus = "pare-chocs enfoncé ou roue levée"
elif abs(e["radar"]["servo"]) > 2:
    refus = "le capteur de distance n'est pas devant (%d°)" % e["radar"]["servo"]
if refus:
    print("%s  RIEN N'EST ENVOYÉ : %s." % (heure(), refus))
    sys.exit(1)
# la place devant
get("/api/radar?mode=fixe&angle=0")
time.sleep(1.5)
D, vus = [], set()
t_fin = time.time() + 1.5
while time.time() < t_fin:
    time.sleep(0.08)
    s = get("/api/state")
    ra = s["radar"]
    if ra["a"] == 0 and ra["mm_age"] < 500:
        tm = round((s["ms"] - ra["mm_age"]) / 20.0)
        if tm not in vus:
            vus.add(tm)
            D.append(ra["mm"])
if len(D) < 4:
    print("%s  pas assez de lectures devant (%d) : rien ne bouge." % (heure(), len(D)))
    sys.exit(1)
pos = [x for x in D if x > 0]
libre = min(pos) if len(pos) * 2 >= len(D) else 4000
if libre - a.jusqua < a.marge:
    print("%s  pas assez de place devant : %d mm lus, il en faut %d. Rien ne bouge." % (heure(), libre, a.jusqua + a.marge))
    sys.exit(1)
print("%s  devant : %s ; départ pour %d mm à %d mm/s." % (heure(), ("%d mm" % libre) if libre < 4000 else "rien à portée", a.depart, a.v1))
journal = open(a.prefixe + "_retouche.jsonl", "a", encoding="utf-8")
r = get("/api/mouv?av=%d&v=%d%s" % (a.depart, a.v1, ("&opt=%d" % a.opt) if a.opt else ""))
if r.get("etat") != 1:
    print("%s  avance refusée : %s" % (heure(), r.get("raison")))
    sys.exit(1)
t0 = time.time()
prec, envois, v_mini, t_ret = None, 0, None, None
reponses = []
while True:
    time.sleep(0.04)
    try:
        s = get("/api/state")
    except Exception:
        if time.time() - t0 > 25:
            break
        continue
    mv = s["mouv"]
    now = time.time()
    v_est = None
    if prec is not None and now > prec[0]:
        v_est = (mv["fait_mm"] - prec[1]) / (now - prec[0])
    prec = (now, mv["fait_mm"])
    journal.write(json.dumps(dict(t=now, h=heure(), fait_mm=mv["fait_mm"], fait_deg=mv["fait_deg"], but=mv["but"], cap_vise=mv["cap_vise"],
                                  v=mv["v"], ret=mv["ret"], opt=mv["opt"], etat=mv["etat"], v_est=v_est, pc=s["robot"]["bump"],
                                  lb=s["robot"]["light"], devant=s["radar"]["front_mm"]), ensure_ascii=False) + "\n")
    if mv["etat"] != 1:
        break
    if envois == 0 and mv["fait_mm"] >= 120:
        rr = get("/api/mouv?retouche=1&cap=%.1f&jusqua=%d&v=%d" % (a.cap, a.jusqua, a.v2))
        reponses.append((mv["fait_mm"], rr.get("retouche"), rr.get("but"), rr.get("cap_vise"), rr.get("v")))
        envois, t_ret = 1, now
    elif envois == 1 and now - t_ret >= 0.3:
        rr = get("/api/mouv?retouche=1&cap=%.1f&jusqua=%d&v=%d" % (a.cap, a.jusqua, a.v2))
        reponses.append((mv["fait_mm"], rr.get("retouche"), rr.get("but"), rr.get("cap_vise"), rr.get("v")))
        envois = 2
    # le creux de vitesse : entre la retouche et les 100 derniers millimètres, le robot ne doit pas s'arrêter
    if envois >= 1 and v_est is not None and mv["fait_mm"] < a.jusqua - 100 and now - t_ret > 0.4:
        v_mini = v_est if v_mini is None else min(v_mini, v_est)
    if now - t0 > 25:
        get("/api/mouv?stop=1")
        print("%s  trop long : arrêt demandé." % heure())
        break
journal.close()
time.sleep(0.6)
mj = get("/api/mouv")
s = get("/api/state")
for k, (fm, rep, but, capv, v) in enumerate(reponses, 1):
    print("%s  retouche %d envoyée à %.0f mm : %s ; but %s mm, cap visé %s°, vitesse %s mm/s" % (heure(), k, fm, rep, but, capv, v))
print("%s  fin : %s, %s mm faits (demandé au départ %d, retouché à %d) en %.1f s ; cap %+.1f° (demandé %+.1f°) ; raison : %s" % (
    heure(), mj.get("texte"), mj.get("fait_mm"), a.depart, a.jusqua, mj.get("duree_ms", 0) / 1000.0, mj.get("fait_deg", 0.0), a.cap, mj.get("raison")))
print("              retouches comptées par le cerveau : %s ; vitesse la plus basse entre la retouche et les 10 derniers centimètres : %s mm/s" % (
    mj.get("retouches"), ("%.0f" % v_mini) if v_mini is not None else "?"))
print("              capteurs optiques de devant : seuil %s, plus forte lecture %s, %s ordre(s) ralenti(s) ; pare-chocs %s ; devant %s mm" % (
    mj.get("opt_seuil"), mj.get("opt_max"), mj.get("opt_ralentis"), s["robot"]["bump"], s["radar"]["front_mm"]))
bon = (mj.get("etat") == 2 and abs((mj.get("fait_mm") or 0) - a.jusqua) <= 15 and abs(mj.get("fait_deg", 0.0) - a.cap) <= 2.0
       and mj.get("retouches") == 2 and (v_mini is None or v_mini > 30))
print("ESSAI DE LA RETOUCHE :", "bon" if bon else "À REGARDER")
sys.exit(0 if bon else 2)
