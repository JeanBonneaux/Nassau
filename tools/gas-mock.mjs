// In-memory stand-in for the Google Apps Script services Code.gs uses, so the real backend
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

/** Loads src/parser.js + apps-script/Code.gs into a sandbox with mocked services. */
export function loadBackend({ parserPath = path.join(ROOT, 'src/parser.js'), codePath = path.join(ROOT, 'apps-script/Code.gs') } = {}) {
  const sheets = new Map([['Sheet1', new Sheet('Sheet1')]]);
  const props = new Map();
  const logs = [];
  const ss = {
    getId: () => 'SHEET_ID',
    getUrl: () => 'https://docs.google.com/spreadsheets/d/SHEET_ID/edit',
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
  const context = {
    SpreadsheetApp: {
      getActiveSpreadsheet: () => ss,
      openById: (id) => { if (id !== 'SHEET_ID') throw new Error('no spreadsheet ' + id); return ss; }
    },
    PropertiesService: {
      getScriptProperties: () => ({
        getProperty: (k) => (props.has(k) ? props.get(k) : null),
        setProperty(k, v) { props.set(k, String(v)); return this; },
        deleteProperty(k) { props.delete(k); return this; }
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
    Utilities: { getUuid: () => crypto.randomUUID() },
    LockService: { getScriptLock: () => ({ waitLock() {}, tryLock: () => true, releaseLock() {} }) },
    Logger: { log: (...a) => { logs.push(a.join(' ')); } },
    console
  };
  vm.createContext(context);
  const src = fs.readFileSync(parserPath, 'utf8') + '\n;\n' + fs.readFileSync(codePath, 'utf8');
  vm.runInContext(src, context, { filename: 'apps-script' });

  const unwrap = (out) => {
    if (out.mime !== 'application/json') throw new Error('response is not JSON');
    return JSON.parse(out.getContent());
  };
  return {
    context, sheets, props, logs, ss,
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
