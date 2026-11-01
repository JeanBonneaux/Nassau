/*
 * SpendInsights: pure functions that turn the transaction list into insights:
 * clean merchant names, recurring charges, alerts at capture, month summaries,
 * budget pace, the last week and a weekly e-mail digest in French.
 *
 * One source, two consumers (like SpendParser): the Google Apps Script backend and the
 * dashboard. Plain JavaScript, no dependencies, no modules, no Intl: it defines one global,
 * `SpendInsights`. Nothing reads the clock: every function that needs "today" takes `now`.
 * Dates are calendar days in local time; a date-only string 'YYYY-MM-DD' is that local day.
 * Amounts are signed: positive = money out, negative = money back (refunds).
 */
var SpendInsights = (function () {
  'use strict';

  var DAY = 86400000;
  var SPENDING_TYPES = { purchase: true, refund: true, cash: true, fee: true };

  /* ------------------------------------------------------------------ helpers */

  function clean(s) {
    return String(s == null ? '' : s).replace(/[​-‍﻿]/g, '').replace(/\s+/g, ' ').trim();
  }
  function fold(s) {
    return String(s == null ? '' : s).normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  }
  function round2(n) { return Math.round(n * 100) / 100; }
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function amt(tx) { return Number(tx.amount) || 0; }
  function sum(list) { var t = 0; for (var i = 0; i < list.length; i++) t += amt(list[i]); return round2(t); }
  function median(a) {
    if (!a.length) return 0;
    var s = a.slice().sort(function (x, y) { return x - y; }), h = s.length >> 1;
    return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
  }
  function copy(o) {
    var r = {};
    for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) r[k] = o[k];
    return r;
  }
  function values(o) { return Object.keys(o).map(function (k) { return o[k]; }); }

  function toDate(v) {
    if (Object.prototype.toString.call(v) === '[object Date]') return new Date(v.getTime());
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v == null ? '' : v));
    return m ? new Date(+m[1], m[2] - 1, +m[3]) : new Date(v);
  }
  function isoDay(d) { d = toDate(d); return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  // Day number (days since 1970-01-01) of the local calendar day: DST-proof differences.
  function dayNo(d) { d = toDate(d); return Math.round(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()) / DAY); }
  function daysIn(y, m) { return new Date(y, m + 1, 0).getDate(); }
  function addDays(d, n) { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
  function addMonths(d, n) {
    var t = new Date(d.getFullYear(), d.getMonth() + n, 1);
    t.setDate(Math.min(d.getDate(), daysIn(t.getFullYear(), t.getMonth())));
    return t;
  }

  // Same rule as SpendParser.countsAsSpending (kept separate so this file stands alone).
  function counts(tx) {
    return !!tx && SPENDING_TYPES[tx.type] === true && tx.status !== 'duplicate' && tx.status !== 'excluded';
  }
  function inCurrency(tx, cur) { return !cur || !tx.currency || tx.currency === cur; }
  // Counting transactions in `cur` whose day number is in [from, to].
  function spendIn(txs, cur, from, to) {
    return (txs || []).filter(function (t) {
      if (!counts(t) || !inCurrency(t, cur)) return false;
      var n = dayNo(t.date);
      return n >= from && n <= to;
    });
  }
  function byDesc(field) { return function (a, b) { return b[field] - a[field]; }; }

  /* ------------------------------------------------------------------ merchants */

  var ACRONYMS = ['IGA', 'SAQ', 'SQDC', 'STM', 'STL', 'RTL', 'REM', 'EXO', 'BMR', 'MEC', 'LCBO', 'RBC', 'TD',
    'BMO', 'CIBC', 'KFC', 'A&W', 'H&M', 'VIA', 'NYT'];
  // Folded name (or its start, followed by a space) -> display name.
  var ALIASES = [['tim hortons', 'Tim Hortons'], ['iga extra', 'IGA'], ['uber trip', 'Uber'], ['uber eats', 'Uber Eats'],
    ['amazon.ca', 'Amazon'], ['amzn mktp', 'Amazon'], ['couche-tard', 'Couche-Tard'], ['couche tard', 'Couche-Tard'],
    ['jean coutu', 'Jean Coutu'], ['pjc', 'Jean Coutu'], ['netflix.com', 'Netflix'], ['spotify', 'Spotify'],
    ['google *youtube', 'YouTube']];
  // Payment-processor prefixes: what follows is the merchant; the name is used when nothing follows.
  var PREFIXES = [[/^SQ ?\*\s*/i, 'Square'], [/^TST ?\*\s*/i, 'Toast'], [/^(?:PAYPAL|PP) ?\*\s*/i, 'PayPal'],
    [/^(?:APL ?\*|APPLE\.COM\/BILL)\s*/i, 'Apple'], [/^AMZN MKTP(?: CA)? ?\*?\s*/i, 'Amazon'],
    [/^SP ?\*\s*/i, 'Shopify'], [/^SUMUP ?\*\s*/i, 'SumUp'], [/^(?:DD|DOORDASH) ?\*\s*/i, 'DoorDash']];
  var DOMAIN = /(?:https?:\/\/)?(?:www\.)?(?:[a-z0-9-]+\.)*([a-z0-9-]+)\.(?:com|ca|net|org|io|co|fr|tv|ai|app)\b(?:\/\S*)?/gi;
  var PROVINCE = /\s+(?:QC|ON|BC|AB|MB|SK|NS|NB|NL|PE|YT|NT|NU)$/;

  function alias(folded) {
    var variants = [folded.replace(/\s*\*\s*/g, ' *'), clean(folded.replace(/\*/g, ' '))];
    for (var i = 0; i < ALIASES.length; i++) {
      for (var j = 0; j < variants.length; j++) {
        var k = ALIASES[i][0], v = variants[j];
        if (v === k || v.indexOf(k + ' ') === 0) return ALIASES[i][1];
      }
    }
    return '';
  }

  function titleCase(s) {
    return s.split(' ').map(function (w) {
      if (ACRONYMS.indexOf(w.toUpperCase()) >= 0) return w.toUpperCase();
      return w.toLowerCase().replace(/(^|[-\/(])(\S)/g, function (all, p, c) { return p + c.toUpperCase(); });
    }).join(' ');
  }

  // "SQ *CAFE OLIMPICO 0042 MONTREAL QC" -> "Cafe Olimpico"; "TIM HORTONS #1234" -> "Tim Hortons".
  function canonicalMerchant(name) {
    var s = clean(name), fallback = '';
    if (!s) return '';
    var known = alias(fold(s));
    if (known) return known;
    s = s.replace(/^UBER ?\* ?/i, 'UBER ');
    for (var i = 0; i < PREFIXES.length; i++) {
      if (PREFIXES[i][0].test(s)) { fallback = PREFIXES[i][1]; s = s.replace(PREFIXES[i][0], ''); i = -1; }
    }
    if (fallback && /^[A-Z0-9]*\d[A-Z0-9]*$/i.test(s)) s = ''; // only a reference code follows the prefix
    s = s.replace(/\*\s*[A-Z0-9]*\d[A-Z0-9]*\s*$/i, '').replace(/\*/g, ' '); // trailing reference "*2K4XY"
    s = clean(s.replace(DOMAIN, ' ')) || clean(s).replace(DOMAIN, '$1'); // "help.uber.com" -> "uber"
    s = clean(s.replace(/#\s*\d+/g, ' ').replace(/\b\d{3}[- .]\d{3}[- .]\d{4}\b/g, ' ')); // store #, phone
    s = s.replace(/\s+(?:\d{3,}|0\d+)(?=\s|$)/g, ''); // store numbers: "0042", "23045" (never the first word)
    s = s.replace(/\s+CA$/, '');
    if (PROVINCE.test(s)) s = s.replace(PROVINCE, '').replace(/(\S)\s+[^\s\d]+$/, '$1'); // "... MONTREAL QC"
    s = clean(s.replace(/^[\s\-,.;:\/]+|[\s\-,.;:\/]+$/g, ''));
    if (!s) return fallback;
    if (!/[a-zß-ÿ]/.test(s) || !/[A-ZÀ-Þ]/.test(s)) s = titleCase(s); // ALL CAPS or all lower-case
    return alias(fold(s)) || s;
  }

  var keyCache = Object.create(null);
  function key(name) {
    var s = String(name == null ? '' : name);
    if (!(s in keyCache)) keyCache[s] = fold(canonicalMerchant(s));
    return keyCache[s];
  }

  /* ------------------------------------------------------------------ recurring charges */

  // maxLate: a series whose next charge is this many days late is considered ended.
  var PERIODS = [
    { name: 'weekly', min: 6, max: 8, minCount: 3, perMonth: 4.33, maxLate: 14 },
    { name: 'monthly', min: 26, max: 35, minCount: 2, perMonth: 1, maxLate: 45 },
    { name: 'yearly', min: 360, max: 370, minCount: 2, perMonth: 1 / 12, maxLate: 60 }
  ];
  function periodOf(name) { return PERIODS.filter(function (p) { return p.name === name; })[0] || PERIODS[1]; }
  function stable(a) { return Math.max.apply(null, a) <= Math.min.apply(null, a) * 1.05 + 0.005; }
  // All amounts within ±5 % of each other, or one price change (after ≥ 2 charges) that is stable again.
  function steady(a) {
    if (stable(a)) return true;
    for (var k = 2; k < a.length; k++) {
      var before = a.slice(0, k), after = a.slice(k), r = median(after) / median(before);
      if (stable(before) && stable(after) && r > 0.67 && r < 1.5) return true;
    }
    return false;
  }

  function recurring(txs, now, opts) {
    opts = opts || {};
    var cur = opts.currency || 'CAD', today = dayNo(now), groups = {}, out = [];
    (txs || []).forEach(function (t) {
      if (!counts(t) || t.type === 'refund' || amt(t) <= 0 || !inCurrency(t, cur)) return;
      var d = dayNo(t.date), k = key(t.merchant);
      if (k && d <= today) (groups[k] = groups[k] || []).push({ tx: t, day: d, amount: amt(t) });
    });
    Object.keys(groups).forEach(function (k) {
      var g = groups[k].sort(function (a, b) { return a.day - b.day; }), gaps = [];
      for (var i = 1; i < g.length; i++) gaps.push(g[i].day - g[i - 1].day);
      var p = PERIODS.filter(function (p) {
        var bad = gaps.filter(function (x) { return x < p.min || x > p.max; }).length;
        return g.length >= p.minCount && (bad === 0 || (bad === 1 && g.length >= 4));
      })[0];
      if (!p || !steady(g.map(function (e) { return e.amount; }))) return;
      var last = g[g.length - 1], prev = g[g.length - 2], lastDate = toDate(last.tx.date);
      var next = p.name === 'weekly' ? addDays(lastDate, 7) : addMonths(lastDate, p.name === 'monthly' ? 1 : 12);
      var late = today - dayNo(next);
      if (late > p.maxLate) return;
      out.push({
        merchant: canonicalMerchant(last.tx.merchant), key: k, amount: last.amount,
        avgAmount: round2(g.reduce(function (s, e) { return s + e.amount; }, 0) / g.length),
        period: p.name, count: g.length, lastDate: isoDay(lastDate), nextExpected: isoDay(next), overdue: late > 5,
        increased: last.amount >= prev.amount * 1.05 - 1e-9 ? { from: prev.amount, to: last.amount } : null,
        category: last.tx.category || '', monthly: round2(last.amount * p.perMonth)
      });
    });
    return out.sort(byDesc('monthly'));
  }

  function monthlyTotal(list) {
    return round2((list || []).reduce(function (s, r) { return s + r.amount * periodOf(r.period).perMonth; }, 0));
  }

  /* ------------------------------------------------------------------ alerts at capture */

  // `recent`: earlier transactions. Returns [] or some of 'large', 'new'.
  function flagAtCapture(tx, recent) {
    var flags = [], a = tx ? amt(tx) : 0;
    if (!counts(tx) || a <= 0) return flags;
    var prior = (recent || []).filter(function (t) { return t && t !== tx && (tx.id == null || t.id !== tx.id); });
    var buys = prior.filter(function (t) { return counts(t) && t.type === 'purchase' && amt(t) > 0 && inCurrency(t, tx.currency); })
      .sort(function (x, y) { return toDate(y.date) - toDate(x.date); }).slice(0, 60).map(amt);
    if (buys.length < 10) return a > 500 ? ['large'] : flags;
    var med = median(buys), k = key(tx.merchant);
    if (a > Math.max(4 * med, 100)) flags.push('large');
    if (k && a > 2 * med && !prior.some(function (t) { return key(t.merchant) === k; })) flags.push('new');
    return flags;
  }

  /* ------------------------------------------------------------------ months, pace, week */

  function monthTxs(txs, cur, y, m, lastDay) {
    return spendIn(txs, cur, dayNo(new Date(y, m, 1)), dayNo(new Date(y, m, Math.min(lastDay || 31, daysIn(y, m)))));
  }
  function elapsedDays(y, m, now) {
    var n = toDate(now);
    if (n.getFullYear() === y && n.getMonth() === m) return n.getDate();
    return y * 12 + m < n.getFullYear() * 12 + n.getMonth() ? daysIn(y, m) : 0;
  }

  function monthSummary(txs, currency, year, month, now) {
    var dim = daysIn(year, month), el = elapsedDays(year, month, now), cats = {}, merch = {};
    var list = monthTxs(txs, currency || 'CAD', year, month, el || dim), total = sum(list); // month to date
    list.forEach(function (t) {
      var c = t.category || 'Other', k = key(t.merchant);
      cats[c] = (cats[c] || 0) + amt(t);
      if (!k) return;
      var m = merch[k] = merch[k] || { merchant: canonicalMerchant(t.merchant), total: 0, count: 0 };
      m.total += amt(t);
      m.count++;
    });
    return {
      year: year, month: month, total: total, count: list.length,
      perDay: el ? round2(total / el) : 0,
      projected: el && el < dim ? round2(total / el * dim) : total,
      byCategory: Object.keys(cats).map(function (c) {
        return { category: c, total: round2(cats[c]), share: total > 0 ? Math.round(cats[c] / total * 1000) / 1000 : 0 };
      }).sort(byDesc('total')),
      topMerchants: values(merch).map(function (m) { m.total = round2(m.total); return m; }).sort(byDesc('total')).slice(0, 5),
      largest: list.filter(function (t) { return amt(t) > 0; }).sort(function (a, b) { return amt(b) - amt(a); }).slice(0, 3).map(copy)
    };
  }

  function compareMonths(txs, currency, year, month, now) {
    var n = toDate(now), cur = currency || 'CAD', py = month ? year : year - 1, pm = month ? month - 1 : 11;
    var inProgress = n.getFullYear() === year && n.getMonth() === month, cut = inProgress ? n.getDate() : 31;
    var a = monthTxs(txs, cur, year, month, cut), b = monthTxs(txs, cur, py, pm, cut), cats = {};
    function add(list, field) {
      list.forEach(function (t) {
        var c = t.category || 'Other';
        cats[c] = cats[c] || { category: c, cur: 0, prev: 0 };
        cats[c][field] += amt(t);
      });
    }
    add(a, 'cur');
    add(b, 'prev');
    var c = sum(a), p = sum(b);
    return {
      current: c, previous: p, delta: round2(c - p), deltaPct: p > 0 ? Math.round((c - p) / p * 1000) / 10 : null,
      samePoint: inProgress,
      categories: values(cats).map(function (x) {
        return { category: x.category, cur: round2(x.cur), prev: round2(x.prev), delta: round2(x.cur - x.prev) };
      }).sort(function (x, y) { return Math.abs(y.delta) - Math.abs(x.delta); })
    };
  }

  function pace(txs, currency, budget, now) {
    budget = Number(budget) || 0;
    if (budget <= 0) return null;
    var n = toDate(now), y = n.getFullYear(), m = n.getMonth(), dim = daysIn(y, m);
    var s = monthSummary(txs, currency, y, m, n);
    return {
      spent: s.total, budget: budget, expectedToday: round2(budget * n.getDate() / dim), projected: s.projected,
      ratio: Math.round(s.total / budget * 1000) / 1000,
      status: s.total > budget ? 'over' : s.projected > budget ? 'warn' : 'ok'
    };
  }

  // The last 7 full days (today excluded) against the 7 days before.
  function week(txs, currency, now) {
    var n = toDate(now), t = dayNo(n), cur = currency || 'CAD';
    var a = spendIn(txs, cur, t - 7, t - 1), b = spendIn(txs, cur, t - 14, t - 8), total = sum(a), prev = sum(b);
    return {
      start: isoDay(addDays(n, -7)), end: isoDay(addDays(n, -1)), total: total, count: a.length,
      previousTotal: prev, delta: round2(total - prev), deltaPct: prev > 0 ? Math.round((total - prev) / prev * 1000) / 10 : null
    };
  }

  /* ------------------------------------------------------------------ formatting */

  var FR = {
    months: ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'],
    days: ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi']
  };
  var EN = {
    months: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    days: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  };
  var SYMBOLS = { fr: { CAD: '$', USD: '$ US', EUR: '€', GBP: '£' }, en: { CAD: '$', USD: 'US$', EUR: '€', GBP: '£' } };
  var NBSP = ' ', NNBSP = ' ';
  function isFr(locale) { return /^fr/i.test(locale || 'fr'); }

  // fr: "1 234,56 $" (no-break space thousands, narrow no-break space before the symbol); en: "$1,234.56".
  function formatMoney(n, currency, locale) {
    var v = Number(n) || 0, cents = Math.round(Math.abs(v) * 100), cur = currency || 'CAD';
    var ip = String(Math.floor(cents / 100)), dp = pad(cents % 100), sign = v < 0 && cents ? '-' : '';
    if (isFr(locale)) return sign + ip.replace(/\B(?=(\d{3})+(?!\d))/g, NBSP) + ',' + dp + NNBSP + (SYMBOLS.fr[cur] || cur);
    return sign + (SYMBOLS.en[cur] || cur + ' ') + ip.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + '.' + dp;
  }

  // fr: "lundi 2 novembre", "1er novembre"; en: "Monday, November 2". opts: { weekday, year }.
  function formatDate(d, locale, opts) {
    d = toDate(d);
    opts = opts || {};
    if (isNaN(d.getTime())) return '';
    var fr = isFr(locale), L = fr ? FR : EN, day = d.getDate();
    var s = fr ? (day === 1 ? '1er' : day) + ' ' + L.months[d.getMonth()] : L.months[d.getMonth()] + ' ' + day;
    if (opts.year) s += (fr ? ' ' : ', ') + d.getFullYear();
    return opts.weekday ? L.days[d.getDay()] + (fr ? ' ' : ', ') + s : s;
  }

  /* ------------------------------------------------------------------ weekly digest (French) */

  var CATEGORY_FR = { Groceries: 'Épicerie', Dining: 'Restaurants', Transport: 'Transport', Travel: 'Voyages',
    Shopping: 'Magasinage', Subscriptions: 'Abonnements', Bills: 'Factures', Health: 'Santé', Entertainment: 'Loisirs',
    Cash: 'Retraits', Fees: 'Frais', Other: 'Autre', Income: 'Revenus', Transfers: 'Virements' };

  function esc(s) { return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function trend(pct) {
    var r = Math.round(Math.abs(pct));
    return (r === 0 ? '= ' : pct > 0 ? '▲ ' : '▼ ') + r + NBSP + '%';
  }
  function plural(n, word) { return n + ' ' + word + (n > 1 ? 's' : ''); }
  function dayRange(a, b) {
    a = toDate(a);
    b = toDate(b);
    return 'du ' + (a.getMonth() === b.getMonth() ? (a.getDate() === 1 ? '1er' : a.getDate()) : formatDate(a, 'fr')) +
      ' au ' + formatDate(b, 'fr');
  }
  function para(text, html) { return { text: text, html: '<p>' + (html || esc(text)) + '</p>' }; }
  function list(head, items) {
    if (!items.length) return para(head);
    return {
      text: head + '\n' + items.map(function (i) { return '• ' + i; }).join('\n'),
      html: '<p><strong>' + esc(head) + '</strong></p>\n<ul>' + items.map(function (i) { return '<li>' + esc(i) + '</li>'; }).join('') + '</ul>'
    };
  }

  // opts: { now, currency, budget, locale, health: { lines: [] }, reviewCount, dashboardUrl }
  function digest(txs, opts) {
    opts = opts || {};
    txs = txs || [];
    var now = toDate(opts.now), cur = opts.currency || 'CAD', loc = opts.locale || 'fr', y = now.getFullYear(), m = now.getMonth();
    var money = function (n) { return formatMoney(n, cur, loc); };
    var cat = function (c) { return CATEGORY_FR[c] || c; };
    var w = week(txs, cur, now), cmp = compareMonths(txs, cur, y, m, now), ms = monthSummary(txs, cur, y, m, now);
    var prevMonth = FR.months[(m + 11) % 12], out = [], s;
    var title = 'Vos dépenses — ' + formatDate(now, loc, { weekday: true });

    if (w.count || w.previousTotal) {
      s = 'Cette semaine (' + dayRange(w.start, w.end) + ') : ' + money(w.total) + ' en ' + plural(w.count, 'transaction');
      if (w.deltaPct != null) s += ', ' + trend(w.deltaPct) + ' par rapport à la semaine précédente (' + money(w.previousTotal) + ')';
      out.push(para(s + '.'));
    }
    if (cmp.current || cmp.previous) {
      s = 'Depuis le 1er ' + FR.months[m] + ' : ' + money(cmp.current);
      if (cmp.deltaPct != null) s += ', ' + trend(cmp.deltaPct) + ' par rapport à la même période en ' + prevMonth + ' (' + money(cmp.previous) + ')';
      out.push(para(s + '.'));
    }
    var p = pace(txs, cur, opts.budget, now);
    if (p) {
      s = 'Budget du mois : ' + money(p.spent) + ' dépensés sur ' + money(p.budget) + ' (' + Math.round(p.ratio * 100) + NBSP + '%)';
      if (p.status === 'over') s += ' — budget dépassé de ' + money(p.spent - p.budget) + '.';
      else s += '. Au rythme actuel : environ ' + money(p.projected) + ' d’ici la fin du mois, ' +
        (p.status === 'warn' ? 'soit ' + money(p.projected - p.budget) + ' de plus que prévu.' : 'dans les limites du budget.');
      out.push(para(s));
    }
    var top = ms.byCategory.filter(function (c) { return c.total > 0; }).slice(0, 3).map(function (c) {
      var x = cmp.categories.filter(function (k) { return k.category === c.category; })[0], d = x ? x.delta : 0;
      var change = x && x.prev ? (d > 0 ? '▲ ' : d < 0 ? '▼ ' : '= ') + money(Math.abs(d)) : 'nouveau';
      return cat(c.category) + ' : ' + money(c.total) + ' (' + change + ')';
    });
    if (top.length) out.push(list('Principales catégories du mois (par rapport à ' + prevMonth + ') :', top));

    var rec = recurring(txs, now, { currency: cur });
    if (rec.length) {
      out.push(list('Paiements récurrents : ' + plural(rec.length, 'détecté') + ', environ ' + money(monthlyTotal(rec)) + ' par mois.',
        rec.filter(function (r) { return r.increased; }).map(function (r) {
          return 'Hausse : ' + r.merchant + ' est passé de ' + money(r.increased.from) + ' à ' + money(r.increased.to) + '.';
        }).concat(rec.filter(function (r) { return r.overdue; }).map(function (r) {
          return r.merchant + ' : attendu vers le ' + formatDate(r.nextExpected, loc, { weekday: true }) + ', pas encore reçu.';
        }))));
    }

    var t = dayNo(now), buys = spendIn(txs, cur, t - 7, t - 1).filter(function (x) { return amt(x) > 0; });
    var items = buys.slice().sort(function (a, b) { return amt(b) - amt(a); }).slice(0, 3).map(function (x) {
      return money(amt(x)) + ' — ' + (canonicalMerchant(x.merchant) || cat(x.category)) + ' (' + formatDate(x.date, loc, { weekday: true }) + ')';
    });
    var seen = {}, fresh = [];
    buys.forEach(function (x) {
      var k = key(x.merchant), d = dayNo(x.date);
      if (!k || seen[k]) return;
      var earlier = txs.filter(function (o) { return o !== x && dayNo(o.date) < d; });
      if (flagAtCapture(x, earlier).indexOf('new') >= 0) { seen[k] = 1; fresh.push(canonicalMerchant(x.merchant) + ' (' + money(amt(x)) + ')'); }
    });
    if (fresh.length) items.push('Nouveau' + (fresh.length > 1 ? 'x marchands' : ' marchand') + ' : ' + fresh.join(', ') + '.');
    if (items.length) out.push(list('Plus gros achats de la semaine :', items));

    var n = Number(opts.reviewCount) || 0, url = String(opts.dashboardUrl || '');
    if (n > 0) {
      s = plural(n, 'transaction') + ' à vérifier';
      var safe = /^https?:\/\//i.test(url);
      out.push(para(s + (url ? ' dans le tableau de bord : ' + url : '.'),
        esc(s) + (safe ? ' dans le <a href="' + esc(url) + '">tableau de bord</a>.' : '.')));
    }
    var lines = (opts.health && opts.health.lines) || [];
    if (lines.length) out.push(list('État de la capture :', lines.map(String)));

    s = 'Dépenses : ' + money(w.total) + ' cette semaine' + (w.deltaPct != null ? ' (' + trend(w.deltaPct) + ')' : '') +
      ', ' + money(cmp.current) + ' depuis le 1er ' + FR.months[m];
    return {
      subject: s,
      text: [title].concat(out.map(function (x) { return x.text; })).join('\n\n'),
      html: '<div lang="fr">\n<h2>' + esc(title) + '</h2>\n' + out.map(function (x) { return x.html; }).join('\n') + '\n</div>'
    };
  }

  return {
    counts: counts,
    canonicalMerchant: canonicalMerchant,
    key: key,
    recurring: recurring,
    monthlyTotal: monthlyTotal,
    flagAtCapture: flagAtCapture,
    monthSummary: monthSummary,
    compareMonths: compareMonths,
    pace: pace,
    week: week,
    digest: digest,
    formatMoney: formatMoney,
    formatDate: formatDate,
    isoDay: isoDay
  };
})();

if (typeof module !== 'undefined' && module.exports) module.exports = SpendInsights;
