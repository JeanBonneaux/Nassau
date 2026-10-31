import test from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const P = require('../src/parser.js');

const CAD = { defaultCurrency: 'CAD' };
const USD = { defaultCurrency: 'USD' };
const EUR = { defaultCurrency: 'EUR' };

// [name, input, options, expected subset of the result]
const CASES = [
  // ---- purchases, English
  ['Chase: "transaction with"', { title: 'Chase Freedom', body: 'You made a $45.20 transaction with STARBUCKS on Oct 30, 2026 at 8:14 AM ET.' }, USD,
    { kind: 'transaction', type: 'purchase', amount: 45.2, currency: 'USD', merchant: 'STARBUCKS', category: 'Dining', status: 'ok' }],
  ['Amex: 5-digit card', { body: 'A charge of $54.30 at WHOLE FOODS was approved on your Card ending in 12345.' }, USD,
    { amount: 54.3, merchant: 'WHOLE FOODS', card: '••12345', category: 'Groceries' }],
  ['Capital One: amount after colon', { body: 'A transaction was charged to your account: $12.34 at UBER *TRIP' }, USD,
    { amount: 12.34, merchant: 'UBER *TRIP', category: 'Transport' }],
  ['RBC style', { title: 'RBC', body: 'A purchase of $54.21 was made at METRO #123 with your RBC Visa card ending in 1234' }, CAD,
    { amount: 54.21, currency: 'CAD', merchant: 'METRO #123', card: 'Visa ••1234', category: 'Groceries' }],
  ['TD style', { body: 'TD Alert: A purchase of $23.45 at TIM HORTONS was made on your TD credit card ending in 4321' }, CAD,
    { amount: 23.45, merchant: 'TIM HORTONS', card: 'Credit ••4321', category: 'Dining' }],
  ['Wise: currency code suffix', { body: 'You spent 12.50 USD at STARBUCKS' }, CAD,
    { amount: 12.5, currency: 'USD', merchant: 'STARBUCKS' }],
  ['US$ prefix', { body: 'Purchase of US$12.00 at AMAZON.COM' }, CAD,
    { amount: 12, currency: 'USD', merchant: 'AMAZON.COM', category: 'Shopping' }],
  ['bare $ with a non-dollar default means USD', { body: 'Purchase of $30.00 at TARGET' }, EUR, { currency: 'USD' }],
  ['purchase + available balance picks the purchase', { body: 'Purchase of $45.20 at SHELL. Available balance: $1,234.56' }, CAD,
    { amount: 45.2, merchant: 'SHELL', category: 'Transport' }],
  ['thousands separator', { body: 'A purchase of $1,234.56 was made at BEST BUY' }, USD,
    { amount: 1234.56, merchant: 'BEST BUY', category: 'Shopping' }],
  ['foreign purchase with conversion in brackets', { body: 'Purchase of €45.00 (CAD 66.20) at HOTEL DU PORT' }, CAD,
    { amount: 45, currency: 'EUR', merchant: 'HOTEL DU PORT', category: 'Travel' }],
  ['city / province after merchant', { body: 'Purchase of $8.75 at STARBUCKS TORONTO ON M5V' }, CAD, { merchant: 'STARBUCKS TORONTO' }],
  ['"Winners" is a store, not a promo', { body: 'Purchase of $45.00 at WINNERS' }, CAD,
    { kind: 'transaction', merchant: 'WINNERS', category: 'Shopping' }],
  ['used at 7-Eleven for', { body: 'Your card ending 9876 was used at 7-ELEVEN for $4.99' }, USD,
    { merchant: '7-ELEVEN', amount: 4.99, card: '••9876' }],
  ['"in" inside a merchant name is kept', { body: 'Purchase of $9.12 at JACK IN THE BOX #4521' }, USD, { merchant: 'JACK IN THE BOX #4521' }],
  ['subscription: merchant as prefix', { body: 'Netflix: $16.99 charged to your card ending in 1234' }, CAD,
    { merchant: 'Netflix', category: 'Subscriptions', amount: 16.99 }],
  ['labelled fields, bare amount', { title: 'Card alert', body: 'Amount: 45.20 Merchant: CORNER STORE' }, CAD,
    { amount: 45.2, currency: 'CAD', merchant: 'CORNER STORE', status: 'ok' }],

  // ---- purchases, French
  ['Desjardins', { title: 'Desjardins', body: 'Achat de 54,21 $ chez IGA EXTRA effectué avec votre carte Visa se terminant par 1234.' }, CAD,
    { amount: 54.21, currency: 'CAD', merchant: 'IGA EXTRA', card: 'Visa ••1234', category: 'Groceries', status: 'ok' }],
  ['Banque Nationale', { body: 'Transaction de 12,50 $ effectuée chez STM sur votre carte se terminant par 5678.' }, CAD,
    { amount: 12.5, merchant: 'STM', card: '••5678', category: 'Transport' }],
  ['French CB with date', { body: 'Paiement CB de 23,90 € chez CARREFOUR CITY le 30/10' }, EUR,
    { amount: 23.9, currency: 'EUR', merchant: 'CARREFOUR CITY', category: 'Groceries' }],
  ['French thousands with narrow no-break space', { body: 'Achat de 1 234,56 $ chez COSTCO' }, CAD,
    { amount: 1234.56, merchant: 'COSTCO', category: 'Groceries' }],
  ['EU thousands', { body: 'Paiement de 1.234,56 € chez FNAC' }, EUR, { amount: 1234.56, merchant: 'FNAC', category: 'Shopping' }],
  ['"$ CA" suffix', { body: 'Achat de 45,00 $ CA chez SAQ' }, EUR, { amount: 45, currency: 'CAD', merchant: 'SAQ' }],
  ['French "auprès de"', { body: 'Paiement de 9,99 € auprès de SPOTIFY' }, EUR, { merchant: 'SPOTIFY', category: 'Subscriptions' }],

  // ---- apps that put the merchant in the title / subtitle
  ['Revolut: merchant in title', { title: 'Pret A Manger', body: 'Paid €4.50' }, EUR,
    { amount: 4.5, currency: 'EUR', merchant: 'Pret A Manger', category: 'Dining', status: 'ok' }],
  ['Revolut: "paid at"', { body: '💳 Paid £4.50 at Pret A Manger' }, EUR, { amount: 4.5, currency: 'GBP', merchant: 'Pret A Manger' }],
  ['Wallet: title = card, subtitle = merchant', { app: 'Wallet', title: 'Visa ••1234', subtitle: 'Starbucks', body: '$5.75' }, CAD,
    { amount: 5.75, currency: 'CAD', merchant: 'Starbucks', card: 'Visa ••1234', status: 'ok' }],
  ['Wallet: Apple Card', { app: 'Wallet', title: 'Apple Card', subtitle: 'Uber Eats', body: '$23.10 with Apple Card' }, USD,
    { amount: 23.1, merchant: 'Uber Eats', card: 'Apple Card', category: 'Dining' }],
  ['amount then merchant, no cue', { title: 'N26', body: '-12,50 € Monoprix' }, EUR,
    { kind: 'transaction', amount: 12.5, type: 'purchase', merchant: 'Monoprix', category: 'Groceries', status: 'ok' }],
  ['compact "$45.00 SHELL"', { title: 'Transaction alert', body: '$45.00 SHELL' }, CAD, { merchant: 'SHELL', category: 'Transport', status: 'ok' }],
  ['compact "STARBUCKS $5.75"', { title: 'Scotiabank', body: 'STARBUCKS $5.75' }, CAD, { merchant: 'STARBUCKS', category: 'Dining' }],
  ['"Pending:" is not a merchant', { body: 'Pending: $3.25 – DUNKIN #3345 – Visa ••8812' }, USD,
    { merchant: 'DUNKIN #3345', card: 'Visa ••8812', category: 'Dining' }],
  ['no merchant: sentence text is not taken as one', { body: 'A purchase of $45.20 was approved on your card ending 1234' }, CAD,
    { merchant: '', status: 'review' }],
  ['"Vous avez payé" + Monop\'', { body: 'Vous avez payé 12,50 € chez Monop\u2019 Bastille' }, EUR, { merchant: 'Monop\u2019 Bastille', category: 'Groceries' }],

  // ---- Bahamas
  ['CIBC FirstCaribbean: BSD prefix, "used for"', { title: 'CIBC FirstCaribbean', body: 'Your card ending 1234 was used for BSD 45.00 at SOLOMONS FRESH MARKET' }, USD,
    { amount: 45, currency: 'BSD', merchant: 'SOLOMONS FRESH MARKET', card: '••1234', category: 'Groceries' }],
  ['Scotiabank: BSD', { body: 'Purchase of BSD 120.00 at JOHN BULL with your card ending in 4567.' }, USD,
    { amount: 120, currency: 'BSD', merchant: 'JOHN BULL', category: 'Shopping' }],

  // ---- other movement types
  ['refund', { body: 'Refund of $25.00 from AMAZON has been credited to your card ending in 1234.' }, USD,
    { type: 'refund', amount: 25, merchant: 'AMAZON', category: 'Shopping' }],
  ['card payment received is a transfer', { body: "We've received your payment of $500.00. Thank you!" }, USD,
    { type: 'transfer', category: 'Transfers', status: 'ok' }],
  ['payment posted is a transfer', { body: 'Your payment of $250.00 has been posted to your account.' }, CAD, { type: 'transfer' }],
  ['deposit is income', { body: 'A deposit of $1,250.00 was made to your account' }, CAD, { type: 'income', amount: 1250, category: 'Income', merchant: '' }],
  ['ATM withdrawal is cash', { body: 'Withdrawal of $100.00 at ATM 1234 MAIN ST' }, CAD, { type: 'cash', category: 'Cash', amount: 100 }],
  ['pre-authorized debit is a bill, not cash', { body: 'A pre-authorized debit of $45.00 to BELL CANADA was processed' }, CAD,
    { type: 'purchase', merchant: 'BELL CANADA', category: 'Bills' }],
  ['bill payment "to"', { body: 'Bill payment of $85.00 to HYDRO-QUEBEC was successful' }, CAD,
    { type: 'purchase', merchant: 'HYDRO-QUEBEC', category: 'Bills' }],
  ['e-Transfer sent', { body: 'You sent $50.00 to John Doe via Interac e-Transfer' }, CAD, { type: 'transfer', merchant: 'John Doe' }],
  ['Interac debit purchase stays a purchase', { body: 'Interac purchase of $23.45 at METRO' }, CAD,
    { type: 'purchase', merchant: 'METRO', card: 'Interac' }],
  ['foreign transaction fee', { body: 'A foreign transaction fee of $1.35 was charged to your card ending in 1234' }, CAD,
    { type: 'fee', category: 'Fees', amount: 1.35 }],
  ['French refund', { body: 'Remboursement de 19,99 € de ZARA crédité sur votre carte' }, EUR, { type: 'refund', amount: 19.99 }],

  // ---- not transactions
  ['balance only', { body: 'Your balance is $1,234.56' }, CAD, { kind: 'ignore', reason: 'not-a-spend' }],
  ['promo without amount', { body: 'Get 5% cash back at Amazon this weekend!' }, CAD, { kind: 'ignore' }],
  ['promo with amount', { body: 'Earn $50 when you refer a friend' }, CAD, { kind: 'ignore', reason: 'promo' }],
  ['"spend $100, get $20" offer', { body: 'Spend $100 and get $20 back – limited time offer!' }, CAD, { kind: 'ignore', reason: 'promo' }],
  ['cash-back reward', { body: 'You earned $1.25 cash back on your purchase at METRO' }, CAD, { kind: 'ignore', reason: 'not-a-spend' }],
  ['one-time code', { body: 'Your verification code is 482913. Do not share it.' }, CAD, { kind: 'ignore', reason: 'no-amount' }],
  ['sign-in alert', { title: 'Security alert', body: 'New sign-in to your account from iPhone' }, CAD, { kind: 'ignore', reason: 'no-amount' }],
  ['declined', { body: 'Your transaction of $45.00 at XYZ STORE was declined' }, CAD, { kind: 'ignore', reason: 'declined' }],
  ['declined, French', { body: 'Transaction de 45,00 $ refusée chez XYZ' }, CAD, { kind: 'ignore', reason: 'declined' }],
  ['statement', { body: 'Your statement is ready. Statement balance: $1,234.56. Minimum payment: $25.00 due Nov 15' }, CAD, { kind: 'ignore', reason: 'statement' }],
  ['upcoming payment', { body: 'Upcoming payment of $15.99 to Spotify on Nov 3' }, CAD, { kind: 'ignore', reason: 'upcoming' }],
  ['empty', { title: '', body: '   ' }, CAD, { kind: 'ignore', reason: 'empty' }]
];

