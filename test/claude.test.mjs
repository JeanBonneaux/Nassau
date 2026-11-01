import test from 'node:test';
import assert from 'node:assert/strict';
import { loadBackend } from '../tools/gas-mock.mjs';

function fresh(props = {}) {
  const b = loadBackend();
  const info = b.setup();
  for (const [k, v] of Object.entries(props)) b.props.set(k, v);
  return { b, admin: info.adminToken, capture: info.captureToken };
}

// A Messages API response whose last text block is the JSON record.
function reply(record, extra = {}) {
  return {
    body: {
      id: 'msg_test', type: 'message', role: 'assistant', model: 'claude-opus-5-5', stop_reason: 'end_turn',
      content: [{ type: 'thinking', thinking: '', signature: 'x' }, { type: 'text', text: JSON.stringify(record) }],
      usage: { input_tokens: 900, output_tokens: 120 },
      ...extra
    }
  };
}
const RECORD = {
  is_transaction: true, ignore_reason: 'none', type: 'purchase', amount: 54.21, currency: 'CAD',
  merchant: 'IGA Extra', card: 'Visa ••1234', category: 'Groceries', confidence: 'high'
};
const CLEAR = { title: 'InfoAlerte Scotia', body: 'Un achat de 54,21 $ a été effectué chez IGA EXTRA avec votre carte se terminant par 1234.' };
const UNSURE = { title: 'Capital One', body: 'A purchase of $54.21 was approved on your card ending 1234' }; // amount, no merchant -> review
const KEY = { ANTHROPIC_API_KEY: 'sk-ant-test' };

test('without an API key nothing is sent anywhere, ever', () => {
  const { b, admin, capture } = fresh();
  assert.equal(b.post({ token: capture, ...UNSURE }).tx.reader, 'rules');
  b.context.enrichPending_();
  assert.equal(b.fetches.length, 0);
  assert.equal(b.post({ token: admin, action: 'ping' }).claude, 'off');
});

test('with a key, Claude is never in the Shortcut request path: unsure rows wait for the trigger', () => {
  const { b, admin, capture } = fresh(KEY);
  b.onFetch(() => reply(RECORD));
  const clear = b.post({ token: capture, ...CLEAR });
  assert.deepEqual([clear.tx.reader, clear.tx.status], ['rules', 'ok'], 'a clear notification is not sent to Claude in review mode');
  b.setNow(new Date(Date.now() + 20 * 60000)); // otherwise the same amount minutes later would be a suspected duplicate
  const unsure = b.post({ token: capture, ...UNSURE });
  assert.deepEqual([unsure.tx.reader, unsure.tx.status], ['pending', 'review']);
  assert.equal(b.fetches.length, 0, 'no network call during capture');
  const r = b.context.enrichPending_();
  assert.equal(r.calls, 1);
  const row = b.sheet('Transactions').objects().find((t) => t.reader !== 'rules');
  assert.deepEqual([row.reader, row.merchant, row.category, row.status], ['claude', 'IGA Extra', 'Groceries', 'ok']);
  assert.equal(b.post({ token: admin, action: 'ping' }).claude, 'review · claude-opus-5-5');
  assert.equal(b.post({ token: admin, action: 'ping' }).health.claude.callsToday, 1);
});

