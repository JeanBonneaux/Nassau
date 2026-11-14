# ping_suivi.py — note, deux fois par seconde, si le cerveau répond à un ping du PC, pour savoir après coup si un
# trou du journal vient de la liaison Wi-Fi ou d'autre chose. Le ping est traité par la pile réseau du cerveau, pas par
# sa boucle principale : un cerveau dont la boucle attend répond encore au ping, une liaison coupée non.
# N'envoie rien au robot.
#
# Usage : python ping_suivi.py ADRESSE SORTIE.csv [--secondes 160] [--periode 0.5]
import argparse
import re
import subprocess
import sys
import time

p_ = argparse.ArgumentParser()
p_.add_argument("adresse")
p_.add_argument("sortie")
p_.add_argument("--secondes", type=float, default=160.0)
p_.add_argument("--periode", type=float, default=0.5)
a = p_.parse_args()
attente = ["-n", "1", "-w", "700"] if sys.platform.startswith("win") else ["-c", "1", "-W", "1"]
t0 = time.time()
n = perdus = 0
with open(a.sortie, "w", encoding="utf-8") as f:
    f.write("pc_s,ok,ms\n")
    while time.time() - t0 < a.secondes:
        t = time.time()
        r = subprocess.run(["ping"] + attente + [a.adresse], capture_output=True, text=True, errors="replace")
        m = re.search(r"(?:time|temps)[=<]\s*(\d+)\s*ms", r.stdout)
        ok = m is not None and "TTL" in r.stdout.upper()
        f.write(f"{t:.3f},{int(ok)},{m.group(1) if ok else ''}\n")
        f.flush()
        n += 1
        perdus += 0 if ok else 1
        time.sleep(max(0.0, a.periode - (time.time() - t)))
print(f"{n} pings, {perdus} sans réponse ; écrit : {a.sortie}")
