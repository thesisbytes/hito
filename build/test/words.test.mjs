/**
 * The field with a deck: the farang carry words.
 *
 * What is being defended is the seam again, one level up. A word monster's
 * `i` has to be the kana it is waiting for; a finished kana has to advance
 * that monster and nothing else, keep the lock on it, knock it back a step
 * and not kill it; the last kana has to banish it; the ghost light has to be
 * kept by the word; and the sign has to speak for words in all three voices.
 *
 *   node build/test/words.test.mjs dist/katakana-game-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const html = readFileSync(target, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

let raf = [], T = 0;
const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4), width: 40}; }, set: () => true });
const el = () => new Proxy({ style:{}, classList:{add(){},remove(){},contains:()=>false},
  getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0,width:600,height:400}),
  querySelectorAll:()=>[], children:[], dataset:{}, insertBefore(){}, removeChild(){},
  append(){}, appendChild(){}, addEventListener(){} },
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
globalThis.clearTimeout = () => {};
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
const probe = `\nwindow.__probe = { get idx(){ return idx; }, get LETTERS(){ return LETTERS; }, get done(){ return done; }, get prog(){ return prog; }, setProg(v){ prog=v; }, get MASTERY(){ return MASTERY; } };`;
new Function(blocks.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();

const F = globalThis.__field, P = globalThis.__probe;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const fresh = () => { timers = []; F.restart(); F.quench(); F.fill(99); T += 100; };   // a full bag of 気: these checks are about the lights, not the fuel
const advance = (ms, stepMs = 16) => {
  for (let e = T + ms; T < e; ){
    T = Math.min(T + stepMs, e);
    const due = timers.filter(t => t.at <= T);
    timers = timers.filter(t => t.at > T);
    for (const d of due) d.fn();
    F.frame(T);
  }
};
const carried = m => P.LETTERS[m.i][0];
const kanaOf = m => m.w.chars[m.ci];

ok(F && P, 'the field layer did not initialise');
if (!F || !P) process.exit(1);
const cfgSrc = html.match(/window\.__FIELD_CFG=(\{[\s\S]*?\});<\/script>/)[1];
const cfg = Object.fromEntries([...cfgSrc.matchAll(/,([a-zA-Z]+):(-?[\d.]+|true|false|"[^"]*")/g)]
  .map(m => [m[1], /^[\d.-]/.test(m[2]) ? Number(m[2]) : m[2] === 'true' ? true : m[2] === 'false' ? false : m[2].slice(1,-1)]));

// ---- the deck is in the page and every kana of every word has strokes
{
  ok(Array.isArray(F.words) && F.words.length > 50, `the roster is ${F.words ? F.words.length : 'no'} words`);
  const missing = new Set();
  for (const w of F.words) for (const c of w.ja) if (F.at[c] === undefined) missing.add(c);
  ok(!missing.size, `words use characters the tracer cannot load: ${[...missing].join('')}`);
  ok(F.words.every(w => w.romaji && w.en), 'a word lacks its reading or its meaning');
  const seen = new Set(); ok(F.words.every(w => !seen.has(w.ja) && seen.add(w.ja)), 'a word is on the roster twice');
}

// ---- a monster carries a word, and the tracer is on its first kana
fresh();
{
  const m = F.target;
  ok(m && m.w, 'the target carries no word');
  ok(m.ci === 0 && P.idx === F.at[m.w.chars[0]], `the tracer is on ${carried(m)}, not the first kana of ${m.w.ja}`);
  ok(m.i === F.at[kanaOf(m)], 'the monster\'s i is not the kana it is waiting for');
}

// ---- a finished kana advances the word, keeps the lock, knocks it back, and does not kill
fresh();
{
  const m = F.target, n = m.w.chars.length, k0 = F.killed, d0 = m.d;
  for (const o of F.monsters) if (o !== m) o.d = 0.3;   // the others closer, so a lost lock would show
  m.d = 0.8;
  globalThis.conjure();
  ok(m.ci === 1, `after one kana the word is at ${m.ci}, expected 1`);
  ok(n === 1 || m.i === F.at[m.w.chars[1]], 'the monster did not move on to its second kana');
  ok(F.shots.length === 1 && F.shots[0].to === m && F.shots[0].partial === (n > 1), 'no partial shot at the word\'s own monster');
  advance(cfg.advanceMs + 120);
  if (n > 1){
    ok(F.killed === k0 && F.monsters.includes(m), 'one kana banished a whole word');
    // The lock holds while the next kana is dark. If it is the same kana
    // again it was just lit, and the hand is rightly sent elsewhere.
    if (m.w.chars[1] !== m.w.chars[0]){
      ok(F.target === m, 'the lock let go of a half-written word whose next kana is dark');
      ok(P.idx === m.i && P.idx === F.at[m.w.chars[1]], `the tracer is on ${P.LETTERS[P.idx][0]}, not the second kana of ${m.w.ja}`);
    }
    ok(m.d > 0.8 - 0.01 && m.d >= 0.8 + cfg.knockback - 0.03, `the farang was not knocked back (d ${m.d.toFixed(3)} from 0.8, knockback ${cfg.knockback})`);
    ok(F.charge(m.w.chars[0]) === cfg.hitodamaGain + cfg.cleanBonus, `the kana just written holds ${F.charge(m.w.chars[0])} lights, expected ${cfg.hitodamaGain + cfg.cleanBonus}`);
    ok(!(m.w.ja in F.hitodama), 'a light was kept by the word: nothing can spend it');
  }
}

// ---- the whole word, by hand, banishes it, blooms its reading, and lights every kana in it
// Quenched after each kana so this stays about the hand: a light just lit
// would otherwise write a repeated kana, or somebody else's, before the pen.
fresh();
{
  const m = F.target, n = m.w.chars.length, k0 = F.killed;
  for (let k = 0; k < n; k++){
    ok(P.idx === F.at[m.w.chars[k]], `kana ${k} of ${m.w.ja}: tracer on ${P.LETTERS[P.idx][0]}`);
    globalThis.conjure();
    ok(F.charge(m.w.chars[k]) >= cfg.hitodamaGain + cfg.cleanBonus, `kana ${k} of ${m.w.ja} was written cleanly and holds ${F.charge(m.w.chars[k])} lights`);
    F.quench();
    advance(cfg.advanceMs + 120);
  }
  ok(F.killed === k0 + 1, `the whole word did not banish its farang (killed ${F.killed - k0})`);
  ok(!F.monsters.includes(m), 'the banished farang is still on the field');
  const r = F.readings[F.readings.length - 1];
  // (piano is "piano" in both voices; only ask for two different halves when there are two)
  ok(r && [m.w.en, m.w.romaji].includes(r.text) && [m.w.en, m.w.romaji].includes(r.sub) && (r.text !== r.sub || m.w.en === m.w.romaji),
     `the bloom shows ${r ? JSON.stringify([r.text, r.sub]) : 'nothing'}, expected the reading and the meaning`);
  ok(F.sign === 'romaji' ? r.text === m.w.en : r.text === m.w.romaji, 'the bloom leads with the half the sign already said');
  ok(F.target && P.idx === F.target.i, 'after the word the tracer is not on the next target');
}

// ---- a zap costs the clean bonus of the kana it happened in, and no other
fresh();
{
  const m = F.target;
  globalThis.zap({x:10, y:10});
  globalThis.conjure();
  ok(F.charge(m.w.chars[0]) === cfg.hitodamaGain, `a zapped kana holds ${F.charge(m.w.chars[0])} lights, expected ${cfg.hitodamaGain}`);
  if (m.w.chars.length > 1 && m.w.chars[1] !== m.w.chars[0]){
    advance(cfg.advanceMs + 120);
    globalThis.conjure();
    ok(F.charge(m.w.chars[1]) === cfg.hitodamaGain + cfg.cleanBonus, 'a zap in the first kana cost the second its clean bonus');
  }
}

// ---- a kana nobody is waiting for hits nothing and advances nothing
// The single-character game falls back to the locked monster when nothing
// carries what was drawn. A word must not: its farang only ever takes its
// own next kana, or a stray character would count as part of the word.
fresh();
{
  const m = F.target, first = m.w.chars[0];
  globalThis.conjure();                 // the first kana: the farang moves on to its second
  const shots0 = F.shots.length, ci0 = m.ci;
  globalThis.conjure();                 // the same kana again, before the tracer has advanced
  const twin = F.monsters.some(o => o !== m && carried(o) === first);
  if (!twin) ok(F.shots.length === shots0 && m.ci === ci0, 'a kana nobody is waiting for advanced a word or fired');
}

// ---- the arsenal: a word is answered by the lights of its own kana, in order
// The idle half of the game, and the rule it must not break: a light writes
// the kana a farang is waiting on and no other. A word with a dark kana in it
// stops there and waits for the hand, however much is lit behind the gap.
// exactly three, all different: one to light, one to leave dark, one lit behind the gap
const distinct = F.words.find(w => w.chars.length === 3 && new Set(w.chars).size === 3);
ok(distinct, 'no word of three different kana on the roster to test the arsenal with');
const carry = (m, w) => { m.w = w; m.ci = 0; m.i = F.at[w.chars[0]]; m.d = 0.9; m.speed = 0; m.hp = 1; };
if (distinct){
  // every kana lit: the farang is written away with no hand at all
  fresh();
  for (const o of F.monsters.slice(1)) o.d = 2;          // out of the way; one farang, one question
  const m = F.monsters[0]; carry(m, distinct);
  for (const o of F.monsters) if (o !== m) F.monsters.splice(F.monsters.indexOf(o), 1);
  for (const c of distinct.chars) F.kindle(c, 1);
  const k0 = F.killed, d0 = m.d;
  advance(100);
  const first = F.shots.find(s => s.auto);
  ok(first && first.to === m && first.partial === true && first.ch === distinct.chars[0], 'the first light did not write the first kana');
  ok(m.ci === 1 && m.i === F.at[distinct.chars[1]], 'a light did not move the word on to its next kana');
  advance(cfg.castMs * (distinct.chars.length + 1) + 1500);
  ok(F.killed === k0 + 1 && !F.monsters.includes(m), `a fully lit ${distinct.ja} was not written away by its own lights (stuck at ${m.ci})`);
  ok(distinct.chars.every(c => F.charge(c) === 0), 'a light was not spent for every kana written');
  ok(!(distinct.ja in F.hitodama), 'something was kept by the word');

  // a hole in the middle: the lights stop at it, and what is lit behind it waits
  fresh();
  const h = F.monsters[0]; carry(h, distinct);
  for (const o of [...F.monsters]) if (o !== h) F.monsters.splice(F.monsters.indexOf(o), 1);
  F.kindle(distinct.chars[0], 1); F.kindle(distinct.chars[2], 1);      // 1 is dark
  advance(cfg.castMs * 5 + 1500);
  ok(h.ci === 1, `with its second kana dark the word got to slot ${h.ci}; a light skipped the gap or never flew`);
  ok(F.charge(distinct.chars[2]) === 1, 'the light behind the gap was spent out of order');
  ok(F.monsters.includes(h), 'a word with a dark kana was banished without the hand');
  ok(F.target === h && P.idx === F.at[distinct.chars[1]], `the pen was not sent to the hole: tracer on ${P.LETTERS[P.idx][0]}, the dark kana is ${distinct.chars[1]}`);
  // the hand fills the hole, and the light behind it finishes the word
  const k1 = F.killed;
  globalThis.conjure();
  ok(h.ci === 2, 'the hand did not fill the hole');
  advance(cfg.advanceMs + cfg.castMs * 3 + 1500);
  ok(F.killed === k1 + 1, 'after the hand filled the hole the waiting light did not finish the word');

  // a light does not shove a word back: only the hand does, or there is no clock
  fresh();
  const s = F.monsters[0]; carry(s, distinct); s.d = 0.5;
  for (const o of [...F.monsters]) if (o !== s) F.monsters.splice(F.monsters.indexOf(o), 1);
  F.kindle(distinct.chars[0], 1);
  advance(1200);
  ok(s.ci === 1 && Math.abs(s.d - 0.5) < 1e-9, `a light knocked the farang back to ${s.d}`);

  // the lights do not write the kana the hand is in the middle of
  fresh();
  const y = F.monsters[0]; carry(y, distinct);
  for (const o of [...F.monsters]) if (o !== y) F.monsters.splice(F.monsters.indexOf(o), 1);
  F.retarget(true);
  F.touch();                                   // a pen on the pad
  F.kindle(distinct.chars[0], 2);
  advance(Math.min(cfg.holdMs - 100, cfg.castMs + 200));
  ok(y.ci === 0, 'a light wrote the kana the pen was already on, and changed the glyph under it');
}

// ---- lights kept by word before v0.1.40 are dropped, and only those
{
  ok(/\[\.\.\.k\]\.length > 1\) delete HITODAMA\[k\]/.test(html), 'old word-keyed lights are not cleaned out on load');
}

// ---- the sign speaks for words in all three voices
fresh();
{
  const m = F.target;
  ok(F.setSign('kana') && F.signOf(m) === m.w.ja, 'kana sign is not the word');
  ok(F.setSign('romaji') && F.signOf(m) === m.w.romaji, 'romaji sign is not the reading');
  ok(F.setSign('gaijin') && F.signOf(m) === m.w.en, 'gaijin sign is not the farang\'s own word');
  F.setSign(cfg.sign);
  F.openStart();
  ok(/katakana/.test(F.startHtml), 'the start page does not name the realm');
  ok(/koohii|coffee/.test(F.startHtml), 'the sign blurbs still talk about single characters');
  ok(!/href="hiragana-game\.html"/.test(F.startHtml), 'the start page still links to another realm: the front page is the level switcher');
  F.begin();
}

// ---- tapping another farang mid-word keeps that word's progress
fresh();
{
  F.spawn();
  const a = F.target, b = F.monsters.find(o => o !== a);
  // A known word, and the lights put out after the first kana: this is about
  // the tap, and a random word with a doubled kana would have its second slot
  // written by the light the first one just lit.
  if (b && distinct){
    carry(a, distinct); F.retarget(true);
    globalThis.conjure(); F.quench(); advance(cfg.advanceMs + 120);
    ok(a.ci === 1 && F.target === a, 'setup: the first kana did not stick');
    const p = F.posOf(b); F.pick(p.x, p.y-14);
    ok(F.target === b && P.idx === b.i, 'the tap did not move the lock to the other word');
    ok(a.ci === 1, 'switching away lost the first word\'s progress');
    const q = F.posOf(a); F.pick(q.x, q.y-14);
    ok(F.target === a && P.idx === F.at[a.w.chars[1]], 'coming back did not resume at the second kana');
  }
}

// ---- a deck is not staged: it is class content with its own order
fresh();
{
  ok(F.rowsOpen() === Infinity && F.roster().length === P.LETTERS.length, 'the word game put a row gate on a deck');
  for (let k = 0; k < 12; k++) F.spawn();
  ok(!F.bossAlive(), 'a deck run has a boss: a word is long enough');
}

if (fail){ console.log(`  ${fail} failure(s) in ${target}`); process.exit(1); }
console.log('  the farang carry words: a kana advances and knocks back, the last one banishes, every kana written is lit, a word is written away by the lights of its own kana in order and stops at a dark one, and the sign has three voices');
