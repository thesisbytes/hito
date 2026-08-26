import { readFileSync } from 'fs';
const book = JSON.parse(readFileSync('scripts/hiragana/strokes.json','utf8'));
const letters = book.fonts[book.activeFont].letters;

const R_ON = 0.07, LOOK = 24, COVER_MIN = 0.85;

function build(ch){
  const PATH=[], SEGS=[];
  for (const st of letters[ch].strokes){
    const a = PATH.length;
    for (const q of st) PATH.push({x:q.x, y:q.y});
    SEGS.push([a, PATH.length-1]);
  }
  return {PATH, SEGS};
}

// Faithful re-implementation of the new follow() for offline exercise.
function simFor(ch, pen){            // pen = array of strokes, each array of {x,y}
  const {PATH,SEGS} = build(ch);
  let prog=0, segIdx=0, awaitLift=false, conjured=false, blocked=0;
  let travel=0, lastN=null, PATHLEN=0;
  for(const g of SEGS) for(let i=g[0];i<g[1];i++)
    PATHLEN+=Math.hypot(PATH[i+1].x-PATH[i].x,PATH[i+1].y-PATH[i].y);
  const hit = new Uint8Array(PATH.length);
  const covered = () => hit.reduce((a,b)=>a+b,0)/hit.length;

  for (const stroke of pen){
    // pen down
    if (awaitLift && segIdx < SEGS.length-1){ segIdx++; prog=SEGS[segIdx][0]; awaitLift=false; }
    lastN=null;
    for (const n of stroke){
      const seg = SEGS[segIdx]; if(!seg) break;
      if(!lastN){ lastN={x:n.x,y:n.y}; }
      else { const step=Math.hypot(n.x-lastN.x,n.y-lastN.y);
        if(step>=0.006){ travel+=step; lastN={x:n.x,y:n.y}; } }
      if (awaitLift){
        const e=PATH[seg[1]];
        if(Math.hypot(n.x-e.x,n.y-e.y)<R_ON*1.6) continue;   // still finishing
        blocked++; continue; }
      const lo=Math.max(prog,seg[0]), hi=Math.min(seg[1],prog+LOOK);
      for(let i=seg[0];i<=seg[1];i++)
        if(Math.hypot(n.x-PATH[i].x,n.y-PATH[i].y)<R_ON) hit[i]=1;
      let best=-1, bd=R_ON;
      for(let i=lo;i<=hi;i++){
        const d=Math.hypot(n.x-PATH[i].x, n.y-PATH[i].y);
        if(d<bd){bd=d;best=i;}
      }
      if(best>=0){
        prog=Math.max(prog,best);
        if(prog>=seg[1]-4 && Math.hypot(n.x-PATH[seg[1]].x,n.y-PATH[seg[1]].y)<R_ON){
          prog=seg[1];
          if(segIdx>=SEGS.length-1){
            const eff=PATHLEN?travel/PATHLEN:1;
            if(covered()>=COVER_MIN && eff<=2.5){ conjured=true; }
            return {conjured, cover:covered(), blocked, eff};
          }
          awaitLift=true;
        }
      }
    }
  }
  return {conjured, cover:covered(), blocked, eff:PATHLEN?travel/PATHLEN:0};
}

const CH='き';                                   // 4 strokes, the hook case
const raw = letters[CH].strokes.map(st=>st.map(q=>({x:q.x,y:q.y})));
const R = (label, pen) => {
  const r = simFor(CH, pen);
  console.log(`  ${r.conjured?'CONJURED':'rejected'}  cover ${(r.cover*100).toFixed(0)}%`
    + `  travel ${(r.eff||0).toFixed(1)}x` + (r.blocked?`  blocked ${r.blocked}`:'') + `   ${label}`);
  return r;
};

console.log(`き — ${raw.length} strokes, ${raw.flat().length} path points\n`);

