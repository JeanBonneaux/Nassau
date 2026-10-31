// Local stand-in for the deployed web app: serves index.html and runs the real Spending.gs
// (through tools/gas-mock.mjs) at /exec. Data lives in memory and is lost on exit.
//   node tools/dev-server.mjs [--port 8787] [--empty]
// Then open http://localhost:8787/ and use the printed URL + token in Settings.
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadBackend } from './gas-mock.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

const SAMPLES = [
  { app: 'RBC', title: 'RBC', body: 'A purchase of $54.21 was made at METRO #123 with your RBC Visa card ending in 1234' },
  { app: 'Desjardins', title: 'Desjardins', body: 'Achat de 23,45 $ chez TIM HORTONS effectué avec votre carte Visa se terminant par 5678.' },
  { app: 'Wallet', title: 'Visa ••1234', subtitle: 'Starbucks', body: '$6.25' },
  { app: 'RBC', title: 'RBC', body: 'Purchase of $41.80 at SHELL. Available balance: $1,234.56' },
  { app: 'Amex', body: 'A charge of $129.99 at AMAZON.CA was approved on your Card ending in 12345.' },
  { app: 'RBC', title: 'RBC', body: 'A purchase of $18.50 was made at UBER *TRIP with your RBC Visa card ending in 1234' },
  { app: 'Desjardins', body: 'Achat de 67,10 $ chez IGA EXTRA effectué avec votre carte Visa se terminant par 5678.' },
  { app: 'Amex', body: 'Netflix: $16.99 charged to your card ending in 12345' }
];
const NOISE = [
  { app: 'RBC', body: 'Your verification code is 482913. Do not share it.' },
  { app: 'Amex', body: 'Earn $50 when you refer a friend – limited time offer!' },
  { app: 'RBC', body: 'Your balance is $2,318.40' }
];

// Push sample notifications through the real capture path, then spread them over past days.
function seed(backend, token) {
  const day = 86400000;
  let n = 0;
  for (let back = 40; back >= 0; back--) {
    const perDay = (back * 7) % 3;
    for (let i = 0; i < perDay; i++) {
      const s = SAMPLES[n++ % SAMPLES.length];
      const r = backend.post({ token, ...s, body: s.body.replace(/\d+[.,]\d\d/, (m) => (parseFloat(m.replace(',', '.')) + back % 7).toFixed(2).replace('.', m.includes(',') ? ',' : '.')) });
      if (r.tx) {
        const when = new Date(Date.now() - back * day);
        when.setHours(9 + i * 4, (back * 13) % 60, 0, 0);
        backend.post({ token, action: 'update', id: r.tx.id, fields: { date: when.toISOString() } });
      }
    }
  }
  NOISE.forEach((x) => backend.post({ token, ...x }));
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

export function startDevServer({ port = 8787, empty = false, currency = 'CAD' } = {}) {
  const backend = loadBackend();
  const { token } = backend.setup();
  backend.props.set('CURRENCY', currency);
  if (!empty) seed(backend, token);
  const server = http.createServer(async (req, res) => {
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
  return new Promise((resolve) => {
    server.listen(port, '127.0.0.1', () => {
      const p = server.address().port;
      resolve({ server, backend, token, url: `http://localhost:${p}/`, api: `http://localhost:${p}/exec` });
    });
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const arg = (name) => { const i = process.argv.indexOf(name); return i > 0 ? process.argv[i + 1] : undefined; };
  const s = await startDevServer({ port: Number(arg('--port') || 8787), empty: process.argv.includes('--empty') });
  console.log(`Dashboard:   ${s.url}\nWeb app URL: ${s.api}\nToken:       ${s.token}`);
}
