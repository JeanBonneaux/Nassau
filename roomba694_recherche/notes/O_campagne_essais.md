# O — Campagne d'essais : les coins sombres du robot, et une localisation plus précise

Session de revue, 2026-11-15, 10 h 30. Demande de l'utilisateur, telle quelle :

> « une fois cette run process, continue d<explorer les coins sombres du fonctionnement, et de mapper par des tests et d<ameliorer le software et de voir ce qu<il nous cache, ce qui pourrait nous etre utile, tu parle a l<autre session, elle execute le pilotage et tu ecoute et commande, et analyse, mappons loin, augmentons nos capacites de localisation precise »

Cette note est le plan de travail. Elle est tenue à jour : chaque essai y reçoit son résultat et le nom du fichier où il est.

## En bref

1. **Les rôles.** La session de revue choisit les essais, les commande à la session de navigation, écoute et analyse. La session de navigation pilote, et reste seule à juger de la sécurité d'un geste : elle peut refuser ou adapter un essai. La session de revue n'envoie aucun ordre de roues.
2. **Deux buts** : savoir ce que le robot fait et cache d'utile ; savoir où il est, plus précisément.
3. **Ce que la matinée a appris** (note N) : les roues et les tours sur place sont bons à 1 à 3 cm ; c'est le calcul de la position qui saute de 16 à 31 cm. La campagne commence donc par ce qui donne un repère sûr, et par ce qui empêche un saut.
4. **Ce qui reste interdit sans un mot de l'utilisateur** : chercher des ordres inconnus du robot (« Capteurs seuls pour le moment », le 14) ; le mode Full ; les brosses autres que la brosse latérale ; l'ordre « rentre à la base » (son accord à chaque fois).

## 1. Les essais courts, dans l'ordre

Chacun répond à une question. Un tour sur place avant le premier et après le dernier.

| N° | Essai | La question | Ce qu'on en ferait | État |
|---|---|---|---|---|
| 1 | Trois traversées de l'axe de la base, à 0,7 m, 1,1 m et 1,5 m d'elle, à 60 mm/s ; puis un tour sur place sur l'axe | Où exactement le faisceau vert passe-t-il au rouge ? Les deux récepteurs de devant donnent-ils un cap ? | un repère absolu, au centimètre, près de la base ; un contrôle de « devant la base » | commandé à 10 h 35 |
| 2 | Lecture des numéros cachés, robot en mode passif sur l'axe, base vue | L'octet parasite 177 vient-il quand la base est vue ? | savoir quand les lectures sont brouillées | commandé |
| 3 | Avance à 30 mm/s jusqu'à la ligne sombre du tapis, puis recul droit capteur posé dessus | Le robot surveille-t-il le vide en reculant ? | franchir un bord sombre à reculons, sans rien changer d'autre | commandé |
| 4 | Approche lente d'un mur nu, de 45 cm à 3 cm, à 40 mm/s | Que lisent les six capteurs optiques du pare-chocs selon la distance ? | une distance de près, et un arrêt avant le contact | commandé |
| 5 | Essai des pivots devant un mur nu | Les séries de pivots reculent-elles vraiment le robot de 3 à 5 mm ? | corriger l'estime dans les couloirs (note J § 2.3) | commandé |
| 6 | Lecture des numéros cachés, robot sur sa base en charge | Que deviennent les numéros 62, 128, 132 et 145 en charge ? | finir de lire ce que le robot cache | à faire en fin de séance, robot posé sur sa base |

## 2. « Mappons loin » : les règles d'une cartographie longue

À proposer à la session de navigation après les essais courts. Elles viennent toutes de mesures de la note N.

1. **L'estime garde la main sur les trajets courts.** Une correction du filtre ou des repères de plus de 12 cm, quand le robot a roulé moins de 2 m depuis le tour précédent, n'est pas appliquée ; elle est signalée, et un second tour est fait sur place.
2. **Le cap vient du gyroscope**, multiplié par 1,0045, et non d'un cap recompté après chaque geste. La perte de position de 10 h 10 venait d'un cap faux de 94°.
3. **Une avance qui dévie s'arrête** (roues et gyroscope en désaccord de 8°), et un tour sur place suit avant de repartir.
4. **Un tour sur place tous les 2 m au plus**, loin des bords de tapis (plus de 20 cm).
5. **Les anciens repères ne servent plus tels quels** près de la base et de D12 : ils y ont fait sauter la position trois fois. Un fichier de repères refait avec l'estime comme contrainte est en préparation (§ 3).
6. **L'outil d'analyse en direct signale** les sauts de position, les avances déviées, les roues qui forcent et les chutes du mode Safe ; `rv_ou_est_le_robot.py` redonne la position par l'estime à tout moment.

## 3. Le logiciel : qui fait quoi

Pour ne pas écrire à deux dans les mêmes fichiers.

| Chantier | Qui | État |
|---|---|---|
| Repères refaits avec l'estime comme contrainte (fichier à essayer avec `--reperes`) | session de revue, dans `data_analysis/` | en cours |
| Refus des corrections de plus de 12 cm sur trajet court, dans l'explorateur | session de navigation, sur ma proposition | proposé |
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

À remplir essai par essai.
