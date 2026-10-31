/**
 * Spending tracker: Google Apps Script backend.
 *
 * Receives bank / card notifications (iPhone Shortcuts automation, Android, the dashboard),
 * reads them with SpendParser and stores them in this spreadsheet.
 * tools/build.mjs bundles this file with src/parser.js into apps-script/Spending.gs,
 * the single file you paste into Apps Script.
 *
 * Setup (details in docs/SETUP.md):
 *   1. In a new Google Sheet: Extensions > Apps Script. Replace Code.gs with apps-script/Spending.gs.
 *   2. Run setup() once (choose it in the toolbar, press Run, allow access). The log shows your token.
 *   3. Deploy > New deployment > Web app. Execute as: Me. Who has access: Anyone. Copy the URL.
 *
 * Optional: set ANTHROPIC_API_KEY in Project Settings > Script properties to have Claude read each
 * notification too (see the "Claude" section below). Without a key nothing leaves Google.
 *
 * API (every call needs the token, in the JSON body or as ?token=...):
 *   POST {source, app, title, subtitle, body}       a notification to parse and store
 *   POST {source:'applepay', amount, merchant, card} fields already split (Wallet automation)
 *   POST {action:'add'|'update'|'delete'|'rule'|'settings', ...}   used by the dashboard
 *   GET  ?action=list | ?action=ping
 */

var VERSION = '0.2.0';
var TX_SHEET = 'Transactions';
var IGNORED_SHEET = 'Ignored';
var RULES_SHEET = 'Rules';
var TX_COLS = ['date', 'amount', 'currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id', 'captured_at', 'reader'];
var TX_FORMATS = ['yyyy-mm-dd hh:mm', '0.00', '@', '@', '@', '@', '@', '@', '@', '@', '@', '@', 'yyyy-mm-dd hh:mm:ss', '@'];
var IGNORED_COLS = ['captured_at', 'source', 'reason', 'raw'];
var IGNORED_FORMATS = ['yyyy-mm-dd hh:mm:ss', '@', '@', '@'];
var RULES_COLS = ['pattern', 'category'];
var IGNORED_MAX = 1000;                    // older ignored notifications are trimmed
var DUP_WINDOW_MS = 30 * 60 * 1000;        // same amount from two different sources within 30 min = duplicate
var SAME_SOURCE_WINDOW_MS = 5 * 60 * 1000; // same amount, other wording, same source within 5 min = duplicate
var EXACT_WINDOW_MS = 10 * 60 * 1000;      // same text from the same source within 10 min = sent twice
var STATUSES = ['ok', 'review', 'duplicate', 'excluded'];
var EDITABLE = ['date', 'amount', 'currency', 'merchant', 'category', 'type', 'card', 'status', 'note'];

/* ------------------------------------------------------------------ run these from the editor */

function setup() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Open the script from the spreadsheet (Extensions > Apps Script), then run setup again.');
  var props = PropertiesService.getScriptProperties();
  props.setProperty('SHEET_ID', ss.getId());
  if (!props.getProperty('TOKEN')) props.setProperty('TOKEN', newToken_());
  if (!props.getProperty('CURRENCY')) props.setProperty('CURRENCY', 'USD');
  ensureSheet_(ss, TX_SHEET, TX_COLS);
  ensureSheet_(ss, IGNORED_SHEET, IGNORED_COLS);
  ensureSheet_(ss, RULES_SHEET, RULES_COLS);
  // Remove the empty default tab ("Sheet1", "Feuille 1", ...).
  ss.getSheets().forEach(function (sh) {
    var name = sh.getName();
    if (name !== TX_SHEET && name !== IGNORED_SHEET && name !== RULES_SHEET && sh.getLastRow() === 0 && ss.getSheets().length > 3) {
      ss.deleteSheet(sh);
    }
  });
  var info = { token: props.getProperty('TOKEN'), currency: props.getProperty('CURRENCY'), sheet: ss.getUrl() };
  Logger.log('Setup done.\n\nYour token: ' + info.token +
    '\nDefault currency: ' + info.currency + ' (change it from the dashboard, or in Project Settings > Script properties > CURRENCY)' +
    '\n\nNext: Deploy > New deployment > type "Web app", Execute as "Me", Who has access "Anyone". Copy the Web app URL.' +
    '\nRunning setup() again is safe: it keeps your data and token.');
  return info;
}

