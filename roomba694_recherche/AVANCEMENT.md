# Roomba 694 : où en est le projet

*État au 14 novembre 2026, 15 h. Le détail de chaque essai est dans [`code/journal_wifi.md`](code/journal_wifi.md) (48 sections) ; ce résumé n'en garde que l'essentiel.*

## En bref

- Le robot **va seul d'une case à l'autre de l'appartement**, conduit par le cerveau et par le programme du PC. Trajet le plus long : de sa base jusqu'en C28 et retour, **32 m en 23 minutes, 5 contacts légers**.
- Il **sait où il est à 1 cm près** là où il a déjà fait un tour sur lui-même (81 repères enregistrés). Loin d'un repère, l'erreur a atteint 20 à 30 cm.
- **Trois choses ne sont pas au point** : rentrer sur sa base tout seul (réussi 1 fois sur 2), passer les portes et les passages étroits sans que je le guide pas à pas, et rouler plus vite.
- **La cuisine est explorée** depuis le 14 après-midi (8 tours sur place, un contact léger), sauf le passage étroit qui mène à la marche.
- **Un défaut de sécurité trouvé le 14** : par moments le cerveau reste plusieurs secondes sans nouvelles des capteurs du robot, aux moments où le Wi-Fi décroche. Il laisse alors le robot rouler jusqu'à 1,5 s sans rien surveiller (20 cm une fois). Le robot a aussi redémarré tout seul pendant un essai immobile. Les causes ne sont pas trouvées : à régler avant de le refaire rouler.
- En ce moment : robot **endormi dans la cuisine, en F36**. Il n'est pas sur sa base : **il ne charge pas**. Cerveau allumé, rien ne roule.

## Le but, pour mémoire

Dire « va dans telle pièce » et que le robot y aille seul. L'ordre que tu as fixé : **d'abord une position précise, ensuite la vitesse et une conduite fluide**. Le nettoyage (brosses, aspirateur) vient après : pour l'instant elles restent à l'arrêt.

## Le chemin parcouru

| Date | Ce qui a été franchi |
|---|---|
| 8 nov. | Recherche : comment parler au robot (la prise sous le capot) |
| 9 nov. | Le cerveau branché ; pilotage au téléphone en Wi-Fi ; capteur de distance sur son servo ; premier tour sur place |
| 10 nov. | Arrêt automatique sur pare-chocs ; premières cartes ; le plan de l'appartement sert de fond ; carte quadrillée « comme aux échecs » ; le robot explore seul le couloir et la pièce centrale (77 m) ; premier trajet demandé par cases |
| 13 nov. | Nouvelle localisation et conduite d'un seul tenant (2 à 3 fois plus rapide) ; firmware v10 ; les repères ; la base mesurée (case B16) ; premier accostage réussi ; premier aller-retour jusqu'en C28 ; découverte du patinage d'une roue |
| 14 nov. | Le même aller-retour refait pour mesurer : deux fois plus vite. Second accostage : manqué. Centrage automatique des passages étroits écrit. La cuisine explorée, robot posé à la main en C39. Des trous dans les lectures des capteurs découverts |

## Ce que le robot sait faire aujourd'hui (mesuré)

- **Obéir au cerveau en Wi-Fi**, lu 20 fois par seconde, avec arrêt immédiat si le pare-chocs touche. Mode sûr seulement, 150 mm/s au plus, brosses à l'arrêt.
- **Avancer et tourner juste** : à 1° et 7 mm près sur un geste (firmware v10).
- **Se situer sur le plan** : à 1 cm près sur un repère ; se retrouver à 1 ou 2 cm et 1 ou 2° près, neuf minutes après avoir été porté à la main devant sa base.
- **Planifier un trajet** en évitant les murs et les 14 obstacles qu'il a déjà touchés ou vus.
- **Atteindre les cases demandées** : C28, B22, C9, K10, et revenir en D16 devant sa base.
- **Explorer seul une pièce qu'il ne connaît pas** : la cuisine le 14, posé à la main en C39. Huit tours sur place et 7 m en 4 minutes de route, un contact léger contre l'îlot en bois.
- **Retrouver l'axe de sa base** grâce à ses faisceaux infrarouges : à 2 mm près à la dernière arrivée ; signal reçu jusqu'à 2 m.

## Ce qui n'est pas encore au point

| Sujet | Où on en est |
|---|---|
| Monter sur sa base | L'ordre « rentre à la base » du robot a réussi le 13 (21 s) et échoué le 14 : trois contacts en route, arrêt hors de la base. Quelque chose gêne l'approche |
| Portes et passages étroits | La porte H12 (62 cm), le couloir entre J15 et J17 (68 cm), le passage de E22 (48 cm) : je les fais encore pas à pas, 10 minutes sur les 23 du dernier trajet. Un centrage automatique est écrit depuis ce matin, pas encore essayé sur le robot |
| Vitesse | 32 m en 23 min, soit 1,4 m par minute en moyenne. Les tours sur place, ceux où il regarde autour de lui, prenaient 46 % du temps sur une boucle d'essai du 13 |
| Position loin des repères | Le calcul seul s'est trompé de 20 à 30 cm devant la base ; il faut passer par les endroits à repères |
| Patinage d'une roue | Le code qui le détecte et ralentit est écrit et vérifié sur les enregistrements, mais aucune roue n'a patiné depuis : pas encore prouvé sur le robot |
| Trous dans les lectures | Par moments le cerveau reste sans nouvelles des capteurs : 0,4 à 5 s, cinq fois plus d'une seconde le 14 après-midi, aux moments où le Wi-Fi décroche. Il laisse alors le robot rouler jusqu'à 1,5 s sans surveiller le pare-chocs ; une fois, 20 cm. Le robot a aussi redémarré tout seul pendant un essai immobile. Rien n'a été touché, mais les causes ne sont pas trouvées |
| Cuisine | Explorée à 10 ou 20 cm près, sans repères encore (il faut y repasser). Le passage étroit vers la marche (55 cm sur le plan) et la marche elle-même ne sont pas vus |
| « Va dans telle pièce » | Pas encore : il manque les noms des pièces sur la carte, et une commande unique qui enchaîne tout sans moi |

