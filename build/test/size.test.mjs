/**
 * Does an honest trace pass at every glyph size?
 *
 * The difficulty curve shrinks the glyph, and three separate simulations have
 * said every level is passable while the hand said level 6 was not. Each of
 * those simulations built its pen path by scaling the ideal path, so the
 * simulated hand shrank along with the target: its wobble stayed the same
 * *fraction* of the stroke at every size, and travel/PATHLEN came out constant
 * by construction. That is not a hand.
 *
 * Two things do not shrink when the glyph does:
 *
 *   - how far apart the digitizer samples the pen (a screen-space distance)
 *   - how far the hand strays from the line (a screen-space distance)
 *
 * Both are held constant here, in pixels, and converted into normalised units
 * per size. That single change is the difference between a model that always
 * agrees with the scorer and one that can disagree with it.
 *
 * This is still a model, and the log's standing lesson is that the hand
 * outranks it. It is here to catch sizes that are impossible in principle —
 * where no trace of any accuracy can satisfy the scoring — not to certify
 * that a size is comfortable.
 *
 *   node build/test/size.test.mjs [build.html] [--wobble=6] [--canvas=360]
 */
import { readFileSync } from 'fs';

const args   = process.argv.slice(2);
const target = args.find(a => !a.startsWith('--'))
            || 'dist/' + (readFileSync('scripts/hiragana/pack.json','utf8')
                 .match(/"version":\s*"([^"]+)"/)[1]
                 .replace(/^/, 'hiragana-v')) + '.html';
const opt = k => { const a = args.find(x => x.startsWith(`--${k}=`));
                   return a ? parseFloat(a.split('=')[1]) : null; };
const BRIEF = args.includes('--brief');     // the suite wants the verdict, not the table

const s = readFileSync(target, 'utf8');
const num = (re, dflt) => { const m = s.match(re); return m ? parseFloat(m[1]) : dflt; };