/** Makes a new token (the old one stops working). Update the Shortcut and the dashboard afterwards. */
function rotateToken() {
  var token = newToken_();
  PropertiesService.getScriptProperties().setProperty('TOKEN', token);
  Logger.log('New token: ' + token);
  return token;
}

/** Try the parser on any text without deploying anything. */
function testParse() {
  var samples = [
    { title: 'Visa', body: 'Purchase of $45.20 at SHELL. Available balance: $1,234.56' },
    { body: 'Achat de 54,21 $ chez IGA EXTRA effectué avec votre carte Visa se terminant par 1234.' },
    { body: 'Your verification code is 482913' }
  ];
  samples.forEach(function (s) {
    Logger.log(JSON.stringify(s) + '\n  -> ' + JSON.stringify(SpendParser.parse(s, { defaultCurrency: currency_(), rules: readRules_(ss_()) })));
  });
}

/* ------------------------------------------------------------------ web app entry points */

function doGet(e) {
  return respond_(function () {
    var p = (e && e.parameter) || {};
    checkToken_(p.token);
    var action = p.action || 'list';
    if (action === 'list') return list_();
    if (action === 'ping') return ping_();
    throw new Error('Unknown action: ' + action);
  }, false);
}

function doPost(e) {
  return respond_(function () {
    var b = body_(e);
    checkToken_(b.token);
    var action = b.action || 'capture';
    if (action === 'capture') return capture_(b);
    if (action === 'add') return add_(b.tx || b);
    if (action === 'update') return update_(b.id, b.fields || {});
    if (action === 'delete') return delete_(b.id);
    if (action === 'rule') return addRule_(b.pattern, b.category, b.apply !== false);
    if (action === 'settings') return settings_(b);
    if (action === 'list') return list_();
    if (action === 'ping') return ping_();
    throw new Error('Unknown action: ' + action);
  }, true);
}