for (const [name, input, opts, expected] of CASES) {
  test(name, () => {
    const r = P.parse(input, opts);
    for (const [k, v] of Object.entries(expected)) {
      assert.deepEqual(r[k], v, `${k}: got ${JSON.stringify(r[k])}, expected ${JSON.stringify(v)}\n${JSON.stringify(r)}`);
    }
  });
}

test('plain string input works', () => {
  const r = P.parse('Purchase of $12.00 at SUBWAY', CAD);
  assert.equal(r.merchant, 'SUBWAY');
  assert.equal(r.category, 'Dining');
});

test('toNumber handles separators', () => {
  assert.equal(P.toNumber('1,234.56'), 1234.56);
  assert.equal(P.toNumber('1 234,56'), 1234.56);
  assert.equal(P.toNumber('1.234,56'), 1234.56);
  assert.equal(P.toNumber('1,234'), 1234);
  assert.equal(P.toNumber('45,5'), 45.5);
  assert.equal(P.toNumber('45'), 45);
  assert.ok(Number.isNaN(P.toNumber('abc')));
});

test('"$45.00 USD" is one amount, in USD', () => {
  const found = P.findAmounts('Charge of $45.00 USD at X', 'CAD');
  assert.equal(found.length, 1);
  assert.equal(found[0].currency, 'USD');
  assert.equal(found[0].value, 45);
});

