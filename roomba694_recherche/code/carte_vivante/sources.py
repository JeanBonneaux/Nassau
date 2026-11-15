# sources.py — d'où viennent les données de la carte vivante : les fichiers d'un enregistrement, lus en direct pendant
# que l'enregistreur et la navigation les écrivent, ou rejoués après coup à la vitesse voulue.
#
# Tout est lu, rien n'est écrit dans ces fichiers et rien n'est demandé au robot :
#   NOM_capteurs.csv            le journal du cerveau (enregistreur.py), suivi ligne après ligne ;
#   NOM[_x]_stations.json       explorer3.py : chaque tour sur place, avec la position que le filtre lui donne sur le plan ;
#   NOM[_x]_explorer3.txt       explorer3.py : départ donné, destinations reçues, atteintes, arrêts ;
#   NOM_CIBLES.json             les destinations données à explorer3.py ;
#   NOM_essai_tours.json        essai_tours.py : tours sur place faits au même endroit, jugés par le filtre ;
#   NOM*passage*.txt            la sortie de passage.py, si elle a été gardée dans un fichier : lignes POSE=U,V,CAP ;
#   NOM*balise*.txt             la sortie de balise_base.py : où passe l'axe de la base par rapport au robot ;
#   NOM_tour_xxx.json           un tour sur place fait à la main par la navigation, avec la position qu'elle tenait alors ;
#   NOM_etat.jsonl              /api/state relu par l'enregistreur : version du firmware, tour sur place en cours, charge
#                               de la batterie, robot posé ou non sur sa base ; et, pour la feuille « Capteurs » de la page,
#                               température, gyroscope, capteur de distance, réflexes, brosses (fonction plus_etat) ;
#   NOM_e.csv                   les réponses à la touche e : boutons, mur, saleté, roulette avant, courants des brosses ;
#   NOM_console.txt             ce que le cerveau écrit sur sa console, dont le texte que le robot envoie de lui-même.
# Les champs « sta » et « ap » de /api/state (réseaux Wi-Fi) ne sont jamais lus ici, et les lignes de la console
# repassent par les règles de masquage de l'enregistreur (nom du réseau de la maison, identifiants de l'appareil).
# À côté du plan (plan_lidar/, hors dépôt), ce que la navigation a appris de l'appartement (classe Connaissances) :
#   obstacles.json              les obstacles trouvés par le robot et absents du plan (explorer3.py --plan-ferme) ;
#   reperes_tours.json          les repères : tours sur place déjà faits, sur lesquels un nouveau tour se recale ;
#   reperes_AAAAMMJJ*.json      les notes de la dernière carte quadrillée envoyée (carte_grille.py --reperes).
import bisect
import datetime
import glob
import json
import math
import os
import re
import time

from suivi import ANGLES_OPTIQUES, C_, K_GYRO, MS_, RAYON, RAYON_IR, T_, X_, Y_, LecteurCsv, carto_mod

RE_MIN = re.compile(r"^\[\s*([\d.]+) min\]\s?(.*)$")
RE_DEPART = re.compile(r"localisation : filtre à \d+ hypothèses autour du pixel \((-?[\d.]+), (-?[\d.]+)\), cap (-?[\d.]+)")
RE_RECUES = re.compile(r"cibles reçues \(série (\S+)\) : \[(.*)\]")
RE_PAIRE = re.compile(r"\((-?[\d.]+), (-?[\d.]+)\)")
RE_VERS = re.compile(r"vers la cible \((-?[\d.]+), (-?[\d.]+)\) du plan : (\d+) étapes(.*)")
RE_CIBLE = re.compile(r"cible \((-?[\d.]+), (-?[\d.]+)\)(.*)")
RE_ARRETE = re.compile(r"arrêté : (.*?)(?: ; robot en .*)?$")
RE_FIN = re.compile(r"^fin : (.*?) \|")
RE_NOM = re.compile(r"_(\d{8})_(\d{6})_capteurs\.csv$")
RE_POSE = re.compile(r"^POSE=(-?[\d.]+),(-?[\d.]+),(-?[\d.]+)\s*$", re.M)
RE_AXE = re.compile(r"AXE de la base à ([+-]?\d+) mm du centre du robot")
RE_NOTES = re.compile(r"^reperes_(\d{4})(\d{2})(\d{2})[^/\\]*\.json$")


def lire_csv(chemin):
    lect, lignes = LecteurCsv(), []
    with open(chemin, encoding="utf-8", errors="replace") as f:
        for texte in f:
            if lect.ix is None:
                lect.entete(texte)
                continue
            r = lect.ligne(texte.rstrip("\n"))
            if r is not None:
                lignes.append(r)
    return lignes


def t_heure(heure, t_ref):
    """« 12:49:20 » -> secondes de l'horloge du PC, le jour de t_ref"""
    d = datetime.datetime.fromtimestamp(t_ref)
    h, m, s = (int(x) for x in heure.split(":"))
    t = d.replace(hour=h, minute=m, second=s, microsecond=0).timestamp()
    if t - t_ref > 43200:
        t -= 86400
    elif t_ref - t > 43200:
        t += 86400
    return t


def _pareil(r, q, tol_mm=3.0, tol_deg=0.25):
    return abs(r[C_] - q["cap_pos"]) <= tol_deg and abs(r[X_] - q["x_mm"]) <= tol_mm and abs(r[Y_] - q["y_mm"]) <= tol_mm


def parois_tour(mesures, X, Y, cap, s, H):
    """Les parois vues par le capteur de distance pendant un tour sur place, lues comme le fait la navigation
    (carto.paliers_souples) : quand la distance reste la même sur une douzaine de degrés au moins, c'est une surface
    vue de face, à cette distance, dans la direction du milieu. Renvoie une liste plate [u1, v1, u2, v2, …] : un trait
    de 12 cm par surface, en travers du regard (un seul tour ne dit pas si c'est un mur ou un pied de meuble : ce sont
    les traits de plusieurs tours, mis bout à bout, qui dessinent un mur). mesures : [[dixièmes de degré depuis le
    début du tour, mm], …] ; X, Y, cap : position du robot sur le plan et cap au début du tour (mm, degrés)."""
    if carto_mod is None or not mesures:
        return []
    try:
        pal = carto_mod.paliers_souples([m[0] / 10.0 for m in mesures], [m[1] for m in mesures])
    except Exception:                                             # mesures incomplètes : pas de parois pour ce tour
        return []
    seg = []
    for a, dist, larg, _ in pal:
        if larg < 12.0 or dist > 3500.0:
            continue
        ang = math.radians(cap + a)
        px, py = X + dist * math.cos(ang), Y + dist * math.sin(ang)
        tx, ty = -math.sin(ang) * 60.0, math.cos(ang) * 60.0
        seg += [round((px - tx) * s, 1), round(H - (py - ty) * s, 1), round((px + tx) * s, 1), round(H - (py + ty) * s, 1)]
    return seg


