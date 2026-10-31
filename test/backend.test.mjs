import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { loadBackend } from '../tools/gas-mock.mjs';

function fresh(currency = 'CAD') {
  const b = loadBackend();
  const info = b.setup();
  b.props.set('CURRENCY', currency);
  return { b, token: info.token };
}

test('setup creates the tabs, a token and removes the empty default tab', () => {
  const b = loadBackend();
  const info = b.setup();
  assert.match(info.token, /^[0-9a-f]{40}$/);
  assert.deepEqual([...b.sheets.keys()], ['Transactions', 'Ignored', 'Rules']);
  assert.equal(b.sheet('Transactions').rows[0][0], 'date');
  assert.ok(b.logs.join('\n').includes(info.token));
  // running it again keeps the token
  assert.equal(b.setup().token, info.token);
});

test('every call needs the right token', () => {
  const { b, token } = fresh();
  assert.equal(b.get({ action: 'list' }).ok, false);
  assert.match(b.get({ action: 'list', token: 'nope' }).error, /Unauthorized/);
  assert.equal(b.post({ body: 'Purchase of $5.00 at X' }).ok, false);
  assert.equal(b.sheet('Transactions').getLastRow(), 1);
  assert.equal(b.get({ action: 'ping', token }).ok, true);
});

test('a bank notification is parsed and stored', () => {
  const { b, token } = fresh();
  const r = b.post({ token, source: 'notification', app: 'RBC', title: 'RBC', body: 'A purchase of $54.21 was made at METRO #123 with your RBC Visa card ending in 1234' });
  assert.equal(r.ok, true);
  assert.equal(r.status, 'added');
  assert.equal(r.message, '✓ 54.21 CAD · METRO #123 · Groceries');
  const [row] = b.sheet('Transactions').objects();
  assert.equal(row.amount, 54.21);
  assert.equal(row.currency, 'CAD');
  assert.equal(row.merchant, 'METRO #123');
  assert.equal(row.card, 'Visa ••1234');
  assert.equal(row.source, 'notification:RBC');
  assert.equal(row.status, 'ok');
  assert.ok(row.date instanceof Date);
  assert.match(row.id, /^t[0-9a-f]{12}$/);
  assert.equal(row.raw, 'RBC | A purchase of $54.21 was made at METRO #123 with your RBC Visa card ending in 1234');
});

test('one-time codes are never stored', () => {
  const { b, token } = fresh();
  b.post({ token, app: 'TD', body: 'Your verification code is 482913. Do not share it.' });
  b.post({ token, app: 'Desjardins', body: 'Votre code de sécurité est 7731' });
  b.post({ token, app: 'TD', body: 'New sign-in to your account from iPhone' });
  const raws = b.sheet('Ignored').objects().map((r) => r.raw);
  assert.deepEqual(raws, ['Your verification code is ••••••. Do not share it.', 'Votre code de sécurité est ••••••', 'New sign-in to your account from iPhone']);
  assert.ok(!JSON.stringify(b.get({ token }).ignored).includes('482913'));
});

test('non-transactions go to the Ignored tab', () => {
  const { b, token } = fresh();
  const r = b.post({ token, app: 'TD', title: 'TD', body: 'Your verification code is 482913' });
  assert.equal(r.status, 'ignored');
  assert.equal(r.reason, 'no-amount');
  assert.equal(b.sheet('Transactions').getLastRow(), 1);
  const [row] = b.sheet('Ignored').objects();
  assert.equal(row.reason, 'no-amount');
  assert.equal(row.source, 'notification:TD');
});

test('the same notification twice is stored once', () => {
  const { b, token } = fresh();
  const n = { token, app: 'TD', body: 'A purchase of $23.45 at TIM HORTONS was made on your TD credit card ending in 4321' };
  assert.equal(b.post(n).status, 'added');
  assert.equal(b.post(n).status, 'exists');
  assert.equal(b.sheet('Transactions').getLastRow(), 2);
});

test('Apple Pay automation + bank notification for one purchase: the second is flagged, not counted', () => {
  const { b, token } = fresh();
  const a = b.post({ token, source: 'applepay', amount: '$12.50', merchant: 'Starbucks', card: 'RBC Visa' });
  assert.equal(a.status, 'added');
  assert.equal(a.tx.category, 'Dining');
  const n = b.post({ token, app: 'RBC', body: 'A purchase of $12.50 was made at STARBUCKS #0042 with your RBC Visa card ending in 1234' });
  assert.equal(n.status, 'duplicate');
  assert.match(n.tx.note, /Possible duplicate of Starbucks \(applepay\)/);
  const list = b.get({ token });
  assert.deepEqual(list.transactions.map((t) => t.status), ['ok', 'duplicate']);
});