const book    = JSON.parse(s.match(/const DEFAULT_BOOK=(\{.*?\});\nlet TEACHER/s)[1]);
const letters = book.fonts[Object.keys(book.fonts)[0]].letters;
const BASE_F  = num(/const BASE_F=([\d.]+);/);
const SHRINK  = num(/Math\.pow\(([\d.]+),MASTERY/);
const FLOOR   = num(/Math\.max\(([\d.]+),BASE_F\*Math\.pow/);
const R_ON0   = num(/(?:const|let) R_ON0=([\d.]+)/);
const MIN_TOL = num(/const R_ON=\(\)=>Math\.max\(([\d.]+)/);
const SQRT_TOL= /R_ON0\*Math\.sqrt\(curS\)/.test(s);
const COVER   = num(/COVER_MIN=([\d.]+)/, 0.85);
const SLACK   = num(/END_SLACK=(\d+)/, 4);
const MAXTRAV = num(/MAX_TRAVEL=([\d.]+)/, 2.5);
const TRAV_EPS= num(/TRAVEL_EPS=([\d.]+)/, 0.006);
const LOOK    = num(/LOOK=(\d+)/, 24);
const SPACING = 0.008;                    // load()'s resample spacing

const CANVAS  = opt('canvas') || 360;     // px; the reference in NOTES
const WOBBLE  = opt('wobble') ?? 6;       // px of hand stray, at the gate
const SAMPLE  = 2.5;                      // px between pointermove samples

// ---------- helpers lifted from the engine, unchanged -----------------------
function resample(st, n){
  if (st.length < 2) return Array(n).fill(st[0]);
  const d=[0];
  for (let i=1;i<st.length;i++) d.push(d[i-1]+Math.hypot(st[i].x-st[i-1].x, st[i].y-st[i-1].y));
  const L=d[d.length-1]; if(!L) return Array(n).fill(st[0]);
  const out=[]; let j=0;
  for (let k=0;k<n;k++){ const tgt=L*k/(n-1); while(j<st.length-2 && d[j+1]<tgt) j++;
    const seg=d[j+1]-d[j]||1, f=(tgt-d[j])/seg;
    out.push({x:st[j].x+(st[j+1].x-st[j].x)*f, y:st[j].y+(st[j+1].y-st[j].y)*f}); }
  out.len=L; return out;
}

// exactly load(): scale the recording to curF, then resample at SPACING
function buildPath(ch, curF){
  const curS=curF/BASE_F, cy0=.5+BASE_F*.06, cyN=.5+curF*.06;
  const shrink = q => ({x:.5+(q.x-.5)*curS, y:cyN+(q.y-cy0)*curS});
  const PATH=[], SEGS=[];
  for (const st of letters[ch].strokes){
    const sc=st.map(shrink), a=PATH.length;
    const R=resample(sc, Math.max(6, Math.round((resample(sc,32).len||.05)/SPACING)));
    PATH.push(...R); SEGS.push([a, PATH.length-1]);
  }
  let PATHLEN=0;
  for (const g of SEGS) for (let i=g[0];i<g[1];i++)
    PATHLEN += Math.hypot(PATH[i+1].x-PATH[i].x, PATH[i+1].y-PATH[i].y);
  return {PATH, SEGS, PATHLEN, R_ON: Math.max(MIN_TOL, R_ON0*(SQRT_TOL?Math.sqrt(curS):curS))};
}

const mulberry32 = a => () => {
  a|=0; a=a+0x6D2B79F5|0;
  let t=Math.imul(a^a>>>15, 1|a); t=t+Math.imul(t^t>>>7, 61|t)^t;
  return ((t^t>>>14)>>>0)/4294967296;
};

/**
 * A hand tracing the path on screen.
 *
 * Sample spacing and wobble amplitude are given in pixels and converted once,
 * so they stay the same physical size no matter how small the glyph is drawn.
 * The wobble is smooth and correlated along the stroke — per-sample white
 * noise is not what a hand does, and summing it would inflate travel until an
 * honest trace failed. That mistake has already been made once here.
 */
function handTrace(PATH, SEGS, wobblePx, rnd){
  const amp = wobblePx/CANVAS, step = SAMPLE/CANVAS;
  const pen = [];
  for (const [a,b] of SEGS){
    const ph = [rnd()*6.28, rnd()*6.28, rnd()*6.28];
    // wavelengths in screen space: a hand wobbles at a physical frequency
    const wl = [55/CANVAS, 23/CANVAS, 11/CANVAS], wt = [0.6, 0.3, 0.1];
    const line = PATH.slice(a, b+1);
    let arc = 0, out = [];
    for (let i=0;i<line.length;i++){
      if (i) arc += Math.hypot(line[i].x-line[i-1].x, line[i].y-line[i-1].y);
      const p = line[i], q = line[Math.min(i+1,line.length-1)], r = line[Math.max(i-1,0)];
      let nx=-(q.y-r.y), ny=(q.x-r.x); const m=Math.hypot(nx,ny)||1; nx/=m; ny/=m;
      let w=0; for (let k=0;k<3;k++) w += wt[k]*Math.sin(ph[k] + arc*2*Math.PI/wl[k]);
      out.push({x:p.x+nx*amp*w, y:p.y+ny*amp*w});
    }
    // re-sample the drawn line at the digitizer's fixed screen-space rate
    let L=0; for (let i=1;i<out.length;i++) L+=Math.hypot(out[i].x-out[i-1].x,out[i].y-out[i-1].y);
    pen.push(resample(out, Math.max(2, Math.round(L/step))));
  }
  return pen;
}

// ---------- the shipped scoring, ported ------------------------------------
function score(ch, curF, wobblePx, seed){
  const {PATH,SEGS,PATHLEN,R_ON} = buildPath(ch, curF);
  const pen = handTrace(PATH, SEGS, wobblePx, mulberry32(seed));
  const hit = new Uint8Array(PATH.length);
  const cov = () => { let c=0; for (let i=0;i<hit.length;i++) c+=hit[i]; return c/hit.length; };
  let prog=0, segIdx=0, awaitLift=false, travel=0, lastN=null;

  for (const stroke of pen){
    if (awaitLift && segIdx < SEGS.length-1){          // pen down advances
      segIdx++; prog=SEGS[segIdx][0]; awaitLift=false; }
    lastN=null;
    for (const n of stroke){
      const seg=SEGS[segIdx]; if(!seg) break;
      if(!lastN) lastN={x:n.x,y:n.y};
      else { const st=Math.hypot(n.x-lastN.x,n.y-lastN.y);
             if (st>=TRAV_EPS){ travel+=st; lastN={x:n.x,y:n.y}; } }
      if (awaitLift){
        const e=PATH[seg[1]];
        if (Math.hypot(n.x-e.x,n.y-e.y) < R_ON*1.6) continue;
        continue; }
      for (let i=seg[0];i<=seg[1];i++)
        if (Math.hypot(n.x-PATH[i].x,n.y-PATH[i].y) < R_ON) hit[i]=1;
      let best=-1, bd=R_ON;
      const lo=Math.max(prog,seg[0]), hi=Math.min(seg[1],prog+LOOK);
      for (let i=lo;i<=hi;i++){
        const d=Math.hypot(n.x-PATH[i].x,n.y-PATH[i].y); if(d<bd){bd=d;best=i;} }
      if (best>=0){
        prog=Math.max(prog,best);
        if (prog>=seg[1]-SLACK && Math.hypot(n.x-PATH[seg[1]].x,n.y-PATH[seg[1]].y)<R_ON){
          prog=seg[1];
          if (segIdx>=SEGS.length-1){
            const c=cov(), eff=PATHLEN?travel/PATHLEN:1;
            return {ok: c>=COVER && eff<=MAXTRAV, cover:c, eff,
                    why: c<COVER ? `missed ${Math.round((1-c)*100)}%` :
                         eff>MAXTRAV ? `travel ${eff.toFixed(1)}x` : ''};
          }
          awaitLift=true;
        }
      }
    }
  }
  const c=cov(), eff=PATHLEN?travel/PATHLEN:0;
  return {ok:false, cover:c, eff, why:`never reached the end (${Math.round(c*100)}% covered)`};
}

// ---------- sweep -----------------------------------------------------------
const CHARS = Object.keys(letters);
const SIZES = [];
for (let f=BASE_F; f>=FLOOR-1e-9; f-=0.02) SIZES.push(Math.round(f*1000)/1000);
if (SIZES[SIZES.length-1] > FLOOR) SIZES.push(FLOOR);
const lvOf = f => { let lv=0; while (Math.max(FLOOR,BASE_F*Math.pow(SHRINK,lv)) > f+1e-9 && lv<40) lv++; return lv; };
const SEEDS = [1,2,3];

// A glyph passes a size if any of the simulated hands gets through; a size
// passes if every glyph does.
function failuresAt(f, wobblePx){
  const bad = [];
  let effSum=0, effN=0;
  for (const ch of CHARS){
    let ok=false, last=null;
    for (const seed of SEEDS){
      const r = score(ch, f, wobblePx, seed); last=r; effSum+=r.eff; effN++;
      if (r.ok){ ok=true; break; }
    }
    if (!ok) bad.push([ch, last.why]);
  }
  return {bad, eff:effSum/effN};
}

// The most useful number per size is not pass/fail at one wobble, it is how
// much stray the size tolerates at all — a budget in pixels, which is the
// same unit the hand reports in. If that budget shrinks as the glyph does,
// the curve is outrunning the hand; if it holds, the difficulty is elsewhere.
// Scanned upward, not bisected: whether a given hand gets through is not
// monotonic in the wobble amplitude — a larger stray can pass where a smaller
// one failed, because the phase differs. Bisection silently reports whichever
// side of that noise it lands on. The first amplitude that fails is the real
// budget.
function budget(f){
  let last = 0;
  for (let w=2; w<=48; w+=2){
    if (failuresAt(f, w).bad.length) return last;
    last = w;
  }
  return last;
}

console.log(`  ${target.split('/').pop()} · ${CHARS.length} glyphs × ${SIZES.length} sizes`
  + ` · ${CANVAS}px canvas · ${SAMPLE}px sampling`);
if (!BRIEF) console.log(`  tolerance ${SQRT_TOL?'R_ON0*sqrt(curS)':'R_ON0*curS'} floored at ${MIN_TOL},`
  + ` cover ${COVER}, travel cap ${MAXTRAV}x`);
if (!BRIEF){
  console.log('');
  console.log('   size    glyph   tol   hand budget   travel   honest trace');
  console.log('  ' + '─'.repeat(62));
}

const px = f => Math.round(f*CANVAS);
const rows = [], gateFail = [];
for (const f of SIZES){
  const curS = f/BASE_F;
  const tol  = Math.max(MIN_TOL, R_ON0*(SQRT_TOL?Math.sqrt(curS):curS))*CANVAS;
  const g    = failuresAt(f, WOBBLE);
  const b    = budget(f);
  rows.push({f, lv:lvOf(f), tol, b, ...g});
  if (g.bad.length) gateFail.push({f, bad:g.bad});
  const tag = g.bad.length
    ? `${String(g.bad.length).padStart(2)} fail ${g.bad.slice(0,5).map(x=>x[0]).join(' ')}`
      + (g.bad.length>5 ? ' …' : '')
    : 'all 46 pass';
  if (!BRIEF) console.log(`  ${f.toFixed(2)} lv${String(lvOf(f)).padStart(2)}`
    + `  ${String(px(f)).padStart(3)}px`
    + `  ${tol.toFixed(0).padStart(3)}px`
    + `  ${String(b).padStart(4)}px stray`
    + `  ${g.eff.toFixed(2)}x`
    + `   ${tag}`);
}

// Two trends worth stating outright, because each accuses a different suspect.
const t0=rows[0], tN=rows[rows.length-1];
if (!BRIEF) console.log('');
console.log(`  travel ratio ${t0.eff.toFixed(2)}x → ${tN.eff.toFixed(2)}x against a ${MAXTRAV}x cap`
  + `  — ${Math.abs(tN.eff/t0.eff-1) < 0.15 ? 'flat, so travel does not explain small-glyph failure'
                                            : 'CLIMBING as the glyph shrinks'}`);
console.log(`  hand budget  ${t0.b}px → ${tN.b}px on a glyph that goes ${px(t0.f)}px → ${px(tN.f)}px`
  + `  — ${tN.b >= t0.b*0.8 ? 'holds up, so the scoring is not what makes small glyphs hard'
                            : 'SHRINKING, the curve is outrunning the hand'}`);

if (gateFail.length){
  console.log('');
  console.log(`  FAIL: ${gateFail.length} size(s) reject an honest ${WOBBLE}px trace`);
  for (const g of gateFail.slice(0,6))
    console.log(`    ${g.f.toFixed(2)} (${px(g.f)}px): ${g.bad.slice(0,4).map(b=>`${b[0]} ${b[1]}`).join(', ')}`);
  console.log('    a size in the shipped range that no honest trace can pass is a bug,');
  console.log('    not a difficulty setting.');
  process.exit(1);
}
if (!BRIEF) console.log('');
console.log(`  every glyph passes at every size down to ${FLOOR}, with ${Math.min(...rows.map(r=>r.b))}px`
  + ` of stray to spare at the worst size (model only — the hand outranks it).`);
