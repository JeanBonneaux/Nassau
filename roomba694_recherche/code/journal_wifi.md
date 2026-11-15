# Journal des tests — `roomba694_wifi` (console et page web par Wi-Fi, gyroscope GY-521, mises à jour sans câble)

Date : 2026-11-08 (soir), à la suite de [journal_tests.md](journal_tests.md). Même PC (Windows 11 Pro 10.0.26200), même outillage (arduino-cli 1.5.1, paquet `esp32:esp32` 3.3.7, FQBN `esp32:esp32:esp32`, port COM4, pont CP2102), même robot (Roomba 694) et même carte (ESP32 DevKit 30 broches).

## Résumé

- Le firmware Wi-Fi compile, se téléverse et fonctionne : point d'accès « Roomba694 » (192.168.4.1), page web, console TCP, lecture périodique des capteurs, gyroscope MPU-6050 détecté et lu à 100 Hz, robot commandé et interrogé à travers les résistances de 1 kΩ.
- Première version (v1) testée par USB puis par le téléphone : la page s'affiche, mais l'enregistrement du réseau de la maison a échoué (page protégée par un identifiant non communiqué, puis redémarrage de la carte). Une version 2 corrige cela et refait l'interface (voir § 6).
- Trois comportements du 694 mesurés ce soir : octet parasite `B0` quelques secondes après un réveil par BRC (lecture fausse une fois : température −80 °C, puis état de charge 176) ; réponse à la lecture groupée (opcode 149, 22 paquets) correcte mais lente, au-delà des 200 ms d'attente d'une lecture simple ; rendormissement du robot malgré l'anti-veille par BRC (à creuser).
- Le robot n'a pas bougé de la soirée (câble USB vers le PC branché) : aucun test de déplacement par la page web pour l'instant.
- **2026-11-09 : version 3 préparée** (radar à ultrasons HC-SR04 sur servo SG90, fichier `radar.ino`), compilée (1 093 074 octets, 83 %), **pas encore téléversée, câblée ni testée** : § 13 et [../notes/G_radar_ultrason_servo.md](../notes/G_radar_ultrason_servo.md).

## 1. Câblage du jour

Sur plaque d'essai, carte alimentée par son USB-C uniquement (VIN libre), d'après le plan donné à l'utilisateur :

| ESP32 | vers | remarque |
|---|---|---|
| 3V3 | GY-521 VCC | rail rouge |
| GND | robot trou 6 + GY-521 GND | rail bleu |
| D4 (GPIO4) | robot trou 5 (BRC) | 1 kΩ en série (facultatif) |
| RX2 (GPIO16) | robot trou 4 (TXD) | 1 kΩ en série (facultatif) |
| TX2 (GPIO17) | robot trou 3 (RXD) | 1 kΩ en série (facultatif) |
| D21 (GPIO21) | GY-521 SDA | |
| D22 (GPIO22) | GY-521 SCL | |

Trous 1 et 2 du robot jamais reliés. GY-521 à plat, puce vers le haut, AD0 libre (adresse 0x68).

## 2. Compilation et téléversement

| Version | Taille | Résultat |
|---|---|---|
| v1 (gyroscope, page simple) | 1 043 383 octets (79 %), 53 288 octets de RAM | OK, deux avertissements `-Wvolatile` corrigés (`x++` sur un `volatile` remplacé par `x = x + 1`) |
| v2, premier essai | — | erreur : prototypes des fonctions du second fichier `web.ino` non générés à partir de `handleLog` → prototypes explicites ajoutés dans le fichier principal |
| v2, deuxième essai | — | erreur : `'asyncfunction' does not name a type` dans le HTML : l'outil Arduino prend le JavaScript des pages (`function ...`) pour des fonctions C++ et génère de faux prototypes → le HTML est déplacé dans `pages.h` (les `.h` ne sont pas analysés) |
| v2 (interface refaite, lecture groupée bloquante) | 1 063 691 octets (81 %), 58 248 octets de RAM | OK, sans avertissement |
| v2 finale (lecture groupée non bloquante) | voir § 7 | |
| v3 (radar à ultrasons, 2026-11-09) | 1 093 074 octets (83 %), 59 248 octets de RAM | OK, sans avertissement ; pas encore téléversée |

Téléversement par USB sur COM4 à chaque fois : `arduino-cli upload -p COM4 --fqbn esp32:esp32:esp32 roomba694_recherche/code/roomba694_wifi`, environ 12 s pour 1,06 Mo (« Hash of data verified »).

Incident avant le premier téléversement : le PC ne voyait plus la carte (Windows : « Unknown USB Device (Device Descriptor Request Failed) », pas de COM4). Causes possibles : câble USB mal enfoncé (même symptôme que l'après-midi) ou court-circuit sur le nouveau câblage. Vérification demandée à l'utilisateur : LED rouge de l'ESP32 et LED du GY-521 allumées, rien de chaud → pas de court-circuit ; après rebranchement du câble, COM4 revenu.

## 3. Démarrage et vérifications par USB (v1)

Extrait de la sortie au démarrage :

```
=== Roomba 694 — console Wi-Fi v1 ===
...
Point d'accès « Roomba694 » démarré, adresse 192.168.4.1, mot de passe par défaut : voir en-tête du sketch.
Gyroscope MPU-6050 détecté (WHO_AM_I 0x72) : calibration pendant 1 s, robot immobile.
```

`WHO_AM_I` vaut 0x72 et non 0x68 : module compatible (clone courant), lu sans erreur (680 lectures, 0 erreur après 7 s ; 11 772 lectures, 0 erreur après 2 min).

Gyroscope au repos (`g`) : accélérations X −0,01 g, Y −0,03 g, Z 1,10 g (axe vertical Z détecté, vers le haut ; 1,10 au lieu de 1,00 : échelle du clone, sans effet sur le cap qui n'utilise que la rotation), vitesses de rotation 0,0 à 0,1 °/s, cap 0,0°.

Test de continuité `n`, robot endormi, à travers les résistances de 1 kΩ :

```
RX2 (GPIO16, fil du trou 4) : haut 400/400 rappel haut, 400/400 rappel bas, 400/400 sans rappel  -> tenu HAUT par le robot : fil relié.
TX2 (GPIO17, fil du trou 3) : haut 400/400 rappel haut, 0/400 rappel bas, 400/400 sans rappel    -> relié à travers un rappel FAIBLE : fil probablement relié.
D4  (GPIO4, fil du trou 5)  : haut 400/400 rappel haut, 0/400 rappel bas, 400/400 sans rappel    -> relié à travers un rappel FAIBLE : fil probablement relié.
```

Les trois fils sont donc bons ; les 1 kΩ ne gênent pas le test.

## 4. Robot par USB (v1) : réveil BRC, Passive, lectures

Séquence `w`, `s`, `b`, `k`, `a`, `i` (3 s entre les touches) :

```
Envoyé : Start (128) -> Passive
Query List (149) sans réponse : lecture paquet par paquet désormais.
Tension batterie : 15301 mV
Courant : -127 mA   (négatif = décharge)
Température : -80 °C
Charge : 1588 / 2068 mAh
État de charge : 0
Mode OI lu : 2   (... sur ce 694 la valeur est décalée de +1)
Encodeurs : gauche 229, droit 353
Anti-veille activé.
Robot : joignable (dernier contact il y a 697 ms, lecture paquet par paquet)
```

- Température −80 °C = octet `0xB0` : c'est l'octet parasite déjà vu après un réveil par BRC (`B0 02`), arrivé pendant la lecture de la température. Relecture 2 min plus tard : 19 °C (16 à 19 °C dans le journal de l'après-midi). Le réveil par BRC pollue donc une lecture quelques secondes après l'impulsion (voir aussi § 7 : « État de charge : 176 » = `0xB0`, même cause).
- « Query List (149) sans réponse » : la cause n'est pas une absence de prise en charge, voir § 7.
- Encodeurs 229 / 353 : valeurs de l'après-midi conservées tant que le robot n'a pas été éteint ; après le rendormissement et un nouveau réveil ils repartent de 2 / 4 (§ 7).

`e` : pare-chocs 0/0, roues levées 0/0, vide 0 0 0 0, light bumper 0 0 0 0 0 0, boutons 0 (robot posé, rien devant).

## 5. Essai depuis le téléphone (v1) et constats

L'utilisateur a connecté le téléphone au réseau « Roomba694 » et ouvert la page, puis tenté d'enregistrer le réseau de la maison par /wifi : échec (« ça n'a pas marché »). Vérification par USB (`i`) : « Réseau de la maison : aucun enregistré ». Causes identifiées dans le code de la v1 :

1. la page /wifi demandait un identifiant (`admin` + mot de passe du point d'accès) que l'utilisateur n'avait pas reçu ;
2. après enregistrement la carte redémarrait, ce qui coupe le point d'accès quelques secondes et fait décrocher le téléphone ;
3. les téléphones quittent volontiers un réseau « sans internet ».

Deux autres constats dans la même capture série :

- **Robot rendormi** : « Robot : sans réponse (dernier contact il y a 700 s) » alors que l'anti-veille (impulsion BRC toutes les 60 s) était active. Le robot s'est rendormi environ 6 min après son réveil par BRC. Réveillé à nouveau par `w` puis `s` : réponse immédiate (15 217 mV, 20 °C). Question ouverte : l'impulsion BRC périodique n'empêche pas la veille sur ce 694 (ou l'utilisateur a envoyé `x`/`o` depuis la page ; à confirmer). Pour une session stable : réveil par le bouton CLEAN, puis `s`, comme l'après-midi.
- **Inondation de la console** : 18 600 lignes « Roues arrêtées. » reçues à l'ouverture du port, puis encore une centaine par seconde, puis plus rien trois minutes plus tard ; `i` indiquait « Roues : arrêtées », aucun client TCP, aucun appareil sur le point d'accès. Origine non identifiée (le seul chemin qui imprime ce message en boucle est la touche stop répétée : octets `0x20` ou `0x35` arrivés en rafale sur une entrée, ou appui répété sur STOP dans la page). La v2 ne peut plus produire cette inondation : message et ordre d'arrêt limités à une fois par seconde quand les roues sont déjà arrêtées, octets non imprimables ignorés sur l'USB et le TCP, « Touche inconnue » limitée à une par seconde.

## 6. Version 2 : ce qui change

- **Page /wifi** : plus d'identifiant ; bouton « Chercher les réseaux » (liste des réseaux 2,4 GHz à portée, un appui remplit le nom) ; enregistrement puis connexion immédiate sans redémarrage ; état affiché en continu avec la cause d'un échec (réseau introuvable, mot de passe refusé, signal perdu) obtenue par les événements Wi-Fi de l'ESP32 ; le mot de passe n'est ni renvoyé par l'API ni écrit sur la console.
- **Tableau de bord** (fichiers `web.ino` + `pages.h`) : pavé « maintenir pour rouler » (ordre répété toutes les 400 ms, arrêt au relâchement, garde-fou 1,5 s conservé), curseur de vitesse 50 à 150 mm/s (`/api/speed`), batterie en pourcentage, mode OI décodé (brut + 1), dessin du robot vu de dessus (pare-chocs, 6 signaux light bumper, 4 capteurs de vide, roues levées), cadran du cap gyroscopique, actions avec confirmation pour Clean / base / extinction, console intégrée qui affiche les mêmes lignes que la console série (`/api/log`, journal de 40 lignes en mémoire) et permet d'envoyer une touche.
- **Touche `q`** : réessaie la lecture groupée (149) et affiche les octets reçus et le temps de réponse.
- **Lecture groupée non bloquante** : la réponse est ramassée au fil de la boucle, délai maximal 600 ms, aucune autre requête tant qu'elle est attendue (§ 7).
- **Plausibilité** : une lecture périodique est rejetée si la tension, la température, l'état de charge ou le mode OI sont aberrants (octets parasites).
- Protections contre l'inondation de la console (§ 5), vitesse affichée dans `i`, version « v2 » dans l'aide et `i`.

## 7. Démarrage et vérifications par USB (v2)

Séquence après redémarrage : `i`, `g`, `w`, `s`, `b`, `q`, `k`, `a`, `i`.

```
=== Roomba 694 — console Wi-Fi v2 ===
Point d'accès « Roomba694 » démarré, adresse 192.168.4.1 ...
Gyroscope MPU-6050 détecté (WHO_AM_I 0x72) : calibration pendant 1 s, robot immobile.
Firmware roomba694_wifi v2, compilé le Nov  8 2026 20:05:10, en marche depuis 5 s
Gyroscope : 680 lectures, 0 erreurs ; X -0.01  Y -0.03  Z 1.09 g ; rotation 0,0 °/s ; cap 0,0°
Impulsion BRC envoyée.
Envoyé : Start (128) -> Passive
Tension batterie : 15133 mV / Courant : -127 mA / Température : 17 °C / Charge : 1588 / 2068 mAh
État de charge : 176     <- octet parasite 0xB0, 3 s après le réveil par BRC (même cause que le -80 °C du § 4)
Mode OI lu : 2
Query List (149) avec 22 paquet(s) : 38 octet(s) reçu(s) sur 38 :
  00 00 00 3B 1D FF 81 10 06 34 08 14 03 83 07 5F 08 E1 03 14 02 00 02 00 04 00 00 00 00 02 00 07 00 03 00 0C 00 00
Lecture groupée réactivée.
Encodeurs : gauche 2, droit 4
```

Décodage des 38 octets (ordre des paquets 7, 18, 21, 22, 23, 24, 25, 26, 28, 29, 30, 31, 35, 43, 44, 45, 46 à 51) : pare-chocs 0, boutons 0, état de charge 0, tension `3B1D` = 15 133 mV, courant `FF81` = −127 mA, température `10` = 16 °C, charge `0634` = 1 588 mAh, capacité `0814` = 2 068 mAh, signaux de vide 899 / 1 887 / 2 273 / 788 (gauche, avant gauche, avant droit, droit, robot posé sur le sol), mode `02`, encodeurs 2 / 4, light bumper bits 0 puis signaux 0, 2, 7, 3, 12, 0. Tout est cohérent avec les lectures simples : **le 694 prend bien en charge l'opcode 149.**

Pourquoi la lecture périodique l'abandonne-t-elle ? Première hypothèse : réponse plus lente que les 200 ms d'attente d'une lecture simple. La v2 finale ramasse donc la réponse au fil de la boucle pendant au plus 600 ms, sans qu'aucune autre requête ne parte entre-temps. Mesures avec cette version (robot réveillé par `w`, `w`, `s`) :

```
Query List (149) avec 22 paquet(s) : 38 octet(s) reçu(s) sur 38 en 15 ms : 00 00 00 3B 01 FF 81 14 05 27 08 14 ...
Lecture groupée réactivée.
Query List (149) : 37 octet(s) sur 38 en 600 ms, lecture paquet par paquet désormais (q pour réessayer).
```

- La requête manuelle (`q`) obtient les 38 octets en **15 ms** : la réponse n'est donc pas lente.
- La requête périodique qui suit immédiatement n'obtient que **37 octets** en 600 ms, puis le firmware repasse en lecture paquet par paquet, qui fonctionne (« Robot : joignable, lecture paquet par paquet », dernier contact 300 ms).
- Hypothèse restante : le robot tronque ou saute un octet quand une requête groupée suit de près une autre requête (celle de `q`, ou les lectures simples du cycle précédent) ; à instrumenter (afficher les octets reçus en cas d'échec périodique, espacer la requête groupée de 50 ms). Sans conséquence pour l'usage : la lecture paquet par paquet, un paquet par passage de la boucle, laisse la page web réactive.

Réveil par BRC avec cette version : une première impulsion `w` suivie de `s` 3 s plus tard n'a rien donné (aucune réponse à `b`, `q`, `k`) ; deux impulsions à 4 s d'intervalle puis `s` ont réveillé le robot (15 105 mV, 19 °C, 1 321 / 2 068 mAh, mode 2). La charge est passée de 1 588 à 1 321 mAh pendant la soirée (robot réveillé la plupart du temps).

Encodeurs après ce réveil : 2 / 4 (ils repartent de zéro à chaque réveil, contrairement à l'après-midi où le robot n'avait pas dormi entre deux lectures).

Interface web (v2) vérifiée hors robot : pages servies depuis un petit serveur local avec de fausses données `/api/state`, `/api/log`, `/api/scan` ; rendu correct au format téléphone (375 px), aucune erreur de script, pavé de pilotage : un appui envoie `/api/cmd?c=8` puis `/api/cmd?c=%20` au relâchement, STOP envoie `c=%20`, liste des réseaux affichée après « Chercher les réseaux ». Deux retouches faites à cette occasion : légende du dessin du robot sur deux lignes, et console web qui n'ajoute que les lignes nouvelles.

## 8. Depuis le téléphone : réseau de la maison, pilotage, incidents

- **Réseau de la maison** : enregistré par l'utilisateur depuis la nouvelle page /wifi (téléphone sur « Roomba694 »), connexion obtenue, adresse 192.168.18.25. Le PC (192.168.18.6) joint la carte : `ping` 95 ms, `/api/state` en 0,13 s, console TCP (`tcp_console.ps1 -HostName 192.168.18.25 -Commands 'i'`) fonctionnelle. Le câble USB a été débranché du PC pour alimenter la carte par la batterie portable fixée sur le robot.
- **« Ça ne fonctionne pas »** : le journal de la carte (`/api/log`) a montré la cause : réveil puis « Passive (s) », puis flèches, **sans « Safe (f) »** ; le robot ignore les ordres de roues en Passive. Puis le robot s'est rendormi et n'a plus répondu, ni aux impulsions BRC envoyées par le réseau. Après appui sur CLEAN par l'utilisateur, puis `s` et `f` depuis la page : le robot roule, piloté depuis le téléphone (vitesse réglée à 60 mm/s par l'utilisateur). Le voyant CLEAN clignote pendant le pilotage en Safe.
- **Redémarrages répétés de la carte** sur batterie portable : uptime observé 199 s, puis 47 s, puis 406 s, puis 50 s, puis 12 s, puis 11 s... soit un redémarrage toutes les 2 à 6 minutes, y compris pendant le pilotage. Chaque redémarrage perdait l'anti-veille, le mode et la vitesse choisie (retour à 150 mm/s). Cause à établir : la version 20:46 affiche la raison du dernier redémarrage (`esp_reset_reason`) au démarrage, dans `i`, dans `/api/state` (`rst`) et en bas de la page : « BAISSE DE TENSION » désignerait l'alimentation (câble, batterie), « PLANTAGE » le firmware.
- **Flux continu de capteurs** : après un de ces redémarrages, toutes les lectures sont devenues du charabia (« Tension batterie : 4924 mV », « Mode OI lu : 19 », encodeur droit 4924). 4924 = `0x133C` : en-tête 19 (`0x13`) et longueur 60 (`0x3C`) d'un **flux de capteurs (opcode 148)**, et 60 octets = exactement nos 22 identifiants + 38 octets de données. Le robot a donc reçu notre liste avec l'opcode 148 (flux toutes les 15 ms) au lieu de 149, vraisemblablement un octet altéré au moment d'un redémarrage de la carte (la ligne TX2 n'est pas pilotée pendant la réinitialisation). Tout ce qui est lu ensuite est décalé. Correction (version 20:46) : opcode 150 (pause du flux) envoyé au démarrage de la carte, touche `p` pour le renvoyer à la main, et envoi automatique après trois lectures périodiques incohérentes de suite.
- Ajouts de la même version : arrêt des roues envoyé au démarrage de la carte (un redémarrage pendant un déplacement en Safe laisserait sinon le robot sur son dernier ordre), vitesse de la page conservée en mémoire d'un démarrage à l'autre.

## 9. Mise à jour sans câble depuis le PC

| Voie | Résultat |
|---|---|
| ArduinoOTA : `espota.exe -r -i 192.168.18.25 -p 3232 --auth=roomba694 -f build/esp32.esp32.esp32/roomba694_wifi.ino.bin` | « Sending invitation… Authenticating… OK » puis « No response from device » : la carte doit ouvrir une connexion vers le PC pour recevoir le fichier, et le pare-feu de Windows la bloque selon toute vraisemblance (à autoriser une fois pour `espota.exe`, ou utiliser l'autre voie) |
| Page /update : `curl -u admin:roomba694 -F "firmware=@…/roomba694_wifi.ino.bin" http://192.168.18.25/update` | « Mise à jour réussie, la carte redémarre. » : 1 065 990 octets en 10,7 s ; 20 s plus tard la carte répond avec la nouvelle version (compilée 20:46:54), raison du redémarrage « redémarrage logiciel (mise à jour) », robot joignable |

Après cette mise à jour le robot répond à nouveau normalement (la pause du flux au démarrage a suffi). Deux autres mises à jour par la même voie dans la soirée, robot en charge sur sa base et OI fermée : 21:17 (libellé de l'état de charge 2 : « charge à pleine puissance »), 21:23 (anti-veille BRC toutes les 45 s au lieu de 60, d'après les retours d'autres montages). Chacune : 1,07 Mo en 10 s, redémarrage « logiciel (mise à jour) ».

Reste à faire : lire la raison des redémarrages après la prochaine coupure (pied de page ou `i`), comparer le cap du gyroscope et les encodeurs sur un quart de tour, consigner les réponses du robot en Safe pendant un déplacement.

## 10. Observation de dix minutes pendant le pilotage au téléphone (20:51 → 21:01)

Outil : `code/outils/monitor_wifi.py` (une lecture de `/api/state` et de `/api/log` par seconde, sans rien envoyer au robot) ; fichiers `mesures/monitor_2026-11-08_20h51.csv` (608 lignes) et `…_evenements.txt`. Robot en Safe, piloté depuis la page par l'utilisateur, 192 s de roues en mouvement.

- **Cap du gyroscope contre rotation calculée par les encodeurs** (rotation = (Δdroit − Δgauche) × 0,4446 mm / 235 mm), par épisode de mouvement :

  | Type de mouvement | Encodeurs | Gyroscope |
  |---|---|---|
  | rotation sur place | +48° | +48,2° |
  | rotation sur place | −85° | −90,6° |
  | rotation sur place | +60° | +60,3° |
  | rotation sur place | +117° | +106,7° |
  | rotation sur place | −64° | −60,0° |
  | rotation sur place | −155° | −141,1° |
  | ligne droite 1,1 à 1,8 m | 0° | +2,1° à +3,2° |
  | virage en roulant | +39° | +60,2° |
  | virage en roulant | −23° | −17,6° |

  Lecture : sur une rotation sur place les deux concordent à quelques degrés près, les encodeurs surestimant les grandes rotations (−155° contre −141°, comme les 5 à 7 % de trop vus l'après-midi) ; en ligne droite le gyroscope voit 1 à 3° que les encodeurs ne voient pas (vrai léger virage ou dérive) ; en virage en roulant les écarts grandissent (glissement). Le gyroscope est donc le bon juge du cap, les encodeurs celui de la distance.
- **Les compteurs d'encodeurs sont sur 16 bits signés** : un épisode a affiché −58 192 pas en 24 s (impossible), c'est le passage de +32 767 à −32 768. Le script en tient compte désormais (différence modulo 65 536) ; à faire aussi dans tout calcul d'odométrie.
- **Capteurs** : pare-chocs gauche et droit vus actifs lors de contacts avec les murs ; light bumper jusqu'à 1 300 (gauche) près d'un mur, quelques dizaines à 1 m ; capteurs de vide à 0 quand le robot est soulevé ou sur sa base, 770 à 2 400 au sol ; roues levées signalées en montant sur la base.
- **Retour à la base** : « Base (h) » (Seek Dock 143) envoyé depuis la page à 20:58:35 : le robot passe en Passive, cherche et rejoint sa base seul en 25 s (pare-chocs puis roues levées sur la rampe) ; courant ensuite +1 295 mA, état de charge 2 (charge à pleine puissance). Tension vue de 14,21 V (roues en mouvement, −1 240 mA) à 15,92 V (sur la base).
- **Un redémarrage de la carte** pendant la montée sur la base, raison lue : « mise sous tension », donc coupure franche de l'alimentation (connecteur USB ou batterie portable secoués par le choc avec la rampe), ni baisse de tension progressive ni plantage. Les redémarrages répétés de la soirée ont très probablement la même cause mécanique : scotcher batterie et connecteurs, ou alimenter la carte depuis le robot.
- Après ce redémarrage la lecture groupée a de nouveau échoué (0 octet) puis la lecture paquet par paquet a repris sans incohérence : la pause du flux (150) au démarrage joue son rôle.
- Fin de session : `s` puis `x` envoyés par le réseau une fois le robot sur sa base (OI fermée, charge en cours).

## 11. Problèmes rencontrés et corrections

| Problème | Cause | Correction |
|---|---|---|
| PC sans COM4, périphérique USB en erreur | câble USB mal enfoncé (court-circuit exclu : LED allumées, rien de chaud) | rebranchement |
| Avertissements `-Wvolatile` | `imu.samples++` sur un champ `volatile` | `imu.samples = imu.samples + 1` |
| Température −80 °C, état de charge 176 | octet parasite `0xB0` émis par le robot quelques secondes après un réveil par BRC | relire ; lectures périodiques filtrées (tension, température, état de charge, mode) ; préférer le bouton CLEAN |
| Lecture groupée 149 « sans réponse » en lecture périodique | non élucidé : la même requête envoyée à la main (`q`) obtient les 38 octets en 15 ms, la requête périodique n'en reçoit que 37 | réponse ramassée sans bloquer (délai 600 ms), repli automatique sur la lecture paquet par paquet (un paquet par passage de la boucle), touche `q` de diagnostic |
| Page /wifi inutilisable depuis le téléphone | identifiant non communiqué, redémarrage de la carte, téléphone quittant le réseau sans internet | plus d'identifiant sur /wifi, connexion sans redémarrage, liste des réseaux, état et cause d'échec affichés, conseils sur la page |
| Inondation « Roues arrêtées. » | origine non identifiée (touche stop en rafale ?) | arrêt et message limités à une fois par seconde si déjà arrêté ; octets non imprimables ignorés ; « Touche inconnue » limitée |
| Prototypes non générés pour `web.ino` ; `'asyncfunction' does not name a type` | limites de l'outil Arduino face au second `.ino` et au JavaScript des pages | prototypes explicites ; HTML déplacé dans `pages.h` |
| Robot rendormi malgré l'anti-veille BRC | non élucidé (BRC inefficace sur ce 694 ?) ; les impulsions BRC ne le réveillent pas toujours non plus | CLEAN puis `s` reste la méthode sûre ; `w` deux fois à 4 s d'intervalle parfois |
| Flèches sans effet depuis le téléphone | robot en Passive (Safe jamais envoyé) | rappel sur la page ; séquence CLEAN, `s`, `f` |
| Lectures incohérentes (4924 mV, mode 19) | robot passé en flux continu (opcode 148) après un redémarrage de la carte | opcode 150 au démarrage, touche `p`, envoi automatique après trois lectures incohérentes |
| Redémarrages de la carte toutes les 2 à 6 min sur batterie portable | coupure franche de l'alimentation (« mise sous tension » lue après le redémarrage observé), connecteur USB ou batterie secoués | raison du redémarrage affichée ; arrêt des roues et pause du flux au démarrage ; vitesse conservée ; à faire : fixer connecteurs et batterie, ou alimenter depuis le robot |
| ArduinoOTA « No response from device » | connexion retour carte → PC bloquée (pare-feu) | mise à jour par la page /update, qui fonctionne |

## 12. Rappel de fin de session

Toujours finir par `s` puis `x` (console série, console TCP ou page web). Ne jamais brancher l'USB du PC et une autre alimentation en même temps. Ne pas utiliser les flèches de la page tant que le câble USB relie la carte au PC.

## 13. Version 3 (2026-11-09) : radar à ultrasons, préparée et compilée, non testée

Demande de l'utilisateur : tirer le meilleur parti de deux modules de son kit ELEGOO, le capteur à ultrasons HC-SR04 et le micro-servo SG90, en attendant le LiDAR (note F). Rien n'a été câblé ni téléversé : le robot est resté en charge sur sa base.

- **Code** : nouveau fichier `radar.ino` (tâche sur le second cœur : servo par PWM LEDC 50 Hz sans bibliothèque, mesure de l'écho par interruption, carte polaire 33 cases de −80° à +80°, médiane des trois dernières mesures du secteur avant, modes arrêt / fixe / balayage, « devant en marche avant », réglages en flash) ; dans le fichier principal : touches `r` et `u`, refus de la touche `8` et arrêt des roues devant un obstacle (`radarTick`), colonne `us_mm` du CSV, drapeau `driveForward` ; dans `web.ino` : `/api/radar`, résumé `radar` dans `/api/state`, version « v3 » ; dans `pages.h` : carte « Radar à ultrasons » avec dessin polaire sur `canvas`, réglages, orientation du capteur en touchant le dessin. Outils : `monitor_wifi.py` (colonnes `radar_mode`, `us_mm`), nouveau `radar_capture.py` (CSV par mesure avec encodeurs et cap, dernière carte en SVG).
- **Broches** : D27 servo, D32 Trig, D34 Echo via diviseur 1 kΩ / 2 kΩ, 5 V des modules sur VIN. Côté « VIN » de la carte, dont la rangée de trous libres (colonne j) et les bandes du bas sont encore vides d'après les photos de la plaque (`images/plaque_esp32_placee_rangees.jpg`).
- **Compilation** : 1 093 074 octets (83 % de la flash), 59 248 octets de RAM, sans avertissement (`arduino-cli compile --fqbn esp32:esp32:esp32 --export-binaries`). Fichier `build/esp32.esp32.esp32/roomba694_wifi.ino.bin` prêt pour la page /update.
- **Page web** : vérifiée hors robot, au format téléphone (375 px), avec un petit serveur local servant la page et de fausses réponses `/api/state`, `/api/log`, `/api/radar` : la carte « Radar à ultrasons » se dessine (mur à 1,5 m en vert, obstacle sous le seuil en rouge, « rien à portée » en gris au bord, points hors portée du dessin en cercles creux, trait bleu de la direction du capteur), aucune erreur de script ; toucher le dessin à gauche envoie `mode=fixe&angle=45` et la page affiche « Fixe devant » et « Capteur vers +45° » ; « Arrêt » vide la carte et affiche « – » devant ; réglages (seuil, cases, pas, amplitude, portée, Effacer) rendus correctement.
- **Correction du 2026-11-09 (matin)** : la photo de la plaque sur le robot montre que la colonne VIN de la carte est collée au bord de la plaque (aucun trou libre à côté de VIN, GND, D27, D32, D34), alors que la colonne 3V3 a bien sa colonne libre (déjà utilisée par le robot et le gyroscope). Broches du radar déplacées côté 3V3 : servo **D18**, Trig **D19**, Echo **D23** (constantes de `radar.ino`, recompilé). Le 5 V des modules ne peut pas venir de VIN : source externe à choisir (second port de la batterie USB, ou sortie 5 V de l'abaisseur ; la version de l'abaisseur à prise USB alimenterait aussi la carte par son câble, ce qui règle la question). Les schémas `images/plan_radar_ultrason_plaque*.png` sont à refaire. Autre constat sur la photo : la carte est en rangées 15 à 29 (3V3 en rangée 15), pas 11 à 25 comme sur le plan de la veille : se repérer aux étiquettes des broches plutôt qu'aux numéros.
- **Reprise du 2026-11-09 (après-midi)** : relecture complète avant tout essai. Décision de l'utilisateur : le 5 V des deux modules est pris sur la patte **VIN** de la carte, par un fil qu'il pose lui-même jusqu'à la ligne rouge libre du côté VIN de la plaque ; la masse y arrive par un fil entre les deux lignes bleues. Deux corrections dans `radar.ino` : rappel interne vers la masse sur l'entrée Echo (`INPUT_PULLDOWN`), qui restait en l'air tant que rien n'était câblé ; en balayage, le capteur reste devant dès qu'une avance est demandée et 1 s après le dernier ordre (`RADAR_HOLD_MS`), sinon le refus d'avancer expirait au bout de 1,5 s et le robot pouvait s'approcher d'un obstacle par à-coups, bouton tenu. Limites connues ajoutées à la note G (en mode fixe orienté de côté, rien ne surveille l'avant). Recompilation avec `--warnings all` : 1 093 166 octets (83 % de la flash), 59 256 octets de RAM, aucun avertissement. Plaque re-mesurée sur la photo : la carte occupe les rangées 16 (3V3 / VIN) à 30 (D23 / EN), et non 15 à 29 comme écrit le matin. Câblage de la note G refait (section 2) avec un seul dessin sur la photo réelle (`images/branchement_radar_sur_photo.jpg`) ; les deux schémas `images/plan_radar_ultrason_plaque*.png`, faux, sont retirés du dépôt. **Toujours rien de téléversé, câblé ni testé** : la carte n'était joignable ni en Wi-Fi ni en USB ce jour-là.
- **Reprise du 2026-11-09 (soir), nouvelle session** : la session de l'après-midi s'est arrêtée avant d'enregistrer son travail et avant d'envoyer le dessin. Tout a été relu avant l'enregistrement. Recompilation refaite avec `--warnings all` : même résultat, 1 093 166 octets (83 %), 59 256 octets de RAM, aucun avertissement. Dessin `images/branchement_radar_sur_photo.jpg` comparé de nouveau à la photo d'origine, agrandie zone par zone : les trous à côté de D23, D19 et D18 sont libres ; les rangées 35, 40 et 45 de la moitié côté VIN sont vides ; rien n'est planté dans les deux lignes du côté VIN, dont les trous sont en face des rangées 15 à 19, 21 à 25 et 27 à 31 ; le trou de la ligne bleue du côté 3V3 en face de la rangée 31 est libre et sur le même tronçon que le fil de masse du cerveau. Dessin envoyé à l'utilisateur avec les neuf étapes. La carte ne répondait toujours pas (ni Wi-Fi, ni port USB) : **rien de téléversé, câblé ni testé**.
- **Reste à faire, dans l'ordre** (plan détaillé dans la note G, section 5) : téléverser la v3 (la carte « Radar » apparaît, mode arrêt, rien ne change pour le robot) ; câbler carte hors tension, deux mesures au multimètre (pas de bip continu, puis environ 4,7 V entre la ligne rouge et la ligne bleue du côté VIN) ; servo seul (sens de rotation, case « servo inversé ») ; capteur seul (livre à 20, 50, 100 cm) ; balayage sur la table ; carte depuis le robot à l'arrêt ; **avec l'accord de l'utilisateur**, test de l'arrêt automatique devant un carton à 60 mm/s ; plus tard, comparaison distance ultrason / encodeurs en approchant un mur.

## 14. Version 3 sur le matériel (2026-11-09, soir) : installation, mise à jour sans mot de passe, premiers essais du radar

Robot éteint pendant toute la séance : aucun ordre de roues.

- **Câblage réel** (trois photos de l'utilisateur, vers 18 h 45) : il diffère du dessin `images/branchement_radar_sur_photo.jpg`, l'utilisateur ayant déplacé des fils. Fil 5 V violet, passé sous le cerveau depuis la rangée de VIN jusqu'à la ligne rouge du côté VIN (bout USB) ; condensateur au même endroit ; servo par trois fils brun / gris / orange (brun → ligne bleue, gris = rouge du servo → ligne rouge, orange → D18) ; capteur de distance : Vcc → ligne rouge, Gnd → ligne bleue en face de la rangée 31, Trig → D19, Echo → rangée 42 de la moitié côté VIN ; résistances de la rangée 42 à la rangée 39, puis de la rangée 39 à la rangée 35 ; fil rouge de la rangée 39 à D23 ; fil de masse (rouge) de la ligne bleue du côté 3V3 (rangée 49) à la ligne bleue du côté VIN (rangée 37), donc sur l'autre moitié des lignes. Le fil de la rangée 35 à la ligne bleue du côté VIN manquait sur les photos : signalé avec un dessin, posé ensuite d'après l'utilisateur. Fils du robot refaits avec d'autres couleurs (D4 rouge, TX2 brun, RX2 bleu).
- **Installation** : la page /update du firmware v2 demandait un mot de passe, que l'assistant ne saisit pas à la place de l'utilisateur ; l'envoi depuis le téléphone n'a pas abouti (la page ne proposait pas le fichier). L'utilisateur a branché le cerveau en USB sur le PC : `arduino-cli upload -p COM4 --fqbn esp32:esp32:esp32 --input-dir …/build/esp32.esp32.esp32 …/roomba694_wifi`, 11,8 s, « Hash of data verified ». La carte répond « v3 Nov 9 2026 19:07:55 » et a retrouvé seule le réseau de la maison (192.168.18.25). Binaire : 1 087 018 octets (82 % de la flash), 59 272 octets de RAM, aucun avertissement.
- **Mise à jour par Wi-Fi sans mot de passe** (demande de l'utilisateur : « mot de passe pas nécessaire, on est sur le wifi safe de la maison ») : `web.ino` ne demande plus d'identifiant pour /update ; il vérifie seulement que la requête vise une adresse de la carte (en-tête Host) et ne vient pas d'une page d'un autre site (en-tête Origin absent ou identique), fonction `updateRequestIsLocal`. Essais : envoi avec `Origin: http://exemple.invalid` → 403 ; envoi avec `Host: autre.exemple` → 403 ; dans les deux cas rien n'est écrit et la carte ne redémarre pas (ligne « Mise à jour refusée » dans la console) ; envoi normal par `curl -F "firmware=@…bin" http://192.168.18.25/update` → « Mise à jour réussie, la carte redémarre. » en 10,4 s, puis réponse 5 s après le redémarrage, raison « redémarrage logiciel (mise à jour) », réseau de la maison retrouvé. ArduinoOTA garde son mot de passe (non utilisé). L'utilisateur a aussi demandé d'écrire le réseau de la maison en dur dans le code : non fait, il est conservé dans la mémoire de la carte d'une installation à l'autre, et son mot de passe ne s'écrit dans aucun fichier.
- **Réglage** : l'utilisateur demande de ne pas trop faire tourner le servo (fils du capteur courts) : amplitude du balayage réglée à 20° (`/api/radar?amplitude=20`), essais limités à ±15°.
- **Capteur de distance, servo au centre** (19 h 14, cerveau de nouveau sur son alimentation habituelle, mode fixe à 0°) : capteur détecté dès la première mesure ; 44 mesures en 5 s, aucune sans écho, aucune sans réaction ; 71,4 à 71,8 cm, stable. Première mesure du radar sur le matériel.
- **Servo à +15°, −15°, 0°** (mode fixe) : à +15°, une mesure de 11 cm, puis **24 mesures de suite sans réaction du capteur** (Echo jamais haut) pendant les 2,5 s passées de ce côté ; à −15°, le capteur répond de nouveau tout de suite : 200 cm environ, ou rien à portée (8 fois) ; de retour à 0° : 32 à 33 cm, au lieu de 72 cm avant les mouvements. Aucun redémarrage de la carte pendant l'essai. Les distances changent avec l'angle demandé : le servo déplace bien le capteur.
- **À comprendre** (non vérifié, il faut regarder le montage) : la perte du capteur d'un seul côté fait penser à un fil du capteur qui se tend et perd le contact quand le servo tourne de ce côté, ou au servo qui force contre les fils et fait baisser le 5 V du capteur ; le changement de 72 à 33 cm au centre peut venir d'un objet déplacé devant le capteur ou du capteur qui a glissé sur le servo. Le sens de rotation (+ = gauche du robot ?) n'est pas encore vérifié.
- **Cause trouvée et capteur remis en place** (19 h 20 à 19 h 30) : l'utilisateur voit le servo « tourner beaucoup à gauche » à chaque démarrage, puis faire les petits mouvements. Le capteur avait été posé sur l'axe alors que le servo n'était pas à son milieu : le milieu commandé par le programme (1500 µs) se trouvait loin à gauche de la position de montage, d'où les fils tendus. Remède : capteur retiré de l'axe, servo maintenu à 0° (mode fixe), capteur renfoncé face à l'avant. Nouvel essai à 0°, +15°, −15°, 0° : capteur détecté aux quatre positions, aucune mesure sans réaction, 43 à 44 cm partout (obstacle large devant), aucun redémarrage. La perte du capteur à +15° venait donc du mauvais calage. Reste à vérifier : le sens (+ = gauche du robot ?), le balayage, et une butée d'angle dans le programme (toucher le dessin de la page peut encore demander jusqu'à ±80°).
- **Premier balayage** (19 h 35, avec l'accord de l'utilisateur, amplitude 20°, pas de 10°, 9 s) : la carte se remplit sur les cinq directions, −20° : 43 cm, −10° : 43 cm, 0° : 43 cm, +10° : 44 cm, +20° : 46 cm (une valeur isolée à 86 cm à +20°) ; environ 9 mesures par seconde, aucune sans écho ni sans réaction, aucun redémarrage. Puis capteur laissé à +20° en mode fixe pour que l'utilisateur dise de quel côté il regarde.
- **Sens du servo** : à +20°, le capteur regarde à gauche, vu de derrière le robot (réponse de l'utilisateur) : le sens est bon, « servo inversé » reste décoché.
- **Butée du servo** (19 h 29, à la demande de l'utilisateur, qui ne veut pas que le servo tourne trop et fixe la limite à 30°) : nouveau réglage `butee` (10 à 80°, conservé en flash, `radarLimit()` dans `radar.ino`) que ni le balayage, ni le mode fixe, ni le dessin touché sur la page ne dépassent ; paramètre `butee=` de `/api/radar` ; sur la page, liste « butée du servo », deux traits orange sur le dessin, et 20° ajouté aux amplitudes. Page vérifiée avant l'envoi dans un navigateur au format téléphone, avec le petit serveur local de fausses données : la liste affiche 30, et un toucher à l'extrême gauche du dessin demande 30° au lieu de 80°. Firmware « v3 Nov 9 2026 19:29:16 », 1 088 150 octets (83 %), aucun avertissement, envoyé par Wi-Fi sans mot de passe en 10,5 s. Sur la carte, butée et amplitude réglées à 30° : une demande de +60° s'arrête à +30°, une demande de −60° à −30° ; le capteur répond aux deux extrémités (74 cm à +30°, 44 cm à −30°) ; balayage de −30° à +30° par pas de 15° : 44, 43, 43, 44 et 75 cm, aucune mesure perdue, aucun redémarrage.

## 15. Tour sur place (2026-11-09, 19 h 45) : programmé, vérifié sans mouvement

Nouvel objectif de l'utilisateur : cartographier une pièce, sans aspirer ni brosser pour l'instant ; stratégie dans `notes/H_cartographie_strategie.md`, acceptée (« Commence avec 1 »). Première étape : le tour sur place.

- **Code** : nouveau fichier `tour.ino` (préparation de 1,5 s avec recalage du gyroscope, rotation vers la gauche à 30 °/s par `driveDirect(+62, -62)` répété toutes les 300 ms, arrêt à 380° d'après le gyroscope, mesures rangées par la tâche radar avec le cap à l'instant du tir, 256 au plus) ; dans `radar.ino`, une seule mesure par direction et capteur à 0° pendant le tour ; dans le fichier principal, touche `t`, arrêt du tour par toute touche d'arrêt, de roues, de mode ou de recalibration, par une mise à jour ou par la déconnexion de la console TCP ; dans `web.ino`, `/api/tour` (`go=1`, `stop=1`) et résumé `tour` dans `/api/state`. Outil PC `code/outils/tour_capture.py` (vue de dessus, courbe distance / direction, paliers repérés ; `--go` pour lancer).
- **Sécurités** : refus si le robot ne répond pas, n'est pas en mode Safe (valeur lue 3 sur ce 694), a une roue soulevée ou le pare-chocs enfoncé, si le gyroscope manque ou si les roues tournent déjà ; arrêt sur pare-chocs, roue soulevée, robot muet plus de 2,5 s ou sorti du mode Safe, vitesse de rotation inférieure à 8 °/s pendant 2 s ou supérieure à 90 °/s, capteur sans réaction, 30 s de rotation, mémoire pleine. Limite : si la carte perd son alimentation pendant la rotation, le robot garde son dernier ordre.
- **Compilation** : 1 092 390 octets (83 % de la flash), 60 448 octets de RAM, aucun avertissement. Envoi par Wi-Fi sans mot de passe en 10,8 s ; la carte répond « v3 Nov 9 2026 19:44:25 ».
- **Vérifié, robot éteint** : `/api/tour` répond « repos » ; `/api/tour?go=1` et la touche `t` sont refusés avec « le robot ne répond pas (CLEAN sur le robot, puis s, puis f) », les roues restent à l'arrêt ; le radar mesure toujours en mode fixe (80 cm, aucune mesure perdue) ; la butée de 30° est conservée. L'outil PC, essayé avec des mesures simulées d'une pièce de 4,2 m sur 3,1 m, retrouve les quatre murs (149, 120, 270 et 190 cm) et les coins.
- **Pas encore fait** : aucun tour réel. Il demande le robot réveillé, en mode Safe, posé au sol hors de sa base, sans câble, avec l'accord de l'utilisateur au moment de le lancer. À vérifier au premier tour : la rotation réelle (380° annoncés contre un tour vu à l'œil), le recouvrement entre le début et la fin, la tenue de l'alimentation.

## 16. Robot muet : il était passé à 19200 bauds ; premier tour sur place réussi (2026-11-09, 19 h 50 à 20 h 50)

- **Symptômes** : robot allumé (bouton CLEAN éclairé, confirmé par l'utilisateur), mais aucune réponse aux questions du cerveau et aucun ordre exécuté (les trois notes de la touche `m`, envoyées trois fois, ne sont jamais jouées). Test des fils (`n`) : TX2 et D4 reliés par un rappel faible ; RX2 tenu haut, puis « en l'air » après une vérification des fils par l'utilisateur, puis de nouveau relié après remplacement d'un fil. L'utilisateur précise que le fil du trou 4 (TXD du robot) va à RX2 sans résistance : seuls les fils de TX2 et de D4 ont la leur. Depuis le début de la soirée, aucune réponse valable du robot n'avait été vue ; les « réponses complètes » notées aux démarrages étaient des octets non plausibles.
- **Indice** : une lecture de diagnostic (`q`) a renvoyé `00 E0 00 00 E0 00 00 E0 00 00 00 00 00 E0…`. À 115200 bauds, l'octet E0 correspond à un niveau bas de six bits, soit 52 µs : exactement la durée d'un bit à 19200 bauds.
- **Cause** : le robot communiquait à **19200 bauds**. Un Roomba 600 quitte ses 115200 bauds si l'on garde CLEAN appuyé une dizaine de secondes en l'éteignant (suite de notes descendantes), ou s'il reçoit trois impulsions basses sur BRC après son allumage ; il garde ce débit jusqu'au retrait de sa batterie ou jusqu'à l'ordre Baud. Laquelle des deux causes a joué n'est pas établi. À vérifier : la patte D4 (GPIO4) a un rappel vers le bas pendant le redémarrage de l'ESP32, et le test `n` montre que ce rappel l'emporte sur celui du robot ; chaque redémarrage de la carte (mise à jour, coupure de la batterie portable) enverrait donc une impulsion basse sur BRC. La soirée en a compté une dizaine.
- **Remède** : nouvelle touche `y` (`baudRescue`) : passage de la liaison à 19200 bauds, Start, lecture de la tension ; si le robot répond, ordre Baud (opcode 129, code 11 = 115200), retour à 115200 bauds et vérification. Firmware « v3 Nov 9 2026 20:44:08 » (1 093 346 octets, 83 %), envoyé par Wi-Fi. Résultat : « Le robot répond à 19200 bauds : batterie 15580 mV », puis liaison normale à 115200 bauds quelques secondes plus tard (la vérification immédiate de la fonction a échoué une fois ; la lecture périodique a ensuite réussi) : batterie 15 580 mV, 1 851 / 2 068 mAh, mode Passive, capteurs de vide 2 600 à 2 700 (robot au sol), capteurs optiques 14 à 47. Mode Safe confirmé (valeur lue 3).
- **Premier tour sur place** (20 h 46, avec l'accord de l'utilisateur, robot au sol en mode Safe) : `tour_capture.py --go`. 381° en 13,7 s (27,8 °/s), 122 mesures, arrêt normal des roues, aucun redémarrage de la carte. Fichiers `mesures/tour_20261109_204605.csv` et `.png`. La fin du tour retrouve le début : 119 cm de 360° à 381° comme de 0° à 21°, ce qui valide les 360° du gyroscope sur ce tour. Paliers repérés par l'outil : 119 cm vers 43° (très large, 65°), 152 cm vers 103°, 84 cm vers 149°, 82 cm vers 193°, un groupe à 57 cm entre 220° et 250°, 168 cm vers 293° (35° de large), 167 cm vers 336° ; rien avant 3,3 m vers 121° et vers 259°. Les deux paliers les plus nets et opposés (152 cm vers 103°, 168 cm vers 293°) feraient 3,2 m entre deux parois, décalage du capteur non corrigé. Rien de tout cela n'est encore comparé à la pièce réelle (mètre ruban, description par l'utilisateur).
- **À faire** : faire tenter le retour à 115200 bauds par le firmware lui-même quand le robot reste muet ; refuser `y` pendant un mouvement ; vérifier l'hypothèse des impulsions BRC aux redémarrages (et, si elle se confirme, déplacer le fil de BRC sur D5, dont le rappel est vers le haut au redémarrage, ou ne plus relier BRC) ; mesurer le décalage du capteur par rapport au centre du robot.

## 17. Deuxième tour sur place, retour automatique à 115200 bauds (2026-11-09, 20 h 50 à 21 h 00)

- **Deuxième tour** (20 h 51) : robot déplacé à la main d'environ un mètre par l'utilisateur ; le soulever l'a remis en Passive, d'où un nouveau `f`. 380° en 13,7 s, 124 mesures, la fin retrouve le début (103 cm). Paliers : 104 cm sur un large arc de 315° à 30°, 182 cm vers 47°, 148 cm vers 91°, 90 cm vers 175° (42° de large), 68 cm vers 262° (66° de large), 226 cm vers 305°. Fichiers `mesures/tour_20261109_205150.csv` et `.png`.
- **Comparaison des deux tours** : d'après le gyroscope, le second tour part environ 48° plus à gauche que le premier (381° du premier tour, plus 27° pendant le transport). Dans le repère du premier tour : le grand arc passe de 119 à 104 cm dans la même direction (vers 38°), la paroi de droite de 168 à 68 cm, le groupe arrière-droite de 57 à 90 cm. C'est cohérent avec un déplacement d'un mètre environ vers la paroi de droite. Non confirmé par l'utilisateur ; décalage du capteur par rapport au centre du robot non corrigé.
- **Retour automatique à 115200 bauds** (demande de l'utilisateur : noter le problème et l'intégrer au code) : `baudRescue(bool automatique)` est appelée par `y`, par un Start (`s`) resté sans réponse (au plus une fois toutes les 5 s), et après trois lectures non plausibles (au plus une fois toutes les 30 s, par la boucle principale). Elle est refusée si les roues tournent ou pendant un tour sur place, attend 350 ms après l'ordre Baud et vérifie la liaison jusqu'à trois fois. Compteur `bauds19200` dans `/api/state` et dans `i`. Firmware « v3 Nov 9 2026 20:55:25 », 1 094 090 octets (83 %), aucun avertissement.
- **Hypothèse des redémarrages écartée** : trois envois du programme à la suite (trois redémarrages logiciels de la carte en une minute, robot allumé en mode Safe) n'ont rien changé ; le robot répond à 115200 bauds après chacun (lecture groupée complète en 8 ms) et reste en Safe. Causes restantes du passage à 19200 bauds : CLEAN gardé appuyé une dizaine de secondes, ou trois impulsions de réveil (bouton « Réveil » de la page, touche `w`). Non tranché. Les coupures brèves d'alimentation de la carte ne sont pas testées.
- **Déclenchement automatique vu une fois** : à 20 h 59, le robot ne répondait plus (ni à 115200 ni à 19200 bauds, les trois fils vus reliés) ; `s` a lancé de lui-même l'essai à 19200 bauds, resté sans réponse : robot endormi ou éteint. Le retour automatique complet, robot réellement à 19200 bauds, n'a pas encore été observé ; le retour par `y` l'a été à 20 h 45.
- **À noter** : entre 20 h 56 et 20 h 58, l'utilisateur a piloté le robot depuis la page (rotations à gauche, avances). L'assistant avait remis le robot en Passive à 20 h 57 (`s`), ce qui rend les flèches sans effet jusqu'au prochain `f`. Le robot a cessé de répondre vers 20 h 57 min 40 s, sans ordre de l'assistant.

## 18. Enquête sur la coupure de 20 h 57, firmware v4, position du robot (2026-11-09, 21 h 05 à 22 h 10)

Demande de l'utilisateur : « rien n'a bougé physiquement, mène ton enquête » ; le robot « s'est remis à fonctionner après avoir clignoté » (vidéo de 21 h 04 : anneau du bouton CLEAN qui pulse) ; puis étape 2.

**Chronologie reconstituée** (journal de la carte relu dans la transcription de la session) :

| Heure | Fait |
|---|---|
| 20 h 56 min 10 s à 58 s | trois redémarrages de la carte (trois envois du programme), robot en Safe |
| avant 20 h 57 min 36 s | « Query List (149) : 0 octet(s) sur 38 en 600 ms, lecture paquet par paquet désormais », moins de 40 s après le démarrage |
| 20 h 57 min 38 s | `s` envoyé par l'assistant alors que l'utilisateur pilotait (roues en mouvement) : robot en Passive ; une lecture complète réussit encore (mode 2), puis plus rien une seconde plus tard ; dans ces deux secondes, quatre « Tourne à gauche (150 mm/s) » partent de la page, puis deux « Safe » |
| 20 h 58 min 47 s | test des fils : les trois reliés, RX2 **tenu haut par le robot** ; aucune réponse à 115200 ni à 19200 bauds |
| 21 h 04 | vidéo : l'anneau CLEAN pulse |
| 21 h 07 | robot joignable, mode Safe ; charge affichée 1 603 mAh, contre 1 845 mAh à 20 h 48 |

**Piste « octet 7 », annoncée puis écartée.** L'ancienne lecture envoyait souvent l'octet 7 (numéro du paquet « pare-chocs »), qui est l'ordre Reset d'après la documentation du Create 2. Essais faits avec le nouveau programme, sans mouvement :

| Essai | Résultat |
|---|---|
| liaison ouverte (Safe), « 142, 7 » | un octet `00` en retour (réponse normale), robot inchangé |
| liaison fermée par `x`, puis 14 s de nouvelle lecture | silence, aucun redémarrage |
| liaison fermée, « 142, 7 » | rien ; à la réouverture (`s`) les compteurs des roues sont intacts (8 577 / 6 281 puis 8 578 / 6 282) |
| liaison ouverte (Passive), octet 7 seul | rien : robot toujours joignable, mode et compteurs inchangés |

Conclusion : **sur ce 694 l'octet 7 ne provoque rien.** Les deux touches d'essai ont été retirées du programme.

**Autres pistes essayées, sans mouvement, toutes négatives :**

- ordre d'arrêt des roues (vitesses nulles) envoyé trois fois en Passive : aucun effet ;
- ordre refusé dans le mauvais mode : l'ordre des voyants (139) envoyé en Passive avec les données 142, 22, 0 ne ramène aucun octet, alors que « 142, 22 » seul ramène la tension (`3B 8D`, 15 245 mV). Le robot avale donc bien les données d'un ordre qu'il refuse, il ne les lit pas comme de nouveaux ordres ;
- retour en Passive (`s`) après 5 min 46 s d'immobilité en Safe : le robot répond encore 40 s après.

**Ce qui reste non expliqué.** Le déclencheur de 20 h 57 n'est pas reproduit. Seul point commun avec l'épisode du 2026-11-08 (§ 8) : des flèches (ordres de roues non nuls) reçues par un robot en Passive. Cet essai-là demande l'accord de l'utilisateur (c'est un ordre de roues, même si le robot ne doit pas bouger en Passive) : pas fait. Entre 20 h 57 et 21 h 07 le robot est probablement passé par un arrêt complet suivi d'un redémarrage : sa charge affichée a sauté de 1 845 à 1 603 mAh en vingt minutes (une cinquantaine de mAh attendus à 143 mA), et un saut du même genre a été vu ce soir à un réveil (ci-dessous). Ce qui l'a réveillé vers 21 h 04 n'est pas établi (bouton « Réveil » de la page, CLEAN, ou le robot seul).

**Faits mesurés pendant l'enquête :**

- **Sommeil** : le robot s'est endormi à 21 h 45 min 05 s, cinq minutes pile après la fermeture de sa liaison (`x` à 21 h 40 min 05 s), bien qu'un `s` l'ait remis en Passive entre-temps. Endormi, il ne tient plus sa ligne TXD (RX2 lue « en l'air ») : à 20 h 58 il n'était donc pas dans ce sommeil-là.
- **Réveil par la ligne BRC** (le test `n` suffit : son rappel bas l'emporte 20 ms sur celui du robot) : le robot envoie le texte « rtc configured: LSI », répond aux capteurs sans attendre `s`, puis émet seize fois par seconde cinq octets à lui, `B0 02 01 15 34` (c'est l'« octet parasite B0 » du § 4), qui brouillent une lecture sur trois. Il s'est rendormi 64 s plus tard, en Passive.
- **Deux sortes de réveil** : au premier (21 h 52, après sept minutes de sommeil) compteurs et charge sont conservés (8 578 / 6 282, 1 514 mAh) ; au second (21 h 54) les compteurs repartent de zéro (4 / 6) et la charge affichée passe de 1 512 à 1 611 mAh. Le robot réestime donc sa charge quand il redémarre vraiment.
- En Safe après un réveil par BRC, le robot reste éveillé (six minutes observées).
- `s` (Start) ajoute un pas à chaque compteur de roue.

**Défaut réel trouvé dans l'ancien programme** : l'heure d'envoi de la lecture groupée était notée « | 1 » pour ne jamais valoir zéro ; elle pouvait donc être en avance d'une milliseconde, et un passage de la boucle dans la même milliseconde calculait une attente de quatre milliards de ms : faux « délai dépassé », zéro octet, puis abandon définitif de la lecture groupée. C'est la cause probable du « non élucidé » des § 7 et § 9, et du message de 20 h 57.

**Firmware v4** (« v4 Nov 9 2026 21:57:27 », 1 109 894 octets, 84 %, aucun avertissement, envoyé par Wi-Fi) :

- lecture des capteurs par une seule requête, « 142, 100 » : les 80 octets des paquets 7 à 58, réponse complète en 13 à 17 ms (22 requêtes et 0,6 s par cycle auparavant). Repli prévu sur les groupes 6 puis 101 ; touche `q` pour essayer les trois. Lus en plus : capteur de mur, courants des moteurs, infrarouge, roulette avant (touche `e`) ;
- **les flèches ne partent plus que si le robot est en mode Safe** et vient de répondre (`wheelsAllowed`) ; sinon « Ordre de roues refusé » sur la console. Vérifié en Passive : rien n'est envoyé au robot ;
- un texte envoyé par le robot est reconnu, compté (`robot_redem` dans `/api/state`, touche `i`) et affiché ; touche `v` pour écouter la ligne deux secondes ;
- l'essai automatique à 19200 bauds ne part plus quand de bonnes lectures passent encore ; `s` pose trois fois sa question avant de conclure que le robot est muet ;
- `/api/essai?b=...` : envoi d'octets choisis pour les essais sans mouvement (refuse tout ordre de roues, de moteurs, de mode, de débit ou de nettoyage, même lu de travers) ;
- le cap du gyroscope n'est plus remis à zéro en interne par `z` (seul le cap affiché l'est), pour que la position ne saute pas.

**Étape 2 de la cartographie : position du robot** (`position.ino`, note H) :

- à chaque lecture (200 ms), distance d'après les compteurs des deux roues, direction d'après le gyroscope, déplacement ajouté dans la direction moyenne ; repère fixé à la remise à zéro (x vers l'avant du robot, y vers sa gauche, cap positif vers la gauche) ;
- déplacements écartés et comptés : silence de plus de 2 s avec plus de 20 pas, saut de compteur impossible ; robot soulevé compté et signalé ;
- tracé gardé dans la carte (800 points, un tous les 25 mm, un point sur deux gardé quand la mémoire est pleine) ; `/api/pose` (et `zero=1`), touche `0`, touche `k`, trois colonnes de plus au CSV ; `/api/tour` donne la position du robot au départ de chaque tour (`depart`) ;
- carte « Position » sur la page : tracé, point de départ, robot et son cap, x, y, chemin parcouru, écart au départ, bouton de remise à zéro. Vérifiée dans le navigateur avec un faux parcours en carré (serveur local), format téléphone ;
- calcul rejoué sur l'enregistrement du 2026-11-08 (24 m de pilotage, une mesure par seconde) : roues et gyroscope tournent dans le même sens 39 fois sur 40, les compteurs décroissent en marche arrière, les roues seules donnent 0,963 fois la rotation du gyroscope et finissent à 116° de lui ; le gyroscope reste donc la référence du cap ;
- **pas encore fait** : l'essai sur le sol (un carré piloté à la main qui doit se refermer), aucune mesure de la justesse en centimètres.

**Leçon pour l'assistant** : ne pas changer le mode du robot (`s`, `x`) pendant que l'utilisateur pilote ; regarder d'abord `driving` et les dernières lignes de la console. Et ne pas annoncer une piste comme solide avant de l'avoir essayée.

## 19. Firmware v5 : nouvelle page de pilotage, carte des obstacles, premier carré (2026-11-09, 22 h 10 à 22 h 40)

Demande de l'utilisateur : repenser la page de pilotage, « beaucoup plus belle et clean », y voir la distance mesurée par le capteur et les autres capteurs, y intégrer la carte et des analyses. But final annoncé : voir le robot en 3D dans l'appartement, lui dire dans quelle pièce aller, cibler un endroit sale en traçant un carré.

**Premier carré piloté à la main (essai de l'étape 2, fait par l'utilisateur avec le firmware v4)** : `mesures/position_20261109_222619.csv` et `.png`. Carré d'environ 45 cm de côté, 1,79 m parcourus, trois virages à gauche (cap 272,2° au gyroscope, 272,9° d'après les roues seules). Le tracé se referme à 38 mm de son départ, soit 2,1 % du chemin. Ce chiffre n'a de sens que si le robot est vraiment revenu sur sa marque de départ, ce qui n'est pas confirmé. Aucun déplacement écarté, robot jamais soulevé.

**Carte des obstacles dans le cerveau** (`carte.ino`, `/api/carte`) : à chaque écho, la tâche du radar place l'obstacle dans la pièce avec la distance, l'angle du servo, le cap du gyroscope à l'instant du tir et la position du robot. Anneau des 1 500 derniers points ; un écho à moins de 30 mm d'un des douze derniers points n'est pas rangé de nouveau ; rien au-delà de 3 m ni quand la position n'est pas fiable (robot muet ou soulevé). Réglage `dx` pour le décalage du capteur par rapport au centre du robot (0 mm par défaut, pas encore mesuré). Remettre la position à zéro efface la carte.

- Vérifié sur le matériel, robot immobile : capteur devant, 616 mm, point rangé en (616 ; 0) ; balayage ±30° par pas de 15°, points en (774 ; −447), (850 ; −228), (864 ; 231), (1102 ; 636), soit les directions −30°, −15°, +15°, +30° attendues.
- En usage réel dix minutes plus tard (l'utilisateur tourne sur place et roule, capteur devant) : 173 points en quelques minutes ; `mesures/position_20261109_223017.*` montre des arcs et des amas cohérents entre eux. Pas encore comparé à la pièce.

**Nouvelle page** (`pages.h`, 38 Ko, sans aucune ressource extérieure, thème clair ou sombre selon l'appareil) :

- sur un téléphone, le premier écran contient la distance mesurée en grand, la carte et le pavé de pilotage ; le reste est replié en dessous (batterie, capteurs du robot, réglages du capteur de distance, autres commandes, console) ;
- carte en vue de dessus ou en 3D (dessin fait par la page elle-même, on tourne autour au doigt, pincement ou molette pour approcher) : tracé du robot, obstacles vus (points, ou poteaux en 3D), robot avec son cap, rayon du capteur de distance jusqu'à l'obstacle qu'il voit, pare-chocs touché ; bouton « Suivre » ;
- un seul bouton d'état qui change selon la situation : « Réveiller le robot » (une impulsion de réveil, puis Passive, puis Safe), « Prendre la main » (Safe), « Fin de session » (arrêt des roues, Passive, puis Stop) ; les flèches sont grisées hors mode Safe ; flèches du clavier et barre d'espace sur un ordinateur ;
- alertes en clair, toujours avec une pastille et un texte : pare-chocs, roue soulevée, vide, obstacle sous le seuil, robot soulevé, déplacements non comptés, gyroscope absent, batterie faible ;
- « Tour sur place », « Nouveau départ » (position et carte à zéro) et « Effacer les obstacles » sous la carte ;
- la page ne redemande que les points nouveaux du tracé et de la carte.

Vérifiée dans le navigateur avec un faux robot (serveur local qui simule une pièce, un meuble et un balayage) : téléphone 375 px et écran large, thèmes clair et sombre, vues de dessus et 3D, rotation et zoom de la vue 3D, cas « robot muet », « flèches bloquées », pare-chocs et obstacle ; aucune erreur de script, aucun débordement horizontal. Couleurs du tracé, des obstacles et du robot passées au contrôle de lisibilité pour daltoniens (toutes les paires).

**Firmware** « v5 Nov 9 2026 22:25:31 », 1 127 638 octets (86 %), 70 552 octets de RAM, aucun avertissement, envoyé par Wi-Fi robot à l'arrêt (le tracé de l'utilisateur avait été enregistré avant : la mise à jour le remet à zéro). `/api/state` donne en plus la dernière mesure du capteur et sa direction, le résumé de la carte, le signal du capteur de mur, les courants des moteurs de roues.

**Outil** `code/outils/position_capture.py ADRESSE [DOSSIER]` : enregistre tracé et obstacles (CSV et dessin), affiche le chemin parcouru et l'écart au départ.

**Observation à creuser** : dans la minute qui a suivi le redémarrage de la carte (22 h 27), la lecture des capteurs par le groupe 100 a échoué trois fois de suite (zéro octet, alors que le robot répondait à une question simple) et une centaine d'échos ont été écartés faute de position fiable ; le programme est passé de lui-même aux groupes 6 et 101. Ensuite, plus rien : 262 lectures réussies sur 262 en 35 s, roues en mouvement ou non, capteur de distance en marche. Piste : la patte D4 tire la ligne BRC du robot vers le bas à chaque redémarrage de la carte, et le § 18 a montré qu'une impulsion sur BRC fait bavarder le robot pendant une minute (`B0 02 01 15 34`). Remède possible, à voir avec l'utilisateur : une résistance de rappel entre BRC et le 3,3 V, ou le fil de BRC sur D5.

**Vers le but final** (robot visible en 3D dans l'appartement, « va dans telle pièce », zone à nettoyer tracée au doigt) : voir la suite proposée dans la note H.

## 20. Reprise sur la branche de recherche ; robot sur sa base : le mode Safe y tient, texte « bat: », outil d'enregistrement (2026-11-10, 11 h 15 à 11 h 45)

Session locale qui reprend le rapport `reports/Roomba 694 sensor exploitation ideas.md` et son ordre de travail (consigne : [PROMPT_session_locale_2.md](PROMPT_session_locale_2.md)). Branche `claude/pensive-hopper-qmvast` ; rien n'était resté non poussé sur l'ancienne branche. Objectif redit par l'utilisateur : tirer le plus possible des capteurs actuels pour voir si le robot sait se repérer et se déplacer ; la cartographie d'abord ; plus tard le diriger (« va nettoyer autour de la table de la cuisine »).

**Décision de l'utilisateur sur l'étape 0** : pas de multimètre ni de règle pour l'instant (« les branchements et ce qu'on a fait hier avec la v5 sont bons »). Il préfère des essais sur le robot : un enregistrement pendant un pilotage, puis l'assistant prend la main. Ce que les vérifications sautées auraient tranché, et qui reste donc ouvert : le cerveau tire-t-il le fil de réveil vers le bas quand il redémarre (problème 1 du rapport) ; le fil de masse du diviseur de l'écho est-il posé (confirmé de vive voix seulement) ; la position du capteur de distance et des capteurs de vide sur le robot (problème 9) ; la roulette avant est-elle bicolore.

**État trouvé** (11 h 16, lecture seule) : cerveau en « v5 Nov 9 2026 22:25:31 », allumé à 11 h 14 min 20 s (raison « mise sous tension »), pas relié au PC (aucun port COM), sur le réseau de la maison ; gyroscope présent. Au repos sur la base, l'accéléromètre donne −0,13 / −0,04 / 1,09 g : plaque penchée de 7° environ, ou décalage de la puce ; à regarder à l'étape 1, car un gyroscope penché compte les rotations un peu court. Outils du PC : Python 3.13 avec numpy, scipy et matplotlib, arduino-cli 1.5.1. Captures : `mesures/carte_demarrage_20261110_111649.json`, `mesures/carte_ecoute_base_20261110_111911.json`.

**Le robot posé sur sa base envoie une ligne de texte par seconde** (touche `v`, qui n'envoie rien au robot) :

```
bat:   min 815  sec 43  mV 16252  mA 0  rx-byte 94  mAH 2067  state 18  mode 5
```

- « min » et « sec » comptent depuis le dernier vrai redémarrage du robot : 815 min 43 s avant 11 h 29 min 46 s, soit 21 h 54 la veille, l'heure du second réveil du § 18 (compteurs des roues repartis de zéro).
- Le firmware v5 compte ce texte comme un réveil du robot (« Le robot envoie du texte : il vient de démarrer ou de se réveiller », `robot_redem`). Ce message, apparu trois secondes après l'allumage de la carte, **n'est donc pas un indice pour le problème 1** (fil de réveil) : piste regardée puis écartée avant d'être annoncée.
- Après la fermeture de la liaison (`x`), le texte reprend en moins de 3 s ; 6 s plus tard le firmware affiche « Flux continu de capteurs (opcode 148) mis en pause (150, 0), tampon vidé », puis « Robot muet ou incompréhensible : essai automatique de la liaison à 19200 bauds... », puis « Pas de réponse à 19200 bauds non plus ». Il prend ce texte pour des lectures incohérentes : robot sur sa base, liaison fermée, le cerveau lui envoie donc de lui-même des octets (au plus toutes les 30 s). Vu aussi : la lecture était repliée sur « groupes 6 et 101 » avant l'essai ; la touche `q` l'a ramenée au groupe 100.
- **À corriger à l'étape 1** (défaut absent des douze du rapport) : reconnaître les lignes « bat: », ne pas les compter comme un réveil, ne pas lancer l'essai à 19200 bauds. C'est aussi un signal gratuit : « je suis sur ma base, liaison fermée », avec tension, courant et charge.

**Essai « le mode Safe tient-il sur la base alimentée ? »** (11 h 29, aucun ordre de roues ; fichiers `mesures/base_safe_20261110_112942_*`) :

| Heure | Touche | Résultat |
|---|---|---|
| 11 h 29 min 46 s | `s` | Passive |
| 49 s | `b` | 16 252 mV, 0 mA, 2 067 / 2 068 mAh, état de charge 4 (attente), mode lu 2 (Passive) |
| 51 s | `e` | pare-chocs droit 1, gauche 1 ; roues levées 0, 0 ; capteurs de vide 0, 0, 0, 0 ; capteurs optiques 0 partout ; infrarouge dessus 0, gauche 0, droite 0 ; sur la base : oui |
| 54 s | `q` | groupe 100 complet en 25 ms : `03 00 01 01 01 01 00 00 00 00 00 00 00 00 00 00 04 3F 7C 00 00 11 08 13 …` |
| 57 s | `f` | Safe envoyé |
| 59 s | `b` | 16 196 mV, **−72 mA**, état de charge **0** (pas en charge), **mode lu 3 (Safe)** |
| 11 h 30 min 02 s et 05 s | `e` | comme en Passive, sauf les capteurs optiques : 1 à 3 sur quatre des six ; infrarouge toujours 0, 0, 0 ; courants des roues 0, brosse −9 mA |
| 07 s | `s` | Passive ; l'état de charge revient à 4 en 1,5 s |
| 12 s | `x` | liaison fermée ; le texte « bat: » reprend |

- **Le mode Safe a tenu 10,0 s sur la base alimentée** : 21 lectures de `/api/state` de suite avec le mode 3, jusqu'à ce que l'assistant le quitte. Cela remplace l'affirmation du rapport (« by the specification a powered charger ends Safe mode », et la ligne « Driving off and onto the dock in Safe mode » de son tableau des désaccords) : sur ce 694 et sa base, le mode Safe s'obtient et se garde à l'arrêt. La charge s'arrête pendant ce temps (état 4 → 0, −56 à −72 mA). Non essayé : faire tourner les roues sur la base.
- Sur la base, les quatre bits « vide » sont levés (`01 01 01 01`, signaux à 0) et les deux côtés du pare-chocs sont enfoncés. D'après la spécification, un vide n'arrête le mode Safe qu'en marche avant, ou en marche arrière en virage serré : un recul tout droit pour quitter la base reste possible sur le papier, à essayer avec l'accord de l'utilisateur. Une avance n'aurait aucun sens, et le tour sur place est refusé (pare-chocs enfoncé).
- Les trois octets infrarouges restent à 0 sur la base, en Passive comme en Safe. Cela ne dit rien des récepteurs gauche et droit ; l'essai à 2 m devant la base reste à faire.
- En Passive sur la base, les capteurs optiques du pare-chocs lisent 0 ; en Safe, 1 à 3.
- La température de la batterie passe de 20 à 16 puis 19 °C en vingt secondes : inutilisable comme thermomètre, comme l'annonce le rapport.

**Outil `code/outils/enregistreur.py`** (nouveau) : garde la console TCP ouverte et écrit au fil de l'eau, sur l'horloge du PC, toutes les lignes de la console (`_console.txt`), le journal CSV du firmware (`_capteurs.csv`, touche `j` lancée et arrêtée par l'outil), les réponses à la touche `e` envoyée chaque seconde (`_e.csv` : infrarouge, courants des moteurs, roulette avant, surintensités, que le CSV n'a pas) et `/api/state` deux fois par seconde (`_etat.jsonl`). Arrêt propre par un fichier `_STOP`. Il n'envoie aucune touche de roues. Rappel : le firmware arrête les roues et un tour sur place quand la console TCP se ferme.

- Essai de 15 s sur la base, en Passive (`mesures/base_repos_20261110_113340_*`) : 61 lignes du journal CSV ; intervalle médian 203 ms, mais de 32 à 828 ms : première mesure de l'irrégularité de la boucle (problème 11 du rapport), ici avec la console, la touche `e` et `/api/state` en même temps. L'écart entre l'horloge du PC et celle de la carte reste dans 33 ms sur 12 s. Une lecture de `/api/state` prend 158 ms en moyenne vue du PC.
- Capteur de distance : mis en mode fixe, droit devant (`/api/radar?mode=fixe&angle=0` ; le paramètre `mode` attend `off`, `fixe` ou `balayage`, un chiffre est refusé). Sur la base il lit 128 mm.

**En cours à 11 h 40** : l'enregistreur tourne (`mesures/pilotage_20261110_113452_*`, 45 min au plus) en attendant le pilotage à la main de l'utilisateur, capteur de distance devant et arrêt automatique à 30 cm actif.

## 21. Premier enregistrement complet pendant un pilotage (2026-11-10, 11 h 39 à 11 h 45) : le robot tire à gauche, un choc le fait grimper, la base se voit à l'infrarouge

Étape 0 du rapport, gain rapide 0. Robot posé au sol par l'utilisateur, « Réveiller le robot » à 11 h 39 min 21 s, mode Safe à 11 h 39 min 24 s, pilotage au téléphone de 11 h 39 min 28 s à 11 h 44 min 25 s au réglage 150 mm/s : 22 avances (180 s), 35 rotations (56 s), un recul, **27,1 m**. Firmware v5, capteur de distance fixe devant, arrêt automatique à 30 cm actif.

- **Fichiers** : `mesures/pilotage_20261110_113452_console.txt`, `_capteurs.csv` (2 023 lignes), `_e.csv` (338 lectures de la touche `e`), `_etat.jsonl` (805 lectures de `/api/state`) ; tracé et carte du cerveau : `mesures/position_20261110_114639.csv` et `.png` (444 points de tracé, 761 obstacles).
- **Analyse** : `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/f_pilotage_enregistre.py` (nouveau, rejouable : `python f_pilotage_enregistre.py ../../../mesures pilotage_20261110_113452`), résultats bruts dans `results_f_pilotage_20261110_113452.txt`, figures `fig9` à `fig13_pilotage_20261110_113452_*.png` au même endroit.
- **Texte du robot au réveil** : « key-wakeup-any slept for 0 minutes 11 seconds 2020-05-13-1928-L r3-robot/branches/aero-sup… port:7587 CLEAN wifi-version: 3.5.62 bootloader id: 80B5 0114 4033 358… » (coupé par la console).

**L'enregistrement lui-même** : 5,96 lignes par seconde (une ligne de plus à chaque touche `e`), intervalle médian 203 ms, jamais plus de 250 ms. Écart entre l'horloge du PC et celle de la carte : 222 ms d'étendue sur 340 s, dérive de 16 ppm. En mode Safe, aucune ligne abîmée détectée sur 1 999 (saut de compteur impossible ou capteur au-delà de 4 095).

**Résultats, face aux chiffres du rapport** :

| Sujet | Rapport (estimation ou mesure du 2026-11-08) | Mesuré ce matin |
|---|---|---|
| Vitesse réelle au réglage 150 | 142,3 mm/s, soit 5 paliers de 28,5 mm/s | **149,5 mm/s** (13 avances, de 147,7 à 153,2) ; en rotation 71,6 °/s au gyroscope, pour 73,1 attendus à ±150 mm/s et 69,5 à ±142,5 |
| Roue gauche et roue droite | (non regardé) | **147,0 et 151,9 mm/s** pour le même ordre : la droite tourne 3,3 % plus vite |
| Dérive du cap en ligne droite | +1,33 ° par mètre vers la gauche, vue par le gyroscope seul | **+9,3 ° par mètre vers la gauche au gyroscope, +7,7 d'après les roues** (20,3 m, 13 avances, de +5,1 à +11,9) ; l'écart gyroscope − roues est constant : +1,69 ± 0,18 ° par mètre |
| Rapport roues / gyroscope en rotation | 0,981 ± 0,003 sur le sol principal ; 1,022 ± 0,005 sur la zone sombre à motifs | **0,987** sur le sol clair (6 rotations, 7,6 tours, de 0,976 à 0,990) ; **1,014** sur la zone à motifs (2,5 tours) |
| Bruit des capteurs de vide au repos | 2,5 par capteur, 0,9 pour la différence de deux capteurs | 4,5 à 5,1 par capteur, **0,93** pour la différence avant gauche − avant droit (9 arrêts, 340 lignes) |
| Bruit des capteurs optiques au repos | moins de 1 | 0,4 à 1,5 |
| Capteur de distance au repos | 8 mm d'une mesure à l'autre dans un palier | 4,4 mm (valeur filtrée du journal) ; « rien à portée » sur 31 % des lignes |
| Chocs sans préavis des capteurs optiques | 2 sur 7 | **2 sur 2** (le plus fort des six capteurs : 24 et 27 dans les deux secondes d'avant, leur niveau de repos) |
| Roulette avant (paquet 58) | « peut-être absente sur un 694 » | **0 sur 154 lectures en marche avant** : inutilisable sur ce robot |
| Récepteurs infrarouges gauche et droit | inconnu | 0 sur 338 lectures en mode Safe, y compris les quatre fois où le récepteur du dessus voyait la base ; non concluant tant que le robot n'a pas tourné face à la base |

- **Le robot tire à gauche.** Environ 9 ° par mètre, soit un cercle de 6 m de rayon ; l'utilisateur corrigeait par de petits coups à droite. Le 2026-11-08 la dérive était sept fois plus faible et les roues ne la voyaient pas. Cause non établie (charge posée sur le robot depuis, tension de la batterie : 16,1 V ce matin, régulation de vitesse du robot). Deux conséquences : la position reste juste, puisque le cap vient du gyroscope ; mais toute ligne droite décidée par le cerveau devra tenir son cap au gyroscope. La part que les roues ne voient pas (+1,69 ° par mètre) correspond à une roue droite qui roule 0,7 % de plus par pas que la gauche (0,55 % dans le rapport), avec une part possible du zéro du gyroscope (+0,07 °/s au repos, caché par la zone morte).
- **Les « paliers de 28,5 mm/s »** : l'idée du rapport que 150 vaut en réalité 142,5 ne tient pas ce matin. Reste à mesurer à plusieurs réglages.
- **Le choc de 11 h 42 min 22 s, ligne par ligne** : pare-chocs gauche enfoncé à 22,09 s ; les roues continuent de pousser (courants des roues 777 et 815 mA, batterie −874 mA) ; à 22,29 s la roue gauche se lève et les capteurs de vide tombent à 79, 336 et 754, ce qui ressemble à un robot qui grimpe sur l'obstacle (à confirmer par l'utilisateur, qui l'a vu) ; à 22,56 s il est en Passive. Rien ne l'annonçait : capteurs optiques à leur niveau de repos, capteur de distance à 35 cm. Le mode Safe n'arrête pas les roues sur un choc, comme le dit le rapport (problème 5) ; ici il a fallu 0,4 s et une roue levée pour que le robot s'arrête, avec le doigt de l'utilisateur sur la flèche. Le second choc (11 h 43 min 42 s, 0,2 s) n'était pas annoncé non plus.
- **L'arrêt automatique devant un obstacle n'a jamais joué** (compteurs `arrets` 0, `refus` 0) : la distance la plus courte lue en avançant est 349 mm.
- **Une lecture abîmée, en Passive** (problème 10 du rapport, vu pour la première fois) : à 11 h 42 min 25 s, trois octets `B0 1E 01` se sont glissés au milieu de la réponse de 80 octets ; les compteurs des roues lus sont faux (−20 450 et 315), le capteur optique gauche vaut 11 333, qui est en fait le compteur droit. Le cerveau a écarté ce saut, puis le saut inverse de la lecture saine suivante (« 2 déplacements non comptés »), comme le rapport l'annonçait.
- **Deux sols** : le sol principal (médiane des quatre capteurs de vide 2 634, de 2 583 à 2 657) et une zone à motifs de 4,5 m de trajet où les signaux sautent entre 800 et 2 500. Sur cette zone le courant de la batterie passe de −262 à **−338 mA** et celui des deux roues de 314 à **454 mA** : un sol qui freine. Ce que sont ces deux sols reste à demander à l'utilisateur.
- **Courants des moteurs des roues, jamais relevés jusqu'ici** : au repos 0 et 0 ; en avance 133 mA à gauche et 182 mA à droite sur le sol principal, 232 et 277 mA sur la zone à motifs ; 777 et 815 mA pendant le choc.
- **Infrarouge de la base, premiers codes relevés** : le récepteur du dessus a lu 168 (faisceau rouge) à 11 h 43 min 51, 52 et 54 s, puis 164 (faisceau vert) à 57 s, pendant une avance passant de 1,0 m à 0,45 m du point de départ ; rien aux secondes 53, 55 et 56. Entre la dernière lecture « rouge » et la lecture « verte », 21 cm de trajet : l'axe de la base est quelque part dans cet intervalle, qu'une lecture par seconde ne permet pas de resserrer.
- **Arrêt et départ** : 8 mm parcourus après l'ordre d'arrêt (de 4 à 29 mm sur 13 arrêts, à ±15 mm près) ; premier pas de roue 0,16 s après l'ordre.
- **Capteur de distance contre compteurs des roues** (deux instruments, aucune règle) : sur cinq approches de 0,7 à 1,6 m, la distance lue baisse de 1,053, 1,020, 0,937, 1,025 et 0,984 mm par millimètre roulé. Un objet de face donne 1 au plus : les deux instruments diffèrent donc de 2 à 5 % sur trois approches. Le mètre ruban dira lequel.
- **Sans valeur** : l'écart de 1,88 m entre l'arrivée et le départ (le robot n'est pas revenu à son point de départ).

**Ce que cela change dans l'ordre de travail** : l'arrêt sur pare-chocs dans le cerveau (gain rapide 6) passe devant tout déplacement que l'assistant piloterait lui-même, le choc de 11 h 42 en donne la raison ; la tenue du cap au gyroscope devient nécessaire dès la première ligne droite décidée par le cerveau ; la roulette avant sort de la liste des signaux utiles.

**Précision de l'utilisateur** (12 h 45) : les deux zones à motifs sont bien des tapis. Le choc de 11 h 42 s'est donc produit en montant sur le second tapis.

## 22. L'assistant prend la main : trois tours au même endroit, firmware v6 (arrêt sur pare-chocs), sauts pilotés depuis le PC, contact avec une paroi (2026-11-10, 12 h 45 à 13 h 15)

Demande de l'utilisateur après lecture du § 21 : « Continue, prends la main ». Il avait posé le robot à environ 0,8 m devant sa base, sur le sol principal. Suite annoncée et suivie : trois tours sur place, puis la v6, puis des déplacements pilotés par l'assistant. Analyse rejouable : `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/g_tours_sauts_approche.py`, résultats bruts dans `results_g_tours_sauts_approche_20261110.txt`, figures 14 à 16.

**Trois tours sur place au même endroit** (firmware v5, 12 h 47 à 12 h 49 ; `mesures/tour_20261110_124753`, `_124820`, `_124838`, et tous les capteurs dans `mesures/tours_20261110_124718_*`) :

| Tour | Gyroscope | Roues | Rapport roues / gyroscope | Durée | Mesures |
|---|---|---|---|---|---|
| 1 | 382,5° | 378,7° | 0,9901 | 10,8 s | 97 |
| 2 | 383,9° | 379,8° | 0,9893 | 10,7 s | 98 |
| 3 | 385,8° | 381,5° | 0,9889 | 10,9 s | 98 |

- **Un tour se répète.** Recalées l'une sur l'autre, les trois courbes distance / direction s'écartent de 3,7 à 4,4 cm en moyenne (critère du rapport pour reconnaître une station : moins de 5 cm). Le décalage qui les superpose le mieux vaut 23,6°, 24,8° et 49,2° d'après le motif de la pièce, contre 22,5°, 23,9° et 46,4° d'après le gyroscope.
- **Première mesure de l'échelle du gyroscope** (idée 1 du rapport, avec le firmware existant) : le gyroscope compte 382,5° là où le motif de la pièce en donne 383,6°, soit une échelle de **0,997** (0,9963 à 0,9977 selon la paire). La méthode vaut ±1° par paire, donc ±0,3 % : le gyroscope est juste à mieux que 1 %, sans qu'on puisse encore dire mieux. Le critère du rapport (six tours d'accord à 0,5°) demandera les tours lents de plusieurs tours.
- Rapport roues / gyroscope : **0,9895 ± 0,0006** sur ces trois tours (0,987 pendant le pilotage du matin, 0,981 dans le rapport).
- **Le tour ne tourne pas à la vitesse demandée** : 35,6 °/s et des roues à 72 mm/s pour un ordre de ±62 mm/s. La veille, le même ordre donnait 27,8 °/s. D'où 97 mesures par tour au lieu de 122.

**Infrarouge de la base pendant ces tours** (touche `e` quatre fois par seconde, soit une lecture tous les 9°) :

- **Les récepteurs gauche et droit fonctionnent sur ce 694**, en mode Safe seulement : robot posé face à la base, ils lisent tous deux 168 (faisceau rouge) ; en Passive, au même endroit, ils restent à 0 pendant que le récepteur du dessus lit 168 (15 lectures). Cela répond à la question laissée ouverte par le rapport. Les deux octets ont été identiques dans les 351 lectures : un seul récepteur regardant vers l'avant, ou deux récepteurs très proches.
- Pendant les tours, ces récepteurs avant ne voient la base que sur 10 à 23° de cap, autour de **27°** (repère du gyroscope) ; ils l'ont manquée au troisième tour, la lecture étant trop espacée. Le récepteur du dessus la voit sur 200 à 220°, centrés sur 34°, 38° et 36° : le montage posé sur le robot lui cache le reste. Le robot avait été posé face à la base au cap 24°.
- Codes lus par le récepteur du dessus : 168 (121 fois), 172 rouge et vert (38 fois), 160 (4 fois, code absent du tableau de la spécification).

**Firmware v6 : arrêt sur pare-chocs dans le cerveau** (problème 5 du rapport, gain rapide 6 ; seul changement de cette version) :

- `reflexCheck()`, appelée à chaque lecture réussie des capteurs : pare-chocs enfoncé ou roue levée pendant que les roues tournent, roues arrêtées par le cerveau (sauf pare-chocs enfoncé pendant un recul tout droit, qui est la façon de se dégager) ; le tour sur place garde son propre arrêt.
- `bumperBlocks()` : avance et rotations refusées tant que le pare-chocs est enfoncé, puis, après un arrêt réflexe, tant qu'on n'a ni reculé ni demandé l'arrêt, pare-chocs relâché. Sans ce verrou, la page, qui répète l'ordre toutes les 400 ms, renverrait le robot contre l'obstacle.
- `/api/state` : champ `reflexe` (`arrets`, `refus`, `verrou`, `cause`). Aide de la console et numéro de version mis à jour.
- Délai : au plus une période de lecture (200 ms), soit 3 cm à 150 mm/s. Limite connue : un choc plus bref que cet intervalle peut passer inaperçu ; la lecture 20 fois par seconde (gain rapide 2) le réduira.
- Compilation : 1 128 890 octets (86 %), 70 608 octets de RAM, aucun avertissement. Envoi par Wi-Fi vers 12 h 58, robot immobile en mode Safe : « v6 Nov 10 2026 12:56:04 », de retour en 4 s, raison « redémarrage logiciel (mise à jour) », robot toujours en Safe, lecture par le groupe 100, aucun texte reçu du robot.

**Outil `code/outils/pilote.py`** (nouveau) : des « sauts » commandés depuis le PC pendant qu'`enregistreur.py` tourne. Un saut est une seule touche de roues suivie de la touche d'arrêt, 1,4 s au plus. Contrôles avant chaque saut (mode Safe, pare-chocs, roues au sol, sol clair, capteurs optiques au repos, rien devant à moins de la marge) et pendant (arrêt immédiat sur pare-chocs, roue levée, sortie du mode Safe, capteur optique très fort). Un recul ne se fait que sur le terrain qui vient d'être parcouru : rien ne regarde derrière.

**Sauts aller-retour à cinq réglages** (12 h 59 à 13 h 01, `mesures/sauts_20261110_125854_*`, 22 sauts, aucune alarme, aucun refus ; sol principal, batterie à 15,9 V) :

| Réglage | En avant : roue gauche / droite | En arrière : roue gauche / droite | Rotation au gyroscope par saut arrière |
|---|---|---|---|
| 50 mm/s | 71,5 / 70,5 | 73,8 / 62,8 | +2,9° et +4,2° |
| 75 | 96,4 / 97,3 | 101,8 / 91,8 | +3,1° et +3,9° |
| 100 | 122,2 / 123,1 | 125,5 / 114,8 | +3,2° et +4,1° |
| 125 | 144,4 / 149,4 | 151,8 / 139,7 | +4,3° et +2,9° |
| 150 | 145,9 / 144,7 | 149,0 / 138,8 | +3,8° et +3,3° |

- **La vitesse réelle n'est pas la vitesse demandée** : environ 21 mm/s de plus de 50 à 125, puis un plafond vers 146 mm/s, que le réglage 125 atteint déjà. Cela remplace l'idée des « paliers de 28,5 mm/s » du rapport : ni 71, ni 97, ni 122 n'en sont des multiples. Avec la veille (57 mm/s pour un ordre de 62) et le 2026-11-08 (142 pour 150), la vitesse réelle dépend aussi du jour, sans doute de la tension de la batterie. Le cerveau ne doit donc jamais compter sur la vitesse demandée ; il ne le fait pas, la position vient des compteurs.
- **En marche arrière, la roue gauche tourne 10 mm/s plus vite que la droite**, à tous les réglages : le robot pivote de 3 à 4° vers la gauche par saut de 9 à 19 cm, soit +26 ° par mètre en moyenne. En marche avant sur ces sauts courts : +2,8 ° par mètre en moyenne, de −4 à +12.
- Rotations par sauts jusqu'à un cap voulu, avec le gyroscope comme juge (avant l'approche ci-dessous) : cible atteinte à 1,2° près au plus, en un ou deux sauts, quatre fois sur quatre.

**Approche d'une paroi jusqu'au contact** (13 h 03 à 13 h 07, `mesures/approche_20261110_130302_*`) : paroi choisie d'après les tours, à 0,98 m ; robot tourné face à elle, puis quatre sauts au réglage 100, puis des pas de 3 cm au réglage 50, l'arrêt automatique du capteur de distance étant suspendu le temps du contact, puis rétabli (`securite=1`, seuil 30 cm, vérifié).

- **Arrêt sur pare-chocs de la v6 vérifié sur un vrai contact** : au dixième pas, les deux côtés du pare-chocs s'enfoncent ; `reflexe` passe à `arrets: 1`, cause « pare-chocs, de face », verrou posé ; le saut s'arrête à 24 mm au lieu de 31 ; courants des roues à 0, courant de la batterie au plus à −294 mA (−874 mA lors du choc du matin), mode Safe gardé. Une avance redemandée contre la paroi est refusée (`refus` 0 → 1, roues immobiles). Le recul dégage le robot et fait tomber le verrou.
- **Position du capteur de distance sur le robot, par contact** (problème 9 du rapport, première mesure) : il lit **143 mm** quand le pare-chocs touche la paroi. Pour un rayon de 170 mm (valeur de catalogue), le devant du capteur est donc à 27 mm en avant du centre du robot, à l'épaisseur de la plinthe près. Le réglage `dx` de la carte vaut toujours 0.
- **Le capteur de distance et les compteurs des roues sont d'accord de près** : de 418 à 159 mm, 259 mm de baisse pour 263 mm roulés (rapport 0,986).
- **Piège vu en direct** : avant de partir, la distance lue était la même à 1 cm près en regardant 12° à droite, en face et 12° à gauche (995, 985, 1 020 mm), ce que l'assistant a pris pour une paroi plane. Pendant l'approche, la distance a d'abord baissé moins vite que le robot n'avançait (rapports 0,92, 0,97, 0,98, 0,82), puis elle est remontée de 396 à 418 mm : le capteur entendait un objet plus proche situé de côté, sorti ensuite de son faisceau. La paroi d'en face était à 1,08 m et non à 0,98 m. Une même distance sous plusieurs caps ne distingue pas un mur d'un objet ponctuel ; c'est le déplacement qui les distingue, comme l'écrit la note de recherche sur le capteur de distance.
- **Capteurs optiques contre écart au mur** (première courbe, robot immobile à chaque pas) :

| Écart pare-chocs / paroi (mm) | 275 | 239 | 207 | 175 | 144 | 110 | 75 | 45 | 16 | 0 |
|---|---|---|---|---|---|---|---|---|---|---|
| Centre gauche | 40 | 44 | 48 | 55 | 64 | 82 | 100 | 105 | 128 | 152 |
| Avant gauche | 16 | 20 | 20 | 24 | 25 | 34 | 44 | 60 | 76 | 108 |
| Centre droit | 12 | 10 | 10 | 10 | 12 | 15 | 18 | 20 | 28 | 37 |

  Le signal monte jusqu'au contact, sans l'effondrement vu le 2026-11-08, et bien moins haut (152 contre 710 à 13 cm ce jour-là) : la réponse dépend de la paroi. Le centre droit répond quatre fois moins que le centre gauche. Après le recul, à 75 mm d'écart : 99 au centre gauche, contre 100 à l'aller.
- **Erreur de l'outil, corrigée** : `pilote.py` refusait le recul tant que le pare-chocs était enfoncé (le firmware, lui, l'acceptait). Le robot est resté 78 s contre la paroi, roues à l'arrêt, avant le recul.

**Quatrième tour, près de la paroi** (station B, 13 h 07, `mesures/tour_20261110_130703`) : 380° en 11,0 s, 101 mesures, à 840 mm de la station A d'après les roues et le gyroscope ; rapport roues / gyroscope 0,9899. Dans un même repère (figure 16), les échos de B tombent sur la paroi touchée (écart médian −1 mm) ; ceux de A sont 73 mm devant, pour la raison du piège ci-dessus ; la paroi de gauche est placée au même endroit par les deux stations, à 5 cm près à l'œil.

**Fin de séance** à 13 h 08 : `s` puis `x`, capteur de distance éteint. Le robot reste à 22 cm de la paroi, hors de sa base ; batterie 1 856 mAh sur 2 068.

**Pas fait** : tenue du cap au gyroscope, lecture 20 fois par seconde, infrarouge et courants dans le journal CSV (gains rapides 2 à 4), essai du recul pour quitter la base.

## 23. Première carte : un carré de 60 cm piloté par l'assistant, six tours sur place, les murs en lignes (2026-11-10, 13 h 55 à 14 h 05)

Demande de l'utilisateur : « Carte de pièce ». Le robot n'avait pas été déplacé : le premier tour retrouve la courbe du tour de 13 h 07, au même cap à 1° près. L'espace cartographié est donc celui où il se trouvait, devant sa base. Étape 3 du rapport (idée 2), premier essai complet.

**Constats au réveil** :

- **Le cap n'a pas bougé pendant 47 minutes de repos** : le cap affiché du gyroscope valait 382,7° à 13 h 55, exactement la rotation du tour de 13 h 07 (le tour remet le cap affiché à zéro en partant ; le cap de la position, lui, valait 487,1° = 104,4° + 382,7°). Fausse piste de l'assistant, écartée avant d'être annoncée : l'écart de 104° entre ces deux caps avait d'abord été pris pour une dérive, puis pour un robot déplacé à la main ; ce sont deux origines différentes du même cap. À retenir : `imu.yaw` et `pose.cap` de `/api/state` ne se comparent pas directement après un tour ou une touche `z`.
- Texte du robot relevé par le cerveau pendant l'attente : « key-wakeup-wifi slept for 26 minutes 40 seconds » (un réveil vers 13 h 40 que personne n'a demandé, suivi d'un nouveau sommeil).
- Réveil par l'assistant : `s` seul est resté sans réponse ; une impulsion de réveil (`w`), puis `s` : le robot répond (« key-wakeup-any slept for 11 minutes 50 seconds »), puis `f`, position remise à zéro (`0`).

**Outil `code/outils/parcours_stations.py`** (nouveau) : va de point en point par sauts (rotation vers le point avec le gyroscope pour juge, avances d'1,3 s au plus, arrêt à moins de 3 cm d'après la position du cerveau), fait le tour sur place du firmware à chaque point et range ses mesures avec la position de départ dans `…_stations.json`. Il s'arrête à la première alarme ou au premier refus.

**Le parcours** (`mesures/carre_20261110_135624_*`, `mesures/tour_20261110_135646.*` pour la station 0, tracé du cerveau `mesures/position_20261110_140234.*`) : station 0 à 22 cm du mur touché à 13 h 05, puis un carré de 60 cm de côté commencé 35 cm plus loin du mur, parcouru dans l'ordre 1, 2, 3, 4, puis retour au point 1 (station 5). Réglage 75 mm/s (93 à 99 mm/s réels).

| Station | Position d'après le cerveau (mm) | Écart au point visé | Tour |
|---|---|---|---|
| 0 | (0, 0) | — | 382°, 102 mesures |
| 1 | (−298, 155) | 17 mm | 381°, 99 mesures |
| 2 | (−825, 451) | 12 mm | 382°, 99 mesures |
| 3 | (−1 108, −60) | 15 mm | 380°, 96 mesures |
| 4 | (−607, −348) | 12 mm | 382°, 100 mesures |
| 5 | (−311, 168) | 5 mm | 381°, 97 mesures |

39 sauts (23 avances pour 2,70 m, 16 rotations), aucune alarme, aucun refus, aucun arrêt réflexe ; fin de séance par `s` puis `x`, capteur de distance éteint. Le robot reste à la station 5, son centre à 54 cm du mur touché.

**La carte** (`research_notes/…/data_analysis/h_carte_stations.py`, nouveau et rejouable ; `results_h_carre_20261110_135624.txt` ; figure 17). Dans chaque tour, un palier donne un point d'un mur et sa direction ; les directions votent pour deux axes à angle droit ; les paliers qui regardent le même axe et tombent au même endroit, vus de stations différentes, forment un mur, dont la direction est ensuite ajustée pour mettre les stations d'accord. Les stations restent où le cerveau les a placées : aucun ajustement d'ensemble encore.

- Axes de la pièce dans le repère du cerveau : 57°, 147°, 237° et 327° ; 60 % des mesures de palier sont à moins de 20° de l'un d'eux.

| Mur (direction de sa normale) | Position | Vu des stations | Écart-type entre stations |
|---|---|---|---|
| 327° (le mur touché à 13 h 05) | 19 cm | 0, 1, 2, 3, 4, 5 | 3,0 cm (étendue 9,7 cm) |
| 147°, paroi proche | 158 cm | 0, 1, 5 | 0,6 cm |
| 147°, paroi lointaine | 190 cm | 1, 2, 3, 5 | 1,7 cm |
| 57°, paroi lointaine | 106 cm | 2, 3, 4 | 0,3 cm |
| 57°, paroi proche | 83 cm | 0, 2 | (deux stations) |

- **Critère du rapport** (« la position de chaque mur d'accord à 3 cm près entre stations ») : tenu pour trois murs sur quatre (0,3, 0,6 et 1,7 cm d'écart-type) ; le mur vu des six stations est à 3,0 cm d'écart-type mais 9,7 cm d'étendue. Explication probable, déjà rencontrée au § 22 : de loin, le capteur entend un objet situé 7 à 10 cm devant ce mur.
- Dimensions : **175 cm** entre le mur touché et la paroi proche d'en face, **207 cm** jusqu'à la paroi lointaine. Non comparées au mètre ruban. Le quatrième côté (237°) n'est vu que d'une station : la pièce est ouverte de ce côté.
- **Fermeture du carré** (stations 1 et 5, au même point d'après le cerveau à 18 mm près) : les deux courbes se superposent avec un décalage de 264,4° d'après le motif de la pièce contre 263,4° d'après le gyroscope, soit **1,0° d'erreur de cap après 4,7 tours de rotation cumulée**. Trois murs vus des deux tours disent que le robot est revenu 3,3, 5,3 et 3,0 cm plus près du côté 147° qu'au départ, quand le cerveau annonce 1,8 cm : erreur de position d'environ 2 cm le long de cet axe après 2,70 m. L'autre axe n'est pas observable (aucun mur vu des deux tours de ce côté). Critère du rapport (3 cm après ajustement) : tenu sur l'axe mesuré, sans même ajuster.
- **Direction de la base** : les récepteurs infrarouges avant l'ont vue aux caps 156°, 156° et 149° depuis les stations 0, 1 et 2, qui se trouvent alignées vers elle : sa direction est donc connue, pas sa distance. Les stations 3, 4 et 5 ne l'ont pas attrapée : une lecture tous les 9° est trop peu pour une fenêtre de 10 à 20°.

**Limites de ce premier essai** : six stations dans un rectangle de 60 cm, soit peu de recul pour fixer la direction des murs (ajustements de −3 à +6° autour des axes) ; rien n'est comparé au mètre ruban ; les stations ne sont pas encore ajustées ensemble sur les murs ; un meuble plan est pris pour un mur.

## 24. Firmware v7 (lecture 20 fois par seconde) et v8 (infrarouge et courants dans le journal, tour lent), puis exploration pilotée par l'assistant (2026-11-10, 14 h 55 à 15 h 40)

Demande de l'utilisateur : « v7, puis pilote toi-même et carto ». Les changements de firmware ont été faits en deux versions, chacune compilée, envoyée par Wi-Fi robot immobile, puis vérifiée à l'arrêt avant tout mouvement.

**Firmware v7** (« v7 Nov 10 2026 15:03:30 », 1 128 978 octets, 86 %) — gain rapide 2 du rapport :

- `POLL_PERIOD_MS` passe de 200 à 50 ms : le robot est lu 20 fois par seconde. L'arrêt sur pare-chocs de la v6 réagit donc en 50 ms au plus (5 mm à 100 mm/s), la position est mise à jour tous les 5 à 7 mm.
- Les lignes du journal CSV ne sont plus recopiées dans la console de la page web (elles en chassaient les vrais messages : la console ne garde que 40 lignes) ; elles vont toujours à l'USB et à la console TCP.
- **Vérifié robot immobile, en mode Safe** (`mesures/v7_repos_20261110_150504_*`, 39 s) : 779 lignes, soit **20,0 par seconde** ; intervalle médian 47 ms, 64 ms au plus, aucun au-delà de 100 ms ; lecture restée sur le groupe 100 ; âge maximal de la dernière réponse 47 ms ; aucune valeur impossible ; mode Safe gardé. La crainte du rapport (« ce robot a déjà refusé des requêtes rapprochées ») ne s'est pas vérifiée à cette cadence.
- Bruit au repos à cette cadence : capteurs de vide 3,7 à 4,1, capteurs optiques 0,8 à 1,9.

**Firmware v8** (« v8 Nov 10 2026 15:09:20 », 1 129 622 octets, 86 %, 71 184 octets de RAM) — deux ajouts indépendants, annoncés à l'utilisateur comme tels :

- **Cinq colonnes à la fin du journal CSV** (gain rapide 4, en partie) : `ir_dessus`, `ir_g`, `ir_d` (codes infrarouges de la base reçus par les trois récepteurs) et `cur_g`, `cur_d` (courants des moteurs des roues). Vérifié robot immobile : 32 colonnes, 20 lignes par seconde, `ir_dessus` à 168 (la base est en vue), courants à 0.
- **Tour sur place à vitesse réglable** : `/api/tour?go=1&v=NN`, roues de 20 à 62 mm/s demandés, pour ce tour seulement ; 400 mesures au plus (256 avant) et 45 s au plus (30 avant). La touche `t` garde 62 mm/s.
- `enregistreur.py` reconnaît le nouvel en-tête ; `pilote.py` : un recul n'est plus refusé pour un sol sombre (il refait le chemin déjà parcouru) et l'attente d'immobilité passe à 7 lignes.

**Non fait dans ces versions**, bien qu'annoncé dans le choix proposé : la tenue du cap au gyroscope pendant une ligne droite. Le pilotage par sauts corrige le cap entre deux sauts avec le gyroscope, ce qui a suffi pour atteindre les points du carré à 5 à 17 mm près ; la tenue du cap dans le cerveau reste à faire avant de longs trajets continus.

**Exploration pilotée par l'assistant** (15 h 11 à 15 h 17, firmware v8 ; `mesures/exploration_20261110_151119_*`, tracé du cerveau `mesures/position_20261110_151637.*`) :

- **Outil `code/outils/explorer.py`** (nouveau) : après chaque tour sur place, il calcule la distance libre par direction, choisit la prochaine station à 80 cm dans la direction libre qui l'éloigne le plus des stations déjà faites (rien à moins de 1,30 m dans un cône de ±25°, point visé à plus de 42 cm de tout écho, zone interdite autour de la base), y va par sauts, refait un tour, et revient à la fin par les trajets déjà faits. Chaque station retient celle d'où le robot est venu.
- **Tours lents** (`v=30`) : 380° en 16 à 17 s, soit 23 °/s (roues à 47 mm/s environ pour 30 demandés), **148 à 154 mesures par tour**, une tous les 2,5° au lieu de 3,9°.
- **Déroulé** : station 0 au point de départ (là où le carré s'était terminé), puis stations 1, 2 et 3 choisies par l'outil dans les directions 130°, 140° et 150° : (−508, 609), (−1 101, 1 103), (−1 788, 1 498) mm. En route vers une cinquième station, à 52 cm de la station 3, le pilote a refusé d'avancer : « sol sombre ou vide sous un capteur (745) ». Les deux capteurs de vide avant lisaient 1 367 et 741, les deux de côté 2 528 et 2 516 : **l'avant du robot était au bord du tapis**. Le mode Safe n'a pas bronché.
- **Défaut de l'outil, repris à la main** : pour revenir, `explorer.py` a demandé une rotation, que `pilote.py` a refusée pour la même raison (sol sombre) ; l'outil s'est arrêté là, robot immobile en mode Safe. L'assistant a fait reculer le robot d'un saut (112 mm, capteurs de vide de retour à 2 600), puis l'a ramené au départ par les stations 3, 2, 1 et 0, et a lancé le tour final. À corriger dans l'outil : après un refus pour sol sombre, reculer d'abord.
- **Bilan du parcours** : 72 sauts dont 47 avances (5,60 m), aucune alarme, aucun arrêt réflexe, aucune sortie du mode Safe ; deux refus du pilote, tous deux au bord du tapis. Retour au point de départ à (−6, 7) mm d'après le cerveau. Fin de séance par `s` puis `x`.
- **Le bord du tapis devient un repère** (idée 4 du rapport) : il se trouve sous les capteurs avant du robot quand son centre est en (−2 236, 1 747) mm, cap 151°, soit vers (−2,37 m, 1,82 m).

**La carte de l'exploration** (`h_carte_stations.py`, figure 17 `fig17_exploration_20261110_151119_carte.png`, résultats `results_h_exploration_20261110_151119.txt`) :

| Mur (direction de sa normale) | Position | Vu des stations | Écart-type entre stations |
|---|---|---|---|
| 328° (fond du couloir, derrière le départ) | 101 cm | 0, 1, 2, 3, retour | 1,4 cm |
| 238° (le mur touché à 13 h 05) | 58 cm | 0, 1, 2, retour | 2,8 cm |
| 58°, paroi lointaine (côté de la base) | 148 cm | 0, 3, retour | 2,4 cm |
| 58°, paroi proche (côté de la base) | 120 cm | 0, retour | (vue du seul point de départ, à l'aller et au retour) |

- Le fond du couloir est placé au même endroit, à 1,4 cm près, par cinq tours faits jusqu'à 2,4 m plus loin : la distance comptée par les roues le long du couloir tient donc à ce niveau.
- Largeur du couloir : 120 + 57 = **177 cm** jusqu'à la paroi proche, 148 + 57 = **204 cm** jusqu'à la paroi lointaine. Le carré de 14 h donnait 175 et 207 cm, avec d'autres stations et un autre repère : les deux cartes s'accordent à 2 ou 3 cm. Toujours rien au mètre ruban.
- **Fermeture de la boucle** (5,60 m d'avances, 4,8 tours de rotation cumulée, 6 minutes) : le cerveau se croit revenu à 9 mm de son départ ; les quatre murs vus des deux tours disent qu'il en est à **67 mm** (51 mm et 43 mm sur les deux axes), et que son cap a dérivé de **3,8°**. C'est au-delà du critère de 3 cm du rapport et dans son estimation (« 5 à 10 cm après 3 m ») : sur plusieurs mètres, la position du cerveau doit être recalée sur les murs.
- **La base confirme cette dérive** : les récepteurs infrarouges avant l'ont vue au cap 68° depuis le départ, puis au cap 64° au retour, au même endroit ; l'écart de 4° est celui que donnent les murs. Avec l'infrarouge dans le journal 20 fois par seconde, la fenêtre des récepteurs avant est décrite par 11 à 12 lectures sur 21 à 25° ; le récepteur du dessus voit la base tout autour à cette distance. Les stations 1 à 3, plus loin dans le couloir, ne voient plus la base.

**Ce que cette séance apprend pour la suite** : le robot sait aller seul de station en station et s'arrêter devant un sol qu'il ne connaît pas ; la carte par murs en lignes se répète d'un essai à l'autre à 2 ou 3 cm ; la position seule dérive de 1 % environ et le cap de 0,7 ° par minute, ce que deux repères fixes savent déjà corriger : les murs et la base.

## 25. Seconde exploration, tapis permis : huit stations, deux sur le tapis, carte d'ensemble (2026-11-10, 15 h 28 à 15 h 36)

Réponse de l'utilisateur à la question « éviter les tapis ou les traverser ? » : « Traverse-les ».

**Outils modifiés** :

- `pilote.py` : le seuil de sol sombre devient un réglage du saut (`vide_min`). 1 500 arrête le robot devant un tapis ; 150 n'arrête plus que devant un vrai vide.
- `explorer.py` : `--vide-min` ; `--reprise FICHIER_stations.json` reprend une exploration faite dans le même repère de position (ses stations comptent comme déjà faites, ses échos comme déjà vus, et le retour final passe par elles) ; `--partir-de NOM` envoie d'abord le robot sur une station reprise, par les trajets déjà faits ; un refus pour vide arrête tout mouvement. Le fichier écrit contient les stations reprises et les nouvelles, pour que la carte se calcule d'un seul coup.
- Le cerveau n'avait pas redémarré depuis la v8 et la position n'a pas été remise à zéro : les deux explorations partagent le même repère.

**Déroulé** (`mesures/exploration2_20261110_152857_*`, tracé du cerveau `mesures/position_20261110_153443.*`) : réveil par `w` puis `s`, mode Safe ; trajet vers la station 3 par les stations 1 et 2 ; station 4 au même endroit que la 3 (à 4 cm) ; puis trois stations choisies par l'outil, chacune n'ayant qu'une seule direction libre :

| Station | Position (mm) | Direction prise | Sol sous les capteurs de vide au départ du tour |
|---|---|---|---|
| 4 | (−1 753, 1 477) | — | sol principal |
| 5 | (−2 352, 988) | 220° | 2 672, 2 673, 2 613, 2 566 : sol principal |
| 6 | (−2 357, 1 778) | 90° | 945, 1 271, 1 511, 2 585 : **tapis** |
| 7 | (−2 756, 2 462) | 120° | 1 031, 1 894, 1 083, 1 239 : **tapis** |

Depuis la station 7, plus aucune direction ne remplissait les conditions (1,30 m libres dans un cône de ±25°) ; le robot est revenu de station en station jusqu'au départ, sans en trouver d'autre, puis a fait son tour final. 109 sauts dont 73 avances (9,24 m), **aucune alarme, aucun refus, aucun arrêt réflexe, mode Safe gardé du début à la fin**, y compris en montant sur le tapis et en en redescendant. 6 930 lignes à 19,95 par seconde, intervalle le plus long 197 ms. Fin de séance par `s` puis `x`.

**Le tapis, vu par les capteurs** :

- Un capteur de vide est descendu à **152** sur le tapis sans que le mode Safe ne coupe les moteurs : son seuil propre est donc plus bas. C'est le chiffre qui manquait à l'idée 4 du rapport, à un facteur près : un repère au sol peut descendre au moins jusque-là.
- Rapport roues / gyroscope pendant les tours : **1,064 et 1,040 sur le tapis**, 0,985, 0,990 et 0,991 sur le sol principal. Le tapis se reconnaît donc aussi à ce rapport, comme l'annonçait le rapport.
- Courant en avance (réglage 75) : batterie −294 mA sur le tapis contre −230 mA ; roues 204 et 229 mA contre 133 et 157 mA.

**Carte d'ensemble** (dix tours : stations 0 à 7 et les deux tours de retour ; figure `fig17_exploration2_20261110_152857_carte.png`) : neuf parois vues d'au moins deux stations, cinq d'au moins trois, d'accord entre stations à 1,1, 1,6, 1,7, 2,4 et 2,8 cm. Le fond du couloir est maintenant vu de huit stations, jusqu'à 3,9 m, à 1,6 cm près. Du côté de la base, les parois se rangent en plusieurs lignes parallèles à quelques centimètres les unes des autres : une part vient de meubles réels, une part de la dérive ci-dessous, puisque les stations ne sont pas encore recalées entre elles.

**Fermeture après les deux explorations** (15,7 m parcourus au total d'après le cerveau, 23 minutes, 10,9 tours de rotation cumulée) : le cerveau se croit à 11 mm de son départ. Les parois larges vues au départ et à la fin disent autre chose : 16,7 cm plus loin du mur du couloir, 16,0 et 13,4 cm plus près des parois d'en face, environ 1 cm le long du couloir. **L'erreur de position est donc d'environ 15 cm, en travers du couloir, soit 1 % du chemin.** L'ajustement automatique sur neuf parois donne 16 cm avec des résidus de 13 cm : il confond encore des paliers étroits, et son chiffre vaut surtout par les trois parois larges. Le cap, d'après le motif de la pièce, n'a que 1,2° d'erreur à la fin (3,8° après la première exploration) : cette mesure est moins sûre quand le robot n'est pas revenu exactement au même point. La base est vue au cap 59° au retour, contre 68° au premier passage : la somme de la dérive de cap et du déplacement de 15 cm vu à 1,2 m.

**Ce que cela dit** : l'estimation du rapport (« une carte d'appartement qui tient à 10 ou 15 cm ») est atteinte sur ce trajet sans aucun recalage ; avec le recalage sur les murs, déjà mesurable, l'erreur devrait retomber à quelques centimètres. C'est le travail suivant sur le PC : ajuster ensemble toutes les stations et toutes les parois.

## 26. Recalage des stations sur les murs, sur le PC ; le gyroscope compte un peu trop peu ; le cerveau ne répond plus ; l'exploration complète écrite et essayée en simulation (2026-11-10, 15 h 40 à 17 h 30)

Demande de l'utilisateur : « Continue avec la meilleure option la plus intelligente et novatrice pour explorer intégralement. Recale puis explore encore. » Cette section couvre le recalage, fait sur le PC à partir des dix tours déjà enregistrés ; le robot n'a pas bougé.

**Outils nouveaux** :

- `code/outils/carto.py` : la carte par murs en lignes, en module. Un palier large (15° au moins) tourné vers un des deux axes de la pièce est un mur ; les paliers étroits (objets, arêtes) ne servent ni à recaler ni à dessiner. `Carte.ajouter()` recale une station à son arrivée sur les murs déjà connus ; `Carte.ajuster()` reprend après coup toutes les stations et tous les murs ensemble (moindres carrés, avec les déplacements annoncés par le cerveau, la position des murs, un rappel doux vers les angles droits, et les retours au même endroit) ; `apparier()` compare deux tours faits presque au même endroit et donne le décalage réel entre les deux passages.
- `research_notes/…/data_analysis/i_recalage.py` : compare la carte brute, le recalage station par station et l'ajustement d'ensemble (`results_i_exploration2_20261110_152857.txt`, figure `fig18_exploration2_20261110_152857_recalage.png`).

**Résultats sur les dix tours des deux explorations** (stations 0 à 7 et les deux tours de retour) :

| | Murs partagés | Accord entre stations | Où tombent les deux retours au départ |
|---|---|---|---|
| Positions du cerveau, sans correction | 5 murs, 11 paliers | 2,4 cm (le pire 4,0) | à 1 cm du départ (faux) |
| Recalage station par station | 6 murs, 13 paliers | 0,3 cm | à 6 et 12 cm, mais dans la mauvaise direction pour le second |
| Ajustement d'ensemble | 4 murs, 12 paliers | 0,3 cm (le pire 0,6) | **à 5,8 cm puis 16,7 cm du départ**, cap corrigé de +4,1° puis +7,7° |

- **Les retours au même endroit sont la mesure la plus sûre.** Deux tours faits au même point voient les mêmes parois larges dans les mêmes directions ; la différence des distances donne le décalage, paroi par paroi. Stations 0 et premier retour : le cerveau annonce (−6, +7) mm, les parois disent (+30, +45) mm, soit 5,5 cm (3 parois d'accord). Stations 0 et second retour : (+43, +163) mm, soit 16,9 cm (4 parois). Stations 3 et 4 : 9,0 cm (2 parois). Entre les deux retours : 11,0 cm (4 parois).
- **Le recalage station par station ne suffit pas seul.** Chaque station ne revoit qu'un ou deux murs connus, et la porte de rattachement est étroite (8 cm) pour ne pas confondre un meuble et le mur qui est derrière : quand l'erreur dépasse la porte, la station crée un mur de plus au lieu de se corriger. Les murs s'accordent alors très bien entre eux et la position est quand même fausse. C'est l'ajustement d'ensemble avec les retours qui donne la bonne réponse.
- **La direction d'un palier n'est pas une boussole.** Le milieu d'un palier large donne la direction du mur à ±5° au mieux, et jusqu'à 40° d'erreur pour un palier étroit : essayé, écarté. Le cap se corrige par les différences de distance aux murs et par les retours.
- Deux murs vus de trois stations au moins après ajustement : celui du couloir à 53,9 cm du départ (stations 0, 1 et les deux retours, 0,3 cm d'écart) et un mur parallèle à 118,4 cm (stations 3, 4, 5, 6, 0,4 cm).

**Le gyroscope compte un peu trop peu.** En rejouant les deux explorations avec un cap multiplié par un facteur fixe, la position finale rejoint celle que donnent les murs :

| Facteur appliqué au cap du cerveau | Écart à la position vraie, premier retour | second retour |
|---|---|---|
| 1,0000 (le cerveau tel quel) | 56 mm | 157 mm |
| 1,0013 | 8 mm | 37 mm |
| 1,0015 | 3 mm | 45 mm |
| 1,0018 | 12 mm | 72 mm |

Le robot tourne toujours dans le même sens pendant ses tours sur place (4 289° nets en dix tours) : une erreur d'échelle de 0,15 % y fait 6° d'erreur de cap, et c'est elle qui explique l'essentiel des 16 cm. Une dérive dans le temps explique moins bien les deux retours (écarts de 17 et 43 mm au mieux, avec 0,7° par minute de mouvement), et le cap n'a pas bougé d'un dixième de degré pendant les 12 minutes de pause entre les deux explorations. **Première valeur de l'échelle du gyroscope : 1,0015 ± 0,0005**, à confirmer par un essai de plusieurs tours sur place ; elle précise le 0,997 ± 0,003 du § 22. Le PC l'appliquera dans la prochaine exploration ; la mettre dans le firmware sera un changement à part.

**Consommation** : 181 et 198 mA en moyenne pendant les deux explorations (16 et 19 mAh pour 5,3 et 5,8 minutes). La batterie du robot n'est pas la limite d'une exploration longue.

**15 h 53 : le cerveau ne répond plus.** Ni `ping`, ni page, ni port série sur le PC ; le routeur répond. Le robot dormait depuis 15 h 35 (`s` puis `x`) : aucun ordre de roues en cours, aucun risque. Cause la plus probable : la batterie portable du cerveau s'est éteinte ou vidée ; à vérifier par l'utilisateur. Conséquences : au redémarrage, le cerveau repart d'une position à zéro, et le repère des deux explorations est perdu pour lui ; il faudra que le robot se retrouve sur sa carte par un tour sur place. Et le risque décrit dans les règles devient concret : si la batterie du cerveau lâche pendant un saut, le robot garde son dernier ordre de roues.

### Suite : l'exploration complète, écrite et mise au point sans le robot (16 h 15 à 17 h 30)

Le cerveau étant resté hors ligne, la seconde partie de la demande (« explore encore », « intégralement ») a été préparée sur le PC : **rien de ce qui suit n'a encore été essayé sur le robot.**

**Outils nouveaux** :

- `code/outils/explorer3.py` : l'exploration complète. Ce qu'elle fait de plus qu'`explorer.py` est décrit en tête du fichier ; en résumé : position tenue par le PC avec l'échelle du gyroscope, obstacles réduits à un point par palier, murs en lignes avec leurs parties tenues pour pleines, sol « déjà regardé » sur une grille de 10 cm, prochaine station choisie parmi toutes les stations d'après le sol qu'elle promet de montrer, portes repérées par leurs deux montants, station faite sur place quand un trajet est arrêté, recalage en repassant par une station connue, retour au départ par l'arbre des trajets déjà faits. Mêmes sécurités qu'`explorer.py` (sauts de `pilote.py`, réflexes du firmware) ; une requête au cerveau restée sans réponse est reprise au lieu de tout arrêter.
- `code/outils/simulateur.py` : un robot simulé dans un appartement dessiné (trois mondes : deux pièces et une porte, un couloir en L, un appartement de cinq pièces avec des portes de 75 à 80 cm). Il imite ce que les mesures ont montré : un mur ne répond que vu de face, une arête de plus près, un coin rentrant de loin ; les capteurs optiques ne préviennent pas ; le cerveau compte trop peu de rotation ; le robot tire à gauche. Ce n'est pas un modèle fidèle : c'est un banc d'essai pour la logique. `python explorer3.py --simulation appartement -- sim PREFIXE`.
- `code/outils/essai_explorer3.py` : lance une exploration simulée, mesure la part du sol accessible vue d'au moins une station, et dessine le résultat.
- `carto.paliers_souples()` : paliers avec une tolérance qui grandit avec la distance, pour décider ce qui est un mur.
- `research_notes/…/data_analysis/j_rejeu_exploration.py` : rejoue la logique « à blanc » sur des tours enregistrés (`results_j_exploration2_20261110_152857.txt`, figure `fig19_exploration2_20261110_152857_rejeu.png`).

**Ce que les enregistrements et la simulation ont appris en chemin** :

1. **Le servo ne peut pas regarder sur les côtés.** L'idée de départ était de tourner le capteur de distance à ±80° à chaque saut pour suivre les murs et y voir les portes. La butée du servo est à 30° sur ce montage (fils courts, réglage voulu par l'utilisateur, § 14) : idée écartée sans toucher à la butée.
2. **Les capteurs optiques ne préviennent pas.** Dans l'approche du § 22, ils lisent 153 au plus au contact : les seuils de `pilote.py` (150 et 400) ne se déclenchent donc jamais avant le pare-chocs. Ce sont le capteur de distance, avant chaque saut, et le pare-chocs, avec l'arrêt réflexe du firmware, qui arrêtent le robot.
3. **Un mur lointain donne un palier large mais agité.** À 3,3 et 3,9 m, les vrais tours montrent des paliers de 35 à 43° dont les lectures bougent de 3 à 6 cm ; `paliers()` (tolérance fixe de 25 mm) les coupait en morceaux de moins de 15°. Avec `paliers_souples()`, les dix tours donnent 30 paliers de 25° ou plus, au lieu de 18.
4. **Le montant d'une porte, vu de face, ressemble à un bout de mur.** D'où trois règles : un pied de mur « franc » (palier de 25° au moins) vaut pour 2 m de mur, un pied « faible » pour 50 cm ; un pied faible disparaît si la station voit plus loin que le mur juste à côté ; deux repères (arêtes ou pieds faibles) à 60 à 130 cm l'un de l'autre sur la ligne d'un mur franc font une porte possible.
5. **Un même objet vu de plusieurs stations donne des points décalés de 10 à 20 cm**, qui finissaient par boucher les portes sur la carte : seul le point vu du plus près est gardé, et un point que la station de départ contredit (elle lit plus loin que lui) ne compte pas.
6. **Une direction sans écho n'est pas une direction vue.** Elle ne compte comme « regardée » que jusqu'au mur connu qu'elle longe de biais, sinon jusqu'à 90 cm.
7. **Comparer deux tours entiers ne donne pas le cap** (essai sur les quatre paires de tours faits au même endroit) : le décalage sort bien, à 1 ou 2 cm de celui des parois, mais le cap seulement à ±3°. Ce qui donne le cap, c'est un mur longé : entre deux stations de suite qui voient le même mur, la distance à ce mur ne doit changer que de ce que dit le trajet. Une mesure seule est bruitée (±1,5° en simulation) ; toutes ensemble ajustent l'échelle du gyroscope, et tout le trajet est alors recalculé.

**Essais en simulation, version finale** (échelle vraie du gyroscope simulé 1,0015 sauf mention) :

| Monde | Essais | Stations | Durée simulée | Sol accessible vu | Contacts | Retour, écart au départ | Erreur de cap finale |
|---|---|---|---|---|---|---|---|
| Deux pièces, une porte (13,7 m²) | 6 | 10 à 15 | 10 à 21 min | 100 % | 0 à 3 | 3 à 11 cm | 0 à 2°, une fois 5,5° |
| Couloir en L (13,3 m²) | 6 | 9 à 11 | 9 à 13 min | 100 % | 0 | 2 à 7 cm | 0 à 1,3° |
| Appartement de cinq pièces (38,1 m²) | 6 | 39 à 42 | 50 à 63 min | 92 à 100 % | 1 à 6 | 6 à 12 cm | 1,8 à 2,8° |
| Le même, gyroscope simulé à 1,0030 | 1 | 33 | 42 min | 96 % | 1 | 6 cm | 0,5° (échelle retrouvée : 1,0030) |
| Le même, gyroscope simulé à 1,0000 | 1 | 41 | 63 min | 100 % | 7 | 28 cm | 3,5° (échelle retrouvée : 1,0002) |

Sans l'ajustement de l'échelle en route, le même appartement avec un gyroscope à 1,0030 finissait à 30° d'erreur de cap, 16 contacts et un retour manqué : c'est ce défaut qui a fait ajouter la mesure du cap par les murs.

**Rejeu sur les huit vraies stations** (figure 19) : treize lignes de murs retenues, dont celles du couloir (53,8 cm et 121 cm du départ) ; une porte possible ; 12,5 m² de sol déjà regardés ; 91 candidats. Le premier choix part de la station 7, sur le tapis, vers 100°, 70 cm plus loin, avec 2,9 m² à voir : au-delà de la zone où `explorer.py` s'était arrêté faute de 1,30 m libres.

**Limites à garder en tête** : le simulateur a des murs lisses, des arêtes nettes et peu de meubles ; le vrai couloir montre déjà plus d'échos épars (zone du bas de la figure 19) ; les contacts y seront plus nombreux. Une heure pour 38 m² : les limites par défaut d'`explorer3.py` (40 stations, 45 minutes, 12 trajets arrêtés) coupent avant. Le point faible connu reste le cap quand peu de murs sont longés. Et tant que le cerveau est alimenté par la batterie portable, le risque de la règle (cerveau qui s'éteint pendant un saut, robot qui garde son dernier ordre de roues) est entier : à décider avec l'utilisateur avant une exploration longue.

**État en fin de séance** : cerveau toujours hors ligne à 17 h 14 ; robot endormi (`s` puis `x` à 15 h 35), là où la seconde exploration l'a laissé, sauf si l'utilisateur l'a déplacé ; rien n'a été envoyé au robot depuis.

## 27. Un plan de l'appartement issu d'un LiDAR : ce que le robot a mesuré se pose dessus (2026-11-10, 17 h 20 à 17 h 50)

La batterie du cerveau est en charge. En attendant, l'utilisateur envoie trois images de la même vue de dessus de son appartement, tirée d'un fichier LiDAR (1 214 × 434 pixels) : le plan seul (murs en traits sombres, meubles en gris) ; le même avec, en vert, le chemin des endroits atteignables et, en rouge, deux zones inatteignables ; le même avec un point vert sur la base. Ses questions : cela peut-il aider le système, et la carte finale ?

**Le plan est une donnée privée** : les images et les dessins qui les montrent sont dans `roomba694_recherche/plan_lidar/`, que le dépôt ignore (`.gitignore`). Seuls l'outil et les chiffres ci-dessous sont enregistrés. Ne pas pousser ce dossier sans que l'utilisateur le demande.

**Outil nouveau** : `research_notes/…/data_analysis/k_plan_lidar.py PLAN.png CHEMIN_DE_mesures PREFIXE --sortie DOSSIER [--base U,V --base-robot X,Y] [--trajet PREFIXE] [--zones IMAGE]`. Il cherche l'échelle, l'orientation et la position pour lesquelles la carte du robot a ses paliers sur des murs ou des meubles du plan, ses rayons libres hors des murs et ses stations sur du sol ; et pour lesquelles un trajet enregistré reste dans le sol libre, sans traverser de mur. Il écrit `PREFIXE_calage.json` (la formule qui passe des millimètres du robot aux pixels du plan) et un dessin.

**Résultat avec les dix tours des deux explorations et le trajet piloté à la main à midi (27 m, § 21)** :

| Source | Échelle |
|---|---|
| Carte du robot seule (autour de la base marquée) | 57 pixels par mètre |
| Trajet de midi seul, sans aucun a priori sur son départ | 51 pixels par mètre |
| Largeur des portes du plan (quatre ouvertures de 33 à 41 pixels, pour 71 à 81 cm) | 50 à 57 pixels par mètre |
| **Les deux ensemble** | **54 pixels par mètre (18,5 mm par pixel), entre 52 et 58** |

- Le plan fait donc environ 22,5 m sur 8,0 m ; le sol libre à l'intérieur environ 53 m², zones rouges comprises.
- Soixante paliers larges de la carte du robot : 90 % tombent à moins de 10 cm d'un mur ou d'un meuble du plan (c'est le critère de l'ajustement : ce chiffre dit que l'ajustement est cohérent, pas encore que la carte est juste à 10 cm).
- Le trajet de midi, placé sans rien lui dire, démarre à 2 m de la base, passe par les ouvertures du plan, et son repère est tourné de 52° par rapport à celui des explorations : c'est l'écart déjà estimé l'après-midi par une autre voie. Les deux calages se confirment l'un l'autre.
- La base : marquée par l'utilisateur à 84 cm de l'endroit où la carte du robot la met. Sa position dans le repère du robot n'était qu'estimée (direction par l'infrarouge, distance par le mur), et le point est tracé à la main.

**Ce que le plan apprend sur les cartes d'aujourd'hui** : ce que les sections 23 à 26 appellent « le couloir de la base » est une grande pièce double, profonde d'environ 2,9 m devant la base. Les deux parois que le robot y voit à 1,75 m l'une de l'autre seraient donc des devants de meubles, à 45 cm du mur côté base et à 70 cm du mur d'en face ; à confirmer par l'utilisateur. Les stations 6 et 7, sur le tapis, sont dans la moitié voisine de la pièce. Le capteur de distance est à une dizaine de centimètres du sol : il voit le bas des meubles, pas les murs qui sont derrière.

**À quoi le plan peut servir** :

1. **Juge.** C'est la vérité terrain qui manquait (rien n'avait été comparé au mètre ruban) : après chaque exploration, la carte du robot se pose sur le plan et l'erreur se lit en centimètres ; les zones vertes et rouges disent ce qu'il fallait atteindre.
2. **Fond de la carte finale.** Un seul capteur à ultrasons ne dessinera jamais des murs aussi nets. Le robot n'a plus à découvrir l'appartement : il lui reste à se repérer sur ce plan, ce que ses distances aux murs font bien. Les pièces et les meubles peuvent y être nommés, pour « va dans telle pièce ».
3. **Guide.** Les portes y sont : un trajet de pièce en pièce peut être préparé d'avance, au lieu de chercher les portes par leurs montants.

**Limites** : l'échelle n'est connue qu'à 5 % près, soit un mètre sur la longueur de l'appartement ; une exploration plus longue la donnera à 1 % (les roues du robot mesurent les distances). Le plan montre les meubles à toutes les hauteurs, le robot ce qui est à 10 cm du sol. Les meubles bougent.

**Pour l'essai de ce soir** : l'exploration autonome reste telle qu'elle est (`explorer3.py`) ; le plan sert à suivre le robot et à juger le résultat. Sol à explorer : une quarantaine de mètres carrés hors zones rouges, comme l'appartement simulé ; compter une heure, donc des limites plus larges que celles par défaut.

## 28. Le robot explore seul, d'abord sans le plan puis guidé par lui ; où il est vraiment passé ; la carte quadrillée (2026-11-10, 17 h 45 à 19 h 50)

Premier essai d'`explorer3.py` sur le vrai robot, l'utilisateur à côté (« ne le limite pas, je vais le surveiller »). Sept passages, 77 tours sur place, 77 m roulés. Enregistrements : `mesures/exploration3_20261110_174457_*` (passage 1) et `mesures/exploration4_20261110_180750_*` (passages a à f : `_a_stations.json` … `_f_stations.json`, le journal de chaque passage en `_X_explorer3.txt`, un seul `_capteurs.csv` d'un seul tenant de 18 h 07 à 19 h 15), `mesures/position_20261110_180056.*` et `position_20261110_191511.*`.

### Les sept passages

Les cases sont celles de la carte quadrillée décrite plus bas (lettre de la ligne, numéro de la colonne, 50 cm de côté).

| Passage | Heure | Tours | Où (cases) | Fin |
|---|---|---|---|---|
| 1 | 17 h 47 à 17 h 58 | 16 | grande pièce double de la base : de E15 à C17 devant la base, puis vers la gauche jusqu'à C7, tapis de C7 à G10 | le capteur de distance, qui dépasse du robot, heurte le dessous d'un meuble vers G9 ; l'utilisateur soulève le robot et le repose dans le couloir |
| a | 18 h 09 à 18 h 18 | 12 | croisement du couloir, de H12 à K14, pointes jusqu'à G12 et H18 | « plus rien à voir » après dix stations, à tort (voir plus bas) ; retour au départ fait |
| b | 18 h 21 à 18 h 28 | 12 | tout le couloir puis le bas de la pièce centrale, de J13 à H28 : 7,5 m en 6 minutes et demie | roue droite soulevée par un bord de tapis en H28 |
| c | 18 h 33 à 18 h 47 | 17 | pièce centrale, tout le tour : F21 à J27, puis B25 à D28 | arrêt demandé par l'assistant (`_ARRET`) |
| d | 18 h 49 à 18 h 51 | 5 | premier passage guidé par le plan : C24 à D28 | arrêt demandé |
| e | 18 h 53 à 18 h 57 | 7 | porte des pièces de droite (C29), puis descente jusqu'à H28 | arrêt demandé |
| f | 19 h 04 à 19 h 10 | 8 | devant la porte de K23, puis l'ouest de la pièce centrale, jusqu'à H20 | « pause » demandée par l'utilisateur |

### Ce que le vrai robot a appris au programme

- **Le capteur de distance dépasse** : le pare-chocs passe sous un meuble bas, la tourelle non, et aucun capteur ne le dit d'avance (17 h 59). Limite connue ; l'utilisateur préfère surveiller plutôt que d'interdire le sol proche des meubles.
- **Un arrêt mal expliqué** : la première sortie du mode Safe a d'abord été mise sur le compte d'un bord de tapis sombre ; c'était l'utilisateur qui avait soulevé le robot. La garde ajoutée pour rien (capteurs de vide sous 500) est retirée ; les passages suivants tournent avec `--vide-min 150`.
- **Le recalage sur une station connue donnait de fausses corrections** : 5 cm, une fois 18 cm avec deux murs seulement. Il n'est plus accepté que s'il s'appuie sur trois murs au moins, dans deux directions, et s'il ne dépasse pas trois fois la dérive attendue.
- **« Plus rien à voir » après dix stations** (passage a) : le programme tenait pour plein un mur sur 2 m autour d'un pied franc ; dans le vrai appartement quatorze lignes de murs et de meubles ainsi prolongées se croisaient et fermaient tout. Portée ramenée à 60 cm (pied franc) et 25 cm (pied faible).
- **Le zéro du gyroscope glisse** quand la carte chauffe : −9,76° par minute à l'arrêt, 25 minutes après la mise sous tension, une vingtaine de degrés perdus sur un passage de dix minutes. Le programme envoie maintenant `z` (étalonnage d'une seconde, robot immobile) avant chaque tour sur place.
- **Les tapis** : 9,4 m roulés sur tapis au passage 1, 7,3 m ensuite ; un bord de tapis a soulevé une roue (H28). Tapis ou sol sombre relevés en C7 à G10, H13 à K14, D27 à H28.
- **Sept appuis du pare-chocs** en 77 m (E7, D8 deux fois, K12, G28 deux fois, F21) : l'arrêt réflexe du firmware v6 a tenu chaque fois.

### Le robot guidé par le plan (passages d, e, f)

`explorer3.py --plan PLAN.png --px-par-m 53 --depart-plan U,V,CAP [--plan-passe IMAGE]` : la carte du robot est celle du plan.

- `code/outils/plan.py` (nouveau) : `Plan.localiser` pose un tour sur place sur le plan (paliers sur un mur ou un meuble, rayons libres hors des murs) ; `Plan.chemin` trace un chemin dans le sol libre, au milieu des portes ; `Plan.jalons` le découpe en étapes de 45 à 90 cm ; `Plan.fermer` note un obstacle rencontré, `Plan.ouvrir` un trajet réellement roulé, `Plan.confirmer` un mur du plan vu par le robot.
- Des destinations se donnent de l'extérieur pendant que le programme tourne : fichier `PREFIXE_CIBLES.json` (`{"serie": n, "cibles": [[u, v], …]}`, pixels du plan). Sans destination, le programme explore comme avant, dans le repère du plan. Arrêt sur place : fichier `PREFIXE_ARRET` ; retour au départ : `PREFIXE_RENTRE`. `code/outils/attendre.py` attend le tour suivant et montre la fin du journal ; `code/outils/suivi_plan.py` dessine un passage sur le plan.
- En simulation (`essai_explorer3.py MONDE DOSSIER --plan --cibles "x,y;…"`) : destinations atteintes à 3 à 5 cm et 1° près.
- Sur le robot : la destination « devant la porte de K23 » atteinte en trois étapes (19 h 07). Deux refus utiles : dans la porte des pièces de droite (C29), un obstacle à 21 à 32 cm, trois essais, destination abandonnée ; devant K23, une surface plane à 68 cm sur toute la largeur — la porte est fermée.
- **Le trait vert de l'utilisateur n'est pas un relevé** : il entrait dans la pièce de K23 à travers son mur, à un mètre de la vraie porte, et le programme le tenait pour un passage sûr. Règle ajoutée : ce que le robot voit l'emporte ; un mur du plan confirmé par un tour sur place referme le passage tracé à la main.
- **Le suivi tour par tour se trompe peu à peu** : à chaque relance, le premier tour (fenêtre large : 60 cm, 25°) a dû corriger la position laissée par le passage précédent de 60 cm et 20°, puis de 43 cm et 21°.

### Le malentendu de 19 h 10, et la vérification

À 19 h 09 l'utilisateur écrit que le robot « va vers la pièce en haut à droite » et qu'il est arrêté « au seuil entre la pièce en haut à droite et la grande pièce », alors que l'assistant venait d'annoncer un départ vers « la pièce en bas à gauche ». L'assistant en conclut d'abord, à tort, que le programme se croyait au mauvais endroit (la pièce centrale est presque carrée, 4,2 m sur 4,0 m : une carte peut s'y poser à l'envers) et le dit à l'utilisateur.

Vérification, sans rien supposer : `research_notes/…/data_analysis/l_localisation_globale.py` (nouveau). Deux millions de positions et de caps de départ, partout sur les 53 m² de sol du plan ; chaque hypothèse avance de tour en tour avec le trajet compté par le cerveau, qui ne dépend d'aucune carte ; ne survivent que celles dont les paliers tombent sur le plan et dont le trajet ne traverse aucun mur (filtre à particules).

| Recherche | Résultat |
|---|---|
| Passages a à f, dans le sens du temps, départ quelque part dans le couloir sous la grande pièce (seul fait donné par l'utilisateur, à 18 h 21) | 61 tours enchaînés sans un mur traversé, notes de 0,55 à 0,87, nuage resserré à ±25 cm dès la fin du couloir ; fin en H20 |
| Les mêmes, **à rebours depuis 19 h 10, sans aucune indication** | retrouve seule le départ dans le couloir (J13, ±23 cm) et le même trajet : **1,7 cm d'écart médian** avec la recherche précédente sur les 61 tours, 10 cm au plus |
| Les mêmes dans le sens du temps, sans indication, 40 000 hypothèses | échoue : les dix premiers tours, autour du croisement, ressemblent à plusieurs endroits, et le fil se perd au passage c. Le départ ne se devine pas d'un seul côté ; la fin, si |
| Passage 1, dans les deux sens, sans indication | même trajet à 2,8 cm près (médiane), dans la grande pièce double, là où l'utilisateur l'avait dessiné |

Résultats chiffrés : `data_analysis/results_l_*.txt`. Conclusion : **la soirée n'a qu'une façon de se poser sur le plan, et le programme était au bon endroit** — à 19 h 10 il se croyait à 27 cm de la position retrouvée. Le robot est en H20, à la sortie sud-ouest de la pièce centrale, tourné vers le couloir. Le malentendu venait des noms : « la pièce en haut à droite » n'était pas la même pièce pour l'utilisateur et pour l'assistant.

Ce que la comparaison apprend en plus : pendant les passages guidés, la position tenue par le programme s'écartait de 17 cm (médiane) et jusqu'à 63 cm de la position retrouvée, et son cap de 9° (médiane) et jusqu'à 27°. Un tour sur place donne bien la position, mal le cap ; le programme corrigeait donc sa position de 5 à 13 cm à chaque station sans jamais rattraper son cap. Le filtre, lui, tire le cap de la suite des déplacements.

### La carte quadrillée

Pour ne plus se tromper de pièce, l'utilisateur demande une carte « avec des coordonnées assez précises, comme aux échecs », sur laquelle il dira d'où part le robot et où il doit aller.

- `code/outils/grille.py` : cases de 50 cm ; une case se nomme par la lettre de sa ligne (A en haut, sans I ni O) et le numéro de sa colonne (1 à gauche) : 17 lignes, 46 colonnes. Directions : droite = cap 0°, haut = 90°, gauche = 180°, bas = 270°.
- `code/outils/carte_grille.py PLAN.png DOSSIER --zones IMAGE --base U,V --global "F1.json;F2.json" --reperes F.json` : la vue d'ensemble et trois agrandissements où le nom de chaque case est écrit dans son coin ; par-dessus le plan, le trajet roulé, les tours sur place, les tapis, les appuis du pare-chocs, la base, le robot, les zones barrées par l'utilisateur et des remarques numérotées. Les dessins montrent le plan : ils restent dans `plan_lidar/`, hors du dépôt.
- Sur cette carte : base en B17 ; robot en H20, tourné vers la gauche ; porte fermée en K23 ; obstacle derrière la porte en C29 ; meuble bas vers G9 ; bord de tapis qui soulève une roue en H28.
- Parcouru ce soir : 83 cases, soit la grande pièce double, le croisement, le couloir et la pièce centrale. Pas encore vus : le bout gauche du couloir, la pièce d'en bas à gauche (K7 à Q11), la pièce derrière la porte de K23, les pièces de droite (colonnes 30 à 40).

### État à la fin

Robot en H20, session fermée (`5`, `s`, `x`), capteur de distance au repos, sécurité du capteur active (seuil 30 cm). Batterie du robot : 1 804 mAh. Le cerveau compte 75,7 m et « soulevé 2 fois, 1 déplacement non compté » (dont le transport par l'utilisateur vers 18 h).

### Pour la suite

1. L'utilisateur donne la case de départ, la direction du robot et la case objectif.
2. Au départ, chercher la position dans la case donnée et autour, cap à 45° près, au lieu de la reprendre du passage précédent.
3. Remplacer le suivi à une seule hypothèse par le filtre pendant que le robot roule (il tourne en quelques secondes pour toute la soirée), ou au moins corriger le cap d'après le sens des corrections de position.
4. L'amélioration de la page du cerveau avec la carte, demandée à 17 h 50, n'est pas commencée.

## 29. Premier trajet demandé par cases : de H20 vers la base par la porte de H12 ; mis en pause après la porte (2026-11-10, 20 h 05 à 20 h 30)

Demande de l'utilisateur, avec la carte quadrillée sous les yeux : « il part de la position de 19 h 10, droit devant, vers sa recharge, en passant par la porte en H12 ». Compris ainsi : départ en H20 tel qu'il est, couloir, porte de H12, arrêt en C17 à 85 cm devant la base ; pas d'accostage sur la base (manœuvre jamais essayée, à lui demander). Enregistrements : `mesures/exploration5_20261110_200838_*` (`_g0_` : un tour sur place sans avancer ; `_g1_` : premier départ ; `_g2_` : second départ), `mesures/position_20261110_202534.*`.

**Préparation.** Chemin tracé d'avance sur le plan, 8,8 m en onze étapes, par les destinations (322, 212), (296, 172), (368, 91) et (442, 72) en pixels, soit J13 (au bord de H13), G12, D14 et C17. Trois options nouvelles d'`explorer3.py` : `--plan-roule "F1.json;F2.json"` (les trajets déjà roulés, sortis de `l_localisation_globale.py`, sont tenus pour du sol sûr : le chemin les préfère), `--cibles-seules` (s'arrêter quand les destinations sont faites, sans explorer ensuite), `--depart-sur` (premier tour cherché dans 30 cm et 10° seulement).

**Le robot avait tourné pendant la pause.** Au réveil (20 h 08, une impulsion `w`, puis `s` et `f`), le cerveau compte −22,5° au gyroscope et −87,5° aux roues depuis 19 h 15, sans déplacement ; le capteur de distance lit 1,55 m devant au lieu de 1,27 m. Cause non établie (l'utilisateur n'a rien dit). Pour trancher sans passer par le plan : le tour sur place refait en H20 est comparé, degré par degré, à celui de 19 h 10 au même endroit ; le meilleur décalage est de −13° (écart médian de 24 cm entre les deux courbes, contre 76 cm en moyenne). Le gyroscope avait donc raison à 5° près, les roues tort : le robot regardait vers 172 à 177°, droit dans le couloir.

**Un tour sur place seul ne donne pas le cap.** Ce même tour, posé sur le plan à sa place connue, va aussi bien à 55°, à 165° et à 355° (notes 0,94, 0,94 et 0,91). Et la recherche sans a priori, lancée sur les quatre premiers tours sans lui donner le cap, a pris une fausse piste (départ vers le bas, dans la pièce barrée). Avec le cap de départ donné à ±18° (nouvelle option `--cap-depart CAP,TOLERANCE` de `l_localisation_globale.py`), elle retrouve le couloir. Le cap de départ doit donc venir d'ailleurs : du gyroscope depuis une position sûre, ou de l'utilisateur.

**Premier départ (20 h 11, `_g1_`).** Un bond de 0,9 m, puis arrêt en J16 : « capteur optique à 289 » (quelque chose à quelques centimètres d'un côté). Le programme a noté un obstacle de 25 cm de rayon dans un couloir d'un mètre de large : le couloir s'est trouvé fermé sur le plan, et il a cherché un détour par une ouverture du plan que le capteur de distance a trouvée fermée (obstacle à 33 cm). Arrêté par l'assistant. L'utilisateur envoie alors une photo : couloir libre, le robot devant une porte fermée, un chat assis au bout sur le tapis, devant un piano. Lecture de l'assistant, à confirmer : la porte fermée est celle de la pièce barrée de rouge ; ce que le robot a vu de près est le chat ou un montant de porte. La photo n'est pas gardée.

**Correction.** Quand quelque chose barre un trajet sur un sol où le robot est déjà passé, le programme attend 8 secondes et réessaie, deux fois, avant de le noter sur le plan et de chercher un détour.

**Second départ (20 h 21, `_g2_`).** Le premier tour recale le robot de 30 cm (note 0,96). Trois étapes dans le couloir jusqu'en J13, puis la porte de H12 passée d'un bond (20 h 23), puis un bond dans la grande pièce. « Pause » demandée par l'utilisateur à 20 h 25 : arrêt sur place, session fermée (`5`, `s`, `x`), capteur de distance au repos, enregistreur arrêté. 7,7 m roulés depuis 20 h 08, aucun appui du pare-chocs. Batterie 1 727 mAh.

**Où est le robot.** Le programme se croit en E12 ; la recherche indépendante sur les six tours du second départ le met en F11, 55 cm avant, juste après la porte. Le dernier tour s'accorde bien mieux avec F11 (note 0,92 contre 0,35). L'utilisateur peut trancher sur la carte.

**Ce que ce trajet confirme** : le suivi tour par tour dérive toujours. L'écart entre le programme et la recherche indépendante passe de 24 à 63 cm en six tours, et l'écart de cap de 13 à 23° ; au premier bond le robot arrive 13 cm à côté de l'endroit prévu (un cap faux de 9°), et le tour sur place ne corrige le cap que de 1°. La recherche indépendante n'est pas sûre non plus avec si peu de tours : le long d'un couloir elle peut glisser de 45 cm (elle a déplacé d'autant un point de départ pourtant bien connu). Pour la suite : la mettre dans la boucle avec le cap du gyroscope comme point de départ, et corriger le cap d'après le côté où le robot arrive.

## 30. La carte quadrillée remise à jour avec le trajet du 10 au soir (2026-11-13)

L'utilisateur demande « la carte actuelle ». Le cerveau ne répond pas ce jour-là (`/api/state` sans réponse ; sa batterie est sans doute vide depuis le 10) : la carte montre donc la dernière position mesurée, celle du 10 novembre à 20 h 25. Aucun ordre n'a été envoyé au robot.

- **Le trajet du § 29 replacé d'un seul tenant** : `l_localisation_globale.py` sur les onze tours de `exploration5` (`_g0_`, `_g1_`, `_g2_`), départ cherché dans la case H20 et autour, cap de départ 172° ± 15° (mesuré au § 29). Fin en **F11**, pixel (288, 149), cap 57° ; 95 % des hypothèses finissent dans quatre carrés voisins de 50 cm autour du dernier tour, 2 % à la place que tenait le programme. Résultat : `data_analysis/results_l_exploration5_onze_tours.txt`.
- **À rebours et sans indication, la même recherche échoue** avec onze tours seulement (elle finit dans l'ouest de la grande pièce). Le § 28 avait réussi avec 61 tours : il faut assez de tours, ou un point sûr.
- **Une limite de la recherche** : elle a fait glisser le départ de 43 cm le long du couloir, (526, 215) au lieu de (503, 213) pourtant bien connu. La fin, elle, est tenue par la porte et par la pièce.
- **Contrôle à l'œil des deux derniers tours**, dessinés aux deux places possibles : à la place donnée par la recherche, le dernier tour tombe sur le flanc d'un meuble, sur la face du mur et sur le pan coupé à droite de la porte ; à la place que tenait le programme, il ne tombe sur rien. Le robot est donc bien juste après la porte, en F11 ; le programme se croyait 55 cm plus loin.
- **Carte** : `carte_grille.py` reçoit `--robot-texte` (étiquette libre du robot, ici « robot (10 nov., 20 h 25) ») et serre l'interligne des remarques quand elles sont nombreuses. Sur la carte du jour : 76 m de trajet, 88 tours sur place, cinq remarques (la cinquième : l'arrêt de 20 h 13 en J16). Images dans `plan_lidar/` (`carte_grille_20261113.png` et `_1`, `_2`, `_3`), hors du dépôt.

## 31. Leçons des passages du 10, nouvelle localisation rejouée sur les enregistrements, conduite d'un seul tenant en simulation (2026-11-13, sans le robot)

Demande de l'utilisateur : améliorer le robot — plus de vitesse, une conduite plus fluide, et d'abord une localisation précise, « l'objectif principal » — en tirant les leçons des passages précédents. Le robot repartira de sa base ; il rebranchera le cerveau quand tout sera prêt. Tout ce qui suit est fait sur les enregistrements du 10 novembre et en simulation ; **rien n'a encore tourné sur le robot** et le firmware n'a pas changé (v8).

### Où passait le temps

| Enregistrement | Durée en mode Safe | Distance | Vitesse moyenne | En avance | En rotation sur place | À l'arrêt |
|---|---|---|---|---|---|---|
| Passage 1 (grande pièce) | 14,0 min | 17,5 m | 21 mm/s | 28 % du temps, à 75 mm/s | 34 % | 38 % |
| Passages a à f | 61,8 min | 59,8 m | 16 mm/s | 22 %, à 72 mm/s | 27 % (69 tours) | 51 % |
| Trajet H20 → F11 | 16,4 min | 7,7 m | 8 mm/s | 12 % | 18 % | 70 % (dont les pauses) |

Le robot avançait par sauts de 1,3 s, soit 12 à 15 cm, s'arrêtait, relisait sa position, repartait ; et il faisait un tour complet (17 s) tous les 60 à 90 cm. Il ne roulait qu'un quart du temps, à la moitié de la vitesse permise.

### Pourquoi le cap glissait

Mesuré sur les 75 trajets entre deux tours dont la position de référence est connue (§ 28) :

- **Le gyroscope du cerveau compte trop peu.** Le soir du 10, il manque 111° sur 23 024° comptés : il faut multiplier par **1,0045**, et non 1,0015 (§ 26, estimé sur deux retours). Par passage : de 1,0010 à 1,0072. Chaque tour sur place de 380° ajoutait donc plus d'un degré d'erreur ; avec un tour tous les 60 cm, le cap du programme glissait de 6 à 7° en six stations.
- **Sa zone morte cache les rotations lentes.** `roomba694_wifi.ino` n'ajoute rien au cap sous 0,3 °/s, contre la dérive au repos. Or le robot dévie lentement en roulant : sur 14 % des lignes où il roule, le gyroscope se tait pendant que les roues tournent.
- **Entre deux tours, le trajet compté est bon** : sur 39 avances droites de plus de 50 cm, la direction suivie s'écarte du cap de 1,4° (médiane, écart-type 2,2°) et la distance de 0,8 %. Le capteur de distance est donc bien dans l'axe du robot, et les roues mesurent bien les distances.
- **Une seule hypothèse ne se rattrape pas.** Le recalage du 10 (`caler_sur_le_plan`, fenêtre de 30 cm et 10°) ne pouvait corriger le cap que de 1 ou 2° par tour.

### Deux pistes essayées et écartées

- Juger chaque lecture du capteur de distance une à une, en roulant (« il y a quelque chose sur l'arc vu par le capteur ») : 14 à 17 cm et 7° d'erreur médiane, pire que l'ancien recalage. Le faisceau réel est plus large que le modèle (des paliers de 65°) et le cap part de travers.
- Tenir le trajet compté pour sûr à 1° près entre deux tours : 11 cm. Le plan lui-même n'est juste qu'à 10 ou 20 cm d'une pièce à l'autre ; il faut laisser le tour sur place décider.

### La nouvelle localisation : `code/outils/localiser.py`

Classe `Filtre` : 20 000 hypothèses (position, cap, erreur d'échelle du gyroscope, erreur d'échelle des roues). Elles avancent à chaque ligne du journal avec le trajet compté par le cerveau ; quand le gyroscope est muet et que le robot roule, la rotation lente est prise sur les roues. Une hypothèse qui entre dans un mur perd beaucoup ; un appui du pare-chocs doit tomber près de quelque chose. À la fin de chaque tour sur place, les paliers du tour jugent les hypothèses (la note de `plan.Plan.localiser`), après un bruit large sur le trajet (2 cm + 4 % ; 3°, parfois 8 ou 20°).

Rejeu sur toute la soirée du 10 (`research_notes/…/data_analysis/m_rejeu_filtre.py` : le filtre ne voit chaque ligne et chaque tour qu'à son tour ; 61 tours, 59,8 m ; 27 fois plus vite que le robot). L'erreur est mesurée contre les positions de référence du § 28, retrouvées après coup dans les deux sens — pas contre un mètre ruban.

| | Position, médiane | 9 fois sur 10 sous | Pire | Cap, médiane | Pire |
|---|---|---|---|---|---|
| Programme du 10 novembre, après son recalage (20 tours guidés par le plan) | 168 mm | 343 mm | 632 mm | 9,1° | 27,2° |
| Nouveau filtre, mêmes 20 tours, juste après le tour | 76 mm | 172 mm | 199 mm | 1,6° | 7,0° |
| Nouveau filtre, les 61 tours, juste après le tour | 70 mm | 168 mm | 326 mm | 1,7° | 16,7° |
| Nouveau filtre, juste avant le tour (le robot vient de rouler) | 92 mm | 197 mm | 322 mm | 2,3° | 16,4° |
| Un tour sur deux seulement donné au filtre : erreur aux tours qu'il n'a pas vus | 126 mm | 325 mm | 349 mm | 2,6° | 12,5° |
| Un tour sur trois | 128 mm | 316 mm | 463 mm | 2,8° | 12,4° |
| Départ faussé de 30 cm, 20 cm et 15° | 67 mm | 205 mm | 335 mm | 2,2° | 16,4° |

Le filtre ne décroche jamais sur ces 60 m. Tourner deux à trois fois moins souvent coûte 5 à 6 cm : c'est le prix de la vitesse, et il reste sous l'erreur de l'ancien programme qui tournait à chaque étape.

### La conduite d'un seul tenant

- `Pilote.avance(dist_mm, …)` (`pilote.py`) : l'ordre « 8 » est redonné toutes les 0,5 s (le firmware coupe les roues 1,5 s après le dernier ordre) et chaque ligne du journal est surveillée ; arrêt à la distance (en anticipant le retard du journal), sur une alarme, si le cap a tourné de 5°, si le capteur de distance voit quelque chose dans la marge, ou si le journal se tait plus d'une seconde. Les réflexes du firmware (pare-chocs, 30 cm) restent ce qu'ils sont.
- `explorer3.py` avec le plan : le filtre remplace `caler_sur_le_plan` (l'ancien reste par `--sans-filtre`) ; `--fluide` (avances d'un seul tenant), `--tour-tous-les MM` (distance entre deux tours vers une destination, 600 par défaut), `--sans-z` (le tour du firmware refait déjà le zéro du gyroscope : 1,4 s gagnée par tour), `--filtre-n`, `--base-plan U,V` (le champ infrarouge de la base n'arrête plus que les avances vers elle : il faut cela pour partir de la base). Les rotations se font à 75 mm/s au plus, quel que soit le réglage des avances. Le tour sur place accepte 20 à 62 mm/s (`tour.ino`) : `--tour-v 60` le ramène d'environ 17 s à 10 s.
- `simulateur.py` : la même avance simulée, le tour à vitesse réglable, les compteurs de roues justes en rotation (ils comptaient double).

Simulation, appartement de cinq pièces, quatre destinations, 19 à 20 m, gyroscope simulé à 1,0045 :

| Réglage | Durée | Vitesse moyenne | Erreur après un tour (médiane / pire) | Contacts |
|---|---|---|---|---|
| Comme le 10 : une hypothèse, sauts, 75 mm/s, tour tous les 60 cm | 15,1 min | 21 mm/s | 26 / 53 mm | 0 |
| Filtre seul, même conduite | 15,1 min | 21 mm/s | 18 / 38 mm | 0 |
| Filtre, avances d'un seul tenant à 150 mm/s, tour tous les 1,8 m à 60 mm/s (trois tirages) | 5,6 à 6,0 min | 55 à 59 mm/s | 25 à 28 / 35 à 90 mm | 0 |
| Le même à 100 mm/s | 6,0 min | 54 mm/s | 28 / 41 mm | 0 |

La simulation retrouve la vitesse réelle du 10 (21 mm/s), ce qui donne du crédit au gain annoncé : 2,7 fois plus vite. Passer de 100 à 150 mm/s ne gagne presque rien : le temps part maintenant dans les rotations et les tours. La simulation a aussi trouvé un défaut du filtre avant le robot : le journal n'écrit le cap qu'à 0,1° près, et les rotations lentes étaient comptées deux fois (trois contacts avec un montant de porte simulé) ; corrigé en lisant la vitesse de rotation du gyroscope (`rot_dps`).

### Ce qui n'est pas vérifié

- La référence du rejeu n'est pas une mesure indépendante ; le capteur simulé est plus propre que le vrai.
- `Pilote.avance`, le tour à 60 mm/s et la sortie de la base en marche arrière n'ont jamais tourné sur le robot.
- Trois corrections relèvent du firmware et attendent l'accord de l'utilisateur : l'échelle du gyroscope et la zone morte seulement à l'arrêt ; un ordre de roues gauche et droite séparées, pour tourner en roulant ; un tour plus rapide que 62 mm/s.

### Pour l'essai sur le robot

Robot sur sa base, cerveau rebranché. Dans l'ordre : sortie de la base par des reculs courts (jamais essayée) ; deux tours au même endroit, à 30 puis 60 mm/s, comparés ; un trajet court avec le filtre et l'ancienne conduite ; puis la conduite d'un seul tenant à 100, puis 150 mm/s.

## 32. Premier essai sur le robot de la nouvelle localisation et de la conduite d'un seul tenant (2026-11-13, 11 h 08 à 11 h 40)

Robot sur sa base, cerveau rebranché par l'utilisateur, qui surveille (« la base est un peu encombrée » : une table, un pot de plante et un tapis de sol roulé autour d'elle). Firmware inchangé (v8). Enregistrements : `mesures/exploration6_20261113_110823_*` (`_essai_tours.json`, puis six trajets `_t1_` à `_t6_`), `mesures/position_20261113_113834.*`. 26,1 m roulés d'après le cerveau, **aucun appui du pare-chocs, aucun arrêt imprévu, aucune sortie du mode Safe**.

**La sortie de la base par le programme ne marche pas.** Sur la base alimentée le mode Safe s'obtient (mode lu 3), mais deux ordres de recul à 75 mm/s restent sans effet : compteurs de roues immobiles, courant des deux moteurs à zéro, mode toujours 3. Le robot ignore les ordres de roues tant qu'il est sur ses contacts de charge. L'utilisateur l'a fait glisser de 70 cm en arrière, nez vers la base ; le robot s'était endormi en quittant la base (réveil par `w` puis `s`). Nouvel outil `code/outils/sortie_base.py`, gardé pour le jour où la base sera débranchée ou le firmware changé.

**Un tour rapide voit aussi bien qu'un tour lent** (`code/outils/essai_tours.py`, deux tours au même endroit) : à 30 mm/s, 19,7 s et 162 mesures ; à 60 mm/s, 12,7 s et 102 mesures ; les deux courbes se superposent à 13 mm près (médiane ; 326 mm pour un décalage quelconque) avec le décalage attendu (20° trouvés, 22° au gyroscope). Les tours se font désormais à 60 mm/s. Le filtre, parti d'une position donnée à 25 cm et 15° près, place le robot en C17/D17 tourné vers la base, comme l'utilisateur l'avait posé.

**Les trajets**, tous dans la grande pièce de la base, sur du sol déjà roulé le 10 :

| Trajet | Réglage | Distance | Durée | Vitesse moyenne | Remarques |
|---|---|---|---|---|---|
| t1 : C17 → E15 → D12 | filtre, sauts de 1,3 s, 75 mm/s, tour tous les 60 cm | 2,6 m | 2,0 min | 22 mm/s | 4 tours ; la conduite du 10 |
| t2 : D12 → E15 → D17 | avances d'un seul tenant, 100 mm/s | 2,9 m | 1,5 min | 32 mm/s | première avance continue : 121 mm/s réels |
| t3 : D17 → E15 → D12 | le même à 150 mm/s | 2,9 m | 1,5 min | 32 mm/s | 147 à 150 mm/s réels ; 13 rotations par à-coups |
| t4 : D12 → E15 → D17 | + rotations d'un seul tenant (`Pilote.tourne`) | 2,9 m | 1,5 min | 32 mm/s | 170° d'une traite en 3,5 s |
| t5 : boucle D17, E15, D12, E11, D14, C17 | + visée qui compense la dérive | 7,5 m | 3,6 min | 35 mm/s | 1 arrêt pour le cap sur 15 avances, mais 29 rotations : 36 % du temps |
| t6 : la même boucle | + point de passage accepté à 10 cm, fin de rotation mieux anticipée | 7,5 m | 2,8 min | 45 mm/s | 14 rotations, 13 s d'ordres de rotation au lieu de 36 |

Du 10 au 13, sur ce robot : de 16 à 21 mm/s à 45 mm/s. Sur les trajets de 3 m, la vitesse des roues ne change rien (32 mm/s à 100 comme à 150) : trois tours sur place y prennent 39 s sur 90.

**Ce que le robot a appris au programme pendant l'essai** :

- **Il tire à gauche bien plus que prévu** : 5 à 13° par mètre selon les tronçons (2° sur d'autres). Avec un arrêt dès 5° d'écart, il s'arrêtait tous les 40 cm. Désormais `aller_a` vise à côté du point, de la moitié de ce que le robot va tourner (4° au plus), d'après la dérive mesurée sur les avances précédentes : les étapes de 87 cm se font d'une traite.
- **Un point de passage à 3 cm près coûte un quart de tour** : pour 3 à 9 cm d'écart en fin d'étape, le robot pivotait de 90°, avançait de quelques centimètres et repivotait. En conduite d'un seul tenant, un point de passage est accepté à 10 cm (6 cm pour le dernier).
- **Le journal arrive parfois en retard au PC** : une rotation demandée de 98° en a fait 150, une autre de 72° en a fait 94. Quand le Wi-Fi hésite, le robot continue jusqu'à 1,5 s sur son dernier ordre. Les réflexes du firmware (pare-chocs, 30 cm) n'en dépendent pas, mais la précision des arrêts, si : c'est la raison de fond pour mettre « avance de tant » et « tourne de tant » dans le cerveau.
- **Enchaîner les destinations sans tour sur place** (essayé en simulation seulement) laissait parfois le robot simulé coincé devant une porte : gardé en option (`--enchainer`), pas utilisé.

**La localisation pendant ces trajets** : à chaque tour sur place le filtre a corrigé la position tenue par le PC de 3 à 6 cm le plus souvent, 18 cm au plus (après une étape longue en t6), et le cap de 0 à 5°. Notes des tours : 0,58 à 1,00. Il n'y a pas de mesure indépendante de l'erreur ; deux indices : le robot est revenu deux fois au même point devant la base (pixels (439, 73) puis (441, 75) pour une destination en (442, 72)), et aucune étape n'a rencontré d'obstacle là où le plan n'en montre pas. Le trajet compté par le cerveau seul finit, lui, à 75 cm de son départ après 26 m.

**État à la fin** : robot en C17, à 75 cm devant sa base, nez vers le haut-droite ; session fermée (`5`, `s`, `x`), capteur de distance au repos ; batterie 1 828 mAh. À remettre sur sa base à la main.

**Suite proposée** : une version 9 du firmware, avec l'accord de l'utilisateur — avance et rotation exécutées par le cerveau lui-même (arrêt exact malgré le Wi-Fi), roues gauche et droite commandées séparément pour tenir le cap en roulant, échelle du gyroscope corrigée et zone morte à l'arrêt seulement ; puis le même essai par la porte de H12 et le couloir.

## 33. Firmware v9 et v10 préparés : écrits et compilés, pas encore installés (2026-11-13, 11 h 45 à 12 h 10)

L'utilisateur a dit « Oui, prépare la v9 ». Sa consigne demande des changements de firmware petits et un à la fois : ce qui était annoncé comme « la v9 » est donc préparé en deux versions, à installer et vérifier l'une après l'autre, avec son accord à chaque fois. **Rien n'a été envoyé au cerveau, qui tourne toujours en v8.** Binaires : `code/roomba694_wifi/build/roomba694_v9.bin` et `roomba694_v10.bin` (dossier hors du dépôt).

**v9 — le gyroscope seulement** (`roomba694_wifi.ino`, tâche `imuTask` ; 1 129 854 octets, 86 %).

- La zone morte de 0,3 °/s ne sert plus qu'à l'arrêt : tant qu'un ordre de roues est en cours, et une demi-seconde après, toute rotation mesurée entre dans le cap (§ 31 : le gyroscope se taisait sur 14 % des lignes où le robot roulait).
- À l'arrêt complet (aucun ordre de roues depuis 1,5 s, rotation mesurée dans la zone morte), le zéro du gyroscope suit lentement la mesure (constante de temps 2,5 s). C'est ce que recommandait l'audit du firmware ; sans cela, le glissement du zéro (10° par minute le 10) entrerait dans le cap dès que le robot roule.
- `/api/state` : `imu.biais` (zéro sur l'axe vertical, °/s) et `imu.suivis`.
- Aucun ordre de roues ni aucune sécurité n'est modifié. L'échelle du gyroscope (1,0045) reste corrigée sur le PC, qui l'estime en route.

**v10 — les mouvements exécutés par le cerveau** (nouveau fichier `mouv.ino`, `/api/mouv` ; 1 141 094 octets, 87 %).

- `/api/mouv?av=MM[&v=][&cap=DEG]` : avance de MM mm (2 m au plus ; négatif : recul, 30 cm au plus) en tenant le cap au gyroscope, les deux roues commandées séparément 20 fois par seconde ; `cap` change le cap en roulant (45° au plus) ; départ progressif, ralentissement dans les huit derniers centimètres, arrêt par le cerveau. `/api/mouv?rot=DEG` : rotation sur place, ralentie dans les trente derniers degrés. `/api/mouv?stop=1`. `/api/mouv` : état.
- Sécurités : celles des flèches et du tour sur place. Refus au départ si le robot est muet, hors mode Safe, une roue soulevée, le pare-chocs enfoncé ou un choc non dégagé (sauf pour un recul), un obstacle sous le seuil du capteur de distance (avance), les roues déjà en marche. En route : les mêmes causes, une durée maximale, un robot qui n'avance pas ou ne tourne pas. Le réflexe pare-chocs de la v6 et l'arrêt du capteur de distance restent actifs et inchangés ; toute touche d'arrêt, de roues ou de mode interrompt le mouvement. Le plafond de 150 mm/s de `driveDirect` s'applique.
- Ce qui change pour la sécurité, à dire nettement : si le Wi-Fi se coupe pendant un mouvement, le robot ne s'arrête plus au bout de 1,5 s ; il va au bout du mouvement demandé (2 m au plus), sous la garde de ses réflexes. Le tour sur place se comporte déjà ainsi.
- La v10 suppose la v9 : pour tenir le cap contre une dérive lente, il faut que le gyroscope la voie.

**Côté PC** : `Pilote.avance` et `Pilote.tourne` passent par `/api/mouv` quand le cerveau le propose (`Pilote.sait_mouv`), et gardent l'ancienne façon sinon ; le PC continue de surveiller le journal et envoie `stop` pour ses propres arrêts (capteurs optiques, sol sombre, obstacle dans sa marge). Avec la v10, `aller_a` ne s'arrête pour pivoter que si le point est à plus de 35° de l'axe du robot : en dessous, le cerveau change de cap en roulant. Le filtre de localisation ne reprend plus les rotations lentes sur les roues à partir de la v9 (elles seraient comptées deux fois). `simulateur.py` : `firmware=10` simule ces mouvements.

**Simulation** (circuit de 20 m, trois tirages) : firmware 8, 70 à 71 mm/s ; firmware 10, 73 à 74 mm/s ; erreurs de position inchangées (15 à 30 mm), aucun contact. Le gain simulé est faible parce que le robot simulé ne tire que de 4° par mètre et que sa liaison n'a jamais de retard ; sur le vrai robot (5 à 13° par mètre, une seconde de retard par moments) il devrait être plus net. À mesurer.

**Non vérifié** : aucune ligne de la v9 ni de la v10 n'a tourné sur la carte ; `Pilote._mouvement` n'a tourné nulle part (le simulateur remplace `avance` et `tourne` en entier).

**Ordre d'installation proposé, chaque étape avec l'accord de l'utilisateur** : (1) v9 par Wi-Fi, robot hors de sa base et immobile : version affichée, cap stable une minute, `imu.biais` qui bouge peu, un tour sur place normal ; puis un trajet court déjà fait le matin, pour comparer. (2) v10 : robot immobile, `/api/mouv` répond, un mouvement demandé en mode passif est refusé ; puis, avec lui à côté, une rotation de 30°, une avance de 10 cm, une avance de 50 cm, et la boucle de 7,5 m.

## 34. Firmware v9 installé et vérifié (2026-11-13, 11 h 57 à 12 h 05)

Accord de l'utilisateur : « Oui, installe la v9 ». Robot en C17, hors de sa base, immobile depuis la fin du § 32 (position du cerveau inchangée). Enregistrements : `mesures/exploration7_20261113_115916_*`, `mesures/position_20261113_120240.*`.

- **Installation** par Wi-Fi (`curl -F firmware=@…/build/roomba694_v9.bin http://192.168.18.25/update`) : 10 s, « Mise à jour réussie », carte revenue en 6 s, version affichée « v9 Nov 13 2026 11:47:43 », raison du démarrage « redémarrage logiciel (mise à jour) ». Réglages du capteur de distance conservés (sécurité active, seuil 30 cm).
- **Robot immobile, une minute** : cap du gyroscope et cap de la position à 0,00° du début à la fin ; zéro du gyroscope entre +0,009 et +0,017 °/s, retouché 100 fois par seconde (`imu.suivis` : 6 072 retouches en 61 s). Aucune dérive au repos, et le zéro se suit.
- **Un tour sur place** à 60 mm/s : 12,8 s, 103 mesures, 8 paliers, comme en v8 (12,7 s, 102 mesures). Le filtre place le robot en C17, pixel (440, 73), cap 63° : là où le trajet du matin l'avait laissé ((441, 75), 63°).
- **Trajet de comparaison** C17 → E15 → D12 → E15 → C17, conduite d'un seul tenant à 150 mm/s : 5,7 m en 2,2 min, 15 mouvements (9 avances, 6 rotations), un seul arrêt pour le cap, aucun contact, aucun arrêt imprévu. Le même aller, en v8 le matin (t3), demandait 1,5 min et 13 rotations pour 2,9 m. Corrections du filtre à chaque tour : 6 à 10 cm, 1,7 à 2,5°.
- **Ce que la v9 fait voir** : pendant les avances le gyroscope compte maintenant 8,6° de dérive à gauche par mètre en moyenne (jusqu'à 10,5), contre 5,3 le matin sur les mêmes tronçons. La zone morte cachait donc environ 40 % de la dérive du robot. La visée de compensation, qui se règle sur cette mesure, en devient juste : les étapes de 88 cm se font d'une traite.
- **Le trajet compté par le cerveau seul** finit à 14,5 cm de son départ après 6,0 m (2,4 %), alors que le robot est revenu à 8 cm de son point de départ d'après le filtre ; le matin, en v8, le même compte finissait à 75 cm après 26 m.

**État à la fin** : firmware v9 sur la carte ; robot en C17, à 75 cm devant sa base, session fermée (`5`, `s`, `x`), capteur de distance au repos, batterie 1 807 mAh. La v10 (mouvements exécutés par le cerveau, § 33) est compilée et attend l'accord de l'utilisateur.

## 35. Firmware v10 installé et essayé : les mouvements exécutés par le cerveau (2026-11-13, 12 h 09 à 12 h 30)

Accord de l'utilisateur : « Oui, installe la v10 ». Robot en C17, hors de sa base, l'utilisateur à côté. Enregistrements : `mesures/exploration8_20261113_121304_*` (`_a_` : trajet de retour, `_b_` : boucle), `mesures/position_20261113_122943.*`. Outils écrits pour la séance : `outils/essai_mouv.py` (un mouvement à la fois, ce que le cerveau annonce et ce que montre le journal) et `outils/essai_cadence.py`.

**Installation** par Wi-Fi à 12 h 09 : « Mise à jour réussie », carte revenue en 6 s, version affichée « v10 Nov 13 2026 11:53:11 », `/api/mouv` répond « repos ». Réglages du capteur de distance conservés.

**Robot immobile, avant tout ordre de roues.**

- Robot endormi : `rot=5` et `av=100` refusés (« le robot ne répond pas »), roues jamais mises en marche. Cap à 0,0° pendant 20 s, zéro du gyroscope retouché 100 fois par seconde.
- Robot réveillé, en mode passif : `rot=5`, `av=100`, `av=-50` refusés (« le robot n'est pas en mode Safe (touche f) »).
- En mode Safe : `rot=0.5` et `av=5` refusés (angle, distance trop petits) ; `stop` sans mouvement en cours : sans effet.
- `/api/mouv` répond en 33 ms (médiane), 79 ms au plus.

**Rotations** (16 menées à leur terme dans la séance, de 10° à 169°) : écart à l'arrêt complet de 0,5° en médiane, 1,1° au plus. Essais isolés : 30° → 30,3° ; −30° → −30,0° ; 10° → 10,4° ; −10° → −10,6° ; 151° → 151,9° en 3,5 s ; −43° → −43,5° ; 169° → 168,9° en 4,0 s. Le cerveau coupe les roues 1,2 à 1,6° avant le but et le robot finit sur son élan. Le matin, pilotées par le PC, les rotations dépassaient de 5° et, sur un retard du Wi-Fi, de 50°.

**Avances** (19 menées à leur terme, de 100 à 893 mm) : distance trop longue de 3,9 mm en médiane, 7,2 mm au plus ; cap à l'arrivée à 0,6° du cap demandé en médiane, 2,0° au plus.

| Demande | Chemin fait | Cap à l'arrivée | Écart de cap le plus grand en route | En travers | Vitesse réelle |
|---|---|---|---|---|---|
| 100 mm à 50 mm/s | 101,6 mm | −0,8° | 0,8° | 1 mm | 72 mm/s |
| 500 mm à 100 mm/s | 503,2 mm | +0,1° | 1,4° | 4 mm | 117 mm/s |
| 500 mm à 125 mm/s | 504,6 mm | −0,2° | 1,0° | 0 mm | 136 mm/s |
| 500 mm à 150 mm/s | 500,8 mm | +1,2° | 3,8° | 17 mm | 146 mm/s à gauche, 151 à droite |
| 300 mm à 135 mm/s, par `Pilote.avance` | 303,0 mm | +0,6° | 1,5° | 1 mm | 146 mm/s |

Le matin (firmware v9, avance pilotée par le PC), le cap tournait de 8,6° par mètre, soit 4° sur 50 cm.

**Changement de cap en roulant** (`av=600,cap=30`, par `Pilote.avance`) : 604 mm, cap +30,3°, virage pris en 2,8 s sans arrêt (roue intérieure à 95 mm/s, extérieure à 150 ; 13 °/s, puis de plus en plus doucement).

**Vitesse réelle et tenue de cap.** Les vitesses réelles ci-dessus suivent la loi déjà mesurée le 10 (§ 22 : une vingtaine de mm/s de plus que demandé, puis un plafond vers 146 à 150). Elles ne dépendent pas du rythme des ordres : à 50 mm/s demandés, 70 à 74 mm/s réels que la flèche soit répétée 2, 5, 10 ou 20 fois par seconde (`essai_cadence.py`). En cours de séance j'avais annoncé le contraire à l'utilisateur (« 20 ordres par seconde font rouler plus vite ») : c'était faux, et corrigé aussitôt la mesure faite. Ce qui est nouveau : à 150 demandés les deux roues sont au plafond, la correction de cap ne peut plus accélérer une roue, et freiner l'autre n'a d'effet qu'une fois celle-ci descendue sous le plafond ; d'où 3,8° d'écart en route à 150, contre 1 à 2° à 125 et 135. `explorer3.py` ne demande donc plus que 135 mm/s quand le cerveau conduit (`V_CERVEAU`), ce qui donne 146 mm/s réels : rien n'est perdu.

**Arrêts demandés** : `stop=1` pendant une avance à 117 mm/s : roues immobiles 0,16 s après l'envoi, 11 mm parcourus ; touche `5` pendant une rotation : 0,17 s, 5° d'élan ; `stop=1` pendant une rotation : 0,13 s, 3°.

**Deux sécurités vues à l'œuvre sans les avoir cherchées.**

- **Contact du pare-chocs gauche en D14**, à 12 h 22 min 13, à 145 mm/s, pendant une avance de 612 mm : réflexe du cerveau et mouvement interrompu (« pare-chocs touché »), robot arrêté 8 mm et 0,2 s après. Rien n'avait été vu : capteur de distance entre 1,29 et 1,47 m, capteurs optiques au repos (28 à 41). Le robot était au pixel (359, 90), cap 15° ; le programme place l'obstacle au pixel (364, 82), une dizaine de centimètres sous la bande grise que le plan montre en haut de D14 : quelque chose en dépasse, que le plan ne montre pas. Le matin le robot était passé 6 cm plus bas sans toucher. À demander à l'utilisateur ce que c'est.
- Défaut du programme vu à cette occasion et corrigé : il a appliqué sa règle « quelque chose sur un passage déjà roulé : attendre 8 s » et le robot est resté **8,8 s appuyé contre l'obstacle** avant de reculer (26 cm). Après un contact, `explorer3.py` recule maintenant tout de suite ; l'attente ne vaut plus que pour un obstacle vu à distance.
- **Arrêt du capteur de distance** : en C17, une avance de 67 mm vers l'encombrement à gauche de la base s'est arrêtée à 26 mm (« obstacle devant (capteur de distance) », 28 cm).

**Trajets avec le pilote complet** (`explorer3.py`, options du matin, 135 mm/s demandés).

- E12 → D14 → C17 : 3,8 m en 1,7 min, 4 tours sur place, le contact ci-dessus puis reprise, destination atteinte.
- La boucle du matin, C17, E15, D12, E11, D14, C17 (D14 visé 11 cm plus bas, au pixel (368, 97)) : **7,5 m en 2,7 min, soit 46 mm/s** ; 6 tours sur place ; 7 rotations (539° en 14 s) et 9 avances (7,0 m en 51 s, 138 mm/s en moyenne), dont deux avec un vrai changement de cap en roulant (23° et 11°) ; aucun contact, aucun arrêt pour le cap, aucun arrêt imprévu. Le matin (t6, firmware v8) : 2,8 min, 45 mm/s, 14 rotations.
- Où passe le temps de la boucle (162 s) : les tours sur place 75 s, soit 46 % (6 fois 12,5 s, dont 1,5 s de préparation) ; les mouvements 65 s, soit 40 % ; le reste (calcul du filtre, pauses entre deux ordres) 22 s.
- Corrections du filtre aux six tours : 2 à 12 cm et 0 à 3,3°, du même ordre que le matin.
- Le compte du cerveau seul finit à 41 cm de la position donnée par le filtre après 14,4 m et 4 337° tournés vers la gauche au total (dont 0,45 % manquent au gyroscope, soit 19° : c'est le PC qui corrige cette échelle).

**Ce que ces mesures remplacent.**

- § 33, « sur le vrai robot [le gain de vitesse] devrait être plus net » : **non**. La boucle prend 2,7 min contre 2,8. La v10 apporte autre chose : des gestes justes (rotation à 1° près, distance à 7 mm près), deux fois moins de rotations, plus aucun arrêt pour redresser le cap, et un arrêt qui ne dépend plus du Wi-Fi. Le temps part maintenant dans les tours sur place.
- § 33, « `Pilote._mouvement` n'a tourné nulle part » : il a mené 27 mouvements sur le robot, dont un arrêté par le pare-chocs et un par le capteur de distance.
- `simulateur.py` supposait un virage en roulant à 20 °/s : mesuré, 13 °/s puis de plus en plus doucement. Le simulateur est aligné sur la mesure (65 à 66 mm/s sur un circuit de 12 m, 62 en firmware 8).

**Défauts vus, pas encore corrigés.**

- Après une avance avec changement de cap, le robot arrive à côté du point visé, de 4 à 9 cm : le cerveau vise un cap, pas un point, et le virage décale la trajectoire. Il faut alors une rotation et quelques centimètres pour finir (mouvements 27 et 28), ou une rotation devenue inutile juste avant un tour (mouvement 35). Remède à proposer : une v11 où le cerveau vise le point lui-même, en recalculant son cap en route d'après sa position.
- Chaque tour sur place commence par 1,5 s de préparation (zéro du gyroscope) qui ne sert plus depuis la v9.

**Non vérifié** : ce qui se passe si le Wi-Fi se coupe pendant un mouvement ; les arrêts sur roue soulevée, sortie du mode Safe, durée maximale et robot bloqué (aucun ne s'est produit).

**État à la fin** : firmware v10 sur la carte ; robot en C17, pixel (443, 61), cap 98°, face à sa base et à 65 cm d'elle ; session fermée (`5`, `s`, `x`) à 12 h 29, capteur de distance au repos (sécurité active, seuil 30 cm), vitesse remise à 150, batterie 1 752 mAh.

## 36. « Amène le robot en K9 » : la porte H12, un passage de 47 cm, une zone jamais vue (2026-11-13, 12 h 42 à 13 h 10)

Demande de l'utilisateur : « amène le robot en K9 ». Robot en C17 devant sa base (inchangé depuis le § 35), firmware v10. Enregistrements : `mesures/exploration9_20261113_124811_*` (`_a_` : jusqu'à la porte ; `_b_` : la porte ; `_c_` : point d'observation ; `_essai_tours.json` : tour final), `mesures/position_20261113_131023.*`. Carte : `plan_lidar/carte_grille_20261113_k9*.png` (hors dépôt).

**Préparation.** K9 est sous le mur de la grande pièce, à l'ouest de la porte H12 : zone jamais explorée, mais sur le trait vert de l'utilisateur. Le chemin du planificateur (7,2 m, 8 étapes) suit ce trait, qui rase le montant ouest de la porte puis la pointe d'un élément en biais : j'ai donné mes propres points de passage, au milieu de la porte et au large de la pointe.

**De C17 à la porte** (`explorer3.py`, options du § 35) : C17 → D14 (pixel (368, 97)) → E12 → G12, 3,8 m en 1,6 min, 4 tours sur place, aucun contact. Le balayage fait en G12 concorde avec le plan : l'ouverture de la porte est vue entre les caps 280° et 300° (2,26 m), là où le plan la prédit depuis la position du filtre ; le meuble bas de G9 est à 1,2 m à l'ouest.

**La porte H12** (100 mm/s demandés) : contact du pare-chocs gauche dans l'ouverture à 12 h 52 min 57, à 114 mm/s ; arrêt en 6 mm ; recul immédiat (correctif du § 35 : 0,84 s d'appui au lieu de 8,8 s à midi), tour sur place, second essai réussi. Cause : le robot est parti avec 22° d'écart de cap, pris en roulant ; le virage l'a décalé vers l'est et son côté gauche a touché le montant est. Le plan montre là un liseré gris que j'avais négligé : l'ouverture libre est plus étroite que ses traits sombres (68 cm) ne le font croire, et son milieu est vers u = 305 plutôt que 308.

- Corrigé dans `explorer3.py` : quand le cerveau conduit, le robot pivote d'abord dès que l'écart de cap dépasse 15° (35° avant) ; en simulation, 63 à 68 mm/s, comme avant.
- Corrigé dans `Pilote._mouvement` : le côté du contact est lu dans le journal (le cerveau dit seulement « pare-chocs touché », et ce contact avait été noté droit devant).

**Le passage vers l'ouest.** Balayage depuis le sud de la porte, puis regards cap par cap, robot à l'arrêt, depuis deux points (nouvel outil `outils/passage.py`).

- Le battant de la porte H12 est ouvert à angle droit vers le sud. Son chant ne renvoie un écho que dans l'axe du capteur (caps 172° à 179°, à 44 cm) : le tour sur place ne l'avait attrapé qu'une fois sur cent mesures.
- Le bout du mur d'en face se voit de 205° à 241°, à 64 cm.
- Entre les deux : 47 cm (45 à 52 selon l'incertitude), pour un robot de 34 cm. Le « point » isolé que le plan montre en J11 est sans doute ce chant ; le chemin du planificateur passait dessus.

Franchissement : robot placé à l'estime dans l'axe (2,2 m libres droit devant, bords à 23 cm de part et d'autre), puis 98 cm en ligne droite à 50 mm/s demandés (72 réels) : aucun contact, capteurs optiques à 60 au plus.

**Arrivée.** À 27 cm du but, contact du pare-chocs droit (13 h 05, 94 mm/s, arrêt en 4 mm, appui de 0,14 s : l'objet a cédé ou le robot a rebondi ; capteur optique avant droit à 373 juste avant) : un coin de meuble ou un pied de chaise à la limite de J10 et K10. Recul de 12 cm, regards au capteur, contournement par le sud-ouest en deux avances (24 et 21 cm). Tour sur place final : objets fins à 18 à 20 cm du centre du robot au nord et à l'ouest-nord-ouest (2 à 3 cm de sa coque), un autre à 25 cm au sud-sud-ouest, une grande surface à 70 cm à l'ouest. Je n'ai pas avancé davantage.

**Où est le robot.** À l'estime depuis le dernier calage : pixel (234, 256). Le filtre, sur le tour final : pixel (240, 251), case K10 à 3 cm près, note 0,52, étalement 38 cm (les objets proches ne sont pas sur le plan). Les obstacles vus ou touchés à l'ouest de la porte (bout du mur, chant du battant, coin de meuble) sont tous 5 à 10 pixels plus au nord sur le plan que là où l'estime les place. Position retenue : pixel (236, 251), **en K9, à 5 cm de la limite avec K10**, à 10 cm près. Aucun autre juge que les capteurs du robot. **Corrigé au § 37 : l'utilisateur a vu le robot en K10 ; c'est le filtre qui avait raison.**

**Ce que ces mesures remplacent ou apprennent.**

- § 29, « porte H12 passée » (deux fois le 10, sans contact) : cela ne disait rien de la marge. L'ouverture libre fait moins de 70 cm et un virage pris en roulant suffit à toucher un montant.
- Le plan n'est pas fiable à 10 cm près pour ce qui bouge (battant, chaise) ni pour les meubles bas ou à pieds : la zone grise de J7 à J10 laisse passer le capteur de distance jusqu'au mur (1,05 m), et son coin arrête le pare-chocs.
- Le trait vert ne doit pas l'emporter sur la distance aux murs : `Plan.chemin` donne au trait le coût du sol libre même contre un mur. À corriger, pas fait.
- Un chant de porte est presque invisible au tour sur place : avant un passage étroit, regarder cap par cap, à l'arrêt.

**Non fait, non vérifié** : le retour ; `passage.py` suit la position à l'estime et ne connaît pas le plan ; le seuil de 15° n'a tourné qu'en simulation.

**État à la fin** : robot annoncé en K9 (pixel (236, 251)), en réalité en K10 (§ 37), cap 193° (vers la gauche), immobile entre des objets fins ; session fermée (`5`, `s`, `x`) à 13 h 10, capteur de distance au repos, vitesse 150, batterie 1 685 mAh ; 8,3 m parcourus depuis C17, mode Safe jamais quitté, sol clair partout (signal le plus bas : 2 453). Pour revenir : le même passage en sens inverse (se remettre dans l'axe à l'estime, regarder, passer), puis la porte H12 en visant u = 305, robot aligné avant d'avancer.

## 37. Le robot était en K10, pas en K9 ; retour de K10 à C17 sans contact (2026-11-13, 13 h 22 à 13 h 33)

Message de l'utilisateur : « tu es bien en K10, devant ma chaise », et « continue dans cette session pour la navigation ». Il a aussi demandé une session à part pour une carte qui suit le robot en direct : elle est lancée, en lecture seule vis-à-vis du robot, et n'écrit que dans `code/carte_vivante/`. Enregistrements du retour : `mesures/exploration10_20261113_132251_*`, `mesures/position_20261113_133311.*`. Carte : `plan_lidar/carte_grille_20261113_retour*.png` (hors dépôt).

**Ce que son observation remplace** (nuancé au § 38 : il a précisé ensuite « K9, K10, peut-être entre les deux »)**.** Le § 36 retenait le pixel (236, 251), « en K9 à 5 cm de la limite », d'après l'estime et les obstacles. C'était faux : le robot était en K10. Le filtre, qui le plaçait au pixel (240, 251) avec une note de 0,52 et 38 cm d'étalement, avait raison ; l'estime était 10 cm trop à l'ouest, et je l'avais préférée. K9 est occupée par sa chaise : les objets fins vus à 2 ou 3 cm de la coque en sont les pieds.

**Retour, à l'estime depuis la position du filtre** (`outils/passage.py`, départ au pixel (240, 251), cap 216°).

- Sortie par le chemin d'arrivée, en trois avances (22, 25 et 15 cm), sans contact.
- À l'ouest du passage, regards vers l'est : le bout du mur à 34 cm au cap 315° (pixel (281, 250) : le coin que montre le plan), le chant du battant à 34 cm au cap 49° (pixel (281, 225) : c'est bien le « point » isolé du plan, à 5 pixels près). Largeur mesurée de ce côté : 49 cm (47 à l'aller).
- Un objet immobile vu à 89 cm droit devant, de l'autre côté du passage (pixel (320, 244) environ). À l'aller le robot s'était arrêté tout près de lui (quelques centimètres, d'après les positions) sans le voir : aucun capteur ne regarde sur le côté.
- Passage vers l'est : 56 cm à 50 mm/s demandés, arrêt avant l'objet ; aucun contact, capteurs optiques à 53 au plus.
- Porte H12 vue du sud : vue dégagée de 89° à 113° (3,6 m), montant est à 60 cm au cap 60° (pixel (322, 187) : le liseré gris du plan), montant ouest à 53 cm vers 133° (le coin (290, 193) du plan). **Environ 62 cm entre les deux montants.** Passée en visant u = 304 : 72 cm à 50 mm/s demandés, aucun contact. Le cap a glissé de 3,4° pendant cette avance : à 50 mm/s demandés la tenue de cap est molle.
- En G12, premier tour sur place d'`explorer3.py` : le filtre corrige de 4 cm et 0,3° (note 0,83). **Après 2,6 m à l'estime, passage et porte compris, l'estime et le filtre sont d'accord à 4 cm près** : cela confirme aussi la position du filtre en K10.

**De G12 à C17** (`explorer3.py`, options habituelles, avec le pivot dès 15° d'écart du § 36, essayé ici pour la première fois sur le robot) : E12, D14, C17 ; 3,9 m en 1,7 min, 4 tours sur place, 6 rotations et 6 avances, aucun contact, aucun arrêt imprévu. En D14 le filtre a corrigé de 22 cm et 4,8° avec une note médiocre (0,59) ; l'arrivée en C17 s'est faite quand même à 2 cm de la position visée d'après le tour suivant (note 0,74, étalement 41 cm).

**Bilan du retour** : 6,6 m en 10 minutes (regards compris), aucun contact en mouvement, mode Safe jamais quitté, sol clair partout. Le journal montre le pare-chocs droit enfoncé 0,7 s à 13 h 23 min 05, robot immobile en mode passif, juste après le réveil et avant tout mouvement : cause inconnue (la chaise, ou une main).

**Leçons.**

- Quand le filtre et l'estime divergent, c'est le filtre qu'il faut croire, même avec une note médiocre, et il faut dire qu'ils divergent au lieu de trancher. D'où venaient les 10 cm d'écart de l'estime à l'aller (glissement au moment du contact avec le coin de meuble ?) : non établi.
- La méthode de `passage.py` (regards cap par cap à l'arrêt, mise dans l'axe, ligne droite lente) a passé les 47 cm et la porte dans les deux sens sans contact. Les deux seuls contacts de la journée dans ces endroits ont eu lieu sous la conduite d'`explorer3.py` ou au bout d'une avance non regardée.
- Le robot ne voit rien sur ses côtés : un objet peut être à 10 cm de sa coque sans qu'il le sache.

**À faire, pas fait** : dans `Plan.chemin`, le trait vert efface encore la distance aux murs ; donner à `explorer3.py` la méthode de `passage.py` pour les passages étroits ; l'accostage sur la base n'a jamais été essayé (touche `h` du firmware : l'ordre « rentre à la base » du robot, à ne lancer qu'avec l'accord de l'utilisateur).

**État à la fin** : robot en C17, pixel (440, 71), cap 67°, à 85 cm devant sa base ; session fermée (`5`, `s`, `x`) à 13 h 33, capteur de distance au repos, vitesse 150, batterie 1 648 mAh.

## 38. Guidage et précision : le signal de la base, la précision mesurée par les retours au même endroit, les repères (2026-11-13, 13 h 45 à 14 h 10)

Message de l'utilisateur : « il était je ne sais pas, K9, K10, peut-être entre les deux ; essaie d'améliorer encore le guidage et la précision ; voit-on le signal que la base émet ? cela peut-il aider ? ». Enregistrement de l'essai sur le robot : `mesures/exploration11_20261113_135821_*` (`_a_`, `_b_` : deux tours de boucle), `mesures/position_20261113_140541.*`.

**Correction du § 37.** J'y écrivais « c'était faux : le robot était en K10 ; c'est le filtre qui avait raison ». Son observation ne permet pas de trancher : il était à la limite des deux cases, et mes deux positions (pixels 236 et 240, limite à 238,5) sont à 7,5 cm l'une de l'autre, de part et d'autre de cette limite. Ce qui reste établi vient du retour, pas de son observation : l'estime repartie de la position du filtre est retombée sur le filtre à 4 cm près après 2,6 m, et dans ce repère le coin du mur et le chant du battant sont là où le plan les montre, à 2 pixels près.

**Le signal de la base** (`data_analysis/n_signal_base.py`, `results_n_signal_base_20261113.txt` ; chaque ligne du journal replacée sur le plan).

- On le voit : le récepteur du dessus reçoit les codes 168 (faisceau rouge), 164 (vert) et 172 (les deux) sur 2,2 % des lignes de la journée. **Jamais au-delà de 2,0 m** (34 586 lignes entre 2 et 5 m, aucune avec un code).
- À l'endroit où il avait fait glisser le robot hors de sa base le matin (dans l'axe, à 70 cm) : un code sur 44 % des lignes, presque toujours 172, et les deux récepteurs avant lisent 168 quand le robot fait face à la base.
- Au même endroit, le code change selon le cap du robot (rouge, les deux, vert) : le récepteur est à l'avant, à une quinzaine de centimètres du centre, et balaie les faisceaux quand le robot tourne. Les limites entre faisceaux sont donc nettes à quelques centimètres. Le récepteur ne voit pas vers l'arrière.
- **En C17, où je croyais le robot juste devant sa base, aucun code sur des milliers de lignes, tours sur place compris.** La base n'est donc pas là où la carte la place (B17, pixel (442, 27), tournée vers le bas) : sa marque sur le plan est un trait en biais, et les faisceaux reçus s'expliquent par une base tournée vers le bas à gauche (axe entre 231° et 254° selon sa place exacte). Sa position n'est pas résolue à mieux que 10 à 30 cm : il faudra un passage devant elle, récepteurs relevés.
- Ce que cela peut apporter : un repère fixe, indépendant du plan et des meubles, pour recaler le robot de côté à quelques centimètres quand il est à moins de 2 m de sa base, et pour l'accoster. Rien en K9 ou K10 : trop loin.

**La précision mesurée sans vérité de terrain** (`data_analysis/p_precision_retours.py`, `results_p_precision_retours_*.txt`). Deux tours sur place faits presque au même endroit se comparent directement (`carto.apparier`), à 2 ou 3 cm près, sans le plan ; l'écart avec ce que disent les positions du filtre est une erreur de localisation.

- Trajets de l'après-midi en firmware v10, avant les repères : 16 paires, écart médian 64 mm, **un quart des paires au-dessus de 200 mm**, pire 264 mm.
- Tour par tour, sur les 53 tours de la journée : la plupart à moins de 7 cm ; quelques-uns décalés de 10 à 23 cm, dont le retour en D14 (23 cm, note 0,59), le premier tour du matin (20 cm) et **l'arrivée en C17 du § 37 (14 cm)**.
- Rejeux du filtre : garder le filtre d'un trajet à l'autre ou serrer l'incertitude du trajet ne change rien (médiane 51 à 70 mm au lieu de 56). Les écarts viennent de la pose du tour sur le plan, là où le plan ne ressemble pas à ce que le robot voit, pas du trajet compté. Laisser moins flotter le cap (1,5° au lieu de 3°) rend la position prédite avant chaque tour plus juste (50 mm au lieu de 58 en médiane) sans changer le reste : adopté pour le firmware v10.
- Par rapport au § 31 (« 7 cm d'erreur médiane » au rejeu du 10) : la médiane se confirme (6 cm), mais elle cachait une queue : quelques tours faussés de 10 à 23 cm, qui mettent un quart des paires au-delà de 20 cm.

**Le planificateur** (`plan.py`, `explorer3.py`).

- Le trait vert ouvre un passage mais n'efface plus la distance aux murs.
- Le sol tenu pour libre le long d'un trajet déjà roulé est une voie de 6 cm de part et d'autre, tracée sur le trajet réel (15 cm, et la ligne droite d'un tour au suivant, jusque-là).
- Un raccourci en ligne droite doit laisser 17 cm au centre du robot (9 jusque-là).
- Obstacles trouvés par le robot et absents du plan : `--plan-ferme plan_lidar/obstacles.json` (D14, montant est de la porte H12, objet après le passage, coin de meuble J10, chaise en K9).
- Résultat : le chemin de C17 à K10 franchit la ligne de la porte H12 à u = 301 à 304 (297 avant, sur le liseré du montant ouest), passe sous l'obstacle de D14, et s'arrête devant la chaise quand on demande K9. Simulation : 63 à 73 mm/s, deux portes de 80 cm, aucun contact.

**Les repères** (`outils/reperes.py`, `explorer3.py --reperes`). Un repère est un tour sur place déjà fait ; un nouveau tour fait à moins de 35 cm de repères se recale sur eux par comparaison directe (deux repères d'accord à 6 cm, ou un seul comparé sur quatre parois). Le fichier `plan_lidar/reperes_tours.json` vient des 53 tours du jour : 35 gardés (C17, D12 et E15 : 8 chacun ; D17 : 4 ; D14 : 3 ; D15 et G12 : 2), les tours sans voisin ou corrigés de plus de 12 cm étant écartés.

- Hors robot : les tours de l'après-midi recalés sur les repères du matin et de midi : écart entre deux passages au même endroit de 200 mm à 41 mm (médiane, 5 paires).
- Sur le robot, deux fois la boucle de 7,5 m (2,8 et 2,9 min, aucun contact, 16 et 18 mouvements) : calage sur les repères à quatre tours sur six dans la première boucle (le tour de départ ne s'est pas calé) et cinq dans la seconde, à 2 à 13 cm du filtre (en D14 : 11 cm les deux fois, le filtre y est décalé). **Entre les deux boucles, aux quatre endroits calés, la position annoncée concorde avec la comparaison directe des deux tours à 1 cm près** (1 à 10 mm) ; en E11, sans repère : 26 mm.
- Ce que cela ne fait pas : le cap (toujours celui du filtre) ; un endroit vu pour la première fois ; la porte et K10 (deux repères en G12, aucun au-delà).

**Ce qui limite encore le guidage.** Savoir où l'on est à 1 cm ne suffit pas à arriver sur la cible : à la première boucle le robot est arrivé en E15 à 24 cm du point visé (le départ, l'arrivée du § 37, était faux de 14 cm et le premier tour ne s'est pas calé), à la seconde à 9 cm. Deux causes vues : le cap est recalé à chaque tour par le filtre, à 2 ou 3° près, ce qui déplace l'arrivée suivante de 5 à 10 cm (nuancé au § 41 : mesuré sur 43 trajets, cet effet existe mais n'est pas le principal) ; et après le tour d'arrivée le robot ne se rapproche pas de la cible.

**À faire, pas fait** : tenir le cap par le gyroscope avec une correction lente ; une petite avance de rattrapage après le tour d'arrivée ; rendre les repères de deux endroits cohérents entre eux par le trajet compté ; replacer la base sur le plan par un passage devant elle et s'aligner sur le couloir « rouge et vert » ; donner à `explorer3.py` la méthode de `passage.py` pour les passages étroits.

**État à la fin** : robot en C17, pixel (437, 68), cap 66°, devant sa base ; session fermée (`5`, `s`, `x`) à 14 h 05, capteur de distance au repos, vitesse 150, batterie 1 613 mAh.

## 39. La base mesurée par ses faisceaux : elle est en B16, et le robot aligné sur son axe (2026-11-13, 14 h 22 à 14 h 30)

Accord de l'utilisateur : « Oui, la base » (mesurer la base par ses faisceaux et aligner le robot sur son axe). Enregistrements : `mesures/exploration12_20261113_142305_*`, `mesures/position_20261113_143035.*`. Carte : `plan_lidar/carte_grille_20261113_base*.png` (hors dépôt). Nouvel outil : `outils/balise_base.py`.

**Ce que disaient déjà les données du matin**, robot juste glissé hors de sa base et tourné vers elle (début de `exploration6`, relu cap par cap) :

- les deux récepteurs avant ne voient la base que si le robot lui fait face, à 20° près ;
- le récepteur du dessus voit sur 240° (rien quand la base est à plus de 120° du nez) ; à cet endroit il lisait « rouge » tant que le robot était tourné vers la droite ou de moins de 30° vers la gauche, puis « rouge et vert » de 30° à 120° vers la gauche : en tournant, le récepteur (à l'avant du robot) se déplace de côté et traverse les faisceaux. Un code n'arrive que sur une ligne sur deux environ.

**La méthode** (`balise_base.py`, un tour sur place) : le milieu des caps où les récepteurs avant voient la base donne sa direction ; les caps où le récepteur du dessus passe de rouge à « les deux », puis à vert, donnent de combien l'axe de la base est à gauche ou à droite du centre du robot. Face à la base, le rouge est à droite et le vert à gauche.

**Les trois tours.**

| Robot au pixel | Récepteurs avant | Récepteur du dessus | Conclusion |
|---|---|---|---|
| (423, 65), là où l'axe aurait dû passer si la base était en B17 | rien | rouge seulement, et seulement quand le récepteur est du côté ouest du robot | bord extérieur du faisceau rouge : la base et son axe sont plus à l'ouest |
| (409, 75) | base vue à ±20° autour du cap 89° | rouge jusqu'à +10°, les deux de +12° à +49°, vert au-delà | axe à gauche du robot, d'une soixantaine de millimètres |
| (405, 75), après 75 mm vers la gauche | base vue à ±27° autour du cap 90°, surtout « les deux » | rouge jusqu'à −20°, les deux de −18° à +5°, vert de +5° à +40° | axe à 15 mm à droite du robot : aligné |

- Vérification à l'arrêt, robot tourné vers le cap 90° : **les trois récepteurs lisent « rouge et vert »** (37 lignes sur 82, le reste sans code).
- Le déplacement de 75 mm a fait passer l'écart mesuré de +72 à −16 mm avec un récepteur supposé à 150 mm du centre : il est donc à 126 mm du centre, et les écarts vrais étaient +61 puis −14 mm. Le couloir « rouge et vert » fait 5 à 7 cm de large à 85 cm de la base.
- Capteur de distance dans l'axe : 878 mm, soit quelque chose à 905 mm du centre, là où le plan montre le mur (v = 27 à 28) ; je pensais la base trop basse pour lui (corrigé au § 40 : c'était le dos de la base, ou le mur juste derrière). Depuis (409, 75) il voyait quelque chose à 52 cm vers le cap 89° : un objet près de l'axe, côté droit, à 38 cm du mur (pot ou pied de table ; position à 10 cm près, le faisceau du capteur est large ; § 41 : revu à 37 cm du mur, mais du côté gauche : son côté n'est pas sûr).

**Où est la base.** Son axe est la droite u = 405 du plan (à 2 pixels près), elle regarde vers le bas (cap 270° à 3° près), adossée au mur du haut : pixel (405, 33), **case B16**. Cela remplace la position tenue depuis le 10 (B17, pixel (442, 27), centre de la marque de l'utilisateur) : 70 cm trop à l'est. Tout ce que ce journal appelle « C17, devant la base » depuis le § 32 était donc 60 à 70 cm à côté de son axe ; c'est pour cela qu'aucun faisceau n'y était reçu (le faisceau rouge s'arrête vers u = 420 à cette hauteur). `--base-plan` devient `405,33`.

**Ce que cela apporte.** Un tour sur place à moins de 2 m de la base, dans ses faisceaux, donne la direction de la base à 3° près et l'écart à son axe à 1 ou 2 cm près, sans le plan : un repère fixe pour recaler le robot et pour l'accoster. Pas encore branché sur le filtre ni sur `explorer3.py`.

**Non fait** : l'accostage (avancer sur la base, ou l'ordre « rentre à la base » du robot, touche `h`) ; le champ proche (code 161) n'a pas été revu.

**État à la fin** : robot en C16, pixel (405, 75), cap 90°, **dans l'axe de sa base à 1 ou 2 cm près, tourné vers elle, le pare-chocs à 60 cm d'elle environ** ; session fermée (`5`, `s`, `x`) à 14 h 30, capteur de distance au repos, vitesse 150, batterie 1 585 mAh.

## 40. Accostage : l'ordre « rentre à la base » du robot, lancé dans l'axe (2026-11-13, 14 h 34 à 14 h 36)

Accord de l'utilisateur : « Oui, lance-le ». Enregistrements : `mesures/exploration13_20261113_143420_*`, `mesures/position_20261113_143621.*`. Robot aligné sur l'axe de sa base depuis le § 39, le pare-chocs à 60 cm d'elle, endormi.

**Déroulement.** Réveil (`w`, `s` : mode passif), puis touche `h` du firmware (Seek Dock, 143) à 14 h 35 min 03. C'est le robot qui se conduit ; le cerveau ne fait que lire ses capteurs.

- 0 à 3 s : immobile, le courant de la batterie passe de 0,13 à 0,62 A.
- 3 à 21 s : il avance vers la base, reçoit le champ proche (code 161) après 52 cm de trajet, recule de 9 cm en pivotant vers 18 s, puis reprend.
- 21 s : contacts de charge trouvés (`base` vrai). Quatre secondes plus tard la charge commence (état 2) : 0,93 A, puis 1,27 A sous 16,2 V.
- Déplacement compté : 787 mm droit devant, 38 mm vers la droite, cap +1,3° ; chemin 1 019 mm.

**Ce que cet ordre fait, à savoir avant de le relancer.**

- Vitesse la plus forte : **209 mm/s**, au-dessus des 150 mm/s de la consigne pour les ordres du cerveau.
- Courant pendant l'approche : **0,9 à 1,05 A**, contre 0,27 A quand le cerveau fait rouler le robot à 135 mm/s (boucles du § 38). Le robot a donc fait tourner autre chose que ses roues pendant une vingtaine de secondes, sans doute ses brosses ou son aspirateur. Pas vérifié à l'oreille : à demander à l'utilisateur.

**Où est la base, d'après le robot posé.** Son centre est à 787 mm du point d'alignement, au pixel (407, 34) : la base est juste au-delà, contre le mur du haut, pixel (407, 30) environ, case B16. Le § 39 disait (405, 33) : d'accord à 3 pixels.

**Correction du § 39.** J'y écrivais que la base était trop basse pour le capteur de distance et qu'il voyait le mur à 905 mm. Le robot posé a son centre à 12 cm seulement de ce point : ce que le capteur voyait était donc le dos de la base, ou le mur juste derrière elle.

**Ce qui est fait aujourd'hui, bout à bout** : aller jusqu'à la limite de K9 et K10, retour, repérage de la base par ses faisceaux, alignement sur son axe, accostage et charge.

**Non vérifié** : l'accostage lancé de plus loin ou de travers ; si les brosses ont tourné ; un accostage mené par le cerveau, à vitesse réglée et brosses arrêtées (jamais essayé).

**État à la fin** : robot sur sa base (B16), en charge ; session fermée (`s`, `x`) à 14 h 36, capteur de distance au repos, vitesse 150, batterie 1 585 mAh. Pour repartir, il faudra le tirer de sa base à la main : sur la base alimentée il ignore les ordres de roues (§ 32).

## 41. Aller-retour de la base à C28 : aller sans contact, retour laborieux, et ce que les données apprennent (2026-11-13, 14 h 43 à 15 h 33)

Demande de l'utilisateur : « fais un aller retour, vers le c28, en utilisant ces données pour encore t'améliorer, je recule le robot ». Enregistrements : `mesures/exploration14_20261113_144300_*` (aller, puis retour jusqu'au nord de la porte H12 ; passages `a`, `b`, `c`, `d`), `mesures/exploration15_20261113_152720_*` (fin du retour ; mesure par les faisceaux dans `_balise.txt`), `mesures/position_20261113_153245.*`. Carte : `plan_lidar/carte_grille_20261113_c28*.png` (hors dépôt). Analyses : `data_analysis/q_cap_filtre.py`, `data_analysis/r_tours_consecutifs.py` et leurs fichiers `results_*_20261113.txt`.

**En bref.** Aller : 14,4 m en 8 min, aucun contact. Retour : 24,3 m en 37 min, sept contacts légers, et deux endroits passés à la main (un intervalle de 40 à 45 cm dans la pièce centrale, la porte H12). Arrivée devant la base dans son axe à 1 cm près. Trois défauts trouvés, un corrigé dans le planificateur (vérifié en rejeu et en simulation, pas encore sur le robot).

### L'aller (14 h 44 à 14 h 52)

- **Départ faux de 40 cm, rattrapé par les repères.** L'utilisateur avait tiré le robot de sa base à la main. Position de départ : direction et axe par `balise_base.py`, distance par le capteur de distance (630 mm), d'où le pixel (410, 64). Or le capteur voyait un objet posé à 37 cm devant le mur de la base, pas la base. Au premier tour, en D14 : « repères : calé sur 4 tours déjà faits ici ; (−41, −283) mm par rapport au filtre ». Le départ vrai était vers (411, 86). Vérification indépendante faite à l'arrivée (plus bas) : l'objet est bien à 37 cm du mur, ce qui place le départ à v = 82.
- Base → D14 → E12 → G12 : 3,0 m, 4 tours sur place, 1,8 min.
- Porte H12 vers le sud, à l'estime (`passage.py`) : 1,2 m, sans contact.
- Couloir (ligne J) → G26 → C28 : 10,2 m, 6 tours, 3,7 min, soit 46 mm/s. Arrivée au pixel (728, 75).

### Le retour (14 h 53 à 15 h 30)

1. **Pièce centrale, en automatique (passage `c`) : 5 contacts en 3 min, puis arrêt.** *(Explication corrigée au § 43 : une roue avait patiné à l'aller, le robot était 37 cm à côté de là où il se croyait, et les positions de ce paragraphe sont décalées d'autant.)* Contacts en E27 (trois), E26 et D26. Cause du premier, retrouvée en rejouant le planificateur : le chemin allait en ligne droite de (728, 77) à (713, 122), dix centimètres à l'ouest du virage que la trace de l'aller fait en (720, 116). Le sol est blanc sur le plan à cet endroit, mais un objet que ni le capteur de distance ni les six capteurs optiques ne voient borde le passage (son bord est vers u = 705 à 707 pour v = 113 à 122). Pare-chocs droit, robot au pixel (713, 113). Ensuite le robot a cherché des détours dans une pièce où le filtre le place à 5 à 16 cm près, et a touché quatre autres choses.
2. **Reprise à la main (14 h 56 à 15 h 12).** Un essai de recalage sur le tour de l'aller en C28, position et cap ensemble (outil `recaler_tour.py`, non gardé ; son tour est dans `_tour_c28_retour.json`), a rendu un cap faux d'une dizaine de degrés : dans cette pièce les parois appariées d'un tour à l'autre ne sont pas les mêmes. Position et cap repris par des regards vers le mur nord, puis l'intervalle (40 à 45 cm entre l'objet et le côté est, à cheval sur E27 et E28) a été repassé **en suivant la trace de l'aller à l'estime**, à 50 puis 75 mm/s demandés, en six petites avances : aucun contact. Le tour suivant, en G26, n'a corrigé que de (−11, −25) mm.
3. **Couloir, en automatique (passage `d`) : 9,0 m en 4,2 min, 6 tours, 1 contact** (pare-chocs gauche en J23, pixel (589, 223)). Le cap repris à la main était faux d'une dizaine de degrés, d'après les corrections du filtre, toutes dans le même sens : +0,1°, +3,3°, +1,1°, +4,0°, +1,2°, +0,9°, soit 10,6° en six tours. Entre-temps le robot dérivait vers le sud, et chaque tour corrigeait la position de ce côté, de 3 à 29 cm.
4. **Porte H12 vers le nord (15 h 16 à 15 h 27).** Devant la porte (J12), le filtre plaçait le robot une vingtaine de centimètres trop à l'ouest (19 cm d'après le tour fait ensuite en G12, 25 cm d'après le montant). Position reprise sur le montant est, au capteur de distance :
   - à 60 cm de la porte, un écho de 608 à 627 mm sur tous les caps de 60° à 100°, rien de 110° à 120° : le montant est à 61 cm, presque droit devant ; la porte est plus à gauche ;
   - après 15 cm vers l'ouest, écho le plus court (619 mm) entre 70° et 80° ; après 7,5 cm de plus, plus rien à 89° et 93°, et 3,9 m à 97° : l'ouverture est devant ;
   - après 30 cm d'avance, montant est à 400 mm entre les caps 50° et 60°, battant ouvert à 39 cm sur la gauche, rien de 89° à 119° ;
   - franchie au cap 106° (13 à 14 cm de marge à droite d'après le montant), 65 cm à 60 mm/s demandés : aucun contact.
5. **G12 → E12 → D14 → D16 (exploration15) : 4,1 m en 2,2 min, 4 tours, 1 contact** (pare-chocs droit en E13, pixel (318, 124)) : quelque chose au sud de la ligne suivie à l'aller, que les capteurs n'ont pas vu. Ajouté aux obstacles connus (fichier local `plan_lidar/obstacles.json`, 12 entrées).

### L'arrivée, mesurée par la base (15 h 30)

- `balise_base.py`, deux tours sur place : axe de la base à **−5 mm puis −13 mm** du centre du robot ; au second, base vue par les récepteurs avant à ±19° autour du cap 88,5° du plan (90° attendu). Robot tourné vers elle : récepteur du dessus et avant droit « rouge et vert », avant gauche « vert ».
- Le filtre plaçait le robot au pixel (405,7 ; 81,0), donc sur l'axe (u = 405 à 407, § 39 et § 40). **En travers, l'arrivée est juste à 1 ou 2 cm.**
- **En long, pas tranché.** *(Tranché au § 42 : le robot était à v = 92, le filtre le plaçait 20 cm trop près de la base ; la « paroi » est un objet.)* Pendant le tour, le capteur de distance voit deux choses dans la direction de la base : un objet à 43 cm du centre, de 0 à 30° à gauche, et une paroi à 78 cm, de 6 à 42° à droite. Si cette paroi est le mur derrière la base (celui que le § 39 voyait à 905 mm), le robot est à v = 69 et non 81 : 22 cm plus près de la base que ne le dit le filtre. Un accostage le dirait (66 cm ou 89 cm à parcourir).
- L'objet à 43 cm est à 37 cm devant le mur : c'est celui du § 39, et c'est lui que le capteur avait pris pour la base au départ. Le § 39 le disait « côté droit » de l'axe ; aujourd'hui il apparaît à gauche : son côté n'est pas connu, le faisceau du capteur est trop large.

### Ce que disent les données

- **Les repères** ont servi deux fois à l'aller (D14, G12 : des endroits déjà vus plusieurs fois) et jamais au retour. Les tours de l'aller avaient été ajoutés comme repères (`reperes.py --tout`), mais un repère seul doit être comparé sur quatre parois, et les tours du retour n'en partageaient que trois au plus avec ceux de l'aller.
- **Deux tours faits au même endroit se comparent à 1 cm** (`r_tours_consecutifs.py`) : sur les 14 fois où un passage finit par un tour et le suivant commence par un autre sans que le robot ait bougé (enregistrements du 10 et du 13), la comparaison tour contre tour retrouve le déplacement compté par le cerveau à 10 mm près en médiane, 22 mm au pire.
- **Le cap n'est pas ce qui limite l'arrivée** (`q_cap_filtre.py`, 43 trajets du jour entre deux tours). Le filtre corrige le cap de 2,2° à chaque tour (écart quadratique). Si ces corrections n'étaient que du bruit, la correction de travers au tour suivant vaudrait la longueur du trajet fois l'angle : la pente mesurée est 0,39, la corrélation 0,21, et n'appliquer qu'une part de la correction de cap ne changerait rien (113 mm quadratiques, 111 au mieux). La correction de travers (56 mm en médiane, 113 quadratiques) et la correction en long (65 mm) viennent donc surtout de la position que le filtre donne. **Cela remplace l'explication du § 38** (« le cap est recalé à chaque tour par le filtre, à 2 ou 3° près, ce qui déplace l'arrivée suivante de 5 à 10 cm ») : l'effet existe, il n'est pas le principal.
- **Un cap faux de 10° au départ se rattrape mal** : six tours et 9 m dans le couloir. J'avais lancé ce passage avec `--depart-sur` (départ tenu pour connu à 10 cm et 6° près) alors que le cap venait d'être repris à la main. Rejoué sans cette option (25 cm et 15°), le premier tour corrige le cap de +2,8° au lieu de +0,1° et la position de 13 cm vers le sud : mieux, sans suffire. Un tour dans cette pièce renseigne peu sur le cap : après le tour, l'étalement du cap reste celui d'avant. À retenir : pas de `--depart-sur` après une reprise à la main, et surtout ne pas perdre le cap que tient le gyroscope.

### Ce qui change dans le code

1. **Le planificateur préfère le sol déjà roulé** (`plan.py`). *(Devenu un réglage, plus la conduite par défaut : § 44.)* Un pas hors des voies coûte trois pas sur une voie (`Plan.hors_voie`), et une ligne droite entre deux points du chemin n'est prise que si elle n'ajoute pas de trajet hors voie (`jalons`, 6 cm de tolérance). Avant, une voie ne valait pas mieux que du sol blanc, et les lignes droites coupaient ses virages.
   - Rejeu du départ du retour : le chemin passe maintenant par (721, 98) puis (715, 120), sur la trace de l'aller, au lieu de couper de (728, 77) à (713, 122).
   - Sur les 104 trajets possibles entre les 11 endroits visités aujourd'hui : 627 m au lieu de 625, dont 51 m hors voie au lieu de 98 ; aucun trajet allongé de plus d'un quart.
   - Simulation (`essai_explorer3.py --plan`, deux mondes, cinq tirages, allers-retours répétés) : aucun contact avant comme après, trajets 1,6 % plus longs dans l'appartement simulé, durée égale à 2 % près, même précision. La simulation n'a pas d'objet invisible : elle montre l'absence de dégât, pas le gain.
   - Aussi dans `plan.py` (fait avant ce trajet, en service pendant) : une ligne droite ne traverse plus un obstacle connu.
2. **Les voies se transmettent d'un passage au suivant** (`explorer3.py`). Le fichier de tours garde, sous « voies », la trace de chaque trajet roulé sans contact entre deux tours ; `--plan-roule` accepte ces fichiers `_stations.json` en plus des anciens. Pour revenir par où l'on vient d'aller, donner le fichier de l'aller. Aujourd'hui les voies de l'aller n'existaient pas quand le retour est parti (elles se fabriquaient à la main). Vérifié en simulation : 18 voies pour 19 tours, relues par un autre passage.
3. `reperes.py --tout` : garde aussi les tours sans voisin. N'a rien apporté aujourd'hui (voir plus haut).

### Méthode pour une porte abordée avec une position douteuse (faite à la main, à automatiser)

Depuis 60 cm environ : regards de 10° en 10° vers la porte ; le montant le plus proche donne un écho stable sur une trentaine de degrés. Se décaler par pas de 8 à 15 cm jusqu'à ne plus rien voir droit devant. Avancer de 30 cm. Mesurer le montant de près (écho le plus court : sa distance ; milieu des caps où on le voit : sa direction). Choisir le cap qui laisse au moins 13 cm entre le robot et chaque montant. Franchir à 60 mm/s demandés. Dix minutes à la main aujourd'hui, dont une seule de mouvement.

### Erreurs de ma part pendant ce trajet

- Plusieurs noms de cases annoncés à l'utilisateur étaient faux (calculés de tête) : « E26 » pour G26, « G22 » et « G23 » pour J22 et J23 (le couloir est la ligne J), « D27 » pour l'intervalle étroit (à cheval sur E27 et E28), « C16 » pour l'arrivée (D16). Les noms de cette section viennent de `grille.py`.
- Le cap repris à la main dans la pièce centrale était faux d'une dizaine de degrés : c'est la cause du contact du couloir.

**Non vérifié** : le nouveau planificateur sur le robot ; l'erreur d'arrivée en long ; ce que sont les objets invisibles de E27 et de E13 (à demander à l'utilisateur) ; ce que vaut un repère seul comparé sur trois parois, faute de cas où la vérité est connue ; la méthode de la porte, automatisée.

**État à la fin** : robot en D16, pixel (406, 81) d'après le filtre, **dans l'axe de sa base à 1 cm près, tourné vers elle, à 78 cm de la paroi qui est derrière elle** ; il n'est pas posé sur sa base et ne charge pas. Session fermée (`5`, `s`, `x`) à 15 h 32 min 52, capteur de distance au repos, vitesse 150, batterie 1 541 mAh.

## 42. Essai du planificateur modifié sur une boucle, et ce que la boucle dit de la précision (2026-11-13, 16 h 09 à 16 h 17)

Demande de l'utilisateur : « Teste d'abord » (essayer le planificateur du § 41 avant d'accoster). Enregistrements : `mesures/exploration16_20261113_160926_*`, `mesures/position_20261113_161721.*`. Carte : `plan_lidar/carte_grille_20261113_boucle*.png` (hors dépôt). Analyse : `data_analysis/s_estime_boucle.py`, `results_s_estime_boucle_exploration16.txt`.

**La boucle.** D16 → E15 → D12 → E11 → G12 → C17 → D16, dans la pièce de la base : trois trajets communs avec les deux boucles du § 38, deux où le nouveau planificateur choisit un autre chemin (E11 → G12 par un coude au lieu d'une ligne droite, G12 → C17 par d'autres points).

| | Boucle d'essai | Boucles du § 38 |
|---|---|---|
| Chemin | 8,6 m | 7,5 et 7,4 m |
| Durée | 4,5 min | 2,8 et 2,9 min |
| Vitesse moyenne | 32 mm/s | 45 et 43 mm/s |
| Tours sur place | 8 | 6 et 6 |
| Rotations, avances | 14 et 14 | 7 et 9, 8 et 10 |
| Contacts, trajets arrêtés | aucun | aucun |

- Le planificateur modifié marche sur le robot : aucun contact, et les 7 voies de la boucle sont bien gardées dans le fichier de tours (première fois).
- Il est plus lent. En suivant les anciennes traces de près, le chemin se découpe en deux fois plus de petits trajets, et chaque rotation coûte 4 à 6 s. D'E15 à D12, le même trajet prend 42 s au lieu de 31 et 34 s.
- Une variante rejouée sur le plan (ligne droite permise partout où le corps du robot est déjà passé) n'a pas été gardée : elle redonnait la ligne droite du § 41 dans la pièce centrale.

**Les repères sont cohérents entre eux, le filtre seul ne l'est pas.** La boucle refaite à l'estime pure (roues et gyroscope, aucun recalage), posée au mieux sur les cinq tours calés par les repères (E15, D12, G12, D15, C17) :

- l'estime passe à 55 mm de ces cinq tours (quadratique), 79 mm au pire ; sur les deux boucles du § 38 : 37 et 32 mm. Des repères faits à des endroits différents s'accordent donc avec le trajet compté à 3 à 6 cm près sur 8 m ;
- **le départ, que le filtre seul plaçait au pixel (407, 80), était en (403, 92) : 22 cm d'écart**, presque tout dans l'axe de la base ; l'arrivée, (407, 80) d'après le filtre, était en (408, 83) : 5 cm ;
- les deux tours, de départ et d'arrivée, comparés directement (trois parois) : l'arrivée est à (+46, +187) mm du départ ; l'estime dit (+81, +173) mm ; le filtre disait (−12, +4) mm. **Devant la base, le filtre donne v = 80 pour deux endroits distants de 19 cm** : dans l'axe de la base, il ne voit pas où est le robot ;
- même défaut au départ de la première boucle du § 38 (C17, après le retour de K9) : 29 cm.

**Ce que cela corrige au § 41.**

- « En long, pas tranché … le robot est à v = 69 et non 81 » : faux dans les deux sens. Le robot était à v = 92 : **le filtre le plaçait 20 cm trop près de sa base**, et non trop loin. L'arrivée de l'aller-retour vers C28, faite sans aucun repère depuis C28, était donc juste à 1 cm en travers et fausse de 21 cm en long.
- « Une paroi à 78 cm » n'était pas le mur : c'est un objet, vers le pixel (419, 51), à 25 cm à l'est de l'axe de la base et 45 cm devant le mur. Il a été vu trois fois à la même place (14 h 44 à 65 cm, 15 h 30 à 80 cm, 16 h 14 à 65 cm), et c'est lui qui avait faussé le départ. Ajouté aux obstacles connus.
- « Un objet à 43 cm, à 37 cm devant le mur » : quelque chose était bien là, vers le pixel (398, 68), immobile de 15 h 30 à 16 h 10 ; il n'y était ni à 14 h 44 ni à 16 h 14. Passager (à demander à l'utilisateur).

**Arrivée de la boucle, mesurée par la base** : axe à +17 mm du centre du robot, direction de la base au cap 91,2° du plan, les trois récepteurs « rouge et vert » robot tourné vers elle.

**État à la fin** : robot en D16, pixel (408, 83), dans l'axe de sa base, tourné vers elle, pas posé dessus ; session fermée (`5`, `s`, `x`) à 16 h 17 min 29, batterie 1 507 mAh.

## 43. Le couloir, C28 et B22 : une roue qui patinait expliquait le retour manqué (2026-11-13, 16 h 32 à 17 h 04)

Demandes de l'utilisateur, en cours de route : « reesaie le couloir et le c 28 », puis « direction B22 avant le retour », puis « stop ». Enregistrements : `mesures/exploration17_20261113_163238_*` (passages `a` à `e`, tours sur place `_tour_c28.json` et `_tour_b22.json`). Analyse : `data_analysis/t_patinage.py`, `results_t_patinage_20261113.txt`.

### Ce qui s'était vraiment passé au premier aller (14 h 51)

En relisant roue par roue l'aller du § 41 dans la pièce centrale :

- deux fois, juste après le départ d'une avance à 135 mm/s demandés, **la roue droite a tourné plus que le sol ne défilait sous elle** : 43 cm de trop en 3,5 s (14 h 51 min 46), puis 35 cm en 2,8 s (14 h 52 min 03). Les codeurs disent que le robot tourne à gauche de 14 °/s, le gyroscope qu'il tourne à droite de 16 °/s : la roue patine, et le robot pivote autour d'elle ;
- le robot a ainsi tourné de 58° puis de 47° pendant ces avances, que le cerveau a menées à leur terme ;
- le cerveau compte le chemin comme la moyenne des deux roues : il a compté **21 puis 17 cm de trop**. À l'arrivée le programme se croyait au pixel (729, 66), en C28 ; **il était en (713, 78), en C27, à 37 cm de là**. Le filtre, dans cette pièce encombrée, n'a corrigé que de 17 cm, et dans une autre direction : il restait 28 cm d'erreur ;
- sur les 160 m roulés ce jour-là, c'est arrivé seulement là. Le sol y est sombre sous les capteurs de vide (signal 700 à 1 700 au lieu de 2 600) : un tapis ou son bord, sans doute.

**Ce que cela corrige au § 41.**

- « Cause du premier contact : le chemin coupait de dix centimètres un virage de l'aller » : faux. Ce « virage » de la trace n'a jamais existé, c'était le patinage. La vraie cause : le robot est reparti 28 cm à l'ouest de là où il se croyait, droit dans les chaises de la table.
- « Un objet que les capteurs ne voient pas borde le passage », « un intervalle de 40 à 45 cm » : ces positions étaient données dans le repère faussé. Replacés, les objets touchés sont vers les pixels (688 à 690, 119 à 122), (679, 124) et (661 à 662, 110 à 113), en E25 et E26 : les chaises et la table, 30 à 40 cm à l'ouest du chemin de l'aller. Le chemin lui-même est libre, et rien ne montre un intervalle étroit à cet endroit.
- « Arrivée au pixel (728, 75), C28 » : le robot était en C27.
- La préférence du planificateur pour les voies (§ 41) reposait sur ce faux virage : voir le § 44.

### Le trajet

- **Base → G12** (`a`) : 2,9 m en 1,7 min, deux recalages sur les repères, aucun contact. **Porte H12 vers le sud** à l'estime, comme à 14 h 47 : aucun contact.
- **Couloir → G26** (`b`) : 8,3 m en 3,4 min, un contact léger au début (pare-chocs gauche en H14, à 16 h 37 : après la porte le robot était 10 cm plus au nord qu'il ne le croyait).
- **G26 → C28 → G26, lentement, à l'estime** (`passage.py`, 60 mm/s demandés) : le tour fait en G26 a d'abord été comparé à celui de 14 h 51 au même endroit (5 parois : 5 cm d'écart avec le programme), puis le robot a suivi le chemin vrai du premier aller, recompté sans le patinage : (703, 131), (713, 117), (711, 92), (717, 84), puis 55 cm de plus jusqu'au pixel **(733, 59), en C28** (mur du fond à 69 cm). Retour par les mêmes points. **4,7 m, aucun contact.** Au même endroit que le matin la roue droite a encore glissé, de 4 cm seulement (2 cm de chemin en trop).
- **Détour par B22**, demandé pendant le retour (le robot était en J20) : J20 → G22 (`d`), puis à l'estime par la colonne 22, entre un grand meuble à l'ouest et la table à l'est. Arrivé au pixel **(578, 43), en B22**, mur du fond à 17 cm du pare-chocs, grand meuble à 10 cm du flanc gauche.
- **Le point étroit de E22** : 48 cm entre le grand meuble et le bord ouest de la table, pour un robot de 34 cm. À l'aller le robot est passé à moins d'un centimètre du meuble sans le toucher. Au retour, son flanc gauche a frôlé le bord de la table, que le capteur de distance ne voit pas même à 23 cm (seul le capteur optique de gauche a répondu, faiblement) ; recul de 12 cm, recentrage sur le meuble au capteur de distance (23 cm du centre, soit 6 et 8 cm de marge), second passage sans contact.
- **Retour dans le couloir** (`e`) : contact du pare-chocs gauche en J16, vers le pixel (409, 223), à 17 h 03 min 39 ; puis « stop » de l'utilisateur : roues arrêtées à 17 h 03 min 54.

Trois contacts légers en tout (H14, flanc en E22, J16) sur 32 m, tous hors de la pièce centrale.

**Ce que ce trajet apprend d'autre.**

- La comparaison au capteur de distance, depuis C28 : le mur nord est 17 cm plus loin que le plan ne le place vu du point où le robot se croyait. Dans cette pièce le plan et le trajet compté ne s'accordent qu'à 15 ou 20 cm.
- Un passage de 48 cm ne se franchit pas sur la foi d'une position : il faut se centrer sur ce qu'on voit (ici le meuble, au capteur de distance), comme pour la porte H12 (§ 41).
- Les quatre obstacles notés le matin dans la pièce centrale ont été déplacés de 28 cm dans `plan_lidar/obstacles.json`, et la voie fausse retirée.

**État à la fin** : robot arrêté dans le couloir, en J16, éveillé en mode Safe, batterie 1 403 mAh. La suite est au § 44.

## 44. Robot porté devant sa base, localisation, C9, coupure ; et ce qui change dans le code (2026-11-13, 17 h 08 à 17 h 20, puis hors robot)

Messages de l'utilisateur : « Déplace en avant de la base reprend localise bien et va en c9 puis retourne. Ensuite recharge toi. Ensuite apprend de cette run », puis, pendant le retour de C9 : « debranche et range, had to go, apprend et inove ». Enregistrements : `mesures/exploration18_20261113_171121_*` (passages `a`, `b`, `c`, tour `_tour_d12.json`, `_balise1.txt` ; les fichiers sans lettre sont ceux du retour interrompu).

**Deux messages mal lus d'abord.** « Déplace en avant de la base » : j'ai cru à un ordre et préparé le retour par le couloir. L'enregistrement disait autre chose : à 17 h 08 min 24 les deux roues se lèvent, le mode passe de Safe à passif, et neuf secondes plus tard le robot est reposé dans les faisceaux de sa base. C'est l'utilisateur qui l'avait porté. De même « débranche et range » : le cerveau ne répond plus au réseau depuis 17 h 19 min 55. Ses phrases sont souvent sans sujet : vérifier dans les mesures avant d'agir.

**Localisation d'un robot reposé à la main.**

1. Remis en mode Safe à sa demande (« reprend »), robot au sol, roues baissées.
2. `balise_base.py` : la base est dans le cap 208,8° du cerveau, le robot du côté rouge de ses faisceaux. D'où un départ supposé au pixel (420, 92), cap 125°.
3. `explorer3.py` sans `--depart-sur`, par C17, E15 et D12 : quatre recalages sur les repères, de 13 à 22 cm par rapport au filtre. Mais posée sur ces quatre tours, l'estime ne passe qu'à 151 mm d'eux (237 mm au pire), contre 32 à 55 mm sur les boucles : **avec un cap flottant (15° d'incertitude au départ), le filtre a bougé le cap de 2 à 5° à chaque tour, et les repères eux-mêmes se calent moins bien.** Le cap de départ tiré des faisceaux était pourtant bon : 125° donnés, 124° d'après l'estime posée sur les repères.
4. Contrôle sur place : robot amené sur l'endroit exact de D12 où il a déjà tourné, tour sur place comparé à cinq repères. Position : même point à 1 cm près (dispersion 10 et 12 mm). Cap : 19 parois vues à −0,9° de leur direction connue. Robot localisé à 1 ou 2 cm et 1 ou 2° près, neuf minutes après avoir été posé.

**C9.** D12 → D10 → C9 : 2,1 m en 1,4 min, aucun contact, corrections du filtre de 3 cm. Arrivé au pixel (224, 67). Le sol est un tapis en D10 et en C9.

**La coupure.** Le retour part de C9 à 17 h 19 min 33 : tour sur place, puis rotation de +134,5° lancée à 17 h 19 min 55,0. La dernière ligne reçue du cerveau est de 17 h 19 min 55,1 ; depuis, ni page ni réponse au ping. Le message de l'utilisateur arrive une minute après. Je n'ai donc ni fermé la séance (`s`, `x`), ni lancé l'accostage demandé plus tôt (« recharge toi »), ni rien vérifié. À savoir : un cerveau débranché pendant un mouvement laisse au robot son dernier ordre de roues, jusqu'à ce qu'on le soulève ou qu'on appuie sur CLEAN (règle connue) ; soulevé, le robot repasse en mode passif, puis s'endort et peut charger.

### Ce qui change dans le code, et comment c'est vérifié

1. **Le patinage est retiré du chemin compté** (`carto.patinage`, `carto.part_roulee`, branchés dans `explorer3.Estime` et dans le filtre de `localiser.py`, pour le firmware v9 et suivants). Quand les codeurs annoncent une rotation que le gyroscope ne voit pas, la roue en trop est retirée. Rejoué avec le code du dépôt sur l'aller de 14 h 51 : arrivée au pixel (713, 78) au lieu de (729, 66), 389 mm retirés. Sur les onze enregistrements du jour, hors des deux vrais patinages : 0 à 20 mm retirés par enregistrement, 0,05 % du chemin.
2. **Le pilote arrête une avance quand une roue patine** (`Pilote._mouvement`, 80 mm de trop) et `explorer3.py` finit alors le trajet à 60 mm/s demandés. Rejoué : les deux avances du matin auraient été arrêtées après 1,5 et 1,2 s, avec 4 cm comptés en trop au lieu de 21 et 17.
3. **La préférence pour les voies n'est plus la conduite par défaut** (`Plan.hors_voie` = 1 ; `explorer3.py --voies-fortes 3` la remet). Raisons : le contact qui la motivait n'en était pas un effet (§ 43), et sur le robot elle coûte un tiers de vitesse (§ 42). Les voies gardées dans les fichiers de tours et relues par `--plan-roule` restent. Vérifié : les chemins par défaut sont redevenus ceux d'avant le § 41, à l'identique sur sept trajets.
4. **Le cap lu sur les repères** (`Reperes.cap`) : du même endroit, les mêmes parois se voient dans les mêmes directions. Sur les tours du jour : juste à 3° près en général (corrélation 0,61 avec le cap tiré du trajet compté). `explorer3.py` ne corrige le cap que si l'écart est net (15 parois, 4° au moins, les deux quartiles du même signe) : cette règle n'aurait joué que deux fois aujourd'hui, robot reposé à la main, les deux fois dans le bon sens (−4,4° et −7,3° pour 8,2° et 6,2° d'erreur).
5. `explorer3.py --depart-sigma MM,DEG` : incertitudes de départ de la position et du cap données séparément (ici il aurait fallu 250,6).
6. `passage.py re=MM` : un recul court après un contact (il a fallu l'écrire à la main en séance).
7. `explorer3.py` finit proprement quand le cerveau ne répond plus, en disant que l'état du robot est inconnu.
8. Simulation (`essai_explorer3.py --plan`, deux mondes, cinq tirages, allers-retours) avec tout cela : mêmes résultats qu'avant le § 41 au millimètre et à la seconde près, aucun patinage vu (le simulateur n'en produit pas).

Hors dépôt : `plan_lidar/reperes_tours.json` refait avec les tours de l'après-midi (79 repères au lieu de 35 : couloir, G26, E11, devant la base), les quatre tours de devant la base étant posés d'après l'estime de la boucle et non d'après le filtre ; ils se recalent les uns sur les autres à 3 à 5 cm.

### Leçons de la journée

- **Avant de soupçonner le plan ou le planificateur, regarder si une roue a patiné.** Une demi-journée d'explications fausses (§ 41) tenait à 39 cm de chemin compté en trop.
- **Les repères sont la bonne mesure de position ; le filtre seul peut se tromper de 20 à 30 cm, même devant la base.** Là où il n'y a pas de repères (retour de C28, devant la base), l'erreur revient.
- **Le cap se garde, il ne se retrouve pas en un tour** : un tour sur place renseigne peu sur le cap. Les sources sûres sont le gyroscope, les faisceaux de la base (3°) et un tour fait sur un endroit à repères (1 ou 2°).
- **Un passage étroit se prend en mesurant ce qui le borde**, pas sur la foi d'une position : porte H12 par son montant, E22 par le meuble.
- **Lentement là où le sol accroche mal** : à 60 mm/s demandés la roue glisse de 4 cm, à 135 de 43.

**Non vérifié sur le robot** (cerveau éteint) : le retrait du patinage et l'arrêt sur patinage en roulant ; le cap corrigé sur les repères ; `--depart-sigma` ; `re=` ; les nouveaux repères. **Non fait** : le retour de C9, l'accostage, la fermeture de la séance ; relier entre eux par le trajet compté les repères d'endroits différents (seuls ceux de devant la base l'ont été, à la main) ; automatiser la porte et le centrage dans un passage étroit.

**État à la fin** : inconnu de moi. Dernière position sûre : C9, pixel (224, 67), à 17 h 19 min 55, en mode Safe, une rotation tout juste lancée ; batterie 1 370 mAh à 17 h 17. D'après son message, l'utilisateur a débranché le cerveau et rangé le robot. À vérifier à son retour : robot immobile et endormi, posé ou non sur sa base, voyant de charge.

## 45. Mesure : base → C28 → base d'un trait, avec le code corrigé (2026-11-14, 9 h 04 à 9 h 30)

Demande de l'utilisateur, à ma question « je refais base → C28 → base pour mesurer le gain sur le robot ? » : « oui mesure le je vais brancher et reculler quand tu es pret », puis « C'est fait ». Enregistrements : `mesures/exploration19_20261114_090420_*` (passages `a` à `g`, mesures par les faisceaux `_balise0.txt`, `_balise1.txt`, `_balise2.txt`), `mesures/position_20261114_092951.*`.

**Avant de rouler**, hors robot : le recalage sur les repères et le cap lu sur les repères, qui n'avaient jamais tourné dans un trajet, ont été essayés en simulation avec des repères tirés de cinq trajets simulés. Trois trajets : 13 tours sur 13 calés, aucun cap corrigé quand le cap de départ est juste, un cap corrigé de −5,2° et de +6,0° quand il est donné faux de +8° et de −8° ; erreur finale 18 à 27 mm.

### Le résultat

| | Premier trajet (13, § 41) | Ce trajet |
|---|---|---|
| Durée, du départ à l'arrivée devant la base | 45,7 min | **22,9 min** |
| Chemin | 38,7 m | 32,3 m |
| Contacts (tous légers) | 7 | **5** |
| Tours sur place calés sur les repères | 2 sur 23 | **16 sur 23** |
| Pièce centrale, G26 → C28 → G26 | 5 contacts, 19 min dont 16 à la main | 3 contacts, 3,5 min, sans reprise à la main |
| Porte H12 vers le nord | 10 min à la main | 3,3 min à la main |
| Patinage | deux fois, 43 et 35 cm de roue en trop | aucun |
| Arrivée : écart à l'axe de la base | 0,5 et 1,3 cm | 0,2 et 0,0 cm |
| Arrivée : direction de la base, 90° attendus | 88,5° | 83,0° et 81,9° |

**Deux fois plus vite, deux contacts de moins.** Le gain de temps vient surtout de ce qui avait été compris la veille (le vrai chemin de la pièce centrale, la méthode pour la porte) et des repères. **Le retrait du patinage et l'arrêt sur patinage n'ont pas servi : aucune roue n'a patiné**, alors que le robot a traversé à 135 mm/s demandés le sol sombre où la roue avait glissé deux fois la veille (33 mm retirés en tout sur 32 m, aucun arrêt). Ce code reste donc vérifié par rejeu seulement ; il n'a rien dérangé.

### Par tronçon

| Tronçon | Heures | Chemin | Contacts |
|---|---|---|---|
| Base → D14 → E12 → G12 (`a`) | 9 h 05 min 15 à 9 h 06 min 42 | 3,1 m | 0 |
| Porte H12 vers le sud (`passage.py`) | 9 h 06 min 49 à 9 h 08 min 15 | 1,0 m | 0 |
| Couloir → G26 (`b`) | 9 h 08 min 20 à 9 h 11 min 21 | 9,0 m | 1, en J16 |
| G26 → C28 (`c`, `--voies-fortes 3`) | 9 h 11 min 45 à 9 h 12 min 36 | 2,5 m | 0 |
| C28 → G26 (`d`) | 9 h 13 min 30 à 9 h 15 min 15 | 4,1 m | 3, au même objet, en E28 |
| G26 → J24 → J20 (`e`) | 9 h 15 min 57 à 9 h 17 min 13 | 3,5 m | 0 |
| J20 → J12, centré au capteur de distance (`passage.py`) | 9 h 17 min 21 à 9 h 22 min 40 | 3,9 m | 0 |
| Porte H12 vers le nord (`passage.py`) | 9 h 22 min 57 à 9 h 26 min 15 | 0,8 m | 0 |
| G12 → E12 → D14 → D16 (`g`) | 9 h 26 min 18 à 9 h 28 min 08 | 3,9 m | 1, en E13 |

### Les cinq contacts, et leur cause

1. **J16, pare-chocs gauche (côté nord), 9 h 09.** Mesuré au retour, regards à 90° et 270° tous les 20 cm : entre J15 et J17 le couloir ne laisse que 68 cm (un rebord de 10 cm au nord à partir de la colonne 16), soit 17 cm de chaque côté du robot. Le chemin prévu y passait 5 à 15 cm au nord du milieu, et deux obstacles que j'avais notés côté sud d'après des contacts l'y poussaient ; celui ajouté le matin même était mal placé (le mur sud est à 39 cm du milieu) : retiré. Au retour, centré au capteur de distance : aucun contact.
2. **E28, pare-chocs gauche, trois fois de suite, 9 h 14. Ma faute.** En C28 le repère de la veille avait recalé le robot de 13 cm de travers ; j'en ai déduit une erreur de cap de 3° et je l'ai corrigée à la main avant le retour. C'était faux : le filtre a rendu +3,4° au tour suivant, et entre-temps le robot avait dévié de 9 cm vers l'est, contre quelque chose qui borde le passage de ce côté. Les deux contacts suivants sont le même essai refait deux fois (« passage déjà roulé »). À l'aller, sans cette correction : 2,5 m en 50 s, aucun contact.
3. **E13, pare-chocs droit, 9 h 27.** Le même objet que la veille, au même endroit du robot (pixel (318, 122)) : il est plus près de la ligne suivie que je ne l'avais noté. Replacé en (325, 129), rayon 22 cm.

### Ce que ce trajet apprend d'autre

- **Passer par les endroits à repères.** Au retour je visais (370, 117) en D14, à 45 cm des repères de (368, 97) : aucun recalage sur le dernier tronçon (1 tour calé sur 4), et l'arrivée a un cap faux de 7 à 8° d'après les faisceaux. À l'aller, par (368, 97) : 3 tours calés sur 4.
- **Un repère seul peut servir** : celui de C28, un seul tour fait la veille, a calé le robot deux fois (quatre parois communes au moins).
- **Devant la porte H12 côté couloir, la position était encore fausse de 14 cm** (vers l'est), malgré le couloir roulé centré : c'est le regard vers la porte (mur à 35 ou 40 cm, ouverture à gauche) qui l'a montré. Décalage, nouveaux regards (ouverture de 80° à 120°, montant est à 45 cm vers 55°), passage au cap 100°, qui laisse 15 et 13 cm : aucun contact, en 3,3 min au lieu de 10.
- **Ne pas corriger le cap à la main** d'après un seul écart de position : c'est précisément ce que la règle prudente de `Reperes.cap` refuse de faire (elle n'a jamais joué pendant ce trajet : écarts lus de −4,9° à +5,6° sur 7 à 26 parois, jamais nets).
- Le cap lu sur les repères en G12 au retour (19 parois, −3,0°) n'a pas atteint le seuil de 4° ; l'erreur de cap à l'arrivée était de 7 à 8°. Le seuil est peut-être trop haut quand les parois sont nombreuses : à revoir avec plus de cas.

**Hors dépôt** : `plan_lidar/obstacles.json` (14 entrées : objet de E13 replacé, côté est de la pièce centrale ajouté au pixel (724, 120), entrée fausse de J16 retirée) ; `plan_lidar/voies_piece_centrale.json` (le chemin de la veille) ; `plan_lidar/reperes_tours.json` (81 repères, avec les tours de C28 et de B22).

**Non vérifié** : l'arrêt sur patinage en roulant (pas de patinage ce jour-là) ; la distance du robot à sa base à l'arrivée (99 cm de sa place sur la base d'après le filtre ; un objet à 50 cm dans la direction de la base au capteur de distance).

**État à la fin** : robot en D16, devant sa base, dans son axe à quelques millimètres près, tourné vers elle (récepteurs du dessus et avant gauche « rouge et vert », avant droit « rouge »), pas posé dessus ; session fermée (`5`, `s`, `x`) à 9 h 29 min 57, capteur de distance au repos, vitesse 150, batterie 1 992 mAh.

## 46. Accostage après la mesure : l'ordre du robot n'a pas abouti seul (2026-11-14, 9 h 34)

Accord de l'utilisateur : « Oui, accoste-le ». Enregistrement : `mesures/exploration20_20261114_093358_*`. Robot au départ : en D16, dans l'axe de sa base à quelques millimètres près, tourné vers elle (§ 45), endormi.

**Ce que l'enregistrement montre.**

- 9 h 34 min 13 : réveil, mode passif, touche `h` (Seek Dock). Les trois récepteurs lisent la base (172, 172, 168).
- 9 h 34 min 16 à 30 : le robot avance vers la base en louvoyant (cap de −29° à +27°), jusqu'à **215 mm/s** et **1,57 A**. **Le pare-chocs gauche s'enfonce trois fois en route**, à 44, 54 et 64 cm du départ : quelque chose se trouve sur le chemin de la base. Champ proche (161) reçu à partir de 70 cm. À 1,15 m du départ, pare-chocs gauche enfoncé de nouveau : la base.
- 9 h 34 min 31 à 39 : il recule, tourne sur lui-même, touche encore (droit, puis les deux, puis gauche), et **s'arrête pour de bon à 9 h 34 min 39, à 94 cm du départ et 10 cm à droite de l'axe, tourné de 140° vers la droite**, moteurs coupés. Il n'est pas sur sa base.
- 9 h 34 min 40 à 43 : le cap revient de −140° à +10° **sans que les roues tournent**, puis le sol devient sombre sous les deux capteurs de vide avant et les deux pare-chocs s'enfoncent : le robot a été tourné et poussé sur sa base à la main.
- 9 h 34 min 48 : le robot ne répond plus aux lectures (toutes à zéro). 9 h 34 min 50 : dernière ligne reçue du cerveau ; ni page ni ping depuis.

**Ce que cela dit.**

- **L'ordre « rentre à la base » a échoué cette fois**, alors que le robot partait dans l'axe à moins d'un mètre. Le 13 (§ 40) il avait réussi en 21 s depuis le même genre de départ, avec un seul recul. La différence visible : trois contacts en route. L'objet vu au capteur de distance à l'est de l'axe (§ 42, pixel (419, 51)) ou autre chose gêne l'approche.
- La distance : le robot a touché la base après 1,15 m de trajet. Le filtre le plaçait à 99 cm de sa place sur la base ; l'objet vu à 50 cm (§ 45) n'était donc pas la base.
- Pendant cet ordre le robot roule plus vite et consomme six fois plus que quand le cerveau le conduit (§ 40) : confirmé.

**Non vérifié** : que le robot charge (le cerveau s'est tu deux secondes après l'arrivée sur la base) ; pourquoi le cerveau s'est tu (débranché par l'utilisateur, comme la veille à 17 h 19, ou autre chose). La séance n'avait pas à être fermée : le robot est resté en mode passif pendant tout l'accostage.

**À proposer** : dégager le devant de la base (rien à moins de 50 cm de chaque côté de l'axe sur 1,2 m) ; ou un accostage mené par le cerveau, lentement, sur les faisceaux.

## 47. Centrage automatique dans les passages étroits : écrit, essayé en simulation, rejoué sur les mesures du matin (2026-11-14, sans le robot)

Demande de l'utilisateur, à ma proposition de préparer un centrage automatique au capteur de distance : « Oui prepare, et prepare moi donc un resume de l<avancement de la situaiton ». Rien n'a roulé : robot sur sa base, en charge d'après lui (« Oui, il charge ») ; cerveau muet depuis 9 h 34. Le résumé demandé est dans [`../AVANCEMENT.md`](../AVANCEMENT.md).

### Ce que l'enregistrement du matin a appris

Relecture de `mesures/exploration19_20261114_090420_capteurs.csv`, couloir de J20 à J12 (9 h 17 à 9 h 22) et porte H12 (9 h 22 à 9 h 26). Scripts : `data_analysis/u_echelle_gyro_murs.py`, `data_analysis/v_rejeu_centrage.py` (résultats `results_u_…` et `results_v_…_20261114.txt`).

1. **Où est passé le temps du couloir fait à la main** : 3,9 m en 319 s, dont 188 s à l'arrêt, 102 s en rotation et une trentaine de secondes à avancer. Sept arrêts ; à chacun, 12 s de rotations et de lectures, puis 15 à 25 s d'attente entre deux de mes ordres.
2. **Les capteurs optiques de côté ne voient pas les murs du couloir.** Dans la partie de 68 cm, pendant les avances : 4 à 16 pour le capteur gauche (mur à 22 cm du flanc), 0 pour le droit (mur à 13 cm). Sur toute la séance ils montent à 308 et 99. Pas de centrage en roulant à attendre d'eux à ces distances.
3. **Un regard de côté, robot immobile, est stable à 3 mm** (441 à 447, 364 à 366, 271, 287 à 291…).
4. **Tous mes regards tournaient dans le même sens** : un tour complet vers la droite à chaque arrêt, 2 792° nets dans le couloir. L'échelle du gyroscope pèse alors lourd : en tournant chaque pas du cap corrigé par 1,0045, la position en fin de couloir diffère de 42 cm de celle qu'on obtient en tournant tout le trajet d'un seul angle. Jugée sur les murs, qui sont droits : ils sortent droits et parallèles pour une échelle de 1,001 à 1,0025 ; et le déplacement de côté compté s'accorde avec ce que les regards disent de la distance au mur à 3, 3 et 8 mm près avec 1,002, contre 8, 13 et 29 mm avec 1,0045. **Indication, pas mesure** (un seul passage, sept arrêts, des rotations vers la droite faites par le cerveau) : pour ces rotations-là, 1,0045 serait trop fort. À vérifier par un essai simple : quelques tours à droite puis autant à gauche devant un mur.
5. **La lecture du capteur de distance écrite dans le journal a 0,15 s de retard pendant une rotation.** Le cerveau y écrit la médiane de ses trois dernières mesures, faites dix fois par seconde (`radar.ino`, `radarFrontMm`). Vu devant la porte : robot immobile au cap 67°, 443 mm ; pendant une rotation à 45 °/s la même lecture arrive 6° plus tard ; au cap 77°, 478 mm, 7° plus tard. Autre effet de cette médiane : un écho qui ne tient qu'une mesure n'apparaît pas.
6. **Ce qu'un vrai éventail montre.** Une paroi proche s'entend très en biais : à 44 cm, lecture plate de 439 à 445 mm sur 15° autour de sa perpendiculaire, puis qui monte lentement jusqu'à 622 mm à 81° d'elle. Le coin d'un rétrécissement à 58 cm s'entend sur 50°. La direction d'un écho est donc floue à 15° près, alors que sa distance est juste. Devant la porte H12, ce qui se lit nettement est la trouée : des lectures lointaines (3,6 m, ou rien) du cap 88° au cap 123°, milieu 105° ; le robot y est passé à la main, tout droit au cap 102 à 103°, sans contact.

Ce que cela remplace : mon simulateur, où un mur vu de biais ne renvoie rien (vrai à 3 m, faux à 50 cm) ; et l'idée du rapport de suivre un mur avec les capteurs optiques une fois étalonnés (étape 7) : à plus de 10 cm du flanc, ils ne lisent rien d'utile sur ces murs.

### Ce qui est écrit

- **`code/outils/centrage.py`**. À chaque arrêt : regard à gauche, demi-tour par l'avant en lisant le capteur (l'éventail), regard à droite, retour vers l'avant. Les trois rotations s'annulent (+90°, −180°, +90°) : l'échelle du gyroscope ne s'accumule plus. Dans un couloir, le milieu se lit sur les deux regards ; un écho de l'éventail ne le déplace que s'il est entier et plus près de la ligne que la paroi, et jamais jusqu'à moins de 8 cm d'une paroi mesurée. Devant une porte (aucune paroi de côté), c'est la trouée qui commande : décalage vers son milieu, approche, regard de près, franchissement d'une traite. Deux arrêts de suite donnent le cap du robot par rapport aux murs. Le pas passe de 40 à 80 cm quand tout est calme. Au premier contact, tout s'arrête.
- **`code/outils/passage.py`** : ordres `centre=CAP,DIST[,PAS[,VITESSE]]` et `eventail=CAP` (regards et éventail sans avancer, avec la trouée). La position y est maintenant suivie par `centrage.Mobile`, chaque pas tourné du cap corrigé comme dans `explorer3.py` (1 et 6 mm d'écart avec l'ancienne façon sur les deux passages de porte du matin).
- **`code/outils/pilote.py`** : `tourne(…, v_roues=)` demande au cerveau une rotation à une vitesse donnée (50 à 100 mm/s). Aucun changement du firmware.
- **`code/outils/simulateur.py`** : durée d'une rotation à vitesse donnée d'après les mesures du matin (un quart de tour 3 s, un demi-tour 5 s à 45 °/s) ; lecture en retard et médiane de trois pendant une rotation. Vérifié : les essais d'`explorer3.py` donnent le même résultat qu'avant (monde `deux_pieces`, graine 2 : 23 tours, 41,1 m, 17,0 min avec le firmware 8 ; 26 tours, 52,7 m, 20,6 min avec le 10).
- **`code/outils/essai_centrage.py`** : les essais simulés ci-dessous.

### En simulation

`essai_centrage.py tout --graines 5` (`results_w_essai_centrage_20261114.txt`, figure `fig20_centrage_simulation_20261114.png`). Deux mondes : un couloir qui reprend les largeurs mesurées le matin (95, 84, 73 puis 68 cm, et plus loin une ouverture sur un côté), 3,9 m à faire ; une porte de 62 cm dans une cloison de 12 cm, 1,8 m à faire. 75 départs par méthode : robot décalé de −15, 0 ou +15 cm, cap faux de −6 à +6°.

| | Tout droit, sans regarder | Centrage, pas fixe de 40 cm | Centrage, pas qui s'allonge |
|---|---|---|---|
| Couloir : essais avec contact | 54 sur 75 | 0 | **0** |
| Couloir : jeu le plus petit (médiane) | | 91 mm (133) | 88 mm (133) |
| Couloir : arrêts, durée simulée | | 11, 197 s | **9, 169 s** (de 151 à 228) |
| Couloir : écart au milieu à l'arrivée | 74 mm, 170 au pire | 7 mm, 23 au pire | 3 mm, 26 au pire |
| Porte : essais avec contact | 29 sur 75 | 0 | **0** |
| Porte : jeu le plus petit (médiane) | | 80 mm (119) | 80 mm (119) |
| Porte : arrêts, durée simulée | | 6, 104 s | **5, 90 s** (de 75 à 118) |

Le cap par rapport aux murs est retrouvé à 0,1° près en médiane (1,4° au pire). Le couloir simulé prend 2,8 min ; le vrai, à la main, 5,3 min.

### Sur les mesures du matin

`v_rejeu_centrage.py` redonne au programme ce que le capteur a lu le matin, y compris pendant les rotations, et note ce qu'il aurait décidé.

- **Couloir, sept arrêts.** Largeurs lues : 945, 859, 740, 688 et 679 mm, puis un côté ouvert. Au premier arrêt l'éventail voit le rétrécissement 43 cm devant, à droite, et le programme décide un pas de côté de 57 mm vers la gauche (le passage qui suit est décalé de 5 à 6 cm de ce côté). Ensuite des avances de 40 cm, cap retouché de −5,2° à +6,6°. Cap par rapport aux murs mesuré trois fois : +2,9°, +0,6°, +2,0°. Aucune décision ne pousse le robot vers une paroi.
- **Porte H12, premier arrêt** (le robot y était 14 cm trop à l'est, et je l'avais décalé de 14,5 cm vers l'ouest) : trouée du cap 110° au cap 127° ; décision : pas de côté de 173 mm vers la gauche, c'est-à-dire l'ouest. Les échos des bords, eux, auraient dit 258 mm : ils ne sont pas crus.
- **Porte H12, second arrêt** (d'où j'étais passé tout droit au cap 102 à 103°) : trouée du cap 88° au cap 123°. Avec l'axe 100° : pas de côté de 53 mm vers la gauche. Avec l'axe 103° : franchissement, 867 mm à +1,5° de l'axe. C'est ce que j'avais fait à la main.

### Ce qui n'est pas vérifié

- **Rien n'a roulé.** Le simulateur n'entend pas les parois en biais comme le vrai capteur ; le rejeu ne porte que sur un couloir et sur deux arrêts devant une seule porte, un seul jour.
- La durée réelle (2,8 min simulées contre 5,3 à la main) et le jeu réel.
- `CAP_MURS`, le cap d'après les murs affiché à la fin : il suppose que l'axe donné est bien celui du passage sur le plan ; pas encore utilisé.
- L'éventail lu dans le journal perd les échos d'une seule mesure (médiane). Pour un éventail fin il faudrait la mesure brute dans le journal : une colonne de plus, donc un changement de firmware, à proposer à l'utilisateur.

### Première sortie proposée sur le robot

Dans cet ordre, lentement, sous surveillance : `eventail=` devant la porte H12 et dans le couloir (des rotations seulement) ; puis `centre=` dans le couloir entre J17 et J15 ; puis la porte.

**État à la fin** : robot sur sa base d'après l'utilisateur (non vérifié par moi) ; cerveau muet ; aucun ordre envoyé.

## 48. La cuisine explorée, robot posé à la main en C39 ; et des trous de plusieurs secondes dans les lectures, pendant lesquels le robot roule sans surveillance (2026-11-14, 14 h 31 à 15 h 09)

Demande de l'utilisateur : « je vais aller placer le robot vers c39, explore et map cette piece puis dit moi quand c fait (il y a une mini marche entre c28 et c29, mais le robot etait capable de la franchir, il faut juste insister un peu), apres la map de la cuisine on lui apprendra a bien franchir le pallier ». Je lui ai demandé de retirer du sol ce qui peut se renverser et de poser le robot le nez vers la marche. Enregistrements : `mesures/exploration21_20261114_143415_*` (passages `a` et `b`, `_essai_tours.json`, `_essai_tours_interrompu.json`), puis `mesures/repos_f36_*` (robot immobile). Cartes et dessins, hors dépôt : `plan_lidar/carte_grille_20261114_cuisine*.png`, `plan_lidar/exploration21_trajet_cuisine.json`, `plan_lidar/cuisine_*.png`.

### Mise en route

- 14 h 31 : cerveau rallumé (« mise sous tension »), robot en l'air (roue droite levée), puis posé. Il répondait en mode passif, puis s'est tu 25 s après le démarrage du cerveau ; une seule impulsion de réveil (`w`) à 14 h 34 min 39 a suffi. Batterie 2 068 mAh sur 2 068 ; les quatre capteurs de vide lisent 2 480 à 2 550 sur ce sol.
- Entre 14 h 32 et 14 h 34, robot posé et endormi, le gyroscope l'a vu tourner de 172° : l'utilisateur l'orientait vers la marche.
- `f` (Safe), capteur de distance droit devant : 1,10 m.

### Premier tour sur place : arrêté par le cerveau, « rotation trop rapide »

`essai_tours.py … --depart 1020,66,180 --flou 500,25 --vitesses 60`. Arrêté après 64°. Dans le journal : rotation normale à 35 °/s, puis une lecture manquée (406 ms sans ligne), pendant laquelle le cap passe de 500,4° à 522,3° ; les compteurs des roues disent la même chose (19°). Le cerveau a coupé les roues quand le gyroscope a dépassé 90 °/s, et le robot a encore tourné de 16° sur son élan. Il a donc réellement tourné deux à trois fois plus vite que demandé pendant un instant. **Cause non établie.** Deux pistes : quelqu'un ou quelque chose l'a poussé ; ou un ordre de roues a été mal reçu par le robot, à un moment où il brouillait une lecture sur trois (voir plus bas). Une fois sur onze tours ce jour-là, jamais vu les jours précédents.

### Second tour : où est le robot

Tour complet, 100 mesures, 7 paliers (direction depuis le début du tour, distance en mm, largeur en degrés) : `33°:189/14 58°:352/22 97°:260/49 200°:662/42 305°:1450/16 322°:1181/12 1°:741/42`. Filtre : case C39, pixel (1010, 71), cap au début du tour 269°, note 0,66, étalement 657 mm et 31°. Le robot était dans un recoin : le mur de droite à 29 cm de son centre, une surface plane à 77 cm vers le bas, une autre à 69 cm vers le haut, et quelque chose à 19 cm du capteur, soit 5 cm de sa coque, en bas à droite. Il était bien tourné vers la marche avant le premier tour (188° ± 5°). La surface du bas est 25 cm plus loin que le bord de la masse sombre du plan en E39 : le plan montre peut-être le dessus d'un meuble sous lequel le capteur voit.

### Exploration

Commande du passage `a` (14 h 41 à 14 h 44) :

```
python explorer3.py --plan plan_lidar/plan_lidar.png --px-par-m 53 --depart-plan 1015,67,291 --depart-sigma 250,8
  --plan-passe plan_lidar/plan_lidar_zones.jpg --plan-ferme plan_lidar/obstacles.json --reperes plan_lidar/reperes_tours.json
  --fluide --vitesse 100 --tour-v 60 --sans-z --k-gyro 1.0045 --filtre-n 20000 --stations 14 --minutes 30
  --interdit "14000,6943,1300;21698,6679,1650;21698,3849,1650" -- 192.168.18.25 PREFIXE
```

Les zones interdites (millimètres du plan) : un disque de 1,3 m autour de la marche (limite C28/C29, pixel (742, 66)) et deux disques sur la pièce marquée inaccessible. Sans destination, `explorer3.py` choisit lui-même ses arrêts dans ce que chaque tour voit de libre ; le plan ne sert qu'au filtre.

| Tour | Case, pixel | Note du filtre | Correction du filtre | Saut à l'arrivée | Remarque |
|---|---|---|---|---|---|
| a0 | C39 (1013, 67) | 0,96 | (−38, −4) mm, +0,9° | | départ |
| a1 | D37 (975, 91) | 0,69 | (+57, −8) mm, +0,8° | 66 mm | |
| a2 | D36 (937, 81) | 0,70 | (+50, −76) mm, +3,1° | 110 mm | arrêt seul le long du comptoir : capteur optique à 408 |
| a3 | E36 (930, 129) | 0,21 | (+16, −20) mm, +1,2° | 57 mm | |
| a4 | F36 (937, 142) | 0,67 | (−154, +151) mm, −6,1° | 205 mm | |
| a5 | limite D35/E35 (925, 106) | 0,60 | (+27, +48) mm, −3,9° | 45 mm | « devant une porte » |
| b0 | G36 (937, 180) | 0,81 | (−20, −63) mm, −0,5° | 59 mm | départ du passage `b` |
| b1 | F36 (935, 156) | 0,92 | (−70, −51) mm, +0,3° | 100 mm | |

- Passage `a` : 6 tours, 18 mouvements, 5,5 m en 2,7 min, aucun contact. Fin : en avançant de F36 vers G36, « le robot ne répond plus » (voir plus bas), puis le capteur de distance a arrêté le robot à 29 cm de quelque chose de bas devant le mur du bas, et l'avance suivante a été refusée (27 cm, seuil 30) ; `explorer3.py` s'arrête sur un refus.
- Passage `b` (14 h 46 à 14 h 47), relancé depuis `relance.py`, avec en plus des disques interdits sur les tours déjà faits et sur le passage étroit de D32 à D34 : 2 tours, 1,6 m, **un contact** du pare-chocs, de face, en F37 au pixel (957, 150), la table ou une chaise ; roues arrêtées par le réflexe du cerveau, deux reculs, puis le tour b1. Fin : « plus rien à voir ».
- Troisième lancement vers D34 (pixel (903, 88)), pour regarder l'entrée du passage étroit : premier tour arrêté à 209° sur « le robot ne tourne pas (roues bloquées ?) », pendant un silence du robot de 3,3 s. Fausse alarme : il tournait (120° pendant le silence). Je n'ai pas insisté.

`outils/trajet_passages.py` (nouveau) fabrique, à partir des passages, le fichier de trajet que `carte_grille.py --global` dessine.

### Ce que la carte montre

- Sol roulé : la bande D34 à D39 sous le comptoir, le recoin C39, et le coin à gauche de la table, de E35 à G36. La table du plan (E37, F37) est là où le robot a touché.
- Pas visité : le côté droit de la table (F38, encombré, sans doute des chaises), le passage étroit qui part de D34 vers la marche (55 cm sur le plan entre le comptoir et un mur, de D32 à D34), la marche elle-même.
- Le plan ressemble moins qu'ailleurs à ce que voit le capteur : notes de 0,21 à 0,96, corrections de 45 à 205 mm à l'arrivée sur un tour (66 mm en médiane). La carte de la pièce est donc juste à 10 ou 20 cm près, pas mieux.
- Aucun repère : `reperes.py` ne garde aucun des 8 tours, aucun endroit n'ayant été vu deux fois.

### Des trous de plusieurs secondes dans les lectures : cause non établie

En cherchant pourquoi deux tours avaient été arrêtés, j'ai compté les trous du journal sur l'horloge du cerveau (une ligne par lecture réussie des capteurs, toutes les 47 ms en temps normal). Outil : `data_analysis/y_silences_robot.py`, résultats dans `results_y_silences_robot_20261114.txt`.

| Enregistrement | Durée | Trous de plus de 250 ms | Dont plus d'une seconde | Le plus long |
|---|---|---|---|---|
| `exploration17` (2026-11-13, 16 h 32) | 38,4 min | 1 | 0 | 0,9 s |
| `exploration19` (2026-11-14, 9 h 04) | 25,4 min | 4 | 1 | 1,5 s |
| `exploration21` (2026-11-14, 14 h 34) | 16,1 min | 56 | 5 | 5,1 s |

Dans `exploration21`, par minute depuis le réveil de 14 h 34 min 39 : 28, 14, 7, 1, puis presque rien, et cinq trous longs : 2,6 s et 1,1 s (robot à l'arrêt), 1,6 s (pendant un tour), 5,1 s à 14 h 44 min 19 (pendant une avance), 3,3 s (pendant un tour).

**Ce que le robot fait pendant un trou.** Le cerveau ne lit plus le pare-chocs, les roues ni le sol. Une avance n'est coupée qu'après 1,5 s sans lecture (`mouv.ino`), un tour après 2,5 s (`tour.ino`). À 14 h 44 min 19 le robot a ainsi roulé **196 mm sans surveillance** (compteurs des roues : +428 et +454 pas ; capteur de distance : de 617 à 416 mm), puis le cerveau a coupé les roues (« le robot ne répond plus »). Ces 196 mm n'ont pas été comptés dans la position (`sauts` refusés : 2) : le passage `b` est parti d'une position fausse d'autant, et le filtre n'en a repris que 6 cm. Rien n'a été touché pendant ces trous ; le contact de F37 est arrivé pendant que les lectures passaient, et le réflexe a joué.

**Affirmation remplacée.** `code/README.md` dit du réflexe du pare-chocs : « roues arrêtées par le cerveau (au plus 200 ms après le contact) ». C'est vrai tant que les lectures passent. Pendant un trou, le robot roule jusqu'à 1,5 s sans réflexe (2,5 s pendant un tour) : une vingtaine de centimètres à 100 mm/s.

**Trois essais robot immobile**, en F36, mode passif, pour chercher la cause (aucun ordre de roues) :

| Essai | Réveil par impulsion | Touche `e` chaque seconde | Ce qui s'est passé |
|---|---|---|---|
| `repos_f36_sans_e`, 14 h 58 min 42 à 15 h 01 min 10 | 14 h 58 min 27 | non | aucun trou : 2 916 lectures, le plus long écart 0,11 s |
| `repos_f36_avec_e`, 15 h 01 min 22 à 15 h 03 min 28 | le même | oui | 47 s sans trou, puis six trous de 2,1 à 11,5 s entre 15 h 02 min 08 et 15 h 02 min 45 (31,5 s sans lecture) ; pendant ce temps le PC n'obtient plus l'état du cerveau (onze demandes sans réponse) |
| `repos_f36_avec_e_ping`, 15 h 04 min 55 à 15 h 08 min 05, avec un ping du PC deux fois par seconde (`outils/ping_suivi.py`) | 15 h 04 min 41 | oui | « Pas de réponse du robot » quatorze fois en 40 s ; 797 lectures en 51 s au lieu de 1 080 ; à 15 h 05 min 46 le robot écrit « Soft reset! » puis « iRobotBoot V4 Roomba 600-STM32 Bootloader … » : **il a redémarré de lui-même** et ne répond plus ensuite ; à partir de 15 h 05 min 48, 175 pings sur 370 restent sans réponse (coupures de 0,5 à 11 s) |

**Ce qui est établi :**

1. Chaque trou de plus d'une seconde d'`exploration21`, et celui du matin, tombe au moment où le PC n'arrive plus à joindre le cerveau ou n'obtient sa réponse qu'après une à deux secondes (fichier `_etat.jsonl` : 14 h 36 min 48, 14 h 38 min 10, 14 h 43 min 18, 14 h 44 min 13 à 18, 14 h 48 min 18 à 20 ; le matin 9 h 23 min 59).
2. La liaison entre le PC et le cerveau décroche par périodes : 40 pings sur 40 à 14 h 53, 2 perdus sur 12 à 15 h 08 (jusqu'à 1,7 s d'aller-retour), près d'un sur deux pendant le troisième essai. En F36 le cerveau reçoit le réseau de la maison à −72 dBm, avec six autres réseaux entre −67 et −88 dBm.
3. Dans le firmware, chaque ligne de la console et du journal est écrite au client TCP depuis la boucle principale (`TeeOut::write`), la même boucle qui lit les capteurs, tient le réflexe du pare-chocs, l'arrêt du capteur de distance et la surveillance des tours et des avances. Lu dans le code, pas démontré par un essai : une écriture qui attend le réseau suspend tout le reste.
4. Le robot, de son côté, s'est mal conduit après un réveil par impulsion : des lectures de la touche `e` sans réponse, « Performing eEEProm transfer » à 14 h 37 min 11, et un redémarrage à 15 h 05 min 46 alors que le cerveau ne lui envoyait que des questions.

**Ce qui ne l'est pas :**

- pourquoi la liaison décroche : la force du signal dans la cuisine, les réseaux voisins, le PC (un VPN y est actif depuis le matin), ou l'alimentation du cerveau ;
- pourquoi le robot a redémarré, et si la « rotation trop rapide » du premier tour était un ordre de roues mal reçu ;
- si une seule cause explique les deux (une alimentation du cerveau trop faible ferait décrocher la radio et brouillerait aussi ce qu'il envoie au robot) ;
- la rafale des trois premières minutes d'`exploration21` (49 trous d'environ 0,4 s) : le firmware note depuis le 2026-11-09 qu'après un réveil par impulsion le robot « brouille une lecture sur trois », mais l'essai sans la touche `e`, fait quinze secondes après un tel réveil, n'a eu aucun trou.

**Erreurs de ma part pendant la séance, corrigées depuis.** J'ai écrit à l'utilisateur que le Wi-Fi faisait des « absences du cerveau », puis que ce n'était pas le Wi-Fi mais le robot qui ne répondait pas. Aucune des deux phrases n'était établie quand je l'ai écrite : les deux phénomènes existent, et leur lien n'est pas connu.

### À faire avant de refaire rouler le robot

1. Par l'utilisateur : regarder si la batterie portable du cerveau est chargée et son câble bien enfoncé ; regarder les trois fils entre le cerveau et le robot (une photo suffit).
2. Robot immobile, cinq minutes de lectures avec le ping en même temps, sans la touche `e` : aucun trou attendu. À refaire près de la base pour comparer la liaison.
3. À proposer à l'utilisateur, parce que cela touche au firmware : que le cerveau n'attende jamais le réseau (une ligne qui ne part pas tout de suite est abandonnée), et qu'il coupe les roues dès 0,3 s sans lecture au lieu de 1,5 et 2,5 s.
4. Dans les outils du PC : ne plus envoyer la touche `e` chaque seconde (ses valeurs sont dans le journal depuis la v8) ; refuser un mouvement si une lecture a manqué dans les trente dernières secondes ; compter le chemin sur les compteurs des roues quand la position du cerveau saute un trou.

### Non fait, non vérifié

Le tour de D34 et le passage étroit vers la marche ; le côté droit de la table ; des repères dans la cuisine ; la carte vivante pendant cette séance (je ne l'ai pas regardée) ; les causes ci-dessus.

**État à la fin** : `s` puis `x` à 14 h 50 min 46 après l'exploration ; ensuite trois réveils pour les essais immobiles, sans aucun ordre de roues ; le robot a redémarré de lui-même à 15 h 05 min 46 et ne répond plus au cerveau (il dort). Il est en F36, pixel (935, 156), tourné vers 318° environ, **hors de sa base : il ne charge pas** ; batterie 2 007 mAh sur 2 068 à 15 h 04. Cerveau allumé. Capteur de distance arrêté.

### Complément : une photo de la pièce (reçue à 15 h 16, non gardée)

L'utilisateur a envoyé une photo de la cuisine, prise du bas du plan vers le haut. Ce qu'elle précise, reporté sur la carte (`plan_lidar/reperes_20261114_cuisine.json`) :

- Le bloc gris de B34 à C37, que j'appelais « le comptoir », est la cuisinière et le frigo. À leur gauche, une table avec les bacs de recyclage dessous ; à droite du frigo, la poubelle, puis une porte, fermée sur la photo (B38).
- La « table » de E37 et F37 est un îlot en bois sur pieds, avec une tablette basse : le contact de F37 est un pied ou cette tablette, pas une chaise.
- Le long du mur de droite, une étagère métallique sur pieds (E39), puis un comptoir en inox sur pieds (F39 à H39). Le capteur de distance voit entre leurs pieds : c'est ce qui explique la surface vue 25 cm plus loin que le bord du plan au premier tour, et sans doute une part des notes médiocres du filtre dans cette pièce. À droite de l'îlot, le sol est libre le long de ce comptoir ; le robot n'y est pas allé.
- Sur la photo le robot est contre le pied de l'étagère, près de la porte : c'est sa position de départ (C39), et ce pied est « l'objet à 5 cm de sa coque ». La photo daterait donc du moment où il a été posé ; non vérifié auprès de l'utilisateur.
- Le chat est dans la pièce, à un mètre et demi du robot. C'est une cause possible de la rotation trop rapide du premier tour (robot poussé), sans preuve.
- Ce que le robot a vu à 27 cm devant lui en G36 est hors de la photo : toujours pas identifié.

La photo ne montre pas d'assez près la batterie du cerveau ni ses fils : une photo de près est redemandée.

## 49. Cinq minutes robot immobile : un accroc du Wi-Fi suffit à suspendre les lectures ; et la version 11 du firmware, écrite sans être installée (2026-11-14, 15 h 20 à 15 h 30)

Message de l'utilisateur : « peut etre un buffer de data pour rien perdre quand wifi drop ? relance la carto de la salle ou tu es, trouve de bon repere et va partout ou tu peux (autour de la table en 5 par exemple) puis va a l'etape de la marche a franchir plusierus fois et apprendre, ensuite retour face a la base, attend la photo et continue ». Rien n'a roulé pendant cette section : j'attends la photo des branchements, comme il le demande.

### Cinq minutes robot immobile, avec le ping du PC

`mesures/repos_f36_5min_20261114_152221_*` et `mesures/repos_f36_5min_20261114_ping.csv`. Mode passif, sans la touche `e`. 5 503 lectures en 4,7 min ; 560 pings, dont 3 sans réponse ; 9 ms d'aller-retour en médiane.

| Trou dans les lectures | Durée | Pings du PC au même moment |
|---|---|---|
| 15 h 23 min 56,6 | 0,8 s | un ping perdu à 56,3 s, puis 124 et 119 ms |
| 15 h 24 min 12,0 | 2,4 s | 68 ms, 125 ms, un ping perdu à 13,3 s, puis 192 et 107 ms |
| 15 h 24 min 18,6 | 0,5 s | 210 ms |
| 15 h 25 min 41,1 | 1,4 s | 64, 51 et 51 ms |

Chaque trou tombe sur un ping perdu ou lent ; il n'y a pas de trou ailleurs. Un accroc du Wi-Fi d'un ou deux dixièmes de seconde devient une à deux secondes sans lecture. Le troisième ping perdu (15 h 26 min 12) n'a pas fait de trou.

**Le mécanisme**, lu dans la bibliothèque installée sur ce PC (cœur ESP32 3.3.7, `NetworkClient::write`) : quand le client ne peut pas recevoir tout de suite, une écriture attend jusqu'à une seconde, et recommence jusqu'à dix fois. Le firmware écrit chaque ligne de la console et du journal au client TCP depuis sa boucle principale (`TeeOut::write`) : la boucle attend avec elle, et avec elle la lecture des capteurs, le réflexe du pare-chocs et la surveillance des mouvements. **Ceci remplace le « lu dans le code, pas démontré » du § 48** : l'essai le montre, robot immobile, sans la touche `e` ni rien d'autre en jeu.

Restent sans explication : le redémarrage du robot à 15 h 05 min 46 et la rotation trop rapide du premier tour (§ 48). Autre constat, non étudié : 19 demandes d'état du PC sur 505 ont attendu leur réponse 2,0 à 2,5 s, à des moments sans trou.

### Version 11 du firmware : écrite et compilée, pas installée

L'idée du tampon est de l'utilisateur. Une seule retouche, dans `roomba694_wifi.ino` et `web.ino` :

- ce que le cerveau écrit pour le client TCP va dans un tampon en mémoire de 24 ko (environ 8 s de journal) ; `tcpTick()` envoie à chaque passage ce que la liaison accepte tout de suite (`send` avec `MSG_DONTWAIT`) et n'attend jamais ;
- si le tampon est plein, des lignes entières sont abandonnées et comptées : aucune ligne du journal n'arrive coupée ou collée à la suivante ;
- `/api/state` gagne `console` : `tampon` (octets en attente), `max`, `perdus` ; la version affichée devient « v11 » ;
- rien d'autre ne change : mêmes sécurités, mêmes délais (1,5 s pour une avance, 2,5 s pour un tour).

Compilée sans avertissement : 1 141 818 octets, 87 % de la place. **La carte porte toujours la v10** : l'installation attend l'accord de l'utilisateur, puis un essai robot immobile (cinq minutes avec le ping : plus aucun trou attendu, même quand un ping se perd).

### Ce qui est prêt pour la suite demandée

- **Second passage dans la cuisine**, pour créer des repères : repasser par les huit tours du § 48 et faire le tour de l'îlot par la droite, le long du comptoir en inox. Le plan donne un chemin pour chaque étape (`plan_lidar/cuisine_chemin_passage2.png`) ; la bande à droite de l'îlot y fait 60 cm. Destinations, en pixels : (937, 180), (975, 91), (984, 122), (984, 150), (984, 176), (1005, 70), (937, 81), (925, 106), (930, 129), (937, 142).
- **Vers la marche** : le passage entre la table aux bacs de recyclage et le mur ne fait que 49 cm sur le plan, de D31 à D34 (le planificateur n'y passe que grâce au trait vert de l'utilisateur) ; puis une porte en C29, où doit être la marche (`plan_lidar/cuisine_vers_marche.png`). À mesurer au capteur de distance avant de s'y engager.
- **La marche** : sa hauteur et son sens ne sont pas connus. En mode Safe, une roue qui se soulève fait retomber le robot en mode passif : il faudra l'accord de l'utilisateur pour le remettre en mode Safe à chaque fois pendant cette leçon.

## 50. Second passage dans la cuisine : arrêté au bout de trente secondes par les trous des lectures (2026-11-14, 15 h 31 à 15 h 40)

Réponses de l'utilisateur : deux photos (les branchements de près ; la cuisine vue de l'autre bout, avec le robot), puis « Oui tu enchaîne seul » à ma question sur la marche : il m'autorise, pour la leçon de la marche, à remettre moi-même le robot en mode Safe quand il retombe en mode passif. Il n'a pas répondu à la question sur l'installation de la v11 ; je ne l'ai donc pas installée.

### Ce que montrent les photos (non gardées)

- **Branchements** : carte du cerveau allumée, câble USB enfoncé, batterie portable à deux voyants sur quatre. Les trois fils vers le robot sortent du cadre : leur prise n'est pas vérifiée. La batterie portable n'est pas fixée et son coin arrive au bord du bouton CLEAN. Vérifié dans les enregistrements du jour (`btn` de `/api/state` deux fois par seconde, et réponses à la touche `e`) : aucun appui sur un bouton l'après-midi, y compris avant le redémarrage du robot de 15 h 05 ; ce n'est donc pas un appui long sur CLEAN qui l'a fait redémarrer. Demandé à l'utilisateur : la fixer au ruban, loin du bouton, avant la marche (si elle glisse et débranche le cerveau, le robot garde son dernier ordre de roues).
- **La pièce vue du haut du plan vers le bas** : le robot est entre l'îlot et des armoires blanches avec évier (le bloc de E34 à G35, plein jusqu'au sol), à une cinquantaine de centimètres d'une porte de balcon fermée, avec un seuil. C'est elle que le robot avait vue à 27 cm en G36 (§ 48). La position de fin du § 48 était donc juste à une dizaine de centimètres près, plutôt trop haute sur le plan, comme le laissaient attendre les 196 mm non comptés. Une boîte en carton est au sol à gauche de cette porte (H37). La première photo datait bien du moment où le robot avait été posé en C39.

### Le passage

Enregistrement `mesures/exploration22_20261114_153302_*`, sans la touche `e`, firmware v10, vitesse demandée 75 mm/s. Destinations : celles du § 49, sans (984, 176) à cause de la boîte en carton.

- 15 h 33 min 40 : premier tour sur place, complet malgré un trou de 1,5 s. Filtre : G36, pixel (933, 162), note 0,83, correction (−32, +51) mm et −1,7°.
- Avance de 33 cm vers (937, 180), faite.
- 15 h 33 min 58 : second tour arrêté par le cerveau avant d'avoir tourné, « le robot ne répond plus » : 4,9 s sans lecture.

Dans les quatre premières minutes de l'enregistrement : 24 trous de plus de 250 ms, dont 18 de plus d'une seconde ; 15 % du temps sans lecture (par minute : 4, 4, 11, 4, 1). Je n'ai pas relancé : avec la v10 et une liaison dans cet état, le robot roulerait sans surveillance une bonne partie du temps. La suite attend l'accord de l'utilisateur pour installer la v11.

## 51. Firmware v11 installé et vérifié ; la cuisine refaite deux fois, ses repères ; le passage étroit franchi au centrage automatique ; la marche trouvée et mesurée (2026-11-14, 15 h 39 à 16 h 13)

Accords de l'utilisateur : « Vas y installe la nouvelle version », puis, à ma remarque sur le Wi-Fi : « cest car il capte moins bien ou il est ca ira mieux des le couloir le pense, continue ». Enregistrements : `mesures/repos_g36_v11_*`, `mesures/exploration23_20261114_154855_*` (passages `a` et `b`, sorties `_passage1.txt` à `_passage6.txt`) et `mesures/exploration23_20261114_ping.csv` (un ping du PC deux fois par seconde pendant toute la séance). Cartes hors dépôt : `plan_lidar/carte_grille_20261114_marche*.png`.

### Installation de la v11

Par `curl -F firmware=@… http://192.168.18.25/update`, robot endormi. Quatre envois : les trois premiers coupés par la liaison (458, 131 et 393 ko partis sur 1 142), le cerveau gardant chaque fois la v10 intacte ; le quatrième réussi à 15 h 40 min 59, en 15,8 s. Au redémarrage : « v11 Nov 14 2026 15:25:48 », raison « redémarrage logiciel (mise à jour) », `console` présent dans `/api/state`.

Au même moment, pings envoyés en parallèle depuis le PC : 25 sur 25 vers la box (3 ms en moyenne), 20 sur 25 vers le cerveau (152 ms). **C'est entre la box et le cerveau que la liaison décroche**, pas du côté du PC. L'utilisateur le dit autrement : le robot capte moins bien là où il est.

### Vérification robot immobile

Mode Safe, 1,9 min (début d'`exploration23`) : 2 153 lectures, **aucun trou de plus de 250 ms** (le plus long écart 0,16 s) alors que 16 pings sur 233 sont restés sans réponse ; les lignes arrivent au PC avec jusqu'à 2,2 s de retard, aucune n'est perdue (`perdus` 0, tampon rempli jusqu'à 2 316 octets), aucune n'est mal formée, l'horloge du cerveau y est toujours croissante. Sur les quinze minutes de route qui ont suivi : 17 966 lectures, aucun trou, 24 pings perdus sur 1 799, 3,3 s de retard au pire, tampon rempli jusqu'à 6 384 octets sur 24 576.

Un essai immobile d'avant (`repos_g36_v11`, 15 h 44) n'a rien mesuré : le robot avait cessé de répondre 110 s après son réveil, sans texte de redémarrage cette fois ; réveillé de nouveau à 15 h 48, il a répondu. Non expliqué, comme le redémarrage de 15 h 05.

### La cuisine, deuxième et troisième passages

`explorer3.py` par destinations (`--cibles-seules`), 75 mm/s demandés, mêmes endroits que le § 48 plus le côté droit de l'îlot.

- **Passage `a`** (15 h 51 à 15 h 55) : 10 tours sur place en 4,7 min ; notes du filtre de 0,69 à 0,96. Un contact du pare-chocs droit en remontant à gauche de l'îlot : son pied nord-ouest, pixel (946, 122), E36 ; roues arrêtées par le réflexe, obstacle contourné. Ce pied est ajouté à `plan_lidar/obstacles.json`. Le côté droit de l'îlot (E38, F38) est parcouru sans contact.
- **Passage `b`** (15 h 56 à 16 h 01) : 11 tours, 9,0 m en 5,0 min. Un contact du pare-chocs droit en quittant C38, au pixel (993, 66) : sans doute la poubelle.

**Repères** (`reperes.py` sur les cinq fichiers de tours des § 48, 50 et 51). Avec les 30 tours : 12 gardés, corrections de 75 mm en médiane et jusqu'à 312 mm, les tours de gauche de l'îlot rejetés. En écartant cinq tours faits avec la v10 (`e21a3`, `e21a4`, `e21b0`, `e21b1`, `e22a0` : ceux d'après les 196 mm non comptés du § 48, et celui du § 50) : **16 repères gardés sur 25 tours, corrections de 35 mm en médiane, neuf sur dix sous 75 mm**, la plus grande 138 mm. Les endroits qui n'ont que deux visites (G36, E38, F38, C38) s'accordent à 21 à 55 mm mais ne sont pas gardés (il faut deux voisins). Ajoutés à `plan_lidar/reperes_tours.json` : 97 repères (l'ancien fichier est gardé sous `reperes_tours_20261114_0859.json`).

### Le passage étroit : premier essai réel de `eventail=` et de `centre=`

- `eventail=180` à l'entrée, pixel (902,6 ; 88,6) : parois à 237 mm à gauche et 460 mm à droite du centre du robot ; les deux coins de l'entrée à 517 et 552 mm, soit **49 cm d'ouverture**, comme sur le plan.
- `centre=180,900,300,60` : 0,88 m en 4 arrêts et 73 s, sans contact. Largeurs lues : 491, 754, 414 et 419 mm. À un arrêt le capteur a lu 104 mm à droite du centre du robot, moins que son rayon : quelque chose passait au-dessus de sa coque, à la hauteur du capteur (le bord de la table aux bacs).
- `centre=180,600,200,50` : 0,60 m en 4 arrêts et 67 s, sans contact. Une ouverture à gauche (861 mm de vide) vers le pixel (845, 104), puis 459 et 488 mm de large. Arrivée en D32, pixel (824,0 ; 89,2).

**Le centrage automatique du § 47 marche sur le robot** : 1,48 m en 8 arrêts et 140 s, sans aucun contact, dans un passage de 42 à 49 cm (4 à 7 cm de chaque côté). Il reste lent (1 cm par seconde). Sa décision de biais n'a servi qu'une fois (`CAP_MURS` : 2,2° d'écart avec l'estime sur 2 mesures).

### La porte et la marche

- `eventail=172` en C30, pixel (770,0 ; 73,4) : les deux montants de la porte, **75 cm d'ouverture** environ, la trouée vers le cap 193°.
- Robot mis dans l'axe de la porte, pixel (768,0 ; 77,2), cap 179°, puis avances de 5 cm à 50 mm/s en lisant les capteurs de vide et l'accéléromètre :

| Chemin fait depuis (768, 77) | Capteurs de vide de devant | Capteurs de vide de côté | Inclinaison |
|---|---|---|---|
| 0 à 38 cm | 2 490 à 2 540 | 2 480 à 2 550 | à plat |
| 44 cm | montent à 3 316 et 2 873 | inchangés | à plat |
| 49 cm | creux à 1 180 et 1 132, puis 2 470 | inchangés | à plat |
| 55 cm | 2 720 et 2 600 | montent à 3 673 et 3 372 | **nez levé de 7 à 8°** |

La roulette avant est montée sur la marche à 50 mm/s sans que le pare-chocs soit enfoncé, sans roue levée, le mode Safe tenu, les moteurs à 450 mA au plus. **La marche monte quand on va de la cuisine vers la pièce centrale ; elle fait environ 17 mm** (13 cm entre la roulette et l'axe des roues, inclinaison de 7,6°) ; son bord est vers le pixel 733 à 737 en travers, c'est-à-dire **dans C28, 9 cm à gauche de la limite C28/C29** que donnait l'utilisateur, à la précision de l'estime près (2,6 m et beaucoup de rotations depuis le dernier repère). Les capteurs de vide la voient venir 10 cm avant : c'est un signal utilisable pour la franchir.
- Recul de 108 mm pour remettre le robot à plat : il a pivoté de 6° en redescendant.

**La marche n'est pas franchie.** J'avais demandé à l'utilisateur de fixer d'abord la batterie portable au ruban (si elle glisse et débranche le cerveau, le robot garde son dernier ordre de roues) ; il n'a pas encore répondu à cette question, posée trois fois.

**Bilan de la liaison sur tout l'enregistrement** (27 min, v11) : 32 221 lectures, aucun trou de plus de 250 ms (0,16 s au plus), 87 pings sans réponse sur 3 243, jusqu'à 3,3 s de retard d'arrivée des lignes, aucune ligne perdue.

**État à la fin** : `s` puis `x` à 16 h 16 ; robot endormi, à plat dans l'encadrement de la porte entre la cuisine et la pièce centrale, pixel (744 ; 77), C29, tourné vers 186° ; hors de sa base, il ne charge pas ; batterie 1 784 mAh. Cerveau allumé (v11). Capteur de distance arrêté. Non fait : la marche, le retour face à la base.

## 52. Le seuil de la cuisine franchi trois fois, et retour face à la base sans un contact (2026-11-14, 16 h 18 à 16 h 37)

Accord de l'utilisateur, à ma question sur la batterie portable : « Rentre à la base franchi la marche tout est bon ». Enregistrement : `mesures/exploration24_20261114_161758_*` (passages `a` et `b`, sorties `_passage1.txt` à `_passage10.txt`, `_balise0.txt`). Carte hors dépôt : `plan_lidar/carte_grille_20261114_retour*.png`. Firmware v11 : 22 041 lectures en 18,4 min, aucun trou de plus de 250 ms.

### Le seuil : trois franchissements

| | Sens | Vitesse demandée | Ce qui s'est passé |
|---|---|---|---|
| 1 | vers la pièce centrale | 60 mm/s | 38 cm d'avance en 12 s, sans alarme : ni pare-chocs, ni roue levée, mode Safe tenu, moteurs à 490 mA au plus. Le robot lève le nez de 7 à 8°, puis se remet à plat |
| 2 | vers la cuisine | 60 mm/s | aucune alarme non plus, mais le robot est resté le nez baissé de 5°, moteurs à 700 mA, sur les 39 cm demandés puis sur 16 cm de plus : son arrière était posé sur le seuil et ses roues patinaient. Un pivot sur place l'a dégagé |
| 3 | vers la pièce centrale | 100 mm/s | 48 cm d'avance, sans alarme, moteurs à 375 mA |

**Ce que c'est.** Pas un changement de niveau franc, mais un **seuil en relief sous la porte**, d'environ 17 mm, avec le sol de la cuisine un peu plus bas : en allant vers la pièce centrale les roues sont déjà sur le sol haut quand l'arrière passe, en allant vers la cuisine les roues retombent sur le sol bas et l'arrière se pose sur le seuil. C'est ce sens-là qui demande d'« insister », comme le disait l'utilisateur.

**Où il est.** Les capteurs de vide du robot le voient passer comme une bande claire (3 000 à 3 700) : d'après eux il est à 141 mm de l'endroit où le robot attendait, les capteurs de devant étant à 154 mm du centre du robot et ceux de côté à 81 mm (déduit des passages 1 et 2). **Correction du § 51** : j'y plaçais le seuil « dans C28, à 9 cm de la limite C28/C29 ». C'était l'erreur de mon estime : le tour sur place fait ensuite en C28, calé sur le repère de la veille, a placé le robot 35 cm plus haut sur le plan que je ne le croyais, et les quatre tours suivants ont confirmé ce calage (corrections de 2 à 11 cm seulement). Le seuil est donc bien sous la porte, à la limite de C28 et C29, comme l'utilisateur l'avait dit ; les positions du § 51 dans le passage étroit et devant la porte sont à lire avec cette réserve (une trentaine de centimètres, surtout de travers).

**Le patinage du passage 2 n'a pas été vu comme tel** : l'estime a compté 546 mm vers la cuisine alors que le robot n'en a fait qu'environ 350 (les capteurs de vide ont revu le seuil pendant le pivot). Le retrait du patinage de `carto.py` ne joue que sur une roue qui tourne plus que le gyroscope ne le dit, pas sur deux roues qui patinent ensemble.

**Non essayé** : le sens difficile à plus de 60 mm/s, ou de biais.

### Le retour, de C28 à D16

| Tronçon | Heures | Durée | Contacts | Remarque |
|---|---|---|---|---|
| C28 → G26 → H23 → J20 (`explorer3.py`, passage `a`, 100 mm/s demandés, `--voies-fortes 3`) | 16 h 22 min 30 à 16 h 25 | 2,3 min | 0 | 5 tours sur place, tous calés sur leurs repères (3 contacts sur ce tronçon le matin) |
| Couloir J20 → J12, `centre=180,3900,400,100` | 16 h 25 min 15 à 16 h 29 | 3,8 min | 0 | 12 arrêts ; 5,3 min à la main le matin |
| Porte H12 vers le nord (`passage.py` : deux éventails, un décalage, dix regards, 35 cm d'approche, un éventail, passage au cap 100°) | 16 h 29 à 16 h 33 min 30 | 4,5 min | 0 | 3,3 min le matin |
| G12 → E12 → D15 → D16 (passage `b`) | 16 h 33 min 45 à 16 h 35 min 30 | 1,8 min | 0 | 4 tours, calés sur 10 et 4 repères |

**13 minutes de C28 à D16, aucun contact** (le matin : 15 minutes et 4 contacts sur le même chemin). Sur tout l'après-midi depuis l'installation de la v11 : 37 m, 30 tours sur place, 2 contacts légers, tous deux dans la cuisine.

**Devant la porte H12, l'estime était fausse de 28 à 32 cm** (le robot plus à droite sur le plan que son calcul) après le couloir mené par `centre=` : 318 mm de saut au premier tour calé en G12. Le matin, 14 cm au même endroit après le couloir mené à la main. Vu de la même façon les deux fois : une paroi droit devant à 67 cm, l'ouverture sur la gauche. Cause non cherchée ; `centre=` fait un tour complet de rotations à chaque arrêt (douze ici), et l'audit a montré que l'échelle du gyroscope n'est pas la même dans les deux sens (note I).

**Arrivée** (`balise_base.py`) : la base est vue par les récepteurs de devant autour du cap 75° du plan ; son axe est à 44 mm à droite du centre du robot, le « couloir » rouge et vert fait 66 mm de large à cet endroit ; 67 cm de vide au capteur de distance dans cette direction.

**Non fait** : l'accostage (l'ordre « rentre à la base » du robot demande l'accord de l'utilisateur à chaque fois ; demandé).

**État à la fin** : `s` puis `x` à 16 h 36 min 40 ; robot endormi en D16, pixel (401 ; 84), tourné vers 70°, à un mètre de sa base, pas posé dessus : il ne charge pas ; batterie 1 725 mAh sur 2 068. Cerveau allumé (v11). Capteur de distance arrêté.

## 53. Accostage : non lancé, l'utilisateur a posé le robot sur sa base ; ce qu'il y a devant la base (2026-11-14, 16 h 42 à 16 h 46)

Accord de l'utilisateur pour l'accostage : « Oui, accoste-le ». Enregistrement : `mesures/exploration25_20261114_164147_*`. **L'ordre `h` n'a pas été envoyé.**

Avant de le lancer, regards au capteur de distance depuis D16, pixel (401 ; 84), caps du plan d'après l'estime :

| Cap | Distance au centre du robot |
|---|---|
| 49° à 71° | 69 cm |
| 80° à 100° | **29 à 32 cm** |
| 111° à 121° | 88 cm |

Le tour sur place d'arrivée, à 16 h 35, donnait la même chose (268 à 279 mm de 80° à 98°) : ce n'est donc pas quelqu'un qui passait. Les récepteurs de devant voient la base autour du cap 75° ; la surface à 69 cm de ce côté-là est sans doute la base elle-même, ce qui mettrait le robot à une cinquantaine de centimètres de sa place sur la base, et non à un mètre comme le dit le plan (non tranché). **Un objet d'une dizaine de centimètres de large se tient donc à 30 cm devant le robot, à peine à gauche de l'axe de la base, à 40 cm environ devant elle.** C'est là que le pare-chocs gauche touche à chaque accostage (les 13 et 14, § 40 et § 46 ; relevé par l'audit, note I). Je l'ai écrit à l'utilisateur en lui demandant de l'enlever.

À 16 h 43 min 07, pendant que j'analysais ces regards, les deux roues se sont levées : l'utilisateur a porté le robot (« je l<ai pos'e »). À 16 h 43 min 12 le pare-chocs est enfoncé des deux côtés et le courant remonte : le robot est sur sa base. Le cerveau a redémarré à ce moment-là (« mise sous tension » : son alimentation a été coupée un instant pendant le geste ; la batterie portable n'est pas fixée) ; il est reparti en v11.

**État à la fin** : robot sur sa base, en charge (16,6 V, 1,29 A, état de charge 2, 1 768 mAh sur 2 068 à 16 h 45) ; `x` envoyé à 16 h 45 min 54 ; cerveau allumé (v11). L'objet devant la base n'est pas identifié et, à ma connaissance, pas enlevé.

## 54. Revue de la localisation et du code par une session à part ; firmware v12 installé par elle (2026-11-14, 17 h 39 à 18 h 37)

Rien de ce qui suit n'a été fait par la session de navigation, qui tient ce journal : je rapporte le travail d'une session à part, d'après son compte rendu et ses commits, en disant ce que j'ai vérifié moi-même. **Rien n'a roulé ; je n'ai rien envoyé au cerveau.**

**La demande.** L'utilisateur : « propose moi une fork en mythos 5.2 pour review les possibilite de localisation que je pourrais manquer et les vulnerabilites dans mon code ». La session a été lancée avec une consigne qui lui interdisait toute requête au cerveau et toute modification d'un fichier existant. Il a levé la première limite peu après (« dit lui dans la nouvelle session quil peut parler a la carte et me demander de le faire rouler un peu si necessaireet faire les tes quil veut »). D'après le compte rendu de cette session, il lui a ensuite demandé les corrections (« tu peux faire les corrections suite à tes findings ») et a accepté l'installation (« Oui »).

**Ce qu'elle a rendu.**

- `notes/J_revue_localisation.md` (commits f2ec0c3, 1d33f5b, f53a934) et ses scripts `data_analysis/rv_…py` : ce que le projet pourrait manquer pour se localiser. En tête : le cap du cerveau gardé dans un nombre trop court (corrigé par la v12, ci-dessous) ; le courant de la batterie, qui a signalé sans fausse alerte les deux patinages connus sur 195 m d'avances des 13 et 14 ; le capteur de distance, qui s'accorde avec les roues à 0,2 % sur 29 m d'avances vers un mur de face et que personne ne lit pendant les avances ; l'échelle du plan, juste à 0,5 % près (0,995 ± 0,005 sur 70 trajets), donc hors de cause dans les 30 cm du couloir (§ 52).
- Une revue de sécurité du code. Ce dépôt est public : son détail reste sur le PC de l'utilisateur, hors du dépôt, tant qu'il n'en a pas décidé autrement.
- Onze lectures de l'état du cerveau le 14 à 17 h 43, robot endormi sur sa base, sans rien changer à ce que la carte garde en mémoire (en-tête de la note J).

**Firmware v12** (commit 232dee5). Sept retouches indépendantes ; d'après son en-tête, aucune ne change la conduite du robot ni une sécurité existante. J'ai relu la différence entre la v11 et la v12 : elle contient ces sept retouches et rien d'autre dans le firmware, à part le numéro de version à trois endroits (dont la ligne d'information, qui disait encore « v5 »).

| | Retouche | Où |
|---|---|---|
| 1 | Le cap du gyroscope est cumulé dans un `double` propre à la tâche du gyroscope ; `imu.yawDeg` n'en est plus que la copie. Jusqu'à la v11 le cumul se faisait dans un `float` jamais remis à zéro : au-delà de 16 384° cumulés (43 tours sur place) les rotations lentes étaient mal comptées, au-delà de 32 768° plus du tout sous 0,1 °/s. 44 562° atteints le 13 après-midi (note J § 3.1 : lu dans le code, simulé) | `roomba694_wifi.ino`, `imuTask` |
| 2 | Au démarrage de la carte l'ordre d'arrêt des roues part trois fois, à 20 ms d'intervalle, au lieu d'une : si la carte s'était éteinte au milieu d'un ordre de roues, le robot prenait le début de l'unique arrêt pour la fin de cet ordre | `roomba694_wifi.ino`, `setup` |
| 3 | `/api/mouv` répond 400 à une valeur `av`, `rot` ou `cap` qui n'est pas un nombre fini : « nan » passait les contrôles de distance | `mouv.ino` |
| 4 | La page `/wifi` affiche ce qui vient de la carte comme du texte, jamais comme du HTML | `pages.h` |
| 5 | `/api/essai` n'est plus compilé (`ESSAI_LIAISON` à 0) ; aucun outil ne s'en servait | `roomba694_wifi.ino`, `web.ino` |
| 6 | La butée du servo ne peut plus dépasser `RADAR_BUTEE_MAX`, 30°, la valeur fixée par l'utilisateur le 9 : `/api/radar?butee=` n'accepte plus que 10 à 30, la page ne propose plus que 15, 20 et 30, et une mémoire vide redonne 30° et non 80° | `radar.ino`, `web.ino`, `pages.h` |
| 7 | La touche `n` (test des trois fils) est refusée pendant que les roues tournent | `roomba694_wifi.ino` |

Dans le même commit, hors firmware : `outils/monitor_wifi.py` masque le nom du réseau de la maison dans les lignes de console, comme le fait déjà `enregistreur.py` ; un chemin du PC est retiré de `journal_tests.md`. Hors dépôt, d'après son compte rendu : un fichier `secrets.h` a été créé sur le PC de l'utilisateur, de sorte que le point d'accès « Roomba694 » de la carte et ArduinoOTA ne prennent plus le mot de passe par défaut écrit dans ce dépôt (pas essayé depuis un téléphone).

**Installation et vérification**, d'après son compte rendu :

| Heure | |
|---|---|
| 17 h 58 | Compilation : 1 140 602 octets, 87 % de la place |
| 18 h 34 min 54 | État avant l'envoi : v11, roues à l'arrêt, robot muet sur sa base |
| 18 h 35 min 04 | `curl -F firmware=@…/build/roomba694_v12.bin http://192.168.18.25/update` : réussi au premier envoi, 1 140 752 octets en 9,9 s, « Mise à jour réussie » |
| 18 h 35 min 15 | Lectures seules, robot immobile : « v12 Nov 14 2026 17:58:04 » ; raison du redémarrage « redémarrage logiciel (mise à jour) » ; gyroscope présent et calibré (zéro à −0,12 °/s, 310 retouches du zéro en 3 s, cap stable) ; butée 30° ; arrêt automatique actif, seuil 30 cm ; `/api/essai` en 404 ; `/api/mouv?av=nan` en 400 sans toucher à l'état du dernier mouvement ; pages `/` et `/wifi` servies |

Aucune touche envoyée, console du port 23 non ouverte, rien n'a roulé.

**Ce que j'ai vérifié moi-même, sans le cerveau** : les quatre commits sont sur la branche ; la différence du firmware (ci-dessus) ; `build/roomba694_v12.bin` fait bien 1 140 752 octets ; `secrets.h` et `build/` sont ignorés par git, seul `secrets.example.h` est suivi ; `explorer3.py` et la carte vivante lisent le numéro de version dans son premier mot (« v12 » donne 12), et `pilote.py` ne regarde pas la version mais la présence de `/api/mouv`. **Ce que je n'ai pas vérifié** : la version en service sur la carte et les lectures de 18 h 35. La session de revue m'a demandé de ne rien envoyer au cerveau pendant qu'elle prépare son essai.

**Non vérifié sur le robot** : aucune rotation ni avance n'a été faite avec la v12. Les retouches 1 et 2 touchent le cap et le démarrage : le premier tour sur place et la première avance sont à regarder de près (cap du gyroscope comparé aux roues), avant tout trajet.

**Ce que cela change pour la suite.**

- Le conseil de la note J pour les firmwares d'avant la v12, redémarrer le cerveau au début de chaque séance, n'a plus lieu d'être.
- Le cerveau a redémarré à 18 h 35 : sa position et son cap sont revenus à zéro.
- Retour à la v11 si besoin : `curl -F firmware=@roomba694_recherche/code/roomba694_wifi/build/roomba694_v11.bin http://192.168.18.25/update`.
- `pilote.get` lèvera une erreur HTTP 400 si un outil envoyait un jour `av`, `rot` ou `cap` non fini ; aucun mouvement dans ce cas.
- Les scripts de l'audit qui trient les enregistrements par firmware (`y_cap_gyro_tours.py`, `z_estime_boucles.py`, `za_rejeu_cap.py`, `zb_carte_coherente.py`, `zf_inclinaison_gyro.py`) ne retiennent que « v9 » et « v10 » (vu dans leur code) : les enregistrements faits en v11 et en v12 en sont exclus tant que ce tri n'est pas élargi.
- À faire dans les outils du PC, d'après la note J (§ 6) : l'arrêt d'une avance sur le courant de la batterie, avant de refaire le seuil vers la cuisine ; le capteur de distance comme règle pendant les avances ; le cap par la corde entre deux tours, une fois la carte des repères rendue cohérente.
- Annoncé par la session de revue : un essai de séries de pivots sur place, trois minutes, robot face à un mur, avec l'accord de l'utilisateur, pour mesurer ce que les petits pivots du centrage font à la position (les 30 cm du couloir, § 52). Pas encore fait à l'heure où j'écris.

**État à la fin** (18 h 45) : robot endormi sur sa base ; cerveau allumé, en v12 d'après la session de revue ; l'objet devant la base et la batterie portable non fixée restent à régler (§ 53).

**Complément, 18 h 46 min 36 : la version lue par moi.** La session de revue m'a écrit que la voie était libre jusqu'à son essai des pivots, pas encore lancé. Une seule lecture de `/api/state`, rien d'autre envoyé : « v12 Nov 14 2026 17:58:04 » ; dernier redémarrage « redémarrage logiciel (mise à jour) » ; carte en marche depuis 690 s, donc depuis 18 h 35 min 06 ; roues à l'arrêt ; robot sans réponse (il dort sur sa base) ; gyroscope présent, pas de calibration en cours, cap 0,0°, vitesse 0,0 °/s, zéro à −0,127 °/s, 68 669 retouches du zéro à l'arrêt en 690 s (le gyroscope est lu 100 fois par seconde) ; position, tours et mouvements à zéro ; arrêt automatique du capteur de distance actif, seuil 30 cm ; tampon de la console vide, aucune ligne perdue ; aucun appareil sur le point d'accès de la carte. **La version en service est bien la v12.** Restent non vérifiés par moi : les réponses 404 et 400 relevées par la session de revue, et tout mouvement.

## 55. Veille d'une séance sous firmware v13 : ce que la session de revue a préparé pour le lendemain, et mes outils mis en état (2026-11-14, 22 h 50 à 23 h 05, sans le robot)

**La demande.** Je ne l'ai pas reçue moi-même : la session de revue me l'a rapportée le 14 vers 22 h 50, et elle figure dans sa note `notes/L_retro_ingenierie_robot.md`. Les mots de l'utilisateur, d'après elle : « Capteurs seuls pour le moment / Prépare tout pour que demain j'ai juste à brancher / L'autre session pilotera et tu analysera en live pour le reverse engenNERING et la précision possible d'amélioration d'utilisation optimale des capteurs ». « L'autre session », c'est celle-ci : je piloterai, elle analysera en direct.

**Rien n'a roulé et aucun ordre n'est parti vers le robot.** Une seule demande de `/api/state`, à 22 h 58, restée sans réponse.

**État à 22 h 50.**

- Le cerveau ne répond plus sur le réseau depuis 20 h 40 au moins, d'après la session de revue ; ma dernière lecture réussie est celle de 18 h 46 (§ 54). Cause non cherchée : sa batterie portable est la première chose à regarder.
- La carte porte donc toujours la v12. La v13 est écrite et compilée par la session de revue (commits a85394e, 76c5596, 36a2122), pas installée.
- Le robot est sur sa base depuis 16 h 43 (§ 53), à ma connaissance.

**Ce que la session de revue a mis en place** (ses outils, dans `data_analysis/` ; je n'y ai pas touché).

| Quoi | Ce que c'est |
|---|---|
| `rv_matin.py`, « le veilleur » | lancé détaché le 14 à 22 h 45 pour vingt heures au plus (processus vu vivant à 22 h 52). Dès que le cerveau répond : il installe la v13 par `/update` (accord de l'utilisateur rapporté par elle : « oui » ; seulement sur un cerveau allumé depuis moins de dix minutes, et si rien ne roule), écoute le robot huit minutes avec les touches `w`, `w`, `s`, `b`, puis `x` (aucun ordre de roues), et lit par la sonde les 256 numéros de capteurs, en lecture seule. Il tient à jour `mesures/matin_dernier.txt` ; pour l'arrêter : créer `mesures/matin_STOP` |
| `rv_direct.py`, l'analyse en direct | lit l'enregistrement d'`enregistreur.py` à mesure qu'il s'écrit (le `_capteurs.csv` le plus récent et sa console) et, avec la v13, `/api/texte`. N'envoie rien au robot, n'ouvre pas la console |
| `rv_essai_pivots.py` | l'essai des pivots annoncé au § 54 n'a pas eu lieu ; elle me le confie si l'utilisateur veut le faire (rotations seules, lui à côté du robot) |

**Ce qui est convenu entre les deux sessions.**

1. Avant de parler au cerveau ou de faire rouler : lire la première ligne de `mesures/matin_dernier.txt`. « en cours » : attendre (dix minutes au plus après le branchement). « fini, bon » ou « fini, avec un échec » : la voie est libre. Fichier absent, ou « en attente » alors que le cerveau répond : le veilleur n'a pas tourné, le lui écrire.
2. Lui écrire quand je lance `enregistreur.py` (c'est ce message qui la réveille) et quand je l'arrête.
3. Elle ne m'enverra en direct que les alertes fortes : roues qui forcent, pivot où roues et gyroscope diffèrent de plus de 6°, texte inhabituel du robot, trou de lecture de plus d'une seconde en mouvement, mode Safe tombé en mouvement.
4. Ce qui l'aide, sans changer ma route : le capteur de distance fixe devant pendant les avances (c'est déjà le cas), de temps en temps une avance de 50 cm ou plus face à un mur, un seuil franchi signalé, et, si l'utilisateur accepte un « rentre à la base », un enregistrement avec `--e 1` pour lire le courant des brosses.

**La v13 relue dans le dépôt** (différence entre les commits 232dee5 et 36a2122 : `roomba694_wifi.ino`, `web.ino` et `secrets.example.h` sont les seuls fichiers du firmware changés ; `mouv.ino` et `radar.ino` ne le sont pas). Ce qui touche au pilotage :

| Changement | Conséquence pour mes outils |
|---|---|
| Lignes « texte du robot » de la console : une par ligne écrite par le robot, entière, précédée de l'heure de la carte ; avant, les 160 premiers caractères seulement | aucun de mes outils ne lit ces lignes ; l'enregistreur les range : voir le masquage ci-dessous |
| `/api/state` : champs `texte`, `bat` et `sonde` en plus ; `ver` commence par « v13 » | mes outils lisent les champs par leur nom et comparent la version à 10 : rien à changer |
| Routes nouvelles `/api/texte` et `/api/sonde` (celle-ci sous clé, compilée seulement avec le `secrets.h` de ce PC) | je ne m'en sers pas |
| Pendant une sonde, puis 3 s (60 s si la liaison est restée douteuse) : lecture périodique des capteurs, impulsion anti-veille et essai à 19200 bauds suspendus ; la sonde est refusée quand le robot bouge ; après ses actions autres que « lire », l'état du robot est tenu pour inconnu jusqu'à une lecture complète réussie | le veilleur ne fait que « lire », et avant mon départ ; `etat_cerveau.py` s'oppose au départ si `sonde.suspend` ou `sonde.douteux` est vrai |
| Ordres de roues, tour sur place, mouvements, arrêt automatique du capteur de distance | absents de la différence ; la lecture périodique n'y gagne que la ligne qui la suspend pendant une sonde |

J'ai lu la différence, pas les fichiers entiers, et je n'ai pas relu ligne à ligne le corps de la route de la sonde.

**Mes outils.**

- `outils/enregistreur.py` : avec la v13 la console donne en entier ce que le robot écrit à son réveil, et l'enregistreur l'aurait rangé tel quel dans `_console.txt`, un fichier qui part sur GitHub. Il masque maintenant, dans les lignes « texte du robot », les identifiants de l'appareil (suites de groupes hexadécimaux comme après « bootloader id: », la règle de `rv_ecoute_robot.py` ; longues suites hexadécimales d'un seul tenant ; adresses matérielles), et, dans toute ligne, le nom du réseau de la maison, qu'il apprend par `/api/state` avant d'ouvrir la console et ne garde qu'en mémoire. Rien d'autre ne change : mêmes fichiers, mêmes colonnes, mêmes touches.
- `outils/etat_cerveau.py` (nouveau, lecture seule) : à lancer avant de piloter. Il lit la première ligne du veilleur ; si elle dit « en cours », il n'interroge pas le cerveau et dit d'attendre. Sinon, une seule lecture de `/api/state` : l'état affiché sans le nom du réseau, puis ce qui s'oppose au pilotage (quelque chose roule, sonde en cours ou liaison douteuse, gyroscope absent ou en calibrage) et ce qu'il faut savoir (robot endormi, robot sur sa base, firmware d'avant la v12). Code de sortie : 0, 1, ou 2 quand le cerveau ne répond pas.

**Vérifié sur le PC, sans le robot.**

- L'enregistreur, lancé tel quel face à un faux cerveau « v13 » ouvert sur le PC (console et `/api/state`), en deux passages, avec et sans lecture périodique de l'état : 26 contrôles bons sur 26. Le nom du réseau est absent des trois fichiers, les trois sortes d'identifiants sont masquées, le reste du texte du robot est entier, une ligne ordinaire du cerveau faite de groupes de chiffres reste intacte, le journal des capteurs est complet, les champs nouveaux de l'état sont gardés, aucune touche n'est envoyée.
- `etat_cerveau.py` face au même genre de faux cerveau : 10 cas bons sur 10 (veilleur fini ; en cours ; « en cours » depuis deux heures ; en attente alors que le cerveau répond ; fichier absent ; liaison douteuse ; mouvement en cours ; roues en marche ; gyroscope en calibrage ; cerveau éteint), sans une seule demande au cerveau quand le veilleur travaille. Puis une fois pour de bon à 22 h 58 : veilleur « en attente », cerveau sans réponse, code 2.

**Non vérifié.**

- Tout ce qui touche à la carte et au robot : la v13 n'est pas installée, le veilleur n'a encore rien eu à faire, et aucun mouvement n'a été fait ni avec la v12 ni avec la v13.
- Le masquage n'a vu que de faux textes : je ne connais pas la fin du texte de réveil du robot, que la v12 coupait. **Relire les lignes « texte du robot » du premier enregistrement fait sous v13 avant de le pousser.**
- Le suivi par `rv_direct.py` d'un enregistrement en train de s'écrire (la note L le dit non vérifié).

**Ce que l'utilisateur aura à faire : un peu plus que brancher.** Brancher le cerveau, robot sur sa base. Puis, une dizaine de minutes plus tard, quand le veilleur a fini : tirer le robot de sa base à la main, de 70 cm, le nez vers la base (posé sur sa base alimentée il ignore les ordres de roues, § 32), et enlever l'objet qui se tient devant la base (§ 53).

**Programme de pilotage proposé, à lui faire confirmer.**

1. `etat_cerveau.py`, puis l'enregistreur (`--nom exploration26 --duree 3000 --csv`) et le message à la session de revue.
2. Réveil (`w`, `s`, attendre 3 s, `f`), capteur de distance fixe devant, une minute immobile : première vérification de la v13 robot réveillé (20 lignes par seconde, aucun trou, cap stable).
3. Premiers mouvements faits avec la v12 et la v13, rotations seules : `essai_mouv.py … rot=90 rot=-180 rot=90`, gyroscope contre roues.
4. L'essai des pivots de la session de revue (`rv_essai_pivots.py --go`, dix séries, trois minutes, rotations seules), s'il est d'accord : c'est lui qui dira si les petits pivots du centrage déplacent le robot (les 24 cm du couloir, note J § 2.3). Ce programme ferme la séance lui-même (`s`, `x`).
5. La boucle connue de 7,5 m devant la base (D16, E15, D12, E11, G12, C17, D16 ; § 42 à 44), avec les repères : des avances face à des murs et des pivots pour l'analyse en direct.
6. Fin : `5`, `s`, `x`. L'accostage par le robot (touche `h`, enregistrement avec `--e 1`) seulement s'il le demande et si le devant de la base est dégagé.

**État à la fin** (23 h 03) : cerveau muet, veilleur en attente, robot sur sa base à ma connaissance ; rien d'installé, rien d'envoyé.

**Complément, 23 h 05 : la note M, et ce qu'elle change au programme.** Pendant que j'écrivais cette section, la session de revue a poussé `notes/M_plan_analyse_en_direct.md` (commit c280057), sur une autre demande de l'utilisateur qu'elle rapporte : « Outil d'analyse en direct et plan d'analyse en direct pendant session de mapping ». La séance du lendemain est donc une séance de cartographie : l'utilisateur est à côté du robot et dit où aller ; je pilote et cartographie avec `enregistreur.py` et `explorer3.py` ; son outil suit en plus le journal de l'explorateur et les fichiers de stations. Le programme ci-dessus se lit donc ainsi : les points 1 à 3 restent (c'est ce que la consigne demande après un changement de firmware) ; le point 5 devient la cartographie de l'endroit qu'il choisira ; l'essai des pivots (point 4) et les quatre autres gestes de la note M § 4 (dix secondes d'arrêt complet au début et à la fin, une avance de 50 cm ou plus face à un mur dans chaque pièce, deux tours de suite à une station, un aller et retour sur un même tronçon de 2 m) sont à sa décision. Deux endroits n'ont encore aucun repère et sont à lui proposer : la grande pièce à gauche de la base, où seule la case C9 a été atteinte (§ 42 à 44), et la pièce derrière la porte H12, où le robot s'est arrêté à la limite K9/K10 (§ 36).

**Second complément, 23 h 10 : un accroc mesuré entre `relance.py` et l'analyse en direct.** À la fin de chaque passage, `relance.py` renomme `PREFIXE_stations.json` et `PREFIXE_explorer3.txt` en `PREFIXE_LETTRE_…`. L'outil de la session de revue (`rv_direct.py`, commit c280057) garde le journal de l'explorateur ouvert pour le suivre. **Mesuré sur ce PC** : un fichier qu'un autre programme Python tient ouvert en lecture ne peut pas être renommé (erreur Windows 32), alors qu'on peut continuer d'y écrire ; `relance.py` s'arrêtait alors sur cette erreur, sans donner le départ du passage suivant. Retouche de `relance.py` : il réessaie pendant cinq secondes, puis dit clairement quel fichier est tenu ; relancé, il reprend où il s'était arrêté. Vérifié face à un lecteur qui tient le journal 1,2 s (fichiers rangés) puis 6 s (message clair après 5 s). Cela ne suffit pas si l'autre outil garde le fichier ouvert toute la séance : je l'ai écrit à la session de revue, avec le second effet du renommage (le même journal et les mêmes stations reparaissent sous un autre nom et seraient lus deux fois). Non vérifié : les deux outils ensemble.

**Troisième complément, 23 h 19 : les deux outils essayés ensemble.** La session de revue a corrigé le sien (commits 55d29e5 puis 2bd190b : plus aucun fichier gardé ouvert, un journal de l'explorateur reconnu à ses deux premières lignes, un tour sur place à son nom et à son heure ; l'essai a porté sur la version du second commit, fichier de 23 h 17, essai de 23 h 18 min 56 à 23 h 19 min 30). Essai sur ce PC, sans le robot : une fausse séance faite des vrais fichiers d'`exploration24` (passes a et b), écrite au fil de l'eau dans un dossier à part, hors de `mesures/` (journal de l'explorateur tenu ouvert en écriture et rempli ligne à ligne, fichier des stations réécrit à chaque station, journal des capteurs par petits paquets) ; `rv_direct.py` lancé tel quel pour la suivre ; le vrai `relance.py` lancé dès la fin de chaque passe, face à un faux cerveau. Résultat : 8 contrôles bons sur 8. Les deux renommages sont faits du premier coup (0,2 s chacun, départ de la passe suivante donné), 9 stations et 9 tours sur place sont annoncés une fois chacun, les deux fins de passe sont vues, aucune erreur. Non vérifié : une vraie séance, avec le robot et la console du cerveau.

## 56. Première séance sous firmware v13 : l'essai des pivots, un tapis que le robot prend pour un vide, la bande de parquet de la pièce à gauche et les cinq gestes de mesure (2026-11-15, 8 h 35 à 9 h 17, séance encore ouverte)

**Les demandes de l'utilisateur.** À moi : « Pièce à gauche » (8 h 38 : l'endroit à cartographier, parmi les deux proposés au § 55) ; « je k<ai recule de sa base depuis le debut » (8 h 42 : le robot était donc hors de sa base avant le branchement du cerveau) ; « reprend exploration, monte sur le tapis » (9 h 01). À la session de revue, d'après elle : « Les cinq » (8 h 35 : les cinq gestes de mesure de sa note M § 4), et une photo du tapis, que je n'ai pas vue.

**Avant le départ.**

- Le PC a redémarré dans la nuit à 2 h 47 : le veilleur de la session de revue et mon guetteur sont morts avec lui ; elle a relancé le sien à 8 h 35 min 34.
- Cerveau rebranché vers 8 h 35 min 36. Le veilleur a installé la v13 (« v13 Nov 14 2026 21:15:18 », carte redémarrée à 8 h 36 min 29), écouté le robot jusqu'à 8 h 44 min 30 et lu ses 256 numéros de capteurs ; première ligne « fini, bon » à 8 h 44 min 31 (détail dans sa note L).
- Un piège : la ligne « en cours » du veilleur contient le mot « fini » entre guillemets. Mon guetteur, qui cherchait ce mot seul, s'est déclenché trop tôt, sans conséquence. Il cherche maintenant « ÉTAT : fini » ; `etat_cerveau.py`, qui teste « en cours » d'abord, n'était pas concerné.
- 8 h 44 min 46, `etat_cerveau.py` : v13, sonde ni suspendue ni douteuse, robot muet, rien ne s'oppose. Enregistrement `exploration26_20261115_084456` lancé à 8 h 44 min 56.

**Déroulé.**

| Heure | Quoi | Résultat |
|---|---|---|
| 8 h 45 min 15 | réveil (`w`, `s`), `f` à 8 h 45 min 34, capteur de distance fixe devant | robot en D16, à 1 m de sa position sur la base et tourné vers elle ; 2 050 mAh |
| 8 h 45 min 40 à 8 h 46 min 46 | une minute immobile en mode Safe | 20,0 lectures par seconde, écart le plus long 64 ms, cap 0,00°, compteurs fixes, −143 mA |
| 8 h 47 min 28 | `rot=90`, `rot=-180`, `rot=90` par `/api/mouv` | gyroscope 89,8°, −180,2°, 90,4° ; roues 89,2°, −179,1°, 90,1° ; retour au cap de départ |
| 8 h 48 min 43 à 8 h 51 min 13 | essai des pivots de la session de revue (`rv_essai_pivots.py --go`, dix séries +90°, −180°, +90°) | l'écho de devant passe de 659 à 703 mm ; cap tenu à 0,8° ; le programme ferme la liaison (`s`, `x`), rouverte à 8 h 51 min 43 |
| 8 h 52 à 8 h 53 min 46 | passe « a » d'`explorer3.py`, 100 mm/s : D16 (412, 89), D15 (371, 100), D12 (305, 96), puis vers D9 | trois stations calées sur les repères ; **arrêt en D10, pixel (259, 105) : capteur de vide droit à 81 puis 36 pendant une rotation, mode Safe tombé**, sans contact |
| 8 h 58 min 46 | — | le robot s'endort, cinq minutes après la chute, liaison ouverte en mode passif |
| 9 h 02 | réveil ; `f` à 9 h 02 min 33 : le mode Safe tient à l'arrêt avec le capteur droit à 68-72 | une avance demandée à 9 h 02 min 50 est refusée par le cerveau : la session de revue lisait les capteurs par la sonde à cet instant (voir plus bas) |
| 9 h 04 min 10 | essai demandé par l'utilisateur : avance de 150 mm à 60 mm/s vers le tapis | arrêtée par le robot après 238 ms et 5 mm, mode Safe tombé |
| 9 h 04 min 43 | `f`, puis recul droit de 300 mm à 60 mm/s | 299 mm faits, mode Safe tenu, capteurs de vide revenus à 2 550-2 660 |
| 9 h 06 à 9 h 07 min 43 | passe « b », le long du tapis, 100 mm/s : E11 (275, 108), E11 (281, 130), F11 (279, 149), une remontée d'un mètre vers le nord, D12 (300, 98) | quatre stations, ni contact ni alarme ; capteurs de vide jamais sous 2 486 |
| 9 h 08 min 34 | passe « c » : un second tour au même endroit, sans bouger (le « double tour ») | filtre corrigé de 7 mm |
| 9 h 09 min 44 à 9 h 10 min 33 | aller et retour de 2 m par `passage.py` (`cap=0 av=2000,100 cap=180 av=2000,100`), de D12 à D16 | 2 003,7 et 2 003,6 mm ; position comptée au retour (299,8 ; 99,6) |
| 9 h 10 min 48 | passe « d » : un tour de contrôle au point de retour | repères : (300,3 ; 99,7), soit la position comptée à 1 cm près |
| 9 h 11 min 36 à 9 h 12 min 59 | passe « e » : retour par D14 (366, 86) jusqu'en D16 (413, 82), 150 mm/s | trois stations, ni contact ni alarme |
| 9 h 13 min 20 | `passage.py va=405,88,80 cap=90` | robot en D16, pixel (404,8 ; 88,1), cap 89°, face à la base, écho à 1 220 mm |
| 9 h 13 min 47 à 9 h 14 min 00 | arrêt complet de la fin | 20,1 lectures par seconde, cap et compteurs fixes |

**La v13 est vérifiée robot immobile puis en mouvement**, ce que le § 55 laissait non vérifié : lectures régulières, rotations et avances exécutées par le cerveau comme avec la v11. Les lignes « texte du robot » arrivent entières. Au réveil de 8 h 45 le robot écrit, après « bootloader id », cinq lignes que la v12 coupait : « assembly: ningbo-wifi-v2 », « revision: 8 », « flash version: 13 », « flash info crc passed: 1 », « battery-current-zero 252 ». Le masquage de l'enregistreur a joué sur l'identifiant. Deux lignes « Flux continu de capteurs (opcode 148) mis en pause » à 8 h 45 min 25 et 27 sont absentes des consoles du 14 ; d'après la session de revue c'est le réflexe du firmware après trois lectures incohérentes qui suivent un réveil, déjà vu le 10.

**L'essai des pivots.** Après chacune des dix séries, robot revenu à son cap : 672, 663, 665, 668, 668, 676, 681, 686, 686, 703 mm, pour 659 au départ. Dépouillé par la session de revue : environ 5 mm de recul par série, que les roues ne comptent pas (le cerveau compte −2 et +1 mm), sans déplacement de côté (l'écho de droite reste vers 980 mm). Réserve : la cible n'était pas un mur nu. Je la croyais être le dos de la base ; le premier tour de la cartographie a montré que le robot était à 1 m de sa position sur la base, donc que l'écho de 650 à 700 mm venait d'autre chose, sans doute de l'objet posé devant la base (§ 53). D'après elle une cible de dix centimètres à 66 cm ne suffit pas à expliquer 44 mm ; elle propose de refaire l'essai dans un coin, face à un vrai mur. Ce recul va dans le sens des 24 cm comptés en trop dans le couloir mené au centrage (note J § 2.3) : une vingtaine de séries en expliqueraient une dizaine.

**Le tapis de la pièce à gauche.**

- Mesuré. En entrant dans la pièce, à la fin d'une avance de 870 mm (8 h 53 min 42,6 à 43,2), les capteurs de vide passent sur une bande sombre (avant droit 749, avant gauche 881, droit 153) ; le mode Safe tient. Pendant la rotation suivante (−25,4° demandés), le capteur droit lit 1 215, 418, 81 : mon programme demande l'arrêt (seuil 150) et à la lecture suivante, 36, le mode lu passe de 3 à 2. Rotation arrêtée à −22,0°. À l'arrêt : gauche 1 628, avant gauche 1 530, avant droit 2 065, droit 64 à 70.
- D'après la photo que l'utilisateur a envoyée à la session de revue : un tapis vert foncé à motifs, bordé de franges blanches ; l'avant du robot débordait sur les franges. Les franges donnent 1 060 à 1 700, le poil sombre 36 à 81, le parquet 2 100 à 2 660.
- Mesuré sur la demande « monte sur le tapis ». Le mode Safe se prend et tient à l'arrêt avec un capteur à 68-72 (97 s). Une avance le fait tomber en 0,25 s au plus, après 5 mm. Un recul droit passe : le capteur descend à 100 pendant deux lectures, le mode tient. La documentation du robot dit la même chose de l'avance et du recul ; la rotation sur place, qu'elle ne cite pas, le fait tomber aussi (8 h 53).
- Conséquence : **en mode Safe le robot ne peut pas rouler sur ce tapis.** Il faudrait lui retirer sa protection contre le vide (mode Full, que la consigne interdit, ou capteurs masqués) : décision de l'utilisateur, non prise. Règle pour les outils, pas encore écrite dans le code : quand un capteur de vide est sous 150 environ, ni avance ni rotation, un recul droit d'abord.
- Tracé. Bord est du poil sombre vers u = 257 du plan, entre v = 97 et v = 105 ; aucune frange à l'est de u = 265 (tour en (275, 108) : capteurs à 2 507 au moins). L'étendue vers le nord, le sud et l'ouest n'est pas mesurée. Zone interdite provisoire ajoutée à `plan_lidar/obstacles.json`, hors dépôt (trois disques ; l'ancien fichier gardé sous `obstacles_20261115_0915.json`) : le planificateur ne trouve plus de chemin vers D9 et garde ceux de la bande de parquet.
- La consigne demande de ne pas reprendre le mode Safe de moi-même après une retombée. Je l'ai dit à l'utilisateur et ne l'ai repris qu'après son « reprend exploration ». Après le refus de monter, je l'ai repris une seconde fois pour reculer, comme je le lui avais écrit avant d'essayer.

**Ce que la cartographie donne.**

- Stations nouvelles sur la bande de parquet à l'est du tapis : E11 (275, 108) et F11 (279, 149). Stations sur des endroits déjà connus : E11 (281, 130), D12, D14, D15, D16. Le milieu de la pièce, de C9 à E10 sur le plan, est sous le tapis : fermé au robot.
- Filtre et repères s'accordent à 10 cm ou moins en D12, D15 et E11. Ils diffèrent de 31 cm au départ devant la base (station 0 de « a ») et de 21 cm en D14 et devant la base au retour (stations 1 et 2 de « e »), comme les 13 et 14 (§ 42 à 44). À la station 3 de « b » (D12, après la remontée d'un mètre) ils diffèrent de 25 cm ; le tour suivant au même endroit, parti de la position des repères, donne un filtre à 7 mm d'elle avec une note de 0,93, mais cette fois sans repère reconnu. Je ne tranche pas ; la session de revue regarde.
- La règle du cap lu sur les repères (§ 45) a joué pour la première fois sur le robot : « cap corrigé de +4,1° (16 parois) » en E11, après la reprise au bord du tapis.

**Les cinq gestes de la note M § 4.** Arrêts complets du début et de la fin ; essai des pivots ; une avance face à un mur dans chaque pièce (la remontée de F11 vers le nord ; l'aller de l'aller et retour, écho de 3 309 à 1 295 mm) ; double tour en D12, deux tours de suite au même endroit : filtre à 7 mm ; aller et retour de 2 m : position comptée retrouvée à 1 cm près par les repères, après 4 m et deux demi-tours. Le dépouillement revient à la session de revue.

**Les deux outils ensemble sur une vraie séance**, laissé non vérifié au § 55 : `relance.py` a rangé cinq passes pendant que `rv_direct.py` tournait, du premier coup à chaque fois.

**Un croisement entre les deux sessions.** À 9 h 02 min 42 la session de revue a lancé une lecture par la sonde en croyant que je réveillais le robot pour elle ; je reprenais la séance. La lecture périodique a été suspendue jusqu'à 9 h 03 min 14 et le cerveau a refusé mon avance de 9 h 02 min 50 (« le robot ne répond pas ») : la sécurité de la v13 a joué, rien n'a bougé. Deux lignes de la console à cet instant (« Le robot envoie du texte… », puis « d6d6d6G7G7G7 ») sont des octets de ses réponses pris pour du texte, pas un écrit du robot. Convenu : plus de sonde pendant un enregistrement sans mon mot écrit.

**Deux erreurs de ma part.** J'ai écrit à la session de revue que le robot était à 50 cm de sa base, d'après le seul écho de 650 mm : il était à 1 m, d'après les repères. Et j'ai nommé « D11 » à l'utilisateur la première station de la passe « b » : c'est E11, calculé après coup avec `grille.py` ; corrigé auprès de lui.

**Non vérifié.** L'étendue du tapis ; ce que donne l'essai des pivots devant un vrai mur ; pourquoi filtre et repères diffèrent devant la base ; les lignes « texte du robot » de l'enregistrement, à relire avant de le pousser.

**État à 9 h 17** : robot en D16, pixel (404,8 ; 88,1), cap 89°, face à sa base à 1 m, en mode Safe, immobile, 1 871 mAh ; enregistreur en marche jusqu'à 9 h 34 min 56 ; l'utilisateur doit dire s'il lance « rentre à la base », s'il continue ailleurs ou s'il arrête.

**Complément, 9 h 23 : la séance fermée, et ce que l'utilisateur demande pour le tapis.** À ma question (lancer « rentre à la base », ou continuer ailleurs), il a répondu à 9 h 19 : « non, va sur le tapis, il va meme falloir au final le designer comme zone focus de nettoyage ». En mode Safe c'est impossible (plus haut). Je ne l'ai pas tenté une troisième fois et je n'ai pas touché au mode Full : la consigne l'interdit, et le firmware ne sait pas le demander. Séance fermée à 9 h 20 min 43 (`5`, capteur de distance arrêté, `s`, `x`) ; enregistreur arrêté par son fichier STOP ; robot laissé en D16, pixel (404,8 ; 88,1), cap 89°, à 1 m devant sa base, pas dessus, 1 855 mAh. Question posée à 9 h 22, réponse attendue. Première façon : le mode Full, avec la surveillance du vide et des roues levées refaite dans le cerveau partout sauf sur le tapis ; il y faut une version 14, sa règle « jamais le mode Full » levée par lui, et son accord pour l'installer ; c'est ma recommandation, parce qu'on garde la lecture des capteurs de vide, qui est ce qui fait reconnaître le tapis. Seconde façon : masquer les quatre capteurs de vide au papier blanc et au ruban ; c'est immédiat, mais le robot devient aveugle au sol partout. Dans les deux cas le robot ne se protège plus seul d'une vraie marche : je lui ai demandé s'il y en a une chez lui. Enregistrement relu avant d'être poussé : treize lignes « texte du robot », identifiant masqué, aucun nom de réseau, aucun chemin du PC.

## 57. Le tapis abordé de face : la brosse latérale se glisse sous son bord ; firmware v14 écrit, pas installé ; trois corrections des repères mises en doute (2026-11-15, 9 h 25 à 9 h 42)

**Les demandes de l'utilisateur.** « mais avant en operant seul il pouvais y monter, on peut reculer et reessayer ? » (9 h 25). Puis, en regardant le robot : « en fait la brosse laterale ne tournant pas, elle se glisse sous l tapis et bloc le robot, peut on la faire tourner juste elle tres doucement quand on franchi des obsracles ? » (9 h 31).

**Ce que sa première phrase corrige.** Je lui avais écrit que le nettoyage normal du robot refuserait « sans doute » ce tapis : c'était une supposition, et lui l'a vu y monter. Les deux essais du § 56 partaient d'un robot de travers sur le bord, un capteur déjà au-dessus du poil sombre : ils ne disaient rien d'une entrée de face.

**Les deux essais** (enregistrement `exploration27_20261115_092602`). Retour vers le tapis par une passe d'`explorer3.py`, puis cap plein ouest, robot entièrement sur le parquet ; une avance droite de 900 mm demandée par `/api/mouv`, sans l'alarme de mes outils du PC : c'est le robot qui décide.

| | Essai 1, 9 h 28 min 38, 100 mm/s | Essai 2, 9 h 30 min 23, 150 mm/s |
|---|---|---|
| Avance droite avant le bord | 536 mm | 402 mm |
| Capteurs de vide avant, à l'arrivée sur les franges | 1 264 puis 904 | 861 et 704 |
| Cap à la fin | −41° (le robot tourne à droite) | −67° |
| Compteurs des roues | gauche 776 mm, droite 1 035 mm | gauche 786 mm, droite 1 019 mm |
| Courants | roue droite 320 à 480 mA, batterie jusqu'à −461 mA | roue droite 320 à 480 mA, batterie jusqu'à −517 mA |
| Mode Safe | tenu | tenu |
| Capteurs de vide au plus bas | 744 | 704 |
| Fin annoncée par le cerveau | « 899 mm pour 900 mm demandés, distance atteinte » | « 897 mm pour 900 mm demandés, distance atteinte » |

- Les capteurs de vide ne sont jamais descendus sous 700 : le poil sombre (36 à 81, § 56) n'a pas été atteint. Cette fois ce n'est donc pas la sécurité du robot contre le vide qui l'a empêché de monter.
- D'après les compteurs le robot aurait tourné à gauche ; d'après le gyroscope il a tourné à droite. La roue droite tournait sans faire avancer le robot. La session de revue l'a lu de même ; son outil a signalé « les roues forcent » 1,5 s après le début, la première fois qu'il prend un patinage sur le fait.
- Ni contact du pare-chocs ni roue levée.
- Dégagements : recul droit de 300 mm, rotation pour revenir face au tapis, second recul. Après le second essai les quatre capteurs de vide lisaient 1 000 à 1 389 (l'avant sur les franges) et le capteur de distance voyait quelque chose à 398 mm, sur le tapis ; un dernier recul de 246 mm a remis le robot sur le parquet. Séance fermée à 9 h 32 min 18 (`5`, `s`, `x`).

**L'explication, donnée par l'utilisateur qui regardait** : à l'arrêt, la brosse latérale se glisse sous le bord du tapis et retient le robot. En nettoyage normal elle tourne et passe par-dessus. Je ne l'ai pas vu moi-même ; les mesures vont dans ce sens (pivot sur le coin avant droit, où est cette brosse ; roue droite qui patine).

**Un défaut du firmware que ces essais montrent.** Le cerveau a poussé jusqu'au bout pendant que le robot pivotait de 41° puis de 67° : les roues tournaient et le chemin compté augmentait, donc aucun de ses arrêts ne jouait. Une avance devrait s'arrêter quand le cap s'écarte de plus d'une quinzaine de degrés. Pas corrigé ici : un changement à la fois.

**Firmware v14 : écrit, compilé, PAS installé** (commit 0a273a3). Un seul ajout ; la conduite et les autres sécurités ne changent pas.

- `brosseLaterale(p)` : ordre 144 du robot, brosse principale 0, brosse latérale `p` bornée dans le code à [0, 60] sur 127, sens normal seulement, aspiration 0.
- `/api/mouv?…&brosse=N` : la brosse part avec le premier ordre de roues du mouvement et s'arrête à sa fin, quelle qu'elle soit.
- `/api/brosse?lat=N[&ms=T]` : une impulsion de 5 s au plus, robot immobile, pour régler la puissance sous les yeux de l'utilisateur ; refusée robot muet, hors du mode Safe, roue soulevée, robot qui bouge, sonde en cours.
- Arrêts : fin de mouvement, tout arrêt des roues (`stopWheels`), échéance de l'impulsion, garde-fou de la boucle (brosse en marche sans mouvement ni impulsion, ou robot sorti du mode Safe), démarrage de la carte. Un mouvement qui ne demande pas la brosse arrête une impulsion en cours.
- `/api/state` gagne « brosse » ; `/api/mouv` gagne le champ « brosse ». Aucune touche ne met la brosse en marche.
- Vérifié : compilation sans erreur (1 150 678 octets, 87 % de la place), relecture de la différence ; binaire hors dépôt, `build/roomba694_v14.bin`. Non vérifié : rien sur la carte ni sur le robot ; la logique n'a pas tourné sur le PC face à un faux robot. Relecture demandée à la session de revue.
- La consigne dit « Brushes and vacuum off ». La v14 la lève pour la brosse latérale seule, à puissance réduite, le temps d'un mouvement ou d'une impulsion courte. L'accord de l'utilisateur pour l'installer est demandé (9 h 42), pas encore donné à l'heure où j'écris.
- Une fois monté sur le tapis, le robot peut encore être arrêté par ses capteurs de vide sur le poil sombre : la question du § 56 (lever la protection contre le vide) reste ouverte.

**Trois corrections des repères mises en doute** (analyse de la session de revue sur l'enregistrement du § 56 ; ses chiffres, dans `data_analysis/results_rv_gestes_20261115.txt`). Ce que le § 56 affirmait, et ce que cette analyse remplace :

- Le § 56 place la station 3 de la passe « b » en D12, pixel (300, 98), d'après les repères (« calé sur 5 tours », à 250 mm du filtre). D'après elle, trois témoins indépendants disent que cette correction est fausse : le chemin refait avec les roues et le gyroscope seuls (238 mm d'écart sur ce tronçon, 7 à 80 mm sur les autres), les parois comparées d'un tour à l'autre, et la base. Le robot était là où le filtre le voyait, vers le pixel (287, 96), en D11. Même chose pour les stations 1 et 2 de la passe « e » (corrections de 21 cm).
- Conséquence : à partir de cette station les positions retenues sont décalées d'environ 25 cm vers l'est, puis de 15 à 20 cm de plus au retour. **La position finale du § 56, « face à la base, pixel (404,8 ; 88,1) », est donc fausse** : pendant les sept minutes d'attente aucun récepteur infrarouge n'a vu la base, et le capteur de distance lisait 1 204 mm ; d'après l'estime le robot a fini une cinquantaine de centimètres à l'ouest de son point de départ.
- Ce qui tient, ce sont les mesures brutes. Roues contre capteur de distance : 1,0000 sur cinq avances face à un mur (6 m). Deux tours au même endroit : 3 et 8 mm d'écart entre leurs parois. Aller et retour de 2 m : d'après les parois le robot revient à (−10, −54) mm de son départ, `passage.py` le comptait à (0, −25) mm : 3 cm d'erreur de l'estime après 4 m. Le « 1 cm » du § 56 comparait l'estime aux repères, pas à une référence indépendante.
- Le filtre, relancé autour de la position des repères, l'a confirmée avec une note de 0,93 : filtre et repères peuvent donc s'accorder sur une position que les roues, les parois et la base contredisent.
- Supposé par elle : un objet vu par les anciens tours près de D12 et de la base a changé de place, et plusieurs repères se trompent ensemble.
- Son idée, pas encore dans le code : ne pas appliquer une correction des repères de plus de 12 cm quand l'estime depuis le tour précédent a moins de 2 m. Ce matin elle aurait écarté ces trois corrections et gardé les autres.
- Je rapporte sans trancher entre le plan, les repères et l'estime. Les stations nouvelles de la passe « b » faites avant celle-là (E11 deux fois, F11) ne sont pas en cause. La règle « croire les repères » (§ 43) ne vaut donc pas sans contrôle.

**Non vérifié.** La v14 sur la carte ; l'explication par la brosse (vue par l'utilisateur, pas par moi) ; la position du robot en ce moment (les roues ont patiné, aucun tour sur place depuis) ; l'étendue du tapis.

**État à 9 h 42** : robot sur le parquet, face au tapis, à 25 cm des franges environ, vers E11 (position non mesurée), séance fermée, 1 828 mAh ; cerveau en v13 ; v14 prête ; accord de l'utilisateur attendu.

## 58. Firmware v14 installé ; le tapis se prend à reculons ; la position perdue un quart d'heure par ma faute, puis retrouvée (2026-11-15, 9 h 43 à 10 h 27)

**Les demandes de l'utilisateur.** « Oui, installe » (9 h 43, pour la v14). Puis, vers 9 h 50, le robot à moitié sur le tapis : « continue de mapper cette salle au complet et de receuillir toute info necessaire a l<autre session ». Je lui avais demandé s'il m'autorisait, pour ce tapis, à reprendre seul le mode Safe et à reculer quand le robot coupe ses roues ; j'ai pris sa réponse pour un oui, et le lui ai écrit.

**Enregistrements** : `exploration28_20261115_094456` (9 h 44 min 56 à 10 h 14 min 33) et `exploration29_20261115_101456` (10 h 14 min 56 à 10 h 26 min 44), tous deux avec la touche `e` chaque seconde (courants des moteurs dans `_e.csv`).

### 58.1 La v14 sur la carte

- Envoi à 9 h 44 min 25 par `/update` (9,9 s) ; « v14 Nov 15 2026 09:38:48 » lue à 9 h 44 min 46, dernier redémarrage par la mise à jour, `brosse` : lat 0, max 60.
- Robot immobile : `/api/brosse?lat=25` refusé robot endormi (« le robot ne répond pas »), puis refusé en mode passif (« le robot n'est pas en mode Safe »). En mode Safe : impulsion à 25 sur 127 pendant 3 s : brosse latérale 48, 40, 62 mA (touche `e`), arrêt seul à l'échéance ; impulsion à 40 coupée par la touche `5` après 2,2 s : 63 et 66 mA. La brosse principale reste à −10 mA du début à la fin (un décalage : ce courant est là dès la prise du mode Safe), les roues à 0.
- Relue après coup par la session de revue : rien de bloquant. Deux chemins à fermer dans une prochaine version, tous deux pendant une impulsion robot immobile : une mise à jour qui commence, et un tour sur place lancé pendant l'impulsion (la brosse va alors à son échéance, 5 s au plus). Ses suggestions : arrêter une avance dès 8° d'écart de cap ; couper la brosse quand son courant reste haut ; mettre ce courant dans le journal à 20 lignes par seconde.

### 58.2 Le bord du tapis en marche avant, brosse en marche : une réussite, un échec

| | 9 h 46 min 50, brosse à 40 | 9 h 57 min 12, brosse à 40 |
|---|---|---|
| Demandé | 900 mm à 150 mm/s | 950 mm à 150 mm/s |
| Résultat | 694 mm tout droit, cap à 1° près, arrêt par le capteur de distance à 29 cm d'un meuble | 239 mm droit, puis pivot de 93° à droite ; « distance atteinte » à 947 mm comptés |
| Roues | 694 mm chacune | gauche 786 mm, droite 1 119 mm |
| Brosse latérale | 56 à 72 mA sur le parquet, 142 puis 120 mA en montant | 45 à 89 mA, puis 323 à 358 mA pendant tout le pivot : bloquée dans les franges |
| Capteurs de vide avant au bord | 920 et 705 à la même lecture : bord pris d'équerre | l'avant gauche seul d'abord (355), le capteur droit resté sur le parquet : bord pris de biais |

Lecture de la session de revue, que je partage : la brosse ne suffit pas, il faut aussi arriver d'équerre sur le bord. À 60, le maximum de la v14, je n'ai pas eu l'occasion d'aborder des franges.

### 58.3 Deux erreurs de ma part

**Un recul à l'aveugle dans la mauvaise direction.** Mon nouvel outil `peigne.py` (une avance droite sur le tapis, puis le retour en marche arrière de la distance comptée) n'avait pas prévu le pivot : après les 93°, il a reculé « tout droit » de 947 mm, donc vers le bas du plan, sans rien voir derrière lui (9 h 57 min 21 à 35). Aucun contact détecté, mais le robot s'est retrouvé près du mur du fond. Corrigé le jour même : `peigne.py` arrête un mouvement dès que le cap s'écarte de 12° et ne lance plus aucun retour après un pivot.

**Un cap faux de 97° pendant un quart d'heure.** À 9 h 59 min 47 un tour sur place a été interrompu par une zone sombre (capteur de vide avant gauche à 287, 93 puis 37 ; le mode tombe 75 ms après, d'après la session de revue). J'ai lu dans le journal que le tour en était à 110° ; il en était à 373°. Tout ce que j'ai fait ensuite, jusqu'à 10 h 12, est parti d'un cap faux de 97° : deux tours sur place aux notes médiocres (0,64 et 0,70, passes « d » et « e » d'`exploration28`, **positions fausses**), une « dent » de 748 mm qui était en réalité une remontée de l'allée vers le nord, une avance de 799 mm en biais. Ce qui m'a alerté : le capteur de distance voyait 3 695 mm de libre là où la pièce n'en fait que 2. J'ai arrêté le robot, envoyé la carte à l'utilisateur pour qu'il me dise sa case, et demandé à la session de revue de refaire le chemin ; c'est un de ses messages (« à 373° du tour ») qui m'a fait voir l'erreur. Refait avec le bon cap, le chemin colle avec quatre lectures du capteur de distance (2 563 mm vers le mur du haut depuis le bas de l'allée, 3 695 mm vers le mur est de la pièce de la base, etc.). Tour de contrôle à 10 h 13 (passe « f ») : filtre corrigé de 56 mm et 5°, note 0,74, pixel (299,5 ; 131,5), case E12.

Ce que j'en retiens pour la méthode :

- après un patinage, la position comptée ne vaut plus rien : un tour sur place tout de suite, et un second si la note est sous 0,5 (le tour de 9 h 51, note 0,30, plaçait le robot 64 cm à côté ; celui de 9 h 55, note 0,97, l'a remis) ;
- le filtre lancé avec un mauvais départ ne dit pas qu'il se trompe : il rend une note moyenne ;
- `Plan.localiser` promené sur tout le plan et tous les caps, avec deux tours liés par le chemin compté entre eux, trouve une dizaine de solutions de 0,92 à 1,00 dans quatre pièces : les parois seules ne situent pas le robot sans un départ à peu près juste ;
- après un tour sur place le cap n'est plus celui d'avant : prendre la ligne `DEPART=` de `relance.py` (oublié une fois ce matin).

### 58.4 Le tapis se prend à reculons

| Heure | Quoi | Résultat |
|---|---|---|
| 10 h 15 min 54 | depuis le parquet, pixel (290 ; 100), robot tourné vers l'est : trois reculs de 300 mm à 60 mm/s, sans brosse | 893 mm, cap tenu, mode Safe tenu, aucun patinage ; capteurs de vide au plus bas 832 |
| 10 h 16 min 45 | deux reculs de plus | 596 mm ; au plus bas 755 ; robot au milieu du tapis |
| 10 h 17 min 33 | dix secondes d'arrêt, puis un tour sur place complet sur le tapis | aucune chute du mode Safe ; filtre 0,79 ; pixel (209 ; 101), case D8 |
| 10 h 18 min 16 | avance de 402 mm vers le mur du haut, sur le poil ; retour par deux reculs | capteur de distance 677 mm à l'arrivée ; sol au plus bas 754 |
| 10 h 18 min 55 | sortie en marche avant, 1 503 mm plein est à 100 mm/s, brosse à 40 | cap tenu, aucune alarme ; robot sur le parquet |
| 10 h 19 min 58 | seconde ligne, v ≈ 122 : 1 492 mm à reculons | au plus bas 803 |
| 10 h 20 min 38 | tour sur place en (208 ; 126), case E8 | filtre 0,71 ; puis sortie en avant de 1 505 mm |
| 10 h 23 min 33 | recul de 598 mm le long de v ≈ 156, où j'attendais une bordure sombre | du parquet seulement (2 561 au plus bas) |

- **En marche arrière le robot monte sur le tapis sans patiner** : la brosse latérale, à l'avant, suit au lieu de pousser sous le bord. Une fois dessus il avance, tourne sur place et ressort en marche avant.
- Le poil renvoie 755 à 2 246 sur les deux lignes relevées : presque tout le tapis est acceptable pour les capteurs de vide. Les zones très sombres (36 à 81 le matin, 37 à 287 à 9 h 59) sont petites et près des bords.
- **Ce que cela remplace** : le § 56 concluait « en mode Safe le robot ne peut pas rouler sur ce tapis ». C'est faux dit ainsi : il ne peut ni avancer ni pivoter tant qu'un capteur de vide est au-dessus d'une de ces petites zones très sombres, et il s'en dégage en reculant. La zone interdite que j'avais tracée dans `plan_lidar/obstacles.json` en est retirée (copie gardée). La question du mode Full ou des capteurs masqués (§ 56) n'est plus urgente : elle ne se pose que pour ces petites zones.
- La mesure que la session de revue demandait en premier, un recul droit avec les capteurs au-dessus du sombre pendant une seconde, **n'est pas faite** : je n'ai pas trouvé de zone sombre sous les capteurs pendant un recul.

### 58.5 Le reste

- **Contact** à 10 h 21 min 51,6, pare-chocs, à 80 mm/s, en remontant l'allée de parquet : un objet mince en C11, pixel (287 ; 78), ajouté aux obstacles. Le capteur de distance lisait 1 042 mm ; le capteur optique centre gauche est monté de 48 à 485 en deux secondes. `passage.py` laisse ce capteur monter jusqu'à 3 000 avant d'arrêter : trop permissif hors des passages étroits.
- **Outils.** `outils/pilote.py` : la variable d'environnement `ROOMBA_BROSSE` (0 à 60) ajoute `&brosse=N` à chaque mouvement demandé au cerveau, pour tous les outils qui passent par le pilote. `outils/peigne.py` (nouveau) : une avance droite depuis le parquet et son retour, avec l'arrêt sur écart de cap. Les passes d'`explorer3.py` de cette section sont faites sans `--reperes` (§ 57).
- **Retour** : par l'allée, puis 2 004 mm plein est le long de la ligne D, sans contact. Devant la base, un tour sur place (filtre corrigé de 167 mm, note 0,89) reçoit des codes infrarouges sur 42 lectures seulement (164 surtout, 172, les trois récepteurs à 164 neuf fois) ; à l'arrêt final, tourné vers la base d'après mon cap, les récepteurs lisent 0. La position ou le cap y sont encore faux de quelque chose : je ne dis pas que le robot est dans l'axe.

**Non fait.** Le reste de la pièce : le haut du tapis au-delà de C8, son bas, la bande entre le lit et le mur de gauche. Le recul sur une zone sombre. L'essai des pivots face à un mur nu. Les repères à refaire avec les stations du jour.

**État à la fin** (10 h 29) : séance fermée à 10 h 26 min 43 (`5`, `s`, `x`) ; robot dans la pièce de la base, à 1 m environ devant elle, pas dessus, 1 707 mAh ; cerveau en v14.

**Complément, 10 h 30 : ce que la session de revue tire de ces enregistrements** (ses chiffres ; je les rapporte).

- **Ce que le robot prend pour un vide n'est pas le poil du tapis : c'est une ligne sombre très étroite, juste derrière les franges.** Pendant le recul de 10 h 15 les capteurs lisent, dans l'ordre : le parquet (2 500 à 2 650), les franges sur 4 cm (945 à 1 100), une seule lecture basse (797, 179, 736 en trois lectures, soit 8 mm de chemin), puis le tapis lui-même, 750 à 2 400, et 698 au plus bas pendant le tour sur place. Les trois chutes du mode Safe de la matinée s'expliquent ainsi : un capteur resté sur cette ligne, robot arrêté dessus (9 h 02) ou capteur qui la longe pendant une rotation (8 h 53 et 9 h 59). Traversée d'équerre et sans s'arrêter, elle ne fait rien : 153 au plus bas à 110 mm/s, 179 à 60 mm/s. Lignes déjà vues, en pixels : (254,9 ; 102,5) en D10, (260,7 ; 142,6) en F10, et vers (261,6 ; 101,9). Le bord du tapis est à gauche de u = 266 à 270, au moins entre v = 98 et v = 129. Supposé par elle tant que le reste du tapis n'est pas vu : à plus de 20 cm du bord, le robot peut travailler sur le tapis en mode Safe, tours sur place compris. Cela précise ce que j'écrivais plus haut (« petites zones très sombres près des bords »).
- En reculant, le robot est monté sur le bord sans la brosse et sans dévier (cap tenu à 1,1° près, roues à 270 à 470 mA au passage) : les roues passent avant la brosse.
- **La position perdue** : son calcul à partir du tour de 9 h 55, patinage retiré (`data_analysis/rv_ou_est_le_robot.py`), place le robot au pixel (305,7 ; 123,3), case E12, à 10 h 06 ; mon tour de contrôle de 10 h 13 donne (299,5 ; 131,5) : même case, 19 cm d'écart. Le tour interrompu avait tourné de 375,3° au gyroscope, soit +17° de cap ; je l'avais compté +110°. Elle se fierait à sa position à 10 cm près et au cap du gyroscope plutôt qu'aux 5° du filtre.
- **Le contact de 10 h 21** : le capteur de distance n'a jamais vu l'obstacle ; le capteur optique centre gauche lisait 47 au repos, 72 à 10 cm, 176 à 6 cm, 333 à 2,5 cm, 428 puis 475 au choc. Un arrêt quand un capteur optique dépasse trois fois son repos aurait arrêté les roues 6 à 7 cm avant. Un seul cas.
- **Pour trancher la question du recul sur le sombre** (non faite) : partir avec un capteur posé sur la ligne. Avancer d'équerre vers le bord le plus lentement possible (le firmware ne descend pas sous 50 mm/s), laisser le robot couper ses roues, vérifier au repos qu'un capteur lit moins de 100, reprendre le mode Safe, puis reculer droit de 100 mm : si le mode tient, le robot ne surveille pas le vide en reculant. À proposer à l'utilisateur.

## 59. Campagne d'essais commandée par la session de revue : les faisceaux de la base, les pivots, une approche lente, la ligne sombre du tapis cherchée, le contour du tapis, et un retour recalé sur les faisceaux (2026-11-15, 10 h 34 à 11 h 53)

**La demande.** L'utilisateur a écrit à la session de revue à 10 h 30 : « une fois cette run process, continue d<explorer les coins sombres du fonctionnement, et de mapper par des tests et d<ameliorer le software et de voir ce qu<il nous cache, ce qui pourrait nous etre utile, tu parle a l<autre session, elle execute le pilotage et tu ecoute et commande, et analyse, mappons loin, augmentons nos capacites de localisation precise ». La session de revue a écrit le plan (`notes/O_campagne_essais.md`, cinq essais courts) ; j'ai piloté, en restant seul juge de la sécurité de chaque geste. Je lui ai écrit le début de chaque essai ; aucun message d'elle ne m'est parvenu pendant la séance.

**Les enregistrements** : `exploration30_20261115_104014` (10 h 40 à 11 h 00, essai 1) et `exploration31_20261115_110551` (11 h 05 à 11 h 52, le reste). Firmware v14. Aucune roue levée, aucune chute du mode Safe, trois contacts légers du pare-chocs.

| Heure | Geste | Résultat |
|---|---|---|
| 10 h 34 | contrôle avant de rouler (`etat_cerveau.py`) | robot pas déplacé depuis 10 h 26 (même cap au gyroscope, 357,8°) |
| 10 h 41 | tour sur place au départ, point P0 (passe « a » d'`exploration30`) | filtre (399,8 ; 78,5), note 0,89 ; 10 cm au nord du tour de 10 h 26 fait au même endroit |
| 10 h 47 à 10 h 53 | **essai 1** : trois traversées de l'axe de la base à 60 mm/s, chacune dans les deux sens (lignes B, C, D : à la hauteur de P0, 400 mm et 800 mm plus au sud) | tableau ci-dessous ; aucun contact ; cap tenu à 1° près |
| 10 h 55 | tour sur place sur l'axe (passe « b ») | ce que voient les trois récepteurs selon le cap |
| 10 h 58 | cinq arrêts de 5 s sur l'axe, caps 180°, 270°, 90°, 135°, 0° | idem, robot immobile |
| 11 h 00 à 11 h 05 | **essai 2** : robot en mode passif sur l'axe, base vue ; lecture des numéros cachés par la session de revue (11 h 01 min 03 à 20) | ses fichiers `sonde_…` ; le robot s'est endormi à 11 h 05 min 10, cinq minutes après la touche `s` |
| 11 h 07 à 11 h 10 | **essai 5** : dix séries de pivots (`rv_essai_pivots.py`) face à la paroi est de la pièce, à 77 cm | +1,2 mm par série |
| 11 h 10 à 11 h 11 | **essai 4** : approche lente de cette paroi, 440 mm puis 61 mm à 50 mm/s | pas de contact ; tableau ci-dessous ; cette paroi n'est pas un mur nu |
| 11 h 13 | retour dans la pièce à gauche par la porte, 1,31 m puis 1,99 m | sans contact |
| 11 h 14 à 11 h 32 | **essai 3** : chercher au bord du tapis un endroit que le robot prend pour un vide, y poser un capteur, reculer | non conclu : l'endroit trouvé n'est pas assez sombre |
| 11 h 32 à 11 h 46 | stations au sud du tapis, sur le tapis, au nord du tapis (passes « b », « c », « d » d'`exploration31`) ; bords nord et sud du tapis | notes 0,83, 0,89, 0,66 ; un contact près du lit |
| 11 h 46 à 11 h 49 | retour par la porte | deux contacts du pare-chocs gauche |
| 11 h 49 à 11 h 52 | traversée de l'axe, retour au point de l'axe du matin, tour sur place (passe « e ») | position retrouvée à 3 cm près |
| 11 h 52 min 30 | fin : `5`, capteur de distance arrêté, `s`, `x` | robot devant sa base, sur l'axe, pas dessus ; 1 426 mAh |

### Essai 1 : les faisceaux de la base

Mesuré, au récepteur infrarouge du dessus, en millimètres vers l'est comptés depuis P0 (ma lecture ; la session de revue a refait le calcul de son côté et trouve la même chose, commits `59bb49b` et `631ea99`) :

| Ligne | vert seul (code 164) | rouge et vert (172) | rouge seul (168) |
|---|---|---|---|
| B, à la hauteur de P0 | de −40 à +138 | de +146 à +201 | de +208 à +475 |
| C, 400 mm plus au sud | de −167 à +80 | de +85 à +105 | de +116 à +535 |
| D, 800 mm plus au sud | de −300 à +6 | aucun (un trou de 2 à 5 cm) | de +40 à +580 |

- **Le récepteur du dessus est à 146 mm en avant du centre du robot** (144 pour la session de revue). Avec ce décalage, les bords lus à l'aller (cap 0°) et au retour (cap 180°) coïncident à 1 cm près. Sans lui, la même frontière paraît à 29 cm d'écart selon le sens de marche.
- **Le passage du vert au rouge est une droite** : +174, +95, +23 mm sur les trois lignes. Elle est inclinée de 10,7° sur la perpendiculaire à mes traversées. C'est un repère absolu au centimètre, d'est en ouest, devant la base.
- **La largeur dit à quelle distance on est** : le vert seul fait 18, 25 puis 30 cm, le recouvrement 5,5, 2 puis 0 cm. Une seule traversée donne donc aussi la position nord-sud, à quelques centimètres près (utilisé au retour, plus bas).
- Les deux récepteurs de devant ne voient rien en traversée. Ils voient la base quand le robot est tourné vers elle (caps 60° à 105° au tour sur l'axe). Robot immobile sur l'axe, face à la base : dessus 164, devant gauche 164, devant droit 172. Ils ne lisent pas le même code : c'est une indication de cap, à exploiter.
- Le récepteur du dessus ne voit pas la base quand le robot lui tourne le dos (rien du cap 135° au cap 318° au tour sur l'axe, rien à l'arrêt aux caps 180° et 270°). Non expliqué : en traversée au cap 180°, au même endroit, il voyait le vert 45 % du temps. Supposé, non vérifié : ce qui est monté sur le robot masque le récepteur vers l'arrière.
- **Ce que je n'ai pas pu dire : la distance à la base.** Les largeurs des faisceaux mettent leur source entre 0,7 et 1,2 m au nord de la ligne B, selon le bord qu'on prolonge.

**Quelque chose en hauteur devant la base.** Depuis le point de l'axe (ligne C), cap 90°, le capteur de distance lit 546 mm, au millimètre près à dix minutes d'intervalle. Cela met un obstacle 17 cm au nord de la ligne B, là où le robot venait de passer sans rien toucher ni rien voir de côté, et où, depuis P0, le même capteur lisait un fond plat à 715 mm. Supposé : le bord d'un meuble au-dessus du robot, que le capteur ne voit pas de près et attrape de loin par le haut de son cône ; les deux échos étroits du tour de 10 h 41, à 44 et 45 cm de part et d'autre, seraient ses pieds. J'ai posé la question à l'utilisateur ; pas de réponse à 11 h 53. Conséquence tenue pendant la séance : ne pas aller plus au nord que la ligne B, parce que ce qui est monté sur le robot dépasse du pare-chocs en hauteur.

### Essai 5 : les pivots, face à une paroi

Dix séries +90°, −180°, +90°. Distance de départ 769 mm (étendue 8 mm sur 19 tirs). Après les séries 1 à 9 : +1, +2, −1, 0, 0, +6, +9, +8, +10 mm ; la dixième lecture est vide. **+1,2 mm par série.** Cap revenu à 1° près à chaque fois. Cela remplace le chiffre du § 56 (+44 mm en dix séries, soit 5 mm par série) : la cible de ce matin-là n'était pas une paroi sûre. Fichier : `revue_20261115_110746_pivots.json` (session de revue).

### Essai 4 : approche lente

Le cerveau ne descend pas sous 50 mm/s. Je n'ai pas retiré l'arrêt du capteur de distance : j'ai abaissé son seuil de 30 à 17 cm, puis à 10 cm (le minimum), le temps de l'approche, et je l'ai remis à 30 cm à la fin (relu). Petit programme jeté après usage ; sortie dans `exploration31_20261115_110551_approche_mur.txt`.

| Capteur de distance (mm) | gauche | avant gauche | centre gauche | centre droit | avant droit | droit |
|---|---|---|---|---|---|---|
| repos | 20 | 16 | 34 | 12 | 48 | 4 |
| 394 | 24 | 20 | 45 | 10 | 56 | 8 |
| 287 | 28 | 22 | 55 | 12 | 56 | 7 |
| 211 | 35 | 30 | 75 | 14 | 63 | 11 |
| 157 | 48 | 44 | 119 | 20 | 63 | 11 |
| 132 | 66 | 68 | 196 | 33 | 68 | 15 |
| 104 | 100 | 145 | 394 | 79 | 95 | 18 |
| 91 | 119 | 205 | 500 | 114 | 119 | 20 |

- Le capteur optique centre gauche domine, comme au contact de C11 (§ 58). Le droit ne bouge presque pas.
- **Cette paroi n'est pas un mur nu.** Le 10 novembre le capteur de distance lisait 143 mm quand le pare-chocs touchait une paroi (§ 22) ; ici il lit 84 mm sans contact. Ce qu'il voit, en haut, dépasse donc d'au moins 6 cm ce qu'il y a à hauteur de pare-chocs. La distance du pare-chocs à ce qu'il a devant lui n'est pas connue : le tableau ne peut pas servir tel quel de règle de distance. À refaire devant un vrai mur.

### Essai 3 : la ligne sombre du tapis

Question de la session de revue : le robot surveille-t-il le vide en reculant ? Il fallait poser un capteur sur un endroit que le robot prend pour un vide, puis reculer.

- 11 h 14, approche de face à 50 mm/s, brosse latérale à 40 sur 127 : à 349 mm la brosse cale dans les franges (346 mA, indicateur de surintensité à 1), le robot dévie de 8° ; aucune lecture sous 667.
- 11 h 17, reculs vers le tapis par pas de 10 mm : les roues arrivent arrêtées contre le bord et patinent ; le robot pivote de 30°, l'estime compte 653 mm quand le capteur de distance en mesure 544.
- 11 h 20, comme le matin : recul de 300 mm d'un trait, puis recul arrêté quand un capteur de devant arrive sur les franges, puis pas de 10 mm sur le tapis : cap tenu à 1°, rien sous 771.
- 11 h 23, 748 mm le long du bord est, sur le tapis, à 50 mm/s : rien sous 707 ; le robot sort par le bas du tapis.
- 11 h 25, approche de face à 50 mm/s **sans brosse** : cap tenu à 2,6° près. Le capteur de vide gauche passe sur une ligne sombre : 571, 417, 271, 230, 233, 340, 762 en 15 mm de chemin. Le mode Safe ne tombe pas.
- 11 h 26 à 11 h 28, capteur gauche ramené dessus par des pivots d'une fraction de degré : 178 au plus bas au repos. Ces pivots se sont faits capteur entre 178 et 250 : le mode Safe a tenu.

**Ce qu'on peut dire** : le seuil du robot est entre 93 (chute de 9 h 59 : 287, 93, 37) et 154 à 178 (pas de chute aujourd'hui, en avance comme en pivot). La ligne sombre n'est pas continue : sombre sur 1 à 2 cm de long seulement, les trois autres capteurs, qui coupaient le bord 5 à 14 cm plus au nord, ne sont pas descendus sous 681. L'endroit très sombre du matin (36 à 81, capteur droit) n'a pas été retrouvé. **La question du recul reste où le § 56 l'avait laissée** : à 9 h 04 une avance est coupée par le robot en 0,25 s (capteur à 59), puis un recul droit de 300 mm repasse sur le même endroit (capteur à 100 pendant deux lectures) et le mode tient. C'est aussi ce que dit la documentation du robot.

### Le tapis : ce qui est mesuré de plus

- **Bord nord** : à 61 cm du mur nord (capteurs de devant de retour sur le parquet à 611 mm du mur, lu au capteur de distance), sans franges. **Bord sud** : sans franges, vers v = 146 ; le robot en sort en marche avant à 50 mm/s sans dévier (0,2°). **Bord est** : franges, couture vers u = 260. Bord ouest : pas atteint, un objet est posé à 43 cm à l'ouest de la station du tapis.
- **Monter dessus** : d'un trait, à reculons, 60 mm/s (trois fois aujourd'hui, cap tenu à 1°). Pas par petits pas. De face, la brosse à 40 cale dans les franges ; brosse arrêtée, l'approche lente passe.
- **Sur le poil l'estime compte 5 % de trop** (1 304 mm comptés pour 1 237 au capteur de distance, cap nord). Courant des roues : 200 à 250 mA sur le tapis, 120 à 180 sur le parquet.

### La pièce à gauche

Trois stations : au sud du tapis (262,0 ; 162,0), note 0,83 ; sur le tapis, note 0,89 ; au nord du tapis (219,9 ; 49,5), note 0,66. Vu au capteur de distance : le mur sud à v ≈ 183,5 ; un lit dont la face est est à u ≈ 234 et la face nord à v ≈ 132,5 ; un meuble dans le coin nord-ouest (face est à u ≈ 193) ; un objet rond à l'ouest du tapis (bord est vers u = 201 à 208). Les zones grises du plan ne disent pas ce qui est au sol : le robot a roulé dans plusieurs d'entre elles.

**Trois contacts**, tous légers (60 à 80 mm/s), tous sur des choses que ni le capteur de distance ni les capteurs optiques n'ont vues, ajoutés à `plan_lidar/obstacles.json` (19 entrées) : 11 h 34, pare-chocs droit, devant le lit ; 11 h 46 et 11 h 47, pare-chocs gauche, dans le passage entre les deux pièces. Ces deux-là sont de ma faute : mon repère avait dérivé (ci-dessous) et le robot longeait le bord sud du meuble de C14-C16, 30 cm plus au nord que je ne le croyais. Il fallait se recaler avant la porte.

### La position : ce que la séance apprend

- **Le filtre a eu raison une fois contre l'estime, et tort une fois, à dix minutes d'écart.** Sur le tapis il corrige de 17 cm (note 0,89) : je refuse la correction (règle des 12 cm de la note O), et le mur nord lu au capteur de distance lui donne raison à 1,4 pixel près. Au nord du tapis il corrige de 16 cm (note 0,66) : je refuse, et là le mur nord et le meuble de l'ouest donnent raison à l'estime. Ce qui les départageait : la note, et un mur lu droit devant.
- **Dans la pièce de la base, le filtre tire vers le nord à chaque tour** (+154, +102, +87 mm aux tours de 10 h 26, 10 h 41 et 10 h 55), et l'estime de la session de revue place le robot 46 cm plus au sud que lui. Au retour, les deux contacts du passage tombent sur le bord du meuble du plan si l'on prend la position du filtre. Supposé : soit le plan n'est pas juste d'une pièce à l'autre, soit une station de la pièce à gauche est fausse. Non tranché.
- **Retour recalé sur les faisceaux.** À 11 h 49, une traversée de l'axe à 60 mm/s : vert sur 227 mm, recouvrement sur 39 mm. Par les largeurs, la ligne est entre B et C ; par la frontière, mon repère avait dérivé de 10 cm d'est en ouest et de 17 cm du nord au sud depuis le matin (47 minutes, quatre stations, deux traversées du tapis). Parti de la position lue sur les faisceaux, le robot est revenu au point de l'axe du matin : mêmes codes aux récepteurs (droit : 164 au lieu de 172), 513 mm au capteur de distance au lieu de 546. **Même endroit à 3 cm près.** Le tour sur place qui a suivi donne (404,9 ; 96,0) ; celui de 10 h 55, au même endroit, (404,9 ; 95,5).

### Mes erreurs

- Deux contacts dans le passage faute de m'être recalé avant.
- Une correction du filtre refusée à tort sur le tapis.
- Un pivot lancé du mauvais côté à 11 h 19 (le capteur s'est éloigné des franges), et un programme de recoupes qui avançait de 5 cm à chaque passe : seules deux recoupes sur six ont croisé la ligne.
- À 11 h 41 mon programme de surveillance s'est arrêté sur une requête sans réponse : le robot a fini son avance de 1,3 m sous la seule garde du cerveau (pare-chocs, capteur de distance, mode Safe). Rien n'est arrivé, mais l'arrêt que j'avais prévu au bord du tapis n'était plus là. Un programme qui surveille un mouvement doit survivre à une requête perdue.

**Non fait** : la conclusion de l'essai 3 ; l'essai 4 devant un vrai mur ; l'essai 6 (numéros cachés, robot en charge sur sa base) ; le parcours long (« mappons loin »), que la session de revue devait m'envoyer.

**État à la fin** (11 h 53) : séance fermée ; robot dans la pièce de la base, sur l'axe, face à elle, pas dessus ; 1 426 mAh ; cerveau en v14 ; seuil du capteur de distance à 30 cm.

**Complément, 12 h 05 : les messages de la session de revue, arrivés d'un bloc à midi, et trois tours sur place.** Ses messages étaient retenus pendant que je pilotais ; les voici, avec ce qu'ils changent à ce qui est écrit plus haut.

- **Devant la base, ce n'est pas un bord en hauteur : c'est un pied de meuble.** L'utilisateur lui a envoyé une photo à 11 h 01 et répondu « Base collée au mur ». D'après elle : un pied de meuble blanc est planté entre le robot et la base, à gauche de l'axe vu du robot ; un autre pied est contre le mur à gauche de la base ; un grand pot de plante est contre le mur à sa droite. L'écho stable à 546 mm est sans doute le premier pied, et le trou d'une seconde dans le vert de la traversée C son ombre. Cela remplace ma supposition. La consigne de prudence reste : pas plus au nord que la ligne B sans y regarder.
- **La paroi de l'essai 4 : deux lectures, non départagées.** La mienne : ce mur n'est pas nu. La sienne : le capteur de distance n'est pas à 27 mm en avant du centre mais vers 120 à 125 mm (photo du robot mise à l'échelle sur son diamètre ; le récepteur infrarouge y tombe à 148 mm, pour 144 à 146 mesurés par les faisceaux). Un mur plat serait alors touché vers 45 à 50 mm lus, et le contact du 10 novembre (143 mm, § 22) se serait fait contre un objet posé devant ce que le capteur voyait. Elle a demandé à l'utilisateur une mesure à la règle. **Rien n'est changé dans les outils d'ici là.** De mon côté, deux indices vont dans son sens : mes outils ajoutent 27 mm à chaque lecture de côté, et le couloir « de 68 cm » ferait 88 cm avec 125 ; et ce chiffre ferait placer le robot trop près du mur qu'il voit le mieux, donc trop au nord dans la pièce de la base et trop au sud dans la pièce à gauche, ce qui est le sens des corrections du filtre de la journée.
- **L'échelle du plan.** Elle demande d'où vient le 53 pixels par mètre. Il a été ajusté le 10 novembre sur les tours du robot (§ 27 : 57 pour la carte du robot seule, 51 pour le trajet seul, 50 à 57 pour la largeur des portes, 54 pour l'ensemble ; 53 retenu ensuite), donc avec le capteur compté à sa place d'alors. Elle trouve, sur 210 trajets entre deux tours, des corrections qui vont contre le trajet de 3,4 % de sa longueur : cela ferait 51 pixels par mètre, la valeur que donnait le trajet seul. Non tranché.
- **La règle « refuser une correction de plus de 12 cm » est retirée par elle** : essayée sur 192 tours enregistrés, elle dégrade la position (elle reste accrochée à un mauvais départ). À la place : un second tour sur place quand l'estime et la correction se contredisent. Je l'avais appliquée deux fois, une fois à tort (plus haut).
- **Ma position au retour, dite plus exactement.** Par rapport au repère du tour de 10 h 41 (celui des lignes B, C, D), ma position retenue à 11 h 49 était 17 cm trop à l'est et 53 cm trop au sud. De ces 53 cm, 25 viennent de l'écart déjà là le matin entre le repère de la pièce à gauche et celui de la pièce de la base (les deux corrections du filtre de 10 h 26 et 10 h 41), 10 de la correction du filtre acceptée à 11 h 32, et 17 de la tournée. C'est après la traversée de 11 h 49 que j'ai redonné au robot la position lue sur les faisceaux ; le tour « e » et la suite sont dans le repère de 10 h 41. L'estime de la session de revue, accrochée à mon tour de 11 h 32, donnait à 11 h 49 une position 31 cm au nord de la mienne : elle allait dans le bon sens. Les deux contacts du passage viennent bien de là : le robot passait plus au nord que je ne le croyais, contre l'objet de D14.
- **Le facteur du gyroscope** (1,0045) : elle a douté de sa valeur du jour, puis retiré son alerte ; non tranché (1,0040 les 10, 13 et 14 ; 1,0013 ± 0,0007 sur quatre tours de ce matin ; 1,0042 ± 0,0014 par une autre mesure). Pour le savoir, **trois tours sur place de suite au point P, de 12 h 02 min 12 à 12 h 03 min 10** (`exploration32_20261115_120142`, passes « a », « b », « c ») : corrections de cap du filtre +0,2°, +0,2° et 0,0° ; positions (405,1 ; 93,4), (405,8 ; 92,8), (405,1 ; 91,9), notes 0,80, 0,85, 0,79. Le filtre tire encore vers le nord, de moins en moins : 49, 12 puis 17 mm. **Dépouillé par elle dans le quart d'heure : 1,0045 est bon aujourd'hui aussi.** Les trois tours sont au même endroit à 5, 7 et 12 mm près ; l'écart de cap entre les directions des parois et le gyroscope est de −0,2°, +1,0° et +2,7° pour 382, 382 et 765° de rotation nette, soit des facteurs de 1,0039 à 1,0080, chacun connu à 0,002 à 0,004 près ; le gyroscope seul, enchaîné du tour de 10 h 41 à celui de 11 h 52 (70 minutes, 2 510° de rotation nette), reste à moins de 2° de mes caps retenus. Son « 1,0013 » venait de quatre tours seulement : il est retiré. Elle relève aussi que la distance du robot à la base n'est pas la même selon la façon de la prendre : 1,12 m d'après le filtre, 1,31 m ± 0,13 d'après la photo de l'utilisateur (lames du parquet comptées), 18 à 33 cm de plus que le filtre d'après la largeur des faisceaux. Elle demande à l'utilisateur une mesure au mètre, robot laissé où il est : je ne le bouge pas d'ici là.
- **Essai 4, deux demandes arrivées trop tard** : un arrêt de deux secondes puis le recul lent jusqu'à 45 cm ; une seconde approche de biais, à 30°. Non faites.
- **L'utilisateur a levé « capteurs seuls pour le moment » auprès d'elle** (« Oui, essaie ») : l'essai des ordres inconnus du robot (essai 7) sera mené par elle, robot posé sur un support, les deux roues dans le vide. Je n'y pilote pas ; un tour sur place de ma part ensuite, puisque le robot aura été porté.

**État** (12 h 05) : séance refermée à 12 h 03 min 24 ; robot au point P, pas sur sa base ; 1 412 mAh.

## 60. La grande boucle : de la base à la pièce du bas à droite, puis au fond de la cuisine, et retour ; mon cap était faux de 10° depuis le matin (2026-11-15, 12 h 15 à 13 h 37)

**La demande.** À ma question de midi (« La porte de la pièce du bas à droite (K23) est-elle ouverte, pour que j'y lance la grande boucle ? »), l'utilisateur a répondu à 12 h 15 : « Oui, vas-y ». À 12 h 45, robot arrêté dans cette pièce (plus bas) : « Repars et va tout au fond à gauche comme hier puis rentre / N'oublie pas la marche ». J'ai lu : la cuisine, jusqu'au coin où il avait posé le robot le 14, par le seuil de sa porte, puis le retour. Pendant que le robot roulait il a encore écrit, avec des photos qui ne me sont arrivées qu'une fois le robot rentré (elles ne sont pas gardées) : « Il te faut peut être un peu plus d'élan ou bien continuer quand ça monte / Oublie pas de faire tourner la brosse comme on a dit plus tôt ce matin / Il faut i aller plus vite/fort et peut être wiggle un peu ? », puis « Non explore plus la cuisine en détail tu n'a pas atteints le coin / Voici ou tu es au moment où tu me dis je suis au coin », puis « 2 screenshots simultaneous pour t'aider à localiser », et enfin « Reprend a partir de tout les derniers messages recus pendant, puis propose et je te dirai go ou non ».

La boucle elle-même est le parcours commandé par la session de revue (`notes/O_campagne_essais.md`, § 2) : partir d'un point P devant la base, aller loin par un chemin connu, revenir au même point, avec un tour sur place tous les 2 m, pour mesurer ce que vaut chaque façon de se situer.

**Les enregistrements** : `exploration33_20261115_121629` (12 h 16 à 12 h 38, l'aller jusqu'à la pièce du bas à droite), `exploration34_20261115_123906` (12 h 39 à 13 h 11, cette pièce, la pièce centrale, le seuil, la cuisine) et `exploration35_20261115_131131` (13 h 11 à 13 h 37, le retour). Firmware v14, sans repères. 45 m environ d'après mon suivi, 54,8 m comptés par les roues, 34 tours sur place.

| Heure | Tronçon | Résultat |
|---|---|---|
| 12 h 17 | tour sur place au point P (passe « a » de 33) | départ |
| 12 h 17 à 12 h 20 | passage vers la pièce à gauche, allée ; stations « b », « c », « d » | sans contact |
| 12 h 20 à 12 h 22 | porte H12 vers le sud : éventail, puis 1 m au cap 280° | sans contact ; stations « e », « f » au bout du couloir |
| 12 h 23 à 12 h 29 | couloir, `centre=0` en deux fois 1 950 mm, station « g » au milieu | douze arrêts, sans contact ; **le cap repris sur les murs** |
| 12 h 29 à 12 h 31 | J20 (station « h »), puis devant la porte K23 (station « i ») | notes 0,87 et 0,83 |
| 12 h 32 à 12 h 35 | porte K23, entrouverte : `centre=282` par pas de 200 mm | passée, 646 mm entre les montants |
| 12 h 35 à 12 h 39 | pièce du bas à droite : stations doubles « j », « k » puis « l », « m » | 12,6 m depuis P |
| 12 h 40 | avance face au mur du fond | contact du pare-chocs gauche contre un meuble bas, à 60 mm/s |
| 12 h 41 min 37 | début du retour | **chute du mode Safe** : capteur de vide gauche à 10 au pied d'un meuble |
| 12 h 48 | reprise sur le mot de l'utilisateur ; sortie par la porte K23 | sans contact |
| 12 h 49 à 12 h 53 | pièce centrale jusqu'à la porte de la cuisine ; stations « b », « c », « d » de 34 | sans contact ; 1 cm d'écart entre filtre et estime en G26 |
| 12 h 55 à 13 h 03 | **le seuil de la cuisine** (plus bas) | passé au troisième essai |
| 13 h 04 à 13 h 09 | entrée de la cuisine, passage étroit, D36 (station « g ») | sans contact |
| 13 h 10 | arrêt en C38 après un contact du pare-chocs gauche ; station « h » | **ce n'était pas le coin** (plus bas) |
| 13 h 12 à 13 h 18 | retour : D36, passage étroit, seuil vers la pièce centrale | sans contact |
| 13 h 19 à 13 h 24 | pièce centrale jusqu'à J20 | un objet nouveau sur le chemin, touché deux fois presque à l'arrêt, contourné |
| 13 h 25 à 13 h 30 | couloir, `centre=180` | sans contact ; mon outil de station a roulé 0,4 m au milieu (plus bas) |
| 13 h 30 à 13 h 32 | porte H12 vers le nord, 1,3 m au cap 108° | sans contact |
| 13 h 32 à 13 h 34 | allée, passage vers la pièce de la base | sans contact |
| 13 h 35 à 13 h 36 | traversée de l'axe de la base, retour au point P, tour sur place (passe « j » de 35) | arrivée |
| 13 h 36 min 51 | `5`, capteur arrêté, `s`, `x` | robot au point P, pas sur sa base, 1 175 mAh |

### Mon cap était trop petit de 10° depuis le matin

Mesuré dans le couloir à 12 h 25 : le centrage lit le cap du robot par rapport aux deux murs, sur trois arrêts, à +6,6°, +7,3° et +7,4° de mon cap à l'estime ; j'avais déjà ajouté 3,4° pris au filtre. Le cap du gyroscope enchaîné depuis P était donc 10,8° trop petit. Le tour suivant, reparti du cap des murs, rend « axes de la pièce 0,0° ».

La session de revue l'a confirmé par le gyroscope seul, enchaîné de tour en tour depuis 9 h 51 : −10,7° au tour de départ de la boucle, et **l'erreur date du tour de 9 h 55 min 40**, fait juste après les patinages au bord du tapis (le filtre y a placé le cap 22,6° sous le gyroscope) ; le tour de contrôle de 10 h 13 n'en a repris qu'une partie.

Ce que cela remplace dans le § 59 :

- **L'axe des faisceaux de la base n'est pas incliné de 10,7° : il est d'équerre au mur.** Les lignes B, C et D, que je croyais tracées d'ouest en est, l'étaient à 10,7° de travers.
- **Les deux pièces « décalées de 25 à 50 cm »** : en roulant 2 m vers l'ouest au cap que je croyais 180°, le robot partait au cap 190° et arrivait 35 cm plus au sud. C'est ce que le filtre corrigeait à chaque tour, vers le sud dans la pièce à gauche, vers le nord dans la pièce de la base, et ce qui a causé les deux contacts du passage. Ni la place du capteur de distance ni l'échelle du plan ne l'expliquent (rejeu de la session de revue, quatre réglages, même correction).
- **Les corrections de cap du filtre** (+1,1° à +2,6° par tour) étaient justes et trop timides ; je les avais écartées.

Une fois le cap repris sur les murs, le filtre et l'estime s'accordent : 4 cm en J20, 6 cm devant K23, 1 cm en G26, 4 cm en D28.

### La pièce du bas à droite

La porte K23, fermée le 10 novembre, était entrouverte : l'éventail donne une trouée vers le cap 282°, `centre=282` passe en six arrêts et 115 s. À l'intérieur, vu au capteur de distance : une face à 36 cm à l'ouest de la première station (battant de la porte ou armoire), un angle de meuble à l'est (un lit sur le plan), le mur du fond. Les deux premiers tours ont des notes de 0,44 et 0,34 et veulent déplacer le robot de 25 à 30 cm : cette pièce a des meubles que le plan ne montre pas, j'ai gardé l'estime, qui colle avec les montants de la porte. Les deux tours du fond s'accordent à 2 pixels (notes 0,95 et 0,86).

- **Contact** à 12 h 40 : pare-chocs gauche, à 60 mm/s, pendant l'avance face au mur du fond ; le capteur de distance lisait encore 338 mm (le mur) : un meuble bas devant le mur.
- **Chute du mode Safe** à 12 h 41 min 37. Le centrage, lancé dans un espace ouvert d'un côté, s'est cru 149 mm à droite du milieu et a mené le robot vers le meuble de l'ouest ; pendant le regard de côté qui a suivi, le capteur de vide gauche a lu 175, 430, 392 puis 10, et le robot a coupé ses roues. Le capteur optique gauche lisait 286 à 295 au même instant : le bord du robot était à 2 ou 3 cm du meuble, sans le toucher. Au repos, sol lu normalement sous les quatre capteurs. Je n'ai pas remis le mode Safe ; l'utilisateur a écrit « Repars » ; recul droit de 150 mm, puis sortie par le trait de l'aller.
- Pour le seuil du robot (§ 59) : 163 en avançant et 175 en pivotant ne font pas tomber le mode, 10 le fait tomber à la lecture même.

### Le seuil de la porte de la cuisine, dans le sens difficile

C'est une baguette entre le parquet de la pièce centrale et le sol de la cuisine, un peu plus bas (photo de l'utilisateur). Trois essais vers la cuisine :

| Heure | Manière | Ce qui s'est passé |
|---|---|---|
| 12 h 55 min 54 | de face, 100 mm/s | la roulette passe, puis les roues patinent au pied du seuil : le capteur de distance reste à 1 245 mm pendant que l'estime compte 215 mm de plus ; roues à 350-640 mA ; nez baissé de 6°. Trois pivots suivis d'une petite avance : le robot tourne de 12 à 15° vers la droite à chaque fois, la roue droite reste prise (analyse de la session de revue) |
| 13 h 01 min 07 | à reculons, 100 mm/s | l'arrière bute contre le seuil : capteur de distance figé à 2 625 mm pendant 300 mm comptés |
| 13 h 02 min 52 | **de biais à 25°, 150 mm/s** | **passé d'un trait** : 847 mm, cap tenu à 0,8°, un seul pic de courant (504 mA) |

Dans l'autre sens, au retour (13 h 18 min 21) : 1 046 mm à 100 mm/s au cap 160°, sans rien, comme le 14.

- Aucune chute du mode Safe, aucune roue levée, aucun contact.
- **Sur un seuil l'estime compte ce que les roues tournent, pas ce que le robot avance** ; le capteur de distance, lui, le voit tout de suite. Mon programme de surveillance jugeait le blocage sur le chemin compté : il n'a donc rien vu. À refaire sur le capteur de distance.
- **Le gyroscope y perd environ 5°** (4,7° entre mes tours de 12 h 52 et 13 h 00, d'après la session de revue ; rien au retour) : il est monté penché et le robot se cabre sur la baguette. Après un seuil pris en force, le cap se reprend sur des parois franches.
- **Non fait : la brosse latérale pendant ces franchissements.** L'utilisateur l'avait demandée le matin et me l'a rappelé ; je l'ai oubliée.
- Cela complète le § 52 (« non essayé : le sens difficile à plus de 60 mm/s, ou de biais »).

### La cuisine : arrêté à un mètre du coin

Le passage étroit (D32 à D34) : le centrage a refusé deux fois d'avancer (obstacle « dans la direction prise » à 208 mm de côté pour une limite à 210) ; fait à la main par pas de 300 mm avec un regard de chaque côté : 237 et 242 mm, 201 et 214, 211 et 187 du centre du robot aux parois, sans contact, à l'aller comme au retour.

Arrêt à 13 h 10 au pixel (1001,7 ; 70,5), case C38, sur un contact du pare-chocs gauche à 50 mm/s. **J'ai écrit à l'utilisateur que le robot était « au coin du fond à gauche ». C'était faux** : sa photo le montre devant le réfrigérateur, à un mètre environ du vrai coin, celui de la poubelle et de la porte (vers C40). Le capteur de distance lisait encore 977 mm de libre devant le robot ; je ne l'ai pas regardé avant d'annoncer. Ce que le pare-chocs a touché n'était donc sans doute pas la poubelle (l'entrée ajoutée à `plan_lidar/obstacles.json` le dit à tort : à corriger en y retournant).

Repères donnés par ses photos : ma station D35/D36 (pixel (925 à 932 ; 88)) est entre le meuble de l'évier et la cuisinière ; C38 est devant le réfrigérateur.

### Le retour

- **Un objet nouveau dans la pièce centrale** à 13 h 20 min 52, sur le trait de l'aller (rien à 12 h 50) : capteur optique gauche à 596, puis pare-chocs gauche presque à l'arrêt, puis pare-chocs droit en cherchant à passer au sud. À l'éventail : un écho mince à 214 mm et un écho large à 559 mm. Contourné par l'est et le sud, sans autre contact. Chaise déplacée ou personne : je ne sais pas.
- **Mon outil de station a roulé sans que je le veuille** à 13 h 27, au milieu du couloir : le filtre s'est trompé de 30 cm (note −0,24), l'explorateur s'est cru loin de sa destination et a roulé 0,4 m vers elle avant de refaire un tour. Dans un couloir, sans contact. Corrigé : un seul tour par station, aucun trajet. Le filtre se perd au milieu du couloir à l'aller comme au retour.
- Couloir : cap des murs à 1,5° et 1,7° de mon estime. Porte H12 : éventail (montants à 545 mm vers le cap 82° et 811 mm vers 144°), puis 1,3 m d'un trait au cap 108°.
- **Arrivée** : traversée de l'axe de la base vers l'est à 60 mm/s, vert de 1 à 223 mm, les deux de 226 à 258, rouge de 263 à 699 : frontière à u = 404,5 dans mon repère, pour une base à 405 sur le plan. Puis tour sur place au point P. Robot tourné vers la base : écho du pied de meuble à 559-564 mm (546 le matin).

### Ce que vaut la boucle (dépouillement de la session de revue, ses chiffres)

- Les deux tours du point P, comparés paroi par paroi : **le robot est revenu à 27 mm de son point de départ** (15 mm à l'ouest, 22 mm au sud).
- **Mes positions retenues : 18 mm d'erreur à l'arrivée**, 50 mm avant la correction du dernier tour. L'estime seule : 58 à 74 cm, soit 1,1 à 1,3 % des 54,8 m comptés.
- L'échelle du plan : sur les douze trajets propres de la boucle, la correction va contre le trajet de 2,4 % d'est en ouest et 2,8 % du nord au sud ; avec les trajets des jours d'avant, cela ferait un plan à 51,5 à 51,8 pixels par mètre plutôt que 53. Non tranché, comme la place du capteur de distance (le couloir, 84 cm sur le plan pour 645 mm lus, la mettrait à 97-114 mm du centre) : il manque la mesure à la règle.
- Sa conclusion : avec le cap juste, la façon de faire de cette séance (le filtre quand sa note est bonne, l'estime quand elle est mauvaise, les passages au capteur, le cap pris sur les murs) tient 5 cm sur 45 m et six pièces.

### Contacts et erreurs

Quatre contacts légers, tous sur des choses que ni le capteur de distance ni les capteurs optiques n'avaient annoncées à temps : le meuble bas de la pièce du bas à droite, l'arrêt de C38, l'objet nouveau de la pièce centrale (deux fois). Une chute du mode Safe. `plan_lidar/obstacles.json` : 22 entrées.

Mes erreurs : le coin de la cuisine annoncé sans l'avoir vérifié ; la brosse latérale oubliée au seuil ; le centrage lancé dans un espace ouvert d'un côté ; un outil de station qui pouvait rouler ; une surveillance du seuil fondée sur le chemin compté ; les corrections de cap du filtre écartées jusqu'au couloir.

**Non fait** : le vrai coin de la cuisine et son exploration en détail (proposés à l'utilisateur à 13 h 42, en attente de son accord) ; l'essai 4 devant un vrai mur ; les essais 6 et 7 de la session de revue ; la mesure à la règle.

**État à la fin** (13 h 43) : robot au point P devant sa base, pas dessus ; 1 175 mAh (57 %) ; cerveau en v14 ; seuil du capteur de distance à 30 cm.

---

## 61. Vers la cuisine par la nouvelle porte du mur sud (case H18) ; le seuil manqué au premier essai ; l'enregistreur coupé par une liaison morte (2026-11-15, 13 h 45 à … — séance en cours)

**La demande.** À ma proposition de 13 h 42 (retourner dans la cuisine, l'explorer en détail jusqu'au vrai coin du fond, puis revenir devant la base), l'utilisateur a répondu à 13 h 45 : « Go en passant par nouvelle Porte ouverte mais étroite car y'a un truc qui gêne en g18 ». J'ai lu : la porte du mur sud de la pièce de la base, qui donne sur le couloir (sur le plan, une ouverture de u = 435 à 477 vers v = 188, cases H17 et H18), restée fermée jusque-là ; quelque chose en G18 en réduit le passage.

**Les enregistrements** : `exploration36_20261115_134922` (13 h 49 à 14 h 23 min 18, arrêté seul, voir plus bas) et `exploration37_20261115_142437` (trois lignes : la carte a refusé l'enregistreur). Firmware v14, sans repères, brosse latérale demandée aux franchissements.

### 61.1 La nouvelle porte, aux capteurs (13 h 49 à 14 h 06)

Tour sur place au point P à 13 h 49 (passe « a ») : P gardé en (404,3 ; 101,0). Le plan ne montre pas la porte telle qu'elle est aujourd'hui (le battant y est dessiné à mi-course) : je l'ai donc approchée par regards du capteur de distance, robot à l'arrêt (`_passage1.txt` à `_passage10.txt`).

| Heure | Geste | Ce que les capteurs ont montré |
|---|---|---|
| 13 h 50 à 13 h 55 | P → (425 ; 140) → (432 ; 157), éventails vers le sud-est | une paroi à 31 cm au sud (le mur), qui finit par un angle vers u = 447 ; par les caps 315° et 322°, 95 cm de libre : l'ouverture |
| 13 h 55 | vers (452 ; 151) | arrêté par le capteur de distance à 288 mm d'une paroi qui regarde l'ouest (la chose de G18, ou le battant ouvert contre elle) |
| 13 h 56 | 49 cm au cap 300°, à 5 cm/s, jusqu'en (462,5 ; 174,0) | aucun contact ; regard à l'est : 49 mm lus, la paroi est contre le flanc du robot ; à l'ouest 414 mm ; au sud 0,8 à 1,36 m de libre |
| 14 h 02 | deux pas de 10 cm plein sud | est : 50 puis 56 mm (la paroi est droite et longe le robot sur 20 cm) ; ouest : 210 puis 531 mm |
| 14 h 04 | un pas de 15 cm : centre du robot dans l'encadrement | est 89 mm, ouest 498 mm : les deux montants |
| 14 h 05 | **erreur de ma part** : deux avances lancées après un regard à l'ouest, cap non remis au sud : le robot a roulé 21 cm vers l'ouest dans l'encadrement, puis s'est arrêté seul à 297 mm du montant | aucun contact ; du second point, est 261 mm, ouest 344 mm |
| 14 h 06 | cap au sud, 39 cm | robot au milieu du couloir |

Mesuré :
- **le passage libre** entre la paroi de l'est (la chose de G18, ou le battant qu'elle retient : je ne sais pas lequel) et ce qui dépasse à l'ouest fait 41 à 49 cm au plus étroit, selon la place du capteur sur le robot, pour un robot de 34 cm. Le robot est passé en longeant la paroi de l'est à moins d'un centimètre, sans que le pare-chocs touche. La ligne qui a marché : (449 ; 152) → (462,5 ; 174) au cap 300°, puis plein sud ; 5 cm plus à l'ouest aurait été mieux centré.
- **l'ouverture de la porte, d'un montant à l'autre** : 89 + 498 = 587 mm lus d'un point, 261 + 344 = 605 mm de l'autre, plus deux fois la distance du capteur au centre du robot. Le plan donne 42 pixels, soit 80 cm : le capteur serait alors à **10 cm** environ du centre, et non à 2,7 cm comme le supposent encore les outils (`carto.DX`). C'est la valeur que la session de revue avait avancée (note O) ; rien n'est changé dans les outils avant la mesure à la règle.
- le milieu de l'ouverture tombe 4 pixels (8 cm) plus à l'ouest dans mon estime que sur le plan.

### 61.2 Le couloir (14 h 06 à 14 h 10)

À 75 cm à l'est de la porte, les deux murs du couloir lus de côté : 184 mm au nord, 546 mm au sud ; 50 cm plus loin, 304 et 454 mm. Largeur : 730 à 758 mm lus plus deux fois la distance du capteur au centre, pour 92 cm sur le plan : de nouveau 8 à 10 cm pour cette distance. Le robot roulait 17 cm trop près du mur nord : mon estime était décalée de 16 cm vers le sud depuis la porte (cause non cherchée ; les regards de côté dans l'encadrement se sont faits par huit pivots de suite). Position reprise à la main sur ces murs, puis tour sur place en J20 : le filtre la corrige de 2 cm et de -1,4° (note 0,75).

### 61.3 La pièce centrale (14 h 10 à 14 h 15)

Par (611 ; 209), puis le détour au sud de l'objet mobile de 13 h 20 : aucun contact. Tour en G26 (note 0,75, correction de 8 cm vers le nord). Puis, sur la ligne suivie trois fois sans encombre plus tôt dans la journée, **un contact léger du pare-chocs gauche à 14 h 12 min 16**, après 17 cm : une chose étroite et sombre en F27, vers (691 ; 147), qui n'était pas là à 13 h. Ni le capteur de distance (qui lisait 1,69 m devant) ni les capteurs optiques (131 au plus, puis 15 au contact) ne l'ont vue ; une fois reculé de 10 cm, le capteur de distance la trouve à 175 mm quand le robot la vise (cap 70°) et ne la voit plus à 20° de part et d'autre : un pied de chaise ou de tabouret, sans doute. Contournée par l'est à 8 cm/s : (702 ; 158) → (706 ; 135) → (711 ; 113) → (720 ; 85), sans contact. Tour en D28 : note 0,86, correction de 8 cm vers l'ouest.

### 61.4 Devant la porte de la cuisine et premier essai du seuil (14 h 15 à 14 h 23)

En arrivant au point de départ de 13 h 02, (739 ; 62), au cap 64°, le pare-chocs droit s'est enfoncé en fin d'avance : sans doute le coin du montant nord, que le plan place à 4 mm du bord du robot en ce point, ou le tabouret que la photo de 12 h 55 montrait près de ce montant (non tranché). Recul de 8 cm : le robot est en (737,4 ; 65,6), face à l'ouverture (60 à 86 cm lus sur tous les caps de 64° à 300°).

**Le seuil, premier essai** (`_seuil1.txt`, 14 h 20 min 06) : avance de 850 mm au cap 335° (de biais à 25°), 150 mm/s, **brosse latérale à 40 sur 127**, suivie par un nouvel outil (`seuil2.py`, hors dépôt) réglé pour couper si le cap s'écartait de 15°.

| Chemin compté | Ce que le journal à 20 Hz montre |
|---|---|
| 0 à 600 mm | cap tenu à 0,5° près, roues à 40-250 mA |
| 609 à 636 mm | le capteur de vide avant gauche passe la baguette : 943 puis 3 266 (2 650 sur le parquet) |
| 666 mm | le capteur de vide gauche la passe à son tour (3 205) |
| 727 à 778 mm | la **roue gauche** arrive sur la baguette : 538, 445, 555 mA ; le robot pivote vers la gauche à 27-38° par seconde |
| 779 mm | mon outil demande l'arrêt : écart de cap de 16° |

Sur les 9 derniers centimètres le compteur de la roue gauche avance de 219 pas et celui de la droite de 197, alors qu'un pivot de 18° vers la gauche demande à la roue droite 70 mm de plus qu'à la gauche : la roue gauche a patiné de 8 cm environ contre la baguette, la droite poussait sur le parquet. Ni chute du mode Safe, ni roue levée, ni contact du pare-chocs.

Ce que j'en retiens :
- **mon outil a coupé trop tôt.** Le firmware, quand le cap s'écarte, donne plus de vitesse à la roue en retard et moins à l'autre (jusqu'à la moitié de la vitesse demandée, `mouv.ino`) : c'est justement ce qui aide la roue butée à monter, et c'est ce que l'utilisateur avait écrit à 13 h (« continuer quand ça monte »). À refaire avec une limite de 45°.
- à 13 h 02 la roue gauche avait rencontré la baguette après 47 cm ; cette fois après 73 cm, alors que mes deux points de départ ne diffèrent que de 3 cm d'est en ouest : mon repère de 13 h 02 (après les patinages) et celui de 14 h 20 (tour en D28) diffèrent donc de 22 cm le long de la ligne, sans que je sache lequel est juste. Centre du robot au moment où la roue gauche touche la baguette : (773 ; 82) dans le repère de 14 h 20, (762 ; 72) dans celui de 13 h 02.
- un calcul d'ordre de grandeur, le mien et non vérifié sur le robot : à 150 mm/s l'élan ne fournit pas le cinquième de l'énergie qu'il faut pour hisser une roue de 17 mm ; ce serait donc surtout l'adhérence des roues, une à la fois, qui fait passer, plus que la vitesse.

Recul de 34 cm le long de la même ligne pour refaire l'essai.

### 61.5 L'enregistreur coupé, et une faiblesse du firmware trouvée (14 h 23 à …)

À 14 h 23 min 18, pendant le dernier recul, l'enregistreur s'est arrêté : « liaison TCP perdue : connexion fermée par l'hôte distant ». Au même instant la réponse à un ordre HTTP s'est perdue (le recul, lui, s'est fait : 144 mm pour 150).

**Cause, lue à 14 h 40 dans le journal des réseaux de Windows** (heures et numéros d'événements seulement, aucun nom de réseau relevé) : à 14 h 23 min 17,7 un réseau du PC dont le nom ressemble à celui d'un VPN s'est déconnecté ; il était branché depuis 8 h 33, s'est rebranché à 14 h 29 min 55 et s'est recoupé à 14 h 33 min 50. La coupure vient donc du PC, ni de la carte ni du robot : les liaisons du PC vers la carte ont été réinitialisées à cet instant, et la carte n'en a rien su. Ceci remplace ce que j'avais d'abord supposé (un hoquet du Wi-Fi, noté dans l'en-tête de `exploration37` et `exploration38`).

Mais ensuite **la carte a refusé tout nouvel enregistreur** : « Un client est déjà connecté à la console » (14 h 24 min 37, puis à chaque essai). `/api/state` le confirme : tampon de la console plein (23 955 octets), compteur « perdus » à 1,3 million et qui monte. Aucun programme du PC ne tient de liaison vers le port 23. Lecture du code (`tcpTick`, `consVider`) : depuis la v11 la carte n'écrit vers la console que ce que la liaison accepte à l'instant ; une liaison morte dont l'autre bout a disparu sans le dire n'accepte plus rien, ne rend pas d'erreur non plus, et reste comptée comme un client présent tant que la pile TCP de la carte n'a pas renoncé à ses réémissions (d'après ce que je sais de cette pile, sans l'avoir vérifié dans son code : une douzaine, de plus en plus espacées, soit de 7 à 30 minutes). Pendant ce temps : pas de journal à 20 Hz, donc pas de pilotage (`pilote.py` refuse de rouler sans lignes fraîches, et c'est bien ainsi).

Deux conséquences à retenir :
- quand la carte s'aperçoit enfin que ce client a disparu, elle arrête les roues et met fin au mouvement ou au tour sur place en cours, à un instant quelconque ;
- **correction proposée pour un firmware v15** (rien n'est changé sans l'accord de l'utilisateur) : fermer le client de la console quand il n'a rien accepté depuis quelques secondes.

Le robot n'a pas bougé pendant l'attente : mode Safe, à l'arrêt devant le seuil, côté pièce centrale.
