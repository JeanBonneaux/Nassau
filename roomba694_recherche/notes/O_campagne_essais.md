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
8. **Le résultat de la grande boucle (§ 5.14) : 45 m, six pièces, 79 minutes, et le robot revient à 27 mm de son point de départ ; la position tenue par la session de navigation s'y retrouve à 2 à 5 cm, l'estime seule à 60 ou 70 cm.** Avec un cap juste, la méthode tient donc 5 cm. L'échelle du plan serait fausse de 2,5 %. (J'écrivais ici que le gyroscope perd 5° quand le robot se bat sur une marche : le § 5.15 montre que ce n'est pas établi.)
9. **La séance de l'après-midi, dépouillée une fois close (§ 5.15) : le robot est revenu à 18 mm de son départ, mais trois positions tenues en route étaient fausses de 25 à 65 cm, chaque fois avec une bonne note du filtre.** À l'entrée de la cuisine deux endroits distants de 65 cm notaient 1,00 ; celui qui a été gardé (0,93) était le mauvais. C'est l'origine du « mètre d'écart » de la cuisine : l'estime y était décalée vers l'est depuis le seuil, le plan n'y est pour rien.
10. **Le facteur du gyroscope n'est pas la constante que je croyais (§ 5.15.2).** Les fermetures du 15 donnent 1,0044 à 1,0056, celles du 14 donnaient 1,0035 à 1,0046. Une sortie cumule 9 000 à 11 500° de rotation nette, parce que chaque tour sur place en ajoute 380, toujours vers la gauche : 0,0005 d'erreur sur le facteur y font 5°. D'où il vient : la carte du gyroscope est penchée de 5,5° et le firmware ne lit qu'un axe ; 1/cos(5,5°) = 1,0046. Il change donc quand la carte est reposée sur le robot.
11. **Trois repères de la carte à reprendre** (§ 5.15.3 et 5.15.4) : la baguette du seuil de la cuisine est dans la ligne du mur (u = 750 environ, et non 775) ; l'entrée de la cuisine, juste après le seuil, est en C29 ; le milieu de la nouvelle porte H18 est 8 à 25 cm plus à l'ouest que la session de navigation ne le lit sur le plan, selon celui des deux repères de cap de l'après-midi qui était le bon ; dans les deux cas cela rend compte des 28 cm d'erreur à l'arrivée.
12. **Trois changements proposés, aucun fait** (§ 5.15.7) : compter la rotation autour de la verticale mesurée et non d'un seul axe (firmware) ; alterner le sens des tours sur place (firmware) ; ne plus accepter un calage sur sa seule note, et se servir de la baguette du seuil comme d'un repère.
13. **La décision de l'utilisateur, le 15 au soir** (§ 5.15.8) : l'essai 11 est accepté pour la prochaine séance de pilotage, et il demande que la liste de la session de navigation porte tout ce qui est proposé ici, avec son idée du capteur de distance tourné à 90° en roulant (journal § 61.9, note P § 6). Transmis à la session de navigation ; rien n'est installé ni changé.

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
| 11 | Pendant un tour sur place devant la base, la touche g du cerveau envoyée une dizaine de fois, une par seconde, et une fois à l'arrêt avant et après (elle affiche les trois axes du gyroscope et n'arrête pas le tour) | Les axes X et Y lisent-ils -9 % et -4 % de ce que lit Z (-2,5 et -1 °/s pour 28) ? | confirmer que le facteur du gyroscope est l'inclinaison de la carte (§ 5.15.2) ; décider du changement de firmware | **accepté par l'utilisateur le 15 au soir (« Yes add it »)** ; demandé à la session de navigation pour sa prochaine séance de pilotage (§ 5.15.8) |
| 12 | Deux tours sur place au point P, l'un au départ, l'autre au retour de chaque sortie ; `rv_cap_profil.py` | De combien le cap du gyroscope s'est-il écarté pendant la sortie ? | le facteur du jour à 0,0002 près, sans rien ajouter au parcours | se fait déjà ; à dépouiller à chaque séance |

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

### 5.12 Une quatrième chute du mode Safe, en pivot, capteur de vide gauche (12 h 41 min 37)

Pendant le retour de la grande boucle, dans la pièce du bas à droite (`exploration34_20261115_123906`, mouvement 431, rotation de +68,7° à 100 mm/s arrêtée à 26°).

**Mesuré** (lectures toutes les 47 ms).

