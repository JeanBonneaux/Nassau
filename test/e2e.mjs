// End-to-end check of the dashboard in Chromium (phone-sized, French Canada), against the real
// Spending.gs running behind tools/dev-server.mjs. Needs Playwright with Chromium installed.
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

const phone = { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true, locale: 'fr-CA', timezoneId: 'America/Toronto' };
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
const money = (s) => parseFloat(String(s).replace(/[^\d,.-]/g, '').replace(/\s/g, '').replace(',', '.'));
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
    await page.getByText('Vos dépenses, à partir des notifications de vos banques').waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.lang), 'fr');
    step('écran d’accueil en français');
    await page.getByRole('button', { name: 'Voir avec des exemples' }).click();
    await page.locator('.hero').waitFor();
    assert.match(await page.locator('.hero').textContent(), /\d\s?\$/, 'montant en dollars canadiens');
    assert.match(await page.locator('#monthLabel').textContent(), /^[a-zéû]+ \d{4}$/i, 'mois en français');
    assert.ok(await page.locator('.cat').count() >= 4, 'catégories');
    assert.ok(await page.locator('#list .row').count() >= 5, 'liste');
    assert.ok(await page.locator('#daily .bar').count() >= 3, 'graphique');
    assert.ok(await page.locator('#insights').isVisible(), 'carte des abonnements / achats inhabituels');
    assert.match(await page.locator('#insights').textContent(), /Abonnements|Achats inhabituels|Où va l’argent/);
    assert.ok(await page.locator('#review').isVisible(), 'file « À vérifier »');
    assert.ok(await page.locator('#review .review-item').count() >= 1);
    assert.equal(await page.locator('.banner').isVisible(), true);
    step('exemples : total, graphique, catégories, analyses, file à vérifier');
    if (shoot) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.join(SHOTS, 'dashboard-light.png') });
      await page.locator('#list').scrollIntoViewIfNeeded();
      await page.screenshot({ path: path.join(SHOTS, 'transactions-light.png') });
    }
    const before = await page.locator('.hero').textContent();
    await page.reload();
    await page.locator('.hero').waitFor();
    assert.equal(await page.locator('.hero').textContent(), before);
    step('les exemples survivent à un rechargement');
    await ctx.close();
  }

  console.log('connected to the sheet (mock Apps Script)');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page = await ctx.newPage();
    watch(page, 'live');
    // The setup link from the Configuration tab connects the page and strips its own hash.
    srv.backend.props.delete('LAST_PHONE_AT'); // as on a fresh install: no notification from the phone yet
    await page.goto(srv.setupLink);
    await page.locator('#foot', { hasText: 'Synchronisé' }).waitFor();
    assert.equal(await page.evaluate(() => location.hash), '', 'le jeton ne reste pas dans l’adresse');
    assert.ok(await page.locator('#checklist').isVisible(), 'liste de vérification tant que le raccourci n’est pas relié');
    assert.match(await page.locator('#checklist').textContent(), /Raccourci relié/);
    step('lien de configuration → connecté, liste de vérification affichée');

    // The month shown by the page (Toronto time) against the sheet's rows in the same time zone.
    const monthOf = (iso) => {
      const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Toronto', year: 'numeric', month: 'numeric' }).formatToParts(new Date(iso));
      return parts.find((x) => x.type === 'year').value + '-' + parts.find((x) => x.type === 'month').value;
    };
    const expectedTotal = async () => {
      const m = await page.evaluate(() => { const d = window.__depenses.state.month; return d.getFullYear() + '-' + (d.getMonth() + 1); });
      return srv.backend.get({ token: srv.admin }).transactions
        .filter((t) => monthOf(t.date) === m && SPENDING.includes(t.type) && !['duplicate', 'excluded'].includes(t.status) && t.currency === 'CAD')
        .reduce((s, t) => s + t.amount, 0);
    };
    let hero = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(hero - await expectedTotal()) < 0.01, `total ${hero} != ${await expectedTotal()}`);
    assert.ok(await page.locator('.meter').isVisible(), 'budget du serveur affiché');
    step(`total du mois = feuille (${hero})`);

    // The Shortcut test ping turns step 3 green.
    srv.backend.post({ token: srv.capture, titre: '', soustitre: '', corps: '' });
    await page.locator('#syncBtn').click();
    await page.waitForFunction(() => window.__depenses.state.data.health.shortcutPingAt);
    assert.equal(await page.locator('#checklist').isVisible(), false, 'liste de vérification terminée');
    step('test ▶ du raccourci reçu → liste de vérification disparue');

    // Paste a notification: it goes through the server (dedup) and keeps its date.
    await page.locator('#addBtn').click();
    await page.locator('#fText').fill('Un achat de 12,34 $ a été effectué chez BOULANGERIE GUILLAUME avec votre carte Visa se terminant par 5678.');
    await page.locator('#fPreview', { hasText: 'BOULANGERIE GUILLAUME' }).waitFor();
    assert.match(await page.locator('#fPreview').textContent(), /Restos/);
    if (shoot) await page.screenshot({ path: path.join(SHOTS, 'paste-light.png') });
    await page.locator('#fSavePaste').click();
    await page.locator('#toast', { hasText: 'Ajoutée' }).waitFor();
    let row = srv.backend.sheet('Transactions').objects().find((r) => r.merchant === 'BOULANGERIE GUILLAUME');
    assert.ok(row, 'collée dans la feuille');
    assert.deepEqual([row.amount, row.currency, row.source, row.card, row.category], [12.34, 'CAD', 'paste', 'Visa ••5678', 'Dining']);
    hero = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(hero - await expectedTotal()) < 0.01, 'total mis à jour');
    step('notification collée → lue, enregistrée, comptée');

    // Edit: changing the category pre-checks the rule.
    await page.locator('#list .row', { hasText: 'BOULANGERIE GUILLAUME' }).click();
    await page.locator('#fCategory').selectOption('Shopping');
    assert.equal(await page.locator('#fRule').isChecked(), true, 'la règle est cochée d’office quand la catégorie change');
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#toast', { hasText: 'Enregistré' }).waitFor();
    await page.locator('#foot', { hasText: 'Synchronisé' }).waitFor();
    row = srv.backend.sheet('Transactions').objects().find((r) => r.merchant === 'BOULANGERIE GUILLAUME');
    assert.equal(row.category, 'Shopping');
    assert.equal(srv.backend.sheet('Rules').objects()[0].pattern, 'BOULANGERIE GUILLAUME');
    step('correction de catégorie → règle créée dans la feuille');

    // Review queue: one tap.
    const unsure = srv.backend.post({ token: srv.capture, title: 'Capital One', body: 'A purchase of $77.77 was approved on your card ending 5678' });
    assert.equal(unsure.status, 'review');
    await page.locator('#syncBtn').click();
    await page.locator('#review .review-item', { hasText: '77,77' }).waitFor();
    await page.locator(`[data-act="confirm"][data-id="${unsure.tx.id}"]`).click();
    await page.locator('#toast', { hasText: 'Confirmée' }).waitFor();
    await page.waitForFunction((id) => window.__depenses.state.data.transactions.find((t) => t.id === id).status === 'ok', unsure.tx.id);
    assert.equal(srv.backend.sheet('Transactions').objects().find((r) => r.id === unsure.tx.id).status, 'ok');
    step('« C’est bon » en un geste');

    // Exclude from the totals.
    const before = money(await page.locator('.hero').textContent());
    const target = page.locator('#list .row:not(.muted)').first();
    const amt = money(await target.locator('.amt span').first().textContent());
    await target.click();
    await page.locator('#fCount').uncheck();
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#toast', { hasText: 'Enregistré' }).waitFor();
    const after = money(await page.locator('.hero').textContent());
    assert.ok(Math.abs(before - amt - after) < 0.011, `exclusion de ${amt} : ${before} -> ${after}`);
    step('« Compter dans mes dépenses » décoché → total et feuille à jour');

    // Filters, search, chart tooltip, table view.
    await page.locator('.cat').first().click();
    const catName = (await page.locator('#chipRow .chip').textContent()).replace('Catégorie :', '').replace('✕', '').trim();
    const metas = await page.locator('#list .row .meta').allTextContents();
    assert.ok(metas.length > 0 && metas.every((m) => m.startsWith(catName)), 'filtre par catégorie');
    await page.locator('#chipRow .chip').click();
    await page.locator('#q').fill('netflix');
    const names = await page.locator('#list .row .name').allTextContents();
    assert.ok(names.length > 0 && names.every((n) => /netflix/i.test(n)), 'recherche');
    assert.equal(await page.locator('#q').inputValue(), 'netflix');
    await page.locator('#q').fill('');
    const bar = page.locator('#daily .bar').last();
    await bar.scrollIntoViewIfNeeded();
    const box = await bar.boundingBox();
    await page.mouse.move(box.x + box.width / 2, box.y + Math.min(4, box.height / 2));
    await page.locator('#tip:not([hidden])').waitFor();
    await page.locator('#daily svg').focus();
    await page.keyboard.press('ArrowLeft');
    assert.ok(await page.locator('#tip:not([hidden])').isVisible(), 'infobulle au clavier');
    await page.locator('details.table-view summary').click();
    assert.ok(await page.locator('details.table-view tbody tr').count() > 0, 'vue tableau');
    step('filtre, recherche, infobulle, tableau');

    // Ignored tab and "Ajouter" from an ignored row.
    await page.getByRole('tab', { name: /Ignorées/ }).click();
    await page.locator('#list .raw', { hasText: 'verification code' }).waitFor();
    assert.ok(await page.locator('[data-act="copy-ignored"]').isVisible());
    await page.getByRole('tab', { name: 'Tout' }).click();
    step('onglet Ignorées');

    // Statement reconciliation: one missing line is proposed and added.
    await page.locator('#addBtn').click();
    await page.locator('[data-mode="csv"]').click();
    const d = new Date();
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    await page.locator('#cText').fill(`${iso},BOULANGERIE GUILLAUME,12.34\n${iso},"GARAGE DUPUIS",88.80\n`);
    await page.locator('[data-sheet="csv-match"]').click();
    await page.locator('#cSummary', { hasText: '1 sur 2 déjà présents' }).waitFor();
    await page.locator('#cAdd').click();
    await page.locator('#toast', { hasText: 'ajoutées depuis le relevé' }).waitFor();
    await page.waitForFunction(() => window.__depenses.state.data.transactions.some((t) => t.merchant === 'GARAGE DUPUIS'));
    assert.equal(srv.backend.sheet('Transactions').objects().find((r) => r.merchant === 'GARAGE DUPUIS').source, 'statement');
    step('relevé CSV : la ligne manquante est ajoutée');

    // Settings: wrong token reported, shortcut link copyable, QR present, budget saved to the sheet.
    await page.locator('#settingsBtn').click();
    assert.ok(await page.locator('#sQr svg').count() === 1, 'code QR affiché');
    assert.equal(await page.locator('#sShortcut').inputValue(), `${srv.api}?token=${srv.capture}`);
    await page.locator('#sToken').fill('mauvais-jeton');
    await page.locator('[data-sheet="test"]').click();
    await page.locator('#sTest', { hasText: 'Non autorisé' }).waitFor();
    await page.locator('#sToken').fill(srv.admin);
    await page.locator('[data-sheet="test"]').click();
    await page.locator('#sTest', { hasText: 'Connecté' }).waitFor();
    await page.locator('#sBudget').fill('2000');
    await page.locator('[data-sheet="save"]').click();
    await page.waitForFunction(() => window.__depenses.state.data.settings.budget === 2000);
    assert.equal(srv.backend.props.get('BUDGET'), '2000');
    step('réglages : test de connexion, lien du raccourci, QR, budget dans la feuille');

    // Previous month navigation.
    await page.locator('#prevMonth').click();
    assert.notEqual(await page.locator('#monthLabel').textContent(), '');
    await page.locator('#nextMonth').click();
    assert.equal(await page.locator('#nextMonth').isDisabled(), true);
    if (shoot) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.screenshot({ path: path.join(SHOTS, 'live-light.png') });
    }
    await ctx.close();
  }

  console.log('misconfigured shortcut, pasted setup link, failed save, dark, offline');
  {
    const ctx = await browser.newContext({ ...phone, colorScheme: 'light' });
    const page = await ctx.newPage();
    watch(page, 'misconfigured', { networkErrorsExpected: true });
    srv.backend.post({ token: srv.capture, titre: 'Titre', soustitre: 'Sous-titre', corps: 'Corps' });
    await page.goto(srv.url);
    await page.getByRole('button', { name: 'Connecter ma feuille' }).click();
    await page.locator('#sUrl').fill(srv.setupLink);
    assert.equal(await page.locator('#sUrl').inputValue(), srv.api, 'le lien de configuration collé remplit les champs');
    assert.equal(await page.locator('#sToken').inputValue(), srv.admin);
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#foot', { hasText: 'Synchronisé' }).waitFor();
    await page.locator('.banner.alert', { hasText: 'pastille bleue' }).waitFor();
    assert.match(await page.locator('#checklist').textContent(), /Raccourci relié/);
    step('raccourci mal configuré → bannière rouge et explication');
    srv.backend.post({ token: srv.capture, title: 'InfoAlerte Scotia', body: 'Un achat de 9,99 $ a été effectué chez SAQ avec votre carte Visa se terminant par 1234.' });
    await page.locator('#syncBtn').click();
    await page.waitForFunction(() => !document.querySelector('.banner.alert'));
    step('une vraie notification efface l’alerte');

    // The sheet goes away: an edit is rolled back instead of pretending it was saved.
    const first = page.locator('#list .row:not(.muted)').first();
    const name = (await first.locator('.name').textContent()).replace(/À vérifier|Doublon \?|Non comptée|Gros achat/g, '').trim();
    await first.click();
    await page.locator('#fMerchant').fill('RENOMMÉ HORS LIGNE');
    await page.route('**/exec**', (route) => route.abort());
    await page.locator('[data-sheet="save"]').click();
    await page.locator('#toast', { hasText: 'Non enregistré' }).waitFor();
    assert.equal(await page.locator('#list .row', { hasText: 'RENOMMÉ HORS LIGNE' }).count(), 0, 'annulé');
    assert.ok(await page.locator('#list .row .name', { hasText: name }).count() > 0);
    step('enregistrement impossible → retour arrière');
    await ctx.close();

    const ctx2 = await browser.newContext({ ...phone, colorScheme: 'dark' });
    const page2 = await ctx2.newPage();
    watch(page2, 'dark');
    await page2.goto(srv.url);
    await page2.getByRole('button', { name: 'Voir avec des exemples' }).click();
    await page2.locator('.hero').waitFor();
    assert.equal(await page2.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(13, 13, 13)');
    if (shoot) await page2.screenshot({ path: path.join(SHOTS, 'dashboard-dark.png') });
    step('thème sombre');
    await ctx2.close();

    const ctx3 = await browser.newContext({ ...phone, colorScheme: 'light' });
    const cache = srv.backend.post({ token: srv.admin, action: 'list' });
    await ctx3.addInitScript(([api, token, cacheJson]) => {
      localStorage.setItem('depenses.settings.v3', JSON.stringify({ url: api + '-missing', token }));
      localStorage.setItem('depenses.cache.v3', cacheJson);
    }, [srv.api, srv.admin, JSON.stringify({ ...cache, savedAt: Date.now() - 600000 })]);
    const p3 = await ctx3.newPage();
    p3.on('pageerror', (e) => errors.push(`offline pageerror: ${e.message}`));
    await p3.goto(srv.url);
    await p3.locator('.banner', { hasText: 'Données d’il y a 10 min' }).waitFor();
    assert.ok(await p3.locator('#list .row').count() > 0, 'données en cache affichées');
    step('hors ligne : cache + bannière');
    await ctx3.close();
  }

  assert.deepEqual(errors, [], 'aucune erreur de page ni de console');
  console.log('e2e: all checks passed');
} catch (err) {
  console.error(err);
  if (errors.length) console.error('page errors:', errors);
  process.exitCode = 1;
} finally {
  await browser.close();
  srv.server.close();
}
