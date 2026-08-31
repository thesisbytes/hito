/**
 * The game loop, driven rather than looked at.
 *
 * The field is where the tracer stops being the whole program: monsters move
 * on a clock, the tracer is pointed at whichever one is most urgent, and a
 * finished glyph has to actually reach and remove it. None of that is visible
 * to a smoke run, which only proves the first frame did not throw.
 *
 * The specific thing being defended is the seam. The field drives the tracer
 * through load() and reads its result through conjure(); if that seam slips,
 * the game and the workshop disagree about which glyph is being asked for,
 * and the player traces one character to kill a monster carrying another.
 *
 *   node build/test/field.test.mjs dist/hiragana-game-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const html = readFileSync(target, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);

let raf = [], T = 0;
const ctx = new Proxy({}, { get: () => function(){ return {data:new Uint8ClampedArray(4)}; }, set: () => true });
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
// A real timer queue on the fake clock: the field advances to the next glyph
// on a setTimeout, and a stub that drops callbacks would let a broken advance
// pass silently.
let timers = [];
globalThis.setTimeout = (fn, ms) => { timers.push({fn, at: T + (ms||0)}); return timers.length; };
globalThis.setInterval = () => 0;
globalThis.clearTimeout = () => {};
globalThis.URL = { createObjectURL:()=>"" };
globalThis.Blob = class {};
globalThis.localStorage = { getItem:()=>null, setItem(){}, removeItem(){} };
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
const probe = `\nwindow.__probe = { get idx(){ return idx; }, get LETTERS(){ return LETTERS; } };`;
new Function(blocks.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();

const F = globalThis.__field, P = globalThis.__probe;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const advance = (ms, stepMs = 16) => {
  for (let e = T + ms; T < e; ){
    T = Math.min(T + stepMs, e);
    const due = timers.filter(t => t.at <= T);
    timers = timers.filter(t => t.at > T);
    for (const d of due) d.fn();
    F.frame(T);
  }
};

ok(F && P, 'the field layer did not initialise');
if (!F || !P) process.exit(1);

// ---- the sketchbook stays square
// Not a style preference. norm() divides x by W and y by H separately, so on a
// rectangular stage every distance in normalised space becomes anisotropic —
// tolerance, coverage radius and travel ratio all stop meaning one thing, and
// the pen gets forgiven more sideways than vertically. This is a lint on the
// built CSS because the geometry itself is not observable in a stubbed DOM.
const stageCss = html.match(/body\.field \.stage\{([^}]*)\}/);
ok(stageCss, 'no body.field .stage rule — the shell is not sizing the sketchbook');
if (stageCss){
  ok(/aspect-ratio:\s*1/.test(stageCss[1]),
     'the sketchbook is not square: norm() is anisotropic on a rectangular stage');
  ok(!/aspect-ratio:\s*auto/.test(stageCss[1]), 'the square aspect ratio is explicitly disabled');
}

// ---- the field starts with something to fight, and the tracer is on it
ok(F.monsters.length >= 1, 'no monster at boot — there is nothing to answer');
ok(F.target, 'no target chosen');
ok(P.idx === F.target.i,
   `the tracer is on ${P.LETTERS[P.idx][0]} but the target carries ${P.LETTERS[F.target.i][0]}`);

// ---- the redirect itself, not just the boot state
// retarget() calls the unwrapped load directly, so idx matching the target at
// boot proves nothing about the wrapper. What the wrapper is for is every load
// the *engine* initiates on its own — conjure()'s delayed load(idx+1), the
// clear button, a mode change. Those must land on what the field is asking
// for, or the player traces one character to kill a monster carrying another.
const away = (F.target.i + 7) % P.LETTERS.length;
globalThis.load(away);
ok(P.idx === F.target.i,
   `load(${away}) landed on ${P.LETTERS[P.idx][0]}, not the target's `
   + `${P.LETTERS[F.target.i][0]} — the field is not driving the tracer`);

// ---- the target is locked, not recomputed
// The bug this replaces: target() returned whichever monster was nearest the
// ward at that instant, so one overtaking yours mid-glyph stole the shot. You
// drew one character and something carrying another died for it.
F.restart(); T += 100;
F.spawn(); F.spawn();
const mine = F.target;
ok(mine, 'no target to lock');
// shove every other monster past it — under the old code this would retarget
for (const m of F.monsters) if (m !== mine) m.d = 0.2;
mine.d = 0.9;
advance(300);
ok(F.target === mine,
   'the target changed while it was being answered — a closer monster stole it');
ok(P.idx === mine.i, 'the tracer followed the thief instead of the locked target');
globalThis.conjure();
ok(F.shots.length === 1 && F.shots[0].to === mine,
   'the shot went to a monster other than the one whose glyph was traced');

// ---- tapping picks a different one
F.restart(); T += 100;
F.spawn(); F.spawn();
const other = F.monsters.find(m => m !== F.target);
if (other){
  const p = F.posOf(other);
  ok(F.pick(p.x, p.y - 14), 'tapping a monster did not select it');
  ok(F.target === other, 'tap did not move the lock');
  ok(P.idx === other.i, 'tap did not point the tracer at the tapped monster');
}

// ---- the next glyph arrives promptly, not after the celebration
F.restart(); T += 100;
const before2 = F.killed;
globalThis.conjure();
// the shot flies at t += dt*2.6, so it lands at ~385ms
advance(420);
ok(F.killed === before2 + 1, 'the shot had not landed by 420ms');
const cfg = JSON.parse(html.match(/window\.__FIELD_CFG=(\{[^}]*\})/)[1]
  .replace(/([a-zA-Z]+):/g, '"$1":'));
advance(cfg.advanceMs + 120);
ok(F.target && P.idx === F.target.i,
   `after ${cfg.advanceMs}ms the tracer is on ${P.LETTERS[P.idx][0]} `
   + `but the target carries ${F.target ? P.LETTERS[F.target.i][0] : '-'}`);
ok(cfg.advanceMs < 1900,
   `advance delay is ${cfg.advanceMs}ms — the engine's 1.9s celebration is dead time under a clock`);

// ---- monsters actually advance
const d0 = F.target.d;
advance(2000);
ok(F.monsters.length >= 1, 'the field emptied itself');
const still = F.monsters.find(m => m.d >= d0 - 1e-9 && m === F.target);
ok(!still, 'the target is not advancing — d did not decrease');

// ---- more of them arrive over time
const n1 = F.monsters.length;
advance(20000);
ok(F.monsters.length > n1 || F.ward < 5, `nothing spawned over 20s (still ${n1})`);

// ---- a finished glyph reaches the monster and removes it
F.restart(); T += 100;
const victim = F.target, before = F.killed;
ok(victim, 'no target after restart');
globalThis.conjure();
ok(F.shots.length === 1, `conjure fired ${F.shots.length} shots, expected 1`);
ok(F.shots[0].to === victim, 'the shot is aimed at something other than the target');
advance(1200);
ok(F.killed === before + 1, `killed went ${before} -> ${F.killed}, expected one banishment`);
ok(!F.monsters.includes(victim), 'the monster survived a completed glyph');

// ---- and the tracer moves to whatever is next
if (F.target) ok(P.idx === F.target.i,
  'after a kill the tracer is still on the dead monster\'s glyph');

// ---- a monster that arrives costs the ward
F.restart(); T += 100;
const w0 = F.ward;
for (const m of F.monsters) m.d = 0.07;
advance(500);
ok(F.ward < w0, `a monster reached the centre and the ward stayed at ${w0}`);

// ---- and the ward can fall
F.restart(); T += 100;
let guard = 0;
while (!F.over && guard++ < 400){ for (const m of F.monsters) m.d = 0.07; advance(200); }
ok(F.over, 'the ward never falls — there is no losing');
ok(F.ward <= 0, `run ended with ward ${F.ward}`);

// ---- and it can be started again
F.restart();
ok(!F.over && F.ward > 0 && F.monsters.length >= 1, 'restart did not begin a new run');

if (fail) { console.log(`  ${fail} field check(s) failed`); process.exit(1); }
console.log(`  monsters advance and spawn, a finished glyph banishes the target, `
  + `the tracer retargets, the ward falls and restarts`);
