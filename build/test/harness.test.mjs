/**
 * The debug harness has to actually reach into the engine, not merely parse.
 *
 * smoke.test.mjs runs each <script> in its own new Function scope, so the
 * telemetry layer there cannot see the engine's top-level `let` bindings at
 * all — and every one of its reads is wrapped in try/catch, so a layer that
 * touched nothing would still pass. In a browser, classic scripts share one
 * global lexical scope. This rig concatenates them the way a browser would,
 * then drives the controls and checks the engine moved.
 *
 * What is being defended: a size pin that silently does nothing would make
 * every sweep result a lie, and this project has already shipped one control
 * that reported success while writing nothing.
 *
 *   node build/test/harness.test.mjs dist/hiragana-vX.Y.Z-debug.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const html = readFileSync(target, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

let raf = [];
const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4)}; }, set: () => true });
const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
  getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:400,height:400}),
  querySelectorAll:()=>[], children:[], dataset:{}, append(){}, appendChild(){} },
  { get(t,k){
      if (k in t) return t[k];
      if (k==='width'||k==='height'||k==='offsetWidth') return 400;
      if (typeof k==='symbol') return undefined;
      return new Proxy(function(){ return el(); }, { get:()=>'' });
    }, set(){ return true; } });
globalThis.document = { getElementById:el, createElement:el, body:el(), addEventListener(){},
  documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
globalThis.window = globalThis;
globalThis.addEventListener = () => {};
globalThis.setTimeout = () => 0;
globalThis.setInterval = () => 0;
globalThis.clearTimeout = () => {};
globalThis.URL = { createObjectURL:()=>"" };
globalThis.Blob = class {};
const store = {};
globalThis.localStorage = { getItem:k=>store[k]??null, setItem(k,v){store[k]=v;}, removeItem(k){delete store[k];} };
globalThis.requestAnimationFrame = f => { raf.push(f); return raf.length; };
globalThis.performance = { now:()=>0 };
Object.defineProperty(globalThis,"navigator",{value:{vibrate(){}},configurable:true});
globalThis.FontFace = class { load(){ return Promise.resolve(this); } };
globalThis.atob = s => Buffer.from(s,'base64').toString('binary');
globalThis.matchMedia = () => ({matches:false, addEventListener(){}});
globalThis.devicePixelRatio = 1;

// One scope, as a browser gives classic scripts — plus a probe for the
// bindings that are lexical and so never land on window.
const probe = `
window.__probe = {
  get curF(){ return curF; },
  get SIZE_PIN(){ return SIZE_PIN; },
  get SIZE_MODE(){ return SIZE_MODE; },
  get SIZE_MIN(){ return SIZE_MIN; },
  get SIZE_MAX(){ return SIZE_MAX; },
  get idx(){ return idx; },
  sizeFor,
};`;
new Function(blocks.join('\n;\n') + probe)();

const P = globalThis.__probe, H = globalThis.__hito;
let fail = 0;
const ok  = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };

ok(P && H, 'the layer never reached the engine scope');
if (!P || !H) process.exit(1);

// ---- the seam exists and is wired to the pack
ok(typeof P.sizeFor === 'function', 'sizeFor() missing — the size seam did not land');
ok(P.SIZE_MAX > P.SIZE_MIN, `sizeRange is not ascending (${P.SIZE_MIN}..${P.SIZE_MAX})`);

// ---- random mode actually varies, and stays inside the range
if (P.SIZE_MODE === 'random') {
  const draws = Array.from({length: 200}, () => P.sizeFor('あ'));
  ok(new Set(draws).size > 100, 'random mode returns the same size over and over');
  ok(Math.min(...draws) >= P.SIZE_MIN && Math.max(...draws) <= P.SIZE_MAX,
     `random sizes escape [${P.SIZE_MIN}, ${P.SIZE_MAX}]`);
  ok(Math.min(...draws) < P.SIZE_MIN + (P.SIZE_MAX-P.SIZE_MIN)*0.1,
     'random mode never reaches the small end — the sizes that need testing');
}

// ---- a pin holds, and holds across glyph navigation
const want = H.sizes[Math.floor(H.sizes.length/2)];
H.setSize(want);
ok(Math.abs(P.curF - want) < 1e-9, `pinning ${want} left curF at ${P.curF}`);
const before = P.idx;
H.stepGlyph(1);
ok(P.idx !== before, 'stepGlyph did not move to another glyph');
ok(Math.abs(P.curF - want) < 1e-9,
   `the pin did not survive navigation: curF ${P.curF} after moving glyph`);
for (let i = 0; i < 5; i++) H.stepGlyph(1);
ok(Math.abs(P.curF - want) < 1e-9, 'the pin drifted while walking the alphabet');

// ---- the whole ladder is reachable and monotonic
const seen = H.sizes.map(f => { H.setSize(f); return P.curF; });
ok(seen.every((v,i) => Math.abs(v - H.sizes[i]) < 1e-9), 'some ladder sizes cannot be pinned');
ok(seen.every((v,i) => i === 0 || v < seen[i-1]), 'the ladder is not descending');
ok(Math.abs(seen[seen.length-1] - P.SIZE_MIN) < 1e-9,
   `the ladder stops at ${seen[seen.length-1]}, not the floor ${P.SIZE_MIN}`);

// ---- releasing the pin gives the mode back
H.unpinSize();
ok(P.SIZE_PIN === null, 'unpin left the size pinned');

// ---- the flag records what tells the three suspects apart
H.setSize(want);
H.clearFlags();
const rec = H.flagFail();
ok(H.flags.length === 1, 'the flag was not recorded');
ok(Math.abs(rec.size - want) < 1e-9, `flag recorded size ${rec.size}, not the pinned ${want}`);
for (const k of ['char','size','level','coverage','travel','reason','pinned'])
  ok(k in rec, `flag is missing ${k} — it cannot distinguish curve from data from state`);
ok(rec.pinned === true, 'flag did not notice the size was pinned');

// ---- flags survive a reload, since a sweep spans sessions
ok(store['hito-size-flags'] && JSON.parse(store['hito-size-flags']).length === 1,
   'flags are not persisted — a sweep would lose everything on reload');

// ---- the matrix is readable on the tablet
H.setSize(H.sizes[0]); H.flagFail();
const m = H.matrix();
ok(/\S/.test(m) && m.includes(rec.char), 'the matrix does not show the flagged glyph');
ok(m.split('\n').length >= 2, 'the matrix has no rows');

if (fail) { console.log(`  ${fail} harness check(s) failed`); process.exit(1); }
console.log(`  size pin holds across navigation, ${H.sizes.length}-step ladder reaches `
  + `${P.SIZE_MIN}, flags persist and tabulate`);
