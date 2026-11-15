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