def faits_stations(J, R, Tt, s, H):
    """Les tours sur place d'un passage d'explorer3.py guidé par le plan : une ancre à la fin de chaque tour (la position
    que le filtre lui a donnée), pour le premier une ancre au départ (la position donnée au programme), et les parois
    vues pendant chaque tour."""
    ancres, obstacles, parois = [], [], []
    if J.get("mode") != "exploration3" or "plan" not in J or not Tt:
        return ancres, obstacles, parois                          # passage sans le plan : ses positions ne sont pas dans son repère
    infos, t_fin = J.get("plan", []), None
    for q, st in enumerate(J.get("stations", [])):
        info = infos[q] if q < len(infos) else {}
        av, ap, pose = st.get("avant"), st.get("apres"), st.get("pose")
        if not av or not ap or not pose or not st.get("heure"):
            continue
        # fin du tour : la dernière ligne du journal où le cerveau est à la position « apres », autour de l'heure notée
        t_h = t_heure(st["heure"], Tt[0])
        t_fin = t_h
        j = bisect.bisect_right(Tt, t_h + 1.5) - 1
        while j >= 0 and Tt[j] > t_h - 25.0:
            if _pareil(R[j], ap):
                while j > 0 and _pareil(R[j - 1], ap):            # le robot ne bouge plus depuis cette ligne-là
                    j -= 1
                t_fin = Tt[j]
                break
            j -= 1
        cle = f"{st.get('heure')}|{st.get('nom')}|{st.get('depart_cerveau')}"
        duree = (st.get("duree_ms") or 12000) / 1000.0
        if q == 0 and st.get("depart"):
            t_deb = t_fin - duree - 1.5
            j = bisect.bisect_right(Tt, t_fin - 0.5 * duree) - 1
            while j >= 0 and Tt[j] > t_fin - duree - 40.0:
                if _pareil(R[j], av, 1.5, 0.06):
                    t_deb = Tt[j]
                    break
                j -= 1
            d = st["depart"]
            ancres.append({"cle": "dep|" + cle, "t": t_deb, "src": "depart", "X": d[0], "Y": d[1], "C": d[2],
                           "b": (av["x_mm"], av["y_mm"], av["cap_pos"]), "info": {"nom": "départ"}})
        if info.get("garde", True):
            echelle = info.get("echelle_gyro") or J.get("k_gyro") or K_GYRO
            # Recalé sur les repères (reperes.py) : la pose du fichier en tient déjà compte. On garde le nombre de
            # repères d'accord, l'écart avec le filtre seul, et le cap s'il a été repris sur eux.
            rep = info.get("reperes") or None
            if rep:
                rep = {"n": rep.get("n"), "mm": round(math.hypot(rep.get("dx") or 0.0, rep.get("dy") or 0.0)),
                       "cap": (rep.get("cap") or {}).get("corrige")}
            ancres.append({"cle": "st|" + cle, "t": t_fin, "src": "filtre" if info.get("filtre") else "plan",
                           "X": pose[0], "Y": pose[1], "C": pose[2] + echelle * (ap["cap_pos"] - av["cap_pos"]),
                           "b": (ap["x_mm"], ap["y_mm"], ap["cap_pos"]),
                           "info": {"nom": str(st.get("nom")), "genre": st.get("genre"), "note": info.get("note"), "etal": info.get("etalement_mm"),
                                    "n": st.get("n"), "tapis": bool(st.get("tapis")), "rep": rep}})
            if info.get("filtre") and st.get("mesures"):
                seg = parois_tour(st["mesures"], pose[0], pose[1], pose[2], s, H)
                if seg:
                    parois.append((t_fin, "st|" + cle, seg))
    for c in J.get("contacts", []):
        if c[2] != "contact" and t_fin is not None:               # les contacts du pare-chocs sont déjà vus dans le journal
            obstacles.append((t_fin, round(c[0] * s, 1), round(H - c[1] * s, 1), c[2]))
    return ancres, obstacles, parois


def faits_essai_tours(J, R, Tt, s, H, mtime):
    """Les tours d'essai_tours.py : le fichier ne donne que le cap du cerveau avant et après chaque tour ; on retrouve
    l'instant dans le journal, en remontant depuis l'heure d'écriture du fichier."""
    ancres = []
    j_max = bisect.bisect_right(Tt, mtime + 1.0) - 1
    tours = J.get("tours", [])
    for q in range(len(tours) - 1, -1, -1):
        tr = tours[q]
        f = tr.get("filtre")
        if not f or "cap_cerveau_apres" not in tr:
            continue
        j = j_max
        while j >= 0 and abs(R[j][C_] - tr["cap_cerveau_apres"]) > 0.06:
            j -= 1
        if j < 0:
            break
        j1 = j
        while j1 > 0 and abs(R[j1 - 1][C_] - tr["cap_cerveau_apres"]) <= 0.06:
            j1 -= 1
        j0 = j1
        while j0 >= 0 and abs(R[j0][C_] - tr["cap_cerveau_avant"]) > 0.06:
            j0 -= 1
        cle = f"{tr.get('cap_cerveau_avant')}|{tr['cap_cerveau_apres']}"
        ancres.append({"cle": "et|" + cle, "t": min(Tt[j], Tt[j1] + 0.3), "src": "filtre", "X": f["u"] / s, "Y": (H - f["v"]) / s, "C": f["cap"],
                       "b": (R[j1][X_], R[j1][Y_], R[j1][C_]),
                       "info": {"nom": "essai", "genre": "essai_tours", "note": f.get("note"), "etal": f.get("etalement_mm"), "n": tr.get("n")}})
        if j0 < 0:
            break
        if q == 0 and J.get("depart"):
            d = J["depart"]
            ancres.append({"cle": "etdep|" + cle, "t": Tt[j0], "src": "depart", "X": d[0] / s, "Y": (H - d[1]) / s, "C": d[2],
                           "b": (R[j0][X_], R[j0][Y_], R[j0][C_]), "info": {"nom": "départ"}})
        j_max = j0
    return ancres


def faits_explorer3(texte, t0, cle, su):
    """Ce que dit explorer3.py, daté d'après ses minutes : événements du journal, état des destinations au fil du temps,
    et la position de départ qu'il annonce."""
    evts, hist, ancres, cibles = {}, [], [], []
    t_prec = t0

    def nom(u, v):
        return su.gr.nom(float(u), float(v))

    def ev(n, t, g, x, u=None, v=None):
        e = {"t": t, "g": g, "x": x}
        if u is not None:
            e["u"], e["v"] = round(float(u), 1), round(float(v), 1)
        evts[f"{cle}|{n}"] = e

    def trouver(u, v):
        for c in cibles:
            if round(c[0]) == round(float(u)) and round(c[1]) == round(float(v)) and c[2] in ("à venir", "en cours"):
                return c
        return None

    for n, ligne in enumerate(texte.splitlines()):
        m = RE_MIN.match(ligne)
        if not m:
            continue
        t = max(t_prec + 0.001, t0 + float(m[1]) * 60.0)
        t_prec = t
        x = m[2].strip()
        q = RE_DEPART.search(x)
        if q:
            ancres.append({"cle": f"ann|{cle}", "t": t0, "src": "annonce", "X": float(q[1]) / su.s, "Y": (su.H - float(q[2])) / su.s,
                           "C": float(q[3]), "b": None, "info": {"nom": "départ"}})
            cibles = []
            hist.append((t0, []))
            continue
        q = RE_RECUES.search(x)
        if q:
            cibles = [[float(a), float(b), "à venir"] for a, b in RE_PAIRE.findall(q[2])]
            ev(n, t, "cible", ("Destinations reçues : " if len(cibles) > 1 else "Destination reçue : ") + ", ".join(nom(c[0], c[1]) for c in cibles))
        elif RE_VERS.search(x):
            q = RE_VERS.search(x)
            c = trouver(q[1], q[2])
            if c:
                c[2] = "en cours"
            if "essai" in q[4]:
                ev(n, t, "info", f"Nouvel essai vers {nom(q[1], q[2])}, en contournant l'obstacle", q[1], q[2])
        elif RE_CIBLE.search(x):
            q = RE_CIBLE.search(x)
            c = trouver(q[1], q[2])
            if "atteinte" in q[3]:
                if c:
                    c[2] = "atteinte"
                ev(n, t, "cible", f"Destination {nom(q[1], q[2])} atteinte", q[1], q[2])
            elif "laissée" in q[3]:
                if c:
                    c[2] = "laissée"
                ev(n, t, "alerte", f"Destination {nom(q[1], q[2])} abandonnée" + (" : pas de chemin libre sur le plan" if "pas de chemin" in q[3] else " après trois essais"), q[1], q[2])
        elif "quelque chose sur un passage déjà roulé" in x:
            ev(n, t, "info", "Quelque chose barre un passage déjà roulé : attente de 8 s, puis nouvel essai")
        elif "avance arrêtée, la suite de ce trajet" in x:
            ev(n, t, "info", "Avance arrêtée par la navigation : une roue patinait ; la suite du trajet se fait lentement")
        elif RE_ARRETE.search(x):
            if "pare-chocs" in x:
                continue                                          # déjà dit par le contact vu dans le journal du cerveau
            ev(n, t, "alerte", "Trajet arrêté : " + RE_ARRETE.search(x)[1])
        elif RE_FIN.search(x):
            for c in cibles:
                if c[2] in ("à venir", "en cours"):
                    c[2] = "laissée"
            ev(n, t, "info", "Fin du trajet : " + RE_FIN.search(x)[1])
        elif any(mot in x for mot in ("impossible", "refusé", "liaison :", "ne répond plus")):
            ev(n, t, "alerte", x[0].upper() + x[1:])
        else:
            continue
        hist.append((t, [list(c) for c in cibles]))
    return {"evts": evts, "hist": hist, "ancres": ancres}


