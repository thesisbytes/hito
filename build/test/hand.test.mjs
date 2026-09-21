/**
 * The hand: what draws, what it drew, and how it has been going.
 *
 * Three promises, and each has a way of being quietly false:
 *
 *   - the pen/finger switch has to reach the ENGINE's penOnly, not a copy of
 *     it. A switch that only changes its own label is the save button that
 *     said "saved ✓" all over again.
 *   - a trace is stored in the stroke book's space, so the same shape drawn at
 *     two sizes must come out as the same numbers. If it does not, nothing
 *     drawn at 0.32 can ever be compared with anything drawn at 0.62.
 *   - writing things down must never cost a glyph. conjure() and fizzle() are
 *     wrapped, so a throw in here would be a character that cannot be landed.
 *
 *   node build/test/hand.test.mjs dist/hiragana-vX.Y.Z.html [dist/hiragana-game-vX.Y.Z.html]
 */
import { readFileSync } from 'fs';

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };

function boot(file, { stored = {}, touchPoints = 0, fine = false, coarse = false, screen = {width:1280, height:800} } = {}){
  const html = readFileSync(file, 'utf8');
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  let T = 0;
  const store = {...stored};
  const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4)}; }, set: () => true });
  const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
    getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:400,height:400}),
    querySelectorAll:()=>[], children:[], dataset:{}, insertBefore(){}, removeChild(){},
    append(){}, appendChild(){}, addEventListener(){}, setAttribute(){} },
    { get(t,k){
        if (k in t) return t[k];
        if (k==='width'||k==='height'||k==='offsetWidth') return 400;
        if (k==='parentNode') return el();
        if (typeof k==='symbol') return undefined;
        return new Proxy(function(){ return el(); }, { get:()=>'' });
      }, set(t,k,v){ t[k]=v; return true; } });
  const g = globalThis;
  g.document = { getElementById:el, createElement:el, body:el(), addEventListener(){},
    documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
  g.window = g;
  g.addEventListener = () => {};
  g.setTimeout = () => 0; g.setInterval = () => 0; g.clearTimeout = () => {};
  g.URL = { createObjectURL:()=>"" }; g.Blob = class {};
  g.localStorage = { getItem:k => (k in store ? store[k] : null), setItem:(k,v) => { store[k] = String(v); }, removeItem:k => { delete store[k]; } };
  g.requestAnimationFrame = () => 0;
  g.performance = { now:()=>T };
  Object.defineProperty(g, 'navigator', {value:{vibrate(){}, maxTouchPoints:touchPoints, onLine:false}, configurable:true});
  g.screen = screen;
  g.FontFace = class { load(){ return Promise.resolve(this); } };
  g.atob = s => Buffer.from(s,'base64').toString('binary');
  g.matchMedia = q => ({matches: q.includes('fine') ? fine : q.includes('coarse') ? coarse : false, addEventListener(){}});
  g.devicePixelRatio = 1;
  g.fetch = () => Promise.reject(new Error('the test is offline'));
  for (const k of ['__hand','__sync','__field','__vocab','__probe']) delete g[k];

  const bridgeFor = src => {
    const names = [...src.matchAll(/^function\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]);
    return names.length ? `\n;${names.map(n => `try{window.${n}=${n};}catch(_){}`).join('')}\n` : '';
  };
  const probe = `\nwindow.__probe = { get penOnly(){ return penOnly; }, get done(){ return done; }, get idx(){ return idx; },
    get LETTERS(){ return LETTERS; }, get strokes(){ return strokes; }, get BASE_F(){ return BASE_F; },
    setStrokes(v){ strokes = v; }, setSize(f){ curF = f; curS = f/BASE_F; }, get W(){ return W; }, get H(){ return H; } };`;
  new Function(blocks.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();
  g.resize();
  if (g.__field) g.__field.begin();
  return { H: g.__hand, P: g.__probe, S: g.__sync, store, g, tick: ms => { T += ms; } };
}

const workshop = process.argv[2], game = process.argv[3];

// ---- the first guess avoids a dead sketchbook, and is not saved as a choice
{
  const tablet = boot(workshop, {touchPoints:10, coarse:true, screen:{width:1280, height:800}});
  ok(tablet.H, 'the hand layer did not initialise');
  if (!tablet.H) process.exit(1);
  ok(tablet.H.input === 'pen' && tablet.P.penOnly === true, 'a tablet did not start pen-only — a resting palm would draw');
  ok(!('hito-input' in tablet.store), 'a guess was saved as if the player had chosen it');
  const phone = boot(workshop, {touchPoints:5, coarse:true, screen:{width:390, height:844}});
  ok(phone.H.input === 'finger' && phone.P.penOnly === false, 'a phone started pen-only: the sketchbook ignores the only thing it has');
  const desk = boot(workshop, {touchPoints:0});
  ok(desk.H.input === 'finger' && desk.P.penOnly === false, 'a mouse-only desktop started pen-only');
}

// ---- the switch reaches the engine, and is remembered
{
  const a = boot(workshop, {touchPoints:10, coarse:true});
  a.H.setInput('finger');
  ok(a.P.penOnly === false, 'setInput("finger") did not clear the engine\'s penOnly');
  ok(a.store['hito-input'] === 'finger', 'the choice was not saved');
  a.H.setInput('pen');
  ok(a.P.penOnly === true, 'setInput("pen") did not set the engine\'s penOnly');
  const b = boot(workshop, {stored:{'hito-input':'finger'}, touchPoints:10, coarse:true});
  ok(b.H.input === 'finger' && b.P.penOnly === false, 'a saved choice lost to the guess on reload');
}

// A stroke in canvas pixels, as the engine keeps them.
const line = (x0, y0, x1, y1, n, t0 = 0) => Array.from({length:n}, (_, i) => ({
  x: x0 + (x1 - x0)*i/(n - 1), y: y0 + (y1 - y0)*i/(n - 1), p:.5, t: t0 + i*8 }));

// ---- a landed glyph is written down, and still lands
{
  const { H, P, S, store, g } = boot(workshop, {stored:{'hito-input':'pen'}});
  const ch = P.LETTERS[P.idx][0];
  P.setStrokes([line(120, 120, 280, 130, 60), line(200, 100, 210, 300, 80, 900)]);
  g.zap({x:1, y:1});
  g.conjure();
  ok(P.done === true, 'conjure() did not reach the engine through the hand');
  const e = H.ledger.g[ch];
  ok(e && e.n === 1 && e.zaps === 1 && e.clean === 0, `ledger for ${ch} is ${JSON.stringify(e)}`);
  const r = H.hands[H.hands.length - 1];
  ok(r && r.glyph === ch && r.ok === true && r.strokes === 2 && r.zaps === 1, `trace record is ${JSON.stringify(r).slice(0,160)}`);
  ok(r.ms === 900 + 79*8, `trace time is ${r.ms}ms, expected ${900 + 79*8}`);
  ok(r.s.length === 2 && r.s.every(f => f.length % 3 === 0 && f.length >= 6), 'strokes are not flat x,y,t triples');
  ok(r.s.every(f => f.length/3 <= 64), 'a stroke kept more than maxPoints');
  ok(JSON.stringify(r).length < 7000, `one trace is ${JSON.stringify(r).length} characters`);
  ok(JSON.parse(store['hito-ledger']).g[ch].n === 1, 'the ledger was not persisted');
  const queued = JSON.parse(store['hito-outbox'] || '[]');
  ok(queued.some(q => q.kind === 'trace' && q.body.glyph === ch), 'the trace was not handed to the outbox');
  ok(S.enabled === true, 'this build has no sync endpoint, so nothing it records can ever arrive');
}

// ---- a fizzle is written down too, and the attempt carries its history
{
  const { H, P, g } = boot(workshop, {stored:{'hito-input':'pen'}});
  const ch = P.LETTERS[P.idx][0];
  P.setStrokes([line(100, 100, 300, 300, 50)]);
  g.zap({x:1,y:1}); g.zap({x:1,y:1});
  g.fizzle();
  ok(P.strokes.length === 0, 'fizzle() did not reach the engine through the hand');
  let e = H.ledger.g[ch];
  ok(e.fizz === 1 && e.n === 0 && e.zaps === 2, `after a fizzle the ledger is ${JSON.stringify(e)}`);
  ok(H.hands[H.hands.length-1].ok === false, 'the fizzled trace was not kept');
  P.setStrokes([line(100, 100, 300, 300, 50)]);
  g.conjure();
  e = H.ledger.g[ch];
  ok(e.n === 1 && e.clean === 0, 'a glyph landed after a fizzle was counted as clean');
  ok(H.hands[H.hands.length-1].tries === 1, 'the landed trace does not say it took a second try');
}

// ---- the same shape at two sizes is the same numbers
{
  const { H, P } = boot(workshop, {stored:{'hito-input':'pen'}});
  const shape = [[.35,.30],[.65,.32],[.60,.55],[.40,.70]];
  const at = f => {
    P.setSize(f);
    const s = f/P.BASE_F, cy0 = .5 + P.BASE_F*.06, cyN = .5 + f*.06;
    return H.pack([shape.map(([x, y], i) => ({ x: (.5 + (x - .5)*s)*P.W, y: (cyN + (y - cy0)*s)*P.H, p:.5, t:i*100 }))])[0];
  };
  const big = at(0.62), small = at(0.32);
  const xy = f => f.filter((_, i) => i % 3 !== 2);
  const worst = Math.max(...xy(big).map((v, i) => Math.abs(v - xy(small)[i])));
  ok(big.length === small.length && worst <= 1, `a shape drawn at 0.62 and 0.32 differs by ${worst} units in book space`);
  ok(Math.abs(big[0] - 350) <= 1 && Math.abs(big[1] - 300) <= 1, `book space is off: first point came back as ${big[0]},${big[1]}, drew 350,300`);
}

// ---- a note that cannot be taken does not cost the glyph
{
  const { P, g, H } = boot(workshop, {stored:{'hito-input':'pen'}});
  P.setStrokes([[{x:NaN, y:undefined}], null, 'not a stroke']);
  let threw = null;
  try { g.conjure(); } catch(e){ threw = e; }
  ok(!threw && P.done === true, `garbage in strokes stopped a glyph landing: ${threw && threw.message}`);
  // Not left lying about: the engine repaints `strokes` on a deferred
  // font-ready resize, and it cannot paint a null any more than a pen can draw one.
  P.setStrokes([]);
  const bare = boot(workshop);
  bare.P.setStrokes([]);
  try { bare.g.conjure(); } catch(e){ threw = e; }
  ok(!threw && bare.P.done === true, 'a conjure with no ink (a hint, a cast) threw');
  ok(Object.keys(bare.H.ledger.g).length === 0, 'a conjure with no ink was counted as handwriting');
}

// ---- shaky is recent, not forever
{
  const { H, P, g } = boot(workshop, {stored:{'hito-input':'pen'}});
  const ch = P.LETTERS[P.idx][0];
  const go = zaps => { P.setStrokes([line(100,100,300,300,40)]); for (let i = 0; i < zaps; i++) g.zap({x:1,y:1}); H.note(true); };
  go(4); go(5);
  ok(!H.shaky(ch), 'two attempts were enough to call a character shaky');
  go(4);
  ok(H.shaky(ch), `three rough attempts did not make ${ch} shaky (tr ${H.ledger.g[ch].tr})`);
  ok(H.stats().bites.some(b => b.c === ch), 'a shaky character is missing from "these bite you most"');
  let cleans = 0; while (H.shaky(ch) && cleans < 10){ go(0); cleans++; }
  ok(cleans <= 3, `it took ${cleans} clean traces to stop being called shaky`);
}

// ---- sharing off: the ledger still works and nothing is queued
{
  const { H, P, S, g, store } = boot(workshop, {stored:{'hito-input':'pen', 'hito-share':'0'}});
  P.setStrokes([line(100,100,300,300,40)]);
  g.conjure();
  ok(S.share === false, 'the share switch did not load as off');
  ok(Object.keys(H.ledger.g).length === 1, 'with sharing off the local ledger stopped too');
  ok(JSON.parse(store['hito-outbox'] || '[]').length === 0, 'a trace was queued with sharing off');
}

// ---- export and import: merged, the fuller record wins, junk is refused
{
  const a = boot(workshop, {stored:{'hito-input':'pen'}});
  const ch = a.P.LETTERS[a.P.idx][0];
  for (let i = 0; i < 3; i++){ a.P.setStrokes([line(100,100,300,300,40)]); a.H.note(true); }
  const text = a.H.exportText();
  const b = boot(workshop, {stored:{'hito-input':'pen'}});
  b.P.setStrokes([line(100,100,300,300,40)]); b.H.note(true);
  ok(b.H.importText(text) === true, 'a fresh export was refused on import');
  ok(b.H.ledger.g[ch].n === 3, `import kept ${b.H.ledger.g[ch].n} conjures; the fuller record (3) should win`);
  ok(JSON.parse(b.store['hito-ledger']).g[ch].n === 3, 'the imported ledger was not persisted');
  ok(b.H.importText('{"score":9000}') === false && b.H.importText('not json') === false, 'junk was accepted as a ledger');
  b.H.importText(JSON.stringify({hito:'ledger', ledger:{g:{'<img src=x onerror=alert(1)>':{n:99, fizz:9, tr:9}}}}));
  b.H.render();
  ok(!/<img/.test(b.H.html), 'an imported character name reached the page unescaped');
}

// ---- the sheet says what it is doing
{
  const { H, P } = boot(workshop, {stored:{'hito-input':'pen'}});
  P.setStrokes([line(100,100,300,300,40)]); H.note(true);
  H.render();
  ok(/draw with/.test(H.html) && /pen only/.test(H.html) && /finger/.test(H.html), 'the sheet has no pen/finger switch');
  ok(/notes to the workshop/.test(H.html) && /no account, no name/.test(H.html), 'a syncing build does not say what it sends');
  ok(/<svg/.test(H.html), 'the sheet does not show the handwriting it kept');
  ok(/export the ledger/.test(H.html), 'progress with no export is progress that lives only in browser storage');
}

// ---- in the game: the start page carries the switch, and the ledger steers the spawn
if (game){
  const { H, g } = boot(game, {stored:{'hito-input':'pen'}});
  const F = g.__field;
  ok(F && H, 'the game build is missing the field or the hand');
  F.openStart();
  ok(/draw with/.test(F.startHtml) && /data-k="input"/.test(F.startHtml), 'the start page has no pen/finger row');
  ok(/how the hand is doing/.test(F.startHtml), 'the start page has no way into the stats');
  F.begin();
  H.show();
  ok(F.paused === true, 'the hand sheet opened over a running field: the farang do not wait');
}

if (fail) { console.log(`  ${fail} hand check(s) failed`); process.exit(1); }
console.log('  the switch reaches the engine and is remembered, a phone is not locked out, every attempt is written '
  + 'down in book space without costing a glyph, shaky decays, sharing off means off, and the ledger exports and merges');