R('perfect trace, correct lifts', raw);
R('one continuous line, no lifts', [raw.flat()]);
R('stroke 3 skipped', [raw[0], raw[1], raw[3]]);
R('strokes in wrong order', [raw[1], raw[0], raw[2], raw[3]]);
R('every 6th point only (fast sloppy)', raw.map(s=>s.filter((_,i)=>i%6===0)));
// Hooks live in the tail of a stroke, so the tail is what must not be
// forgiven. Cuts are proportional: an absolute point count means something
// different on a long stroke than a short one, and different again once
// mastery shrinks the glyph.
R('tail cut 5%  (a few px — should pass)',
  raw.map(s=>s.slice(0, Math.max(2, Math.round(s.length*0.95)))));
R('tail cut 10% (hook skipped)',
  raw.map(s=>s.slice(0, Math.max(2, Math.round(s.length*0.90)))));
R('tail cut 20% (hook clearly skipped)',
  raw.map(s=>s.slice(0, Math.max(2, Math.round(s.length*0.80)))));
R('full-canvas scribble', [Array.from({length:1200},(_,i)=>({
    x:0.5+0.34*Math.cos(i*0.41), y:0.5+0.34*Math.sin(i*0.27)}))]);
R('dense raster scribble', [(()=>{const p=[];for(let r=0;r<40;r++)for(let c=0;c<40;c++)
    p.push({x:0.26+c*0.012, y:0.29+r*0.012});return p;})()]);

console.log('\n--- realistic pen input (dense samples, human wobble) ---');
function jitter(strokes, amp, keep){
  return strokes.map(s => s.filter((_,i)=>i%keep===0).map(q=>({
    x:q.x+(Math.random()-0.5)*amp, y:q.y+(Math.random()-0.5)*amp })));
}
// a real pen samples far denser than the path: interpolate up, then wobble
function dense(strokes, amp, mult){
  // A hand wobbles slowly; it does not jitter independently every sample.
  return strokes.map(s=>{
    const out=[]; let n=0, ph=Math.random()*6.28;
    for(let i=0;i<s.length-1;i++){
      for(let k=0;k<mult;k++){
        const t=k/mult; n++;
        const wx=Math.sin(n*0.06+ph)*amp*0.5, wy=Math.cos(n*0.045+ph*1.7)*amp*0.5;
        out.push({x:s[i].x+(s[i+1].x-s[i].x)*t+wx, y:s[i].y+(s[i+1].y-s[i].y)*t+wy});
      }
    }
    out.push(s[s.length-1]);
    return out;
  });
}
for (const amp of [0.005, 0.015, 0.030, 0.050]){
  const r = simFor(CH, dense(raw, amp, 3));
  console.log(`  ${r.conjured?'CONJURED':'rejected'}  cover ${(r.cover*100).toFixed(0)}%   wobble ±${(amp/2*100).toFixed(1)}% of canvas`);
}
console.log('\n--- sparse sampling (slow device / fast hand) ---');
for (const keep of [1,2,4,8,16]){
  const r = simFor(CH, jitter(raw, 0.01, keep));
  console.log(`  ${r.conjured?'CONJURED':'rejected'}  cover ${(r.cover*100).toFixed(0)}%   every ${keep}${keep===1?'st':'th'} path point`);
}

console.log('\n--- all 46: does a correct trace conjure? ---');
let ok=0, bad=[];
for (const ch of Object.keys(letters)){
  const raw = letters[ch].strokes.map(st=>st.map(q=>({x:q.x,y:q.y})));
  const pen = dense(raw, 0.012, 3);
  const {PATH,SEGS}=build(ch);
  const r = simFor(ch, pen);
  if (r.conjured) ok++; else bad.push(`${ch} ${(r.cover*100).toFixed(0)}%`);
}
console.log(`  ${ok}/46 conjure with a correct, slightly wobbly trace`);
if (bad.length) console.log('  failures:', bad.join('  '));

console.log('\n--- all 46: does a scribble ever get through? ---');
let leaked=[];
for (const ch of Object.keys(letters)){
  const scribble=[Array.from({length:1500},(_,i)=>({
    x:0.5+0.24*Math.cos(i*0.37)+0.08*Math.cos(i*1.9),
    y:0.5+0.24*Math.sin(i*0.29)+0.08*Math.sin(i*2.3)}))];
  if (simFor(ch, scribble).conjured) leaked.push(ch);
}
console.log(leaked.length ? `  LEAKED: ${leaked.join(' ')}` : '  0/46 — no scribble conjured');