def faits_tour(J, R, Tt, s, H, mtime, cle):
    """Un tour sur place fait à la main par la navigation (fichier NOM_tour_xxx.json) : s'il porte la position qu'elle
    tenait alors sur le plan (« pose_plan_avant » : pixel et cap) avec celle du cerveau au même instant (« depart »),
    c'est une position donnée, datée par la dernière ligne du journal où le cerveau est à ce départ. Renvoie cette
    ancre et les parois vues pendant le tour."""
    p, d = J.get("pose_plan_avant"), J.get("depart")
    if not p or not d or not Tt:
        return [], []
    q = {"x_mm": float(d[0]), "y_mm": float(d[1]), "cap_pos": float(d[2])}
    j = bisect.bisect_right(Tt, mtime + 1.0) - 1
    while j >= 0 and Tt[j] > mtime - 120.0:
        if _pareil(R[j], q, 3.0, 0.3):
            X, Y = float(p[0]) / s, (H - float(p[1])) / s
            seg = parois_tour(J.get("points"), X, Y, float(p[2]), s, H)
            return ([{"cle": "tour|" + cle, "t": Tt[j], "src": "pose", "X": X, "Y": Y, "C": float(p[2]),
                      "b": (q["x_mm"], q["y_mm"], q["cap_pos"]), "info": {"nom": "la navigation, avant un tour fait à la main"}}],
                    [(Tt[j], "tour|" + cle, seg)] if seg else [])
        j -= 1
    return [], []


def faits_balise(texte, t, cle, su):
    """La sortie de balise_base.py (un tour sur place dans les faisceaux de la base), gardée dans un fichier : ce
    qu'elle dit de l'axe de la base, et la position POSE= qu'elle redonne. t : heure d'écriture du fichier."""
    F = {"evts": {}, "ancres": []}
    m = RE_AXE.search(texte)
    if m:
        a = int(m[1])                                             # positif : l'axe passe à gauche du robot tourné vers la base
        x = (f"robot dans l'axe de sa base à {max(1, round(abs(a) / 10.0))} cm près" if abs(a) < 25
             else f"l'axe de la base passe à {round(abs(a) / 10.0)} cm à {'gauche' if a > 0 else 'droite'} du robot tourné vers elle")
    elif "rouge seulement" in texte:
        x = "robot du côté rouge, l'axe de la base passe à sa gauche quand il lui fait face"
    elif "vert seulement" in texte:
        x = "robot du côté vert, l'axe de la base passe à sa droite quand il lui fait face"
    elif "aucun code reçu" in texte:
        x = "aucun signal reçu ici (à plus de 2 m de la base, ou trop de côté)"
    else:
        x = None
    if x:
        F["evts"][f"{cle}|axe"] = {"t": t, "g": "base", "x": "Mesure par les faisceaux de la base : " + x}
    poses = RE_POSE.findall(texte)
    if poses:
        u, v, cap = (float(q) for q in poses[-1])
        F["ancres"].append({"cle": f"pose|{cle}|{t:.1f}", "t": t, "src": "pose", "X": u / su.s, "Y": (su.H - v) / su.s, "C": cap,
                            "b": None, "info": {"nom": "balise_base.py"}})
    return F


