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

Plan de montage (version du 2026-11-08, tard le soir, après repositionnement de la plaque **à l'horizontale** sur le robot) : la carte ESP32 est à droite de la plaque, ses broches 3V3 … D23 dans la colonne b du bandeau du haut, **3V3 en rangée 11 et D23 en rangée 25** ; la rangée de trous libres (colonne a) est juste au-dessus des broches. Les composants vont à gauche de la carte, rangées 28 à 48 du bandeau du haut (le ruban adhésif commence vers la rangée 50). Alimentation **uniquement par l'USB-C de la carte**. Les bandes du haut distribuent le 3,3 V (rouge +) et la masse (bleue −) **de la carte**, tout étant branché dans leur segment de droite (rangées ≤ 30). Trous 1, 2 et 7 du robot : vides.

| # | De | Vers | Quoi | Trou du robot |
|---|---|---|---|---|
| 1 | trou libre de **3V3** (r11) | bande rouge +, trou vers r10 | fil | — |
| 2 | trou libre de **GND** (r12) | bande bleue −, trou vers r10 | fil | — |
| 3 | trou libre de **TX2** (r17) | r44 (colonne b) | fil | — |
| 4 | r44 | r46 | résistance 1 kΩ debout, colonne c | — |
| 5 | r46 (colonne d) | prise du robot | fil long, bout mâle | **trou 3** (RXD) |
| 6 | trou libre de **RX2** (r16) | r41 (colonne b) | fil | — |
| 7 | r41 | r43 | résistance 1 kΩ debout, colonne c | — |
| 8 | r43 (colonne d) | prise du robot | fil long | **trou 4** (TXD) |
| 9 | trou libre de **D4** (r15) | r38 (colonne b) | fil | — |
| 10 | r38 | r40 | résistance 1 kΩ debout, colonne c | — |
| 11 | r40 (colonne d) | prise du robot | fil long | **trou 5** (BRC) |
| 12 | bande bleue − (trou vers r20) | prise du robot | fil long, sans résistance | **trou 6** (GND) |
| 13 | module GY-521 sur ses broches, colonne c, rangées 29 à 36 : VCC 29, GND 30, SCL 31, SDA 32 ; XDA, XCL, AD0, INT (33 à 36) libres ; corps à plat vers le canal, puce en haut | | | — |
| 14 | r29 (VCC, colonne b) | bande rouge +, trou vers r27 | fil | — |
| 15 | r30 (GND, colonne b) | bande bleue −, trou vers r28 | fil | — |
| 16 | r31 (SCL, colonne b) | trou libre de **D22** (r24) | fil | — |
| 17 | r32 (SDA, colonne b) | trou libre de **D21** (r21) | fil | — |

Rangées des broches de la carte (colonne b, à lire sur la plaque) : 3V3 11, GND 12, D15 13, D2 14, D4 15, RX2 16, TX2 17, D5 18, D18 19, D19 20, D21 21, RX0 22, TX0 23, D22 24, D23 25. Les bandes sont probablement coupées vers le milieu de la plaque (rangées 31-33 observées sur une photo précédente) : toutes les connexions aux bandes ci-dessus sont dans le même segment (rangées 10 à 28), donc sans risque ; vérifier après mise sous tension 3,3 V entre bande rouge et bande bleue près de la rangée 27. Image du plan sur la photo de la plaque : `../images/plan_sur_photo_plaque.jpg`. Position du module : `../images/gy521_position_sur_plaque.jpg` (module à plat, axe Z vertical).

## Alimentation par le robot (étape suivante, non câblée)

Vpwr (broches 1-2) → abaisseur à découpage (buck) réglé sur 5,0 V → broche VIN/5V de l'ESP32. Module conseillé : MP1584EN (entrée jusqu'à 28 V) ou Pololu D24V5F5 (36 V). Régler la sortie au multimètre **avant** de brancher l'ESP32. Budget du port : 200 mA continus côté batterie, soit environ 500 mA sous 5 V après conversion (estimation).

## `roomba694_wifi/` — pilotage et mises à jour par Wi-Fi

Même câblage, mêmes touches et mêmes sécurités que `roomba694_test1`, plus le gyroscope GY-521 (MPU-6050) sur D21/D22, et sans câble vers le PC : l'ESP32 peut être alimenté par une batterie portable USB fixée sur le robot. Trois fichiers : `roomba694_wifi.ino` (robot, capteurs, gyroscope, console, Wi-Fi), `web.ino` (API et pages servies) et `pages.h` (le HTML des pages, dans un `.h` parce que l'outil Arduino prend le JavaScript des pages pour des fonctions C++ s'il est dans un `.ino`). Déroulé des tests : [journal_wifi.md](journal_wifi.md).

