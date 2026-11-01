// Tests for src/qr.js (SpendQR). Run with: node --test test/qr.test.mjs
//
// Three layers of checks:
//   1. Structural (always run): size, finder/timing/alignment patterns, dark module, format and
//      version information read back independently (ISO/IEC 18004 bit positions) and BCH-checked.
//   2. Round trip through an independent decoder, jsQR (run when jsQR can be loaded). The matrix
//      is rendered to an RGBA pixel buffer with a 4-module quiet zone and decoded.
//   3. Module-for-module comparison with the `qrcode` npm package forced to the same version, level
//      and mask (run when `qrcode` can be loaded). This catches any single misplaced module that
//      the decoder's own error correction would otherwise hide.
// Optional packages are looked up in the repo, then in $QR_TEST_MODULES, then /tmp/qrcheck/node_modules:
//   mkdir -p /tmp/qrcheck && cd /tmp/qrcheck && npm install --no-save jsqr qrcode
import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';

const require = createRequire(import.meta.url);
const SpendQR = require('../src/qr.js');

function optionalResolve(name) {
  const dirs = [process.env.QR_TEST_MODULES, '/tmp/qrcheck/node_modules'].filter(Boolean);
  for (const id of [name, ...dirs.map((dir) => path.join(dir, name))]) {
    try { return require.resolve(id); } catch { /* try the next location */ }
  }
  return null;
}
const JSQR_FILE = optionalResolve('jsqr');
const QRCODE_FILE = optionalResolve('qrcode');
const jsQR = JSQR_FILE && require(JSQR_FILE);
const QRCodeRef = QRCODE_FILE && require(QRCODE_FILE);

// jsQR (1.4.0 and earlier) has one wrong entry in its alignment table: version 23 is listed as
// [6, 30, 54, 74, 102], but ISO/IEC 18004 Annex E (and zxing, and the qrcode package) say
// [6, 30, 54, 78, 102]. So it misreads version-23 symbols from any encoder; at level L the damage
// exceeds the error correction and decoding fails. For version 23 only, decode with a copy of jsQR
// that has just that entry corrected (or with jsQR itself once it is fixed upstream).
const jsQRv23 = (() => {
  if (!jsQR) return null;
  const src = fs.readFileSync(JSQR_FILE, 'utf8');
  const bad = 'alignmentPatternCenters: [6, 30, 54, 74, 102]';
  if (!src.includes(bad)) return jsQR;
  const mod = { exports: {} };
  new Function('module', 'exports', src.replace(bad, 'alignmentPatternCenters: [6, 30, 54, 78, 102]'))(mod, mod.exports);
  return mod.exports.default || mod.exports;
})();
const NO_JSQR = !jsQR && 'jsQR not installed (cd /tmp/qrcheck && npm install --no-save jsqr)';
const NO_REF = !QRCodeRef && 'qrcode not installed (cd /tmp/qrcheck && npm install --no-save qrcode)';

/* ------------------------------------------------------------------ reference data (ISO/IEC 18004) */

// Byte-mode capacity, Table 7, versions 1..25 (index 0 unused).
const CAPACITY = {
  L: [0, 17, 32, 53, 78, 106, 134, 154, 192, 230, 271, 321, 367, 425, 458, 520, 586, 644, 718, 792, 858, 929, 1003, 1091, 1171, 1273],
  M: [0, 14, 26, 42, 62, 84, 106, 122, 152, 180, 213, 251, 287, 331, 362, 412, 450, 504, 560, 624, 666, 711, 779, 857, 911, 997],
  Q: [0, 11, 20, 32, 46, 60, 74, 86, 108, 130, 151, 177, 203, 241, 258, 292, 322, 364, 394, 442, 482, 509, 565, 611, 661, 715],
  H: [0, 7, 14, 24, 34, 44, 58, 64, 84, 98, 119, 137, 155, 177, 194, 220, 250, 280, 310, 338, 382, 403, 439, 461, 511, 535]
};
// Alignment pattern centre coordinates, Annex E.
const ALIGN = [null, [], [6, 18], [6, 22], [6, 26], [6, 30], [6, 34], [6, 22, 38], [6, 24, 42], [6, 26, 46],
  [6, 28, 50], [6, 30, 54], [6, 32, 58], [6, 34, 62], [6, 26, 46, 66], [6, 26, 48, 70], [6, 26, 50, 74],
  [6, 30, 54, 78], [6, 30, 56, 82], [6, 30, 58, 86], [6, 34, 62, 90], [6, 28, 50, 72, 94], [6, 26, 50, 74, 98],
  [6, 30, 54, 78, 102], [6, 28, 54, 80, 106], [6, 32, 58, 84, 110]];