class Seance:
    """les fichiers qu'écrivent les programmes de navigation pour un enregistrement ; relus quand ils changent"""

    def __init__(self, prefixe, su):
        self.prefixe, self.su = prefixe, su
        self.vus, self.par_fichier, self.t0 = {}, {}, {}

    def lire(self, R, Tt):
        """relit les fichiers qui ont changé ; renvoie True si quelque chose a changé"""
        change = False
        presents = set()
        for chemin in glob.glob(glob.escape(self.prefixe) + "*"):
            nom = chemin[len(self.prefixe):]
            genre = ("stations" if nom.endswith("_stations.json") else "explorer3" if nom.endswith("_explorer3.txt")
                     else "essai" if nom.endswith("_essai_tours.json") else "cibles" if nom == "_CIBLES.json"
                     else "passage" if (nom.endswith(".txt") and "passage" in nom)
                     else "balise" if (nom.endswith(".txt") and "balise" in nom)
                     else "tour" if (nom.endswith(".json") and nom.startswith("_tour_")) else None)
            if genre is None:
                continue
            presents.add(chemin)
            try:
                st = os.stat(chemin)
                sig = (st.st_mtime, st.st_size)
                if self.vus.get(chemin) == sig:
                    continue
                with open(chemin, encoding="utf-8", errors="replace") as f:
                    texte = f.read()
                F = {"genre": genre}
                if genre == "stations":
                    F["ancres"], F["obstacles"], F["parois"] = faits_stations(json.loads(texte), R, Tt, self.su.s, self.su.H)
                    F["tronc"] = chemin[:-len("_stations.json")]
                elif genre == "essai":
                    F["ancres"] = faits_essai_tours(json.loads(texte), R, Tt, self.su.s, self.su.H, st.st_mtime)
                elif genre == "explorer3":
                    # Heure de lancement du passage : l'heure d'écriture du fichier moins les minutes de sa dernière ligne
                    # (à 3 s près : les minutes n'ont qu'une décimale). L'heure de création du fichier ne convient pas :
                    # Windows redonne celle de l'ancien fichier à un fichier recréé sous le même nom dans les 15 s.
                    # Si le fichier a été écrit après la fin du journal (cerveau éteint en route le 2026-11-13 à 17 h 19 :
                    # le programme a encore écrit vingt minutes plus tard, avec des minutes arrêtées), c'est la fin du
                    # journal qui sert de repère.
                    if chemin not in self.t0:
                        minutes = [float(m[1]) for m in map(RE_MIN.match, texte.splitlines()) if m]
                        fin = min(st.st_mtime, Tt[-1] + 5.0) if Tt else st.st_mtime
                        self.t0[chemin] = fin - (minutes[-1] * 60.0 if minutes else 0.0)
                    F.update(faits_explorer3(texte, self.t0[chemin], nom, self.su))
                    F["tronc"] = chemin[:-len("_explorer3.txt")]
                elif genre == "cibles":
                    J = json.loads(texte)
                    F["attente"] = (st.st_mtime, [[float(c[0]), float(c[1]), "donnée"] for c in J.get("cibles", [])])
                elif genre == "passage":
                    poses = RE_POSE.findall(texte)
                    if poses:
                        u, v, cap = (float(x) for x in poses[-1])
                        F["ancres"] = [{"cle": f"pose|{st.st_mtime:.1f}|{len(poses)}", "t": st.st_mtime, "src": "pose", "X": u / self.su.s,
                                        "Y": (self.su.H - v) / self.su.s, "C": cap, "b": None, "info": {"nom": "passage.py"}}]
                elif genre == "balise":
                    F.update(faits_balise(texte, st.st_mtime, nom, self.su))
                elif genre == "tour":
                    F["ancres"], F["parois"] = faits_tour(json.loads(texte), R, Tt, self.su.s, self.su.H, st.st_mtime, nom)
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                continue                                          # fichier en cours d'écriture ou incomplet : relu au prochain passage
            self.vus[chemin], self.par_fichier[chemin] = sig, F
            change = True
        for chemin in list(self.par_fichier):                     # fichier renommé (relance.py) : ses faits reviennent sous le nouveau nom
            if chemin not in presents:
                del self.par_fichier[chemin], self.vus[chemin]
                self.t0.pop(chemin, None)
                change = True
        return change

    def faits(self):
        ancres, evts, hist, obstacles, attente, parois = {}, {}, [], {}, None, {}
        # le départ annoncé par explorer3.py (au pixel près) ne sert que tant que son premier tour n'est pas écrit :
        # ensuite le fichier des tours donne ce départ exactement, avec la position du cerveau au même instant
        precis = {F["tronc"] for F in self.par_fichier.values() if F["genre"] == "stations" and any(a["src"] == "depart" for a in F["ancres"])}
        for F in self.par_fichier.values():
            for a in F.get("ancres", []):
                if a["src"] == "annonce" and F.get("tronc") in precis:
                    continue
                ancres[a["cle"]] = a
            evts.update(F.get("evts", {}))
            hist.extend(F.get("hist", []))
            for o in F.get("obstacles", []):
                obstacles[(o[1], o[2], o[3])] = o
            for p in F.get("parois", []):
                parois[p[1]] = p
            if F.get("attente"):
                attente = F["attente"]
        hist.sort(key=lambda h: h[0])
        return {"ancres": sorted(ancres.values(), key=lambda a: a["t"]), "evts": evts, "hist": hist,
                "obstacles": sorted(obstacles.values()), "attente": attente,
                "parois": sorted(((p[0], p[2]) for p in parois.values()), key=lambda p: p[0])}


def version_firmware(texte):
    """« v10 Nov 13 2026 11:53:11 » -> 10, comme le lit explorer3.py ; None si ce n'est pas lisible"""
    try:
        return int("".join(c for c in str(texte).split()[0] if c.isdigit()))
    except (ValueError, IndexError):
        return None


def _garde(d, cles):
    """les seules clés voulues d'un dictionnaire de l'état, quand elles y sont"""
    return {c: d[c] for c in cles if isinstance(d, dict) and c in d}


def plus_etat(e, r):
    """Ce que la feuille « Capteurs » de la page montre de l'état du cerveau, champ par champ : rien n'est recopié en
    bloc. Les parties « sta » et « ap » (réseaux Wi-Fi) et le nom de la carte ne sont pas lus."""
    d = _garde(e, ("ver", "lecture", "speed", "driving", "rst"))
    d.update(_garde(r, ("ok", "v", "i", "t", "q", "qmax", "chg", "mode", "wall", "btn", "cur")))
    d["robot_age"] = r.get("age")                                 # millisecondes depuis la dernière réponse du robot au cerveau
    d["redem"] = e.get("robot_redem")
    for nom, cles in (("imu", ("ok", "cal", "yaw", "rate", "biais")), ("pose", ("dist", "leves", "sauts", "gyro")),
                      ("radar", ("mode", "mm", "a", "mm_age", "present", "seuil", "securite")), ("tour", ("etat", "n")),
                      ("mouv", ("etat", "n", "fait_mm", "fait_deg")), ("brosse", ("lat", "max", "marches")),
                      ("reflexe", ("arrets", "refus", "verrou", "cause")), ("console", ("perdus",)), ("texte", ("lignes",))):
        g = _garde(e.get(nom), cles)
        if g:
            d[nom] = g
    return d


E_NOMBRES = ("btn_clean", "btn_spot", "btn_dock", "mur", "mur_signal", "mur_virtuel", "salete", "roulette", "base", "cur_g", "cur_d",
             "cur_brosse", "cur_lat", "surint")
RE_RESEAU = re.compile(r"([Rr]éseau de la maison « )[^»]*( »)")
RE_SSID = re.compile(r"(?i)(ssid\W{0,3})\S+")
RE_ID = (re.compile(r"\b[0-9A-Fa-f]{4}(?: [0-9A-Fa-f]{3,4}){2,}\b"), re.compile(r"\b[0-9A-Fa-f]{2}(?:[:-][0-9A-Fa-f]{2}){5}\b"),
         re.compile(r"\b[0-9A-Fa-f]{12,}\b"))
MOUVEMENTS = ("Mouvement", "Tour sur place", "Avance", "Recule", "Tourne", "Roues arrêtées", "Vitesse réglée", "Brosse")
ALERTES = ("Réflexe", "Radar : obstacle", "Pas de réponse du robot", "## liaison", "## la carte a fermé", "Le robot envoie du texte",
           "Redémarrage de la carte", "Erreur")


def ligne_console(texte):
    """Une ligne de NOM_console.txt -> (genre, texte à montrer), ou None pour une ligne à ne pas montrer.
    Genres : « robot » (le texte que le robot écrit de lui-même), « alerte », « mouv » (ordres de mouvement et leur
    résultat), « ordre » (touche envoyée par un outil), « info ». Les relevés demandés chaque seconde par
    l'enregistreur (touche e) ne sont pas montrés. L'enregistreur masque déjà le nom du réseau de la maison et les
    identifiants de l'appareil ; les mêmes règles sont repassées ici, par précaution."""
    x = RE_SSID.sub(r"\1…", RE_RESEAU.sub(r"\1…\2", texte.rstrip()))
    s = x.strip()
    if not s:
        return None
    if s.startswith(">>"):
        touche = s[2:].strip()
        return None if touche == "e" else ("ordre", "touche envoyée : " + touche)
    if s.startswith("texte du robot"):
        for r in RE_ID:
            s = r.sub("[identifiant masqué]", s)
        return "robot", s.split(":", 1)[1].strip() if ":" in s else s
    if s.startswith(ALERTES) or " refusé" in s:                   # « Mouvement 12 refusé : … », « Tour sur place refusé : … »
        return "alerte", s
    # « 5 ou espace pour arrêter. » : un rappel pour qui pilote au clavier, sans intérêt sur la carte
    return ("mouv" if s.startswith(MOUVEMENTS) else "info"), s.replace(" 5 ou espace pour arrêter.", "")


