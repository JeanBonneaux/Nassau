# Journal des tests — `roomba694_wifi` (console et page web par Wi-Fi, gyroscope GY-521, mises à jour sans câble)

Date : 2026-11-08 (soir), à la suite de [journal_tests.md](journal_tests.md). Même PC (Windows 11 Pro 10.0.26200), même outillage (arduino-cli 1.5.1, paquet `esp32:esp32` 3.3.7, FQBN `esp32:esp32:esp32`, port COM4, pont CP2102), même robot (Roomba 694) et même carte (ESP32 DevKit 30 broches).

## Résumé

- Le firmware Wi-Fi compile, se téléverse et fonctionne : point d'accès « Roomba694 » (192.168.4.1), page web, console TCP, lecture périodique des capteurs, gyroscope MPU-6050 détecté et lu à 100 Hz, robot commandé et interrogé à travers les résistances de 1 kΩ.
- Première version (v1) testée par USB puis par le téléphone : la page s'affiche, mais l'enregistrement du réseau de la maison a échoué (page protégée par un identifiant non communiqué, puis redémarrage de la carte). Une version 2 corrige cela et refait l'interface (voir § 6).
- Trois comportements du 694 mesurés ce soir : octet parasite `B0` quelques secondes après un réveil par BRC (lecture fausse une fois : température −80 °C, puis état de charge 176) ; réponse à la lecture groupée (opcode 149, 22 paquets) correcte mais lente, au-delà des 200 ms d'attente d'une lecture simple ; rendormissement du robot malgré l'anti-veille par BRC (à creuser).
- Le robot n'a pas bougé de la soirée (câble USB vers le PC branché) : aucun test de déplacement par la page web pour l'instant.

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

(à compléter : tests depuis le téléphone, réseau de la maison, console TCP et mise à jour sans câble depuis le PC, gyroscope en rotation)

## 8. Problèmes rencontrés et corrections

| Problème | Cause | Correction |
|---|---|---|
| PC sans COM4, périphérique USB en erreur | câble USB mal enfoncé (court-circuit exclu : LED allumées, rien de chaud) | rebranchement |
| Avertissements `-Wvolatile` | `imu.samples++` sur un champ `volatile` | `imu.samples = imu.samples + 1` |
| Température −80 °C, état de charge 176 | octet parasite `0xB0` émis par le robot quelques secondes après un réveil par BRC | relire ; lectures périodiques filtrées (tension, température, état de charge, mode) ; préférer le bouton CLEAN |
| Lecture groupée 149 « sans réponse » en lecture périodique | non élucidé : la même requête envoyée à la main (`q`) obtient les 38 octets en 15 ms, la requête périodique n'en reçoit que 37 | réponse ramassée sans bloquer (délai 600 ms), repli automatique sur la lecture paquet par paquet (un paquet par passage de la boucle), touche `q` de diagnostic |
| Page /wifi inutilisable depuis le téléphone | identifiant non communiqué, redémarrage de la carte, téléphone quittant le réseau sans internet | plus d'identifiant sur /wifi, connexion sans redémarrage, liste des réseaux, état et cause d'échec affichés, conseils sur la page |
| Inondation « Roues arrêtées. » | origine non identifiée (touche stop en rafale ?) | arrêt et message limités à une fois par seconde si déjà arrêté ; octets non imprimables ignorés ; « Touche inconnue » limitée |
| Prototypes non générés pour `web.ino` ; `'asyncfunction' does not name a type` | limites de l'outil Arduino face au second `.ino` et au JavaScript des pages | prototypes explicites ; HTML déplacé dans `pages.h` |
| Robot rendormi malgré l'anti-veille BRC | non élucidé (BRC inefficace sur ce 694 ? touche `x`/`o` envoyée depuis la page ?) | réveil par `w` puis `s` fonctionne ; à instrumenter plus tard |

## 9. Rappel de fin de session

Toujours finir par `s` puis `x` (console série, console TCP ou page web). Ne jamais brancher l'USB du PC et une autre alimentation en même temps. Ne pas utiliser les flèches de la page tant que le câble USB relie la carte au PC.
