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
const probe = `\nwindow.__probe = { get idx(){ return idx; }, get LETTERS(){ return LETTERS; }, get prog(){ return prog; }, setProg(v){ prog=v; }, get done(){ return done; }, get strokes(){ return strokes; }, get PATH(){ return PATH; } };`;
new Function(blocks.map(b => b + bridgeFor(b)).join('\n;\n') + probe)();

const F = globalThis.__field, P = globalThis.__probe;
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
// Restart the run AND the clock. conjure() queues a forced advance on a timer,
// and one left over from an earlier block will fire inside a later one and
// force exactly the reload that block is checking does not happen. This cost
// a wrong diagnosis once already.
// Quench the ghost lights too: a lit character answers its own monsters, and
// a charge left over from an earlier block would kill something a later block
// is counting on to still be there.
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

// ---- the workshop's practice controls and hint are gone from the game
ok(/body\.field[^{]*\.only-p[^{]*\{ display:none/.test(html),
   'the practice row (Back/Clear/Next, Watch teacher) is showing in the game');
ok(/body\.field[^{]*\.hint[^{]*\{ display:none/.test(html), 'the "Easy mode" hint is showing in the game');

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
fresh();
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
// By character, not identity: a finished glyph hits whichever monster carries
// it, nearest first, and the spawn is random enough that one of the shoved
// monsters carries the same character every twenty runs or so.
ok(F.shots.length === 1 && P.LETTERS[F.shots[0].to.i][0] === P.LETTERS[mine.i][0],
   'the shot went to a monster other than the one whose glyph was traced');

// ---- tapping picks a different one
fresh();
F.spawn(); F.spawn();
const other = F.monsters.find(m => m !== F.target);
if (other){
  const p = F.posOf(other);
  ok(F.pick(p.x, p.y - 14), 'tapping a monster did not select it');
  ok(F.target === other, 'tap did not move the lock');
  ok(P.idx === other.i, 'tap did not point the tracer at the tapped monster');
}

// ---- the next glyph arrives promptly, not after the celebration
fresh();
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

// ---- two of the same in a row do not strand the tracer in its celebration
// retarget() used to return early whenever the target's glyph was already
// loaded, which after a conjure meant `done` stayed set until the engine's
// own 1.9s timer — dead time exactly when two monsters carrying the same
// character arrive together.
fresh();
{
  F.spawn();
  const twin = F.monsters.find(m => m !== F.target);
  if (twin){
    twin.i = F.target.i;
    // restart() leaves spawnAt at 0, so the first frame adds a third monster;
    // let it arrive, then send it away so only the twin can be next.
    advance(50);
    for (const m of [...F.monsters]) if (m !== F.target && m !== twin) F.monsters.splice(F.monsters.indexOf(m), 1);
    globalThis.conjure();
    // The conjure kindles the character, and a wisp would take the twin, empty
    // the field, and let the refill clear `done` for the wrong reason.
    F.quench();
    advance(cfg.advanceMs + 120);
    ok(!P.done, 'after a conjure the next target carried the same glyph and the tracer stayed in its celebration');
    ok(F.target && P.idx === F.target.i, 'the tracer is not on the twin');
  }
}

// ---- the cached trail is dropped when the glyph changes
// The cache is keyed on prog, and load() resets prog to 0 — so switching from
// a glyph that was also at 0 left the previous glyph's trail on screen until
// the first pen touch moved prog. An engine bug, visible in the workshop too.
ok(/prog=0; offCount=0; smudge=0; outCount=0; trailProg=-1;/.test(html),
   'load() does not reset trailProg — the previous glyph\'s trail survives the switch');

// ---- what was drawn decides what is hit
fresh();
F.spawn(); F.spawn(); F.spawn();
{
  const drew = P.LETTERS[P.idx][0];
  const carriers = F.monsters.filter(m => P.LETTERS[m.i][0] === drew);
  globalThis.conjure();
  ok(F.shots.length === 1, 'no shot fired');
  ok(P.LETTERS[F.shots[0].to.i][0] === drew,
     `drew ${drew} but the shot flew at a monster carrying ${P.LETTERS[F.shots[0].to.i][0]}`);
  ok(carriers.includes(F.shots[0].to), 'the shot picked a monster that is not carrying that glyph');
}

// ---- a retarget will not interrupt a trace in progress
fresh();
F.spawn();
{
  const held = P.idx;
  const victim = F.target;
  // simulate the player being mid-glyph, then a monster reaching the ward
  globalThis.__probe.setProg(5);
  for (const m of F.monsters) if (m === victim) m.d = 0.07;
  advance(400);
  ok(P.idx === held,
     'the glyph changed under a trace in progress — a swarm would wipe every attempt');
  ok(F.pending || P.idx === held, 'no retarget was queued for later');
  globalThis.__probe.setProg(0);
  advance(300);
}

// ---- a hand that has just touched the pad is still tracing
// prog > 0 misses the first stroke before it finds the path and a hand that
// has lifted to think. Both are when a wisp elsewhere, or a breach, would
// swap the glyph under a pen about to come back down.
fresh();
F.spawn();
{
  const held = P.idx, victim = F.target;
  ok(P.prog === 0 && P.strokes.length === 0, 'test setup: nothing traced yet');
  F.touch();
  victim.d = 0.07;
  advance(400);
  ok(P.idx === held, 'the glyph changed within holdMs of the pen touching the pad');
  advance(cfg.holdMs + 400);
  if (F.target) ok(P.idx === F.target.i, 'the deferred retarget never applied once the hand was gone');
}

// ---- a stroke that never found the path is erased on pen-up
fresh();
{
  ok(P.PATH.length > 0, 'test setup: the tracer has no path loaded');
  P.strokes.push([{x:5,y:5,on:false},{x:9,y:9,on:false},{x:14,y:12,on:false}]);
  ok(F.tidy() > 0 && P.strokes.length === 0, 'a wholly stray stroke was left on the board');
  // an overdrawn line: on the path for a while, then wandering. The wander
  // goes, the good run stays, and nothing joins across the gap.
  P.strokes.push([{x:1,y:1,on:false},{x:5,y:5,on:true},{x:9,y:9,on:true},{x:14,y:12,on:false},{x:20,y:20,on:false}]);
  ok(F.tidy() === 3, 'the off-path runs of a mixed stroke were not erased');
  ok(P.strokes.length === 1 && P.strokes[0].length === 2 && P.strokes[0].every(q => q.on),
     `after tidy the board holds ${JSON.stringify(P.strokes)}, expected only the on-path run`);
  P.strokes.length = 0;
  P.strokes.push([{x:5,y:5,on:true},{x:9,y:9,on:true}]);
  ok(F.tidy() === 0 && P.strokes.length === 1, 'a clean stroke was touched');
  P.strokes.length = 0;
}

// ---- ink thins with the glyph
// A fixed 9px line on a 115px glyph buried the four small strokes of ふ
// under their own ink. Not observable in a stubbed canvas, so a lint on the
// built source: the width and the glow both follow the size factor.
{
  ok(/const widthFor=p=>\(3\+p\*13\)\*inkK\(\)/.test(html), 'ink width does not follow the glyph size');
  ok(/ctx\.shadowBlur=\(opt\.blur\?\?14\)\*inkK\(\)/.test(html), 'ink glow does not follow the glyph size');
}

// ---- an emptied field refills, and the tracer wakes up with it
// The freeze: after a conjure prog sits at the end of the last stroke, so a
// tracing() guard without a `done` clause stayed true forever. The deferred
// retarget never ran and the tracer was stranded on the celebration of a glyph
// nothing was carrying.
fresh();
{
  // The reported freeze, reproduced exactly: the field runs dry at the moment
  // a glyph is finished. conjure() leaves done=true with prog at the end of
  // the last stroke; the forced advance then finds nothing to target and gives
  // up, and nothing ever asks again. The tracer sits on the celebration of a
  // character nothing is carrying.
  //
  // prog is set by hand because nothing traced here — in play the pen has
  // already driven it to the stroke end, and that is the state that sticks.
  // Let the field settle first: restart() leaves spawnAt at 0, so without a
  // frame or two the very next one spawns no matter what, and the dry field
  // never actually happens.
  advance(200);
  P.setProg(9);
  globalThis.conjure();
  ok(P.done, 'conjure did not mark the attempt done');
  ok(P.prog > 0, 'prog was cleared — this test is not reproducing the freeze');
  F.monsters.length = 0;
  advance(2500);
  ok(F.monsters.length >= 1,
     'an empty field did not refill within 2.5s — a dead screen, not a rest');
  ok(!P.done, 'still celebrating after 2.5s — the tracer is frozen');
  ok(F.target && P.idx === F.target.i,
     `tracer stuck on ${P.LETTERS[P.idx][0]} while the target carries `
     + `${F.target ? P.LETTERS[F.target.i][0] : '-'}`);
}

// ---- the reading is shown when a monster falls
fresh();
{
  const before = F.readings.length;
  globalThis.conjure();
  advance(500);
  ok(F.readings.length > before, 'no reading shown on a kill — the sound never arrives');
  const r = F.readings[F.readings.length-1];
  ok(r && /^[a-z]+$/.test(r.text),
     `reading is ${r ? JSON.stringify(r.text) : 'absent'}, expected romaji`);
  // and the way you probably said it, underneath
  ok(r && typeof r.sub === 'string' && /^[A-Z-]+$/.test(r.sub),
     `no gaijin reading under it (got ${r ? JSON.stringify(r.sub) : 'nothing'})`);
}

// ---- every glyph has all three voices, and they are distinct
{
  const L = P.LETTERS;
  const missing = L.filter(e => !e[7]);
  ok(!missing.length, `${missing.length} glyph(s) have no gaijin reading`);
  const same = L.filter(e => e[7] && e[7].toLowerCase() === e[2].toLowerCase());
  ok(same.length < L.length,
     'every gaijin reading is just the romaji uppercased — the joke is not there');
  ok(L.every(e => !e[7] || /^[A-Z-]+$/.test(e[7])),
     'a gaijin reading is not in the shouty caps the joke depends on');
}

// ---- a fizzle puts the glyph back to the start
fresh();
{
  P.setProg(9);
  globalThis.fizzle();
  advance(400);
  ok(P.prog === 0, `after a fizzle prog is ${P.prog} — the glyph did not restart`);
}

// ---- hitodama: a traced character lights, and a lit character defends itself
// The idle economy's potency stat with teeth: every trace kindles the
// character, and a lit character throws its own wisp at any monster carrying
// it, spending one charge per cast. The hand is pushed toward the characters
// whose flame is out, which are exactly the ones that need practice.
fresh();
{
  const drew = P.LETTERS[P.idx][0];
  ok(F.charge(drew) === 0, 'a fresh run starts with a lit character');
  globalThis.conjure();
  const clean = F.charge(drew);
  ok(clean >= 1, `tracing ${drew} left its charge at ${clean} — nothing was kindled`);
  advance(cfg.advanceMs + 600);
  // a scrappy trace pays less than a clean one
  F.quench();
  const drew2 = P.LETTERS[P.idx][0];
  globalThis.zap({x:10, y:10});
  globalThis.conjure();
  ok(F.charge(drew2) < clean,
     `a zapped trace kindled ${F.charge(drew2)}, a clean one ${clean} — clean does not pay more`);
  advance(cfg.advanceMs + 600);
}

// a lit character answers its own monster, without the pen
fresh();
{
  F.spawn(); F.spawn();
  const m = F.monsters[F.monsters.length - 1];
  const ch = P.LETTERS[m.i][0];
  // point the tracer somewhere else so the lock is not on this one
  for (const o of F.monsters) if (o !== m) { const p = F.posOf(o); F.pick(p.x, p.y-14); break; }
  F.kindle(ch, 2);
  const c0 = F.charge(ch), k0 = F.killed;
  // The wisp lands at ~385ms and is gone from `shots` once it has. Look for it
  // while it is still in the air — asserting on it after a full second is the
  // same mistake the shot-timing test made once already.
  advance(100);
  const auto = F.shots.find(s => s.auto);
  ok(auto, 'a lit character did not throw a wisp at its own monster');
  ok(!auto || P.LETTERS[auto.to.i][0] === ch, 'the wisp flew at a monster carrying a different character');
  ok(F.charge(ch) === c0 - 1, `the cast spent ${c0 - F.charge(ch)} charge(s), expected 1`);
  advance(600);
  ok(F.killed === k0 + 1, 'the wisp did not banish the monster');
}

// an unlit character does not, and the pen is pointed at it
// The lock holds through a retarget, so nearest() is only consulted once the
// lock is gone: let the current target breach the ward, with a lit monster
// nearer than an unlit one, and see which the tracer is pointed at after.
fresh();
{
  F.spawn(); F.spawn(); F.spawn();
  const A = F.target;
  const [B, C] = F.monsters.filter(m => m !== A);
  if (B && C && P.LETTERS[B.i][0] !== P.LETTERS[C.i][0]){
    B.d = 0.5; C.d = 0.8;
    F.kindle(P.LETTERS[B.i][0], 3);
    A.d = 0.07;
    advance(300);   // ~180ms to close from 0.07 to the 0.06 breach line
    ok(!F.monsters.includes(A), 'test setup: the old target should have breached');
    ok(F.target === C,
       `after the breach the tracer went to ${F.target === B ? 'the lit, nearer' : 'an unexpected'} monster, not the unlit one`);
  }
  const dark = F.target;
  if (F.charge(P.LETTERS[dark.i][0]) === 0){
    advance(cfg.castMs * 3);
    ok(F.monsters.includes(dark) || F.ward < cfg.wardHp,
       'an unlit monster was banished without a trace');
    ok(!F.shots.some(s => s.auto && s.to === dark), 'a wisp flew at an unlit character');
  }
}

// the one under the pen is yours: no wisp at the locked target mid-trace
fresh();
{
  const mine = F.target;
  const ch = P.LETTERS[mine.i][0];
  F.kindle(ch, 3);
  P.setProg(4);
  advance(cfg.castMs * 2 + 100);
  ok(F.monsters.includes(mine) && !F.shots.some(s => s.auto && s.to === mine),
     'a wisp took the monster the hand was answering');
  P.setProg(0);
}

// the charge is capped
fresh();
{
  F.kindle('あ', 999);
  ok(F.charge('あ') === cfg.hitodamaCap, `charge went to ${F.charge('あ')}, cap is ${cfg.hitodamaCap}`);
}

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
fresh();
const victim = F.target, before = F.killed;
ok(victim, 'no target after restart');
globalThis.conjure();
// The conjure also kindles the character, and every forty runs or so a second
// monster carries it and a wisp would make this two banishments, not one.
F.quench();
ok(F.shots.length === 1, `conjure fired ${F.shots.length} shots, expected 1`);
ok(F.shots[0].to === victim, 'the shot is aimed at something other than the target');
advance(1200);
ok(F.killed === before + 1, `killed went ${before} -> ${F.killed}, expected one banishment`);
ok(!F.monsters.includes(victim), 'the monster survived a completed glyph');

// ---- and the tracer moves to whatever is next
if (F.target) ok(P.idx === F.target.i,
  'after a kill the tracer is still on the dead monster\'s glyph');

// ---- a monster that arrives costs the ward
fresh();
const w0 = F.ward;
for (const m of F.monsters) m.d = 0.07;
advance(500);
ok(F.ward < w0, `a monster reached the centre and the ward stayed at ${w0}`);

// ---- and the ward can fall
fresh();
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
