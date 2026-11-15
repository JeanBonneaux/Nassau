# M — Plan d'analyse en direct pendant une séance de cartographie

Session de revue, 2026-11-14 au soir. Demandes de l'utilisateur : « L'autre session pilotera et tu analysera en live pour le reverse engenNERING et la précision possible d'amélioration d'utilisation optimale des capteurs », puis « Outil d'analyse en direct et plan d'analyse en direct pendant session de mapping ».

Chaque chiffre dit d'où il vient : **mesuré** (en faisant relire à l'outil les séances du 14), **prévu** (ce que je ferai), **supposé**.

## En bref

1. La session de navigation cartographie. La session de revue ne pilote pas : elle lit les fichiers de la séance à mesure qu'ils s'écrivent, avec `data_analysis/rv_direct.py`, et ne parle pas au robot.
2. Trois questions suivies en direct : **la position est-elle juste**, **quels capteurs pourraient servir davantage**, **que fait le robot de lui-même**.
3. Trois niveaux d'événements. Seul le niveau 3 est envoyé tout de suite à la navigation : roues qui forcent, pivot où une roue glisse, long trou de lecture en mouvement, mode Safe tombé en mouvement, texte inhabituel du robot.
4. Toutes les cinq minutes un bilan ; à la fin, un compte rendu avec les mêmes chiffres que le tableau du § 5, pour comparer d'une séance à l'autre.
5. Repère mesuré sur les trois cartographies du 14 : le robot passe **54 à 62 % du temps à l'arrêt**, 14 à 16 % à avancer ; le filtre corrige de **32 à 93 mm** par station en médiane ; les tours sur place se referment à **1 ou 2 mm** en moyenne.
6. Cinq petits gestes, laissés au choix de l'utilisateur, donneraient des mesures qu'aucune séance n'a encore (§ 4).

## 1. Qui fait quoi

| Qui | Rôle |
|---|---|
| L'utilisateur | à côté du robot ; dit où aller ; décide des gestes du § 4 |
| La session de navigation | pilote et cartographie (`enregistreur.py`, `explorer3.py`) ; m'écrit quand elle lance l'enregistrement et quand elle l'arrête |
| La session de revue | lance `rv_direct.py`, lit, signale ; n'envoie rien au robot pendant le pilotage |

Avant la séance, le veilleur (`rv_matin.py`, note L § 7.1) a installé la version 13, écouté le robot et lu ses numéros de capteurs. La navigation lit la première ligne de `mesures/matin_dernier.txt` avant de rouler.

## 2. L'outil

`rv_direct.py` lit, à mesure qu'ils s'écrivent, les fichiers de la séance la plus récente :

| Fichier | Ce qu'il en tire |
|---|---|
| `…_capteurs.csv` (20 lignes par seconde) | gestes du robot, courants, capteur de distance, capteurs de vide, capteurs optiques, infrarouge, mode |
| `…_console.txt` | refus, réflexes, silences du robot |
| `…_etat.jsonl` | direction du capteur de distance, batterie |
| `…_X_explorer3.txt` | à chaque station : correction du filtre, note, accord avec les repères |
| `…_X_stations.json` | chaque tour sur place : s'est-il bien refermé |
| `/api/texte` du cerveau (version 13) | tout texte écrit par le robot, une lecture toutes les trois secondes |

Il écrit chaque événement dans `mesures/direct_AAAAMMJJ_HHMMSS_evenements.txt` et n'affiche que les niveaux 2 et 3. Je le lance pour 29 minutes et je le relance tant que la séance dure.

Il ne garde aucun de ces fichiers ouvert : il ouvre, lit depuis la position retenue et referme à chaque passage. Sous Windows, un fichier tenu ouvert ne peut pas être renommé, et `relance.py` renomme le journal de l'explorateur et les stations à la fin de chaque passe (blocage constaté par la session de navigation le 14 au soir, corrigé). Un journal renommé est reconnu à sa première ligne et n'est pas relu ; un tour sur place est reconnu à son nom et à son heure. Relancé en cours de séance, l'outil relit ce qui est déjà écrit sans rien redire, pour que ses bilans portent sur toute la séance.

**Mesuré** : il a relu cinq séances du 13 et du 14 ; il a suivi un enregistrement recopié par petits paquets pendant l'analyse ; et il a suivi une fausse séance en deux passes, avec les renommages de fin de passe (quatre renommages immédiats, chaque station comptée une fois, rien de redit après un relancement). La session de navigation a ensuite essayé les deux outils ensemble, sans le robot (journal § 55, commit c0c2c6a) : son vrai `relance.py` face à cet outil, sur une fausse séance faite des fichiers d'`exploration24`. Les deux renommages passent du premier coup, et l'outil annonce 9 stations et 9 tours pour 9 attendus, une fois chacun. **Non vérifié** : le suivi d'une vraie séance, et le texte du robot sur une vraie carte en version 13.