// Version information bit streams, Annex D.
const VERSION_INFO = { 7: 0x07c94, 8: 0x085bc, 9: 0x09a99, 10: 0x0a4d3, 11: 0x0bbf6, 12: 0x0c762, 13: 0x0d847,
  14: 0x0e60d, 15: 0x0f928, 16: 0x10b78, 17: 0x1145d, 18: 0x12a17, 19: 0x13532, 20: 0x149a6, 21: 0x15683,
  22: 0x168c9, 23: 0x177ec, 24: 0x18ec4, 25: 0x191e1 };
const FINDER = ['1111111', '1000001', '1011101', '1011101', '1011101', '1000001', '1111111'];
const ALIGNMENT = ['11111', '10001', '10101', '10001', '11111'];

function expectedVersion(byteLength, ecl) {
  const v = CAPACITY[ecl].findIndex((cap, i) => i > 0 && cap >= byteLength);
  return v === -1 ? 0 : v;
}

/* ------------------------------------------------------------------ test texts */

const B64URL = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
function b64ish(n, seed) { // deterministic pseudo-random base64url characters
  let s = '', x = seed >>> 0;
  for (let i = 0; i < n; i++) { x = (Math.imul(x, 1103515245) + 12345) >>> 0; s += B64URL[x >>> 26]; }
  return s;
}

const URL_60 = 'https://example.com/s?k=' + b64ish(36, 5);
const URL_300 = (() => {
  const head = `https://script.google.com/macros/s/${b64ish(58, 7)}/exec?setup=v1.a-b_c${b64ish(20, 3)}#cfg=`;
  return head + b64ish(300 - head.length - 2, 11) + '==';
})();
const TEXT_1000 = Array.from({ length: 1000 }, (_, i) => String.fromCharCode(32 + (i * 37 + 11) % 95)).join('');
const ACCENTS = 'Dépenses: café crème 4,50 € · Montréal (Québec) — naïve façade, Ærøskøbing, ñandú, 東京 😀';

const utf8 = (s) => [...Buffer.from(s, 'utf8')];

// [label, text, requested level (undefined = default), expected level after any fallback]
const CASES = [
  ['HELLO default', 'HELLO', undefined, 'M'],
  ...['L', 'M', 'Q', 'H'].map((e) => ['HELLO ' + e, 'HELLO', e, e]),
  ...['L', 'M', 'Q', 'H'].map((e) => ['60-char URL ' + e, URL_60, e, e]),
  ['300-char URL default', URL_300, undefined, 'M'],
  ...['L', 'M', 'Q', 'H'].map((e) => ['300-char URL ' + e, URL_300, e, e]),
  ['1000-char L', TEXT_1000, 'L', 'L'],
  ['1000-char M (falls back to L)', TEXT_1000, 'M', 'L'],
  ['1000-char Q (falls back to L)', TEXT_1000, 'Q', 'L'],
  ['1000-char H (falls back to L)', TEXT_1000, 'H', 'L'],
  ...['L', 'M', 'Q', 'H'].map((e) => ['UTF-8 accents ' + e, ACCENTS, e, e])
];

/* ------------------------------------------------------------------ independent readers */

const bit = (m, r, c) => (m[r][c] ? 1 : 0);

// Polynomial remainder over GF(2).
function gf2Remainder(value, gen) {
  const deg = 31 - Math.clz32(gen);
  for (let i = 31 - Math.clz32(value); i >= deg; i--) if ((value >>> i) & 1) value ^= gen << (i - deg);
  return value;
}

