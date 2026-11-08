# Journal des tests — ESP32 ↔ Roomba 694 (sketch `roomba694_test1`)

Session locale du 2026-11-08 (après-midi et soirée) sur l'ordinateur Windows relié à l'ESP32. Branche `claude/eager-ride-crj3f0`, clone local `C:\Users\hugue\romba`. Les étapes suivent le plan de [PROMPT_session_locale.md](PROMPT_session_locale.md).

## Résumé

- Compilation du sketch du premier coup, sans erreur ni avertissement ; téléversement et test à vide sans problème.
- Premier essai sur le robot : aucune réponse. Cause trouvée avec une variante diagnostic du sketch ([roomba694_diag/](roomba694_diag/), touche `n`) : côté robot, deux pions n'étaient pas dans les bons trous. Après recâblage par l'utilisateur, **la liaison fonctionne**.
- Une seule correction au sketch : une pause de 20 ms avant chaque requête capteur. Sans elle, une requête sur deux restait sans réponse sur ce robot.
- Mesures lues par l'OI : 15 580 mV, -127 mA, 17 à 19 °C, 1853 / 2068 mAh, état de charge 0, mode OI lu 2 en Passive et 3 en Safe (décalage de +1 confirmé sur ce 694).
- Déplacements : voir la section 5 (en attente de l'accord de l'utilisateur au moment où ces lignes sont écrites).

## Environnement

| Élément | Valeur relevée |
|---|---|
| Système | Microsoft Windows 11 Pro, version 10.0.26200 |
| arduino-cli | 1.5.1 (commit 01f3d4f2b), installé dans `C:\Program Files\Arduino CLI`, présent dans le PATH |
| Paquet de cartes | `esp32:esp32` **3.3.7** (3.3.10 disponible, pas mis à jour : rien n'a été installé ni modifié) |
| esptool | v5.1.0 (fourni par le paquet esp32) |
| IDE Arduino | 2.3.8 installé, non utilisé (tout est fait avec arduino-cli) |
| Carte | ESP32 DevKit 30 broches, puce ESP32-D0WD-V3 (révision v3.1), quartz 40 MHz, flash en mode DIO |
| Pont USB-série | Silicon Labs CP210x, pilote 11.3.0.176 (Silicon Laboratories, 2023-04-12), installé automatiquement par Windows au premier branchement |
| Port | **COM4** (`\Device\Silabser0`) |
| FQBN | `esp32:esp32:esp32` (« ESP32 Dev Module », réglages par défaut) |
| git | 2.54.0.windows.1 |

Avant le branchement de la carte, `arduino-cli board list` ne voyait aucun port ; après le branchement, Windows a installé le pilote seul et le port COM4 est apparu.

## 1. Compilation — OK, aucune correction nécessaire

Commande, depuis la racine du dépôt :

```
arduino-cli compile --fqbn esp32:esp32:esp32 --warnings default roomba694_recherche/code/roomba694_test1
```

Résultat (première compilation, cache vide : environ 1 min 30) :

```
Sketch uses 287308 bytes (21%) of program storage space. Maximum is 1310720 bytes.
Global variables use 22084 bytes (6%) of dynamic memory, leaving 305596 bytes for local variables. Maximum is 327680 bytes.
```

Aucune erreur, aucun avertissement. Le sketch écrit « à l'aveugle » par la session cloud compile tel quel avec la vraie chaîne ESP32.

## 2. Téléversement — OK

```
arduino-cli upload -p COM4 --fqbn esp32:esp32:esp32 roomba694_recherche/code/roomba694_test1
```

Extrait de la sortie d'esptool (la connexion s'est faite seule, sans tenir le bouton BOOT) :

