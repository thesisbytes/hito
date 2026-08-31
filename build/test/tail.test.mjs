/**
 * How much of a stroke can be left undrawn and still count as finished?
 *
 * Hooks are the tail of a stroke, and forgiving them is the exact failure this
 * pack uses KanjiVG rather than a font to avoid. v0.1.9 added a distance test
 * because a fixed index count of 4 points forgave more of a short stroke than
 * of a long one — but the distance was itself a fixed radius, which has the
 * same shape of bug one level up: the same pixels on a 300px stroke and on a
 * 21px one. It was measured at full size only, and at the 0.32 floor it had
 * grown to swallow a third of the short strokes.
 *
 * The number that matters is therefore not "how many pixels" but "what
 * fraction of this stroke", held steady across every size. That is what is
 * checked here.
 *
 *   node build/test/tail.test.mjs dist/hiragana-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const s = readFileSync(target, 'utf8');
const num = (re, d) => { const m = s.match(re); return m ? parseFloat(m[1]) : d; };

const book    = JSON.parse(s.match(/const DEFAULT_BOOK=(\{.*?\});\nlet TEACHER/s)[1]);
const letters = book.fonts[Object.keys(book.fonts)[0]].letters;
const BASE_F  = num(/const BASE_F=([\d.]+);/);
const FLOOR   = num(/Math\.max\(([\d.]+),BASE_F\*Math\.pow/);
const R_ON0   = num(/const R_ON0=([\d.]+)/);
const MIN_TOL = num(/const R_ON=\(\)=>Math\.max\(([\d.]+)/);
const SLACK   = num(/END_SLACK=(\d+)/, 4);
const TAIL    = num(/TAIL_FRAC=([\d.]+)/, null);
const END_MIN = num(/END_MIN=([\d.]+)/, null);
const LOOK    = num(/LOOK=(\d+)/, 24);
const SPACING = 0.008, CANVAS = 353;

// A build from before the fix has no TAIL_FRAC: its endpoint tolerance is the
// flat R_ON() and its slack a flat index count. Model that rather than bailing,
// so the same measurement runs on both and the regression is a number.
const FLAT = (TAIL === null || END_MIN === null);
if (FLAT) console.log('  (pre-fix build: flat endpoint radius, measured for comparison)');

// MUST_DRAW is the floor on how much of any stroke has to be traced. DRIFT is
// how much that fraction may move between the largest and smallest glyph — the
// whole point is that it should barely move at all.
const MUST_DRAW = 0.80, DRIFT = 0.10;

function geom(ch, curF){
  const curS = curF/BASE_F, cy0 = .5+BASE_F*.06, cyN = .5+curF*.06;
  const sh = q => ({x:.5+(q.x-.5)*curS, y:cyN+(q.y-cy0)*curS});
  const rs = (a,n) => { if (a.length<2) return Array(n).fill(a[0]);
    const d=[0]; for(let i=1;i<a.length;i++) d.push(d[i-1]+Math.hypot(a[i].x-a[i-1].x,a[i].y-a[i-1].y));
    const L=d[d.length-1]; if(!L) return Array(n).fill(a[0]);
    const o=[]; let j=0;
    for(let k=0;k<n;k++){ const t=L*k/(n-1); while(j<a.length-2&&d[j+1]<t) j++;
      const g=d[j+1]-d[j]||1, f=(t-d[j])/g;
      o.push({x:a[j].x+(a[j+1].x-a[j].x)*f, y:a[j].y+(a[j+1].y-a[j].y)*f}); }
    o.len=L; return o; };
  const PATH=[], SEGS=[];
  for (const st of letters[ch].strokes){ const sc=st.map(sh), a=PATH.length;
    PATH.push(...rs(sc, Math.max(6, Math.round((rs(sc,32).len||.05)/SPACING))));
    SEGS.push([a, PATH.length-1]); }
  const SEGLEN = SEGS.map(g => { let L=0;
    for(let i=g[0];i<g[1];i++) L+=Math.hypot(PATH[i+1].x-PATH[i].x, PATH[i+1].y-PATH[i].y); return L; });
  const R = Math.max(MIN_TOL, R_ON0*Math.sqrt(curS));
  return { PATH, SEGS, SEGLEN, R,
    endTol: FLAT ? () => R : i => Math.max(END_MIN, Math.min(R, TAIL*SEGLEN[i])),
    slack:  FLAT ? SEGS.map(() => SLACK)
                 : SEGS.map(g => Math.max(1, Math.min(SLACK, Math.round(TAIL*(g[1]-g[0]))))) };
}

// Trace the stroke along its own centreline — the most generous case there is —
// and report the fraction drawn at the moment the engine calls it finished.
function drawnAtCompletion(ch, curF, si){
  const G = geom(ch, curF), seg = G.SEGS[si];
  let prog = seg[0], arc = 0;
  for (let p=seg[0]; p<=seg[1]; p++){
    if (p>seg[0]) arc += Math.hypot(G.PATH[p].x-G.PATH[p-1].x, G.PATH[p].y-G.PATH[p-1].y);
    let best=-1, bd=G.R;
    const lo=Math.max(prog,seg[0]), hi=Math.min(seg[1], prog+LOOK);
    for (let i=lo;i<=hi;i++){
      const d=Math.hypot(G.PATH[p].x-G.PATH[i].x, G.PATH[p].y-G.PATH[i].y); if(d<bd){bd=d;best=i;} }
    if (best>=0){ prog=Math.max(prog,best);
      if (prog>=seg[1]-G.slack[si]
        && Math.hypot(G.PATH[p].x-G.PATH[seg[1]].x, G.PATH[p].y-G.PATH[seg[1]].y) < G.endTol(si))
        return arc/G.SEGLEN[si]; }
  }
  return 1;
}

const SIZES = [BASE_F, (BASE_F+FLOOR)/2, FLOOR];
const CHARS = Object.keys(letters);
let fail = 0, worst = {v:2}, drifts = [];

for (const ch of CHARS){
  const n = letters[ch].strokes.length;
  for (let si=0; si<n; si++){
    const at = SIZES.map(f => drawnAtCompletion(ch, f, si));
    const lo = Math.min(...at);
    if (lo < worst.v) worst = {v:lo, ch, si, f:SIZES[at.indexOf(lo)]};
    if (lo < MUST_DRAW){
      if (fail < 8) console.log(`  FAIL: ${ch} stroke ${si+1} counts as finished at `
        + `${(lo*100).toFixed(0)}% drawn (floor is ${MUST_DRAW*100}%)`);
      fail++;
    }
    const drift = Math.max(...at) - lo;
    drifts.push({drift, ch, si});
    if (drift > DRIFT){
      if (fail < 8) console.log(`  FAIL: ${ch} stroke ${si+1} drifts ${(drift*100).toFixed(0)}% `
        + `across sizes — endpoint forgiveness is still tracking the canvas, not the stroke`);
      fail++;
    }
  }
}

const maxDrift = drifts.reduce((a,b) => b.drift>a.drift?b:a);
if (fail){
  console.log(`  ${fail} stroke(s) forgive too much of their tail`);
  process.exit(1);
}
console.log(`  every stroke needs >=${(worst.v*100).toFixed(0)}% drawn at every size `
  + `(worst ${worst.ch} stroke ${worst.si+1} at ${worst.f.toFixed(2)}); `
  + `size drift <=${(maxDrift.drift*100).toFixed(0)}%`);