class Fil:
    """un fichier texte qui grandit, relu par morceaux : les lignes entières arrivées depuis la dernière lecture"""

    def __init__(self, chemin):
        self.chemin, self.pos, self.reste = chemin, 0, ""

    def lignes(self):
        try:
            with open(self.chemin, "rb") as f:
                f.seek(self.pos)
                bloc = f.read()
                self.pos = f.tell()
        except OSError:
            return []
        morceaux = (self.reste + bloc.decode("utf-8", "replace")).split("\n")
        self.reste = morceaux.pop()                               # dernière ligne peut-être incomplète
        return morceaux


class LecteurE:
    """NOM_e.csv : les réponses à la touche e (boutons, mur, saleté, roulette avant, courants des brosses), une par seconde"""

    def __init__(self, prefixe):
        self.fil, self.cols = Fil(prefixe + "_e.csv"), None

    def lire(self):
        rangs = []
        for texte in self.fil.lignes():
            f = texte.strip().split(",")
            if self.cols is None:
                if "pc_s" in f:
                    self.cols = f
                continue
            if len(f) != len(self.cols):
                continue
            try:
                v = dict(zip(self.cols, f))
                d = {"t": float(v["pc_s"])}
                for c in E_NOMBRES:
                    if v.get(c, "") != "":
                        d[c] = int(float(v[c]))
                rangs.append(d)
            except (ValueError, KeyError):
                continue
        return rangs


class LecteurConsole:
    """NOM_console.txt : ce que le cerveau écrit sur sa console, dont le texte que le robot envoie de lui-même. Chaque
    ligne gardée devient [heure, genre, texte]. La note de l'enregistrement (son but, écrit en tête par l'outil qui
    l'a lancé) est gardée à part."""

    def __init__(self, prefixe):
        self.fil, self.note, self._entetes = Fil(prefixe + "_console.txt"), None, 0

    def lire(self):
        lignes = []
        for texte in self.fil.lignes():
            if texte.startswith("#"):
                self._entetes += 1                                # 1 : nom et adresse, puis la note s'il y en a une, puis les colonnes
                if self._entetes == 2 and not texte.startswith("# colonnes"):
                    self.note = texte[1:].strip() or None
                continue
            f = texte.split("\t", 2)
            if len(f) != 3:
                continue
            try:
                t = float(f[0])
            except ValueError:
                continue
            g = ligne_console(f[2])
            if g is not None:
                lignes.append([t, g[0], g[1]])
        return lignes


def lire_etats(chemin, pos=0):
    """NOM_etat.jsonl à partir de l'octet pos : une liste de dictionnaires (heure, tour en cours, charge, version du
    firmware, robot sur sa base ou non), et la nouvelle position dans le fichier. « base » vaut None quand le robot
    ne répond pas (endormi) : ce que le cerveau redit alors de la base est vieux."""
    etats = []
    try:
        with open(chemin, "rb") as f:
            f.seek(pos)
            bloc = f.read()
    except OSError:
        return etats, pos
    fin = bloc.rfind(b"\n")
    if fin < 0:
        return etats, pos
    for ligne in bloc[:fin].split(b"\n"):
        try:
            j = json.loads(ligne.decode("utf-8", "replace"))
            e = j["etat"]
            r = e.get("robot") or {}
            frais = bool(r.get("ok")) and (r.get("age") or 0) < 3000
            etats.append({"t": j["pc_s"], "tour": (e.get("tour") or {}).get("etat"), "q": r.get("q"), "qmax": r.get("qmax"),
                          "ver": version_firmware(e.get("ver")), "base": (bool(r["base"]) if frais and "base" in r else None),
                          "chg": r.get("chg") if frais else None, "plus": plus_etat(e, r)})
        except (ValueError, KeyError, AttributeError, TypeError):
            continue
    return etats, pos + fin + 1


def firmware_de(prefixe):
    """version du firmware notée au début de NOM_etat.jsonl, ou None"""
    try:
        with open(prefixe + "_etat.jsonl", "rb") as f:
            debut = f.read(20000)
    except OSError:
        return None
    for ligne in debut.split(b"\n")[:5]:
        try:
            v = version_firmware(json.loads(ligne.decode("utf-8", "replace"))["etat"].get("ver"))
        except (ValueError, KeyError, AttributeError, TypeError):
            continue
        if v is not None:
            return v
    return None


class Base:
    """Suit, seconde après seconde, ce que l'état du robot dit de sa base. Quand le robot est posé dessus, sa position
    est connue sans aucun tour sur place : une ancre « base ». Quand il la quitte, c'est qu'on l'en a tiré à la main
    (sur sa base alimentée il ignore les ordres de roues, journal_wifi.md § 32) : sa position n'est plus connue."""

    def __init__(self, pose):
        # sur : True ou False d'après le dernier état frais ; None : pas encore su ; « avant » : le robot était sur sa
        # base à la fin de l'enregistrement précédent, et rien de frais ne l'a encore confirmé (il dort peut-être dessus)
        self.pose, self.sur, self.t_vrai = pose, None, None

    def suivre(self, etats):
        """renvoie (ancres à poser, départs de la base : [(heure, clé, cause)]) pour ces nouveaux états"""
        ancres, departs = [], []
        if self.pose is None:
            return ancres, departs
        for e in etats:
            b = e.get("base")
            if b is None:
                continue
            if b and self.sur is not True:
                ancres.append({"cle": f"base|{e['t']:.1f}", "t": e["t"], "src": "base", "X": self.pose[0], "Y": self.pose[1], "C": self.pose[2],
                               "b": None, "info": {"nom": "base"}})
            elif self.sur and not b:
                departs.append((self.t_vrai, f"quitte|{self.t_vrai:.1f}", "base"))
            if b:
                self.t_vrai = e["t"]
            self.sur = b
        return ancres, departs


def cibles_objet(su, liste):
    return [{"u": round(c[0], 1), "v": round(c[1], 1), "etat": c[2], "case": su.gr.nom(c[0], c[1])} for c in liste]


def obstacles_objet(liste):
    return [[o[1], o[2], o[3]] for o in liste]