## 3. Ce que je regarde, et ce que cela peut changer

### 3.1 La position est-elle juste ?

| Question | Signal | Je le signale quand | Ce que cela peut changer |
|---|---|---|---|
| De combien l'estime dérive-t-elle entre deux stations ? | correction du filtre, en mm et en mm par mètre parcouru | 250 mm ou plus | où placer les stations, quelle vitesse garder |
| Le filtre et les repères disent-ils la même chose ? | écart entre les deux à chaque station | 250 mm ou plus : je le dis sans trancher | savoir auquel se fier dans chaque pièce |
| Le filtre est-il sûr de lui ? | sa note | sous 0,5 | refaire un tour, ou se fier aux repères |
| Le robot a-t-il glissé pendant un tour sur place ? | la même paroi relue à la fin du tour (380°) | plus de 25 mm d'écart | confiance dans le tour |
| Les roues comptent-elles juste ? | distance lue devant contre chemin compté, à chaque avance vers une cible | pente hors de 0,90 à 1,08 sur 30 cm ou plus | corriger l'estime par le capteur de distance (note J § 2.2) |
| Une roue a-t-elle patiné ? | courant de la batterie à +250 mA ou roues à 330 mA pendant 1,5 s (note J § 2.1) | tout de suite, niveau 3 | arrêter l'avance avant de perdre la position |
| Un pivot a-t-il raté ? | roues contre gyroscope | plus de 6° et de 6 % d'écart, niveau 3 | refaire le pivot, ne pas compter le chemin |

### 3.2 Quels capteurs pourraient servir davantage ?

| Capteur | Ce que je mesure pendant la séance | Ce qu'on en ferait |
|---|---|---|
| Capteur de distance, pendant les avances | combien d'avances ont une cible devant, et l'écart entre roues et son | une règle indépendante des roues |
| Courant de la batterie et des roues | les alertes, comparées à ce qui s'est vraiment passé | un arrêt sur effort |
| Six capteurs optiques du pare-chocs | leur lecture selon la distance lue devant, de 4 à 45 cm (sondage 4) | une distance de près, là où le capteur de distance est aveugle |
| Quatre capteurs de vide | sols sombres et bords rencontrés | reconnaître un seuil ou un tapis, donc une porte |
| Trois récepteurs infrarouges | où et sous quel cap la base est vue | un cap sûr près de la base |
| Gyroscope | échelle du cap contre les roues, pivot par pivot | vérifier son réglage (1,0045) |
| Le temps | part du temps à l'arrêt, en tour, en pivot, en avance | où gagner de la vitesse |
| La liaison | cadence des lectures, lectures manquées, lignes arrivées en retard au PC | savoir à quelle vitesse on peut rouler sans risque |
| La batterie | mAh par minute | prévoir la durée d'une séance |

### 3.3 Que fait le robot de lui-même ? (rétro-ingénierie, note L)

| Question | Signal |
|---|---|
| Qu'écrit-il, et quand ? | texte du robot : réveil, « eEEProm transfer », « Soft reset! » |
| Répond-il mal après un réveil ? | trous de lecture et « pas de réponse » dans les minutes qui suivent |
| Pourquoi le mode Safe tombe-t-il ? | ce que lisaient les capteurs de vide, les roues levées et le pare-chocs juste avant |
| Ses compteurs bougent-ils sans lui ? | pas comptés à l'arrêt, gyroscope immobile (vu à chaque changement de mode le 14) |
| A-t-il des capteurs non documentés ? | lecture des 256 numéros faite par le veilleur avant la séance |

## 4. Cinq gestes qui donneraient des mesures nouvelles

Aucun n'est nécessaire à la cartographie. Chacun est à la décision de l'utilisateur, et c'est la navigation qui le mène.

| Geste | Durée | Ce qu'il mesure |
|---|---|---|
| Dix secondes d'arrêt complet au début et à la fin de la séance | 20 s | zéro du gyroscope et courant de repos, propres |
| Dans chaque pièce, une avance de 50 cm ou plus face à un mur | rien de plus si elle est sur la route | la règle « capteur de distance contre roues », pièce par pièce |
| À une station, deux tours sur place de suite | 25 s | si deux tours au même endroit donnent la même position |
| Un aller et retour sur un même tronçon de 2 m | 1 à 2 min | de combien l'estime se referme, sans le filtre |
| L'essai des pivots (`rv_essai_pivots.py`, note J § 2.3) | 3 min | si les séries de pivots déplacent le robot : la question des 24 cm du couloir |

