# G — Radar à ultrasons : HC-SR04 sur servo SG90 (modules du kit ELEGOO)

Rédigé le 2026-11-09 (nuit). **État : code écrit et compilé (firmware `roomba694_wifi` v3, fichier `radar.ino`), rien n'est câblé ni testé sur le matériel.** Cette note dit ce qu'on obtient, comment brancher les deux modules sans rien abîmer, comment les fixer sur le robot et comment tester pas à pas. Rien ne doit être branché avant qu'on ait repassé le plan ensemble.

## En deux mots

- Le HC-SR04 mesure la distance de l'obstacle devant lui (2 cm à 4 m, cône d'environ 15°) ; monté sur le servo SG90, il balaie de −80° à +80° et dessine une **carte polaire des distances** sur la page web : un « radar » grossier en attendant le LiDAR (note F).
- Le firmware s'en sert aussi comme **garde-fou** : si un obstacle est vu devant à moins du seuil (30 cm par défaut), les roues sont arrêtées quand le robot avance et les ordres d'avance sont refusés ; reculer et tourner restent possibles. Le pare-chocs du robot reste la vraie sécurité.
- Les deux modules marchent en 5 V : ils se branchent sur la broche **VIN** de la carte (le 5 V de l'USB tant que la carte est alimentée par USB ; plus tard le rail 5 V de l'abaisseur de la note F). L'Echo du HC-SR04 sort du 5 V : il passe par un **diviseur 1 kΩ / 2 kΩ** avant d'entrer dans l'ESP32 (qui ne supporte que 3,3 V).
- Broches choisies (révision du 2026-11-09, matin) : servo sur **D18**, Trig sur **D19**, Echo (après diviseur) sur **D23**, toutes du côté 3V3 de la carte, celui qui a une colonne de trous libres. La première version (D27 / D32 / D34, côté VIN) est abandonnée : la photo de la plaque montre que la colonne VIN est collée au bord, sans aucun trou libre, donc ni VIN ni ces broches ne sont accessibles. Conséquence : le 5 V des modules ne peut pas venir de la broche VIN ; il viendra d'une source externe amenée sur une bande libre de la plaque (second port de la batterie USB en attendant, puis la sortie 5 V de l'abaisseur de la note F, idéalement la version à prise USB qui alimente aussi la carte par son câble).

## 1. Les deux modules

| Module | Alimentation | Courant | Signal | À savoir |
|---|---|---|---|---|
| HC-SR04 (bleu, deux « yeux », quartz 16,9344 MHz) | 5 V (4,5 à 5,5 V ; en 3,3 V il marche mal ou pas) | 15 mA | **Trig** : impulsion de 10 µs envoyée par l'ESP32 (3,3 V suffisent). **Echo** : impulsion de **5 V** dont la durée = temps aller-retour du son | distance = durée × 0,1715 mm/µs (son à 343 m/s). Portée 2 cm à 4 m, cône ~15°, une mesure toutes les 60 ms au plus. Sans écho, certains exemplaires tiennent Echo haut jusqu'à 200 ms |
| SG90 (micro-servo, bras en plastique) | 4,8 à 6 V | ~10 mA au repos, 100 à 250 mA en mouvement, jusqu'à 650 mA bloqué | impulsion de 500 à 2500 µs toutes les 20 ms (50 Hz) : 1500 µs = milieu, ±10 µs par degré environ | ~0,1 s pour 60°, course 180°. Fil brun = masse, rouge = 5 V, orange = signal |

Les deux sont des modules « 5 V Arduino » ; l'ESP32 est une carte 3,3 V. Les deux règles qui en découlent : **le 5 V des modules vient de VIN, jamais de 3V3** (le régulateur 3,3 V de la carte ne tiendrait pas le servo et le HC-SR04 n'aime pas 3,3 V) ; **l'Echo ne touche jamais directement une broche de l'ESP32**.

## 2. Câblage

> **Révision du 2026-11-09 (matin).** Les sections 2.1 et 2.2 et les deux schémas `images/plan_radar_ultrason_plaque*.png` ont été écrits en supposant une rangée de trous libres du côté VIN de la carte. La photo de la plaque sur le robot montre qu'il n'y en a pas : la carte occupe la plaque jusqu'au bord de ce côté. Ce qui reste vrai : les deux modules, le diviseur 1 kΩ / 2 kΩ sur l'Echo, le condensateur, les règles. Ce qui change : les signaux vont côté 3V3 (servo **D18**, Trig **D19**, Echo **D23**, dans la colonne de trous libres déjà utilisée par le robot et le gyroscope), et le 5 V vient d'une source externe posée sur une bande libre de la plaque. Les schémas seront refaits une fois la source 5 V choisie.

