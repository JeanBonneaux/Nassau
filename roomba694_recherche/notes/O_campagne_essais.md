# O — Campagne d'essais : les coins sombres du robot, et une localisation plus précise

Session de revue, 2026-11-15, 10 h 30. Demande de l'utilisateur, telle quelle :

> « une fois cette run process, continue d<explorer les coins sombres du fonctionnement, et de mapper par des tests et d<ameliorer le software et de voir ce qu<il nous cache, ce qui pourrait nous etre utile, tu parle a l<autre session, elle execute le pilotage et tu ecoute et commande, et analyse, mappons loin, augmentons nos capacites de localisation precise »

Cette note est le plan de travail. Elle est tenue à jour : chaque essai y reçoit son résultat et le nom du fichier où il est.

## En bref

1. **Les rôles.** La session de revue choisit les essais, les commande à la session de navigation, écoute et analyse. La session de navigation pilote, et reste seule à juger de la sécurité d'un geste : elle peut refuser ou adapter un essai. La session de revue n'envoie aucun ordre de roues.
2. **Deux buts** : savoir ce que le robot fait et cache d'utile ; savoir où il est, plus précisément.
3. **Ce que la matinée a appris** (note N) : les roues et les tours sur place sont bons à 1 à 3 cm ; c'est le calcul de la position qui saute de 16 à 31 cm. La campagne commence donc par ce qui donne un repère sûr, et par ce qui empêche un saut.
4. **Ce qui reste interdit sans un mot de l'utilisateur** : le mode Full ; le mode d'essai d'usine ; les brosses autres que la brosse latérale ; l'ordre « rentre à la base » (son accord à chaque fois).
5. **Les ordres inconnus du robot sont permis depuis le 15 à 10 h 50** : à ma question « est-ce que j'essaie aussi des ordres inconnus ? », posée après lui avoir redit le risque, l'utilisateur a répondu « Oui, essaie ». Marche à suivre et garde-fous dans la note L § 4.7 ; c'est l'essai 7.
6. **La trouvaille du 15 à 11 h 30 : le capteur de distance n'est pas où les outils de carte le comptent** (§ 5.6). Ils le placent 27 mm en avant du centre du robot ; l'approche du mur de l'essai 4 montre qu'il est à plus de 86 mm, et la photo du robot le montre vers 125 mm. Si la règle le confirme, chaque écho est placé 9 cm trop près du robot depuis le 10. C'est la première erreur systématique trouvée dans la mesure elle-même, et non dans le calcul. À midi une seconde est apparue, liée à la première : l'échelle du plan (53 pixels par mètre) avait été réglée le 10 avec le capteur mal placé, et vaudrait plutôt 51 (§ 5.10). Les deux se compenseraient dans une pièce. Mais un rejeu fait à 12 h 25 montre qu'elles n'expliquent pas le décalage de 25 à 50 cm entre la pièce de la base et sa voisine.
7. **L'explication de ces décalages, trouvée par la session de navigation à 12 h 26 et confirmée par le gyroscope : le cap retenu était faux de 10 à 22° depuis 9 h 55** (§ 5.11). Il avait été repris au filtre après des patinages. Le gyroscope, lui, a tenu 1° en deux heures et demie. L'axe de la base « incliné de 10,6° » n'était que cela.

## 1. Les essais courts, dans l'ordre

Chacun répond à une question. Un tour sur place avant le premier et après le dernier.

| N° | Essai | La question | Ce qu'on en ferait | État |
|---|---|---|---|---|
| 1 | Trois traversées de l'axe de la base, à 0,7 m, 1,1 m et 1,5 m d'elle, à 60 mm/s ; puis un tour sur place sur l'axe | Où exactement le faisceau vert passe-t-il au rouge ? Les deux récepteurs de devant donnent-ils un cap ? | un repère absolu, au centimètre, près de la base ; un contrôle de « devant la base » | **fait** (§ 5.2) : axe lu à 1 cm près, cap à 2° près |
| 2 | Lecture des numéros cachés, robot en mode passif sur l'axe, base vue | L'octet parasite 177 vient-il quand la base est vue ? | savoir quand les lectures sont brouillées | **fait** (§ 5.3) : non, il ne vient pas |
| 3 | Avance à 30 mm/s jusqu'à la ligne sombre du tapis, puis recul droit capteur posé dessus | Le robot surveille-t-il le vide en reculant ? | franchir un bord sombre à reculons, sans rien changer d'autre | **essayé, pas tranché** (§ 5.7) : la ligne sombre n'a pas été retrouvée |
| 4 | Approche lente d'un mur nu, de 45 cm à 3 cm, à 40 mm/s | Que lisent les six capteurs optiques du pare-chocs selon la distance ? | une distance de près, et un arrêt avant le contact | **fait** (§ 5.5) : le capteur centre gauche voit le mur dès 21 cm ; et une trouvaille (§ 5.6) |
| 5 | Essai des pivots devant un mur nu | Les séries de pivots reculent-elles vraiment le robot de 3 à 5 mm ? | corriger l'estime dans les couloirs (note J § 2.3) | **fait** (§ 5.4) : non, 1,4 mm par série ; rien à corriger |
| 6 | Lecture des numéros cachés, robot sur sa base en charge | Que deviennent les numéros 62, 128, 132 et 145 en charge ? | finir de lire ce que le robot cache | à faire en fin de séance, robot posé sur sa base |
| 7 | Ordres inconnus, un à la fois, par étapes (note L § 4.7) ; robot posé sur un support, les deux roues dans le vide, hors de sa base, quelqu'un à côté ; menée par la session de revue, la navigation ne pilotant pas | Le robot accepte-t-il des ordres que sa documentation ne donne pas ? | peut-être rien ; peut-être un ordre ou une lecture utile | **permis par l'utilisateur le 15 à 10 h 50 (« Oui, essaie »)** ; à faire après les essais roulants |

| 8 | Mesure à la règle, robot arrêté : du devant des deux « yeux » du capteur de distance au devant du pare-chocs ; ou, sans règle, une approche d'un mur nu jusqu'au contact | Où est le capteur de distance sur le robot ? Les outils comptent 143 mm, l'essai 4 et la photo du robot disent 45 à 50 mm | placer chaque écho au bon endroit : 9 cm d'écart sur chaque mur (§ 5.6) | **demandé à l'utilisateur le 15 à 11 h 35** |
| 9 | Mesure au mètre, robot laissé devant la base où il est depuis 12 h 03 : du devant de la base au bord du robot le plus proche | À quelle distance de la base le robot est-il vraiment ? Quatre façons de la prendre donnent de 1,2 à 1,9 m (§ 5.9) | savoir si le filtre se trompe du nord au sud devant la base | **demandé à l'utilisateur le 15 à 12 h 15** |
| 10 | Trois tours sur place de suite au même endroit | Le facteur du gyroscope vaut-il encore 1,0045 ? | éviter une erreur de cap de 1° par tour | **fait** à 12 h 02 (§ 5.8) : oui, 1,0040 à 1,0045 |

