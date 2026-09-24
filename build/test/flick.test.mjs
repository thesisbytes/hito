/* A stroke shorter than a fingertip is a flick.
 * 点々 are two strokes a sixth of the glyph long. By finger, voiced kana
 * fizzled 33% against 13% for the rest, with the ticks drawn as short
 * dashes a reader would pass — and a tick that fell short did not fail the
 * tick, it restarted the whole character. For the finger's profile a stroke
 * under `flick` of the canvas is judged as a flick: started at its start,
 * moved a third of its way in its direction, ended near its end. One that
 * went nowhere is dropped, never a restart. The pen has no flicks.
 *   node build/test/flick.test.mjs dist/hiragana-game-vX.Y.Z.html
 */
import { boot } from './dom.mjs';
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };

function rig(file, input){
  const r = boot(file, {stored:{'hito-input':input, 'hito-share':'0'}, touchPoints: input === 'finger' ? 5 : 0, coarse: input === 'finger'});
  const { P, g, fire, tick } = r;
  const want = P.LETTERS.findIndex(l => l[0] === 'だ');
  if (want < 0) throw new Error(`${file}: no だ to trace`);
  if (g.__field) g.__field.ask(want);
  g.load(want);
  const pt = input === 'finger' ? 'touch' : 'pen';
  const px = i => P.denorm(P.PATH[i]);
  const along = (a, b, f = q => q) => {
    const s = f(px(a)); fire('pointerdown', s.x, s.y, pt);
    for (let i = a + 1; i <= b; i++){ tick(12); const q = f(px(i)); fire('pointermove', q.x, q.y, pt); }
    const e = f(px(b)); fire('pointerup', e.x, e.y, pt); tick(60);
  };
  const body = () => { for (let i = 0; i < P.SEGS.length - 2; i++){ const [a, b] = P.SEGS[i]; along(a, b); } };
  return { ...r, along, px, pt, body, tickSeg: P.SEGS.length - 2 };
}
const short = (r, a, b) => r.along(a, a + Math.max(1, Math.round((b - a) * 0.6)));
const off = (r, a, b) => r.along(a, b, q => ({x: q.x - 14, y: q.y + 14}));
const dab = (r, a) => { const s = r.px(a); r.fire('pointerdown', s.x, s.y, r.pt); for (let i = 1; i <= 3; i++){ r.tick(12); r.fire('pointermove', s.x + i, s.y + i, r.pt); } r.fire('pointerup', s.x + 3, s.y + 3, r.pt); r.tick(60); };
const back = (r, a, b) => { const s = r.px(b); r.fire('pointerdown', s.x, s.y, r.pt); for (let i = b - 1; i >= a; i--){ r.tick(12); const q = r.px(i); r.fire('pointermove', q.x, q.y, r.pt); } const e = r.px(a); r.fire('pointerup', e.x, e.y, r.pt); r.tick(60); };

for (const file of process.argv.slice(2)){
  // A landed stroke waits for the lift: strokes grows by one and awaitLift is set. A dropped
  // stroke leaves strokes as it was. A restart empties them.
  const landed = (P, n) => P.strokes.length === n + 1 && P.awaitLift === true;
  const dropped = (P, n) => P.strokes.length === n && P.awaitLift === false;
  const state = P => `strokes ${P.strokes.length}, seg ${P.segIdx}, awaitLift ${P.awaitLift}`;
  // finger: a short tick lands, an offset tick lands, a dab and a backwards tick are dropped and nothing restarts
  { const r = rig(file, 'finger'); const { P } = r; r.body();
    const seg = r.tickSeg, [a, b] = P.SEGS[seg];
    ok(landed(P, seg - 1), `test setup: the body of だ did not land (${state(P)})`);
    short(r, a, b);
    ok(landed(P, seg), `by finger, a tick drawn to 60% did not land (${state(P)})`); }
  { const r = rig(file, 'finger'); const { P } = r; r.body(); const seg = r.tickSeg, [a, b] = P.SEGS[seg];
    off(r, a, b);
    ok(landed(P, seg), `by finger, a tick drawn 14px off did not land (${state(P)})`); }
  { const r = rig(file, 'finger'); const { P } = r; r.body(); const seg = r.tickSeg, [a, b] = P.SEGS[seg];
    dab(r, a);
    ok(dropped(P, seg), `by finger, a dab on a tick ${P.strokes.length === 0 ? 'restarted the character' : 'was taken as the tick'} (${state(P)})`);
    back(r, a, b);
    ok(dropped(P, seg), `by finger, a tick drawn backwards ${P.strokes.length === 0 ? 'restarted the character' : 'was taken as the tick'} (${state(P)})`);
    r.along(a, b);
    ok(landed(P, seg), `after two dropped tries the real tick did not land (${state(P)})`); }
  // pen: no flicks. A short tick is a stroke that went nowhere, and the rule for that stands (restart in the games)
  { const r = rig(file, 'pen'); const { P } = r; r.body(); const seg = r.tickSeg, [a, b] = P.SEGS[seg];
    short(r, a, b);
    ok(!landed(P, seg), `by pen, a tick drawn to 60% was taken as the tick: the pen has no flicks (${state(P)})`); }
  console.log(`  ${file.replace(/^.*\//, '')}: ${fail ? fail + ' failures' : 'a flick is a flick by finger and a stroke by pen'}`);
}
process.exit(fail ? 1 : 0);
