# Roomba 694 : où en est le projet

*État au 15 novembre 2026, 9 h 23. Le détail de chaque essai est dans [`code/journal_wifi.md`](code/journal_wifi.md) (56 sections) ; ce résumé n'en garde que l'essentiel.*

## En bref

- Le robot **va seul d'une case à l'autre de l'appartement**, conduit par le cerveau et par le programme du PC. Le 14 au matin : de sa base jusqu'en C28 et retour, 32 m en 23 minutes, 5 contacts légers. Le 14 après-midi : **de la cuisine jusque devant sa base, 16 m sans un seul contact**, seuil de porte, couloir et porte H12 compris.
- Il **sait où il est à 1 cm près** là où il a déjà fait un tour sur lui-même (97 repères enregistrés, dont 16 dans la cuisine). Loin d'un repère, l'erreur a atteint 20 à 30 cm.
- **Trois choses ne sont pas au point** : rentrer sur sa base tout seul (réussi 1 fois sur 2), aller plus vite (il s'arrête encore beaucoup), et garder une position juste dans les longs passages menés au capteur (30 cm d'erreur devant la porte H12, rattrapés au capteur).
- **La cuisine est explorée et a ses repères** depuis le 14 après-midi : trois passages, 16 repères d'accord entre eux à 3,5 cm. Le passage étroit (42 cm au plus serré) et le seuil de sa porte (1,7 cm) sont franchis.
- **Un défaut de sécurité trouvé et corrigé le 14** : à chaque accroc du Wi-Fi, le cerveau se figeait une à cinq secondes et ne surveillait plus le pare-chocs (20 cm roulés ainsi une fois). Ton idée du tampon est en service, c'est la version 11 : plus aucun trou en quinze minutes de route, même quand le Wi-Fi décroche.
- **Une revue à part, le 14 au soir** (localisation et code) : elle a trouvé que le cerveau comptait mal les rotations lentes après une quarantaine de tours sur place sans redémarrage, et l'a corrigé dans la version 12, avec six autres petites protections. La version 12 est installée et vérifiée robot immobile ; elle a roulé le 15 avec la version 13.
- **Le 15 au matin, première séance en version 13** (elle garde en entier ce que le robot écrit de lui-même) : installée seule au branchement, vérifiée au repos puis en mouvement. Trois résultats. Les séries de petits pivots du centrage font reculer le robot d'environ 5 mm chacune, sans que les roues le comptent : une part de l'erreur du couloir. En ligne droite le calcul tient : 1 cm d'écart après un aller et retour de 4 m. Et **le tapis vert foncé de la pièce à gauche arrête le robot** : ses capteurs de vide le prennent pour un vide.
- En ce moment : robot **à 1 m devant sa base, pas dessus** (case D16, tourné vers elle, batterie à 90 %), séance fermée à 9 h 20. Cerveau allumé, **version 13**. J'attends ta décision sur le tapis (voir « La suite »).

## Le but, pour mémoire

Dire « va dans telle pièce » et que le robot y aille seul. L'ordre que tu as fixé : **d'abord une position précise, ensuite la vitesse et une conduite fluide**. Le nettoyage (brosses, aspirateur) vient après : pour l'instant elles restent à l'arrêt.

## Le chemin parcouru

