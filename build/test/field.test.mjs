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
    }, set(t,k,v){ t[k]=v; return true; } });   // writes persist, as in dom.mjs: a `hidden` the shell sets is a `hidden` a test can read
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
const probe = `\nwindow.__probe = { get W(){ return W; }, get H(){ return H; }, get idx(){ return idx; }, get LETTERS(){ return LETTERS; }, get prog(){ return prog; }, setProg(v){ prog=v; }, get done(){ return done; }, get strokes(){ return strokes; }, get PATH(){ return PATH; }, get R_ON0(){ return R_ON0; }, get DRAIN(){ return DRAIN; }, get FIZZ(){ return FIZZ; }, get GUIDE_ON(){ return GUIDE_ON; }, get COMET_ON(){ return COMET_ON; }, get SHADOW_MODE(){ return SHADOW_MODE; }, get COVER_MIN(){ return COVER_MIN; }, get MAX_TRAVEL(){ return MAX_TRAVEL; }, get DOT_SCALE(){ return DOT_SCALE; }, get parts(){ return parts; }, get SIZE_PIN(){ return SIZE_PIN; }, get SIZE_MAX(){ return SIZE_MAX; }, get curF(){ return curF; }, get DRAG_FOLLOW(){ return DRAG_FOLLOW; }, get SEGS(){ return SEGS; }, get segIdx(){ return segIdx; }, get awaitLift(){ return awaitLift; }, get R(){ return R_ON(); }, setSeg(i){ segIdx=i; prog=SEGS[i][0]; awaitLift=false; segTravel=0; segBase=prog; segStarted=false; segNagged=false; }, denorm(q){ return denorm(q); }, follow(q,d){ return follow(q,d); }, get toast(){ return toast; }, setToast(f){ toast=f; } };`;
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

