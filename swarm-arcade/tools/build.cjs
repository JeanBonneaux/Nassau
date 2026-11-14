#!/usr/bin/env node
// Inject tools/manifest.json into index.html (between the /*NAME*/ markers).
const fs = require('fs'), path = require('path');
const root = path.join(__dirname, '..');
const m = JSON.parse(fs.readFileSync(path.join(__dirname, 'manifest.json'), 'utf8'));
let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const put = (name, value) => {
  const re = new RegExp('(const ' + name + ' = /\\*' + name + '\\*/)[^\\n]*;');
  if (!re.test(html)) throw new Error('marker not found: ' + name);
  html = html.replace(re, (_, head) => head + JSON.stringify(value).replace(/</g, '\\u003c') + ';');
};
put('SQUADS', m.squads); put('DEMOS', m.demos); put('STEPS', m.steps); put('FINE', m.fine);
fs.writeFileSync(path.join(root, 'index.html'), html);
console.log('index.html updated:', m.demos.length, 'demos');