test('card digits are not read as an amount', () => {
  const r = P.parse('Card ending 1234 $5.00 at KIOSK', CAD);
  assert.equal(r.amount, 5);
});

test('user rules win over defaults (substring and /regex/)', () => {
  const rules = [{ pattern: 'starbucks', category: 'Coffee' }, { pattern: '/^metro\\b/', category: 'Groceries+' }];
  assert.equal(P.categorize('STARBUCKS #12', rules, 'purchase'), 'Coffee');
  assert.equal(P.categorize('METRO #123', rules, 'purchase'), 'Groceries+');
  assert.equal(P.categorize('Café Olimpico', [{ pattern: 'cafe olimpico', category: 'Treats' }], 'purchase'), 'Treats');
  assert.equal(P.categorize('Unknown Shop', [], 'purchase'), 'Other');
  assert.equal(P.categorize('', [], 'purchase'), 'Other');
  assert.equal(P.categorize('ATM', [], 'cash'), 'Cash');
  const r = P.parse('Purchase of $5.00 at STARBUCKS', { defaultCurrency: 'CAD', rules });
  assert.equal(r.category, 'Coffee');
});

test('bad user regex does not throw', () => {
  assert.equal(P.categorize('X', [{ pattern: '/[unclosed/', category: 'Y' }], 'purchase'), 'Other');
});