test('same amount on two different cards is not a duplicate', () => {
  const { b, token } = fresh();
  b.post({ token, app: 'RBC', body: 'Purchase of $20.00 at SHELL with card ending in 1111' });
  const r = b.post({ token, app: 'TD', body: 'Purchase of $20.00 at ESSO with card ending in 2222' });
  assert.equal(r.status, 'added');
});

test('list returns transactions, ignored notifications, rules and the currency', () => {
  const { b, token } = fresh();
  b.post({ token, app: 'X', body: 'Purchase of $9.99 at NETFLIX.COM' });
  b.post({ token, app: 'X', body: 'Your balance is $100.00' });
  const r = b.get({ action: 'list', token });
  assert.equal(r.ok, true);
  assert.equal(r.currency, 'CAD');
  assert.equal(r.transactions.length, 1);
  assert.match(r.transactions[0].date, /^\d{4}-\d{2}-\d{2}T/);
  assert.equal(r.transactions[0].category, 'Subscriptions');
  assert.equal(r.ignored.length, 1);
  assert.equal(r.ignored[0].reason, 'not-a-spend');
  assert.deepEqual(r.rules, []);
});

test('the dashboard can add, edit and delete', () => {
  const { b, token } = fresh();
  const added = b.post({ token, action: 'add', tx: { amount: 30, merchant: 'Farmers market', date: '2026-10-02T15:00:00Z', note: 'veggies' } });
  assert.equal(added.ok, true);
  assert.equal(added.tx.category, 'Groceries');
  assert.equal(added.tx.source, 'manual');
  assert.equal(added.tx.date, '2026-10-02T15:00:00.000Z');
  const id = added.tx.id;

  let u = b.post({ token, action: 'update', id, fields: { category: 'Dining', type: 'refund' } });
  assert.equal(u.tx.category, 'Dining');
  assert.equal(u.tx.amount, -30, 'a refund is stored negative');
  u = b.post({ token, action: 'update', id, fields: { status: 'excluded', type: 'purchase', merchant: 'Market' } });
  assert.deepEqual([u.tx.status, u.tx.amount, u.tx.merchant, u.tx.note], ['excluded', 30, 'Market', 'veggies']);
  assert.equal(b.post({ token, action: 'update', id, fields: { status: 'bogus' } }).tx.status, 'excluded');

  assert.equal(b.post({ token, action: 'delete', id }).ok, true);
  assert.equal(b.sheet('Transactions').getLastRow(), 1);
  assert.equal(b.post({ token, action: 'delete', id }).ok, false);
  assert.equal(b.post({ token, action: 'add', tx: { merchant: 'No amount' } }).ok, false);
});

test('a rule goes on top, re-categorizes past rows and applies to new ones', () => {
  const { b, token } = fresh();
  b.post({ token, app: 'X', body: 'Purchase of $4.00 at CORNER CAFE' });
  b.post({ token, app: 'X', body: 'Purchase of $6.00 at CORNER CAFE' });
  b.post({ token, action: 'rule', pattern: 'cafe', category: 'Treats', apply: false });
  const r = b.post({ token, action: 'rule', pattern: 'corner cafe', category: 'Coffee' });
  assert.equal(r.updated, 2);
  assert.deepEqual(r.rules.map((x) => x.pattern), ['corner cafe', 'cafe']);
  assert.deepEqual(b.sheet('Transactions').objects().map((t) => t.category), ['Coffee', 'Coffee']);
  assert.equal(b.post({ token, app: 'X', body: 'Purchase of $3.00 at CORNER CAFE' }).tx.category, 'Coffee');
  assert.equal(b.post({ token, app: 'X', body: 'Purchase of $3.50 at OTHER CAFE' }).tx.category, 'Treats');
  // same pattern again replaces the old rule instead of adding a second one
  assert.equal(b.post({ token, action: 'rule', pattern: 'Cafe', category: 'Dining', apply: false }).rules.length, 2);
});

