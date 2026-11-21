# Roomba 694 : où en est le projet

*État au 21 novembre 2026, 14 h 11. Le détail de chaque essai est dans [`code/journal_wifi.md`](code/journal_wifi.md) (62 sections) ; ce résumé n'en garde que l'essentiel.*

## En bref

- **Le 21 novembre, la priorité change : la vitesse d'abord**, à ta demande (« il est lent, et ça devrait être notre focus principal de pouvoir l'accélérer, peut-être en pensant à la façon de voir les murs de côté »). **L'essai du gyroscope est fait** : pendant deux tours sur place, les deux axes que le cerveau ne compte pas lisent 10 % et 4 % de la rotation ; la carte est penchée de 6°, et c'est bien ce qui faisait compter 0,6 % de rotation en moins. La correction est simple et ira dans une version suivante. **La version 15 du cerveau est écrite et compilée, pas installée** : le capteur de distance peut tourner jusqu'à 90° de chaque côté, un degré à la fois, à 5° par seconde. **L'essai du capteur tourné attend ton go.**

- Le robot **va seul d'une case à l'autre de l'appartement**, conduit par le cerveau et par le programme du PC. Le 14 au matin : de sa base jusqu'en C28 et retour, 32 m en 23 minutes, 5 contacts légers. Le 14 après-midi : **de la cuisine jusque devant sa base, 16 m sans un seul contact**, seuil de porte, couloir et porte H12 compris.
- Il **sait où il est à 1 cm près** là où il a déjà fait un tour sur lui-même (97 repères enregistrés, dont 16 dans la cuisine). Loin d'un repère, l'erreur a atteint 20 à 30 cm.
- **Trois choses ne sont pas au point** : rentrer sur sa base tout seul (réussi 1 fois sur 2), aller plus vite (il s'arrête encore beaucoup), et garder une position juste dans les longs passages menés au capteur (30 cm d'erreur devant la porte H12, rattrapés au capteur).
- **La cuisine est explorée et a ses repères** depuis le 14 après-midi : trois passages, 16 repères d'accord entre eux à 3,5 cm. Le passage étroit (42 cm au plus serré) et le seuil de sa porte (1,7 cm) sont franchis.
- **Un défaut de sécurité trouvé et corrigé le 14** : à chaque accroc du Wi-Fi, le cerveau se figeait une à cinq secondes et ne surveillait plus le pare-chocs (20 cm roulés ainsi une fois). Ton idée du tampon est en service, c'est la version 11 : plus aucun trou en quinze minutes de route, même quand le Wi-Fi décroche.
- **Une revue à part, le 14 au soir** (localisation et code) : elle a trouvé que le cerveau comptait mal les rotations lentes après une quarantaine de tours sur place sans redémarrage, et l'a corrigé dans la version 12, avec six autres petites protections. La version 12 est installée et vérifiée robot immobile ; elle a roulé le 15 avec la version 13.
- **Le 15 au matin, première séance en version 13** (elle garde en entier ce que le robot écrit de lui-même) : installée seule au branchement, vérifiée au repos puis en mouvement. Trois résultats. Les séries de petits pivots du centrage font reculer le robot d'environ 5 mm chacune, sans que les roues le comptent : une part de l'erreur du couloir. En ligne droite le calcul tient : 3 cm d'écart après un aller et retour de 4 m. Et **le tapis vert foncé de la pièce à gauche arrête le robot**, pour deux raisons : ses capteurs de vide prennent le poil sombre pour un vide, et sa brosse latérale, à l'arrêt, se glisse sous le bord (tu l'as vu). Une mauvaise nouvelle aussi : **trois fois ce matin les repères ont déplacé la position de 16 à 24 cm, à tort** d'après la session de revue.
- **Le tapis se prend à reculons** (10 h 15) : en marche arrière le robot monte dessus sans patiner, il y tourne sur place et en ressort en avant. Deux lignes du tapis sont relevées, avec un repère chacune (cases D8 et E8). Presque tout le tapis est acceptable pour ses capteurs ; seules de petites zones très sombres, près des bords, l'arrêtent.
- **Le 15, de 10 h 40 à 11 h 52, une série d'essais** que tu as demandée à l'autre session, qui les a choisis ; j'ai piloté. **Les faisceaux infrarouges de la base donnent une position au centimètre** : le robot lit du vert, puis les deux, puis du rouge en traversant devant elle, et les bords retombent à 1 cm près à l'aller et au retour. Au retour d'une tournée de 47 minutes, mon calcul de position avait dérivé de 10 et 17 cm ; recalé sur les faisceaux, le robot est revenu au même endroit que le matin à 3 cm près. Les petits pivots font reculer le robot de 1 mm chacun, et non 5. Le tapis : son bord nord est à 61 cm du mur, ses bords nord et sud n'ont pas de franges ; le robot y monte d'un trait à reculons, pas par petits pas. L'endroit du tapis que le robot prend pour un vide n'a pas été retrouvé (le plus sombre trouvé lit 178, et il ne s'y arrête pas). Trois contacts légers, sur des choses basses que ses capteurs ne voient pas ; deux par ma faute, dans le passage entre les deux pièces.
- **Une trouvaille de l'autre session, à confirmer par une mesure à la règle** : le capteur de distance serait 10 cm plus en avant sur le robot que ce que les programmes comptent (12 cm du centre au lieu de 2,7). Chaque mur paraîtrait alors 10 cm trop près, ce qui expliquerait une bonne part des 10 à 50 cm d'écart de position d'une pièce à l'autre. Rien n'est changé dans les programmes tant que la mesure n'est pas faite.
- **Le 15, de 12 h 17 à 13 h 36, la plus longue sortie à ce jour** : de la base à la pièce du bas à droite (jamais vue, porte K23), puis au fond de la cuisine, et retour ; 45 m, six pièces, 34 tours sur place. **Le robot est revenu à 3 cm de son point de départ**, et sa position calculée y était juste à 2 cm (mesure de l'autre session). Trouvé en route : **mon cap était faux de 10° depuis 9 h 55 le matin**, après les patinages au bord du tapis ; c'est ce qui décalait les pièces de 25 à 50 cm entre elles. Les murs du couloir l'ont montré ; corrigé, tout se recoupe à quelques centimètres. **Le seuil de la cuisine** se franchit vers la cuisine de biais et à 15 cm/s (de face les roues patinent, à reculons l'arrière bute) ; dans l'autre sens il passe sans rien. Quatre contacts légers et un arrêt du robot de lui-même au pied d'un meuble sombre. **Pas atteint : le vrai coin du fond de la cuisine** ; je l'avais annoncé à tort, le robot était devant le réfrigérateur, à un mètre. La brosse latérale n'a pas tourné au seuil, alors que tu l'avais demandé.
- **Le 15, de 13 h 49 à 15 h 53, retour à la cuisine par la nouvelle porte (case H18), jusqu'au vrai coin du fond** : la poche à droite du réfrigérateur, devant la poubelle (C39 sur ta carte), puis retour devant la base. La porte étroite se passe aux capteurs, sans contact à l'aller. **Le seuil de la cuisine n'a cédé qu'au cinquième essai** : de biais, la première roue monte et la seconde reste coincée ; c'est un pivot sur place qui la fait monter, ton idée de « wiggle ». La brosse latérale n'y change rien. Deux fois tes photos m'ont corrigé : j'avais pris la porte du réfrigérateur pour le mur du fond, puis annoncé une case fausse (ma position calculée était un mètre trop à l'est au fond de la cuisine, pour une raison non trouvée). Au retour, mené vite à ta demande : dix contacts légers du pare-chocs sur la séance, et **28 cm d'erreur à l'arrivée, vus et corrigés grâce aux faisceaux de la base** que tu m'as demandé de vérifier. Une attente de 19 minutes au milieu : un VPN du PC a coupé l'enregistreur, et le cerveau a gardé l'ancienne liaison pour vivante (défaut du firmware trouvé, correction proposée).
- **Le 15 au soir, l'analyse de la journée**, que tu as demandée (`notes/P_capteurs_en_direct.md`) : sur les six trajets du jour, 92 m en 3 h 02, le robot n'avance que 11 % du temps ; il attend mon ordre suivant 59 % du temps et tourne sur lui-même 19 % du temps (166 tours complets). **Il ne longe pas les murs parce qu'en roulant il ne les voit pas** : son capteur de distance regarde devant, et ses capteurs de côté ne lisent rien au-delà de 6 cm. Sur 17 contacts dans la journée, ses capteurs optiques en annonçaient 7 et mon pilotage n'en tenait pas compte. **Tu as accepté, auprès de l'autre session, un essai d'une minute du gyroscope à la prochaine séance**, et demandé que ma liste porte ses propositions et ton idée du capteur de distance tourné à 90° : la liste est au § 8 de cette note, résumée plus bas dans « La suite ».
- En ce moment (état relevé le 21 à 14 h 11) : robot **à l'arrêt là où tu l'as conduit toi-même à 13 h 37** (batterie à 88 %) ; je ne sais pas où il est dans l'appartement. Vers 14 h 09 le cerveau a été remis sous tension et le robot roulait de nouveau un peu : tu t'en occupais toi-même. Il ne charge pas tant qu'il n'est pas sur sa base. Entre 13 h 43 et 14 h 08 le capteur de distance a cessé de répondre quatre fois, puis a repris : si tu as touché à ses fils, dis-moi ce qui a changé avant l'essai. Cerveau en **version 14** ; la version 15 est prête sur le PC, pas installée. Rien n'a été envoyé au servo. **Une première simulation du suivi de mur** (un seul mur lu de côté) donne le couloir de 3,9 m en une demi-minute au lieu de cinq minutes. En attente de toi : le go pour installer la version 15 et essayer le capteur tourné (trois minutes, robot immobile, toi à côté pour regarder les fils). Non fait : le sud de la cuisine, les mesures à la règle.

## Le but, pour mémoire

Dire « va dans telle pièce » et que le robot y aille seul. L'ordre fixé jusqu'au 15 novembre : d'abord une position précise, ensuite la vitesse. **Depuis le 21 novembre, à ta demande : la vitesse d'abord.** Le nettoyage (brosses, aspirateur) vient après : pour l'instant elles restent à l'arrêt.

## Le chemin parcouru

| Date | Ce qui a été franchi |
|---|---|
| 8 nov. | Recherche : comment parler au robot (la prise sous le capot) |
| 9 nov. | Le cerveau branché ; pilotage au téléphone en Wi-Fi ; capteur de distance sur son servo ; premier tour sur place |
| 10 nov. | Arrêt automatique sur pare-chocs ; premières cartes ; le plan de l'appartement sert de fond ; carte quadrillée « comme aux échecs » ; le robot explore seul le couloir et la pièce centrale (77 m) ; premier trajet demandé par cases |
| 13 nov. | Nouvelle localisation et conduite d'un seul tenant (2 à 3 fois plus rapide) ; firmware v10 ; les repères ; la base mesurée (case B16) ; premier accostage réussi ; premier aller-retour jusqu'en C28 ; découverte du patinage d'une roue |
| 14 nov. | Le même aller-retour refait pour mesurer : deux fois plus vite. Second accostage : manqué. Centrage automatique des passages étroits écrit, puis essayé dans la cuisine et le couloir. La cuisine explorée puis cartographiée (16 repères). Trous dans les lectures des capteurs trouvés et corrigés (version 11). Seuil de la cuisine franchi, retour devant la base sans contact. Deux sessions à part : l'audit, puis la revue de la localisation et du code ; version 12 du cerveau ; version 13 prête, pas encore installée |
| 15 nov. | Version 13 installée et vérifiée en mouvement. Essai des petits pivots. La bande de parquet de la pièce à gauche cartographiée ; le tapis vert foncé trouvé : le robot refuse d'y monter, puis bute sur son bord. Deux tours de suite au même endroit, aller et retour de 2 m. Version 14 écrite. Version 14 installée ; le tapis pris à reculons. Série d'essais devant la base : ses faisceaux lus au centimètre ; contour du tapis ; trois stations de plus dans la pièce à gauche. Grande boucle de 45 m par la pièce du bas à droite et la cuisine, retour à 3 cm du départ ; erreur de cap de 10° trouvée et corrigée ; seuil de la cuisine franchi de biais L'après-midi : la cuisine jusqu'au coin du fond par la nouvelle porte H18 ; le seuil franchi par un pivot sur place ; retour calé sur les faisceaux de la base. |

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
| Vitesse | 32 m en 23 min, soit 1,4 m par minute en moyenne. Les tours sur place, ceux où il regarde autour de lui, prenaient 46 % du temps sur une boucle d'essai du 13. Le 15, sur six trajets (92 m en 3 h 02) : il avance 11 % du temps, attend mon ordre suivant 59 % du temps et tourne sur lui-même 19 % du temps (`notes/P_capteurs_en_direct.md`) |
| Position loin des repères | Le calcul seul s'est trompé de 20 à 30 cm devant la base ; il faut passer par les endroits à repères |
| Repères qui se trompent | Le 15, trois corrections des repères de 16 à 24 cm (D12, D14, devant la base) sont contredites par les roues, les parois et la base, d'après la session de revue : un objet a sans doute changé de place. La position de fin de séance que je t'avais annoncée (« à 1 m devant la base ») était donc fausse d'une cinquantaine de centimètres. À corriger : ne plus appliquer une grosse correction quand le robot vient de rouler peu |
| Patinage | Une roue seule : le code qui le détecte et ralentit est écrit et vérifié sur les enregistrements, pas encore prouvé sur le robot. Les deux roues ensemble, comme sur le seuil de la cuisine le 14 : pas détecté. La revue montre que le courant de la batterie signale les deux cas, sans fausse alerte sur 195 m d'avances : à ajouter au pilote |
| Trous dans les lectures | Corrigé le 14 par la version 11 du cerveau (ton tampon) : le cerveau n'attend plus le Wi-Fi. Restent deux choses sans explication : le robot a redémarré tout seul une fois, et un tour sur place a tourné trop vite une fois. L'audit signale aussi trois points à durcir encore (note I) |
| Version 12 du cerveau | Installée le 14 à 18 h 35 par la session de revue, à ta demande : cap compté dans un nombre plus long, arrêt des roues répété au démarrage, cinq petites protections. Vérifiée robot immobile seulement : le premier tour sur place et la première avance sont à regarder de près |
| Version 13 du cerveau | Écrite le 14 au soir par la session de revue : elle garde en entier ce que le robot écrit de lui-même (réveil, charge, redémarrage) et ajoute une sonde fermée par une clé, pour lire les capteurs que la documentation ne cite pas. Installée le 15 à 8 h 36, vérifiée au repos et en mouvement |
| Le tapis de la pièce à gauche | Vert foncé, à franges. Les capteurs de vide y lisent 36 à 81, contre 2 600 sur le parquet : pour le robot c'est un vide, et sa propre sécurité coupe les roues dès qu'il avance ou pivote dessus. Il recule sans problème. Marqué zone interdite, tracé provisoire. Pour y rouler, et en faire une zone de nettoyage comme tu le veux, il faut lever cette protection : ta décision. Abordé de face depuis le parquet, sa brosse latérale à l'arrêt se glisse sous le bord et il pivote sur place (41° puis 67°). La version 14 la fait tourner lentement : une montée réussie, une ratée (brosse bloquée dans les franges). **En marche arrière il monte sans problème**, tourne au milieu du tapis et ressort en avant : c'est la façon retenue. Restent à relever : le haut et le bas du tapis, la bande entre le lit et le mur |
| Petits pivots du centrage | Chaque série (un quart de tour, un demi-tour, un quart de tour) fait reculer le robot d'environ 5 mm que les roues ne comptent pas. Mesuré une fois, sur une cible médiocre : à refaire face à un vrai mur |
| Cuisine | Trois passages, 16 repères. Sans repère encore : le coin de la porte du balcon (G36) et le côté droit de l'îlot. Le seuil de sa porte passe sans effort vers la pièce centrale ; vers la cuisine il se franchit de biais, puis par un pivot sur place qui fait monter la seconde roue (trouvé le 15). Le coin du fond est atteint depuis le 15 ; le sud de la cuisine n'est pas exploré |
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
5. **Des erreurs de ma part, à ne pas refaire** : corriger le cap du robot à la main (trois contacts le 14) ; annoncer une case calculée de tête (cases fausses le 13, et encore une le 15) ; le 15, un recul automatique lancé après un pivot (95 cm à l'aveugle) et un cap mal relu qui m'a fait perdre la position un quart d'heure.
6. **Un tapis très sombre est un vide pour le robot.** Ses capteurs de vide mesurent la lumière que le sol renvoie ; le poil vert foncé n'en renvoie presque pas.

## La suite que je propose, dans l'ordre

**Le plan pour la vitesse, au 21 novembre** (le détail est dans `notes/P_capteurs_en_direct.md`, § 9). Le 15, sur 92 m, le robot n'avançait que 11 % du temps : il attendait mon ordre suivant 59 % du temps et tournait sur lui-même 19 % du temps. Le but : qu'un trajet connu se fasse dix fois plus vite, sans dépasser les 15 cm par seconde que tes règles autorisent.

1. **Voir les murs de côté** : la version 15 du cerveau (prête) et l'essai du capteur tourné à 90°, robot immobile, à ton go. Puis une ligne droite de 2 m le long d'un mur, capteur tourné, pour voir ce qu'il lit en roulant.
2. **Rouler sans s'arrêter** : une version 16 du cerveau, à écrire, où le PC peut corriger le cap et prolonger une avance pendant qu'elle se fait. Aujourd'hui chaque avance s'arrête au bout de 2 m au plus, et toute correction demande un arrêt.
3. **Longer un mur** : le programme du PC qui tient le robot à distance constante d'un mur lu de côté (le prototype de l'audit existe, essayé en simulation). Premier but : le couloir, 3,9 m en moins d'une minute, contre 5 min 19 le 14.
4. **Ne plus m'attendre** : un trajet connu rejoué d'une seule commande, qui enchaîne les murs à longer, les portes et les recalages, et ne m'appelle que si quelque chose ne va pas.
5. **Garder un œil devant** : capteur tourné de côté, c'est le pare-chocs qui protège l'avant. Les capteurs optiques du pare-chocs annonçaient 7 contacts sur 17 le 15 : ralentir quand ils voient quelque chose.

**La liste du 15 au soir**, qui reste valable pour le reste (le détail est dans `notes/P_capteurs_en_direct.md`, § 8) ; l'essai du gyroscope y est fait (le 21), la photo des fils n'est plus demandée :

- **À la prochaine séance, une minute avant de partir : l'essai du gyroscope que tu as accepté.** Le robot fait deux tours sur lui-même devant sa base pendant que je lis les trois axes de son gyroscope ; il faut que tu sois à côté de lui. L'essai dira si le gyroscope compte un peu faux parce que sa carte est montée penchée.
- **Sans rien changer au robot** : un trajet connu rejoué d'une seule commande (c'est par là que je propose de commencer) ; ralentir quand les capteurs optiques du pare-chocs voient quelque chose ; se recaler tout seul sur la base, sur la baguette du seuil de la cuisine et sur les montants des portes ; ne plus croire un recalage que rien d'autre ne confirme.
- **Une version 15 du cerveau, dont rien n'est écrit** : les tours sur place tantôt vers la gauche, tantôt vers la droite ; les trois axes du gyroscope et l'angle du servo dans le journal ; la console qui lâche un client muet ; puis, selon ce que dira l'essai du gyroscope, une autre façon de compter les rotations. Chaque installation te sera demandée.
- **Ton idée du capteur de distance tourné à 90° en roulant** : d'abord une photo de ses fils (la limite de 30° avait été posée le 9 parce qu'ils sont courts), des fils plus longs s'il le faut, deux mesures à la règle, puis le cerveau et le programme qui longe un mur.

