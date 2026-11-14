const { chromium } = require('playwright');
const f = process.argv[2];
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader','--use-angle=swiftshader','--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  await p.goto('file://' + f);
  await new Promise(r => setTimeout(r, 1200));
  const t0 = Date.now();
  await p.screenshot({ timeout: 25000 });
  console.log('shot ok in', Date.now() - t0, 'ms');
  await b.close();
  process.exit(0);
})().catch(e => { console.error('ERR', e.message.slice(0,200)); process.exit(1); });