## 2. « Mappons loin » : les règles d'une cartographie longue

À proposer à la session de navigation après les essais courts. Elles viennent toutes de mesures de la note N.

1. **Quand l'estime et la correction se contredisent de plus de 12 cm sur moins de 2 m, un second tour est fait sur place.** La correction n'est pas refusée d'office : cette règle-là, rejouée sur les séances enregistrées, dégrade la position (§ 5.1).
2. **Le cap vient du gyroscope**, multiplié par 1,0045, et non d'un cap recompté après chaque geste. La perte de position de 10 h 10 venait d'un cap faux de 94°.
3. **Une avance qui dévie s'arrête** (roues et gyroscope en désaccord de 8°), et un tour sur place suit avant de repartir.
4. **Un tour sur place tous les 2 m au plus**, loin des bords de tapis (plus de 20 cm).
5. **Les anciens repères ne servent plus tels quels** près de la base et de D12 : ils y ont fait sauter la position trois fois. Un fichier de repères refait avec l'estime comme contrainte est en préparation (§ 3).
6. **L'outil d'analyse en direct signale** les sauts de position, les avances déviées, les roues qui forcent et les chutes du mode Safe ; `rv_ou_est_le_robot.py` redonne la position par l'estime à tout moment.

**Le parcours commandé le 15 à 11 h 40 : une grande boucle qui se mesure elle-même.** Après la fin de la pièce du tapis (demande de l'utilisateur du matin) :

1. départ d'un point P devant la base (case C16, sur la ligne de l'essai 1) : une traversée de l'axe de la base, puis un tour sur place ;
2. aller le plus loin possible de la base, dans une zone jamais vue, par un chemin déjà roulé jusqu'à sa porte (12 m d'aller ou plus ; le choix de la zone est laissé à la session de navigation, selon les portes ouvertes) ; stations tous les 2 m au plus ;
3. là-bas : cartographie par stations, deux doubles tours, une avance face à un mur ;
4. retour par le même chemin jusqu'à P, à 20 cm près et au même cap : une traversée de l'axe, un tour sur place.

Les deux tours faits en P se comparent directement (3 à 8 mm le matin) et donnent le vrai écart entre le départ et l'arrivée ; la traversée de l'axe le recoupe. On saura donc, sans le plan et sans dépendre de la place du capteur de distance, de combien dérivent l'estime seule, le filtre et les repères sur une vraie longue distance.

## 3. Le logiciel : qui fait quoi

Pour ne pas écrire à deux dans les mêmes fichiers.

