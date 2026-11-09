# G — Radar à ultrasons : HC-SR04 sur servo SG90 (modules du kit ELEGOO)

Rédigé le 2026-11-09 (nuit), câblage refait le 2026-11-09 (après-midi) sur la photo réelle de la plaque. **État : code écrit, relu, corrigé et compilé (firmware `roomba694_wifi` v3, fichier `radar.ino`) ; rien n'est encore téléversé, câblé ni testé sur le matériel.** Cette note dit ce qu'on obtient, comment brancher les deux modules sans rien abîmer, comment les fixer sur le robot et comment tester pas à pas. Mots employés avec l'utilisateur : **le cerveau** = la carte ESP32, **le capteur de distance** = le HC-SR04, **le servo** = le SG90, **le gyroscope** = le GY-521.

## En deux mots

- Le HC-SR04 mesure la distance de l'obstacle devant lui (2 cm à 4 m, cône d'environ 15°) ; monté sur le servo SG90, il balaie de −80° à +80° et dessine une **carte polaire des distances** sur la page web : un « radar » grossier en attendant le LiDAR (note F).
- Le firmware s'en sert aussi comme **garde-fou** : si un obstacle est vu devant à moins du seuil (30 cm par défaut), les roues sont arrêtées quand le robot avance et les ordres d'avance sont refusés ; reculer et tourner restent possibles. Le pare-chocs du robot reste la vraie sécurité.
- Les deux modules marchent en 5 V. Décision de l'utilisateur du 2026-11-09 : ce 5 V est pris sur la patte **VIN** du cerveau (environ 4,7 V quand le cerveau est alimenté par sa prise USB : le 5 V de l'USB moins la diode de la carte), par un fil qu'il pose lui-même jusqu'à la **ligne rouge libre du côté VIN** de la plaque. Plus tard, l'abaisseur 5 V de la note F prendra le relais (branchement à valider ensemble : jamais deux sources 5 V en même temps sur cette ligne). L'Echo du capteur de distance sort presque 5 V : il passe par **deux résistances (1 kΩ et 2 kΩ)** qui le ramènent à environ 3,1 V avant d'entrer dans le cerveau, qui ne supporte que 3,3 V.
- Broches : servo sur **D18**, Trig sur **D19**, Echo (après les résistances) sur **D23**, toutes du côté 3V3 du cerveau, le seul qui a un trou libre à côté de chaque patte. La première version (D27 / D32 / D34, côté VIN) est abandonnée : de ce côté le cerveau va jusqu'au bord de la zone de trous.

## 1. Les deux modules

| Module | Alimentation | Courant | Signal | À savoir |
|---|---|---|---|---|
| HC-SR04 (bleu, deux « yeux », quartz 16,9344 MHz) | 5 V (4,5 à 5,5 V ; en 3,3 V il marche mal ou pas) | 15 mA | **Trig** : impulsion de 10 µs envoyée par l'ESP32 (3,3 V suffisent). **Echo** : impulsion de **5 V** dont la durée = temps aller-retour du son | distance = durée × 0,1715 mm/µs (son à 343 m/s). Portée 2 cm à 4 m, cône ~15°, une mesure toutes les 60 ms au plus. Sans écho, certains exemplaires tiennent Echo haut jusqu'à 200 ms |
| SG90 (micro-servo, bras en plastique) | 4,8 à 6 V | ~10 mA au repos, 100 à 250 mA en mouvement, jusqu'à 650 mA bloqué | impulsion de 500 à 2500 µs toutes les 20 ms (50 Hz) : 1500 µs = milieu, ±10 µs par degré environ | ~0,1 s pour 60°, course 180°. Fil brun = masse, rouge = 5 V, orange = signal |

