import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const I = require('../src/insights.js');

const NOW = new Date('2026-10-31T12:00:00Z'); // a Saturday, in every time zone from UTC-11 to UTC+11
const NB = ' '; // no-break space (thousands, before %)
const NN = ' '; // narrow no-break space (before $)

// Fixtures: dates are local calendar days 'YYYY-MM-DD' (1-based month in the helper).
const d = (y, m, day) => I.isoDay(new Date(y, m - 1, day));
let seq = 0;
const tx = (date, amount, merchant, category = 'Other', extra = {}) => ({
  id: 'T' + ++seq, date, amount, currency: 'CAD', merchant, category,
  type: amount < 0 ? 'refund' : 'purchase', status: 'ok', source: 'test', note: '', ...extra
});
const monthly = (merchant, amounts, firstMonth, day, category, year = 2026) =>
  amounts.map((a, i) => tx(d(year, firstMonth + i, day), a, merchant, category));

/* ------------------------------------------------------------------ fixtures */

function recurringFixture() {
  return [
    ...monthly('NETFLIX.COM', [16.99, 16.99, 16.99, 16.99, 16.99, 18.99], 5, 5, 'Subscriptions'),
    tx(d(2026, 10, 5), 18.99, 'NETFLIX.COM', 'Subscriptions', { status: 'duplicate' }),
    ...monthly('Hydro-Québec', [92, 92, 92, 92, 92], 5, 15, 'Bills'), // last 15 Sept: due ~15 Oct, overdue
    ...[21, 28, 35, 42, 49, 56].map((n) => tx(d(2026, 9, n), 15, 'ECONOFITNESS #12', 'Health')), // weekly, Mondays 21 Sept to 26 Oct
    tx(d(2025, 3, 10), 480, 'INTACT ASSURANCE', 'Bills'),
    tx(d(2026, 3, 10), 492, 'INTACT ASSURANCE', 'Bills'),
    ...[[3, 82.15], [10, 45.3], [17, 120.4], [24, 33.1], [30, 67.85]].map(([n, a]) => tx(d(2026, 10, n), a, 'IGA EXTRA #8123 MONTREAL QC', 'Groceries')),
    ...monthly('PAYPAL *SPOTIFY', [11.99, 11.99, 11.99, 11.99], 7, 20, 'Subscriptions'),
    tx(d(2026, 9, 22), -11.99, 'PAYPAL *SPOTIFY', 'Subscriptions'),
    ...monthly('ARCHAMBAULT', [-25, -25, -25], 8, 12, 'Shopping'), // refunds only: never recurring
    ...monthly('CRAVE', [9.99, 9.99, 9.99, 9.99, 9.99], 1, 10, 'Subscriptions'), // ended in May
    ...monthly('GITHUB', [4, 4, 4], 8, 2, 'Subscriptions').map((t) => ({ ...t, currency: 'USD' }))
  ];
}

// September 2026 = 410 $; October 2026 = 530 $ in CAD counting rows.
function monthFixture() {
  return [
    tx(d(2026, 9, 3), 100, 'IGA', 'Groceries'),
    tx(d(2026, 9, 10), 70, 'CHEZ LÉVÊQUE', 'Dining'),
    tx(d(2026, 9, 20), 200, 'BEST BUY #555', 'Shopping'),
    tx(d(2026, 9, 28), 40, 'IGA', 'Groceries'),
    tx(d(2026, 10, 2), 120, 'IGA', 'Groceries'),
    tx(d(2026, 10, 5), 4.5, 'SQ *CAFE OLIMPICO 0042 MONTREAL QC', 'Dining'),
    tx(d(2026, 10, 8), 5.5, 'SQ *CAFE OLIMPICO', 'Dining'),
    tx(d(2026, 10, 12), 300, 'BEST BUY #555', 'Shopping'),
    tx(d(2026, 10, 14), -50, 'BEST BUY', 'Shopping'),
    tx(d(2026, 10, 18), 1200, 'LOYER', 'Bills', { status: 'excluded' }),
    tx(d(2026, 10, 19), 80, 'IGA EXTRA', 'Groceries', { status: 'duplicate' }),
    tx(d(2026, 10, 20), 80, 'IGA EXTRA', 'Groceries'),
    tx(d(2026, 10, 21), -2000, 'EMPLOYEUR', 'Income', { type: 'income' }),
    tx(d(2026, 10, 22), 99, 'AMAZON.COM', 'Shopping', { currency: 'USD' }),
    tx(d(2026, 10, 23), 300, 'VIREMENT', 'Transfers', { type: 'transfer' }),
    tx(d(2026, 10, 25), 45, 'SAQ 23045', 'Groceries'),
    tx(d(2026, 10, 26), 25, 'UBER *TRIP', 'Transport', { status: 'review' })
  ];
}

