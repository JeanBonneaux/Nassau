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

if (exists('docs/GUIDE.fr.md')) {
  const script = read('apps-script/Spending.gs');
  write('guide.html', guideHtml(read('docs/GUIDE.fr.md'), script));
  write('Spending.txt', script);
}

// A small Markdown subset: headings, paragraphs, ordered/unordered lists, bold, italics, code, links, blockquotes, rules.
function guideHtml(md, script) {
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
    const h = /^(#{1,4})\s+(.*?)(?:\s+\{#([a-z0-9-]+)\})?$/.exec(line);
    const li = /^(\s*)([-*]|\d+[.)])\s+(.*)$/.exec(line);
    if (h) {
      flushPara(); closeList();
      if (h[1].length === 1 && title === 'Guide') title = h[2];
      out.push(`<h${h[1].length}${h[3] ? ` id="${h[3]}"` : ''}>${span(h[2])}</h${h[1].length}>`);
    } else if (li) {
      flushPara();
      const kind = /^\d/.test(li[2]) ? 'ol' : 'ul';
      if (list !== kind) {
        closeList(); list = kind;
        const start = kind === 'ol' ? parseInt(li[2], 10) : 1;
        out.push(start > 1 ? `<ol start="${start}">` : `<${kind}>`);
      }
      out.push(`<li>${span(li[3])}</li>`);
    } else if (/^\s*$/.test(line)) {
      flushPara(); closeList();
    } else if (line.trim() === '{{SCRIPT}}') {
      flushPara(); closeList();
      out.push('<div class="script"><button type="button" id="copyScript">Copier le script</button> <a href="Spending.txt" target="_blank" rel="noopener">ou l’ouvrir dans un onglet</a><span id="copied" hidden> Copié ✓</span>' +
        `<textarea id="scriptText" readonly aria-label="Script Apps Script">${esc(script || '')}</textarea></div>`);
    } else if (/^---+$/.test(line)) {
      flushPara(); closeList(); out.push('<hr>');
    } else if (/^\|/.test(line)) {
      flushPara(); closeList();
      const cells = line.split('|').slice(1, -1).map((c) => c.trim());
      if (cells.every((c) => /^-+$/.test(c))) continue;
      const tag = out[out.length - 1] && out[out.length - 1].startsWith('<table') ? 'td' : 'th';
      const rowHtml = `<tr>${cells.map((c) => `<${tag}>${span(c)}</${tag}>`).join('')}</tr>`;
      if (tag === 'th') out.push(`<table>${rowHtml}`); else out[out.length - 1] += rowHtml;
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
  for (let i = 0; i < out.length; i++) if (out[i].startsWith('<table')) out[i] += '</table>';
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
table { border-collapse: collapse; width: 100%; font-size: .95em; } th, td { text-align: left; padding: .4rem .5rem; border-bottom: 1px solid #c3c2b7; vertical-align: top; } th { color: #52514e; }
.script { margin: .6rem 0 1.2rem; } .script button { font: inherit; font-weight: 600; padding: .6rem 1rem; border: 0; border-radius: 10px; background: #2a78d6; color: #fff; cursor: pointer; } .script a { margin-left: .6rem; font-size: .95em; }
#scriptText { display: block; width: 100%; height: 6rem; margin-top: .6rem; font: 11px/1.3 ui-monospace, Menlo, monospace; color: #52514e; background: #e9e8e2; border: 1px solid #c3c2b7; border-radius: 8px; padding: .4rem; }
@media (prefers-color-scheme: dark) { #scriptText { background: #2c2c2a; color: #c3c2b7; } th, td { border-color: #383835; } th { color: #c3c2b7; } }
</style>
</head>
<body>
${out.join('\n')}
<script>
(function () {
  var b = document.getElementById('copyScript'), t = document.getElementById('scriptText'), ok = document.getElementById('copied');
  if (!b || !t) return;
  b.addEventListener('click', function () {
    var done = function () { ok.hidden = false; setTimeout(function () { ok.hidden = true; }, 4000); };
    var fallback = function () { t.focus(); t.select(); try { document.execCommand('copy'); done(); } catch (e) { alert('Sélectionnez le texte ci-dessous et copiez-le.'); } };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t.value).then(done, fallback); else fallback();
  });
})();
</script>
</body>
</html>
`;
}