### 2.1 Vue d'ensemble

| Fil | De | Vers | Remarque |
|---|---|---|---|
| 5 V | broche **VIN** de la carte | bande **rouge du bas** de la plaque | VIN porte le 5 V de l'USB (à travers une diode : 4,6 à 5 V lus, c'est normal) ; plus tard, le rail 5 V de l'abaisseur arrive ici |
| masse | broche **GND** (côté VIN) | bande **bleue du bas** | masse commune avec le reste du montage (la carte relie ses deux GND) |
| HC-SR04 Vcc | bande rouge du bas | | |
| HC-SR04 Gnd | bande bleue du bas | | |
| HC-SR04 Trig | trou libre de **D32** | | sortie de l'ESP32, 3,3 V, suffisant |
| HC-SR04 Echo | **1 kΩ** | nœud du diviseur | le nœud va au trou libre de **D34** |
| nœud du diviseur | **2 kΩ** | bande bleue du bas | 5 V × 2 / (1 + 2) = 3,33 V sur D34 |
| SG90 brun | bande bleue du bas | | masse |
| SG90 rouge | bande rouge du bas | | 5 V |
| SG90 orange | trou libre de **D27** | | signal 50 Hz |
| condensateur 100 à 470 µF | bande rouge du bas (+, patte longue) | bande bleue du bas (−, patte courte, bande marquée) | amortit les appels de courant du servo ; près des fils du servo |

