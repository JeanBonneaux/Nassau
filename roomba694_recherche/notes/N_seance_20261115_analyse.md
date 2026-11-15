# N — La séance du 15 au matin, analysée en direct

Session de revue, 2026-11-15. C'est le compte rendu prévu par la note M (§ 6, « Après »).

- **Qui a fait quoi.** La session de navigation a piloté le robot, l'utilisateur à côté. J'ai suivi ses enregistrements avec `rv_direct.py` et je les ai dépouillés. Je n'ai envoyé aucun ordre de roues.
- **Les séances.** `exploration26` (8 h 44 à 9 h 20) : la minute immobile, l'essai des pivots, la cartographie de la pièce à gauche de la base, les cinq gestes de mesure demandés par l'utilisateur (« Les cinq »). `exploration27` (9 h 26 à 9 h 32) : deux essais de montée sur le tapis, à sa demande.
- **Où sont les chiffres.** `data_analysis/results_rv_gestes_20261115.txt` (script `rv_gestes_20261115.py`), `results_rv_pivots_lecture_20261115.txt`, et les fichiers d'événements `mesures/direct_20261115_*_evenements.txt`.

Chaque affirmation dit d'où elle vient : **mesuré**, **lu**, **supposé**.

## En bref

1. **Les mesures brutes sont bonnes** (mesuré). Les roues comptent juste : 1,000 mm vu par le capteur de distance pour 1 mm compté, sur 6 m. Deux tours sur place au même endroit se répètent à moins d'un centimètre. Après 4 m et un demi-tour, l'estime (roues et gyroscope) se trompe de 3 cm.
2. **La position retenue, elle, a sauté trois fois de 16 à 24 cm** (mesuré), chaque fois quand les repères l'ont corrigée. Trois témoins indépendants le disent : les roues et le gyroscope, la comparaison directe des tours, et le signal de la base. **À la fin, le robot se croyait devant sa base ; d'après l'estime il était environ 40 cm à côté, et la base ne le voyait plus.**
3. **Le tapis vert foncé est un obstacle pour ce robot**, pour deux raisons mesurées : son poil sombre est lu comme un vide (deux chutes du mode Safe), et son bord fait patiner la roue droite (deux essais : le robot dévie de 41° puis de 67° pendant que les roues comptent 90 cm).
4. **L'outil d'analyse en direct a pris le patinage sur le fait**, une seconde et demie après son début. C'est la première fois.
5. **Trois propositions chiffrées** au § 7. Aucune n'est décidée.

## 1. Le tableau de la séance, à côté de celles du 14

**Mesuré** en faisant relire `exploration26` à l'outil. Les séances du 14 sont dans la note M, § 5.

| | `exploration26` (le 15) | Les trois séances du 14 |
|---|---|---|
| Chemin, durée | 11,9 m en 31 min | 17 à 32 m en 18 à 27 min |
| Temps à l'arrêt | 77 % (dont 10 min au bord du tapis et 7 min d'attente à la fin) | 54 à 62 % |
| Temps en tours sur place, en pivots, à avancer | 9 %, 8 %, 5 % | 10 à 19 %, 9 à 15 %, 14 à 16 % |
| Stations | 12 | 9 à 22 |
| Correction du filtre, médiane et plus forte | 34 et 181 mm | 32 à 93, et 106 à 156 mm |
| Note du filtre, médiane et plus basse | 0,84 et 0,55 | 0,81 à 0,91, et 0,34 à 0,64 |
| Repères contre filtre, médiane et pire | 100 et 312 mm (9 stations) | 66 à 85, et 222 à 353 mm |
| Capteur de distance contre roues, murs de face | 1,000 (5 avances, 6,0 m) | 0,985 à 1,020 |
| Cap, gyroscope contre roues | 1,010 (61 pivots) | 1,007 à 1,011 |
| Lectures | une toutes les 47 ms | une toutes les 47 ms |
| Lectures manquées | aucune en roulant | aucune depuis la version 11 |
| Contacts | 0 | 0 à 6 |
| Roues qui forcent | 0 (4 alertes dans `exploration27`, au bord du tapis) | 0 à 2 |
| Chutes du mode Safe en roulant | 2 (le tapis) | — |
| Batterie | 2,3 mAh par minute | 2,8 à 3,0 mAh par minute |

## 2. Les cinq gestes

### 2.1 Les arrêts complets (8 h 45 min 40, 66 s ; 9 h 13 min 47, puis 7 min d'attente)

**Mesuré.**

