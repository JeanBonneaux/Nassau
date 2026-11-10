# H — Cartographier une pièce avec ce Roomba : stratégie

Rédigé le 2026-11-09 au soir, après les premiers essais du radar sur le matériel. **État : stratégie acceptée par l'utilisateur (« Commence avec 1 ») ; l'étape 1 est programmée, pas encore essayée avec le robot en mouvement.** Mots employés avec l'utilisateur : le cerveau (ESP32), le capteur de distance (HC-SR04), le servo (SG90), le gyroscope (GY-521).

**Suite du 2026-11-10** : une recherche plus poussée sur ce que les capteurs actuels peuvent encore donner (revue du firmware et du câblage, analyse des enregistrements de `mesures/`, idées classées avec leur premier essai, ce qui ne marchera pas) est dans [`../reports/Roomba 694 sensor exploitation ideas.md`](../reports/Roomba%20694%20sensor%20exploitation%20ideas.md), en anglais comme la demande ; les notes de travail et les scripts d'analyse sont dans `../research_notes/`. Ce rapport revoit plusieurs résultats de la présente note à la lumière des enregistrements (le rapport roues / gyroscope de 0,963, ce que prouve le recouvrement de 20° des tours, la largeur des paliers, l'essai du carré) : le lire avant de s'appuyer sur ces chiffres. Rien de ce rapport n'a été essayé sur le robot.

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
