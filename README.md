# Dépenses : spending tracker from bank notifications

Tracks card and bank spending without a bank API. The iPhone forwards each bank or credit-card notification to a Google Sheet that the user owns; the sheet's script reads it, watches the bank alert emails in Gmail as a second channel, de-duplicates, and emails a weekly digest. A single-page dashboard in French shows where the money goes. User guide (French): [jeanculess.github.io/Nassau/guide.html](https://jeanculess.github.io/Nassau/guide.html).

```
 bank / card app notification ──► iPhone Shortcuts automation (iOS 27 "Notification" trigger) ──POST──┐
 bank alert e-mails in Gmail ──► read by the script every 15 min (GmailApp) ─────────────────────────┤
 paste / manual entry / monthly CSV statement ──► dashboard ─────────────────────────────────────────┤
                                                                                                     ▼
                     Google Apps Script web app (apps-script/Spending.gs = parser + insights + backend)
                       · SpendParser: amount, currency, merchant, card, type, category (EN + FR)
                       · duplicates matched by amount, merchant and channel; never hidden, only flagged
                       · capture-only token for the Shortcut, admin token for the dashboard
                       · tick() every 15 min: e-mails, optional Claude re-read, daily health check, Monday digest
                       · Google Sheet tabs: Transactions · Ignored · Rules · Configuration (ready-made links)
                                                                                                     ▲
                     Dashboard: depenses.html (one file, French, QR code hand-off, Add to Home Screen)
```

<p>
<img src="docs/img/dashboard-light.png" width="260" alt="Tableau de bord : total du mois, budget, file à vérifier, dépenses par jour">
<img src="docs/img/transactions-light.png" width="260" alt="Transactions par jour, avec catégorie, carte et heure">
<img src="docs/img/paste-light.png" width="260" alt="Une notification collée est lue : montant, marchand, catégorie, carte">
</p>

- **Try it:** [open the dashboard](https://jeanculess.github.io/Nassau/depenses.html) → *Voir avec des exemples*.
- **Install it:** the French guide above. Needs a Google account and an iPhone on iOS 27 (the Shortcut trigger that fires on notifications is new in iOS 27).

## What the parser reads

English and French alert formats, for example:

| Notification | Result |
|---|---|
| `Un achat de 54,21 $ a été effectué chez IGA EXTRA à 20 h 14 avec votre carte Visa Scotia se terminant par 1234.` | 54,21 $ · IGA EXTRA · Épicerie · Visa ••1234 |
| Cartes (Wallet): title `Visa Scotia`, subtitle `Jean Coutu`, body `12,50 $` | 12,50 $ · Jean Coutu · Santé · Visa Scotia |
| `A purchase of $22.10 at COUCHE-TARD was approved on your card ending in 1234.` | 22,10 $ · COUCHE-TARD · Épicerie |
| `A purchase of 49.99 USD ($67.89 CAD) was made at AMAZON.COM` | 67,89 $ (original 49.99 USD in the note) |
| `Un paiement de 500,00 $ a été porté à votre carte de crédit…`, transfers to a TFSA, investment orders | transfer, not spending |
| `Un crédit de 25,00 $ de AMAZON.CA a été porté à votre compte.` | refund, lowers spending |
| `Le solde de votre compte … est inférieur à 100,00 $.`, codes, promos, declined, statements, Interac requests | ignored, listed in the *Ignorées* tab |
| `Cafe Olimpico 7.50` (short text, no currency) | kept, flagged *À vérifier* |

The exact wording of the user's banks (Scotiabank, Capital One Canada, Wealthsimple) is not documented publicly; the fixtures in `test/parser.test.mjs` are plausible guesses to be replaced by real samples (the dashboard's *Copier pour améliorer la lecture* button exists for that).

## Files

| Path | What it is |
|---|---|
| `apps-script/Spending.gs` | **The one file to paste into Apps Script** (generated) |
| `src/parser.js` | Notification parser, shared by the backend and the dashboard |
| `src/insights.js` | Recurring charges, budget pace, month comparison, French digest; shared |
| `src/qr.js` | Inline QR code generator (verified against an independent decoder in its tests) |
| `src/backend.gs` | Apps Script backend: tokens, capture, duplicates, Gmail polling, trigger, e-mails, optional Claude |
| `src/dashboard.html` | Dashboard source → `index.html` (published as `depenses.html`) |
| `docs/GUIDE.fr.md` | User guide → `guide.html` (with a *Copier le script* button) and `Spending.txt` |
| `tools/build.mjs` | Generates `Spending.gs`, `index.html`, `guide.html`, `Spending.txt` |
| `tools/gas-mock.mjs`, `tools/dev-server.mjs` | In-memory Google services and a local server, used by the tests and for development |
| `test/` | Parser, backend, Claude, insights and QR tests (`node --test`); browser test (`test/e2e.mjs`) |

## Develop

```sh
node tools/build.mjs            # after editing src/ or docs/GUIDE.fr.md
node --test test/*.test.mjs     # parser + backend (the real Spending.gs against mocked Google services) + insights + QR
node test/e2e.mjs               # dashboard in Chromium (fr-CA, America/Toronto) against the local backend (needs Playwright)
node tools/dev-server.mjs       # local dashboard + backend with sample data; prints a setup link
```

Publishing: copy `index.html` to `depenses.html`, plus `guide.html` and `Spending.txt`, onto the `page` branch; its workflow deploys to GitHub Pages.

Status: the whole pipeline is covered by tests (262 unit tests, 20 browser checks), but it has not yet been run against a real iOS 27 device or a real Google deployment with the user's banks.