**Ce qui était déjà sur la liste, et y reste.**

**Finir la pièce à gauche et son tapis.** Le robot y monte à reculons et s'y déplace. Il reste à relever le haut et le bas du tapis et à repérer ses petites zones très sombres, pour pouvoir en faire la zone de nettoyage que tu veux. Pour ces petites zones seulement, il faudra peut-être choisir comment lever sa protection contre le vide. Soit par le cerveau : le robot ne surveille plus rien lui-même, le cerveau surveille le vide et les roues levées à sa place, partout sauf sur le tapis ; c'est une version du cerveau à écrire, sans geste de ta part, et c'est ce que je recommande parce qu'on garde la lecture du sol. Soit en masquant ses quatre capteurs de vide au papier blanc : immédiat, mais le robot ne voit plus le sol nulle part. Dans les deux cas il ne se protège plus seul d'une vraie marche. La pièce derrière la porte H12 (celle de K9 et K10) n'a toujours aucun repère.

1. **L'accostage** : enlever l'objet qui se tient devant la base, à 40 cm d'elle et à peine à gauche de son axe (le capteur le voit, c'est là que le robot touche à chaque fois), puis réessayer l'ordre « rentre à la base » avec ton accord.
2. **Lire l'audit et la revue ensemble.** L'audit (`notes/I_audit_regard_neuf.md`) : le robot n'avance que 17 % du temps ; c'est la carte des repères qu'il faut rendre cohérente ; le gyroscope est monté penché et le cerveau n'en lit qu'un axe. La revue (`notes/J_revue_localisation.md`) y ajoute : arrêter une avance quand le courant de la batterie monte (les roues forcent), se servir du capteur de distance comme d'une règle pendant les avances, et, avant tout achat, un téléphone posé en hauteur avec un marqueur imprimé collé sur le robot, pour avoir sa position vue de l'extérieur.
3. **La dérive du calcul de position dans le couloir mené au centrage** (30 cm). Le seuil de la cuisine, lui, est réglé depuis le 15 : de biais pour la première roue, puis un pivot sur place pour la seconde. Pour la dérive : la revue a mis l'échelle du plan hors de cause (juste à 0,5 % près) et son essai de trois minutes sur place, fait le 15, montre que les séries de petits pivots du centrage font reculer le robot d'environ 5 mm chacune : une dizaine des 24 cm s'expliquent ainsi.
4. **Passages étroits plus rapides** : le centrage automatique marche sur le robot (passage de la cuisine), mais il s'arrête tous les 20 à 40 cm. L'audit propose de lire les distances de côté en roulant, ce qui demande un petit changement de montage : c'est aussi ton idée du 15, le capteur de distance tourné à 90° (voir la liste du 15 au soir, plus haut).
5. **Aller plus vite** : moins de tours sur place, seulement là où ils servent.
6. **« Va dans telle pièce »** : tu me donnes le nom des pièces, je les attache aux cases ; une seule commande enchaîne trajet, portes et repères.
7. **La carte vivante sur ton téléphone** : l'autre session l'a mise à jour ce matin (la base en B16, le robot reconnu sur sa base, les obstacles et les repères). Elle n'a pas encore été vue sur ton téléphone ; un VPN actif sur le PC peut la bloquer.

## Ce dont j'ai besoin de toi

- **Maintenant (21 novembre)** : ton go pour installer la version 15 et essayer le capteur tourné. Pendant l'essai (trois minutes), rester à côté du robot et regarder les fils du capteur ; si l'un d'eux se tend, m'écrire « stop ». Ne pas basculer le VPN du PC pendant un trajet. **À la règle, quand tu veux** : du devant des deux « yeux » du capteur de distance au devant du pare-chocs ; de l'axe du servo au devant du capteur ; et, au mètre, la largeur de l'encadrement de la porte H18.
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
| La campagne d'essais de la session de revue et ses résultats | `notes/O_campagne_essais.md` |
| L'analyse de la journée du 15 et la liste de travail | `notes/P_capteurs_en_direct.md` |
| Les outils et leur mode d'emploi | `code/README.md` |
| Les enregistrements | `mesures/` |
| Le plan de l'appartement et les cartes | `plan_lidar/`, sur ton PC seulement : jamais envoyé sur GitHub |
