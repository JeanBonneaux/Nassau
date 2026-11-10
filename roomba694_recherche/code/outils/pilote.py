# pilote.py — petits déplacements commandés depuis le PC, un saut à la fois, avec contrôles avant et pendant.
#
# S'utilise PENDANT qu'enregistreur.py tourne (il tient la console TCP et écrit le journal CSV) : le pilote envoie les
# touches par HTTP (/api/cmd) et lit les capteurs dans le fichier NOM_capteurs.csv que l'enregistreur remplit.
#
# Un « saut » = une seule touche de roues (8 avance, 2 recule, 4 gauche, 6 droite), puis la touche d'arrêt (5) au bout
# de la durée voulue. Le firmware arrête de toute façon les roues 1,5 s après le dernier ordre, et, depuis la v6,
# dès qu'une lecture montre le pare-chocs enfoncé ou une roue levée. Le pilote ajoute ses propres contrôles :
#   avant le saut : robot qui répond, mode Safe, pare-chocs libre, roues au sol, sol clair sous les quatre capteurs de
#                   vide, rien de proche sur les capteurs optiques, et pour une avance rien devant à moins de la marge ;
#   pendant       : arrêt immédiat (touche 5) si le pare-chocs, une roue levée, la sortie du mode Safe ou un capteur
#                   optique très fort apparaît dans une ligne du journal.
# Un recul se fait à l'aveugle (aucun capteur ne regarde derrière) : ne reculer que sur le terrain qu'on vient de parcourir.
#
# Ce module n'envoie rien tout seul : c'est le script qui l'utilise qui décide des sauts.
import json
import os
import time
import urllib.request

MM_PAR_PAS = 3.141592653589793 * 72.0 / 508.8      # 0,4446 mm par pas de compteur
ENTRAXE_MM = 235.0
LB = ["lb_g", "lb_avg", "lb_cg", "lb_cd", "lb_avd", "lb_d"]
VIDE = ["vide_g", "vide_avg", "vide_avd", "vide_d"]


def w16(d):
    return (int(d) + 32768) % 65536 - 32768