// Both 15-bit format information copies, most significant bit first (the order decoders read them).
function readFormat(m) {
  const n = m.length;
  let a = 0, b = 0;
  for (let c = 0; c <= 5; c++) a = (a << 1) | bit(m, 8, c); // row 8, left of the timing column
  a = (a << 1) | bit(m, 8, 7);
  a = (a << 1) | bit(m, 8, 8);
  a = (a << 1) | bit(m, 7, 8);
  for (let r = 5; r >= 0; r--) a = (a << 1) | bit(m, r, 8); // column 8, above the timing row
  for (let r = n - 1; r >= n - 7; r--) b = (b << 1) | bit(m, r, 8); // column 8, bottom-left
  for (let c = n - 8; c < n; c++) b = (b << 1) | bit(m, 8, c); // row 8, top-right
  return [a, b];
}

function parseFormat(raw) {
  const v = raw ^ 0x5412;
  assert.equal(gf2Remainder(v, 0x537), 0, 'format information fails its BCH check');
  return { ecl: ['M', 'L', 'H', 'Q'][v >>> 13], mask: (v >>> 10) & 7 };
}

// Both 18-bit version information copies, most significant bit first.
function readVersionInfo(m) {
  const n = m.length;
  let a = 0, b = 0;
  for (let r = 5; r >= 0; r--) for (let c = n - 9; c >= n - 11; c--) a = (a << 1) | bit(m, r, c);
  for (let c = 5; c >= 0; c--) for (let r = n - 9; r >= n - 11; r--) b = (b << 1) | bit(m, r, c);
  return [a, b];
}

function assertPattern(m, r0, c0, rows, what) {
  rows.forEach((row, dr) => [...row].forEach((ch, dc) => {
    assert.equal(m[r0 + dr][c0 + dc], ch === '1', `${what}: module (${r0 + dr}, ${c0 + dc})`);
  }));
}

function checkStructure(q, { text, ecl }) {
  const bytes = utf8(text);
  const n = q.size, m = q.modules, v = (n - 17) / 4;
  assert.ok(Number.isInteger(v) && v >= 1 && v <= 25, `size ${n} is not 17 + 4·version`);
  assert.equal(q.version, v);
  assert.equal(n, 17 + 4 * q.version);
  assert.equal(m.length, n);
  m.forEach((row) => { assert.equal(row.length, n); row.forEach((x) => assert.equal(typeof x, 'boolean')); });
  assert.equal(q.ecl, ecl);
  assert.equal(q.version, expectedVersion(bytes.length, ecl), 'not the smallest version that fits');

  // Finder patterns, with their light separators.
  for (const [r0, c0] of [[0, 0], [0, n - 7], [n - 7, 0]]) {
    assertPattern(m, r0, c0, FINDER, 'finder');
    for (let i = -1; i <= 7; i++) {
      for (const [r, c] of [[r0 - 1, c0 + i], [r0 + 7, c0 + i], [r0 + i, c0 - 1], [r0 + i, c0 + 7]]) {
        if (r >= 0 && c >= 0 && r < n && c < n) assert.equal(m[r][c], false, `separator (${r}, ${c})`);
      }
    }
  }
  // Timing patterns.
  for (let i = 8; i < n - 8; i++) {
    assert.equal(m[6][i], i % 2 === 0, `timing row, column ${i}`);
    assert.equal(m[i][6], i % 2 === 0, `timing column, row ${i}`);
  }
  // Alignment patterns.
  const pos = ALIGN[v];
  for (const r of pos) for (const c of pos) {
    const overlapsFinder = (r === 6 && c === 6) || (r === 6 && c === n - 7) || (r === n - 7 && c === 6);
    if (!overlapsFinder) assertPattern(m, r - 2, c - 2, ALIGNMENT, 'alignment');
  }
  // Dark module.
  assert.equal(m[4 * v + 9][8], true, 'dark module');
  // Format information: two identical copies, valid BCH, matching level and mask.
  const [f1, f2] = readFormat(m);
  assert.equal(f1, f2, 'the two format information copies differ');
  assert.deepEqual(parseFormat(f1), { ecl: q.ecl, mask: q.mask });
  // Version information (version 7 and up): two identical copies equal to the spec value.
  if (v >= 7) {
    const [v1, v2] = readVersionInfo(m);
    assert.equal(v1, VERSION_INFO[v], 'version information (top right)');
    assert.equal(v2, VERSION_INFO[v], 'version information (bottom left)');
    assert.equal(gf2Remainder(v1, 0x1f25), 0);
  }
}