Les deux sont des modules « 5 V Arduino » ; l'ESP32 est une carte 3,3 V. Les deux règles qui en découlent : **le 5 V des modules vient de VIN, jamais de 3V3** (le régulateur 3,3 V de la carte ne tiendrait pas le servo et le HC-SR04 n'aime pas 3,3 V) ; **l'Echo ne touche jamais directement une broche de l'ESP32**.

## 2. Câblage

> **Révision du 2026-11-09 (après-midi).** Plan refait sur la photo réelle de la plaque, après la décision de l'utilisateur de prendre le 5 V sur la patte VIN avec son propre fil. Les deux anciens schémas `images/plan_radar_ultrason_plaque*.png` (D27 / D32 / D34, rangées 11 à 25, trous libres supposés du côté VIN) étaient faux : ils sont retirés du dépôt et remplacés par un seul dessin sur la photo.

Dessin sur la photo réelle, numéros 1 à 9 comme dans le tableau de la section 2.2 : [`images/branchement_radar_sur_photo.jpg`](../images/branchement_radar_sur_photo.jpg). Brochage complet (robot, gyroscope, radar) : [`code/README.md`](../code/README.md), section « Brochage complet ».

### 2.1 Ce que montre la photo de la plaque

- Le cerveau occupe les rangées 30 (pattes EN et D23, bout antenne) à 16 (pattes VIN et 3V3, bout prise USB) ; les numéros de rangée sont imprimés sur la plaque. Sur cette carte, la patte 5 V s'appelle **VIN** : c'est la patte du coin, bout prise USB, et **sa voisine immédiate est une patte GND**.
- **Côté 3V3** : un trou libre à côté de chaque patte. Libres le 2026-11-09 : ceux de **D23**, **D19** et **D18** (pris par le radar), TX0, RX0 et D5. Occupés : D22 et D21 (gyroscope), TX2, RX2 et D4 (robot), GND et 3V3 (vers les deux lignes de ce côté).
- **Côté VIN** : aucun trou libre à côté des pattes, le cerveau va jusqu'au bord de la zone de trous. Pour atteindre VIN, l'utilisateur passe son propre fil. Les seuls trous reliés à VIN sont les quatre autres trous de sa rangée (16), cachés sous le cerveau ; la rangée 17, sa voisine vers l'antenne, est celle de la patte GND, et la rangée 15, vers la prise USB, n'est reliée à aucune patte.
- **Les deux lignes du côté 3V3** portent le 3,3 V (rouge) et la masse (bleue) du cerveau et du gyroscope. On n'y touche pas, sauf pour y prendre la masse.
- **Les deux lignes du côté VIN** sont entièrement libres : la rouge devient la **ligne 5 V** du radar, la bleue sa **masse**. Sur les lignes, les trous vont par groupes de cinq : le long du cerveau, en face des rangées 15 à 19, 21 à 25 et 27 à 31 (aucun trou en face des rangées 20, 26 et 32 ; la rangée 32 est le milieu de la plaque, là où les lignes seraient coupées si elles le sont). Tous les trous utilisés par le dessin existent et sont libres sur la photo (vérifié de nouveau le 2026-11-09 au soir).
- **La zone au-dessus de l'antenne, moitié côté VIN** (rangées 33 à 50) est vide ; dans chaque rangée, les cinq trous sont reliés entre eux. Elle reçoit les deux résistances, montées comme les trois résistances du robot dans l'autre moitié.

### 2.2 Les branchements, dans l'ordre

Tout se fait cerveau éteint : câble USB débranché et prise du robot débranchée. Tout ce qui va dans la ligne rouge ou la ligne bleue du côté VIN se plante **le long du cerveau** (entre la rangée 30 et la rangée 16) : si les lignes sont coupées au milieu de la plaque, tout reste ainsi sur le même tronçon.