class Direct:
    """suit l'enregistrement le plus récent du dossier des mesures, pendant qu'il s'écrit"""
    mode = "direct"

    def __init__(self, dossier, fabrique, prefixe=None):
        self.dossier, self.fabrique, self.force = dossier, fabrique, prefixe
        self.epoque = 0
        self.suivi = self.prefixe = None
        self._t_liste = self._t_fichiers = 0.0
        self.vitesse, self.pause = 1.0, False
        self._ouvrir(prefixe or self._plus_recent())

    def _enregistrements(self):
        """Préfixes des enregistrements du dossier, du plus ancien au plus récent : d'après la date et l'heure que
        l'enregistreur met dans leur nom (l'heure de modification d'un fichier change dès qu'un outil le réécrit)."""
        L = []
        for c in glob.glob(os.path.join(glob.escape(self.dossier), "*_capteurs.csv")):
            m = RE_NOM.search(c)
            try:
                L.append((m[1] + m[2] if m else time.strftime("%Y%m%d%H%M%S", time.localtime(os.path.getmtime(c))), c[:-len("_capteurs.csv")]))
            except OSError:
                pass
        return [p for _, p in sorted(L)]

    def _plus_recent(self):
        E = self._enregistrements()
        return E[-1] if E else None

    def _ouvrir(self, prefixe):
        self.epoque += 1
        self.prefixe = prefixe
        self.suivi = self.fabrique()
        self.lect, self.pos, self.reste = LecteurCsv(), 0, ""
        self.pos_etat = 0
        self.seance = Seance(prefixe, self.suivi) if prefixe else None
        self._cles = set()
        self._report_fait = False
        self._base = Base(self.suivi.pose_base)
        self._base_attente = []                                   # ancres « base » à poser dès que le journal a une ligne
        self._departs = []                                        # départs de la base, de même
        self._lect_e = LecteurE(prefixe) if prefixe else None
        self._lect_console = LecteurConsole(prefixe) if prefixe else None
        self._note = None
        self.suivi.fixer("seance", {"mode": "direct", "nom": os.path.basename(prefixe) if prefixe else None})

    def horloge(self, maintenant):
        return maintenant

    def _lire_csv(self):
        try:
            with open(self.prefixe + "_capteurs.csv", "rb") as f:
                f.seek(self.pos)
                bloc = f.read()
                self.pos = f.tell()
        except OSError:
            return []
        morceaux = (self.reste + bloc.decode("utf-8", "replace")).split("\n")
        self.reste = morceaux.pop()                               # dernière ligne peut-être incomplète
        lignes = []
        for texte in morceaux:
            if self.lect.ix is None:
                self.lect.entete(texte)
                continue
            r = self.lect.ligne(texte)
            if r is not None:
                lignes.append(r)
        return lignes

    def _report(self):
        """Position de départ reprise de l'enregistrement précédent, si le cerveau n'a pas redémarré entre les deux :
        son repère est alors le même, et la dernière position connue plus ce qu'il a compté depuis vaut encore.
        Pas de reprise si le robot a été soulevé à la fin de l'enregistrement précédent : sa position y est inconnue.
        S'il y était sur sa base, la reprise vaut tant que rien de frais ne dit le contraire (il dort peut-être
        dessus) ; au premier état frais, la base confirme, ou bien il n'y est plus : on l'en a tiré à la main."""
        self._report_fait = True
        E = self._enregistrements()
        if self.prefixe not in E or E.index(self.prefixe) == 0:
            return
        avant = E[E.index(self.prefixe) - 1]
        try:
            su, base, _ = rejouer(avant, self.fabrique)
        except (OSError, ValueError):
            return
        if not su.R or (base.sur is True and self._base.sur is False):
            return                                                # il était sur sa base, il n'y est plus : tiré à la main entre les deux
        P, a, r = su.est[-1], su.R[-1], self.suivi.R[0]
        dt, dms = r[T_] - a[T_], r[MS_] - a[MS_]
        if P is None or dms <= 0 or abs(dms / 1000.0 - dt) > max(5.0, 0.02 * dt) or abs(r[C_] - a[C_]) > 3000:
            return
        P = su._pas(P, (a[X_], a[Y_], a[C_]), (r[X_], r[Y_], r[C_]))
        self.suivi.poser([{"cle": "report|" + os.path.basename(avant), "t": r[T_], "src": "report", "X": P[0], "Y": P[1], "C": P[2],
                           "b": (r[X_], r[Y_], r[C_]), "info": {"nom": os.path.basename(avant)}}])
        if base.sur is True and self._base.sur is None:
            self._base.sur, self._base.t_vrai = "avant", r[T_]

    def tick(self, maintenant):
        if maintenant - self._t_liste >= 1.0 and not self.force:
            self._t_liste = maintenant
            p = self._plus_recent()
            if p and p != self.prefixe:
                self._ouvrir(p)
        if not self.prefixe:
            return
        # l'état d'abord : la version du firmware dit s'il faut retirer le patinage, avant de compter le chemin
        etats, self.pos_etat = lire_etats(self.prefixe + "_etat.jsonl", self.pos_etat)
        if etats:
            self.suivi.etat = etats[-1]
            self.suivi.fixer_firmware(next((e["ver"] for e in etats if e["ver"] is not None), None))
            ancres, departs = self._base.suivre(etats)
            self._base_attente.extend(ancres)
            self._departs.extend(departs)
        lignes = self._lire_csv()
        if lignes:
            self.suivi.ajouter_lignes(lignes)
            if not self._report_fait:
                self._report()
        if self.suivi.R and (self._base_attente or self._departs):
            if self._base_attente:
                self.suivi.poser(self._base_attente)
            for t, cle, cause in self._departs:
                self.suivi.deplacer(t, cle, cause)
            self._base_attente, self._departs = [], []
        # pour la feuille « Capteurs » et le journal : les réponses à la touche e, et ce que le cerveau écrit sur sa console
        rangs = self._lect_e.lire()
        if rangs:
            self.suivi.e = rangs[-1]
        parues = self._lect_console.lire()
        if parues:
            self.suivi.sortie.extend(parues)
            self.suivi.n_sortie = len(self.suivi.sortie)
        if self._lect_console.note != self._note:
            self._note = self._lect_console.note
            self.suivi.fixer("seance", {"mode": "direct", "nom": os.path.basename(self.prefixe), "note": self._note})
        if maintenant - self._t_fichiers >= 0.4:
            self._t_fichiers = maintenant
            if self.seance.lire(self.suivi.R, self.suivi.Tt):
                F = self.seance.faits()
                cles = {a["cle"] for a in F["ancres"]}
                self.suivi.retirer(self._cles - cles)
                self._cles = cles
                self.suivi.poser(F["ancres"])
                self.suivi.fixer_evts(F["evts"])
                cibles = F["hist"][-1][1] if F["hist"] else []
                # des destinations écrites dans NOM_CIBLES.json que le programme n'a pas encore annoncées : montrées « données »
                if F["attente"] and (not F["hist"] or F["attente"][0] > F["hist"][-1][0] + 1.0) and maintenant - F["attente"][0] < 600:
                    cibles = F["attente"][1]
                self.suivi.fixer("cibles", cibles_objet(self.suivi, cibles))
                self.suivi.fixer("obstacles", obstacles_objet(F["obstacles"]))
                self.suivi.fixer("parois", [x for _, seg in F["parois"] for x in seg])


def rejouer(prefixe, fabrique):
    """Un enregistrement terminé, donné d'un coup au suivi : journal, fichiers de la navigation, base. Renvoie le suivi,
    ce que l'on sait de la base à la fin, et les faits tirés des fichiers de la navigation (None sans journal)."""
    su = fabrique()
    su.fixer_firmware(firmware_de(prefixe))
    su.ajouter_lignes(lire_csv(prefixe + "_capteurs.csv"))
    base, F = Base(su.pose_base), None
    if su.R:
        se = Seance(prefixe, su)
        se.lire(su.R, su.Tt)
        F = se.faits()
        etats, _ = lire_etats(prefixe + "_etat.jsonl")
        ancres, departs = base.suivre(etats)
        su.poser(sorted(F["ancres"] + ancres, key=lambda a: a["t"]))
        for t, cle, cause in departs:
            su.deplacer(t, cle, cause)
        su.fixer_evts(F["evts"])
    return su, base, F


