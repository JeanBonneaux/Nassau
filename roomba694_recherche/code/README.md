# Code — Roomba 694 piloté par un ESP32

État au 2026-11-08 (soir). Sketches Arduino pour un ESP32 classique (ESP32-WROOM, devkit 30 ou 38 broches), compilés avec arduino-cli 1.5.1 et le paquet « esp32 » 3.3.7, téléversés et validés sur le robot : déroulé et mesures dans [journal_tests.md](journal_tests.md).

## Mesures faites sur le robot (multimètre, 2026-11-08)

| Broche Mini-DIN | Rôle | Mesure (par rapport au trou 6) |
|---|---|---|
| 1, 2 | Vpwr, + batterie | 14,66 V hors base (jusqu'à ~21 V sur la base selon iRobot) |
| 3 | RXD, entrée série du robot | 4,98 V au repos (rappel vers 5 V) |
| 4 | TXD, sortie série du robot | **3,30 V** au repos, robot éveillé |
| 5 | BRC, réveil | 4,98 V au repos (rappel vers 5 V) |
| 6, 7 | masse | 0 V entre 6 et 7 |

Conséquence : la sortie du robot est déjà en 3,3 V. Aucun adaptateur de niveau n'est nécessaire.

## Câblage du test 1 (alimentation par USB, sans abaisseur)

| Robot | ESP32 | Remarque |
|---|---|---|
| 4 (TXD) | GPIO16 (RX2) | direct ; 1 kΩ en série conseillé |
| 3 (RXD) | GPIO17 (TX2) | direct ; 1 kΩ en série conseillé |
| 5 (BRC) | GPIO4 | sortie, haute au repos ; impulsion basse = réveil |
| 6 ou 7 (GND) | GND | masse commune obligatoire |
| 1, 2 (Vpwr) | **rien** | ne pas relier pour ce test |

Carte de l'utilisateur (photo du 2026-11-08) : ESP32 DevKit 30 broches, module ESP32-WROOM-32 sans PSRAM, USB-C, CP2102. Sérigraphie : RX2 = GPIO16, TX2 = GPIO17, D4 = GPIO4, trois broches voisines sur le bord droit.

![Brochage complet, une couleur par fil](../images/brochage_complet_roomba694_esp32.jpg)

![Câblage sur la carte](../images/cablage_esp32_devkit30_test1.jpg)

Carte avec PSRAM (ESP32-WROVER) : GPIO16/17 sont pris par la PSRAM, utiliser 25/26 (modifier `PIN_RX`/`PIN_TX`).

Prompt prêt à coller pour la session Claude Code locale qui fera la compilation et le test : [PROMPT_session_locale.md](PROMPT_session_locale.md).

## `roomba694_test1/` — console série

Moniteur série à 115200 bauds, une touche puis Entrée :

- `w` impulsion BRC (réveil), `s` Start → Passive, `f` Safe, `b` batterie et mode OI, `e` pare-chocs/vide/boutons
- `m` 3 notes, `l` LEDs (mode Safe requis), `c` Clean, `h` retour base
- `8` avance, `2` recule, `4` gauche, `6` droite, `5` ou espace stop — chaque ordre s'arrête seul après 1,5 s
- `a` anti-veille (impulsion BRC toutes les 60 s), `o` Power, `x` Stop OI

Séquence de validation : `w`, `s`, `b` → la tension lue doit être proche de 14,66 V. Puis `f`, `m` (3 notes), `8`/`4`/`6`, et pour finir `s` puis `x`.

Règles :
- robot au sol, hors de sa base, espace dégagé ; ne pas le soulever en mode Safe (roue levée → retour automatique en Passive, c'est voulu) ;
- toujours finir par `s` puis `x` : en Safe/Full le robot ne se recharge pas et ne dort jamais ;
- si le robot part nettoyer après un appui sur CLEAN : `s` puis `f` le stoppent, puis `s`.

## Alimentation par le robot (étape suivante, non câblée)

Vpwr (broches 1-2) → abaisseur à découpage (buck) réglé sur 5,0 V → broche VIN/5V de l'ESP32. Module conseillé : MP1584EN (entrée jusqu'à 28 V) ou Pololu D24V5F5 (36 V). Régler la sortie au multimètre **avant** de brancher l'ESP32. Budget du port : 200 mA continus côté batterie, soit environ 500 mA sous 5 V après conversion (estimation).
