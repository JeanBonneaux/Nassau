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
