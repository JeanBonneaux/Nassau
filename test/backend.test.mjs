import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { loadBackend } from '../tools/gas-mock.mjs';

const SCOTIA = 'Un achat de 54,21 $ a été effectué chez IGA EXTRA avec votre carte Visa se terminant par 1234.';

function fresh(opts = {}) {
  const b = loadBackend(opts);
  const info = b.setup();
  return { b, admin: info.adminToken, capture: info.captureToken, info };
}
const iso = (minutesAgo, b) => new Date((b ? b.context.now_() : new Date()).getTime() - minutesAgo * 60000).toISOString();

test('setup: tabs, two tokens, currency from the sheet locale, trigger, Configuration tab', () => {
  const { b, admin, capture, info } = fresh();
  assert.match(admin, /^[0-9a-f]{40}$/);
  assert.match(capture, /^[0-9a-f]{40}$/);
  assert.notEqual(admin, capture);
  assert.deepEqual([...b.sheets.keys()], ['Transactions', 'Ignored', 'Rules', 'Configuration']);
  assert.equal(b.props.get('CURRENCY'), 'CAD', 'fr_CA locale -> CAD');
  assert.equal(b.triggers.length, 1);
  assert.equal(b.triggers[0].getHandlerFunction(), 'tick');
  assert.equal(info.webAppUrl, 'https://script.google.com/macros/s/TEST/exec');
  const cfg = b.sheet('Configuration').rows;
  assert.match(cfg[2][1], /^https:\/\/jeanculess\.github\.io\/Nassau\/depenses\.html#setup=/);
  assert.equal(cfg[3][1], `https://script.google.com/macros/s/TEST/exec?token=${capture}`);
  assert.ok(!b.logs.join('\n').includes(admin), 'the admin token is not printed in the log');
  // running it again keeps the tokens and the single trigger
  const again = b.setup();
  assert.equal(again.adminToken, admin);
  assert.equal(again.captureToken, capture);
  assert.equal(b.triggers.length, 1);
});

test('setup: a US sheet gets USD; an unknown locale falls back to CAD', () => {
  assert.equal(fresh({ locale: 'en_US' }).b.props.get('CURRENCY'), 'USD');
  assert.equal(fresh({ locale: 'fr_FR' }).b.props.get('CURRENCY'), 'EUR');
  assert.equal(fresh({ locale: '' }).b.props.get('CURRENCY'), 'CAD');
});

test('upgrading from the single-token version replaces the leaked token and reports a Shortcut still using it', () => {
  const b = loadBackend();
  b.props.set('TOKEN', 'old-leaked-token');
  const info = b.setup();
  assert.equal(info.migrated, true);
  assert.equal(b.props.has('TOKEN'), false);
  const r = b.post({ token: 'old-leaked-token', body: 'Purchase of $5.00 at X' });
  assert.equal(r.ok, false);
  assert.match(r.error, /périmé/);
  assert.equal(b.post({ token: info.adminToken, action: 'ping' }).health.staleHits, 1);
  assert.match(b.logs.join('\n'), /ancien jeton unique a été remplacé/);
});

test('the web app URL: remembered from a real request, or typed into the Configuration tab when getUrl() gives /dev', () => {
  const b = loadBackend({ webAppUrl: 'https://script.google.com/macros/s/HEAD/dev' });
  const info = b.setup();
  assert.equal(info.webAppUrl, '');
  const cfg = () => Object.fromEntries(b.sheet('Configuration').rows.map((r) => [r[0], r[1]]));
  assert.match(cfg()['Lien de configuration (ouvre le tableau de bord déjà connecté)'], /collez l'adresse/);
  // the user pastes the /exec address next to « Adresse du script »
  b.sheet('Configuration').rows[4][1] = 'https://script.google.com/macros/s/REAL/exec';
  b.setup();
  assert.equal(b.props.get('WEB_APP_URL'), 'https://script.google.com/macros/s/REAL/exec');
  assert.match(cfg()['Lien de configuration (ouvre le tableau de bord déjà connecté)'], /^https:\/\/jeanculess\.github\.io\/Nassau\/depenses\.html#setup=/);
  assert.equal(cfg()['Lien du raccourci (action « Obtenir le contenu de l’URL »)'] || cfg()["Lien du raccourci (action « Obtenir le contenu de l'URL »)"], `https://script.google.com/macros/s/REAL/exec?token=${info.captureToken}`);
  // a real request also records the address (the mock answers /exec during requests here)
  const b2 = loadBackend();
  b2.props.delete('WEB_APP_URL');
  const i2 = b2.setup();
  b2.props.delete('WEB_APP_URL');
  b2.post({ token: i2.captureToken, titre: '', corps: '' });
  assert.equal(b2.props.get('WEB_APP_URL'), 'https://script.google.com/macros/s/TEST/exec');
});

test('the capture token can only send notifications; the admin token does everything', () => {
  const { b, admin, capture } = fresh();
  assert.equal(b.get({ action: 'list' }).ok, false);
  assert.match(b.get({ action: 'list', token: 'nope' }).error, /Non autorisé/);
  assert.match(b.get({ action: 'list', token: capture }).error, /ne permet que d'envoyer/);
  assert.match(b.post({ token: capture, action: 'delete', id: 'x' }).error, /ne permet que d'envoyer/);
  assert.equal(b.post({ token: capture, titre: 'Scotia', corps: SCOTIA }).status, 'added');
  const list = b.get({ action: 'list', token: admin });
  assert.equal(list.ok, true);
  assert.equal(list.captureToken, capture);
  assert.equal(list.shortcutUrl, `https://script.google.com/macros/s/TEST/exec?token=${capture}`);
  assert.equal(b.post({ token: admin, action: 'ping' }).ok, true);
});

test('rotateToken: both tokens change, the old Shortcut link is refused but counted', () => {
  const { b, capture } = fresh();
  const r = b.context.rotateToken();
  assert.notEqual(r.captureToken, capture);
  const refused = b.post({ token: capture, titre: 'Scotia', corps: SCOTIA });
  assert.equal(refused.ok, false);
  assert.match(refused.error, /périmé/);
  const h = b.post({ token: r.adminToken, action: 'ping' }).health;
  assert.equal(h.staleHits, 1);
  assert.ok(h.lastStaleAt);
  assert.equal(b.post({ token: r.captureToken, titre: 'Scotia', corps: SCOTIA }).status, 'added');
});

test('French and English keys, the single "n" field, and form posts all work', () => {
  const { b, capture } = fresh();
  assert.equal(b.post({ token: capture, titre: 'InfoAlerte Scotia', soustitre: '', corps: SCOTIA }).status, 'added');
  assert.equal(b.post({ token: capture, title: 'Capital One', body: 'A purchase of $12.00 at COUCHE-TARD was approved on your card ending in 1234.' }).status, 'added');
  assert.equal(b.post({ token: capture, n: 'Wealthsimple\nYou spent $14.20 at Uber Eats' }).status, 'added');
  assert.equal(b.postForm({ token: capture, title: 'Scotia', body: 'Purchase of $2.00 at BRAVO' }).status, 'added');
  assert.equal(b.post('Purchase of $3.00 at CHARLIE', { token: capture }).status, 'added');
  const rows = b.sheet('Transactions').objects();
  assert.deepEqual(rows.map((r) => r.source), ['phone:scotia', 'phone:capitalone', 'phone:wealthsimple', 'phone:scotia', 'phone']);
  assert.deepEqual(rows.map((r) => r.merchant), ['IGA EXTRA', 'COUCHE-TARD', 'Uber Eats', 'BRAVO', 'CHARLIE']);
});

test('a notification is parsed and stored with its bank, card and flags column', () => {
  const { b, capture } = fresh();
  const r = b.post({ token: capture, title: 'InfoAlerte Scotia', body: SCOTIA });
  assert.equal(r.status, 'added');
  assert.equal(r.message, '✓ 54,21 $ · IGA EXTRA · Épicerie');
  const [row] = b.sheet('Transactions').objects();
  assert.equal(row.amount, 54.21);
  assert.equal(row.currency, 'CAD');
  assert.equal(row.card, 'Visa ••1234');
  assert.equal(row.source, 'phone:scotia');
  assert.equal(row.status, 'ok');
  assert.equal(row.reader, 'rules');
  assert.equal(row.flags, '');
  assert.ok(row.date instanceof Date);
  assert.match(row.id, /^t[0-9a-f]{12}$/);
});

test('an empty send is the Shortcut test button: noted, nothing added', () => {
  const { b, admin, capture } = fresh();
  const r = b.post({ token: capture, titre: '', soustitre: '', corps: '' });
  assert.equal(r.status, 'test');
  assert.match(r.message, /Raccourci relié/);
  assert.equal(b.sheet('Transactions').getLastRow(), 1);
  assert.equal(b.sheet('Ignored').getLastRow(), 1, 'header only');
  assert.ok(b.post({ token: admin, action: 'ping' }).health.shortcutPingAt);
});

test('a Shortcut that sends the words "Titre/corps" is caught and explained', () => {
  const { b, admin, capture } = fresh();
  const r = b.post({ token: capture, titre: 'Titre', soustitre: 'sous-titre', corps: 'corps' });
  assert.equal(r.status, 'ignored');
  assert.equal(r.reason, 'raccourci');
  assert.match(r.message, /pastilles bleues/);
  assert.equal(b.sheet('Ignored').objects()[0].reason, 'raccourci');
  assert.ok(b.post({ token: admin, action: 'ping' }).health.misconfiguredAt);
});

test('one-time codes are never stored; non-transactions go to Ignored', () => {
  const { b, admin, capture } = fresh();
  b.post({ token: capture, title: 'Capital One', body: 'Your verification code is 482913. Do not share it.' });
  b.post({ token: capture, title: 'Scotia', body: 'Votre code de sécurité est 7731' });
  const r = b.post({ token: capture, title: 'Scotia', body: 'New sign-in to your account from iPhone' });
  assert.equal(r.status, 'ignored');
  assert.equal(r.reason, 'no-amount');
  const raws = b.sheet('Ignored').objects().map((x) => x.raw);
  assert.deepEqual(raws, ['Capital One | Your verification code is ••••••. Do not share it.', 'Scotia | Votre code de sécurité est ••••••', 'Scotia | New sign-in to your account from iPhone']);
  assert.ok(!JSON.stringify(b.get({ token: admin })).includes('482913'));
  assert.equal(b.sheet('Transactions').getLastRow(), 1);
});

test('duplicates: the same text within 90 s is a duplicate; a few minutes later it is counted but flagged', () => {
  const { b, capture } = fresh();
  const n = { token: capture, title: 'Scotia', body: 'A purchase of $3.75 at STM was made on your card ending in 4321' };
  assert.equal(b.post(n).status, 'added');
  const again = b.post(n);
  assert.equal(again.status, 'duplicate');
  assert.equal(again.tx.note, 'Même notification reçue deux fois');
  b.setNow(new Date(Date.now() + 5 * 60000));
  const later = b.post(n);
  assert.equal(later.status, 'review');
  assert.match(later.tx.note, /Même texte il y a 5 min : deux achats, ou envoi en double \?/);
  assert.deepEqual(b.sheet('Transactions').objects().map((r) => r.status), ['ok', 'duplicate', 'review']);
});

test('duplicates: Cartes + bank push for one Apple Pay tap -> second one not counted (merchants compatible)', () => {
  const { b, capture } = fresh();
  assert.equal(b.post({ token: capture, title: 'Visa Scotia', subtitle: 'Jean Coutu', body: '12,50 $' }).status, 'added');
  const bank = b.post({ token: capture, title: 'InfoAlerte Scotia', body: 'Un achat de 12,50 $ a été effectué chez JEAN COUTU #123 avec votre carte se terminant par 1234.' });
  assert.equal(bank.status, 'duplicate');
  assert.match(bank.tx.note, /Doublon probable de Jean Coutu \(Cartes · iPhone\)/);
  assert.deepEqual(b.sheet('Transactions').objects().map((r) => r.source), ['phone:cartes', 'phone:scotia']);
});

test('duplicates: same amount but different merchants or different cards are two purchases', () => {
  const { b, capture } = fresh();
  assert.equal(b.post({ token: capture, title: 'Scotia', body: 'Purchase of $5.00 at STARBUCKS with card ending in 1111' }).status, 'added');
  assert.equal(b.post({ token: capture, title: 'Capital One', body: 'Purchase of $5.00 at STM with card ending in 2222' }).status, 'added');
  assert.equal(b.post({ token: capture, title: 'Capital One', body: 'Purchase of $5.00 at DOLLARAMA' }).status, 'added');
  assert.equal(b.post({ token: capture, title: 'Scotia', body: 'Purchase of $5.00 at SHELL with card ending in 3333' }).status, 'added');
});

test('duplicates: same bank, same amount, compatible merchant, different wording within 10 min -> counted, to check', () => {
  const { b, capture } = fresh();
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $3.75 at STM with card ending in 1111' });
  const r = b.post({ token: capture, title: 'Scotia', body: 'Your card ending in 1111 was used online for a purchase of $3.75 at STM' });
  assert.equal(r.status, 'review');
  assert.match(r.tx.note, /Même montant chez STM/);
});

test('duplicates: lines added by hand or from a statement are counted but flagged, never silently discounted', () => {
  const { b, admin } = fresh();
  const a = b.post({ token: admin, action: 'add', tx: { amount: 50, merchant: 'PETRO-CANADA 1234', date: '2026-10-03T16:00:00Z', source: 'statement' } });
  const c = b.post({ token: admin, action: 'add', tx: { amount: 50, merchant: 'PETRO-CANADA 1234', date: '2026-10-04T16:00:00Z', source: 'statement' } });
  assert.equal(a.status, 'added');
  assert.equal(c.status, 'review');
  assert.match(c.tx.note, /Ressemble à PETRO-CANADA 1234 \(relevé\) : deux achats, ou doublon \?/);
  assert.match(c.tx.flags, /dup/);
  // the same text pasted twice is a duplicate
  const t1 = b.post({ token: admin, action: 'add', text: SCOTIA, date: '2026-10-05T15:00:00Z' });
  const t2 = b.post({ token: admin, action: 'add', text: SCOTIA, date: '2026-10-05T15:30:00Z' });
  assert.deepEqual([t1.status, t2.status], ['added', 'duplicate']);
});

test('duplicates: a notification and the bank email for the same purchase, hours apart', () => {
  const { b, capture } = fresh();
  b.post({ token: capture, title: 'Capital One', body: 'A purchase of $45.20 at SHELL was approved on your card ending in 1234.' });
  b.setNow(new Date(Date.now() + 3 * 3600000));
  const mail = b.post({ token: capture, channel: 'email', from: 'alerts@capitalone.ca', title: "You've made a purchase", body: 'A purchase of $45.20 was made at SHELL on your Capital One card ending in 1234.', date: iso(180, b), trusted: true });
  assert.equal(mail.status, 'duplicate');
  assert.equal(b.sheet('Transactions').objects()[1].source, 'email:capitalone');
  // the email of a purchase the phone missed is counted
  const only = b.post({ token: capture, channel: 'email', from: 'alerts@capitalone.ca', title: "You've made a purchase", body: 'A purchase of $8.00 was made at TIM HORTONS on your Capital One card ending in 1234.', date: iso(60, b), trusted: true });
  assert.equal(only.status, 'added');
});

test('when the sheet is locked, the notification is still stored (to check), never lost', () => {
  const { b, capture } = fresh();
  b.setLockBusy(true);
  const r = b.post({ token: capture, title: 'Scotia', body: SCOTIA });
  assert.equal(r.status, 'review');
  assert.match(r.tx.note, /sans vérification de doublon/);
  assert.equal(b.sheet('Transactions').getLastRow(), 2);
});

test('rate limit: past 300 captures a day, notifications are noted without being read', () => {
  const { b, capture } = fresh();
  b.context.CAPTURE_MAX_PER_DAY = 2;
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $1.00 at ALPHA' });
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $2.00 at BRAVO' });
  const r = b.post({ token: capture, title: 'Scotia', body: 'Purchase of $3.00 at CHARLIE' });
  assert.equal(r.reason, 'rate-limit');
  assert.equal(b.sheet('Transactions').getLastRow(), 3);
});

test('list returns health, settings, links, rules, ignored notifications of the last 62 days', () => {
  const { b, admin, capture } = fresh();
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $9.99 at NETFLIX.COM' });
  b.post({ token: capture, title: 'Scotia', body: 'Your balance is $100.00' });
  const r = b.get({ action: 'list', token: admin });
  assert.equal(r.currency, 'CAD');
  assert.equal(r.transactions.length, 1);
  assert.equal(r.transactions[0].category, 'Subscriptions');
  assert.equal(r.ignored.length, 1);
  assert.equal(r.ignored[0].reason, 'not-a-spend');
  assert.deepEqual(r.rules, []);
  assert.equal(r.settings.budget, 0);
  assert.equal(r.settings.triggers, true);
  assert.ok(r.health.lastPhoneAt);
  assert.equal(r.health.bySource['phone:scotia'], r.health.lastPhoneAt);
  assert.equal(r.health.claude.on, false);
});

test('the dashboard can add (through the capture path), edit, confirm and delete', () => {
  const { b, admin } = fresh();
  const pasted = b.post({ token: admin, action: 'add', text: SCOTIA, date: '2026-10-02T15:00:00Z' });
  assert.equal(pasted.status, 'added');
  assert.equal(pasted.tx.source, 'paste');
  assert.equal(pasted.tx.date, '2026-10-02T15:00:00.000Z', 'a pasted notification keeps its date');
  assert.equal(b.post({ token: admin, action: 'add', text: SCOTIA, date: '2026-10-02T15:30:00Z' }).status, 'duplicate', 'pasting it twice is caught');
  const manual = b.post({ token: admin, action: 'add', tx: { amount: 30, merchant: 'Marché Jean-Talon', date: '2026-10-03T15:00:00Z', note: 'légumes' } });
  assert.equal(manual.tx.category, 'Groceries');
  assert.equal(manual.tx.source, 'manual');
  assert.equal(manual.tx.note, 'légumes');
  const id = manual.tx.id;
  let u = b.post({ token: admin, action: 'update', id, fields: { category: 'Dining', type: 'refund' } });
  assert.equal(u.tx.amount, -30, 'a refund is stored negative');
  u = b.post({ token: admin, action: 'update', id, fields: { status: 'excluded', type: 'purchase', merchant: 'Marché' } });
  assert.deepEqual([u.tx.status, u.tx.amount, u.tx.merchant], ['excluded', 30, 'Marché']);
  assert.equal(b.post({ token: admin, action: 'confirm', id }).tx.status, 'ok');
  assert.equal(b.post({ token: admin, action: 'delete', id }).deleted, true, 'a manual row is removed');
  const phone = b.post({ token: admin, title: 'Scotia', body: 'Purchase of $7.00 at SAQ' }).tx;
  const del = b.post({ token: admin, action: 'delete', id: phone.id });
  assert.equal(del.deleted, false, 'a captured row is kept, excluded');
  assert.equal(b.sheet('Transactions').objects().find((t) => t.id === phone.id).status, 'excluded');
  assert.equal(b.post({ token: admin, action: 'add', tx: { merchant: 'Sans montant' } }).ok, false);
  assert.match(b.post({ token: admin, action: 'add', text: 'Your code is 4242' }).error, /pas été lu comme une transaction/);
});

test('rules: category, display name, "(ignorer)", applied to the past and the future, deletable', () => {
  const { b, admin, capture } = fresh();
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $4.00 at SQ *CAFE OLIMPICO 0042' });
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $6.00 at SQ *CAFE OLIMPICO 0042' });
  const r = b.post({ token: admin, action: 'rule', pattern: 'cafe olimpico', category: 'Dining', name: 'Café Olimpico' });
  assert.equal(r.updated, 2);
  assert.deepEqual(b.sheet('Transactions').objects().map((t) => [t.category, t.merchant]), [['Dining', 'Café Olimpico'], ['Dining', 'Café Olimpico']]);
  const n = b.post({ token: capture, title: 'Scotia', body: 'Purchase of $3.00 at SQ *CAFE OLIMPICO 0042' });
  assert.deepEqual([n.tx.category, n.tx.merchant], ['Dining', 'Café Olimpico']);
  b.post({ token: admin, action: 'rule', pattern: 'loyer', category: '(ignorer)' });
  const rent = b.post({ token: capture, title: 'Scotia', body: 'Purchase of $1200.00 at LOYER MONTREAL' });
  assert.equal(rent.tx.status, 'excluded');
  assert.equal(b.post({ token: admin, action: 'rule', pattern: 'Cafe Olimpico', category: 'Treats', apply: false }).rules.length, 2, 'same pattern replaces');
  assert.equal(b.post({ token: admin, action: 'rule-delete', pattern: 'loyer' }).rules.length, 1);
});

test('settings: currency, budget, digest, email, heartbeat', () => {
  const { b, admin, capture } = fresh();
  const s = b.post({ token: admin, action: 'settings', budget: 1500, digest: false, email: 'off', heartbeatDays: 5 }).settings;
  assert.deepEqual([s.budget, s.digest, s.email, s.heartbeatDays, s.currency], [1500, false, false, 5, 'CAD']);
  assert.equal(b.post({ token: admin, action: 'settings', currency: 'usd' }).settings.currency, 'USD');
  assert.equal(b.post({ token: capture, title: 'Scotia', body: 'Purchase of $6.00 at B' }).tx.currency, 'USD');
  assert.equal(b.post({ token: admin, action: 'settings', currency: 'dollars' }).ok, false);
});

test('unignore removes an Ignored row', () => {
  const { b, admin, capture } = fresh();
  b.post({ token: capture, title: 'Wealthsimple', body: 'Your balance is $100.00' });
  const ig = b.get({ token: admin }).ignored;
  assert.equal(ig.length, 1);
  assert.equal(b.post({ token: admin, action: 'unignore', captured_at: ig[0].captured_at, raw: ig[0].raw }).removed, 1);
  assert.equal(b.get({ token: admin }).ignored.length, 0);
});

test('rows typed straight into the sheet get an id and normalized status/type', () => {
  const { b, admin } = fresh();
  b.sheet('Transactions').rows.push([new Date('2026-10-05T12:00:00Z'), 15, 'cad', 'Typed by hand', '', 'Achat', '', 'Doublon', '', '', '', '', '', '', '']);
  const r = b.get({ token: admin });
  const t = r.transactions[0];
  assert.match(t.id, /^t[0-9a-f]{12}$/);
  assert.deepEqual([t.type, t.status, t.currency, t.source], ['purchase', 'duplicate', 'CAD', 'sheet']);
});

test('a moved column is reported instead of silently corrupting the sheet', () => {
  const b = loadBackend();
  b.setup();
  b.sheet('Transactions').rows[0][1] = 'montant';
  assert.throws(() => b.setup(), /colonne 2 devrait s'appeler « amount »/);
});

test('email polling reads bank alerts from Gmail, labels them, skips phishing', () => {
  const { b, admin } = fresh();
  b.setInbox([
    { from: 'InfoAlertes Scotia <infoalerts@scotiabank.com>', subject: 'InfoAlerte : achat', body: 'Un achat de 23,45 $ a été effectué chez TIM HORTONS avec votre carte de débit se terminant par 5678.\n\nSe désabonner: https://x', date: iso(20, b) },
    { from: 'Capital One <alerts@capitalone.ca>', subject: "You've made a purchase", body: 'A purchase of $45.20 was made at SHELL on your card ending in 1234.', date: iso(10, b) },
    { from: 'Capital One <security@capitalone.ca>', subject: 'Action required', body: 'Please verify your account now at https://evil.example.com to confirm your password.', date: iso(5, b) }
  ]);
  const r = b.context.pollEmail_();
  assert.deepEqual([r.seen, r.added], [3, 2]);
  const rows = b.sheet('Transactions').objects();
  assert.deepEqual(rows.map((t) => [t.source, t.merchant, t.amount]), [['email:scotia', 'TIM HORTONS', 23.45], ['email:capitalone', 'SHELL', 45.2]]);
  assert.ok(rows[0].date instanceof Date);
  assert.equal(b.sheet('Ignored').objects()[0].reason, 'suspect');
  assert.ok(b.inbox().every((m) => m.labels.has('Depenses')));
  assert.equal(b.context.pollEmail_().seen, 0, 'already read');
  assert.equal(b.get({ token: admin }).health.lastEmailAt !== null, true);
  b.post({ token: admin, action: 'settings', email: false });
  assert.equal(b.context.pollEmail_().skipped, 'off');
});

test('email polling: a grouped Gmail conversation is read message by message, each one once', () => {
  const { b } = fresh();
  b.setNow(new Date('2026-10-20T15:00:00Z'));
  b.setInbox([
    { id: 'm1', from: 'alerts@capitalone.ca', subject: 'Purchase alert', body: 'A purchase of $10.00 was made at SHELL on your card ending in 1234.', date: '2026-10-20T14:00:00Z' },
    { id: 'm2', from: 'alerts@capitalone.ca', subject: 'Purchase alert', body: 'A purchase of $20.00 was made at SAQ on your card ending in 1234.', date: '2026-10-20T14:30:00Z' }
  ]);
  assert.deepEqual([b.context.pollEmail_().seen, b.sheet('Transactions').objects().length], [2, 2]);
  // a new alert joins the same conversation; the cache is gone (hours later), the label too (user removed it)
  b.setNow(new Date('2026-10-21T15:00:00Z'));
  b.cache.clear();
  b.inbox().forEach((m) => m.labels.clear());
  b.addMail({ id: 'm3', from: 'alerts@capitalone.ca', subject: 'Purchase alert', body: 'A purchase of $30.00 was made at IGA on your card ending in 1234.', date: '2026-10-21T14:00:00Z' });
  const r = b.context.pollEmail_();
  assert.equal(r.seen, 1, 'only the new message');
  assert.equal(b.sheet('Transactions').objects().length, 3);
  // a message older than 3 days never gets read, even if unseen
  b.addMail({ id: 'm0', from: 'alerts@capitalone.ca', subject: 'Purchase alert', body: 'A purchase of $99.00 was made at OLD on your card ending in 1234.', date: '2026-10-10T14:00:00Z' });
  assert.equal(b.context.pollEmail_().seen, 0);
  assert.ok(JSON.parse(b.props.get('MAIL_SEEN')).m3);
});

test('tick runs every step safely and writes the health block', () => {
  const { b } = fresh();
  b.setNow(new Date('2026-11-02T13:00:00Z')); // a Monday morning in Toronto
  b.context.tick();
  assert.ok(b.props.get('LAST_TICK_AT'));
  const cfg = b.sheet('Configuration').rows.map((r) => r[0]);
  assert.ok(cfg.includes('Santé de la capture'));
});

test('daily check: nothing captured for 3 days -> one French email, repeated at most weekly', () => {
  const { b, capture } = fresh();
  b.setNow(new Date('2026-10-20T15:00:00Z'));
  b.post({ token: capture, title: 'Scotia', body: SCOTIA });
  b.setNow(new Date('2026-10-22T15:00:00Z'));
  assert.equal(b.context.dailyCheck_(false).sent, false, 'two days: fine');
  b.setNow(new Date('2026-10-25T15:00:00Z'));
  const r = b.context.dailyCheck_(false);
  assert.equal(r.sent, true);
  assert.deepEqual([...r.problems], ['silent']);
  assert.equal(b.mails.length, 1);
  assert.equal(b.mails[0].to, 'moi@example.com');
  assert.match(b.mails[0].subject, /Dépenses : une chose à vérifier/);
  assert.match(b.mails[0].body, /Rien n'est arrivé depuis 5 jours/);
  assert.ok(!b.mails[0].body.includes(capture), 'no secret in the email');
  b.setNow(new Date('2026-10-26T15:00:00Z'));
  assert.equal(b.context.dailyCheck_(false).sent, false, 'not repeated the next day');
  b.setNow(new Date('2026-11-03T15:00:00Z'));
  assert.equal(b.context.dailyCheck_(false).sent, true, 'repeated after a week');
  // nothing before 8 am, and once a day
  b.setNow(new Date('2026-11-04T09:00:00Z')); // 5 am Toronto
  assert.equal(b.context.dailyCheck_(false).skipped, 'early');
});

test('daily check: a bank that goes quiet, a stale link, a misconfigured shortcut, email-only purchases', () => {
  const { b, capture } = fresh();
  b.setNow(new Date('2026-10-01T15:00:00Z'));
  b.post({ token: capture, title: 'Capital One', body: 'A purchase of $12.00 at COUCHE-TARD was approved on your card ending in 1234.' });
  b.setNow(new Date('2026-10-10T15:00:00Z'));
  b.post({ token: capture, title: 'Scotia', body: SCOTIA });
  b.post({ token: capture, titre: 'Titre', corps: 'corps' });
  b.post({ token: capture, channel: 'email', from: 'alerts@capitalone.ca', title: 'Purchase', body: 'A purchase of $8.00 was made at TIM HORTONS on your card ending in 1234.', date: '2026-10-10T14:00:00Z' });
  b.post({ token: capture, channel: 'email', from: 'alerts@capitalone.ca', title: 'Purchase', body: 'A purchase of $9.00 was made at SHELL on your card ending in 1234.', date: '2026-10-10T14:30:00Z' });
  const r = b.context.rotateToken();
  b.post({ token: capture, title: 'Scotia', body: SCOTIA }); // old link
  const out = b.context.dailyCheck_(true);
  assert.deepEqual([...out.problems].sort(), ['email-only', 'misconfigured', 'quiet-phone:capitalone', 'stale'].sort());
  assert.equal(b.mails.length, 1);
  assert.match(b.mails[0].body, /Rien de Capital One · iPhone depuis 9 jours/);
  assert.match(b.mails[0].body, /ancien lien/);
  assert.match(b.mails[0].body, /pastille bleue/);
  assert.match(b.mails[0].body, /2 achats des 7 derniers jours ne sont arrivés que par courriel/);
  assert.ok(!b.mails[0].body.includes(r.captureToken));
});

test('apps-script/Spending.gs is up to date (run: node tools/build.mjs)', () => {
  const gs = fs.readFileSync(new URL('../apps-script/Spending.gs', import.meta.url), 'utf8');
  const parser = fs.readFileSync(new URL('../src/parser.js', import.meta.url), 'utf8');
  const backend = fs.readFileSync(new URL('../src/backend.gs', import.meta.url), 'utf8');
  assert.ok(gs.includes(parser) && gs.endsWith(backend), 'Spending.gs is stale');
});

test('legacy Apple Pay style fields still work', () => {
  const { b, capture } = fresh();
  const r = b.post({ token: capture, amount: '$4.10', merchant: 'Tim Hortons', card: 'Visa' });
  assert.equal(r.tx.source, 'applepay');
  assert.equal(b.post({ token: capture, title: 'Scotia', body: 'Purchase of $4.10 at TIM HORTONS #22 with card ending in 1234' }).status, 'duplicate');
});
