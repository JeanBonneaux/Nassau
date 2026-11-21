# P — Ce que les trajets du 15 novembre apprennent, et comment se servir des capteurs en roulant

Session de navigation, 15 novembre 2026, après la séance du § 61 du journal. Demande de l'utilisateur : « On a fait beaucoup de run aujourd'hui / Analyse comment on peut apprendre de ces donnés puis comment on peut améliorer en utilisant plus l'info des capteurs en live pourquoi ne pas longer les murs plus souvent ».

Cette note ne refait pas l'audit du 14 (note I) : elle refait ses mesures sur la journée du 15, y ajoute ce que les capteurs de côté voient d'un mur, et dit ce qui en découle. Rien n'a été envoyé au robot pour l'écrire.

**Sources.** Les 14 enregistrements `exploration26` à `exploration40` du 15 (5 h 28 de journal à 20 lignes par seconde). Outils, dans `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/` : `x_budget_temps.py` (audit, inchangé) et `nav_capteurs_en_direct.py` (nouveau ; résultats dans `results_nav_capteurs_en_direct_20261115.txt`).

## En bref

- **Le robot roule 11 % du temps.** Sur les six enregistrements de trajet du 15 (3 h 02, 92 m), il avance pendant 20 minutes. Le reste : 59 % à attendre l'ordre suivant, 19 % à tourner sur lui-même, 11 % en petits arrêts.
- **Il a tourné sur lui-même l'équivalent de 166 tours pour 92 m** : 570 ordres de rotation et 47 tours sur place. Chaque regard de côté fait pivoter le robot entier ; sur toute la journée, 796 pivots suivis d'un arrêt pour lire.
- **Pourquoi il ne longe pas les murs : en roulant, il ne les voit pas.** Le capteur de distance regarde devant (son servo est limité à 30° parce que ses fils sont courts). Les capteurs optiques de côté ne réagissent qu'à moins de 6 cm du flanc, et pas toujours.
- **Les contacts** : 17 dans la journée, tous avec « rien devant » au capteur de distance. Les capteurs optiques du pare-chocs en annonçaient 7 (41 %) dans la seconde et demie d'avant ; le pilotage n'en tenait pas compte.
- **Ce qui ferait le plus gagner**, dans l'ordre : un seul programme qui enchaîne un trajet connu au lieu d'ordres donnés un à un ; un réflexe sur les capteurs optiques ; le recalage automatique sur les signaux fixes (base, seuil, portes) ; puis le capteur de distance tourné vers le côté en roulant, qui demande des fils plus longs et un firmware v15.
- **Ajout du 15 au soir** : la liste de travail est au § 8. Elle réunit ces propositions, celles de la session de revue, et l'essai du gyroscope que l'utilisateur a accepté pour la prochaine séance.

## 1. Où est passé le temps

Six enregistrements de trajet du 15 : `exploration33`, `34`, `35` (la boucle de midi), `36`, `39`, `40` (la cuisine et le retour). Mesuré avec l'outil de l'audit.

