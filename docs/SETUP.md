# Setup

The user guide is in French: [docs/GUIDE.fr.md](GUIDE.fr.md), published at [jeanculess.github.io/Nassau/guide.html](https://jeanculess.github.io/Nassau/guide.html) with a *Copier le script* button.

Short version, for developers:

1. New Google Sheet → Extensions → Apps Script → paste `apps-script/Spending.gs` over `Code.gs` → save.
2. Deploy → New deployment → Web app → *Execute as: Me*, *Who has access: Anyone* → Deploy.
3. Run `setup` once (authorize). The sheet gets a *Configuration* tab with the dashboard setup link (admin token) and the Shortcut link (capture-only token), plus a `tick` trigger every 15 minutes (Gmail polling of bank alert e-mails, optional Claude re-read, daily health e-mail, Monday digest).
4. Open the dashboard from the *Configuration* tab, show the QR code (⚙ Réglages) to the iPhone, add it to the Home Screen, copy the Shortcut link.
5. Shortcuts: one *Notification* automation covering the bank apps and Wallet → *Get Contents of URL* (POST, JSON) with Text fields `titre`, `soustitre`, `corps` bound to the notification's Title, Subtitle, Body. Tap ▶ once: the dashboard's checklist turns green.

API (JSON body or `?token=`): `POST {titre, soustitre, corps}` with the capture token; admin actions `list`, `ping`, `add`, `update`, `delete`, `confirm`, `rule`, `rule-delete`, `settings`, `unignore`. Script properties of note: `WEB_APP_URL` (the `/exec` address; recorded automatically on the first real request, or pasted into the Configuration tab when `ScriptApp.getService().getUrl()` only gives the `/dev` address from the editor), `CURRENCY`, `BUDGET`, `EMAIL` (`off` to stop reading Gmail), `EMAIL_QUERY`, `DIGEST`, `HEARTBEAT_DAYS`, `ANTHROPIC_API_KEY`, `CLAUDE_MODE` (`review` default, `always`, `off`), `CLAUDE_MODEL`, `CLAUDE_MAX_PER_DAY`, `CLAUDE_MAX_MONTH_USD`.
