/*
 * SpendQR: a small, dependency-free QR code generator (ISO/IEC 18004, model 2).
 *
 * The dashboard uses it to show the "setup link" as a QR code that an iPhone camera can scan.
 * Byte mode only (the text is encoded as UTF-8, without an ECI header, which is what phone
 * readers expect), versions 1 to 25, error-correction levels L/M/Q/H, automatic mask selection
 * with the standard penalty rules.
 * Plain JavaScript, no dependencies, no modules: it defines one global, `SpendQR`.
 *
 *   SpendQR.encode(text, { ecl: 'M' })        -> { size, modules, version, ecl, mask }
 *   SpendQR.svg(text, { ecl: 'M', px: 240 })  -> '<svg ...>...</svg>'
 *
 * `modules[row][col]` is true for a dark module. If the text does not fit at the requested
 * level (default 'M'), level 'L' is used instead; if it does not fit in version 25-L, encode throws.
 */
var SpendQR = (function () {
  'use strict';

  var MAX_VERSION = 25;
  var ECL_INDEX = { L: 0, M: 1, Q: 2, H: 3 };
  // The 2-bit level indicator written into the format information (note: not in L, M, Q, H order).
  var ECL_FORMAT_BITS = { L: 1, M: 0, Q: 3, H: 2 };

  /* Error-correction structure (ISO/IEC 18004 Table 9), indexed [level][version], version 0 unused.
   * EC_PER_BLOCK: EC codewords per block (same for every block of a symbol).
   * NUM_BLOCKS: number of blocks. When the data codewords do not split evenly, the last
   * (total % blocks) blocks carry one extra data codeword ("long" blocks). */
  var EC_PER_BLOCK = [
    [0, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28, 28, 28, 30, 30, 26],
    [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26, 26, 28, 28, 28, 28],
    [0, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30, 28, 30, 30, 30, 30],
    [0, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28, 30, 24, 30, 30, 30]
  ];
  var NUM_BLOCKS = [
    [0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8, 8, 9, 9, 10, 12],
    [0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16, 17, 17, 18, 20, 21],
    [0, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20, 23, 23, 25, 27, 29],
    [0, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25, 25, 34, 30, 32, 35]
  ];

  /* ------------------------------------------------------------------ capacity */

  // Number of modules left for data + EC after all function patterns (includes remainder bits).
  function rawDataModules(ver) {
    var result = (16 * ver + 128) * ver + 64; // n*n minus finders, separators, timing, format
    if (ver >= 2) {
      var numAlign = Math.floor(ver / 7) + 2;
      result -= (25 * numAlign - 10) * numAlign - 55; // alignment patterns (minus timing overlap)
      if (ver >= 7) result -= 36; // two 6x3 version information blocks
    }
    return result;
  }

  function numDataCodewords(ver, ecl) {
    var e = ECL_INDEX[ecl];
    return Math.floor(rawDataModules(ver) / 8) - EC_PER_BLOCK[e][ver] * NUM_BLOCKS[e][ver];
  }

  // Byte-mode character count indicator: 8 bits up to version 9, 16 bits from version 10.
  function countBits(ver) { return ver < 10 ? 8 : 16; }

  // Maximum number of bytes that fit in byte mode.
  function capacity(ver, ecl) {
    return Math.floor((numDataCodewords(ver, ecl) * 8 - 4 - countBits(ver)) / 8);
  }

  function pickVersion(len, ecl) {
    for (var v = 1; v <= MAX_VERSION; v++) if (len <= capacity(v, ecl)) return v;
    return 0;
  }

  /* ------------------------------------------------------------------ data */

  function utf8(s) {
    var out = [];
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c >= 0xd800 && c < 0xe000) { // surrogates: combine a valid pair, replace a lone one
        var d = i + 1 < s.length ? s.charCodeAt(i + 1) : 0;
        if (c < 0xdc00 && d >= 0xdc00 && d < 0xe000) { c = 0x10000 + ((c - 0xd800) << 10) + (d - 0xdc00); i++; }
        else c = 0xfffd;
      }
      if (c < 0x80) out.push(c);
      else if (c < 0x800) out.push(0xc0 | c >> 6, 0x80 | c & 63);
      else if (c < 0x10000) out.push(0xe0 | c >> 12, 0x80 | c >> 6 & 63, 0x80 | c & 63);
      else out.push(0xf0 | c >> 18, 0x80 | c >> 12 & 63, 0x80 | c >> 6 & 63, 0x80 | c & 63);
    }
    return out;
  }

  // Mode indicator, count, data, terminator, bit padding, then pad codewords 0xEC 0x11 ...
  function dataCodewords(bytes, ver, ecl) {
    var cap = numDataCodewords(ver, ecl) * 8, bits = [], i;
    function put(val, len) { for (var j = len - 1; j >= 0; j--) bits.push((val >>> j) & 1); }
    put(4, 4); // 0100 = byte mode
    put(bytes.length, countBits(ver));
    for (i = 0; i < bytes.length; i++) put(bytes[i], 8);
    put(0, Math.min(4, cap - bits.length)); // terminator: up to four 0 bits
    put(0, (8 - bits.length % 8) % 8);
    var out = [];
    for (i = 0; i < bits.length; i += 8) {
      var b = 0;
      for (var j = 0; j < 8; j++) b = b << 1 | bits[i + j];
      out.push(b);
    }
    for (var pad = 0xec; out.length < cap / 8; pad ^= 0xec ^ 0x11) out.push(pad);
    return out;
  }

  /* ------------------------------------------------------------------ Reed-Solomon over GF(256) */

  // Field generated by x^8 + x^4 + x^3 + x^2 + 1 (0x11D), primitive element 2.
  var EXP = [], LOG = [];
  (function () {
    for (var i = 0, x = 1; i < 255; i++) {
      EXP[i] = x; LOG[x] = i;
      x <<= 1; if (x & 0x100) x ^= 0x11d;
    }
    for (i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
  })();
  function gmul(a, b) { return a && b ? EXP[LOG[a] + LOG[b]] : 0; }

  // Generator polynomial (x - 2^0)(x - 2^1)...(x - 2^(degree-1)); coefficients high to low,
  // leading 1 omitted.
  function rsGenerator(degree) {
    var g = [];
    for (var i = 0; i < degree - 1; i++) g.push(0);
    g.push(1);
    for (var root = 1, k = 0; k < degree; k++, root = gmul(root, 2)) {
      for (var j = 0; j < degree; j++) {
        g[j] = gmul(g[j], root);
        if (j + 1 < degree) g[j] ^= g[j + 1];
      }
    }
    return g;
  }

  // EC codewords = remainder of data(x) * x^degree divided by the generator.
  function rsRemainder(data, gen) {
    var rem = gen.map(function () { return 0; });
    for (var i = 0; i < data.length; i++) {
      var factor = data[i] ^ rem.shift();
      rem.push(0);
      for (var j = 0; j < gen.length; j++) rem[j] ^= gmul(gen[j], factor);
    }
    return rem;
  }

  // Split into blocks, compute EC per block, then interleave: data codewords column by column
  // across blocks (long blocks contribute their extra codeword last), then EC codewords likewise.
  function addErrorCorrection(data, ver, ecl) {
    var e = ECL_INDEX[ecl], numBlocks = NUM_BLOCKS[e][ver], ecLen = EC_PER_BLOCK[e][ver];
    var total = Math.floor(rawDataModules(ver) / 8);
    var numShort = numBlocks - total % numBlocks;
    var shortData = Math.floor(total / numBlocks) - ecLen;
    var gen = rsGenerator(ecLen), blocks = [], k = 0, i, j;
    for (i = 0; i < numBlocks; i++) {
      var d = data.slice(k, k += shortData + (i < numShort ? 0 : 1));
      blocks.push({ data: d, ec: rsRemainder(d, gen) });
    }
    var out = [];
    for (i = 0; i <= shortData; i++) {
      for (j = 0; j < numBlocks; j++) if (i < blocks[j].data.length) out.push(blocks[j].data[i]);
    }
    for (i = 0; i < ecLen; i++) for (j = 0; j < numBlocks; j++) out.push(blocks[j].ec[i]);
    return out;
  }

  /* ------------------------------------------------------------------ matrix */

  function grid(n) {
    var g = [];
    for (var r = 0; r < n; r++) { g.push([]); for (var c = 0; c < n; c++) g[r].push(false); }
    return g;
  }

  // Centre coordinates of the alignment patterns (same list for rows and columns).
  function alignmentPositions(ver) {
    if (ver === 1) return [];
    var num = Math.floor(ver / 7) + 2, size = 17 + 4 * ver;
    var step = Math.ceil((ver * 4 + 4) / (num * 2 - 2)) * 2; // even spacing (v32 is special, n/a)
    var pos = [6];
    for (var p = size - 7; pos.length < num; p -= step) pos.splice(1, 0, p);
    return pos;
  }

  function drawFunctionPatterns(m, f, ver) {
    var n = m.length, i, j, dr, dc;
    function set(r, c, v) { m[r][c] = v; f[r][c] = true; }
    for (i = 0; i < n; i++) { set(6, i, i % 2 === 0); set(i, 6, i % 2 === 0); } // timing
    // Finder patterns with their separators: rings at distance 0-1 and 3 are dark, 2 and 4 light.
    [[3, 3], [3, n - 4], [n - 4, 3]].forEach(function (p) {
      for (dr = -4; dr <= 4; dr++) for (dc = -4; dc <= 4; dc++) {
        var r = p[0] + dr, c = p[1] + dc, d = Math.max(Math.abs(dr), Math.abs(dc));
        if (r >= 0 && r < n && c >= 0 && c < n) set(r, c, d !== 2 && d !== 4);
      }
    });
    // Alignment patterns at every pair of positions, except the three finder corners.
    var pos = alignmentPositions(ver), k = pos.length;
    for (i = 0; i < k; i++) for (j = 0; j < k; j++) {
      if ((i === 0 && j === 0) || (i === 0 && j === k - 1) || (i === k - 1 && j === 0)) continue;
      for (dr = -2; dr <= 2; dr++) for (dc = -2; dc <= 2; dc++) {
        set(pos[i] + dr, pos[j] + dc, Math.max(Math.abs(dr), Math.abs(dc)) !== 1);
      }
    }
    drawFormat(m, f, 'M', 0); // reserves the format areas (and the dark module); redrawn per mask
    if (ver >= 7) {
      // Version information: 6-bit version + 12-bit BCH(18,6) remainder, generator 0x1F25.
      var rem = ver;
      for (i = 0; i < 12; i++) rem = (rem << 1) ^ ((rem >>> 11) * 0x1f25);
      var bits = ver << 12 | rem;
      for (i = 0; i < 18; i++) {
        var bit = ((bits >>> i) & 1) === 1, a = n - 11 + i % 3, b = Math.floor(i / 3);
        set(b, a, bit); // top-right block: rows 0-5, columns n-11..n-9
        set(a, b, bit); // bottom-left block: the transpose
      }
    }
  }

  // Format information: 2-bit level + 3-bit mask, BCH(15,5) with generator 0x537, XOR 0x5412
  // (so it is never all light). Bit 0 is the least significant bit.
  function drawFormat(m, f, ecl, mask) {
    var n = m.length, data = ECL_FORMAT_BITS[ecl] << 3 | mask, rem = data, i;
    for (i = 0; i < 10; i++) rem = (rem << 1) ^ ((rem >>> 9) * 0x537);
    var bits = (data << 10 | rem) ^ 0x5412;
    function set(r, c, k) { m[r][c] = ((bits >>> k) & 1) === 1; f[r][c] = true; }
    // Copy 1, around the top-left finder: bits 0-7 down column 8 (skipping timing row 6),
    // then bits 8-14 leftwards along row 8 (skipping timing column 6).
    for (i = 0; i < 6; i++) set(i, 8, i);
    set(7, 8, 6); set(8, 8, 7); set(8, 7, 8);
    for (i = 9; i < 15; i++) set(8, 14 - i, i);
    // Copy 2, split: bits 0-7 along row 8 from the right edge, bits 8-14 up column 8 to the bottom.
    for (i = 0; i < 8; i++) set(8, n - 1 - i, i);
    for (i = 8; i < 15; i++) set(n - 15 + i, 8, i);
    m[n - 8][8] = true; f[n - 8][8] = true; // the "dark module", always dark
  }

  // Codeword bits go in two-column strips from the right edge, alternating upward and downward,
  // skipping function modules. Leftover remainder bits stay light (they are masked like data).
  function placeData(m, f, codewords) {
    var n = m.length, i = 0, total = codewords.length * 8;
    for (var right = n - 1; right >= 1; right -= 2) {
      if (right === 6) right = 5; // the vertical timing column is not part of any strip
      var upward = ((right + 1) & 2) === 0;
      for (var v = 0; v < n; v++) {
        var r = upward ? n - 1 - v : v;
        for (var j = 0; j < 2; j++) {
          var c = right - j;
          if (!f[r][c] && i < total) {
            m[r][c] = ((codewords[i >>> 3] >>> (7 - (i & 7))) & 1) === 1;
            i++;
          }
        }
      }
    }
  }

  // Mask conditions (r = row, c = column); where true, a data module is inverted.
  var MASKS = [
    function (r, c) { return (r + c) % 2 === 0; },
    function (r) { return r % 2 === 0; },
    function (r, c) { return c % 3 === 0; },
    function (r, c) { return (r + c) % 3 === 0; },
    function (r, c) { return (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0; },
    function (r, c) { return (r * c) % 2 + (r * c) % 3 === 0; },
    function (r, c) { return ((r * c) % 2 + (r * c) % 3) % 2 === 0; },
    function (r, c) { return ((r + c) % 2 + (r * c) % 3) % 2 === 0; }
  ];

  function isLight(line, from, to) { // modules outside the symbol count as light (quiet zone)
    for (var i = Math.max(from, 0); i < Math.min(to, line.length); i++) if (line[i]) return false;
    return true;
  }

  // Standard penalty score (ISO/IEC 18004 7.8.3): N1=3, N2=3, N3=40, N4=10. Lower is better.
  function penalty(m) {
    var n = m.length, score = 0, dark = 0, a, i, j;
    for (a = 0; a < 2; a++) { // rows, then columns
      for (i = 0; i < n; i++) {
        var line = [];
        for (j = 0; j < n; j++) line.push(a ? m[j][i] : m[i][j]);
        // Rule 1: a run of 5+ same-colour modules scores 3, plus 1 per module beyond 5.
        for (var run = 1, k = 1; k <= n; k++) {
          if (k < n && line[k] === line[k - 1]) run++;
          else { if (run >= 5) score += run - 2; run = 1; }
        }
        // Rule 3: finder-like 1:1:3:1:1 (dark:light:dark:light:dark) with 4 light modules on a side.
        for (j = 0; j + 6 < n; j++) {
          if (line[j] && !line[j + 1] && line[j + 2] && line[j + 3] && line[j + 4] && !line[j + 5] &&
              line[j + 6] && (isLight(line, j - 4, j) || isLight(line, j + 7, j + 11))) score += 40;
        }
      }
    }
    for (i = 0; i < n; i++) {
      for (j = 0; j < n; j++) {
        if (m[i][j]) dark++;
        // Rule 2: every 2x2 block of one colour scores 3.
        if (i + 1 < n && j + 1 < n && m[i][j] === m[i][j + 1] && m[i][j] === m[i + 1][j] &&
            m[i][j] === m[i + 1][j + 1]) score += 3;
      }
    }
    // Rule 4: 10 points per full 5% step that the dark proportion deviates from 50%.
    score += 10 * Math.floor(Math.abs(dark * 20 / (n * n) - 10));
    return score;
  }

  /* ------------------------------------------------------------------ API */

  function encode(text, opts) {
    opts = opts || {};
    var bytes = utf8(String(text));
    var ecl = String(opts.ecl || 'M').toUpperCase();
    if (!Object.prototype.hasOwnProperty.call(ECL_INDEX, ecl)) {
      throw new Error('SpendQR: unknown error-correction level "' + opts.ecl + '"');
    }
    var version = pickVersion(bytes.length, ecl);
    if (!version && ecl !== 'L') { ecl = 'L'; version = pickVersion(bytes.length, ecl); }
    if (!version) {
      throw new Error('SpendQR: text too long for a QR code (' + bytes.length + ' bytes, max ' +
        capacity(MAX_VERSION, 'L') + ')');
    }

    var n = 17 + 4 * version, m = grid(n), f = grid(n);
    drawFunctionPatterns(m, f, version);
    placeData(m, f, addErrorCorrection(dataCodewords(bytes, version, ecl), version, ecl));

    var best = null, bestScore = Infinity, bestMask = 0;
    for (var mask = 0; mask < 8; mask++) {
      var cond = MASKS[mask];
      var t = m.map(function (row, r) {
        return row.map(function (v, c) { return f[r][c] ? v : v !== cond(r, c); });
      });
      drawFormat(t, f, ecl, mask);
      var s = penalty(t);
      if (s < bestScore) { best = t; bestScore = s; bestMask = mask; }
    }
    return { size: n, modules: best, version: version, ecl: ecl, mask: bestMask };
  }

  // SVG with a 4-module quiet zone; dark modules as one path of horizontal runs.
  function svg(text, opts) {
    opts = opts || {};
    var q = encode(text, opts), n = q.size, w = n + 8, d = '';
    for (var r = 0; r < n; r++) {
      for (var c = 0; c < n; c++) {
        if (!q.modules[r][c]) continue;
        var start = c;
        while (c + 1 < n && q.modules[r][c + 1]) c++;
        d += 'M' + (start + 4) + ' ' + (r + 4) + 'h' + (c - start + 1) + 'v1h-' + (c - start + 1) + 'z';
      }
    }
    var px = Number(opts.px), dims = px > 0 ? ' width="' + px + '" height="' + px + '"' : '';
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + w + ' ' + w + '"' + dims +
      ' shape-rendering="crispEdges"><rect width="' + w + '" height="' + w + '" fill="#fff"/>' +
      '<path fill="#000" d="' + d + '"/></svg>';
  }

  return {
    encode: encode,
    svg: svg,
    capacity: capacity,
    MAX_VERSION: MAX_VERSION
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SpendQR;
