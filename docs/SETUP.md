# Setup

You need an iPhone on **iOS 27 or later** (for the notification trigger), a Google account, and about 15 minutes. Step 1 is easier on a computer.

## 1. The Google Sheet and its script

1. Create a blank Google Sheet ([sheets.new](https://sheets.new)) and name it, for example, *Spending*.
2. Open **Extensions → Apps Script**.
3. Replace everything in `Code.gs` with the contents of [`apps-script/Code.gs`](../apps-script/Code.gs).
4. Next to **Files**, click **+ → Script**, name it `Parser`, and paste the contents of [`apps-script/Parser.gs`](../apps-script/Parser.gs).
5. Save. In the toolbar, select the function **`setup`** and click **Run**.
   Google asks for permission: *Review permissions* → your account → *Google hasn't verified this app* → **Advanced → Go to … (unsafe)** → **Allow**.
   It is your own script. The permission screen mentions your spreadsheets in general, but the code only opens this one.
6. Open the **Execution log**. It shows your **token**. Keep it somewhere private, like a note.
7. Click **Deploy → New deployment**, then the gear icon → **Web app**:
   - Execute as: **Me**
   - Who has access: **Anyone**

   Click **Deploy** and copy the **Web app URL** (it ends in `/exec`).

*Anyone* only means the URL is reachable without a Google login (the iPhone Shortcut can't log in). Every request must also carry the token; without it, nothing is read or written.

When you update the code later, go to **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**. The URL stays the same.

The default currency is USD. Change it in the dashboard settings, or in **Project Settings → Script properties → `CURRENCY`** (e.g. `CAD`, `EUR`). It is also the currency a plain "$" in a notification stands for.

## 2. iPhone: forward the bank notifications (iOS 27+)

Do this once per banking or credit-card app.

1. Open **Shortcuts → Automation → +**.
2. Choose the **Notification** trigger (under *Apps*; it reads "When I get a notification"). Set **App** to the bank's app.
   Leave the filters empty. The sheet decides what counts as a transaction, and everything else goes to the *Ignored* tab, so you can check that nothing was missed.
3. Make it run on its own (not *Ask Before Running*). Turn off *Notify When Run* if you don't want a banner each time.
4. Add the action **Get Contents of URL**:
   - URL: your web app URL
   - Method: **POST**
   - Request Body: **JSON**, with these Text fields:

   | Key | Value |
   |---|---|
   | `token` | your token |
   | `source` | `notification` |
   | `app` | the bank's name, typed in (e.g. `RBC`) |
   | `title` | notification → **Title** |
   | `subtitle` | notification → **Subtitle** |
   | `body` | notification → **Body** |

   To insert a field from the notification, tap the value, choose **Select Variable**, then tap **Shortcut Input** (it may be labeled *Notification*). Tap the inserted variable and pick *Title*, *Subtitle* or *Body*.
5. Optional, while you test: add **Get Dictionary Value** (key `message`, from *Contents of URL*), then **Show Notification** with it. After each capture you'll see something like `✓ 45.20 CAD · SHELL · Transport`. Remove it once you trust the setup.

**Test it** with a small purchase on that card. Within a few seconds a row appears in the *Transactions* tab. If none appears, check the *Ignored* tab: a notification that didn't look like a purchase is listed there with its original text.

Tips:
- The bank app must send detailed alerts that include the amount and the merchant. Many apps have an alert setting such as *Every purchase* or *Purchases over $0*. If the notification only says "New activity on your account", there is nothing to read.
- If rows arrive with empty text, set **Settings → Notifications → (bank app) → Show Previews → Always**.
- With Apple Intelligence you can describe the automation instead of building it: *"When I get a notification from RBC, send its title, subtitle and body as JSON in a POST request to (URL), with token (TOKEN) and source notification."* Check the result against the table above.

Known limits:
- The notification trigger is new in iOS 27. A developer report on iOS 27.0.1 ([FB25255777](https://developer.apple.com/forums/thread/852334)) shows it can skip notifications that arrive seconds apart. Bank alerts usually come one at a time, but compare with your statement once a month.
- The phone needs a network connection when the notification arrives. There is no retry.

## 3. Optional: other sources

**Apple Pay taps (iOS 17+).** Automation → + → **Wallet** (transaction) → pick your cards → run immediately → **Get Contents of URL** as above, with JSON fields `token`, `source` = `applepay`, `merchant` = Shortcut Input → *Merchant*, `amount` = Shortcut Input → *Amount*, `card` = Shortcut Input → *Card or Pass*. If the bank also sends a notification for the same purchase within 30 minutes, the second one is marked *Duplicate?* and not counted.

**SMS alerts.** Automation → + → **Message** → *Message Contains* a word your bank's texts always include (and/or the sender) → run immediately → **Get Contents of URL** with `token`, `source` = `sms`, `app` = the bank's name, `body` = Shortcut Input (the message).

**Android.** Android lets apps read notifications directly. With MacroDroid or Tasker: trigger *Notification Received* for your bank apps, action *HTTP Request*, POST to the web app URL with a JSON body `{"token":"…","source":"android","app":"Bank","title":"…","body":"…"}`. Fill in `title` and `body` with the notification title and text variables the app provides.

## 4. The dashboard

Open [the dashboard](https://htmlpreview.github.io/?https://github.com/Jeanculess/Nassau/blob/claude/spending-tracker/index.html), go to **Settings**, paste the web app URL and the token, tap **Test connection**, pick your currency (and a monthly budget if you want one), then **Save**.

To get it on your Home Screen, use **Share → Add to Home Screen** in Safari. The Home Screen app keeps its own storage, separate from Safari's. Either enter the settings again inside it, or, in Safari, tap **Copy setup link**, open that link in Safari, and add *that* page to the Home Screen. The link carries the settings, and the Home Screen app reads them on first launch.

## Privacy

- Your transactions live in your Google Sheet. The dashboard also keeps a copy on the device so it works offline.
- The shortcut only sends notifications from the apps you choose.
- The token is the key: anyone who has both the URL and the token can read and add rows. To revoke access, run `rotateToken()` in the script editor, then put the new token in the shortcut and the dashboard.
- This repository is public. Never commit your URL or token.
- `htmlpreview.github.io` serves many people's pages from one website, and the dashboard stores your token in that website's storage. That is fine for trying it out. For daily use, host `index.html` on your own GitHub Pages or any other static host.

## Tuning

- **Wrong category:** open the transaction, pick the right one and tick *Always put … in …*. This adds a rule to the *Rules* tab (`pattern | category`, checked top to bottom; `/regex/` works too) and re-files past transactions from that merchant.
- **A notification the parser misreads:** copy its text from the *Ignored* tab or from the transaction's *Original* line. Add it as a case in `test/parser.test.mjs` and fix `src/parser.js`. Then run `node tools/build.mjs`, paste the new `Parser.gs` into the script and deploy a new version.