## Les chiffres : le même trajet, base → C28 → base

| | 13 nov. | 14 nov. |
|---|---|---|
| Durée | 45,7 min | **22,9 min** |
| Contacts (tous légers) | 7 | **5** |
| Tours sur place calés sur un repère | 2 sur 23 | **16 sur 23** |
| Pièce centrale, aller et retour | 19 min, 5 contacts | 3,5 min, 3 contacts |
| Arrivée : écart à l'axe de la base | 0,5 à 1,3 cm | 0 à 0,2 cm |

Le gain vient surtout du vrai chemin de la pièce centrale, de la méthode pour la porte et des repères. Trois des cinq contacts du 14 sont de ma faute (voir plus bas).

## Ce qu'on a appris

1. **Les repères valent mieux que le calcul seul.** Un tour sur place à un endroit déjà vu recale le robot à 1 cm. D'où la règle : faire passer les trajets par ces endroits.
2. **Une roue peut patiner.** Le 13, dans la pièce centrale (sol sombre vers D27 et E27), la roue droite a tourné 43 puis 35 cm de trop. Le robot se croyait en C28, il était en C27. C'est ce qui avait fait rater le retour.
3. **Le couloir se resserre à 68 cm entre J15 et J17** : 17 cm de chaque côté du robot. En se centrant au capteur de distance, il passe sans toucher.
4. **La base est en B16**, tournée vers le bas du plan ; le robot retrouve son axe à quelques millimètres près.
5. **Deux erreurs de ma part, à ne pas refaire** : corriger le cap du robot à la main (trois contacts le 14), et annoncer une case calculée de tête (cases fausses le 13).

## La suite que je propose, dans l'ordre

1. **Retrouver des lectures sûres, avant tout** : toi, un coup d'œil à la batterie du cerveau et à ses fils ; moi, cinq minutes robot immobile sans aucun trou ; puis, avec ton accord parce que cela change le programme du cerveau, qu'il n'attende jamais le Wi-Fi et qu'il coupe les roues dès 0,3 s sans nouvelles des capteurs.
2. **La marche de la cuisine** : d'abord le passage étroit qui y mène (de D32 à D34), puis la marche entre C28 et C29, lentement.
3. **Passages étroits sans mon aide** : le robot se centre lui-même au capteur de distance. C'est écrit. En simulation, 75 départs sur 75 passent sans contact dans un couloir qui se resserre à 68 cm et devant une porte de 62 cm ; et sur les mesures de ce matin, le programme aurait décidé ce que j'avais fait à la main. Il reste à l'essayer sur le robot : d'abord des regards sans avancer, puis le couloir, puis la porte H12.
4. **Accostage fiable** : dégager le devant de la base, puis réessayer ; sinon, un accostage lent mené par le cerveau sur les faisceaux.
5. **Aller plus vite** : moins de tours sur place, seulement là où ils servent.
6. **« Va dans telle pièce »** : tu me donnes le nom des pièces, je les attache aux cases ; une seule commande enchaîne trajet, portes et repères.
7. **La carte vivante sur ton téléphone** : l'autre session l'a mise à jour ce matin (la base en B16, le robot reconnu sur sa base, les obstacles et les repères). Elle n'a pas encore été vue sur ton téléphone ; un VPN actif sur le PC peut la bloquer.

## Ce dont j'ai besoin de toi

- **Le robot dort dans la cuisine, en F36, et ne charge pas.** Si on ne continue pas aujourd'hui, repose-le sur sa base.
- **Avant une séance qui part de la base** : rebrancher le cerveau s'il est débranché, et tirer le robot de sa base à la main (posé dessus, il refuse de rouler).
- **Dégager le devant de la base** : rien à moins de 50 cm de chaque côté de son axe, sur 1,2 m.
- **Trois réponses courtes, quand tu veux** :
  - Y a-t-il un tapis dans la pièce centrale, vers D27 et E27 ?
  - Qu'y a-t-il en E13, et autour de E25 et E26 ? Le robot y touche ou y voit quelque chose.
  - As-tu débranché le cerveau après avoir posé le robot sur sa base ?

## Où trouver quoi

| Quoi | Où |
|---|---|
| Le journal de tous les essais | `code/journal_wifi.md` |
| La stratégie et ce que les mesures ont changé | `notes/H_cartographie_strategie.md` |
| Les outils et leur mode d'emploi | `code/README.md` |
| Les enregistrements | `mesures/` |
| Le plan de l'appartement et les cartes | `plan_lidar/`, sur ton PC seulement : jamais envoyé sur GitHub |