/* ------------------------------------------------------------------ counts, merchants */

test('counts: spending types only, duplicates and excluded rows never count', () => {
  assert.equal(I.counts(tx('2026-10-01', 5, 'X')), true);
  assert.equal(I.counts(tx('2026-10-01', -5, 'X')), true);
  assert.equal(I.counts(tx('2026-10-01', 5, 'X', 'Cash', { type: 'cash', status: 'review' })), true);
  assert.equal(I.counts(tx('2026-10-01', 5, 'X', 'Fees', { type: 'fee' })), true);
  assert.equal(I.counts(tx('2026-10-01', -5, 'X', 'Income', { type: 'income' })), false);
  assert.equal(I.counts(tx('2026-10-01', 5, 'X', 'Transfers', { type: 'transfer' })), false);
  assert.equal(I.counts(tx('2026-10-01', 5, 'X', 'Other', { status: 'duplicate' })), false);
  assert.equal(I.counts(tx('2026-10-01', 5, 'X', 'Other', { status: 'excluded' })), false);
  assert.equal(I.counts(null), false);
});

const MERCHANTS = [
  ['SQ *CAFE OLIMPICO 0042 MONTREAL QC', 'Cafe Olimpico'],
  ['UBER *TRIP', 'Uber'],
  ['UBER* EATS', 'Uber Eats'],
  ['UBER *TRIP HELP.UBER.COM CA', 'Uber'],
  ['help.uber.com', 'Uber'],
  ['TIM HORTONS #1234', 'Tim Hortons'],
  ['IGA EXTRA', 'IGA'],
  ['IGA EXTRA #8123 MONTREAL QC', 'IGA'],
  ['AMZN Mktp CA*2K4', 'Amazon'],
  ['Amazon.ca*RT5YU', 'Amazon'],
  ['Netflix.com', 'Netflix'],
  ['NETFLIX.COM', 'Netflix'],
  ['STM', 'STM'],
  ['Jean Coutu', 'Jean Coutu'],
  ['PJC 0123', 'Jean Coutu'],
  ['TST* LE PETIT DEP', 'Le Petit Dep'],
  ['PAYPAL *SPOTIFY', 'Spotify'],
  ['COUCHE-TARD # 456 LAVAL QC', 'Couche-Tard'],
  ['MÉTRO PLUS 123 MONTRÉAL QC', 'Métro Plus'],
  ['SAQ 23045 TORONTO ON', 'SAQ'],
  ['KFC #123 QUEBEC QC', 'KFC'],
  ['A&W 4567', 'A&W'],
  ['H&M 0874 MONTREAL QC CA', 'H&M'],
  ['GOOGLE *YouTube', 'YouTube'],
  ['APPLE.COM/BILL', 'Apple'],
  ['SUMUP *BOULANGERIE GUILLAUME', 'Boulangerie Guillaume'],
  ['DOORDASH*THAI EXPRESS', 'Thai Express'],
  ['Starbucks #4521 Toronto ON', 'Starbucks'],
  ['Café Myriade', 'Café Myriade'],
  ['Hydro-Québec', 'Hydro-Québec'],
  ['  ECONOFITNESS   #12 ', 'Econofitness'],
  ['', ''],
  [null, '']
];

for (const [raw, want] of MERCHANTS) {
  test(`canonicalMerchant(${JSON.stringify(raw)}) = ${JSON.stringify(want)}`, () => {
    assert.equal(I.canonicalMerchant(raw), want);
  });
}

