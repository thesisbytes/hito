/**
 * A stroke that went nowhere, and a fizzle that starts the character again.
 *
 * A stroke that starts off the path gets a zap, the hand lifts and draws it
 * again, and the first one stayed: on the canvas in the workshop and in the
 * hand's record everywhere — 61 of the first 286 traces carried a redrawn
 * stroke, and the maintainer called the recordings a mess. Now the pen
 * lifting asks whether the stroke got anywhere. If not: dropped as if it
 * never happened (guided, easy, the workshop), or the character restarts
 * (medium and up), or kept (the old rule, for anyone who wants it).
 *
 *   node build/test/stray.test.mjs dist/hiragana-vX.Y.Z.html [dist/hiragana-game-vX.Y.Z.html]
 */
import { boot } from './dom.mjs';

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };

function rig(file, opts){
  const r = boot(file, {stored:{'hito-input':'pen'}, ...opts});
  const { P, g, fire, tick } = r;
  // A one-stroke glyph would land on the first stroke instead of lifting. In
  // the field every load lands on the target, so aim the target through its
  // lock; in the workshop a plain load will do.
  // (an explicit load, not retarget(): in the stub the engine's first load waits
  // on a fonts promise nobody awaits, and retargeting to the glyph the engine
  // already names is a no-op on an engine that has loaded nothing)
  const want = P.LETTERS.findIndex(l => l[0] === 'あ');
  if (g.__field) g.__field.target.i = want;
  g.load(want);
  if (P.SEGS.length < 2) throw new Error(`${file}: could not load a multi-stroke glyph (got ${P.LETTERS[P.idx][0]})`);
  const px = i => P.denorm(P.PATH[i]);
  // the pen along path points a..b, as a real trace would go
  const along = (a, b) => {
    const s = px(a); fire('pointerdown', s.x, s.y, 'pen');
    for (let i = a + 1; i <= b; i++){ tick(8); const q = px(i); fire('pointermove', q.x, q.y, 'pen'); }
    const e = px(b); fire('pointerup', e.x, e.y, 'pen');
  };
  // a stroke in a corner of the canvas the glyph never reaches
  const nowhere = () => {
    fire('pointerdown', 6, 6, 'pen');
    for (let i = 1; i <= 8; i++){ tick(8); fire('pointermove', 6 + i * 4, 6 + (i % 2), 'pen'); }
    fire('pointerup', 40, 6, 'pen');
  };
  return { ...r, along, nowhere, px };
}