S'il accepte un « rentre à la base » : l'enregistrer avec la touche `e` (`--e 1`), pour lire le courant des brosses.

**Décision de l'utilisateur, le 15 à 8 h 35 : « Les cinq ».** Ordre proposé à la navigation, qui reste libre de l'adapter à sa route :

1. au tout début, robot sorti de sa base : les dix secondes d'arrêt complet (elles peuvent faire partie de sa minute immobile) ;
2. juste après ses premières rotations : l'essai des pivots, robot face à un mur nu à 1 m ;
3. pendant la cartographie : dans chaque pièce une avance de 50 cm ou plus face à un mur ; à une station au choix, deux tours sur place de suite ; sur un tronçon dégagé, un aller et retour de 2 m ;
4. à la toute fin, avant de fermer la liaison : dix secondes d'arrêt complet.

## 5. Le repère : ce que donnent les cartographies du 14

**Mesuré** en faisant relire ces trois séances à l'outil.

| | `exploration19` (matin) | `exploration23` (après-midi) | `exploration24` (après-midi) |
|---|---|---|---|
| Chemin, durée | 32,0 m en 25 min | 21,6 m en 27 min | 17,2 m en 18 min |
| Temps à l'arrêt | 54 % | 62 % | 61 % |
| Temps en tours sur place | 19 % | 14 % | 10 % |
| Temps en pivots | 11 % | 9 % | 15 % |
| Temps à avancer | 16 % | 14 % | 14 % |
| Stations | 22 | 20 | 9 |
| Correction du filtre, médiane et plus forte | 54 et 156 mm | 32 et 106 mm | 93 et 148 mm |
| Note du filtre, médiane et plus basse | 0,81 et 0,34 | 0,91 et 0,64 | 0,83 et 0,44 |
| Repères contre filtre, médiane et pire | 85 et 222 mm | pas de repères | 66 et 353 mm |
| Fermeture des tours, moyenne et pire | −2 et 20 mm | +1 et 16 mm | −1 et 11 mm |
| Capteur de distance contre roues, murs de face | 1,020 (2 avances) | 0,991 (7 avances) | 0,985 (2 avances) |
| Cap, gyroscope contre roues | 1,011 (91 pivots) | 1,010 (79 pivots) | 1,007 (67 pivots) |
| Lectures | une toutes les 47 ms | une toutes les 47 ms | une toutes les 47 ms |
| Trous de lecture, le plus long | 4, 1,5 s (version 10) | aucun (version 11) | aucun (version 11) |
| Lignes arrivées en retard au PC (Wi-Fi) | 1, 1,5 s | 7, 2,5 s au plus | aucune |
| Roues qui forcent | 0 | 0 | 2 (seuil de la cuisine) |
| Contacts | 6 | 2 | 0 |
| Batterie | 3,0 mAh par minute | 2,8 mAh par minute | 3,0 mAh par minute |

Deux lectures de ce tableau :

- **Le robot est à l'arrêt plus de la moitié du temps.** Il avance 14 à 16 % du temps. La vitesse de la cartographie se joue donc dans les arrêts (calculs, attentes), plus que dans la vitesse des roues.
- **Les tours sur place sont bons** : ils se referment à 1 ou 2 mm en moyenne, 20 mm au pire. Ce n'est pas là que la position se perd.
- **Depuis la version 11, plus aucune lecture ne manque** ; il reste des lignes qui arrivent en retard au PC quand le Wi-Fi hésite. L'outil compte les deux à part, sur l'horloge du cerveau.

## 6. Le déroulé

1. **Avant.** Le veilleur a fini (`mesures/matin_dernier.txt` : « fini »). La navigation m'écrit qu'elle lance l'enregistrement.
2. **Pendant.** Niveau 3 : message immédiat à la navigation, une ligne, avec l'heure. Niveaux 1 et 2 : dans le fichier d'événements. Toutes les cinq minutes, le bilan.
3. **Après.** Je fais relire la séance entière à l'outil et je rends : le tableau du § 5 pour cette séance à côté de celles du 14, la liste des alertes avec ce qui s'est vraiment passé, la courbe des capteurs optiques, ce que le robot a écrit, et au plus trois propositions chiffrées pour la séance suivante.

## 7. Ce que ce plan ne fait pas

- Il ne corrige rien pendant la séance : la navigation reste seule à décider de la route et des arrêts.
- Il ne cherche aucun ordre inconnu du robot (« Capteurs seuls pour le moment »).
- Les seuils d'alerte viennent des séances des 13 et 14. Sur un autre sol ou à une autre vitesse, ils peuvent être à retoucher : le compte rendu le dira.
