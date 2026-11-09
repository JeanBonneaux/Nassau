# F — Ce que d'autres ont fait avec leurs Roomba : améliorations, programmation, cartographie

Recherche web du 2026-11-08 (soir), menée en trois volets parallèles (matériel ajouté ; façons de programmer ; cartographie et autonomie), chaque lien ouvert et vérifié. Elle complète la note [C_projets_existants.md](C_projets_existants.md) (ponts série ESP8266/ESP32/Raspberry Pi et projets caméra, déjà recensés) et s'appuie sur ce que nous avons mesuré nous-mêmes sur le 694 ([../code/journal_tests.md](../code/journal_tests.md), [../code/journal_wifi.md](../code/journal_wifi.md)).

Mise à jour du 2026-11-08 (nuit) : décision de **ne plus utiliser de batterie portable** (tout alimenté par la prise du robot, LiDAR compris), budget de courant chiffré et références d'achat Amazon.fr en section 2.1, liste des modules du kit confirmée en section 5.

## En deux mots

- **Aucune carte ne viendra du robot lui-même** : la série 600 navigue au hasard et l'application iRobot ne garde que des statistiques. La carte viendra de notre électronique.
- **Ce que nous avons déjà (ESP32 + encodeurs + gyroscope) permet une carte « par contact »** reconnaissable d'une pièce, comme le projet « Old Roomba, new tricks » (Roomba 632 + ESP8266 + MPU-6050, la configuration la plus proche de la nôtre). Pas une carte métrique.
- **La seule voie vers une vraie carte de l'appartement est un LiDAR 2D (65 à 110 €)**. Bonne nouvelle : l'ESP32 suffit à lire le LiDAR et à envoyer les mesures en Wi-Fi vers le PC, qui fait le calcul (SLAM). Un Raspberry Pi ne devient nécessaire que pour une navigation autonome sans PC allumé.
- **Première amélioration matérielle à faire : l'alimentation.** Les redémarrages de la carte de ce soir ont pour cause une coupure franche de l'alimentation (connecteur ou batterie secoués). Les autres bricoleurs alimentent leur module depuis la prise du robot avec un petit abaisseur de tension, dans la limite de 200 mA, avec un interrupteur. Ces 200 mA se comptent côté robot (14 à 21 V) : après conversion en 5 V il reste environ 500 mA, de quoi alimenter la carte, le gyroscope **et** le LiDAR sans batterie portable (section 2.1).
- Les pièges rapportés par les autres recoupent les nôtres : veille après 5 min en Passive, réveil BRC capricieux, paquets « distance » faux, robot qui ne se recharge pas en Safe, TX à 5 V de certains robots, octets parasites.

## 1. Ce que le 694 ne fera jamais seul

Le 694 nettoie par rebonds pseudo-aléatoires, sans caméra ni LiDAR ; l'application iRobot Home affiche l'historique et les durées, pas de plan. Chez iRobot, la carte « Clean Map » apparaît avec la série 900 (caméra de localisation) et les cartes « Imprint Smart Mapping » (pièces nommées, zones interdites) avec les i3 à i8, j6 à j9, s9, m6 et Combo 10 Max ; la fiche officielle sur la sauvegarde des cartes ne mentionne pas la série 600. [M1, M2, M3]

## 2. Matériel : ce que les gens ajoutent

### 2.1 Alimenter le module depuis le robot