Pourquoi ces broches : D27 et D32 sont des sorties sans rôle au démarrage ; D34 est une **entrée seule** (parfaite pour l'Echo, et le 2 kΩ vers la masse la tient à 0 V au repos, puisqu'elle n'a pas de résistance de rappel interne). RX2/TX2/D4/D21/D22 restent au robot et au gyroscope, D25/D26 sont réservées au LiDAR (UART1, note F).

Résistances : 1 kΩ = brun-noir-rouge, 2 kΩ = rouge-noir-rouge (le kit en a). À défaut de 2 kΩ : 2,2 kΩ (rouge-rouge-rouge, donne 3,44 V, acceptable) ou deux 1 kΩ en série. La règle : 5 V × R2 / (R1 + R2) entre 2,5 et 3,4 V.

### 2.2 Sur la plaque d'essai (plan de la note README, carte à droite, rangées 11 à 25)

Schéma trou par trou, dans l'orientation de la photo de la plaque : [`images/plan_radar_ultrason_plaque.png`](../images/plan_radar_ultrason_plaque.png) ; version simplifiée en quatre blocs (A le 5 V et la masse, B le servo, C le capteur de distance, D les deux résistances), avec les mots employés avec l'utilisateur : [`images/plan_radar_ultrason_plaque_simple.png`](../images/plan_radar_ultrason_plaque_simple.png). Sur sa carte, la patte 5 V s'appelle **VIN** (pas de patte « 5V »). Brochage complet (robot, gyroscope, radar) : [`code/README.md`](../code/README.md), section « Brochage complet ».

La carte occupe les colonnes b à i ; la rangée libre **au-dessus** (colonne a) sert déjà au robot et au gyroscope. La rangée libre **au-dessous** (colonne j) est intacte : c'est elle qu'on utilise ici, avec **les deux bandes du bas** (rouge = 5 V, bleue = masse), libres elles aussi. Rangées des broches du bas, à lire sur la sérigraphie avant de brancher : VIN 11, GND 12, D13 13, D12 14, D14 15, **D27 16**, D26 17, D25 18, D33 19, **D32 20**, D35 21, **D34 22**, VN 23, VP 24, EN 25.

| # | De | Vers | Quoi |
|---|---|---|---|
| 1 | trou libre sous **VIN** (r11, colonne j) | bande **rouge du bas**, trou vers r11 | fil |
| 2 | trou libre sous **GND** (r12, colonne j) | bande **bleue du bas**, trou vers r12 | fil |
| 3 | condensateur 100 à 470 µF : patte longue (+) dans la bande rouge du bas, patte courte (−) dans la bande bleue du bas, vers r14 | | composant |
| 4 | servo : connecteur femelle 3 fils → trois fils mâle-mâle : **brun** → bande bleue du bas (vers r16), **rouge** → bande rouge du bas (vers r16), **orange** → trou libre sous **D27** (r16, colonne j) | | 3 fils |
| 5 | HC-SR04 **Vcc** (fil femelle-mâle depuis le capteur) | bande rouge du bas, trou vers r20 | fil |
| 6 | HC-SR04 **Gnd** | bande bleue du bas, trou vers r20 | fil |
| 7 | HC-SR04 **Trig** | trou libre sous **D32** (r20, colonne j) | fil |
| 8 | HC-SR04 **Echo** | **r27, colonne f** (bandeau du bas, à gauche de la carte) | fil |
| 9 | r27 | r30 | résistance **1 kΩ** debout, colonne g |
| 10 | r30 | r33 | résistance **2 kΩ** debout, colonne g |
| 11 | r33 (colonne h) | bande bleue du bas, trou vers r28 | fil (masse du diviseur) |
| 12 | r30 (colonne h) | trou libre sous **D34** (r22, colonne j) | fil : c'est le point à 3,3 V |

Les bandes sont probablement coupées vers le milieu de la plaque (rangées 30-33) : toutes les connexions aux bandes du bas ci-dessus sont dans le segment de droite (rangées ≤ 28), donc du même côté. Vérifier au multimètre, carte sous tension et modules **pas encore branchés** : entre bande rouge du bas et bande bleue du bas vers r20, on doit lire 4,6 à 5,0 V ; entre bande rouge du **haut** (3,3 V) et bande rouge du **bas** (5 V), rien ne doit être relié. Un bout de ruban « 5 V » sur la bande du bas évite la confusion.

### 2.3 Les règles

1. Tout se câble **carte hors tension** (USB débranché) et prise du robot débranchée.
2. Le 5 V des modules vient de **VIN**. Jamais de 3V3, jamais directement des trous 1-2 du robot (14 à 21 V : les modules grilleraient ; l'abaisseur de la note F est fait pour ça).
3. L'Echo passe **toujours** par le diviseur. Vérifier au multimètre, capteur branché et carte sous tension mais fil 12 pas encore mis : entre r30 et la masse, 0 V au repos (l'Echo est bas quand le capteur ne mesure pas). Puis mettre le fil 12.
4. Ne pas tourner le bras du servo à la main quand il est alimenté ; à l'arrêt (mode « arrêt » du firmware), il est relâché et on peut le bouger.
5. Si la carte redémarre avec la raison « **baisse de tension** » quand le servo bouge (pied de page, touche `i`), l'alimentation USB faiblit : condensateur plus gros, câble USB plus court ou autre port, et à terme l'abaisseur de la note F. Sur le port USB d'un PC (500 mA), ESP32 Wi-Fi + servo en mouvement passent en général, mais c'est juste ; sur la batterie portable, pas de problème.
6. Toujours finir une session robot par `s` puis `x` ; le radar peut rester en marche, il ne touche pas au robot.

Budget quand tout viendra du robot (note F, abaisseur 5 V) : ESP32 Wi-Fi 150 mA + servo 100 à 250 mA en mouvement + capteur 15 mA, soit 270 à 420 mA sous 5 V, environ 110 à 170 mA côté robot : sous les 200 mA continus, mais **pas en même temps que le LiDAR** (le radar est l'étape intermédiaire, le LiDAR le remplacera).

## 3. Fixation sur le robot

- Le servo se fixe **sur le dessus du robot, à l'avant**, axe du bras **vertical**, avec du ruban double face épais ou un collier ; le bras (palonnier en croix ou simple) porte le HC-SR04 par un petit support : morceau de carte plastique ou de carton rigide collé au bras, capteur fixé dessus par deux élastiques ou du ruban, **les deux « yeux » tournés vers l'avant, à l'horizontale**.
- Hauteur : le dessus du Roomba est à ~9 cm du sol ; avec un cône de ±7,5°, le bord bas du faisceau touche le sol à ~70 cm devant. Pour éviter les échos du sol, incliner très légèrement le capteur **vers le haut** (2 à 5°, une cale de carton sous l'arrière) ; si la carte montre des points fixes vers 60-90 cm en terrain dégagé, c'est le sol.
- Centre : avant de fixer le capteur sur le bras, mettre le servo en mode « fixe devant » (il se place au centre) **puis** fixer le bras pour que le capteur regarde l'avant du robot. Si, en mode fixe à +45°, le capteur part vers la **droite**, cocher « servo inversé » sur la page.
- Fils : quatre fils femelle-mâle pour le capteur et trois pour le servo, avec du mou pour ±80° de rotation, scotchés sur le capot jusqu'à la plaque. Le pare-chocs doit rester libre.
- Le servo n'a rien à faire sous le capteur de vide ni devant le pare-chocs : il ne gêne pas la base de charge si l'ensemble reste dans le gabarit du robot.

## 4. Ce que fait le firmware v3 (`radar.ino`)

- **Trois modes** : *arrêt* (servo recentré puis relâché, aucune mesure), *fixe* (le capteur regarde dans une direction choisie, 0° = devant, et mesure 10 fois par seconde), *balayage* (de −amplitude à +amplitude par pas réglable, aller puis retour ; ±60° par pas de 10° ≈ 2 s par passage). La tâche tourne sur le second cœur, comme le gyroscope : rien ne bloque la liaison robot.
- **Carte polaire** : une case tous les 5° de −80° à +80° ; chaque case garde la dernière distance (ou « rien à portée ») et sa date. La page web la dessine (points qui pâlissent avec l'âge, rouge sous le seuil, gris au bord = rien à portée, trait bleu = direction actuelle du capteur, arc rouge pointillé = seuil). **Toucher le dessin** met le mode fixe dans la direction touchée.
- **Distance devant** : médiane des trois dernières mesures du secteur ±15° (une mesure parasite isolée n'arrête pas le robot).
- **Arrêt auto** (case « arrêt auto », active par défaut) : distance devant sous le seuil et vieille de moins de 1,5 s → roues arrêtées si le robot avance, ordre `8` refusé avec un message dans la console ; `2`, `4`, `6` passent toujours. **Devant en marche avant** (actif par défaut) : en balayage, dès que le robot avance, le capteur se met devant et mesure à 10 Hz, puis reprend le balayage à l'arrêt. Sans cela, le secteur avant ne serait revu qu'une fois par passage (~2 s, soit 30 cm à 150 mm/s).
- **Réglages** conservés en mémoire flash : seuil (10 à 150 cm), arrêt auto, devant en marche avant, pas (5 à 45°), amplitude (20 à 80°), mesures par direction (1 à 3, médiane), sens du servo.
- **Console** : `r` fait tourner arrêt → fixe devant → balayage ; `u` affiche l'état, les compteurs (mesures, sans écho, sans réaction, passages, arrêts auto, avances refusées) et la carte en texte. La console signale le premier écho reçu (« capteur détecté »), un capteur qui ne réagit plus (Echo jamais haut : fil ou alimentation), chaque arrêt auto.
- **API** : `/api/radar` renvoie l'état et la carte (`points` = [angle, mm, âge ms]) ; paramètres : `mode=off|fixe|balayage`, `angle=-80..80`, `seuil=`, `securite=0|1`, `auto=0|1`, `pas=`, `amplitude=`, `ech=1..3`, `inv=0|1`, `effacer=1`. `/api/state` contient un résumé `radar` (mode, distance devant en mm, âge). Le CSV (touche `j`) a une colonne `us_mm` de plus (−1 inconnue, 0 rien à portée).
- **PC** : `monitor_wifi.py` enregistre `radar_mode` et `us_mm` ; `radar_capture.py` enregistre chaque mesure avec les encodeurs et le cap du moment (CSV) et dessine la dernière carte en SVG (ouvrable dans un navigateur), sans rien à installer : `python roomba694_recherche/code/outils/radar_capture.py 192.168.18.25 120 0.5 roomba694_recherche/mesures`.

Limites à garder en tête : une seule mesure à la fois et un faisceau large (un obstacle à 60° du capteur est vu « dans l'axe » s'il est le plus proche du cône) ; les tissus, rideaux et coussins renvoient peu ; une surface très oblique renvoie le son ailleurs (« rien à portée » alors qu'il y a un mur) ; les pieds de chaise et les plinthes sont sous le faisceau. C'est un garde-fou et une première carte, pas une cartographie.

## 5. Plan de test, dans l'ordre

Chaque étape se fait quand la précédente est bonne ; je demande confirmation avant tout ce qui fait bouger le robot.

1. **Mise à jour du firmware** sans rien de câblé : page `/update` ou `curl -u admin:roomba694 -F "firmware=@…/roomba694_wifi.ino.bin" http://192.168.18.25/update`. Attendu : la page affiche la carte « Radar à ultrasons », `i` dit « v3 », `u` dit « mode arrêt ». Rien ne change pour le robot.
2. **Câblage** (section 2.2), carte hors tension, prise du robot débranchée, puis les deux mesures au multimètre de la section 2.3 (5 V sur la bande du bas ; 0 V sur r30 au repos).
3. **Servo seul** : carte sous tension (USB), capteur pas encore fixé au bras. Au démarrage le servo se centre une fois puis se relâche (signe de vie). Page : « Fixe devant » → il tient le centre ; toucher le dessin à gauche (+45°) → il doit tourner vers la **gauche** du robot (vu du dessus, sens anti-horaire) ; sinon cocher « servo inversé ». « Arrêt » → recentré puis relâché. Raison du dernier redémarrage toujours « mise à jour » ou « mise sous tension » : si « baisse de tension » apparaît, voir règle 5.
4. **Capteur seul**, mode « Fixe devant », un livre à 20, 50 et 100 cm devant les yeux (mètre ruban) : la case « Devant » doit suivre à ±2 cm ; la console a dit « capteur détecté ». Sans livre, dans une pièce dégagée : la distance du mur ou « rien < 4 m ».
5. **Balayage** sur la table, capteur fixé au bras : la carte se remplit en 2 à 4 s ; placer un objet à 50 cm à gauche puis à droite et vérifier qu'il apparaît du bon côté. Essayer pas 5° / amplitude 80 pour une carte plus fine, et `ech` 3 si des points isolés apparaissent.
6. **Sur le robot, à l'arrêt** (plaque et modules fixés, prise rebranchée, robot réveillé, `s`) : balayage, carte de la pièce depuis la position du robot ; `u` pour la version texte.
7. **Arrêt auto** (avec votre accord, robot au sol, espace dégagé, vitesse 60 mm/s) : `f`, radar en balayage, un carton debout à 1 m devant ; avancer avec la flèche : le robot doit s'arrêter seul à ~30 cm du carton, la console dit « obstacle à 30 cm devant, roues arrêtées » ; la flèche avant est ensuite refusée, reculer est possible. Puis le même test en mode « Fixe devant ».
8. **Mesure contre les encodeurs** (plus tard) : CSV actif (`j`), mode fixe devant, avancer vers un mur de 150 cm à 40 cm : la colonne `us_mm` doit diminuer d'autant que les encodeurs avancent (0,4446 mm par pas) ; c'est un bon contrôle de l'odométrie à venir.

## 6. Suite envisagée

- Odométrie (x, y, cap) dans le firmware : permettra à `radar_capture.py` de replacer les points dans la pièce et de dessiner une carte au fil des déplacements.
- Un mode « exploration » prudent (avancer, s'arrêter devant un obstacle, balayer, tourner vers la plus grande ouverture), à n'écrire qu'après les tests 1 à 7 et avec un bouton d'arrêt et une durée limitée.
- Le LiDAR (note F) remplacera le radar sur le même rail 5 V ; le servo et le capteur resteront utiles ailleurs.

## Sources

Fiches techniques classiques (liens stables, non revérifiés ce jour) : HC-SR04 https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf · SG90 http://www.ee.ic.ac.uk/pcheung/teaching/DE1_EE/stores/sg90_datasheet.pdf · PWM LEDC de l'ESP32 (cœur Arduino 3.x, `ledcAttach` / `ledcWrite`) https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html · interruptions GPIO https://docs.espressif.com/projects/arduino-esp32/en/latest/api/gpio.html. Vitesse du son 343 m/s à 20 °C. Mesures et plan de plaque : `code/README.md`, `images/plan_sur_photo_plaque.jpg`, `images/plaque_esp32_placee_rangees.jpg` (rangée libre sous les broches du bas visible sur les deux photos).