for (const file of process.argv.slice(2)){
  // ---- drop: the stray never happened, on the canvas or in the record
  {
    const { P, H, g, along, nowhere } = rig(file);
    if (!g.__field) ok(P.stray === 'drop', `${file}: the workshop's rule is ${P.stray}, not drop`);
    P.stray = 'drop';    // the games open on medium, whose rule is restart; drop is checked here
    nowhere();
    ok(P.strokes.length === 0, 'a stroke that went nowhere stayed on the canvas');
    ok(P.prog === 0 && P.segIdx === 0, `a stroke that went nowhere moved progress (prog ${P.prog}, seg ${P.segIdx})`);
    ok(H.note(true) === null, 'a stroke that went nowhere was written into the hand\'s record');
    const [a, b] = P.SEGS[0];
    along(a, b);
    ok(P.awaitLift === true && P.strokes.length === 1, `a real first stroke did not finish its segment (awaitLift ${P.awaitLift}, strokes ${P.strokes.length})`);
    nowhere();
    ok(P.strokes.length === 1, 'a stray after a good stroke took the good stroke with it, or stayed');
    // the lift before the stray already advanced to stroke two; the stray leaves it there, unbegun
    ok(P.segIdx === 1 && P.prog === P.SEGS[1][0] && P.awaitLift === false, `a stray after a good stroke rewound it (seg ${P.segIdx}, prog ${P.prog})`);
    ok(P.strayed === true, 'the engine did not say the stroke was dropped');
    const r = H.note(true);
    ok(r && r.strokes === 1, `the record has ${r && r.strokes} strokes: the stray is in it, or the good one is not`);
  }
  // ---- restart: in medium the character starts again
  {
    const { P, g, along, nowhere } = rig(file);
    P.stray = 'restart';
    const [a, b] = P.SEGS[0];
    along(a, b);
    ok(P.prog > 0, 'the first stroke did not register');
    nowhere();
    ok(P.prog === 0 && P.segIdx === 0 && P.strokes.length === 0, `medium did not restart the character on a stray (prog ${P.prog}, strokes ${P.strokes.length})`);
    along(a, b);
    ok(P.prog > 0, 'the character did not take a stroke after the restart');
    g.fizzle();
    ok(P.prog === 0 && P.segIdx === 0 && P.strokes.length === 0 && P.awaitLift === false, 'fizzle() did not restart the character');
  }
  // ---- the note the hand takes between the engine's lift and its own has the stroke that caused it
  // In a browser the engine's fizzle() is the hand's wrapper, so the note is
  // taken inside endStroke: the engine holds the stray, the hand has not heard
  // the lift yet. The stub cannot rebind the engine's own call, so the order
  // is played by hand: the engine's listener alone, then the note.
  {
    const { P, H, along, heard, fire, tick } = rig(file);
    P.stray = 'keep';
    const [a, b] = P.SEGS[0];
    along(a, b);
    fire('pointerdown', 6, 6, 'pen');
    for (let i = 1; i <= 8; i++){ tick(8); fire('pointermove', 6 + i * 4, 6, 'pen'); }
    const e = { type:'pointerup', pointerId:1, pointerType:'pen', clientX:40, clientY:6, buttons:1, pressure:.5, preventDefault(){}, getCoalescedEvents(){ return [e]; } };
    heard.pointerup[0](e);
    const r = H.note(false);
    ok(r && r.strokes === 2, `taken between the engine's lift and the hand's, the note has ${r && r.strokes} stroke(s), not 2`);
  }
  // ---- guided: covering the end closes the stroke; stopping well short does not
  if (rig(file).g.__field) {
    const { P, g, along, px, fire, tick } = rig(file);
    g.__field.setDifficulty('guided'); g.resize();
    g.__field.target.i = P.LETTERS.findIndex(l => l[0] === 'あ'); g.load(g.__field.target.i);
    ok(P.DRAG === true, 'guided did not switch the engine to dragging');
    const [a, b] = P.SEGS[0], sp = P.SEGLEN[0] / (b - a), R = P.R;
    const short = b - Math.round(0.6 * R / sp);          // the light 0.6R from the end: the finger covers it
    const far   = b - Math.round(1.6 * R / sp);          // 1.6R: it does not
    if (short > a + 2 && far > a + 2){
      along(a, far);
      ok(P.awaitLift === false, 'a finger 1.6 reaches short of the end closed the stroke');
      const { P: Q, g: h, along: go } = rig(file);
      h.__field.setDifficulty('guided'); h.resize();
      h.__field.target.i = Q.LETTERS.findIndex(l => l[0] === 'あ'); h.load(h.__field.target.i);
      go(a, short);
      ok(Q.awaitLift === true, `a finger covering the end (0.6R short) did not close the stroke (prog ${Q.prog} of ${b})`);
    }
    // and guided draws from every row, where easy at stage 1 does not
    ok(g.__field.roster().length === P.LETTERS.length, `guided offers ${g.__field.roster().length} of ${P.LETTERS.length} characters`);
    g.__field.setDifficulty('medium');
    ok(g.__field.roster().length < P.LETTERS.length, 'medium at stage 1 offers the whole chart');
  }
  // ---- a run that restarts on the character the engine is still celebrating starts it clean
  if (rig(file).g.__field) {
    const { P, g, along } = rig(file);
    g.__field.setDifficulty('medium'); g.resize();
    g.__field.target.i = P.LETTERS.findIndex(l => l[0] === 'あ'); g.load(g.__field.target.i);
    for (const [x, y] of P.SEGS) along(x, y);
    ok(P.done === true, 'tracing every stroke did not conjure あ');
    g.__field.restart();
    ok(P.done === false && P.prog === 0 && P.strokes.length === 0, `a restart left the engine celebrating (done ${P.done}, prog ${P.prog})`);
    // and a run that restarts mid-stroke starts the character clean too ("again" after the ward fell)
    along(P.SEGS[0][0], P.SEGS[0][1]);
    ok(P.prog > 0, 'the stroke after the restart did not register');
    g.__field.restart();
    ok(P.prog === 0 && P.strokes.length === 0, `a restart mid-trace kept the half-traced character (prog ${P.prog})`);
  }
  // ---- the heading gate: a loop is drawn by going round it, not by crossing it
  {
    const { P, g, fire, tick, px } = rig(file);
    const want = P.LETTERS.findIndex(l => l[0] === 'め');
    if (want >= 0){
      if (g.__field) g.__field.target.i = want;
      g.load(want);
      // the loop: the first stroke that crosses itself, and where
      const cross = (a, b, c, d) => { const x = (o, p, q) => (p.x-o.x)*(q.y-o.y) - (p.y-o.y)*(q.x-o.x); return x(a,b,c)*x(a,b,d) < 0 && x(c,d,a)*x(c,d,b) < 0; };
      let loop = null;
      for (const [a, b] of P.SEGS){
        for (let i = a; i < b && !loop; i++) for (let j = i + 2; j < b; j++)
          if (cross(P.PATH[i], P.PATH[i+1], P.PATH[j], P.PATH[j+1])){ loop = {a, b, i, j}; break; }
        if (loop) break;
      }
      ok(loop, 'め has no loop in the book');
      if (loop){
        const { a, b, i, j } = loop;
        // the strokes before the loop's, drawn properly, so the loop's stroke is the one in play
        const before_ = P.SEGS.filter(([x]) => x < a);
        const upTo = () => { for (const [x, y] of before_){ const s0 = px(x); fire('pointerdown', s0.x, s0.y, 'pen'); for (let k = x + 1; k <= y; k++){ tick(8); const q = px(k); fire('pointermove', q.x, q.y, 'pen'); } fire('pointerup', px(y).x, px(y).y, 'pen'); tick(200); } };
        upTo();
        // to the mouth of the loop along the path, then straight across it to where it closes
        const s = px(a); fire('pointerdown', s.x, s.y, 'pen');
        for (let k = a + 1; k <= i; k++){ tick(8); const q = px(k); fire('pointermove', q.x, q.y, 'pen'); }
        const from = px(i), to = px(j + 1);
        for (let k = 1; k <= 6; k++){ tick(8); fire('pointermove', from.x + (to.x-from.x)*k/6, from.y + (to.y-from.y)*k/6, 'pen'); }
        ok(P.prog < j - 2, `cutting across め's loop credited it (prog ${P.prog}, loop ${i}..${j})`);
        // sitting still on the far side advances nothing either
        const before = P.prog;
        for (let k = 0; k < 8; k++){ tick(8); fire('pointermove', to.x, to.y, 'pen'); }
        ok(P.prog === before, `a still pen advanced from ${before} to ${P.prog}`);
        fire('pointerup', to.x, to.y, 'pen');
        // and going round it, the loop is drawn (a fizzle restarts the same character at the same size;
        // a reload could roll another, and the loop's indices with it)
        g.fizzle(); upTo();
        const s2 = px(a); fire('pointerdown', s2.x, s2.y, 'pen');
        for (let k = a + 1; k <= b; k++){ tick(8); const q = px(k); fire('pointermove', q.x, q.y, 'pen'); }
        ok(P.prog >= b - 4, `going round the loop did not draw the stroke (prog ${P.prog} of ${b})`);
        fire('pointerup', px(b).x, px(b).y, 'pen');
      }
    }
  }
  // ---- the last farang of a stage is a boss: tougher, and traced with the shape hidden
  if (rig(file).g.__field) {
    const { P, g } = rig(file);
    const F = g.__field; F.setDifficulty('medium'); g.resize();
    F.restart();
    const n = F.stageCount(1);
    while (F.monsters.length < n) F.spawn();
    const boss = F.monsters[F.monsters.length - 1];
    ok(boss.boss === true && F.monsters.slice(0, -1).every(m => !m.boss), 'the last farang of the stage is not the boss, or another is');
    ok(boss.hp >= 3, `the boss takes ${boss.hp} hits`);
    F.monsters.splice(0, F.monsters.length - 1);   // leave only the boss, and aim at it
    F.retarget(true);
    ok(P.LETTERS[P.idx][0] === P.LETTERS[boss.i][0], 'the tracer is not on the boss');
    ok(P.SHADOW_MODE === 'faint', `the boss shows its full shape or none (${P.SHADOW_MODE})`);
    boss.hp = 1; F.hit(boss, false, false);
    F.spawn(); F.retarget(true);
    ok(P.SHADOW_MODE === 'strokes', `after the boss the shape did not come back (${P.SHADOW_MODE}; ${F.monsters.length} farang, tracer on ${P.LETTERS[P.idx][0]}, boss was ${P.LETTERS[boss.i][0]})`);
  }
  // ---- past the end without reaching it: the stroke starts over, not the character
  {
    const { P, g, fire, tick, px, along } = rig(file);
    const [a, b] = P.SEGS[0];
    const s = px(a); fire('pointerdown', s.x, s.y, 'pen');
    // six points short: the window can credit a few points ahead of the pen, and
    // three short was inside the end tolerance on some strokes, which closed it
    for (let k = a + 1; k <= b - 6; k++){ tick(8); const q = px(k); fire('pointermove', q.x, q.y, 'pen'); }
    ok(P.prog >= b - 9 && P.awaitLift === false, `did not get near the end, or closed early (prog ${P.prog} of ${b}, lift ${P.awaitLift})`);
    // then on past the end along its direction, a little to one side, outside the end tolerance
    const e = px(b), f = px(b - 3), tx = e.x - f.x, ty = e.y - f.y, tl = Math.hypot(tx, ty) || 1;
    const R = P.R * P.W, side = { x: -ty / tl, y: tx / tl };
    for (let k = 1; k <= 8; k++){ tick(8); fire('pointermove', e.x + tx / tl * R * 0.45 * k + side.x * R * 0.6, e.y + ty / tl * R * 0.45 * k + side.y * R * 0.6, 'pen'); }
    ok(P.prog === a && P.strayed === true, `passing the end did not start the stroke over (prog ${P.prog}, strayed ${P.strayed})`);
    fire('pointerup', e.x, e.y, 'pen');
    ok(P.strokes.length === 0, 'the discarded stroke stayed on the canvas');
    along(a, b);
    ok(P.awaitLift === true, 'the stroke drawn again did not complete');
  }
  // ---- keep: the old rule, every stroke stays
  {
    const { P, H, nowhere } = rig(file);
    P.stray = 'keep';
    nowhere();
    // (the field's own tidy still erases a stray from the canvas; the record is what keep is about)
    const r = H.note(true);
    ok(r && r.strokes === 1, `keep did not record the stroke (${r && r.strokes})`);
  }
}
console.log(fail ? `  ${fail} stray check(s) failed` : '  strays are dropped, restart the character in medium, or kept; a fizzle restarts');
process.exit(fail ? 1 : 0);
