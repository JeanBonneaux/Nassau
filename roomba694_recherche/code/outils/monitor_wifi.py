# monitor_wifi.py — observe le robot à travers l'API du firmware roomba694_wifi, sans rien lui envoyer.
# Toutes les `periode` secondes : GET /api/state -> une ligne CSV ; GET /api/log -> lignes de console nouvelles.
# Événements détectés et datés dans un second fichier : redémarrage de la carte (et sa raison), robot joignable
# ou non, changement de mode OI, pare-chocs, roue levée, bouton, épisodes de déplacement (distance et rotation
# calculées d'après les encodeurs, comparées au cap du gyroscope), carte injoignable.
#
# Usage : python monitor_wifi.py [adresse] [duree_s] [periode_s] [dossier_de_sortie]
#   ex.  : python monitor_wifi.py 192.168.18.25 1200 1 roomba694_recherche/mesures
# Firmware v3 : colonnes radar_mode (0 arrêt, 1 fixe, 2 balayage) et us_mm (distance devant mesurée par le radar à
# ultrasons : > 0 mm, 0 rien à portée, -1 inconnue) ; vides avec un firmware plus ancien.
import csv
import datetime
import json
import os
import sys
import time
import urllib.request

host = sys.argv[1] if len(sys.argv) > 1 else "192.168.18.25"
duration = float(sys.argv[2]) if len(sys.argv) > 2 else 600.0
period = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
outdir = sys.argv[4] if len(sys.argv) > 4 else "."
os.makedirs(outdir, exist_ok=True)

MM_PER_COUNT = 0.4446   # 508,8 pas par tour, roue de 72 mm (mesuré le 2026-11-08 : 500 pas pour 22 cm)
WHEELBASE_MM = 235.0

stamp = datetime.datetime.now().strftime("%Y-%m-%d_%Hh%M")
csv_path = os.path.join(outdir, f"monitor_{stamp}.csv")
ev_path = os.path.join(outdir, f"monitor_{stamp}_evenements.txt")

FIELDS = ["heure", "uptime_s", "robot_ok", "age_s", "mode", "v_mV", "i_mA", "t_C", "q_mAh", "enc_g", "enc_d",
          "cap_deg", "rot_dps", "roues", "vitesse", "bump_g", "bump_d", "drop_g", "drop_d",
          "vide_g", "vide_avg", "vide_avd", "vide_d", "lb_g", "lb_avg", "lb_cg", "lb_cd", "lb_avd", "lb_d",
          "lbits", "btn", "radar_mode", "us_mm", "ap_clients", "sta_ip", "rst"]


def now():
    return datetime.datetime.now().strftime("%H:%M:%S")


def get(path, timeout=3.0):
    with urllib.request.urlopen(f"http://{host}{path}", timeout=timeout) as r:
        return json.load(r)