- **Réseau de la carte** : elle crée toujours le Wi-Fi « Roomba694 » (mot de passe par défaut `roomba694`, à changer via `secrets.h`, voir `secrets.example.h`). Connecter le téléphone ou le PC à ce réseau (rester dessus même si l'appareil signale « pas d'internet »), puis ouvrir http://192.168.4.1.
- **Réseau de la maison (option)** : page http://192.168.4.1/wifi : bouton « Chercher les réseaux » (liste des réseaux 2,4 GHz à portée), saisie du mot de passe, enregistrement et connexion immédiate sans redémarrage ; la page affiche l'avancement et, en cas d'échec, la cause (réseau introuvable, mot de passe refusé). Le nom et le mot de passe restent dans la mémoire de la carte, jamais dans le code ni sur la console. La carte garde son propre réseau et répond aussi à l'adresse obtenue sur le réseau de la maison et à http://roomba694.local.
- **Page web** (port 80, conçue pour le téléphone) : pavé de pilotage « maintenir pour rouler, relâcher pour arrêter » (l'ordre est répété toutes les 400 ms tant que le doigt reste appuyé ; arrêt au relâchement et, de toute façon, 1,5 s après le dernier ordre), curseur de vitesse de 50 à 150 mm/s, boutons réveil / Passive / Safe / Stop OI, batterie (pourcentage, tension, courant, température, état de charge), mode OI décodé, dessin du robot vu de dessus (pare-chocs, 6 signaux « light bumper », 4 capteurs de vide, roues levées), encodeurs, cadran du cap gyroscopique, actions (3 notes, LEDs, anti-veille, CSV, Clean, base, extinction avec confirmation) et console intégrée (les mêmes lignes que la console série, avec envoi d'une touche). API : http://192.168.4.1/api/state (JSON complet), `/api/cmd?c=8` (une touche), `/api/speed?v=100`, `/api/log?since=0` (dernières lignes de la console), `/api/scan` (réseaux à portée).
- **Console TCP** (port 23) : mêmes touches qu'en USB, même sortie. Depuis le PC : `powershell -ExecutionPolicy Bypass -File roomba694_recherche/code/outils/tcp_console.ps1 -HostName 192.168.4.1 -Commands 's','b'`. La sortie va aussi sur l'USB si un câble est branché.
- **Journal CSV** : touche `j` (console ou bouton). Une ligne toutes les 200 ms tant que le robot répond : `csv,ms,enc_g,enc_d,pc_g,pc_d,roue_g,roue_d,vide_g,vide_avg,vide_avd,vide_d,lb_g,lb_avg,lb_cg,lb_cd,lb_avd,lb_d,mv,ma,mode`. Pour enregistrer une minute : `tcp_console.ps1 -HostName 192.168.4.1 -Commands 'j' -ListenSeconds 60 -Log parcours.csv`, puis renvoyer `j` pour arrêter.
- **Lecture des capteurs** : toutes les 200 ms par une seule requête groupée (opcode 149, 22 paquets, 38 octets). Le 694 testé y répond, mais met plusieurs centaines de ms à envoyer la réponse complète : le firmware la ramasse au fil de la boucle, sans bloquer (délai maximal 600 ms), et aucune autre requête n'est envoyée tant qu'elle est attendue. Sans réponse complète, repli sur une lecture paquet par paquet (un paquet par passage de la boucle, cycle de 0,6 s environ) ; touche `q` pour réessayer la lecture groupée et afficher les octets reçus et le temps de réponse. Si le robot ne répond plus (endormi, OI fermée), une tentative toutes les 2 s seulement.
- **Gyroscope** : touche `g` (accélérations, vitesses de rotation, axe vertical détecté, cap intégré), touche `z` (recalibration 1 s robot immobile et cap remis à zéro). Le cap est positif vers la gauche (anti-horaire), comme l'angle de l'OI ; une petite zone morte (0,3 °/s) évite la dérive à l'arrêt, mais le cap peut dériver pendant les mouvements : `z` avant chaque mesure.
- **Mises à jour sans câble** :
  1. page http://192.168.4.1/update : envoyer le fichier `.bin` produit par `arduino-cli compile --fqbn esp32:esp32:esp32 --export-binaries roomba694_recherche/code/roomba694_wifi` (il apparaît dans `roomba694_wifi/build/esp32.esp32.esp32/roomba694_wifi.ino.bin`) ;
  2. ArduinoOTA, carte sur le réseau de la maison : `arduino-cli upload -p ADRESSE_IP --fqbn esp32:esp32:esp32 --upload-field password=roomba694 roomba694_recherche/code/roomba694_wifi` (syntaxe à confirmer au premier essai, voir le journal).
- **Mises en garde** : la batterie portable doit rester allumée (le Wi-Fi actif, 100 à 250 mA, suffit en général à éviter sa coupure automatique) ; scotcher la carte, la batterie et les fils, car un pion qui sort de la prise pendant un déplacement laisse le robot sur son dernier ordre ; ne pas brancher l'USB du PC et une autre alimentation en même temps ; toujours finir par `s` puis `x`.
