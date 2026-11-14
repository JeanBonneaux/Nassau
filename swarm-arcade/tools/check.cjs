#!/usr/bin/env node
// Smoke-test a demo page: console errors, animation, non-blank output, interaction, preview mode.
// Usage: node swarm-arcade/tools/check.cjs <file.html> [more.html ...]
// Screenshots land next to this script in tools/shots/<slug>-{a,b,preview}.png
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Only two checks run at once machine-wide: headless browsers starve each other on a small box
// and screenshots then time out. Extra callers queue here.
const LOCKS = [0, 1].map((i) => path.join(require('os').tmpdir(), 'swarm-arcade-check-' + i + '.lock'));
let held = null;
function release() { if (held) { try { fs.rmSync(held, { recursive: true, force: true }); } catch (e) {} held = null; } }
async function acquire() {
  for (;;) {
    for (const l of LOCKS) {
      try { fs.mkdirSync(l); fs.writeFileSync(path.join(l, 'pid'), String(process.pid)); held = l; return; }
      catch (e) {
        try {
          const pid = Number(fs.readFileSync(path.join(l, 'pid'), 'utf8'));
          try { process.kill(pid, 0); } catch (dead) { fs.rmSync(l, { recursive: true, force: true }); }
        } catch (e2) { try { if (Date.now() - fs.statSync(l).mtimeMs > 5000) fs.rmSync(l, { recursive: true, force: true }); } catch (e3) {} }
      }
    }
    await sleep(400 + Math.random() * 400);
  }
}
process.on('exit', release);
for (const sig of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(sig, () => { release(); process.exit(130); });

async function stats(browser, png) {
  const p = await browser.newPage();
  const res = await p.evaluate(async (b64) => {
    const img = new Image();
    img.src = 'data:image/png;base64,' + b64;
    await img.decode();
    const c = document.createElement('canvas');
    c.width = 160; c.height = 90;
    const g = c.getContext('2d');
    g.drawImage(img, 0, 0, 160, 90);
    const d = g.getImageData(0, 0, 160, 90).data;
    const seen = new Set(); let lit = 0;
    for (let i = 0; i < d.length; i += 4) {
      seen.add((d[i] >> 3) << 10 | (d[i + 1] >> 3) << 5 | (d[i + 2] >> 3));
      if (d[i] + d[i + 1] + d[i + 2] > 60) lit++;
    }
    return { colors: seen.size, litPct: Math.round((lit / (d.length / 4)) * 100) };
  }, png.toString('base64'));
  await p.close();
  return res;
}

async function checkOne(browser, file) {
  const abs = path.resolve(file);
  const slug = path.basename(abs, '.html');
  const shots = path.join(__dirname, 'shots');
  fs.mkdirSync(shots, { recursive: true });
  const out = { slug, file, errors: [], externalRequests: [] };
  if (!fs.existsSync(abs)) { out.errors.push('FILE MISSING'); out.pass = false; return out; }

  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 } });
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error') out.errors.push('console: ' + m.text().slice(0, 300)); });
  page.on('pageerror', (e) => out.errors.push('pageerror: ' + String(e.message).slice(0, 300)));
  page.on('request', (r) => { const u = r.url(); if (!u.startsWith('file:') && !u.startsWith('data:') && !u.startsWith('blob:')) out.externalRequests.push(u.slice(0, 120)); });

  await page.goto('file://' + abs);
  await sleep(1200);
  const a = await page.screenshot();
  await sleep(900);
  const b = await page.screenshot();
  fs.writeFileSync(path.join(shots, slug + '-a.png'), a);
  out.animatesIdle = !a.equals(b);
  out.idle = await stats(browser, b);
  out.fps = await page.evaluate(() => new Promise((res) => {
    let n = 0; const t0 = performance.now();
    (function f() { n++; performance.now() - t0 < 1000 ? requestAnimationFrame(f) : res(n); })();
  }));

  // interaction: pointer sweep, drag, click, a few keys
  await page.mouse.move(200, 200);
  for (let i = 0; i <= 20; i++) await page.mouse.move(200 + i * 40, 200 + Math.sin(i / 3) * 150 + 100);
  await page.mouse.down(); for (let i = 0; i <= 12; i++) await page.mouse.move(1000 - i * 50, 500 - i * 20); await page.mouse.up();
  await page.mouse.click(640, 360);
  for (const k of ['Space', 'ArrowLeft', 'ArrowRight', 'KeyR', 'Digit1']) await page.keyboard.press(k);
  await sleep(600);
  const c = await page.screenshot();
  fs.writeFileSync(path.join(shots, slug + '-b.png'), c);
  out.afterInteraction = await stats(browser, c);
  await ctx.close();

  // preview mode: small iframe-sized viewport with #preview hash
  const pctx = await browser.newContext({ viewport: { width: 420, height: 260 } });
  const pp = await pctx.newPage();
  pp.on('pageerror', (e) => out.errors.push('preview pageerror: ' + String(e.message).slice(0, 300)));
  await pp.goto('file://' + abs + '#preview');
  await sleep(1200);
  const p1 = await pp.screenshot(); await sleep(600); const p2 = await pp.screenshot();
  fs.writeFileSync(path.join(shots, slug + '-preview.png'), p2);
  out.previewAnimates = !p1.equals(p2);
  out.preview = await stats(browser, p2);
  await pctx.close();

  out.sizeKB = Math.round(fs.statSync(abs).size / 1024);
  const problems = [];
  if (out.errors.length) problems.push('JS errors');
  if (out.externalRequests.length) problems.push('external network requests');
  if (!out.animatesIdle) problems.push('static when idle (no attract mode)');
  if (out.idle.colors < 6 || out.idle.litPct < 2) problems.push('nearly blank when idle');
  if (!out.previewAnimates || out.preview.litPct < 2) problems.push('preview mode static or blank');
  if (out.fps < 20) problems.push('very low fps in headless (' + out.fps + ') - likely too heavy');
  out.problems = problems;
  out.pass = problems.length === 0;
  out.screenshots = ['a', 'b', 'preview'].map((s) => path.join(shots, `${slug}-${s}.png`));
  return out;
}

(async () => {
  const files = process.argv.slice(2);
  if (!files.length) { console.error('usage: check.cjs <file.html> ...'); process.exit(2); }
  await acquire();
  const browser = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  const results = [];
  for (const f of files) {
    try { results.push(await checkOne(browser, f)); }
    catch (e) { results.push({ file: f, pass: false, problems: ['checker crashed: ' + e.message] }); }
  }
  await browser.close();
  console.log(JSON.stringify(results, null, 2));
  process.exit(results.every((r) => r.pass) ? 0 : 1);
})();