test('the request follows the documented API shape and masks codes and long numbers', () => {
  const { b, admin, capture } = fresh(KEY);
  b.post({ token: capture, title: 'Scotia', body: 'Purchase of $1.00 at ALPHA' }); // gives Claude a past merchant
  b.post({ token: admin, action: 'rule', pattern: 'iga', category: 'Épicerie' });
  b.onFetch(() => reply(RECORD));
  b.post({ token: capture, title: 'Capital One', body: 'Your verification code is 482913 and account 1234567890 was charged $54.21' });
  b.context.enrichPending_();
  const call = b.fetches.at(-1);
  assert.equal(call.url, 'https://api.anthropic.com/v1/messages');
  assert.equal(call.params.method, 'post');
  assert.equal(call.params.headers['x-api-key'], 'sk-ant-test');
  assert.equal(call.params.headers['anthropic-version'], '2026-10-21');
  assert.equal(call.params.headers['anthropic-beta'], 'server-side-fallback-2026-07-01');
  const body = call.body;
  assert.equal(body.model, 'claude-opus-5-5');
  assert.equal(body.fallbacks, 'default');
  assert.equal(body.output_config.effort, 'low');
  assert.equal(body.output_config.format.type, 'json_schema');
  assert.equal(body.output_config.format.schema.additionalProperties, false);
  assert.equal(body.temperature, undefined);
  assert.equal(body.thinking, undefined);
  const user = body.messages[0].content;
  assert.match(user, /Default currency: CAD/);
  assert.match(user, /- iga -> Épicerie/);
  assert.match(user, /ALPHA -> /);
  assert.ok(!user.includes('482913'), 'one-time codes are masked');
  assert.ok(!user.includes('1234567890'), 'long numbers are masked');
});

test('the user\'s rules win over Claude\'s category', () => {
  const { b, admin, capture } = fresh(KEY);
  b.post({ token: admin, action: 'rule', pattern: 'iga', category: 'Épicerie' });
  b.onFetch(() => reply(RECORD));
  b.post({ token: capture, ...UNSURE });
  b.context.enrichPending_();
  assert.equal(b.sheet('Transactions').objects()[0].category, 'Épicerie');
});

test('Haiku is called without the fallback parameter it does not support', () => {
  const { b, capture } = fresh({ ...KEY, CLAUDE_MODEL: 'claude-haiku-5-5' });
  b.onFetch(() => reply(RECORD));
  b.post({ token: capture, ...UNSURE });
  b.context.enrichPending_();
  const call = b.fetches.at(-1);
  assert.equal(call.body.model, 'claude-haiku-5-5');
  assert.equal(call.body.fallbacks, undefined);
  assert.equal(call.params.headers['anthropic-beta'], undefined);
});

test('failures keep the rule-based reading', () => {
  const cases = [
    () => ({ code: 500, body: { type: 'error', error: { type: 'api_error', message: 'boom' } } }),
    () => ({ code: 401, body: { type: 'error', error: { type: 'authentication_error', message: 'bad key' } } }),
    () => reply(RECORD, { stop_reason: 'refusal', content: [] }),
    () => reply(RECORD, { stop_reason: 'max_tokens' }),
    () => ({ body: 'not json' }),
    () => reply({ ...RECORD, amount: 0 }),
    () => { throw new Error('network down'); }
  ];
  for (const handler of cases) {
    const { b, capture } = fresh(KEY);
    b.onFetch(handler);
    b.post({ token: capture, ...UNSURE });
    b.context.enrichPending_();
    const row = b.sheet('Transactions').objects()[0];
    assert.deepEqual([row.amount, row.reader, row.status], [54.21, 'rules', 'review']);
  }
});

test('Claude can rescue a notification the rules could not read', () => {
  const { b, admin, capture } = fresh(KEY);
  b.onFetch(() => reply({ ...RECORD, merchant: 'Cafe Olimpico', amount: 7.5, category: 'Dining', card: '' }));
  const r = b.post({ token: capture, title: 'Wealthsimple', body: 'Olimpico: 7.50 plus taxes. New activity, check the app for details and more text to exceed the short-text limit.' });
  assert.equal(r.status, 'ignored');
  const out = b.context.enrichPending_();
  assert.equal(out.rescued, 1);
  const row = b.sheet('Transactions').objects()[0];
  assert.deepEqual([row.merchant, row.amount, row.reader, row.status, row.source], ['Cafe Olimpico', 7.5, 'claude', 'review', 'phone:wealthsimple']);
  assert.equal(b.get({ token: admin }).ignored.length, 0, 'the Ignored row is gone');
});

