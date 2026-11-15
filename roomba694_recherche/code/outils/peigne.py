# peigne.py — une « dent de peigne » sur un tapis que le robot peut prendre pour un vide : depuis le parquet, une avance
# droite sur le tapis, brosse latérale en marche, puis le retour en marche arrière sur le même trait.
#
# Pourquoi (journal_wifi.md § 56 à § 58) : en mode Safe le robot coupe ses roues et retombe en mode passif dès qu'il
# avance ou pivote avec un capteur de vide au-dessus d'un poil très sombre ; un recul droit, lui, passe toujours. En
# n'allant sur le tapis qu'en ligne droite depuis le parquet, on en ressort toujours en reculant, sans jamais y pivoter.
# C'est le robot qui décide de l'arrêt : ce programme ne met aucune alarme de son côté sur les capteurs de vide.
#
# Ce que fait une dent :
#   1. contrôles : robot qui répond, mode Safe, roues au sol, pare-chocs libre, capteurs de vide sur un sol clair ;
#   2. /api/mouv?av=DISTANCE&v=VITESSE&brosse=N (firmware v14) et attente de la fin ;
#   3. si le robot a quitté le mode Safe : touche f (l'utilisateur l'a permis pour ce tapis le 2026-11-15), une fois ;
#   4. retour : reculs droits de 300 mm au plus, brosse en marche, jusqu'à avoir refait la distance comptée à l'aller ;
#   5. une ligne dans PREFIXE_peigne.jsonl : heures, distances, raison de l'arrêt, capteurs de vide au bout et au retour.
# Il s'arrête sans rien tenter d'autre si le robot ne répond plus, si une roue se lève ou si le mode Safe ne revient pas.
# enregistreur.py doit tourner : toutes les lectures de la dent sont dans son journal.
#
# Usage : python peigne.py ADRESSE PREFIXE NOM [--distance 900] [--vitesse 150] [--brosse 40] [--sans-retour]
import argparse
import json
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
p_ = argparse.ArgumentParser(description="Une avance droite sur un tapis, brosse latérale en marche, et le retour en marche arrière.")
p_.add_argument("adresse")
p_.add_argument("prefixe")
p_.add_argument("nom", help="nom de la dent, pour le journal (par exemple v127)")
p_.add_argument("--distance", type=int, default=900)
p_.add_argument("--vitesse", type=int, default=150)
p_.add_argument("--brosse", type=int, default=40)
p_.add_argument("--sans-retour", action="store_true", help="laisser le robot au bout de la dent")
a = p_.parse_args()
a.distance = max(100, min(2000, a.distance))
SAFE = 3


def get(chemin, t=6):
    return urllib.request.urlopen("http://%s%s" % (a.adresse, chemin), timeout=t).read().decode("utf-8", "replace")


def robot():
    s = json.loads(get("/api/state"))
    r = s["robot"]
    return {"ok": bool(r.get("ok")) and r.get("age", 9999) < 1500, "mode": r.get("mode"), "vide": r.get("cliff"), "pare": r.get("bump"),
            "leve": r.get("drop"), "devant": (s.get("radar") or {}).get("front_mm"), "cap": (s.get("pose") or {}).get("cap")}


CAP_MAX = 12.0     # degrés : au-delà, le robot ne va plus droit (brosse prise dans les franges, roue qui patine)


def mouvement(requete, attente=30.0):
    """Lance un mouvement et l'attend. Arrêt demandé par ce programme dès que le cap s'écarte de plus de CAP_MAX :
    le 2026-11-15 à 9 h 57 une dent a pivoté de 93° au bord du tapis, le cerveau a poussé jusqu'au bout, et le retour
    « tout droit » est alors parti dans une autre direction (journal_wifi.md § 58). Renvoie le compte rendu du cerveau,
    avec « pivot » vrai si l'arrêt vient d'ici."""
    m = json.loads(get("/api/mouv?" + requete))
    if m.get("etat") != 1:
        return m
    fin = time.time() + attente
    while time.time() < fin:
        time.sleep(0.12)
        m = json.loads(get("/api/mouv"))
        if m.get("etat") != 1:
            return m
        if abs(float(m.get("fait_deg") or 0.0)) > CAP_MAX:
            get("/api/mouv?stop=1")
            time.sleep(0.3)
            m = json.loads(get("/api/mouv"))
            m["pivot"] = True
            return m
    get("/api/mouv?stop=1")
    return json.loads(get("/api/mouv"))