/* ------------------------------------------------------------------ decoding helpers */

function toRGBA(q, scale) {
  const w = (q.size + 8) * scale, px = new Uint8ClampedArray(w * w * 4).fill(255);
  for (let r = 0; r < q.size; r++) {
    for (let c = 0; c < q.size; c++) {
      if (!q.modules[r][c]) continue;
      for (let y = 0; y < scale; y++) {
        for (let x = 0; x < scale; x++) {
          const i = (((r + 4) * scale + y) * w + (c + 4) * scale + x) * 4;
          px[i] = px[i + 1] = px[i + 2] = 0;
        }
      }
    }
  }
  return { px, w };
}

function assertDecodes(q, text, scale = 8) {
  const { px, w } = toRGBA(q, scale);
  const decoder = q.version === 23 ? jsQRv23 : jsQR;
  const res = decoder(px, w, w, { inversionAttempts: 'dontInvert' });
  assert.ok(res, `jsQR could not decode version ${q.version}-${q.ecl}`);
  assert.equal(res.version, q.version);
  assert.deepEqual(res.binaryData, utf8(text));
  assert.equal(res.data, text);
}

function asciiText(len, seed) {
  return Array.from({ length: len }, (_, i) => String.fromCharCode(33 + (i * 7 + seed) % 94)).join('');
}

/* ------------------------------------------------------------------ tests */