test('a disagreement on the amount is kept for review with both readings', () => {
  const { b, capture } = fresh(KEY);
  b.onFetch(() => reply({ ...RECORD, amount: 45.21 }));
  b.post({ token: capture, ...UNSURE });
  b.context.enrichPending_();
  const row = b.sheet('Transactions').objects()[0];
  assert.equal(row.status, 'review');
  assert.equal(row.amount, 54.21, 'the rule-based amount stays');
  assert.match(row.note, /Claude lit 45\.21 CAD/);
});

test('when Claude says "not a transaction" about a captured row, it is kept for review', () => {
  const { b, capture } = fresh(KEY);
  b.onFetch(() => reply({ ...RECORD, is_transaction: false, ignore_reason: 'promo', amount: 0 }));
  b.post({ token: capture, ...UNSURE });
  b.context.enrichPending_();
  const row = b.sheet('Transactions').objects()[0];
  assert.equal(row.status, 'review');
  assert.match(row.note, /Claude pense que ce n'est pas une transaction \(promotion\)/);
});

test('CLAUDE_MODE=always sends every notification, after the fact', () => {
  const { b, capture } = fresh({ ...KEY, CLAUDE_MODE: 'always' });
  b.onFetch(() => reply(RECORD));
  assert.equal(b.post({ token: capture, ...CLEAR }).tx.reader, 'pending');
  assert.equal(b.fetches.length, 0);
  b.context.enrichPending_();
  assert.equal(b.fetches.length, 1);
});

test('daily and monthly caps stop the calls', () => {
  const { b, admin, capture } = fresh({ ...KEY, CLAUDE_MAX_PER_DAY: '2' });
  b.onFetch(() => reply(RECORD));
  for (let i = 0; i < 4; i++) b.post({ token: capture, title: 'Capital One', body: `A purchase of $${10 + i}.00 was approved on your card ending 1234` });
  b.context.enrichPending_();
  assert.equal(b.fetches.length, 2);
  assert.equal(b.post({ token: admin, action: 'ping' }).health.claude.callsToday, 2);
  assert.ok(b.post({ token: admin, action: 'ping' }).health.claude.costMonthUsd > 0);
  const { b: b2, capture: c2 } = fresh({ ...KEY, CLAUDE_MAX_MONTH_USD: '0.001' });
  b2.onFetch(() => reply(RECORD));
  b2.post({ token: c2, ...UNSURE });
  b2.post({ token: c2, title: 'Capital One', body: 'A purchase of $12.00 was approved on your card ending 1234' });
  b2.context.enrichPending_();
  assert.equal(b2.fetches.length, 1, 'the first call exceeds the monthly cap, no second call');
});

test('CLAUDE_MODE=off keeps everything local even with a key; the old endpoint option is ignored', () => {
  const { b, capture } = fresh({ ...KEY, CLAUDE_MODE: 'off', CLAUDE_ENDPOINT: 'https://me--spending-reader.modal.run' });
  b.onFetch(() => reply(RECORD));
  b.post({ token: capture, ...UNSURE });
  b.context.enrichPending_();
  assert.equal(b.fetches.length, 0);
});

test('an older sheet gets the new column headers', () => {
  const { b, admin } = fresh();
  const sheet = b.sheet('Transactions');
  sheet.rows[0] = sheet.rows[0].slice(0, 13); // header as written by version 0.1
  b.get({ token: admin, action: 'list' });
  assert.deepEqual(sheet.rows[0].slice(13), ['reader', 'flags']);
});

test('testClaude logs the reading and the cost', () => {
  const { b } = fresh(KEY);
  b.onFetch(() => reply(RECORD));
  b.context.testClaude();
  const log = b.logs.join('\n');
  assert.match(log, /900 tokens in, 120 out ≈ \$0\.0060/);
  assert.match(log, /"merchant":"IGA Extra"/);
});
