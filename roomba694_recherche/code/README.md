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

*Image mise à jour le 2026-11-08 (soir) : prise du robot, carte ESP32, gyroscope GY-521 et plan de la plaque d'essai (section plus bas).*

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

## Résistances de protection (facultatives, conseillées pour le montage définitif)

Trois résistances de **1 kΩ** (brun-noir-rouge ; 470 Ω à 2,2 kΩ conviennent), une **en série sur chaque fil de signal**, n'importe où le long du fil :

| Fil | Liaison | Ce que la résistance limite |
|---|---|---|
| bleu | robot 4 (TXD) → RX2 | le courant entrant dans l'ESP32 si le fil touche autre chose que TXD (Vpwr 14,66 V / 1 kΩ ≈ 15 mA au lieu d'un court-circuit) |
| vert | TX2 → robot 3 (RXD) | le courant poussé par l'ESP32 si le pion est dans un mauvais trou |
| orange | D4 → robot 5 (BRC) | idem ; dans le journal du 2026-11-08, D4 a poussé 3,3 V pendant 40 min dans un fil à 0 V, sans dégât mais sans protection |

Rien sur la masse ni sur l'alimentation. 1 kΩ ne gêne pas la liaison à 115200 bauds. La liaison a été validée sans ces résistances ; elles servent d'assurance contre une erreur de câblage, pas au fonctionnement.

## Gyroscope GY-521 (MPU-6050) et plan de la plaque d'essai

Module de l'utilisateur : GY-521 (sérigraphie « HW-123 », 8 broches : VCC, GND, SCL, SDA, XDA, XCL, AD0, INT). Liaison I²C sur les broches par défaut de l'ESP32 : **SDA = D21 (GPIO21), SCL = D22 (GPIO22)**, toujours sur le bord droit de la carte. Alimentation du module en 3,3 V depuis la broche 3V3 de la carte (le module a son propre régulateur et ses résistances de rappel I²C). AD0 laissé libre → adresse I²C 0x68. XDA, XCL, INT : libres.

Plan de montage établi par la session locale du 2026-11-08 (soir) : l'ESP32 enfiché sur une plaque d'essai, rangées ~29 à 45, la rangée de trous libres au-dessus des broches du bord droit (D23 … 3V3). Alimentation **uniquement par l'USB-C de la carte** (PC, puis batterie portable). Les bandes du haut de la plaque distribuent le 3,3 V (rouge +) et la masse (bleue −) **de la carte**. Trous 1 et 2 du robot : vides.

| # | De | Vers | Quoi |
|---|---|---|---|
| 1 | trou libre au-dessus de **3V3** | bande rouge + | fil (la bande porte 3,3 V) |
| 2 | trou libre au-dessus de **GND** | bande bleue − | fil |
| 3 | trou libre au-dessus de **TX2** | rangée 22 | fil |
| 4 | rangée 22 | rangée 24 | résistance 1 kΩ |
| 5 | rangée 24 | robot trou **3** (RXD) | fil long mâle-mâle |
| 6 | trou libre au-dessus de **RX2** | rangée 18 | fil |
| 7 | rangée 18 | rangée 20 | résistance 1 kΩ |
| 8 | rangée 20 | robot trou **4** (TXD) | fil long |
| 9 | trou libre au-dessus de **D4** | rangée 14 | fil |
| 10 | rangée 14 | rangée 16 | résistance 1 kΩ |
| 11 | rangée 16 | robot trou **5** (BRC) | fil long |
| 12 | bande bleue − | robot trou **6** (GND) | fil long, sans résistance |
| 13 | module GY-521 **debout**, 8 broches dans les rangées 3 à 10 : VCC en 3, GND en 4, SCL en 5, SDA en 6 ; rangées 7 à 10 libres | | |
| 14 | rangée 3 (VCC) | bande rouge + | fil |
| 15 | rangée 4 (GND) | bande bleue − | fil |
| 16 | rangée 5 (SCL) | trou libre au-dessus de **D22** | fil |
| 17 | rangée 6 (SDA) | trou libre au-dessus de **D21** | fil |

Repères (approximatifs, lire le numéro imprimé sur la plaque) : 3V3 ≈ 30, GND ≈ 31, D4 ≈ 34, RX2 ≈ 35, TX2 ≈ 36, D21 ≈ 40, D22 ≈ 43. **Plan dessiné sur la photo de la plaque, numéros = étapes de ce tableau : `../images/plan_sur_photo_plaque.jpg`.** Photo annotée de la plaque : `../images/plaque_esp32_placee_rangees.jpg`. Schéma de la zone composants (position du GY-521, résistances, fils) : `../images/plan_plaque_zone_composants.jpg`. **Attention** : sur cette plaque, les bandes d'alimentation semblent coupées vers les rangées 31-33 ; brancher les deux fils qui alimentent les bandes (étapes 1 et 2) dans des trous de bande situés **au-dessus de la rangée 29**, du même côté que le gyroscope, puis vérifier au multimètre 3,3 V entre la bande rouge et la bande bleue près de la rangée 5. Dans une moitié de plaque, les cinq trous d'une rangée sont reliés et deux rangées voisines ne le sont pas : une résistance va donc d'une rangée à l'autre (23, 19 et 15 restent vides pour la lisibilité). Vérifier que la bande rouge n'est pas coupée au milieu de la plaque. Dernier coup d'œil avant l'USB : rien sur les trous 1 et 2 du robot, la bande rouge ne va qu'au VCC du gyroscope, chaque résistance a une patte dans chaque rangée.

## Alimentation par le robot (étape suivante, non câblée)

Vpwr (broches 1-2) → abaisseur à découpage (buck) réglé sur 5,0 V → broche VIN/5V de l'ESP32. Module conseillé : MP1584EN (entrée jusqu'à 28 V) ou Pololu D24V5F5 (36 V). Régler la sortie au multimètre **avant** de brancher l'ESP32. Budget du port : 200 mA continus côté batterie, soit environ 500 mA sous 5 V après conversion (estimation).