test('key: accent-free lower-case canonical name, so variants group together', () => {
  assert.equal(I.key('MÉTRO PLUS 123 MONTRÉAL QC'), 'metro plus');
  assert.equal(I.key('SQ *CAFE OLIMPICO'), I.key('SQ *CAFE OLIMPICO 0042 MONTREAL QC'));
  assert.equal(I.key('IGA EXTRA #8123'), 'iga');
  assert.equal(I.key(''), '');
});

/* ------------------------------------------------------------------ recurring */

test('recurring: detects monthly, weekly and yearly charges, sorted by monthly cost', () => {
  const list = I.recurring(recurringFixture(), NOW, { currency: 'CAD' });
  assert.deepEqual(list.map((r) => r.merchant), ['Hydro-Québec', 'Econofitness', 'Intact Assurance', 'Netflix', 'Spotify']);
  const by = Object.fromEntries(list.map((r) => [r.merchant, r]));

  const nf = by.Netflix;
  assert.equal(nf.period, 'monthly');
  assert.equal(nf.count, 6); // the duplicate row is ignored
  assert.equal(nf.amount, 18.99);
  assert.equal(nf.avgAmount, 17.32);
  assert.deepEqual(nf.increased, { from: 16.99, to: 18.99 });
  assert.equal(nf.lastDate, '2026-10-05');
  assert.equal(nf.nextExpected, '2026-11-05');
  assert.equal(nf.overdue, false);
  assert.equal(nf.category, 'Subscriptions');
  assert.equal(nf.key, 'netflix');

  const hq = by['Hydro-Québec'];
  assert.equal(hq.period, 'monthly');
  assert.equal(hq.nextExpected, '2026-10-15');
  assert.equal(hq.overdue, true);
  assert.equal(hq.increased, null);

  const gym = by.Econofitness;
  assert.equal(gym.period, 'weekly');
  assert.equal(gym.count, 6);
  assert.equal(gym.lastDate, '2026-10-26');
  assert.equal(gym.nextExpected, '2026-11-02');
  assert.equal(gym.overdue, false);

  const ins = by['Intact Assurance'];
  assert.equal(ins.period, 'yearly');
  assert.equal(ins.nextExpected, '2027-03-10');
  assert.equal(ins.increased, null); // +2.5 % is not an increase

  assert.equal(by.Spotify.count, 4); // the refund is not one of the charges
  assert.equal(by.Spotify.increased, null);

  // weekly ×4.33, yearly ÷12: 92 + 64.95 + 41 + 18.99 + 11.99
  assert.equal(I.monthlyTotal(list), 228.93);
  assert.equal(I.monthlyTotal([]), 0);
});

test('recurring: varying amounts, refunds, ended series and other currencies are left out', () => {
  const keys = I.recurring(recurringFixture(), NOW, { currency: 'CAD' }).map((r) => r.key);
  assert.ok(!keys.includes('iga'), 'weekly groceries with varying amounts');
  assert.ok(!keys.includes('archambault'), 'refunds only');
  assert.ok(!keys.includes('crave'), 'stopped in May');
  assert.ok(!keys.includes('github'), 'USD');
  assert.deepEqual(I.recurring(recurringFixture(), NOW, { currency: 'USD' }).map((r) => r.key), ['github']);
});

test('recurring: two weekly charges are not enough; one missed month is tolerated in a long series', () => {
  const two = [tx(d(2026, 10, 19), 10, 'YOGA'), tx(d(2026, 10, 26), 10, 'YOGA')];
  assert.equal(I.recurring(two, NOW).length, 0);
  const gap = [6, 7, 9, 10].map((m) => tx(d(2026, m, 1), 30, 'BELL CANADA', 'Bills'));
  const [bell] = I.recurring(gap, NOW);
  assert.equal(bell.merchant, 'Bell Canada');
  assert.equal(bell.period, 'monthly');
  assert.equal(bell.nextExpected, '2026-11-01');
  // a 40 % jump in a two-charge series is not "within 5 %"
  assert.equal(I.recurring([tx(d(2026, 9, 3), 50, 'GARAGE'), tx(d(2026, 10, 3), 70, 'GARAGE')], NOW).length, 0);
});

/* ------------------------------------------------------------------ flagAtCapture */