| | Temps | Part |
|---|---|---|
| Durée totale | 10 900 s (3 h 02) | |
| Chemin | 92 m, soit 8 mm/s en moyenne | |
| Avancer (71 mm/s en moyenne pendant les avances) | 1 232 s | 11 % |
| Tourner pour viser ou pour regarder de côté | 1 351 s | 12 % |
| Tours sur place complets (47) | 716 s | 7 % |
| Arrêts de moins de 5 s (enchaînement de deux ordres, lectures) | 1 170 s | 11 % |
| Arrêts de 5 à 30 s (la session décide de l'ordre suivant) | 2 140 s | 20 % |
| Arrêts de plus de 30 s (la session analyse, relance un outil, attend une réponse) | 4 250 s | 39 % |

Rotations : 570 ordres, 41 958°, plus 17 860° de tours sur place : 166 tours complets en tout, 1,8 tour par mètre parcouru. À 100 mm/s sans arrêt, les 92 m prendraient 15 minutes.

Comparé au 14 (note I, § 2.1 : 17,5 % à avancer, 49 % à l'arrêt) : pas mieux, plutôt moins bien, parce que le 15 a été fait de passages nouveaux menés ordre par ordre. Même le retour demandé « rapidement » (`exploration40`) : 16 % à avancer, à 90 mm/s, et 55 % en arrêts de plus de 5 s.

**Ce que cela dit.** Ce ne sont ni les roues ni la vitesse qui limitent. C'est d'abord la façon de piloter : une session qui donne un ordre, lit le résultat, réfléchit, donne le suivant. Ensuite, les pivots.

## 2. Les contacts : ce que les capteurs voyaient avant

17 contacts du pare-chocs en roulant dans la journée, à 61 mm/s en médiane (52 à 111).

- Capteur de distance : rien à moins de 30 cm dans 17 cas sur 17. Il regarde droit devant, les contacts sont sur les côtés du pare-chocs (12 à gauche, 5 à droite) ou contre des choses basses ou fines.
- Capteurs optiques du pare-chocs, plus forte lecture dans la seconde et demie d'avant : 25, 36, 43, 48, 48, 52, 52, 61, 61, 80, 131, 243, 315, 404, 424, 485, 596. Au repos ils lisent 0 à 50 selon le capteur.
- **7 contacts sur 17 étaient annoncés par une lecture de 100 ou plus** (10 sur 17 au seuil de 60, trop près du repos pour être sûr). Le préavis, quand la lecture reste haute jusqu'au contact : 1 s environ, 10 cm de chemin.
- 7 autres n'étaient vus par aucun capteur (rien au-dessus de 52) : pieds de chaise, choses basses ou sombres. Ceux-là ne s'évitent qu'en connaissant l'obstacle ou en roulant doucement dans les endroits encombrés.

Aujourd'hui `passage.py` appelle les avances avec une alarme optique à 3 000, autant dire coupée (réglée ainsi pour les passages étroits, où un mur proche la déclenchait).

## 3. Longer un mur : ce que le robot voit de côté

Mesuré sans essai nouveau, avec les regards de côté déjà faits : à chaque arrêt où le robot a pivoté de 90° pour lire la distance d'un mur, cette distance est comparée à la lecture du capteur optique du même côté quand le robot était dans l'axe. 1 217 paires.

| Distance du mur lue de côté | Jeu entre le flanc et le mur (si le capteur est à 10 cm du centre) | Paires | Capteur optique de côté, médiane (quartiles) | Lectures de 60 ou plus |
|---|---|---|---|---|
| 20 à 60 mm | flanc contre le mur | 9 | 32 (23 à 60) | 33 % |
| 60 à 80 mm | 0 à 1 cm | 4 | 66 (5 à 132) | 50 % |
| 80 à 100 mm | 1 à 3 cm | 7 | 8 (8 à 8) | 0 % |
| 100 à 130 mm | 3 à 6 cm | 13 | 36 (8 à 85) | 38 % |
| 130 à 170 mm | 6 à 10 cm | 41 | 13 (11 à 15) | 0 % |
| 170 à 300 mm | 10 à 23 cm | 138 | 4 à 10 | 0 % |
| plus de 300 mm | plus de 23 cm | 1 005 | 8 à 18 | moins de 1 % |

Au repos (mur à plus de 30 cm) : médiane 11, 95 % des lectures sous 24. Pendant les 30 minutes d'avance de la journée, un capteur optique de côté a lu 60 ou plus pendant 20 secondes (1 %).

**Ce que cela dit.** Au-delà de 6 cm de jeu, les capteurs optiques de côté ne lisent jamais rien. En deçà, ils réagissent une fois sur trois à une fois sur deux, selon la surface (33 paires seulement si près : un ordre de grandeur). Le capteur de mur d'origine du robot n'apporte rien de plus : c'est le capteur optique droit sous un autre nom (corrélation 0,99, résultat de la session de revue le 14). **Tel qu'il est monté, le robot ne peut longer un mur qu'en le frôlant**, là où les plinthes, les cadres de porte et les pieds de meuble font toucher. Le seul capteur qui lit un mur à 20-60 cm est le capteur de distance, et il regarde devant.

C'est la réponse à « pourquoi ne pas longer les murs plus souvent » : pour lire un mur de côté, il faut aujourd'hui arrêter le robot et le faire pivoter. 796 fois dans la journée.

## 4. D'où sont venues les erreurs de position du 15

Relevé dans le journal (§ 58 à 61), pour savoir quel signal les aurait évitées.

| Erreur | Cause trouvée | Signal qui l'aurait montrée en roulant |
|---|---|---|
| Cap faux de 10° de 9 h 55 à 12 h 26 | pivots après des patinages | un mur longé (le cap se lit sur la pente de la distance de côté) |
| Deux contacts dans le passage de la pièce de la base, six au retour de la cuisine | cap décalé de quelques degrés, robot de 10 à 15 cm de côté | la distance de côté, lue en continu |
| Position fausse de 40 cm le long du couloir (note du filtre 0,84) | un couloir se ressemble d'un bout à l'autre | les portes qui s'ouvrent sur le côté pendant qu'on le longe |
| 28 cm d'erreur à l'arrivée devant la base | estime et filtre d'accord et faux | les faisceaux de la base (lus seulement à la demande de l'utilisateur) |
| 22 cm d'écart entre deux repères autour du seuil de la cuisine | patinage sur la baguette | la baguette elle-même, vue par les capteurs de vide |
| Un mètre d'écart au fond de la cuisine | non trouvée ; le plan ne correspond pas aux meubles | — |

## 5. Ce que le robot lit déjà en roulant, 20 fois par seconde, et dont le pilotage ne se sert pas

| Signal | Ce qu'il donne | Preuve dans les données |
|---|---|---|
| Six capteurs optiques du pare-chocs | un obstacle à moins de 10 cm devant ou sur le côté avant | 7 contacts sur 17 annoncés (§ 2) |
| Quatre capteurs de vide | les changements de sol : la baguette du seuil de la cuisine (943 puis 3 266 pour 2 650 sur le parquet), le bord du tapis ; position le long du trajet au centimètre, et angle du robot par rapport à la baguette | § 61.4 ; `rv_signaux_oublies.py` de la session de revue |
| Trois récepteurs infrarouges | à moins de 2 m de la base : de quel côté de son axe, à 1 cm près | § 59, § 61.9 |
| Compteurs des roues contre gyroscope, courants des roues | une roue qui patine ou qui bute : l'estime n'est plus sûre | seuil : 30 cm de patinage, 700 à 800 mA |
| Capteur de distance, devant | ce qui approche ; et le patinage, quand il ne se rapproche pas alors que le chemin compté monte | § 60, § 61.6 |
| Accéléromètre | le robot penché : une roue sur un obstacle | § 61.6 |

Ce qui manque à cette liste : **la distance de côté**. Elle n'existe aujourd'hui qu'à l'arrêt.

## 6. Propositions, dans l'ordre de ce qu'elles rapportent

Les trois premières ne demandent ni pièce ni firmware.

1. **Un trajet connu se rejoue d'une seule commande.** Les lignes qui ont marché le 15 (la porte H18, le seuil par biais puis pivot, la ligne du passage étroit, le détour de la pièce centrale) deviennent les étapes d'un trajet écrit, avec ses vérifications, que le programme du PC enchaîne ; la session surveille au lieu de décider chaque geste. C'est la proposition A2 de la note I, que les 59 % d'attente du 15 rendent plus pressante. Ordre de grandeur, non mesuré : base → coin de la cuisine, 16 m, en moins de dix minutes au lieu d'une heure et demie.
2. **Un réflexe sur les capteurs optiques pendant les avances** : ralentir à 50 mm/s dès qu'un capteur dépasse son repos de 60, s'arrêter et regarder s'il le dépasse de 150 ; un niveau de repos par capteur. Attendu d'après le § 2 : quatre contacts sur dix évités. À couper dans les passages de moins de 60 cm, où le mur est toujours proche.
3. **Se recaler tout seul sur les signaux fixes** : traversée des faisceaux à chaque départ et à chaque arrivée devant la base ; la baguette du seuil comme repère (position et cap) ; les deux montants d'une porte lus au passage.
4. **Le capteur de distance tourné vers le côté en roulant** (idée de l'utilisateur du 15 à 15 h 50 ; proposition C1 de la note I). Trois choses à faire ensemble :
   - le montage : la limite de 30° du servo a été posée le 9 parce que les fils du capteur sont courts (journal, 9 novembre). Tourner lentement ne les rallonge pas : il faut voir sur une photo s'ils permettent 90°, sinon quatre fils de 20 à 30 cm (moins de 10 $) ;
   - le firmware v15 : servo lent jusqu'à 90°, angle du servo écrit avec chaque lecture, cap retouché pendant une avance (B3 et B5 de la note I), et le regard vers l'avant gardé un instant sur deux ;
   - le PC : le prototype `code/outils/suivi_lateral.py` de l'audit, essayé en simulation seulement (couloir de 3,9 m en 41 s au lieu de 169 s par arrêts).
   Ce que cela changerait le 15 : les 796 pivots de regard, les contacts par décalage de côté (§ 4), et le cap, qui se lirait sur les murs au lieu de dépendre du seul gyroscope.
5. **Plus tard, avec une pièce** : deux petits capteurs de distance fixes sur les côtés (C2), ou un LiDAR (C3).

## 7. Limites de cette analyse

- Le budget de temps compte comme « arrêt » les 19 minutes de panne de l'enregistreur seulement en partie (le robot n'était pas enregistré), et les attentes de réponse de l'utilisateur : la part des arrêts longs n'est pas toute imputable au pilotage.
- Le tableau du § 3 a peu de paires à moins de 13 cm (33 sur 1 217) : la portée de 5 à 6 cm est un ordre de grandeur. Il suppose que le mur lu de côté est parallèle à l'axe du robot, ce qui est vrai dans le couloir et le passage de la cuisine, moins ailleurs.
- Les « 796 pivots suivis d'un arrêt pour lire » sont comptés d'après le journal seul (un pivot, puis au moins 0,6 s d'immobilité au même endroit) : c'est le nombre de regards à un dixième près, pas un décompte des ordres.
- « Annoncé » au § 2 veut dire qu'un capteur a dépassé 100 dans la seconde et demie d'avant, pas qu'un réflexe aurait suffi : dans cinq cas la lecture retombe avant le contact.
- Les gains du § 6 sont des ordres de grandeur ; seul le chiffre du couloir vient d'une simulation, aucune n'est une mesure sur le robot.

## 8. La liste de travail, au 15 au soir

**D'où elle vient.** Le 15 vers 18 h, la session de revue a demandé à l'utilisateur s'il fallait ajouter un essai d'une minute du gyroscope à la prochaine séance de pilotage. Sa réponse, que je tiens de l'autre session (son message, et sa note O § 5.15.8) et non de lui directement : « Yes add it and text that session to add anything you said plus the thing for the radar I suggested to it ». Cette liste réunit donc l'essai, les propositions de la revue (note O § 5.15.7), celles du § 6 et son idée du capteur de distance tourné à 90°. **C'est une liste de travail, pas un accord** : installer un firmware, toucher au montage ou dépasser la butée du servo se demandent au moment de le faire. Rien n'a été envoyé au robot pour l'écrire ; le code du cerveau (v14) a été relu.

### 8.1 À la prochaine séance de pilotage

1. **L'essai du gyroscope** (essai 11 de la note O), accepté par l'utilisateur. Une minute, au point P devant la base, l'utilisateur à côté du robot.
   - *La question.* Le facteur du gyroscope a valu 1,0035 à 1,0056 selon les jours. La revue pense que la carte est penchée de 5,5° et que le cerveau ne compte qu'un axe. Si c'est cela, pendant un tour sur place les axes X et Y lisent environ −9 % et −4 % de ce que lit Z (−2,5 et −1,0 °/s pour 28 °/s) ; s'ils restent à moins de 0,3 °/s de zéro, l'explication est fausse.
   - *Le déroulement.* Robot à l'arrêt, en mode Safe, sur l'axe de la base vérifié aux faisceaux, enregistreur en marche. Une touche `g` (`/api/cmd?c=g`). Un tour sur place ordinaire (`/api/tour?go=1`) et, pendant qu'il tourne, une touche `g` deux fois par seconde. Une touche `g` après l'arrêt. Un second tour, pareil. Les lignes « gyroscope (°/s) : X … Y … Z … » arrivent dans `NOM_console.txt` ; la session de revue les dépouille une fois la séance close.
   - *Relu dans le code avant de l'inscrire.* `g` fait partie des commandes que `/api/cmd` accepte (`web.ino`, ligne 139) et n'appelle que `printImu()` : trois lignes, écrites par le tampon de la v11 qui n'attend pas le Wi-Fi. Elle n'est pas dans les touches qui arrêtent un tour ou une avance (`roomba694_wifi.ino`, lignes 1282 et 1283). Les trois axes affichés sont corrigés du zéro, remesuré pendant la préparation de chaque tour. Un tour : 380° vers la gauche, 62 mm/s aux roues, une treizaine de secondes.
   - *Deux écarts par rapport à ce que la revue demandait* : deux lectures par seconde au lieu d'une (une vingtaine par tour au lieu d'une dizaine, le bruit d'une lecture n'étant pas connu), et deux tours d'office.
   - *Avant de commencer* : si le robot a été posé sur sa base pour charger, il faut le tirer à la main devant elle (posé dessus, il refuse de rouler).
2. **Les deux tours du point P** (essai 12) : un au départ et un au retour de la sortie, au même endroit. Ils se font déjà ; ils donnent le facteur du gyroscope du jour (`rv_cap_profil.py`, outil de la revue).
3. **Départ et arrivée calés sur les faisceaux de la base** (journal § 61.9) : la traversée d'ouest en est, puis la lecture des deux faisceaux à l'arrêt.
4. **Ce que seul l'utilisateur peut faire**, demandé et pas encore fait : une photo du capteur de distance et de ses fils, vus du dessus ; à la règle, du devant des deux « yeux » du capteur au devant du pare-chocs (essai 8), et de l'axe du servo au devant du capteur (cette longueur s'ajoutera à chaque lecture de côté) ; au mètre, la largeur de l'encadrement de la porte H18, qui sépare la place du capteur de l'échelle du plan (note O § 5.15.6).

### 8.2 Sans rien changer au robot : les outils du PC

D'abord les points 1 à 3 du § 6 : le trajet rejoué d'une seule commande, le réflexe sur les capteurs optiques, le recalage sur les signaux fixes. S'y ajoutent quatre propositions de la revue ; ce sont mes outils, j'en décide.

| Proposition de la revue | Ce que j'en fais |
|---|---|
| **Ne plus accepter un calage du filtre sur sa seule note** : pour 40 tours sur 45 du 15 après-midi, un autre endroit à plus de 15 cm note aussi bien ou mieux (`rv_calage_large.py`) | Retenu dès la prochaine séance, comme règle de pilotage : un calage n'est pris que si un second témoin le confirme (les roues depuis le dernier point sûr, les faisceaux, la baguette du seuil, un montant de porte), surtout dans un couloir, à l'entrée de la cuisine et après un patinage. À écrire ensuite dans l'outil des tours sur place, qui doit montrer les autres endroits possibles et pas seulement le meilleur |
| **La baguette du seuil de la cuisine comme repère** : les capteurs de vide y lisent plus de 3 200 ; le centre du robot est à 15 cm d'elle quand les deux capteurs de devant la lisent | Retenu, c'est une partie du point 3 du § 6. À vérifier d'abord sur mes enregistrements du 15 (`exploration39` et `exploration40`), dans les deux sens de passage |
| **Le facteur du gyroscope du jour au lieu de 1,0045** | Retenu. 1,0045 est écrit en dur dans `passage.py` et `balise_base.py`, et par défaut dans `centrage.py`, `localiser.py`, `relance.py` et `trajet_passages.py` : une option commune, et la mesure du jour sur les deux tours de P. Sans objet le jour où le firmware compte la rotation autour de la verticale (§ 8.3) |
| **Quatre repères à reprendre**, relevés par la revue sur les enregistrements de l'après-midi (note O § 5.15.3 et 5.15.4) : la baguette du seuil à u = 751 et non 775 (colonne 29 et non 30) ; l'entrée de la cuisine vers (758 ; 68), case C29 ; le point des deux tours que j'appelle « D28 » vers u = 700, donc dans la colonne 27 ; le milieu de la porte H18 entre u = 443 et 452 pour 456 lu, à cheval sur les colonnes 17 et 18 | À vérifier sur place avant de corriger mes repères : mon estime était décalée dans cette partie de l'appartement (65 cm vers l'est dès le seuil d'après la revue, deux cases au fond de la cuisine d'après la photo de l'utilisateur), et je ne sais pas encore lequel des deux relevés déplacer. Les noms « porte H18 » et « D28 » restent ceux dont on se sert |

### 8.3 Firmware v15 : rien n'est écrit

La règle du projet vaut pour chacun de ces points : une modification à la fois, compilée, chargée, vérifiée robot immobile avant tout essai en mouvement, et aucun téléversement sans l'accord écrit de l'utilisateur. Dans l'ordre que je propose :

1. **Un sens au choix pour le tour sur place** (revue). Aujourd'hui tous les tours vont vers la gauche (`tour.ino`) : une sortie cumule 9 000 à 11 500° de rotation nette, et un demi-millième d'erreur sur le facteur du gyroscope y fait 5°. En alternant gauche et droite, cette somme tombe presque à zéro. Côté PC, aucun de mes outils n'a jamais lu un tour vers la droite (`balise_base.py`, `relance.py`, `localiser.py`, la carte vivante) : à vérifier et adapter avant le premier.
2. **Les trois axes du gyroscope dans le journal à 20 lignes par seconde** (revue) : pour voir ce que fait la carte quand une roue patine ou monte sur le seuil. `enregistreur.py` et `pilote.py` comptent les colonnes (journal § 61.5) : à adapter dans le même geste.
3. **L'angle du servo dans le journal, avec chaque lecture du capteur de distance** (B5 de la note I) : préalable au capteur tourné.
4. **La console du cerveau qui lâche un client muet** : la panne de 19 minutes du 15 (journal § 61.5).
5. **La rotation comptée autour de la verticale mesurée** (revue) : les trois axes projetés sur la pesanteur relevée à l'arrêt ; il n'y aurait plus de facteur à régler. Seulement après l'essai 11, et s'il confirme l'inclinaison.
6. **Le servo lent jusqu'à 90° et le cap retouché pendant une avance** (idée de l'utilisateur ; B3 de la note I) : voir § 8.4, pas avant d'avoir vu les fils.

### 8.4 L'idée de l'utilisateur : le capteur de distance tourné à 90° en roulant

Elle est au § 6, point 4. Ce que la revue y ajoute :

- **elle fournit le second témoin qui manque** (§ 8.2) : un mur lu de côté donne l'écart au mur et un cap qui ne dépend pas du gyroscope ; les montants de porte qui défilent donneraient la position le long d'un couloir, là où le filtre s'est trompé de 40 cm le 15 (journal § 61.8). Non essayé ;
- **deux constantes du firmware sont en jeu, pas une** (relu dans `radar.ino`) : la butée du servo, `RADAR_BUTEE_MAX = 30`, posée le 9 à la demande de l'utilisateur parce que les fils du capteur sont courts, et la taille de la carte des distances, `RADAR_SPAN_MAX = 80`, qui s'arrête à 80° de chaque côté ;
- **la place du capteur compte davantage** : les mesures à la règle du § 8.1 deviennent un préalable.

L'ordre : la photo des fils ; s'ils sont trop courts, quatre fils plus longs posés par l'utilisateur, pas à pas ; les mesures à la règle ; le firmware (§ 8.3, points 3 et 6), essayé d'abord robot immobile en regardant les fils pendant que le servo tourne ; enfin le prototype `suivi_lateral.py` de l'audit sur le robot, dans le couloir. La butée ne change qu'avec la confirmation de l'utilisateur.

### 8.5 Toujours en attente

Les essais 6 et 7 de la revue (menés par elle, sur le mot de l'utilisateur) ; le sud de la cuisine ; l'approche lente d'un vrai mur (essai 4) ; et la réponse de l'utilisateur sur l'ordre : je propose de commencer par le trajet rejoué d'une seule commande (§ 6, point 1), qui ne change rien au robot.

## 9. Le plan pour la vitesse, au 21 novembre

**D'où il vient.** Le 21 novembre l'utilisateur écrit : « Tu as raison, il est lent. Et ça devrait être notre focus principal de pouvoir l'accélérer. Peut-être en pensant à la façon de voir les murs de côté », puis « n'oublie pas ma requête de vitesse ». La vitesse passe donc avant le reste. Ce paragraphe remplace l'ordre du § 8 pour tout ce qui touche à la conduite ; le § 8 reste valable pour le reste.

### 9.1 Le but, en chiffres

Le 15, sur six trajets : 92 m en 3 h 02, soit un demi-mètre par minute. Le robot avance 11 % du temps, attend mon ordre suivant 59 % du temps, tourne sur lui-même 19 % du temps (§ 1). Les règles du projet plafonnent la vitesse à 150 mm/s : à cette vitesse, 92 m se roulent en dix minutes. **Le but : un trajet connu dix fois plus vite qu'aujourd'hui, sans toucher au plafond de 150 mm/s.** Ce qui manque n'est pas de la vitesse de roues : c'est de ne plus s'arrêter.

### 9.2 Trois freins, trois réponses

| Frein (mesuré le 15) | Réponse | Ce qu'il faut |
|---|---|---|
| 59 % du temps à attendre mon ordre | Un programme du PC enchaîne tout un trajet connu et ne m'appelle que si quelque chose ne va pas | Le trajet rejoué d'une commande (§ 6, point 1), et un cerveau qui accepte une correction en route |
| 19 % du temps à tourner sur place pour se situer (166 tours) | Lire un mur de côté en roulant : l'écart au mur et le cap viennent en continu | Le capteur de distance tourné à 90° (firmware v15), puis le suivi de mur |
| Un arrêt à la fin de chaque avance (2 m au plus) et à chaque correction de cap | Corriger le cap et prolonger l'avance pendant qu'elle se fait | Firmware v16, à écrire |

### 9.3 Les étapes, dans l'ordre

1. **Firmware v15 : le capteur jusqu'à 90°, lentement.** Écrit et compilé le 21, pas installé (journal § 62.3). Essai robot immobile au go de l'utilisateur (`essai_servo_lent.py`).
2. **Une ligne droite de 2 m le long d'un mur, capteur tourné**, sans rien corriger : ce que le capteur lit en roulant (bruit, trous, cadres de porte). Les lectures viennent de `/api/state`, que l'enregistreur relit jusqu'à dix fois par seconde (`--etat 0.1`) ; aucun changement de firmware.
3. **Firmware v16 : la retouche en route.** Pendant une avance, `/api/mouv?cap=…` déplace le cap visé et `&plus=MM` prolonge la distance, sans arrêt ; si le PC se tait, l'avance va à son terme et s'arrête, comme aujourd'hui. Dans le même firmware : la dernière distance lue et l'angle du servo dans le journal à 20 lignes par seconde (§ 8.3, points 2 et 3), ce qui oblige à adapter `enregistreur.py` et `pilote.py` du même geste.
4. **Longer un mur** (`suivi_lateral.py` de l'audit, un seul côté) : d'abord le couloir. But : 3,9 m en moins d'une minute, contre 5 min 19 le 14. **Avec les capteurs optiques dès le départ** (demande de l'utilisateur du 21, § 9.5) : le capteur de distance donne l'écart au mur, le capteur optique du flanc, du côté du mur, dit quand le robot le serre de trop près.
5. **Le trajet rejoué d'une commande** : une liste de tronçons (mur à longer et à quelle distance, cap à tenir, porte, recalage sur les faisceaux de la base ou la baguette du seuil), exécutée sans moi.
6. **Garder un œil devant.** Capteur tourné de côté, plus rien ne regarde devant que le pare-chocs. Les capteurs optiques du pare-chocs annonçaient 7 contacts sur 17 le 15 (§ 2) : un réflexe du cerveau qui ralentit quand ils voient quelque chose. À faire avec le suivi de mur et non après lui (§ 9.5).
7. **Le gyroscope compté sur son axe vrai** (journal § 62.2) : moins de cap perdu, donc moins de recalages.

Chaque firmware reste une modification à la fois, vérifiée robot immobile, installée avec l'accord de l'utilisateur.

### 9.4 Ce que la simulation dit déjà (21 novembre, sans le robot)

Outil nouveau `code/outils/essai_longe_mur.py`. L'essai de l'audit supposait deux capteurs de côté ou un servo rapide qui alterne gauche, devant, droite. La v15 fait autre chose : au-delà de 30° le servo ne tourne qu'à 5° par seconde, donc en roulant le capteur reste tourné d'un seul côté et y lit le mur dix fois par seconde. Même couloir simulé que l'audit (95 cm, puis 84, 73 et 68 ; une ouverture de 80 cm à droite ; 3,9 m), mêmes 75 départs (décalé de 15 cm ou non, cap faux de −6 à +6°).

| Réglage | Sans contact jusqu'au bout | Durée des 3,9 m | Jeu le plus petit |
|---|---|---|---|
| Longer le mur à la distance du départ | 46 à 50 sur 75 | 27 à 36 s | 0 à 26 mm |
| Longer le mur à 342 mm (le milieu de la partie étroite, lu sur le plan), à 100 mm/s | 75 sur 75 | 36 s | 15 à 39 mm |
| Le même, à 130 mm/s | 75 sur 75 | 28 à 29 s | 9 à 35 mm |
| Le même, à 147 mm/s | 75 sur 75 | 27 à 28 s | 9 à 34 mm |
| Le même, avec une lecture sur cinq perdue et 0,15 s de retard en plus | 75 sur 75 | 27 à 36 s | 7 à 36 mm |

Trois choses à en retenir. **Un seul côté suffit**, à condition de dire au robot à quelle distance du mur rouler : « la distance du départ » échoue une fois sur trois dès que le couloir se resserre ; cette distance se lit sur le plan, tronçon par tronçon. **Le PC peut tenir la boucle** (cinq corrections par seconde, un quart de seconde de retard) : le mettre dans le cerveau ne gagne que 7 à 13 mm de jeu ; il n'y a donc pas besoin d'un gros firmware pour commencer, la retouche en route suffit. **L'axe du couloir est retrouvé à moins d'un degré** (0,2 à 0,7° en médiane, 2° au pire) par la seule pente du mur : un cap qui ne dépend pas du gyroscope. Durée : une demi-minute au lieu de cinq minutes.

**Limites.** C'est une simulation, plus indulgente que l'appartement : vrais murs avec plinthes, cadres de porte, objets posés, et un capteur à ultrasons qui ne lit rien sur une surface molle ou très oblique. Le jeu de 7 à 15 mm au pire, du côté de l'ouverture, est petit. Rien de tout cela n'a roulé.

### 9.5 Ce que les essais du 21 et l'utilisateur ajoutent au plan

**Ce qui est acquis le 21** (journal § 62 à § 67) : le capteur de distance tourne lentement au-delà de 30° (firmware v15), l'utilisateur l'oriente lui-même depuis la page (v16), et, tourné à gauche, il lit un mur pendant que le robot roule : son relief et sa fin au bon endroit du trajet, une lecture tous les 13 mm, un bruit de 2 cm en roulant (1 cm à l'arrêt). Le côté droit ne lisait pas ce qu'il devait à 15 h 15 ; l'utilisateur dit l'avoir réparé, ce n'est pas remesuré.

**Le côté droit compte pour plus tard** (remarque de l'utilisateur) : la brosse latérale est à droite. Pour nettoyer le sol au pied d'un mur, le mur devra être à droite du robot. Un seul côté suffit pour aller vite ; les deux serviront pour nettoyer.

**Le capteur de distance peut servir même tout près du mur** (correction de l'utilisateur à ce que j'avais écrit) : j'avais dit qu'il ne conviendrait pas pour serrer un mur à 1 ou 2 cm, parce qu'il ne mesure pas en dessous de 2 cm. C'était mal raisonné : le capteur est sur le dessus du robot, vers son axe, et non sur son flanc. Flanc du robot à 1 ou 2 cm du mur, il en est encore à une quinzaine de centimètres (le demi-diamètre du robot, 17 cm, moins son propre décalage vers le mur, plus l'écart). Ce qui reste à mesurer n'est pas sa portée mais sa précision à cette distance.

**Les capteurs optiques entrent dans le suivi de mur dès le départ** (demande de l'utilisateur : « n'oublions pas d'inclure les capteurs optiques dans le plan du code pour bien longer »). Trois entrées, trois rôles :

| Capteur | Ce qu'il donne | Rôle dans le suivi de mur |
|---|---|---|
| capteur de distance, tourné du côté du mur | l'écart au mur, de 15 cm à 2 m, à 1 ou 2 cm près, dix fois par seconde | tenir l'écart et, par la pente de l'écart le long du chemin, l'angle du robot par rapport au mur |
| capteur optique du flanc, du côté du mur (celui de droite est aussi le « capteur de mur » du robot, note J) | une valeur qui monte quand une paroi est à moins de 6 cm du flanc (§ 3) ; pas une distance | garde-fou : s'écarter quand il monte ; plus tard, serrer le mur de près pour le nettoyage |
| capteurs optiques de devant (quatre) | une valeur qui monte devant un obstacle proche ; 7 contacts sur 17 annoncés le 15 (§ 2) | ralentir, puis s'arrêter : capteur de distance tourné de côté, c'est le seul regard vers l'avant avec le pare-chocs |

Ces six capteurs sont déjà lus par le cerveau vingt fois par seconde (`robot.light` dans `/api/state`, colonnes `lb_*` du journal). Le ralentissement devant vit **dans le cerveau**, où il ne dépend pas du Wi-Fi (firmware v17, journal § 69) ; la tenue de l'écart au mur reste sur le PC (§ 9.4), et le garde-fou du flanc aussi pour commencer : le robot se rapproche d'un mur qu'il longe à quelques millimètres par seconde, dix lectures par seconde y suffisent (corrigé le 21 au soir : j'avais d'abord écrit qu'il devait être dans le cerveau). Les seuils sont à tirer des enregistrements du 15 et du 21, pas à deviner.

Ordre révisé : (a) firmware v17 : retouche du cap et de la distance pendant une avance, et ralentissement sur les capteurs optiques de devant ; (b) la boucle du PC qui longe un mur, avec le capteur du flanc comme garde-fou ; (c) le trajet rejoué d'une commande. Chaque firmware reste une modification vérifiée robot immobile et installée avec l'accord de l'utilisateur.

**Fait le 21 au soir** (journal § 69) : le firmware v17 est écrit et compilé, pas installé ; `longe_mur.py` est écrit, pas essayé ; la simulation refaite avec 20 mm de bruit garde 43 départs sur 45 sans contact du côté gauche dans le couloir étroit (75 sur 75 avec 4 mm), les deux contacts étant sur une avancée du mur que le capteur de côté ne peut pas voir venir.
