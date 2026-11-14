# J — Revue de la localisation : ce que le projet pourrait manquer

Rédigé le 2026-11-14 par une session à part, à ta demande : « review les possibilités de localisation que je pourrais manquer ». **C'est une revue : rien n'a roulé, aucun ordre n'a été envoyé au robot, aucun fichier existant n'a été modifié.** Le cerveau n'a été interrogé qu'après coup, le 14 à 17 h 43, une fois cette limite levée par toi : des lectures de son état, robot endormi sur sa base, rien de changé dans sa mémoire. Elle part de l'audit du même jour ([note I](I_audit_regard_neuf.md)) et ne le refait pas.

Chaque affirmation porte une étiquette :

- **mesuré** : lu dans un enregistrement de `mesures/` ;
- **rejoué** : calcul refait sur ces enregistrements, sans le robot ;
- **simulé** : calcul sur des nombres fabriqués, pas sur le robot ;
- **lu** : lu dans le code ou dans un document du projet ;
- **supposé** : raisonnement, pas encore vérifié.

Scripts et résultats : `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/`, fichiers `rv_…py` et `results_rv_…_20261114.txt`.

## En bref

1. **Le cap du cerveau s'abîme quand il reste allumé longtemps.** Il est gardé dans un nombre trop court, jamais remis à zéro. Au-delà de 16 384° accumulés (43 tours sur place), les rotations lentes sont mal comptées ; au-delà de 32 768°, elles ne le sont plus du tout. Le 13 après-midi il est monté à 44 562° (lu dans le code, simulé, mesuré pour les 44 562°). Correction : trois lignes du firmware, écrites à ta demande dans la version 12, installée le 14 à 18 h 35 ; pas encore essayée en mouvement.
2. **Le courant de la batterie dit quand les roues forcent.** Sur 195 m d'avances des 13 et 14, il a dépassé son niveau normal de 250 mA pendant 1,5 s à quatre moments seulement : les deux patinages connus (une roue le 13 à 14 h 51, les deux roues sur le seuil de la cuisine le 14 à 16 h 19). Aucune fausse alerte (mesuré). Personne ne s'en sert.
3. **Le capteur de distance est une règle que personne ne lit pendant les avances.** Sur 29 m d'avances vers un mur de face, il s'accorde avec les roues à 0,2 % en moyenne, à 1 % près d'un jour à l'autre (mesuré). Cela donne un étalon sans mètre ruban, et une correction de l'avance que le filtre n'utilise pas.
4. **Le plan est à la bonne échelle** : 0,995 ± 0,005 contre les roues sur 70 trajets (rejoué). Ce n'est donc pas lui qui explique les 30 cm d'erreur du couloir.
5. **Ces 30 cm** : sur la carte cohérente de l'audit il en reste 24 sur un tronçon de 9,1 m qui contient le couloir (rejoué). Les roues comptent juste en ligne droite et un tour complet ne déplace pas le robot (−0,8 ± 1,0 mm sur 62 tours, mesuré). Reste à mesurer ce que font les séries de petits pivots du centrage : un essai immobile de deux minutes.
6. **Le cap tiré de deux tours consécutifs** (la direction du trajet entre eux) fait un peu mieux que le cap lu sur les parois : 35 mm de travers au lieu de 50 sur 10 trajets, une fois la carte rendue cohérente (rejoué, petit échantillon).
7. **Matériel** : avant tout achat, un téléphone posé en hauteur et un marqueur imprimé collé sur le robot donneraient la « vérité extérieure » qui manque (0 $). Le LiDAR de l'audit reste le seul achat qui change le principe ; le capteur de flux optique, la caméra vers le plafond et la boussole viennent loin derrière.
8. **Regardé et écarté** : la roulette avant (muette sur ce robot), le signal du capteur de mur, le seuil de la cuisine comme repère de cap, les joints du sol, l'appui contre un mur, les balises radio.

## 1. Ce que j'ai lu