class Pilote:
    def __init__(self, adresse, prefixe):
        self.adr = adresse
        self.csv = prefixe + "_capteurs.csv"
        self.pos = 0
        self.cols = None
        self.reste = ""
        self.lignes = []           # une ligne du journal = un dictionnaire de nombres

    # ------------------------------------------------------------ liaison
    def get(self, chemin, timeout=3.0):
        with urllib.request.urlopen(f"http://{self.adr}{chemin}", timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")

    def etat(self):
        return json.loads(self.get("/api/state"))

    def touche(self, c):
        return self.get(f"/api/cmd?c={c}")

    def vitesse(self, v):
        return self.get(f"/api/speed?v={int(v)}")

    # ------------------------------------------------------------ lecture du journal tenu par l'enregistreur
    def lire(self):
        if not os.path.exists(self.csv):
            return 0
        with open(self.csv, encoding="utf-8") as f:
            f.seek(self.pos)
            bloc = f.read()
            self.pos = f.tell()
        bloc = self.reste + bloc
        lignes = bloc.split("\n")
        self.reste = lignes.pop()          # dernière ligne peut-être incomplète
        n = 0
        for l in lignes:
            if not l:
                continue
            if self.cols is None:
                self.cols = l.split(",")
                continue
            v = l.split(",")
            if len(v) != len(self.cols):
                continue
            try:
                self.lignes.append({c: float(x) for c, x in zip(self.cols, v)})
                n += 1
            except ValueError:
                pass
        return n

    def frais(self, age_max=0.7, attente=3.0):
        """Attend une ligne du journal vieille de moins de age_max secondes ; renvoie cette ligne, ou None."""
        fin = time.time() + attente
        while time.time() < fin:
            self.lire()
            if self.lignes and time.time() - self.lignes[-1]["pc_s"] < age_max:
                return self.lignes[-1]
            time.sleep(0.05)
        return None

    def immobile(self, attente=3.0, lignes=7):     # 7 lignes : 0,35 s à 20 lignes par seconde (firmware v7), 1,4 s à 5
        """Attend que les compteurs des roues ne bougent plus sur `lignes` lignes de suite."""
        fin = time.time() + attente
        while time.time() < fin:
            self.lire()
            q = self.lignes[-(lignes + 1):]
            if len(q) > lignes and all(q[k]["enc_g"] == q[0]["enc_g"] and q[k]["enc_d"] == q[0]["enc_d"] for k in range(len(q))):
                return True
            time.sleep(0.05)
        return False

    # ------------------------------------------------------------ contrôles
    @staticmethod
    def alarme(l, lb_max=400, recul=False):
        """Raison d'arrêter tout de suite d'après une ligne du journal, ou None.
        En recul, le pare-chocs enfoncé n'est pas une alarme : reculer est justement la façon de se dégager."""
        if (l["pc_g"] or l["pc_d"]) and not recul:
            return "pare-chocs " + ("gauche" if l["pc_g"] else "") + (" droit" if l["pc_d"] else "")
        if l["roue_g"] or l["roue_d"]:
            return "roue levée"
        if l["mode"] != 3:
            return f"sorti du mode Safe (mode lu {int(l['mode'])})"
        if max(l[c] for c in LB) > lb_max:
            return f"capteur optique à {max(l[c] for c in LB):.0f}"
        return None

    def controle(self, l, avance, marge_mm=600, lb_repos=150, vide_min=1500, recul=False):
        """Raison de ne pas partir, ou None si tout va bien."""
        a = self.alarme(l, lb_max=lb_repos, recul=recul)
        if a:
            return a
        if min(l[c] for c in VIDE) < vide_min and not recul:      # un recul refait le chemin qu'on vient de parcourir : permis
            return f"sol sombre ou vide sous un capteur ({min(l[c] for c in VIDE):.0f})"
        if avance:
            if l["us_mm"] < 0:
                return "capteur de distance éteint ou sans mesure"
            if 0 < l["us_mm"] < marge_mm:
                return f"obstacle à {l['us_mm']:.0f} mm devant (marge {marge_mm} mm)"
        return None

    # ------------------------------------------------------------ un saut
    def saut(self, touche, duree, marge_mm=600, lb_repos=150, lb_max=400):
        """Envoie une touche de roues, surveille, arrête au bout de `duree` secondes (1,4 s au plus).
        Renvoie un dictionnaire : refus éventuel, alarme éventuelle, déplacement et rotation mesurés."""
        duree = min(duree, 1.4)
        l0 = self.frais()
        if l0 is None:
            return {"refus": "aucune ligne récente du journal (robot muet ?)"}
        recul = (touche == "2")
        refus = self.controle(l0, avance=(touche == "8"), marge_mm=marge_mm, lb_repos=lb_repos, recul=recul)
        if refus:
            return {"refus": refus}
        i0 = len(self.lignes) - 1
        t_ordre = time.time()
        self.touche(touche)
        alarme = None
        while time.time() - t_ordre < duree:
            n = self.lire()
            for l in self.lignes[len(self.lignes) - n:] if n else []:
                alarme = self.alarme(l, lb_max=lb_max, recul=recul)
                if alarme:
                    break
            if alarme:
                break
            time.sleep(0.03)
        t_stop = time.time()
        self.touche("5")
        self.immobile()
        self.lire()
        seg = self.lignes[i0:]
        dl = sum(w16(b["enc_g"] - a["enc_g"]) for a, b in zip(seg, seg[1:]))
        dr = sum(w16(b["enc_d"] - a["enc_d"]) for a, b in zip(seg, seg[1:]))
        mouv = [k for k in range(1, len(seg)) if seg[k]["enc_g"] != seg[k - 1]["enc_g"] or seg[k]["enc_d"] != seg[k - 1]["enc_d"]]
        res = {
            "touche": touche, "duree_ordre": round(t_stop - t_ordre, 2), "alarme": alarme,
            "g_mm": round(dl * MM_PAR_PAS, 1), "d_mm": round(dr * MM_PAR_PAS, 1),
            "avance_mm": round((dl + dr) / 2 * MM_PAR_PAS, 1),
            "rot_roues": round((dr - dl) * MM_PAR_PAS / ENTRAXE_MM * 57.29578, 2),
            "rot_gyro": round(seg[-1]["cap_pos"] - seg[0]["cap_pos"], 2),
            "us_avant": seg[0]["us_mm"], "us_apres": seg[-1]["us_mm"],
            "lb_max": max(max(l[c] for c in LB) for l in seg), "vide_min": min(min(l[c] for c in VIDE) for l in seg),
            "ma_min": min(l["ma"] for l in seg), "lignes": len(seg),
            "t0": seg[0]["pc_s"], "t1": seg[-1]["pc_s"],
        }
        if len(mouv) >= 4:     # vitesse de chaque roue en régime établi : on écarte la première et la dernière ligne en mouvement
            a, b = seg[mouv[1]], seg[mouv[-2]]
            dt = (b["ms"] - a["ms"]) / 1000.0
            if dt > 0.25:
                res["v_g"] = round(sum(w16(seg[k]["enc_g"] - seg[k - 1]["enc_g"]) for k in range(mouv[1] + 1, mouv[-2] + 1)) * MM_PAR_PAS / dt, 1)
                res["v_d"] = round(sum(w16(seg[k]["enc_d"] - seg[k - 1]["enc_d"]) for k in range(mouv[1] + 1, mouv[-2] + 1)) * MM_PAR_PAS / dt, 1)
        return res