La spécification officielle (série 600) est claire : les broches 1-2 (Vpwr) donnent la tension **non régulée** de la batterie (14 à 21 V, jusqu'à ~16 V mesurés sur la base) à travers un fusible réarmable de **200 mA**, « ne pas dépasser 500 mA en crête ». En Safe/Full le robot ne dort jamais et **ne se recharge pas**, même posé sur la base : toujours finir en Passive puis Stop. [H1, H2, H16]

| Approche | Projet (année, robot) | Matériel | Retour d'expérience |
|---|---|---|---|
| Abaisseur 5 V sur Vpwr | PiCreate, Servo Magazine (2018, Create 2 + Pi 3) [H3] | UBEC 5 V Adafruit + interrupteur | fonctionne en démonstration |
| Abaisseur 3,3 V sur Vpwr | ESP8266 controlled Roomba (2015, Roomba 780) [H4] | Mini360 ou Recom R78B3.3 | régler la tension avant de brancher ; des 650 s'endorment malgré les impulsions BRC |
| Abaisseur MP1584EN | Roomba + Alexa (2021, série 500) [H5, H6] | MP1584EN (4,5 à 28 V en entrée) | module laissé sous tension = batterie vidée, d'où l'interrupteur ; la console de debug parasite l'OI |
| Linéaire puis abaisseur | **Old Roomba, new tricks (2022 → 2025, Roomba 632 + ESP8266 + MPU-6050)** [H7, H8] | LM7833 (chauffe : 1,4 W) remplacé par un abaisseur 3,3 V + condensateur 3300 µF | coupures Wi-Fi quand les moteurs forcent (chute de tension) ; le condensateur a réglé le problème |
| Abaisseur + transistor | The Hook Up (2018, Roomba 530, ESP-01) [H9] | abaisseur réglé au multimètre | OI muette après rebranchement : retirer la batterie quelques secondes |
| Batterie séparée | nnarain (2021 → 2026, Create 2 + Pi) [H10 à H13] | batterie 12 V 6 A + abaisseur, logée dans un bac à poussière agrandi | un Raspberry Pi (5 V/3 à 5 A) est hors de portée du port OI |

Pièges confirmés ailleurs : TX à 5 V d'un robot qui grille l'entrée d'un Raspberry Pi [H15] (notre 694 sort du 3,3 V, mesuré) ; module Thinking Cleaner qui se met en sécurité sous 10 % de batterie [H18] ; brosse principale qui perturbe le magnétomètre d'une IMU [H19] ; bug de réveil BRC pendant la charge d'entretien, contourné par une LED infrarouge qui imite la télécommande [H17].

**Pour nous (décision du 2026-11-08 : plus de batterie portable, tout depuis le robot).** Le fusible limite le courant **côté robot** ; un abaisseur à découpage transforme la puissance, donc 200 mA sous 14 à 16 V (2,8 à 3,2 W) deviennent, avec un rendement de 85 %, environ **480 à 540 mA sous 5 V**. Budget estimé (rendement 85 %, batterie à 14,4 V ; consommation de l'ESP32 d'après [A5, A6], du LD19 d'après sa fiche technique [A7]) :

| Charge sur le rail 5 V | Courant sous 5 V | Courant côté robot |
|---|---|---|
| ESP32 Wi-Fi actif (130 à 160 mA en moyenne, pointes de 0,3 à 0,7 A pendant moins d'une milliseconde, lissées par les condensateurs) + GY-521 (4 mA) | ~150 mA | ~60 mA |
| + LiDAR LD19 en rotation (180 mA) | ~330 mA | ~135 mA |
| + LiDAR au lancement (300 mA pendant 1 à 2 s) | ~450 mA | ~185 mA |
| Limite de la prise (spécification) | | 200 mA en continu, coupure du fusible au-delà de 500 mA en crête |

Montage retenu : un abaisseur **5 V fixe** (rien à régler, donc pas d'erreur de réglage), entrée acceptant au moins 30 V (la prise monte à 21-22 V sur la base), sortie 3 A, du type « module voiture 12/24 V → 5 V 3 A » moulé avec fils. Entrée + sur la broche 1 ou 2 du robot **à travers un interrupteur**, entrée − sur 6 ou 7 ; sortie 5 V sur le rail + de la plaque d'essai, qui alimente la broche VIN de l'ESP32 et le 5 V du LiDAR ; masse commune (déjà le cas pour la liaison série) ; un condensateur de 470 à 1000 µF sur le rail 5 V (« Old Roomba, new tricks » a réglé ses coupures Wi-Fi avec 3300 µF [H8]). Règles : câbler prise débranchée du robot (les broches 1-2 sont sous tension même robot éteint), vérifier la polarité au multimètre, puis mesurer 5,0 V en sortie **avant** de relier la carte ; ne jamais brancher l'USB du PC tant que le fil VIN est en place (retirer ce fil d'abord ; les mises à jour passent de toute façon par /update en Wi-Fi) ; couper l'interrupteur quand le robot n'est pas sur sa base (sinon ~135 mA vident sa batterie de 1800 mAh en une douzaine d'heures). L'arrêt du moteur du LiDAR par sa broche PWM est documenté mais des utilisateurs le rapportent inopérant [A8] : PWM à la masse (régulation interne à 10 Hz) et, si l'on veut couper le LiDAR sans couper la carte, un second interrupteur ou un petit module MOSFET sur son 5 V.

Références Amazon.fr relevées le 2026-11-08 (prix à vérifier sur la fiche) : abaisseur moulé Yeeco 8-35 V → 5 V 3 A avec fils [A1], ou GYVRM 8-58 V → 5 V 3 A [A2] ; à défaut, lot de MP1584EN réglables 4,5-28 V [A3], à régler à 5,0 V au multimètre avant tout branchement ; interrupteur à bascule KCD1 deux broches avec fils [A4] ; kit LiDAR LDROBOT D500 à 79 € [A9]. Rien dans le kit ELEGOO ne remplace l'abaisseur (section 5).

### 2.2 Fixations

| Solution | Projet | Détail utile |
|---|---|---|
| Plaque sur entretoises | JetsonBot (2015, Create 2) [H20, H21] | écrous captifs, entretoises 5 cm, plaque plastique 6 mm ; le robot accepte des entretoises M3 dans ses bossages, « ne jamais percer le robot au hasard » [H1] |
| Blocs imprimés en 3D | nnarain 2021 [H10] | trois pièces, pieds dans des trous du capot, cavité pour la batterie |
| Plaque modulaire openGrid | nnarain 2026 [H11] | inserts filetés à chaud, cellules découpées autour du bouton et de la prise |
| Tout à l'intérieur | Roomba RPi (2021-22, **Roomba 690**) [H19, H26] | fils passés sous la carte mère, connecteur dans le trou de la prise OI, robot d'aspect d'origine |
| Un trou dans le capot | Old Roomba, new tricks [H8] | carte de 6 × 2 cm derrière la roue droite, cache par-dessus |

Dans tous les cas : laisser la prise Mini-DIN accessible, garder le robot assez bas et léger pour qu'il monte sur sa base (un robot alourdi a nécessité une entaille dans la base [H15]).

### 2.3 Capteurs ajoutés (prix relevés 2025-2026)

| Capteur | Prix | Alimentation | Lisible par l'ESP32 ? |
|---|---|---|---|
| LiDAR LDROBOT LD19 / kit D500 | 65 à 105 € [H28, M4], 79 € sur Amazon.fr [A9] | 5 V, 180 mA en rotation, 300 mA au lancement [A7], UART 230400 | oui (bibliothèque kaiaai/LDS) [H33] |
| LiDAR RPLIDAR C1 | 75 à 80 € [H28] | 5 V | oui |
| LiDAR RPLIDAR A1 | 105 à 150 € [H28 à H30] | 5 V, UART 115200 | oui ; le plus documenté sur Roomba (Perceptor, CMU) |
| LiDAR LD14P (kit D200) | 50 à 55 € [H28] | 5 V | oui |
| LiDAR YDLIDAR X2 | 62 € HT [H35] | 5 V | oui |
| LiDAR de récupération LDS02RR (Xiaomi/Roborock) | 15 à 35 € d'occasion [H36] | carte moteur externe | oui |
| Télémètre ultrason HC-SR04 (dans votre kit) | 2 € | 5 V, diviseur sur Echo | oui |
| Télémètre laser VL53L1X | 12 à 17 € | 3,3 V, I2C | oui |
| IMU MPU-6050 (déjà en place) | 0 € | 3,3 V | oui |
| Kinect, RealSense | occasion / cher | 12 V, USB 3 | non : PC x86 ou Jetson requis |

### 2.4 Autres améliorations vues

Manette DualShock 4 en Bluetooth (Roomba 690 + Pi [H19] ; côté ESP32, Bluepad32 + ArduRoomba [H40]) ; télé-présence avec tablette (2016, [H15]) ; mélodies jouées par l'OI (déjà fait ici) ; Boomba (mai 2026) qui ne garde que le châssis et les moteurs et remplace toute l'électronique par un Arduino UNO R4 WiFi, des ponts en H et 16 accus 18650 [H38] ; déclenchement de cycles de nettoyage supplémentaires depuis la domotique [H9].

### 2.5 Le Roomba comme base robotique

TurtleBot 1 (2011) était un Create + netbook + Kinect [H43] ; depuis : JetsonBot (Jetson TK1, 2015) [H20], Roomblock (Pi 2 + RPLIDAR A2, ROS 1, 2017) [H24], Roomba RPi (Pi Zero 2 W sur un **690**, ROS 2, RAM insuffisante pour compiler : Pi 4 requis) [H19], lubobot (Jetson Nano, ROS 2, actif en 2026) [H44], nnarain (Pi 5, 2026) [H11 à H13]. Le pilote ROS `create_robot` annonce la série 600 « supportée, non vérifiée » ; sa bibliothèque `libcreate` applique le même protocole que le Create 2 [H45, M9].

### 2.6 Classement pour l'objectif « cartographier et rendre autonome »

| Rang | Ajout | Coût | Difficulté | Pourquoi |
|---|---|---|---|---|
| 1 | Alimentation propre : abaisseur 5 V sur Vpwr (ou connecteurs et batterie bien fixés) | 3 à 10 € | facile | supprime les redémarrages ; condition de tout le reste |
| 2 | LiDAR 2D (LD19/D500 ou RPLIDAR C1) lu par l'ESP32, mesures envoyées en Wi-Fi au PC | 65 à 110 € | moyenne | seul capteur qui donne une vraie carte |
| 3 | Plaque supérieure sur entretoises M3, prise Mini-DIN libre | 10 à 20 € | facile | fixe LiDAR et carte, robot toujours dockable |
| 4 | Gyroscope déjà en place : fusion cap gyroscope + distance encodeurs | 0 € | moyenne | corrige la dérive de cap, validé ce soir à quelques degrés près |
| 5 | Raspberry Pi 4/5 + batterie 12 V + ROS 2 (create_robot, slam_toolbox, Nav2) | 120 à 180 € | difficile | navigation autonome sans PC ; plus tard |

## 3. Cartographier l'appartement : les trois voies

### 3.1 Odométrie seule (encodeurs + gyroscope) et carte « par contact »

- Nos chiffres sont confirmés par la spécification : 508,8 pas par tour, roue de 72 mm, soit 0,4446 mm par pas ; le paquet « distance » (19) est réputé inutilisable (l'équipe CMU 2020 a réécrit son odométrie à cause de « bugs du firmware » sur ces paquets) [M5, H1].
- Dérive attendue : sur Create 2, les encodeurs surestiment la distance de 6 à 11 % sur moquette (glissement), 2 % sur carrelage [M6] ; un autre projet mesure 7,3 % d'erreur sur 1 m [M7]. Le cap du MPU-6050 dérive surtout par biais : remettre le zéro à chaque arrêt est le geste le plus rentable. Notre observation de ce soir : gyroscope et encodeurs concordent à quelques degrés près sur les rotations sur place, les encodeurs surestiment les grandes rotations, le gyroscope est le bon juge du cap.
- L'exemple le plus proche de notre montage : **Old Roomba, new tricks** (632 + ESP8266 + MPU-6050) [M8] : un Raspberry Pi reçoit position et capteurs en MQTT et dessine la trajectoire ; les six « light bumpers » dessinent les murs ; la boucle est fermée en partant de la base et en y revenant, l'erreur angulaire finale (~11°) étant répartie sur le trajet. Résultat : plan reconnaissable des pièces, pas une carte métrique.
- Balayage d'un télémètre sur servo (Wall-SLAM : ESP32 + deux VL53L1X sur servo 180° + HC-SR04) [M10] : calcul déporté sur PC (« trop lourd pour le microcontrôleur »), portée ~4 m, un balayage à chaque arrêt, résultat grossier.

### 3.2 LiDAR 2D + SLAM : la seule qui donne une vraie carte

| Projet | Base | Matériel | Logiciel | Résultat |
|---|---|---|---|---|
| Perceptor (2025) [M11] | Roomba 650 | RPLIDAR A1, Pi 5 (d'abord Pi 3) | ROS 2 Jazzy, create_robot, slam_toolbox, Nav2 | cartes correctes, localisation ±5 cm ; fermeture de boucle jamais fiable ; Pi alimenté à part (200 mA du port) |
| CMU 18-500 (2020) [M5] | Create 2 | RPLIDAR A1, Pi 4, batterie USB 5 V/3 A | BreezySLAM (Python, sans ROS) | 96 % de surface juste dans une petite pièce, 86 % en chambre, couloir raté ; 516 $ au total |
| Roomblock (2017) [H24] | Roomba 500 à 800 | RPLIDAR A2, Pi 2 | ROS 1 | plateforme d'apprentissage |
| Open Simple Lidar [M12] | vieux Roomba | LiDAR maison, Orange Pi | Hector SLAM | carte de plusieurs pièces |

Sans ROS : BreezySLAM (Python, Linux ou macOS) [M13]. Avec ROS 2 : slam_toolbox est le standard (Cartographer et gmapping ont bloqué l'équipe CMU à l'installation). Difficulté moyenne à élevée (Linux, ROS 2).

**Point clé pour nous** : deux projets montrent qu'un **ESP32 suffit** à lire le LiDAR et à relayer scans et odométrie en Wi-Fi vers un PC qui fait le SLAM : le relais linorobot2 (LD19/LD06, « aucun ordinateur n'est requis sur le robot ») [M14] et la pile kaiaai / Maker's Pet (micro-ROS sur ESP32, SLAM et exploration sur PC) [M15, H33]. Le Raspberry Pi ne devient nécessaire que pour l'autonomie embarquée (naviguer sans PC allumé) ou une caméra.

### 3.3 Caméra : à oublier pour l'instant

Le seul montage Roomba + ESP32-CAM trouvé ne fait que du streaming vidéo, l'évitement venant d'un HC-SR04 [M16]. Le SLAM visuel (RTAB-Map, ORB-SLAM) exige au moins un Pi 4, qu'il sature [M17, M18]. Usage réaliste plus tard : une ESP32-CAM qui streame vers le PC pour repérer des marqueurs (ArUco) et recaler la position.

### 3.4 Sans capteur ajouté : grille d'occupation grossière sur l'ESP32

Les six light bumpers (paquets 46 à 51, « force » 0 à 4095, pas une distance, orientés de −64° à +40° avec un trou à droite [M19]), les pare-chocs et les capteurs de vide fournissent des points d'obstacle datés de la position odométrique. Faisable sur ESP32 : grille de 10 cm d'un appartement de 12 × 10 m = 12 000 cellules (12 Ko), cellules traversées marquées libres, point de contact marqué occupé ; exploration par suivi de mur (light bumper droit comme signal, pare-chocs comme confirmation). Qualité : contours de pièces reconnaissables, dérive de 5 à 10 % à annuler en revenant à la base. Suffisant pour visualiser, insuffisant pour naviguer.

### 3.5 Plan progressif

| Étape | Achat | Ce qu'on obtient |
|---|---|---|
| 1 — maintenant (~12 €) | abaisseur 5 V fixe + interrupteur + condensateur (section 2.1) ; ESP32 + MPU-6050 + encodeurs déjà en place | le firmware calcule et envoie la position (x, y, cap) avec les bits light bumper et pare-chocs 10 fois par seconde ; un script Python sur le PC trace trajectoire et contacts sur une grille de 10 cm ; départ et retour sur la base pour fermer la boucle. Résultat : plan grossier d'une pièce. |
| 2 — carte propre (~80 €) | kit LiDAR D500 (79 € [A9]) ou LDS02RR d'occasion ; alimenté par le robot via l'abaisseur de l'étape 1 (section 2.1) | l'ESP32 lit le LiDAR (kaiaai/LDS) et relaie vers le PC ; SLAM sur PC (BreezySLAM, ou slam_toolbox dans ROS 2 sous WSL2/Docker). Résultat : carte métrique de l'appartement, pilotage au téléphone. |
| 3 — autonomie (+70 à 120 €) | Raspberry Pi 4 ou 5, batterie 12 V + abaisseur 5 A | ROS 2 embarqué : create_robot, slam_toolbox puis Nav2 (±5 cm) et exploration automatique. |

## 4. Programmation : comment les autres programment leur Roomba

Méthode du volet : chaque dépôt ouvert (README, sources), dates vérifiées sur GitHub le 2026-11-08, spécification OI série 600 (révision 2018) relue. Rien d'exploitable en français : tout est anglophone.

### 4.1 Bibliothèques pour la liaison série (Open Interface)

| Ressource | Cible | Activité | Couverture | Verdict pour ESP32 + 694 |
|---|---|---|---|---|
| Roomba (Mike McCauley) [P1] | Arduino | 2010, miroir archivé 2021 | drive, LEDs, chansons, capteurs ; écrite pour les premiers Roomba | lisible, mais sans les paquets de la série 600 (35, 43/44) |
| **ArduRoomba v4** [P2] | Uno/Mega, ESP32, ESP8266 | 09/2026 | drive, capteurs de base, chansons, LEDs, page web (`/cmd`, `/status`), BLE ; pas de 148/149 | bon modèle de page web ; 690/694 « non testés » |
| MQTT-Roomba-ESP01 (The Hook Up) [P3] | ESP-01 | 2019 | 128/131/135/143, paquets 21/25/26 toutes les 5 s, BRC bas 1 s toutes les 60 s | code minimal, base de nombreux projets |
| esp-roomba-mqtt (johnboiles) [P4] | ESP8266 | 2020 | MQTT, OTA, telnet ; les 650 récents s'endorment sur base en ~1 min, BRC inefficace | squelette MQTT ; veille non résolue |
| **ESPRoomba (ShonP40)** [P5] | ESP32-C3, ESPHome | 12/2025 | 600/700/800 ; Query List 149 (14 paquets) toutes les 10 s ; réveil « lazy650 » ; horloge ; activité déduite du courant | le plus récent et le plus proche de notre cas : à lire en premier |
| ESPHomeRoombaComponent [P6, P7] | ESP8266/ESP32 | 2020-2022, suite en cours | bug « pas de réveil BRC en charge d'entretien », contournement par LED IR ; flux 148 relancé après 3/7/15 s de silence | idées de réveil et de resynchronisation |
| **libcreate (AutonomyLab)** [P8] | C++ (socle ROS) | 2023-2025 | protocole V_3 = Create 2 et 600-800 ; contournement du mode +1 ; compteurs de paquets corrompus | référence propre du flux 148 |
| pycreate2 ; **PyRoombaAdapter** [P9, P10] | Python 3 | 2020 ; 2024 | drive_direct, 49 champs capteurs, chansons ; PyRoombaAdapter « testé uniquement sur Roomba 690 » | côté PC, le plus pertinent |
| create2, create-oi (Node) ; barredora, CleanIt (Rust) [P11 à P14] | Node ; Rust | 2016-2018 ; 2025-2026 | peu maintenus ; CleanIt = pile d'autonomie Rust (Pi 4 + RealSense) | curiosités |

### 4.2 ROS et ROS 2

`create_robot` + `libcreate` : publiés pour ROS 2 Humble (3.1.0, 2023), Foxy, Noetic ; pas de version Jazzy publiée. Série 600 « prise en charge, non vérifiée ». Fournit l'odométrie (encodeurs), pare-chocs, vide, batterie, LEDs, son, téléopération manette, commande en vitesse. [P8, P15]

**L'issue #64 de create_robot est exactement notre « mode OI lu +1 »** : sur 642, 675, 690 et 694 (firmwares 3.2.47 et 3.5.62), le paquet 35 renvoie mode + 1, confirmé à l'analyseur logique ; contournement `oi_mode_workaround` dans libcreate 3.0.0. iRobot a répondu (2022) ne pas prendre en charge l'OI sur ses robots Wi-Fi. [P16]

Matériel ROS : Raspberry Pi 4/5 sous Ubuntu 22.04 + Humble ; le projet roomba-rpi (690 + Pi Zero 2 W + IMU) a dû compiler sur un Pi 4 et a été mis de côté [P17]. Coût d'entrée pour un débutant : élevé (Linux, colcon, concepts ROS) : à garder pour l'étape 3 du plan.

### 4.3 L'interface Wi-Fi locale du 694 (celle de l'application iRobot)

| Outil | Langage | Activité | Ce qu'il fait |
|---|---|---|---|
| dorita980 [P18] | Node | 02/2026 | 600 (675, 690), 800, 900, e/i/j ; start / stop / pause / dock / find, état du robot, mission, préférences, programmation hebdomadaire |
| rest980 [P19] | Node | 03/2026 | API REST au-dessus de dorita980 |
| roombapy [P20] | Python | 11/2026 | socle de l'intégration Home Assistant |
| Roomba980-Python [P21] | Python | 2024 | 600/900/i/s |
| Home Assistant (officiel) ; ha_roomba_plus [P22, P23] | Python | 2026 | 690 « devrait fonctionner » ; batterie, bac, missions |
| roomba-bridge-esphome [P24] | ESP32 | archivé 2025 | preuve qu'un ESP32 peut parler au MQTT local du robot |

Protocole : MQTT/TLS sur le port 8883 ; mot de passe lu localement, robot sur la base, bouton HOME ~2 s ; une seule connexion locale à la fois (l'application passe alors par le cloud) ; cette méthode « cesse de fonctionner sur les derniers firmwares ». On lit la batterie, le bac, l'état de mission ; **aucune conduite des roues** : seule la liaison série le permet. Contexte 2025-2026 : iRobot en chapitre 11 le 14/12/2025, repris par Picea, continuité de l'application annoncée [P25]. Voir aussi la note [D_wifi_local.md](D_wifi_local.md).

### 4.4 Pièges de l'OI rapportés par les autres, recoupés avec notre 694

| Piège | Spécification (2018) et retours de développeurs | Notre 694 |
|---|---|---|
| Veille | Passive : veille après 5 min hors base ; « pour désactiver la veille, passer en Safe ou Full » ; sur base, impulsion BRC ; bug « Dock wakeup BRC pulse » corrigé dans un firmware 3.8.2 | BRC capricieux : cohérent |
| Réveil | The Hook Up : BRC bas 1 s toutes les 60 s ; crc.id.au : plus d'une impulsion par minute ; ESPRoomba : BRC en haute impédance, impulsion basse 200 ms puis Start (128), toutes les 50 s, puis Clean + Dock si sur base | anti-veille passé de 60 à 45 s ; séquence ESPRoomba à essayer |
| Paquets 19/20 | annexe B de la spécification : 19 « valeur incorrecte » (corrigé en 3.3.0), 20 corrigé en 3.4.1 ; lire 43/44 (508,8 impulsions par tour, roue de 72 mm, débordement 16 bits) | confirme : abandonner 19, encodeurs seuls |
| Paquet 35 (+1) | create_robot #64 : 642/675/690/694 | identique |
| Flux 148 | 150 met en pause ou reprend « sans effacer la liste » : le flux vit dans le robot et survit à un redémarrage de la carte ; 172 octets maximum par trame | pause (150, 0) au démarrage : fait |
| Débit | 148 toutes les 15 ms ; 142/149 pas plus d'une fois toutes les 15 ms | nos 20 ms entre requêtes : cohérent |
| Octets parasites | bannière ASCII au reset du robot ; messages au réveil (« key-wakeup », « slept for… ») vus à l'oscilloscope ; bip au Start | explique le `B0` après réveil : purger, filtrer |
| Full | supprime vide/roues/chargeur ; la charge s'arrête ; décharge profonde | rester en Passive/Safe (règle du projet) |

### 4.5 Réalisations qui donnent des idées

Alexa par émulation Wemo sur ESP8266 (2021) [P26] ; pilotage web + caméra avec un XIAO ESP32-S3 Sense (2025) [P27, P28] ; 690 + Pi + IMU + ROS 2 (roomba-rpi) [P17] ; suivi de ligne avec les capteurs de vide (cours Rose-Hulman) [P29] ; Hector SLAM + LiDAR sur un vieux Roomba (section 3) ; Vroomba à 60 km/h stabilisé par gyroscope (2024) [P30].

### 4.6 Recommandations du volet

À lire en priorité : l'annexe B de la spécification OI 600, l'issue #64 de create_robot, `Roomba.h` d'ESPRoomba, PyRoombaAdapter, la page web d'ArduRoomba v4. Trois fonctions à ajouter à notre firmware : (1) odométrie par encodeurs fusionnée au cap du gyroscope, tracé (x, y, cap) dans la page ; (2) réveil et resynchronisation robustes (séquence ESPRoomba, purge et pause du flux au démarrage, affichage de la bannière firmware) ; (3) estimation d'activité à partir du courant et de l'état de charge, publiée en MQTT pour Home Assistant.

## 5. Vos modules : lesquels servent le projet

Contenu confirmé le 2026-11-08 par la fiche du kit (Mega 2560 R3 ; LCD1602, lecteur RFID RC522, DHT11, détecteur de mouvement PIR HC-SR501, télémètre ultrason, capteur de niveau d'eau, GY-521, pilote de LED MAX7219, clavier 16 touches, joystick, encodeur rotatif, module relais, servo SG90, moteur pas à pas, moteur à courant continu, plaque d'essai, fils, LED, résistances, condensateurs, circuits intégrés, horloge temps réel). Les lignes « si présent » concernent des modules habituels de ce kit que la fiche ne cite pas.

| Module | Utile ? | Usage pour le Roomba |
|---|---|---|
| GY-521 (MPU-6050) | **oui, en place** | cap du robot, validé ce soir ; à éloigner de la brosse principale si on ajoute un magnétomètre un jour |
| HC-SR04 (ultrason) + servo SG90 | oui, étape « 1 bis » | télémètre balayé à l'arrêt (portée 0,02 à 4 m, cône large) pour voir les murs à distance en attendant le LiDAR ; résultat grossier mais instructif ; 5 V depuis le rail de l'abaisseur (le servo tire 100 à 250 mA en mouvement : pas en même temps que le LiDAR), diviseur 1 kΩ / 2 kΩ sur Echo |
| Résistances, condensateurs | oui | 1 kΩ en série sur la liaison (en place) ; diviseur sur l'Echo du HC-SR04 ; condensateurs électrolytiques en parallèle sur le rail 5 V (section 2.1) |
| Écran LCD 1602 | oui, confort | état de la carte sans téléphone : adresse IP, tension, mode, dernière erreur ; version sans I2C : six broches de l'ESP32, logique 5 V à adapter |
| Matrice LED MAX7219 | confort | « visage » ou état du robot en trois fils SPI ; logique 5 V, fonctionne en général avec des signaux 3,3 V |
| DHT11 (température, humidité) | oui, original | carte de température et d'humidité de l'appartement pendant que le robot roule (une mesure par position) |
| Récepteur infrarouge + télécommande (si présent) | oui, amusant | piloter le robot avec la télécommande du kit, décodée par l'ESP32 (le robot a aussi son propre récepteur IR, voir note E) |
| Buzzer (si présent) | oui, trivial | bip de la carte au démarrage, à la perte de liaison, au pare-chocs |
| Photorésistance (si présent) | oui, simple | carte de luminosité, détection d'une pièce éteinte |
| Détecteur de mouvement PIR HC-SR501 | gadget | mettre le robot en pause quand quelqu'un bouge dans la pièce ; 5 V, portée 7 m |
| RFID RC522 | gadget | portée 2 à 3 cm : étiquettes collées au sol au pas des portes et lecteur sous le robot pour savoir dans quelle pièce il est ; pas une localisation |
| Horloge temps réel | peut-être | horodatage des mesures sans Wi-Fi ; en Wi-Fi l'heure vient du réseau |
| Joystick, clavier 16 touches, encodeur rotatif | non | le téléphone fait déjà mieux |
| Arduino Mega 2560 | non pour le robot | l'ESP32 fait tout ; garder le Mega pour essayer un module à part sur le PC |
| Relais | non | couper le LiDAR serait possible mais la bobine consomme 70 mA : préférer un petit module MOSFET |
| Capteur de niveau d'eau, moteur pas à pas, moteur CC, L293D, afficheurs 7 segments | non | sans objet pour le robot |
| Module d'alimentation de plaque d'essai (si présent) | **non, danger** | entrée 6,5 à 12 V, régulateur linéaire : la batterie du robot (14 à 21 V) le détruirait |

À acheter, option sans batterie portable (décision du 2026-11-08) : 1) un abaisseur 5 V fixe moulé 8-35 V → 5 V 3 A [A1] (ou GYVRM [A2]), un interrupteur à bascule [A4] et, si le kit n'a pas de condensateurs de 100 µF ou plus, un 1000 µF 16 V : une douzaine d'euros en tout ; 2) le kit LiDAR LDROBOT D500 (79 € [A9]) ; 3) une plaque et des entretoises M3 ; beaucoup plus tard un Raspberry Pi 4 ou 5.

## 6. Ce que cela change pour notre firmware

1. **Odométrie dans la carte** : intégrer x, y, cap à partir des encodeurs (16 bits signés, différence modulo 65 536) et du gyroscope, exposer `/api/pose` et une ligne CSV ; sur le PC, un script qui trace la trajectoire et les contacts (étape 1 du plan).
2. **Grille d'occupation** simple sur l'ESP32 (section 3.4) et affichage dans la page web.
3. **Préparer le LiDAR** : la liaison robot occupe UART2 (GPIO16/17) ; un LiDAR LD19 se branche sur UART1 (par exemple GPIO25/26) à 230 400 bauds, lu par kaiaai/LDS, et ses scans partent en UDP vers le PC. Son 5 V vient du rail de l'abaisseur, sa broche PWM va à la masse (section 2.1).
4. **Robustesse déjà ajoutée ce soir** : pause du flux 148, arrêt des roues au démarrage, raison du redémarrage ; reste à alimenter proprement la carte.

## Sources

Volet matériel (H) : H1 https://cdn.hackaday.io/files/1835247851890816/2021-04-13_iRobot_Roomba_600_Open_Interface_Spec-3.pdf · H2 https://www.adafruit.com/product/2438 · H3 https://www.servomagazine.com/magazine/article/irobot-create2-raspberry-pi-picreate · H4 https://hackaday.io/project/8290-esp8266-controlled-roomba · H5 https://myhomethings.eu/en/roomba-voice-control-alexa-and-belkin-wemo-emulator/ · H6 https://hackaday.com/2021/03/09/roomba-gets-alexa-support-with-an-esp8266-stowaway · H7 https://hackaday.io/project/183524-old-roomba-new-tricks · H8 https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202540-add-hardware · H9 https://www.thesmarthomehookup.com/?p=377 · H10 https://nnarain.github.io/2021/02/14/iRobot-Create-2-Mounting-a-Raspberry-Pi.html · H11 https://nnarain.github.io/2026/01/13/iRobot-Create-2-openGrid-baseplate.html · H12 https://nnarain.github.io/2026/02/02/iRobot-Create-2-Battery-Mounting-Solution.html · H13 https://nnarain.github.io/2026/02/15/iRobot-Create-2-Mounting-and-Powering-Pi.html · H15 https://hackaday.io/project/18005-raspberry-pi-teleprescence-v1 · H16 https://forum.mysensors.org/post/53041 · H17 https://github.com/brembygit/ESPHomeRoombaComponent · H18 https://community.smartthings.com/t/deprecated-thinking-cleaner-2-x-roomba-control/65671?page=3 · H19 https://hackaday.io/project/178565-roomba-rpi · H20 https://jetsonhacks.com/2015/06/15/jetson-tk1-create-2-robot-part-i/ · H21 https://jetsonhacks.com/2015/07/11/jetsonbot-part-ii-a-vision-robot-with-a-create-2-base/ · H24 https://github.com/7675t/roomblock · H26 https://hackaday.io/project/178565-roomba-rpi/discussion-178856 · H28 https://www.waveshare.com/product/modules/sensors/light-ranging.htm?mode=grid · H29 https://robot-italy.com/en/products/4010-slamtec-rplidar-a1-360-laser-range-scanner · H30 https://www.waveshare.com/wiki/RPLIDAR_A1 · H33 https://github.com/kaiaai/LDS · H35 https://exp-tech.de/en/products/x2 · H36 https://github.com/kaiaai/awesome-2d-lidars · H38 https://blog.arduino.cc/2026/05/05/boomba-is-a-roomba-with-every-upgrade-imaginable/ · H40 https://github.com/pkyanam/ArduRoomba · H43 https://en.wikipedia.org/wiki/TurtleBot · H44 https://github.com/apojomovsky/lubobot · H45 https://github.com/AutonomyLab/create_robot

Volet cartographie (M) : M1 https://homesupport.irobot.com/articles/en_US/Knowledge/53000 · M2 https://support.irobot.de/articles/en_US/Knowledge/19531 · M3 https://www.bestcordlessvacuumguide.com/roomba-694-review/ · M4 https://sensorlidar.com/products/ldrobot-ld06-ld19-d300-of-laser-radar-lidar-scanner-360-scanning-d500-lidar-kit-support-ros1-and-ros2-for-indoor-and-outdoor · M5 http://course.ece.cmu.edu/~ece500/projects/s20-teamb2/wp-content/uploads/sites/84/2020/05/Team_B2.pdf · M6 https://kendell.dev/blog/roombamotors · M7 https://hackaday.io/project/203547/logs?sort=oldest · M8 https://hackaday.io/project/183524-old-roomba-new-tricks · M9 https://github.com/AutonomyLab/libcreate · M10 https://github.com/kreslotim/Wall-SLAM · M11 https://hackaday.io/project/203547-perceptor-ros2-autonomous-mapping-navigation · M12 https://hackaday.io/project/20628-open-simple-lidar/log/67460-testing-lidar-with-ros · M13 https://github.com/simondlevy/BreezySLAM · M14 https://github.com/hippo5329/linorobot2_hardware/wiki · M15 https://discourse.openrobotics.org/t/fyi-10-low-cost-lidar-lds-interfaced-to-ros2-micro-ros-arduino/36369 · M16 https://structables.lunar.icu/How-to-Make-an-Autonomous-Robot-for-Under-30 · M17 https://dev.to/admantium/ros-simultaneous-mapping-and-localization-with-rtabmap-2o09 · M18 https://community.husarion.com/t/onboard-rgb-d-slam-not-feasible-on-rosbot-2r-due-to-raspberry-pi-4-cpu-load/2161 · M19 https://kendell.dev/milliblog/lightbumper · Prix Raspberry Pi : https://www.raspberrypi.com/products/raspberry-pi-4-model-b/ et https://www.blog-nouvelles-technologies.fr/350916/raspberry-pi-5-modele-1-go-52-euros/

Achats et alimentation (A, relevés le 2026-11-08) : A1 https://www.amazon.fr/Yeeco-Etanche-Converter-Dalimentation-R%C3%A9gulateur/dp/B015B5XQWW · A2 https://www.amazon.fr/Convertisseur-Dalimentation-Abaisseur-Voiture-Ventilateur/dp/B0DGFZ3RN2 · A3 https://www.amazon.fr/MP1584EN-Convertisseurs-Abaisseur-Tension-R%C3%A9glable/dp/B0FDQ759MP · A4 https://www.amazon.fr/Interrupteur-Bascule-Broches-Couvercle-%C3%A9tanche/dp/B0BM95Q68T · A5 https://esp32.com/viewtopic.php?p=12510 · A6 https://community.hubble.com/guides/esp32-power-consumption-datasheet-vs-reality · A7 https://botland.com.pl/img/art/inne/21991_Karta%20katalogowa.pdf et https://waveshare.com/wiki/DTOF_LIDAR_LD19 · A8 https://forum.youyeetoo.com/t/ld19-external-speed-control/329 · A9 https://www.amazon.fr/LDROBOT-Outdoor-Navigation-Scanning-Support/dp/B0DDKXQ23R · Spécification OI 600 (fusible 200 mA, 500 mA crête) : H1 et https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf

Volet programmation (P) : P1 https://github.com/Apocrathia/Roomba · P2 https://github.com/pkyanam/ArduRoomba · P3 https://github.com/thehookup/MQTT-Roomba-ESP01 · P4 https://github.com/johnboiles/esp-roomba-mqtt · P5 https://github.com/ShonP40/ESPRoomba · P6 https://github.com/brembygit/ESPHomeRoombaComponent · P7 https://retsamedoc.github.io/esphome-components/roomba/ · P8 https://github.com/AutonomyLab/libcreate · P9 https://pypi.org/project/pycreate2/ · P10 https://github.com/AtsushiSakai/PyRoombaAdapter · P11 https://www.npmjs.com/package/create2 · P12 https://github.com/drzaiusx11/create-oi · P13 https://crates.io/api/v1/crates/barredora · P14 https://github.com/Sollimann/CleanIt · P15 https://index.ros.org/r/create_robot/ · P16 https://github.com/AutonomyLab/create_robot/issues/64 · P17 https://github.com/process1183/roomba-rpi · P18 https://github.com/koalazak/dorita980 · P19 https://github.com/koalazak/rest980 · P20 https://github.com/pschmitt/roombapy · P21 https://github.com/NickWaterton/Roomba980-Python · P22 https://www.home-assistant.io/integrations/roomba/ · P23 https://github.com/johnnyh1975/ha_roomba_plus · P24 https://github.com/solarkennedy/roomba-bridge-esphome · P25 https://www.manufacturingdive.com/news/roomba-braava-maker-irobot-chapter-11-bankruptcy-acquisition-picea-china/807997/ · P26 https://hackaday.com/2021/03/09/roomba-gets-alexa-support-with-an-esp8266-stowaway/ · P27 https://circuitdigest.com/news/hacking-roomba-turn-your-vacuum-into-a-web-controlled-robot-with-esp32 · P28 https://github.com/meech-ward/roomba · P29 https://www.rose-hulman.edu/class/cs/archive/csse120-old/csse120-old-terms/200920robotics/Homework/hw12.html · P30 https://hackaday.com/2024/01/15/vroomba-gets-upgrades-and-a-spoiler/ · Pièges terrain : https://www.crc.id.au/hacking-the-roomba-600/ et https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202538-interfacing