test('test texts have the intended shape', () => {
  assert.equal(URL_60.length, 60);
  assert.equal(URL_300.length, 300);
  assert.match(URL_300, /^https:\/\/[A-Za-z0-9\-_.=?#/]+$/);
  for (const ch of '-_.=?#/') assert.ok(URL_300.includes(ch), `300-char URL lacks ${ch}`);
  assert.equal(TEXT_1000.length, 1000);
  assert.ok(utf8(ACCENTS).length > ACCENTS.length, 'accented text should need multi-byte UTF-8');
});

test('capacity matches the byte-mode table of the standard', () => {
  for (const e of ['L', 'M', 'Q', 'H']) {
    for (let v = 1; v <= 25; v++) assert.equal(SpendQR.capacity(v, e), CAPACITY[e][v], `${v}-${e}`);
  }
});

for (const [label, text, ecl, expectEcl] of CASES) {
  const opts = ecl ? { ecl } : undefined;

  test(`structure: ${label}`, () => {
    const q = SpendQR.encode(text, opts);
    checkStructure(q, { text, ecl: expectEcl });
  });

  test(`jsQR round trip: ${label}`, { skip: NO_JSQR }, () => {
    assertDecodes(SpendQR.encode(text, opts), text, 8);
  });
}

test('every version 1-25 at every level, filled to capacity: structure + jsQR round trip', () => {
  for (const e of ['L', 'M', 'Q', 'H']) {
    for (let v = 1; v <= 25; v++) {
      const text = asciiText(CAPACITY[e][v], v);
      const q = SpendQR.encode(text, { ecl: e });
      checkStructure(q, { text, ecl: e });
      if (jsQR) assertDecodes(q, text, 4);
      if (v < 25) assert.equal(SpendQR.encode(text + 'x', { ecl: e }).version, v + 1, `${v}-${e} + 1 byte`);
    }
  }
});

test('automatic fallback to L at the version 25 boundary, and the hard limit', () => {
  assert.deepEqual(pick(SpendQR.encode(asciiText(997, 1), { ecl: 'M' })), { version: 25, ecl: 'M' });
  assert.deepEqual(pick(SpendQR.encode(asciiText(998, 1), { ecl: 'M' })), { version: 22, ecl: 'L' });
  assert.deepEqual(pick(SpendQR.encode(asciiText(536, 1), { ecl: 'H' })), { version: 16, ecl: 'L' });
  assert.deepEqual(pick(SpendQR.encode(asciiText(1273, 1))), { version: 25, ecl: 'L' });
  assert.throws(() => SpendQR.encode(asciiText(1274, 1)), /too long/);
  assert.throws(() => SpendQR.encode(asciiText(1274, 1), { ecl: 'L' }), Error);
  assert.throws(() => SpendQR.encode('é'.repeat(637)), /too long/); // 1274 UTF-8 bytes
  assert.throws(() => SpendQR.encode('HELLO', { ecl: 'X' }), /error-correction level/);
  assert.equal(SpendQR.encode('HELLO', { ecl: 'q' }).ecl, 'Q');
  function pick(q) { return { version: q.version, ecl: q.ecl }; }
});

test('mask selection is deterministic and uses all patterns across inputs', () => {
  const a = SpendQR.encode(URL_300), b = SpendQR.encode(URL_300);
  assert.deepEqual(a, b);
  const masks = new Set();
  for (let i = 0; i < 60; i++) masks.add(SpendQR.encode(asciiText(40 + i, i)).mask);
  assert.equal(masks.size, 8, `masks used: ${[...masks].sort()}`);
});

test('matches the qrcode npm package module for module (same version, level, mask)', { skip: NO_REF }, () => {
  const texts = CASES.map((c) => [c[1], c[3]]); // the named texts, then every version/level full
  for (let v = 1; v <= 25; v++) for (const e of ['L', 'M', 'Q', 'H']) texts.push([asciiText(CAPACITY[e][v], v), e]);
  for (const [text, ecl] of texts) {
    const q = SpendQR.encode(text, { ecl });
    const ref = QRCodeRef.create([{ data: Buffer.from(text, 'utf8'), mode: 'byte' }],
      { errorCorrectionLevel: ecl, version: q.version, maskPattern: q.mask });
    assert.equal(ref.modules.size, q.size);
    for (let r = 0; r < q.size; r++) {
      for (let c = 0; c < q.size; c++) {
        assert.equal(q.modules[r][c], !!ref.modules.get(r, c), `${q.version}-${ecl} mask ${q.mask} at (${r}, ${c})`);
      }
    }
  }
});

test('svg: valid markup with viewBox, quiet zone, background and a single path', () => {
  const q = SpendQR.encode(URL_300);
  const s = SpendQR.svg(URL_300);
  const w = q.size + 8;
  assert.match(s, /^<svg [^>]*><rect [^>]*\/><path [^>]*\/><\/svg>$/);
  assert.ok(s.includes('xmlns="http://www.w3.org/2000/svg"'));
  assert.ok(s.includes(`viewBox="0 0 ${w} ${w}"`));
  assert.ok(s.includes('shape-rendering="crispEdges"'));
  assert.equal((s.match(/<path\b/g) || []).length, 1);
  assert.ok(s.includes(`<rect width="${w}" height="${w}" fill="#fff"/>`));
  const svgTag = s.slice(0, s.indexOf('>'));
  assert.ok(!/\b(width|height)=/.test(svgTag), 'no width/height by default');

  // Rebuild the matrix from the path: it must be exactly the encoded modules, offset by 4.
  const d = s.match(/<path [^>]*\bd="([^"]*)"/)[1];
  assert.match(d, /^(M\d+ \d+h\d+v1h-\d+z)+$/);
  const grid = Array.from({ length: q.size }, () => Array(q.size).fill(false));
  for (const [, x, y, len, back] of d.matchAll(/M(\d+) (\d+)h(\d+)v1h-(\d+)z/g)) {
    assert.equal(len, back);
    for (let i = 0; i < +len; i++) {
      const r = +y - 4, c = +x - 4 + i;
      assert.ok(r >= 0 && c >= 0 && r < q.size && c < q.size, 'path inside the quiet zone');
      assert.equal(grid[r][c], false, 'overlapping runs');
      grid[r][c] = true;
    }
  }
  assert.deepEqual(grid, q.modules);
});

test('svg: px option sets width and height; ecl option is honoured', () => {
  const s = SpendQR.svg('HELLO', { px: 240, ecl: 'H' });
  assert.ok(s.startsWith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 29 29" width="240" height="240"'));
  assert.notEqual(SpendQR.svg(URL_60, { ecl: 'L' }), SpendQR.svg(URL_60, { ecl: 'H' }));
});
