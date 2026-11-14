# essai_direct.py — vérifie le suivi « en direct » sans le robot.
#
# Réécrit un ou plusieurs enregistrements dans un dossier temporaire au rythme où ils ont été écrits : le journal ligne
# après ligne, le fichier des tours après chaque tour sur place, la sortie d'explorer3.py ligne après ligne, puis le
# renommage que fait relance.py à la fin de chaque passage. La source « Direct » (celle du serveur) suit ce dossier
# avec une horloge simulée. À la fin, ce qu'elle a retenu est comparé au rejeu des fichiers d'origine.
#
#   python essai_direct.py NOM [NOM2 ...]        (noms d'enregistrements de mesures/, du plus ancien au plus récent)
#   ex. : python essai_direct.py exploration9_20261113_124811 exploration10_20261113_132251
# Rien n'est écrit dans mesures/, rien n'est demandé au robot.
import glob
import json
import os
import shutil
import sys
import tempfile
import time

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import sources  # noqa: E402
import suivi as suivi_mod  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
MESURES = os.path.normpath(os.path.join(ICI, "..", "..", "mesures"))
PAS = 0.2                                                         # secondes simulées entre deux lectures de la source


def fabrique():
    su = suivi_mod.Suivi()
    su.pose_base = (405.0 / 0.053, (434 - 33.0) / 0.053, 90.0)       # le robot posé sur sa base : pixel (405, 33), nez vers le haut
    return su


def preparer(nom, tmp):
    """liste datée de ce qui s'écrit pendant l'enregistrement : (heure, action)"""
    src, dst = os.path.join(MESURES, nom), os.path.join(tmp, nom)
    lignes = sources.lire_csv(src + "_capteurs.csv")
    Tl = [r[suivi_mod.T_] for r in lignes]
    A = []
    with open(src + "_capteurs.csv", encoding="utf-8") as f:
        entete = f.readline()
        brut = [l for l in f if l.strip()]
    temps = []
    for l in brut:
        try:
            temps.append(float(l.split(",", 1)[0]))
        except ValueError:
            temps.append(temps[-1] if temps else Tl[0])

    def ecrire(chemin, texte, t, mode="w"):
        with open(chemin, mode, encoding="utf-8", newline="\n") as f:
            f.write(texte)
        os.utime(chemin, (t, t))

    A.append((temps[0] - 0.01, lambda t: ecrire(dst + "_capteurs.csv", entete, t)))
    passages = sorted(glob.glob(glob.escape(src) + "_*_stations.json"), key=os.path.getmtime)
    if os.path.exists(src + "_stations.json"):                    # dernier passage, resté sans lettre : la séance a été coupée avant relance.py
        passages.append(src + "_stations.json")
    for q, chemin in enumerate(passages):
        tronc = chemin[:-len("_stations.json")]
        with open(chemin, encoding="utf-8") as f:
            J = json.load(f)
        t_fin_passage = os.path.getmtime(chemin)
        ancres, _, _ = sources.faits_stations(J, lignes, Tl, 0.053, 434)
        fins = [a["t"] for a in ancres if a["cle"].startswith("st|")]
        for k, t_st in enumerate(fins):                           # après chaque tour : le fichier des tours, tel qu'il était alors
            Jk = dict(J, stations=J["stations"][:k + 1], plan=J.get("plan", [])[:k + 1], contacts=[], fin=None,
                      sauts=[s for s in J["sauts"] if s.get("t1", 0) <= t_st + 1.0])
            A.append((min(t_st + 1.0, t_fin_passage - 0.5), lambda t, Jk=Jk: ecrire(dst + "_stations.json", json.dumps(Jk, ensure_ascii=False), t)))
        A.append((t_fin_passage, lambda t, J=J: ecrire(dst + "_stations.json", json.dumps(J, ensure_ascii=False), t)))
        txt = tronc + "_explorer3.txt"
        t_fin_txt = t_fin_passage
        if os.path.exists(txt):
            with open(txt, encoding="utf-8") as f:
                L = f.read().splitlines()
            t_fin_txt = os.path.getmtime(txt)
            minutes = [float(m[1]) for m in map(sources.RE_MIN.match, L) if m]
            t0 = t_fin_txt - (minutes[-1] * 60.0 if minutes else 0.0)
            t_prec = t0
            for n, l in enumerate(L):
                m = sources.RE_MIN.match(l)
                t_l = max(t_prec + 0.001, t0 + float(m[1]) * 60.0) if m else t_prec + 0.001
                t_prec = t_l
                A.append((t_l, lambda t, l=l, n=n: ecrire(dst + "_explorer3.txt", l + "\n", t, "w" if n == 0 else "a")))
        # relance.py range le passage sous sa lettre, une vingtaine de secondes plus tard (ou juste avant le passage suivant)
        t_suivant = min([a[0] for a in A if a[0] > max(t_fin_passage, t_fin_txt)] + [max(t_fin_passage, t_fin_txt) + 20.0])
        lettre = os.path.basename(tronc)[len(nom) + 1:]

        def ranger(t, lettre=lettre):
            for suf in ("_stations.json", "_explorer3.txt"):
                if os.path.exists(dst + suf):
                    os.replace(dst + suf, f"{dst}_{lettre}{suf}")
        if lettre:
            A.append((max(t_fin_passage, t_fin_txt) + 20.0, ranger))
    # fichiers écrits d'un coup : essais de tours, destinations, tours faits à la main, mesures par les faisceaux de la base
    autres = [src + suf for suf in ("_essai_tours.json", "_CIBLES.json")] + glob.glob(glob.escape(src) + "_tour_*.json") + glob.glob(glob.escape(src) + "_*balise*.txt")
    for chemin in autres:
        if os.path.exists(chemin):
            def copier(t, suf=chemin[len(src):], chemin=chemin):
                shutil.copyfile(chemin, dst + suf)
                os.utime(dst + suf, (os.path.getmtime(chemin),) * 2)
            A.append((os.path.getmtime(chemin), copier))
    if os.path.exists(src + "_etat.jsonl"):
        with open(src + "_etat.jsonl", encoding="utf-8") as f:
            for l in f:
                try:
                    t_l = json.loads(l)["pc_s"]
                except (ValueError, KeyError):
                    continue
                A.append((t_l, lambda t, l=l: ecrire(dst + "_etat.jsonl", l, t, "a")))
    A.sort(key=lambda x: x[0])
    return {"nom": nom, "dst": dst, "brut": brut, "temps": temps, "actions": A, "T0": temps[0], "T1": temps[-1]}


