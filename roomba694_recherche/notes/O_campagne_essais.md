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

## 1. Les essais courts, dans l'ordre

Chacun répond à une question. Un tour sur place avant le premier et après le dernier.

| N° | Essai | La question | Ce qu'on en ferait | État |
|---|---|---|---|---|
| 1 | Trois traversées de l'axe de la base, à 0,7 m, 1,1 m et 1,5 m d'elle, à 60 mm/s ; puis un tour sur place sur l'axe | Où exactement le faisceau vert passe-t-il au rouge ? Les deux récepteurs de devant donnent-ils un cap ? | un repère absolu, au centimètre, près de la base ; un contrôle de « devant la base » | **fait** (§ 5.2) : axe lu à 1 cm près, cap à 2° près |
| 2 | Lecture des numéros cachés, robot en mode passif sur l'axe, base vue | L'octet parasite 177 vient-il quand la base est vue ? | savoir quand les lectures sont brouillées | **fait** (§ 5.3) : non, il ne vient pas |
| 3 | Avance à 30 mm/s jusqu'à la ligne sombre du tapis, puis recul droit capteur posé dessus | Le robot surveille-t-il le vide en reculant ? | franchir un bord sombre à reculons, sans rien changer d'autre | commandé |
| 4 | Approche lente d'un mur nu, de 45 cm à 3 cm, à 40 mm/s | Que lisent les six capteurs optiques du pare-chocs selon la distance ? | une distance de près, et un arrêt avant le contact | commandé |
| 5 | Essai des pivots devant un mur nu | Les séries de pivots reculent-elles vraiment le robot de 3 à 5 mm ? | corriger l'estime dans les couloirs (note J § 2.3) | commandé |
| 6 | Lecture des numéros cachés, robot sur sa base en charge | Que deviennent les numéros 62, 128, 132 et 145 en charge ? | finir de lire ce que le robot cache | à faire en fin de séance, robot posé sur sa base |
| 7 | Ordres inconnus, un à la fois, par étapes (note L § 4.7) ; robot posé sur un support, les deux roues dans le vide, hors de sa base, quelqu'un à côté ; menée par la session de revue, la navigation ne pilotant pas | Le robot accepte-t-il des ordres que sa documentation ne donne pas ? | peut-être rien ; peut-être un ordre ou une lecture utile | **permis par l'utilisateur le 15 à 10 h 50 (« Oui, essaie »)** ; à faire après les essais roulants |

## 2. « Mappons loin » : les règles d'une cartographie longue

À proposer à la session de navigation après les essais courts. Elles viennent toutes de mesures de la note N.

1. **Quand l'estime et la correction se contredisent de plus de 12 cm sur moins de 2 m, un second tour est fait sur place.** La correction n'est pas refusée d'office : cette règle-là, rejouée sur les séances enregistrées, dégrade la position (§ 5.1).
2. **Le cap vient du gyroscope**, multiplié par 1,0045, et non d'un cap recompté après chaque geste. La perte de position de 10 h 10 venait d'un cap faux de 94°.
3. **Une avance qui dévie s'arrête** (roues et gyroscope en désaccord de 8°), et un tour sur place suit avant de repartir.
4. **Un tour sur place tous les 2 m au plus**, loin des bords de tapis (plus de 20 cm).
5. **Les anciens repères ne servent plus tels quels** près de la base et de D12 : ils y ont fait sauter la position trois fois. Un fichier de repères refait avec l'estime comme contrainte est en préparation (§ 3).
6. **L'outil d'analyse en direct signale** les sauts de position, les avances déviées, les roues qui forcent et les chutes du mode Safe ; `rv_ou_est_le_robot.py` redonne la position par l'estime à tout moment.

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
| Carte des capteurs de vide du tapis (`rv_tapis_carte.py`) | session de revue | faite pour `exploration28` et `29` |

## 4. Les coins sombres : où on en est

Détail dans la note L. La liste des quatorze sondages y est au § 1.

