// Builds the generated files from their sources:
//   src/parser.js + src/insights.js + src/backend.gs -> apps-script/Spending.gs (the one file to paste into Apps Script)
//   src/dashboard.html + src/parser.js + src/insights.js + src/qr.js -> index.html (one self-contained file)
//   docs/GUIDE.fr.md -> guide.html (published next to the dashboard)
// Run: node tools/build.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const exists = (p) => fs.existsSync(path.join(ROOT, p));
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
const write = (p, s) => {
  fs.mkdirSync(path.dirname(path.join(ROOT, p)), { recursive: true });
  fs.writeFileSync(path.join(ROOT, p), s);
  console.log(`wrote ${p} (${(Buffer.byteLength(s) / 1024).toFixed(1)} KB)`);
};
const inline = (js) => js.replace(/<\/script/gi, '<\\/script');

const parser = read('src/parser.js');
const insights = exists('src/insights.js') ? read('src/insights.js') : '';
const qr = exists('src/qr.js') ? read('src/qr.js') : '';
const backend = read('src/backend.gs');
write('apps-script/Spending.gs',
  '// Dépenses : script Google Apps Script. Collez ce fichier entier dans Code.gs (à la place de son contenu).\n' +
  '// Généré par tools/build.mjs à partir de src/parser.js, src/insights.js et src/backend.gs : modifiez ceux-là, pas ce fichier.\n\n' +
  parser + '\n' + (insights ? insights + '\n' : '') + backend);

const html = read('src/dashboard.html');
for (const mark of ['/*__PARSER__*/', '/*__INSIGHTS__*/', '/*__QR__*/']) {
  if (!html.includes(mark)) throw new Error(`src/dashboard.html has no ${mark} placeholder`);
}
// Function replacements keep the "$" characters in the literals.
write('index.html', html
  .replace('/*__PARSER__*/', () => inline(parser))
  .replace('/*__INSIGHTS__*/', () => inline(insights))
  .replace('/*__QR__*/', () => inline(qr)));

if (exists('docs/GUIDE.fr.md')) write('guide.html', guideHtml(read('docs/GUIDE.fr.md')));

// A small Markdown subset: headings, paragraphs, ordered/unordered lists, bold, italics, code, links, blockquotes, rules.
function guideHtml(md) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const span = (s) => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2">$1</a>');
  const lines = md.split('\n');
  const out = [];
  let list = null; // 'ul' | 'ol'
  let para = [];
  const flushPara = () => { if (para.length) { out.push(`<p>${span(para.join(' '))}</p>`); para = []; } };
  const closeList = () => { if (list) { out.push(`</${list}>`); list = null; } };
  let title = 'Guide';
  for (const raw of lines) {
    const line = raw.replace(/\s+$/, '');
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    const li = /^(\s*)([-*]|\d+[.)])\s+(.*)$/.exec(line);
    if (h) {
      flushPara(); closeList();
      if (h[1].length === 1 && title === 'Guide') title = h[2];
      out.push(`<h${h[1].length}>${span(h[2])}</h${h[1].length}>`);
    } else if (li) {
      flushPara();
      const kind = /^\d/.test(li[2]) ? 'ol' : 'ul';
      if (list !== kind) { closeList(); list = kind; out.push(`<${kind}>`); }
      out.push(`<li>${span(li[3])}</li>`);
    } else if (/^\s*$/.test(line)) {
      flushPara(); closeList();
    } else if (/^---+$/.test(line)) {
      flushPara(); closeList(); out.push('<hr>');
    } else if (/^>\s?/.test(line)) {
      flushPara(); closeList(); out.push(`<blockquote>${span(line.replace(/^>\s?/, ''))}</blockquote>`);
    } else if (list && /^\s{2,}/.test(raw)) {
      // continuation of a list item
      out[out.length - 1] = out[out.length - 1].replace(/<\/li>$/, ` ${span(line.trim())}</li>`);
    } else {
      closeList();
      para.push(line);
    }
  }
  flushPara(); closeList();
  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<style>
:root { color-scheme: light dark; }
body { margin: 0 auto; max-width: 42rem; padding: 1.2rem 1rem 4rem; font: 16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; color: #0b0b0b; background: #f9f9f7; }
@media (prefers-color-scheme: dark) { body { color: #f0efec; background: #0d0d0d; } a { color: #86b6ef; } code { background: #2c2c2a; } blockquote { border-color: #383835; color: #c3c2b7; } }
h1 { font-size: 1.7rem; line-height: 1.2; } h2 { font-size: 1.3rem; margin-top: 2rem; } h3 { font-size: 1.1rem; margin-top: 1.6rem; }
li { margin: .45rem 0; } ol ol, ul ul { margin-top: .3rem; }
code { background: #e9e8e2; padding: .1em .35em; border-radius: 4px; font-size: .93em; }
a { color: #1c5cab; } blockquote { margin: 1rem 0; padding: .4rem .9rem; border-left: 3px solid #c3c2b7; color: #52514e; }
hr { border: 0; border-top: 1px solid #c3c2b7; margin: 2rem 0; }
</style>
</head>
<body>
${out.join('\n')}
</body>
</html>
`;
}