def comparer(nom, su):
    """ce que le direct a retenu, comparé au rejeu des fichiers d'origine"""
    rj = sources.Rejeu(os.path.join(MESURES, nom), fabrique, pause=True)
    rj.aller(rj.T1)
    ref = rj.suivi
    A = [b for b in su.bornes if b["type"] == "ancre" and b["src"] != "report"]
    B = [b for b in ref.bornes if b["type"] == "ancre"]
    ok = len(A) == len(B)
    pire_mm = pire_deg = 0.0
    for a, b in zip(A, B):
        ok &= a["src"] == b["src"]
        pire_mm = max(pire_mm, abs(a["X"] - b["X"]), abs(a["Y"] - b["Y"]))
        pire_deg = max(pire_deg, abs(suivi_mod.ecart(a["Cd"] - b["Cd"])))
        if a.get("corr") and b.get("corr") and a["src"] in suivi_mod.SOURCES_MESUREES:
            pire_mm = max(pire_mm, abs(a["corr"][0] - b["corr"][0]), abs(a["corr"][1] - b["corr"][1]))
    Pa, Pb = su.est[-1], ref.est[-1]
    d_fin = ((Pa[0] - Pb[0]) ** 2 + (Pa[1] - Pb[1]) ** 2) ** 0.5 if Pa and Pb else None
    ok &= pire_mm < 1.0 and pire_deg < 0.1 and d_fin is not None and d_fin < 1.0
    if Pa is None and Pb is None:                                 # position inconnue à la fin des deux côtés (robot porté à la main)
        d_fin, ok = 0.0, len(A) == len(B) and pire_mm < 1.0 and pire_deg < 0.1 and all(a["src"] == b["src"] for a, b in zip(A, B))
    ok &= [c[1] for c in su.contacts] == [c[1] for c in ref.contacts] and len(su.R) == len(ref.R)
    ok &= su.patinage == ref.patinage and [round(e[2]) for e in su.patine] == [round(e[2]) for e in ref.patine]
    # Ce qui est publié (sans son numéro de version ; rien et une liste vide se valent). Le signal de la base n'est
    # comparé que si le direct n'a pas repris de position de l'enregistrement précédent : avec cette reprise il sait
    # où était le robot dès la première ligne, et place donc des points que le rejeu d'un enregistrement seul ignore.
    repris = any(b["type"] == "ancre" and b["src"] == "report" for b in su.bornes)
    for cle in ("parois",) if repris else ("parois", "ir"):
        ok &= ((su.obj.get(cle) or (0, None))[1] or []) == ((ref.obj.get(cle) or (0, None))[1] or [])
    portes = [f"{suivi_mod.heure_de(b['t'])} {b['cause']}" for b in su.bornes if b["type"] == "porte"]
    portes_ref = [f"{suivi_mod.heure_de(b['t'])} {b['cause']}" for b in ref.bornes if b["type"] == "porte"]
    print(f"  {nom} : {len(su.R)} lignes (rejeu {len(ref.R)}), {len(A)} ancres (rejeu {len(B)}), écart le plus grand {pire_mm:.2f} mm et {pire_deg:.3f}°,"
          f" position finale à {d_fin if d_fin is None else round(d_fin, 2)} mm de celle du rejeu, contacts {[c[1] for c in su.contacts]},"
          f" firmware v{su.firmware} (patinage retiré : {'oui' if su.patinage else 'non'}, {sum(1 for e in su.patine if abs(e[2]) >= 60)} patinage(s) de plus de 6 cm),"
          f" {len(su.obj.get('parois', (0, []))[1]) // 4} parois vues, déplacé à la main : {portes or 'non'} (rejeu : {portes_ref or 'non'})"
          f" -> {'IDENTIQUE' if ok else 'DIFFÉRENT'}")
    return ok


