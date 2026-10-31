import test from 'node:test';
import assert from 'node:assert/strict';
import { loadBackend } from '../tools/gas-mock.mjs';

function fresh(props = {}) {
  const b = loadBackend();
  const { token } = b.setup();
  b.props.set('CURRENCY', 'CAD');
  for (const [k, v] of Object.entries(props)) b.props.set(k, v);
  return { b, token };
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
const NOTE = { title: 'Scotiabank', body: 'Achat de 54,21 $ chez IGA EXTRA avec votre carte se terminant par 1234.' };

test('without an API key nothing is sent anywhere', () => {
  const { b, token } = fresh();
  const r = b.post({ token, ...NOTE });
  assert.equal(r.status, 'added');
  assert.equal(r.tx.reader, 'rules');
  assert.equal(b.fetches.length, 0);
  assert.equal(b.get({ token, action: 'ping' }).claude, 'off');
});

test('with a key, Claude reads the notification and its answer is stored', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.onFetch(() => reply(RECORD));
  const r = b.post({ token, ...NOTE });
  assert.equal(r.status, 'added');
  assert.deepEqual([r.tx.merchant, r.tx.amount, r.tx.category, r.tx.reader], ['IGA Extra', 54.21, 'Groceries', 'claude']);
  assert.match(r.message, /read by Claude/);
  assert.equal(b.sheet('Transactions').objects()[0].reader, 'claude');
  assert.equal(b.get({ token, action: 'ping' }).claude, 'always · claude-opus-5-5');
});

test('the request follows the documented API shape', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.post({ token, app: 'X', body: 'Purchase of $1.00 at ALPHA' }); // gives Claude a past merchant
  b.post({ token, action: 'rule', pattern: 'iga', category: 'Épicerie' });
  b.onFetch(() => reply(RECORD));
  b.post({ token, app: 'Scotiabank', title: 'Scotiabank', body: 'Your verification code is 482913 and Achat de 54,21 $ chez IGA' });
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
  assert.match(user, /from the app "Scotiabank"/);
  assert.ok(!user.includes('482913'), 'one-time codes are masked before leaving Google');
});

test('the user\'s rules win over Claude\'s category', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.post({ token, action: 'rule', pattern: 'iga', category: 'Épicerie' });
  b.onFetch(() => reply(RECORD));
  assert.equal(b.post({ token, ...NOTE }).tx.category, 'Épicerie');
});

test('Haiku is called without the fallback parameter it does not support', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test', CLAUDE_MODEL: 'claude-haiku-5-5' });
  b.onFetch(() => reply(RECORD));
  b.post({ token, ...NOTE });
  const call = b.fetches.at(-1);
  assert.equal(call.body.model, 'claude-haiku-5-5');
  assert.equal(call.body.fallbacks, undefined);
  assert.equal(call.params.headers['anthropic-beta'], undefined);
});

test('failures fall back to the rule-based reading', () => {
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
    const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
    b.onFetch(handler);
    const r = b.post({ token, ...NOTE });
    assert.equal(r.status, 'added');
    assert.deepEqual([r.tx.merchant, r.tx.amount, r.tx.reader], ['IGA EXTRA', 54.21, 'rules']);
  }
});

test('Claude can catch a transaction the rules missed', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.onFetch(() => reply({ ...RECORD, merchant: 'Cafe Olimpico', amount: 7.5, category: 'Dining', card: '' }));
  const r = b.post({ token, title: 'Wealthsimple', body: 'Cafe Olimpico 7.50' });
  assert.equal(r.status, 'added');
  assert.deepEqual([r.tx.merchant, r.tx.amount, r.tx.reader], ['Cafe Olimpico', 7.5, 'claude']);
});

test('when Claude says "not a transaction" but the rules are sure, it is kept for review', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.onFetch(() => reply({ ...RECORD, is_transaction: false, ignore_reason: 'promo', amount: 0 }));
  const r = b.post({ token, ...NOTE });
  assert.equal(r.status, 'added');
  assert.equal(r.tx.status, 'review');
  assert.match(r.tx.note, /Claude thinks this is not a transaction \(promo\)/);
});

test('Claude can set aside a notification the rules were unsure about', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.onFetch(() => reply({ ...RECORD, is_transaction: false, ignore_reason: 'statement', amount: 0 }));
  const r = b.post({ token, title: 'Card', body: 'Amount: 45.20' }); // rules: amount but no merchant -> review
  assert.equal(r.status, 'ignored');
  assert.equal(r.reason, 'statement');
});

test('review mode only asks Claude when the rules are unsure', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test', CLAUDE_MODE: 'review' });
  b.onFetch(() => reply(RECORD));
  b.post({ token, ...NOTE });                                        // clear: not sent
  b.post({ token, body: 'New sign-in to your account from iPhone' }); // no digits: not sent
  assert.equal(b.fetches.length, 0);
  b.post({ token, title: 'Card', body: 'Amount: 45.20' });           // unsure: sent
  assert.equal(b.fetches.length, 1);
});

test('CLAUDE_MODE=off keeps everything local even with a key', () => {
  const { b, token } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test', CLAUDE_MODE: 'off' });
  b.onFetch(() => reply(RECORD));
  b.post({ token, ...NOTE });
  assert.equal(b.fetches.length, 0);
});

test('an older sheet gets the new "reader" column header', () => {
  const { b, token } = fresh();
  const sheet = b.sheet('Transactions');
  sheet.rows[0] = sheet.rows[0].slice(0, 13); // header as written by version 0.1
  b.get({ token, action: 'list' });
  assert.equal(sheet.rows[0][13], 'reader');
});

test('testClaude logs the reading and the cost', () => {
  const { b } = fresh({ ANTHROPIC_API_KEY: 'sk-ant-test' });
  b.onFetch(() => reply(RECORD));
  b.context.testClaude();
  const log = b.logs.join('\n');
  assert.match(log, /900 tokens in, 120 out ≈ \$0\.0060/);
  assert.match(log, /"merchant":"IGA Extra"/);
});