class Rejeu:
    """rejoue un enregistrement terminé, avec les mêmes calculs que le direct : les lignes du journal et les fichiers de
    la navigation sont donnés au suivi à l'heure où ils ont été écrits"""
    mode = "rejeu"

    def __init__(self, prefixe, fabrique, vitesse=8.0, debut=None, pause=False):
        self.prefixe, self.fabrique = prefixe, fabrique
        self.lignes = lire_csv(prefixe + "_capteurs.csv")
        if not self.lignes:
            raise SystemExit("aucune ligne lisible dans " + prefixe + "_capteurs.csv")
        self.Tl = [r[T_] for r in self.lignes]
        su = fabrique()
        se = Seance(prefixe, su)
        se.lire(self.lignes, self.Tl)
        F = se.faits()
        self.hist, self.obstacles, self.parois = F["hist"], F["obstacles"], F["parois"]
        self.evts = sorted(F["evts"].items(), key=lambda kv: kv[1]["t"])
        self.etats, _ = lire_etats(prefixe + "_etat.jsonl")
        self._Te = [e["t"] for e in self.etats]
        self.firmware = firmware_de(prefixe)
        ancres_base, self.departs = Base(su.pose_base).suivre(self.etats)
        self.ancres = sorted(F["ancres"] + ancres_base, key=lambda a: a["t"])
        self.T0, self.T1 = self.Tl[0], self.Tl[-1]
        self.vitesse, self.pause = vitesse, pause
        self.e_rangs = LecteurE(prefixe).lire()                   # réponses à la touche e, et lignes de la console du cerveau
        self._Tr = [d["t"] for d in self.e_rangs]
        lecteur = LecteurConsole(prefixe)
        self.console, self.note = lecteur.lire(), lecteur.note
        self._Tc = [s[0] for s in self.console]
        self.epoque = 0
        self._zero()
        if debut is not None:
            self.aller(debut)

    def _zero(self):
        self.epoque += 1
        self.suivi = self.fabrique()
        self.suivi.fixer_firmware(self.firmware)
        self.suivi.fixer("seance", {"mode": "rejeu", "nom": os.path.basename(self.prefixe), "note": self.note})
        self.suivi.sortie = self.console                          # la même liste : seul le nombre de lignes parues avance
        self.iL = self.iA = self.iE = self.iD = 0
        self.T, self._mur = self.T0, None
        self._evts = {}

    def horloge(self, maintenant):
        return self.T

    def aller(self, T):
        T = max(self.T0, min(self.T1, T))
        if T < self.T:
            self._zero()
        self.T = T
        self._nourrir()

    def tick(self, maintenant):
        if self._mur is not None and not self.pause:
            self.T = min(self.T1, self.T + (maintenant - self._mur) * self.vitesse)
        self._mur = maintenant
        self._nourrir()

    def _nourrir(self):
        T, su = self.T, self.suivi
        j = bisect.bisect_right(self.Tl, T)
        if j > self.iL:
            su.ajouter_lignes(self.lignes[self.iL:j])
            self.iL = j
        k = self.iA
        while k < len(self.ancres) and self.ancres[k]["t"] + 0.3 <= T:
            k += 1
        if k > self.iA:
            su.poser(self.ancres[self.iA:k])
            self.iA = k
        while self.iD < len(self.departs) and self.departs[self.iD][0] + 1.0 <= T:      # l'état n'arrive qu'une fois par seconde
            su.deplacer(*self.departs[self.iD])
            self.iD += 1
        k = self.iE
        while k < len(self.evts) and self.evts[k][1]["t"] <= T:
            self._evts[self.evts[k][0]] = self.evts[k][1]
            k += 1
        if k > self.iE:
            self.iE = k
            su.fixer_evts(self._evts)
        cibles = []
        for t, c in self.hist:
            if t <= T:
                cibles = c
        su.fixer("cibles", cibles_objet(su, cibles))
        su.fixer("obstacles", obstacles_objet([o for o in self.obstacles if o[0] <= T]))
        su.fixer("parois", [x for t, seg in self.parois if t + 0.3 <= T for x in seg])
        k = bisect.bisect_right(self._Te, T) - 1
        if k >= 0:
            su.etat = self.etats[k]
        k = bisect.bisect_right(self._Tr, T) - 1
        su.e = self.e_rangs[k] if k >= 0 else None
        su.n_sortie = bisect.bisect_right(self._Tc, T)


MOIS = ("janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc.")
VERSION_MEMOIRE = 7                     # à augmenter quand le calcul des positions change : les anciens résultats sont refaits


def code_base(code):
    """code infrarouge de la base -> 0 : faisceau rouge, 1 : vert, 2 : les deux, 3 : champ proche seul ; None sinon"""
    n = int(code) - 160
    if not 0 < n < 16:
        return None
    rouge, vert = bool(n & 8), bool(n & 4)
    return 2 if rouge and vert else 0 if rouge else 1 if vert else 3