def heure():
    return time.strftime("%H:%M:%S")


J = {"dent": a.nom, "debut": heure(), "demande_mm": a.distance, "vitesse": a.vitesse, "brosse": a.brosse}
r = robot()
J["depart"] = r
print(heure(), "dent", a.nom, ": départ", r)
refus = None
if not r["ok"]:
    refus = "le robot ne répond pas"
elif r["mode"] != SAFE:
    refus = "le robot n'est pas en mode Safe (mode lu %s)" % r["mode"]
elif any(r["leve"]) or any(r["pare"]):
    refus = "roue levée ou pare-chocs enfoncé"
elif min(r["vide"]) < 2000:
    refus = "un capteur de vide n'est pas sur un sol clair (%s) : partir du parquet" % r["vide"]
if refus:
    J["refus"] = refus
    print(heure(), "REFUS :", refus)
else:
    m = mouvement("av=%d&v=%d&brosse=%d" % (a.distance, a.vitesse, a.brosse))
    time.sleep(0.6)
    r = robot()
    J["aller"] = {"fin": heure(), "fait_mm": m.get("fait_mm"), "cap_deg": m.get("fait_deg"), "raison": m.get("raison"), "etat": m.get("texte")}
    J["bout"] = r
    print(heure(), "   aller : %s mm, cap %+.1f°, « %s » ; au bout : mode %s, vide %s, devant %s mm"
          % (m.get("fait_mm"), m.get("fait_deg") or 0.0, m.get("raison"), r["mode"], r["vide"], r["devant"]))
    fait = float(m.get("fait_mm") or 0.0)
    devie = abs(float(m.get("fait_deg") or 0.0)) > CAP_MAX or bool(m.get("pivot"))
    if devie:
        J["aller"]["pivot"] = True
    if not r["ok"] or any(r["leve"]):
        J["arret"] = "robot muet ou roue levée au bout de la dent : rien d'autre n'est envoyé"
        print(heure(), "ARRÊT :", J["arret"])
    elif devie:
        # Le robot n'est plus dans l'axe de la dent : un recul « de la distance comptée » partirait ailleurs, à l'aveugle.
        J["arret"] = "le robot a pivoté de %+.0f° : pas de retour automatique" % float(m.get("fait_deg") or 0.0)
        print(heure(), "ARRÊT :", J["arret"])
    elif not a.sans_retour and fait > 20:
        if r["mode"] != SAFE:
            get("/api/cmd?c=f")
            time.sleep(1.5)
            r = robot()
            J["safe_repris"] = {"heure": heure(), "mode": r["mode"]}
            print(heure(), "   mode Safe repris : mode lu", r["mode"])
        if r["mode"] != SAFE:
            J["arret"] = "le mode Safe ne revient pas : rien d'autre n'est envoyé"
            print(heure(), "ARRÊT :", J["arret"])
        else:
            reste, reculs = fait, []
            while reste > 15:
                pas = int(min(300.0, reste))
                m = mouvement("av=%d&v=80&brosse=%d" % (-pas, a.brosse))
                reculs.append({"demande": -pas, "fait_mm": m.get("fait_mm"), "raison": m.get("raison")})
                if m.get("etat") != 2 or m.get("pivot") or abs(float(m.get("fait_mm") or 0.0)) < 0.5 * pas:
                    print(heure(), "   recul interrompu :", m.get("raison"), "(le robot pivotait)" if m.get("pivot") else "")
                    break
                reste -= abs(float(m.get("fait_mm")))
                time.sleep(0.3)
            time.sleep(0.5)
            r = robot()
            J["retour"] = {"fin": heure(), "reculs": reculs, "reste_mm": round(reste), "robot": r}
            print(heure(), "   retour : %d recul(s), reste %.0f mm ; mode %s, vide %s" % (len(reculs), reste, r["mode"], r["vide"]))
with open(a.prefixe + "_peigne.jsonl", "a", encoding="utf-8", newline="\n") as f:
    f.write(json.dumps(J, ensure_ascii=False) + "\n")