| Date | Ce qui a été franchi |
|---|---|
| 8 nov. | Recherche : comment parler au robot (la prise sous le capot) |
| 9 nov. | Le cerveau branché ; pilotage au téléphone en Wi-Fi ; capteur de distance sur son servo ; premier tour sur place |
| 10 nov. | Arrêt automatique sur pare-chocs ; premières cartes ; le plan de l'appartement sert de fond ; carte quadrillée « comme aux échecs » ; le robot explore seul le couloir et la pièce centrale (77 m) ; premier trajet demandé par cases |
| 13 nov. | Nouvelle localisation et conduite d'un seul tenant (2 à 3 fois plus rapide) ; firmware v10 ; les repères ; la base mesurée (case B16) ; premier accostage réussi ; premier aller-retour jusqu'en C28 ; découverte du patinage d'une roue |
| 14 nov. | Le même aller-retour refait pour mesurer : deux fois plus vite. Second accostage : manqué. Centrage automatique des passages étroits écrit, puis essayé dans la cuisine et le couloir. La cuisine explorée puis cartographiée (16 repères). Trous dans les lectures des capteurs trouvés et corrigés (version 11). Seuil de la cuisine franchi, retour devant la base sans contact. Deux sessions à part : l'audit, puis la revue de la localisation et du code ; version 12 du cerveau ; version 13 prête, pas encore installée |
| 15 nov. | Version 13 installée et vérifiée en mouvement. Essai des petits pivots. La bande de parquet de la pièce à gauche cartographiée ; le tapis vert foncé trouvé : le robot refuse d'y monter. Deux tours de suite au même endroit, aller et retour de 2 m |

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
| Portes et passages étroits | Le centrage automatique mène maintenant seul le passage de la cuisine (42 à 49 cm) et le couloir entre J20 et J12 (3,9 m en 3 min 50, contre 5 min 20 à la main), sans contact. Il reste lent, et la porte H12 demande encore que je regarde et décale à la main (4 min 30) |
| Vitesse | 32 m en 23 min, soit 1,4 m par minute en moyenne. Les tours sur place, ceux où il regarde autour de lui, prenaient 46 % du temps sur une boucle d'essai du 13 |
| Position loin des repères | Le calcul seul s'est trompé de 20 à 30 cm devant la base ; il faut passer par les endroits à repères |
| Patinage | Une roue seule : le code qui le détecte et ralentit est écrit et vérifié sur les enregistrements, pas encore prouvé sur le robot. Les deux roues ensemble, comme sur le seuil de la cuisine le 14 : pas détecté. La revue montre que le courant de la batterie signale les deux cas, sans fausse alerte sur 195 m d'avances : à ajouter au pilote |
| Trous dans les lectures | Corrigé le 14 par la version 11 du cerveau (ton tampon) : le cerveau n'attend plus le Wi-Fi. Restent deux choses sans explication : le robot a redémarré tout seul une fois, et un tour sur place a tourné trop vite une fois. L'audit signale aussi trois points à durcir encore (note I) |
| Version 12 du cerveau | Installée le 14 à 18 h 35 par la session de revue, à ta demande : cap compté dans un nombre plus long, arrêt des roues répété au démarrage, cinq petites protections. Vérifiée robot immobile seulement : le premier tour sur place et la première avance sont à regarder de près |
| Version 13 du cerveau | Écrite le 14 au soir par la session de revue : elle garde en entier ce que le robot écrit de lui-même (réveil, charge, redémarrage) et ajoute une sonde fermée par une clé, pour lire les capteurs que la documentation ne cite pas. Installée le 15 à 8 h 36, vérifiée au repos et en mouvement |
| Le tapis de la pièce à gauche | Vert foncé, à franges. Les capteurs de vide y lisent 36 à 81, contre 2 600 sur le parquet : pour le robot c'est un vide, et sa propre sécurité coupe les roues dès qu'il avance ou pivote dessus. Il recule sans problème. Marqué zone interdite, tracé provisoire. Pour y rouler, et en faire une zone de nettoyage comme tu le veux, il faut lever cette protection : ta décision |
| Petits pivots du centrage | Chaque série (un quart de tour, un demi-tour, un quart de tour) fait reculer le robot d'environ 5 mm que les roues ne comptent pas. Mesuré une fois, sur une cible médiocre : à refaire face à un vrai mur |
| Cuisine | Trois passages, 16 repères. Sans repère encore : le coin de la porte du balcon (G36) et le côté droit de l'îlot. Le seuil de sa porte passe sans effort vers la pièce centrale ; vers la cuisine, l'arrière du robot y reste accroché à vitesse lente : à réessayer plus vite |
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
5. **Deux erreurs de ma part, à ne pas refaire** : corriger le cap du robot à la main (trois contacts le 14), et annoncer une case calculée de tête (cases fausses le 13, et encore une le 15).
6. **Un tapis très sombre est un vide pour le robot.** Ses capteurs de vide mesurent la lumière que le sol renvoie ; le poil vert foncé n'en renvoie presque pas.

## La suite que je propose, dans l'ordre

**D'abord, le tapis de la pièce à gauche.** Tu veux que le robot y monte, et qu'à terme ce soit une zone de nettoyage. Il faut choisir comment lever sa protection contre le vide. Soit par le cerveau : le robot ne surveille plus rien lui-même, le cerveau surveille le vide et les roues levées à sa place, partout sauf sur le tapis ; c'est une version 14 à écrire, sans geste de ta part, et c'est ce que je recommande parce qu'on garde la lecture du sol. Soit en masquant ses quatre capteurs de vide au papier blanc : immédiat, mais le robot ne voit plus le sol nulle part. Dans les deux cas il ne se protège plus seul d'une vraie marche. La pièce derrière la porte H12 (celle de K9 et K10) n'a toujours aucun repère.