def event(text):
    line = f"{now()}  {text}"
    print(line, flush=True)
    with open(ev_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def row_from_state(s):
    r, i = s["robot"], s["imu"]
    return {
        "heure": now(), "uptime_s": s["ms"] // 1000, "robot_ok": int(r["ok"]), "age_s": round(r["age"] / 1000, 1),
        "mode": r["mode"], "v_mV": r["v"], "i_mA": r["i"], "t_C": r["t"], "q_mAh": r["q"],
        "enc_g": r["enc"][0], "enc_d": r["enc"][1], "cap_deg": i["yaw"], "rot_dps": i["rate"],
        "roues": int(s["driving"]), "vitesse": s["speed"],
        "bump_g": r["bump"][0], "bump_d": r["bump"][1], "drop_g": r["drop"][0], "drop_d": r["drop"][1],
        "vide_g": r["cliff"][0], "vide_avg": r["cliff"][1], "vide_avd": r["cliff"][2], "vide_d": r["cliff"][3],
        "lb_g": r["light"][0], "lb_avg": r["light"][1], "lb_cg": r["light"][2], "lb_cd": r["light"][3],
        "lb_avd": r["light"][4], "lb_d": r["light"][5], "lbits": r["lbits"], "btn": r["btn"],
        "radar_mode": s.get("radar", {}).get("mode", ""), "us_mm": s.get("radar", {}).get("front_mm", ""),
        "ap_clients": s["ap"]["clients"], "sta_ip": s["sta"]["ip"], "rst": s.get("rst", ""),
    }


MODES = {1: "Off", 2: "Passive", 3: "Safe", 4: "Full"}

event(f"Observation de {host} pendant {duration:.0f} s, une mesure toutes les {period} s. CSV : {csv_path}")
t_end = time.time() + duration
prev = None
reachable = True
seq = None
drive_start = None   # (heure, enc_g, enc_d, cap) au début d'un épisode de roues en mouvement
with open(csv_path, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS, delimiter=";")
    w.writeheader()
    while time.time() < t_end:
        t0 = time.time()
        try:
            s = get("/api/state")
        except Exception as e:  # carte injoignable (redémarrage, Wi-Fi)
            if reachable:
                event(f"carte injoignable ({type(e).__name__})")
                reachable = False
            time.sleep(max(0.0, period - (time.time() - t0)))
            continue
        if not reachable:
            event("carte de nouveau joignable")
            reachable = True
        row = row_from_state(s)
        w.writerow(row)
        f.flush()
        r = s["robot"]
        if prev is not None:
            if row["uptime_s"] < prev["uptime_s"]:
                event(f"REDÉMARRAGE de la carte (en marche depuis {row['uptime_s']} s) — raison : {row['rst']}")
            if row["robot_ok"] != prev["robot_ok"]:
                event("robot joignable" if row["robot_ok"] else f"robot sans réponse (dernier contact il y a {row['age_s']} s)")
            if row["robot_ok"] and row["mode"] != prev["mode"]:
                event(f"mode OI : {MODES.get(row['mode'], row['mode'])} (brut {row['mode']})")
            if row["robot_ok"] and (row["bump_g"], row["bump_d"]) != (prev["bump_g"], prev["bump_d"]):
                event(f"pare-chocs gauche {row['bump_g']}, droit {row['bump_d']}")
            if row["robot_ok"] and (row["drop_g"], row["drop_d"]) != (prev["drop_g"], prev["drop_d"]):
                event(f"roue levée gauche {row['drop_g']}, droite {row['drop_d']}")
            if row["robot_ok"] and row["btn"] != prev["btn"] and row["btn"]:
                event(f"bouton(s) du robot : bits {row['btn']}")
            if row["vitesse"] != prev["vitesse"]:
                event(f"vitesse réglée : {row['vitesse']} mm/s")
            if row["roues"] and not prev["roues"]:
                drive_start = (now(), row["enc_g"], row["enc_d"], row["cap_deg"])
            if prev["roues"] and not row["roues"] and drive_start is not None:
                # les compteurs d'encodeurs sont sur 16 bits signés et bouclent à ±32 768 (vu le 2026-11-08 : -58 192 pas en 24 s)
                dg = (row["enc_g"] - drive_start[1] + 32768) % 65536 - 32768
                dd = (row["enc_d"] - drive_start[2] + 32768) % 65536 - 32768
                dist = (dg + dd) / 2 * MM_PER_COUNT
                rot_enc = (dd - dg) * MM_PER_COUNT / WHEELBASE_MM * 57.2958
                dcap = row["cap_deg"] - drive_start[3]
                event(f"déplacement {drive_start[0]} -> {now()} : encodeurs G {dg:+d} / D {dd:+d} pas "
                      f"= {dist:+.0f} mm, rotation d'après encodeurs {rot_enc:+.0f}°, d'après gyroscope {dcap:+.1f}°")
                drive_start = None
        else:
            event(f"première mesure : carte en marche depuis {row['uptime_s']} s (raison : {row['rst']}), "
                  f"robot {'joignable' if row['robot_ok'] else 'sans réponse'}, mode brut {row['mode']}, "
                  f"{row['v_mV']} mV, cap {row['cap_deg']}°")
        prev = row
        # Lignes de console nouvelles
        try:
            lg = get(f"/api/log?since={seq if seq is not None else 0}")
            if seq is None:
                seq = lg["seq"]          # on ne rejoue pas l'historique, on part de maintenant
            else:
                for k, line in enumerate(lg["lines"]):
                    if lg["from"] + k >= seq and line.strip():
                        event(f"console : {line}")
                seq = lg["seq"]
        except Exception:
            pass
        time.sleep(max(0.0, period - (time.time() - t0)))
event("fin de l'observation")
