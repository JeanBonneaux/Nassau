# Prompt pour la session Claude Code locale — test ESP32 ↔ Roomba 694

À coller tel quel au démarrage d'une session Claude Code sur l'ordinateur relié à l'ESP32 (clone local du dépôt JeanBonneaux/Nassau).

---

# Test de la liaison série ESP32 ↔ Roomba 694 (sketch roomba694_test1)

Contexte : une session cloud a produit une recherche et un premier sketch dans ce dépôt, sur la branche `claude/eager-ride-crj3f0`, dossier `roomba694_recherche/`. Je suis débutant en électronique : explique chaque étape, demande confirmation avant toute action physique sur le robot, et ne fais rien qui puisse endommager la carte ou le robot.

## 0. Récupérer le travail
- `git fetch origin && git checkout claude/eager-ride-crj3f0 && git pull`
- Lire `roomba694_recherche/code/README.md` (câblage, mesures) et `roomba694_recherche/code/roomba694_test1/roomba694_test1.ino` (le sketch). Le rapport complet est dans `roomba694_recherche/rapport.md` (section 1 pour le port série).

## Faits établis (mesurés au multimètre le 2026-11-08 sur mon robot)
- Prise série Mini-DIN 7 broches sous le capot ; brochage vérifié : 1-2 = + batterie (14,66 V hors base, jusqu'à ~21 V sur la base), 3 = RXD (entrée robot, rappel 5 V), 4 = TXD (sortie robot, **3,3 V**), 5 = BRC (réveil, rappel 5 V), 6-7 = masse.
- Carte : ESP32 DevKit 30 broches, module ESP32-WROOM-32 (pas de PSRAM), USB-C, puce USB-série CP2102. Sérigraphie : GPIO16 = RX2, GPIO17 = TX2, GPIO4 = D4.
- Le sketch n'a jamais été compilé avec la vraie chaîne ESP32 (seulement vérifié contre une maquette) : s'il y a une erreur de compilation, corrige-la a minima et explique.

## 1. Chaîne de compilation
- Vérifier si l'IDE Arduino (2.x) ou `arduino-cli` est installé, et si le paquet de cartes « esp32 » (Espressif) est présent. **Demander avant d'installer quoi que ce soit.**
- Avec arduino-cli : `arduino-cli core update-index`, `arduino-cli core install esp32:esp32`, puis compiler avec le FQBN `esp32:esp32:esp32` (carte « ESP32 Dev Module »).
- Port série : CP2102 → Windows `COMx` (pilote Silicon Labs CP210x si rien n'apparaît), macOS `/dev/cu.usbserial-*` ou `/dev/cu.SLAB_USBtoUART`, Linux `/dev/ttyUSB0` (ajouter l'utilisateur au groupe `dialout` en cas de « permission denied »). `arduino-cli board list` pour le trouver.
- Téléverser (`arduino-cli upload -p PORT --fqbn esp32:esp32:esp32 roomba694_recherche/code/roomba694_test1`). Si ça reste sur « Connecting... », maintenir le bouton BOOT de la carte pendant la connexion.

## 2. Test à vide (ESP32 seul, rien de branché au robot)
- Ouvrir le moniteur série à 115200 bauds (`arduino-cli monitor -p PORT -c baudrate=115200` ou le moniteur de l'IDE). Appuyer sur EN (reset) : l'aide du sketch doit s'afficher. Taper `?` puis Entrée. Si rien ne s'affiche : vérifier le port et la vitesse.

## 3. Câblage (ESP32 DÉBRANCHÉ de l'USB pendant qu'on câble ; robot au sol, hors de sa base)
Fils Dupont : côté mâle enfoncé dans la prise du robot, côté femelle sur les broches de la carte.

| Robot (trou) | Carte ESP32 (sérigraphie) |
|---|---|
| 4 (TXD) | RX2 |
| 3 (RXD) | TX2 |
| 5 (BRC) | D4 |
| 6 ou 7 (GND) | GND (celui à côté de 3V3) |
| 1 et 2 | **RIEN** — ne jamais relier pour ce test |

Le croisement est normal : la sortie du robot va sur l'entrée de l'ESP32, et inversement. Repérage des trous : la rangée de trois trous est 5-6-7 (6 au milieu) ; dans l'axe du détrompeur rectangulaire : 3 (à côté du 5) et 4 (à côté du 7) ; les deux restants : 1 (à côté du 3) et 2 (à côté du 4). Photos annotées : `roomba694_recherche/images/acces_694_minidin_brochage_annote.jpg` (prise) et `roomba694_recherche/images/cablage_esp32_devkit30_test1.jpg` (carte). Me faire relire le câblage (je peux envoyer une photo) avant de rebrancher l'USB.

## 4. Validation de la liaison
- Rebrancher l'USB, ouvrir le moniteur. Séquence : `w` (réveil), `s` (Start → Passive), `b` (batterie).
- Attendu : « Tension batterie : ~14660 mV » (à quelques centaines de mV près). Si « Pas de réponse » : appuyer sur le bouton CLEAN du robot, attendre 2 s, refaire `s` puis `b`. Si le robot part nettoyer : `s` puis `f` l'arrêtent, puis `s`. Si toujours rien : vérifier que RX2 et TX2 ne sont pas inversés, puis me demander avant toute autre idée.
- Ensuite `e` (capteurs), `f` (Safe), `m` (3 notes), `l` (LEDs), `b` à nouveau.
- Déplacements (`8`, `2`, `4`, `6`, espace = stop) : **seulement après mon accord explicite**, espace dégagé, robot au sol. Chaque ordre s'arrête seul après 1,5 s.
- Toujours finir par `s` puis `x` (en Safe/Full le robot ne se recharge pas et ne dort jamais), puis débrancher l'USB.

## 5. Consigner et pousser
- Écrire `roomba694_recherche/code/journal_tests.md` : date, OS, versions (IDE ou arduino-cli, paquet esp32), port, résultat de chaque étape, sortie série copiée telle quelle (surtout les valeurs de `b` et `e`), problèmes rencontrés et corrections faites au sketch.
- Commit et push sur la même branche `claude/eager-ride-crj3f0`. Ne rien modifier hors de `roomba694_recherche/`.

## Règles
- Ne jamais relier les broches 1-2 du robot, ni VIN/3V3/5V de la carte, dans ce test.
- Pas de mode Full (opcode 132), pas de vitesse au-delà de 150 mm/s sans mon accord.
- Demander avant d'installer un logiciel, avant toute action qui fait bouger le robot, et dès qu'une mesure ne correspond pas à l'attendu.
- Répondre en français, de façon concise, en expliquant chaque étape.
