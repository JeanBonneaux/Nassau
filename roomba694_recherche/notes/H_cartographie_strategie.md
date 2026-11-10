# H — Cartographier une pièce avec ce Roomba : stratégie

Rédigé le 2026-11-09 au soir, après les premiers essais du radar sur le matériel. **État : stratégie acceptée par l'utilisateur (« Commence avec 1 ») ; l'étape 1 est programmée, pas encore essayée avec le robot en mouvement.** Mots employés avec l'utilisateur : le cerveau (ESP32), le capteur de distance (HC-SR04), le servo (SG90), le gyroscope (GY-521).

**Suite du 2026-11-10** : une recherche plus poussée sur ce que les capteurs actuels peuvent encore donner (revue du firmware et du câblage, analyse des enregistrements de `mesures/`, idées classées avec leur premier essai, ce qui ne marchera pas) est dans [`../reports/Roomba 694 sensor exploitation ideas.md`](../reports/Roomba%20694%20sensor%20exploitation%20ideas.md), en anglais comme la demande ; les notes de travail et les scripts d'analyse sont dans `../research_notes/`. Ce rapport revoit plusieurs résultats de la présente note à la lumière des enregistrements (le rapport roues / gyroscope de 0,963, ce que prouve le recouvrement de 20° des tours, la largeur des paliers, l'essai du carré) : le lire avant de s'appuyer sur ces chiffres. Rien de ce rapport n'a été essayé sur le robot.

### Ce que les mesures ont changé au rapport (tenu à jour)

| Date | Affirmation du rapport | Mesure sur le robot | Conséquence |
|---|---|---|---|
| 2026-11-10 | Sur la base alimentée, le mode Safe ne peut pas être gardé (lecture de la spécification) ; le cerveau ne pourrait donc ni quitter la base ni y monter | Mode Safe obtenu et gardé 10 s sur la base, robot à l'arrêt ; la charge s'arrête pendant ce temps ([journal_wifi.md § 20](../code/journal_wifi.md)) | Quitter la base en reculant tout droit devient un essai à faire (roues jamais essayées sur la base) |
| 2026-11-10 | (absent du rapport) | Sur sa base, liaison fermée, le robot envoie une ligne « bat: … » par seconde ; le firmware v5 la prend pour un réveil du robot, puis pour des lectures incohérentes | Défaut de plus à corriger à l'étape 1 ; signal gratuit « je suis sur ma base » |

| 2026-11-10 | Au réglage 150 le robot roule à 142,5 mm/s (5 paliers de 28,5 mm/s) | 149,5 mm/s en ligne droite, roue gauche 147,0 et roue droite 151,9 ([journal_wifi.md § 21](../code/journal_wifi.md)) | L'idée des paliers ne tient pas à ce réglage ; à mesurer à plusieurs réglages |
| 2026-11-10 | En ligne droite, +1,33 ° par mètre vers la gauche, vus par le gyroscope seul | +9,3 ° par mètre au gyroscope, +7,7 d'après les roues (20 m, 13 avances) | Le robot tire à gauche ; une ligne droite décidée par le cerveau doit tenir son cap au gyroscope |
| 2026-11-10 | Rapport roues / gyroscope : 0,981 sur le sol principal, 1,022 sur la zone à motifs | 0,987 et 1,014, mesurés à 5 lectures par seconde, cap et compteurs lus au même instant | Confirme que ce rapport dépend du sol |
| 2026-11-10 | Le mode Safe n'arrête pas les roues sur un choc (lecture de la spécification) | Vu : 0,4 s de poussée, le robot grimpe sur l'obstacle, roue levée, retombée en Passive ; 2 chocs sur 2 sans préavis des capteurs | L'arrêt sur pare-chocs dans le cerveau passe en premier |
| 2026-11-10 | La roulette avant (paquet 58) dépend d'une roulette bicolore que le 694 n'a peut-être pas | 0 sur 154 lectures en marche avant | Signal inutilisable sur ce robot |
| 2026-11-10 | Les codes infrarouges de la base n'ont jamais été relevés | Le récepteur du dessus lit 168 puis 164 en passant devant la base ; gauche et droite à 0 | L'axe de la base se repère en roulant ; l'essai des récepteurs gauche et droit reste à faire face à la base |

