# Carte vivante — le Roomba 694 suivi en direct sur le plan quadrillé

État au 2026-11-14. Une page à ouvrir sur le PC ou sur le téléphone : le plan de l'appartement avec ses cases de 50 cm nommées comme aux échecs (`../outils/grille.py`, la convention de `carte_grille.py`), et le robot qui s'y déplace pendant un essai. La position se corrige d'elle-même à chaque tour sur place et chaque fois que le robot se pose sur sa base ; la page dit d'où vient la position affichée. La carte garde d'un essai à l'autre ce que le robot a appris : le sol parcouru, les parois vues, le signal de sa base, ce qu'il a touché.

Ce dossier ne fait que **lire** : aucun ordre n'est envoyé au robot ni au cerveau, aucun fichier de `mesures/`, de `outils/` ou de la navigation n'est modifié, rien ne sort du réseau de la maison.

## Lancer

```
python roomba694_recherche/code/carte_vivante/serveur.py
```

puis ouvrir http://127.0.0.1:8694 sur ce PC. Le serveur suit l'enregistrement le plus récent de `mesures/` (celui qu'`enregistreur.py` est en train d'écrire) et passe tout seul au suivant quand un nouvel enregistrement commence.

Rejouer un enregistrement terminé, avec les mêmes calculs que le direct :

```
python roomba694_recherche/code/carte_vivante/serveur.py --rejeu exploration17_20261113_163238 --vitesse 8
```