class Memoire:
    """Ce que les enregistrements passés ont appris, placé sur le plan, pour que la carte le garde d'un essai à l'autre :
    le sol déjà parcouru, les parois vues par le capteur de distance pendant les tours sur place, là où le signal de
    la base a été reçu, ce que le robot a touché ou frôlé, là où une roue a patiné. Seuls comptent les trajets situés
    par un tour sur place jugé par le filtre ou par la base (avant le 2026-11-13 le calage dérivait de plusieurs dizaines de centimètres). Les résultats
    sont gardés dans un fichier hors dépôt, à côté du plan : un enregistrement terminé n'est calculé qu'une fois."""

    def __init__(self, dossier, fabrique, fichier, oublis=None):
        """oublis : fichier JSON, tenu à la main à côté du plan, des moments d'enregistrements passés à ne pas garder :
        [{"enregistrement": NOM, "de": "HH:MM:SS", "a": "HH:MM:SS", "raison": "…"}]. Il sert quand on a compris après
        coup que le calage de l'époque était faux (2026-11-13, 14 h 51 : une roue avait patiné, journal_wifi.md § 43)."""
        self.dossier, self.fabrique, self.fichier, self.f_oublis = dossier, fabrique, fichier, oublis

    def _oublis(self):
        try:
            with open(self.f_oublis, encoding="utf-8") as f:
                return [[str(o["enregistrement"]), str(o["de"]), str(o["a"])] for o in json.load(f)]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def _un(self, prefixe, oublis=()):
        su, _, F = rejouer(prefixe, self.fabrique)
        if not su.R:
            return {"contacts": [], "proches": [], "traces": [], "parois": [], "ir": [], "patine": []}
        B = su.bornes
        fenetres = [(t_heure(de, su.Tt[0]), t_heure(a, su.Tt[0])) for nom, de, a in oublis if nom == os.path.basename(prefixe)]

        def sur_troncon(s):
            """le tronçon s (entre les bornes s − 1 et s) touche-t-il une ancre mesurée par le filtre ou par la base ?"""
            return any(0 <= k < len(B) and B[k]["type"] == "ancre" and B[k]["src"] in ("filtre", "base") for k in (s - 1, s))

        def garde(i):
            """la ligne i est-elle bien située, et hors des moments à oublier ?"""
            if su.pose_ligne(i) is None or any(t0 <= su.Tt[i] <= t1 for t0, t1 in fenetres):
                return False
            k = 0
            while k < len(B) and B[k]["i"] <= i:
                k += 1
            return sur_troncon(k)

        def date(i):
            d = datetime.datetime.fromtimestamp(su.Tt[i])
            return f"{d.day} {MOIS[d.month - 1]}, {d.hour} h {d.minute:02d}"

        contacts, proches, traces, parois, ir, patine = [], [], [], [], set(), []
        for t, seg in F["parois"]:                                # les parois vues pendant les tours sur place bien situés
            i = bisect.bisect_right(su.Tt, t) - 1
            if i >= 0 and garde(i):
                parois.extend(round(x) for x in seg)
        for i, cote in su.contacts:
            uv = su.point_contact(i, cote)
            if uv is not None and garde(i):
                contacts.append([uv[0], uv[1], cote, date(i)])
        for i, q, val in su.proches:
            if garde(i):
                P = su.pose_ligne(i)
                ang = math.radians(P[2] + ANGLES_OPTIQUES[q])
                proches.append(list(su.px(P[0] + (RAYON + 40.0) * math.cos(ang), P[1] + (RAYON + 40.0) * math.sin(ang))))
        for s in range(len(B) + 1):                               # le tracé, tronçon par tronçon : le sol parcouru
            if not sur_troncon(s):
                continue
            i0, i1 = (B[s - 1]["i"] if s > 0 else 0), (B[s]["i"] if s < len(B) else len(su.R))
            pts, ref, fin = [], None, None

            def ranger():
                if fin is not None and pts[-2:] != [round(fin[0]), round(fin[1])]:
                    pts.extend([round(fin[0]), round(fin[1])])
                if len(pts) >= 4:
                    traces.append(list(pts))

            for i in su.ech[bisect.bisect_left(su.ech, i0):bisect.bisect_left(su.ech, i1)]:
                P = su.pose_ligne(i)
                if P is None or any(t0 <= su.Tt[i] <= t1 for t0, t1 in fenetres):
                    ranger()                                      # le tracé s'interrompt là où la position n'est pas à garder
                    pts, ref, fin = [], None, None
                    continue
                fin = su.px(P[0], P[1])
                if ref is None or abs(fin[0] - ref[0]) + abs(fin[1] - ref[1]) >= 4.0:        # un point tous les 7 cm environ
                    pts.extend([round(fin[0]), round(fin[1])])
                    ref = fin
            ranger()
        for i, code in su.ir:
            c = code_base(code)
            if c is not None and garde(i):
                P = su.pose_ligne(i)
                a = math.radians(P[2])
                u, v = su.px(P[0] + RAYON_IR * math.cos(a), P[1] + RAYON_IR * math.sin(a))
                ir.add((round(u / 2.0), round(v / 2.0), c))
        for ep in su.patine:
            if abs(ep[2]) >= 60.0 and garde(ep[0]):
                P = su.pose_ligne(ep[0])
                u, v = su.px(P[0], P[1])
                patine.append([u, v, "droite" if ep[2] > 0 else "gauche", round(abs(ep[2])), round(ep[3]), date(ep[0])])
        return {"contacts": contacts, "proches": proches, "traces": traces, "parois": parois,
                "ir": [x for c in sorted(ir) for x in c], "patine": patine}

    def calculer(self, avant):
        """l'objet « anciens » : ce qu'ont appris les enregistrements plus anciens que le préfixe donné"""
        base, oublis = list(self.fabrique().pose_base or []), self._oublis()
        try:
            with open(self.fichier, encoding="utf-8") as f:
                cache = json.load(f)
            if cache.get("version") != VERSION_MEMOIRE or cache.get("base") != base or cache.get("oublis") != oublis:
                cache = {}
        except (OSError, ValueError):
            cache = {}
        garde = cache.get("enregistrements", {})
        L = []
        for c in glob.glob(os.path.join(glob.escape(self.dossier), "*_capteurs.csv")):
            m = RE_NOM.search(c)
            if m:
                L.append((m[1] + m[2], c[:-len("_capteurs.csv")]))
        L.sort()
        cle_avant = next((k for k, p in L if p == avant), None)
        A = {"contacts": [], "proches": [], "traces": [], "parois": [], "patine": []}
        ir, change = set(), False
        for k, p in L:
            if cle_avant is not None and k >= cle_avant:
                break
            nom = os.path.basename(p)
            try:
                sig = [os.path.getsize(p + "_capteurs.csv")] + sorted([os.path.basename(f), os.path.getsize(f)] for f in glob.glob(glob.escape(p) + "*")
                                                                     if f.endswith((".json", ".jsonl", "_explorer3.txt")) or "balise" in f or "passage" in f)
                if garde.get(nom, {}).get("sig") != sig:
                    garde[nom] = dict(self._un(p, oublis), sig=sig)
                    change = True
            except (OSError, ValueError, KeyError, IndexError, TypeError):
                continue
            for c in A:
                A[c].extend(garde[nom][c])
            r = garde[nom]["ir"]
            ir.update(zip(r[0::3], r[1::3], r[2::3]))
        if change:
            try:
                os.makedirs(os.path.dirname(self.fichier), exist_ok=True)
                with open(self.fichier + ".tmp", "w", encoding="utf-8") as f:
                    json.dump({"version": VERSION_MEMOIRE, "base": base, "oublis": oublis, "enregistrements": garde}, f, ensure_ascii=False)
                os.replace(self.fichier + ".tmp", self.fichier)
            except OSError:
                pass
        # le signal de la base est rangé sur une grille de 2 pixels (4 cm) : une case où il a été reçu cent fois ne compte qu'une fois
        A["ir"] = [x for c in sorted(ir) for x in c]
        return A


class Connaissances:
    """Ce que la navigation a appris de l'appartement et garde à côté du plan, hors dépôt : les obstacles absents du plan
    (obstacles.json, donné à explorer3.py par --plan-ferme), les repères (reperes_tours.json, fabriqué par reperes.py)
    et les notes de sa dernière carte quadrillée (le fichier reperes_AAAAMMJJ*.json le plus récent). Relus quand ils
    changent ; un fichier absent ou illisible un instant ne vide pas la carte."""

    def __init__(self, dossier, su, obstacles="obstacles.json", reperes="reperes_tours.json"):
        self.dossier, self.su = dossier, su
        self.f_obstacles, self.f_reperes = os.path.join(dossier, obstacles), os.path.join(dossier, reperes)
        self._sig = {}
        self.obj = {"connus": [], "reperes": {"r": round(350.0 * su.s, 1), "p": []}, "notes": {"jour": "", "p": []}}

    def _change(self, cle, chemin):
        try:
            st = os.stat(chemin)
            sig = (chemin, st.st_mtime, st.st_size)
        except OSError:
            sig = (chemin, None, None)
        if self._sig.get(cle) == sig:
            return False
        self._sig[cle] = sig
        return True

    def objets(self):
        su = self.su
        if self._change("connus", self.f_obstacles):
            try:
                with open(self.f_obstacles, encoding="utf-8") as f:
                    self.obj["connus"] = [{"u": float(o["u"]), "v": float(o["v"]), "r": round(float(o.get("rayon_mm", 250.0)) * su.s, 1),
                                           "x": str(o.get("note") or ""), "case": su.gr.nom(float(o["u"]), float(o["v"]))} for o in json.load(f)]
            except (OSError, ValueError, KeyError, TypeError):
                pass
        if self._change("reperes", self.f_reperes):
            try:
                with open(self.f_reperes, encoding="utf-8") as f:
                    pts = sorted({su.px(float(r["x"]), float(r["y"])) for r in json.load(f)["reperes"]})
                self.obj["reperes"] = {"r": round(350.0 * su.s, 1), "p": [list(p) for p in pts]}
            except (OSError, ValueError, KeyError, TypeError):
                pass
        notes = None                                              # le fichier de notes le plus récent
        try:
            for nom in os.listdir(self.dossier):
                m = RE_NOTES.match(nom)
                if m:
                    c = os.path.join(self.dossier, nom)
                    cand = (os.path.getmtime(c), c, m)
                    if notes is None or cand[:2] > notes[:2]:
                        notes = cand
        except OSError:
            notes = None
        if notes is not None and self._change("notes", notes[1]):
            try:
                with open(notes[1], encoding="utf-8") as f:
                    P = [{"u": float(q["u"]), "v": float(q["v"]), "x": " ".join(str(q.get("texte") or "").split()),
                          "case": su.gr.nom(float(q["u"]), float(q["v"]))} for q in json.load(f)]
                m = notes[2]
                self.obj["notes"] = {"jour": f"{int(m[3])} {MOIS[int(m[2]) - 1]}", "p": P}
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                pass
        return self.obj
