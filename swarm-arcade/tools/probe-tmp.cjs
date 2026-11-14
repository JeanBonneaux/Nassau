const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader', '--use-angle=swiftshader', '--ignore-gpu-blocklist'] });
  for (const f of process.argv.slice(2)) {
    const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
    await p.goto('file://' + f);
    await new Promise(r => setTimeout(r, 1000));
    const fps = await p.evaluate(() => new Promise(res => { let n=0; const t0=performance.now(); (function f(){ n++; performance.now()-t0<2000?requestAnimationFrame(f):res(n); })(); }));
    const t0 = Date.now();
    await p.screenshot({ path: f + '.png', timeout: 90000 });
    console.log(f.split('/').pop(), 'fps', fps, 'shot ms', Date.now() - t0);
    await p.close();
  }
  await b.close();
})().catch(e => { console.log('FAIL', e.message.slice(0,200)); process.exit(1); });