| Sujet | Ce qu'on sait | Ce qui manque |
|---|---|---|
| Mode Safe et sol sombre | surveillé seulement en roulant ; il faut 0,1 s sous 100 ; c'est une ligne étroite au bord du tapis, pas le poil | le recul (essai 3) |
| Sommeil | cinq minutes après le dernier ordre, hors du mode Safe ; deux sortes de réveil, avec ou sans texte | — |
| Numéros de capteurs cachés | horloge (134 à 136), mode (131), deux valeurs qui suivent le mode (128, 145) | 62 et 132 ; l'octet parasite 177 (essais 2 et 6) |
| Charge lue par le robot | elle peut sauter de 115 mAh à un réveil | pourquoi |
| Brosse latérale | à l'arrêt elle se prend sous un bord de tapis ; en marche et d'équerre le bord passe ; en reculant il passe sans elle | la plus petite puissance qui suffit |
| Capteurs optiques du pare-chocs | un obstacle étroit vu 15 cm avant le contact | un mur (essai 4) |
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
- **D'où viennent ces 10,6° : non tranché.** L'utilisateur répond « Base collée au mur » (avec une photo, qui n'est dans aucun fichier), et sur la carte quadrillée le mur derrière la base est horizontal. Un axe d'équerre avec ce mur pointerait plein bas. Il reste donc deux lectures : le cap retenu pendant la séance est trop petit d'une dizaine de degrés ; ou l'axe des faisceaux n'est pas d'équerre avec le mur (la base fait 13 cm de large : un côté décollé de 2,4 cm suffit ; ou ses émetteurs ne sont pas dans son axe). J'avais d'abord écrit à la session de navigation que c'était l'angle du mur sur le plan : c'était faux, et je l'ai corrigé. **Ce qui tranchera** : la montée sur la base par l'axe, proposée par la session de navigation ; robot posé sur ses contacts, son cap est celui de la base.
- **La distance à la base n'est pas sûre non plus.** La largeur des faisceaux (505, 675 et 890 mm sur les trois lignes) met la base 1,05 à 1,2 m au nord de la première ligne ; le plan et le filtre disaient 0,87 m.
- **Les deux récepteurs de devant donnent la direction de la base.** Pendant le tour sur place fait sur l'axe (robot à 5 mm de la ligne), ils ne la voient qu'entre les caps 60° et 92° ; leur cap moyen, 79,5°, est celui de l'axe mesuré (79,4°). En tournant, ils reçoivent le rouge, puis les deux faisceaux, puis le vert : le moment où les deux sont reçus marque la direction à 2° près environ.
- **Le récepteur du dessus ne voit rien quand le robot tourne le dos à la base** : il est masqué vers l'arrière par ce qui est monté sur le robot (remarque de la session de navigation, confirmée).
- **Ce qu'on en tire.** Près de la base, on a maintenant un repère absolu qui ne dépend ni du plan ni des repères : une traversée de 50 cm donne la position de côté à 1 cm près, et un tour sur place donne le cap à 2° près. Il reste à savoir où la base est vraiment sur le plan, et si elle est droite.

### 5.3 Essai 2, les numéros cachés robot en mode passif devant sa base (11 h 00) : fait, rien d'utile de plus

**Mesuré** (576 demandes de 11 h 00 min 43 à 11 h 01 min 20 ; détail dans la note L § 4.10).

- **L'octet parasite 177 n'est pas venu**, base vue et mode passif : il ne tient ni à l'un ni à l'autre. Il n'a été vu qu'une fois, dans la minute qui suivait le réveil du matin.
- **Le numéro 131 vaut 21**, alors qu'il valait 1 aux deux autres lectures en mode passif : ce n'est pas le mode tout court, contrairement à ce que j'avais écrit. Le numéro 62 vaut 0 base vue : ce n'est pas un « base en vue ».
- **Aucun capteur utile** dans ces numéros après quatre lectures : une horloge, deux valeurs qui suivent le mode, deux valeurs qui changent sans qu'on sache pourquoi.

### 5.4 Les essais suivants

À remplir essai par essai.