| Chantier | Qui | État |
|---|---|---|
| Repères refaits avec l'estime comme contrainte (fichier à essayer avec `--reperes`) | session de revue, dans `data_analysis/` | **fait, et abandonné** : pas mieux que les anciens sur trois séances tenues à l'écart (§ 5.1) |
| Refus des corrections de plus de 12 cm sur trajet court, dans l'explorateur | session de navigation, sur ma proposition | **proposition retirée** : rejouée sur 15 séances, elle dégrade (§ 5.1) |
| Cap du gyroscope donné au filtre | session de navigation | proposé |
| Firmware, version 15 : arrêt d'une avance sur écart de cap, coupure de la brosse latérale sur son courant, deux arrêts manquants de la brosse | session de navigation ; je relis avant installation | notée par elle |
| Firmware : les quatre indicateurs « vide » du robot dans l'état et le journal ; un arrêt sur capteur optique du pare-chocs | à décider avec l'utilisateur | idée |
| Défaut de ma sonde (ses réponses lues comme du texte) | session de revue, en prévenant la navigation | à faire |
| Place du capteur de distance dans les outils (`carto.DX`, 27 mm aujourd'hui) | session de navigation, après la mesure à la règle (§ 5.6) ; les repères seront à refaire | en attente de la mesure |
| Arrêt du cerveau sur le capteur optique centre gauche (au-dessus de 300 : mur clair à 10 cm du capteur de distance) | à décider avec l'utilisateur ; firmware, donc son accord | idée, chiffrée au § 5.5 |
| Carte des capteurs de vide du tapis (`rv_tapis_carte.py`) | session de revue | faite pour `exploration28` et `29` |

## 4. Les coins sombres : où on en est

Détail dans la note L. La liste des quatorze sondages y est au § 1.

| Sujet | Ce qu'on sait | Ce qui manque |
|---|---|---|
| Mode Safe et sol sombre | surveillé seulement en roulant ; il faut 0,1 s sous 100 ; c'est une ligne étroite au bord du tapis, pas le poil ; une lecture de 180 à 250 ne le fait pas tomber (§ 5.7) | le recul : la ligne n'a pas été retrouvée à l'essai 3 |
| Sommeil | cinq minutes après le dernier ordre, hors du mode Safe ; deux sortes de réveil, avec ou sans texte | — |
| Numéros de capteurs cachés | horloge (134 à 136), mode (131), deux valeurs qui suivent le mode (128, 145) | 62 et 132 ; l'octet parasite 177 (essais 2 et 6) |
| Charge lue par le robot | elle peut sauter de 115 mAh à un réveil | pourquoi |
| Brosse latérale | à l'arrêt elle se prend sous un bord de tapis ; en marche et d'équerre le bord passe ; en reculant il passe sans elle | la plus petite puissance qui suffit |
| Capteurs optiques du pare-chocs | un obstacle étroit vu 15 cm avant le contact ; un mur clair vu par le centre gauche dès 21 cm du capteur de distance, courbe au § 5.5 | la droite, qui répond quatre fois moins : une approche sous un autre angle |
| Place du capteur de distance | à plus de 86 mm en avant du centre (essai 4), vers 125 mm d'après la photo ; les outils comptent 27 mm (§ 5.6) | la mesure à la règle (essai 8) |
| Faisceaux de la base | vue 56 % du temps devant elle, jamais 40 cm à côté | leur forme (essai 1) |
| Ordres inconnus, mode d'essai d'usine | rien d'essayé ; déconseillés (note L § 3.5 et § 4.7) | la décision de l'utilisateur |

## 5. Résultats

### 5.1 Le logiciel de position : deux idées essayées sur les séances enregistrées, et retirées (10 h 40)

**Mesuré sur le PC**, sans le robot (`rv_reperes_estime.py`, `rv_regles_fusion.py`, résultats dans les fichiers `results_` du même nom).

- **La référence.** La position des 207 tours sur place des séances 6 à 29 a été recalculée d'un seul coup, avec trois sortes de contraintes : l'estime d'un tour au suivant (poids fort), les tours voisins comparés par leurs parois (fort dans une même séance, moyen entre deux séances), les positions retenues à l'époque (faible). C'est la meilleure estimation disponible, pas une vérité : elle est sans doute incertaine d'une dizaine de centimètres.
- **D'un jour à l'autre, comparer deux tours par leurs parois se trompe souvent de 10 à 20 cm.** Dans une même séance, la comparaison est bonne à moins d'un centimètre. Une porte ou un objet a bougé entre-temps. C'est la vraie limite des repères, et refaire leurs positions n'y change rien : sur trois séances tenues à l'écart, les repères refaits donnent 2 sauts au lieu de 3 (`exploration26`), 1 au lieu de 2 (`exploration27`), 6 contre 6 (`exploration19`).
- **Le « garde-fou » que j'avais proposé dégrade.** Rejoué sur 15 séances et 192 tours, distance à la référence (médiane, puis 9 tours sur 10) : positions retenues à l'époque, 97 et 222 mm ; garde-fou, 142 et 318 mm ; estime tirée de 30 % vers la correction, 93 et 241 mm ; estime seule, 189 et 446 mm ; lissage sur huit tours, 82 et 216 mm. Le garde-fou échoue quand le premier tour d'une séance est mal placé : il refuse ensuite les bonnes corrections.
- **Pour `exploration26`**, la référence met les tours de D12 vers x = 5 500 mm : entre le filtre (5 414) et les repères (5 664). Mon « décalée de 25 cm vers l'est » de la note N § 3.3 était trop fort de moitié ; le saut, lui, est bien réel.
- **Ce qu'on en tire.** Aucune règle simple ne fait nettement mieux que l'existant contre cette référence. Il manque un repère absolu sûr, pour corriger et pour juger. D'où l'essai 1 (les faisceaux de la base).

### 5.2 Essai 1, les faisceaux de la base (10 h 47 à 10 h 56) : fait, et c'est un vrai repère

**Mesuré** (séance `exploration30` : six traversées à 60 mm/s et un tour sur place, menés par la session de navigation ; `rv_faisceaux_base.py`, résultats dans `results_rv_faisceaux_base_exploration30_20261115_104014.txt`). Les positions sont celles de l'estime, accrochée au tour de départ de la séance.

- **Le récepteur du dessus est 144 mm en avant du centre du robot.** Sans cette correction, la même frontière paraît à 289 mm d'écart selon le sens de marche ; avec elle, l'aller et le retour coïncident.
- **L'axe de la base se lit au centimètre, et il se répète.** Trois lignes, chacune traversée dans les deux sens :

  | Ligne | Distance à la base (d'après le plan) | Axe à l'aller | Axe au retour | Vert seul | Les deux | Rouge seul |
  |---|---|---|---|---|---|---|
  | B | 0,87 m | u = 408,9 | u = 409,0 | 18 cm | 5,5 cm | 27 cm |
  | C | 1,25 m | 404,7 | 405,2 | 24 cm | 1 à 2 cm | 42 cm |
  | D | 1,66 m | 400,9 | 401,2 | 31 cm | aucun | 55 cm |

  Un pixel vaut 19 mm : l'aller et le retour s'accordent à 2 à 10 mm. La base est vue sur 22 à 34 % des lectures pendant une traversée.
- **L'axe est une ligne droite** (3 mm de reste sur les trois lignes), **mais inclinée de 10,6°** dans le repère de la séance : elle part vers l'ouest de 7,5 cm tous les 40 cm. Prolongée jusqu'à la base, elle arrive 24 cm à l'est de la position que le plan donne à la base.
- **D'où viennent ces 10,6° : non tranché.** L'utilisateur répond « Base collée au mur » (avec une photo, qui n'est dans aucun fichier), et sur la carte quadrillée le mur derrière la base est horizontal. Un axe d'équerre avec ce mur pointerait plein bas. Il reste donc deux lectures : le cap retenu pendant la séance est trop petit d'une dizaine de degrés ; ou l'axe des faisceaux n'est pas d'équerre avec le mur (la base fait 13 cm de large : un côté décollé de 2,4 cm suffit ; ou ses émetteurs ne sont pas dans son axe). J'avais d'abord écrit à la session de navigation que c'était l'angle du mur sur le plan : c'était faux, et je l'ai corrigé. **Ce qui tranchera** : la montée sur la base par l'axe, proposée par la session de navigation ; robot posé sur ses contacts, son cap est celui de la base. **Tranché à 12 h 40 (§ 5.11) : c'est la première lecture.** Le cap retenu était trop petit de 10,9° au tour de 10 h 41, d'après le gyroscope enchaîné et les murs du couloir ; l'axe de la base est d'équerre au mur.
- **La distance à la base n'est pas sûre non plus.** La largeur des faisceaux (505, 675 et 890 mm sur les trois lignes) met la base 1,05 à 1,2 m au nord de la première ligne ; le plan et le filtre disaient 0,87 m.
- **Les deux récepteurs de devant donnent la direction de la base.** Pendant le tour sur place fait sur l'axe (robot à 5 mm de la ligne), ils ne la voient qu'entre les caps 60° et 92° ; leur cap moyen, 79,5°, est celui de l'axe mesuré (79,4°). En tournant, ils reçoivent le rouge, puis les deux faisceaux, puis le vert : le moment où les deux sont reçus marque la direction à 2° près environ.
- **Le récepteur du dessus ne voit rien quand le robot tourne le dos à la base** : il est masqué vers l'arrière par ce qui est monté sur le robot (remarque de la session de navigation, confirmée).
- **Ce qu'on en tire.** Près de la base, on a maintenant un repère absolu qui ne dépend ni du plan ni des repères : une traversée de 50 cm donne la position de côté à 1 cm près, et un tour sur place donne le cap à 2° près. Il reste à savoir où la base est vraiment sur le plan, et si elle est droite.

### 5.3 Essai 2, les numéros cachés robot en mode passif devant sa base (11 h 00) : fait, rien d'utile de plus

**Mesuré** (576 demandes de 11 h 00 min 43 à 11 h 01 min 20 ; détail dans la note L § 4.10).

- **L'octet parasite 177 n'est pas venu**, base vue et mode passif : il ne tient ni à l'un ni à l'autre. Il n'a été vu qu'une fois, dans la minute qui suivait le réveil du matin.
- **Le numéro 131 vaut 21**, alors qu'il valait 1 aux deux autres lectures en mode passif : ce n'est pas le mode tout court, contrairement à ce que j'avais écrit. Le numéro 62 vaut 0 base vue : ce n'est pas un « base en vue ».
- **Aucun capteur utile** dans ces numéros après quatre lectures : une horloge, deux valeurs qui suivent le mode, deux valeurs qui changent sans qu'on sache pourquoi.

### 5.4 Essai 5, les pivots devant un mur nu (11 h 07 à 11 h 10) : presque rien, l'alerte du matin est retirée

Séance `exploration31_20261115_110551`, essai mené par la session de navigation (`rv_essai_pivots.py`, firmware v14) : robot à 77 cm d'un mur, tourné vers lui, dix séries +90°, −180°, +90°. Dépouillement : `rv_pivots_lecture.py SEANCE FICHIER_pivots.json`, résultats dans `results_rv_pivots_lecture_20261115_110746.txt`.

**Mesuré.**

- Distance lue devant, robot revenu à son cap de départ, après chaque série : 769, 773, 771, 768, 769, 769, 775, 780, 778, 779, 780 mm. **+11 mm en dix séries.** (Le fichier de l'essai s'arrête à la neuvième série ; la dixième est lue dans l'enregistrement.)
- À 90° à gauche, une cible à 42 cm : 416 → 425 mm, +9 mm. À 90° à droite, une cible à 1,64 m : 1 647 → 1 640 mm, −7 mm. Les deux côtés disent la même chose : 8 mm vers la droite du robot.
- Les roues comptent 0 mm en x et −4 mm en y. Le cap revient à moins de 1° à chaque série. Pour 90° demandés le robot fait 89,1°, pour 180° 179,1°.
- Le glissement n'est pas régulier : rien pendant cinq séries, puis 6 mm et 5 mm aux séries 6 et 7.

**Ce que cela dit.** En dix séries le robot a glissé de 14 mm (11 mm vers l'arrière, 8 mm vers sa droite) sans que les roues le comptent : 1,4 mm par série. C'est quatre fois moins que ce matin devant la base (+44 mm), où la cible était irrégulière : la réserve écrite alors était la bonne. Le critère fixé avant l'essai (« plus de 3 cm en dix séries ») n'est pas atteint. **Un centrage ne coûte presque rien à l'estime ; rien n'est à corriger.** Le suivi en direct annonçait « 5 mm par série » : il dit maintenant 1,4.

Réserve : un seul essai, sur du parquet.

### 5.5 Essai 4, l'approche lente d'un mur (11 h 10 à 11 h 12) : la courbe des six capteurs optiques

Mené par la session de navigation : mur à 782 mm du capteur de distance, mise en place de 188 mm, approche de 440 mm à 50 mm/s arrêtée par le capteur de distance (seuil abaissé à 17 cm), 29 s d'arrêt, seconde approche de 61 mm (seuil à 10 cm, le plus bas que le cerveau accepte), 55 s d'arrêt, puis recul. **Aucun contact.** Dépouillement : `rv_optiques_mur.py SEANCE 11:10:43 11:12:30`, résultats dans `results_rv_optiques_mur_exploration31_1110.txt`.

**Mesuré.** Les distances sont celles du capteur de distance au mur, prolongées par les roues ; sous 20 cm le capteur lit encore 3 mm près ce que disent les roues.

| Capteur de distance au mur | gauche | avant gauche | centre gauche | centre droit | avant droit | droit |
|---|---|---|---|---|---|---|
| plus de 50 cm (repos) | 19 | 16 | 36 | 11 | 48 | 4 |
| 30 à 35 cm | 24 | 20 | 52 | 12 | 56 | 8 |
| 19 à 21 cm | 37 | 32 | 78 | 15 | 61 | 10 |
| 15 à 16 cm | 48 | 43 | 119 | 20 | 63 | 12 |
| 12 à 13 cm | 65 | 65 | 192 | 32 | 68 | 14 |
| 10 à 11 cm | 85 | 108 | 311 | 56 | 84 | 17 |
| 8 à 9 cm (le plus près) | 119 | 202 | 496 | 112 | 118 | 20 |

- Les valeurs sont les mêmes à l'arrêt qu'en roulant (à 153 mm : 48, 44, 119, 20, 64, 12 ; à 87 mm : 120, 202, 497, 112, 119, 21) et les mêmes au recul qu'à l'approche (centre gauche 254 et 241 entre 11 et 12 cm).
- Le capteur **centre gauche** est le plus parlant : le double de son repos à 21 cm, le triple à 16 cm, dix fois à 10 cm. L'avant gauche et le gauche suivent (le double vers 20 cm). Le centre droit répond quatre fois moins (le double à 14,5 cm), l'avant droit presque pas, le droit pas du tout.

**Ce que cela dit.**

- De 20 cm à moins de 9 cm, le capteur centre gauche donne une distance à un mur clair, par une courbe raide et régulière. C'est juste la zone où le capteur de distance cesse de servir (son seuil d'arrêt ne descend pas sous 10 cm). Un arrêt du cerveau sur « centre gauche au-dessus de 300 » arrêterait le robot avec le capteur de distance à 10 cm d'un mur clair.
- La gauche répond bien plus que la droite. Ou le robot n'était pas d'équerre, ou les capteurs ne se valent pas : l'objet mince touché à 10 h 21 avait lui aussi été vu par le centre gauche. À refaire sous un autre angle avant de s'y fier des deux côtés (l'approche à 30° que j'avais demandée n'a pas été faite).
- La courbe dépend de la couleur de l'obstacle : le 10, un autre obstacle ne donnait que 152 au centre gauche au moment du contact.

**La distance du pare-chocs au mur n'est pas écrite ici exprès** : elle dépend de la place du capteur de distance sur le robot, et c'est le sujet du paragraphe suivant.

### 5.6 Le capteur de distance n'est pas où les outils le comptent

**Ce que les outils comptent.** `carto.DX = 27` : le devant du capteur de distance serait 27 mm en avant du centre du robot, donc 143 mm derrière le devant du pare-chocs (rayon du robot : 170 mm). Cette valeur vient d'une seule mesure, le 10 à 13 h 04 : 143 mm lus au moment où le pare-chocs touchait une paroi. Le journal la disait « à confirmer à la règle ».

**Mesuré le 15.**

1. **À la fin de l'essai 4 le capteur lit 84 mm, robot arrêté, et le pare-chocs ne touche pas.** Les roues disent la même distance (782 mm au départ, 689 mm roulés). Avec 143 mm, le pare-chocs aurait dû toucher 59 mm plus tôt, et la session de navigation, qui se croyait à 14 mm du mur, a encore avancé de 61 mm. Donc le devant du capteur est à **moins de 84 mm** du devant du pare-chocs, soit à **plus de 86 mm** en avant du centre. Une lecture sans contact devant un mur ne peut pas tromper dans ce sens.
2. **La photo du robot envoyée par l'utilisateur à 11 h 01** le montre de dessus. Mise à l'échelle sur son diamètre : le récepteur infrarouge du dessus tombe à 148 mm du centre (144 mm mesurés par les faisceaux au § 5.2 : l'échelle est bonne), le devant du pare-chocs à 171 mm, et le devant des deux « yeux » du capteur de distance à **125 mm du centre, à 1 cm près**. Il est donc à 45 ou 50 mm du devant du pare-chocs, juste derrière lui. (La photo reste chez l'utilisateur ; elle n'est pas dans le dépôt.)
3. **Le contact du 10 est pourtant net** : `rv_capteur_avance.py` le retrouve dans l'enregistrement, 138 lectures, 0,98 mm lu par mm roulé, 142 mm au contact. Mais ce jour-là les capteurs optiques ne lisaient que 152 au centre gauche pendant le contact, contre 496 aujourd'hui à quelques centimètres du mur sans le toucher ; les deux capteurs de gauche lisaient le double d'aujourd'hui à distance égale ; et le journal du 10 note déjà que cette « paroi » n'était pas plane. Le pare-chocs a donc touché, le 10, autre chose que ce que le capteur de distance voyait : un objet bas ou mou placé 9 à 10 cm devant. L'autre explication, un capteur déplacé depuis le 10, n'est pas exclue.
4. **Le recoupement par le plan ne tranche pas** (`rv_dx_par_les_tours.py`, 147 tours, 592 murs vus de face) : les traits du plan ont 2 à 14 cm d'épaisseur et un halo gris, et le résultat change de −17 à +8 cm d'une séance à l'autre. Je n'en tire aucun chiffre.

**L'autre lecture, celle de la session de navigation** (son message de 11 h 13) : la place du capteur serait la bonne, et c'est le mur de l'essai 4 qui ne serait pas nu, quelque chose dépassant en hauteur d'au moins 6 cm (meuble à plinthe en retrait, rebord). Elle a déjà vu dans la pièce de la base un bord en hauteur que le capteur attrape de loin et sous lequel il passe de près. Cette lecture explique les 84 mm sans contact ; elle n'explique pas la photo. La mesure à la règle départage les deux.

**Ce que cela change, si la règle confirme 45 à 50 mm.**

- Chaque écho est placé **9 à 10 cm trop près du robot**, dans toutes les directions, depuis le 10.
- Devant un mur seul, les outils croient le robot 9 à 10 cm plus près du mur qu'il ne l'est. C'est le sens et la taille de ce qu'on voit devant la base : le filtre qui tire vers le nord à chaque tour (+154, +102, +87 mm à l'essai 1), la base trouvée 18 à 33 cm plus loin par la largeur des faisceaux que par le filtre.
- Entre deux murs opposés l'erreur se compense pour la position, mais la pièce paraît 19 cm trop étroite : le tour ne peut pas coller au plan des deux côtés à la fois, et la position retenue dépend du mur qui pèse le plus.
- Les repères ont été relevés avec la même erreur : vus du même côté ils se compensent, vus d'ailleurs non.
- L'arrêt du cerveau à 30 cm lus laisse 25 cm devant le pare-chocs, et non 16 : le robot s'arrête plus tôt qu'on ne le croyait devant un obstacle. Le pare-chocs touche un mur vers 45 mm lus.

**Ce qui est demandé.** Une mesure à la règle par l'utilisateur (essai 8). Ensuite, à décider avec la session de navigation : changer `carto.DX` demande de refaire les repères, relevés avec 27. Rien n'est changé tant que la règle n'a pas parlé.

**Une seconde piste, plus faible, notée pour ne pas la perdre.** Sur 210 trajets entre deux tours sur place, la correction de position faite au tour d'arrivée va en moyenne contre le trajet : −3,4 % de sa longueur (± 0,7 ; −3,9, −2,6 et −5,8 % les 10, 13 et 14 ; −2,2 % d'est en ouest, −5,9 % du nord au sud). Comme si le plan, converti en millimètres à 53 pixels par mètre, était un peu plus petit que ce que les roues mesurent. Sur 5 m cela ferait 17 cm, la taille des sauts de position. Ce peut être l'échelle du plan, ou un effet de l'erreur ci-dessus : à reprendre quand la place du capteur sera connue, avec deux longueurs mesurées au mètre ruban.

### 5.7 Essai 3, la ligne sombre du tapis (11 h 14 à 11 h 32) : cherchée, pas retrouvée

La session de navigation a cherché la ligne sombre à plusieurs bords du tapis, par pas de 8 mm, par pivots de 1°, par avances sous sept caps et par reculs de 30 et 45 cm (journal dans `exploration31_20261115_110551_ligne_sombre.txt`).

**Mesuré** (compte rendu de la session de navigation, 11 h 32, recoupé avec son journal).

- Le plus bas trouvé : 178 au repos (capteur de vide gauche, 11 h 26 min 54) ; en roulant, 271, 230, 233 pendant 0,15 s (11 h 25), et une lecture à 154 en quittant le point de repos. Le mode Safe n'est pas tombé une seule fois, ni en avance ni en pivot.
- La ligne sombre n'est pas continue : là où elle a été trouvée elle n'est sombre que sur 1 à 2 cm de long ; les trois autres capteurs, qui coupent le bord 5 à 14 cm plus loin, ne descendent pas sous 681. Rien sous 707 le long du bord est sur 75 cm.
- Les lectures de 36 à 81 de ce matin (capteur droit, 8 h 53 et 9 h 04, case D10) n'ont pas été retrouvées.

**Ce que cela dit.** La question du recul reste ouverte. La meilleure réponse est toujours celle de 9 h 04 : après une avance coupée par le robot (capteur droit à 59), un recul droit de 300 mm à 60 mm/s a passé, le capteur repassant à 100 pendant deux lectures. Ce qu'on apprend aujourd'hui : **le seuil du robot est entre 93 et 154** (chute de 9 h 59 après 287, 93, 37 ; pas de chute à 154).

**Autres faits utiles relevés par la session de navigation pendant l'essai.**

- Le bord du tapis ne se monte pas par petits pas : roues arrêtées contre le bord, elles patinent, le robot pivote de 30° et l'estime compte 11 cm de trop. Il se monte d'un trait, à 60 mm/s.
- La brosse latérale à 40 cale dans les franges (346 mA, indicateur de surintensité levé) et fait dévier de 8° ; brosse à l'arrêt, la même approche de face tient son cap à 2,6°. Le conseil « brosse en marche » de la note N § 5 ne vaut donc pas pour une approche lente de face dans les franges.
- Le bas du tapis n'a pas de franges : il se franchit en marche avant sans rien, cap tenu à 0,2°.

### 5.8 Le facteur du gyroscope : vérifié, il n'a pas changé (et une fausse alerte de ma part)

**Ce qui s'est passé.** Entre 11 h 50 et 12 h 00 j'ai envoyé à la session de navigation trois messages qui se contredisaient : « votre position est 30 cm trop au sud », tirée de mon estime enchaînée sur vingt minutes ; puis « je retire, c'est le facteur du gyroscope qui vaut 1,0013 aujourd'hui », tiré de quatre tours du matin ; puis « aucun des deux ne tient ». Le bilan, une fois ses mesures reçues : **la première alerte allait dans le bon sens** (dans le repère des faisceaux de la base, sa position retenue au retour était 53 cm trop au sud et 17 cm trop à l'est ; elle s'est recalée sur les faisceaux à 11 h 50, § 5.9) ; **c'est le facteur du gyroscope qui n'a pas changé**, et mon retrait qui était faux. Je note le tout pour que la leçon reste : un bon résultat annoncé sur une mesure fragile, puis retiré sur une autre mesure fragile, vaut moins qu'un silence de dix minutes.

**Mesuré** (`rv_facteur_gyro.py`, résultats dans `results_rv_facteur_gyro.txt` ; `rv_boucle.py` pour un couple de tours).

- Couples de tours faits au même endroit : 1,0040 ± 0,0018 le 10, 1,0039 ± 0,0004 le 13, 1,0040 ± 0,0002 le 14.
- Le 15, les quatre tours de D12 du matin donnaient 1,0013 ± 0,0007. À ma demande la session de navigation a fait trois tours de suite au même endroit à 12 h 02 (`exploration32_20261115_120142`) : 1,0039, 1,0072 et 1,0080, chacun à 0,002 à 0,004 près. Avec eux le jour donne 1,0025 ± 0,0010.
- Seconde mesure, indépendante : le recouvrement de la fin de chaque tour sur son début donne 1,0047 ± 0,0011 le 15 (18 tours).
- Le gyroscope seul, enchaîné du tour de 10 h 41 à celui de 11 h 52 (70 minutes, +2 510° de rotation nette, sept tours dans deux pièces), reste à moins de 2° de chacun des caps retenus par le filtre avec un facteur de 1,0040.

**Ce que cela dit.** Le facteur est le même que les autres jours, entre 1,0040 et 1,0045 ; rien n'est à changer. Une direction de paroi ne se lit qu'à 1,5° près : quelques couples de tours pris au même endroit peuvent tromper de 0,003. Et une estime enchaînée sur plusieurs tours est très sensible à ce facteur (12 cm par millième sur les vingt dernières minutes d'`exploration31`) : elle ne vaut que d'un tour au suivant.

**Ce que j'ai changé dans mes outils.** `rv_direct.py` ne lance plus d'alerte forte quand le trajet depuis le tour précédent passe sur un tapis ou un sol sombre : là, c'est l'estime qui est la moins sûre (sur l'avance de 1,30 m de 11 h 41, le capteur de distance n'a vu le mur se rapprocher que de 1,23 m). `rv_ou_est_le_robot.py` prend le facteur en option et dit combien de degrés un millième d'écart ferait sur le trajet demandé.

### 5.9 Devant la base, la position du nord au sud n'est pas sûre

**Mesuré.**

- **Le filtre remonte vers le nord à chaque tour refait au même endroit.** Aux trois tours de 12 h 02 : +48, +12 et +17 mm, alors que les tours comparés paroi par paroi sont au même point à 12 mm près. Le matin, à l'essai 1 : +154, +102 et +87 mm.
- **Le tour de 11:52:07 est au même point que celui de l'essai 1 (10:55:36)** à 2 ou 3 cm près : les huit parois lues sont les mêmes (518 et 544 mm au nord, 1 173 et 1 162 au sud, 1 062 et 1 059 à l'est). Et la traversée des faisceaux de 11 h 50 retrouve l'axe de la base à 7 mm près de celui de l'essai 1. D'est en ouest, la position devant la base est donc sûre au centimètre.
- **Du nord au sud, quatre façons de mesurer la distance du centre du robot à la base ne s'accordent pas**, robot à ce même point : 1,19 m du point de la base sur le plan d'après le filtre ; 1,31 m ± 0,13 du devant de la base d'après la photo de l'utilisateur de 11 h 01 (23 lames de parquet comptées entre la base et le dessous du robot, la lame étalonnée à 58 mm sur le diamètre du robot) ; 18 à 33 cm de plus que le filtre d'après la largeur des faisceaux (§ 5.2) ; 60 à 75 cm de plus d'après deux estimes revenues de la pièce du tapis (la mienne et celle de la session de navigation, qui s'est recalée ensuite sur les faisceaux).
- **Deux contacts du pare-chocs gauche** au retour de la pièce du tapis, à 11 h 46 min 42 et 11 h 47 min 58, robot allant vers l'est : rien n'avait été vu, ni par le capteur de distance (1,3 et 2,2 m devant) ni par les capteurs optiques (52 au plus). Explication de la session de navigation, après recalage sur les faisceaux : le robot passait 30 cm plus au nord qu'elle ne le croyait et a touché le bord sud du meuble de C14 à C16. Un troisième contact, à droite, à 11 h 34 min 51 dans la pièce du tapis : une chose basse devant le lit.
- **Le décalage entre les deux pièces, décompté par la session de navigation** : sa position retenue au retour était 53 cm trop au sud dans le repère des faisceaux ; 25 cm étaient déjà là le matin entre le repère de la pièce du tapis et celui de la pièce de la base, 10 viennent de la correction du filtre acceptée à 11 h 32, 17 de la tournée. À dix minutes d'écart le filtre a eu raison une fois contre l'estime (11 h 39, note 0,89, confirmé par le mur nord) et tort une fois (11 h 43, note 0,66).

**Ce que cela dit.** Rien de tranché. La photo ne contredit pas nettement le filtre (12 cm d'écart, ou 19 si le point de la base est à son milieu, pour 13 cm d'incertitude) ; la largeur des faisceaux dit 18 à 33 cm de plus ; les deux estimes disent bien davantage, mais elles ont traversé le tapis et je ne m'y fie pas. Ce qui est sûr : le filtre n'est pas stable à cet endroit (il remonte à chaque tour), et ce que le robot lit au nord depuis ce point, 52 à 54 cm, reste à identifier.

**Ce qui est demandé.** Une mesure au mètre par l'utilisateur, robot laissé où il est depuis 12 h 03 : du devant de la base au bord du robot le plus proche. Elle dira laquelle des quatre est la bonne.

**Complément de 12 h 45.** L'essentiel de ces désaccords vient du cap faux de 10° du § 5.11 : les deux estimes revenues de la pièce du tapis roulaient 10° de travers. Ce que le robot lit au nord depuis le point P est identifié sur la photo de l'utilisateur : un pied de meuble à 0,68 m ± 0,07 du centre du robot (531 mm lus), un gros pot au nord-est, un objet debout au nord-ouest. Le capteur de distance ne voit donc pas la base depuis P, et le filtre n'y a aucune vraie paroi au nord. La mesure au mètre reste utile pour la distance elle-même.

### 5.10 La place du capteur de distance et l'échelle du plan : deux erreurs possibles qui se compenseraient, mais pas l'explication des sauts entre pièces

À midi la session de navigation a retrouvé d'où vient l'échelle du plan, et j'ai d'abord écrit ici que « tout se rangeait ». **Le rejeu fait à 12 h 25 dit que non** (plus bas) : je laisse les faits, je corrige la conclusion. Rien n'est changé dans les outils.

**Les faits, mis côte à côte.**

1. **L'échelle du plan a été réglée le 10 novembre** (journal § 27) par trois chemins qui ne s'accordaient pas : 57 pixels par mètre par la carte du robot seule (ses tours sur place), 51 par le trajet seul (les roues), 50 à 57 par la largeur des portes. 54 puis 53 ont été retenus.
2. **Mon contrôle du jour sur 210 trajets** (§ 5.6, `rv_dx_par_les_tours.py`) : les corrections de position vont contre le trajet de 3,4 % de sa longueur. Cela fait 51,2 pixels par mètre : la valeur du trajet seul.
3. **Un capteur compté trop en arrière rétrécit chaque pièce vue par le robot** : pour la poser sur le plan il faut alors plus de pixels par mètre. Passer de 51 à 57 pour des murs à 0,8 m (la distance médiane des murs vus de face dans les tours) demande qu'il manque 10 cm à chaque lecture : selon que la carte du 10 comptait déjà les 27 mm ou pas encore, le capteur serait à 126 ou à 100 mm du centre, et non à 27.
4. **La photo du robot** le montre à 125 mm du centre, à 1 cm près ; **l'essai 4** à plus de 86 mm (§ 5.6).
5. **Toutes les corrections du filtre de la journée vont vers la paroi la mieux vue** (relevé de la session de navigation) : vers le nord dans la pièce de la base, sept fois (+154, +102, +87, +70, +49, +12, +17 mm) ; vers le sud dans la pièce du tapis, quatre fois. Les deux pièces se retrouvent décalées de 25 cm l'une par rapport à l'autre.
6. **Les largeurs mesurées par le robot** ajoutent deux fois la place du capteur : le couloir « de 68 cm » entre J15 et J17 ferait 88 cm, le passage « de 47 cm » près de la porte H12 ferait 67 cm.

**Ce que ces six faits suggèrent.** Deux erreurs de sens contraire, nées le même jour : le capteur de distance compté trop en arrière (chaque pièce paraît trop étroite au robot) et l'échelle du plan trop forte (le plan, converti en millimètres, est trop petit). Dans une pièce les deux se compensent, et c'est pourquoi 53 « marchait ».

**Le rejeu de 12 h 25, qui corrige ma première conclusion** (`rv_rejeu_reglages.py` : le filtre de la session de navigation relancé tel quel sur un enregistrement, avec plusieurs jeux de réglages). Sur le début de la grande boucle (`exploration33`, tour en P à 12:17:23, puis deux tours en D12 à 12:18:56 et 12:19:21, 2 m de parquet entre les deux, sans patinage) :

| Capteur, échelle | correction au premier tour de D12 | au second tour, même endroit |
|---|---|---|
| 27 mm, 53 pixels par mètre (les réglages actuels) | 333 mm vers le sud | 100 mm vers le sud |
| 125 mm, 51 | 341 mm | 94 mm |
| 125 mm, 53 | 343 mm | 107 mm |
| 27 mm, 51 | 326 mm | 98 mm |

**Changer ces deux réglages ne fait donc pas disparaître le décalage entre la pièce de la base et la pièce du tapis.** Ma phrase « ce sont les trois endroits où la position sautait » était fausse pour le troisième.

**Ce qu'on peut dire à la place.**

- **La taille d'une pièce ne sépare pas les deux réglages.** En D12 le robot lit 1 494 mm au nord et 1 522 mm au sud, entre deux traits sombres du plan distants de 162 pixels. Cela donne un capteur à 20 mm du centre avec 53 pixels par mètre, à 80 mm avec 51, à 125 mm avec 49,6. Toute une famille de couples convient : seule une mesure extérieure choisit (la règle sur le robot ; ou la largeur du couloir au mètre, demandée par la session de navigation, qui ne dépend pas du plan).
- **Le décalage entre pièces vient surtout de la position que le filtre donne devant la base** (§ 5.9) — écrit à 12 h 30, et dépassé un quart d'heure plus tard : c'était d'abord un cap faux de 10° (§ 5.11). Ce qui suit reste mesuré, mais dans un repère tourné. La station de D12 tient sur deux vrais murs ; l'estime ramenée de là met le point P 38 cm plus au sud que le filtre, la photo et la largeur des faisceaux 15 à 30 cm dans le même sens. Devant la base, ce que le robot lit au nord n'est pas ce que le filtre croit reconnaître sur le plan.
- **Les deux erreurs restent possibles**, chacune avec ses indices : pour le capteur, la photo et l'essai 4 ; pour l'échelle, les 51 du trajet seul et les 3,4 % des 210 trajets (5,9 % du nord au sud, 2,2 % d'est en ouest : le plan n'aurait pas la même échelle dans les deux sens).

**Ce qui n'est pas établi.** Ni la place du capteur, ni l'échelle. Le contact du 10 à 143 mm lus reste à comprendre. Je n'ai pas pu trancher par le plan seul (§ 5.6, point 4 ; `rv_dx_coherence.py`).

**Ajout de 12 h 40 : le couloir, la géométrie la plus propre de la journée.** À la station du milieu du couloir (`exploration33`, tour de 12:26:36, cap recalé sur les murs) les deux murs donnent deux paliers larges et francs : 319 mm lus au nord (palier de 50°) et 326 mm au sud (56°), 645 mm en tout. Sur le plan, les deux traits sombres sont à 840 mm l'un de l'autre (44,5 pixels). Donc 645 mm plus deux fois la place du capteur font 840 : **capteur à 97 mm du centre avec 53 pixels par mètre, 114 mm avec 51**, à 20 mm près (un pixel de chaque côté). Cela va avec la photo (125) et pas avec 27, qui demanderait un couloir de 70 cm. La mesure du couloir au mètre, demandée à l'utilisateur par la session de navigation, tranchera à elle seule : 70 cm, et le capteur est à 27 mm ; 84 à 89 cm, et il est entre 100 et 125. (La station suivante, en J20, donne autre chose, mais son palier du nord n'a que 18° de large : ce n'est sans doute pas le mur.) Même chose pour la porte K23, franchie à 12 h 34 : la session de navigation lit 646 mm entre les montants, chaque côté compté depuis le centre du robot avec 27 mm ; avec un capteur à 97, 110 ou 125 mm cette porte ferait 79, 81 ou 84 cm. Une porte se mesure aussi bien qu'un couloir.

**Ce qu'il faudra faire, à décider avec la session de navigation et l'utilisateur.** Attendre les mesures à la règle et au mètre. Ne changer aucun des deux réglages seul. Avant tout changement, rejouer les séances enregistrées avec `rv_rejeu_reglages.py` : c'est ce rejeu qui a évité ici de changer deux réglages pour rien. Et chercher ce que le robot voit au nord du point P.

### 5.11 L'explication des décalages entre pièces : un cap faux de 10° depuis 9 h 55 (trouvé par la session de navigation, confirmé et daté par le gyroscope)

**La trouvaille est celle de la session de navigation**, à 12 h 26, au milieu du couloir : en se centrant entre les deux murs elle mesure son cap à +6,6°, +7,3° et +7,4° de celui qu'elle tenait, en plus de 3,4° déjà repris au filtre. Son cap était donc trop petit de 10,8°. Elle m'a demandé de le vérifier sur les enregistrements.

**Mesuré** (`rv_cap_chaine.py 20261115 --depart 09:51:56`, résultats dans `results_rv_cap_chaine_20261115.txt`). Le gyroscope seul, facteur 1,0040, enchaîné de tour en tour à travers les séances 28 à 33 (le cerveau n'a pas redémarré depuis l'installation de 9 h 44), comparé au cap retenu à chaque tour :

| Tour | Cap retenu moins gyroscope, depuis le tour de 9:51:56 | Ce que disent les parois de ce tour |
|---|---|---|
| 9:51:56 (départ) | 0 | d'équerre (palier de 66° vu à 360°) |
| 9:55:40 | **−22,6°** | quatre parois larges décalées de +8, +17, +20, +26° |
| 10:00:57 | +73,0° (l'erreur de 97° déjà connue) | |
| 10:13:10, tour de contrôle | −17,5° | |
| 10:41:27, départ de l'essai 1 | −10,9° | mur du sud vu à 260° |
| 11:52:07, point P | −12,1° | mur de l'est vu à 352° |
| 12:17:23, départ de la boucle | **−10,8°** | mur du sud à 260°, mur de l'est à 353° |
| 12:26:36, après le recalage sur les murs du couloir | **+1,0°** | d'équerre (90° et 271°) |

- L'erreur naît au tour de **9 h 55 min 40**, juste après les patinages au bord du tapis : le cap y est repris au filtre, qui laisse 8° de flou. Le tour de contrôle de 10 h 13 ne la corrige qu'en partie. Ensuite le filtre remonte de 6,8° en deux heures, par corrections de 0 à 3°.
- Avant 9 h 55 les parois sont d'équerre à 2° près (8:53:01, 9:06 à 9:12, 9:27:27).
- Les deux bouts de la chaîne sont d'équerre aux murs (9:51:56 et 12:26:36) et la chaîne se referme à 1° après 9 100° de rotation nette : **le facteur du gyroscope vaut 1,0041 à 0,0002 près**. C'est sa mesure la plus fine à ce jour, et elle clôt le § 5.8.

**Ce que cela explique.**

- **Les décalages entre pièces** (§ 5.9, § 5.10) : en roulant 2 m vers l'ouest « au cap 180° » le robot allait en réalité au cap 190° et arrivait 35 cm plus au sud. C'est ce que le filtre corrigeait à chaque entrée dans la pièce du tapis (quatre fois vers le sud le matin, 254 puis 98 mm à 12 h 18), et dans l'autre sens à chaque retour devant la base (+154, +102, +87 mm), avec les deux contacts de 11 h 46 et 11 h 47. Mon rejeu de 12 h 25, où la correction ne dépendait ni de la place du capteur ni de l'échelle, le disait sans que je le lise : c'était une rotation.
- **L'axe de la base « incliné de 10,6° »** (§ 5.2) : il est d'équerre au mur ; c'est le repère de la séance qui était tourné. La question posée à l'utilisateur sur sa base est close.
- **Les positions notées entre 9 h 55 et 12 h 26** (essais 1 à 5, cartes du tapis) sont dans un repère tourné de 10 à 22° autour du point où le robot se trouvait. Les distances et les largeurs mesurées restent justes ; les positions sur le plan non.

**Ce qui reste à part**, non tranché : la place du capteur de distance (§ 5.6) et l'échelle du plan (§ 5.10). Ni l'une ni l'autre n'était la cause des sauts de position d'aujourd'hui.

**La règle que j'en tire, proposée à la session de navigation.** Le gyroscope est le témoin du cap : il a tenu 1° en deux heures et demie. Le filtre ne devrait pas pouvoir déplacer le cap de plus de 1° plus un millième de la rotation nette faite depuis le dernier tour où les parois étaient d'équerre, sauf si les parois du tour le confirment. Le tour de 9 h 55 min 40 aurait été refusé. `rv_cap_chaine.py` signale ces tours : il y en a quatre le 13 (de 5 à 15°) et un le 14, à regarder.

**Ce que je n'ai pas vu.** Mon outil de suivi comparait le cap du gyroscope et celui des roues, pas le cap retenu et le gyroscope enchaîné : il n'a rien dit à 9 h 55. C'est à ajouter.