| 2026-11-10 | Les récepteurs infrarouges gauche et droit : « aucune source n'établit qu'un 694 en a qui fonctionnent » | Ils lisent le faisceau de la base en mode Safe, robot face à elle, et restent à 0 en Passive ; toujours identiques entre eux ; pendant un tour ils ne voient la base que sur 10 à 23° de cap ([journal_wifi.md § 22](../code/journal_wifi.md)) | La direction de la base se lit en tournant ; il faut l'infrarouge dans le journal à 20 lectures par seconde et un tour lent pour la donner à 1 ou 2° près |
| 2026-11-10 | Un tour refait au même endroit devrait se superposer au précédent (extrapolation : 1,3°) | Trois tours : courbes superposées à 3,7 à 4,4 cm en moyenne ; décalage d'après le motif de la pièce et d'après le gyroscope d'accord à 1° près par tour | Une station se reconnaît à sa courbe ; échelle du gyroscope 0,997 ± 0,003, première mesure |
| 2026-11-10 | Paliers de vitesse de 28,5 mm/s | Réglages 50, 75, 100, 125, 150 : vitesses réelles 71, 97, 123, 147, 145 mm/s en avant ; en arrière la roue gauche tourne 10 mm/s plus vite que la droite | Pas de paliers ; la vitesse réelle dépasse la demande de 21 mm/s jusqu'à un plafond vers 146 ; ne jamais compter sur la vitesse demandée |
| 2026-11-10 | Position du capteur de distance jamais mesurée (problème 9) | 143 mm lus au contact du pare-chocs avec une paroi : capteur à 27 mm en avant du centre pour un rayon de 170 mm | Première valeur pour le réglage `dx` de la carte (encore à 0) ; à confirmer à la règle |
| 2026-11-10 | L'arrêt sur pare-chocs dans le cerveau est la condition de toute translation décidée par lui (gain rapide 6) | Firmware v6 : arrêt réflexe et verrou, vérifiés sur un vrai contact | Condition remplie ; délai encore de 200 ms au plus |

| 2026-11-10 | Estimation : murs et stations à 2 ou 3 cm près à partir de tours sur place ; critère : chaque mur d'accord à 3 cm entre stations, première et cinquième station à 3 cm | Carré de 60 cm, six stations : trois murs d'accord à 0,3, 0,6 et 1,7 cm entre stations, le quatrième à 3,0 cm ; retour au point de départ : 1,0° d'erreur de cap, environ 2 cm d'erreur de position sur l'axe mesuré, après 2,70 m ([journal_wifi.md § 23](../code/journal_wifi.md)) | L'estimation tient sur ce premier essai, sans mètre ruban ; à refaire dans une vraie pièce, avec un carré plus grand et deux cotes mesurées |
| 2026-11-10 | Estimation : 5 à 10 cm d'erreur après 3 m parcourus depuis une station ; dérive du cap de 0,2 à 0,5 ° par minute | Boucle de 5,60 m en 6 minutes pilotée par le PC : 6,7 cm d'erreur de position (1,2 %) et 3,8° d'erreur de cap (0,7 ° par minute), mesurés sur les murs et confirmés par l'infrarouge de la base ([journal_wifi.md § 24](../code/journal_wifi.md)) | L'estimation de position tient ; le cap dérive un peu plus qu'estimé : recaler le cap sur les murs ou sur la base à chaque station |
| 2026-11-10 | Lire le robot 20 fois par seconde : « à surveiller, ce robot a déjà refusé des requêtes rapprochées » | Firmware v7 : 20,0 lectures par seconde, 64 ms au plus entre deux, aucune lecture perdue en 39 s au repos ni pendant 6 minutes d'exploration | Gain rapide 2 acquis |
| 2026-11-10 | Deux cartes d'un même lieu devraient s'accorder (jamais essayé) | Carré de 14 h et exploration de 15 h, stations et repères différents : largeur du couloir 175 et 207 cm, puis 177 et 204 cm | La carte par murs en lignes se répète à 2 ou 3 cm ; reste à la comparer au mètre ruban |

