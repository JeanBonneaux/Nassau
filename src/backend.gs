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
 * API (every call needs the token, in the JSON body or as ?token=...):
 *   POST {source, app, title, subtitle, body}       a notification to parse and store
 *   POST {source:'applepay', amount, merchant, card} fields already split (Wallet automation)
 *   POST {action:'add'|'update'|'delete'|'rule'|'settings', ...}   used by the dashboard
 *   GET  ?action=list | ?action=ping
 */

var VERSION = '0.1.0';
var TX_SHEET = 'Transactions';
var IGNORED_SHEET = 'Ignored';
var RULES_SHEET = 'Rules';
var TX_COLS = ['date', 'amount', 'currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id', 'captured_at'];
var TX_FORMATS = ['yyyy-mm-dd hh:mm', '0.00', '@', '@', '@', '@', '@', '@', '@', '@', '@', '@', 'yyyy-mm-dd hh:mm:ss'];
var IGNORED_COLS = ['captured_at', 'source', 'reason', 'raw'];
var IGNORED_FORMATS = ['yyyy-mm-dd hh:mm:ss', '@', '@', '@'];
var RULES_COLS = ['pattern', 'category'];
var IGNORED_MAX = 1000;                    // older ignored notifications are trimmed
var DUP_WINDOW_MS = 30 * 60 * 1000;        // same amount from two different sources within 30 min = duplicate
var EXACT_WINDOW_MS = 10 * 60 * 1000;      // same text from the same source within 10 min = already logged
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
  var r;
  var raw;
  if (structured) {
    r = SpendParser.fromFields({ amount: b.amount, merchant: b.merchant, card: b.card, currency: b.currency, type: b.type },
      { defaultCurrency: cur, rules: rules });
    raw = [str_(b.merchant, 100), str_(b.amount, 40), str_(b.card, 60)].filter(String).join(' | ');
  } else {
    r = SpendParser.parse({ title: title, subtitle: subtitle, body: text, app: app }, { defaultCurrency: cur, rules: rules });
    raw = [title, subtitle, text].filter(String).join(' | ');
  }

  if (r.kind !== 'transaction') {
    appendIgnored_(ss, { captured_at: new Date(), source: source, reason: r.reason, raw: raw });
    return { ok: true, status: 'ignored', reason: r.reason, message: 'Not a transaction (' + r.reason + ')' };
  }

  var tx = {
    id: newId_(), date: when_(b.date), amount: SpendParser.signedAmount(r.amount, r.type), currency: r.currency,
    merchant: r.merchant, category: r.category, type: r.type, card: r.card, status: r.status, note: '',
    source: source, raw: raw, captured_at: new Date()
  };
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
  var dup = findDuplicate_(readTx_(sheet, 200), tx);
  if (dup && dup.exact) return { ok: true, status: 'exists', tx: out_(dup.row, cur), message: 'Already logged' };
  if (dup) {
    tx.status = 'duplicate';
    tx.note = 'Possible duplicate of ' + (dup.row.merchant || 'an earlier transaction') + ' (' + dup.row.source + ')';
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
    source: str_(t.source || 'manual', 30), raw: str_(t.raw, 2000), captured_at: new Date()
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
  var sheet = sheet_(ss, TX_SHEET, TX_COLS);
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
  return { ok: true, version: VERSION, parser: SpendParser.VERSION, currency: currency_() };
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
  ['currency', 'merchant', 'category', 'type', 'card', 'status', 'note', 'source', 'raw', 'id'].forEach(function (k) {
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

// Same text again from the same source = the automation fired twice. Same amount from another
// source (Apple Pay automation + bank notification) = one purchase seen twice.
function findDuplicate_(rows, tx) {
  var t = tx.date.getTime();
  for (var i = rows.length - 1; i >= 0; i--) {
    var r = rows[i];
    if (r.status === 'duplicate' || !r.date) continue;
    if (Math.abs(r.amount - tx.amount) > 0.005 || (r.currency || tx.currency) !== tx.currency) continue;
    var dt = Math.abs(r.date.getTime() - t);
    if (r.source === tx.source && r.raw && r.raw === tx.raw && dt < EXACT_WINDOW_MS) return { exact: true, row: r };
    var da = cardDigits_(r.card);
    var db = cardDigits_(tx.card);
    if (r.source !== tx.source && dt < DUP_WINDOW_MS && !(da && db && da !== db)) return { exact: false, row: r };
  }
  return null;
}

/* ------------------------------------------------------------------ small helpers */

function out_(o, cur) {
  var type = o.type || (o.amount < 0 ? 'refund' : 'purchase');
  return {
    id: o.id, date: o.date ? o.date.toISOString() : null, amount: Math.round(o.amount * 100) / 100,
    currency: o.currency || cur, merchant: o.merchant || '', category: o.category || 'Other', type: type,
    card: o.card || '', status: o.status || 'ok', note: o.note || '', source: o.source || 'sheet', raw: o.raw || '',
    captured_at: o.captured_at ? o.captured_at.toISOString() : null
  };
}

function message_(tx) {
  var s = (tx.amount < 0 ? '+' : '') + Math.abs(tx.amount).toFixed(2) + ' ' + tx.currency + ' · ' + (tx.merchant || '?') + ' · ' + tx.category;
  if (tx.status === 'review') s += ' (check it)';
  if (tx.status === 'duplicate') s += ' (possible duplicate, not counted)';
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