Options : `--debut HH:MM:SS` et `--pause` (rejeu), `--prefixe NOM` (suivre un enregistrement précis), `--port`, `--plan`, `--zones`, `--px-par-m`, `--base U,V` (pixel du robot posé sur sa base ; `405,33` depuis le 2026-11-14, la valeur de `--base-plan` d'`explorer3.py`), `--base-cap DEG` (direction vers laquelle la base est tournée : 270, vers le bas), `--base-portee MM` (2000), `--connaissances DOSSIER` (où la navigation garde ses obstacles, ses repères et ses notes : `plan_lidar/`). Dans l'adresse de la page, `?vue=tout` ouvre sur tout l'appartement.

**Téléphone.** Par défaut le serveur n'écoute que sur ce PC (`127.0.0.1`). Avec `--ouvert`, il écoute en plus sur l'adresse de ce PC **sur le réseau de la maison** et ne sert que les appareils de ce réseau-là. Il affiche l'adresse à ouvrir sur le téléphone, qui doit être relié au même Wi-Fi que le PC (pas au réseau « Roomba694 » du cerveau, pas aux données mobiles), et note dans sa sortie le premier accès de chaque appareil.

```
python roomba694_recherche/code/carte_vivante/serveur.py --ouvert
```

La page montre alors le plan de l'appartement à tout appareil de ce réseau : à ne lancer qu'avec l'accord de l'utilisateur. Il l'a donné le 2026-11-13 à 14 h 20 (« Oui, ouvre-la »), pour cette page et ce réseau ; à redemander si l'un des deux change. Le pare-feu de Windows laissait déjà entrer les connexions vers ce Python sur ce réseau (règle existante, que la carte n'a ni créée ni modifiée).

Le réseau de la maison se reconnaît à son adresse : celle des adresses du PC qui a les mêmes trois premiers nombres que le cerveau (`--cerveau`, `192.168.18.25`). Si le PC n'en a pas, le serveur refuse de se lancer. **Incident du 2026-11-14, 9 h 39** : la version d'avant prenait « la carte réseau par laquelle le PC rejoindrait le cerveau » ; un VPN venait de s'activer sur le PC et avait pris cette route, et le serveur relancé a écouté une minute sur l'adresse du VPN au lieu de celle du Wi-Fi. Arrêté dès que vu, puis corrigé ; il ne tenait alors aucun relevé des accès, on ne peut donc pas dire si quelqu'un s'y est connecté (les fournisseurs de VPN isolent leurs abonnés les uns des autres, et il fallait de toute façon donner cette adresse comme nom d'hôte). Tant que ce VPN est actif, il peut aussi empêcher le téléphone d'atteindre le PC : c'est un réglage du VPN (« autoriser le réseau local »), auquel la carte ne touche pas.

## Ce que montre la page

- **Le plan quadrillé** : cases de 50 cm, lettres des lignes à gauche et numéros des colonnes en haut (toujours visibles), nom de chaque case dans son coin quand la carte est assez agrandie. Pièces inaccessibles en rouge. En bas à gauche, une vue d'ensemble de l'appartement.
- **Le robot** (rond orange, pointe blanche vers l'avant), mis à jour quatre fois par seconde et lissé entre deux mises à jour. Son pare-chocs passe au rouge du côté touché ; les six capteurs optiques s'allument quand quelque chose est tout près ; une pastille de la couleur du faisceau apparaît sur son avant quand il reçoit le signal de sa base. **En gris**, quand la carte ne sait plus où il est : plus de nouvelles depuis deux minutes (« dernière position connue », avec le jour et l'heure), ou robot déplacé à la main (voir plus bas).
- **Ce que voit le capteur de distance** : un cône devant le robot jusqu'à l'écho du moment, un point pour chaque écho de l'essai, et, après chaque tour sur place, **les parois vues** : là où la distance est restée la même sur une douzaine de degrés au moins, un trait de 12 cm en travers du regard (le même calcul que la navigation, `carto.paliers_souples`). Un seul tour ne dit pas si c'est un mur ou un pied de meuble ; ce sont les traits de plusieurs tours, bout à bout, qui dessinent un mur.
- **Le trajet** : trait plein = tronçon « calé », corrigé par la mesure qui l'a suivi ; tirets = tronçon « à l'estime », compté par le robot depuis le dernier calage. Un cercle ambre en tirets autour du robot grandit avec le chemin roulé depuis le dernier calage (2 cm + 4 % du chemin).
- **Les tours sur place** : un rond bleu, avec un point au milieu quand le tour est **confirmé par des repères** (des tours déjà faits au même endroit : précis à 2 ou 3 cm, alors que le plan seul peut se tromper de 10 à 30 cm, journal § 42). Quand un tour recale le robot, une flèche violette va de l'endroit où il se croyait à l'endroit où le calage le place, une bulle l'annonce et le tronçon qui y mène se redresse. Un calage sans repère et de note inférieure à 0,6 est dessiné en ambre et dit « incertain ».
- **La base de recharge** : carré vert à sa place mesurée (case B16, pixel (405, 33)), avec une pointe du côté où elle est tournée (le bas), **son axe** en tirets verts sur 2 m (le robot s'y aligne, face à elle, pour rentrer) et le secteur où ses faisceaux portent. **Le signal de la base** : un point à chaque endroit où le récepteur du dessus l'a reçu, rouge, vert, ou ocre pour « les deux » (dans l'axe) ; face à la base, le rouge est à droite et le vert à gauche.
- **Les contacts du pare-chocs** (croix rouge, avec le côté), **les objets frôlés** (points orange : un capteur optique au-dessus de 200), **les patinages** (rond « ≈ » : une roue a tourné plus que le sol n'a défilé ; la fiche dit de combien et ce qui a été retiré du trajet).
- **Ce que la navigation sait de l'appartement**, relu dans ses fichiers toutes les deux secondes : les **obstacles connus** absents du plan (`plan_lidar/obstacles.json` : disque rouge en tirets du rayon qu'elle contourne, sa note dans la fiche), les **repères** (`plan_lidar/reperes_tours.json` : points violets, et en violet pâle la zone de 35 cm où un tour se recale sur eux), et les **notes** de sa dernière carte quadrillée (le fichier `plan_lidar/reperes_AAAAMMJJ*.json` le plus récent : ronds bleu foncé « i », à toucher pour lire).
- **La mémoire de la carte**, en pâle : le **sol déjà parcouru** lors des essais précédents (une bande de la largeur du robot), les **parois vues**, le **signal de la base**, les contacts, les objets frôlés et les patinages. Voir « Ce que la carte garde en mémoire ».
- **Les destinations** données à `explorer3.py` : anneau vert, plein une fois atteinte, barré si elle est abandonnée ; un trait en tirets relie le robot à celle en cours.
- **En haut** : la case du robot en grand, ce qu'il fait (« Sur sa base, en charge », « une roue patine », « Soulevé, les roues en l'air »), vers où il est tourné, le signal de la base s'il le reçoit, et **d'où vient la position** : « Calé à 17 h 14 par un tour sur place, sur 5 repères · 1,6 m à l'estime depuis », « Posé sur sa base à 9 h 34 : position sûre », « Position de départ donnée à …, pas mesurée », ou « En attente : le robot a été soulevé et déplacé à la main ». Pastille verte : mesure récente et sûre ; ambre : estime longue, calage incertain ou position seulement donnée ; rouge : position inconnue ou robot sans nouvelles.
- **En bas** : le journal de l'essai (calages, contacts, patinages, destinations, mesures par les faisceaux de la base, arrêts) ; toucher une ligne y amène la carte. Toucher un repère de la carte ouvre sa fiche.
- Boutons : « ≡ » pour choisir ce que la carte montre de sa mémoire (six calques ; le choix reste dans le navigateur), suivre le robot, voir tout l'appartement, agrandir, réduire ; deux doigts pour agrandir, un doigt pour déplacer.

## D'où vient la position affichée

Position = **dernière ancre + déplacement compté depuis par le cerveau**. Le calcul est celui d'`Estime.suivre` d'`explorer3.py` et de `relance.py` : chaque petit déplacement du journal (`x_mm`, `y_mm` dans le repère du cerveau) est tourné de l'écart entre le cap du plan et le cap du cerveau, et le cap du cerveau est multiplié par l'échelle du gyroscope (1,0045).

**Patinage.** Quand une roue tourne plus que le sol ne défile sous elle (les compteurs annoncent une rotation que le gyroscope ne voit pas), le chemin compté en trop est retiré, par le calcul de la navigation elle-même (`carto.patinage` et `carto.part_roulee`, importés de `../outils/`), pour le firmware v9 et les suivants (la version est lue au début de `NOM_etat.jsonl`). Un patinage de plus de 6 cm de roue est signalé sur la carte et dans le journal.

Une **ancre** dit « à tel instant le robot était à tel endroit du plan ». La carte les lit dans les fichiers que la navigation écrit ; la seule qu'elle tire elle-même des mesures est celle de la base.

| Source | Fichier | Ce que la carte en fait |
|---|---|---|
| tour sur place jugé par le filtre, puis recalé sur les repères | `NOM[_x]_stations.json` d'`explorer3.py` (`pose`, `apres`, `plan`, dont `plan[i].reperes`) ; `NOM_essai_tours.json` | ancre **mesurée** : la correction est montrée, et répartie sur le tronçon roulé depuis l'ancre précédente, au prorata du chemin |
| robot posé sur sa base | `NOM_etat.jsonl` (`robot.base`, quand le robot répond) | ancre **mesurée**, sans aucun tour : la position est celle de la base, le nez vers elle. Elle dit du même coup l'erreur d'arrivée |
| départ donné à la navigation | premier tour de `NOM[_x]_stations.json` (`depart`, `avant`) ; en attendant, la ligne « localisation : … autour du pixel » de `NOM_explorer3.txt` | ancre **donnée** : corrige le tronçon si elle est à moins de 25 cm et 20° de la position suivie, sinon c'est un repositionnement (trait violet pointillé) |
| position tenue par la navigation à la main | `NOM_tour_xxx.json` (`pose_plan_avant` avec `depart`) ; lignes `POSE=U,V,CAP` de `NOM*balise*.txt` ou de `NOM*passage*.txt`, **si** la sortie de ces outils est gardée dans un fichier | ancre donnée (pour un fichier `.txt`, à son heure d'écriture) |
| enregistrement précédent | les mêmes fichiers, pour l'enregistrement d'avant | si le cerveau n'a pas redémarré entre les deux (son horloge `ms` continue), sa dernière position connue plus ce qu'il a compté depuis sert de départ |

**La position devient inconnue** dans quatre cas, jusqu'à l'ancre suivante ; le robot est alors dessiné en gris là où il a été vu pour la dernière fois, et ce qu'il roule entre-temps est placé après coup, en remontant depuis l'ancre suivante :

- le cerveau redémarre ou sa position est remise à zéro (son repère change) ;
- **le robot est soulevé** : ses deux roues en l'air plus d'une seconde (colonnes `roue_g`, `roue_d`), quelqu'un le porte ;
- **le robot est tourné à la main** : son cap change de 8° ou plus en moins de 5 s alors que les compteurs de ses roues ne bougent pas (on le fait pivoter ou glisser sans le soulever) ;
- **le robot quitte sa base** : sur sa base alimentée il ignore les ordres de roues (journal § 32), c'est donc qu'on l'en a tiré à la main, et le cerveau compte mal un robot poussé à la main (`position.ino`). Si un jour le cerveau sait faire sortir le robot de sa base, cette règle sera à revoir.

Un même geste n'est signalé qu'une fois (30 s). Un robot poussé tout droit sans tourner ni se soulever reste invisible : rien dans les mesures ne le distingue d'un robot immobile.

Ne comptent pas comme contacts les appuis du pare-chocs en mode passif : c'est alors le robot qui se conduit seul (retour à la base) ou quelqu'un qui le pousse, et la position comptée par le cerveau n'y est pas fiable.

**Limites connues.**

- `passage.py` n'écrit sa position que sur l'écran de la session qui le lance. Tant que sa position de départ est celle que donne `relance.py`, la carte et lui comptent la même chose (vérifié le 2026-11-14 : 1 à 7 cm d'écart en C28, B22 et D12). Si la navigation décale cette position à la main sans l'écrire dans un fichier, la carte ne le sait pas : elle continue à l'estime depuis le dernier calage, et l'écrit en haut de la page.
- Pendant un accostage mené par le robot lui-même (mode passif), le cerveau ne sait pas dans quel sens tournent les roues (`position.ino`) : le trajet dessiné pendant cette manœuvre est approximatif ; l'ancre de la base le corrige à l'arrivée.
- La mémoire place les essais passés d'après les calages de l'époque : 6 cm en général, 20 à 40 cm par endroits (devant la base avant les repères du 13 après-midi).

## Ce que la carte garde en mémoire

Au lancement puis à chaque nouvel enregistrement, un fil à part rejoue les enregistrements plus anciens (sept secondes aujourd'hui, puis rien : le résultat est gardé dans `plan_lidar/carte_vivante/memoire_carte.json`, hors dépôt ; le supprimer le fait recalculer). Ne sont gardés que les moments situés par un tour jugé par le filtre ou par la base.

**Moments à oublier.** Quand on comprend après coup que le calage d'un moment était faux, on l'écrit dans `plan_lidar/carte_vivante/a_oublier.json` (hors dépôt, tenu à la main) :

```
[{"enregistrement": "exploration14_20261113_144300", "de": "14:51:46", "a": "15:12:05", "raison": "…"}]
```

La première entrée est celle-là : le 2026-11-13 à 14 h 51 une roue a patiné, le programme de ce jour-là ne retirait pas encore le patinage, et jusqu'au repositionnement de 15 h 12 ses calages plaçaient le robot 28 à 37 cm à côté (journal § 43). Les contacts de ce moment ne sont donc pas sur la carte ; les obstacles de la pièce centrale, replacés par la navigation, y sont par `obstacles.json`.

## Fichiers

- `serveur.py` : le serveur local (bibliothèque standard ; `PIL`, et `numpy` avec `scipy` pour les zones rouges et pour `carto.py`). Sert la page, le plan et l'état (`/api/suite?e=&v=` : seulement ce qui a changé depuis la version `v`). Refuse les requêtes dont l'en-tête Host n'est pas une adresse de ce PC (une page d'un autre site ne peut pas lire le plan).
- `suivi.py` : des lignes du journal et des ancres à la position sur le plan ; le tracé par morceaux, les corrections, le patinage, le robot porté, les contacts, les objets frôlés, le signal de la base, le journal.
- `sources.py` : la lecture des fichiers (en direct ou en rejeu) et ce qu'on en tire ; la base (`Base`), la mémoire (`Memoire`), les fichiers de la navigation (`Connaissances`).
- `page.html` : la page, sans aucune ressource extérieure (un seul fichier ; le plan est demandé au serveur).
- `capture.py` : une image de la page à la taille d'un téléphone (`python capture.py [--url http://127.0.0.1:8694/] [--sortie FICHIER.png]`), rangée par défaut dans `plan_lidar/carte_vivante/`. Le serveur doit tourner.
- `essai_direct.py` : l'essai du mode direct sans robot (voir plus bas).

Données privées : le plan reste dans `plan_lidar/` (hors dépôt) et n'est copié nulle part ; les images de la page, la mémoire de la carte et la liste des moments à oublier vont dans `plan_lidar/carte_vivante/`. Le nom du réseau Wi-Fi (champ `sta` de `/api/state`) n'est pas lu.

## Vérifications du 2026-11-14 (mise à jour : base, repères, patinage, mémoire)

1. **Patinage**, rejeu de `exploration14_20261113_144300` : deux patinages de la roue droite retrouvés, à 14 h 51 min 46 (3,5 s, 427 mm de roue en trop, 214 mm retirés) et 14 h 52 min 03 (2,8 s, 349 mm, 175 mm retirés), 395 mm retirés en tout. Le relevé de la navigation (`results_t_patinage_20261113.txt`) dit 427 et 349 mm, 213 et 174 mm, 395 mm.
2. **Trajets faits à la main**, rejeu de `exploration17_20261113_163238` : la carte, à l'estime depuis le tour de G26, arrive en C28 au pixel (730, 61) quand la navigation tenait (733,3 ; 58,9) : 7 cm ; en B22, 1 cm d'écart avec la position qu'elle tenait avant son tour, puis (577, 43) pour (578, 43) noté au journal § 43 ; en D12 à 17 h 17 (`exploration18`), 1 cm. C9 : pixel (224,1 ; 66,9), celui du journal § 44.
3. **Robot porté**, même enregistrement : les deux roues en l'air à 17 h 08 min 24 pendant 9 s ; la position devient inconnue, « vu pour la dernière fois en J17 » ; dans l'enregistrement suivant elle reste inconnue jusqu'au départ donné à 17 h 13. Avant cette mise à jour la carte gardait le robot dans le couloir alors qu'il avait été porté devant sa base.
4. **Base.** Rejeu de `exploration13_20261113_143420` (accostage d'hier) : « Robot posé sur sa base » à 14 h 35 min 25. Rejeu de `exploration6_20261113_110823` : posé à 11 h 08 min 29, tiré de sa base à 11 h 10 min 57. **En direct le 2026-11-14 à 9 h 34 min 48** (`exploration20_20261114_093358`) : la page a affiché « Sur sa base — Posé sur sa base à 9 h 34 : position sûre ». Ce que cet essai a appris à la carte, corrigé le jour même :
   - elle annonçait d'abord « position corrigée de 26 cm ». Faux : d'après le journal de la navigation (commit e06c1a6), l'accostage du robot n'avait pas abouti et l'utilisateur l'a posé sur sa base à la main ; les 26 cm étaient ce déplacement-là. Dans les mesures, le cap tourne de 154° en 2 s à 9 h 34 min 39 alors que les compteurs des roues ne bougent plus : c'est devenu la règle « robot tourné à la main ». Rejoué : « Robot tourné à la main … position inconnue » à 9 h 34 min 39, puis « Robot posé sur sa base : position sûre », sans correction inventée. La même règle, passée sur les 20 enregistrements des 10, 13 et 14 (400 000 lignes), ne se déclenche que là et à trois moments où le robot était déjà dit soulevé ou tiré de sa base ;
   - elle dessinait cinq contacts pendant la manœuvre du robot, dont deux au-delà du mur. Les appuis du pare-chocs en mode passif ne sont plus des contacts ; les sept contacts du 13 et les six du 14 au matin étaient tous en mode Safe et restent.
5. **Mémoire** des enregistrements d'avant `exploration18` : 7 contacts, 156 objets frôlés, 122 morceaux de trajet, 759 parois, 383 cases où le signal de la base a été reçu ; 6,5 s de calcul, 0,04 s ensuite. Avec les essais du 14 au matin : 13 contacts, 154 morceaux de trajet, 973 parois. Les contacts gardés tombent sur les obstacles de la navigation : (363, 81) pour (364, 82) en D14, (326, 132) pour (326, 132) en E13, (409, 223) pour (409, 223) en J16. Les contacts de 14 h 53 à 14 h 56 (moment à oublier) n'y sont pas.
6. **Fichiers de la navigation** (sur une copie temporaire) : 14 obstacles, 80 repères, 7 notes lus ; un obstacle ajouté et un fichier de notes plus récent sont pris à la lecture suivante ; un fichier illisible ou retiré laisse ce qui était affiché.
7. **Direct simulé** (`essai_direct.py`, qui réécrit maintenant aussi l'état du robot, les tours faits à la main, les mesures par la base et un dernier passage resté sans lettre) : voir le résultat à la fin de cette section.
8. **Page**, dans le navigateur intégré puis en image à la taille d'un téléphone (Edge sans fenêtre) : aucune erreur dans la console ; 1,6 ms par image avec tous les calques sur le PC ; rejeu du robot porté, vue de la base, vue d'ensemble, robot sur sa base regardés un à un.
9. **Réseau**, après la correction de 9 h 41 : le serveur écoute sur `127.0.0.1:8694` et `192.168.18.6:8694` seulement (lu dans la liste des ports ouverts), ne répond pas sur l'adresse du VPN, et une requête au nom d'un autre site reçoit 403.

Résultat du direct simulé, six enregistrements suivis l'un après l'autre comme le fait le serveur (`exploration13`, `14`, `17`, `18` du 13 ; `19` et `20` du 14) : mêmes ancres (1, 23, 24, 14, 32 et 1), 0,00 mm et 0,000° d'écart, même position finale, mêmes contacts, mêmes patinages, mêmes parois (0, 138, 142, 70, 144 et 0) que le rejeu de chaque enregistrement ; un calage est pris en compte 1,1 à 1,2 s après la fin du tour (1,4 s au plus) ; aucune erreur pendant le suivi. Le direct retrouve en plus ce que le rejeu d'un enregistrement seul ne peut pas savoir : le robot tiré de sa base à 14 h 43 min 11 (il y était à la fin de l'enregistrement d'avant) et la position de départ de `exploration20`, reprise de `exploration19` (D16). « Soulevé » à 17 h 08 min 24 et « tourné à la main » à 9 h 34 min 39 sont vus des deux côtés. `17` à `20` ont été passés avec le code final ; `13` et `14` avec celui d'avant la règle « tourné à la main », qui ne s'y déclenche pas (vérifié en rejeu).

**Pas encore vérifié** : sur le téléphone de l'utilisateur, les nouveaux calques, le bouton « ≡ » et le maniement au doigt (il a seulement confirmé le 13 que la page s'affiche) ; si le téléphone atteint encore le PC pendant que le VPN est actif ; un départ de la base vu en direct (seulement en rejeu et en direct simulé) ; un patinage vu en direct ; un redémarrage du cerveau en cours d'enregistrement ; les lignes `POSE=` de `passage.py` (aucun fichier de ce genre n'existe ; celles de `balise_base.py` ont été lues en direct le 14 à 9 h 29).

## Vérifications du 2026-11-13 (première version)

1. **Rejeu de `exploration9_20261113_124811`** (trajet C17 → K10, deux contacts). Les quatorze ancres sont retrouvées, et les corrections calculées par la carte sont celles qu'`explorer3.py` a écrites dans `_explorer3.txt`, au millimètre et au dixième de degré : (+29, −34) mm et +1,0° en D14, (+15, −40) mm et +2,0° en E12, (−79, +46) mm en G12, (+19, +68) mm et +1,7° en J12. Les deux contacts sont vus dans le journal (12 h 52 min 57 à gauche, dans la porte H12 ; 13 h 05 min 22 à droite, en K10). Après la porte, la carte suit le robot à l'estime sur 1,6 m jusqu'au pixel (234, 256), la valeur notée au journal § 36 ; le tour final le recale au pixel (239,6 ; 251,0), en K10.
2. **Rejeu de `exploration10_20261113_132251`** (retour K10 → C17) : départ repris de l'enregistrement précédent (K10), 12 cm et 3,1° d'écart avec le départ donné huit minutes et un passage étroit plus tard, puis quatre tours sur place jusqu'en C17.
3. **Direct simulé** : `python essai_direct.py exploration9_20261113_124811 exploration10_20261113_132251` : mêmes ancres, mêmes corrections et même position finale que le rejeu ; un calage est pris en compte 1,2 s après la fin du tour (1,7 s au plus) ; passage d'un enregistrement au suivant sans intervention.
4. **Direct réel**, de 13 h 58 à 14 h 05 : le serveur tournait pendant que la session de navigation menait le robot (`exploration11_20261113_135821`). Les données affichées avaient 0,1 s au plus ; chaque calage est arrivé 2 à 3 s après la fin du tour ; le renommage de `relance.py` puis le second passage ont été suivis sans intervention. Le serveur a ensuite suivi tout l'après-midi (enregistrements 12 à 18, jusqu'à 17 h 19) sans autre erreur que des coupures de connexion du téléphone, qui ne sont plus affichées.
5. **Ouverture au réseau de la maison**, à 14 h 21 : la page, le plan et l'état répondent sur `127.0.0.1` et sur l'adresse Wi-Fi du PC ; une requête au nom d'un autre site reçoit 403. Essayé depuis le PC, puis par l'utilisateur à 14 h 23 : la page s'affiche sur son téléphone (« Oui, elle s'affiche »).