ok(F && P, 'the field layer did not initialise');
if (!F || !P) process.exit(1);
// The field's tuning, read off the page. The literal carries JSON strings
// (the credit line has colons in it), so the keys are picked individually.
const cfgSrc = html.match(/window\.__FIELD_CFG=(\{[\s\S]*?\});<\/script>/)[1];
const cfg = Object.fromEntries([...cfgSrc.matchAll(/([a-zA-Z]+):(-?[\d.]+|true|false|"[^"]*")/g)]
  .map(m => [m[1], /^[\d.-]/.test(m[2]) ? Number(m[2]) : m[2] === 'true' ? true : m[2] === 'false' ? false : m[2].slice(1,-1)]));

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

// ---- the start page: the field holds still, and difficulty is a switch
// Before any fresh(): restart() is what begins a run, and the point here is
// the state before one has begun.
{
  ok(F.paused, 'the field is running under the start page at boot');
  const d0 = F.target && F.target.d;
  advance(1500);
  ok(F.target && F.target.d === d0, 'monsters advance under the start page');
  const B = F.base;
  ok(B && B.R_ON0 > 0 && B.DRAIN > 0 && B.FIZZ > 0, 'the base penalties were not read off the engine');
  ok(F.setDifficulty('guided'), 'guided is not selectable');
  ok(P.DRAIN === 0 && P.FIZZ === Infinity && P.R_ON0 > B.R_ON0,
     `guided still punishes: drain ${P.DRAIN}, fizz ${P.FIZZ}, tolerance ${P.R_ON0} vs base ${B.R_ON0}`);
  ok(P.GUIDE_ON && P.SHADOW_MODE === 'none', 'guided lost the light it is named for');
  // the objective is the light: no coverage or travel test at the end, a
  // light big enough to hold, no zap, no ink
  ok(P.COVER_MIN === 0 && P.MAX_TRAVEL === Infinity, `guided still tests coverage ${P.COVER_MIN} / travel ${P.MAX_TRAVEL}`);
  ok(P.DOT_SCALE === 1, `the light in guided is ${P.DOT_SCALE}x — 'a giant circle', twice reported`);
  ok(!P.COMET_ON, 'the comet still loops in guided, setting a pace for the hand to chase');
  ok(P.SIZE_PIN === P.SIZE_MAX && P.curF === P.SIZE_MAX,
     `guided did not pin the size: pin ${P.SIZE_PIN}, glyph at ${P.curF}, largest is ${P.SIZE_MAX}`);
  ok(P.DRAG_FOLLOW === true && !F.casting(), 'guided is not dragging the light, or is still casting');
  ok(P.R_ON0 < B.R_ON0*2, 'guided tolerance is still doubled, which is what let a chord cut the curve');
  { const n = P.parts.length; globalThis.zap({x:10,y:10}); ok(P.parts.length === n, 'guided still zaps'); }
  ok(/window\.redrawInk = function/.test(html), 'the pen still leaves ink in guided (no redrawInk wrapper)');
  P.strokes.push([{x:1,y:1,on:false},{x:2,y:2,on:false}]);
  F.tidy(); ok(P.strokes.length === 0, 'guided keeps strokes on the board');
  ok(F.setDifficulty('medium'), 'medium is not selectable');
  ok(!P.GUIDE_ON && P.SHADOW_MODE === 'strokes' && P.DRAIN === B.DRAIN,
     'medium is not shape-only with the pack penalties');
  ok(!F.setDifficulty('hard'), 'hard is selectable, and there is no scorer for it');
  ok(F.difficulty === 'medium', 'a refused difficulty changed the current one');
  ok(!F.setDifficulty('easy'), 'easy is still selectable: it was removed, being guided with ink');
  ok(F.setDifficulty('medium') && P.R_ON0 === B.R_ON0 && P.DRAIN === B.DRAIN && P.FIZZ === B.FIZZ
     && !P.GUIDE_ON && P.SHADOW_MODE === 'strokes', 'medium did not restore the pack values');
  ok(P.COVER_MIN === B.COVER_MIN && P.MAX_TRAVEL === B.MAX_TRAVEL && P.DOT_SCALE === 1,
     'medium did not restore the end-of-glyph checks or the light');
  ok(P.SIZE_PIN === null, 'medium is still pinned to one size');
  ok(P.DRAG_FOLLOW === false && F.casting(), 'medium inherited guided\'s drag or lost its wisps');
  { const n = P.parts.length; globalThis.zap({x:10,y:10}); ok(P.parts.length > n, 'medium no longer zaps'); }
  // medium's shape is a flat centreline at the ink width, one path per
  // stroke — not the glowing shadow, and not the tolerance band, which was
  // a fifth of the glyph wide and unreadable as a shape
  ok(/SHADOW_MODE==='strokes'(?:\|\|SHADOW_MODE==='faint')?\)\{[^]*?g\.lineWidth=widthFor\(\.5\);[^]*?if\(SEGEND\.has\(i\)\)\{ g\.stroke\(\); open=false; \}/.test(html)
     && !/width:2\*R_ON\(\)\*W/.test(html),
     'medium does not draw the shape as a flat centreline, one path per stroke');
  ok(!/menu-btn/.test(html), 'the ☰ button is back');
  ok(F.setSign('romaji') && F.signOf(F.target) === P.LETTERS[F.target.i][2], 'the sign did not switch to romaji');
  ok(!F.setSign('klingon') && F.sign === 'romaji', 'an unknown sign voice was accepted');
  F.setSign('kana');
  F.begin();
  ok(!F.paused, 'begin did not start the field');
  const d1 = F.target && F.target.d;
  advance(500);
  ok(F.target && F.target.d < d1, 'the field is still frozen after begin');
  F.openStart();
  ok(F.paused, 'the menu did not pause the field');
  ok(!F.redoShown, 'the redo button is showing on the start page');
  F.openCredits();
  ok(F.view === 'credits', 'the credits page did not open');
  ok(/KanjiVG/.test(F.startHtml), 'the credits page does not carry the KanjiVG credit the licence requires');
  ok(/leans on/.test(F.startHtml), 'the credits page has lost the point of the name');
  F.openStart();
  ok(F.view === 'start', 'back from credits did not return to the start page');
  ok(!/href="vocab\.html"/.test(F.startHtml) && !/href="katakana-game\.html"/.test(F.startHtml), 'the start page still links to another realm: the front page is the level switcher');
  F.begin();
  ok(F.redoShown, 'the redo button did not come back for the run');
}

// ---- guided: the light is dragged, not chased
// Two reports from play, opposite faces of one rule. "I'm passing the stroke
// by cutting without finishing properly" — the nearest point within a window
// ahead, inside a doubled tolerance, is reachable from a chord. "The dot
// thinks I didn't finish and I have to poke it" — a fast pen outruns the
// window and the light lags until more samples arrive. Dragging: the light
// moves only while the pen is on it, forward through points the pen is near.
fresh();
F.setDifficulty('guided');
globalThis.resize();   // the harness stubs DOMContentLoaded, so W and H are 0 until this runs
// の: one long spiral, which bends away from its chord more than any
// tolerance. Loaded through the lock, since every load lands on the target.
F.ask(P.LETTERS.findIndex(l => l[0] === 'の'));
F.retarget(true);
{
  const R = P.R, den = P.denorm, fol = P.follow;
  // a stroke that bends more than R away from its own chord, so the chord
  // cannot be a legitimate way along it (a straight stroke's chord is the
  // stroke, and must pass)
  const offChord = (p, s0, e) => {
    const dx = e.x-s0.x, dy = e.y-s0.y, L2 = dx*dx+dy*dy || 1e-9;
    const t = Math.max(0, Math.min(1, ((p.x-s0.x)*dx + (p.y-s0.y)*dy)/L2));
    return Math.hypot(p.x - (s0.x+dx*t), p.y - (s0.y+dy*t));
  };
  let si = -1;
  for (let k = 0; k < P.SEGS.length; k++){
    const [a, b] = P.SEGS[k];
    if (P.PATH.slice(a, b).some(p => offChord(p, P.PATH[a], P.PATH[b]) > R*1.2)){ si = k; break; }
  }
  if (si >= 0){
    const [a, b] = P.SEGS[si];
    // the light does not move unless the pen is on it
    P.setSeg(si);
    let m = a; while (m < b && Math.hypot(P.PATH[m].x-P.PATH[a].x, P.PATH[m].y-P.PATH[a].y) < R*1.1) m++;
    fol(den(P.PATH[m]), true);
    ok(P.prog === a, `the light moved to ${P.prog} with the pen ${m-a} points ahead of it and out of reach`);
    // a chord from start to end does not finish the stroke
    P.setSeg(si);
    fol(den(P.PATH[a]), true);
    for (let t = 0.1; t <= 1.0001; t += 0.1)
      fol(den({x: P.PATH[a].x + (P.PATH[b].x-P.PATH[a].x)*t, y: P.PATH[a].y + (P.PATH[b].y-P.PATH[a].y)*t}));
    ok(P.prog < b - 1 && !P.awaitLift && !P.done, `a chord finished the stroke (prog ${P.prog} of ${b})`);
    // dragging along the path does, with nothing to poke
    P.setSeg(si);
    fol(den(P.PATH[a]), true);
    for (let i = a; i <= b; i += 2) fol(den(P.PATH[i]));
    fol(den(P.PATH[b]));
    ok(P.prog === b && (P.awaitLift || P.done), `dragging the light to the end did not finish the stroke (prog ${P.prog} of ${b})`);
    // the light rests under the pen, not at the far edge of the tolerance.
    // Dragged to the middle of the stroke, it is at the middle — not a
    // radius ahead — and a pen that stops a radius short of the end has
    // not finished the stroke. Reported from play: "the circle is way ahead
    // of my stylus and completes the strokes before I can".
    // (a fresh の: the drag above conjured it, and follow() does not check done)
    F.ask(P.LETTERS.findIndex(l => l[0] === 'の'));
    F.retarget(true);
    ok(!P.done && P.LETTERS[P.idx][0] === 'の', 'could not reload の for the resting-light check');
    P.setSeg(si);
    fol(den(P.PATH[a]), true);
    const mid = Math.floor((a+b)/2);
    for (let i = a; i <= mid; i += 2) fol(den(P.PATH[i]));
    fol(den(P.PATH[mid]));
    ok(Math.abs(P.prog - mid) <= 1, `the light ran ${P.prog - mid} points ahead of a pen resting at ${mid}`);
    let short = b; while (short > a && Math.hypot(P.PATH[short].x-P.PATH[b].x, P.PATH[short].y-P.PATH[b].y) < R) short--;
    for (let i = mid; i <= short; i += 2) fol(den(P.PATH[i]));
    fol(den(P.PATH[short]));
    ok(P.prog <= short + 1 && !P.awaitLift && !P.done, `the stroke closed with the pen ${b - short} points short of the end (prog ${P.prog} of ${b})`);
  } else ok(false, 'no stroke on this glyph is long enough to test a chord');
}

// ---- a stroke begins where it begins
// "Fu is cheatable. I can poke my stylus at the end of the tiny hooks and it
// completes them." ふ's ticks are 0.16 long at full size and half that at
// the smallest; the travel cap asks for 58% of that, and a jab with a wiggle
// covers it. So travel counts only once the pen has been near the stroke's
// start — a stroke has a start the way it has an end.
fresh(); F.setDifficulty('medium'); globalThis.resize();
F.ask(P.LETTERS.findIndex(l => l[0] === 'ふ'));
F.retarget(true);
ok(P.LETTERS[P.idx][0] === 'ふ' && !P.done, 'could not load ふ');
{
  const den = P.denorm, fol = P.follow, R = P.R;
  // the shortest stroke that is not the last (the last one ends the glyph
  // and drags coverage of the whole glyph into the question)
  let si = 0;
  for (let k = 1; k < P.SEGS.length - 1; k++) if (P.SEGS[k][1]-P.SEGS[k][0] < P.SEGS[si][1]-P.SEGS[si][0]) si = k;
  const [a, b] = P.SEGS[si], e = P.PATH[b];
  const notDone = (m) => ok(!P.awaitLift && !P.done && P.prog < b - 4, `${m} (prog ${P.prog} of ${a}..${b})`);
  // a jab at the end that skids back along the stroke
  P.setSeg(si);
  fol(den(e), true);
  for (let i = b - 1; i >= a && Math.hypot(P.PATH[i].x-e.x, P.PATH[i].y-e.y) < 0.05; i--) fol(den(P.PATH[i]));
  notDone('a jab at the end of a tick, skidding back along it, finished the stroke');
  // a jab at the end with a wiggle, which is more travel than the tick is long
  // the engine calls toast by its own name, so it is rebound from inside
  const _t = P.toast; let said = ''; P.setToast(m => { said = m; return _t(m); });
  P.setSeg(si);
  fol(den(e), true);
  for (let k = 0; k < 12; k++) fol(den({x: e.x + (k%2 ? .012 : -.012), y: e.y + (k%4 < 2 ? .012 : -.012)}));
  P.setToast(_t);
  notDone('a wiggle at the end of a tick finished the stroke');
  ok(/starts at the other end/.test(said), 'the pen at the end of an unbegun stroke was not told where it starts');
  // begun a little late, within the start tolerance, the stroke still finishes
  P.setSeg(si);
  let late = a; while (late < b && Math.hypot(P.PATH[late+1].x-P.PATH[a].x, P.PATH[late+1].y-P.PATH[a].y) < 0.018) late++;
  fol(den(P.PATH[late]), true);
  for (let i = late; i <= b; i++) fol(den(P.PATH[i]));
  ok(P.awaitLift, `a stroke begun ${late-a} points late did not finish (prog ${P.prog} of ${b})`);
  // and the glyph drawn honestly finishes
  for (let k = 0; k < P.SEGS.length; k++){
    const [sa, sb] = P.SEGS[k]; P.setSeg(k); fol(den(P.PATH[sa]), true);
    for (let i = sa; i <= sb; i++) fol(den(P.PATH[i]));
  }
  ok(P.done, `ふ drawn honestly did not finish (prog ${P.prog} of ${P.PATH.length-1})`);
}
{
  // and nothing is cast or kindled here. A lit monster that is not the
  // target, so the check is on the charge (a wisp would spend one) rather
  // than on a shot that would have landed and gone, and nothing else on the
  // field is trying to kill it.
  F.quench();
  fresh(); F.setDifficulty('guided');
  F.spawn();
  const other = F.monsters.find(m => m !== F.target) || F.target;
  const lit = P.LETTERS[other.i][0];
  F.kindle(lit, 3);
  advance(cfg.castMs * 2);
  ok(F.charge(lit) === 3, `a wisp flew in guided (charge ${F.charge(lit)} of 3)`);
  F.quench();
  const drew = P.LETTERS[P.idx][0];
  globalThis.conjure();
  ok(F.charge(drew) === 0, 'a guided trace kindled the character');
  F.quench();
}
F.setDifficulty('medium');

// ---- the workshop's practice controls and hint are gone from the game
ok(/body\.field[^{]*\.only-p[^{]*\{ display:none/.test(html),
   'the practice row (Back/Clear/Next, Watch teacher) is showing in the game');
ok(/body\.field[^{]*\.hint[^{]*\{ display:none/.test(html), 'the "Easy mode" hint is showing in the game');

// ---- the tracer asks in its own order, not the farang's
// "I wrote tsu like four times in a row. Don't base what I trace on what
// enemies populate." The sketchbook asks from a queue over the open rows;
// what is drawn hits whichever farang carries it, or is kept as a light.
ok(F.monsters.length >= 1, 'no monster at boot — there is nothing to answer');
ok(F.roster().includes(P.idx), `the tracer is on ${P.LETTERS[P.idx][0]}, which is not on the field's rows`);
{
  // a load the engine starts on its own lands on what the field asks for
  fresh();
  const want = P.idx, away = (P.idx + 7) % P.LETTERS.length;
  globalThis.load(away);
  ok(P.idx === want, `load(${away}) landed on ${P.LETTERS[P.idx][0]}, not what the field asked for — the field is not driving the tracer`);
}
{
  // no character comes round again until noRepeat others have
  fresh(); const seen = [];
  for (let k = 0; k <= cfg.noRepeat; k++){ seen.push(P.LETTERS[P.idx][0]); globalThis.conjure(); advance(cfg.advanceMs + 60); }
  ok(new Set(seen).size === seen.length, `a character came round again within ${cfg.noRepeat + 1} traces: ${seen.join(' ')}`);
}
{
  // arrivals do not swap the character under the hand
  fresh(); const before = P.idx;
  for (let k = 0; k < 5; k++) F.spawn();
  advance(300);
  ok(P.idx === before, 'a farang arriving changed what the tracer asked for');
}
{
  // a finished character hits whichever farang carries it, nearest first
  fresh(); F.spawn(); F.spawn();
  const carrier = F.monsters[0]; F.ask(carrier.i); F.retarget(true);
  ok(P.idx === carrier.i, 'ask() did not point the tracer at the character');
  for (const m of F.monsters) if (m !== carrier) m.d = 0.2;
  carrier.d = 0.9;
  globalThis.conjure();
  ok(F.shots.length === 1 && P.LETTERS[F.shots[0].to.i][0] === P.LETTERS[carrier.i][0], 'the shot went to a farang carrying another character');
  // and one nothing carries hits nothing, and is kept as a light
  fresh(); advance(cfg.advanceMs + 60);
  const none = F.roster().find(i => !F.monsters.some(m => m.i === i));
  if (none != null){
    F.ask(none); F.retarget(true);
    const n0 = F.shots.length; globalThis.conjure();
    ok(F.shots.length === n0, 'a character no farang carries hit something');
    ok(F.charge(P.LETTERS[none][0]) >= 1, 'a character no farang carries was not kept as a light');
  }
}
// ---- tapping a farang asks for its character
fresh();
F.spawn(); F.spawn();
{
  const other = F.monsters.find(m => m.i !== P.idx);
  if (other){
    const p = F.posOf(other);
    ok(F.pick(p.x, p.y - 14), 'tapping a monster did not select it');
    ok(P.idx === other.i, 'tap did not point the tracer at the tapped monster');
  }
}

// ---- the next glyph arrives promptly, not after the celebration
fresh();
F.ask(F.monsters[0].i); F.retarget(true);   // ask for a character a farang carries, so the shot has somewhere to go
const before2 = F.killed;
globalThis.conjure();
F.quench();   // the conjure kindled the glyph; a twin would draw a second kill
// the shot flies at t += dt*2.6, so it lands at ~385ms
advance(420);
ok(F.killed === before2 + 1, 'the shot had not landed by 420ms');
advance(cfg.advanceMs + 120);
ok(F.roster().includes(P.idx) && !P.done, `after ${cfg.advanceMs}ms the tracer has not moved on (on ${P.LETTERS[P.idx][0]}, done ${P.done})`);
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
  const first = F.monsters[0], twin = F.monsters.find(m => m !== first);
  if (twin){
    twin.i = first.i; F.ask(first.i); F.retarget(true);
    // restart() leaves spawnAt at 0, so the first frame adds a third monster;
    // let it arrive, then send it away so only the twin can be next.
    advance(50);
    for (const m of [...F.monsters]) if (m !== first && m !== twin) F.monsters.splice(F.monsters.indexOf(m), 1);
    globalThis.conjure();
    // The conjure kindles the character, and a wisp would take the twin, empty
    // the field, and let the refill clear `done` for the wrong reason.
    F.quench();
    advance(cfg.advanceMs + 120);
    ok(!P.done, 'after a conjure the tracer stayed in its celebration');
    ok(F.roster().includes(P.idx), 'the tracer is not on a character from the open rows');
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
  F.ask(F.monsters[1].i); F.retarget(true);   // ask for a character on the field
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
  ok(P.idx === held, 'a breach moved the tracer off what it was asking for: the queue, not the farang, decides');
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
  ok(F.roster().includes(P.idx), `tracer stuck on ${P.LETTERS[P.idx][0]}, which is not on the field's rows`);
}

// ---- the reading is shown when a monster falls
fresh();
{
  F.ask(F.monsters[0].i); F.retarget(true);   // a character a farang carries, so there is a kill
  const before = F.readings.length;
  globalThis.conjure();
  advance(500);
  ok(F.readings.length > before, 'no reading shown on a kill — the sound never arrives');
  const r = F.readings[F.readings.length-1];
  ok(r && /^[a-z ]+$/.test(r.text),
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

// the one under the pen is yours: no wisp at the farang the hand is answering mid-trace
// (the one carrying the character the tracer is on — since the queue, not the nearest)
fresh();
{
  const mine = F.monsters[0];
  F.ask(mine.i); F.retarget(true);
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
  // the lights are the run's: a new run begins dark
  F.restart();
  ok(F.charge('あ') === 0 && Object.keys(F.hitodama).length === 0, `a light carried into the next run (あ holds ${F.charge('あ')})`);
  ok(F.energy === cfg.energyStart, `a run begins with ${F.energy} 気, expected ${cfg.energyStart}`);
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
const victim = F.monsters[0], before = F.killed;
ok(victim, 'no farang after restart');
F.ask(victim.i); F.retarget(true);   // ask for what it carries
globalThis.conjure();
// The conjure also kindles the character, and every forty runs or so a second
// monster carries it and a wisp would make this two banishments, not one.
F.quench();
ok(F.shots.length === 1, `conjure fired ${F.shots.length} shots, expected 1`);
ok(F.shots[0].to === victim, 'the shot is aimed at something other than the target');
advance(1200);
ok(F.killed === before + 1, `killed went ${before} -> ${F.killed}, expected one banishment`);
ok(!F.monsters.includes(victim), 'the monster survived a completed glyph');

// ---- and the tracer moves to whatever is next in its own queue
ok(F.roster().includes(P.idx) && P.idx !== victim.i, 'after a kill the tracer is still on the dead monster\'s glyph');

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

// ---- guided can repaint
// It wipes the pen's mark with the engine's `ink` context on every pointer
// move. v0.1.39 hid that name behind the run's currency and guided threw on
// each one. The stub's contexts answer to anything, so call it and see.
{
  fresh(); F.setDifficulty('guided');
  let threw = null;
  try { globalThis.redrawInk(); } catch (e) { threw = e; }
  ok(!threw, `guided cannot repaint: ${threw && threw.message}`);
  F.setDifficulty('medium');
}

const line = (x0, y0, x1, y1, n, t0 = 0) => Array.from({length:n}, (_, i) => ({ x: x0 + (x1-x0)*i/(n-1), y: y0 + (y1-y0)*i/(n-1), p:.5, t: t0 + i*8 }));
// ---- the run: ink, the workshop strip, and farang that take more than one hit
//
// The rule being defended is the one The Tower does not have: nothing here
// draws for you. Ink comes from tracing, upgrades multiply what a trace is
// worth, and a tough farang still needs the hand before the lights can finish
// it. If any of that slips, the idle half quietly becomes the whole game.
{
  fresh(); F.setDifficulty('medium');
  ok(F.ink === 0 && Object.values(F.upgrades).every(v => v === 0), 'a fresh run did not start with no ink and no upgrades');
  ok(F.hpFor(0) === 1 && F.hpFor(cfg.hpEvery - 1) === 1, 'the first farang take more than one hit');
  ok(F.hpFor(cfg.hpEvery) === 2, `farang did not toughen at wave ${cfg.hpEvery}`);
  ok(F.hpFor(cfg.hpEvery * 99) === cfg.hpMax, 'toughness is not capped');

  // ink is paid for the trace, and a clean one pays more
  globalThis.conjure();
  ok(F.ink === cfg.inkTrace + cfg.inkClean, `a clean trace paid ${F.ink} ink, expected ${cfg.inkTrace + cfg.inkClean}`);
  advance(cfg.advanceMs + 50);
  const before = F.ink;
  globalThis.zap({x:1, y:1});
  globalThis.conjure();
  ok(F.ink - before === cfg.inkTrace, `a zapped trace paid ${F.ink - before} ink, expected ${cfg.inkTrace}`);

  // nothing is bought on credit, and a purchase is spent
  fresh();
  ok(F.buy('quick') === false && F.upgrades.quick === 0, 'an upgrade was bought with no ink');
  const c0 = F.costOf('quick');
  F.earn(c0);
  ok(F.buy('quick') === true && F.upgrades.quick === 1 && F.ink === 0, 'buying did not spend the ink or raise the level');
  ok(F.costOf('quick') > c0, 'the second level costs no more than the first');
  ok(F.castMs() < cfg.castMs, 'quick did not make the lights fly faster');
  ok(F.buy('nonsense') === false, 'an upgrade that does not exist was bought');

  // an upgrade stops at its ceiling
  F.earn(100000);
  let n = 0; while (F.buy('intent') && n < 50) n++;
  ok(F.upgrades.intent === F.UPG.intent.max, `intent went to ${F.upgrades.intent}, its ceiling is ${F.UPG.intent.max}`);
  ok(/<small>max<\/small>/.test(F.upgHtml) && /data-upg="intent"[^>]*disabled/.test(F.upgHtml), 'a maxed upgrade still offers itself for sale');

  // intent: every light cuts deeper — it multiplies the hand, it does not replace it
  fresh(); F.quench(); F.earn(100000); F.buy('intent');
  { const m = F.monsters[0]; m.hp = 5; F.hit(m, false, false); ok(m.hp === 3, `one hit with intent 1 took ${5 - m.hp}, expected 2`); }
  // breath: every stroke fills 気 by one more
  fresh(); F.quench(); F.earn(100000);
  ok(F.buy('breath') === true && F.upgrades.breath === 1, `breath could not be bought (over ${F.over}, ink ${F.ink}, level ${F.upgrades.breath})`);
  { F.fill(-999); P.strokes.length = 0; P.strokes.push(line(120, 120, 280, 130, 60), line(200, 100, 210, 300, 80, 900));
    globalThis.conjure(); const filled = F.energy;   // read before the wait: a light may spend some on a farang carrying the character
    advance(cfg.advanceMs + 60);
    ok(filled === 2 * (cfg.energyPerStroke + 1), `two strokes with breath 1 filled 気 by ${filled}, expected ${2 * (cfg.energyPerStroke + 1)}`); }
  F.quench();
  ok(Object.keys(F.hitodama).length === 0, 'buying something lit a character nobody traced');

  // mend is a heart now and a bigger ward for the rest of the run
  fresh(); F.earn(100000);
  const w0 = F.ward, m0 = F.wardMax;
  F.buy('mend');
  ok(F.wardMax === m0 + 1 && F.ward === w0 + 1, `mend took the ward from ${w0}/${m0} to ${F.ward}/${F.wardMax}`);

  // 耐: the farang bite harder as the waves climb, and the tab stands against it
  fresh();
  ok(F.UPG.mend.tab === 'guard' && F.UPG.wall.tab === 'guard' && F.UPG.tend.tab === 'guard' && F.UPG.intent.tab === 'skills',
     'mend, wall and tend belong to 耐; intent to 技');
  ok(F.biteFor(0, false) === 1, `a breach at the foot of the tower costs ${F.biteFor(0, false)}, expected 1`);
  ok(F.biteFor(cfg.biteEvery, false) === 2, `a breach at wave ${cfg.biteEvery} costs ${F.biteFor(cfg.biteEvery, false)}, expected 2`);
  ok(F.biteFor(cfg.biteEvery * 100, false) === cfg.biteMax, `the bite went past its ceiling: ${F.biteFor(cfg.biteEvery * 100, false)}`);
  { const bb = JSON.parse(html.match(/tower:(\{[^}]*\})/)[1]).bossBite;
    ok(F.biteFor(0, true) === 1 + bb, `a boss bites ${F.biteFor(0, true)}, expected ${1 + bb}`); }
  F.earn(100000); F.buy('wall');
  ok(F.upgrades.wall === 1 && F.biteFor(cfg.biteEvery, false) === 1, `one wall left a wave-${cfg.biteEvery} bite at ${F.biteFor(cfg.biteEvery, false)}, expected 1`);
  ok(F.biteFor(0, false) === 1, 'a wall took a bite below one');
  // and a real breach takes what biteFor says
  { const m = F.monsters[0]; const before = F.ward, bite = F.biteFor(F.wave, m.boss);
    m.d = 0.07; m.speed = 0.055;
    advance(300);
    ok(!F.monsters.includes(m), 'test setup: the farang should have breached');
    ok(F.ward === before - bite, `a breach took ${before - F.ward}, biteFor said ${bite}`); }
  // tend: for every stretch of waves held, a life back, up to the ward's size
  fresh(); F.earn(100000); F.buy('tend');
  { const m = F.monsters[0]; m.d = 0.07; m.speed = 0.055; advance(300); }
  ok(F.ward === F.wardMax - 1, `test setup: the ward should be one down (${F.ward}/${F.wardMax})`);
  for (const m of F.monsters) m.speed = 0;
  { let guard = 0; while (F.wave % cfg.tendEvery !== 0 && guard++ < 50){ F.spawn(); for (const m of F.monsters) m.speed = 0; }
    ok(F.wave % cfg.tendEvery === 0, `test setup: could not reach a tend wave (wave ${F.wave})`);
    ok(F.ward === F.wardMax, `tend did not give the life back at wave ${F.wave}: ${F.ward}/${F.wardMax}`); }
  ok(/data-upg="wall"/.test(F.guardHtml) && /data-upg="tend"/.test(F.guardHtml) && /data-upg="mend"/.test(F.guardHtml) && !/data-upg="mend"/.test(F.upgHtml),
     'the 耐 strip is missing something, or mend is still on 技');
  advance(20);
  ok(/data-tab="boosts"/.test(F.dashHtml) && !/data-tab="guard"|data-tab="lanterns"/.test(F.dashHtml), 'the seam should carry one shop, boosts, and no lantern room');
  ok(/data-tab="boosts"[^>]*>\s*<svg/.test(F.dashHtml), 'the boosts tab has no mark on it');
  ok(/data-tab="trace"[^>]*aria-label="the sketchbook"/.test(F.dashHtml), 'the sketchbook tab is unlabelled');
  // every upgrade wears a mark, and the lanterns too
  { const all = F.upgHtml + F.guardHtml + F.driveHtml;
    for (const id of Object.keys(F.UPG)) ok(new RegExp(`data-upg="${id}"[^>]*>\\s*<b>\\s*<svg`).test(all), `${id} has no mark`);
    F.openTab('lanterns');
    for (const id of Object.keys(F.LANTERN)) ok(new RegExp(`data-lantern="${id}"[^>]*>\\s*<b>\\s*<svg`).test(F.lanternHtml || ''), `lantern ${id} has no mark`);
    F.openTab(null); }
  ok(F.openTab('guard') === 'boosts' && F.tab === 'boosts' && !F.paused, 'the old 耐 tab did not open the boosts, or paused the run');
  F.openTab(null);

  // 志: currency gain. diligence on the trace, harvest on the banish, rise on the fall
  fresh(); F.quench(); F.earn(100000);
  ok(F.UPG.dilig.tab === 'drive' && F.UPG.harvest.tab === 'drive' && F.UPG.rise.tab === 'drive', 'diligence, harvest and rise belong to 志');
  ok(F.buy('dilig') && F.buy('harvest') && F.buy('rise'), 'a full purse could not buy 志');
  { const ink0 = F.ink; P.strokes.length = 0; P.strokes.push(line(120, 120, 280, 130, 60));
    globalThis.conjure(); const paidTrace = F.ink - ink0;
    advance(cfg.advanceMs + 60);
    ok(paidTrace === cfg.inkTrace + cfg.inkClean + 1, `a clean trace with diligence 1 paid ${paidTrace}, expected ${cfg.inkTrace + cfg.inkClean + 1}`); }
  { const m = F.monsters[0]; m.hp = 1; const ink0 = F.ink; F.hit(m, false, true);
    ok(F.ink - ink0 === cfg.inkKill + 1, `a light's banish with harvest 1 paid ${F.ink - ink0}, expected ${cfg.inkKill + 1}`); }
  ok(/data-upg="rise"/.test(F.driveHtml) && !/data-upg="rise"/.test(F.upgHtml) && !/data-upg="rise"/.test(F.guardHtml), 'rise is not on 志 alone');
  advance(20);
  ok(F.openTab('drive') === 'boosts' && !F.paused, 'the old 志 tab did not open the boosts, or paused the run');
  F.openTab(null);

  // a tough farang survives the first hit, and the pips say how much is owed
  fresh(); F.quench();
  const tough = F.monsters[0];
  tough.hp = 3; tough.d = 0.9;
  F.hit(tough, false, false);
  ok(F.monsters.includes(tough) && tough.hp === 2, `one hit on a 3-hit farang left it at ${tough.hp} and ${F.monsters.includes(tough) ? 'alive' : 'gone'}`);
  ok(F.readings.length === 1, 'the hand landed a hit and no reading bloomed');
  F.hit(tough, false, true);
  ok(F.readings.length === 1, 'a wisp that did not finish the job bloomed a reading anyway');
  const inkBefore = F.ink;
  F.hit(tough, false, true);
  ok(!F.monsters.includes(tough), 'three hits did not banish a 3-hit farang');
  ok(F.ink === inkBefore + cfg.inkKill, 'a wisp finishing a farang paid no ink');
  ok(F.readings.length === 2, 'the reading did not bloom when it finally went');

  // shove: every hit pushes them back, and never past the edge
  fresh(); F.earn(100000); F.buy('shove');
  const s = F.monsters[0]; s.hp = 2; s.d = 0.5;
  F.hit(s, false, true);
  ok(Math.abs(s.d - (0.5 + cfg.shoveStep)) < 1e-9, `shove moved it to ${s.d}, expected ${0.5 + cfg.shoveStep}`);
  s.d = 0.999; s.hp = 2; F.hit(s, false, true);
  ok(s.d <= 1, 'shove pushed a farang off the field');

  // the whole loop: a 3-hit farang is finished by the lights one trace lit
  fresh(); F.quench();
  const boss = F.monsters[0];
  // parked near the ward and still, so it stays the nearest target while the
  // wait spawns others (one carrying the same character, nearer, took the light)
  boss.hp = 3; boss.d = 0.3; boss.speed = 0;
  F.ask(boss.i); F.retarget(true);            // ask for what it carries
  globalThis.conjure();                       // hit one, and the character is lit
  advance(cfg.castMs * 4 + 2000);
  ok(!F.monsters.includes(boss), `a clean trace and its two lights did not finish a 3-hit farang (hp ${boss.hp}, charge ${F.charge(P.LETTERS[boss.i][0])}, 気 ${F.energy}, shots ${F.shots.length}, same-character farang ${F.monsters.filter(m => m.i === boss.i).length}, tracer on ${P.LETTERS[P.idx][0]} vs ${P.LETTERS[boss.i][0]}, done ${P.done}, penDown ${F.penDown})`);

  // and all of it belongs to the run
  F.earn(50); F.buy('quick');
  fresh();
  ok(F.ink === 0 && F.upgrades.quick === 0 && F.upgrades.wall === 0 && F.wardMax === cfg.wardHp, 'ink or upgrades survived the ward falling');
  ok(/墨 0/.test(F.inkHtml) && /data-upg="quick"/.test(F.upgHtml), 'the boosts shop is missing or stale after a restart');
  // the dashboard on the seam: hearts, ink, 魂, the wave, and tabs that do not pause the run
  advance(20);
  ok(/class="bar life"/.test(F.dashHtml) && /class="bar energy"/.test(F.dashHtml) && /墨 0/.test(F.dashHtml) && /data-tab="boosts"/.test(F.dashHtml), `the dashboard is missing something: ${F.dashHtml.slice(0, 200)}`);
  ok(new RegExp(`<small>${F.wardMax}/${F.wardMax}</small>`).test(F.dashHtml), `the life bar does not read ${F.wardMax} of ${F.wardMax}`);
  ok(F.openTab('boosts') === 'boosts' && F.tab === 'boosts' && !F.paused, 'opening a tab paused the run, or did not open');
  ok(/data-tab="boosts" aria-pressed="true"/.test(F.dashHtml), 'the open tab is not shown as open');
  // the sketchbook is a tab too: a shop stands where it stood, and there is nothing to trace on
  const stageEl = F.sketchbook;   // the stub hands a fresh element to every lookup, so ask the shell for its own
  ok(stageEl.hidden === true, 'the sketchbook is still there under an open shop');
  ok(F.openTab(null) === null && F.tab === null, 'the tab did not close');
  ok(stageEl.hidden === false && /data-tab="trace" aria-pressed="true"/.test(F.dashHtml), 'closing the shop did not bring the sketchbook back');
  ok(F.openTab('trace') === null && F.tab === null, '筆 is not the way back to the sketchbook');
  // a tap is heard by the seam itself, on pointerdown, however often its buttons are rebuilt
  ok(typeof F.tap === 'function' && F.tap('button[data-tab="boosts"]') === true && F.tab === 'boosts', 'a pointerdown on the boosts tab did not open it');
  F.earn(1); advance(20);   // a re-render between
  ok(F.tap('button[data-tab="boosts"]') === true && F.tab === null, 'a second tap on the open tab, after a re-render, did not close it');
  // and a hand that has just lifted may open it at once: the engine's hold after a lift
  // (the retarget's wait) is not a pen on the glass
  F.touch();
  ok(F.openTab('boosts') === 'boosts' && stageEl.hidden === true, 'a shop would not open in the hold after a lift: "gotta push it a couple times"');
  F.openTab(null);
  advance(cfg.holdMs + 50);   // let the hold pass: the lights leave the hand's own target alone while it lasts
  F.restart();
  ok(F.tab === null && stageEl.hidden === false, 'a new run began with the shop open');

  // 気: one bag, filled by every stroke whatever is on the field, spent by every cast
  F.restart(); F.quench();
  ok(F.energy === cfg.energyStart, `a run starts with ${F.energy} 気, expected ${cfg.energyStart}`);
  P.strokes.length = 0; P.strokes.push(line(120, 120, 280, 130, 60), line(200, 100, 210, 300, 80, 900), line(100, 200, 300, 210, 60, 1800));
  const e0 = F.energy; globalThis.conjure(); const e1 = F.energy;   // read before the wait: a light may spend some on a farang carrying the character
  advance(cfg.advanceMs + 60);
  ok(e1 === e0 + 3 * cfg.energyPerStroke, `three strokes conjured filled 気 by ${e1 - e0}, expected ${3 * cfg.energyPerStroke}`);
  ok(F.fill(999) === cfg.energyMax, `気 overflowed its bag (${F.energy} of ${cfg.energyMax})`);
  // a lit character with an empty bag throws nothing; with 気 to throw, it throws and pays
  F.restart(); F.quench(); F.fill(-999);
  { const m = F.monsters[0]; F.kindle(P.LETTERS[m.i][0], 3); }
  ok(F.energy === 0 && F.autocast(T + 99999) === null, 'a lit character cast with an empty bag');
  F.fill(cfg.castCost);
  ok(F.autocast(T + 199999) !== null && F.energy === 0, `a lit character with 気 to throw did not cast, or the cast did not spend ${cfg.castCost} (left ${F.energy})`);

  // the release: a full bag is thrown all at once, nearest first, until the 気 runs out
  F.restart(); F.quench(); F.fill(-999);
  F.spawn(); F.spawn(); F.spawn();
  { const ms = F.monsters.slice(0, 3); ms.forEach((m, k) => { m.d = 0.9 - k*0.2; m.speed = 0; F.kindle(P.LETTERS[m.i][0], 3); });
    F.ask(ms[0].i); F.retarget(true);   // the hand is pointed at the farthest
    F.fill(cfg.castCost * 2);
    const n = F.release(T + 300000);
    ok(n === 2 && F.shots.length === 2 && F.energy === 0, `a bag of two casts released ${n} lights (shots ${F.shots.length}, 気 left ${F.energy})`);
    ok(F.shots.every(s => s.to !== ms[0]) && F.shots.some(s => s.to === ms[2]), 'the release did not go nearest first, or hit what the hand is tracing');
    ok(F.flare > 0, 'the release left no mark on the ward'); }
  // a stroke that fills the bag releases it
  F.restart(); F.quench(); F.fill(-999);
  { const m = F.monsters[0]; m.d = 0.2; m.speed = 0; F.kindle(P.LETTERS[m.i][0], 3);   // at the door: the hand's own target is answered there too
    F.fill(cfg.energyMax - 1); const b0 = F.flare;
    P.strokes.length = 0; P.strokes.push(line(120, 120, 280, 130, 60)); globalThis.conjure();
    ok(F.flare > b0 || F.shots.length > 0, 'a stroke that filled the bag did not release it'); advance(cfg.advanceMs + 60); }
  // rescue: the farang the hand is tracing for is left to the hand — until it is at the door
  F.restart(); F.quench(); F.fill(999);
  { const m = F.monsters[0]; m.speed = 0; F.kindle(P.LETTERS[m.i][0], 3); F.ask(m.i); F.retarget(true);
    F.touch();   // the pen is down
    m.d = 0.8;
    ok(F.autocast(T + 400000) === null, 'a light took the far farang the hand was tracing for');
    m.d = cfg.rescue - 0.05;
    ok(F.autocast(T + 500000) === m, 'a light left the farang at the door to a pen that was still drawing');
    advance(cfg.holdMs + 50); }
  // the door: a dark character about to walk in is what the pen is asked for, queue or no queue
  F.restart(); F.quench(); F.fill(-999);
  F.spawn(); F.spawn();
  { const [A, B] = F.monsters; A.d = 0.8; B.d = cfg.rescue - 0.05; A.speed = B.speed = 0;
    if (P.LETTERS[A.i][0] !== P.LETTERS[B.i][0]){
      F.ask(A.i); F.retarget(true);
      ok(P.idx === A.i, 'test setup: the tracer should be on the far farang');
      F.ask(null);                       // the hand has no standing request; the queue would decide
      advance(40);
      ok(P.idx === B.i, `a dark farang at the door did not pull the pen (on ${P.LETTERS[P.idx][0]}, the door carries ${P.LETTERS[B.i][0]})`);
      F.kindle(P.LETTERS[B.i][0], 3);    // lit, the lights answer it and the queue is not overridden
      F.ask(A.i); F.retarget(true); F.ask(null);
      advance(40);
      ok(P.idx === A.i, 'a lit farang at the door pulled the pen off the queue');
    } }
}

// ---- the run ends, says what it was, and is written down
// The ward falling was a toast and a field that went quiet. Now it is an
// ending: a record of the run goes to the hand's ledger (and from there to a
// signed-in player's save), the page says what happened, and "again" starts a
// clean run. What must not happen: a run recorded twice, a run that includes
// the time spent reading the start page, or an ending that can be dismissed
// into a field that is still dead.
{
  fresh();
  const H = globalThis.__hand; H.reset();
  F.begin();
  globalThis.conjure(); advance(cfg.advanceMs + 100);
  globalThis.zap({x:1,y:1}); globalThis.conjure(); advance(cfg.advanceMs + 100);
  const tracedBefore = F.run.traced, cleanBefore = F.run.clean;
  ok(tracedBefore === 2 && cleanBefore === 1, `the run counted ${tracedBefore} traces, ${cleanBefore} clean; expected 2 and 1`);
  // let them in
  for (let guard = 0; !F.over && guard < 400; guard++){ for (const m of F.monsters) m.d = 0.061; advance(40); }
  ok(F.over, 'the ward never fell');
  const e = F.ended;
  ok(e && e.rec.traced === 2 && e.rec.clean === 1 && e.rec.wave >= 1, `the run's record is ${JSON.stringify(e && e.rec)}`);
  ok(e && e.rec.ms > 0 && e.rec.ms < 120000, `the run lasted ${e && e.rec.ms}ms by its own account`);
  ok(H.ledger.runs.length === 1 && H.ledger.best[e.rec.realm].wave === e.rec.wave, 'the run was not written into the ledger');
  F.endRun(); F.endRun();
  ok(H.ledger.runs.length === 1, `ending twice recorded the run ${H.ledger.runs.length} times`);
  advance(900);
  ok(F.view === 'over' && F.paused, `after the ward fell the page shows "${F.view}"`);
  ok(/the ward fell/.test(F.startHtml) && /banished/.test(F.startHtml) && />again</.test(F.startHtml), 'the ending does not say what happened or offer another go');
  ok(/saved on this device/.test(F.startHtml), 'the ending does not say where the run was kept');
  // the ending is its own page: the numbers, the pay, again, the workshop, home — no shop on it
  ok(!/data-wtab=/.test(F.startHtml) && /class="start-workshop"/.test(F.startHtml) && /class="start-home" href="\.\.\/index\.html"/.test(F.startHtml), 'the ending should be separate from the workshop and offer a way home');
  // the page and back: still the ending, not a start page over a dead field
  F.openStart();
  ok(F.view === 'over', 'reopening the page after a fall showed the start page over a dead field');
  // again: a clean run
  F.begin();
  ok(!F.over && F.ward === cfg.wardHp && F.run.traced === 0 && F.ink === 0 && F.ended === null, 'again did not start a clean run');
  // a second, shorter run does not overwrite the furthest
  const far = H.ledger.best[e.rec.realm].wave;
  for (let guard = 0; !F.over && guard < 400; guard++){ for (const m of F.monsters) m.d = 0.061; advance(40); }
  ok(H.ledger.runs.length === 2, 'the second run was not recorded');
  ok(H.ledger.best[e.rec.realm].wave >= far, 'a shorter run overwrote the furthest one');
  fresh();
}

// ---- the tower, 魂, and the workshop between rounds
// "There is no completing a level. You just keep going until the swarm
// consumes you." The checks that matter: a character on the field from a row
// the run has not reached, a purchase on credit, a run that ends in a win, a
// boss that does not dim the shape for everyone, a guided run that sets a record.
{
  const H = globalThis.__hand; H.reset();
  fresh(); F.setDifficulty('medium');
  const realm = 'hiragana';
  const tw = JSON.parse(html.match(/tower:(\{[^}]*\})/)[1]);
  ok(F.bestWave === 0 && F.rowsOpen() === tw.rows, `a new player starts with ${F.rowsOpen()} rows open (furthest wave ${F.bestWave})`);
  // only the open rows are ever on the field
  const allowed = new Set(F.roster());
  ok(allowed.size > 0 && allowed.size < P.LETTERS.length, `the first rows put ${allowed.size} of ${P.LETTERS.length} characters on the field`);
  ok([...allowed].every(i => (P.LETTERS[i][6] || 1) <= tw.rows), 'the roster reaches past the open rows');
  let stray = 0; for (let k = 0; k < tw.rowWaves - 1; k++){ F.spawn(); if (!allowed.has(F.monsters[F.monsters.length-1].i)) stray++; }
  ok(stray === 0, `${stray} farang carried a character from a row the run has not reached`);
  // and a row opens as the run goes deeper
  F.spawn();
  ok(F.wave >= tw.rowWaves && F.rowsOpen() === tw.rows + 1 && F.roster().length > allowed.size, `wave ${tw.rowWaves} did not open the next row (${F.rowsOpen()} rows, ${F.roster().length} characters)`);
  // there is no win: answer everything for a long while and the run is still on
  for (let g = 0; g < 300 && !F.over; g++){ for (const m of [...F.monsters]){ m.hp = 1; F.hit(m, false, false); } advance(60); }
  ok(!F.over, 'the run ended without the ward falling');

  // a boss every bossEvery waves, and while it lives every character gets less help
  fresh(); F.setDifficulty('medium');
  for (let k = 0; k < tw.bossEvery; k++) F.spawn();
  // (a fresh field has already spawned once, so the tenth wave is the ninth of these)
  const bosses = F.monsters.filter(m => m.boss);
  ok(bosses.length === 1, `${tw.bossEvery} waves brought ${bosses.length} boss(es)`);
  ok(bosses[0].hp >= 1 + tw.bossHp, `the boss takes ${bosses[0].hp} hits`);
  ok(F.bossAlive() && P.SHADOW_MODE === 'faint', `a boss on the field did not dim the shape for everyone (${P.SHADOW_MODE})`);
  bosses[0].hp = 1; F.hit(bosses[0], false, false);
  ok(!F.bossAlive() && P.SHADOW_MODE === 'strokes', `the shape did not come back when the boss fell (${P.SHADOW_MODE})`);

  // nothing is for sale to an empty purse
  fresh();
  ok(H.tama.balance === 0 && F.buyLantern('heart') === false, 'something was bought with nothing');

  // lose: it pays, and the furthest wave is kept for good
  fresh(); F.begin();
  globalThis.conjure(); advance(cfg.advanceMs + 60);
  const bal0 = H.tama.balance;
  for (let g = 0; !F.over && g < 400; g++){ for (const m of F.monsters) m.d = 0.061; advance(40); }
  ok(F.over && F.ended.pay > 0 && H.tama.balance === bal0 + F.ended.pay, `a lost run paid ${F.ended && F.ended.pay} and the purse moved by ${H.tama.balance - bal0}`);
  ok(F.ended.rec.frames && F.ended.rec.frames.n > 0 && F.ended.rec.frames.slow <= F.ended.rec.frames.n, `the run did not count its frames: ${JSON.stringify(F.ended.rec.frames)}`);
  ok(H.ledger.best[realm] && H.ledger.best[realm].wave === F.ended.rec.wave, 'the furthest wave was not kept');
  advance(900);
  ok(/the ward fell/.test(F.startHtml) && /\+ 魂/.test(F.startHtml) && !/gate to stage/.test(F.startHtml), 'the ending does not say the ward fell and what was paid, or still sells a gate');
  // and the furthest wave opens rows for every run after
  H.ledger.best[realm].wave = tw.rowWaves * 3;
  fresh();
  ok(F.rowsOpen() === tw.rows + 3 && F.roster().length > allowed.size, `a furthest wave of ${tw.rowWaves * 3} opened ${F.rowsOpen()} rows`);
  H.ledger.best[realm].wave = 0;
  fresh(); H.tama.earn(100000);

  // what lasts, lasts: into the next run and the one after
  const hearts = F.wardMax, cap = F.capNow();
  const bag = F.energyMax;
  ok(F.buyLantern('heart') && F.buyLantern('lamp') && F.buyLantern('inkwell') && F.buyLantern('vessel'), 'a full purse could not buy the lanterns');
  // what lasts is bought between runs, in tabs, with 魂: a level that lasts is a level in the run
  F.openStart();
  ok(/data-wtab="attack"/.test(F.startHtml) && /data-wtab="defend"/.test(F.startHtml) && /data-wtab="earn"/.test(F.startHtml) && /data-wtab="lanterns"/.test(F.startHtml) && /data-wtab="more"/.test(F.startHtml), 'the workshop between runs is missing a tab');
  ok(/data-perm="intent"/.test(F.startHtml) && /data-perm="wall"/.test(F.startHtml) && /data-perm="rise"/.test(F.startHtml) && /data-lantern="heart"/.test(F.startHtml), 'the workshop does not sell what lasts');
  ok(/KanjiVG/.test(F.startHtml) && /draw with/.test(F.startHtml), 'the "more" tab has lost the credits or the settings');
  ok(/class="start-home" href="\.\.\/index\.html"/.test(F.startHtml), 'the start page has no way home');
  ok(F.showWtab('defend') === undefined && F.wtab === 'defend', 'a workshop tab did not switch');
  { const own0 = F.own('intent'), bal0 = H.tama.balance, c = F.permCost('intent');
    ok(F.buyPerm('intent') === true && F.own('intent') === own0 + 1 && H.tama.balance === bal0 - c, `a permanent intent could not be bought (own ${F.own('intent')}, balance ${H.tama.balance}, was ${bal0}, cost ${c})`);
    ok(F.permCost('intent') > c, 'the next level of a permanent upgrade does not cost more');
    fresh(); F.quench();
    ok(F.lvl('intent') === own0 + 1 && F.upgrades.intent === 0, `a level that lasts did not carry into the run (lvl ${F.lvl('intent')}, run ${F.upgrades.intent})`);
    const m = F.monsters[0]; m.hp = 5; F.hit(m, false, false);
    ok(m.hp === 5 - (1 + F.lvl('intent')), `a hit with a lasting intent ${F.lvl('intent')} took ${5 - m.hp}`);
    F.earn(100000); let n = 0; while (F.buy('intent') && n < 50) n++;
    ok(F.lvl('intent') === F.UPG.intent.max && F.upgrades.intent === F.UPG.intent.max - F.own('intent'), `the run bought past the ceiling (lvl ${F.lvl('intent')}, run ${F.upgrades.intent}, own ${F.own('intent')})`);
    ok(F.buyPerm('intent') === false || F.own('intent') <= F.UPG.intent.max, 'a permanent upgrade went past its ceiling'); }
  fresh(); F.begin();
  ok(F.energyMax === bag + cfg.vesselStep, `a vessel did not grow the bag (${F.energyMax}, was ${bag})`);
  ok(F.ward === hearts + 1 && F.wardMax === hearts + 1, `a heart did not carry into the next run (ward ${F.ward}, was ${hearts})`);
  ok(F.capNow() === cap + 1, 'a lamp did not raise how many lights a character holds');
  ok(F.ink === cfg.inkwellStep, `an inkwell started the run with ${F.ink} ink, expected ${cfg.inkwellStep}`);
  F.quench(); const ch = P.LETTERS[P.idx][0]; F.kindle(ch, 99);
  ok(F.charge(ch) === cap + 1, `a character holds ${F.charge(ch)} lights with one lamp`);
  F.quench();
  let n = 0; while (F.buyLantern('heart') && n < 20) n++;
  ok(H.tama.own('heart') === F.LANTERN.heart.max, `hearts went to ${H.tama.own('heart')}`);

  // guided cannot be zapped, so it pays less for the same hand
  const payFor = d => { H.reset(); fresh(); F.setDifficulty(d); F.begin(); for (let k = 0; k < 4; k++){ globalThis.conjure(); advance(cfg.advanceMs + 60); }
    for (let g = 0; !F.over && g < 400; g++){ for (const m of F.monsters) m.d = 0.061; advance(40); } return F.ended.pay; };
  const guided = payFor('guided'), medium = payFor('medium');
  ok(guided === 0 && medium > 0, `four clean traces paid guided ${guided}, medium ${medium}`);
  F.setDifficulty('medium'); H.reset(); fresh();
}

// ---- recognisable pays more, and guided only gets you so far
{
  const H = globalThis.__hand; H.reset();
  F.setDifficulty('medium');
  // the book's own shape, drawn dx to the side of where it belongs
  const ink = dx => { P.strokes.length = 0; for (const [a, b] of P.SEGS) P.strokes.push(P.PATH.slice(a, b + 1).map((q, i) => ({x:(q.x + dx)*P.W, y:q.y*P.H, p:.5, t:i*10}))); };
  const payOf = dx => { fresh(); F.begin(); ink(dx); globalThis.conjure(); const r = { pay: F.run.pay, q: H.last && H.last.q }; advance(cfg.advanceMs + 60); return r; };
  // The glyph and its size are random. 0.006 of the canvas is a small drift for the
  // smallest character at the smallest size; 0.035 was already off the scale for those.
  const crisp = payOf(0), off = payOf(0.006), lost = payOf(0.2);
  ok(off.q > 0 && lost.q === 0, `the test's drifts are off the scale: ${off.q}, ${lost.q}`);
  ok(crisp.q >= 0.9, `the book's own shape scored ${crisp.q}`);
  ok(crisp.q > off.q && off.q > lost.q, `recognisability does not fall as the ink drifts: ${crisp.q}, ${off.q}, ${lost.q}`);
  ok(crisp.pay > off.pay && off.pay > lost.pay, `a more recognisable trace did not pay more: ${crisp.pay}, ${off.pay}, ${lost.pay}`);
  ok(lost.pay >= cfg.tamaClean * 0.5 - 1e-9 && crisp.pay <= cfg.tamaClean * 1.5 + 1e-9, `pay left its bounds: ${lost.pay} .. ${crisp.pay}`);
  // a conjure with no ink (nothing to judge) pays par, not zero and not a bonus
  fresh(); F.begin(); P.strokes.length = 0; globalThis.conjure();
  ok(Math.abs(F.run.pay - cfg.tamaClean) < 1e-9, `a trace with nothing to judge paid ${F.run.pay}, par is ${cfg.tamaClean}`);

  // 起 rise: the fall pays more 魂, by riseStep per level
  { const fall = () => { for (let g = 0; !F.over && g < 400; g++){ for (const m of F.monsters) m.d = 0.061; advance(40); } return F.ended.pay; };
    // the glyph and its recognisability are random, so each run is judged
    // against its own base: what it traced plus its waves, times medium's rate
    const base = () => F.run.pay + Math.floor(F.ended.rec.wave / cfg.tamaWaves);
    fresh(); F.begin(); F.setDifficulty('medium'); P.strokes.length = 0; globalThis.conjure(); advance(cfg.advanceMs + 60);
    const plain = fall(), rate = Math.round(plain / base());
    ok(plain > 0 && rate >= 1, `test setup: a plain medium run paid ${plain} on a base of ${base()}`);
    fresh(); F.begin(); F.setDifficulty('medium'); P.strokes.length = 0; globalThis.conjure(); advance(cfg.advanceMs + 60);
    F.earn(100000); F.buy('rise');
    const risen = fall(), want = Math.round(base() * rate * (1 + cfg.riseStep));
    ok(risen === want, `rise 1 paid ${risen} on a base of ${base()} at ×${rate}, expected ${want}`); }

  // guided is a sandbox: it pays nothing, and its waves are no record
  H.reset();
  const fall = d => { fresh(); F.setDifficulty(d); F.begin(); globalThis.conjure(); advance(cfg.advanceMs + 60);
    for (let g = 0; !F.over && g < 400; g++){ for (const m of F.monsters) m.d = 0.061; advance(40); } advance(900); return F.ended; };
  const g = fall('guided');
  ok(g && g.pay === 0 && g.rec.practice === true, `practice in guided paid ${g && g.pay}: it is a sandbox and pays nothing`);
  ok(!H.ledger.best.hiragana, 'a guided run set the furthest wave');
  ok(/guided is practice/.test(F.startHtml), 'the ending does not say guided is practice');
  const e = fall('medium');
  ok(e && e.pay > 0 && H.ledger.best.hiragana && H.ledger.best.hiragana.wave === e.rec.wave, 'the same run at medium did not count');
  fresh(); F.setDifficulty('guided'); F.openStart();
  ok(/practice: nothing counts/.test(F.startHtml), 'the start page does not say guided counts for nothing');
  F.setDifficulty('medium'); H.reset(); fresh();
}

// every conjure in this file went through the hand; none of its notes may have thrown
ok(globalThis.__hand.faults === 0, `the hand's note threw ${globalThis.__hand.faults} time(s) during the field's checks`);

if (fail) { console.log(`  ${fail} field check(s) failed`); process.exit(1); }
console.log(`  monsters advance and spawn, a finished glyph banishes the target, `
  + `the tracer retargets, the ward falls and restarts, `
  + `ink is earned by tracing, upgrades multiply the hand without replacing it, a tough farang is finished by the lights one trace lit, a fallen ward ends the run and writes it down, and a stage cannot be passed without holding it, nor its gate bought on credit, a recognisable trace pays more, and guided only gets you so far`);
