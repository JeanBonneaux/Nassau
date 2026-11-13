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
#   NOM_etat.jsonl              /api/state relu par l'enregistreur : tour sur place en cours, charge de la batterie.
# Le champ « sta » de /api/state (nom du réseau Wi-Fi de la maison) n'est jamais lu ici.
import bisect
import datetime
import glob
import json
import os
import re
import time

from suivi import C_, K_GYRO, MS_, T_, X_, Y_, LecteurCsv, Suivi

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


def faits_stations(J, R, Tt, s, H):
    """Les tours sur place d'un passage d'explorer3.py guidé par le plan : une ancre à la fin de chaque tour (la position
    que le filtre lui a donnée), et pour le premier une ancre au départ (la position donnée au programme)."""
    ancres, obstacles = [], []
    if J.get("mode") != "exploration3" or "plan" not in J or not Tt:
        return ancres, obstacles                                  # passage sans le plan : ses positions ne sont pas dans son repère
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
            ancres.append({"cle": "st|" + cle, "t": t_fin, "src": "filtre" if info.get("filtre") else "plan",
                           "X": pose[0], "Y": pose[1], "C": pose[2] + echelle * (ap["cap_pos"] - av["cap_pos"]),
                           "b": (ap["x_mm"], ap["y_mm"], ap["cap_pos"]),
                           "info": {"nom": str(st.get("nom")), "genre": st.get("genre"), "note": info.get("note"), "etal": info.get("etalement_mm"),
                                    "n": st.get("n"), "tapis": bool(st.get("tapis"))}})
    for c in J.get("contacts", []):
        if c[2] != "contact" and t_fin is not None:               # les contacts du pare-chocs sont déjà vus dans le journal
            obstacles.append((t_fin, round(c[0] * s, 1), round(H - c[1] * s, 1), c[2]))
    return ancres, obstacles


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
                     else "passage" if (nom.endswith(".txt") and "passage" in nom) else None)
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
                    F["ancres"], F["obstacles"] = faits_stations(json.loads(texte), R, Tt, self.su.s, self.su.H)
                    F["tronc"] = chemin[:-len("_stations.json")]
                elif genre == "essai":
                    F["ancres"] = faits_essai_tours(json.loads(texte), R, Tt, self.su.s, self.su.H, st.st_mtime)
                elif genre == "explorer3":
                    # Heure de lancement du passage : l'heure d'écriture du fichier moins les minutes de sa dernière ligne
                    # (à 3 s près : les minutes n'ont qu'une décimale). L'heure de création du fichier ne convient pas :
                    # Windows redonne celle de l'ancien fichier à un fichier recréé sous le même nom dans les 15 s.
                    if chemin not in self.t0:
                        minutes = [float(m[1]) for m in map(RE_MIN.match, texte.splitlines()) if m]
                        self.t0[chemin] = st.st_mtime - (minutes[-1] * 60.0 if minutes else 0.0)
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
        ancres, evts, hist, obstacles, attente = {}, {}, [], {}, None
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
            if F.get("attente"):
                attente = F["attente"]
        hist.sort(key=lambda h: h[0])
        return {"ancres": sorted(ancres.values(), key=lambda a: a["t"]), "evts": evts, "hist": hist,
                "obstacles": sorted(obstacles.values()), "attente": attente}


def lire_etats(chemin, pos=0):
    """NOM_etat.jsonl à partir de l'octet pos : [(heure, tour en cours, charge, charge maximale)], nouvelle position"""
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
            etats.append({"t": j["pc_s"], "tour": e.get("tour", {}).get("etat"), "q": e.get("robot", {}).get("q"), "qmax": e.get("robot", {}).get("qmax")})
        except (ValueError, KeyError, AttributeError):
            continue
    return etats, pos + fin + 1


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
        son repère est alors le même, et la dernière position connue plus ce qu'il a compté depuis vaut encore."""
        self._report_fait = True
        E = self._enregistrements()
        if self.prefixe not in E or E.index(self.prefixe) == 0:
            return
        avant = E[E.index(self.prefixe) - 1]
        try:
            lignes = lire_csv(avant + "_capteurs.csv")
            if not lignes:
                return
            su = self.fabrique()
            su.ajouter_lignes(lignes)
            se = Seance(avant, su)
            se.lire(su.R, su.Tt)
            su.poser(se.faits()["ancres"])
        except (OSError, ValueError):
            return
        P, a, r = su.est[-1], su.R[-1], self.suivi.R[0]
        dt, dms = r[T_] - a[T_], r[MS_] - a[MS_]
        if P is None or dms <= 0 or abs(dms / 1000.0 - dt) > max(5.0, 0.02 * dt) or abs(r[C_] - a[C_]) > 3000:
            return
        P = su._pas(P, (a[X_], a[Y_], a[C_]), (r[X_], r[Y_], r[C_]))
        self.suivi.poser([{"cle": "report|" + os.path.basename(avant), "t": r[T_], "src": "report", "X": P[0], "Y": P[1], "C": P[2],
                           "b": (r[X_], r[Y_], r[C_]), "info": {"nom": os.path.basename(avant)}}])

    def tick(self, maintenant):
        if maintenant - self._t_liste >= 1.0 and not self.force:
            self._t_liste = maintenant
            p = self._plus_recent()
            if p and p != self.prefixe:
                self._ouvrir(p)
        if not self.prefixe:
            return
        lignes = self._lire_csv()
        if lignes:
            self.suivi.ajouter_lignes(lignes)
            if not self._report_fait:
                self._report()
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
            etats, self.pos_etat = lire_etats(self.prefixe + "_etat.jsonl", self.pos_etat)
            if etats:
                self.suivi.etat = etats[-1]


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
        self.ancres, self.hist, self.obstacles = F["ancres"], F["hist"], F["obstacles"]
        self.evts = sorted(F["evts"].items(), key=lambda kv: kv[1]["t"])
        self.etats, _ = lire_etats(prefixe + "_etat.jsonl")
        self.T0, self.T1 = self.Tl[0], self.Tl[-1]
        self.vitesse, self.pause = vitesse, pause
        self.epoque = 0
        self._zero()
        if debut is not None:
            self.aller(debut)

    def _zero(self):
        self.epoque += 1
        self.suivi = self.fabrique()
        self.suivi.fixer("seance", {"mode": "rejeu", "nom": os.path.basename(self.prefixe)})
        self.iL = self.iA = self.iE = 0
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
        k = bisect.bisect_right([e["t"] for e in self.etats], T) - 1 if self.etats else -1
        if k >= 0:
            su.etat = self.etats[k]
