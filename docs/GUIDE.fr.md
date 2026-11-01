# Dépenses : guide d’installation

Chaque notification d’achat de vos applis bancaires est envoyée par votre iPhone vers une feuille Google qui vous appartient. Le script de la feuille lit les notifications, et le tableau de bord vous montre où va l’argent. En plus, le script lit les courriels d’alerte de vos banques dans Gmail et vous écrit si la capture s’arrête. Rien ne passe par un autre serveur.

**Il vous faut :** un compte Google (Gmail), un iPhone sous iOS 27, et un ordinateur pour la partie A. Comptez 20 minutes.

> **Vous avez déjà installé une version précédente ?** Faites la partie A au complet : c’est la mise à jour. Elle remplace automatiquement l’ancien jeton (celui qui a été partagé par erreur). Dans Raccourcis, vous n’aurez que l’adresse à recoller (partie C, étape 12).

## A. Sur l’ordinateur (10 min) {#ordinateur}

### 1. La feuille et le script

1. Ouvrez [sheets.new](https://sheets.new) pour créer une feuille Google et nommez-la **Dépenses**. (Si vous avez déjà la feuille, ouvrez-la.)
2. Menu **Extensions → Apps Script**. Un onglet s’ouvre avec un fichier `Code.gs`.
3. Cliquez sur **Copier le script** ci-dessous. Dans Apps Script, cliquez dans `Code.gs`, sélectionnez tout (⌘A sur Mac, Ctrl+A sur PC), collez par-dessus, puis enregistrez (⌘S ou Ctrl+S).

{{SCRIPT}}

### 2. Publier

4. En haut à droite : **Déployer → Nouveau déploiement**. Cliquez sur la roue ⚙ à côté de « Sélectionner le type » → **Application Web**. Réglez **Exécuter en tant que : Moi** et **Qui a accès : Tout le monde**, puis **Déployer**.
   « Tout le monde » veut seulement dire « sans connexion Google » : c’est nécessaire pour le raccourci de l’iPhone. Rien ne peut être lu ni écrit sans votre jeton secret.
   *Déjà publié ?* Faites plutôt **Déployer → Gérer les déploiements → ✏️ → Version : Nouvelle version → Déployer**. L’adresse ne change pas.

### 3. Installer

5. Dans la barre du haut, choisissez la fonction **setup** dans la liste, puis **Exécuter**.
6. Google demande une autorisation. Cliquez **Examiner les autorisations**, choisissez votre compte, puis sur l’écran « Google n’a pas validé cette application » : **Paramètres avancés → Accéder à … (non sécurisé) → Autoriser**. C’est normal pour un script personnel : vous autorisez votre propre code.
   Ce que le script demande, et pourquoi : modifier *cette* feuille ; vous envoyer des courriels à vous seul (le résumé du lundi et les alertes) ; lire vos courriels (seulement ceux de vos banques, voir la partie B) ; se lancer tout seul toutes les 15 minutes ; contacter un service externe (uniquement si vous activez Claude un jour, voir plus bas).
7. Revenez à la feuille : un onglet **Configuration** est apparu. Cliquez sur le lien **Ouvrir le tableau de bord**. Il s’ouvre déjà connecté.
   (S’il dit « Déployez d’abord », refaites l’étape 4 puis relancez `setup`.)

## B. Dans vos applis bancaires (5 min) {#banques}

Activez les alertes d’achat. Quand la banque le permet, activez **aussi** le courriel : le script le lit dans Gmail, et c’est le filet qui ne dépend pas du téléphone.

- **Banque Scotia** (appli) : menu profil → **Modifiez le profil et les paramètres → Paramètres de communication → Gérer les notifications** (InfoAlertes). Activez « achat par carte de débit », « achat par carte de crédit dépassant la limite » avec la limite au minimum (**1,00 $**), et « carte utilisée en ligne, par téléphone ou à l’extérieur du Canada ». Mode d’envoi : **notification de l’appli et courriel**. Vérifiez que l’adresse des InfoAlertes est bien votre Gmail.
- **Capital One** : dans l’appli, activez les notifications d’achat approuvé. Puis, dans un **navigateur** (pas dans l’appli), connectez-vous à capitalone.ca → **Alertes** → ✏️ à côté de la carte → cochez « You’ve made a purchase » dans la colonne **courriel**. Les cartes Capital One ne fonctionnent pas avec Apple Pay, et Capital One prévient que certaines transactions n’envoient pas d’alerte : le courriel et la comparaison mensuelle (plus bas) comblent les trous.
- **Wealthsimple** (appli) : Profil → ⚙ → **Notifications → Notifications push** : activez les alertes de carte (crédit, et « Paiements et demandes »). Pas d’alerte par courriel chez Wealthsimple. Un VPN ou un bloqueur de publicité peut bloquer ses notifications : désactivez-le pour tester.
- **Cartes** (Apple Pay) : rien à faire. Un achat reçu deux fois (banque + Cartes) n’est compté qu’une fois.
- **Réglages de l’iPhone → Notifications**, pour chaque appli bancaire et Cartes : *Autoriser les notifications* activé, livraison **immédiate** (pas dans le résumé programmé), **Afficher les aperçus : Toujours**. Dans vos modes de concentration, autorisez ces applis.

## C. Sur l’iPhone (5 min) {#iphone}

### 4. Le tableau de bord

8. Sur l’ordinateur, dans le tableau de bord : ⚙ **Réglages**. Un **code QR** s’affiche.
9. Sur l’iPhone, ouvrez l’**Appareil photo**, visez le code, touchez le lien : Dépenses s’ouvre dans Safari, déjà connecté.
10. Touchez **Partager** (le carré avec une flèche) → **Sur l’écran d’accueil** → **Ajouter**. Ouvrez la nouvelle icône **Dépenses**.
    Si elle s’ouvre sur l’écran d’accueil au lieu de vos données : ⚙ Réglages, collez le lien de configuration (celui de l’onglet Configuration) dans le champ *Adresse*, et enregistrez.
11. Dans Dépenses, carte « Il reste quelques étapes » (ou ⚙ Réglages) : touchez **Copier le lien du raccourci**.

### 5. L’automatisation

12. Ouvrez **Raccourcis**. Si vous avez déjà l’automatisation « Quand je reçois une notification de… », ouvrez-la ; sinon touchez **+**, puis **Automatisation → Notification**.
    - **Apps** : Banque Scotia, Capital One, Wealthsimple, Cartes (toutes dans la même automatisation).
    - **Aucun filtre.**
    - Exécution **immédiate**, sans confirmation. L’exécution quand l’iPhone est verrouillé doit être permise (ⓘ → Confidentialité).
13. Action **Obtenir le contenu de l’URL** (supprimez l’ancienne s’il y en a une) :
    - **URL** : collez le lien copié à l’étape 11.
    - Touchez **›** (afficher plus) : **Méthode : POST**, **Corps de la requête : JSON**.
    - **Ajouter un champ → Texte**, trois fois. Pour chaque champ, tapez la clé, puis touchez la case *Valeur* → **Sélectionner une variable** → la pastille **Notification** (parfois nommée *Entrée du raccourci*) → choisissez la propriété :
      - clé `titre` → **Titre**
      - clé `soustitre` → **Sous-titre**
      - clé `corps` → **Corps**
    - ⚠️ La valeur doit être une **pastille bleue**. Si vous tapez le mot « Titre » vous-même, le serveur le détecte et le tableau de bord vous le dit en rouge.
14. Touchez **OK**, puis **▶** pour tester : dans Dépenses, l’étape « Raccourci relié » passe au vert (touchez ↻ au besoin).

## D. Vérifier (2 min) {#verifier}

15. Payez un petit montant avec chaque carte. Quelques secondes plus tard, l’achat est dans Dépenses (↻). Les achats lus dans vos courriels arrivent en moins de 15 minutes.
16. Rien ? Ouvrez l’onglet **Ignorées** :
    - « Raccourci mal configuré » → refaites l’étape 13 (pastilles bleues).
    - La notification est là mais n’a pas été lue comme un achat → touchez **Ajouter**. Touchez aussi **Copier pour améliorer la lecture** et collez le texte dans votre conversation avec Claude : le lecteur apprendra ce format.
    - Rien du tout → l’automatisation ne s’est pas lancée : revérifiez l’étape 12 et les réglages de notifications (partie B).

## Ensuite, il n’y a rien à faire {#ensuite}

- **Le lundi matin**, un courriel résume la semaine : total, comparaison avec le mois dernier, rythme du budget, abonnements, gros achats, ce qu’il reste à vérifier.
- **Si la capture s’arrête** (rien depuis 3 jours, une banque qui se tait, l’ancien lien encore utilisé), vous recevez un courriel qui dit quoi vérifier. Au plus un par problème par semaine.
- **Corriger une catégorie** : ouvrez l’achat, choisissez la bonne catégorie, laissez « Toujours classer… » coché. Les achats passés et futurs du même marchand suivent.
- **« À vérifier »** : quand une notification est difficile à lire, l’achat est compté mais marqué. Un geste suffit : *C’est bon*, *Doublon* ou *Modifier*.
- **Une fois par mois** (facultatif) : **+ → Relevé**, collez le relevé CSV de chaque carte. Les achats manquants vous sont proposés.
- **Budget** : ⚙ Réglages → Budget mensuel.

## Mise à jour du script {#mise-a-jour}

Quand le tableau de bord signale une mise à jour : refaites l’étape 3 (coller le nouveau script), puis **Déployer → Gérer les déploiements → ✏️ → Version : Nouvelle version → Déployer**, puis **setup → Exécuter**. L’adresse, les jetons et vos données ne changent pas.

## Si un lien a été partagé par erreur {#jetons}

Dans Apps Script, exécutez **rotateToken** (ou `changerJetons`). Les deux jetons changent. Puis : onglet Configuration → Ouvrir le tableau de bord (ordinateur) → ⚙ Réglages → QR vers l’iPhone (étapes 8 à 11), et dans Raccourcis remplacez seulement l’URL (étape 13). Le tableau de bord vous préviendra si le raccourci utilise encore l’ancien lien.

Ne collez jamais un lien de Dépenses dans une conversation ou un courriel : il contient un jeton.

## Claude, pour les formats que les règles ne comprennent pas (facultatif) {#claude}

Les règles intégrées lisent les formats courants. Si une banque change ses textes, Claude peut relire ce que les règles n’ont pas compris, en différé (au plus 15 minutes après), avec les codes et les numéros masqués.

1. Créez une clé sur [console.anthropic.com](https://console.anthropic.com) et ajoutez un peu de crédit.
2. Dans Apps Script : ⚙ **Paramètres du projet → Propriétés du script → Ajouter** : `ANTHROPIC_API_KEY` = votre clé.
3. C’est tout. Au plus 40 lectures par jour et 1 $ US par mois (modifiables avec `CLAUDE_MAX_PER_DAY` et `CLAUDE_MAX_MONTH_USD`). Modèle : `claude-opus-5-5` ; `claude-haiku-5-5` coûte bien moins (propriété `CLAUDE_MODEL`). Pour tout faire lire par Claude : `CLAUDE_MODE` = `always`. Pour arrêter : supprimez la clé.

Sans clé, rien ne sort de Google.

## Vie privée {#vie-privee}

- Vos transactions sont dans votre feuille Google, lisible par vous seul. Le tableau de bord en garde une copie sur votre téléphone pour fonctionner hors ligne.
- L’outil n’a jamais vos identifiants bancaires : il lit des textes de notifications. Même avec un jeton, personne ne peut toucher à votre argent.
- Deux jetons : celui du raccourci peut seulement *ajouter* des notifications ; celui du tableau de bord permet de lire et de corriger. Ils ne sont jamais envoyés par courriel ni par message.
- Les codes de vérification sont masqués avant d’être enregistrés.
- Le script lit dans Gmail seulement les courriels des expéditeurs de vos banques (la recherche est visible dans le code, propriété `EMAIL_QUERY`) et leur ajoute l’étiquette « Depenses ». Pour ne pas lire les courriels : ⚙ Réglages → décochez l’option.
- Ne partagez pas la feuille : son onglet Configuration contient vos liens secrets.

## Problèmes fréquents {#problemes}

| Ce que vous voyez | Quoi faire |
|---|---|
| « Non autorisé : jeton incorrect » | Rouvrez le tableau de bord depuis l’onglet Configuration de la feuille (le lien contient le bon jeton). |
| « Réponse inattendue… accès Tout le monde » | Refaites l’étape 4 avec *Qui a accès : Tout le monde*. |
| « Raccourci mal configuré » | Étape 13 : chaque valeur doit être une pastille bleue. |
| « Votre raccourci utilise encore l’ancien lien » | Copiez le lien du raccourci (⚙ Réglages) et remplacez l’URL dans l’action. |
| « Rien de l’iPhone depuis N jours » | L’automatisation est-elle activée, sans confirmation ? Une mise à jour d’iOS l’a-t-elle désactivée ? |
| Des lignes vides dans Ignorées | iPhone : Réglages → Notifications → (appli) → Afficher les aperçus : Toujours. |
| L’onglet Configuration dit « Déployez d’abord » | Étape 4, puis relancez `setup`. |
| Pas de courriel le lundi | ⚙ Réglages → l’option est-elle cochée ? Regardez dans Promotions ou Pourriel. Le script doit avoir été installé par `setup` (déclencheur). |