def main():
    noms = sys.argv[1:]
    if not noms:
        sys.exit("usage : python essai_direct.py NOM [NOM2 ...]")
    tmp = tempfile.mkdtemp(prefix="carte_vivante_essai_")
    tout_bon = True
    try:
        E = [preparer(n, tmp) for n in noms]
        direct, erreurs, retards = None, 0, []
        t_mur = time.time()
        for q, e in enumerate(E):
            iA = iL = 0
            vues = set()
            T = e["T0"] - 0.5
            T_fin = e["T1"] + 30.0
            while T <= T_fin:
                while iA < len(e["actions"]) and e["actions"][iA][0] <= T:
                    e["actions"][iA][1](e["actions"][iA][0])
                    iA += 1
                j = iL
                while j < len(e["brut"]) and e["temps"][j] <= T:
                    j += 1
                if j > iL:
                    with open(e["dst"] + "_capteurs.csv", "a", encoding="utf-8", newline="\n") as f:
                        f.writelines(e["brut"][iL:j])
                    os.utime(e["dst"] + "_capteurs.csv", (T, T))
                    iL = j
                if direct is None and os.path.exists(e["dst"] + "_capteurs.csv"):
                    direct = sources.Direct(tmp, fabrique)
                if direct is not None:
                    try:
                        direct.tick(T)
                        direct.suivi.robot(T)
                    except Exception as err:
                        erreurs += 1
                        if erreurs <= 3:
                            print(f"  erreur à {suivi_mod.heure_de(T)} : {type(err).__name__} : {err}")
                    for b in direct.suivi.bornes if os.path.basename(direct.prefixe) == e["nom"] else ():
                        # combien de temps après la fin d'un tour son calage est-il pris en compte ?
                        if b["type"] == "ancre" and b["src"] in suivi_mod.SOURCES_MESUREES and b["cle"] not in vues:
                            vues.add(b["cle"])
                            retards.append(T - b["t"])
                T += PAS
            su = direct.suivi
            print(f"{e['nom']} suivi en direct simulé ({e['T1'] - e['T0']:.0f} s) ; époque {direct.epoque}, enregistrement suivi : {os.path.basename(direct.prefixe)}")
            rep = [b for b in su.bornes if b["type"] == "ancre" and b["src"] == "report"]
            if rep:
                u, v = su.px(rep[0]["X"], rep[0]["Y"])
                print(f"  position reprise de l'enregistrement précédent : case {su.gr.nom(u, v)}, pixel ({u}, {v})")
            tout_bon &= comparer(e["nom"], su) and os.path.basename(direct.prefixe) == e["nom"] and direct.epoque == q + 1
        retards.sort()
        print(f"calages pris en compte {retards[len(retards) // 2]:.1f} s après la fin du tour (médiane ; au plus {retards[-1]:.1f} s) ; "
              f"{erreurs} erreur(s) pendant le suivi ; {time.time() - t_mur:.0f} s de calcul")
        tout_bon &= erreurs == 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("RÉSULTAT :", "le direct simulé donne la même chose que le rejeu" if tout_bon else "ÉCART entre le direct simulé et le rejeu")
    return 0 if tout_bon else 1


if __name__ == "__main__":
    sys.exit(main())