- **Le cap ne bouge pas du tout** : 0,00° en cinq minutes. La vitesse de rotation lue vaut 0,001 à 0,005°/s en moyenne, avec un bruit de 0,05°/s (supposé : le cerveau ne compte pas ces petites valeurs).
- **Le capteur de distance** : 8 à 11 mm d'écart-type à 65 cm et à 1,20 m, 26 à 34 mm d'étendue.
- **Les capteurs de vide** : 2 550 à 2 670 sur le parquet, 5 d'écart-type. **Les capteurs optiques du pare-chocs** : 1 à 2 d'écart-type.
- **Le courant** : 143 mA au repos en mode Safe, toujours la même valeur.
- **La cadence** : une lecture toutes les 48 ms, 108 ms au pire.

### 2.2 Les avances face à un mur

**Mesuré** sur les treize avances de 30 cm ou plus. Cinq visent un mur de face (moins de 15 mm de reste autour de la droite) :

| Avance | Longueur comptée | Distance lue devant | Vu par mm compté |
|---|---|---|---|
| 8 h 52 min 36 | 829 mm | 2 242 → 2 005 mm (23 tirs seulement) | 0,982 |
| 9 h 07 min 13, pièce à gauche, vers le nord | 870 mm | 2 146 → 1 275 mm | 1,022 |
| 9 h 09 min 50, aller de 2 m | 2 003 mm | 3 313 → 1 284 mm | 1,015 |
| 9 h 10 min 14, retour de 2 m | 2 003 mm | 1 997 → 1 140 mm (échos sur la fin seulement) | 0,987 |
| 9 h 12 min 39 | 335 mm | 1 628 → 1 308 mm | 0,976 |

- **En moyenne pondérée : 1,0000.** D'une avance à l'autre, de 0,976 à 1,022.
- **Ce qu'on en tire** : les roues ne comptent ni trop ni trop peu, à 1 % près. L'écart de 24 cm du couloir (note J § 2.3) ne vient donc pas de l'échelle des roues.
- Les huit autres avances visaient une cible de biais ou qui change en route (pentes de toutes sortes, de −0,9 à 2,7) : la règle ne vaut que face à un mur.

### 2.3 Deux tours sur place de suite, au même endroit

**Mesuré**, avec la fonction de comparaison de la session de navigation (`carto.apparier` : les mêmes parois vues dans les mêmes directions).

- Tours `b3` (9 h 07) et `c0` (9 h 08), robot immobile entre les deux : **8 mm** d'écart, sur 6 parois.
- Tours `d0` (9 h 11) et `e0` (9 h 11), robot immobile entre les deux : **3 mm**, sur 8 parois.
- **Ce qu'on en tire** : le tour sur place est une mesure fidèle. Si deux positions calculées au même endroit diffèrent de plus de 2 cm, c'est le calcul qui diffère, pas le tour.

### 2.4 L'aller et retour de 2 m (9 h 09 min 46 à 9 h 10 min 33, sans le filtre)

**Mesuré.**

- D'après les parois (tour d'avant contre tour d'après) : le robot est revenu à **(−10, −54) mm** de son point de départ.
- `passage.py` le comptait à (0, −25) mm.
- **L'estime se trompe donc de 3 cm après 4 m et un demi-tour**, presque tout de côté : c'est une erreur de cap de 0,8° sur le retour.
- Avec le cap brut du gyroscope (sans le facteur 1,0045) l'erreur serait de 6 cm : ce facteur compte.

### 2.5 L'essai des pivots

Dépouillé à part (note J § 2.3) : une série +90°, −180°, +90° recule le robot de 3 à 5 mm sans que les roues le comptent. Un seul essai, à refaire devant un mur nu. Pendant `exploration26`, onze séries ont eu lieu : environ 5 cm de recul non compté.

## 3. Le saut de position

### 3.1 Ce qui est mesuré

J'ai refait le chemin avec les roues et le gyroscope seuls (gyroscope × 1,0045), sans le plan, sans le filtre et sans les repères, et je l'ai comparé d'un tour au suivant aux positions que la session de navigation a retenues.