test('flagAtCapture: large and new purchases against the recent median', () => {
  const recent = Array.from({ length: 20 }, (_, i) => tx(d(2026, 10, 1 + i), 30 + (i % 5) * 5, 'SHOP ' + (i % 4)));
  // median 40: large above max(160, 100), new above 80
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 250, 'BEST BUY #123'), recent), ['large', 'new']);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 90, 'NOUVEAU RESTO'), recent), ['new']);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 90, 'SHOP 1'), recent), []);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 170, 'SHOP 2'), recent), ['large']);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 60, 'AILLEURS'), recent), []);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), -250, 'BEST BUY'), recent), [], 'refund');
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 250, 'X', 'Other', { status: 'duplicate' }), recent), []);
  // fewer than 10 recent purchases: only the absolute 500 $ threshold, never "new"
  const few = recent.slice(0, 5);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 450, 'BEST BUY'), few), []);
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 650, 'BEST BUY'), few), ['large']);
  // excluded rows and refunds do not count toward the 10 purchases
  const noisy = few.concat(Array.from({ length: 10 }, (_, i) => tx(d(2026, 9, 1 + i), 5, 'X', 'Other', { status: 'excluded' })));
  assert.deepEqual(I.flagAtCapture(tx(d(2026, 10, 30), 450, 'BEST BUY'), noisy), []);
});

/* ------------------------------------------------------------------ months, pace, week */

test('monthSummary: refunds reduce, excluded, duplicate, income, transfer and other currencies do not count', () => {
  const s = I.monthSummary(monthFixture(), 'CAD', 2026, 9, NOW);
  assert.equal(s.total, 530);
  assert.equal(s.count, 8);
  assert.equal(s.perDay, 17.1);
  assert.equal(s.projected, 530); // the month ends today
  assert.deepEqual(s.byCategory, [
    { category: 'Shopping', total: 250, share: 0.472 },
    { category: 'Groceries', total: 245, share: 0.462 },
    { category: 'Transport', total: 25, share: 0.047 },
    { category: 'Dining', total: 10, share: 0.019 }
  ]);
  assert.deepEqual(s.topMerchants, [
    { merchant: 'Best Buy', total: 250, count: 2 },
    { merchant: 'IGA', total: 200, count: 2 },
    { merchant: 'SAQ', total: 45, count: 1 },
    { merchant: 'Uber', total: 25, count: 1 },
    { merchant: 'Cafe Olimpico', total: 10, count: 2 }
  ]);
  assert.deepEqual(s.largest.map((t) => t.amount), [300, 120, 80]);
  assert.equal(s.largest[0].merchant, 'BEST BUY #555');

  const mid = I.monthSummary(monthFixture(), 'CAD', 2026, 9, new Date(2026, 9, 15, 12));
  assert.equal(mid.total, 380);
  assert.equal(mid.projected, 785.33); // 380 / 15 × 31

  const sept = I.monthSummary(monthFixture(), 'CAD', 2026, 8, NOW);
  assert.equal(sept.total, 410);
  assert.equal(sept.projected, 410);
  assert.equal(sept.perDay, 13.67);
  assert.equal(I.monthSummary(monthFixture(), 'USD', 2026, 9, NOW).total, 99);
});

test('compareMonths: whole previous month, or the same point when the month is in progress', () => {
  const c = I.compareMonths(monthFixture(), 'CAD', 2026, 9, NOW);
  assert.equal(c.current, 530);
  assert.equal(c.previous, 410);
  assert.equal(c.delta, 120);
  assert.equal(c.deltaPct, 29.3);
  assert.equal(c.samePoint, true);
  assert.deepEqual(c.categories, [
    { category: 'Groceries', cur: 245, prev: 140, delta: 105 },
    { category: 'Dining', cur: 10, prev: 70, delta: -60 },
    { category: 'Shopping', cur: 250, prev: 200, delta: 50 },
    { category: 'Transport', cur: 25, prev: 0, delta: 25 }
  ]);

  const mid = I.compareMonths(monthFixture(), 'CAD', 2026, 9, new Date(2026, 9, 15, 12));
  assert.equal(mid.current, 380);
  assert.equal(mid.previous, 170); // 1–15 September only
  assert.equal(mid.samePoint, true);

  const past = I.compareMonths(monthFixture(), 'CAD', 2026, 8, NOW);
  assert.equal(past.current, 410);
  assert.equal(past.previous, 0);
  assert.equal(past.deltaPct, null);
  assert.equal(past.samePoint, false);

  // January compares with December of the previous year
  const jan = I.compareMonths([tx(d(2025, 12, 10), 40, 'A'), tx(d(2026, 1, 10), 60, 'A')], 'CAD', 2026, 0, NOW);
  assert.deepEqual([jan.current, jan.previous, jan.deltaPct], [60, 40, 50]);
});

