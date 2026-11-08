# (B) Accès physique au port série (Open Interface) du Roomba 694 et des modèles proches : photos et vidéos

Recherche du 2026-11-08. Étiquettes : **[694 confirmé]** = la source nomme ou montre explicitement un 694 ; **[autre modèle: XXX]** = autre modèle ou famille ; **[non confirmé]** = modèle non indiqué, source vague, ou inférence de ma part.
Limites rencontrées : Reddit inaccessible ici (WebSearch refuse le domaine, WebFetch refusé) ; robotreviews.com (fil « inside the iRobot Roomba 690 ») répond 403 ; pages YouTube : seuls le titre et la chaîne sont récupérables (oEmbed), sans date, description ni chapitres.

## 1. Existe-t-il une preuve directe d'un port série sur le 694 ? Où est-il, comment y accéder, et le capot du 694/692/675 diffère-t-il des anciens 600 ?

### Takeaway
Je n'ai trouvé **aucune photo, vidéo ni témoignage montrant le port série d'un Roomba 694**. La meilleure preuve indirecte est le guide iFixit du **Roomba 692** (nov. 2023). Ses photos montrent un **Mini-DIN femelle 7 broches présent (soudé) sur la carte mère** (sérigraphie « R3 MAIN PCB WIFI CD », « (c) 2020 iRobot »). La prise est visible par un trou rond du capot intérieur dès qu'on a déclipsé, avec un outil d'ouverture, le capot supérieur décoratif, qui est d'une seule pièce. BestReviews (mars 2024) décrit les 692 et 694 comme « physically identical ». Il est donc très probable que le 694 ait le même port au même endroit, mais aucune source 694 ne le confirme.

### Cited Findings