| 2026-11-10 | Estimation : une carte d'appartement qui tient à 10 ou 15 cm ; 3 à 5 cm perdus à chaque porte | Deux explorations enchaînées dans le même repère, 15,7 m, 23 minutes, huit stations dont deux sur un tapis : environ 15 cm d'erreur de position au retour (1 % du chemin), en travers du couloir, sans aucun recalage ([journal_wifi.md § 25](../code/journal_wifi.md)) | L'ordre de grandeur du rapport est atteint sans recalage ; aucune porte n'a encore été franchie |
| 2026-11-10 | Niveau des capteurs de vide auquel le mode Safe coupe les moteurs : « le chiffre qui manque » ; les surfaces sombres peuvent se lire comme un vide | Un capteur à 152 sur un tapis à motifs, robot en marche, mode Safe gardé ; 9,2 m d'exploration dont deux stations sur le tapis sans aucune retombée en Passive | Le seuil du robot est sous 152 ; un tapis sombre à motifs se traverse ; le rapport roues / gyroscope y monte à 1,04 à 1,06 et le courant de moitié : le tapis est un repère |

| 2026-11-10 | Recaler chaque station sur les murs connus ramène l'erreur à quelques centimètres (idée 2) | Dix tours repris ensemble sur le PC : murs partagés d'accord à 0,3 cm au lieu de 2,4 ; les deux retours au départ sont en réalité à 5,8 puis 16,7 cm du départ, cap faux de 4,1° puis 7,7° ; le recalage station par station seul se trompe, ce sont les retours au même endroit qui donnent la bonne réponse ([journal_wifi.md § 26](../code/journal_wifi.md)) | Repasser par une station connue et y refaire un tour devient la façon de corriger la position pendant une exploration |
| 2026-11-10 | La direction des paliers donne le cap à quelques degrés | ±5° au mieux pour un palier large, jusqu'à 40° pour un palier étroit | Pas de boussole par les paliers ; le cap se corrige par les distances aux murs et par les retours |
| 2026-11-10 | Échelle du gyroscope : jamais mesurée (problème 3) ; 0,997 ± 0,003 d'après trois tours (§ 22) | Un cap multiplié par 1,0015 ramène l'erreur des deux retours de 56 et 157 mm à 3 et 45 mm ; aucune dérive au repos en 12 minutes | Première valeur : 1,0015 ± 0,0005 ; l'erreur de cap vient surtout des tours sur place, tous dans le même sens |
| 2026-11-10 | Les capteurs optiques du pare-chocs comme préavis avant un contact (idée 5) | 153 au plus au contact avec la paroi du § 22 ; les seuils de 150 et 400 ne se déclenchent jamais avant le pare-chocs | Sur ces surfaces, c'est le capteur de distance avant chaque saut et le pare-chocs qui arrêtent le robot ; à refaire sur un mur clair |
| 2026-11-10 | Un mur donne un palier « d'une vingtaine de degrés » | À 3,3 et 3,9 m : 35 à 43° de large, lectures qui bougent de 3 à 6 cm ; avec une tolérance qui grandit avec la distance, 30 paliers de 25° ou plus dans dix tours au lieu de 18 | Un palier de 25° ou plus est pris pour un mur franc ; plus étroit, il peut n'être qu'une arête (montant de porte) |
| 2026-11-10 | Regarder sur les côtés avec le servo pendant une avance, pour suivre les murs | Butée du servo à 30° sur ce montage (fils courts) | Impossible sans rallonger les fils ; les portes sont cherchées par leurs deux montants vus pendant les tours sur place (`explorer3.py`, simulation seulement à ce jour) |
| 2026-11-10 | Critère de l'étape 3 : comparer la carte à deux cotes prises au mètre ruban (jamais fait) | L'utilisateur fournit un plan de l'appartement issu d'un LiDAR ; la carte du robot et le trajet de midi s'y posent à la même échelle, 54 pixels par mètre à 5 % près, avec le même écart d'orientation que celui trouvé par une autre voie ([journal_wifi.md § 27](../code/journal_wifi.md)) | Le plan devient la vérité terrain et le fond de la carte finale : au robot de s'y repérer plutôt que de tout redessiner. Le « couloir » des sections 23 à 26 est une pièce de 2,9 m de profondeur ; les parois vues à 1,75 m l'une de l'autre seraient des devants de meubles |