test('the default currency decides what a bare "$" means', () => {
  const { b, token } = fresh('USD');
  assert.equal(b.post({ token, body: 'Purchase of $5.00 at A' }).tx.currency, 'USD');
  assert.equal(b.post({ token, action: 'settings', currency: 'cad' }).currency, 'CAD');
  assert.equal(b.post({ token, body: 'Purchase of $6.00 at B' }).tx.currency, 'CAD');
  assert.equal(b.post({ token, action: 'settings', currency: 'dollars' }).ok, false);
});

test('token in the URL, form-encoded posts and plain-text bodies all work', () => {
  const { b, token } = fresh();
  assert.equal(b.post({ body: 'Purchase of $1.00 at ALPHA' }, { token }).status, 'added');
  assert.equal(b.postForm({ token, app: 'Bank', title: 'Bank', body: 'Purchase of $2.00 at BRAVO' }).status, 'added');
  assert.equal(b.post('Purchase of $3.00 at CHARLIE', { token }).status, 'added');
  assert.deepEqual(b.sheet('Transactions').objects().map((t) => t.merchant), ['ALPHA', 'BRAVO', 'CHARLIE']);
});

test('rows typed straight into the sheet get an id', () => {
  const { b, token } = fresh();
  b.sheet('Transactions').rows.push([new Date('2026-10-05T12:00:00Z'), 15, 'CAD', 'Typed by hand', '', '', '', '', '', '', '', '', '']);
  const r = b.get({ token });
  assert.equal(r.transactions.length, 1);
  const t = r.transactions[0];
  assert.match(t.id, /^t[0-9a-f]{12}$/);
  assert.deepEqual([t.type, t.status, t.category, t.source], ['purchase', 'ok', 'Other', 'sheet']);
  assert.equal(b.sheet('Transactions').objects()[0].id, t.id);
  assert.equal(b.post({ token, action: 'update', id: t.id, fields: { category: 'Shopping' } }).tx.category, 'Shopping');
});

test('capture date: ISO close to now is kept, anything else becomes now', () => {
  const { b, token } = fresh();
  const iso = new Date(Date.now() - 60_000).toISOString();
  assert.equal(b.post({ token, body: 'Purchase of $1.00 at A', date: iso }).tx.date, iso);
  const d = new Date(b.post({ token, body: 'Purchase of $2.00 at B', date: '31 oct. 2026 à 16:15' }).tx.date);
  assert.ok(Math.abs(d - Date.now()) < 5000);
  const old = new Date(b.post({ token, body: 'Purchase of $3.00 at C', date: '2020-01-01T00:00:00Z' }).tx.date);
  assert.ok(Math.abs(old - Date.now()) < 5000);
});

test('the Ignored tab is trimmed', () => {
  const { b, token } = fresh();
  b.context.IGNORED_MAX = 3;
  for (let i = 0; i < 6; i++) b.post({ token, body: `Notice ${i}: your new statement is ready` });
  const rows = b.sheet('Ignored').objects();
  assert.equal(rows.length, 3);
  assert.equal(rows[2].raw, 'Notice 5: your new statement is ready');
});

test('apps-script/Spending.gs is up to date (run: node tools/build.mjs)', () => {
  const gs = fs.readFileSync(new URL('../apps-script/Spending.gs', import.meta.url), 'utf8');
  const parser = fs.readFileSync(new URL('../src/parser.js', import.meta.url), 'utf8');
  const backend = fs.readFileSync(new URL('../src/backend.gs', import.meta.url), 'utf8');
  assert.ok(gs.includes(parser) && gs.endsWith(backend), 'Spending.gs is stale');
});

test('Apple Pay style fields default to the applepay source', () => {
  const { b, token } = fresh();
  const r = b.post({ token, amount: '$4.10', merchant: 'Tim Hortons', card: 'Visa' });
  assert.equal(r.tx.source, 'applepay');
  assert.equal(b.post({ token, body: 'Purchase of $4.10 at TIM HORTONS #22 with card ending in 1234' }).status, 'duplicate');
});

test('a minimal Shortcut works: token in the URL, only title and body', () => {
  const { b, token } = fresh();
  const r = b.post({ title: 'Desjardins', body: 'Achat de 8,50 $ chez CAFE OLIMPICO effectué avec votre carte' }, { token });
  assert.equal(r.status, 'added');
  assert.equal(r.tx.source, 'notification');
  assert.equal(r.tx.merchant, 'CAFE OLIMPICO');
});