| Tronçon | Chemin compté | Écart entre l'estime et les positions retenues | Ce qui s'est passé au second tour |
|---|---|---|---|
| a0 → a1 | 0,86 m | 80 mm | |
| a1 → a2 | 1,27 m | 51 mm | |
| a2 → b0 | 1,22 m | 8 mm | |
| b0 → b1 | 0,38 m | 76 mm | |
| b1 → b2 | 0,41 m | 33 mm | |
| **b2 → b3** | 1,05 m | **238 mm** | les repères corrigent de (+250, +29) mm |
| b3 → c0 | sur place | 7 mm | |
| c0 → d0 | 4,05 m (l'aller et retour) | 9 mm | |
| d0 → e0 | sur place | 13 mm | |
| **e0 → e1** | 1,33 m | **176 mm** | les repères corrigent de (−9, +210) mm |
| **e1 → e2** | 0,78 m | **161 mm** | les repères corrigent de (+160, +135) mm |

Sur un mètre, l'estime ne peut pas se tromper de 20 cm : le § 2.4 la donne à 3 cm après 4 m. Les trois grands écarts sont donc des sauts de la position retenue, et chacun tombe sur un tour où les repères ont déplacé la position de plus de 20 cm.

### 3.2 Deux autres témoins

- **Les parois** (mesuré). La comparaison directe de deux tours, sans le plan, dit comme l'estime et pas comme les positions retenues. Exemples : entre `a2` et `c0`, les parois donnent (−383, −19) mm, l'estime (−356, +34), les positions retenues (−94, −37). Entre `b0` et `d0` : parois (+195, +247), estime (+211, +222), positions retenues (+486, +154). Sur six paires qui enjambent un saut, parois et estime s'accordent à 3 à 13 cm ; parois et positions retenues diffèrent de 24 à 32 cm.
- **La base** (mesuré). Elle émet deux faisceaux infrarouges, que le robot reçoit par trois récepteurs.
  - Au départ (8 h 52), robot posé devant sa base par l'utilisateur : les trois récepteurs voient la base 56 % du temps, et le capteur de distance lit 695 mm.
  - À la fin (9 h 13 min 47 à 9 h 20), position retenue « devant la base » : **aucun récepteur ne la voit pendant sept minutes**, et le capteur de distance lit 1 204 mm.
  - D'après l'estime, le robot a fini 51 à 54 cm à l'ouest de son point de départ. D'après les positions retenues, 13 cm.

### 3.3 Ce que j'en lis

- **À partir du tour `b3` (9 h 07), la position retenue est décalée d'environ 25 cm vers l'est** par rapport à tout ce qui précède. Elle saute encore de 16 à 18 cm aux tours `e1` et `e2`.
- **Le filtre ne l'a pas vu.** Relancé au tour `c0` autour de la position donnée par les repères, il l'a confirmée avec une note de 0,93. Filtre et repères peuvent donc s'accorder sur une position que les roues, les parois et la base contredisent.
- **Les repères ne sont pas stables à cet endroit.** Aux quatre tours faits en D12, les mêmes repères ont donné : un calage sur 5 tours, puis « pas d'accord entre eux », puis deux calages sur 2 tours. Au tour `c0`, un seul repère retrouvait la position ; un autre proposait 24 cm à l'ouest, un troisième 17 cm au sud.
- **Les repères ont aussi eu raison une fois** : au tour `a0`, devant la base, ils ont corrigé le filtre de 31 cm, et l'estime leur donne raison (le filtre seul aurait été à 37 cm de l'estime sur le tronçon suivant).
- **Supposé, pour la cause** : un objet que les anciens tours voyaient près de D12 et de la base a changé de place. Plusieurs repères se trompent alors ensemble, du même côté. À vérifier avec l'utilisateur : a-t-il déplacé quelque chose dans cette pièce depuis le 14 ?
- **Je ne tranche pas sur le plan lui-même** : je ne sais pas dire, des positions d'avant ou d'après 9 h 07, lesquelles sont justes sur le plan. Le signal de la base penche pour celles d'avant.

## 4. Les alertes, et ce qui s'est vraiment passé

| Heure | Ce que l'outil a dit | Ce qui s'est passé |
|---|---|---|
| 8 h 45 min 27 et 29 | deux trous de 2,1 s dans les lectures | juste après le réveil, en mode passif ; le cerveau a vidé son tampon deux fois ; plus rien une fois le mode Safe pris |
| 8 h 53 min 46 | mode Safe tombé pendant un mouvement | le capteur de vide droit au-dessus du poil vert foncé du tapis (note L § 4.9) |
| 8 h 58 min 46 à 9 h 02 min 05 | le robot s'est tu 199 s | il s'est endormi après cinq minutes en mode passif |
| 9 h 02 min 42 à 9 h 03 min 14 | trou de 30,5 s ; « le robot envoie du texte » | **ma faute** : ma lecture des numéros de capteurs, lancée sans le mot de la session de navigation ; le texte annoncé était une fausse alerte de ma sonde (note L § 4.10) |
| 9 h 04 min 11 | mode Safe tombé pendant un mouvement | une avance voulue de 150 mm vers le tapis ; le mode tombe après 5 mm |
| 9 h 28 min 44 et 46 | les roues forcent | **patinage au bord du tapis** (§ 5) |
| 9 h 30 min 27 et 29 | les roues forcent | second essai, même patinage |

