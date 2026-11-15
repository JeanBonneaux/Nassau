# L — Ce que le robot fait et dit de lui-même (rétro-ingénierie)

Session de revue, 2026-11-14 au soir. Demandes de l'utilisateur, dans l'ordre :

- « Qu'est ce que on pourrait probe pour reverse engeneer le contrôle [ou] le système du robot […] Avant de procéder donne moi une liste de ce que tu suggère et je choisirai » ;
- « Plus dans la catégorie reverse engineering » ;
- « creusons [ce] genre de choses : d'essai d'usine des réparateurs. Peut on reprogrammer des choses DANS le robot ? Jaime bien le 10 » ;
- « oui mais avant ca prepare aussi quelque chose pour trouver les autre commandes et ou ce que tu peux inserer dans le robot par ce port » ;
- « Capteurs seuls pour le moment / Prépare tout pour que demain j'ai juste à brancher / L'autre session pilotera et tu analysera en live pour le reverse engenNERING et la précision possible d'amélioration d'utilisation optimale des capteurs ».

Chaque affirmation dit d'où elle vient : **mesuré** (sur les enregistrements ou sur le PC), **lu** (documentation ou témoignage, avec le modèle concerné), **supposé**. Rien n'a roulé pour cette note et aucun ordre n'a été envoyé au robot.

Les parties « lu » des § 3 et 4 viennent de deux recherches déléguées. J'ai relu moi-même, dans le manuel de service officiel de la série 500, la façon d'entrer dans le mode d'essai, l'avertissement sur le blocage et le tableau des limites. Le reste, je ne l'ai pas rouvert page par page ; les messages du forum robotreviews.com n'ont pu être lus qu'en extraits.

## En bref

1. **On ne peut pas réécrire le programme du robot par sa prise** (lu) : aucun moyen public, aucun programme de rechange connu pour cette famille, et un essai raté le laisserait sans retour possible.
2. **Son programme est le dernier publié** (lu) : la liste d'iRobot pour les 600 et 800 à Wi-Fi s'arrête à la version 3.5.62 de juillet 2020, celle que ton robot annonce.
3. **Ce que la prise permet d'y ranger** (lu) : des suites de notes, le jour et l'heure, des horaires de nettoyage (à ne pas toucher). Rien qui change sa façon de rouler.
4. **Le mode d'essai d'usine** (lu) est décrit en détail pour la série 500 et a été vu sur un 655 et un 690 ; rien pour le 694. Il écrit un bilan sur la prise : bon ou mauvais par contrôle, et les courants des moteurs avec leurs limites. Deux dangers : la variante automatique peut bloquer le robot jusqu'à ce qu'on retire sa batterie, et la combinaison de touches est voisine de la remise à zéro d'usine.
5. **Sondage 10** : le robot a déjà écrit 16 textes dans les enregistrements, dont 12 coupés. Le firmware version 13 les garde en entier.
6. **La sonde** demandée est prête : une route du firmware fermée par une clé, et un outil du PC à trois genres de recherche (numéros de capteurs en lecture seule, écritures documentées, ordres inconnus).
7. **Ordres inconnus** : mon avis était de ne pas les balayer à l'aveugle (gain faible, risque petit mais sans retour). **L'utilisateur a tranché le 14 au soir : « Capteurs seuls pour le moment ».**
8. **Le 15 à 8 h 36 la version 13 est installée**, par le veilleur, dès que l'utilisateur a rebranché le cerveau. Elle garde bien le texte du robot en entier (douze lignes au réveil, dont cinq jamais vues : § 2.5), et ses rotations sont justes à 1,3° près.
9. **La lecture des 256 numéros de capteurs a trouvé des réponses non documentées** : trois groupes (108, 109, 110) et les numéros 128 à 178 (§ 4.8). Vrais capteurs ou restes de mémoire : à trancher en les relisant dans d'autres états.
10. **Pour le lendemain** (§ 7) : un veilleur attend le cerveau et fera seul l'installation, l'écoute et la lecture des numéros de capteurs ; un outil d'analyse en direct suivra le pilotage de la session de navigation.

## 1. Les sondages proposés, et où ils en sont

