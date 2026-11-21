# situer_tour.py — où est le robot sur le plan, d'après UN tour sur place, en cherchant sur tout le plan (ou près d'un
# endroit, ou autour d'un cap connu). Sert quand le robot a été déplacé à la main ou que le cerveau a redémarré.
#
#   python situer_tour.py FICHIER_tour.json [--cap DEG --tol 25] [--pres U,V --rayon MM] [--n 8] [--image FICHIER.png]
#
# FICHIER_tour.json : la réponse de /api/tour gardée dans un fichier ({"tour": {"points": [[dixièmes de degré, mm], …]}}),
# ou cette réponse seule. --cap : cap du robot sur le plan AU DÉBUT du tour, s'il est connu à --tol près (par exemple le
# dernier cap connu plus ce que le gyroscope a compté depuis). --pres : ne chercher qu'à moins de --rayon de ce pixel.
#
# La note est celle du filtre de la navigation (localiser.Filtre._note) : les paliers du tour doivent tomber sur un trait
# du plan, les rayons libres ne traverser aucun mur, le centre du robot ne pas être dans un mur.
# ATTENTION, appris le 2026-11-21 (journal_wifi.md § 73) : un tour seul ne tranche pas. Plusieurs endroits du plan ont des
# notes voisines ; cet outil les LISTE, il ne choisit pas. Il faut un second témoin : la case dite par l'utilisateur,
# les faisceaux de la base, ou un second tour relié au premier par le chemin compté.
# Lecture seule : rien n'est envoyé au robot. Le plan est privé (plan_lidar/, hors dépôt) ; l'image aussi y reste.
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carto          # noqa: E402
import grille         # noqa: E402
import plan as plan_  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

RACINE = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
p = argparse.ArgumentParser()
p.add_argument("tour")
p.add_argument("--plan", default=os.path.join(RACINE, "plan_lidar", "plan_lidar.png"))
p.add_argument("--px-par-m", type=float, default=53.0)
p.add_argument("--cap", type=float, default=None, help="cap du robot sur le plan au début du tour, s'il est connu (degrés, 0 = droite, 90 = haut)")
p.add_argument("--tol", type=float, default=25.0, help="tolérance sur --cap, degrés")
p.add_argument("--pres", default="", help="U,V : ne chercher qu'autour de ce pixel")
p.add_argument("--rayon", type=float, default=1500.0, help="mm : rayon de la recherche autour de --pres")
p.add_argument("--n", type=int, default=8, help="nombre d'endroits listés")
p.add_argument("--image", default="", help="image des endroits possibles (à garder dans plan_lidar/, le plan est privé)")
a = p.parse_args()

pl = plan_.Plan(a.plan, a.px_par_m)
s, H, W = pl.s, pl.H, pl.W
gr = grille.Grille(a.px_par_m, W, H)
J = json.load(open(a.tour, encoding="utf-8"))
T = J.get("tour", J)
pts = np.array(T["points"], float)
pal = [(m_, d_, l_) for m_, d_, l_, nb in carto.paliers_souples(pts[:, 0] / 10.0, pts[:, 1])]
print("tour : %d mesures, %d paliers" % (len(pts), len(pal)))
for q in pal:
    print("    palier vers %+6.1f° : %5.0f mm, large de %4.1f°" % (((q[0] + 180) % 360) - 180, q[1], q[2]))
if not pal:
    sys.exit("aucun palier dans ce tour : rien à poser sur le plan")

A32, mur32, Cs32 = pl.A.astype(np.float32), pl.murf.astype(np.float32), pl.Cs.astype(np.float32)
ang = np.radians(np.array([q[0] for q in pal], np.float32))
dist = np.array([q[1] for q in pal], np.float32)
w = np.array([2.0 if q[2] >= 25 else 1.0 if q[2] >= 15 else 0.5 for q in pal], np.float32)
ra, rd = [], []
for k in range(len(dist)):
    m = max(2, int((dist[k] - 250.0) / 100.0))
    f = np.arange(1, m) / m * max(0.0, dist[k] - 250.0)
    ra.append(np.full(len(f), ang[k]))
    rd.append(f)
ra, rd = np.concatenate(ra).astype(np.float32), np.concatenate(rd).astype(np.float32)


def lire(img, X, Y, dehors=0.0):
    ui = np.rint(X * s).astype(np.int32)
    vi = np.rint(H - Y * s).astype(np.int32)
    ok = (ui >= 0) & (ui < W) & (vi >= 0) & (vi < H)
    return np.where(ok, img[np.clip(vi, 0, H - 1), np.clip(ui, 0, W - 1)], dehors)


def note(X, Y, C):
    c = np.radians(C).astype(np.float32)[:, None]
    t = c + ang[None, :]
    sc = (lire(A32, X[:, None] + dist[None, :] * np.cos(t), Y[:, None] + dist[None, :] * np.sin(t)) * w[None, :]).sum(1) / w.sum()
    if len(rd):
        tr = c + ra[None, :]
        sc = sc - 1.5 * lire(mur32, X[:, None] + rd[None, :] * np.cos(tr), Y[:, None] + rd[None, :] * np.sin(tr)).mean(1)
    return sc - lire(Cs32, X, Y, dehors=2.0)


PAS, PAS_CAP = 2, 2.0
ok = pl.interieur & (pl.D_mur >= 170.0 * s)
vv, uu = np.mgrid[0:H:PAS, 0:W:PAS]
m = ok[vv, uu]
if a.pres:
    u0, v0 = (float(x) for x in a.pres.split(","))
    m &= np.hypot(uu - u0, vv - v0) <= a.rayon * s
