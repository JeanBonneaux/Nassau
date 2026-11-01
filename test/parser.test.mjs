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
  ['foreign purchase with conversion in brackets counts in the default currency', { body: 'Purchase of €45.00 (CAD 66.20) at HOTEL DU PORT' }, CAD,
    { amount: 66.2, currency: 'CAD', merchant: 'HOTEL DU PORT', category: 'Travel', original: { amount: 45, currency: 'EUR' } }],
  ['foreign first, conversion second', { app: 'Capital One', body: 'A purchase of 49.99 USD ($67.89 CAD) was made at AMAZON.COM' }, CAD,
    { amount: 67.89, currency: 'CAD', merchant: 'AMAZON.COM', original: { amount: 49.99, currency: 'USD' } }],
  ['foreign first, conversion second, French', { body: 'Un achat de 49,99 $ US (67,89 $ CA) a été effectué chez AMAZON.COM' }, CAD,
    { amount: 67.89, currency: 'CAD', merchant: 'AMAZON.COM' }],
  ['foreign purchase without conversion stays foreign', { body: 'Purchase of US$12.00 at AMAZON.COM' }, CAD, { amount: 12, currency: 'USD' }],

  // ---- the user's sources: Scotiabank (InfoAlertes), Capital One Canada, Wealthsimple, Wallet "Cartes"
  ['Cartes: title = card, subtitle = merchant, body = amount', { app: 'Cartes', title: 'Visa Scotia', subtitle: 'Jean Coutu', body: '12,50 $' }, CAD,
    { amount: 12.5, merchant: 'Jean Coutu', card: 'Visa Scotia', category: 'Health', status: 'ok' }],
  ['Cartes without app name, merchant with an offer word', { title: 'Wealthsimple Cash', subtitle: 'Boost Juice', body: '8,50 $' }, CAD,
    { kind: 'transaction', merchant: 'Boost Juice', card: 'Wealthsimple Cash', category: 'Dining' }],
  ['Cartes: "Dollar Deal" is a shop, not a promo', { app: 'Cartes', title: 'Capital One Mastercard', subtitle: 'Dollar Deal', body: '4,00 $' }, CAD,
    { kind: 'transaction', merchant: 'Dollar Deal', card: 'Capital One Mastercard' }],
  ['Cartes: pending label after the amount is not the merchant', { title: 'Visa Scotia', subtitle: 'SAQ', body: '45,25 $ · En attente' }, CAD,
    { merchant: 'SAQ', category: 'Groceries' }],
  ['Cartes: a plus sign means money back', { app: 'Cartes', title: 'Visa Scotia', subtitle: 'Dollarama', body: '+5,00 $' }, CAD,
    { type: 'refund', merchant: 'Dollarama', category: 'Shopping' }],
  ['Scotia FR: time of day after the merchant', { app: 'Banque Scotia', title: 'InfoAlerte Scotia', body: 'Un achat de 54,21 $ a été effectué chez IGA EXTRA à 20 h 14 avec votre carte Visa Scotia se terminant par 1234.' }, CAD,
    { amount: 54.21, merchant: 'IGA EXTRA', card: 'Visa ••1234', category: 'Groceries', status: 'ok' }],
  ['Scotia FR: bill payment', { app: 'Banque Scotia', body: 'Un paiement de facture de 85,00 $ à HYDRO-QUÉBEC a été effectué depuis votre compte se terminant par 1234.' }, CAD,
    { type: 'purchase', merchant: 'HYDRO-QUÉBEC', category: 'Bills' }],
  ['Scotia FR: pre-authorized debit', { app: 'Banque Scotia', body: 'Un paiement préautorisé de 45,00 $ à BELL CANADA a été effectué depuis votre compte.' }, CAD,
    { type: 'purchase', merchant: 'BELL CANADA', category: 'Bills' }],
  ['Scotia FR: card payment is a transfer', { app: 'Banque Scotia', body: 'Un paiement de 500,00 $ a été porté à votre carte de crédit se terminant par 1234.' }, CAD, { type: 'transfer' }],
  ['Scotia EN: card payment is a transfer', { app: 'Scotiabank', body: 'A payment of $500.00 was made to your credit card ending in 1234.' }, CAD, { type: 'transfer' }],
  ['Scotia EN: transfer between accounts', { body: 'A transfer of $500.00 was made from your account ending in 1234 to your account ending in 5678.' }, CAD, { type: 'transfer' }],
  ['Scotia FR: credit-card purchase over the chosen limit is a purchase', { app: 'Banque Scotia', body: 'Un achat par carte de crédit de 120,00 $ dépassant la limite de 100,00 $ que vous avez fixée a été effectué chez BEST BUY.' }, CAD,
    { type: 'purchase', amount: 120, merchant: 'BEST BUY', category: 'Shopping' }],
  ['Scotia EN: credit-card purchase over the chosen limit', { app: 'Scotiabank', body: 'A credit card purchase of $120.00 exceeded your limit of $100.00 at BEST BUY.' }, CAD,
    { type: 'purchase', amount: 120, merchant: 'BEST BUY' }],
  ['Scotia FR: low balance notice', { app: 'Banque Scotia', body: 'Le solde de votre compte se terminant par 1234 est inférieur à 100,00 $.' }, CAD, { kind: 'ignore' }],
  ['spending threshold notice', { body: 'Your spending this month has reached $500.00, over your limit of $400.00.' }, CAD, { kind: 'ignore' }],
  ['Scotia EN: account withdrawal with a description is a purchase', { app: 'Scotiabank', body: 'A withdrawal of $54.21 was made from your account ending in 1234. Description: IGA EXTRA' }, CAD,
    { type: 'purchase', merchant: 'IGA EXTRA', category: 'Groceries' }],
  ['Scotia EN: ABM withdrawal is cash', { body: 'A withdrawal of $100.00 was made at an ABM from your account ending in 1234.' }, CAD, { type: 'cash', category: 'Cash', merchant: '' }],
  ['Scotia FR: Interac sent', { body: 'Votre Virement Interac de 50,00 $ à JOHN DOE a été envoyé.' }, CAD, { type: 'transfer', merchant: 'JOHN DOE' }],
  ['Scotia FR: Interac received', { body: 'Vous avez reçu un Virement Interac de 50,00 $ de JOHN DOE.' }, CAD, { type: 'transfer', merchant: 'JOHN DOE' }],
  ['Interac request: no money moved', { body: 'JOHN DOE has requested $50.00 from you via Interac e-Transfer.' }, CAD, { kind: 'ignore', reason: 'upcoming' }],
  ['Interac request, French', { body: 'JOHN DOE vous a demandé 50,00 $ par Virement Interac.' }, CAD, { kind: 'ignore', reason: 'upcoming' }],
  ['Capital One FR: credit from a merchant', { app: 'Capital One', body: 'Un crédit de 25,00 $ de AMAZON.CA a été porté à votre compte.' }, CAD,
    { type: 'refund', merchant: 'AMAZON.CA', category: 'Shopping' }],
  ['Capital One FR: credit "de la part de"', { body: 'Un crédit de 25,00 $ a été porté à votre carte de la part de AMAZON.CA' }, CAD, { type: 'refund', merchant: 'AMAZON.CA' }],
  ['Capital One EN: purchase approved', { app: 'Capital One', body: 'A purchase of $22.10 at COUCHE-TARD was approved on your card ending in 1234.' }, CAD,
    { merchant: 'COUCHE-TARD', category: 'Groceries', card: '••1234' }],
  ['Wealthsimple: TFSA transfer', { app: 'Wealthsimple', body: 'Your transfer of $500.00 to your TFSA is complete' }, CAD, { type: 'transfer' }],
  ['Wealthsimple FR: CELI transfer', { app: 'Wealthsimple', body: 'Votre transfert de 500,00 $ vers votre CELI est terminé' }, CAD, { type: 'transfer' }],
  ['Wealthsimple: RRSP contribution', { body: 'Your contribution of $500.00 to your RRSP is complete' }, CAD, { type: 'transfer' }],
  ['Wealthsimple: recurring investment', { body: 'Your recurring investment of $100.00 was placed' }, CAD, { type: 'transfer' }],
  ['Wealthsimple: stock order', { body: 'Your order to buy 2 shares of VFV for $250.00 was filled' }, CAD, { type: 'transfer' }],
  ['Wealthsimple: interest earned is income', { app: 'Wealthsimple', title: 'Interest', body: '$12.34 interest earned on your Cash account' }, CAD, { type: 'income', category: 'Income' }],
  ['Wealthsimple FR: interest deposited is income', { app: 'Wealthsimple', title: 'Intérêts', body: '12,34 $ ont été déposés dans votre compte Cash' }, CAD, { type: 'income' }],
  ['Wealthsimple FR: refund from a merchant', { body: 'Vous avez reçu un remboursement de 7,50 $ de Cafe Olimpico' }, CAD, { type: 'refund', merchant: 'Cafe Olimpico', category: 'Dining' }],
  ['Wealthsimple: short text without a currency marker is kept for review', { app: 'Wealthsimple', body: 'Cafe Olimpico 7.50' }, CAD,
    { kind: 'transaction', amount: 7.5, currency: 'CAD', merchant: 'Cafe Olimpico', status: 'review' }],
  ['Wealthsimple: cash-back tail after the amount is not the merchant', { body: 'Cafe Olimpico 7,50 $ · 1 % de remise en argent' }, CAD, { merchant: 'Cafe Olimpico' }],
  ['Wealthsimple FR: paycheque is income', { body: 'Votre paie de 2 150,00 $ est arrivée' }, CAD, { type: 'income', amount: 2150, status: 'ok' }],
  ['Wealthsimple FR: deposit done', { body: 'Votre dépôt de 1 000,00 $ est terminé' }, CAD, { type: 'income', merchant: '' }],
  ['fee without merchant is not sent to review', { body: 'Des frais annuels de 120,00 $ ont été portés à votre compte' }, CAD, { type: 'fee', status: 'ok' }],
  ['pre-authorization is kept for review', { body: 'A pre-authorization of $150.00 was placed on your card ending in 1234 at PETRO-CANADA' }, CAD,
    { kind: 'transaction', merchant: 'PETRO-CANADA', status: 'review', reason: 'hold' }],
  ['pre-authorization, French', { body: 'Une préautorisation de 150,00 $ a été effectuée chez PETRO-CANADA' }, CAD, { status: 'review', reason: 'hold' }],
  ['amount update takes the new amount', { body: 'The pending transaction of $45.00 at RESTO LA BANQUISE was updated to $52.00' }, CAD,
    { amount: 52, merchant: 'RESTO LA BANQUISE', status: 'review' }],
  ['amount update, French', { body: 'La transaction en attente de 45,00 $ chez RESTO LA BANQUISE est passée à 52,00 $' }, CAD, { amount: 52, merchant: 'RESTO LA BANQUISE' }],
  ['city / province after merchant', { body: 'Purchase of $8.75 at STARBUCKS TORONTO ON M5V' }, CAD, { merchant: 'STARBUCKS TORONTO' }],
  ['"Winners" is a store, not a promo', { body: 'Purchase of $45.00 at WINNERS' }, CAD,
    { kind: 'transaction', merchant: 'WINNERS', category: 'Shopping' }],
  ['used at 7-Eleven for', { body: 'Your card ending 9876 was used at 7-ELEVEN for $4.99' }, USD,
    { merchant: '7-ELEVEN', amount: 4.99, card: '••9876' }],
  ['"in" inside a merchant name is kept', { body: 'Purchase of $9.12 at JACK IN THE BOX #4521' }, USD, { merchant: 'JACK IN THE BOX #4521' }],
  ['subscription: merchant as prefix', { body: 'Netflix: $16.99 charged to your card ending in 1234' }, CAD,
    { merchant: 'Netflix', category: 'Subscriptions', amount: 16.99 }],
  ['"Amount:" is a label, not a merchant', { title: 'Card', body: 'Amount: 45.20' }, CAD, { amount: 45.2, merchant: '', status: 'review' }],
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

