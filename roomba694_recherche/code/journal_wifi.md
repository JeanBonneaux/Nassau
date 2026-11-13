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
