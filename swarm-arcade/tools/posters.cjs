#!/usr/bin/env node
// Capture a poster (preview-mode still) for every demo into swarm-arcade/posters/<slug>.jpg
// Usage: node swarm-arcade/tools/posters.cjs [slug ...]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
(async () => {
  const root = path.join(__dirname, '..');
  const out = path.join(root, 'posters');
  fs.mkdirSync(out, { recursive: true });
  let slugs = process.argv.slice(2);
  if (!slugs.length) slugs = fs.readdirSync(path.join(root, 'demos')).filter((f) => f.endsWith('.html')).map((f) => f.slice(0, -5));
  const browser = await chromium.launch({ args: ['--disable-accelerated-2d-canvas', '--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  for (const slug of slugs) {
    const page = await browser.newPage({ viewport: { width: 840, height: 525 } });
    await page.goto('file://' + path.join(root, 'demos', slug + '.html') + '#preview');
    await page.waitForTimeout(4500);
    await page.screenshot({ path: path.join(out, slug + '.jpg'), type: 'jpeg', quality: 76 });
    await page.close();
    console.log(slug, Math.round(fs.statSync(path.join(out, slug + '.jpg')).size / 1024) + 'KB');
  }
  await browser.close();
})();