test('pace: ok, warn and over against a monthly budget', () => {
  const txs = monthFixture();
  const ok = I.pace(txs, 'CAD', 1000, NOW);
  assert.deepEqual(ok, { spent: 530, budget: 1000, expectedToday: 1000, projected: 530, ratio: 0.53, status: 'ok' });
  assert.equal(I.pace(txs, 'CAD', 500, NOW).status, 'over');
  const warn = I.pace(txs, 'CAD', 700, new Date(2026, 9, 15, 12));
  assert.equal(warn.status, 'warn');
  assert.equal(warn.spent, 380);
  assert.equal(warn.projected, 785.33);
  assert.equal(warn.expectedToday, 338.71);
  assert.equal(I.pace(txs, 'CAD', 0, NOW), null);
  assert.equal(I.pace(txs, 'CAD', undefined, NOW), null);
});

test('week: the last 7 full days against the 7 before', () => {
  const w = I.week(monthFixture(), 'CAD', NOW);
  assert.deepEqual(w, { start: '2026-10-24', end: '2026-10-30', total: 70, count: 2, previousTotal: 80, delta: -10, deltaPct: -12.5 });
  assert.equal(I.week([], 'CAD', NOW).total, 0);
});

/* ------------------------------------------------------------------ formatting, digest */

test('formatMoney and formatDate: fr-CA conventions with an English fallback', () => {
  assert.equal(I.formatMoney(1234.56, 'CAD', 'fr'), `1${NB}234,56${NN}$`);
  assert.equal(I.formatMoney(1234567.891, 'CAD', 'fr-CA'), `1${NB}234${NB}567,89${NN}$`);
  assert.equal(I.formatMoney(-12.5, 'CAD', 'fr'), `-12,50${NN}$`);
  assert.equal(I.formatMoney(0, 'CAD', 'fr'), `0,00${NN}$`);
  assert.equal(I.formatMoney(9.99, 'EUR', 'fr'), `9,99${NN}€`);
  assert.equal(I.formatMoney(1234.56, 'CAD', 'en'), '$1,234.56');
  assert.equal(I.formatMoney(-12.5, 'CAD', 'en'), '-$12.50');
  assert.equal(I.formatDate('2026-11-02', 'fr', { weekday: true }), 'lundi 2 novembre');
  assert.equal(I.formatDate('2026-11-01', 'fr'), '1er novembre');
  assert.equal(I.formatDate(new Date(2026, 7, 15), 'fr', { year: true }), '15 août 2026');
  assert.equal(I.formatDate('2026-11-02', 'en', { weekday: true }), 'Monday, November 2');
  assert.equal(I.formatDate('nope', 'fr'), '');
});

function digestFixture() {
  return [
    ...recurringFixture(),
    ...monthFixture(),
    tx(d(2026, 10, 28), 1234.56, 'BRAULT & MARTINEAU 0123 LAVAL QC', 'Shopping')
  ];
}

const DIGEST_OPTS = {
  now: NOW, currency: 'CAD', budget: 2000, locale: 'fr', reviewCount: 3,
  dashboardUrl: 'https://example.test/dash', health: { lines: ['Dernière notification reçue il y a 2 h.', 'Taux d’analyse < 90 % sur 7 jours.'] }
};

