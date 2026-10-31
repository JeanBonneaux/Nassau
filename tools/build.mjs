// Builds the generated files from their sources:
//   src/parser.js                      -> apps-script/Parser.gs
//   src/dashboard.html + src/parser.js -> index.html (one self-contained file)
// Run: node tools/build.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const read = (p) => fs.readFileSync(path.join(ROOT, p), 'utf8');
const write = (p, s) => {
  fs.writeFileSync(path.join(ROOT, p), s);
  console.log(`wrote ${p} (${(Buffer.byteLength(s) / 1024).toFixed(1)} KB)`);
};

const parser = read('src/parser.js');
write('apps-script/Parser.gs', '// Generated from src/parser.js by tools/build.mjs. Edit that file, not this one.\n' + parser);

const MARK = '/*__PARSER__*/';
if (fs.existsSync(path.join(ROOT, 'src/dashboard.html'))) {
  const html = read('src/dashboard.html');
  if (!html.includes(MARK)) throw new Error(`src/dashboard.html has no ${MARK} placeholder`);
  // A function replacement keeps the "$" characters in the parser literal.
  write('index.html', html.replace(MARK, () => parser.replace(/<\/script/gi, '<\\/script')));
}
