const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch({ args: ['--enable-unsafe-swiftshader','--use-angle=swiftshader','--ignore-gpu-blocklist'] });
  for (const f of ['/tmp/claude-0/-home-user-Nassau/c604a3c3-17a0-518a-be45-954da663a678/scratchpad/nodust.html', 'swarm-arcade/demos/forces-gravity-garden.html']) {
    const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
    await p.goto('file://' + (f.startsWith('/') ? f : '/home/user/Nassau/' + f));
    await new Promise(r => setTimeout(r, 1200));
    const t2 = Date.now(); await p.screenshot({ timeout: 60000 }); console.log(f, 'shot ms', Date.now()-t2);
    await p.close();
  }
  await b.close();
})().catch(e => { console.log('ERR', e.message.slice(0,300)); process.exit(1); });