- **Aucune fausse alerte de niveau fort** en dehors de celle que ma sonde a causée.
- **Une chose que l'outil n'a pas vue** : le saut de position du § 3. Il affichait bien « repères à 252 mm du filtre » pour le tour `b3`, mais sans dire que l'estime contredisait les repères.
- **Ajouté le jour même** : à chaque tour, `rv_direct.py` compare maintenant la position retenue à l'estime depuis le tour précédent, et donne une alerte forte au-delà de 12 cm sur moins de 2,5 m de chemin. **Vérifié par rejeu** : sur `exploration26` il signale `b3` (311 mm), `e1` (204 mm), `e2` (169 mm) et aucun autre tour (7 à 80 mm) ; sur `exploration27` il en signale deux de plus, 290 mm au second tour (les repères) et 172 mm au troisième (le filtre, note 0,47). Il n'a pas encore servi en direct.

## 5. Le bord du tapis fait patiner la roue droite

**Mesuré** sur `exploration27`. L'utilisateur avait demandé de monter sur le tapis.

| | Premier essai (9 h 28, 100 mm/s) | Second essai (9 h 30, 150 mm/s) |
|---|---|---|
| Chemin compté par les roues | 906 mm | 902 mm |
| Les capteurs de vide avant voient le bord | après 536 mm | après 381 mm |
| Le cap s'écarte de 8° | 0,75 s plus tard, à 617 mm | 0,6 s plus tard, à 465 mm |
| Cap à la fin, d'après le gyroscope | 41° à droite | 67° à droite |
| Rotation d'après les roues | 63° à gauche | 57° à gauche |
| Roue droite pendant les trois dernières secondes | 405 mA, 15 pas par lecture | 374 mA, 15 pas par lecture |
| Roue gauche | 280 mA, 6 pas par lecture | 211 mA, 8 pas par lecture |
| Avant le bord | 140 à 150 mA par roue | 150 mA par roue |
| Pare-chocs, roues levées, mode | rien, rien, Safe gardé | rien, rien, Safe gardé |

- **Ce qui se passe** : la roue droite tourne vite sans faire avancer le robot. Le cerveau, qui voit le cap partir à droite, lui demande encore plus de vitesse pour redresser : cela entretient le patinage. Le mouvement se termine « distance atteinte » alors que le robot n'a pas fait ce chemin.
- **Les roues et le gyroscope se contredisent de plus de 100°.** C'est le signe le plus net d'un patinage.
- **Le tapis ne se monte pas en mode Safe**, même si les roues y arrivaient : plus loin, le poil sombre est lu comme un vide et le mode tombe (note L § 4.9).
- **Mon avis** : marquer ce tapis comme un obstacle sur la carte. Son bord se reconnaît : les capteurs de vide y lisent 700 à 1 700, contre 2 500 à 2 700 sur le parquet.

## 6. Ce qui n'a pas pu être mesuré

- **La courbe des capteurs optiques du pare-chocs** (sondage 4) : le robot ne s'est jamais approché à moins de 74 cm d'un obstacle devant lui. Il faudra une avance lente jusqu'à 5 cm d'un mur.
- **Le courant des brosses pendant un « rentre à la base »** : il n'y en a pas eu.
- **Le second essai des pivots**, devant un mur nu.

## 7. Trois propositions chiffrées

Aucune n'est décidée. Les deux premières touchent au code de la session de navigation ou au firmware : elles lui reviennent, ou demandent l'accord de l'utilisateur.

1. **Se servir de l'estime comme garde-fou.** Quand le robot a roulé moins de 2 m depuis le tour précédent, refuser une correction du filtre ou des repères de plus de 12 cm, et le signaler. Aujourd'hui cette règle aurait écarté les trois sauts (`b3`, `e1`, `e2`) et gardé toutes les autres corrections. Erreur attendue ensuite : celle de l'estime, 1 % du chemin.
2. **Arrêter une avance quand le cap s'écarte de 8°**, ou quand les roues et le gyroscope se contredisent de 8°. Les deux arrivent au même instant, 0,6 à 0,75 s après le bord du tapis. Aujourd'hui l'arrêt aurait évité 29 et 44 cm de chemin compté à tort, et 33° et 59° de déviation. C'est une retouche du firmware (version 14).
3. **Se servir de la base comme d'un repère sûr.** Devant elle, les récepteurs la voient plus d'une fois sur deux ; 40 cm à côté, jamais. Un contrôle simple à chaque retour : si la position dit « devant la base » et qu'aucun récepteur ne la voit, la position est fausse.

Plus petit, pour la même version 14 : garder les quatre indicateurs « vide » du robot (note L § 4.9), et corriger le défaut de ma sonde (note L § 4.10).