```
esptool v5.1.0
Serial port COM4:
Connecting....
Connected to ESP32 on COM4:
Chip type:          ESP32-D0WD-V3 (revision v3.1)
Features:           Wi-Fi, BT, Dual Core + LP Core, 240MHz, Vref calibration in eFuse, Coding Scheme None
Crystal frequency:  40MHz
Changing baud rate to 921600...
Wrote 25024 bytes (16034 compressed) at 0x00001000 in 0.7 seconds (294.8 kbit/s).
Wrote 3072 bytes (146 compressed) at 0x00008000 in 0.1 seconds (328.0 kbit/s).
Wrote 8192 bytes (47 compressed) at 0x0000e000 in 0.1 seconds (464.7 kbit/s).
Wrote 287456 bytes (158545 compressed) at 0x00010000 in 3.1 seconds (730.3 kbit/s).
Hash of data verified.
Hard resetting via RTS pin...
```

## 3. Test à vide — OK

Le moniteur n'a pas été ouvert à la main : la sortie série est lue par le script [outils/serial_console.ps1](outils/serial_console.ps1), qui ouvre COM4 à 115200 bauds, fait au besoin un reset matériel de la carte par la ligne RTS (l'équivalent d'un appui sur EN), lit ce que la carte envoie, puis envoie les touches demandées une par une, chacune suivie d'Entrée.

```
powershell -ExecutionPolicy Bypass -File roomba694_recherche/code/outils/serial_console.ps1 -Port COM4 -Reset -Commands '?' -InitialWait 4 -WaitAfter 2
```

Sortie copiée telle quelle (les premières lignes sont celles du chargeur d'amorçage de l'ESP32, normales à chaque reset) :

```
ets Jul 29 2019 12:21:46

rst:0x1 (POWERON_RESET),boot:0x13 (SPI_FAST_FLASH_BOOT)
configsip: 0, SPIWP:0xee
clk_drv:0x00,q_drv:0x00,d_drv:0x00,cs0_drv:0x00,hd_drv:0x00,wp_drv:0x00
mode:DIO, clock div:1
load:0x3fff0030,len:4876
ho 0 tail 12 room 4
load:0x40078000,len:16560
load:0x40080400,len:3500
entry 0x400805b4

=== Roomba 694 — test OI v1 ===
 ?  aide                         w  impulsion BRC (réveil)
 s  Start -> Passive             f  Safe (contrôle, sécurités actives)
 c  Clean                        h  retour à la base
 b  batterie / mode OI           e  pare-chocs, vide, boutons
 m  jouer 3 notes (Safe)         l  LEDs (Safe)
 8  avance   2  recule   4  tourne à gauche   6  tourne à droite   5 ou espace  stop
    (chaque ordre dure 1,5 s puis les roues s'arrêtent seules)
 a  anti-veille BRC toutes les 60 s (on/off)
 o  Power (extinction)           x  Stop OI (à faire en fin de session)

Séquence conseillée : w, s, b  (la tension lue doit être proche de 14,66 V).

---- envoi : '?' ----
(l'aide ci-dessus s'affiche une seconde fois)
```

Les accents sortent correctement (UTF-8 des deux côtés). Remarque après coup : on a cru faire ce test « carte seule », mais les quatre fils étaient déjà en place côté robot, robot endormi. Cela n'a rien changé : la carte a fonctionné normalement.

## 4. Câblage et diagnostic

### 4.1 Premier état : aucune réponse

Câblage réalisé par l'utilisateur avant la session, d'après les photos du dépôt ; côté carte : fil marron (prolongé par un raccord vers un fil jaune côté robot) sur GND, blanc sur D4, vert sur RX2, violet sur TX2. Robot au sol, hors de sa base, endormi.

- `w`, `s`, `b` (deux essais, le second avec 4 s entre chaque touche) : « Pas de réponse du robot ».
- Appui bref sur CLEAN par l'utilisateur (le robot se réveille), puis `s`, `b`, `e` : toujours « Pas de réponse ».

### 4.2 Variante diagnostic `roomba694_diag`

Pour savoir ce que touche chaque fil sans multimètre, une copie du sketch a reçu trois touches :