| N° | Sondage | Ce qu'il apporte | État |
|---|---|---|---|
| 1 | Réveil et sommeil du robot | savoir le réveiller et le rendormir sans y toucher | proposé |
| 2 | Sortir de la base sans les mains | ne plus avoir à tirer le robot à la main | proposé |
| 3 | Ce qui fait retomber le mode Safe | seuils des capteurs de vide, tapis sombres | première mesure le 15, sur un tapis vert foncé (§ 4.9) |
| 4 | Les six capteurs optiques du pare-chocs | une distance de près, sans contact | proposé |
| 5 | La roulette avant | savoir pourquoi son signal est mort | proposé |
| 6 | Réponse du robot à un ordre de roues, arcs, départ et arrêt | rouler plus vite et sans s'arrêter à chaque pivot | proposé |
| 7 | L'accostage par le robot lui-même | réussir « rentre à la base » plus d'une fois sur deux | proposé |
| 8 | Le courant quand le robot force | arrêter une avance avant de patiner | proposé ; l'échelle est maintenant connue (§ 3.3) |
| 9 | Dépouiller les deux retours à la base déjà enregistrés | comme le 7, sans le robot | proposé ; le courant est déjà regardé (§ 5) |
| 10 | Lire en entier ce que le robot écrit | pourquoi il redémarre ou se tait | **choisi** ; préparé, pas encore mené sur le robot (§ 2) |
| 11 | Le Wi-Fi propre au robot | un second moyen de dire « arrête » | proposé |
| 12 | Nos propres balises infrarouges | un repère sûr à chaque porte | proposé |
| 13 | Le mode d'essai d'usine | les limites d'usine des moteurs | creusé sur le papier (§ 3) ; je déconseille de le lancer pour l'instant |
| 14 | Les capteurs sans numéro officiel, les autres ordres | peut-être un capteur de plus ; pour les ordres, sans doute rien | **décidé : capteurs seuls pour le moment** ; lecture prévue dès que le cerveau répond (§ 7) |

## 2. Ce que le robot écrit de lui-même (sondage 10)

### 2.1 Ce que les enregistrements contiennent déjà

**Mesuré** (`data_analysis/rv_textes_robot.py`, 38 consoles enregistrées du 10 au 14 novembre). Le cerveau n'affichait que les 160 premiers caractères de chaque texte : 12 des 16 textes trouvés sont coupés.

| Texte | Fois | Quand |
|---|---|---|
| Texte de réveil : « key-wakeup-any slept for … minutes … seconds », puis une date (2020-05-13), « r3-robot/branches/aero-support:7587 », « CLEAN », « wifi-version: 3.5.62 », un identifiant ; la suite est perdue | 11 | une à trois secondes après une impulsion de réveil envoyée à un robot endormi |
| Ligne de charge : « bat: min … sec … mV … mA … rx-byte … mAH … state 18 mode 5 » | 1 flot | une par seconde, robot sur sa base, liaison fermée |
| « Performing eEEProm transfer » | 2 | le 13 à 14 h 35 min 09, six secondes après l'ordre « rentre à la base » ; le 14 à 14 h 37 min 11, robot immobile, sept secondes après la fin d'un tour sur place |
| « Soft reset! », puis le texte du programme de démarrage (« iRobotBoot V4 Roomba 600-STM32 Bootloader … Version V4.8 ») | 1 | le 14 à 15 h 05 min 46, robot immobile, le cerveau ne lui envoyait que des lectures |

