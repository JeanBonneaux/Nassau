# radar_capture.py — enregistre les mesures du radar à ultrasons (firmware roomba694_wifi v3) depuis le PC, sans rien
# envoyer au robot. Toutes les `periode` secondes : GET /api/radar (carte polaire) et GET /api/state (encodeurs, cap du
# gyroscope). Chaque mesure nouvelle donne une ligne CSV : heure, angle, distance, encodeurs et cap au moment de la
# lecture (de quoi, plus tard, replacer les points dans la pièce quand l'odométrie sera écrite). À la fin, la dernière
# carte est dessinée dans un fichier SVG (ouvrable dans un navigateur), sans bibliothèque à installer.
#
# Usage : python radar_capture.py [adresse] [duree_s] [periode_s] [dossier_de_sortie]
#   ex.  : python radar_capture.py 192.168.18.25 120 0.5 roomba694_recherche/mesures
# Le radar doit être activé par ailleurs (page web, touche r, ou curl "http://ADRESSE/api/radar?mode=balayage").
import csv
import datetime
import json
import math
import os
import sys
import time
import urllib.request

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.18.25"
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
period = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
outdir = sys.argv[4] if len(sys.argv) > 4 else "."
os.makedirs(outdir, exist_ok=True)

stamp = datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
csv_path = os.path.join(outdir, f"radar_{stamp}.csv")
svg_path = os.path.join(outdir, f"radar_{stamp}.svg")
MODES = {0: "arrêt", 1: "fixe", 2: "balayage"}


def get(path, timeout=3.0):
    with urllib.request.urlopen(f"http://{host}{path}", timeout=timeout) as r:
        return json.load(r)


def draw_svg(points, seuil_cm, portee_cm=200):
    """Demi-disque vu de dessus : robot en bas au centre, 0° vers le haut, angles positifs à gauche."""
    W, H, cx, cy, R = 640, 360, 320, 330, 300
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" style="background:#0f1115">',
           f'<path d="M{cx} {cy} L{cx - R} {cy} A{R} {R} 0 0 1 {cx + R} {cy} Z" fill="#232a38" stroke="#3a4255"/>']
    for k in range(1, 5):
        r = R * k / 4
        out.append(f'<path d="M{cx - r:.0f} {cy} A{r:.0f} {r:.0f} 0 0 1 {cx + r:.0f} {cy}" fill="none" stroke="#3a4255"/>')
        out.append(f'<text x="{cx + 4}" y="{cy - r + 12:.0f}" fill="#6b7386" font-size="11" font-family="sans-serif">{portee_cm * k // 4} cm</text>')
    for a in (-60, -30, 0, 30, 60):
        t = math.radians(a)
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{cx - R * math.sin(t):.0f}" y2="{cy - R * math.cos(t):.0f}" stroke="#3a4255"/>')
    rs = R * min(1.0, seuil_cm / portee_cm)
    out.append(f'<path d="M{cx - rs:.0f} {cy} A{rs:.0f} {rs:.0f} 0 0 1 {cx + rs:.0f} {cy}" fill="none" stroke="#ff5252" stroke-dasharray="5 4"/>')
    for a, mm, age in points:
        t = math.radians(a)
        al = max(0.25, 1 - age / 8000)
        if mm <= 0:   # rien à portée : petit point gris au bord
            out.append(f'<circle cx="{cx - (R - 4) * math.sin(t):.0f}" cy="{cy - (R - 4) * math.cos(t):.0f}" r="2.5" fill="#9aa3b5" opacity="{al:.2f}"/>')
            continue
        cm = mm / 10
        d = min(1.0, cm / portee_cm)
        col = "#ff5252" if cm < seuil_cm else "#3ddc84"
        out.append(f'<circle cx="{cx - R * d * math.sin(t):.1f}" cy="{cy - R * d * math.cos(t):.1f}" r="{3 if cm > portee_cm else 5}" fill="{col}" opacity="{al:.2f}"/>')
        out.append(f'<text x="{cx - R * d * math.sin(t) + 6:.0f}" y="{cy - R * d * math.cos(t) - 4:.0f}" fill="#c9d1e0" font-size="10" font-family="sans-serif">{a:+d}° {cm:.0f}</text>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="5" fill="#e8eaf0"/>')
    out.append(f'<text x="{cx}" y="{H - 6}" text-anchor="middle" fill="#9aa3b5" font-size="12" font-family="sans-serif">'
               f'radar à ultrasons · {stamp} · gauche ← 0° devant → droite · arc rouge : seuil {seuil_cm} cm</text>')
    out.append("</svg>")
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))


print(f"Enregistrement du radar de {host} pendant {duration:.0f} s, lecture toutes les {period} s. CSV : {csv_path}")
t_end = time.time() + duration
last_seen = {}          # angle -> date PC de la dernière mesure enregistrée
last_points, last_seuil = [], 30
n_rows, reachable = 0, True
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["heure", "t_mesure_s", "angle_deg", "dist_mm", "enc_g", "enc_d", "cap_deg", "mode", "servo_deg", "devant_cm"])
    while time.time() < t_end:
        t0 = time.time()
        try:
            r = get("/api/radar")
            s = get("/api/state")
        except Exception as e:
            if reachable:
                print(f"{datetime.datetime.now():%H:%M:%S}  carte injoignable ({type(e).__name__})")
                reachable = False
            time.sleep(max(0.0, period - (time.time() - t0)))
            continue
        if not reachable:
            print(f"{datetime.datetime.now():%H:%M:%S}  carte de nouveau joignable")
            reachable = True
        now = time.time()
        rob, imu = s["robot"], s["imu"]
        last_points, last_seuil = r["points"], r["seuil"]
        for a, mm, age in r["points"]:
            t_meas = now - age / 1000.0
            if abs(t_meas - last_seen.get(a, -1e9)) < 0.05:
                continue   # déjà enregistrée
            last_seen[a] = t_meas
            w.writerow([datetime.datetime.fromtimestamp(t_meas).strftime("%H:%M:%S.%f")[:-3], f"{t_meas:.3f}", a, mm,
                        rob["enc"][0], rob["enc"][1], imu["yaw"], r["mode"], r["servo"], r["front_cm"]])
            n_rows += 1
        f.flush()
        print(f"\r{datetime.datetime.now():%H:%M:%S}  mode {MODES.get(r['mode'], r['mode'])}, capteur vers {r['servo']:+d}°, "
              f"devant {r['front_cm']:.0f} cm, {len(r['points'])} cases mesurées, {n_rows} lignes écrites    ", end="", flush=True)
        time.sleep(max(0.0, period - (time.time() - t0)))
print()
if last_points:
    draw_svg(last_points, last_seuil)
    print(f"Dernière carte dessinée : {svg_path}")
print(f"Fin : {n_rows} mesures dans {csv_path}")
