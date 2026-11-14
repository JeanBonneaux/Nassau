# I — Regard neuf sur le projet : audit de la méthode, et ce qu'on peut changer

Rédigé le 2026-11-14 par une session à part, à la demande de l'utilisateur : « nouveau regard, audit et amélioration de la méthode, etc. Innove. » **État : diagnostic tiré des enregistrements et du code, propositions classées, trois d'entre elles rejouées ou simulées ; aucun ordre n'a été envoyé au robot, aucun fichier des autres sessions n'a été modifié.** Mots employés avec l'utilisateur : le cerveau (ESP32), le gyroscope (GY-521), le capteur de distance (HC-SR04), le servo (SG90).

Cette note audite le travail de la session de navigation (journal `code/journal_wifi.md`, 48 sections au moment d'écrire). Ses mesures sont prises pour des faits ; ses jugements sont repris un par un. Tout ce qui suit porte une de ces quatre étiquettes :

- **mesuré** : lu dans un enregistrement de `mesures/` fait sur le robot ;
- **rejoué** : calcul refait sur ces enregistrements, sans le robot ;
- **simulé** : essai dans `code/outils/simulateur.py`, plus indulgent que la réalité ;
- **supposé** : raisonnement ou lecture du code, pas encore vérifié.

Scripts et résultats : `research_notes/Roomba 694 sensor exploitation ideas/data_analysis/`, fichiers `audit_commun.py`, `x_budget_temps.py`, `y_cap_gyro_tours.py`, `z_estime_boucles.py`, `za_rejeu_cap.py`, `zb_carte_coherente.py`, `zd_contacts.py`, `ze_accostage.py`, `zf_inclinaison_gyro.py` et leurs `results_…_20261114.txt` (le fichier `y_silences_robot.py` du même dossier est celui de la session de navigation). Prototype : `code/outils/suivi_lateral.py` et `code/outils/essai_suivi_lateral.py`.

## En bref

1. **Le robot n'avance que 17 % du temps** (mesuré, trajet base → C28 → base du 14, 22,9 min). Il est à l'arrêt 49 % du temps, en tour sur place 21 %, en rotation pour viser ou regarder 12 %. Roulé sans s'arrêter, le même chemin prendrait 4,2 min.
2. **Les roues et le gyroscope comptent mieux qu'on ne le croyait** (rejoué) : 20 boucles de 3 à 25 m se referment à 22 mm en médiane avec la bonne échelle du gyroscope, 70 mm avec l'échelle fixe 1,0045, 304 mm sans échelle.
3. **C'est la carte qui n'est pas cohérente, pas le calcul** (rejoué) : d'un tour au suivant, les positions retenues par le programme contredisent le chemin compté de 73 mm en médiane. Une fois les repères reliés entre eux par ce chemin compté, il reste 18 mm. Sur le trajet du 14, que cette carte n'a jamais vu, l'écart à chaque arrivée passe de 124 à 79 mm en médiane, et de 270 à 122 mm pour le pire dixième.
4. **Le gyroscope est monté penché de 4 à 7°, et le cerveau ne lit qu'un de ses trois axes** (mesuré pour l'inclinaison, lu dans le code pour l'axe unique). L'échelle moyenne qu'il faut lui appliquer, 1,0049, est celle que cette inclinaison prévoit, 1,0047. Le rapport de départ l'avait prévu et donné le remède (fiche 2.B) ; il n'a pas été appliqué.
5. **Ce qui limite maintenant, c'est le cap**, connu à 2° près à chaque tour : 6 cm de travers après 1,8 m. Tant qu'il n'est pas meilleur, espacer les tours coûte cher : 22 cm d'écart en médiane entre 3 et 5 m (rejoué). La proposition « moins de tours » de la session de navigation doit attendre.
6. **Les 18 contacts en roulant ont tous eu lieu en ligne droite, capteur de distance sans rien à moins de 39 cm** (mesuré) : les objets touchés sont devant les côtés du robot, hors du faisceau. Les capteurs optiques du pare-chocs en avaient annoncé 5 sur 18, 0,9 s avant en médiane.
7. **Devant la base, le robot touche quelque chose au même endroit les deux jours** (mesuré) : pare-chocs gauche, à 72 puis 51 cm de la base le 13, à 74, 62 puis 52 cm le 14. Le 13 l'accostage a réussi malgré cela, le 14 non.
8. **Un couloir de 3,9 m passe en 28 à 41 s sans arrêt, contre 169 s par arrêts et 319 s à la main** (simulé), si le robot lit une distance de chaque côté en roulant. Cela demande un petit changement de montage et un petit changement du firmware.
9. **Le défaut trouvé le 14 après-midi par la session de navigation passe avant tout le reste** : le cerveau attend le réseau dans la boucle même qui surveille le pare-chocs. Lu dans le code, je le confirme (§ 2.5).

## 1. Ce que j'ai lu, et ce que je n'ai pas lu

Lu : `AVANCEMENT.md` (en entier, y compris « La suite que je propose », avant d'avoir fait mon classement : je le signale, le brief demandait de la garder pour la fin), `code/README.md`, les sections 45 à 48 du journal, les titres des autres, `outils/localiser.py`, `carto.py`, `reperes.py`, `pilote.py`, `simulateur.py`, `essai_centrage.py`, des parties d'`explorer3.py`, le firmware (`mouv.ino`, `tour.ino`, la tâche du gyroscope et la boucle principale de `roomba694_wifi.ino`), les résultats `p`, `q`, `s`, `u` de `data_analysis/`, le début du rapport de départ et la note sur le gyroscope de `research_notes/`.

Pas lu : `centrage.py` ligne à ligne, `plan.py`, `web.ino`, `radar.ino` au-delà de ses réglages, les sections 1 à 44 du journal au-delà de leurs titres, le plan de l'appartement (aucun de mes scripts ne l'ouvre). Je n'ai donc pas d'avis sur le planificateur de chemins.

## 2. Diagnostic chiffré

### 2.1 Où part le temps

Trajet base → C28 → base du 14 (`exploration19`), de 9 h 05 min 15 à 9 h 28 min 08. Script `x_budget_temps.py` : chaque ligne du journal (20 par seconde) est classée d'après les compteurs des roues ; les tours sur place sont repris de la console du cerveau. **Mesuré.**

| | Tout le trajet (1 373 s) | Six tronçons menés par `explorer3.py` (610 s) | Trois passages menés pas à pas (603 s) |
|---|---|---|---|
| Chemin | 30,3 m | 24,6 m | 5,7 m |
| Vitesse moyenne | 22 mm/s | 40 mm/s | 9 mm/s |
| Avancer | 17,5 % | 28,9 % | 10,7 % |
| Tours sur place | 20,7 % | 44,5 % | 0,8 % |
| Autres rotations | 12,0 % | 7,8 % | 19,3 % |
| À l'arrêt | 49,0 % | 17,3 % | 68,9 % |
| Reculs | 0,7 % | 1,6 % | 0 % |

Le reste du trajet, 160 s (11,7 %), se passe entre deux tronçons : relancer un outil, donner le départ du suivant.

Les arrêts du trajet entier, rangés par durée :

| Durée d'un arrêt | Nombre | Temps | Part du trajet | Ce que c'est |
|---|---|---|---|---|
| moins de 1,5 s | 167 | 148 s | 10,8 % | l'enchaînement de deux ordres (0,9 s chaque fois) |
| 1,5 à 5 s | 46 | 120 s | 8,7 % | lectures à l'arrêt, attentes prévues par les outils |
| 5 à 30 s | 14 | 228 s | 16,6 % | la session réfléchit entre deux ordres d'un passage |
| plus de 30 s | 3 | 179 s | 13,0 % | relance d'un programme |

Autres chiffres du même trajet : 23 tours sur place de 12,3 s chacun ; 57 ordres d'avance de 505 mm en moyenne, à 121 mm/s ; 138 ordres de rotation, dont 47 de moins de 3°. À 121 mm/s sans arrêt, les 30,3 m prendraient 250 s.

**Ce que cela dit.** La vitesse des roues n'est pas ce qui limite. Trois choses mangent le temps, dans cet ordre : la session elle-même, quand elle mène un passage ordre par ordre (30 % du trajet à attendre, plus 12 % à relancer des outils) ; les tours sur place (21 %) ; l'arrêt complet entre deux ordres (11 %). D'où vient la petite seconde entre deux ordres : `Pilote._mouvement` attend sept lignes sans mouvement (0,35 s), `explorer3.tourner_vers` dort 0,3 s, et la vitesse se règle par une requête à part.

Pour comparer, le premier aller-retour du 13 (`exploration14`) : 43,8 min, 10,6 % à avancer, 67,4 % à l'arrêt dont 46 % en arrêts de plus de 30 s.

### 2.2 La position et le cap

**a. L'estime seule referme les boucles à quelques centimètres** (rejoué, `z_estime_boucles.py` et `zf_inclinaison_gyro.py`). Deux tours faits au même endroit se comparent sans le plan : leurs parois communes donnent le vrai décalage (`carto.apparier`), leurs profils le vrai écart de cap. Entre les deux le robot a roulé une boucle, avec ses tours sur place. Refaite avec les seules lignes du journal (chemin compté par le cerveau, cap du gyroscope), cette boucle se referme ainsi, sur 20 boucles du 13 et du 14 (firmware v9 et v10), de 3,2 à 25,4 m, 7,4 m en médiane :

| Échelle du gyroscope | Erreur de fermeture médiane | Trois quarts sous | Pire |
|---|---|---|---|
| la meilleure de chaque boucle | 22 mm | 35 mm | 201 mm (boucle de 25 m) |
| 1,0045 pour toutes | 70 mm | 111 mm | 987 mm (la même) |
| aucune (1,0000) | 304 mm | 354 mm | 1 034 mm |

**b. L'échelle du gyroscope vient de son inclinaison, et elle n'est pas fixe** (mesuré, rejoué, puis lu dans le code).

- Le cerveau compte la rotation sur un seul axe du gyroscope, celui qui voit le plus la gravité (`roomba694_wifi.ino`, `imuTask` : `r = imu.vertSign * imu.gyr[imu.vertAxis]`). Penché d'un angle a, cet axe ne voit que cos(a) de la rotation du robot.
- L'accéléromètre du même module, écrit deux fois par seconde dans `_etat.jsonl`, donne a : **de 4,0 à 7,0° selon les enregistrements**, robot au sol ; 6,9 à 8,2° sur la base. Ce qui prévoit une échelle de 1,0024 à 1,0076.
- Le 13 et le 14 : inclinaison de 4,4 à 5,9° pendant les boucles, échelle prévue 1,0047 en moyenne ; échelle qui referme le mieux les boucles, 1,0049 en moyenne. Les autres jours vont dans le même sens : 4,0 à 4,8° le 10 après-midi (échelle retenue ce jour-là : 1,0015), 5,8 à 6,0° le 10 au soir (1,0045 retenue).
- Par les retours au même endroit (`y_cap_gyro_tours.py`) : à chaque tour sur place le gyroscope compte 382 à 383°, et le robot en a fait 2,3 de plus en moyenne (de 0,1 à 3,8 sur dix paires de tours consécutifs) ; sur les 13 paires du firmware v9 et v10, une seule échelle de 1,0058 ± 0,0004.
- **Ce que l'inclinaison n'explique pas** : d'une boucle à l'autre la meilleure échelle va de 1,0022 à 1,0072 (écart-type 0,0015), et l'inclinaison n'en prévoit presque rien (corrélation +0,29). Une différence entre rotations à gauche et à droite est possible (meilleur couple : 1,0045 à gauche, 1,0080 à droite), mais ce résultat tient à une seule boucle. La session de navigation avait trouvé l'inverse dans le couloir le 14 (1,001 à 1,0025 à droite). **Non tranché : il faut l'essai T2.**
- Ce que cela coûte : 0,0015 d'erreur d'échelle, c'est 0,6° de cap perdu à chaque tour de 380°, toujours dans le même sens puisque tous les tours tournent à gauche. Un degré d'inclinaison de plus change l'échelle de 0,0017.

**c. Les positions retenues à chaque tour ne sont pas cohérentes entre elles** (rejoué, `zb_carte_coherente.py`). Les 97 tours du 13 (firmware v9 et v10) sont reliés de deux façons : 87 liens d'estime d'un tour au suivant (123 m), 162 liens de même lieu entre tours à moins de 35 cm.

| | Positions du programme | Après ajustement d'ensemble |
|---|---|---|
| Estime contre carte, d'un tour au suivant | 73 mm (médiane), 200 mm (neuf dixièmes) | 18 mm, 63 mm |
| Deux tours du même lieu | 57 mm, 225 mm | 7 mm, 16 mm |
| Cap, d'un tour au suivant | 1,3° | 0,4° |

L'ajustement déplace les tours de 78 mm en médiane, 356 mm au plus. Il existe donc des positions qui respectent à la fois l'estime (à 2 cm) et les comparaisons de tours (à 1 cm) : les deux se confirment l'une l'autre. Ce sont les positions posées sur le plan par le filtre qui s'en écartent.

Exemple qui se répète (`za_rejeu_cap.py`, écart en long à l'arrivée) : en arrivant en G12 depuis le nord, l'estime tombe 90, 96, 115 puis 107 mm avant la position du repère, sur quatre trajets des 13 et 14 ; en repartant de G12, 97 mm trop court vers D15 et 94 mm trop long vers H12. Le repère de G12 est donc posé une dizaine de centimètres trop au sud par rapport à ses voisins : un seul décalage explique les six écarts, ce qu'une erreur de cap ne ferait pas (elle déplace de travers, pas en long). En C28, les 12 cm de travers du 14 ne se laissent pas ranger aussi nettement : repère décalé ou cap faux de 3° au départ de G26, mes chiffres ne tranchent pas.

**D'où vient ce défaut.** `reperes.py` rend les tours d'un même endroit cohérents entre eux, mais chaque groupe « garde en moyenne la position que le filtre lui donnait » : il hérite du plan, juste à 10 ou 20 cm d'une pièce à l'autre (c'est écrit en tête de `localiser.py`). À chaque repère, le robot corrige donc sa position d'une dizaine de centimètres qui ne sont pas une dérive.

**d. Sur un trajet jamais vu** (rejoué). La carte ajustée du 13 est essayée sur le trajet du 14 : chaque tour du 14 est situé sur les repères voisins, puis l'estime prédit le tour suivant.

| Trajets de 1,8 m en médiane, 11 présents des deux côtés | Carte du jour | Carte cohérente |
|---|---|---|
| Écart à l'arrivée, médiane | 124 mm | 79 mm |
| Trois quarts sous | 137 mm | 97 mm |
| Neuf dixièmes sous | 270 mm | 122 mm |
| Tours situés | 14 sur 23 | 17 sur 23 |

Ce qui reste est surtout de travers (65 mm en médiane, contre 31 mm en long) : c'est le cap au départ de chaque trajet, connu à 2° près.

**e. Deux idées qui ne tiennent pas au rejeu.**

- *Tenir le cap au gyroscope sur plusieurs tours, et ne le recaler que doucement.* Sur la carte du jour : aucun gain (120, 113 et 115 mm). Sur la carte cohérente : pire (80 mm avec le cap du tour, 88 mm moyenné sur 3 tours, 103 sur 5, 135 sur 8). Le gyroscope tel qu'il est lu aujourd'hui ne tient pas le cap sur plusieurs tours de 380°.
- *Espacer les tours dès maintenant.* Sur la carte cohérente, écart entre l'estime et la carte selon le chemin roulé depuis le dernier tour utilisé : 55 mm jusqu'à 1,5 m, 71 mm de 1,5 à 3 m, 224 mm de 3 à 5 m, 285 mm de 8 à 12 m. Au-delà de 3 m, le robot ne passerait plus une porte.

**f. De quelle précision a-t-on besoin ?** Le robot fait 34 cm de large. Passage de E22 : 48 cm, soit 7 cm de chaque côté. Passage de la cuisine, D32 à D34 : 55 cm sur le plan. Porte H12 : 62 cm, 14 cm de chaque côté. Couloir de J15 à J17 : 68 cm, 17 cm. Partout ailleurs, 15 à 20 cm suffisent. Le centimètre n'est nécessaire nulle part ; 5 cm le sont à quatre endroits, et là c'est la distance aux parois lue sur place qui compte, pas la position sur la carte.

### 2.3 Les contacts

`zd_contacts.py`, 18 appuis du pare-chocs en roulant sous le firmware v10 (13 et 14, cuisine comprise). **Mesuré.**

- 18 sur 18 en ligne droite, à 132 mm/s en médiane.
- 18 sur 18 avec un capteur de distance qui ne voyait rien à moins de 30 cm (lecture la plus courte : 392 mm). 17 sur 18 d'un seul côté du pare-chocs.
- Le capteur regarde droit devant, dans un faisceau d'une quinzaine de degrés : à 30 cm il couvre 8 cm de chaque côté de l'axe, alors que le robot en occupe 17. Les deux coins avant ne sont surveillés par rien d'autre que le pare-chocs.
- Dans 5 cas sur 18, un capteur optique du pare-chocs dépassait 100 depuis au moins 0,2 s (0,87 s en médiane, soit 96 mm de chemin). C'est le cas du contact de J16 le 14 : capteur gauche à 88 une seconde avant, 216 un quart de seconde avant, 291 au contact. Le pilote ne s'arrête qu'à 400.
- Les 13 autres n'ont été annoncés par rien : objets fins, sombres ou bas (E28 trois fois, E13).

Les contacts viennent donc de deux choses ensemble : une trajectoire décalée de 5 à 15 cm dans un endroit serré (J16 et E28 le 14, d'après le § 45 du journal), et rien qui regarde devant les côtés du robot.

### 2.4 Quitter sa base et y revenir

`ze_accostage.py` remet les deux accostages menés par le robot sur la même règle : la distance qu'il restait jusqu'à la base. **Mesuré.**

| | 13 novembre, réussi | 14 novembre, manqué |
|---|---|---|
| Départ | à 82 cm de la base, dans l'axe | à 118 cm, dans l'axe |
| Contacts en route, pare-chocs gauche | à 72 et 51 cm de la base | à 74, 62 et 52 cm |
| Base touchée | 12,8 s après le départ | 12,7 s |
| Ensuite | un recul, une reprise, posé à 18 s | six autres appuis, arrêt tourné de 105°, 21 cm en arrière |

Le robot touche quelque chose du côté gauche au même endroit les deux jours, à 2 cm près pour le premier et le dernier contact. D'après la place de la base (B16, tournée vers le bas) cet objet est vers C16, tout près de la limite avec C15, puis vers B16 côté B15 : calculé avec `grille.py`, à 10 cm près. La session de navigation avait noté autre chose à l'est de l'axe, au pixel (419, 51). S'il y a un obstacle de chaque côté, la base est au fond d'un passage plus étroit que les zigzags du robot. Le 14, les premiers 41 cm ont été roulés presque droit (cap entre −6 et +5°) et le contact a quand même eu lieu : le côté gauche du passage est à 20 cm de l'axe ou moins.

Pour quitter la base, rien de neuf : le robot ignore les ordres de roues tant que la base est alimentée, il faut le tirer à la main.

### 2.5 Qui décide quoi entre le cerveau et le PC

**Ce qui est bien réparti.** Depuis la v10 le cerveau exécute lui-même une avance ou une rotation bornée, tient le cap, s'arrête au but (1°, 7 mm : mesuré par la session de navigation). Le PC garde le calcul lourd et l'enregistrement. C'est la répartition de la note H.

**Ce qui ne l'est pas.**

1. **La sécurité dépend du réseau** (trouvé le 14 après-midi par la session de navigation, journal § 48 ; je le confirme par la lecture du code). `loop()` appelle à la suite `tcpTick()`, `http.handleClient()`, `ArduinoOTA.handle()`, `wifiTick()`, puis `pollTick()` (lecture des capteurs, réflexe du pare-chocs), `radarTick()`, `tourTick()`, `mouvTick()`. Chaque ligne de la console et du journal part par `TeeOut::write`, qui appelle `tcpClient.write` : une écriture qui attend le réseau suspend la lecture des capteurs et les réflexes. Seuls le gyroscope et le capteur de distance ont leur propre tâche. La note H écrivait le 9 : « le Wi-Fi peut manquer : les réflexes restent dans le cerveau » ; le code ne tient pas cette promesse. Mesuré par elle : 196 mm roulés sans surveillance le 14 à 14 h 44.
2. **Le cap du robot est décidé par le PC à chaque tour** avec une lecture à 2° près, alors que le cerveau a le gyroscope. Le cerveau devrait livrer un cap propre (trois axes, § 2.2 b) ; le PC ne devrait le recaler que sur une référence meilleure que lui (un mur longé).
3. **Le PC ne voit le cerveau qu'à travers un fichier** : le cerveau écrit dans une console TCP, `enregistreur.py` l'écrit dans un CSV, `pilote.py` relit ce CSV. C'est simple et tout est gardé, mais chaque ordre attend sept lignes immobiles avant le suivant (11 % du trajet).
4. **Le centrage dans un passage se fait depuis le PC, robot arrêté.** Se tenir au milieu de deux murs est un réflexe ; il a sa place dans le cerveau, comme la tenue du cap.

### 2.6 La façon de travailler

**Ce qui marche.** Tout est enregistré, sur l'horloge du PC : cet audit a pu être fait sans le robot. Chaque section du journal dit ce qui n'est pas vérifié. Les idées sont essayées en simulation ou par rejeu avant de rouler. Les erreurs sont écrites (cap corrigé à la main, cases annoncées de tête).

**Ce qui coûte.**

- **Aucune vérité extérieure.** La précision est jugée contre le filtre ou contre les repères, qui viennent du même capteur et du même plan. C'est ce qui a laissé passer le décalage de G12 pendant deux jours. Quelques cotes prises au mètre ruban suffiraient (essai T4).
- **Des réglages hérités d'un firmware plus ancien.** L'échelle 1,0045 date du 10 au soir (v8, inclinaison de 5,8°). L'incertitude large du filtre (« 20 mm plus 4 % du chemin, exprès ») a été réglée sur la soirée du 10, avant les mouvements exécutés par le cerveau et le retrait du patinage. Ni l'un ni l'autre n'ont été rejoués depuis la v10.
- **La session dans la boucle.** Dans un passage, chaque ordre attend 15 à 25 s que la session le décide : 30 % du trajet du 14. Le centrage automatique écrit le 14 y répond.
- **Pas de rejeu d'ensemble.** Chaque analyse est un script à part (lettres `a` à `z`). Un seul script qui rejoue tous les enregistrements après chaque changement du filtre ou des repères dirait tout de suite si l'on a gagné ou perdu.
- **Les gestes demandés à l'utilisateur à chaque séance** : tirer le robot de sa base, rebrancher le cerveau, le poser sur sa base à la fin. L'alimentation du cerveau par le robot (abaisseur prévu note F) en supprimerait un, et lèverait le doute sur l'alimentation évoqué au § 48 du journal.

### 2.7 Ce que l'utilisateur voit et commande depuis son téléphone

Deux pages aujourd'hui. Le tableau de bord du cerveau (`pages.h`) : une trentaine de boutons (flèches, modes, radar, tour sur place, « Nettoyer », « Base », « Éteindre »…), 78 éléments, pensé pour piloter à la main le 9 novembre. La carte vivante (`code/carte_vivante/`) : lecture seule, servie par le PC. Aucune des deux ne dit ce que le robot est en train de faire et pourquoi il est arrêté, ni ne permet de dire « va là ».

Ce qu'il faudrait, sans que j'aie rien construit (ce n'est pas mon rôle ici) :

- **Une seule page, celle de la carte**, parce que c'est elle qui parle sa langue (les cases).
- **Un bouton d'arrêt toujours visible, qui parle au cerveau sans passer par le PC** (`/api/cmd?c=5`), pour qu'il marche même si le PC est occupé ou éteint. Le serveur de la carte peut ainsi rester en lecture seule.
- **Une ligne d'état en mots simples** : où il est (case), ce qu'il fait, pourquoi il s'est arrêté, la batterie, et l'état de la liaison (depuis le § 48, c'est une information de sécurité).
- **« Va en telle case »** en touchant la carte : la page écrit la destination que lit déjà `explorer3.py` (`_CIBLES.json`).
- **« Rentre à la base »** : son appui sur ce bouton est son accord, à chaque fois, ce que la règle du projet demande.
- Le tableau de bord actuel resterait accessible comme page de réglages.

## 3. Ce qui est solide et qu'il faut garder

- **Les mouvements exécutés par le cerveau** (v10). C'est la base de tout le reste.
- **Le chemin compté par les roues et le gyroscope.** Il vaut mieux que l'usage qu'on en fait.
- **La comparaison de deux tours du même endroit** (`carto.apparier`) : 7 mm en médiane une fois la carte ajustée.
- **Le principe du palier** : un mur vu de face donne sa distance à 1 cm près, quelle que soit la largeur du faisceau.
- **L'axe de la base par ses faisceaux** (2 mm).
- **Le retrait du patinage**, vérifié par rejeu ; je m'en sers dans mes scripts sans rien y trouver à redire.
- **Les enregistrements complets**, le journal et ses « non vérifié ».
- **Les règles de sécurité** : mode Safe, 150 mm/s, brosses à l'arrêt, accord pour l'ordre « rentre à la base ». Aucune de mes propositions n'y touche.

## 4. Les faiblesses, classées

| Rang | Faiblesse | Ce qu'elle coûte | Nature |
|---|---|---|---|
| 1 | Le cerveau attend le réseau dans la boucle de sécurité | jusqu'à 1,5 s sans réflexe (2,5 s en tour) : 20 cm une fois | code du cerveau |
| 2 | Le cap : un seul axe du gyroscope, échelle fixe, tours toujours à gauche, cap relu à 2° près à chaque tour | 6 cm de travers par 1,8 m ; interdit d'espacer les tours | code du cerveau, puis du PC |
| 3 | La carte des repères hérite des décalages du plan | 12 cm de correction à chaque repère ; contacts dans les endroits serrés | code du PC |
| 4 | Un seul capteur de distance, tourné vers l'avant, qui oblige à s'arrêter et à pivoter pour regarder | 21 % du temps en tours, 44 % en passages pas à pas ; 13 contacts sur 18 sans aucun avertissement | principe et montage |
| 5 | La session mène elle-même les passages et relance les outils | 42 % du trajet du 14 | façon de mener les essais |
| 6 | Arrêt complet entre deux ordres | 11 % du trajet | code du PC et du cerveau |
| 7 | Quelque chose devant la base | accostage une fois sur deux | à dégager |
| 8 | Aucune vérité extérieure | des erreurs de carte qui durent | façon de travailler |
| 9 | Deux pages au téléphone, aucune ne dit ce que fait le robot | l'utilisateur dépend des messages de la session | interface |

Les capteurs ne sont pas le premier facteur limitant : les rangs 1, 2, 3, 5 et 6 se règlent sans rien acheter. Le rang 4 est le seul qui tienne au matériel, et c'est lui qui borne la vitesse.

## 5. Ce que le rapport de départ prévoyait, et ce qui s'est passé

Le rapport du 10 (`reports/Roomba 694 sensor exploitation ideas.md`) et sa note sur le gyroscope (`research_notes/…/imu_mpu6050.md`) avaient vu juste sur le cap :

| Le rapport disait | Ce qui a été fait | Ce que les mesures disent aujourd'hui |
|---|---|---|
| Fiche 2.B : la rotation se lit en projetant le gyroscope sur la verticale, pas sur un axe ; « 5° d'inclinaison donnent 0,4 % » | non fait ; une échelle fixe a été ajustée à la place | l'inclinaison est de 4 à 7° et l'échelle mesurée est celle qu'elle prévoit |
| Fiche 2.D : une échelle par sens, et alterner le sens des tours pour que les erreurs s'annulent | non fait ; les tours tournent tous à gauche (8 740° le 14) | 0,6° perdu par tour pour 0,0015 d'erreur d'échelle |
| Idée 1 : plusieurs tours dans les deux sens pour régler l'échelle | non fait | essai T2 de cette note |
| Idée 2 : toutes les stations ajustées ensemble sur le PC | fait le 10 (`Carte.ajuster`), puis remplacé par le filtre sur le plan et les repères | l'ajustement d'ensemble ramène 73 mm à 18 mm |
| Idée 3 : lire le cap sur la distance à un mur, capteur tourné de côté en roulant | non fait (servo limité à 30°) ; repris à l'arrêt par `centrage.py` | simulé ici en roulant : axe du passage retrouvé à 0,5° près |
| Suivre un mur avec les capteurs optiques | écarté le 14 : ils ne lisent rien à 13 ou 22 cm | confirmé ; mais ils annoncent 5 contacts sur 18 |

Le projet a pris un raccourci qui a payé vite : un plan fourni par l'utilisateur et un filtre à hypothèses multiples. Ce raccourci a donné des trajets par cases en trois jours. Il a aussi laissé de côté les remèdes du cap, qui sont devenus le facteur limitant.

## 6. Comment d'autres ont résolu le même problème

Recherche sur le web du 14 novembre, faite par un assistant de cette session avec des termes techniques seulement (rien sur l'utilisateur ni son logement). Les numéros renvoient aux sources en fin de section. « Extrait » : lu dans un résultat de recherche, page non ouverte, à relire avant de s'y fier. Je n'ai rouvert aucune de ces pages moi-même.

### 6.1 Les aspirateurs du commerce sans LiDAR ni caméra ne s'arrêtent pas pour regarder

- iRobot écrit que ses Roomba Essentials utilisent des gyroscopes et une roulette optique pour nettoyer en rangées ; les i3 et i5, sans caméra, se guident par des capteurs de sol, dressent une carte temporaire et se recalent sur la base ou sur un mur droit déjà longé [1]. Pour l'i3 : un capteur optique tourné vers le sol, un gyroscope, les compteurs des roues, les contacts ; la base est son seul repère permanent [2].
- Eufy G30 et G40 : un capteur de flux optique sous le robot, associé au gyroscope [3].
- Ces robots ne se situent pas sur un plan connu : ils tiennent la ligne au gyroscope, comptent le chemin aux roues ou au sol, et se recalent sur un mur et sur la base. (Lecture de l'assistant, pas une phrase des sources.)

**Ce que j'en retiens** : c'est la confiance dans l'estime, le cap d'abord et le recalage sur les murs et la base, c'est-à-dire A1, B1 et le cap lu sur les murs.

### 6.2 Se situer en roulant avec peu de distances, c'est fait depuis 1991

- Leonard et Durrant-Whyte (1991) : localisation sur plan connu par les paliers du sonar. Deux réalisations : un véhicule à un sonar tournant, et un robot à six sonars fixes qui se situe en roulant à 30 cm/s environ [4]. Dès qu'il y a un capteur par direction, on ne s'arrête plus.
- Quatre HC-SR04 fixes et un filtre à particules sur plan connu (2018) : meilleure hypothèse entre 8 et 50 cm de la vraie position ; 33 scénarios simulés sur 40 convergent [5].
- Seize distances et l'estime, sur un iRobot Create 3 qui roule (2026) : 3,9 cm d'erreur moyenne dans 20 m², 9,1 cm dans un appartement de 70 m² [6].
- Non trouvé : un Roomba à un seul capteur à ultrasons situé sur un plan connu. Ce que fait ce projet n'a pas d'équivalent publié que la recherche ait vu.

### 6.3 Ce que donne un LiDAR à 360° de ce prix

- Avec la localisation la plus courante (AMCL) et un RPLIDAR A1 sur un Create 3 : 3,4 cm dans 20 m², 6,6 cm dans un appartement de 70 m² [6]. C'est du même ordre que ce que la carte cohérente donne ici à un tour (8 cm d'un tour au suivant), mais en continu, sans arrêt, cap compris.
- RPLIDAR C1 : 12 m de portée (6 m sur du noir), 5 000 points par seconde, 8 à 12 tours par seconde, ±30 mm, 41 mm de haut [7]. LD19 : 12 m, 4 500 points par seconde, 10 tours par seconde, 180 mA sous 5 V [8].
- Un ESP32 sait les lire : la bibliothèque kaiaai/LDS lit sur ESP32 le LD19, le RPLIDAR A1 et le C1 [9] ; un autre projet fait relayer par l'ESP32 les octets bruts du LiDAR vers le PC, et prévient que la liaison se dégrade quand le Wi-Fi est faible [10]. Ce dernier point rejoint le § 48 du journal.

### 6.4 Les petits capteurs de distance à faisceau étroit (temps de vol)

| Capteur | Champ | Portée et précision | Cadence | Source |
|---|---|---|---|---|
| VL53L1X | 27° (15° en zone réduite) | jusqu'à 1,36 m en mode court, ±20 mm | 50 fois par seconde | [11] |
| VL53L4CD | 18° | de 1 mm à 1,2 m | 100 fois par seconde | [12] |
| VL53L5CX | 45° sur 45°, 16 ou 64 zones | 1,3 m sur une surface grise en 64 zones, ±5 % | 15 fois par seconde en 64 zones | [13] |

- Tous démarrent à la même adresse I²C : on les tient en veille par un fil (XSHUT), on les réveille un à un et on change leur adresse, à chaque mise sous tension [14]. Le VL53L5CX recharge 90 ko de programme à chaque démarrage et consomme 100 mA environ [15].
- Un retour d'expérience (extrait) : trois VL53L0X côte à côte pour se mettre parallèle à un mur lisaient 2 cm d'écart entre eux à 30 cm ; il a fallu les étalonner un par un [16].
- Non trouvé : un récit chiffré d'amateur sur le centrage dans un couloir avec ces capteurs. La simulation de cette note n'a donc pas de point de comparaison.

### 6.5 Le gyroscope penché

- La fiche du MPU-6050 donne la part d'une rotation qui passe sur un autre axe quand le capteur est mal orienté : 0,87 % à 0,5°, 1,75 % à 1° [17]. Ce qui manque à l'axe principal en est le complément ; il faut 5,4° pour 0,45 % (calcul).
- Un brevet décrit le cas exact : capteur monté incliné, l'intégration du seul axe vertical perd la part de rotation passée sur les deux autres ; remède : mesurer l'inclinaison à l'accéléromètre et corriger avant d'intégrer [18].
- Une inclinaison donne la même échelle dans les deux sens. Un écart entre gauche et droite ferait plutôt penser à un zéro mal compensé : à 30 °/s, 0,03 °/s de reste font 0,1 % (remarque de l'assistant). Le zéro suivi par le cerveau a bougé de 0,15 °/s pendant la séance du 14 (mesuré, `_etat.jsonl`).
- Fiche du MPU-6050 : échelle à ±3 %, ±2 % de plus en température, non-linéarité 0,2 % [17]. Un autre module (BNO085) annonce 0,5° de dérive de cap par minute sans boussole [19], soit une dizaine de degrés sur un trajet de 23 min : changer de gyroscope ne dispense pas de se recaler sur les murs.

### 6.6 La base

- La spécification du robot donne les codes des faisceaux (161 champ proche, 164 vert, 168 rouge, 172 rouge et vert) et les trois récepteurs [20]. L'algorithme d'accostage d'iRobot n'est décrit nulle part dans ce qui a été lu ; les programmes libres pour Create se contentent de le déclencher [21]. Le Create 3, plus récent, s'aligne puis monte lentement [22].
- **Dégagement demandé par iRobot : 0,5 m de chaque côté et 1,2 m devant, sans table ni chaise, base à plat contre un mur** [23] [24]. C'est la demande déjà faite à l'utilisateur ; les deux accostages montrent qu'elle n'est pas remplie à gauche.

### 6.7 Prix relevés le 14 novembre 2026

Amazon.ca n'a pas répondu à la recherche : aucun prix Amazon ci-dessous, alors que c'est là que l'utilisateur commande. À revérifier sur la fiche.

| Pièce | Prix relevé | Où |
|---|---|---|
| Fils femelle-femelle de 20 cm, lot de 40 | 2,95 $ (dollars canadiens présumés) | PiShop.ca [25] |
| VL53L1X, un module | 22,20 $ CA ; 24,95 $ | DigiKey.ca [26] ; PiShop.ca [25] |
| VL53L5CX, un module | 35,94 à 48,26 $ CA | DigiKey.ca [27] |
| LiDAR RPLIDAR C1 | 98,57 $ CA | RobotShop Canada [28] (93,99 $ CA sur Amazon.ca le 9, note F) |
| LiDAR LD19 en kit | 149,99 à 170 $ CA | RobotShop Canada [29] (111,13 $ CA sur Amazon.ca le 9, note F) |
| Module BNO085 | 43,81 $ CA | DigiKey.ca [30] |

### Sources

1. https://support.irobot.ca/articles/en_US/Knowledge/31056
2. https://spectrum.ieee.org/irobot-roomba-i3
3. https://service.eufy.com/article-description/What-is-the-Path-Tracking-Sensor-and-how-does-it-work
4. https://manuscript.isc.ac/Inventory/49/1403656.htm (résumé de l'article de 1991, IEEE Transactions on Robotics and Automation 7(3))
5. https://publikationen.bibliothek.kit.edu/1000082750/15098558 (MATEC Web of Conferences 161, 2018)
6. https://arxiv.org/html/2607.17852 (Bilevich, Buber et Halperin, table 1)
7. http://www.slamtec.com/en/c1/spec
8. https://www.waveshare.com/wiki/DTOF_LIDAR_LD19
9. https://github.com/kaiaai/LDS
10. https://github.com/hippo5329/linorobot2_hardware/wiki
11. https://www.pololu.com/file/0J1506/vl53l1x.pdf (fiche ST)
12. https://www.pololu.com/product/3692
13. https://cdn.sparkfun.com/assets/6/e/3/0/6/vl53l5cx-datasheet.pdf
14. https://github.com/pololu/vl53l1x-arduino
15. https://www.sparkfun.com/sparkfun-qwiic-tof-imager-vl53l5cx.html et https://www.pololu.com/product/3417
16. https://community.st.com/t5/imaging-sensors/element-to-element-interference-using-3-element-vl53l0x-array/m-p/89092 (extrait)
17. https://alliance.seas.upenn.edu/~medesign/wiki/uploads/Guides/MPU6050_datasheet.pdf
18. https://patents.google.com/patent/US11079252B2/en
19. https://cdn.sparkfun.com/assets/b/e/e/7/4/BNO080.pdf
20. https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf
21. https://github.com/AutonomyLab/create_robot
22. https://iroboteducation.github.io/create3_docs/api/docking/
23. https://homesupport.irobot.com/articles/en_US/Knowledge/10224
24. https://media-www.canadiantire.ca/manual/product/0438275/0438275p-en-1bbeac25-dbbb-40d3-b276-e5e85936b5a4.pdf (guide du Roomba série 600, page 3)
25. https://www.pishop.ca/search.php?search_query=VL53L1X
26. https://www.digikey.ca/en/products/detail/adafruit-industries-llc/3967/17039169
27. https://www.digikey.ca/en/products/result?keywords=VL53L5CX%20breakout
28. https://ca.robotshop.com/products/slamtec-rplidar-c1-360-dtof-laser-scanner
29. https://ca.robotshop.com/products/hiwonder-ld19-d500-lidar-developer-kit-360-dtof-laser-scanner-supports-ros1-2-raspberry-pi-jetson-nano
30. https://www.digikey.ca/en/products/detail/adafruit-industries-llc/4754/13426653

## 7. Propositions classées

Pour chacune : le principe, le gain attendu et d'où il vient, le coût, le risque, l'essai qui tranche (fiches au § 8).

### 7.0 Avant tout : le cerveau ne doit jamais attendre le réseau (firmware)

- **Principe.** La lecture des capteurs, les réflexes et la conduite d'un mouvement tournent dans une tâche à eux, qui ne touche jamais au réseau. Les lignes du journal passent par une file ; ce qui ne part pas tout de suite est abandonné (ou part en UDP). Roues coupées après 0,3 s sans lecture des capteurs.
- **Gain.** Le réflexe du pare-chocs redevient vrai dans tous les cas. Source : § 48 du journal (trous jusqu'à 5,1 s, 196 mm sans surveillance).
- **Coût.** Firmware : une tâche de plus, une file, deux délais. Aucune pièce.
- **Risque.** Deux tâches qui écrivent sur la même liaison série du robot : n'en laisser qu'une lui parler.
- **Ce que j'ajoute à la proposition de la session de navigation.** Couper les roues plus tôt ne suffit pas si la boucle qui doit le faire est elle-même en attente : il faut d'abord la sortir du réseau.
- **Essai.** T0.

### 7.1 Ce qui se règle dans le code du PC

**A1. Une carte des repères cohérente, reliée par l'estime.** *(prouvée par rejeu ; ma première recommandation pour la position)*
- **Principe.** Tous les tours déjà faits sont reliés entre eux : par le chemin compté d'un tour au suivant, et par la comparaison directe quand ils sont au même endroit. On cherche les positions qui respectent le mieux tous ces liens ; le plan ne sert plus qu'à tenir l'ensemble en place, à 15 cm près. C'est la carte du robot qui fait foi, le plan devient le fond du dessin.
- **Gain.** Sur le trajet du 14, jamais vu : écart à chaque arrivée de 124 à 79 mm en médiane, de 270 à 122 mm pour le pire dixième ; 17 tours situés au lieu de 14. Rejoué, `zb_carte_coherente.py`.
- **Coût.** PC : la fabrication des repères (`reperes.py`) est à refaire sur ce modèle, 200 lignes, 4 s de calcul pour 97 tours. Rien dans le cerveau.
- **Risque.** Faible : la carte se fabrique hors ligne et se compare à l'ancienne avant de servir. Le chemin tracé sur le plan et la carte du robot peuvent alors différer de 10 à 30 cm par endroits : il faudra déplacer les obstacles et les voies avec les repères.
- **Essai.** T3.

**A2. Une seule commande qui enchaîne tout, et plus d'attente entre deux ordres.**
- **Principe.** Un programme donne à la suite les tronçons, les passages et les relances ; la vitesse voyage avec l'ordre ; on n'attend plus sept lignes immobiles quand le cerveau a déjà dit « terminé ».
- **Gain.** Jusqu'à 160 s (relances) et 60 s (103 enchaînements ramenés de 0,9 à 0,3 s) sur 1 373 s. Mesuré pour le temps perdu, supposé pour la part récupérable.
- **Coût.** PC. C'est aussi le point 4 de la suite de la session de navigation ; je le mettrais plus tôt.
- **Risque.** Un enchaînement sans regard humain dans les passages : à ne faire qu'une fois T0 passé.

**A3. Le centrage automatique déjà écrit (`centrage.py`).** Je n'ai rien à y changer. Deux remarques. Il garde le principe « s'arrêter, pivoter, regarder » : 169 s simulées pour 3,9 m, soit 23 mm/s. Et le cap qu'il lit sur les murs (`CAP_MURS`) est la meilleure référence de cap du projet : il devrait recaler le cap du robot à la sortie d'un couloir, ce qui n'est pas encore fait. Le 14, après le couloir, la position devant la porte H12 était fausse de 14 cm.

**A4. Ralentir sur les capteurs optiques de côté.**
- **Principe.** Quand un capteur optique du pare-chocs dépasse 100, le robot passe à 60 mm/s et s'écarte de 5° ; à 200, il s'arrête.
- **Gain.** 5 contacts sur 18 annoncés, 96 mm avant en médiane ; le contact de J16 du 14 en fait partie. Rejoué, `zd_contacts.py`.
- **Coût.** PC d'abord (seuil de `Pilote.alarme`), mieux dans le cerveau ensuite.
- **Risque.** Arrêts pour rien le long d'un mur clair : c'est l'essai T5 qui donne le bon seuil.

**A5. Rejouer tous les enregistrements après chaque changement** (un script), et **prendre quelques cotes au mètre ruban** (T4). Coût : une heure et dix minutes de l'utilisateur.

**À ne pas faire maintenant** (rejoué, § 2.2 e) : tenir le cap au gyroscope sur plusieurs tours ; espacer les tours ; faire des tours deux fois plus rapides à cadence de mesure égale (avec une mesure sur deux, un tour ne garde que 4,2 paliers au lieu de 8,1, et 51 % des paires de tours voisins restent comparables).

### 7.2 Ce qui demande de changer le firmware

**B1. Lire le gyroscope sur ses trois axes.** *(ma première recommandation pour le cap)*
- **Principe.** Pendant la seconde de mise à zéro, robot immobile, l'accéléromètre donne la direction de la verticale. La vitesse de rotation du robot est le gyroscope projeté sur cette direction (somme des trois axes pondérés), au lieu de la lecture d'un seul axe.
- **Gain.** L'échelle ne dépend plus de la pente du module ni de celle du sol : aujourd'hui elle va de 1,0024 à 1,0076 selon l'inclinaison (mesuré), elle deviendrait une constante à mesurer une fois. Supposé pour le résultat : la part de la variation que l'inclinaison n'explique pas (§ 2.2 b) restera.
- **Coût.** Une dizaine de lignes dans `imuCalibrate` et `imuTask`. Aucune pièce. Écrire les deux caps côte à côte dans le journal pendant une séance.
- **Risque.** Faible. L'accéléromètre a ses propres décalages (il lit 1,09 g à la verticale) : la verticale mesurée peut être fausse de 2 ou 3°, ce qui laisse une échelle constante à régler, non plus variable.
- **Essai.** T1.

**B2. Une échelle par sens, et des tours qui alternent.**
- **Principe.** Mesurer l'échelle à gauche et à droite (T2). Puis faire tourner un tour sur deux à droite : ce qu'un tour perd, le suivant le rend.
- **Gain.** L'erreur de cap due à l'échelle ne s'accumule plus (0,6° par tour aujourd'hui pour 0,0015). Supposé ; c'est la fiche 2.D du rapport.
- **Coût.** Un paramètre de sens dans `tour.ino`.
- **Risque.** Aucun pour le robot. Les profils des tours à droite sont à lire à l'envers côté PC.

**B3. Retoucher le cap pendant une avance, et enchaîner deux mouvements sans arrêt.**
- **Principe.** Aujourd'hui `/api/mouv` refuse tout ordre tant qu'un mouvement est en cours. Accepter « nouveau cap visé » et « mouvement suivant » pendant l'avance.
- **Gain.** Supprime l'arrêt de 0,9 s entre deux ordres (148 s le 14) et rend possible le suivi d'un mur en roulant (C1, C2).
- **Coût.** `mouv.ino`, une trentaine de lignes.
- **Risque.** Un cap retouché trop fort dans un endroit serré : borner la retouche à 10° comme le prototype.

**B4. Un accostage lent mené par le cerveau.**
- **Principe.** Le robot est déjà dans l'axe à 2 mm près. Il avance droit à 50 mm/s, cap tenu, jusqu'à ce que le robot signale la charge, ou jusqu'au pare-chocs.
- **Gain.** Supposé. Le robot ne zigzague plus (±50° mesurés pendant l'accostage qu'il mène lui-même, jusqu'à 195 mm/s).
- **Coût.** Firmware ou PC. Le mode Safe ne charge pas : repasser en mode passif une fois posé.
- **Risque.** Pousser la base. Le côté gauche du passage est à moins de 20 cm de l'axe (§ 2.4) : même tout droit, il reste 3 cm au mieux tant que rien n'est dégagé.
- **Essai.** T6.

**B5. La mesure brute du capteur de distance et l'angle du servo dans le journal** (déjà proposé au § 47 du journal). Nécessaire à C1.

### 7.3 Ce qui demande une pièce ou un autre montage

**C0. Dégager le devant de la base.** Aucune pièce. L'objet touché deux jours de suite est à gauche en regardant la base, à 50 à 75 cm d'elle. Essai T6.

**C1. Des fils plus longs pour le capteur de distance : le servo jusqu'à 90° de chaque côté.**
- **Principe.** Le capteur regarde à gauche, devant, à droite, devant, pendant que le robot roule. Les regards de côté ne demandent plus de faire pivoter le robot.
- **Gain.** Couloir de 3,9 m en 41 s au lieu de 169 s par arrêts, sans contact sur 75 départs, jeu le plus petit 87 mm (127 en médiane), axe du passage retrouvé à 0,5° près. Simulé, `essai_suivi_lateral.py`. Tient encore avec une lecture de côté sur trois perdue.
- **Coût.** Des fils de 20 à 30 cm : moins de 10 $ (2,95 $ le lot de 40 relevé le 14, § 6.7). Firmware : B3 et B5. PC : le prototype `suivi_lateral.py`. Difficulté : facile, quatre fils à remplacer.
- **Risque.** **C'est un changement de montage : la butée de 30° a été fixée par l'utilisateur, à lui de décider.** Pendant un regard de côté, rien ne regarde devant pendant 0,7 s : 6 cm à 90 mm/s. Le vrai capteur entend une paroi proche très en biais ; le simulateur non.
- **Essai.** T7.

**C2. Deux petits capteurs de distance fixes, tournés vers les côtés.**
- **Principe.** Deux capteurs à faisceau étroit (temps de vol) lisent en permanence la distance à gauche et à droite. Le capteur actuel garde l'avant.
- **Gain.** Couloir de 3,9 m en 28 s, sans contact sur 75 départs, jeu le plus petit 88 à 92 mm, axe retrouvé à 0,5 ou 0,7° près. Tient encore avec un bruit de 15 mm et une lecture sur cinq perdue (jeu le plus petit 3 à 24 mm) ; 1 à 3 contacts sur 75 avec 25 mm de bruit et une lecture sur trois perdue. Simulé.
- **Coût.** Deux modules VL53L1X, 45 à 50 $ CA la paire (22,20 $ pièce relevé le 14, § 6.7), et quelques fils. Ils se branchent sur les deux fils du gyroscope (même liaison I²C), plus un fil pour les distinguer. Firmware : lecture des deux capteurs, B3. Difficulté : moyenne, huit fils sur des rangées déjà occupées par le gyroscope.
- **Risque.** Un faisceau étroit lit mal une surface sombre ou brillante. À essayer à l'arrêt avant d'en dépendre.

**C3. Un LiDAR à 360°.** *(la piste qui change le plus le principe)*
- **Principe.** Un capteur qui tourne dix fois par seconde et donne des milliers de distances tout autour. Le robot se situe en roulant, sur les murs qu'il voit en continu. Plus de tour sur place, plus de regards.
- **Gain.** Les tours (21 % du trajet) et les regards des passages (la plus grande part de leurs 44 %) disparaissent ; le cap se lit sur les murs à chaque instant. C'est déjà la conclusion de la note F du 8 (« la seule voie vers une vraie carte ») ; ce que cette note y ajoute, ce sont les chiffres du temps. Supposé pour le résultat sur ce robot ; d'autres obtiennent 3 à 7 cm en appartement avec ce genre de capteur (§ 6.3).
- **Coût.** La pièce : 94 à 99 $ CA pour un RPLIDAR C1, 111 à 170 $ CA pour un LD19 en kit (§ 6.7 et note F) ; un support au-dessus du robot, un fil de données vers le cerveau, l'alimentation par l'abaisseur déjà prévu. Firmware : relayer les mesures. PC : une nouvelle localisation. Difficulté : moyenne pour le montage, c'est le plus gros travail de programme de cette liste.
- **Risque.** Il voit à sa hauteur seulement (12 cm) : un objet plus bas reste au pare-chocs. Il ajoute de la hauteur au robot. Le débit de données passe par le Wi-Fi, dont on sait depuis le § 48 qu'il décroche.

**C4. Alimenter le cerveau par le robot** (abaisseur déjà choisi note F). Supprime un geste par séance et un suspect du § 48.

### 7.4 Les pistes qui changent le principe

1. **La carte du robot d'abord, le plan ensuite** (A1). Aujourd'hui le plan fait foi et le robot s'y recale ; les mesures disent que le robot est plus juste que le plan.
2. **Le cap d'abord** (B1, B2, puis le cap lu sur les murs). Une position vaut ce que vaut le cap qui l'emmène au point suivant.
3. **Ne plus s'arrêter pour regarder** (C1 ou C2 dans les passages, C3 partout). C'est le seul changement qui fasse passer la moyenne de 22 mm/s vers la vitesse des roues.

### 7.5 Ce que ces propositions feraient du trajet du 14

Estimations à partir du budget mesuré et des simulations ; aucune n'est une mesure.

| Étape | Durée du trajet | D'où vient le chiffre |
|---|---|---|
| Mesuré le 14 | 22,9 min | |
| Une seule commande (A2) | 20 min | 160 s de relances, 60 s d'enchaînements |
| Passages par le centrage automatique (A3) | 15 min | 603 s remplacés par 349 s simulées (§ 47 du journal) |
| Cap corrigé, puis deux fois moins de tours (B1, B2) | 13 min | 135 s ; seulement après T1 et T2 |
| Regards de côté en roulant (C1 ou C2) | 10 min | couloir 28 à 41 s simulées au lieu de 169 |
| LiDAR (C3) | 6 à 7 min | plus de tours ; supposé |
| Sans jamais s'arrêter | 4,2 min | 30,3 m à 121 mm/s |

## 8. Les essais à faire sur le robot

Écrits pour qu'une autre session les mène. Tous en mode Safe, brosses à l'arrêt, sous surveillance.

**T0. Les réflexes tiennent quand le réseau décroche** (après le changement 7.0). Robot sur cales ou dans un espace dégagé de 2 m. Lancer une avance de 1,5 m à 60 mm/s, puis couper le Wi-Fi du PC pendant 5 s. Enregistrer : le compteur de lectures du cerveau, relu après coup par l'USB ou à la reprise du Wi-Fi. **Oui** si aucune lecture des capteurs n'a plus de 0,3 s de retard et si un appui à la main sur le pare-chocs pendant la coupure arrête les roues en moins de 0,3 s. **Non** sinon : ne pas rouler.

**T1. Le gyroscope est-il penché ?** Sans changer le firmware. Un tour sur place à un endroit dégagé ; pendant la rotation, envoyer cinq fois la touche `g` (elle affiche les trois vitesses de rotation). Enregistrer la console. **Oui** (hypothèse confirmée) si les deux axes horizontaux portent ensemble au moins 7 % de la rotation de l'axe vertical (4° d'inclinaison ou plus). Puis, après le changement B1 : cinq tours de suite au même endroit, comparés par `y_cap_gyro_tours.py`. **Oui** si l'écart entre rotation comptée et rotation vraie, corrigé d'une échelle unique, reste sous 0,5° par tour (aujourd'hui 0,1 à 3,8° par tour avant correction, et 1,2° d'écart quadratique restant avec une seule échelle).

**T2. L'échelle à gauche et à droite.** Rotations seulement, 3 minutes. Au même endroit, avec au moins quatre parois visibles : un tour sur place ; puis `rot=-360` une fois, un tour ; `rot=-360` deux fois, un tour ; `rot=-360` trois fois, un tour. Enregistrer normalement. `y_cap_gyro_tours.py` donne les deux échelles. **Oui, une seule échelle suffit** si elles diffèrent de moins de 0,001. **Sinon** deux échelles dans `Estime` et dans le filtre. Refaire sur le sol sombre de la pièce centrale : si l'échelle y change de plus de 0,001, B1 est indispensable.

**T3. La carte cohérente en service.** Fabriquer la carte avec tous les tours du 13 et du 14 ; refaire base → G12 → base deux fois avec elle, tours comme d'habitude. Enregistrer les corrections à chaque tour. **Oui** si la correction médiane à l'arrivée sur un repère passe sous 6 cm (12 aujourd'hui) et si le saut en G12 disparaît.

**T4. Trois cotes au mètre ruban.** L'utilisateur colle trois bouts de ruban au sol sous le centre du robot arrêté sur trois repères (devant la base en D16, en G12, en H12) et mesure les trois distances. **Ce que cela tranche** : laquelle des deux cartes est juste, et de combien le plan est faux entre G12 et ses voisins (10 cm attendus).

**T5. Le seuil des capteurs optiques.** Approcher un mur clair puis un meuble sombre à 100 mm/s sous 20° d'incidence, cinq fois chacun, sans réflexe ajouté. Enregistrer. **Oui** si le capteur du côté dépasse 100 au moins 0,3 s avant le contact dans quatre approches sur cinq du mur clair ; noter ce qu'il en est du meuble sombre.

**T6. L'accostage.** Avec l'accord de l'utilisateur à chaque fois. Avant de rien dégager : une photo du devant de la base, pour savoir ce qui est touché. Après avoir dégagé 50 cm de chaque côté de l'axe sur 1,2 m : trois accostages par l'ordre du robot depuis D16. **Oui** à trois sur trois sans contact en route. Puis, si B4 est écrit : trois accostages lents menés par le cerveau.

**T7. Les regards de côté** (si l'utilisateur accepte C1). D'abord à l'arrêt, dans le couloir en J17 : capteur à +90° puis −90°. **Oui** si chaque lecture est stable à 5 mm et égale à 1 cm près à celle qu'on obtient en faisant pivoter le robot. Ensuite 1 m à 60 mm/s en lisant sans rien commander, et rejouer `suivi_lateral.py` sur l'enregistrement. Seulement après, en boucle fermée.

## 9. Où je diverge de « la suite » de la session de navigation

Sa liste du 14 à 11 h : passages étroits sans aide ; accostage fiable ; aller plus vite avec moins de tours ; « va dans telle pièce » ; la carte vivante. Depuis 15 h elle met en tête les trous de lecture.

- **D'accord** : les trous de lecture d'abord ; le centrage automatique ; dégager la base.
- **J'ajoute avant le reste** : le cap (B1, T1, T2) et la carte cohérente (A1). Ni l'un ni l'autre n'est dans sa liste, et ce sont eux qui répondent à l'ordre fixé par l'utilisateur, la position d'abord.
- **Je retarde** : « moins de tours sur place ». Rejoué, cela coûte 22 cm entre 3 et 5 m tant que le cap n'est pas meilleur.
- **J'avance** : la commande unique. Elle vaut 12 % du trajet et elle retire la session de la boucle.
- **Je pose la question du matériel**, qu'elle ne pose pas : le centrage par arrêts plafonne à 23 mm/s dans un passage. Au-delà, il faut voir sur les côtés en roulant.

## 10. Ce que je n'ai pas pu vérifier

- **Rien n'a roulé.** Tous mes chiffres viennent de rejeux et de simulations.
- **La cause de l'échelle du gyroscope** : l'inclinaison explique la moyenne et les écarts d'un jour à l'autre, pas ceux d'une boucle à l'autre. La différence entre gauche et droite n'est pas tranchée.
- **La vérité des positions** : la carte cohérente accorde l'estime et les tours entre eux ; rien ne dit qu'elle est juste par rapport au sol (T4).
- **La carte cohérente pendant un trajet réel** : le rejeu situe les tours du 14 après coup. Les chemins tracés sur le plan n'ont pas été rejoués avec elle.
- **Le suivi de côté** : simulé dans un seul couloir, avec un simulateur qui n'entend pas les parois en biais. Pas de porte simulée : devant une porte il n'y a pas de mur à suivre, et le prototype ne traite pas ce cas.
- **Ce qu'est l'objet devant la base**, et s'il y en a un de chaque côté.
- **Les prix et les sources du § 6** : relevés par une recherche du 14 que je n'ai pas relue page par page ; aucun prix d'Amazon.ca. À revérifier avant de commander.
- **Le planificateur, `plan.py`, `centrage.py` ligne à ligne, la page du cerveau en service** : non lus ou non essayés.
- **Les trous de lecture** : je confirme le mécanisme par la lecture du code, pas par un essai.