1. **L'accostage** : enlever l'objet qui se tient devant la base, à 40 cm d'elle et à peine à gauche de son axe (le capteur le voit, c'est là que le robot touche à chaque fois), puis réessayer l'ordre « rentre à la base » avec ton accord.
2. **Lire l'audit et la revue ensemble.** L'audit (`notes/I_audit_regard_neuf.md`) : le robot n'avance que 17 % du temps ; c'est la carte des repères qu'il faut rendre cohérente ; le gyroscope est monté penché et le cerveau n'en lit qu'un axe. La revue (`notes/J_revue_localisation.md`) y ajoute : arrêter une avance quand le courant de la batterie monte (les roues forcent), se servir du capteur de distance comme d'une règle pendant les avances, et, avant tout achat, un téléphone posé en hauteur avec un marqueur imprimé collé sur le robot, pour avoir sa position vue de l'extérieur.
3. **Le seuil de la cuisine dans le sens difficile** : vers la cuisine, essayer plus vite que 60 mm/s, ou de biais. Et chercher pourquoi le calcul de position dérive de 30 cm dans le couloir mené au centrage : la revue a mis l'échelle du plan hors de cause (juste à 0,5 % près) et son essai de trois minutes sur place, fait le 15, montre que les séries de petits pivots du centrage font reculer le robot d'environ 5 mm chacune : une dizaine des 24 cm s'expliquent ainsi.
4. **Passages étroits plus rapides** : le centrage automatique marche sur le robot (passage de la cuisine), mais il s'arrête tous les 20 à 40 cm. L'audit propose de lire les distances de côté en roulant, ce qui demande un petit changement de montage.
5. **Aller plus vite** : moins de tours sur place, seulement là où ils servent.
6. **« Va dans telle pièce »** : tu me donnes le nom des pièces, je les attache aux cases ; une seule commande enchaîne trajet, portes et repères.
7. **La carte vivante sur ton téléphone** : l'autre session l'a mise à jour ce matin (la base en B16, le robot reconnu sur sa base, les obstacles et les repères). Elle n'a pas encore été vue sur ton téléphone ; un VPN actif sur le PC peut la bloquer.

## Ce dont j'ai besoin de toi

- **Enlever ce qui est devant la base**, à 40 cm d'elle, légèrement à gauche quand on la regarde : un objet d'une dizaine de centimètres de large. Et fixer la batterie portable au ruban : le cerveau s'est éteint un instant quand tu as porté le robot.
- **Avant une séance qui part de la base** : rebrancher le cerveau s'il est débranché, et tirer le robot de sa base à la main (posé dessus, il refuse de rouler). Si la batterie portable du cerveau est vide, la recharger avant.
- **Dégager le devant de la base** : rien à moins de 50 cm de chaque côté de son axe, sur 1,2 m.
- **Ta décision sur le tapis** (voir « La suite »), et me dire s'il y a chez toi un escalier ou une marche qui descend.
- **Deux réponses courtes, quand tu veux** :
  - Y a-t-il un tapis dans la pièce centrale, vers D27 et E27 ?
  - Qu'y a-t-il en E13, et autour de E25 et E26 ? Le robot y touche ou y voit quelque chose.

## Où trouver quoi

| Quoi | Où |
|---|---|
| Le journal de tous les essais | `code/journal_wifi.md` |
| La stratégie et ce que les mesures ont changé | `notes/H_cartographie_strategie.md` |
| L'audit « regard neuf » et ses propositions | `notes/I_audit_regard_neuf.md` |
| La revue : ce que le projet pourrait manquer pour se localiser | `notes/J_revue_localisation.md` |
| Ce que le robot fait et écrit de lui-même, et ce que sa prise permet | `notes/L_retro_ingenierie_robot.md` |
| Le plan d'analyse en direct d'une séance de cartographie | `notes/M_plan_analyse_en_direct.md` |
| Les outils et leur mode d'emploi | `code/README.md` |
| Les enregistrements | `mesures/` |
| Le plan de l'appartement et les cartes | `plan_lidar/`, sur ton PC seulement : jamais envoyé sur GitHub |
