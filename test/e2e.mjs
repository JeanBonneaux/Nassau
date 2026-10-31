// End-to-end check of the dashboard in Chromium (phone-sized), against the real Spending.gs
// running behind tools/dev-server.mjs. Needs Playwright with Chromium installed.
//   node test/e2e.mjs                # run the checks
//   node test/e2e.mjs --screenshots  # also refresh docs/img/*.png
import { createRequire } from 'node:module';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { startDevServer } from '../tools/dev-server.mjs';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SHOTS = path.join(ROOT, 'docs', 'img');
const shoot = process.argv.includes('--screenshots');
if (shoot) fs.mkdirSync(SHOTS, { recursive: true });

const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'en-CA', timezoneId: 'UTC' };
const SPENDING = ['purchase', 'refund', 'cash', 'fee'];
const errors = [];
function watch(page, label, { networkErrorsExpected = false } = {}) {
  page.on('pageerror', (e) => errors.push(`${label} pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    if (networkErrorsExpected && /Failed to load resource/.test(m.text())) return;
    errors.push(`${label} console: ${m.text()}`);
  });
}
const money = (s) => parseFloat(String(s).replace(/[^\d.-]/g, ''));
const step = (s) => console.log('  ·', s);

const srv = await startDevServer({ port: 0 });
const browser = await chromium.launch();
try {
  console.log('first visit + sample data');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page = await ctx.newPage();
    watch(page, 'demo');
    await page.goto(srv.url);
    await page.getByText('Track spending from your bank notifications').waitFor();
    step('welcome screen shown');
    await page.getByRole('button', { name: 'Try it with sample data' }).click();
    await page.locator('.hero').waitFor();
    assert.match(await page.locator('.hero').textContent(), /\$\d/);
    assert.ok(await page.locator('.cat').count() >= 4, 'categories rendered');
    assert.ok(await page.locator('#list .row').count() >= 5, 'list rendered');
    assert.ok(await page.locator('#daily .bar').count() >= 3, 'daily bars rendered');
    assert.equal(await page.locator('.banner').isVisible(), true);
    step('sample data renders: hero, chart, categories, list');
    // A duplicate is shown but not counted, the review item has its badge.
    await page.getByRole('tab', { name: /To review/ }).click();
    assert.ok(await page.locator('#list .badge.warn').count() >= 1);
    await page.getByRole('tab', { name: 'All' }).click();
    if (shoot) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.join(SHOTS, 'dashboard-light.png') });
      await page.locator('#list').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(SHOTS, 'transactions-light.png') });
    }
    // Sample data survives a reload (kept in localStorage).
    const before = await page.locator('.hero').textContent();
    await page.reload();
    await page.locator('.hero').waitFor();
    assert.equal(await page.locator('.hero').textContent(), before);
    step('sample data persists across reloads');
    await ctx.close();
  }

  console.log('connected to the sheet (mock Apps Script)');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'light' });
    await ctx.addInitScript(([api, token]) => {
      if (!localStorage.getItem('spend.settings.v1')) {
        localStorage.setItem('spend.settings.v1', JSON.stringify({ url: api, token, currency: 'CAD', budget: 1500 }));
      }
    }, [srv.api, srv.token]);
    const page = await ctx.newPage();
    watch(page, 'live');
    await page.goto(srv.url);
    await page.locator('#foot', { hasText: 'Synced' }).waitFor();

    const expectedTotal = () => {
      const now = new Date();
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      return srv.backend.get({ token: srv.token }).transactions
        .filter((t) => new Date(t.date) >= start && SPENDING.includes(t.type) && !['duplicate', 'excluded'].includes(t.status) && t.currency === 'CAD')
        .reduce((s, t) => s + t.amount, 0);
    };
    let hero = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(hero - expectedTotal()) < 0.005, `hero ${hero} != ${expectedTotal()}`);
    assert.ok(await page.locator('.meter').isVisible(), 'budget meter shown');
    step(`hero total matches the sheet (${hero})`);

    // Paste a notification.
    await page.locator('#addBtn').click();
    await page.locator('#fText').fill('Achat de 12,34 $ chez BOULANGERIE GUILLAUME effectué avec votre carte Visa se terminant par 5678.');
    await page.locator('#fPreview', { hasText: 'BOULANGERIE GUILLAUME' }).waitFor();
    assert.match(await page.locator('#fPreview').textContent(), /Dining/);
    if (shoot) await page.screenshot({ path: path.join(SHOTS, 'paste-light.png') });
    await page.locator('#fSavePaste').click();
    await page.locator('#toast', { hasText: 'Added' }).waitFor();
    let row = srv.backend.sheet('Transactions').objects().find((r) => r.merchant === 'BOULANGERIE GUILLAUME');
    assert.ok(row, 'pasted transaction stored in the sheet');
    assert.deepEqual([row.amount, row.currency, row.source, row.card, row.category], [12.34, 'CAD', 'paste', 'Visa ••5678', 'Dining']);
    hero = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(hero - expectedTotal()) < 0.005, 'hero updated after add');
    step('pasted notification parsed, previewed, saved to the sheet');

    // Edit it: new category + "always" rule.
    await page.locator('#list .row', { hasText: 'BOULANGERIE GUILLAUME' }).click();
    await page.locator('#fCategory').selectOption('Shopping');
    await page.locator('#fRule').check();
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#toast', { hasText: 'Saved' }).waitFor();
    await page.locator('#foot', { hasText: 'Synced' }).waitFor();
    row = srv.backend.sheet('Transactions').objects().find((r) => r.merchant === 'BOULANGERIE GUILLAUME');
    assert.equal(row.category, 'Shopping');
    assert.deepEqual(srv.backend.sheet('Rules').objects()[0], { pattern: 'BOULANGERIE GUILLAUME', category: 'Shopping' });
    step('edit + category rule saved to the sheet');

    // Exclude something from the totals.
    const before = money(await page.locator('.hero').textContent());
    const target = page.locator('#list .row:not(.muted)').first();
    const amt = money(await target.locator('.amt span').first().textContent());
    await target.click();
    await page.locator('#fCount').uncheck();
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#toast', { hasText: 'Saved' }).waitFor();
    const after = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(before - amt - after) < 0.005, `excluding ${amt}: ${before} -> ${after}`);
    assert.ok(srv.backend.sheet('Transactions').objects().some((r) => r.status === 'excluded'));
    step('"count it" toggle updates the total and the sheet');

    // Category filter, search, chart tooltip, ignored tab.
    await page.locator('.cat').first().click();
    const catName = (await page.locator('#chipRow .chip').textContent()).replace('Category:', '').replace('✕', '').trim();
    const metas = await page.locator('#list .row .meta').allTextContents();
    assert.ok(metas.length > 0 && metas.every((m) => m.startsWith(catName)), 'category filter applies');
    await page.locator('#chipRow .chip').click();
    await page.locator('#q').fill('netflix');
    const names = await page.locator('#list .row .name').allTextContents();
    assert.ok(names.length > 0 && names.every((n) => /netflix/i.test(n)), 'search filters the list');
    assert.equal(await page.locator('#q').inputValue(), 'netflix');
    await page.locator('#q').fill('');
    step('category filter and search work');

    const bar = page.locator('#daily .bar').last();
    const box = await bar.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + Math.min(4, box.height / 2));
    await page.locator('#tip:not([hidden])').waitFor();
    assert.match(await page.locator('#tip').textContent(), /\$/);
    await page.locator('#daily svg').focus();
    await page.keyboard.press('ArrowLeft');
    assert.ok(await page.locator('#tip:not([hidden])').isVisible(), 'keyboard shows the tooltip');
    await page.locator('details.table-view summary').click();
    assert.ok(await page.locator('details.table-view tbody tr').count() > 0, 'table view lists days');
    step('chart tooltip (pointer + keyboard) and table view');

    await page.getByRole('tab', { name: /Ignored/ }).click();
    await page.locator('#list .raw', { hasText: 'verification code' }).waitFor();
    step('ignored notifications listed');
    await page.getByRole('tab', { name: 'All' }).click();

    // Previous month navigation keeps working.
    await page.locator('#prevMonth').click();
    assert.notEqual(await page.locator('#monthLabel').textContent(), '');
    await page.locator('#nextMonth').click();
    assert.equal(await page.locator('#nextMonth').isDisabled(), true);

    // Settings: a wrong token is reported by "Test connection".
    await page.locator('#settingsBtn').click();
    await page.locator('#sToken').fill('wrong-token');
    await page.locator('[data-sheet="test"]').click();
    await page.locator('#sTest', { hasText: 'Unauthorized' }).waitFor();
    await page.locator('#sToken').fill(srv.token);
    await page.locator('[data-sheet="test"]').click();
    await page.locator('#sTest', { hasText: 'Connected' }).waitFor();
    await page.locator('[data-sheet="cancel"]').click();
    step('settings: connection test reports bad and good tokens');

    await ctx.close();
  }

  console.log('first-time connect, setup link, failed save');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page = await ctx.newPage();
    watch(page, 'connect');
    await page.goto(srv.url);
    await page.getByRole('button', { name: 'Connect my sheet' }).click();
    assert.equal(await page.locator('#sShortcutBox').isVisible(), false, 'no Shortcut link before the URL and token are in');
    await page.locator('#sUrl').fill(srv.api);
    await page.locator('#sToken').fill(srv.token);
    assert.equal(await page.locator('#sShortcut').inputValue(), `${srv.api}?token=${srv.token}`);
    await page.locator('#sCurrency').selectOption('USD');
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#foot', { hasText: 'Synced' }).waitFor();
    await page.waitForFunction(() => window.__spend.state.data.currency === 'USD');
    assert.equal(srv.backend.props.get('CURRENCY'), 'USD', 'currency pushed to the sheet');
    await page.locator('.facts', { hasText: 'other currencies' }).waitFor();
    srv.backend.props.set('CURRENCY', 'CAD');
    step('connect from the welcome screen; currency saved to the sheet');
    await ctx.close();

    const ctx2 = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page2 = await ctx2.newPage();
    watch(page2, 'setup-link', { networkErrorsExpected: true }); // the last check cuts the network on purpose
    const enc = Buffer.from(JSON.stringify({ u: srv.api, k: srv.token, c: 'CAD' })).toString('base64url');
    await page2.goto(srv.url + '#setup=' + enc);
    await page2.locator('#toast', { hasText: 'Settings imported' }).waitFor();
    await page2.locator('#foot', { hasText: 'Synced' }).waitFor();
    assert.ok(await page2.locator('#list .row').count() > 0);
    // Applied once: a later change in Settings is not overwritten by the link on reload.
    await page2.evaluate(() => {
      const s = JSON.parse(localStorage.getItem('spend.settings.v1'));
      s.budget = 999;
      localStorage.setItem('spend.settings.v1', JSON.stringify(s));
    });
    await page2.reload();
    await page2.locator('#foot', { hasText: 'Synced' }).waitFor();
    assert.equal(await page2.evaluate(() => window.__spend.state.settings.budget), 999);
    step('setup link imports the settings once');

    // Fallback: the setup link pasted into the URL field fills in the settings.
    const ctx3 = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page3 = await ctx3.newPage();
    watch(page3, 'paste-link');
    await page3.goto(srv.url);
    await page3.getByRole('button', { name: 'Connect my sheet' }).click();
    await page3.locator('#sUrl').fill(srv.url + '#setup=' + enc);
    assert.equal(await page3.locator('#sUrl').inputValue(), srv.api);
    assert.equal(await page3.locator('#sToken').inputValue(), srv.token);
    await page3.locator('[data-sheet="save"]').click();
    await page3.locator('#foot', { hasText: 'Synced' }).waitFor();
    step('setup link pasted into the URL field fills in the settings');
    await ctx3.close();

    // The sheet goes away: an edit is rolled back instead of pretending it was saved.
    const first = page2.locator('#list .row:not(.muted)').first();
    const name = await first.locator('.name').textContent();
    await first.click();
    await page2.locator('#fMerchant').fill('RENAMED WHILE OFFLINE');
    await page2.route('**/exec**', (route) => route.abort());
    await page2.locator('[data-sheet="save"]').click();
    await page2.locator('#toast', { hasText: 'Not saved' }).waitFor();
    assert.equal(await page2.locator('#list .row', { hasText: 'RENAMED WHILE OFFLINE' }).count(), 0, 'rolled back');
    assert.ok(await page2.locator('#list .row .name', { hasText: name.replace(/Check|Duplicate\?|Not counted/g, '').trim() }).count() > 0);
    step('failed save is rolled back');
    await ctx2.close();
  }

  console.log('dark mode + offline');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'dark' });
    const page = await ctx.newPage();
    watch(page, 'dark');
    await page.goto(srv.url);
    await page.getByRole('button', { name: 'Try it with sample data' }).click();
    await page.locator('.hero').waitFor();
    const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    assert.equal(bg, 'rgb(13, 13, 13)');
    if (shoot) await page.screenshot({ path: path.join(SHOTS, 'dashboard-dark.png') });
    step('dark theme applied');
    await ctx.close();

    // Unreachable sheet: cached data stays visible with a banner (page errors only; the 404 itself is expected).
    const ctx2 = await browser.newContext({ ...phone, colorScheme: 'light' });
    const cache = srv.backend.get({ token: srv.token });
    await ctx2.addInitScript(([api, token, cacheJson]) => {
      localStorage.setItem('spend.settings.v1', JSON.stringify({ url: api + '-missing', token, currency: 'CAD' }));
      localStorage.setItem('spend.cache.v1', cacheJson);
    }, [srv.api, srv.token, JSON.stringify({ ...cache, savedAt: Date.now() - 600000 })]);
    const p2 = await ctx2.newPage();
    p2.on('pageerror', (e) => errors.push(`offline pageerror: ${e.message}`));
    await p2.goto(srv.url);
    await p2.locator('.banner', { hasText: 'Showing data from 10 min ago' }).waitFor();
    assert.ok(await p2.locator('#list .row').count() > 0, 'cached rows still shown');
    step('offline: cached data + banner');
    await ctx2.close();
  }

  assert.deepEqual(errors, [], 'no page or console errors');
  console.log('e2e: all checks passed');
} catch (err) {
  console.error(err);
  if (errors.length) console.error('page errors:', errors);
  process.exitCode = 1;
} finally {
  await browser.close();
  srv.server.close();
}