Lu en entier : `AVANCEMENT.md`, la note I, `code/PROMPT_session_locale_2.md`, le firmware (`roomba694_wifi.ino`, `position.ino`, `radar.ino`, `tour.ino`, `mouv.ino`, `carte.ino`, `web.ino`), `outils/localiser.py`, `outils/reperes.py`, les sections 51 à 53 du journal, les deux notes de passage des autres sessions.

Lu par trois assistants qui m'ont rendu un inventaire (136, 121 et 108 idées relevées, avec le verdict de chaque document) : le rapport de départ, les sept notes de recherche, les notes A, C, E, F, G et H. Je n'ai pas relu ces fichiers moi-même : quand je dis « absent des documents », c'est d'après ces inventaires et mes recherches par mots.

Lu en partie : `centrage.py`, `explorer3.py`, `carto.py`, `plan.py`, `balise_base.py`, le journal (titres et recherches par mots).

## 2. Ce qui est gratuit : les capteurs et les données déjà là

### 2.1 Le courant de la batterie voit les roues forcer

- **Ce que c'est.** La colonne `ma` du journal (courant de la batterie) et les colonnes `cur_g`, `cur_d` (courants des deux roues) sont enregistrées 20 fois par seconde depuis le firmware v8. Aucun outil du PC ne les lit (lu : recherche dans `code/outils/`).
- **Ce que disent les enregistrements** (`rv_patinage_deux_roues.py`, mesuré). 195 m d'avances des 13 et 14, par fenêtres de 1,5 s :

| | Courant de la batterie, en plus du repos |
|---|---|
| La moitié du temps | 118 mA |
| 99 fois sur 100, sous | 199 mA |
| 999 fois sur 1 000, sous | 296 mA |

  Le seuil « 250 mA de plus qu'au repos pendant 1,5 s » n'est franchi que quatre fois : trois fenêtres le 13 de 14 h 51 min 45 à 14 h 52 min 03 (le patinage de la roue droite dans la pièce centrale, journal § 43), et une le 14 à 16 h 19 min 26 (les deux roues sur le seuil de la cuisine, journal § 52). **Les deux patinages connus, et rien d'autre.**
- **Ce que cela apporte.** Le patinage de deux roues ensemble, que `carto.py` ne voit pas (il compare les roues au gyroscope). Sur le seuil : 546 mm comptés pour 350 parcourus. Avec ce signal l'avance s'arrête en 1,5 s, soit une quinzaine de centimètres comptés en trop au lieu de vingt, et surtout la position est marquée « douteuse » au lieu d'être crue.
- **Autre lecture utile.** Le 13 à 14 h 51 le courant était haut aussi : la roue ne tournait pas dans le vide, elle forçait contre quelque chose (bord de tapis, objet). Cela répond en partie à la question posée dans `AVANCEMENT.md` (« y a-t-il un tapis vers D27 et E27 ? »).
- **Coût.** PC seulement : une condition de plus dans `Pilote._mouvement` et dans `carto.part_roulee`. Aucune pièce, pas de firmware. Mieux ensuite dans le cerveau (§ 3.2).
- **Certitude.** Mesuré, mais sur deux événements seulement. Le rapport de départ avait proposé l'idée (« robot retenu sans contact ») sans données ; les courants n'étaient pas encore enregistrés.
- **Premier essai sans rouler.** Rejouer `rv_patinage_deux_roues.py` après chaque séance : il doit rester muet hors des patinages.
- **Risque.** Un tapis épais ou la rampe de la base font monter le courant sans patinage : le robot s'arrêterait pour rien. Seuil à confirmer sur un tapis.

### 2.2 Le capteur de distance comme règle pendant les avances

- **Ce que c'est.** Pendant une avance le capteur regarde devant, dix fois par seconde, et sa lecture est dans chaque ligne du journal (`us_mm`). Le filtre de `localiser.py` ne s'en sert pas : entre deux tours sur place il ne corrige la position qu'avec les murs à ne pas traverser et les appuis du pare-chocs (lu). Les inventaires disent que l'idée n'a jamais eu sa fiche : la note G la remettait « à plus tard » comme simple contrôle.
- **Ce que disent les enregistrements** (`rv_avance_sonar.py`, mesuré). 366 avances de 15 cm ou plus, 199,5 m :

