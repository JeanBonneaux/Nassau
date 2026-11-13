# Carte vivante — le Roomba 694 suivi en direct sur le plan quadrillé

État au 2026-11-13. Une page à ouvrir sur le PC (plus tard sur le téléphone) : le plan de l'appartement avec ses cases de 50 cm nommées comme aux échecs (`../outils/grille.py`, la convention de `carte_grille.py`), et le robot qui s'y déplace pendant un essai. La position se corrige d'elle-même à chaque tour sur place, et la page dit d'où vient la position affichée.

Ce dossier ne fait que **lire** : aucun ordre n'est envoyé au robot ni au cerveau, aucun fichier de `mesures/` ou de `outils/` n'est modifié, rien ne sort du PC.

## Lancer

```
python roomba694_recherche/code/carte_vivante/serveur.py
```

puis ouvrir http://127.0.0.1:8694 sur ce PC. Le serveur suit l'enregistrement le plus récent de `mesures/` (celui qu'`enregistreur.py` est en train d'écrire) et passe tout seul au suivant quand un nouvel enregistrement commence.

Rejouer un enregistrement terminé, avec les mêmes calculs que le direct :

```
python roomba694_recherche/code/carte_vivante/serveur.py --rejeu exploration9_20261113_124811 --vitesse 8
```

Options : `--debut HH:MM:SS` et `--pause` (rejeu), `--prefixe NOM` (suivre un enregistrement précis), `--port`, `--plan`, `--zones`, `--base U,V`, `--px-par-m`.

**Téléphone.** Par défaut le serveur n'écoute que sur ce PC (`127.0.0.1`). Avec `--ouvert`, il écoute en plus sur l'adresse de ce PC sur le réseau de la maison — sa carte Wi-Fi seulement, pas ses autres cartes réseau — et ne sert que des appareils d'un réseau privé. Il affiche l'adresse à ouvrir sur le téléphone, qui doit être relié au même Wi-Fi que le PC (pas au réseau « Roomba694 » du cerveau, pas aux données mobiles).

```
python roomba694_recherche/code/carte_vivante/serveur.py --ouvert
```