### État de l'ordre de travail du rapport

| Étape du rapport | État |
|---|---|
| 0. Une soirée sans code nouveau | **en cours le 2026-11-10** : essai du mode Safe sur la base fait ; enregistrement pendant un pilotage fait et analysé (§ 21) ; multimètre et règle remis à plus tard par l'utilisateur ; enregistrement pendant un tour sur place, papier et ruban sous un capteur de vide, infrarouge face à la base : à faire |
| 1. Fondations du firmware | **en cours le 2026-11-10** : arrêt sur pare-chocs (v6, vérifié sur un contact), lecture 20 fois par seconde (v7), infrarouge et courants des roues dans le journal et tour lent (v8) ; restent le fil de réveil, l'horloge unique, les enregistrements bruts du capteur de distance, le zéro du gyroscope, le texte « bat: » de la base, la tenue du cap |
| 2. Séance d'étalonnage | **entamée le 2026-11-10** sans mètre ruban : vitesses réelles à cinq réglages, contact avec une paroi (position du capteur, capteurs optiques), échelle du gyroscope à ±0,3 % par trois tours ; restent les tours de plusieurs tours, le mètre ruban, le servo |
| 3. Une pièce à partir de tours, sur le PC | **premier essai complet le 2026-11-10** : carré de 60 cm piloté par l'assistant devant la base, six tours, murs en lignes (figure 17 des analyses, journal § 23) ; puis exploration du couloir par le robot lui-même, quatre stations et retour (journal § 24), puis huit stations dont deux sur un tapis (journal § 25) ; puis ajustement d'ensemble des stations sur les murs et sur les retours au même endroit (`carto.py`, journal § 26 : 16,7 cm de dérive mesurés et repris) ; exploration complète écrite et mise au point en simulation (`explorer3.py`, § 26 : portes, retours, recalages, échelle du gyroscope ajustée par les murs), **pas encore essayée sur le robot** ; restent cet essai, la comparaison au mètre ruban, les autres pièces |
| 4 à 7 | à faire |

## Objectif fixé par l'utilisateur

Cartographier une pièce à partir des capteurs, sans aspirer ni brosser pour l'instant. Plus tard, nettoyer en se servant de la carte. Le calcul peut se faire sur un ordinateur extérieur. Il demande des idées nouvelles qui tirent le meilleur de son matériel.

## Ce que le matériel fait bien, et mal

| Élément | Fait bien | Fait mal |
|---|---|---|
| Capteur de distance sur servo | distance d'un mur vu de face, de 2 cm à 4 m, à 1 cm près | faisceau large (15° environ), aucun écho sur un mur vu de biais, 10 mesures par seconde, servo limité à ±30° par ses fils |
| Roues du robot (encodeurs, 0,4446 mm par pas) | distance parcourue en ligne droite | rotation (glissement : 5 à 10 % d'écart mesurés le 2026-11-08) |
| Gyroscope à 100 Hz | cap sur une à deux minutes, rotations | dérive lente, pas de nord |
| Six capteurs optiques du pare-chocs | obstacle à moins de 15 cm, six directions | rien au-delà |
| Pare-chocs, capteurs de vide | contact certain, bord de marche | rien d'autre |
| Base de charge | position fixe, que le robot retrouve seul | |
| Cerveau + Wi-Fi + PC | calcul lourd sur le PC, enregistrement, mises à jour sans câble | le Wi-Fi peut manquer : les réflexes restent dans le cerveau |

Conclusion : ne pas faire du capteur de distance un mauvais laser. Lui demander ce qu'il fait très bien (mesurer la distance d'un mur de face) et demander au robot ce qu'il fait très bien (tourner sur place en sachant de combien).