- `r` : écho brut, affiche en hexadécimal tout octet venant du robot ;
- `n` : **test de continuité** des trois fils de signal. Chaque broche est lue avec le rappel interne de l'ESP32 (environ 45 kΩ) vers le haut, puis vers le bas, puis sans rappel juste après le rappel bas. Une broche reliée au robot garde le niveau que le robot impose ; une broche en l'air suit le rappel et reste à 0 sans rappel ; une broche reliée à travers une forte résistance suit le rappel mais remonte à 1 sans rappel. TX2 est rendue à l'UART après le test ;
- `9` : bascule 115200 / 19200 bauds (non utilisée).

Dans cette variante, BRC (D4) est piloté en collecteur ouvert (entrée au repos, tirée à la masse pendant l'impulsion), pour ne jamais pousser de courant dans un fil mal placé.

Résultats avec le premier câblage, robot réveillé ou non (identiques pendant plus d'une minute) :

| Fil | Rappel haut | Rappel bas | Lecture |
|---|---|---|---|
| RX2 (vert, trou 4 visé) | 0/400 | 0/400 | tenu à 0 V |
| TX2 (violet, trou 3 visé) | 400/400 | 400/400 | tenu haut par le robot |
| D4 (blanc, trou 5 visé) | 0/400 | 0/400 | tenu à 0 V |

Deux fils sur un point à 0 V alors qu'il n'y a que deux trous de masse, dont un déjà occupé par le fil jaune : au moins un pion n'était pas dans le bon trou (masse ou bague métallique de la prise). Avec le recul, le violet était très probablement sur le trou 4 (TXD à 3,3 V, « tenu haut »), ce qui explique que le robot n'ait jamais reçu les ordres.

Pendant cette période, la carte a poussé 3,3 V (D4 en sortie haute) dans un fil à 0 V, soit un petit court-circuit permanent d'environ 40 minutes sur GPIO4. La carte n'en a pas souffert (tous les tests suivants sont normaux), mais c'est une raison de plus de vérifier le câblage carte débranchée.

### 4.3 Recâblage

L'utilisateur a débranché l'USB, retiré les quatre pions et les a replacés droits, en prenant pour repère les deux trous où il avait mesuré la tension batterie (1 et 2) : jaune dans 6, vert dans 4, violet dans 3, blanc dans 5. Robot réveillé, USB rebranché. Résultat de `n` (deux passages identiques) :

| Fil | Rappel haut | Rappel bas | Sans rappel | Lecture |
|---|---|---|---|---|
| RX2 (vert, trou 4) | 400/400 | 400/400 | 400/400 | tenu à 3,3 V par le robot : TXD, robot réveillé |
| TX2 (violet, trou 3) | 400/400 | 0/400 | 400/400 | relié à travers un rappel faible |
| D4 (blanc, trou 5) | 400/400 | 0/400 | 400/400 | relié à travers un rappel faible |

Enseignement : les rappels vers 5 V du robot sur RXD (trou 3) et BRC (trou 5) sont **faibles** (plus de 30 kΩ environ), puisque le rappel interne de l'ESP32 vers le bas suffit à les faire lire « bas ». Un simple test « haut/bas » les aurait déclarés en l'air ; la troisième mesure sans rappel lève le doute.

Puis `s` et `b` : **première réponse du robot**.

```
---- envoi : 's' ----
Envoyé : Start (128) -> Passive

---- envoi : 'b' ----
Tension batterie : 15580 mV   (multimètre sur Vpwr : 14,66 V)
Température : 19 °C
État de charge : 0   (0 pas en charge, 1 reconditionnement, 2 pleine, 3 entretien, 4 attente, 5 défaut)
```

Il manquait le courant, la charge et le mode OI : une requête capteur sur deux restait sans réponse (voir la correction ci-dessous).

## 5. Validation de la liaison (sketch `roomba694_test1` corrigé)

Après ajout de la pause de 20 ms et retéléversement du sketch officiel :

```
---- envoi : 's' ----
Envoyé : Start (128) -> Passive

---- envoi : 'b' ----
Tension batterie : 15580 mV   (multimètre sur Vpwr : 14,66 V)
Courant : -127 mA   (négatif = décharge)
Température : 17 °C
Charge : 1853 / 2068 mAh
État de charge : 0   (0 pas en charge, 1 reconditionnement, 2 pleine, 3 entretien, 4 attente, 5 défaut)
Mode OI lu : 2   (0 Off, 1 Passive, 2 Safe, 3 Full ; sur 690/694 la valeur est souvent décalée de +1)

---- envoi : 'e' ----
Pare-chocs : droit 0, gauche 0 | Roue levée : droite 0, gauche 0
Vide (cliff) : gauche 0 avant gauche 0 avant droit 0 droit 0
Light bumper (G, AvG, CG, CD, AvD, D) : 0 0 0 0 0 0
Boutons : CLEAN 0, SPOT 0, DOCK 0
```

Puis mode Safe, chanson, LEDs, batterie, retour en Passive :

```
---- envoi : 'f' ----
Envoyé : Safe (131)

---- envoi : 'm' ----
Chanson envoyée (mode Safe requis : 'f' d'abord).

---- envoi : 'l' ----
LEDs envoyées (mode Safe requis).

---- envoi : 'b' ----
Tension batterie : 15552 mV   (multimètre sur Vpwr : 14,66 V)
Courant : -151 mA   (négatif = décharge)
Température : 19 °C
Charge : 1851 / 2068 mAh
État de charge : 0   (0 pas en charge, 1 reconditionnement, 2 pleine, 3 entretien, 4 attente, 5 défaut)
Mode OI lu : 3   (0 Off, 1 Passive, 2 Safe, 3 Full ; sur 690/694 la valeur est souvent décalée de +1)

---- envoi : 's' ----
Envoyé : Start (128) -> Passive
```

Lecture : mode OI 2 en Passive puis 3 en Safe, soit le décalage de +1 décrit dans le rapport, confirmé sur ce robot. Notes entendues et LEDs vues : à confirmer par l'utilisateur (non observables depuis le PC).

- Déplacements (`8`, `2`, `4`, `6`) : **en attente de l'accord explicite de l'utilisateur** au moment où ces lignes sont écrites.
- Réveil par BRC (`w`) : pas encore évalué avec le bon câblage (les deux essais de la section 4.1 ont eu lieu avec BRC mal relié). À tester quand le robot se sera rendormi.
- Fin de session (`s` puis `x`) : à faire.

## Problèmes rencontrés et corrections

1. **Câblage côté robot** (section 4) : résolu par recâblage ; outil de diagnostic conservé dans `roomba694_diag/`.
2. **Une requête capteur sur deux sans réponse** : la spécification OI demande au moins 15 ms entre deux requêtes de capteurs, le sketch les enchaînait sans pause. Correction a minima dans `readSensor()` des deux sketches : `delay(20);` avant la requête. Après correction, toutes les requêtes répondent.
3. **Tension lue 15,58 V contre 14,66 V au multimètre le matin** : écart de 0,9 V, cohérent avec une recharge du robot entre les deux mesures ; à confirmer par l'utilisateur. Le courant négatif et l'état de charge 0 sont cohérents avec un robot hors de sa base.
4. Les trois lignes de signal ne portent aucune résistance série de 1 kΩ (conseillée dans le README, facultative) : fonctionne tel quel.

## Outils

- [outils/serial_console.ps1](outils/serial_console.ps1) : console série non interactive (PowerShell 5.1, `System.IO.Ports.SerialPort`). Options : `-Port COMx`, `-Reset` (reset de la carte par RTS), `-Commands 'w','s','b'`, `-InitialWait` et `-WaitAfter` en secondes. Toute la sortie de cette session a été capturée avec lui.
- [roomba694_diag/](roomba694_diag/) : variante diagnostic du sketch (touches `r`, `n`, `9`, BRC en collecteur ouvert), compilée et testée ce jour.

## Rappel de fin de session

Toujours finir par `s` puis `x` (en Safe/Full le robot ne se recharge pas et ne dort jamais), puis débrancher l'USB. Ne jamais relier les broches 1-2 du robot ni VIN/3V3/5V de la carte dans ce test.
