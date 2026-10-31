# Setup

You need a Google account, an iPhone on **iOS 27 or later**, and about 20 minutes. Part 1 is done on a computer, Part 2 on the iPhone.

## Part 1, on a computer

### 1. Create the sheet and paste the script
1. Open [sheets.new](https://sheets.new) to create a blank Google Sheet, and name it, for example, *Spending*.
2. In the menu, choose **Extensions → Apps Script**.
3. Open [Spending.gs](https://raw.githubusercontent.com/Jeanculess/Nassau/claude/spending-tracker/apps-script/Spending.gs), select everything (⌘A / Ctrl+A) and copy it.
4. Back in Apps Script, select everything in `Code.gs`, paste over it, and save (⌘S / Ctrl+S).

### 2. Run the setup
5. In the toolbar, choose **setup** in the function menu, then click **Run**.
6. Google asks for permission: **Review permissions** → your account → *Google hasn't verified this app* → **Advanced** → **Go to … (unsafe)** → **Allow**.
   It is your own script. Google's screen mentions all your spreadsheets, but the code only opens this one.
7. The **Execution log** shows `Your token: …`. Keep this tab open; you need the token in step 10.

### 3. Publish it as a web app
8. Click **Deploy → New deployment**, then the gear ⚙ next to *Select type* → **Web app**.
9. Set **Execute as: Me** and **Who has access: Anyone**, then click **Deploy** and copy the **Web app URL** (it ends in `/exec`).
   *Anyone* only means the URL works without a Google login, which the iPhone Shortcut needs. Nothing can be read or written without the token.

### 4. Connect the dashboard and send it to your phone
10. Open [the dashboard](https://jeanculess.github.io/Nassau/depenses.html) and click **Connect my sheet**. Paste the **Web app URL** and the **token**, click **Test connection** (it should say ✓ Connected), choose your currency, then **Save**.
11. Open ⚙ **Settings** again, click **Copy setup link**, and send that link to yourself (Messages, email, Notes…).

## Part 2, on the iPhone

### 5. Put the dashboard on your Home Screen
12. Open the setup link in **Safari**. The dashboard opens already connected.
13. Tap **Share → Add to Home Screen**, then open the new icon once.
    If it opens on the welcome screen instead, tap **Connect my sheet** and paste the setup link into the *Web app URL* field. That fills in everything.

### 6. Create the automation (repeat for each bank or card app)
14. In the dashboard, open ⚙ **Settings** and tap **Copy** next to *Link for the iPhone Shortcut*.
15. In **Shortcuts**, start a new automation with the **Notification** trigger: tap **+**, open **Automation** in the list of actions, and choose **Notification** (under *Apps*). It reads "When I get a notification from…". If your Shortcuts app has an *Automation* tab at the bottom, you can start there with **+** instead.
16. For **App**, choose your bank's app. Leave the filters empty. Make sure it runs **without asking**, and turn off *Notify When Run* if you don't want a banner every time.
17. Add the action **Get Contents of URL**:
    - **URL**: paste the link from step 14.
    - Tap the arrow to show more options. Set **Method** to **POST** and **Request Body** to **JSON**.
    - Tap **Add new field → Text** three times:

      | Key | Value |
      |---|---|
      | `title` | Notification → **Title** |
      | `subtitle` | Notification → **Subtitle** |
      | `body` | Notification → **Body** |

      To fill in a value: tap it → **Select Variable** → tap **Shortcut Input** (it may be called *Notification*) → tap the blue variable → pick *Title*, *Subtitle* or *Body*.
    - Optional: add a fourth Text field, `app`, with the bank's name (e.g. `RBC`). It's handy when you track several banks.
18. Tap **Done**.

### 7. Test
19. Pay for something small with that card. A few seconds later the purchase is in the dashboard (tap ↻) and in the sheet's *Transactions* tab.
20. Nothing there? Open the dashboard's **Ignored** tab.
    - If the notification is listed there, the automation works, but the text wasn't read as a purchase. Send that text over so the parser can learn the format.
    - If it isn't there either, the automation didn't run. Check that it is turned on and set to run without asking.

## If something goes wrong

| What you see | What to do |
|---|---|
| *Unauthorized* when testing the connection | The token doesn't match. Run **setup** again: it prints the same token. |
| *Unexpected answer. Is the web app deployed with access "Anyone"?* | Redo step 9 with *Who has access: Anyone*. |
| Rows arrive with empty text | iPhone **Settings → Notifications → (bank app) → Show Previews → Always**. |
| The notification has no amount ("New activity on your account") | In the bank app's alert settings, turn on detailed purchase alerts (e.g. *every purchase* or *over $0*), or use the bank's SMS alerts (below). |
| You updated the script | Paste the new `Spending.gs`, then **Deploy → Manage deployments → ✏️ → Version: New version → Deploy**. The URL stays the same. |

## Optional extras

- **Apple Pay taps (iOS 17+).** Create an automation with the **Wallet** (transaction) trigger and pick your cards. Add **Get Contents of URL** with the same link, *POST*, *JSON*, and the fields `merchant` = Shortcut Input → *Merchant*, `amount` = Shortcut Input → *Amount*, `card` = Shortcut Input → *Card or Pass*. If the bank also sends a notification for that purchase, the second one is marked *Duplicate?* and not counted.
- **SMS alerts.** Create an automation with the **Message** trigger, set to *Message Contains* a word your bank's texts always include. Add the same action with one field, `body` = Shortcut Input.
- **Android.** Use MacroDroid or Tasker: trigger *Notification Received* for your bank apps, action *HTTP Request*, POST to the same link with a JSON body `{"title": "…", "body": "…"}` filled from the app's notification variables.
- **Budget.** Set it in ⚙ Settings → *Monthly budget*.
- **Categories.** Open a transaction, pick the right category, and tick *Always put … in …*. Past and future purchases from that merchant follow.

## Optional: let Claude read the notifications

The built-in rules handle common formats. With an Anthropic API key, the script also asks Claude to read each notification. Claude gets your categories, your rules, and the category you last used for each recent merchant, so it files purchases the way you do. If a call fails or returns something unusable, the rule-based reading is kept.

1. Create an API key at [console.anthropic.com](https://console.anthropic.com) and add credit. Set a monthly spend limit there too.
2. In Apps Script: ⚙ **Project Settings → Script properties → Add script property**. Name it `ANTHROPIC_API_KEY`, paste the key as the value, then **Save**.
3. Optional properties:
   - `CLAUDE_MODE`: `always` (default, every notification), `review` (only notifications the rules are unsure about) or `off`.
   - `CLAUDE_MODEL`: `claude-opus-5-5` (default). `claude-haiku-5-5` costs far less.
4. Run **testClaude** in the editor. The log shows what Claude read and what each call cost.

- **Cost:** roughly one cent per notification with Claude Opus 5.5 (about 1,000 tokens in and a few hundred out), and a small fraction of a cent with Claude Haiku 5.5. `testClaude` prints the real figure.
- **Who read what:** the `reader` column of the *Transactions* tab says who read each row: `claude`, `rules` or `manual`. If Claude says a notification isn't a transaction while the rules are sure it is, the row is kept and marked for review.
- **Privacy:** with a key, the text of the notifications your Shortcut forwards is sent to Anthropic's API, with one-time codes masked. Your categories, your rules and recent merchant names (no amounts) go along with it. Under Anthropic's commercial terms, API data isn't used to train models by default. Delete the key, or set `CLAUDE_MODE` to `off`, to stop.

## Known limits

- The notification trigger is new in iOS 27. A developer report on iOS 27.0.1 ([FB25255777](https://developer.apple.com/forums/thread/852334)) shows it can skip notifications that arrive seconds apart. Bank alerts usually come one at a time, but compare with your statement once a month.
- The phone needs a network connection when the notification arrives. There is no retry.
- This is a prototype. It has not yet been tried on a real iOS 27 device with real bank notifications.

## Privacy

- Your transactions live in your Google Sheet, which is private to your Google account. The dashboard also keeps a copy on the phone so it works offline.
- The tool never sees your bank login. It only reads notification text, so even a leaked token can't move money: at worst someone could read or add rows.
- The Shortcut only sends notifications from the apps you choose. One-time codes in ignored notifications are masked (`••••••`) before they are stored.
- The link for the Shortcut and the setup link both contain your token. Anyone who has one can read and add rows, so keep them private. To revoke access, run `rotateToken` in Apps Script, then update the Shortcut and the dashboard.
- This repository is public. Never commit your URL or token.
- The dashboard is published on your own GitHub Pages site (`jeanculess.github.io/Nassau/depenses.html`, from the `page` branch). The page is public like the code, but it holds no data: your transactions come straight from your Google Sheet, and the token stays in your phone's browser storage for that site only. Avoid opening it through shared preview sites such as `htmlpreview.github.io`, where other pages share that storage.
