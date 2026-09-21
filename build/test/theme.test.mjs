/**
 * A themed page has none of the old colours in it.
 *
 * The theme is a translation table applied to the finished page. That only
 * works while the table knows every colour, and a layer written next month
 * will reach for gold by habit. So: in a page that says it is `night`, any
 * colour warmer than it is cool is either a warning, which is allowed by
 * name, or a colour the table has not been told about, which fails here.
 *
 *   node build/test/theme.test.mjs index.html dist/<build>.html [...]
 */
import { readFileSync } from 'fs';

// Warnings stay warm on purpose: against blue they warn better than ever.
const WARNINGS = new Set(['220,90,60', '#dc5a3c', '#ef8a7a', '#e8a0a0', '232,160,160',   // a zap, a fizzled trace, a failed save
  '#c8842f', '200,132,47',                                                                  // ink that strayed; the fizzle's embers
  '120,60,50', '200,90,70',                                                                 // the ward, fallen
  '#2a1614', '#6b3129']);                                                                  // the debug build's "fails here" button

let fail = 0, themed = 0;
for (const file of process.argv.slice(2)){
  const html = readFileSync(file, 'utf8').replace(/[A-Za-z0-9+/=]{400,}/g, '');
  const name = (html.match(/<meta name="hito-theme" content="([a-z]+)">/) || [])[1] || (file.endsWith('index.html') ? 'night' : 'gold');
  if (name !== 'night') continue;
  themed++;
  const warm = new Set();
  for (const m of html.matchAll(/#([0-9a-fA-F]{6})\b/g)){
    const h = m[1].toLowerCase(), r = parseInt(h.slice(0,2),16), b = parseInt(h.slice(4,6),16);
    if (r > b + 12 && !WARNINGS.has('#' + h)) warm.add('#' + h);
  }
  for (const m of html.matchAll(/rgba?\(\s*(\d{1,3}),\s?(\d{1,3}),\s?(\d{1,3})|'(\d{1,3}),(\d{1,3}),(\d{1,3})'/g)){
    const [r, g, b] = (m[1] !== undefined ? m.slice(1,4) : m.slice(4,7)).map(Number);
    if (r > b + 12 && !WARNINGS.has(`${r},${g},${b}`)) warm.add(`${r},${g},${b}`);
  }
  if (warm.size){ console.log(`  FAIL: ${file} is night but still has ${[...warm].join('  ')} — add it to build/theme.py`); fail++; }
}
if (fail) { console.log(`  ${fail} page(s) with untranslated colours`); process.exit(1); }
console.log(`  ${themed} night page(s), no warm colour left but the warnings`);
