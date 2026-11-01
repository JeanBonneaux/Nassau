// In-memory stand-in for the Google Apps Script services the backend uses, so the real backend
// code can run under Node for tests and for the local dev server. It is strict on purpose:
// mismatched range sizes and non-cell values throw, like Sheets does.
import vm from 'node:vm';
import fs from 'node:fs';
import crypto from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

function cell(v) {
  if (v === null || v === undefined) return '';
  if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') return v;
  if (typeof v.getTime === 'function') return new Date(v.getTime());
  throw new Error('Sheets cannot store ' + Object.prototype.toString.call(v));
}

class Range {
  constructor(sheet, row, col, nr, nc) { Object.assign(this, { sheet, row, col, nr, nc }); }
  getValues() {
    const out = [];
    for (let r = 0; r < this.nr; r++) {
      const src = this.sheet.rows[this.row - 1 + r] || [];
      const line = [];
      for (let c = 0; c < this.nc; c++) {
        const v = src[this.col - 1 + c];
        line.push(v === undefined ? '' : v instanceof Date ? new Date(v.getTime()) : v);
      }
      out.push(line);
    }
    return out;
  }
  setValues(vals) {
    if (!Array.isArray(vals) || vals.length !== this.nr || vals.some((v) => !Array.isArray(v) || v.length !== this.nc)) {
      throw new Error(`setValues: data does not match the range ${this.nr}x${this.nc}`);
    }
    for (let r = 0; r < this.nr; r++) {
      const idx = this.row - 1 + r;
      while (this.sheet.rows.length <= idx) this.sheet.rows.push([]);
      for (let c = 0; c < this.nc; c++) this.sheet.rows[idx][this.col - 1 + c] = cell(vals[r][c]);
    }
    return this;
  }
  setValue(v) { return this.setValues([[v]]); }
  getValue() { return this.getValues()[0][0]; }
  clearContent() { return this.setValues(Array.from({ length: this.nr }, () => Array(this.nc).fill(''))); }
  setNumberFormats(f) {
    if (!Array.isArray(f) || f.length !== this.nr || f.some((x) => x.length !== this.nc)) {
      throw new Error(`setNumberFormats: formats do not match the range ${this.nr}x${this.nc}`);
    }
    return this;
  }
  setNumberFormat() { return this; }
  setFontWeight() { return this; }
}

class Sheet {
  constructor(name) { this.name = name; this.rows = []; }
  getName() { return this.name; }
  getLastRow() {
    for (let i = this.rows.length - 1; i >= 0; i--) {
      if ((this.rows[i] || []).some((v) => v !== '' && v !== undefined)) return i + 1;
    }
    return 0;
  }
  getLastColumn() { return Math.max(0, ...this.rows.map((r) => r.length)); }
  getRange(row, col, nr = 1, nc = 1) {
    if (typeof row !== 'number') throw new Error('mock supports numeric ranges only');
    if (row < 1 || col < 1 || nr < 1 || nc < 1) throw new Error(`invalid range ${row},${col},${nr},${nc}`);
    return new Range(this, row, col, nr, nc);
  }
  deleteRow(r) {
    if (r < 1 || r > this.getLastRow()) throw new Error(`deleteRow(${r}) out of range`);
    this.rows.splice(r - 1, 1);
  }
  deleteRows(r, n) { this.rows.splice(r - 1, n); }
  setFrozenRows() {}
  // Test helper: the data rows as objects keyed by the header row.
  objects() {
    const [header = [], ...rest] = this.rows.slice(0, this.getLastRow());
    return rest.map((r) => Object.fromEntries(header.map((h, i) => [h, r[i] === undefined ? '' : r[i]])));
  }
}

// Minimal Utilities.formatDate: the patterns the backend uses, in a fixed time zone.
function formatDate(date, tz, pattern) {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: tz, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', weekday: 'short'
  }).formatToParts(date).map((p) => [p.type, p.value]));
  const weekday = { Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6, Sun: 7 }[parts.weekday];
  return pattern
    .replace('yyyy', parts.year).replace('MM', parts.month).replace('dd', parts.day).replace('HH', parts.hour).replace('mm', parts.minute)
    .replace(/\bH\b/, String(Number(parts.hour))).replace('u', String(weekday));
}