test('fromFields: Apple Pay automation values', () => {
  let r = P.fromFields({ amount: '$12.50', merchant: 'Starbucks', card: 'RBC Visa' }, CAD);
  assert.deepEqual([r.amount, r.currency, r.merchant, r.card, r.category, r.status], [12.5, 'CAD', 'Starbucks', 'RBC Visa', 'Dining', 'ok']);
  r = P.fromFields({ amount: '12,50 $', merchant: 'IGA' }, CAD);
  assert.deepEqual([r.amount, r.currency, r.category], [12.5, 'CAD', 'Groceries']);
  r = P.fromFields({ amount: 'US$8.00', merchant: 'Uber' }, CAD);
  assert.deepEqual([r.amount, r.currency], [8, 'USD']);
  r = P.fromFields({ amount: '8.25', merchant: 'Kiosk' }, EUR);
  assert.deepEqual([r.amount, r.currency], [8.25, 'EUR']);
  r = P.fromFields({ amount: 19.99, merchant: 'Shop', currency: 'gbp', category: 'Gifts', type: 'refund' }, CAD);
  assert.deepEqual([r.amount, r.currency, r.category, r.type], [19.99, 'GBP', 'Gifts', 'refund']);
  r = P.fromFields({ merchant: 'Starbucks' }, CAD);
  assert.deepEqual([r.amount, r.status], [0, 'review']);
});

test('signedAmount and countsAsSpending', () => {
  assert.equal(P.signedAmount(10, 'purchase'), 10);
  assert.equal(P.signedAmount(-10, 'purchase'), 10);
  assert.equal(P.signedAmount(10, 'refund'), -10);
  assert.equal(P.signedAmount(10, 'income'), -10);
  assert.equal(P.countsAsSpending({ type: 'purchase', status: 'ok' }), true);
  assert.equal(P.countsAsSpending({ type: 'purchase', status: 'review' }), true);
  assert.equal(P.countsAsSpending({ type: 'refund', status: 'ok' }), true);
  assert.equal(P.countsAsSpending({ type: 'purchase', status: 'duplicate' }), false);
  assert.equal(P.countsAsSpending({ type: 'purchase', status: 'excluded' }), false);
  assert.equal(P.countsAsSpending({ type: 'transfer', status: 'ok' }), false);
  assert.equal(P.countsAsSpending({ type: 'income', status: 'ok' }), false);
});

test('utility and phone bills', () => {
  for (const m of ['CITY POWER & LIGHT', 'MOBILE PHONE CO', 'ACME WIRELESS', 'Hydro-Québec', 'Vidéotron']) {
    assert.equal(P.categorize(m, [], 'purchase'), 'Bills', m);
  }
});