- Capteur de vide gauche : 2 664, 2 647, 2 658, 2 530, **175**, 430, 1 488, 2 402, 392, **10**, 137, puis 2 451 à 2 508 robot arrêté. Les trois autres capteurs de vide restent entre 2 557 et 2 674.
- Le mode tombe à la lecture qui suit le 10, un quart de seconde après le 175. Le cerveau coupe les roues aussitôt.
- En même temps le capteur optique gauche du pare-chocs monte de 50 à 295 et l'avant gauche de 13 à 124 (225 et 122 à l'arrêt). Pare-chocs jamais enfoncé, roues jamais levées.

**Ce que cela dit.** Le coin avant gauche du robot est tout près d'un objet, et le capteur de vide gauche est passé pendant la rotation sur une chose sombre et étroite au sol à côté de lui (pied, socle, câble) : pas un vide continu, puisque le sol est lu normalement sous les quatre capteurs une fois le robot arrêté. C'est la première chute observée en pivot avec le capteur gauche ; elle va avec le seuil du § 5.7 (entre 93 et 154) : une seule lecture à 10 a suffi. Les capteurs optiques avaient vu l'objet venir pendant un quart de seconde avant la chute : un arrêt du cerveau sur ces capteurs (§ 5.5) l'aurait évitée.

**Complément de la session de navigation (12 h 45).** Le robot est en M23, contre le pied du meuble de l'ouest de cette pièce ; le noir vu par le capteur est sous ce meuble (plinthe sombre, vide ou grille). Pendant l'avance qui précédait, le même capteur était déjà passé à 381 puis 163 sans que le mode tombe : 163 en avance et 175 en rotation ne suffisent pas, 10 suffit à la lecture même. Cause du geste : le centrage, lancé dans un espace ouvert d'un côté (644 mm à gauche, rien à droite), s'est cru décentré et a avancé vers le meuble ; il fallait refaire à l'envers le trait de l'aller. Une minute plus tôt (12 h 40 min 11), contact du pare-chocs gauche à la fin d'une avance face au mur du fond : un meuble bas devant le mur, que le capteur de distance ne voyait pas (338 mm lus au contact, capteurs optiques 80 au plus). Elle ne remet pas le robot en mode Safe sans le mot de l'utilisateur.

### 5.13 Le seuil de la cuisine (12 h 56 à 13 h 03), et une réserve sur le gyroscope

**Le franchissement.** Mesuré dans `exploration34`, mouvements 469 à 486, menés par la session de navigation ; seuil de 17 mm entre la pièce centrale et la cuisine, pris vers la cuisine.

