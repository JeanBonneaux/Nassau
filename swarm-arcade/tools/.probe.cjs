const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader','--use-angle=swiftshader','--ignore-gpu-blocklist'] });
  const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
  p.on('pageerror', e => console.log('ERR', e.message));
  await p.goto('file:///home/user/Nassau/swarm-arcade/demos/forces-silk-storm.html');
  await new Promise(r => setTimeout(r, 1000));
  const r = await p.evaluate(() => new Promise(res => { let n=0; const t0=performance.now(); (function f(){ n++; performance.now()-t0<3000?requestAnimationFrame(f):res(n/3); })(); }));
  console.log('fps', r);
  await b.close();
})();