test('digest: French sections in order, money and dates in fr-CA format', () => {
  const g = I.digest(digestFixture(), DIGEST_OPTS);
  const t = g.text;
  assert.match(g.subject, /^Dépenses : .+ cette semaine/);
  assert.ok(t.startsWith('Vos dépenses — samedi 31 octobre\n\n'), t.slice(0, 60));
  const order = [
    'Cette semaine (du 24 au 30 octobre) : ',
    'par rapport à la semaine précédente',
    'Depuis le 1er octobre : ',
    'par rapport à la même période en septembre',
    'Budget du mois : ',
    'Principales catégories du mois',
    'Paiements récurrents : 5 détectés',
    `Hausse : Netflix est passé de 16,99${NN}$ à 18,99${NN}$.`,
    'Hydro-Québec : attendu vers le jeudi 15 octobre, pas encore reçu.',
    'Plus gros achats de la semaine :',
    `1${NB}234,56${NN}$ — Brault & Martineau (mercredi 28 octobre)`,
    'Nouveau',
    '3 transactions à vérifier dans le tableau de bord : https://example.test/dash',
    'État de la capture :',
    'Dernière notification reçue il y a 2 h.'
  ];
  let at = -1;
  for (const s of order) {
    const i = t.indexOf(s, at + 1);
    assert.ok(i > at, `missing or out of order: ${s}\n---\n${t}`);
    at = i;
  }
  assert.ok(t.includes('Magasinage : '), 'categories are translated');
  assert.ok(t.includes(`par mois.`));
  assert.match(t, /Nouveaux? marchands? : [^\n]*Brault & Martineau \(1 234,56 \$\)/);
  assert.ok(!t.includes('Crave') && !t.includes('Github'));
  assert.ok(!/\$1,234/.test(t), 'no English money format');
  assert.equal(t.split('\n\n').length, 9, 'title + 8 sections');
});

test('digest: html is simple, escaped and has the dashboard link', () => {
  const g = I.digest(digestFixture(), DIGEST_OPTS);
  assert.ok(g.html.startsWith('<div lang="fr">'));
  assert.ok(g.html.includes('<h2>Vos dépenses — samedi 31 octobre</h2>'));
  assert.ok(g.html.includes('<a href="https://example.test/dash">tableau de bord</a>'));
  assert.ok(g.html.includes('Brault &amp; Martineau'));
  assert.ok(g.html.includes('&lt; 90'));
  assert.ok(g.html.includes(`<li>Hausse : Netflix est passé de 16,99${NN}$ à 18,99${NN}$.</li>`));
  assert.ok(!/<script|<style|<link|javascript:/i.test(g.html));
  const unsafe = I.digest(digestFixture(), { ...DIGEST_OPTS, dashboardUrl: 'javascript:alert(1)' });
  assert.ok(!unsafe.html.includes('href'));
});

test('digest: empty sections are omitted; budget over and warn wording', () => {
  const empty = I.digest([], { now: NOW, currency: 'CAD', locale: 'fr', reviewCount: 0 });
  assert.equal(empty.text, 'Vos dépenses — samedi 31 octobre');
  assert.ok(!empty.html.includes('<p>'));
  const over = I.digest(monthFixture(), { now: NOW, currency: 'CAD', budget: 500, locale: 'fr' });
  assert.ok(over.text.includes(`Budget du mois : 530,00${NN}$ dépensés sur 500,00${NN}$ (106${NB}%) — budget dépassé de 30,00${NN}$.`), over.text);
  assert.ok(!over.text.includes('vérifier'));
  const warn = I.digest(monthFixture(), { now: new Date(2026, 9, 15, 12), currency: 'CAD', budget: 700, locale: 'fr' });
  assert.ok(warn.text.includes(`environ 785,33${NN}$ d’ici la fin du mois, soit 85,33${NN}$ de plus que prévu.`), warn.text);
  const ok = I.digest(monthFixture(), { now: NOW, currency: 'CAD', budget: 1000, locale: 'fr' });
  assert.ok(ok.text.includes('dans les limites du budget.'));
  assert.ok(ok.text.includes(`Cette semaine (du 24 au 30 octobre) : 70,00${NN}$ en 2 transactions, ▼ 13${NB}% par rapport à la semaine précédente (80,00${NN}$).`), ok.text);
  assert.ok(ok.text.includes(`Depuis le 1er octobre : 530,00${NN}$, ▲ 29${NB}% par rapport à la même période en septembre (410,00${NN}$).`), ok.text);
});
