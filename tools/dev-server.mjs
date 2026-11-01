// Local stand-in for the deployed web app: serves index.html and runs the real Spending.gs
// (through tools/gas-mock.mjs) at /exec. Data lives in memory and is lost on exit.
//   node tools/dev-server.mjs [--port 8787] [--empty]
// Then open http://localhost:8787/ and paste the printed setup link in Réglages.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadBackend } from './gas-mock.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const SAMPLES = [
  { title: 'InfoAlerte Scotia', body: 'Un achat de 54,21 $ a été effectué chez IGA EXTRA avec votre carte Visa se terminant par 1234.' },
  { title: 'Capital One', body: 'A purchase of $23.45 at TIM HORTONS was approved on your card ending in 5678.' },
  { title: 'Visa Scotia', subtitle: 'Café Olimpico', body: '6,25 $' },
  { title: 'InfoAlerte Scotia', body: 'Un achat de 41,80 $ a été effectué chez PETRO-CANADA avec votre carte Visa se terminant par 1234.' },
  { title: 'Capital One', body: 'A purchase of $129.99 at AMAZON.CA was approved on your card ending in 5678.' },
  { title: 'Wealthsimple', body: 'Vous avez dépensé 18,50 $ chez Uber' },
  { title: 'InfoAlerte Scotia', body: 'Un achat de 67,10 $ a été effectué chez METRO PLUS avec votre carte de débit se terminant par 1234.' },
  { title: 'Capital One', body: 'A purchase of $16.99 at NETFLIX.COM was approved on your card ending in 5678.' }
];
const NOISE = [
  { title: 'Capital One', body: 'Your verification code is 482913. Do not share it.' },
  { title: 'Wealthsimple', body: 'Gagnez 50 $ en parrainant un ami – offre à durée limitée !' },
  { title: 'InfoAlerte Scotia', body: 'Le solde de votre compte se terminant par 1234 est inférieur à 100,00 $.' }
];

// Push sample notifications through the real capture path, spread over past days (the clock is moved for each one).
function seed(backend, capture, admin) {
  const day = 86400000;
  let n = 0;
  for (let back = 40; back >= 0; back--) {
    const perDay = (back * 7) % 3;
    for (let i = 0; i < perDay; i++) {
      const s = SAMPLES[n++ % SAMPLES.length];
      const when = new Date(Date.now() - back * day);
      when.setHours(9 + i * 4, (back * 13) % 60, 0, 0);
      backend.setNow(when);
      const bump = (m) => (parseFloat(m.replace(',', '.')) + back % 7).toFixed(2).replace('.', m.includes(',') ? ',' : '.');
      backend.post({ token: capture, ...s, body: s.body.replace(/\d+[.,]\d\d/, bump) });
    }
  }
  backend.setNow(null);
  NOISE.forEach((x) => backend.post({ token: capture, ...x }));
  backend.post({ token: admin, action: 'settings', budget: 1500 });
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.setEncoding('utf8');
    req.on('data', (c) => { data += c; });
    req.on('end', () => resolve(data));
    req.on('error', reject);
  });
}

export function startDevServer({ port = 8787, empty = false } = {}) {
  return new Promise((resolve) => {
    const server = http.createServer();
    server.listen(port, '127.0.0.1', () => {
      const p = server.address().port;
      const api = `http://localhost:${p}/exec`;
      const backend = loadBackend({ webAppUrl: api });
      const info = backend.setup();
      if (!empty) seed(backend, info.captureToken, info.adminToken);
      server.on('request', async (req, res) => {
        const url = new URL(req.url, 'http://localhost');
        try {
          if (url.pathname === '/exec') {
            // Like Apps Script: any origin may read the answer, and preflight requests are not supported.
            const headers = { 'Access-Control-Allow-Origin': '*', 'Content-Type': 'application/json; charset=utf-8' };
            if (req.method === 'OPTIONS') { res.writeHead(405); res.end(); return; }
            const parameter = Object.fromEntries(url.searchParams);
            const out = req.method === 'GET'
              ? backend.doGet({ parameter })
              : backend.doPost({ postData: { contents: await readBody(req), type: req.headers['content-type'] || '' }, parameter });
            res.writeHead(200, headers);
            res.end(out.getContent());
            return;
          }
          if (url.pathname === '/' || url.pathname === '/index.html') {
            res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' });
            res.end(fs.readFileSync(path.join(ROOT, 'index.html')));
            return;
          }
          res.writeHead(404);
          res.end('not found');
        } catch (err) {
          res.writeHead(500);
          res.end(String(err && err.stack || err));
        }
      });
      const setupLink = `http://localhost:${p}/#setup=` + Buffer.from(JSON.stringify({ u: api, k: info.adminToken, c: 'CAD' })).toString('base64url');
      resolve({ server, backend, admin: info.adminToken, capture: info.captureToken, url: `http://localhost:${p}/`, api, setupLink });
    });
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const arg = (name) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : undefined; };
  const s = await startDevServer({ port: Number(arg('--port') || 8787), empty: process.argv.includes('--empty') });
  console.log(`Tableau de bord : ${s.url}\nLien de configuration : ${s.setupLink}\nAdresse du script : ${s.api}\nJeton admin : ${s.admin}\nJeton capture : ${s.capture}`);
}
