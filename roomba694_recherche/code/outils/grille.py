# grille.py — des coordonnées « comme aux échecs » sur le plan de l'appartement.
#
# Le plan est quadrillé en cases de 50 cm (une case = un robot et demi). Une case se nomme par la lettre de sa ligne
# puis le numéro de sa colonne : « K20 ». La ligne A est en haut du plan, la colonne 1 à gauche. Les lettres I et O ne
# servent pas : sur un petit écran elles se confondent avec 1 et 0.
#
# Sert à se dire sans ambiguïté où est le robot et où il doit aller (« il part de K20, tourné vers la droite ; objectif
# F8 ») : le 2026-11-10, « la pièce en haut à droite » ne désignait pas la même pièce pour l'utilisateur et pour le
# programme.
#
# Directions sur le plan, pour dire vers où regarde le robot : « droite » = cap 0°, « haut » = 90°, « gauche » = 180°,
# « bas » = 270° (et les quatre diagonales).
import math
import re

LETTRES = "ABCDEFGHJKLMNPQRSTUVWXYZ"
CASE_MM = 500.0
DIRECTIONS = {"droite": 0.0, "haut-droite": 45.0, "haut": 90.0, "haut-gauche": 135.0, "gauche": 180.0,
              "bas-gauche": 225.0, "bas": 270.0, "bas-droite": 315.0}


class Grille:
    def __init__(self, px_par_m, largeur_px, hauteur_px, case_mm=CASE_MM):
        self.c = case_mm * px_par_m / 1000.0                 # côté d'une case, en pixels du plan
        self.W, self.H = largeur_px, hauteur_px
        self.n_col = int(math.ceil(largeur_px / self.c))
        self.n_lig = int(math.ceil(hauteur_px / self.c))
        if self.n_lig > len(LETTRES):
            raise ValueError("plan trop haut pour une lettre par ligne")

    def nom(self, u, v):
        """nom de la case qui contient le pixel (u, v)"""
        col = min(self.n_col - 1, max(0, int(u // self.c)))
        lig = min(self.n_lig - 1, max(0, int(v // self.c)))
        return f"{LETTRES[lig]}{col + 1}"

    def lire(self, texte):
        """« k20 », « K 20 », « K-20 » -> (ligne, colonne) comptées de 0 ; None si ce n'est pas une case du plan"""
        m = re.fullmatch(r"\s*([A-Za-z])\s*[-. ]?\s*(\d{1,2})\s*", texte)
        if not m or m.group(1).upper() not in LETTRES:
            return None
        lig, col = LETTRES.index(m.group(1).upper()), int(m.group(2)) - 1
        if lig >= self.n_lig or not 0 <= col < self.n_col:
            return None
        return lig, col

    def centre(self, texte):
        """pixel du plan au centre de la case nommée ; None si le nom n'est pas une case"""
        lc = self.lire(texte)
        if lc is None:
            return None
        return (lc[1] + 0.5) * self.c, min(self.H - 1.0, (lc[0] + 0.5) * self.c)

    def coins(self, texte):
        lc = self.lire(texte)
        if lc is None:
            return None
        return lc[1] * self.c, lc[0] * self.c, (lc[1] + 1) * self.c, (lc[0] + 1) * self.c


def cap_de(mot):
    """« droite », « haut », « bas-gauche »... -> cap en degrés sur le plan ; None si le mot n'est pas connu"""
    return DIRECTIONS.get(mot.strip().lower().replace(" ", "-").replace("à-", ""))


def mot_du_cap(cap):
    return min(DIRECTIONS, key=lambda k: abs(((DIRECTIONS[k] - cap) + 180.0) % 360.0 - 180.0))


if __name__ == "__main__":
    g = Grille(53.0, 1214, 434)
    assert g.nom(0, 0) == "A1" and g.nom(1213, 433) == "S46", (g.nom(0, 0), g.nom(1213, 433))
    assert g.lire("k20") == (9, 19) and g.lire("I3") is None and g.lire("Z99") is None
    u, v = g.centre("K20")
    assert g.nom(u, v) == "K20"
    assert cap_de("Haut") == 90.0 and mot_du_cap(200.0) == "gauche"
    print("grille : ok,", g.n_lig, "lignes,", g.n_col, "colonnes, case de", round(g.c, 2), "pixels")