test('redactCodes hides one-time codes only', () => {
  assert.equal(P.redactCodes('Your verification code is 482913'), 'Your verification code is ••••••');
  assert.equal(P.redactCodes('Code de vérification : 0042'), 'Code de vérification : ••••••');
  assert.equal(P.redactCodes('Purchase of $45.20 at SHELL ending in 1234'), 'Purchase of $45.20 at SHELL ending in 1234');
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

test('fold strips accents (a corrupted copy of the file would fail here)', () => {
  assert.equal(P.fold('Débité à Montréal'), 'debite a montreal');
  assert.equal(P.clean('a\u200bb c'), 'ab c');
});

test('Quebec and Canada merchants', () => {
  const cases = {
    Groceries: ['SAQ', 'SQDC', 'PA NATURE', 'AVRIL SUPERMARCHE', 'RACHELLE-BERY', 'BULK BARN', 'KIM PHAT', 'MAYRAND', 'COSTCO WHOLESALE'],
    Bills: ['FIZZ', 'COGECO', 'OXIO', 'EBOX', 'BELL CANADA', 'VIDEOTRON', 'HYDRO-QUEBEC'],
    Shopping: ['RENAUD-BRAY', 'ARCHAMBAULT', 'RENO-DEPOT', 'BMR', 'PATRICK MORIN', 'SPORTS EXPERTS', 'ARDENE', 'AUBAINERIE', 'BRAULT & MARTINEAU', 'CANADIAN TIRE'],
    Transport: ['HARNOIS', 'CREVIER', 'EXO', 'REM', 'RTL', 'STL', 'P$ MOBILE', 'FLO', 'CANADIAN TIRE GAS BAR', 'COSTCO GAS', 'ESSO'],
    Dining: ['CHEZ CORA', 'VALENTINE', 'HARVEYS', 'NORMANDIN', 'ASHTON', 'LAFLEUR', 'MIKES', 'SCORES', 'PACINI', 'VAN HOUTTE', 'BOOST JUICE'],
    Entertainment: ['GUZZO', 'LA RONDE', 'CENTRE BELL', 'CENTRE VIDEOTRON'],
    Subscriptions: ['ILLICO', 'TOU.TV', 'GOOGLE', 'DISNEY PLUS'],
    Travel: ['ENTERPRISE RENT-A-CAR', 'BUDGET RENT A CAR', 'DISNEYLAND RESORT'],
    Health: ['NAUTILUS PLUS', 'JEAN COUTU'],
    Other: ['PROCESSOR INC']
  };
  for (const [cat, merchants] of Object.entries(cases)) {
    for (const m of merchants) assert.equal(P.categorize(m, [], 'purchase'), cat, m);
  }
});

test('inferBank reads the bank from the text, or the Wallet layout', () => {
  assert.equal(P.inferBank({ title: 'InfoAlerte Scotia', body: 'Un achat de 5,00 $…' }), 'scotia');
  assert.equal(P.inferBank({ app: 'Banque Scotia', body: 'x' }), 'scotia');
  assert.equal(P.inferBank({ title: 'Capital One', body: 'A purchase of $5.00…' }), 'capitalone');
  assert.equal(P.inferBank({ from: 'alerts@capitalone.ca', title: 'You made a purchase' }), 'capitalone');
  assert.equal(P.inferBank({ title: 'Wealthsimple', body: 'Cafe Olimpico 7.50' }), 'wealthsimple');
  assert.equal(P.inferBank({ title: 'Visa Scotia', subtitle: 'Jean Coutu', body: '12,50 $' }), 'cartes', 'the Wallet layout is its own channel');
  assert.equal(P.inferBank({ title: 'Carte Visa', subtitle: 'Jean Coutu', body: '12,50 $' }), 'cartes');
  assert.equal(P.inferBank({ app: 'Cartes', title: 'x', body: 'y' }), 'cartes');
  assert.equal(P.inferBank({ title: 'Hello', body: 'world' }), '');
});

test('isPlaceholder catches a Shortcut built with typed words instead of variables', () => {
  assert.equal(P.isPlaceholder({ title: 'Titre', subtitle: 'sous-titre', body: 'corps' }), true);
  assert.equal(P.isPlaceholder({ title: 'Title', subtitle: 'Subtitle', body: 'Body' }), true);
  assert.equal(P.isPlaceholder({ title: '', subtitle: '', body: 'Entrée du raccourci' }), true);
  assert.equal(P.isPlaceholder({ title: 'InfoAlerte Scotia', subtitle: '', body: 'Un achat de 5,00 $ a été effectué chez SAQ' }), false);
  assert.equal(P.isPlaceholder({ title: '', subtitle: '', body: '' }), false);
});

test('parse marks the Wallet layout', () => {
  assert.equal(P.parse({ title: 'Visa Scotia', subtitle: 'SAQ', body: '45,25 $' }, CAD).layout, 'wallet');
  assert.equal(P.parse({ body: 'Purchase of $5.00 at SAQ' }, CAD).layout, undefined);
});