function respond_(fn, useLock) {
  var lock = null;
  var out;
  try {
    if (useLock) {
      lock = LockService.getScriptLock();
      lock.waitLock(30000);
    }
    out = fn();
  } catch (err) {
    out = { ok: false, error: String((err && err.message) || err) };
  } finally {
    if (lock) {
      try { lock.releaseLock(); } catch (ignored) { /* lock was never acquired */ }
    }
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

// JSON body (Shortcuts, dashboard), form fields (Android apps), or plain text. Query parameters fill gaps.
function body_(e) {
  var b = {};
  var pd = e && e.postData;
  if (pd && pd.contents && !/x-www-form-urlencoded/i.test(pd.type || '')) {
    try { b = JSON.parse(pd.contents); } catch (err) { b = null; }
    if (!b || typeof b !== 'object' || Array.isArray(b)) b = { body: String(pd.contents) };
  }
  var p = (e && e.parameter) || {};
  Object.keys(p).forEach(function (k) { if (b[k] === undefined) b[k] = p[k]; });
  return b;
}

function checkToken_(token) {
  var expected = PropertiesService.getScriptProperties().getProperty('TOKEN');
  if (!expected) throw new Error('Run setup() in the script editor first.');
  if (!token || String(token).trim() !== expected) throw new Error('Unauthorized: wrong or missing token.');
}

/* ------------------------------------------------------------------ actions */

function capture_(b) {
  var ss = ss_();
  var cur = currency_();
  var rules = readRules_(ss);
  var app = str_(b.app, 40);
  var structured = !blank_(b.amount) || !blank_(b.merchant);
  var source = str_(b.source || (structured ? 'applepay' : 'notification'), 30) + (app ? ':' + app : '');
  var title = str_(b.title, 300);
  var subtitle = str_(b.subtitle, 300);
  var text = str_(first_(b.body, b.text, b.message, b.content, b.notification), 2000);
  var when = when_(b.date);
  var r;
  var raw;
  var reader = 'rules';
  var note = '';
  if (structured) {
    r = SpendParser.fromFields({ amount: b.amount, merchant: b.merchant, card: b.card, currency: b.currency, type: b.type },
      { defaultCurrency: cur, rules: rules });
    raw = [str_(b.merchant, 100), str_(b.amount, 40), str_(b.card, 60)].filter(String).join(' | ');
  } else {
    r = SpendParser.parse({ title: title, subtitle: subtitle, body: text, app: app }, { defaultCurrency: cur, rules: rules });
    raw = [title, subtitle, text].filter(String).join(' | ');
    var cfg = claudeConfig_();
    if (cfg && shouldAskClaude_(cfg, r, raw)) {
      var ctx = claudeContext_(sheet_(ss, TX_SHEET, TX_COLS), rules, cur);
      var c = claudeRead_(cfg, ctx, { app: app, title: title, subtitle: subtitle, body: text, received: when });
      if (c && c.kind === 'ignore' && r.kind === 'transaction' && r.status === 'ok') {
        // The two readers disagree: keep it, but ask the user to look.
        r.status = 'review';
        note = 'Claude thinks this is not a transaction (' + c.reason + ')';
      } else if (c) {
        r = c;
        reader = 'claude';
      }
    }
  }

  if (r.kind !== 'transaction') {
    appendIgnored_(ss, { captured_at: new Date(), source: source, reason: r.reason, raw: SpendParser.redactCodes(raw) });
    return { ok: true, status: 'ignored', reason: r.reason, message: 'Not a transaction (' + r.reason + ')' };
  }

  var tx = {
    id: newId_(), date: when, amount: SpendParser.signedAmount(r.amount, r.type), currency: r.currency,
    merchant: r.merchant, category: r.category, type: r.type, card: r.card, status: r.status, note: note,
    source: source, raw: raw, captured_at: new Date(), reader: reader
  };
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
  // A suspected duplicate is kept but not counted, so nothing is ever silently dropped.
  var dup = findDuplicate_(readTx_(sheet, 200), tx);
  if (dup) {
    tx.status = 'duplicate';
    tx.note = dup.kind === 'repeat'
      ? 'Same notification received twice'
      : 'Possible duplicate of ' + (dup.row.merchant || 'an earlier transaction') + ' (' + dup.row.source + ')';
  }
  appendRow_(sheet, TX_COLS, TX_FORMATS, tx);
  return { ok: true, status: tx.status === 'duplicate' ? 'duplicate' : 'added', tx: out_(tx, cur), message: message_(tx) };
}

function add_(t) {
  var ss = ss_();
  var cur = currency_();
  var r = SpendParser.fromFields({ amount: t.amount, merchant: t.merchant, card: t.card, currency: t.currency, type: t.type, category: t.category },
    { defaultCurrency: cur, rules: readRules_(ss) });
  if (!(r.amount > 0)) throw new Error('The amount is missing.');
  var tx = {
    id: newId_(), date: date_(t.date) || new Date(), amount: SpendParser.signedAmount(r.amount, r.type), currency: r.currency,
    merchant: r.merchant, category: r.category, type: r.type, card: r.card,
    status: STATUSES.indexOf(t.status) >= 0 ? t.status : 'ok', note: str_(t.note, 500),
    source: str_(t.source || 'manual', 30), raw: str_(t.raw, 2000), captured_at: new Date(), reader: 'manual'
  };
  appendRow_(sheet_(ss, TX_SHEET, TX_COLS), TX_COLS, TX_FORMATS, tx);
  return { ok: true, status: 'added', tx: out_(tx, cur) };
}

function update_(id, fields) {
  var ss = ss_();
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
  var row = findRow_(sheet, id);
  if (!row) throw new Error('Transaction not found: ' + id);
  var o = rowObj_(sheet.getRange(row, 1, 1, TX_COLS.length).getValues()[0]);
  EDITABLE.forEach(function (k) {
    if (fields[k] === undefined || fields[k] === null) return;
    var v = fields[k];
    if (k === 'date') {
      var d = date_(v);
      if (d) o.date = d;
    } else if (k === 'amount') {
      var n = Number(v);
      if (isFinite(n)) o.amount = n;
    } else if (k === 'type') {
      if (SpendParser.TYPES.indexOf(v) >= 0) o.type = v;
    } else if (k === 'status') {
      if (STATUSES.indexOf(v) >= 0) o.status = v;
    } else if (k === 'currency') {
      var c = String(v).trim().toUpperCase();
      if (/^[A-Z]{3}$/.test(c)) o.currency = c;
    } else {
      o[k] = str_(v, k === 'note' ? 500 : 100);
    }
  });
  o.amount = SpendParser.signedAmount(o.amount, o.type || 'purchase');
  writeRow_(sheet, row, TX_COLS, TX_FORMATS, o);
  return { ok: true, tx: out_(o, currency_()) };
}

function delete_(id) {
  var sheet = sheet_(ss_(), TX_SHEET, TX_COLS);
  var row = findRow_(sheet, id);
  if (!row) throw new Error('Transaction not found: ' + id);
  sheet.deleteRow(row);
  return { ok: true, id: id };
}

// Rules are checked top to bottom, so a new rule goes on top.
function addRule_(pattern, category, apply) {
  pattern = str_(pattern, 100);
  category = str_(category, 40);
  if (!pattern || !category) throw new Error('A rule needs a pattern and a category.');
  var ss = ss_();
  var rulesSheet = sheet_(ss, RULES_SHEET, RULES_COLS);
  var rules = readRules_(ss).filter(function (r) { return SpendParser.fold(r.pattern) !== SpendParser.fold(pattern); });
  rules.unshift({ pattern: pattern, category: category });
  var last = rulesSheet.getLastRow();
  if (last >= 2) rulesSheet.getRange(2, 1, last - 1, 2).clearContent();
  rulesSheet.getRange(2, 1, rules.length, 2)
    .setNumberFormats(rules.map(function () { return ['@', '@']; }))
    .setValues(rules.map(function (r) { return [r.pattern, r.category]; }));

  var updated = 0;
  if (apply) {
    var sheet = sheet_(ss, TX_SHEET, TX_COLS);
    var catCol = TX_COLS.indexOf('category') + 1;
    readTx_(sheet, 0).forEach(function (r) {
      if (r.type && r.type !== 'purchase' && r.type !== 'refund') return;
      if (r.category !== category && SpendParser.matchRule(SpendParser.fold(r.merchant), pattern)) {
        sheet.getRange(r._row, catCol).setValue(category);
        updated++;
      }
    });
  }
  return { ok: true, updated: updated, rules: readRules_(ss) };
}

function settings_(b) {
  if (b.currency !== undefined) {
    var c = String(b.currency).trim().toUpperCase();
    if (!/^[A-Z]{3}$/.test(c)) throw new Error('The currency must be a 3-letter code like CAD, USD or EUR.');
    PropertiesService.getScriptProperties().setProperty('CURRENCY', c);
  }
  return { ok: true, currency: currency_() };
}

function list_() {
  var ss = ss_();
  var cur = currency_();
  var sheet = ensureSheet_(ss, TX_SHEET, TX_COLS);
  var rows = readTx_(sheet, 0);
  var idCol = TX_COLS.indexOf('id') + 1;
  rows.forEach(function (r) {
    // Rows typed straight into the sheet get an id so the dashboard can edit them.
    if (!r.id) {
      r.id = newId_();
      sheet.getRange(r._row, idCol).setValue(r.id);
    }
  });
  return {
    ok: true, version: VERSION, currency: cur, sheetUrl: ss.getUrl(),
    transactions: rows.map(function (r) { return out_(r, cur); }),
    ignored: readIgnored_(ss, 100),
    rules: readRules_(ss)
  };
}

function ping_() {
  var cfg = claudeConfig_();
  return { ok: true, version: VERSION, parser: SpendParser.VERSION, currency: currency_(), claude: cfg ? cfg.mode + ' · ' + cfg.model : 'off' };
}

/* ------------------------------------------------------------------ storage helpers */

function ss_() {
  var id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  var ss = id ? SpreadsheetApp.openById(id) : SpreadsheetApp.getActiveSpreadsheet();
  if (!ss) throw new Error('Run setup() in the script editor first.');
  return ss;
}

function ensureSheet_(ss, name, cols) {
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  var header = sh.getRange(1, 1, 1, cols.length).getValues()[0];
  if (header.join('') === '') {
    sh.getRange(1, 1, 1, cols.length).setValues([cols]).setFontWeight('bold');
    sh.setFrozenRows(1);
  } else if (header.some(function (h) { return h === ''; })) {
    // A newer version added columns: give them their header, keep the others as they are.
    sh.getRange(1, 1, 1, cols.length).setValues([cols.map(function (c, i) { return header[i] === '' ? c : header[i]; })]);
  }
  return sh;
}

function sheet_(ss, name, cols) {
  return ss.getSheetByName(name) || ensureSheet_(ss, name, cols);
}

function currency_() {
  return PropertiesService.getScriptProperties().getProperty('CURRENCY') || 'USD';
}

function rowObj_(values) {
  var o = {};
  for (var j = 0; j < TX_COLS.length; j++) o[TX_COLS[j]] = values[j];
  ['currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id', 'reader'].forEach(function (k) {
    o[k] = o[k] === null || o[k] === undefined ? '' : String(o[k]);
  });
  o.amount = Number(o.amount) || 0;
  o.date = date_(o.date);
  o.captured_at = date_(o.captured_at);
  return o;
}

function readTx_(sheet, lastN) {
  var last = sheet.getLastRow();
  if (last < 2) return [];
  var start = lastN ? Math.max(2, last - lastN + 1) : 2;
  var values = sheet.getRange(start, 1, last - start + 1, TX_COLS.length).getValues();
  var out = [];
  for (var i = 0; i < values.length; i++) {
    if (values[i].join('') === '') continue;
    var o = rowObj_(values[i]);
    o._row = start + i;
    out.push(o);
  }
  return out;
}

function readIgnored_(ss, n) {
  var sh = ss.getSheetByName(IGNORED_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  var last = sh.getLastRow();
  var start = Math.max(2, last - n + 1);
  return sh.getRange(start, 1, last - start + 1, IGNORED_COLS.length).getValues().reverse().map(function (r) {
    var d = date_(r[0]);
    return { captured_at: d ? d.toISOString() : null, source: String(r[1]), reason: String(r[2]), raw: String(r[3]) };
  });
}

function readRules_(ss) {
  var sh = ss.getSheetByName(RULES_SHEET);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, 2).getValues()
    .filter(function (r) { return String(r[0]).trim() && String(r[1]).trim(); })
    .map(function (r) { return { pattern: String(r[0]).trim(), category: String(r[1]).trim() }; });
}

function appendRow_(sheet, cols, formats, o) {
  var row = sheet.getLastRow() + 1;
  writeRow_(sheet, row, cols, formats, o);
  return row;
}

// Text columns are formatted as plain text first so Sheets never turns "7-11" into a date.
function writeRow_(sheet, row, cols, formats, o) {
  var range = sheet.getRange(row, 1, 1, cols.length);
  range.setNumberFormats([formats]);
  range.setValues([cols.map(function (c) { return o[c] === null || o[c] === undefined ? '' : o[c]; })]);
}

function appendIgnored_(ss, o) {
  var sh = sheet_(ss, IGNORED_SHEET, IGNORED_COLS);
  appendRow_(sh, IGNORED_COLS, IGNORED_FORMATS, o);
  var extra = sh.getLastRow() - 1 - IGNORED_MAX;
  if (extra > 0) sh.deleteRows(2, extra);
}

function findRow_(sheet, id) {
  if (!id) return 0;
  var last = sheet.getLastRow();
  if (last < 2) return 0;
  var ids = sheet.getRange(2, TX_COLS.indexOf('id') + 1, last - 1, 1).getValues();
  for (var i = ids.length - 1; i >= 0; i--) {
    if (String(ids[i][0]) === String(id)) return i + 2;
  }
  return 0;
}

// One purchase can reach the sheet twice:
//   repeat: the same text from the same source (the automation fired twice)
//   cross:  the same amount from another source within 30 min (Apple Pay automation + bank notification)
//   near:   the same amount worded differently within 5 min from the same source, e.g. Wallet and the
//           bank app both covered by one automation
// Different card numbers always mean different purchases.
function findDuplicate_(rows, tx) {
  var t = tx.date.getTime();
  for (var i = rows.length - 1; i >= 0; i--) {
    var r = rows[i];
    if (r.status === 'duplicate' || !r.date) continue;
    if (Math.abs(r.amount - tx.amount) > 0.005 || (r.currency || tx.currency) !== tx.currency) continue;
    var dt = Math.abs(r.date.getTime() - t);
    var same = r.source === tx.source;
    if (same && r.raw && r.raw === tx.raw && dt < EXACT_WINDOW_MS) return { kind: 'repeat', row: r };
    var da = cardDigits_(r.card);
    var db = cardDigits_(tx.card);
    if (da && db && da !== db) continue;
    if (!same && dt < DUP_WINDOW_MS) return { kind: 'cross', row: r };
    if (same && dt < SAME_SOURCE_WINDOW_MS) return { kind: 'near', row: r };
  }
  return null;
}

/* ------------------------------------------------------------------ Claude (optional second reader) */

// Off until ANTHROPIC_API_KEY is set in Project Settings > Script properties. Other properties:
//   CLAUDE_MODE  = always (default: every notification) | review (only when the rules are unsure) | off
//   CLAUDE_MODEL = claude-opus-5-5 (default); claude-haiku-5-5 costs far less
// Calls go straight to the Anthropic API with UrlFetchApp (Apps Script cannot load the SDK).
// When a call fails, is refused or returns something unusable, the rule-based reading is kept.
var CLAUDE_URL = 'https://api.anthropic.com/v1/messages';
var CLAUDE_DEFAULT_MODEL = 'claude-opus-5-5';
var CLAUDE_REASONS = ['none', 'no-amount', 'not-a-spend', 'promo', 'declined', 'upcoming', 'statement', 'other'];
var CLAUDE_PRICES = { 'claude-opus-5-5': [4, 20], 'claude-sonnet-5-5': [2, 10], 'claude-haiku-5-5': [0.1, 0.5] }; // $ per million tokens in / out
var CLAUDE_SCHEMA = {
  type: 'object',
  properties: {
    is_transaction: { type: 'boolean' },
    ignore_reason: { type: 'string', enum: CLAUDE_REASONS },
    type: { type: 'string', enum: ['purchase', 'refund', 'cash', 'fee', 'income', 'transfer'] },
    amount: { type: 'number' },
    currency: { type: 'string' },
    merchant: { type: 'string' },
    card: { type: 'string' },
    category: { type: 'string' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] }
  },
  required: ['is_transaction', 'ignore_reason', 'type', 'amount', 'currency', 'merchant', 'card', 'category', 'confidence'],
  additionalProperties: false
};

/** Reads three sample notifications with Claude and logs the result and the cost of each call. */
function testClaude() {
  var cfg = claudeConfig_();
  if (!cfg) {
    Logger.log('Claude is off. Add ANTHROPIC_API_KEY in Project Settings > Script properties (and do not set CLAUDE_MODE to "off").');
    return;
  }
  var ss = ss_();
  var ctx = claudeContext_(sheet_(ss, TX_SHEET, TX_COLS), readRules_(ss), currency_());
  [
    { app: 'Scotiabank', title: 'Scotiabank', body: 'Achat de 54,21 $ chez IGA EXTRA avec votre carte se terminant par 1234.' },
    { app: 'Wallet', title: 'Visa ••1234', subtitle: 'Starbucks', body: '$5.75' },
    { app: 'Capital One', title: 'Capital One', body: 'Your verification code is 482913' }
  ].forEach(function (n) {
    var out = claudeRead_(cfg, ctx, { app: n.app, title: n.title || '', subtitle: n.subtitle || '', body: n.body, received: new Date() }, true);
    Logger.log(JSON.stringify(n) + '\n  -> ' + JSON.stringify(out));
  });
}

function claudeConfig_() {
  var p = PropertiesService.getScriptProperties();
  var key = String(p.getProperty('ANTHROPIC_API_KEY') || '').trim();
  var mode = String(p.getProperty('CLAUDE_MODE') || 'always').trim().toLowerCase();
  if (!key || mode === 'off') return null;
  return { key: key, mode: mode === 'review' ? 'review' : 'always', model: String(p.getProperty('CLAUDE_MODEL') || CLAUDE_DEFAULT_MODEL).trim() };
}

function shouldAskClaude_(cfg, local, raw) {
  if (!raw) return false;
  if (cfg.mode === 'always') return true;
  if (local.kind === 'transaction') return local.status === 'review';
  return (local.reason === 'no-amount' || local.reason === 'not-a-spend') && /\d/.test(raw);
}

// What Claude gets besides the notification: the currency, the categories, the user's rules
// and the category already used for recent merchants, so it files things the way the user does.
function claudeContext_(sheet, rules, cur) {
  var cats = SpendParser.CATEGORIES.map(function (c) { return c.name; });
  rules.forEach(function (r) { if (cats.indexOf(r.category) < 0) cats.push(r.category); });
  var seen = {};
  var past = [];
  readTx_(sheet, 120).reverse().forEach(function (t) {
    if (t.category && cats.indexOf(t.category) < 0) cats.push(t.category);
    var k = SpendParser.fold(t.merchant);
    if (!t.merchant || seen[k] || t.status === 'duplicate' || past.length >= 40) return;
    seen[k] = true;
    past.push(t.merchant + ' -> ' + (t.category || 'Other'));
  });
  return { currency: cur, categories: cats, rules: rules, past: past };
}

function claudePrompt_(ctx, n) {
  var system = [
    'You read push notifications from banking and credit-card apps for a personal spending tracker, and turn each one into one record that follows the JSON schema.',
    'is_transaction is true only when the notification reports money that moved or was authorized on the user\'s account or card: a purchase, refund, cash withdrawal, fee, income or transfer. Promotions, rewards or cash back earned, balances, statements, reminders of upcoming payments, declined or blocked transactions, security codes and sign-in alerts are not transactions: set is_transaction to false and choose the ignore_reason that fits.',
    'amount is the amount of that transaction as a positive number in major units, never a balance or an available credit. Texts can be in French or English, with amounts written like "1 234,56 $" or "$1,234.56".',
    'currency is an ISO 4217 code. A bare "$" means ' + ctx.currency + ' unless the text says otherwise (US$, USD, CA$, BSD...).',
    'type is purchase for spending (bill payments and pre-authorized debits included), refund for money returned on a purchase, cash for an ATM withdrawal, fee for bank fees and interest, income for salary and deposits, transfer for credit card payments, e-transfers and moves between accounts.',
    'merchant is the business or person as written, without the card or bank name; leave it empty when there is none.',
    'card is a short label such as "Visa ••1234" when the notification names the card; otherwise leave it empty.',
    'category is one of the user\'s categories. Follow the user\'s rules first, then the category already used for the same merchant.',
    'confidence is high when the amount and the merchant are stated plainly, and low when you had to guess either one.',
    'When is_transaction is false, set amount to 0, the text fields to empty strings, type to "purchase" and category to "Other".'
  ].join('\n\n');
  var lines = ['Default currency: ' + ctx.currency, 'Categories: ' + ctx.categories.join(', ')];
  lines.push('Rules (pattern -> category, the first match wins):' + (ctx.rules.length ? '' : ' none'));
  ctx.rules.slice(0, 50).forEach(function (r) { lines.push('- ' + r.pattern + ' -> ' + r.category); });
  lines.push('Categories used before for recent merchants:' + (ctx.past.length ? '' : ' none'));
  ctx.past.forEach(function (p) { lines.push('- ' + p); });
  lines.push('', 'Notification received ' + n.received.toISOString() + (n.app ? ' from the app "' + n.app + '"' : '') + ':');
  lines.push('title: ' + SpendParser.redactCodes(n.title));
  lines.push('subtitle: ' + SpendParser.redactCodes(n.subtitle));
  lines.push('body: ' + SpendParser.redactCodes(n.body));
  return { system: system, user: lines.join('\n') };
}

// Returns the parsed JSON object, or null when the call fails, is refused or is cut short.
function claudeCall_(cfg, prompt, verbose) {
  var body = {
    model: cfg.model,
    max_tokens: 4000,
    system: prompt.system,
    messages: [{ role: 'user', content: prompt.user }],
    output_config: { effort: 'low', format: { type: 'json_schema', schema: CLAUDE_SCHEMA } }
  };
  var headers = { 'x-api-key': cfg.key, 'anthropic-version': '2026-10-21' };
  // Server-side fallback: if a safety classifier declines, the API retries on another model.
  // Haiku has no server-side fallback, so the parameter is left out there.
  if (!/haiku/i.test(cfg.model)) {
    body.fallbacks = 'default';
    headers['anthropic-beta'] = 'server-side-fallback-2026-07-01';
  }
  try {
    var res = UrlFetchApp.fetch(CLAUDE_URL, {
      method: 'post', contentType: 'application/json', headers: headers, payload: JSON.stringify(body), muteHttpExceptions: true
    });
    var code = res.getResponseCode();
    var text = res.getContentText();
    if (code !== 200) {
      Logger.log('Claude: HTTP ' + code + ' ' + text.slice(0, 300));
      return null;
    }
    var msg = JSON.parse(text);
    if (verbose) Logger.log('Claude: ' + msg.model + ', stop ' + msg.stop_reason + ', ' + claudeCost_(msg));
    if (msg.stop_reason === 'refusal' || msg.stop_reason === 'max_tokens') return null;
    var texts = (msg.content || []).filter(function (b) { return b.type === 'text' && b.text; });
    return texts.length ? JSON.parse(texts[texts.length - 1].text) : null;
  } catch (err) {
    Logger.log('Claude: ' + err);
    return null;
  }
}

function claudeCost_(msg) {
  var u = msg.usage || {};
  var tokensIn = (u.input_tokens || 0) + (u.cache_read_input_tokens || 0) + (u.cache_creation_input_tokens || 0);
  var tokensOut = u.output_tokens || 0;
  var price = CLAUDE_PRICES[msg.model];
  var cost = price ? ' ≈ $' + ((tokensIn * price[0] + tokensOut * price[1]) / 1e6).toFixed(4) : '';
  return tokensIn + ' tokens in, ' + tokensOut + ' out' + cost;
}

// Claude's answer checked against what the sheet accepts; null means "keep the rule-based reading".
function claudeRead_(cfg, ctx, n, verbose) {
  var j = claudeCall_(cfg, claudePrompt_(ctx, n), verbose);
  if (!j || typeof j.is_transaction !== 'boolean') return null;
  if (!j.is_transaction) return { kind: 'ignore', reason: CLAUDE_REASONS.indexOf(j.ignore_reason) > 0 ? j.ignore_reason : 'other' };
  var amount = Math.abs(Number(j.amount));
  if (!(amount > 0) || !isFinite(amount)) return null;
  var type = SpendParser.TYPES.indexOf(j.type) >= 0 ? j.type : 'purchase';
  var currency = String(j.currency || '').trim().toUpperCase();
  if (!/^[A-Z]{3}$/.test(currency)) currency = ctx.currency;
  var merchant = str_(j.merchant, 60);
  var spending = type === 'purchase' || type === 'refund';
  var category;
  if (!spending) {
    category = SpendParser.categorize('', ctx.rules, type);
  } else {
    // The user's own rules always win over Claude's pick.
    var fm = SpendParser.fold(merchant);
    var ruled = '';
    ctx.rules.forEach(function (r) { if (!ruled && SpendParser.matchRule(fm, r.pattern)) ruled = r.category; });
    category = ruled || (ctx.categories.indexOf(j.category) >= 0 ? j.category : SpendParser.categorize(merchant, ctx.rules, type));
  }
  return {
    kind: 'transaction', type: type, amount: Math.round(amount * 100) / 100, currency: currency, merchant: merchant,
    card: str_(j.card, 40), category: category, status: j.confidence === 'low' || (spending && !merchant) ? 'review' : 'ok'
  };
}

/* ------------------------------------------------------------------ small helpers */

function out_(o, cur) {
  var type = o.type || (o.amount < 0 ? 'refund' : 'purchase');
  return {
    id: o.id, date: o.date ? o.date.toISOString() : null, amount: Math.round(o.amount * 100) / 100,
    currency: o.currency || cur, merchant: o.merchant || '', category: o.category || 'Other', type: type,
    card: o.card || '', status: o.status || 'ok', note: o.note || '', source: o.source || 'sheet', raw: o.raw || '',
    captured_at: o.captured_at ? o.captured_at.toISOString() : null, reader: o.reader || ''
  };
}

function message_(tx) {
  var s = (tx.amount < 0 ? '+' : '') + Math.abs(tx.amount).toFixed(2) + ' ' + tx.currency + ' · ' + (tx.merchant || '?') + ' · ' + tx.category;
  if (tx.status === 'review') s += ' (check it)';
  if (tx.status === 'duplicate') s += ' (possible duplicate, not counted)';
  if (tx.reader === 'claude') s += ' · read by Claude';
  return '✓ ' + s;
}

function cardDigits_(c) {
  var m = /(\d{4,5})\D*$/.exec(String(c || ''));
  return m ? m[1] : '';
}

// Capture time: trust the phone's date only when it is close to now (Shortcuts may send a localized string).
function when_(v) {
  var now = new Date();
  var d = date_(v);
  return d && Math.abs(d.getTime() - now.getTime()) < 3 * 86400000 ? d : now;
}

function date_(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v.getTime === 'function') return isNaN(v.getTime()) ? null : v;
  var d = typeof v === 'number' ? new Date(v < 1e12 ? v * 1000 : v) : new Date(String(v));
  return isNaN(d.getTime()) ? null : d;
}

function str_(v, max) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/\s+/g, ' ').trim().slice(0, max || 200);
}

function blank_(v) {
  return v === null || v === undefined || String(v).trim() === '';
}

function first_() {
  for (var i = 0; i < arguments.length; i++) {
    if (!blank_(arguments[i])) return arguments[i];
  }
  return '';
}

function newId_() {
  return 't' + Utilities.getUuid().replace(/-/g, '').slice(0, 12);
}

function newToken_() {
  return Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '').slice(0, 8);
}