U0, V0 = uu[m].astype(np.float32), vv[m].astype(np.float32)
if a.cap is None:
    caps = np.arange(0.0, 360.0, PAS_CAP, dtype=np.float32)
else:
    caps = (a.cap + np.arange(-a.tol, a.tol + 0.01, PAS_CAP)).astype(np.float32)
print("recherche : %d positions x %d caps%s%s" % (len(U0), len(caps), "" if a.cap is None else " (cap %.0f° ± %.0f°)" % (a.cap, a.tol),
                                                 "" if not a.pres else " ; à moins de %.1f m du pixel (%s)" % (a.rayon / 1000.0, a.pres)))
if not len(U0):
    sys.exit("aucun sol libre où chercher")
X0, Y0 = U0 / s, (H - V0) / s
N = np.array([note(X0, Y0, np.full(len(X0), c, np.float32)) for c in caps])      # [cap, position]
ordre = np.argsort(N.ravel())[::-1][:20000]
ic, ip = np.unravel_index(ordre, N.shape)
vus = []
for k in range(len(ordre)):
    u, v, c, n_ = float(U0[ip[k]]), float(V0[ip[k]]), float(caps[ic[k]]) % 360.0, float(N[ic[k], ip[k]])
    if any(math.hypot(u - q[0], v - q[1]) < 400.0 * s and abs(((c - q[2] + 180) % 360) - 180) < 25 for q in vus):
        continue
    # affinage local : pas d'un pixel et de 0,5° autour de l'endroit
    du = np.arange(-3, 4, 1.0)
    dc = np.arange(-3.0, 3.01, 0.5)
    UU, VV, CC = np.meshgrid(u + du, v + du, c + dc, indexing="ij")
    nn = note((UU.ravel() / s).astype(np.float32), ((H - VV.ravel()) / s).astype(np.float32), CC.ravel().astype(np.float32))
    j = int(np.argmax(nn))
    vus.append((float(UU.ravel()[j]), float(VV.ravel()[j]), float(CC.ravel()[j]) % 360.0, float(nn[j])))
    if len(vus) >= a.n:
        break
vus.sort(key=lambda q: -q[3])
print("endroits possibles, du mieux noté au moins bien noté (cap : celui du DÉBUT du tour) :")
for i, (u, v, c, n_) in enumerate(vus, 1):
    print("  %d : case %-4s pixel (%6.1f ; %6.1f)  cap %5.1f° (%s)  note %.2f" % (i, gr.nom(u, v), u, v, c, grille.mot_du_cap(c), n_))
if len(vus) > 1 and vus[0][3] - vus[1][3] < 0.10:
    print("ATTENTION : les deux premiers sont à %.2f l'un de l'autre : ce tour ne tranche pas, il faut un second témoin." % (vus[0][3] - vus[1][3]))

if a.image:
    from PIL import Image, ImageDraw, ImageFont
    Z = 2
    im = Image.open(a.plan).convert("RGB").resize((W * Z, H * Z), Image.LANCZOS)
    dr = ImageDraw.Draw(im)
    try:
        fo, fo2 = ImageFont.truetype("arial.ttf", 13), ImageFont.truetype("arialbd.ttf", 22)
    except Exception:
        fo = fo2 = ImageFont.load_default()
    for i in range(gr.n_col + 1):
        dr.line([(i * gr.c * Z, 0), (i * gr.c * Z, H * Z)], fill=(190, 200, 215), width=1)
        if i < gr.n_col:
            dr.text((i * gr.c * Z + 4, 2), str(i + 1), fill=(60, 80, 140), font=fo)
    for j in range(gr.n_lig + 1):
        dr.line([(0, j * gr.c * Z), (W * Z, j * gr.c * Z)], fill=(190, 200, 215), width=1)
        if j < gr.n_lig:
            dr.text((2, j * gr.c * Z + 4), grille.LETTRES[j], fill=(60, 80, 140), font=fo)
    COUL = [(200, 30, 30), (20, 110, 200), (20, 150, 60), (200, 120, 0), (150, 40, 170), (0, 150, 150), (120, 120, 120), (90, 60, 20)]
    for i, (u, v, c, n_) in enumerate(vus, 1):
        col = COUL[(i - 1) % len(COUL)]
        for q in pal:                                   # les paliers du tour, posés depuis cet endroit
            t = math.radians(c + q[0])
            pu, pv = u + s * q[1] * math.cos(t), v - s * q[1] * math.sin(t)
            dr.line([(u * Z, v * Z), (pu * Z, pv * Z)], fill=col, width=1)
            dr.ellipse([pu * Z - 4, pv * Z - 4, pu * Z + 4, pv * Z + 4], fill=col)
        rr = 170.0 * s * Z
        dr.ellipse([u * Z - rr, v * Z - rr, u * Z + rr, v * Z + rr], outline=col, width=3)
        dr.line([(u * Z, v * Z), (u * Z + 2.2 * rr * math.cos(math.radians(c)), v * Z - 2.2 * rr * math.sin(math.radians(c)))], fill=col, width=3)
        dr.text((u * Z + rr + 4, v * Z - rr - 22), "%d : %s" % (i, gr.nom(u, v)), fill=col, font=fo2)
    im.save(a.image)
    print("image :", a.image)
