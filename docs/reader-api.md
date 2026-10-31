# Reading service API (`CLAUDE_ENDPOINT`)

The Apps Script backend can ask Claude to read each notification in two ways:

- **Direct:** it calls the Anthropic API itself with `ANTHROPIC_API_KEY` stored in its Script properties.
- **Through your own service:** it posts to `CLAUDE_ENDPOINT`, and that service holds the Anthropic key, for example on Modal. This page is the contract such a service must follow. The script side is `claudeEndpoint_` in `src/backend.gs`.

Whatever the service answers, the script checks it before storing anything. If the service fails, times out or answers something unusable, the script keeps its rule-based reading.

## Request

`POST {CLAUDE_ENDPOINT}`

```
Content-Type: application/json
Authorization: Bearer {CLAUDE_ENDPOINT_TOKEN}
```

```json
{
  "notification": {
    "app": "Scotiabank",
    "title": "Scotiabank",
    "subtitle": "",
    "body": "Achat de 54,21 $ chez IGA EXTRA avec votre carte se terminant par 1234.",
    "received": "2026-10-31T21:15:00.000Z"
  },
  "context": {
    "currency": "CAD",
    "categories": ["Groceries", "Dining", "Transport", "..."],
    "rules": [{ "pattern": "iga", "category": "Épicerie" }],
    "past": ["METRO #123 -> Groceries", "STARBUCKS -> Dining"]
  }
}
```

- One-time codes are already masked (`••••••`) by the script.
- `app` and `subtitle` can be empty strings.
- `rules` holds at most 50 entries and is checked top to bottom.
- `past` lists up to 40 recent merchants with the category last used for each. It carries no amounts.

The service must reject a missing or wrong token with HTTP 401, comparing in constant time.

## Response

HTTP 200:

```json
{
  "ok": true,
  "record": {
    "is_transaction": true,
    "ignore_reason": "none",
    "type": "purchase",
    "amount": 54.21,
    "currency": "CAD",
    "merchant": "IGA Extra",
    "card": "Visa ••1234",
    "category": "Groceries",
    "confidence": "high"
  },
  "model": "claude-opus-5-5",
  "usage": { "input_tokens": 912, "output_tokens": 140 }
}
```

`record` follows this JSON schema. It is `CLAUDE_SCHEMA` in `src/backend.gs`, and both must stay identical:

| Field | Type |
|---|---|
| `is_transaction` | boolean |
| `ignore_reason` | `none` · `no-amount` · `not-a-spend` · `promo` · `declined` · `upcoming` · `statement` · `other` |
| `type` | `purchase` · `refund` · `cash` · `fee` · `income` · `transfer` |
| `amount` | number, positive; `0` when not a transaction |
| `currency` | ISO 4217 code |
| `merchant`, `card`, `category` | string |
| `confidence` | `high` · `medium` · `low` |

On any failure (refusal, output cut short, invalid output, Anthropic error, timeout), answer `{"ok": false, "error": "..."}`, with a non-200 status or with 200. The script then keeps its own reading. Answer within about 25 seconds: Apps Script stops waiting after 60 seconds, and the iPhone Shortcut waits for the script.

## How the service should call Claude

Use the same request as the script's direct mode, so both modes read notifications the same way:

- **Prompt:** build it exactly like `claudePrompt_(ctx, n)` in `src/backend.gs`. The system text is copied verbatim, with the default currency inserted. The user message has the same lines in the same order: default currency, categories, rules, past merchants, then the notification header and its `title`, `subtitle` and `body` lines.
- **Model:** `claude-opus-5-5` by default, overridable with an environment variable.
- **Structured output:** `output_config.format` = `{"type": "json_schema", "schema": <the schema above, additionalProperties false, every field required>}`, with `output_config.effort` = `low`. Do not send `temperature`.
- **Output limit:** `max_tokens` 4000.
- **Refusals:** use server-side fallback, `fallbacks: "default"` with the beta `server-side-fallback-2026-07-01`. Haiku models don't support it, so leave it out there. Treat `stop_reason` `refusal` or `max_tokens` as a failure.
- **SDK:** use Anthropic's official SDK for the service's language. Read the JSON from the last `text` block of the response.

## Privacy

- Do not log notification text or records. Logging status codes, the model and token counts is fine.
- Never return or log the Anthropic key.