| | Avances | Chemin |
|---|---|---|
| Une distance est lue sur 12 cm ou plus | 342 | 186 m |
| « Cible suivie » : la distance baisse en ligne droite, à 12 mm près | 81 | 40 m (20 % du chemin) |
| dont « mur de face » : elle baisse d'autant que les roues comptent, à 4 % près | 50 | 29 m |

  Sur ces 50 avances vers un mur de face : la distance lue baisse de **1,0017 mm par millimètre compté** (moyenne pondérée ; médiane 0,997 ; erreur de la moyenne 0,003). L'écart autour de la droite est de 9 mm en médiane.
- **Ce que cela apporte, trois choses.**
  1. **Un étalon sans mètre ruban.** Le son va à 343 m/s à 20 °C, à 0,17 % par degré près. Les roues comptent donc juste à 1 % près (1,009 le 13 sur 35 avances, 0,992 le 14 sur 15 : l'écart entre les deux jours n'est pas expliqué). L'audit regrettait qu'il n'y ait « aucune vérité extérieure » : en voici une pour les distances, déjà dans les fichiers.
  2. **Une correction de l'avance entre deux tours**, une fois sur cinq : quand une cible est suivie, le filtre peut juger ses hypothèses sur la distance lue à l'arrivée (à 1 cm près) au lieu d'attendre le tour suivant.
  3. **Un second avis sur le patinage.** Sur le seuil, la distance lue est restée entre 763 et 820 mm pendant que les roues comptaient 170 mm.