| # | Quoi | De | Vers |
|---|---|---|---|
| 1 | fil 5 V (posé par l'utilisateur) | patte **VIN** du cerveau, sans toucher la patte GND voisine | **ligne rouge du côté VIN** |
| 2 | fil de masse | **ligne bleue du côté 3V3**, en face de la rangée 31 | **ligne bleue du côté VIN** (bleu à bleu, jamais vers une ligne rouge) ; le fil contourne le bout du cerveau, il ne reste pas posé sur l'antenne Wi-Fi (le rectangle noir au bout opposé à la prise USB) |
| — | **les deux mesures au multimètre** de la règle 3 (section 2.3), puis USB débranché de nouveau | | |
| 3 | condensateur 100 µF | patte longue (+) dans la ligne rouge du côté VIN | côté rayé (−, patte courte) dans la ligne bleue du côté VIN, trou voisin |
| 4 | servo, trois fils mâle-mâle dans sa prise | fil **rouge** → ligne rouge du côté VIN ; fil **brun** → ligne bleue du côté VIN | fil **orange** → trou à côté de **D18** |
| 5 | capteur de distance, quatre fils femelle-mâle | **Vcc** → ligne rouge du côté VIN ; **Gnd** → ligne bleue du côté VIN ; **Trig** → trou à côté de **D19** | **Echo** → rangée **45** de la zone vide |
| 6 | résistance **1 kΩ** | rangée **45** | rangée **40** |
| 7 | résistance **2 kΩ** | rangée **40** | rangée **35** |
| 8 | fil | rangée **40** | trou à côté de **D23** |
| 9 | fil | rangée **35** | ligne bleue du côté VIN |

Les rangées 45, 40 et 35 sont celles dont le numéro est imprimé sur la plaque, du côté VIN ; trois autres rangées vides et distinctes de cette zone conviennent aussi. Ce que font les deux résistances : l'Echo arrive à environ 4,7 V sur la rangée 45 ; la rangée 40, entre les deux résistances, n'en garde que les deux tiers, soit environ 3,1 V, et c'est elle qui va à D23. Si les deux résistances sont inversées, D23 ne reçoit que 1,6 V : aucun écho n'est vu, rien n'est abîmé.

Résistances : celles du kit sont bleues à cinq anneaux, 1 kΩ = brun, noir, noir, brun, puis brun ; 2 kΩ = rouge, noir, noir, brun, puis brun (à quatre anneaux : brun-noir-rouge et rouge-noir-rouge). Le plus sûr est le multimètre sur Ω : environ 1,00 kΩ et 2,00 kΩ. À défaut de 2 kΩ : 2,2 kΩ ou deux 1 kΩ à la suite. La règle : tension de l'Echo × R2 / (R1 + R2) entre 2,5 et 3,4 V.

Pourquoi ces broches : D18, D19 et D23 n'ont aucun rôle au démarrage du cerveau et leurs trous sont libres. Le programme active en plus un rappel interne vers la masse sur D23 : l'entrée reste calme tant que rien n'est branché. RX2, TX2, D4, D21 et D22 restent au robot et au gyroscope.

### 2.3 Les règles

1. Tout se câble **cerveau éteint** : câble USB débranché et prise du robot débranchée.
2. Le 5 V des modules vient de la patte **VIN**, par la ligne rouge du côté VIN. **Jamais de fil entre les deux lignes rouges** : celle du côté 3V3 porte le 3,3 V du cerveau et du gyroscope, et 4,7 V les abîmerait. Jamais de 3V3 pour les modules, jamais directement des trous 1-2 du robot (14 à 21 V : les modules grilleraient ; l'abaisseur de la note F est fait pour ça).
3. **Deux mesures avant de brancher le moindre module**, une fois les fils 1 et 2 posés. Pour toucher les lignes, planter un fil dans la ligne rouge du côté VIN et un autre dans la ligne bleue du côté VIN, puis poser les pointes du multimètre sur leurs bouts libres, sans que ces deux bouts se touchent. (a) USB débranché, multimètre sur la position « bip » : **pas de bip continu** (un bip très bref au contact est normal, l'écran peut afficher un nombre). Un bip continu veut dire que VIN touche la masse : chercher le fil 1 qui touche la patte GND voisine, ou le fil 2 planté dans une ligne rouge. (b) USB branché, multimètre sur volts continus (calibre 20 V), pointe rouge sur la ligne rouge, pointe noire sur la ligne bleue : **environ 4,7 V** (de 4,4 à 5,1 V), sans signe moins. Toute autre valeur (0 V, 3,3 V, valeur négative ou qui bouge) : débrancher l'USB et ne rien brancher de plus avant d'avoir compris.
4. L'Echo passe **toujours** par les deux résistances : il arrive sur la rangée 45 et nulle part ailleurs, et seul le fil de la rangée 40 va au cerveau. C'est une vérification visuelle (une photo avant la mise sous tension). Contrôle simple en plus, capteur branché et cerveau sous tension : entre la rangée 40 et la ligne bleue, 0 V au repos (l'Echo est bas quand le capteur ne mesure pas) ; si on lit plus de 3,4 V, un fil est au mauvais endroit, débrancher l'USB.
5. Ne pas tourner le bras du servo à la main quand il est alimenté ; à l'arrêt (mode « arrêt » du firmware), il est relâché et on peut le bouger.
6. Le courant du servo passe par la prise USB du cerveau et par la petite diode de la carte. Si le cerveau redémarre quand le servo bouge (raison « **baisse de tension** » ou « mise sous tension » en pied de page, touche `i`), c'est l'alimentation qui faiblit : vérifier le condensateur, raccourcir le câble USB ou changer de port, et à terme passer à l'abaisseur de la note F. Sur le port USB d'un PC (500 mA), ESP32 Wi-Fi + servo en mouvement passent en général, mais c'est juste ; sur la batterie portable, les coupures franches déjà notées au journal peuvent revenir. Ce sont des redémarrages, pas des dégâts.
7. Toujours finir une session robot par `s` puis `x` ; le radar peut rester en marche, il ne touche pas au robot.

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
- **Arrêt auto** (case « arrêt auto », active par défaut) : distance devant sous le seuil et vieille de moins de 1,5 s → roues arrêtées si le robot avance, ordre `8` refusé avec un message dans la console ; `2`, `4`, `6` passent toujours. **Devant en marche avant** (actif par défaut) : en balayage, dès qu'une avance est demandée et pendant toute la marche avant, le capteur se met devant et mesure à 10 Hz ; il y reste 1 s après le dernier ordre d'avance (la page le répète toutes les 400 ms tant que le bouton est tenu), puis reprend le balayage. Sans cela, le secteur avant ne serait revu qu'une fois par passage (~2 s, soit 30 cm à 150 mm/s), et un refus d'avancer expirerait tout seul pendant que l'on tient le bouton (correction du 2026-11-09, avant tout essai). L'entrée Echo a aussi un rappel interne vers la masse : elle reste calme tant que rien n'est câblé.
- **Réglages** conservés en mémoire flash : seuil (10 à 150 cm), arrêt auto, devant en marche avant, pas (5 à 45°), amplitude (20 à 80°), mesures par direction (1 à 3, médiane), sens du servo.
- **Console** : `r` fait tourner arrêt → fixe devant → balayage ; `u` affiche l'état, les compteurs (mesures, sans écho, sans réaction, passages, arrêts auto, avances refusées) et la carte en texte. La console signale le premier écho reçu (« capteur détecté »), un capteur qui ne réagit plus (Echo jamais haut : fil ou alimentation), chaque arrêt auto.
- **API** : `/api/radar` renvoie l'état et la carte (`points` = [angle, mm, âge ms]) ; paramètres : `mode=off|fixe|balayage`, `angle=-80..80`, `seuil=`, `securite=0|1`, `auto=0|1`, `pas=`, `amplitude=`, `ech=1..3`, `inv=0|1`, `effacer=1`. `/api/state` contient un résumé `radar` (mode, distance devant en mm, âge). Le CSV (touche `j`) a une colonne `us_mm` de plus (−1 inconnue, 0 rien à portée).
- **PC** : `monitor_wifi.py` enregistre `radar_mode` et `us_mm` ; `radar_capture.py` enregistre chaque mesure avec les encodeurs et le cap du moment (CSV) et dessine la dernière carte en SVG (ouvrable dans un navigateur), sans rien à installer : `python roomba694_recherche/code/outils/radar_capture.py 192.168.18.25 120 0.5 roomba694_recherche/mesures`.

Limites à garder en tête : une seule mesure à la fois et un faisceau large (un obstacle à 60° du capteur est vu « dans l'axe » s'il est le plus proche du cône) ; les tissus, rideaux et coussins renvoient peu ; une surface très oblique renvoie le son ailleurs (« rien à portée » alors qu'il y a un mur) ; les pieds de chaise et les plinthes sont sous le faisceau. C'est un garde-fou et une première carte, pas une cartographie. Limites du garde-fou lui-même : en mode fixe orienté ailleurs que devant, rien ne surveille l'avant ; au premier ordre d'avance en balayage, le robot peut parcourir quelques centimètres avant que le capteur ne soit revenu devant ; en balayage, la médiane mélange trois directions voisines (−10°, 0°, +10° au pas de 10°).

## 5. Plan de test, dans l'ordre

Chaque étape se fait quand la précédente est bonne ; je demande confirmation avant tout ce qui fait bouger le robot.

1. **Mise à jour du firmware** sans rien de câblé : page `/update` ou `curl -u admin:roomba694 -F "firmware=@…/roomba694_wifi.ino.bin" http://192.168.18.25/update`. Attendu : la page affiche la carte « Radar à ultrasons », `i` dit « v3 », `u` dit « mode arrêt ». Rien ne change pour le robot. L'ordre des étapes 1 et 2 est libre : avec la v2 encore en place, D18, D19 et D23 sont de simples entrées, câbler avant la mise à jour ne risque rien.
2. **Câblage** (section 2.2), cerveau éteint, prise du robot débranchée, avec les deux mesures au multimètre de la règle 3 (pas de bip continu, puis environ 4,7 V entre la ligne rouge et la ligne bleue du côté VIN). Une photo de la plaque avant la remise sous tension permet de vérifier chaque fil.
3. **Servo seul** : carte sous tension (USB), capteur pas encore fixé au bras. Au démarrage le servo se centre une fois puis se relâche (signe de vie). Page : « Fixe devant » → il tient le centre ; toucher le dessin à gauche (+45°) → il doit tourner vers la **gauche** du robot (vu du dessus, sens anti-horaire) ; sinon cocher « servo inversé ». « Arrêt » → recentré puis relâché. Raison du dernier redémarrage toujours « mise à jour » ou « mise sous tension » : si « baisse de tension » apparaît, voir règle 6.
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

Fiches techniques classiques (liens stables, non revérifiés ce jour) : HC-SR04 https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf · SG90 http://www.ee.ic.ac.uk/pcheung/teaching/DE1_EE/stores/sg90_datasheet.pdf · PWM LEDC de l'ESP32 (cœur Arduino 3.x, `ledcAttach` / `ledcWrite`) https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html · interruptions GPIO https://docs.espressif.com/projects/arduino-esp32/en/latest/api/gpio.html. Vitesse du son 343 m/s à 20 °C. Plan de plaque : photo de l'utilisateur du 2026-11-09, annotée, `images/branchement_radar_sur_photo.jpg` ; brochage : `code/README.md`. Les photos annotées plus anciennes `images/plan_sur_photo_plaque.jpg` et `images/plaque_esp32_placee_rangees.jpg` décrivent le plan du 2026-11-08, qui ne correspond pas à la plaque telle qu'elle est fixée sur le robot (pas de trous libres du côté VIN).