## Les idées

1. **Le tour sur place.** Le robot tourne sur lui-même, capteur droit devant ; chaque mesure est rangée avec le cap du gyroscope. Un mur ne renvoie l'écho que vu presque de face : dans la courbe distance / direction, chaque mur donne un palier (creux à fond plat) large d'une vingtaine de degrés. Hauteur du palier = distance du mur ; milieu du palier = direction du mur. Dans une pièce rectangulaire, quatre paliers à 90° donnent les dimensions de la pièce et la position du robot, en un seul tour, sans dépendre de la position calculée par les roues. Les coins rentrants donnent aussi un petit groupe d'échos. La butée du servo ne compte plus : c'est le robot qui sert de plateau tournant.
2. **Les murs servent de boussole.** Les murs d'une pièce sont à angle droit. Les directions trouvées au premier tour deviennent les axes de la carte. Ensuite, chaque tour sur place et chaque trajet le long d'un mur recalent le cap : la dérive du gyroscope n'a plus le temps de s'accumuler.
3. **Le tour de la pièce.** Le robot longe les murs à 10 cm, guidé par les capteurs optiques du pare-chocs. Son trajet enregistré est le contour de la pièce, meubles collés aux murs et portes compris. De retour au point de départ, l'écart entre l'arrivée et le départ mesure l'erreur accumulée, qu'on répartit sur le trajet. Ce trajet servira plus tard au nettoyage des bords.
4. **Quelques tours sur place à l'intérieur**, tous les mètres environ, pour trouver les meubles isolés et remplir la carte. Partout où le robot est passé, le sol est libre : c'est l'information la plus sûre de la carte.
5. **Croiser les mesures prises en roulant.** Une mesure dit seulement « quelque chose se trouve sur cet arc, à telle distance ». Le même objet vu de deux ou trois endroits donne des arcs qui se coupent en un point : le déplacement du robot remplace la finesse que le capteur n'a pas. C'est là que le balayage du servo est utile : multiplier les points de vue pendant une ligne droite.
6. **Le robot s'étalonne seul.** En approchant un mur lentement, le capteur de distance donne la vraie distance pendant que les capteurs optiques donnent leur valeur brute : on obtient leur courbe sans mètre ruban. Dix tours sur place comparés au motif répété des murs règlent l'échelle du gyroscope. Le décalage du capteur par rapport au centre du robot se déduit de la somme des distances de deux murs opposés.
7. **Des cartes en plus, sans capteur de plus.** Nature du sol (valeurs des capteurs de vide, effort des roues) : tapis ou sol dur. Seuils et barres de porte (secousses de l'accéléromètre) : frontières entre pièces. Force du Wi-Fi à chaque position. Plus tard, saleté (capteur de saleté du robot) et effort des brosses.

## Qui calcule quoi

- **Cerveau** : position (roues + gyroscope), réflexes (pare-chocs, vide, obstacle devant), gestes simples (tour sur place, ligne droite à cap tenu, suivi de mur), mesures horodatées. Rien de tout cela ne dépend du Wi-Fi.
- **PC** : enregistrement de tout, carte en petites cases, recalage sur les murs, choix de la prochaine destination, dessin. Tout est enregistré dans `mesures/` pour rejouer les calculs sans refaire rouler le robot.

## Ordre de travail

| Étape | Contenu | État |
|---|---|---|
| 1 | Tour sur place : `tour.ino`, touche `t`, `/api/tour`, outil `code/outils/tour_capture.py` | **fait le 2026-11-09** : deux tours réussis, voir ci-dessous |
| 2 | Position du robot (x, y, cap) dans le cerveau, tracée sur la page ; essai : un carré piloté à la main doit se refermer | **fait le 2026-11-09** (firmware v4, `position.ino`) ; premier carré : écart de 4 cm sur 1,79 m, à confirmer sur un parcours plus long |
| 3 | Première carte : l'utilisateur pilote à la main entre deux tours sur place | **commencé le 2026-11-09** : obstacles placés par le cerveau et dessinés sur la page (firmware v5, `carte.ino`) ; reste à garder la carte et à la recaler |
| 4 | Étalonnages automatiques (capteurs optiques, gyroscope, décalage du capteur) | à faire |
| 5 | Suivi de mur et tour de la pièce automatique | à faire |
| 6 | Exploration de l'intérieur, puis parcours en bandes sans les brosses, puis avec | à faire |

### Premiers résultats de l'étape 1 (2026-11-09, 20 h 46 et 20 h 51)

Deux tours sur place à un mètre d'écart, robot déplacé à la main : 381° et 380° en 13,7 s, 122 et 124 mesures, arrêt normal. Fichiers `mesures/tour_20261109_204605.*` et `mesures/tour_20261109_205150.*`.

- La fin de chaque tour retrouve son début (119 cm, puis 103 cm) : le gyroscope compte bien un tour complet.
- Les paliers existent comme prévu, mais ils sont plus larges que les 20° attendus : jusqu'à 65° pour une paroi proche. Le capteur entend donc un mur bien au-delà de la face. Le milieu du palier reste utilisable comme direction du mur ; sa largeur ne l'est pas.
- D'un tour à l'autre, la paroi de droite passe de 168 à 68 cm et le grand arc de devant de 119 à 104 cm, dans les directions prévues par le gyroscope : c'est le comportement attendu d'un déplacement d'un mètre. Non confirmé par une mesure au mètre ruban.
- À faire avant l'étape 3 : mesurer le décalage du capteur par rapport au centre du robot, comparer un palier au mètre ruban, superposer les deux tours sur un même dessin.

### Étape 2 : où en est la position (2026-11-09, 22 h)

- Le cerveau calcule x, y et le cap à chaque lecture des capteurs (cinq fois par seconde) : distance d'après les compteurs des roues, direction d'après le gyroscope. La page a une carte « Position » (tracé, écart au point de départ, bouton de remise à zéro) ; `/api/pose` donne la position et le tracé ; `/api/tour` donne maintenant la position du robot au départ de chaque tour (`depart`), ce qu'il faut pour l'étape 3.
- Vérifié sans rouler : l'affichage (faux parcours en carré dans le navigateur), et les signes du calcul, en le rejouant sur l'enregistrement du 2026-11-08 (24 m de pilotage). Sur cet enregistrement, les roues seules comptent 0,963 fois la rotation mesurée par le gyroscope et finissent à 116° de lui : le cap doit bien venir du gyroscope.
- Pas encore vérifié : la justesse sur le sol. Essai prévu : remise à zéro, un carré d'un mètre environ piloté à la main, retour sur la marque de départ ; l'écart affiché doit rester de quelques centimètres. Un écart plus grand dira quoi régler (diamètre des roues, pas par tour, glissement dans les virages).

**Premier carré (2026-11-09, 22 h 25, piloté par l'utilisateur)** : environ 45 cm de côté, 1,79 m parcourus, le tracé se referme à 4 cm de son départ (2 % du chemin), cap des roues et du gyroscope d'accord à moins d'un degré. À confirmer : le robot était-il bien revenu sur sa marque ? Fichiers `mesures/position_20261109_222619.*`.

### Étape 3, premier pas : la carte des obstacles se dessine toute seule (2026-11-09, 22 h 30)

Le cerveau place maintenant lui-même chaque écho du capteur de distance dans la pièce (`carte.ino`, firmware v5), et la nouvelle page de pilotage dessine le résultat autour du tracé, en vue de dessus ou en 3D. Piloter le robot capteur allumé, ou lancer un tour sur place, suffit à faire apparaître ce qui l'entoure. Ce n'est pas encore une carte de la pièce : les murs sortent en arcs épais (le capteur entend large), la position dérive sans que rien la recale, et le décalage du capteur par rapport au centre du robot n'est pas mesuré.

## Vers le but final : le robot en 3D dans l'appartement, « va dans telle pièce », une zone tracée au doigt

But donné par l'utilisateur le 2026-11-09 au soir. Chaque marche s'appuie sur la précédente ; les trois premières se font avec le matériel actuel.

| Marche | Ce que l'utilisateur voit | Ce qu'il faut construire | État |
|---|---|---|---|
| A | Le robot, son tracé et les obstacles sur la page, en 3D | position, carte des obstacles, page | **fait le 2026-11-09** |
| B | « Va là » : toucher un point de la carte, le robot y va | dans le cerveau : tourner vers le point, avancer en tenant le cap au gyroscope, s'arrêter au but, au pare-chocs ou devant un obstacle ; sur la page : le toucher de la carte | à faire ; premier déplacement décidé par le robot, donc essais courts et accord à chaque fois |
| C | Une carte qui reste : on la retrouve le lendemain | carte gardée sur le PC ou dans le téléphone ; point zéro fixe (la base du robot) ; recalage du cap sur les murs | à faire |
| D | Une zone tracée au doigt, le robot la parcourt en bandes | parcours en bandes dans un rectangle, puis moteurs des brosses | à faire, après B |
| E | Des pièces qui portent un nom, « va dans la cuisine » | zones nommées sur la carte gardée, passages d'une pièce à l'autre, trajet par étapes | à faire, après C |
| F | L'appartement en 3D avec ses murs | des murs nets : c'est le rôle du LiDAR de la note F (environ 112 $ CA), le capteur de distance actuel donne des arcs trop épais pour cela | matériel à commander |

Le LiDAR de la note F, s'il arrive, remplacera le capteur de distance dans les étapes 3 à 6 ; la position, l'enregistrement, la carte et les parcours resteront les mêmes.

## Nettoyage, plus tard

- **Bandes parallèles** alignées sur les murs, espacées de la largeur des brosses (17 cm environ), au lieu du parcours au hasard du 694 ; la carte des passages montre les endroits manqués.
- **Bords** : le tour de la pièce, brosse latérale (à droite) contre le mur.
- **Zones sales d'abord** : mémoriser où le capteur de saleté réagit, y repasser, et commencer par elles la fois suivante.
- **Reprise après recharge** à l'endroit de l'arrêt, ce que le 694 ne sait pas faire seul.
- **Zones interdites** dessinées sur la page.

## Limites connues

- Le capteur de distance voit mal les pieds de chaise, les tissus et les surfaces de biais ; le pare-chocs et les capteurs optiques les trouveront.
- Avec le capteur sur le dessus, le robot est plus haut qu'à l'origine : il ne passe plus sous les meubles bas, et rien d'autre que le capteur lui-même ne protège ce montage d'un choc en hauteur.
- La batterie portable coupe parfois : si le cerveau s'éteint pendant un mouvement, le robot garde son dernier ordre. L'abaisseur 5 V de la note F est à installer avant de longs trajets sans surveillance.
- Précision attendue, non mesurée : murs à quelques centimètres près dans une pièce ; à vérifier au premier tour sur place.

## Sources

Principe des paliers d'un sonar devant un mur (« regions of constant depth ») : J. Leonard et H. Durrant-Whyte, *Directed Sonar Sensing for Mobile Robot Navigation*, 1992. Croisement d'arcs pris de plusieurs positions : O. Wijk et H. Christensen, « Triangulation-based fusion of sonar data », 2000. Carte en petites cases à partir d'un sonar : H. Moravec et A. Elfes, 1985. Références citées de mémoire, non revérifiées ce jour. Mesures propres au robot : `code/journal_tests.md`, `code/journal_wifi.md`.