- **Limite mesurée.** Seul, ce signal donne trop de fausses alertes : 31 fenêtres « distance fixe » sur 195 m sans patinage (cibles de côté, vitesse lente). Il ne vaut qu'avec le courant (§ 2.1) : les deux ensemble, une seule alerte, la bonne.
- **Limite de principe.** Quatre avances sur cinq n'ont pas de cible stable. Dans le couloir du 14, le faisceau large accroche les montants de porte de côté, et la pente tombe à 0,91 ou 0,96 sur les avances où une cible est suivie. La note du projet le disait déjà : juger chaque lecture une à une donne un résultat faux. D'où la règle « cible suivie » avant de s'en servir.
- **Coût.** PC : une trentaine de lignes dans `localiser.py`. Rien dans le cerveau. La lecture brute du capteur dans le journal (proposition B5 de l'audit) rendrait le signal plus net : aujourd'hui c'est la médiane des trois derniers tirs.
- **Premier essai sans rouler.** Rejouer le filtre sur `exploration19` avec et sans cette correction (`data_analysis/m_rejeu_filtre.py`).
- **Risque.** Une personne ou le chat devant le robot : la cible bouge. La règle « baisse en ligne droite » l'écarte en partie.

### 2.3 L'échelle du plan, et les 30 cm du couloir

- **Question.** Le plan est donné à « 54 ± 2 pixels par mètre » (`plan.py`). Quatre pour cent d'erreur feraient 15 cm sur 3,9 m. Est-ce la cause des 30 cm du couloir (journal § 52) ?
- **Réponse : non** (`rv_cap_corde.py`, partie 2, rejoué). Sur 70 trajets de 1 m ou plus entre deux tours consécutifs, la distance sur le plan vaut **0,995 fois** le chemin droit compté (erreur de la moyenne 0,005). Comme les roues s'accordent au son à 0,3 %, le plan est juste à 1 % près. Dans le sens gauche-droite du plan : 0,991 ± 0,006 (43 trajets). Dans le sens haut-bas : 1,018 ± 0,025 (7 trajets seulement, pas de conclusion).
- **Ce qui reste des 30 cm** (rejoué, mêmes fonctions que l'audit). Le rejeu ne situe pas les deux tours faits juste après la porte ; le seul tronçon jugeable va du dernier tour avant le couloir (J20 d'après le journal) au troisième tour après la porte H12, 9,1 m de chemin : le couloir mené par `centre=`, la porte, puis deux trajets ordinaires. « En long » veut dire dans la direction qui va du départ à l'arrivée de ce tronçon.

| Carte | Écart à l'arrivée | En long | En travers |
|---|---|---|---|
| Positions du programme | 421 mm | +399 mm | −132 mm |
| Carte cohérente de l'audit (A1) | 290 mm | +244 mm | −156 mm |

  La carte cohérente explique donc 15 cm des 40. **Il reste 24 cm comptés en trop sur 9,1 m, soit 2,7 %**, alors que les roues comptent juste à 1 % en ligne droite. Je ne peux pas dire quelle part revient au couloir seul.
- **Une piste écartée** (`rv_derive_pivot.py`, mesuré). Si le robot glissait un peu à chaque pivot, les tours sur place le montreraient : leurs vingt derniers degrés revoient les parois des vingt premiers. Sur 62 tours : −0,8 mm ± 1,0. **Un tour complet ne déplace pas le robot.**
- **Ce qui reste possible** (supposé). Ce tronçon contient une vingtaine de séries de pivots (+90°, −180°, +90°) et des petits pivots de 3°, qui ne sont pas des tours complets. Un centimètre perdu par série suffirait. Les enregistrements ne permettent pas de le dire : devant, la cible change à chaque arrêt.
- **L'essai qui tranche** (rotation seulement, trois minutes, ton accord comme pour tout mouvement). Robot face à une paroi à 1 m, lire la distance ; faire dix fois la série +90°, −180°, +90° comme le fait `centrage.py` (roues à 100, 75 et 100 mm/s, mêmes pauses), en relisant la distance après chaque série. **Oui, les pivots déplacent le robot** si la distance a changé de plus de 3 cm au bout des dix. Sinon la cause est ailleurs et il faudra refaire le couloir en enregistrant la lecture brute du capteur.
- **Le programme est prêt, pas lancé** : `data_analysis/rv_essai_pivots.py`. Sans l'option `--go` il lit l'état et dit ce qu'il ferait (essayé le 14 à 17 h 44, robot sur sa base : « il refuserait »). Avec `--go` il passe par les rotations bornées du cerveau (`/api/mouv?rot=`), s'arrête à la première anomalie sans jamais remettre le mode Safe de lui-même, et finit par `s` puis `x`. Il écrit `mesures/revue_…_pivots.json`.

### 2.4 Le cap tiré de la « corde » entre deux tours

- **Ce que c'est.** L'audit conclut que le cap limite : relu à 2° près à chaque tour, il coûte 6 cm de travers après 1,8 m. Or quand deux tours consécutifs sont situés sur les repères, la direction du trajet de l'un à l'autre est connue de deux façons : sur la carte, et dans le repère du robot (roues et gyroscope). Leur écart est le cap, sans regarder la direction d'aucune paroi. Deux positions justes à 2 cm et distantes de 1,8 m le donnent à 0,9° près.
- **Ce que dit le rejeu** (`rv_cap_corde.py`, partie 1). Trajet du 14 au matin, carte construite avec les tours du 13, dix trajets qui ont un trajet précédent de 0,8 m ou plus :

| Cap de départ | Écart médian à l'arrivée | Trois quarts sous | Neuf dixièmes sous | En travers (médiane) |
|---|---|---|---|---|
| lu sur les repères (l'audit) | 80 mm | 94 mm | 139 mm | 50 mm |
| tiré de la corde précédente | 66 mm | 81 mm | 97 mm | 35 mm |
| moyenne des deux | 73 mm | 79 mm | 99 mm | 33 mm |

- **Deux réserves.** Dix trajets, c'est peu : un indice, pas une preuve. Et cela ne marche que sur la carte cohérente : avec les positions actuelles du programme, aucun gain (123 contre 126 mm), parce que deux positions fausses de 7 cm donnent une corde fausse de 3°.
- **Ce que cela change.** C'est un argument de plus pour faire d'abord la carte cohérente (A1 de l'audit), et une suite gratuite une fois qu'elle est faite. Aujourd'hui le filtre fait l'inverse : à chaque tour il rebrouille le cap de 3° ou plus exprès (`caps=(3.0, 8.0, 20.0…)` dans `localiser.py`), ce qui jette l'information de la corde. Ce réglage date du 10 novembre, quand les positions venaient du plan seul.
- **Coût.** PC, une vingtaine de lignes, après A1.
- **Risque.** Une roue qui patine entre les deux tours fausse la corde : à n'employer que si le courant (§ 2.1) n'a rien signalé.

### 2.5 Les regards du centrage ne servent pas à la position

- **Ce que c'est** (lu, non essayé). Dans le couloir, `centre=` a fait douze arrêts ; à chacun le robot a pivoté de +90° puis de −180° avec le capteur allumé. Ce sont douze demi-tours de mesures. Elles servent à se centrer, pas à se situer : le filtre ne juge ses hypothèses qu'à la fin d'un tour complet.
- **Ce que cela apporterait.** Une position recalée à chaque arrêt d'un passage, là où l'estime dérive aujourd'hui de 24 à 30 cm, sans une seconde de plus.
- **Ce qui manque.** La lecture brute du capteur dans le journal (B5 de l'audit) : à 46 °/s, la médiane de trois tirs étale chaque paroi sur une dizaine de degrés. Sans elle, je ne peux pas dire ce que valent ces demi-tours.
- **Premier essai sans rouler.** Passer à `carto.paliers_souples` les lectures du couloir du 14 (16 h 25 à 16 h 29) et compter les paliers trouvés par arrêt.

## 3. Ce qui demande un changement du firmware

### 3.1 Le cap gardé dans un nombre trop court

- **Ce que j'ai lu.** Dans `roomba694_wifi.ino`, la tâche du gyroscope fait cent fois par seconde `imu.yawDeg += r * dt`, et le commentaire dit que `yawDeg` n'est « jamais remis à zéro (la position en dépend) ». C'est un `float` : il garde 24 bits. Entre 8 192° et 16 384° son plus petit pas vaut 0,001° ; entre 16 384° et 32 768°, 0,002° ; au-delà, 0,004°. Une addition plus petite qu'un demi-pas est perdue.
- **Jusqu'où il monte** (`rv_cap_float32.py`, mesuré). Tous les tours tournent à gauche, 380° chacun. Sur 29 enregistrements : 15 dépassent 8 192°, 7 dépassent 16 384°, 3 dépassent 32 768°. Le 10 au soir : 34 211°. Le 13 après-midi, cerveau allumé depuis cinq heures : **44 562°**. Le 14, redémarré plusieurs fois : 12 035° au plus.
- **Ce que cela coûte** (simulé, avec le bruit mesuré robot immobile, 0,04 °/s, et un pas de temps de 10 ou 11 ms comme dans le firmware). Part d'une rotation lente qui entre vraiment dans le cap :

| Cap déjà accumulé | Rotation de 0,02 °/s | 0,05 °/s | 0,1 °/s | 0,2 °/s | 0,5 °/s |
|---|---|---|---|---|---|
| 10 000° | 100 % | 102 % | 101 % | 101 % | 100 % |
| 20 000° | 36 % | 59 % | 108 % | 95 % | 103 % |
| 40 000° | 0 % | 0 % | 8 % | 122 % | 84 % |

  Les tours sur place eux-mêmes ne sont pas touchés (0,13° d'erreur au pire à 40 000°). Ce sont les rotations lentes qui le sont : la dérive du robot en ligne droite, que la tenue du cap de `mouv.ino` est censée voir et corriger. Au-delà de 32 768°, le robot peut tourner de 0,1 °/s sans que le cerveau le sache : 1,5° sur une avance de quinze secondes, à chaque avance.
- **Un indice dans les mesures de l'audit** (rejoué). L'échelle du gyroscope qui referme le mieux le cap de ses 22 boucles : 1,0052 en moyenne (écart-type 0,0011) pour les 15 boucles des enregistrements restés sous 16 384° ; 1,0025 (écart-type 0,0021, de 0,998 à 1,0047) pour les 7 boucles des enregistrements montés au-dessus. L'audit notait que l'échelle bouge d'une boucle à l'autre sans que l'inclinaison l'explique : ceci peut en être une part. Ce n'est qu'un indice : un seul après-midi est concerné, et les boucles d'un même enregistrement partagent des tours.
- **Correction.** Dans `imuTask`, accumuler dans une variable `double` propre à la tâche et recopier sa valeur dans `imu.yawDeg` à chaque passage. Trois lignes. Les autres tâches continuent de lire un `float`, sans risque de lecture à moitié écrite. **Écrite le 14 au soir à ta demande, dans le firmware version 12** (`roomba694_wifi.ino`, `imuTask`), installé le 14 à 18 h 35 avec ton accord. Vérifié robot immobile : cap stable, zéro du gyroscope suivi. Pas encore essayé en mouvement : aucune rotation n'a été faite avec la version 12.
- **Avec un firmware d'avant la version 12.** Redémarrer le cerveau au début de chaque séance et toutes les quarante rotations complètes environ. Le 14 c'est arrivé par hasard, et c'est le jour où tout a mieux marché ; je ne peux pas dire quelle part lui revient.
- **Premier essai sans rouler.** Aucun sur le robot : le défaut ne se voit qu'après des dizaines de tours. `rv_cap_float32.py` le montre sur le PC. Après la correction : comparer, sur une séance longue, l'échelle des boucles du début et de la fin.
- **Risque de la correction.** Faible. Les calculs en `double` sont plus lents sur cette puce, mais cent additions par seconde ne pèsent rien.

### 3.2 L'arrêt sur effort dans le cerveau

Le signal du § 2.1 a sa place dans `mouvTick`, à côté de « le robot n'avance pas » : courant de la batterie au-dessus du repos de 250 mA pendant une seconde, ou distance lue qui ne baisse pas avec une cible suivie. Le cerveau s'arrête alors de lui-même, même si le PC est en retard. Coût : une dizaine de lignes. Risque : le même qu'au § 2.1. À ne faire qu'après l'avoir vu marcher côté PC.

### 3.3 Deux lectures à ajouter à l'état, pour trancher deux questions

- **La température de la puce du gyroscope.** Le cerveau lit déjà ses deux octets à chaque lecture et les jette (lu). Les écrire dans `/api/state` coûte une ligne. Cela permettrait de dire si le zéro et l'échelle du gyroscope suivent la température : la question est ouverte depuis le rapport de départ, et l'audit laisse 0,0015 d'échelle sans explication. Aucune mesure aujourd'hui.
- **La force du signal Wi-Fi.** Une ligne aussi (`WiFi.RSSI()`). Proposée dès le rapport de départ pour reconnaître la pièce (à 2 à 4 m près, pas mieux), jamais enregistrée. Depuis le 14 elle a un autre intérêt : une carte des endroits où la liaison décroche (la cuisine), utile pour savoir où ne pas compter sur le PC.

### 3.4 Des tirs plus serrés pendant le tour

- **Ce que j'ai lu.** Pendant un tour le capteur tire toutes les 100 ms (`RADAR_FIXED_MS`), alors que le balayage du servo tire déjà toutes les 60 ms (`RADAR_PING_MS`). Une note de recherche juge 16 tirs par seconde sûrs ; ce n'a jamais été appliqué au tour.
- **Ce que cela apporterait** (supposé). À 60 ms, un tour 1,6 fois plus rapide garde une mesure tous les 3°. L'audit a montré qu'on ne peut pas accélérer les tours à cadence égale (un tour ne garde plus que 4 paliers sur 8). Ici la cadence suit. Gain : 5 s par tour sur 12,3, soit 113 s pour les 23 tours du trajet du 14 (8 % de ses 1 373 s).
- **Premier essai sans rouler.** Robot immobile face à un mur à 2 ou 3 m, capteur fixe : comparer la dispersion des lectures à 100 ms et à 60 ms. **Non** si des lectures fausses apparaissent (l'écho du tir précédent).
- **Risque.** Une rotation plus rapide fait patiner davantage les roues ; le gyroscope reste le compteur, donc sans effet sur le cap.

## 4. Ce qui demande du matériel

Prix en dollars canadiens, ordres de grandeur seulement : je n'ai fait aucune recherche de prix aujourd'hui, à vérifier sur Amazon.ca avant de commander.

### 4.1 Un téléphone et un marqueur imprimé : la vérité extérieure (0 $)

- **Ce que c'est.** Un marqueur carré noir et blanc (du genre ArUco, à imprimer sur une feuille) collé sur le dessus du robot ; un téléphone ou une webcam posé en hauteur, qui filme une zone de 2 à 3 m. Sur le PC, la bibliothèque OpenCV (déjà installée) rend la position et l'orientation du marqueur dans chaque image.
- **Précision à attendre** (supposé). Quelques millimètres et 0,3° environ pour un marqueur de 15 cm filmé en haute définition à 2,5 m, dans le champ de la caméra seulement.
- **Ce que cela apporte.** L'audit écrit que rien ne juge la précision de l'extérieur, et propose trois cotes au mètre ruban (T4). Une caméra donne la même chose en continu. Elle tranche d'un coup : l'échelle du gyroscope à gauche et à droite (essai T2 de l'audit), le déplacement pendant les pivots (§ 2.3), la carte cohérente contre la carte du jour dans une pièce. Aucun des inventaires ne mentionne cette idée : la caméra n'y est envisagée qu'embarquée, et écartée.
- **Coût.** Une feuille, du ruban adhésif, un support pour le téléphone. Pas de firmware. Un script d'une cinquantaine de lignes sur le PC.
- **Premier essai sans rouler.** Poser le marqueur au sol à deux endroits distants d'un mètre mesuré à la règle : la caméra doit rendre un mètre à 1 cm près.
- **Risques.** La vidéo montre ton logement : elle reste sur le PC, dans un dossier hors dépôt comme `plan_lidar/`. La caméra déforme les bords de l'image : rester au centre, ou l'étalonner avec un damier imprimé.

### 4.2 Le LiDAR de l'audit (C3) reste le premier achat

Je n'ai rien à ajouter à la note I, § 7.3, sinon ceci : les deux pistes qui suivent ne valent que si tu n'achètes pas de LiDAR.

### 4.3 Un capteur de flux optique sous le robot (25 à 40 $)

- **Ce que c'est.** Le capteur d'une souris d'ordinateur, tourné vers le sol (PAA5100JE, PMW3901). Il mesure le déplacement vrai du robot sur le sol, dans les deux sens, sans les roues. C'est ce qu'emploient les aspirateurs du commerce sans LiDAR (note I, § 6.1). Les notes de recherche le citent comme achat possible, sans étude de montage.
- **Précision** (lu dans les notes, non vérifié). 1 à 2 % du chemin.
- **Ce que cela apporterait.** Le patinage des deux roues et le glissement de côté, mesurés et non plus seulement signalés. Le § 2.1 fait déjà le signalement pour rien.
- **Coût.** La pièce, quatre fils de plus sur le cerveau, une lecture dans le firmware. Le montage est la difficulté : ce capteur veut 15 à 35 mm entre lui et le sol, sous un robot qui en laisse une dizaine. Difficile pour un premier montage.
- **Avis.** À garder en réserve. Les mesures disent que les roues comptent juste hors de deux patinages en 195 m.

### 4.4 Une caméra vers le plafond (15 à 20 $)

- **Ce que c'est** (supposé). Une carte ESP32-CAM qui regarde droit vers le haut et envoie une image au PC. Les lignes du plafond (bords des murs, luminaires) donnent le cap sans tourner, à moins d'un degré en principe.
- **Avis.** Elle vise le bon défaut (le cap), mais c'est un gros travail de programme, et un LiDAR donne le cap et la position pour cinq fois le prix. Absente des documents du projet ; je la cite pour que tu saches qu'elle existe.

### 4.5 Une boussole (8 $) : seulement pour retrouver le cap après un portage

En intérieur une boussole est fausse de 5 à 10°, davantage près des moteurs : inutile pour conduire. Mais le journal note qu'après avoir été porté, « le cap ne se retrouve pas en un tour » : le filtre hésite entre plusieurs directions. Un cap à 10° près suffit à choisir la bonne. Petit gain, petit prix, deux fils sur ceux du gyroscope (supposé).

## 5. Ce que j'ai regardé et qui ne vaut pas la peine

- **La roulette avant** (paquet 58, censée dire si le robot avance vraiment) : 0 à toutes les lectures le 10 novembre, 2 à toutes les lectures le 14, jamais 1 sur 484 lectures en marche avant (`rv_signaux_oublies.py`, mesuré). La valeur 2 veut dire « capteur trop sale ou hors service ». Seule chose à faire, trente secondes : retourner le robot et regarder si la roulette est noire et blanche. Si elle est toute noire, ce robot n'a pas ce capteur.
- **Le signal du capteur de mur** (paquet 27) : c'est le capteur optique droit du pare-chocs divisé par quatre (corrélation 0,99 sur 10 368 lectures, mesuré).
- **Le seuil de la cuisine comme repère de cap** (les capteurs de vide de gauche et de droite ne le passent pas au même instant si le robot est de biais) : sur les deux seules traversées lisibles, le cap ainsi lu s'écarte du gyroscope de 2°. Pas mieux qu'un tour. Les deux autres traversées ne montrent pas la bande claire sur les quatre capteurs.
- **Les joints du sol** (carrelage, lames) : aucun motif régulier dans les capteurs de vide, ni dans la cuisine ni ailleurs (pic de 0,09 au mieux, il en faudrait 0,2 ; `rv_joints_sol.py`, mesuré).
- **S'appuyer contre un mur pour se redresser** : le robot est rond, un appui ne le met pas d'équerre ; et le capteur de distance donne déjà la distance à un mur de face à 1 cm.
- **Balises radio (Wi-Fi, Bluetooth, UWB)** : 2 à 4 m pour les deux premières ; 10 cm sans le cap pour l'UWB, au prix d'un LiDAR.
- **Changer la plage de mesure du gyroscope, ou passer par son calcul embarqué** : aucun gain attendu sur le cap.
- **Une balise infrarouge faite maison dans une porte** : les repères donnent déjà mieux près des portes.

## 6. Ce que cela change dans l'ordre de l'audit

Je garde son ordre (les trous de lecture, puis le cap, puis la carte cohérente). J'y glisse :

1. **Fait le 14 au soir** : les trois lignes du § 3.1, dans la version 12. Il n'y a plus à redémarrer le cerveau avant chaque séance.
2. **Reste à faire pour le cap** : sa lecture sur trois axes (B1 de l'audit).
3. **Côté PC, avant de refaire le seuil de la cuisine** : l'arrêt sur le courant (§ 2.1).
4. **Avec la carte cohérente (A1)** : le cap par la corde (§ 2.4).
5. **Avant de refaire le couloir** : l'essai des dix séries de pivots (§ 2.3).
6. **Avant tout achat** : le marqueur et le téléphone (§ 4.1).

## 7. Ce que je n'ai pas pu vérifier

- **Rien n'a roulé.** Tout vient de rejeux, de lectures du code et d'une simulation.
- **L'effet réel du cap trop court sur un trajet.** La simulation dit ce qui est perdu à vitesse constante ; je ne connais pas les vraies vitesses lentes du robot en ligne droite, le journal n'écrit la rotation qu'au dixième de degré par seconde.
- **Le seuil de 250 mA** ne repose que sur deux patinages.
- **Le cap par la corde** : dix trajets, un seul jour.
- **La cause des 24 cm du couloir** : non trouvée.
- **Les prix et les précisions du § 4** : de mémoire et d'après les notes du projet, sans recherche aujourd'hui.
- **Les documents du projet** : je n'ai lu moi-même ni le rapport de départ ni les sept notes de recherche ; je me fie aux inventaires de mes assistants.
