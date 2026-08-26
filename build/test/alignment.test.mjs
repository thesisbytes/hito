/**
 * The stroke data, the rendered glyph and the practice grid all have to agree,
 * at every mastery level. They have silently disagreed twice: once when
 * KanjiVG coordinates were normalised to the canvas instead of the glyph box
 * (guide 1.44x too large), and once when the grid could have been pinned to
 * BASE_F instead of the shrinking curF.
 */
import { readFileSync } from 'fs';
const target = process.argv[2] || 'dist/hiragana-v0.1.8.html';
const s = readFileSync(target, 'utf8');

const book   = JSON.parse(s.match(/const DEFAULT_BOOK=(\{.*?\});\nlet TEACHER/s)[1]);
const BASE_F = parseFloat(s.match(/const BASE_F=([\d.]+);/)[1]);
const shrink = parseFloat(s.match(/Math\.pow\(([\d.]+),MASTERY/)[1]);
const floor  = parseFloat(s.match(/Math\.max\(([\d.]+),BASE_F\*Math\.pow/)[1]);
const cy     = book.alignment.glyphCy;
const letters = book.fonts[Object.keys(book.fonts)[0]].letters;
const pts = Object.values(letters).flatMap(r => r.strokes.flat());

let fail = 0, ratios = [];
for (const lv of [0,1,2,3,4,6,8,12,20]) {
  const curF = Math.max(floor, BASE_F * Math.pow(shrink, lv));
  const curS = curF / BASE_F;
  const cy0 = .5 + BASE_F*.06, cyN = .5 + curF*.06;
  // exactly the engine's curShrink
  const sx = pts.map(p => .5 + (p.x-.5)*curS);
  const sy = pts.map(p => cyN + (p.y-cy0)*curS);
  // exactly gridBox()
  const x0 = .5-curF/2, x1 = .5+curF/2;
  const y0 = .5-curF*cy, y1 = .5+curF*(1-cy);

  const inside = Math.min(...sx) >= x0-1e-9 && Math.max(...sx) <= x1+1e-9
              && Math.min(...sy) >= y0-1e-9 && Math.max(...sy) <= y1+1e-9;
  const margin = Math.min(Math.min(...sx)-x0, x1-Math.max(...sx),
                          Math.min(...sy)-y0, y1-Math.max(...sy));
  ratios.push(margin/curF);
  if (!inside) { console.log(`  FAIL lv ${lv}: strokes escape the grid box`); fail++; }
}

// the margin must scale with the glyph, not sit at a fixed canvas distance
const spread = Math.max(...ratios) - Math.min(...ratios);
if (spread > 1e-4) {
  console.log(`  FAIL: margin/glyph ratio drifts by ${spread.toFixed(5)} across levels`);
  console.log('        the grid is not tracking the glyph as it shrinks');
  fail++;
}

if (fail) process.exit(1);
console.log(`  grid frames the strokes at every mastery level `
  + `(margin ${(ratios[0]*100).toFixed(1)}% of glyph, constant)`);