- À 100 mm/s en marche avant : l'avant passe, puis les deux roues patinent ensemble (605 mm comptés, 390 mm faits d'après le capteur de distance ; 350 à 640 mA par roue).
- Trois reprises à 100 mm/s après un pivot : à chaque fois la roue droite tourne sur place (62, 73 puis 91 mm de trop, jusqu'à 824 mA) et le robot pivote de 12 à 15° autour d'elle. Répéter le geste ne change rien.
- À reculons, 100 mm/s : le second recul de 300 mm ne déplace pas le robot (capteur de distance à 2 626 puis 2 629 mm).
- **D'un trait à 150 mm/s, avec 85 cm d'élan, en marche avant : le seuil passe**, sans contact ni roue levée (courants de 450 mA au passage, puis normaux).
- Aucune chute du mode Safe sur le seuil lui-même : les capteurs de vide y lisent plus fort que le sol (jusqu'à 3 375), pas plus sombre.

**Le cap après le seuil : gyroscope et cap retenu ne s'accordent plus, de 4,8°.** L'écart se crée pendant les essais sur le seuil (entre les tours de 12:52:03 et 13:00:31) et reste le même ensuite. Deux lectures :

- le suivi du cap de la navigation perd 1,4 à 1,7° à chacune des trois avances arrêtées (le robot finit de tourner après le message de fin du mouvement) : c'est ce que j'ai d'abord écrit ;
- ou le gyroscope a mal compté sur le seuil : il est monté penché et le cerveau n'en lit qu'un axe, et un robot qui se cabre sur une marche fait passer une part de ce mouvement dans le cap.

Les parois de la cuisine penchent pour la seconde : dans le repère de la navigation, les deux paliers les plus larges tombent à 86° (48° de large) et à 92° (58° de large), 89° en moyenne pour 90° attendus ; avec le gyroscope ils seraient attendus vers 95°. Mais une direction de paroi ne se lit qu'à 3° près, et le gyroscope a traversé sans dommage une douzaine de montées de tapis ce matin. **Non tranché** : les deux murs du couloir, au retour, le diront à 1° près.

*(Le § 5.15.2 revient sur cette section : la seconde lecture, « le gyroscope a mal compté sur le seuil », n'est pas établie non plus ; l'écart s'explique par le facteur.)*

**Ce que cela change au § 5.11.** La règle « le gyroscope est le témoin du cap » vaut sur sol plat. Après un seuil ou un bord pris en force, le cap se reprend sur des parois franches avant de continuer.

### 5.14 La grande boucle (12 h 17 à 13 h 36) : le résultat

**Le parcours**, mené par la session de navigation, enregistré en trois morceaux (`exploration33`, `34`, `35`) : point P devant la base → pièce du tapis → porte H12 → couloir → porte K23 → pièce du bas à droite (jamais vue) → retour → pièce centrale → seuil → cuisine jusqu'au coin C38 → retour par le seuil, le couloir et H12 → P. 79 minutes, environ 45 m de parcours (54,8 m comptés par les roues, manœuvres et patinages compris), 31 tours sur place, 104 tours de rotation cumulée. Dépouillement : `rv_boucle.py`, `rv_boucle_trajets.py`, `rv_cap_chaine.py` ; résultats dans `results_rv_boucle_exploration33_1217_1336.txt`, `results_rv_boucle_trajets_exploration33_exploration34_exploration35.txt` et `results_rv_cap_chaine_20261115.txt`.

**Mesuré.**

- **Le retour au point de départ.** Les deux tours faits en P (12:17:23 et 13:36:10), comparés paroi par paroi (6 parois communes, 9 mm de reste) : le robot est revenu à **27 mm** de son point de départ. Cette mesure ne dépend ni du plan ni de la place du capteur de distance.
- **Ce que chacun croyait de ce même retour.**

| Façon de se situer | Erreur à l'arrivée |
|---|---|
| positions tenues par la session de navigation (filtre aux stations, passages au capteur, cap pris sur les murs) | **18 mm** ; 50 mm avant la correction du dernier tour |
| estime seule, roues et gyroscope, patinage retiré | 58 à 74 cm, soit 1,1 à 1,3 % du chemin |
| compteur du cerveau tel quel | 4,2 m |

- **L'axe de la base à l'arrivée** : la session de navigation le retrouve à u = 404,5 dans son repère, pour 405 sur le plan.
- **Le cap.** *(Lecture corrigée au § 5.15.2 : ces 4,7° sont comptés avec un facteur de 1,0041 ; avec le facteur que donnent les fermetures du jour, 1,0047 à 1,0050, il ne manque plus rien, et la marche n'est pas en cause.)* Entre les deux passages dans le couloir (12:26:36 et 13:27:52), où le cap est aligné sur les deux murs à 1,5° près, le gyroscope enchaîné a perdu 4,7°. Tout se perd pendant les essais manqués sur le seuil de la cuisine (+4,4° entre les tours de 12:52 et 13:00) ; rien au retour, où le seuil passe sans forcer. **Le § 5.13 est tranché : c'est le gyroscope qui compte mal quand le robot se bat sur une marche.** (La comparaison des deux tours de P donne 5,1° ± 1,6, mais le centre d'un palier bouge de plusieurs degrés quand un objet de la pièce a changé : je ne m'en sers pas pour le cap.)
- **L'échelle du plan.** Sur les 12 trajets propres de la boucle (aucun patinage, roues qui ne forcent pas, note du filtre de 0,7 ou plus aux deux bouts), la correction va contre le trajet : −2,4 % (± 1,1) d'est en ouest sur 14 m, −2,8 % (± 1,0) du nord au sud sur 6 m. Les 210 trajets des 10, 13 et 14 donnaient −3,4 % (± 0,7). Deux jeux de données, le même sens : le plan vaudrait 51,5 à 51,8 pixels par mètre et non 53.
- **Les incidents** : une chute du mode Safe (§ 5.12) ; le seuil (§ 5.13) ; cinq contacts légers, tous contre des choses basses ou minces que ni le capteur de distance ni les capteurs optiques n'ont vues (un meuble bas, une poubelle, un objet apparu dans la pièce centrale entre l'aller et le retour).
- **Les endroits où le filtre se perd** : le milieu du couloir (notes −0,36 à l'aller, −0,24 au retour, 30 cm d'erreur : deux murs parallèles ne disent rien de la position le long du couloir), l'entrée de la cuisine (−0,09), l'entrée de la pièce du bas à droite (0,34 et 0,44). La session de navigation y a gardé l'estime, à raison.

**Ce que cela dit.**

1. **Avec un cap juste, la méthode tient 5 cm sur 45 m et six pièces.** C'est la réponse à « augmentons nos capacités de localisation précise » : le filtre aux stations où sa note est bonne, l'estime là où elle est mauvaise, les passages étroits au capteur de distance, le cap repris sur des murs francs.
2. **C'est le cap qui commande tout.** Dix degrés d'erreur faisaient 35 cm tous les 2 m (§ 5.11) ; le même robot, cap corrigé, ferme la boucle à 5 cm.
3. **L'estime seule vaut 1 % du chemin** : bonne d'une station à la suivante, pas sur une boucle.
4. ~~Le gyroscope tient 1° sur des heures de sol plat et perd 5° en une minute de lutte sur une marche.~~ **Retiré le 15 au soir (§ 5.15.2)** : le cap du gyroscope dépend d'un facteur connu à 0,0005 près seulement, et une sortie cumule tant de rotation que cela fait 5 à 10°. La règle pratique reste la même : après une longue sortie, le cap se reprend sur des murs francs ou sur la base.
5. **L'échelle du plan est sans doute fausse de 2,5 %** : à confirmer au mètre, puis à corriger avec la place du capteur, après rejeu (§ 5.10).

**Ce qui reste.** Les mesures à la règle et au mètre de l'utilisateur (essais 8 et 9, largeur du couloir ou d'une porte) ; les essais 6 et 7 ; trois idées pour le firmware, à décider avec lui : un arrêt sur le capteur optique centre gauche (§ 5.5), un arrêt quand les roues tournent sans que le capteur de distance bouge (seuil, § 5.13), les quatre indicateurs « vide » du robot dans le journal.

### 5.15 La séance de l'après-midi (13 h 49 à 15 h 53), dépouillée une fois close

**Le cadre.** L'utilisateur a écrit à 13 h 20 : « Stop what you are doing and only wake up later to process the robot outputs ». Je n'ai donc rien suivi en direct ; la session de navigation a mené seule la séance (journal § 61 : la cuisine par la nouvelle porte H18, le coin du fond, le retour) et m'a écrit à la fin. Ce qui suit est tiré des enregistrements `exploration36`, `38`, `39` et `40`, une fois clos. Rien n'a été envoyé au robot. Outils nouveaux : `rv_cap_profil.py`, `rv_gyro_controles.py`, `rv_calage_large.py`, `rv_contacts.py` ; résultats dans les fichiers `results_` du même nom, et `results_rv_boucle_exploration36_1349_1553.txt`.

#### 5.15.1 Le retour au point de départ

Les deux tours faits au point P (13:49:59 et 15:53:00), comparés paroi par paroi (6 parois communes, 10 mm de reste) : après 123 minutes, 44 m et 69 tours de rotation cumulée, **le robot est à 18 mm de son point de départ**. Il y est parce que l'utilisateur a demandé à 15 h 47 de vérifier sur les faisceaux de la base : au tour d'avant (15:47:50), la même comparaison (4 parois seulement) le place 31 cm à l'ouest de P, et la traversée des faisceaux par la session de navigation disait 28 cm. Deux mesures qui ne se doivent rien, le même écart.

| Façon de se situer | Erreur à l'arrivée |
|---|---|
| positions tenues par la session de navigation, avant le calage sur les faisceaux | 28 à 31 cm |
| les mêmes, après ce calage | 8 cm (repère) ; le robot lui-même à 18 mm de son départ |
| estime seule, roues et gyroscope × 1,0045, patinage retiré | 1,6 m, soit 3,5 % du chemin |
| estime seule, cap refermé à la main | 39 cm, soit 0,9 % |
| compteur du cerveau tel quel | 5,5 m |

L'estime seule est trois fois moins bonne qu'à midi (1,1 à 1,3 %) : c'est le cap, voir ci-dessous.

#### 5.15.2 Le cap : le facteur du gyroscope n'est pas la constante que je croyais

**Une mesure nouvelle du cap, sans le plan.** Deux tours faits au même endroit donnent le même profil de distances, décalé de la différence de cap. `rv_cap_profil.py` fait glisser l'un sur l'autre. Sur douze couples de tours enchaînés sans bouger (vraie valeur : zéro) il rend de −1,2° à +1,9° : la mesure vaut ± 1°. Elle ne marche qu'à quelques centimètres près ; à 10 cm d'écart, ou si un objet a bougé, le recalage est flou et le script le dit.

**Ce qu'elle donne** (vraie rotation moins rotation comptée par le gyroscope × 1,0041) :

| De | À | Rotation nette | Il manque au gyroscope | Facteur qui fermerait |
|---|---|---|---|---|
| 14/11, 15:51:24 | 15:57:23 (cuisine, sans le seuil) | 4 309° | −1,4° | 1,0038 |
| 14/11, 15:54:49 | 15:58:36 | 3 148° | −1,8° | 1,0035 |
| 15/11, 10:55:36 | 12:17:23 (point P) | 3 755° | +3,0° | 1,0049 |
| 15/11, 12:17:23 | 13:36:10 (la grande boucle) | 11 514° | +10,6° (recalage flou) | 1,0050 |
| 15/11, 13:49:59 | 15:53:00 (l'après-midi) | 8 982° | **+12,6°** | 1,0055 |

Pour l'après-midi, deux autres mesures indépendantes donnent le même manque : 11° par le cap où les récepteurs infrarouges de devant voient la base pendant le tour, 16° par les directions des parois (à 3° près). Entre les deux tours de D28 qui encadrent la cuisine (14:15:09 et 15:38), il manque 10° (± 2) sur 4 800°.

**Ce que j'avais écrit, et qui tombe.** Aux § 5.13 et 5.14 : « le gyroscope perd 5° quand le robot se bat sur une marche ». Ces 5° étaient comptés avec 1,0041. Avec 1,0047 à 1,0050, la grande boucle de midi se referme sans rien demander à la marche. Et au § 5.8 : « le facteur n'a pas changé, 1,0040 à 0,0002 près ». Les couples du 15 de plus de 1 000° donnent 1,0044 à 1,0056, ceux du 14 donnaient 1,0035 à 1,0046 : il n'est connu qu'à 0,0005 près, et il n'est pas le même d'un jour à l'autre.

**Pourquoi si peu compte autant.** Une sortie cumule 9 000 à 11 500° de rotation nette, 25 à 32 tours complets, parce que chaque tour sur place en ajoute 380 et que le firmware les fait toujours vers la gauche. Un demi-millième d'erreur sur le facteur y fait 5°, un millième 10°. Et 5° de cap font 16 cm de travers sur les 1,9 m qui séparent la porte H18 du point P.

**D'où vient ce facteur.** La carte du gyroscope n'est pas à plat. Son accéléromètre lit, robot à l'arrêt, (−0,10 ; −0,04 ; +1,09) g : la verticale est à 5,5° de l'axe que le firmware prend pour vertical. Or le firmware ne compte que cet axe (`imu.gyr[vertAxis]`) : il lit donc la rotation multipliée par cos(5,5°), et il faut la remultiplier par 1/cos(5,5°) = 1,0046. C'est le facteur. Pendant les rotations, l'accéléromètre donne 5,2° le 14 (1,0041) et 5,5° le 15 (1,0046) : le même sens que les fermetures (1,0040 puis 1,0050). La carte est ôtée et reposée d'un jour à l'autre ; un tiers de degré d'assise en plus, et le facteur bouge de 0,0005. **Non prouvé** : l'accéléromètre n'est pas étalonné (son axe vertical lit 1,09 g pour 1), l'inclinaison vraie peut différer de 1°. L'essai 11 le trancherait en une minute : pendant un tour sur place, la touche g du cerveau doit afficher environ −2,5 °/s sur l'axe X et −1 °/s sur l'axe Y pendant que Z en lit 28.

**Ce que j'ai écarté** (`rv_gyro_controles.py`, journée du 15) :

- un cap qui glisse à l'arrêt : 0,1° en 225 minutes d'arrêt ; vitesse lue juste après chaque arrêt 0,000 °/s (écart-type 0,06) ;
- un zéro du gyroscope faussé par un arrêt brutal : il ne saute jamais de plus de 0,015 °/s, y compris pendant les luttes sur le seuil ;
- un facteur qui change dans la journée, ou d'un sens à l'autre : sur 642 pivots sur place, le rapport entre les roues et le gyroscope reste le même à 0,05 % près du matin au soir, vers la gauche comme vers la droite ;
- un gyroscope qui dérive en ligne droite : il s'écarte des roues de 1,1° par mètre en marche avant et de −0,9° par mètre en marche arrière, toute la journée. Le signe change avec le sens de marche : ce sont les roues (une différence de 0,45 % entre les deux), pas le gyroscope ;
- une carte qui aurait tourné sur le robot : au point P, au même cap, l'accéléromètre lit la même direction à 13 h 40 et à 15 h 52, à 2° près.

**Ce qui reste sans explication.** L'après-midi demande 1,0055, un peu plus que le reste du jour : 4 à 6° de trop, logés entre les deux tours de D28, c'est-à-dire pendant l'aller et retour dans la cuisine avec ses cinq essais sur le seuil. Je ne sais pas si c'est le seuil. Je ne l'affirme plus.

**Le repère de la session de navigation a tourné de 5° entre 13 h 49 et 15 h 53.** Entre les deux tours de P, le vrai changement de cap de départ est de −5,8° (± 1) ; le cap retenu dit −11,0°. Trois témoins : le recalage des profils (5,2°), la base vue par les récepteurs infrarouges (3,9°), et la porte H18, que l'estime ne retrouve au même endroit à l'aller et au retour que si l'on retire ces 5° (§ 5.15.4). **Lequel des deux repères était droit sur le plan, je ne le sais pas** : les parois vues de P disent le second (mais ce sont surtout des objets), la base vue par les récepteurs infrarouges et la chaîne depuis le couloir de 12 h 26 disent le premier. À 5° près, le cap au point P n'a pas de témoin sûr aujourd'hui.

#### 5.15.3 La cuisine : l'estime était décalée de 65 cm vers l'est dès le seuil

Le journal § 61.7 note : « mon estime plaçait le robot deux cases trop à l'est au fond de la cuisine, alors qu'elle était juste à l'entrée ; je n'ai pas trouvé pourquoi ; c'est peut-être le plan qui est resserré ». Les enregistrements disent autre chose : **l'estime n'était pas juste à l'entrée**. Cinq témoins, indépendants deux à deux :

1. **La baguette du seuil.** Au premier essai (14:20:06), les capteurs de vide de devant la passent après 609 à 636 mm, celui de gauche après 666 mm, la roue gauche après 727 mm : la baguette est à 72 cm (± 2) à l'est du point de départ. Sur le plan, le mur qui porte cette porte est à u = 747 à 755. Le robot est donc parti de u = 713 environ, et non de 737 : l'estime avait déjà 46 cm d'avance vers l'est.
2. **Le tour de l'entrée (14:57:59).** `rv_calage_large.py` cherche à ± 1,2 m : deux endroits notent 1,00, celui que le filtre a confirmé (C30, noté 0,93 ce jour-là) et un autre, 65 cm plus à l'ouest et 15 cm plus au nord (C29). Le second est à 13 cm passé le mur, là où se trouve un robot qui vient de franchir une baguette et d'avancer de 15 cm ; le premier est à 80 cm passé le mur.
3. **Le tour de midi au même endroit (13:03:33)**, noté −0,09 à la position retenue : sa meilleure place (1,00) est la même, à 8 cm près.
4. **Les trois tours de la cuisine** (15:04:43, 15:13:41, 15:17:09), notés 0,42 à 0,45 : ils retrouvent le plan (0,90 à 0,98) à 45 à 75 cm à l'ouest et 10 à 18 cm au nord de l'estime. Le plan n'est donc pas faux à cet endroit ; c'est la position d'où on le regardait.
5. **L'utilisateur** : « ça correspond à C39 » quand l'estime disait D41, une case qui est de l'autre côté du mur de la cuisine.

**D'où vient l'écart.** Au tour de D28 (14:15:09), noté 0,86, la meilleure place sur le plan est déjà 30 cm plus à l'ouest (0,96) ; le tour du retour au même endroit (15:38:46) retrouve la même place d'est en ouest, à 1 cm près. Puis la position a été posée à la main après les patinages du seuil, à u = 790, sur une baguette crue à 775. Le filtre a confirmé cet endroit parce qu'il notait bien ; il ne cherche pas à 65 cm de l'estime.

**Trois repères à reprendre**, dans le repère du plan : la baguette du seuil de la cuisine dans la ligne du mur, vers u = 751 (± 4) ; l'entrée de la cuisine juste après le seuil vers (758 ; 68), case C29 ; le point de D28 vers u = 700.

**Un repère gratuit.** Cette baguette se lit sans doute possible : les capteurs de vide y passent de 2 650 (parquet) à plus de 3 200, puis à 2 500 (sol de la cuisine). À l'instant où les deux capteurs de devant la lisent, le centre du robot est à 15 cm d'elle. C'est un calage d'est en ouest à 3 cm près, à chaque passage, que ni le plan ni le filtre ne peuvent fausser.

**Sous les meubles de la cuisine, le capteur de distance et le pare-chocs ne voient pas la même chose.** À 15:02:00, le capteur lit 52 mm vers le côté nord du passage et les six capteurs optiques du pare-chocs ne lisent rien (0 à 29) : le capteur voit une façade, le pare-chocs est devant le vide d'une plinthe en retrait. La largeur lue du passage (54 cm au plus serré) est celle des façades ; au ras du sol il y a plus de place.

#### 5.15.4 La porte H18, et les 28 cm de l'arrivée

L'encadrement a été lu de l'intérieur à l'aller (14:04:50 : 89 mm à l'est, 498 à l'ouest ; 14:05:09 : 261 et 344) et au retour (15:45:42 : 232 et 347). L'estime, accrochée au point P à chaque bout, place le milieu de l'ouverture :

| | milieu de l'ouverture |
|---|---|
| à l'aller, avec le cap retenu à 13:49:59 | u = 451,9 |
| à l'aller, ce cap diminué de 5,2° (§ 5.15.2) | u = 443,3 |
| au retour, en remontant depuis le tour de 15:53:00 | u = 442,6 |
| sur le plan, tel que la session de navigation le lit | u = 456 |

Dans un même repère, l'aller et le retour s'accordent à 1,3 cm : c'est le troisième témoin des 5°. Et les 28 cm de l'arrivée s'expliquent, de l'une ou l'autre façon : si le repère du soir est le bon, la porte est 25 cm plus à l'ouest que sur le plan, et s'y être recalé à 15 h 46 a décalé d'autant ; si c'est celui du début, la porte est à 8 cm de sa place et c'est le cap, faux de 5°, qui a fait 16 cm de travers sur les 1,9 m du dernier trajet, soit 24 cm en tout. Dans les deux cas, la base a eu raison.

#### 5.15.5 Une bonne note ne dit pas que la position est la seule

`rv_calage_large.py`, sur les 45 tours de midi et de l'après-midi, cherche à ± 1,2 m d'est en ouest, ± 45 cm du nord au sud et ± 5° : **pour 40 tours sur 45, un autre endroit, à plus de 15 cm, note aussi bien ou mieux que la position retenue ; 2 seulement ont une place seule en tête.** Deux cas où la vérité est connue par ailleurs :

- le tour du couloir de 15:41:43, accepté sur sa note de 0,84 et faux de 30 cm (journal § 61.8) : quatre endroits notent 0,97 à 1,00, étalés sur 1,45 m le long du couloir ;
- le dernier tour de P (15:53:00), robot sur l'axe de la base à 1 cm près : le meilleur endroit trouvé est à 1,2 m de là (0,84), et il est faux.

Donc la note ne permet seule ni d'accepter une position, ni d'en proposer une autre. Elle classe des candidats ; il faut un second témoin. Ceux qui existent déjà : les faisceaux de la base (1 cm), la baguette du seuil (3 cm), un mur lu de côté, l'estime sur un trajet court sans patinage.

#### 5.15.6 La place du capteur de distance : trois lectures de plus

- **Dans la porte H18, le capteur lit 49 mm, puis 50 et 56 mm, sans que le pare-chocs touche** (13:57:02, 14:02:35, 14:02:56 ; aucun appui pendant le pivot qui y mène). Un objet lu à 49 mm doit être hors du pare-chocs, donc à plus de 164 mm du centre : le capteur serait à **plus de 11,5 cm** du centre. Cela vaut si la chose lue descend jusqu'au sol ; les capteurs optiques du pare-chocs en voient bien une tout contre lui au même instant (443 et 765 à gauche et à l'avant gauche).
- **L'encadrement de H18** : 587, 605 et 579 mm lus d'un montant à l'autre, plus deux fois la place du capteur.
- **Le couloir** : 730 et 758 mm lus, plus deux fois la place du capteur.

Avec 12,5 cm (la photo), la porte ferait 83 à 86 cm et le couloir 98 à 101 cm ; le plan, à 53 pixels par mètre, les donne à 79 et 92 cm, et il faudrait le lire à 50 pixels par mètre pour les retrouver. Avec 10 cm, 78 à 81 cm et 93 à 96 cm, et le plan irait tel quel. Les deux réglages restent liés (§ 5.10) et **seule la règle les sépare** : la largeur de cette porte au mètre suffirait.

#### 5.15.7 Les contacts, et ce qui est proposé

**Dix contacts du pare-chocs** (`rv_contacts.py`), huit à gauche. Pour quatre d'entre eux le capteur optique gauche avait dépassé 200 dans la seconde d'avant (232 à 424, pour 13 au repos) ; les six autres n'ont été vus par rien, ni par le capteur de distance (0,3 à 1,7 m lus au contact), ni par les capteurs optiques : pieds de meubles, montants. Un arrêt sur le capteur optique gauche en aurait évité quatre au plus, et il se déclencherait aussi chaque fois que le robot longe une paroi de près, comme dans la porte H18 : à réserver à un ralentissement.

**Proposé, rien n'est fait.** Les trois premiers touchent le firmware, donc l'accord de l'utilisateur pour une v15 ; les deux derniers touchent les outils de la session de navigation, qui en décide.

1. **Compter la rotation autour de la verticale mesurée**, et non d'un seul axe : le produit des trois axes du gyroscope par la direction de la pesanteur relevée à l'arrêt. Le facteur vaudrait alors 1 quelle que soit l'assise de la carte, et il n'y aurait plus de facteur à régler. À ne faire qu'après l'essai 11.
2. **Alterner le sens des tours sur place**, un vers la gauche, un vers la droite. La rotation nette d'une sortie tomberait de 9 000° à presque rien, et une erreur sur le facteur n'aurait plus de prise sur le cap. C'est le changement le plus simple et celui qui rapporte le plus.
3. **Journal** : les trois axes du gyroscope, pour voir ce qu'il fait quand une roue patine sur le seuil.
4. **Ne plus accepter un calage sur sa seule note** : exiger un second témoin dans un couloir, à l'entrée de la cuisine et après un patinage ; se servir de la baguette du seuil comme d'un repère.
5. **Mesurer le facteur du jour** avec les deux tours de P du départ et du retour (essai 12), et s'en servir au lieu de 1,0045.

**Mes erreurs dans ce dépouillement, corrigées avant d'écrire.** J'ai d'abord cru le facteur du gyroscope établi et cherché une cause à 12° « perdus » : cinq pistes écartées avant de voir que le facteur lui-même n'était pas sûr. J'ai pris pour des « tours lents » des tours ordinaires mal découpés par mon propre script. J'ai nommé des cases avec une largeur de plan fausse (600 pixels pour 1 214) : elles sortaient toutes en colonne 23 ; `rv_calage_large.py` lit maintenant la taille du plan. Et le premier outil d'ambiguïté que j'avais écrit classait presque tout « hors de la tache » : retiré, remplacé par la liste des meilleurs endroits.

**Ce qui n'est pas fait** : les mesures à la règle et au mètre (essais 8 et 9) ; les essais 6, 7 et 11 ; le sud de la cuisine ; savoir lequel des deux repères de cap était le bon au point P.

#### 5.15.8 La décision de l'utilisateur, le 15 au soir

À ma question « Add a one-minute gyroscope check (robot turning in place at its base) to the next driving session? », il répond : **« Yes add it and text that session to add anything you said plus the thing for the radar I suggested to it »**.

**Ce que j'en ai fait** : un message à la session de navigation, et le détail dans la note de passage entre les sessions. L'essai 11 est demandé pour sa prochaine séance de pilotage. Les propositions du § 5.15.7 et les repères du § 5.15.3 vont sur sa liste, avec l'idée de l'utilisateur du 15 à 15 h 50 : le capteur de distance tourné à 90° en roulant (journal § 61.9 ; note P § 6, point 4). **Ma lecture de ses mots** : c'est une liste de travail. Ce n'est pas l'accord pour installer un firmware ni pour toucher au montage, qui se demande au moment de le faire.

**L'essai 11, vérifié dans le code avant de le demander.** La touche g ne fait qu'afficher et n'arrête pas un tour sur place : seules les touches d'arrêt, de roues, de mode et de remise à zéro du gyroscope le font. Ce qu'elle affiche est corrigé du zéro sur les trois axes, remesuré pendant la seconde de préparation de chaque tour. Aucune lecture de ce genre n'existe dans les 53 consoles enregistrées : l'essai est nécessaire. Déroulement : une touche g à l'arrêt, une par seconde pendant le tour (une dizaine), une après l'arrêt ; un second tour si le temps le permet. Attendu si l'explication du § 5.15.2 est la bonne : X à −9 % de Z et Y à −4 % de Z ; si X et Y restent à 0,3 °/s de zéro, elle est fausse. Le calcul : inclinaison = atan(√(X² + Y²) / Z), facteur = √(X² + Y² + Z²) / Z. L'affichage à une décimale suffit (0,0002 sur le facteur) ; le bruit vrai d'une lecture pendant un tour n'est pas connu, d'où la dizaine de lectures.

**Ce que les mesures de cette note ajoutent à son idée du capteur tourné** :

- il fournirait le second témoin qui manque (§ 5.15.5) : un mur lu de côté en roulant donne l'écart au mur et un cap qui ne dépend pas du facteur du gyroscope ; les montants de porte qui défilent donneraient la position le long d'un couloir, là où le filtre hésitait sur 1,45 m. Non essayé ;
- dans le firmware, deux constantes sont en jeu et non une : la butée du servo (30°, fixée à sa demande le 9 parce que les fils du capteur sont courts) et la taille de la carte polaire (± 80°). À ne toucher qu'une fois les fils vérifiés sur une photo ou rallongés ;
- la place du capteur sur le robot compte alors davantage (§ 5.6, § 5.15.6) : la mesure à la règle de l'essai 8 devient un préalable, avec la distance de l'axe du servo à la face du capteur, qui s'ajoute à chaque lecture de côté.
