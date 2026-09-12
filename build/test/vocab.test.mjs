/**
 * The vocab shell, driven rather than looked at.
 *
 * A word is a sequence of glyphs and the card walks the tracer through it.
 * What is being defended is the seam: every load the engine initiates on its
 * own has to land on the kana the card is asking for, a finished kana has to
 * advance to the next one, a finished word has to bloom and move on, and a
 * peek has to count against the word so the next round asks it sooner.
 *
 *   node build/test/vocab.test.mjs dist/vocab-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const html = readFileSync(target, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

let raf = [], T = 0;
const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4)}; }, set: () => true });
const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
  getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:400,height:400}),
  querySelectorAll:()=>[], children:[], dataset:{}, insertBefore(){}, removeChild(){},
  append(){}, appendChild(){}, addEventListener(){}, select(){}, focus(){}, click(){} },
  { get(t,k){
      if (k in t) return t[k];
      if (k==='width'||k==='height'||k==='offsetWidth') return 400;
      if (k==='parentNode') return el();
      if (typeof k==='symbol') return undefined;
      return new Proxy(function(){ return el(); }, { get:()=>'' });
    }, set(){ return true; } });
globalThis.document = { getElementById:el, createElement:el, body:el(), addEventListener(){},
  documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
globalThis.window = globalThis;
globalThis.addEventListener = () => {};
let timers = [];
globalThis.setTimeout = (fn, ms) => { timers.push({fn, at: T + (ms||0)}); return timers.length; };
globalThis.setInterval = () => 0;
globalThis.clearTimeout = id => { if (id) timers[id-1] = null; };
globalThis.URL = { createObjectURL:()=>"" };
globalThis.Blob = class {};
const store = {};
globalThis.localStorage = { getItem:k=>k in store?store[k]:null, setItem(k,v){ store[k]=String(v); }, removeItem(k){ delete store[k]; } };
globalThis.requestAnimationFrame = f => { raf.push(f); return raf.length; };
globalThis.performance = { now:()=>T };
Object.defineProperty(globalThis,"navigator",{value:{vibrate(){}},configurable:true});
globalThis.FontFace = class { load(){ return Promise.resolve(this); } };
globalThis.atob = s => Buffer.from(s,'base64').toString('binary');
globalThis.matchMedia = () => ({matches:false, addEventListener(){}});
globalThis.devicePixelRatio = 1;

function bridgeFor(src){
  const names = [...src.matchAll(/^function\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]);
  return names.length ? `\n;${names.map(n => `try{window.${n}=${n};}catch(_){}`).join('')}\n` : '';
}
const probe = `\nwindow.__probe = { get idx(){ return idx; }, get LETTERS(){ return LETTERS; }, get done(){ return done; }, get prog(){ return prog; }, get strokes(){ return strokes; }, get R_ON0(){ return R_ON0; }, get DRAIN(){ return DRAIN; }, get FIZZ(){ return FIZZ; }, get GUIDE_ON(){ return GUIDE_ON; }, get COMET_ON(){ return COMET_ON; }, get SHADOW_MODE(){ return SHADOW_MODE; }, get COVER_MIN(){ return COVER_MIN; }, get SIZE_PIN(){ return SIZE_PIN; }, get SIZE_MAX(){ return SIZE_MAX; }, get DRAG_FOLLOW(){ return DRAG_FOLLOW; }, get parts(){ return parts; }, get MASTERY(){ return MASTERY; }, get PATH(){ return PATH; }, setIdx(v){ idx=v; }, get SEGS(){ return SEGS; }, get segIdx(){ return segIdx; }, get awaitLift(){ return awaitLift; }, get R(){ return R_ON(); }, setSeg(i){ segIdx=i; prog=SEGS[i][0]; awaitLift=false; segTravel=0; segBase=prog; }, denorm(q){ return denorm(q); }, follow(q,d){ return follow(q,d); } };`;
// In a browser the engine's delayed load(idx+1) after a conjure resolves to
// window.load — the shell's wrapper. Inside one Function it would bind to the
// engine's own declaration and bypass the wrapper, which is exactly the seam
// under test, so that one call is pointed at window.load the way a browser
// would. Asserted, so a moved anchor fails here rather than passing vacuously.
const ADV = 'setTimeout(()=>{if(done) load(idx+1);},1900)';
if (!blocks.some(b => b.includes(ADV))) { console.log('  FAIL: the engine\'s delayed advance has moved; the rig cannot bridge it'); process.exit(1); }
const src = blocks.map(b => b.replace(ADV, ADV.replace('load(', 'window.load(')));
new Function(src.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();

const V = globalThis.__vocab, P = globalThis.__probe;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const advance = ms => {
  for (let e = T + ms; T < e; ){
    T = Math.min(T + 16, e);
    const due = timers.map((t,i)=>t&&t.at<=T?i:-1).filter(i=>i>=0);
    for (const i of due){ const t = timers[i]; timers[i] = null; t.fn(); }
  }
};
const cfg = JSON.parse(html.match(/window\.__VOCAB_CFG=\{deck:(\{[\s\S]*?\}),prompt:/)[1]);
const nums = Object.fromEntries([...html.match(/window\.__VOCAB_CFG=\{[\s\S]*?\};<\/script>/)[0]
  .matchAll(/(advanceMs|wordPauseMs):(\d+)/g)].map(m => [m[1], Number(m[2])]));

ok(V && P, 'the vocab layer did not initialise');
if (!V || !P) process.exit(1);

// ---- the sketchbook stays square (see field.test.mjs for why)
const stageCss = html.match(/body\.vocab \.stage\{([^}]*)\}/);
ok(stageCss && /aspect-ratio:\s*1/.test(stageCss[1]), 'the sketchbook is not square');

// ---- every kana of every word has stroke data in the built page
{
  const chars = new Set();
  for (const s of cfg.sections) for (const w of s.words) for (const c of w.ja) chars.add(c);
  const missing = [...chars].filter(c => V.at[c] === undefined);
  ok(!missing.length, `deck characters with no glyph in the build: ${missing.join('')}`);
  ok(cfg.sections.length >= 5, `expected the three L1 pages plus hours and minutes, got ${cfg.sections.length} sections`);
  ok(cfg.sections.some(s => s.words.some(w => w.ja === 'いっぷん')), 'いっぷん (one minute) is not in the deck');
  ok(cfg.sections.some(s => s.words.some(w => w.ja === 'じゅういちじ')), 'じゅういちじ (11 o\'clock) is not in the deck');
  ok(cfg.sections.some(s => s.words.some(w => w.ja === 'アメリカ')), 'no katakana word in the deck');
  ok(/KanjiVG/.test(html) && /Genki/.test(html), 'the credit line lost KanjiVG or the textbook');
}

// ---- the start page holds the three axes and begins a round
{
  ok(V.phase === 'start', `boot phase is ${V.phase}, expected start`);
  ok(V.redoShown === false, 'the redo button is showing under the start page');
  const B = V.base;
  ok(B.R_ON0 > 0 && B.DRAIN > 0 && B.FIZZ > 0, 'the base penalties were not read off the engine');
  ok(V.setDifficulty('guided') && P.DRAIN === 0 && P.FIZZ === Infinity && P.DRAG_FOLLOW === true
     && P.SIZE_PIN === P.SIZE_MAX && !P.COMET_ON, 'guided did not switch the engine');
  ok(V.setDifficulty('medium') && !P.GUIDE_ON && P.SHADOW_MODE === 'strokes' && P.SIZE_PIN === null,
     'medium did not switch the engine');
  ok(!V.setDifficulty('hard') && V.difficulty === 'medium', 'hard was accepted, and there is no scorer for it');
  ok(V.setDifficulty('easy') && P.R_ON0 === B.R_ON0 && P.GUIDE_ON && P.COMET_ON && P.SHADOW_MODE === 'none',
     'easy did not restore the pack values');
  ok(V.setPrompt('romaji') && V.prompt === 'romaji' && !V.setPrompt('klingon') && V.prompt === 'romaji',
     'the prompt axis misbehaves');
  V.setPrompt('en');
  const all = V.sections.length;
  ok(all === cfg.sections.length, 'not every section is selected at first boot');
  const first = cfg.sections[0].id;
  ok(V.toggleSection(first) && V.sections.length === all - 1, 'a section could not be deselected');
  ok(!V.toggleSection('nope'), 'an unknown section was accepted');
  // nothing selected → nothing to begin
  for (const s of cfg.sections) if (V.sections.includes(s.id)) V.toggleSection(s.id);
  ok(V.sections.length === 0 && !V.begin() && V.phase === 'start', 'a round began with no sections chosen');
  V.openStart();
  ok(/pick a section/.test(V.startHtml), 'the begin button does not say why it is disabled');
  ok(/href="hiragana-game\.html"/.test(V.startHtml), 'the start page has no way into the hiragana game');
  V.toggleSection(first);
  ok(V.begin() && V.phase === 'word' && V.redoShown, 'begin did not start a round');
  ok(V.queue.length === cfg.sections[0].words.length, `round has ${V.queue.length} words, section has ${cfg.sections[0].words.length}`);
}

// ---- the seam: the tracer is on the word's first kana, and stays there
{
  const w = V.word;
  ok(P.LETTERS[P.idx][0] === w.ja[0], `tracer is on ${P.LETTERS[P.idx][0]}, the word ${w.ja} starts with ${w.ja[0]}`);
  ok(P.PATH.length > 0, 'the first kana loaded with no path');
  const away = (P.idx + 5) % P.LETTERS.length;
  globalThis.load(away);
  ok(P.LETTERS[P.idx][0] === w.ja[0], `load(${away}) moved the tracer off the card's kana`);
  ok(/＿/.test(V.cardHtml), 'the slots are not blank on easy — the word is given away');
  ok(new RegExp(w.en.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).test(V.cardHtml), 'the card does not show the English prompt');
}

// ---- a finished kana lights its slot and moves on; a finished word blooms
{
  const w = V.word, n = [...w.ja].length;
  for (let k = 0; k < n; k++){
    ok(V.ci === k && P.LETTERS[P.idx][0] === w.ja[k] && V.phase === 'word',
       `at kana ${k} of ${w.ja}: ci ${V.ci}, tracer on ${P.LETTERS[P.idx][0]}, phase ${V.phase}`);
    globalThis.conjure();
    ok(P.done, 'conjure did not finish the glyph');
    // The engine's own 1.9s advance from an earlier kana can fire while this
    // one is finished and waiting on the shell. It must not reload it.
    const at = P.idx;
    globalThis.load(P.idx + 1);
    ok(P.idx === at && P.done, `a stale engine advance reloaded finished kana ${k} of ${w.ja}`);
    advance(nums.advanceMs + 20);
  }
  ok(V.phase === 'bloom', `after the last kana the phase is ${V.phase}, expected bloom`);
  ok(new RegExp(w.romaji).test(V.cardHtml), 'the bloom does not show the reading');
  // the engine's own delayed advance (1.9s after the last conjure) must not
  // reload anything while the word blooms
  const idxBloom = P.idx;
  globalThis.load(idxBloom + 3);
  ok(P.idx === idxBloom && P.done, 'a load during the bloom reloaded the finished glyph');
  const e = V.ledger[w.ja];
  ok(e && e.n === 1 && e.clean === 1 && e.peek === 0, `ledger after a clean word: ${JSON.stringify(e)}`);
  advance(nums.wordPauseMs + 20);
  ok(V.phase === 'word' && V.qi === 1 && V.word !== w, 'the bloom did not move to the next word');
  ok(P.LETTERS[P.idx][0] === V.word.ja[0] && !P.done, 'the next word\'s first kana is not loaded');
}

// ---- a conjure of some other glyph does not advance the word
// The engine could finish a glyph the card did not ask for (a stale timer, a
// stray load); the card must not count it as this kana.
{
  const w = V.word, ci = V.ci;
  const other = P.LETTERS.findIndex(L => L[0] !== w.ja[ci]);
  P.setIdx(other);
  globalThis.conjure();
  advance(nums.advanceMs + 20);
  ok(V.ci === ci && V.phase === 'word', `a conjure of ${P.LETTERS[other][0]} advanced the word past ${w.ja[ci]}`);
  // and the engine's own advance after that stray brings the tracer back to the card's kana
  globalThis.load(other + 1);
  ok(P.LETTERS[P.idx][0] === w.ja[ci] && !P.done, 'the tracer did not come back to the card\'s kana');
}

// ---- peeking counts, and comes back sooner
{
  const w = V.word;
  V.showReading();
  ok(V.peek === 1 && new RegExp(w.romaji).test(V.cardHtml), 'the reading did not show');
  V.showKana();
  ok(V.peek === 2 && !/＿/.test(V.cardHtml), 'show kana left blanks in the strip');
  for (let k = 0; k < [...w.ja].length; k++){ globalThis.conjure(); advance(nums.advanceMs + 20); }
  const e = V.ledger[w.ja];
  ok(e && e.n === 1 && e.clean === 0 && e.peek === 1, `ledger after a peeked word: ${JSON.stringify(e)}`);
  ok(V.weight(w) > V.weight(V.queue[0]), 'a peeked word does not outweigh a clean one');
  advance(nums.wordPauseMs + 20);
}

// ---- skip goes to the back of the queue, once
{
  const w = V.word, len = V.queue.length;
  V.skip();
  ok(V.queue.length === len + 1 && V.queue[V.queue.length-1].ja === w.ja, 'a skipped word was not requeued');
  ok(V.word !== w && V.phase === 'word', 'skip did not move on');
  ok(V.round.skipped === 1, 'skip was not counted');
  // skipping it again at the end must not requeue it forever
  while (V.phase === 'word' && V.word.ja !== w.ja) V.skip();
  ok(V.phase === 'word' && V.word.ja === w.ja, 'the requeued word never came round');
  V.skip();
  ok(V.queue.filter(x => x.ja === w.ja).length === 2, 'a word can be requeued more than once');
}

// ---- the round ends in a summary, and the ledger survives a new one
{
  let guard = 0;
  while (V.phase === 'word' && guard++ < 500){
    for (let k = 0; k < [...V.word.ja].length && V.phase === 'word'; k++){ globalThis.conjure(); advance(nums.advanceMs + 20); }
    if (V.phase === 'bloom') advance(nums.wordPauseMs + 20);
  }
  ok(V.phase === 'summary', `the round did not end: phase ${V.phase} after ${guard} words`);
  ok(/round done/.test(V.cardHtml) && /again/.test(V.cardHtml), 'the summary is missing');
  const idxS = P.idx;
  globalThis.load(idxS + 2);
  ok(P.idx === idxS, 'a load during the summary moved the tracer');
  const before = Object.keys(V.ledger).length;
  ok(before >= cfg.sections[0].words.length - 1, `ledger has ${before} words after a full round`);
  V.startRound();
  ok(V.phase === 'word' && Object.keys(V.ledger).length === before, 'a new round lost the ledger');
}

// ---- guided shows the kana, leaves no ink, does not zap
{
  V.setDifficulty('guided');
  ok(!/＿/.test(V.cardHtml), 'guided hides the kana it is meant to teach');
  const n = P.parts.length; globalThis.zap({x:10,y:10}); ok(P.parts.length === n, 'guided still zaps');
  P.strokes.push([{x:1,y:1,on:false},{x:2,y:2,on:false}]);
  V.tidy(); ok(P.strokes.length === 0, 'guided keeps strokes on the board');
  V.setDifficulty('easy');
  ok(/＿/.test(V.cardHtml), 'easy shows the kana after guided');
}

// ---- progress travels
{
  const led = JSON.parse(JSON.stringify(V.ledger));
  V.clearLedger();
  ok(Object.keys(V.ledger).length === 0, 'clearLedger did nothing');
  ok(!V.importProgress('not json'), 'garbage was imported');
  ok(V.importProgress(JSON.stringify({hito:'vocab', ledger: led})), 'an export was refused');
  ok(Object.keys(V.ledger).length === Object.keys(led).length, 'import did not restore the ledger');
  // import merges upward, never down
  const ja = Object.keys(led)[0];
  V.importProgress(JSON.stringify({hito:'vocab', ledger: {[ja]: {n:0, clean:0, peek:0, last:0}}}));
  ok(V.ledger[ja].n === led[ja].n, 'an import with lower counts lowered the ledger');
}

// ---- a stroke has to be travelled, not touched
// "The circle for the p sound is too sensitive. Just tapping on the initial
// point passes without doing the stroke." The handakuten circle is 0.081
// across and the tolerance is 0.07 (easy) or 0.105 (guided): from its start
// most or all of it is within reach, and its end is its start. In guided the
// drag walk ran round to the end from a tap; in easy a backward flick of a
// few points put the window onto the tail. Progress is now capped by the
// pen's own travel within the stroke.
{
  if (V.phase !== 'word'){ V.openStart(); if (!V.sections.length) V.toggleSection(cfg.sections[0].id); V.begin(); }
  ok(V.phase === 'word', `no round to put プ on (phase ${V.phase})`);
  const pu = {...cfg.sections[0].words[0], ja:'プ', romaji:'pu', en:'pu (test)'};
  V.queue.splice(V.qi + 1, 0, pu); V.nextWord();
  ok(P.LETTERS[P.idx][0] === 'プ' && P.PATH.length > 0, `could not put プ on the card (tracer on ${P.LETTERS[P.idx][0]})`);
  globalThis.resize();
  const den = P.denorm, fol = P.follow;
  for (const mode of ['guided', 'easy']){
    V.setDifficulty(mode);
    ok(P.LETTERS[P.idx][0] === 'プ' && !P.done, `${mode}: プ was not reloaded live`);
    // the segment is found after the reload: a new size resamples the path
    // and moves every index
    const si = P.SEGS.findIndex(([a, b]) => b - a > 4 && Math.hypot(P.PATH[a].x-P.PATH[b].x, P.PATH[a].y-P.PATH[b].y) < 0.01);
    ok(si >= 0, `${mode}: プ has no closed stroke to be the circle`);
    if (si < 0) continue;
    const [a, b] = P.SEGS[si];
    // a tap just short of the end, which is also the start, with digitizer jitter
    P.setSeg(si);
    fol(den(P.PATH[b-1]), true);
    for (let k = 0; k < 6; k++) fol(den({x: P.PATH[b-1].x + (k%2 ? .002 : -.002), y: P.PATH[b-1].y + (k%3 ? .002 : -.002)}));
    ok(!P.awaitLift && !P.done && P.prog < b - 4, `${mode}: a tap on the circle's start finished it (prog ${P.prog} of ${a}..${b})`);
    // a backward flick of a few points from the start
    P.setSeg(si);
    fol(den(P.PATH[a]), true);
    for (const i of [b-5, b-4, b-3, b-2]) fol(den(P.PATH[i]));
    ok(!P.awaitLift && !P.done && P.prog < b - 4, `${mode}: a backward flick finished the circle (prog ${P.prog} of ${a}..${b})`);
    // and the glyph actually drawn, circle included, still finishes (every
    // stroke, since coverage is judged over the whole glyph at the end)
    for (let k = 0; k < P.SEGS.length; k++){
      const [sa, sb] = P.SEGS[k];
      P.setSeg(k);
      fol(den(P.PATH[sa]), true);
      for (let i = sa; i <= sb; i++) fol(den(P.PATH[i]));
    }
    ok(P.done, `${mode}: drawing プ with its circle did not finish it (prog ${P.prog} of ${P.PATH.length-1})`);
  }
  V.setDifficulty('easy');
}

// ---- the workshop's furniture is hidden
ok(/body\.vocab[^{]*\.only-p[^{]*\{ display:none/.test(html), 'the practice row is showing');
ok(/body\.vocab[^{]*\.grid[^{]*\{ display:none/.test(html), 'the kana grid is showing');

if (fail) { console.log(`  ${fail} vocab check(s) failed`); process.exit(1); }
console.log(`  a word is walked kana by kana through the seam, blooms, peeks count, `
  + `skips requeue once, the round ends, and progress exports and imports`);