La page montre alors le plan de l'appartement à tout appareil de ce réseau : à ne lancer qu'avec l'accord de l'utilisateur. Il l'a donné le 2026-11-13 à 14 h 20 (« Oui, ouvre-la »), pour cette page et ce réseau ; à redemander si l'un des deux change. Le pare-feu de Windows laissait déjà entrer les connexions vers ce Python sur ce réseau (règle existante, que la carte n'a ni créée ni modifiée).

## Ce que montre la page

- **Le plan quadrillé** : cases de 50 cm, lettres des lignes à gauche et numéros des colonnes en haut (toujours visibles), nom de chaque case dans son coin quand la carte est assez agrandie. Pièces inaccessibles en rouge, base en vert. En bas à gauche, une vue d'ensemble de l'appartement.
- **Le robot** (rond orange, pointe blanche vers l'avant), mis à jour quatre fois par seconde et lissé entre deux mises à jour. Son pare-chocs passe au rouge du côté touché ; les six capteurs optiques s'allument quand quelque chose est tout près.
- **Ce que voit le capteur de distance** : un cône devant le robot jusqu'à l'écho du moment, et un point pour chaque écho passé.
- **Le trajet** : trait plein = tronçon « calé », corrigé par le tour sur place qui l'a suivi ; tirets = tronçon « à l'estime », compté par le robot depuis le dernier calage. Un cercle ambre en tirets autour du robot grandit avec le chemin roulé depuis le dernier calage (2 cm + 4 % du chemin : la marge que `localiser.py` accorde au trajet compté).
- **Les tours sur place** : un rond bleu. Quand un tour recale le robot, une flèche violette va de l'endroit où il se croyait à l'endroit où le calage le place, une bulle l'annonce (« Recalé en D14 : 4 cm vers le bas et la droite, 1,0° ») et le tronçon qui y mène se redresse. Un calage de note inférieure à 0,6 est dessiné en ambre et dit « incertain ».
- **Les contacts du pare-chocs** (croix rouge, avec le côté), **les objets frôlés** (points orange : un capteur optique au-dessus de 200), les obstacles notés par la navigation.
- **La mémoire des obstacles** : ce que le robot a touché ou frôlé lors des enregistrements précédents reste sur la carte, en plus pâle, avec la date dans la fiche (le 2026-11-13 : D14 à 12 h 22, H13 à 12 h 52, J10 à 13 h 05, aux endroits notés par la navigation à 3 pixels près). Seuls comptent les endroits situés par un tour jugé par le filtre. Le résultat est gardé dans `plan_lidar/carte_vivante/memoire_obstacles.json`, hors dépôt : le supprimer le fait recalculer (7 s pour la vingtaine d'enregistrements actuels).
- **Les destinations** données à `explorer3.py` : anneau vert, plein une fois atteinte, barré si elle est abandonnée ; un trait en tirets relie le robot à celle en cours.
- **En haut** : la case du robot en grand, ce qu'il fait, vers où il est tourné, et **d'où vient la position** : « Calé à 12 h 57 par un tour sur place · 1,6 m à l'estime depuis », ou « Position de départ donnée à …, pas mesurée ». Pastille verte : calage récent et sûr ; ambre : estime longue, calage incertain ou position seulement donnée ; rouge : position inconnue.
- **En bas** : le journal de l'essai (calages, contacts, destinations, arrêts) ; toucher une ligne y amène la carte. Toucher un repère de la carte ouvre sa fiche (heure, correction, note du calage).
- Boutons : suivre le robot, voir tout l'appartement, agrandir, réduire ; deux doigts pour agrandir, un doigt pour déplacer.

## D'où vient la position affichée

Position = **dernière ancre + déplacement compté depuis par le cerveau**. Le calcul est celui d'`Estime.suivre` d'`explorer3.py` et de `relance.py` : chaque petit déplacement du journal (`x_mm`, `y_mm` dans le repère du cerveau) est tourné de l'écart entre le cap du plan et le cap du cerveau, et le cap du cerveau est multiplié par l'échelle du gyroscope (1,0045).

Une **ancre** dit « à tel instant le robot était à tel endroit du plan ». La carte n'en invente aucune : elle les lit dans les fichiers que la navigation écrit.

| Source | Fichier | Ce que la carte en fait |
|---|---|---|
| tour sur place jugé par le filtre | `NOM[_x]_stations.json` d'`explorer3.py` (`pose`, `apres`, `plan`) ; `NOM_essai_tours.json` | ancre **mesurée** : la correction est montrée, et répartie sur le tronçon roulé depuis l'ancre précédente, au prorata du chemin |
| départ donné à la navigation | premier tour de `NOM[_x]_stations.json` (`depart`, `avant`) ; en attendant, la ligne « localisation : … autour du pixel » de `NOM_explorer3.txt` | ancre **donnée** : corrige le tronçon si elle est à moins de 25 cm et 20° de la position suivie, sinon c'est un repositionnement (trait violet pointillé) |
| estime de `passage.py` | lignes `POSE=U,V,CAP`, **si** sa sortie est gardée dans un fichier `NOM*passage*.txt` | ancre donnée, à l'heure d'écriture du fichier |
| enregistrement précédent | les mêmes fichiers, pour l'enregistrement d'avant | si le cerveau n'a pas redémarré entre les deux (son horloge `ms` continue), sa dernière position connue plus ce qu'il a compté depuis sert de départ |

Si le cerveau redémarre ou si sa position est remise à zéro, son repère change : la position est dite inconnue jusqu'à l'ancre suivante, et le trajet roulé entre-temps est placé après coup, en remontant depuis cette ancre.

**Limite connue.** `passage.py` n'écrit sa position que sur l'écran de la session qui le lance. Tant que sa position de départ est celle que donne `relance.py`, la carte et lui comptent la même chose. Si la navigation décale cette position à la main (le 2026-11-13, cinq pixels vers le nord à l'ouest de la porte H12), la carte ne le sait pas : elle continue à l'estime depuis le dernier tour sur place, et l'écrit en haut de la page. Remède possible, côté navigation : garder la sortie de `passage.py` dans `mesures/NOM_passage.txt`.

## Fichiers

- `serveur.py` : le serveur local (bibliothèque standard ; `PIL`, et `numpy` avec `scipy` pour les zones rouges). Sert la page, le plan et l'état (`/api/suite?e=&v=` : seulement ce qui a changé depuis la version `v`). Refuse les requêtes dont l'en-tête Host n'est pas une adresse de ce PC (une page d'un autre site ne peut pas lire le plan).
- `suivi.py` : des lignes du journal et des ancres à la position sur le plan ; le tracé par morceaux, les corrections, les contacts, les objets frôlés, le journal.
- `sources.py` : la lecture des fichiers (en direct ou en rejeu) et ce qu'on en tire.
- `page.html` : la page, sans aucune ressource extérieure (un seul fichier ; le plan est demandé au serveur).
- `capture.py` : une image de la page à la taille d'un téléphone (`python capture.py [--url http://127.0.0.1:8694/] [--sortie FICHIER.png]`), rangée par défaut dans `plan_lidar/carte_vivante/`. Le serveur doit tourner : il fait attendre le navigateur quatre secondes (`/api/attendre`) pour que l'image soit prise après l'arrivée des données.
- `essai_direct.py` : l'essai du mode direct sans robot (voir plus bas).

Données privées : le plan reste dans `plan_lidar/` (hors dépôt) et n'est copié nulle part ; les images de la page le montrent et vont dans `plan_lidar/carte_vivante/`. Le nom du réseau Wi-Fi (champ `sta` de `/api/state`) n'est pas lu.

## Vérifications faites le 2026-11-13

1. **Rejeu de `exploration9_20261113_124811`** (trajet C17 → K10, deux contacts). Les quatorze ancres sont retrouvées, et les corrections calculées par la carte sont celles qu'`explorer3.py` a écrites dans `_explorer3.txt`, au millimètre et au dixième de degré : (+29, −34) mm et +1,0° en D14, (+15, −40) mm et +2,0° en E12, (−79, +46) mm en G12, (+19, +68) mm et +1,7° en J12. Les deux contacts sont vus dans le journal (12 h 52 min 57 à gauche, dans la porte H12 ; 13 h 05 min 22 à droite, en K10). Après la porte, la carte suit le robot à l'estime sur 1,6 m jusqu'au pixel (234, 256), la valeur notée au journal § 36 ; le tour final le recale au pixel (239,6 ; 251,0), en **K10**, là où l'utilisateur a confirmé que le robot était.
2. **Rejeu de `exploration10_20261113_132251`** (retour K10 → C17) : départ repris de l'enregistrement précédent (K10), 12 cm et 3,1° d'écart avec le départ donné huit minutes et un passage étroit plus tard, puis quatre tours sur place jusqu'en C17.
3. **Direct simulé** : `python essai_direct.py exploration9_20261113_124811 exploration10_20261113_132251` réécrit ces deux enregistrements dans un dossier temporaire au rythme d'origine (journal ligne à ligne, fichier des tours après chaque tour, renommage de `relance.py`) et les fait suivre par la source « direct » : mêmes ancres, mêmes corrections et même position finale que le rejeu ; un calage est pris en compte 1,2 s après la fin du tour (1,7 s au plus) ; passage d'un enregistrement au suivant sans intervention.
4. **Direct réel**, de 13 h 58 à 14 h 05 : le serveur tournait pendant que la session de navigation menait le robot (`exploration11_20261113_135821`, deux boucles C17 → E15 → D12 → E11 → D14 → C17). Le nouvel enregistrement a été pris seul, avec un départ repris du précédent à 9 mm du départ donné à la navigation ; les données affichées avaient 0,1 s au plus ; chaque calage est arrivé 2 à 3 s après la fin du tour ; le renommage de `relance.py` puis le second passage ont été suivis sans intervention. Contrôlé par l'état du serveur relevé toutes les 2,5 s pendant 75 s (case, vitesse, tours en cours, ancres) et par des captures de la page prises pendant que le robot roulait (Edge, taille d'un téléphone).

Ce jour-là `explorer3.py` a reçu une étape de plus : après le filtre, la position est calée sur des tours déjà faits au même endroit (« repères »). La `pose` écrite dans le fichier des tours en tient compte, donc la carte aussi : en E15 elle montre 26 cm de correction, somme des 13 cm du filtre et des 13 cm des repères.

5. **Ouverture au réseau de la maison**, à 14 h 21 : le serveur écoute sur `127.0.0.1` et sur l'adresse Wi-Fi du PC, pas sur ses trois autres cartes réseau ; la page, le plan et l'état répondent sur les deux ; une requête au nom d'un autre site reçoit 403. Essayé depuis le PC seulement.

Pas encore vérifié : la page sur un vrai téléphone (seulement à la taille d'un téléphone, dans Edge et dans le navigateur de l'application), donc ni la traversée du pare-feu ni le confort au doigt ; les lignes `POSE=` (aucun fichier de ce genre n'existe encore) ; un redémarrage du cerveau en cours d'enregistrement ; une séance de plus d'une demi-heure.
