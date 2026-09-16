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
const fresh = () => { timers = []; F.restart(); F.quench(); T += 100; };
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
    ok(F.target === m, 'the lock let go of a half-written word');
    ok(P.idx === m.i && P.idx === F.at[m.w.chars[1]], `the tracer is on ${P.LETTERS[P.idx][0]}, not the second kana of ${m.w.ja}`);
    ok(m.d > 0.8 - 0.01 && m.d >= 0.8 + cfg.knockback - 0.03, `the farang was not knocked back (d ${m.d.toFixed(3)} from 0.8, knockback ${cfg.knockback})`);
    ok(F.charge(m.w.ja) === 0, 'a half-written word was kindled');
  }
}

// ---- the whole word banishes it, blooms its reading, and kindles the word
fresh();
{
  const m = F.target, n = m.w.chars.length, k0 = F.killed;
  for (let k = 0; k < n; k++){
    ok(P.idx === F.at[m.w.chars[k]], `kana ${k} of ${m.w.ja}: tracer on ${P.LETTERS[P.idx][0]}`);
    globalThis.conjure();
    advance(cfg.advanceMs + 120);
  }
  ok(F.killed === k0 + 1, `the whole word did not banish its farang (killed ${F.killed - k0})`);
  ok(!F.monsters.includes(m), 'the banished farang is still on the field');
  const r = F.readings[F.readings.length - 1];
  ok(r && [m.w.en, m.w.romaji].includes(r.text) && [m.w.en, m.w.romaji].includes(r.sub) && r.text !== r.sub,
     `the bloom shows ${r ? JSON.stringify([r.text, r.sub]) : 'nothing'}, expected the reading and the meaning`);
  ok(F.sign === 'romaji' ? r.text === m.w.en : r.text === m.w.romaji, 'the bloom leads with the half the sign already said');
  ok(F.charge(m.w.ja) >= 2, `a clean word kindled ${F.charge(m.w.ja)}, expected the gain plus the clean bonus`);
  ok(!(m.w.chars[0] in F.hitodama), 'the ghost light was kept by the first kana rather than the word');
  ok(F.target && P.idx === F.target.i, 'after the word the tracer is not on the next target');
}

// ---- a zap anywhere in the word costs the clean bonus
fresh();
{
  const m = F.target, n = m.w.chars.length;
  globalThis.zap({x:10, y:10});
  for (let k = 0; k < n; k++){ globalThis.conjure(); advance(cfg.advanceMs + 120); }
  ok(F.charge(m.w.ja) === cfg.hitodamaGain, `a zapped word kindled ${F.charge(m.w.ja)}, expected ${cfg.hitodamaGain}`);
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

// ---- a lit word answers its own farang, whole
fresh();
{
  F.spawn(); F.spawn();
  const m = F.monsters[F.monsters.length - 1];
  for (const o of F.monsters) if (o !== m) { const p = F.posOf(o); F.pick(p.x, p.y-14); break; }
  F.kindle(m.w.ja, 2);
  const k0 = F.killed;
  advance(100);
  const auto = F.shots.find(s => s.auto);
  ok(auto && auto.to === m && !auto.partial, 'a lit word did not throw a whole wisp at its farang');
  ok(F.charge(m.w.ja) === 1, `the cast spent ${2 - F.charge(m.w.ja)}, expected 1`);
  advance(600);
  ok(F.killed === k0 + 1 && !F.monsters.includes(m), 'the wisp did not banish the word');
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
  ok(/href="hiragana-game\.html"/.test(F.startHtml), 'no way back to the hiragana game');
  F.begin();
}

// ---- tapping another farang mid-word keeps that word's progress
fresh();
{
  F.spawn();
  const a = F.target, b = F.monsters.find(o => o !== a);
  if (b && a.w.chars.length > 1){
    globalThis.conjure(); advance(cfg.advanceMs + 120);
    ok(a.ci === 1 && F.target === a, 'setup: the first kana did not stick');
    const p = F.posOf(b); F.pick(p.x, p.y-14);
    ok(F.target === b && P.idx === b.i, 'the tap did not move the lock to the other word');
    ok(a.ci === 1, 'switching away lost the first word\'s progress');
    const q = F.posOf(a); F.pick(q.x, q.y-14);
    ok(F.target === a && P.idx === F.at[a.w.chars[1]], 'coming back did not resume at the second kana');
  }
}

if (fail){ console.log(`  ${fail} failure(s) in ${target}`); process.exit(1); }
console.log('  the farang carry words: a kana advances and knocks back, the last one banishes, the word is what is kindled, and the sign has three voices');