- Le journal (§ 21) lisait « aero-sup… port:7587 » : c'est la console qui coupait le mot en deux. Le texte dit « aero-support:7587 ».
- D'après le journal (§ 20), « min » et « sec » de la ligne de charge comptent depuis le dernier redémarrage du robot. Le sens de « state » et de « mode » n'est pas connu.
- **Mesuré.** Le 14 à 14 h 37 min 11, à l'instant où le robot écrit « Performing eEEProm transfer », ses compteurs de roues avancent de 2 et 3 pas alors qu'il est immobile (gyroscope à zéro, cap inchangé).
- **Mesuré** (`rv_direct.py`, rejeu des enregistrements). Ce n'est pas un cas isolé : les compteurs de roues avancent de 1 à 3 pas, robot immobile, à chaque changement de mode regardé. Mode Safe pris (le 14 à 14 h 35 min 27), mode Safe quitté (14 h 50 min 46 et 16 h 36 min 39), départ de « rentre à la base » (le 13 à 14 h 35 min 03). **Supposé** : le robot met ses moteurs de roues sous tension ou les relâche à ces instants, et il a fait de même à 14 h 37 min 11. Pour la position c'est sans conséquence : un millimètre au plus à chaque fois.
- **Mesuré.** Sur 18 impulsions de réveil, 11 sont suivies du texte de réveil ; le robot répond alors à toutes les lectures des trois minutes suivantes. Les 7 autres ne donnent pas de texte (le robot ne dormait sans doute pas). Une seule est suivie de lectures sans réponse : celle du 14 à 14 h 34 min 40 (six en trois minutes). C'est aussi la séance du tour arrêté pour « rotation trop rapide » (14 h 35 min 51) et du premier « eEEProm transfer » de la journée.
- **Supposé.** Le robot muet après ce réveil, la rotation trop rapide, le « eEEProm transfer » et le redémarrage de 15 h 05 pourraient avoir une même cause du côté du robot. Rien ne le montre encore. Le texte complet, daté, est ce qui manque pour le savoir.
- **Lu** (recherche, témoignages sur d'autres robots). Le texte « Soft reset! » suivi d'une ligne de version est aussi ce qu'écrit un robot Create 2 à processeur STM32. Aucune mention publique de « Performing eEEProm transfer » ni de la branche « aero » n'a été trouvée.

### 2.2 Le firmware version 13 : écrit, compilé, vérifié sur le PC, pas installé

Deux ajouts ; la conduite et les sécurités existantes ne changent pas.

**Premier ajout : le texte du robot gardé en entier.**

- Chaque ligne que le robot écrit est gardée entière, avec l'heure de la carte, dans une mémoire tournante de 4 ko. `/api/texte?depuis=N` la renvoie ; la console l'affiche ligne par ligne.
- Les lignes de charge ne remplissent pas cette mémoire : la dernière est gardée à part (champ `bat` de `/api/state`), et une ligne n'est rangée que si « state » ou « mode » change, ou une fois par minute.
- Un défaut plus ancien est corrigé au passage : un deuxième texte arrivant après un silence, sans octet binaire entre les deux, n'était ni annoncé ni affiché.

**Second ajout : la sonde** (`/api/sonde`), décrite au § 4.3.

**Mesuré sur le PC**, sans le robot : compilation sans erreur, 87 % de la place comme la version 12. Les fonctions nouvelles, recopiées telles quelles du firmware, ont été lancées sur le PC : 22 contrôles pour le texte avec de faux textes, 38 contrôles pour la sonde face à un faux robot. Tous bons.

**Non vérifié** : rien sur la carte ni sur le robot. L'utilisateur a dit oui à l'installation ; elle attend un cerveau qui répond.

### 2.3 L'outil du PC

`data_analysis/rv_ecoute_robot.py` relève ces lignes par HTTP et les range dans `mesures/textes_AAAAMMJJ_HHMMSS.txt` avec l'heure du PC, à côté de ce que le cerveau dit du robot (répond ou non, mode, charge, sur sa base ou non).

- Il ne fait que lire, sauf avec `--touches`. Les seules touches permises ne font tourner aucune roue : `w` (impulsion de réveil), `s` (ouvrir la liaison), `x` (la fermer), `b`, `e`. Il refuse d'en envoyer une si le cerveau dit que le robot bouge.
- Il n'écrit jamais le nom du réseau de la maison ni les longs identifiants.
- Avec un firmware plus ancien il lit la console du cerveau (`/api/log`), texte coupé à 160 caractères.
- **Mesuré** : essayé sur un faux cerveau lancé sur le PC, dans les deux cas (version 13 et version 12).

### 2.4 Ce que je propose de faire avec

**Partie A, robot sur sa base, sans personne à côté** (aucune roue ne peut tourner : sur sa base alimentée le robot ignore les ordres de roues, et l'outil n'en envoie pas). Un quart d'heure.

1. Écouter trois minutes le robot endormi.
2. Une impulsion de réveil : le texte de réveil en entier.
3. Ouvrir la liaison, lire deux minutes, la fermer : les lignes de charge reprennent-elles, avec quels « state » et « mode » ?
4. Le laisser se rendormir : écrit-il quelque chose en s'endormant ?

**Partie B, avec l'utilisateur à côté du robot**, quelques gestes simples, toujours sans rouler.

1. Débrancher puis rebrancher la batterie du cerveau pendant que le robot est réveillé : que reçoit le robot quand le cerveau redémarre, et change-t-il de vitesse de liaison (c'est arrivé : journal § 18) ?
2. Réveiller le robot par son bouton CLEAN plutôt que par l'impulsion : le texte est-il le même ?
3. Soulever le robot, le reposer.
4. Robot posé hors de sa base, immobile, dans les conditions du 14 à 15 h 05 (lectures rapprochées après un réveil par impulsion), une demi-heure : redémarre-t-il encore, et qu'écrit-il juste avant ?

### 2.5 Le 15 au matin : la version 13 sur la carte, et le premier texte entier

**Mesuré sur le robot** (rapport du veilleur `mesures/matin_20261115_083534_rapport.txt`, écoute `mesures/textes_20261115_083630.txt`, console de la séance `exploration26`).

- L'utilisateur rebranche le cerveau à 8 h 35 min 36. Le veilleur le voit onze secondes plus tard, envoie la version 13 en 9,3 s au premier essai, et la carte redémarre dessus à 8 h 36 min 22 (« v13 Nov 14 2026 21:15:18 »). Gyroscope présent et calibré, roues à l'arrêt.
- **La version 13 garde le texte en entier.** Au réveil de 8 h 44 min 46, douze lignes, chacune avec l'heure de la carte, au lieu d'un début coupé à 160 caractères :

  | Ligne | Ce qu'on en comprend |
  |---|---|
  | `key-wakeup-any` | la raison du réveil |
  | `slept for 1 minutes 24 seconds` | la durée du sommeil |
  | `2020-05-13-1928-L` | la date de construction du programme |
  | `r3-robot/branches/aero-support:7587` | sa branche et son numéro de révision |
  | `CLEAN` | sens inconnu (une construction « propre » ? supposé) |
  | `wifi-version: 3.5.62` | la version côté Wi-Fi |
  | `bootloader id: …` | l'identifiant matériel (masqué dans nos fichiers) |
  | `assembly: ningbo-wifi-v2` | **nouveau** : le nom de l'assemblage de la carte |
  | `revision: 8` | **nouveau** : sa révision |
  | `flash version: 13` | **nouveau** |
  | `flash info crc passed: 1` | **nouveau** : le contrôle de sa mémoire est bon |
  | `battery-current-zero 252` | **nouveau** : le zéro de sa mesure du courant |

- **Un réveil sans texte.** À 8 h 38, après la nuit, deux impulsions de réveil puis l'ouverture de la liaison : le robot répond, mais n'écrit rien. À 8 h 44, après 1 min 24 s de sommeil, il écrit ses douze lignes. **Supposé** : à 8 h 38 il ne dormait déjà plus (l'utilisateur venait de le manipuler), et le texte n'accompagne qu'un vrai réveil.
- **Il se rendort vite hors de sa base.** Liaison fermée à 8 h 42 min 00 ; d'après son propre texte il s'est endormi vers 8 h 43 min 22, soit 82 secondes plus tard.
- **Pas de ligne de charge** pendant ces huit minutes : le robot n'était pas en charge (état de charge 0, 127 mA tirés, « sur sa base : non »). Les lignes « bat: » ne viennent que robot sur sa base alimentée.
- **Les mouvements de la version 13** (menés par la session de navigation à 8 h 47) : rotations de 88,7°, 179,3° et 89,1° pour 90°, 180° et 90° demandés.

## 3. Le mode d'essai d'usine (sondage 13)

### 3.1 Ce qui est écrit, et pour quel robot

- **Lu, officiel, série 500** (manuel de service de 2007, pages 42 à 46, relues par moi). Robot éteint. Tenir CLEAN et DOCK, puis appuyer sur SPOT : 3 fois pour l'essai automatique, 6 fois pour l'essai manuel, 9 ou 12 fois pour des essais où **le robot roule**. Dans l'essai, DOCK passe au contrôle suivant, SPOT revient au précédent. Pour en sortir : tenir DOCK et SPOT dix secondes.
- **Lu, officiel, série 500.** En manuel le robot ne juge rien et n'avance pas tout seul. En automatique il décide bon ou mauvais à chaque contrôle.
- **Lu, témoignages, série 600** (forum robotreviews.com, lus en extraits seulement). Un 655 y est entré par six appuis ; un 690 de 2017 a donné un bilan par sa prise ; une réponse de 2018 dit que les touches du manuel marchent sur ces modèles et conseille le manuel, pas l'automatique.
- **Rien trouvé** pour un 694, un 692, un 675, ni pour le programme 3.5.x de 2020. Aucun manuel de service de la série 600 n'est public.

### 3.2 Ce que le robot écrit pendant l'essai

- **Lu, officiel, série 500.** Un bilan d'environ 75 lignes de texte à 115 200 bauds, envoyé à la fin de l'essai et renvoyé quand on appuie sur CLEAN. Un en-tête (date du programme, identifiant, révision de la carte), puis une ligne par contrôle : bon ou mauvais. Pour les moteurs et la charge s'ajoutent le courant mesuré, son minimum et son maximum.
- Il n'y a **aucune valeur brute** des capteurs de vide, du capteur de mur ni des capteurs optiques : bon ou mauvais seulement. Ce mode ne donne donc pas les seuils que cherche le sondage 3.

### 3.3 Les limites d'usine des moteurs (série 500, officiel, relues par moi)

| Moteur | En marche | Bloqué |
|---|---|---|
| Une roue | 75 à 150 mA | 700 à 850 mA |
| Brosse principale | 200 à 500 mA | 1 250 à 1 400 mA |
| Aspiration | 50 à 230 mA | — |
| Brosse latérale | 30 à 120 mA | 440 à 550 mA |

Deux recoupements avec nos mesures :

- **Sondage 8.** Nos roues tirent 135 à 190 mA en roulant au sol. Une roue bloquée en tirerait quatre à cinq fois plus si le 694 ressemble à la série 500 (supposé).
- **Retour à la base.** Les 0,7 A de plus mesurés pendant « rentre à la base » (§ 5) correspondent à la somme de la brosse, de l'aspiration et de la brosse latérale en marche (0,28 à 0,85 A d'après ce tableau). Ce serait donc les trois ensemble (supposé).

### 3.4 Les dangers

- **Blocage** (lu, officiel, série 500). Si un contrôle a échoué à la fin de l'essai, le robot ne s'éteint plus et ne répond plus à aucun bouton tant qu'on n'a pas retiré sa batterie. Sur un 694 la roulette avant n'a pas de capteur qui réponde (sondage 5) : un contrôle au moins échouerait sans doute en automatique (supposé).
- **Écritures définitives** (lu, officiel, série 500). Trois contrôles écrivent dans la mémoire permanente du robot : la « boîte noire », un calibrage des capteurs de vide et l'enregistrement du résultat. Ce que le calibrage change n'est pas documenté.
- **Touches voisines de la remise à zéro** (lu, aide officielle d'iRobot pour les 600 et 800 à Wi-Fi). Tenir DOCK, SPOT et CLEAN ensemble jusqu'au bip remet le robot à zéro. L'entrée dans l'essai tient deux de ces touches et tape la troisième : un appui trop long y ressemble. Et neuf appuis au lieu de six lancent un essai où le robot roule.
- **Le cerveau branché** (lu, témoignage sur un 690). Un module alimenté par la prise a fait échouer le contrôle du courant de repos. Le nôtre a sa propre batterie, ce qui devrait l'éviter (supposé).

### 3.5 Mon avis

Je déconseille de le lancer pour l'instant. Ce qu'il apporterait de plus sûr, les limites de courant des moteurs, est déjà dans le tableau ci-dessus. Ce qu'il risque, un robot bloqué jusqu'au retrait de sa batterie et un calibrage réécrit, ne se rattrape pas depuis le PC. Si l'utilisateur veut tout de même voir ce bilan : la variante manuelle seulement (six appuis), robot hors de sa base, roues dans le vide, la version 13 à l'écoute, et lui qui compte les appuis à voix haute.

## 4. Peut-on reprogrammer des choses dans le robot ? Et la sonde

### 4.1 Son programme principal : non

- **Lu.** Aucun moyen public de réécrire le programme de la carte d'un 500 ou d'un 600 par la prise. Aucune copie de ce programme, aucun programme de rechange, aucun projet qui le modifie n'a été trouvé.
- **Lu, officiel.** Les robots à Wi-Fi se mettent à jour par Internet, robot sur sa base. La liste des versions pour les 600 et 800 à Wi-Fi va de 3.1.0 (2017) à 3.5.62 (15 juillet 2020). Le nôtre annonce 3.5.62 : il n'y a rien de plus récent à recevoir.
- **Lu, officiel.** iRobot fournit un outil de mise à jour par câble pour le robot Create 2, cousin de la série 600, avec deux fichiers chiffrés selon le processeur. Aucun témoignage de son emploi sur un Roomba vendu en magasin. Le texte de réveil du nôtre (« branches/aero-support », version du Wi-Fi) montre un programme d'une autre branche que celle du Create 2 (supposé).
- **Supposé.** Un programme mal écrit dans la carte n'aurait pas de remède connu : aucun fichier de rechange n'existe pour la remettre.
- La voie que les gens suivent quand ils veulent leur propre programme est celle du projet : un ordinateur branché sur la prise, le programme du robot laissé tel quel.

### 4.2 Ce que la prise permet d'y écrire (lu, spécification officielle de la série 600)

| Ordre | Ce qu'il range | Combien de temps |
|---|---|---|
| 140 | quatre suites de 16 notes | non précisé ; un guide dit « jusqu'à l'extinction » |
| 168 | le jour et l'heure | non précisé |
| 167 | des horaires de nettoyage | non précisé. **À ne pas toucher** : le robot partirait nettoyer seul |
| 129 | la vitesse de la liaison | jusqu'à ce que le robot perde son alimentation |
| 139, 162, 164 | l'état des voyants et de l'afficheur | tant que la liaison est ouverte ; le 694 n'a pas d'afficheur |
| 165 | un appui simulé sur ses boutons | l'instant de l'appui |

Aucun ordre documenté n'écrit un réglage de conduite, un calibrage ou un seuil.

### 4.3 Par son Wi-Fi (lu, témoignages sur un 690)

L'application range dans le robot des préférences de nettoyage (deux passages, pause quand le bac est plein, charge économe…), des horaires, son nom, son fuseau horaire, sa langue. Rien de tout cela ne change la vitesse, la réaction au pare-chocs ou au vide, l'accostage, ni ce que fait la prise.

### 4.4 Ce que le robot garde pour lui (lu)

- Une « boîte noire » que le redémarrage n'efface pas : durées de marche, nombre de missions, statistiques de charge, capacité estimée de la batterie, compteurs d'événements, références de courant des moteurs, champs de calibrage (officiel, série 500). Aucun moyen public de la lire.
- La mémoire de la partie Wi-Fi d'un 690 contenait en clair les noms et mots de passe des réseaux Wi-Fi (étude de 2020). À savoir le jour où le robot quitterait la maison.

### 4.5 Les ordres non documentés : ce qu'on en sait (lu)

- Aucune liste publique pour les programmes 3.x. Les bibliothèques n'utilisent que les ordres publiés.
- Deux signaux, lus en extraits de forum et non vérifiés : une suite d'octets commençant par 141 qui mettrait un 500 en mode d'essai d'usine, et le souvenir d'un membre qui aurait rendu son robot inutilisable avec des ordres non documentés, sans détail.

### 4.6 La sonde : ce qui est prêt

**Dans le firmware version 13** : la route `/api/sonde`.

- Elle n'existe que si le fichier `secrets.h` de ce PC définit une clé, et chaque demande doit porter cette clé. Un firmware compilé depuis le dépôt public, sans ce fichier, ne contient pas la route.
- Elle refuse tout pendant que les roues tournent, pendant un tour ou un mouvement.
- Elle refuse toujours, quoi qu'on lui demande : le mode Full, le mode Safe (il se demande par la touche habituelle), les ordres de roues, de brosses, d'aspiration, de nettoyage, de retour à la base, de vitesse de liaison, d'extinction, de flux continu, d'horaires, l'appui simulé sur un bouton, et le Reset.
- Quatre actions :
  - **lire** : seulement des ordres de lecture documentés et complets. Sert à demander au robot des numéros de capteurs que la documentation ne cite pas.
  - **ecrire** : seulement des ordres documentés et complets qui ne font tourner aucun moteur (notes, voyants, jour et heure).
  - **essai** : au plus 12 octets hors de la liste interdite, pour chercher des ordres inconnus. Le cerveau vérifie lui-même, juste avant d'envoyer, que le robot répond, que ses **deux roues sont levées** et qu'il n'est ni sur sa base ni sur son chargeur. Après l'écoute il pose une question de contrôle ; sans réponse, le robot attend peut-être la suite d'un ordre, et tout est refusé jusqu'à l'action suivante.
  - **aplomb** : envoie 40 zéros pour finir un ordre resté en attente, puis remet la liaison en mode passif et repose la question de contrôle.
- Pendant une sonde, la lecture périodique des capteurs est suspendue. Ensuite aucun ordre de roues ne repart avant une lecture complète réussie.

**Sur le PC** : `data_analysis/rv_sonde_robot.py`, trois genres de recherche.

| Genre | Ce qu'il fait | Risque | Conditions |
|---|---|---|---|
| `capteurs` | demande les 256 numéros de paquet et note ce qui revient ; la documentation en décrit 63 (52 paquets et 11 groupes) | aucun connu : ce sont des lectures | robot réveillé, liaison ouverte ; il peut rester sur sa base |
| `notes` | range une suite de trois notes ; avec `--jouer`, la fait jouer (le mode Safe est pris puis rendu) | un bip | robot réveillé |
| `commandes` | essaie des ordres inconnus un par un, compte leurs arguments avec des zéros, compare les capteurs avant et après, relève le texte du robot, s'arrête à la première chose anormale (plus de réponse, moteur qui démarre, roue qui bouge) | **réel** : voir § 4.7 | `--go`, l'utilisateur à côté, robot hors de sa base, posé sur un support, les deux roues dans le vide |

**Mesuré sur le PC**, sans le robot : la route du firmware, recopiée telle quelle, passe 38 contrôles face à un faux robot (clé, ordres incomplets, octets interdits à toute place, roues non levées, robot sur sa base, robot muet, ordre caché qui attend une suite, remise d'aplomb, aucun ordre interdit jamais reçu par le faux robot). L'outil du PC, face à un faux cerveau, trouve un numéro de capteur caché, compte les trois arguments d'un ordre caché et s'arrête quand un ordre caché lance un moteur.

**Non vérifié** : tout ce qui touche au vrai robot. En particulier, la méthode suppose que l'octet zéro seul est sans effet ; l'outil le vérifie en premier et s'arrête sinon.

### 4.7 Mon avis sur ce qu'il faut lancer

- **`capteurs` : oui.** Lecture seule, deux minutes, robot sur sa base. C'est la seule recherche qui peut rapporter quelque chose pour l'objectif (un capteur de plus).
- **`notes` : si la curiosité y est.** Cela montrera ce que le robot garde après un sommeil, et donnerait au robot un bip d'arrivée.
- **`commandes` : je déconseille le balayage à l'aveugle.** Rien de ce qui a été lu ne laisse espérer un ordre caché utile pour rouler ou se repérer. Un ordre inconnu peut effacer un réglage ou bloquer le robot, et le programme du robot ne se remet pas. Si l'utilisateur y tient, une courte liste d'abord : les numéros 130, 147 et 151 à 161, qui sont des ordres connus sur des robots cousins plus anciens.

### 4.8 Le 15 au matin : la lecture des 256 numéros de capteurs

**Mesuré sur le robot** par le veilleur, de 8 h 38 min 34 à 8 h 39 min 19, robot réveillé, liaison ouverte en mode passif, hors de sa base (`mesures/sonde_20261115_083919_capteurs.json`). Lecture seule : l'ordre documenté 142 suivi d'un numéro. Les numéros documentés ont été demandés une fois, les autres trois fois.

| Numéros | Ce que le robot répond |
|---|---|
| Les 63 documentés | 59 répondent comme la documentation le dit. Quatre n'ont rien répondu à leur unique demande (20, 35, 37, 106) ; le 35 avait répondu juste avant, donc ce sont des réponses manquées, pas des paquets absents (à redemander). |
| 59 à 127, hors groupes | deux octets à zéro, toujours |
| **108, 109, 110** | **cinq, trois et sept octets, les mêmes aux trois demandes** : des groupes non documentés. Le 109 rend les valeurs des numéros 134 à 136, le 110 celles des numéros 137 à 143. |
| **128 à 178** | **un ou deux octets chacun, les mêmes aux trois demandes** : par exemple 132 → 58, 135 → 8, 136 → 38, 138 → 110, 177 → 140 |
| 179 à 255 | rien |

- **Ce que cela peut être** (supposé, deux lectures possibles). Soit de vrais paquets ajoutés pour les robots à Wi-Fi et jamais publiés. Soit le programme du robot qui, pour un numéro hors de sa table, lit ce qui se trouve après elle en mémoire : des valeurs fixes sans signification.
- **Comment trancher** : les redemander dans d'autres états (robot qui roule, pare-chocs enfoncé, bouton tenu, sur sa base). Une valeur qui change avec l'état est un capteur. Cela passe par la sonde, qui suspend trois secondes la lecture périodique : jamais pendant un pilotage.
- **Un octet parasite, 177 (B1 en hexadécimal).** Une quarantaine de fois en 45 secondes, un octet isolé est arrivé entre deux réponses, à intervalles assez réguliers. Un autre propriétaire en parle sur un 690. **Supposé** : le robot l'émet de lui-même environ une fois par seconde quand la liaison est ouverte en mode passif. S'il tombe au milieu d'une réponse, il la fausse : ce serait une cause des lectures « brouillées » après un réveil. À mesurer avec les heures, que cette première lecture n'a pas gardées.

### 4.9 Le 15 à 8 h 53 : ce qui fait tomber le mode Safe (première mesure du sondage 3)

**Mesuré sur le robot**, sans l'avoir cherché (séance `exploration26`, vu en direct par `rv_direct.py`). Pendant une rotation de 25° vers la droite, le robot quitte le mode Safe et coupe ses roues de lui-même.

| Heure | Capteur de vide droit | Mode |
|---|---|---|
| 8 h 53 min 45,75 | 1 215 | Safe |
| 45,85 | 418 | Safe |
| 45,95 | 81 | Safe |
| 46,05 | 36 | **passif** |

- Une seconde plus tôt, les capteurs gauche et avant gauche étaient descendus de 2 460 et 2 170 à 1 061, puis remontés.
- **La cause, d'après la photo envoyée par l'utilisateur** : le robot est au bord d'un tapis vert foncé à franges blanches. Les franges et le bord donnent 1 060 à 1 700 ; le poil vert foncé, 36 à 81. Le parquet donne 2 100 à 2 600. Le tapis de C27, le 14, donnait 700 à 1 700 et se laissait franchir.
- **Ce qu'on en tire.** Pour ce robot, un tapis assez sombre est un vide. Le mode Safe a tenu à 418 et à 81 et n'est tombé qu'à la lecture suivante : son seuil est sous 400, peut-être sous 100, avec un dixième de seconde de délai (supposé : une seule chute). Le sondage 3 prévoyait une feuille sombre glissée sous les capteurs ; ce tapis fait le même office.
- **Ce qu'on pourrait en faire** (non décidé). Arrêter les roues depuis le cerveau dès qu'un capteur de vide passe sous 1 000 environ : le premier creux est arrivé 0,8 s avant la chute. Le mode Safe serait gardé, et le bord du tapis deviendrait un repère.

## 5. Deux mesures faites en préparant la liste

- **Mesuré** (`rv_retour_seul.py`). Pendant les deux « rentre à la base » enregistrés, la batterie donne 0,92 à 1,06 A, contre 0,22 à 0,27 A pendant nos avances à vitesse égale, alors que les roues tirent le même courant. Environ 0,7 A partent ailleurs, une seconde après le départ. Le courant des brosses n'était pas enregistré pendant ces retours.
- **Mesuré** (`rv_arret_pivots.py`, note J § 2.3). La documentation dit que les compteurs de roues comptent vers l'avant quand l'ordre est « arrêt ». Sur 820 pivots, les roues s'arrêtent en une lecture et l'erreur fait 0,2 mm au plus.

## 6. Ce que je n'ai pas pu vérifier

- Tout ce qui touche au robot lui-même : la version 13 n'est pas installée, aucune écoute ni aucune sonde n'a eu lieu.
- La compilation du firmware sans le fichier `secrets.h` (donc sans la route de la sonde) : l'essai s'est enlisé plus de vingt minutes et a été arrêté. Avec le fichier, elle passe.
- Le 14 à 20 h 40, 20 h 50, 20 h 52 et 21 h 08, le cerveau ne répondait pas sur le réseau (dernière lecture réussie connue : 18 h 46, par la session de navigation). Cause non cherchée : sa batterie portable est la première chose à regarder.
- Les témoignages du forum robotreviews.com (essai d'usine sur un 655 et un 690, ordres non documentés) : lus en extraits de moteur de recherche, le site refusant les lectures automatiques.

## 7. Pour le lendemain : ce qui est prêt

Demande : « Prépare tout pour que demain j'ai juste à brancher. L'autre session pilotera et tu analysera en live ».

### 7.1 Le veilleur (`data_analysis/rv_matin.py`)

Lancé le 14 à 22 h 45, détaché, pour vingt heures au plus. Il attend que le cerveau réponde sur le réseau, puis :

1. vérifie que rien ne roule et que personne ne pilote ;
2. installe la version 13 (accord donné) et vérifie que la carte redémarre dessus ; seulement sur un cerveau allumé depuis moins de dix minutes, jamais au milieu d'une séance ;
3. écoute le robot huit minutes : endormi, puis deux impulsions de réveil, liaison ouverte, batterie lue, liaison refermée ;
4. pendant que la liaison est ouverte, lit les 256 numéros de capteurs (lecture seule) ;
5. écrit `mesures/matin_AAAAMMJJ_HHMMSS_rapport.txt` et tient à jour `mesures/matin_dernier.txt`, dont la première ligne dit « en attente », « en cours », « fini, bon » ou « fini, avec un échec ».

Il n'envoie aucun ordre de roues ; ses seules touches sont `w`, `s`, `b`, `x`, et il n'en envoie aucune si le robot est en mode Safe ou bouge. Pour l'arrêter : créer `mesures/matin_STOP`.

**Mesuré** : essayé de bout en bout sur un faux cerveau qui apparaît après quelques secondes (attente, écoute, lecture des capteurs, rapport). **Non vérifié** : l'installation elle-même, que le faux cerveau ne sait pas recevoir ; elle reprend la suite d'ordres qui a installé la version 12. Et il ne tourne que si le PC reste allumé.

### 7.2 L'analyse en direct (`data_analysis/rv_direct.py`)

Pendant que la session de navigation pilote, cet outil lit l'enregistrement à mesure qu'il s'écrit (le `_capteurs.csv` le plus récent et sa console) et, avec la version 13, le texte du robot. Il ne parle pas au robot et n'ouvre pas la console du cerveau.

Il signale au fil de l'eau : les roues qui forcent (courant de la batterie à +250 mA sur le repos ou roues à 330 mA pendant 1,5 s, note J § 2.1), un pivot où roues et gyroscope diffèrent de plus de 6°, les trous dans les lectures, le mode Safe qui tombe, les contacts, une roue levée, les compteurs qui avancent à l'arrêt, tout texte du robot. À la fin de chaque avance il compare la distance lue devant au chemin compté par les roues (note J § 2.2). Toutes les cinq minutes il donne un bilan, avec ce que lisent les capteurs optiques du pare-chocs selon la distance (pour le sondage 4).

**Mesuré**, en lui faisant relire trois enregistrements :

| Enregistrement | Ce qu'il retrouve |
|---|---|
| `exploration24` (le 14, seuil de la cuisine) | deux alertes « les roues forcent » à 16 h 19 min 27 et 16 h 19 min 53 ; le pivot de 16 h 20 min 20 où les roues comptent 145° et le gyroscope 86° ; le mode Safe tombé à 16 h 36 min 39 |
| `exploration21` (le 14, début d'après-midi) | les compteurs qui avancent de 2 et 3 pas à 14 h 37 min 11 ; neuf trous de lecture, dont un de 5 s ; un contact ; le mode Safe tombé à 14 h 50 min 46 |
| `exploration13` (le 13, « rentre à la base ») | trois contacts du pare-chocs gauche ; aucune alerte de courant, parce qu'elle ne vaut qu'en mode Safe |

**Mesuré** aussi : le suivi d'un fichier en train de s'écrire, avec un enregistrement recopié par petits paquets pendant l'analyse (lignes coupées en deux comprises). Il retrouve les mêmes alertes. **Non vérifié** : le suivi d'un vrai pilotage, et la lecture du texte du robot sur un vrai cerveau en version 13.

## 8. Sources

- Manuel de service de la série 500 (iRobot, 2007) : [copie en ligne](https://hallaweb.jlab.org/tech/Detectors/public_html/manuals/data_sheets-manuals/G-I/I/irobot/roomba_570.pdf)
- Spécification de l'interface de la série 600, mise à jour en 2021 : [copie en ligne](https://cdn.hackaday.io/files/1835247851890816/2021-04-13_iRobot_Roomba_600_Open_Interface_Spec-3.pdf)
- Versions du programme des 600 et 800 à Wi-Fi : [aide iRobot](https://homesupport.irobot.com/articles/en_US/Knowledge/541)
- Redémarrage et remise à zéro : [aide iRobot, redémarrage](https://homesupport.irobot.com/articles/en_US/Knowledge/9087), [aide iRobot, remise à zéro](https://homesupport.irobot.com/articles/en_US/Knowledge/9047)
- Outil de mise à jour du Create 2 : [iRobotSTEM/CreateDocs](https://github.com/iRobotSTEM/CreateDocs)
- État d'un 690 vu par son Wi-Fi : [dorita980, discussion 71](https://github.com/koalazak/dorita980/issues/71)
- Mémoire d'un 690 : [étude de 2020](https://blog.digital-forensics.it/2020/12/a-journey-into-iot-forensics-episode-4.html)
- Texte de démarrage d'un Create 2 à processeur STM32 : [pycreate2, discussion 12](https://github.com/MomsFriendlyRobotCompany/pycreate2/issues/12)
- Forum robotreviews.com, lu en extraits : sujets 19994 et 20909 (essai d'usine sur un 690), 20950 et 19901 (sur un 655), 12823 et 15138 (ordres non documentés)
