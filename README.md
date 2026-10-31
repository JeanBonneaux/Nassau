# Nassau ↔ Eleuthera

Pages autonomes (un seul fichier chacune, données embarquées, rechargement en direct quand le réseau passe).

| Page | Rôle |
|---|---|
| `retour.html` | Cockpit du retour Cocodimama → Nassau : compte à rebours, score de confort par jour et par heure, tronçons, profil de la traversée, carte avec GPS / estime / trace, ciel et satellite GOES-19, marées (courbes Eleuthera et Nassau), bulletin NHC en direct, mode Avion GHB → NAS |
| `index.html` | Compagnon de la traversée aller Nassau → Eleuthera (18 octobre 2026) |
| `eleuthera.html` | Carnet de séjour, semaine du 19 au 25 octobre |
| `ciel.html` | Prédicteur de soleil pour Alabaster Bay (ensembles, modèles, satellite) |
| `houlometre.html` | Houlomètre par accéléromètre |
| `depenses.html` | Suivi des dépenses à partir des notifications bancaires (copie générée de `index.html` de la branche `claude/spending-tracker`, voir son `docs/SETUP.md`) |

## Ouvrir le cockpit

- Lien direct : `https://htmlpreview.github.io/?https://github.com/Jeanculess/Nassau/blob/page/retour.html` (GPS et données en direct fonctionnent ; sur iPhone, Partager → « Sur l’écran d’accueil » pour le plein écran).
- Une fois GitHub Pages activé (Settings → Pages → Source : GitHub Actions), `.github/workflows/pages.yml` publie le tout sur `https://jeanculess.github.io/Nassau/retour.html`, installable hors ligne grâce au service worker.

Sources : Open-Meteo (modèles, ensembles, mer), NOAA CO-OPS (marées), NHC/TAFB (bulletins), NOAA NESDIS (GOES-19), GADM (trait de côte).