**Le 694 lui-même**
- [694 confirmé] iFixit : « The iRobot Roomba 694 was first released in 2020. » et « The 694 model has an updated faceplate, as well as controls. These updates help the Roomba 694 stand out against the 675 model, its predecessor ». La page ne propose que 3 guides (batterie, brosse, filtre), sans guide pour le capot supérieur ni pour la carte mère. Sources : [iFixit Device iRobot Roomba 694](https://www.ifixit.com/Device/iRobot_Roomba_694) ; [API iFixit, catégorie 694](https://www.ifixit.com/api/2.0/wikis/CATEGORY/iRobot_Roomba_694)
- [694 confirmé] Le seul projet GitHub trouvé qui vise le port série d'un 694 n'a encore rien vérifié sur le matériel : « Verify the exact Roomba 694 Open Interface support and connector pinout against authoritative documentation before wiring. » — [chrisgawbill/SmarterRoomba, docs/architecture.md](https://github.com/chrisgawbill/SmarterRoomba/blob/main/docs/architecture.md) (2026, lu via raw.githubusercontent.com)
- [694 confirmé] Un autre projet 694 passe uniquement par le Wi-Fi local, pas par le port : « macOS Python GUI to control a Roomba 694 over **local Wi‑Fi** » — [mikey-dev404/roomba-controller](https://github.com/mikey-dev404/roomba-controller) (2026)

**Le 692, jumeau du 694**
- [autre modèle: 692 + 694] BestReviews (Jmar Gambol, 4 mars 2024) : « Comparing the Roomba 692 and Roomba 694 is like comparing apples to apples: they’re the same robot vacuum. In the BestReviews Testing Lab, we found they are identical in build, construction and capabilities. » ; « The Roomba 692 and 694 are physically identical, with glossy plastic top plates ». Seule différence citée : un filtre AeroVac livré avec le 692 au lieu de deux avec le 694. — [BestReviews, Roomba 692 vs 694](https://bestreviews.com/articles/home/vacuums/roomba-692-vs-694-which-is-best-for-you)
- [autre modèle: 692] Guide iFixit « iRobot Roomba 692 Motherboard Replacement ». Auteur Ruth Oliva, créé le 2023-11-20, modifié le 2023-12-18, difficulté « Moderate », 30 min. Outils listés : « JIS #0 Screwdriver », « Metal Spudger » (le texte des étapes parle, lui, de « Phillips #0/#00 »). — [iFixit guide 167779](https://www.ifixit.com/Guide/iRobot+Roomba+692+Motherboard+Replacement/167779)
  - Étapes 1 à 5 (accès à la carte mère, pas spécifiquement au port) : brosse latérale (vis de 4,0 mm) ; panneau inférieur (« four black 3.5 mm screws ») ; batterie ; pare-chocs (« Remove the ten 13.3 mm screws ... Pull off the outer and inner holders ») ; capteur (« two 7.4 mm screws ... slide out the sensor to free it from the slide bumper »). — même source
  - **Étape 6, capot supérieur** : « Wedge open the top with an opening tool. » / « Wedge the side tabs and middle tabs upward to remove the top lid. » Le capot tient donc par des languettes latérales et centrales, sans vis. — même source
  - Étape 7 : sous ce capot se trouve un capot intérieur vissé (« Ten 9.6 mm screws. / Four 9.4 mm screws. / One 9.5 mm screw. »). Étape 8 : « Lift up the top cover to access the motherboard » puis « five 7.6 mm screws ». Étape 9 : « Unplug the wiring by pulling it outward ». — même source
  - **Photos de l'étape 7** : capot décoratif retiré, capot intérieur encore vissé, étiquette manuscrite « 692 » collée sur le châssis. Une prise ronde à 7 trous (Mini-DIN femelle) se voit par un trou rond du capot intérieur, près de son bord extérieur, à côté d'une pastille autocollante orange. C'est mon constat visuel sur les images iFixit : [étape 7, photo 3](https://guide-images.cdn.ifixit.com/igi/CFNSUZtkgdHAGHho.full), [étape 7, photo 1](https://guide-images.cdn.ifixit.com/igi/olF2UZKdAmM2KKYo.full)
  - **Photo de l'étape 8** (carte mère à nu) : la même prise Mini-DIN 7 broches est soudée dans un coin de la carte, entourée d'une bague de mousse noire. Constat visuel : [étape 8, photo 3](https://guide-images.cdn.ifixit.com/igi/ZIg521yKc3ndRiZx.full)
- [autre modèle: 692] Un utilisateur a câblé un ESP32 sur le port d'un 692, sans succès et sans cause connue : « This should be uploaded to an ESP32 connected to the ROI of a roomba 692 but for some reasons mine isn't working so i stopped working on this project » — [Tejeda009/roomba_firmware, README](https://github.com/Tejeda009/roomba_firmware) (2026)

**Le 690 (génération Wi-Fi précédente)**
- [autre modèle: 690] Josh Gadeken, projet « Roomba RPi », log « Build Recap » du 2021-04-08 : « The two plastic top covers snap into place. The outer silver plastic ring that conceals the Open Interface connector and RPi's serial port and shutdown button is trivially removed by hand. The center black logo and button cover is a little more difficult to remove, but can be done with a plastic spudger. » — [hackaday.io, Build Recap](https://hackaday.io/project/178565-roomba-rpi/log/191478-build-recap)
- [autre modèle: 690] Même source : « This custom connector does not fit through the Open Interface connector hole in the Roomba's top cover, so it uses an inline JST connector, which does fit through the Open Interface chassis hole. » et « There's just enough room underneath the Roomba's motherboard to run the Open Interface wires from the front of the Roomba to the open space where the additional hardware will be installed. » — [hackaday.io, Build Recap](https://hackaday.io/project/178565-roomba-rpi/log/191478-build-recap)
- [autre modèle: 690] Même source : aucune fiche du commerce ne logeait sous le capot. L'auteur a donc fabriqué une fiche « mini-DIN 7 » extra-plate : un disque plastique percé avec des pattes soudées et 4 fils, broches 1+2 (Vpwr) reliées ensemble et 6+7 (GND) reliées ensemble. Citation : « I cut out a small plastic disk that fits right above the Roomba's mini-DIN connector ». — [hackaday.io, Build Recap](https://hackaday.io/project/178565-roomba-rpi/log/191478-build-recap)
- [autre modèle: 690] Projet de 2026 : « the 690 is the Wi-Fi model, and it was not obvious it even still exposed the wired Open Interface -- community reports on the 600-series Wi-Fi units are contradictory. It does » — [KieranK07/roomba-controller, README](https://github.com/KieranK07/roomba-controller). Son document de recherche précise « verified against **your** robot ... on 2026-09-01 » et « 9/9 sensor queries answered on the first attempt » — [docs/RESEARCH.md](https://raw.githubusercontent.com/KieranK07/roomba-controller/main/docs/RESEARCH.md)

**Anciens 600 (655, 632) et spécification officielle**
- [autre modèle: 655] iFixit, « iRobot Roomba 655 Pet Series Internal Faceplate Removal » (2015-02-19) : « Pull up on the silver handle to release the top protectant plastic / Remove the top plastic carefully ». La façade s'enlève donc à la main par la poignée. Sur la photo de l'étape 5 (façade retirée, capot intérieur en place), une prise Mini-DIN 7 trous est visible par un trou du capot intérieur, à droite de l'anneau de commandes. Sources : [iFixit guide 36880](https://www.ifixit.com/Guide/iRobot+Roomba+655+Pet+Series+Internal+Faceplate+Removal/36880) ; [photo de l'étape 5](https://guide-images.cdn.ifixit.com/igi/Eyo5YSYEsHLoxqoi.full) (constat visuel)
- [autre modèle: 632] Simon Jansen, projet « Old Roomba, new tricks », log « Add hardware » du 2022-01-22 : « Behind the right wheel, there is space and it's quite close to the serial connector. » ; « I connected the wires to the mini DIN7 connector by soldering the ends and just jamming them in. » — [hackaday.io, Add hardware](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202540-add-hardware)
- [autre modèle: série 600, modèle non précisé (« 6 series »)] moskovskiy82, forum HA, 2017-08-01 : « Just use cat5 wire dor wiring and stick it into the din slot. And the buck and wifi board go to the niche near the wheel (do not disconnect the power socket from there. Just leave it there) The cover fits nicely » — [forum HA, message 1](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282)
- [autre modèle: 500/600] kg333, 2019-01-07 : sa carte ESP « fits behind the starboard wheel next to the charging plug » — [forum HA, message 96](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/96)
- [autre modèle: 651] vykintasv, 2023-03-25, à propos d'un faux contact possible : « The wires are bent there and some force is used to screw the cover, maybe the solder didn't hold well. » — [forum HA, message 230](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/230)
- [autre modèle: 630] bholden, 2023-05-13 : « I pulled the battery out of the Roomba before I installed the wires in DIN connector. » — [forum HA, message 248](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/248)
- [autre modèle: Create 2 / « Roomba 600 » générique] Spécification « iRobot Create 2 Open Interface (OI) Specification based on the iRobot Roomba 600 », mention « Last Updated September 8, 2015 » : « The Mini-DIN connector is located in the rear right side of Roomba, beneath a snap-away plastic guard. » ; « Note that pins 6 and 7 are towards the outside circumference of Roomba. » ; « Pins 1 and 2 (Vpwr) are connected to the Roomba battery through a 200 mA PTC resettable fuse. » — [Spec OI Create 2 / Roomba 600 (copie hébergée par l'USC)](https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf)
- [autre modèle: 614] iFixit Answers, 2021-07-18. Question : « I don’t see an obvious way to get the cover off. » Réponse (oldturkey03) : « you need to remove the bumper. Then disconnect the ribbon cable from the bumper before you remove it completely. » Il s'agit d'atteindre la carte mère, pas spécifiquement le port. — [iFixit Answers 699525](https://www.ifixit.com/Answers/View/699525/How+do+I+open+the+top+of+the+Roomba)
- [non confirmé] Forum Domoticz francophone (garycooper, 2020-12-01), modèle non précisé : « Le PCB est compatible avec les deux types de montage du port série installé sur le roomba. » Le même auteur fournit le 2020-12-28 un boîtier à imprimer en 3D « pour boitier du module sur les Roombas séries 5xx et 6xx ». — [easydomoticz.com](https://easydomoticz.com/forum/viewtopic.php?t=10733&start=10)

**CONTRADICTION sur l'emplacement**
- Les sources ne décrivent pas le même emplacement. La spec indique « rear right side » [Create 2/600 générique]. Le projet 690 parle de fils qui viennent « from the front of the Roomba » [690]. Le projet 632 place le connecteur « quite close » de l'espace « behind the right wheel » [632]. Sources : spec USC, hackaday Build Recap et hackaday Add hardware ci-dessus.

### Inferences
- [non confirmé] Les 692 et 694 sont décrits comme physiquement identiques, donc la procédure du 692 vaut très probablement pour le 694 : 1) glisser un outil plastique ou une spatule entre le capot brillant d'une pièce et la carrosserie, puis soulever les languettes latérales et centrales ; 2) chercher, près du bord du capot intérieur noir, un trou rond qui laisse voir une prise à 7 trous. Sur les photos du 692, la prise est visible alors que les vis du capot intérieur sont toujours en place. A priori, aucune vis n'est à retirer pour brancher une fiche, si cette fiche passe dans le trou.
- [non confirmé : ma lecture des photos] Deux photos permettent de s'orienter. Sur celle du 690, on voit le dôme du récepteur IR, situé à l'avant, et la carte série RPi « behind the right wheel module ». La carte du 692 a la même implantation que celle du 690 (même coin pour la prise, sérigraphie « R3 MAIN … WIFI » orientée pareil). Sur ces deux robots, la prise semble donc être dans le **quart avant-gauche** (vu de dessus, pare-chocs vers le haut), près du bord. Cela contredit la phrase « rear right side » de la spec de 2015. Sur les anciens 655 et 632, la prise semble plutôt côté droit, vers la roue droite. Hypothèse : l'emplacement a changé avec la carte « R3 MAIN … WIFI » (690, 692). À vérifier à l'œil sur le 694 de l'utilisateur.
- [non confirmé] Le capot diffère selon la génération :
  - 650/655 : façade argentée à poignée, retirée à la main ;
  - 690 : deux pièces, l'anneau argenté s'enlève à la main et le centre noir à la spatule plastique ;
  - 692/694 : capot brillant d'une seule pièce, clipsé, qu'il faut déclipser avec un outil.
  Dans tous les cas, on accède au port en retirant le capot décoratif supérieur.
- [non confirmé] Une fiche Mini-DIN du commerce risque d'empêcher de refermer le capot : il a fallu une fiche extra-plate maison sur le 690, et sur un 651 les fils étaient pliés et comprimés par le capot. Prévoir une fiche basse ou coudée, ou des fils fins enfichés.
- [non confirmé] Risques : les languettes du capot peuvent casser (aucune source ne le chiffre ni ne le décrit pour le 692/694). Il y a aussi un risque de court-circuit sur Vpwr, qui est la tension batterie non régulée protégée par un fusible PTC de 200 mA selon la spec. Retirer la batterie avant de câbler, comme un utilisateur de 630 l'a fait (message HA 248).

### Gaps
- Aucune photo, vidéo ou témoignage montrant le port d'un 694 (ni d'un 675 ou 671) n'a été trouvé, malgré des recherches en anglais et en français : moteur de recherche, forum HA, GitHub, hackaday, iFixit, forums francophones. Reddit n'était pas consultable.
- Le guide iFixit du 692 retire le pare-chocs et la batterie avant le capot. On ne sait donc pas si le capot du 692/694 se déclipse avec le pare-chocs en place.
- Aucune source ne donne le nombre ni la position exacte des clips du capot 692/694, ni ne décrit un risque de casse.
- Aucune source explicite ne situe la prise à l'avant ou à l'arrière, à gauche ou à droite, sur les 690/692/694 (la spec et les photos se contredisent).

## 2. Des 600 (694, 692, 675, 671, 614, 606, 605, 600) seraient-ils dépourvus de connecteur, ou l'auraient-ils caché ou bloqué, ou faudrait-il souder sur des pastilles ?

### Takeaway
Je n'ai trouvé **aucun rapport daté et précis d'un Roomba 600 dont l'emplacement du Mini-DIN serait vide (non peuplé)**, ni pour le 694 ni pour les autres modèles cités. À l'inverse, la présence du port est attestée, par photo ou par usage, sur les 601, 602, 615, 621, 630, 632, 650, 651, 652, 655, 690 et 692. Un projet de 2026 évoque des avis « contradictory » sur les 600 Wi-Fi, sans les citer. La soudure directe sur pastilles n'est documentée que sur un 560 (série 500).

### Cited Findings
- [autre modèle: 600 Wi-Fi (690/675)] « community reports are ambiguous about whether Wi-Fi 600-series units (690/675) retain OI. Yours does » (aucune source n'est citée pour ces « reports ») — [KieranK07, RESEARCH.md](https://raw.githubusercontent.com/KieranK07/roomba-controller/main/docs/RESEARCH.md)
- [autre modèle: 692] Port physiquement présent sur les photos iFixit de 2023 — [iFixit guide 167779](https://www.ifixit.com/Guide/iRobot+Roomba+692+Motherboard+Replacement/167779)
- [autre modèle: 601] bremby, 2022-09-24 : « I don’t know how to check the model, i saw 601 on the bottom label ». Il venait de montrer son montage le 2022-09-23 et partage ensuite son interface ESPHome. — [forum HA, message 174](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/174) ; [message 171](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/171)
- [autre modèle: 630, 615, 652] sreknob, 2022-10-14 : « I just updated a 630, 615 and 652 with the UART component » — [forum HA, message 210](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/210)
- [autre modèle: 602] wburgers, 2022-10-14 : « Maybe I killed his Roomba 602's OI port now » — [forum HA, message 211](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/211)
- [autre modèle: 621] blackmesa, 2018-11-03 : « i got it working with ESP8266 NodeMCU, my Roomba 621 » — [forum HA, message 87](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/87)
- [autre modèle: 650] davidecavestro, 2021-09-16 : « it works with SoftwareSerial on Roomba 650 » — [forum HA, message 124](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/124)
- [autre modèle: 651] vykintasv, 2022-12-19 : « I have an old Roomba 651 ... Now I have it partly working as I can control the Roomba from HA » — [forum HA, message 224](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/224)
- [autre modèle: 632] Port utilisé, avec la bannière firmware obtenue en série — [hackaday.io, Interfacing](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202538-interfacing)
- [autre modèle: 560] MichielioZ, 2022-12-19 : « For people trying to add their ESP inside the Roomba and need solder points instead of using the DIN connector: (used on a Roomba 560; don't trust me, always measure continuity with a multimeter !) ». Sa photo montre des fils soudés sur des pastilles marquées 5 V, Rx, Tx, BRC et GND, à côté du Mini-DIN. — [forum HA, message 225](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/225)

### Inferences
- [non confirmé] Rien n'indique que les 600 récents ou bon marché aient perdu le port : la carte du 692, datée de 2020, l'a encore. L'incertitude porte sur des variantes non documentées (614, 606, 605, 600, 671, 675) et sur le 694 lui-même.

### Gaps
- Pour les 614, 606, 605, 600, 671, 675 et 694, aucune source ne dit si le port est présent ou absent.
- Aucune source ne décrit, sur les cartes 600 récentes, de pastilles de test pouvant remplacer le Mini-DIN.

## 3. Les teardowns montrent-ils d'autres connecteurs ou headers sur la carte mère (UART de debug, programmation, liaison Wi-Fi) ?

### Takeaway
Aucun teardown ne documente de header de debug UART, de connecteur de programmation ni de liaison vers un module Wi-Fi exploitable sur les 694, 692 ou 690. Les seules informations viennent des photos (iFixit pour le 692, hackaday pour le 690). On y voit un microcontrôleur ST (marqué « STM32F103ZDT6 » sur le 692), une empreinte non peuplée « J5 », des rangées de pastilles « J4 », « J9 » et « J10 », des points de test « TPxx » et les connecteurs des faisceaux.

### Cited Findings
- [autre modèle: 692] Lisible sur la photo de l'étape 8 : « R3 MAIN PCB WIFI CD », « (c) 2020 iRobot », puce « STM32F103ZDT6 » (logos ST et ARM), points de test « TP33 », « TP34 », « TP35 », « TP38 », empreinte percée non peuplée marquée « J5 », pastilles « J4 », « J9 », « J10 », zones « GND » et « VBAT ». Constat visuel sur la [photo iFixit, étape 8](https://guide-images.cdn.ifixit.com/igi/ZIg521yKc3ndRiZx.full) ; recadrage enregistré dans images/acces_692_carte_mere_marquages_STM32_J5_ifixit.jpg
- [autre modèle: 692] iFixit entoure en rouge les connecteurs de faisceaux à débrancher (étape 9 : « Unplug the wiring by pulling it outward ») — [iFixit guide 167779](https://www.ifixit.com/Guide/iRobot+Roomba+692+Motherboard+Replacement/167779)
- [autre modèle: 690] Photo hackaday : sérigraphie « R3 MAIN, WIFI PWR… » et « (c) 2018 iRobot », microcontrôleur portant les logos ST et ARM, Mini-DIN dans un coin de la carte — [photo hackaday du 690](https://cdn.hackaday.io/images/8495211617945356184.jpg) (constat visuel)

### Inferences
- [non confirmé] « J5 » pourrait être un connecteur de programmation ou de debug (SWD ?). C'est une pure hypothèse, rien ne le documente. La mention « WIFI » sur la carte principale suggère que le Wi-Fi est intégré à cette carte (inférence).

### Gaps
- Aucune documentation (iFixit, blog, forum) sur la fonction de J5, J9 ou J10, ni sur un éventuel UART de debug des cartes « R3 MAIN … WIFI ».

## 4. Quelles photos et vidéos montrent l'emplacement du port ou un câblage ? (priorité au 694, sinon 692, 690, 655, 632…)

### Takeaway
Je n'ai trouvé **aucune photo ni vidéo d'un 694 ouvert**. J'ai conservé 18 images dans /home/user/Nassau/roomba694_recherche/images/ (préfixe « acces_ ») :
- 692 (iFixit) : modèle confirmé par le titre du guide et par l'étiquette « 692 » visible sur les photos ;
- 690 (hackaday) : modèle confirmé par le titre du projet ;
- 655 (iFixit) et 632 (hackaday) ;
- 560 (forum HA) ;
- une miniature YouTube de modèle inconnu.
Chaque image a été contrôlée avec `file` puis regardée.

### Cited Findings

**Images conservées** (chaque fichier vérifié avec `file` puis visualisé)

| fichier | URL directe de l'image | page d'origine | ce qu'elle montre | modèle montré | modèle confirmé ? |
|---|---|---|---|---|---|
| acces_692_retrait_capot_spatule_ifixit.jpg | https://guide-images.cdn.ifixit.com/igi/YTPxv12FZV42IOZO.large | [iFixit 167779, étape 6](https://www.ifixit.com/Guide/iRobot+Roomba+692+Motherboard+Replacement/167779) | spatule métallique glissée entre le capot supérieur brillant et la carrosserie pour le déclipser | 692 | oui : guide intitulé « Roomba 692 » ; l'étiquette « 692 » apparaît sur les photos suivantes du même guide |
| acces_692_retrait_capot_spatule2_ifixit.jpg | https://guide-images.cdn.ifixit.com/igi/ovdkXxdf3332MkcN.large | iFixit 167779, étape 6 | spatule insérée sur le côté du capot ; pare-chocs visible | 692 | oui (même raison) |
| acces_692_capot_retire_minidin_visible_ifixit.jpg | https://guide-images.cdn.ifixit.com/igi/CFNSUZtkgdHAGHho.full (réduite à 1600 px) | iFixit 167779, étape 7 | capot décoratif retiré ; prise Mini-DIN 7 trous visible par un trou du capot intérieur (en bas à droite de la photo, à côté d'une pastille orange) | 692 | oui : étiquette manuscrite « 692 » sur la photo + titre du guide |
| acces_692_minidin_gros_plan_trou_chassis_ifixit.jpg | recadrage de CFNSUZtkgdHAGHho.full | iFixit 167779, étape 7 | gros plan de la prise Mini-DIN vue par le trou du capot intérieur | 692 | oui (même photo) |
| acces_692_carte_mere_minidin_ifixit.jpg | https://guide-images.cdn.ifixit.com/igi/ZIg521yKc3ndRiZx.full (réduite) | iFixit 167779, étape 8 | carte mère à nu ; Mini-DIN soudé dans un coin de la carte, avec une bague en mousse | 692 | oui : titre du guide (pas d'étiquette visible sur cette photo) |
| acces_692_carte_mere_marquages_STM32_J5_ifixit.jpg | recadrages de ZIg521yKc3ndRiZx.full | iFixit 167779, étape 8 | « R3 MAIN PCB WIFI CD », « (c) 2020 iRobot », STM32F103ZDT6, J5 non peuplé, TP33 à TP38 | 692 | oui (même photo) |
| acces_690_capots_partiellement_retires_fiche_OI_hackaday.jpg | https://cdn.hackaday.io/images/8201331617161814883.jpg (réduite) | [hackaday.io, Roomba RPi](https://hackaday.io/project/178565-roomba-rpi/log/191478-build-recap) | 690 presque remonté : centre noir et une partie de l'anneau argenté retirés ; fiche OI maison (ruban jaune) sur la gauche ; carte série RPi « GTR » sur la droite | 690 | oui : projet « iRobot Roomba 690 enhanced with a Raspberry Pi Zero 2W and IMU » ; texte du log : « you can see that the Open Interface connector ... can be easily accessed » |
| acces_690_anneau_argent_en_place_centre_retire_hackaday.jpg | https://cdn.hackaday.io/images/757521617161783026.jpg (réduite) | hackaday.io, Roomba RPi | anneau argenté en place, capot central noir retiré | 690 | oui (titre du projet) |
| acces_690_carte_mere_minidin_hackaday.jpg | https://cdn.hackaday.io/images/8495211617945356184.jpg (réduite) | hackaday.io, Build Recap | châssis ouvert ; carte mère avec le Mini-DIN dans un coin | 690 | oui (titre du projet) |
| acces_690_carte_mere_marquage_R3_MAIN_WIFI_2018_hackaday.jpg | recadrage de 8495211617945356184.jpg | hackaday.io, Build Recap | sérigraphie « R3 MAIN, WIFI PWR… » et « (c) 2018 iRobot » | 690 | oui (titre du projet) |
| acces_690_chassis_fiche_dans_minidin_hackaday.jpg | https://cdn.hackaday.io/images/2260291617945628505.jpg (réduite) | hackaday.io, Build Recap | composants ajoutés ; fiche maison enfichée dans le Mini-DIN de la carte | 690 | oui (titre du projet) |
| acces_690_fiche_minidin_basse_maison_hackaday.jpg | https://cdn.hackaday.io/images/9213711617945610618.jpg (réduite) | hackaday.io, Build Recap | fiche « mini-DIN 7 » extra-plate faite maison (4 fils) | 690 (fiche fabriquée pour ce robot) | oui (texte du log) |
| acces_655_retrait_facade_par_poignee_ifixit.jpg | https://guide-images.cdn.ifixit.com/igi/xRvRxsdtsot4HDEq.large | [iFixit 36880, étape 2](https://www.ifixit.com/Guide/iRobot+Roomba+655+Pet+Series+Internal+Faceplate+Removal/36880) | façade argentée (ancien style) soulevée à la main | 655 | oui : guide intitulé « Roomba 655 Pet Series » |
| acces_655_minidin_visible_sous_facade_ifixit.jpg | recadrage de https://guide-images.cdn.ifixit.com/igi/Eyo5YSYEsHLoxqoi.full | iFixit 36880, étape 5 | prise Mini-DIN visible par un trou du capot intérieur une fois la façade retirée (près du bouton CLOCK) | 655 | oui (titre du guide) |
| acces_632_cable_minidin_par_trou_capot_hackaday.jpg | https://cdn.hackaday.io/images/5406971642873762953.jpg (réduite) | [hackaday.io, Add hardware](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202540-add-hardware) | façade retirée ; câble torsadé enfiché dans le Mini-DIN par le trou du capot | 632 | oui : projet « control my Roomba 632 » (pas d'étiquette visible) |
| acces_632_minidin_carte_esp_logement_roue_hackaday.jpg | https://cdn.hackaday.io/images/1344251642872162960.jpg (réduite) | hackaday.io, Add hardware | capot retiré : Mini-DIN sur la carte, petite carte ESP dans la cavité près de la roue | 632 | oui (même projet) |
| acces_560_fils_soudes_pastilles_minidin_HAforum.jpg | https://community-assets.home-assistant.io/original/4X/5/a/8/5a8679e64a873dba9ec7dd01a5caa7df1ffe5688.jpeg | [forum HA, message 225](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/225) | fils soudés sur des pastilles 5V, Rx, Tx, BRC et GND à côté du Mini-DIN | 560 (série 500) | oui d'après le texte du message (« used on a Roomba 560 ») |
| acces_modele_inconnu_cablage_minidin_miniature_youtube_Alizar.jpg | https://i.ytimg.com/vi/Mqzs1bgQc1o/maxresdefault.jpg | [YouTube, « How to hack your Roomba »](https://www.youtube.com/watch?v=Mqzs1bgQc1o) | Roomba sans façade, fils et adaptateur USB-série branchés sur le port | inconnu | non : modèle non indiqué |

**Vidéos repérées** (titre et chaîne via oEmbed ; dates et horodatages non récupérables ; aucune ne concerne explicitement l'ouverture d'un 694, 692 ou 675)
- [autre modèle: série 500/600 générique] https://www.youtube.com/watch?v=szwrgWwf7es — « Roomba 500/600 Series Disassembly » — Justin N. La miniature montre un panneau CLEAN/SPOT/DOCK/CLOCK d'ancien style.
- [autre modèle: série 500/600 ancien style] https://www.youtube.com/watch?v=b3MB6kwl3Qo — « Replacing the Roomba top cover. » — MichaelW_CZ. La miniature montre le retrait d'une façade argentée à poignée.
- [autre modèle: série 500/600 ancien style] https://www.youtube.com/watch?v=pm8BWBI3-0s — « IRobot Roomba How to replace top cover for 500 and 600 series DIY » — IRobot Master.
- [non confirmé] https://www.youtube.com/watch?v=Mqzs1bgQc1o — « How to hack your Roomba » — Alizar. La miniature montre un robot ouvert avec un câblage sur le port ; modèle non indiqué.
- [non confirmé] https://www.youtube.com/watch?v=ClDTvkv74Y0 — « What's inside an iRobot Roomba Vacuum?? Complete disassembly video » — Gage Fixes Everything. Démontage complet ; un extrait de moteur de recherche parle d'un 670, non vérifié.
- [non confirmé] https://www.youtube.com/watch?v=l1mfeHGu9mk — « La desmonté ENTERA para descubrir por qué no cargaba | Roomba paso a paso » — No Lo Tires Bro. Démontage complet en espagnol, modèle non relevé.
- [694 confirmé, sans ouverture connue] https://www.youtube.com/watch?v=dpkZLFHLoKk — « Roomba 694 Full Review & Demo! » — Aphid Reviews.
- [692/694, sans ouverture connue] https://www.youtube.com/watch?v=LJJBkKQB-ec — « Roomba 692 vs. 694: Smart Vacuum Face-off! » — Vacuum Chef.

### Inferences
- [non confirmé] Pour l'utilisateur, les photos du 692 (iFixit) sont la meilleure référence visuelle du 694 : même capot brillant d'une pièce et même génération de carte. Les photos du 690 montrent surtout l'intégration propre d'un câblage sous le capot.

### Gaps
- Aucune vidéo de retrait du capot d'un 692, 694 ou 675 n'a été trouvée. Aucune date ni horodatage de vidéo n'a pu être relevé, les pages YouTube n'étant pas lisibles ici.

## 5. Comment identifier la révision matérielle ou la date de fabrication d'un 694 (si cela compte pour la présence du connecteur) ?

### Takeaway
Aucune source ne relie une révision ou une date de fabrication du 694 à la présence ou à l'absence du port. Trois indices existent : le numéro de série (étiquette sous le bac), l'année sérigraphiée sur la carte (visible une fois le robot ouvert) et la bannière firmware renvoyée par l'OI.

### Cited Findings
- [Roomba générique] Support iRobot, « Where Do I Find the Serial Number? » : « Your Roomba® serial number can be located easily, simply by removing the bin. » — [support.irobot.ca, Knowledge 274](https://support.irobot.ca/articles/en_US/Knowledge/274)
- [autre modèle: 692] La carte porte « (c) 2020 iRobot » — [photo iFixit, étape 8](https://guide-images.cdn.ifixit.com/igi/ZIg521yKc3ndRiZx.full) ; [autre modèle: 690] une carte de 690 porte « (c) 2018 iRobot » — [photo hackaday](https://cdn.hackaday.io/images/8495211617945356184.jpg) (constats visuels)
- [Create 2/600 générique] « To determine the firmware version on your robot, send a 7 via the serial port to reset it. The robot will print a long welcome message which will include the firmware version, for example: r3_robot/tags/release-3.3.0. » — [Spec OI (copie USC)](https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf)
- [autre modèle: 632] Exemple de bannière : « 2012-03-22-1549-L r3_robot/tags/release-3.2.6:4975 » — [hackaday.io, Interfacing](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202538-interfacing)
- [autre modèle: 690] À l'inverse, un 690 n'a renvoyé aucune bannière : « No firmware banner on reset » — [KieranK07, RESEARCH.md](https://raw.githubusercontent.com/KieranK07/roomba-controller/main/docs/RESEARCH.md)

### Inferences
- [non confirmé] Le seul moyen fiable de savoir si un 694 donné a le port est d'ouvrir son capot supérieur et de regarder, puisqu'aucune corrélation numéro de série / révision n'est documentée.

### Gaps
- Aucune source officielle ne décrit le format du numéro de série des 600 ni le moyen d'en déduire la date de fabrication (seuls des articles tiers non vérifiés ont été vus dans les résultats de recherche ; je ne les retiens pas).

## Hors périmètre
- (A, C) Niveaux logiques : le port est en TTL 0–5 V. Sur un 632, un diviseur 2 kΩ/1 kΩ a été utilisé sur RX de l'ESP8266 ; le TX 3,3 V de l'ESP est accepté tel quel par le Roomba. Même projet : « I connected the ESP8266-Tx (orange) to the Roomba's raw battery voltage. So that's one ESP8266 down.. ». Sources : [hackaday, Interfacing](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202538-interfacing) ; [hackaday, Add hardware](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266/log/202540-add-hardware)
- (A) Alimentation : broches 1 et 2 derrière un PTC de 200 mA ; « should not exceed 200 mA », « Do not draw more than 500 mA peak ». — [Spec OI (copie USC)](https://anrg.usc.edu/ee579/spring2016/Roomba/iRobot_Roomba_600_Open_Interface_Spec.pdf)
- (A, E) Sur des 650 récents, une impulsion BRC ne réveille pas le robot sur le dock. Un utilisateur simule l'appui sur CLEAN avec un relais : « The most reliable way I’ve found to make it react again to commands is simulating the push of CLEAN button with a relay. » (650, 2022-02-07) — [forum HA, message 141](https://community.home-assistant.io/t/add-wifi-to-an-older-roomba/23282/141)
- (A) Sur un 690 (2026) : les modes Safe et Full coupent la charge ; le paquet 35 (mode OI) renvoie une valeur décalée de +1 ; pas de bannière firmware ; réveil logiciel impossible avec un câble qui ne sort pas la broche 5 (BRC) : « Your cable does not break out pin 5 (BRC). » — [KieranK07, RESEARCH.md](https://raw.githubusercontent.com/KieranK07/roomba-controller/main/docs/RESEARCH.md)
- (D) 694 en Wi-Fi local : « Wi‑Fi on this model cannot do joystick / WASD driving » ; seules les commandes start, stop, pause, resume et dock sont possibles ; « Roomba **694 does not publish pose or maps** over Wi‑Fi ». — [mikey-dev404/roomba-controller](https://github.com/mikey-dev404/roomba-controller)
- (C) Projets avec photos : Roomba 690 + Raspberry Pi Zero 2W + IMU, ROS2 ([hackaday 178565](https://hackaday.io/project/178565-roomba-rpi)) ; Roomba 632 + ESP8266 + MPU6050, MQTT ([hackaday 183524](https://hackaday.io/project/183524-controll-yer-roomba-600-series-with-esp8266)).