/** Loads apps-script/Spending.gs (the file pasted into Apps Script) into a sandbox with mocked services. */
export function loadBackend({ scriptPath = path.join(ROOT, 'apps-script/Spending.gs'), locale = 'fr_CA', webAppUrl = 'https://script.google.com/macros/s/TEST/exec' } = {}) {
  const sheets = new Map([['Sheet1', new Sheet('Sheet1')]]);
  const props = new Map();
  const logs = [];
  const fetches = [];
  const mails = [];
  const triggers = [];
  const cache = new Map();
  const labels = new Map();
  let fetchHandler = null;
  let lockBusy = false;
  let now = null;
  let inbox = []; // { id, from, subject, body, date, labels: Set }
  const ss = {
    getId: () => 'SHEET_ID',
    getUrl: () => 'https://docs.google.com/spreadsheets/d/SHEET_ID/edit',
    getSpreadsheetLocale: () => locale,
    getSheetByName: (n) => sheets.get(n) || null,
    insertSheet: (n) => {
      if (sheets.has(n)) throw new Error(`sheet ${n} exists`);
      const s = new Sheet(n);
      sheets.set(n, s);
      return s;
    },
    getSheets: () => [...sheets.values()],
    deleteSheet: (s) => { sheets.delete(s.getName()); }
  };
  const message = (m) => ({
    getId: () => m.id, getFrom: () => m.from, getSubject: () => m.subject, getPlainBody: () => m.body, getDate: () => new Date(m.date)
  });
  const thread = (ms) => ({
    getMessages: () => ms.map(message),
    addLabel: (label) => { ms.forEach((m) => m.labels.add(label.getName())); }
  });
  const context = {
    SpreadsheetApp: {
      getActiveSpreadsheet: () => ss,
      openById: (id) => { if (id !== 'SHEET_ID') throw new Error('no spreadsheet ' + id); return ss; }
    },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: (k) => (props.has(k) ? props.get(k) : null),
        setProperty(k, v) { props.set(k, String(v)); return this; },
        deleteProperty(k) { props.delete(k); return this; },
        getProperties: () => Object.fromEntries(props)
      })
    },
    ContentService: {
      MimeType: { JSON: 'application/json', TEXT: 'text/plain' },
      createTextOutput: (s) => ({
        content: String(s), mime: 'text/plain',
        setMimeType(m) { this.mime = m; return this; },
        getContent() { return this.content; }
      })
    },
    Utilities: {
      getUuid: () => crypto.randomUUID(),
      formatDate,
      newBlob: (s) => ({ getBytes: () => [...Buffer.from(String(s), 'utf8')] }),
      base64EncodeWebSafe: (bytes) => Buffer.from(bytes).toString('base64url')
    },
    // Network calls are refused unless a test installs a handler with onFetch().
    UrlFetchApp: {
      fetch: (url, params = {}) => {
        const call = { url, params, body: params.payload ? JSON.parse(params.payload) : null };
        fetches.push(call);
        if (!fetchHandler) throw new Error('UrlFetchApp: no network in the mock');
        const { code = 200, body = {} } = fetchHandler(call) || {};
        const text = typeof body === 'string' ? body : JSON.stringify(body);
        return { getResponseCode: () => code, getContentText: () => text };
      }
    },
    LockService: {
      getScriptLock: () => ({
        waitLock() { if (lockBusy) throw new Error('Lock timeout'); },
        tryLock: () => !lockBusy,
        releaseLock() {}
      })
    },
    ScriptApp: {
      getProjectTriggers: () => triggers.slice(),
      deleteTrigger: (t) => { const i = triggers.indexOf(t); if (i >= 0) triggers.splice(i, 1); },
      newTrigger: (fn) => ({
        timeBased: () => ({ everyMinutes: (n) => ({ create: () => { const t = { getHandlerFunction: () => fn, minutes: n }; triggers.push(t); return t; } }) })
      }),
      getService: () => ({ getUrl: () => webAppUrl })
    },
    MailApp: {
      sendEmail: (o) => { mails.push(o); },
      getRemainingDailyQuota: () => 100 - mails.length
    },
    GmailApp: {
      getUserLabelByName: (n) => labels.get(n) || null,
      createLabel: (n) => { const l = { getName: () => n }; labels.set(n, l); return l; },
      search: (query, start, max) => {
        // The mock understands only "-label:X". Like Gmail, messages with the same subject form one
        // conversation, and a conversation matches when any of its messages lacks the label; the whole
        // conversation (every message) is returned.
        const m = /-label:(\S+)/.exec(query);
        const excluded = m ? m[1] : null;
        const bySubject = new Map();
        inbox.forEach((msg) => { const k = msg.subject; if (!bySubject.has(k)) bySubject.set(k, []); bySubject.get(k).push(msg); });
        const hits = [...bySubject.values()].filter((ms) => !excluded || ms.some((msg) => !msg.labels.has(excluded)));
        return hits.slice(start, start + max).map((ms) => thread(ms));
      }
    },
    CacheService: {
      getScriptCache: () => ({ get: (k) => (cache.has(k) ? cache.get(k) : null), put: (k, v) => { cache.set(k, v); } })
    },
    Session: {
      getEffectiveUser: () => ({ getEmail: () => 'moi@example.com' }),
      getScriptTimeZone: () => 'America/Toronto'
    },
    Logger: { log: (...a) => { logs.push(a.join(' ')); } },
    console
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(scriptPath, 'utf8'), context, { filename: 'Spending.gs' });
  // Tests can freeze the clock.
  const realNow = context.now_;
  context.now_ = () => (now ? new Date(now.getTime()) : realNow());

  const unwrap = (out) => {
    if (out.mime !== 'application/json') throw new Error('response is not JSON');
    return JSON.parse(out.getContent());
  };
  return {
    context, sheets, props, logs, ss, fetches, mails, triggers, cache, labels,
    onFetch: (handler) => { fetchHandler = handler; },
    setLockBusy: (busy) => { lockBusy = busy; },
    setNow: (d) => { now = d ? new Date(d) : null; },
    setInbox: (messages) => { inbox = messages.map((m, i) => ({ id: m.id || 'msg' + i, labels: new Set(), ...m })); },
    addMail: (m) => { inbox.push({ id: m.id || 'msg' + inbox.length, labels: new Set(), ...m }); },
    inbox: () => inbox,
    sheet: (name) => sheets.get(name),
    setup: () => context.setup(),
    get: (parameter = {}) => unwrap(context.doGet({ parameter })),
    post: (body, parameter = {}) => unwrap(context.doPost({
      postData: { contents: typeof body === 'string' ? body : JSON.stringify(body), type: typeof body === 'string' ? 'text/plain' : 'application/json' },
      parameter
    })),
    postForm: (fields) => unwrap(context.doPost({
      postData: { contents: new URLSearchParams(fields).toString(), type: 'application/x-www-form-urlencoded' },
      parameter: fields
    })),
    // Raw doGet/doPost for the dev server.
    doGet: (e) => context.doGet(e),
    doPost: (e) => context.doPost(e)
  };
}
