/* Buddies (v0.1.78): katakana's look-alikes, side by side.
 * Medium draws the shape asked for, so シ and ツ were copied, never told
 * apart. A general whose chart holds a look-alike group brings it along:
 * he carries one, a buddy carries each of the others behind a phrasebook,
 * the sketchbook asks for each of them, and each one's shape is earned away
 * (v0.1.79): whole, faint after three clean traces in a row, gone after six,
 * whole again on a miss, counted in the hand's ledger. A group with a hint
 * shows it once a run, on its first miss. Hiragana and guided are untouched.
 *   node build/test/buddies.test.mjs dist/kana-game-vX.Y.Z.html
 */
import { boot } from './dom.mjs';
let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const file = process.argv[2];

// hiragana climbed (katakana open) and every row of every script open
const ledger = JSON.stringify({ v:1, g:{}, days:{}, by:{}, runs:[], best:{
  hiragana:{ wave:100, banished:1, at:1 }, 'katakana-chars':{ wave:100, banished:1, at:1 }, 'kana-both':{ wave:100, banished:1, at:1 } } });

function rig(script, { diff = 'medium', sore = null } = {}){
  const r = boot(file, { stored: { 'hito-ledger': ledger, 'hito-share':'0', 'hito-input':'pen' } });
  const { g } = r, F = g.__field;
  if (sore && g.__hand) g.__hand.shaky = c => c === sore;
  ok(F.setScript(script), `could not switch to ${script}`);
  F.setDifficulty(diff); F.pickStage(0);    // the tower: a general every tenth wave
  F.restart();
  const len = F.stageLen();
  while (!F.monsters.some(m => m.boss)) F.spawn();
  return { ...r, F, len, chars: () => F.monsters.map(m => r.P.LETTERS[m.i][0]) };
}

const BUDS = ['シツ', 'ソン', 'クケタ', 'ウワ', 'スヌ', 'チテ', 'コユロ'];
const groupOf = c => BUDS.find(b => b.includes(c));

// hiragana: a general alone
{ const r = rig('hiragana');
  ok(!r.F.monsters.some(m => m.buddy), `a hiragana general brought buddies (${r.chars().join('')})`);
  ok(r.F.buddyQ.length === 0, 'a hiragana general left something owed'); }

// guided: no buddies (and no shape to hide)
{ const r = rig('katakana', { diff:'guided' });
  ok(!r.F.monsters.some(m => m.buddy), 'a guided general brought buddies'); }

// katakana, with シ biting: the shin buddies
{ const r = rig('katakana', { sore:'シ' }); const { F, P, g } = r;
  const gen = F.monsters.find(m => m.boss), buds = F.monsters.filter(m => m.buddy);
  const gc = P.LETTERS[gen.i][0], grp = groupOf(gc) || "";
  ok(grp === 'シツ', `with シ shaky the general carried ${gc}, not one of the shin buddies`);
  ok(gen.pals === 'the shin buddies', `the general is named ${gen.pals}`);
  ok(buds.length === grp.length - 1, `${buds.length} buddies for ${grp}`);
  ok(buds.every(m => m.block === 1 && m.hp === 1 && grp.includes(P.LETTERS[m.i][0]) && P.LETTERS[m.i][0] !== gc),
     `the buddies are not the rest of ${grp} behind a phrasebook (${buds.map(m => P.LETTERS[m.i][0] + m.block + '/' + m.hp).join(' ')})`);
  ok(F.buddyQ.length === grp.length, `owed ${F.buddyQ.length}, expected ${grp.length}`);
  // the sketchbook asks for one of them, and shows what this hand has earned:
  // a fresh hand, the whole shape (not even the general's faint), and a count
  F.retarget(true);
  const first = P.LETTERS[P.idx][0], H = g.__hand, fi = P.idx;
  const ask = () => F.kanaTag.innerHTML;
  const sure = c => (H.ledger.g[c] && H.ledger.g[c].sure) || 0;
  const setSure = (c, n) => { (H.ledger.g[c] = H.ledger.g[c] || {n:0, clean:0, zaps:0, fizz:0, ms:0, rt:[], tr:0}).sure = n; };
  ok(grp.includes(first), `the sketchbook asked for ${first}, not one of ${grp}`);
  ok(P.SHADOW_MODE === 'strokes', `a buddy this hand has never written was not shown its shape (${P.SHADOW_MODE})`);
  ok(F.kanaTag && !F.kanaTag.hidden && ask().includes(`<b>${first}</b>`) && /3 clean and it fades/.test(ask()), `the label did not say ${first} and 3 to fade (${ask()})`);
  // earned: three clean in a row and it is faint, six and it is gone
  setSure(first, 3); F.retarget(true); g.load(fi);
  ok(P.SHADOW_MODE === 'faint' && /3 clean and it's gone/.test(ask()), `three clean did not fade ${first} (${P.SHADOW_MODE}, ${ask()})`);
  setSure(first, 6); F.retarget(true); g.load(fi);
  ok(P.SHADOW_MODE === 'none' && /write <b>.<\/b> · [a-z]+ · no shape/.test(ask()), `six clean did not take ${first}'s shape away (${P.SHADOW_MODE}, ${ask()})`);
  // a miss, with ink on the page as a real one has: the ledger's run is back to
  // nothing and the shape is back in full; and the twins' hint, once
  const ink = () => P.setStrokes([[{x:150, y:150, t:0}, {x:170, y:160, t:40}, {x:190, y:175, t:80}]]);
  ink(); g.fizzle(); F.retarget(true); g.load(fi);
  ok(sure(first) === 0, `a miss left ${first}'s run of clean traces at ${sure(first)}`);
  ok(P.SHADOW_MODE === 'strokes', `a miss did not bring ${first}'s shape straight back (${P.SHADOW_MODE})`);
  ok(F.buddyHint && F.hinted[F.buddyHint] === 1, 'the first miss showed no hint');
  ok(/シ shi.*し.*ツ tsu.*つ/.test(F.buddyHint || ''), `the hint is not the twins' rule: ${F.buddyHint}`);
  // landed after that miss, it is not clean, and the run stays where it was
  setSure(first, 2); ink(); g.conjure();
  ok(sure(first) === 2, `a trace landed after a miss counted as clean (${sure(first)})`);
  // written: the next one is asked for, with its own count
  F.retarget(true);
  const second = P.LETTERS[P.idx][0];
  ok(F.buddyShape(P.idx) === (sure(second) >= 6 ? 'none' : sure(second) >= 3 ? 'faint' : 'strokes'), `${second} was not shown its own count`);
  // and a clean trace counts one, in the ledger
  { const before = sure(second); ink(); g.conjure();
    ok(sure(second) === before + 1, `a clean trace of ${second} did not count (${before} -> ${sure(second)})`); }
  ok(!F.buddyQ.includes(fi), `${first} was written and is still owed`);
  ok(second !== first && grp.includes(second), `after ${first} the sketchbook asked for ${second}`);
  // not a buddy any more: the general's faint rule is back for it
  ok(F.buddyShape(fi) === null, `${first}, written, is still judged as a buddy`);
  // the hint is once a run
  g.fizzle();
  ok(Object.keys(F.hinted).length === 1, 'the hint was counted twice');
  F.restart();
  ok(F.buddyQ.length === 0 && Object.keys(F.hinted).length === 0, 'a new run kept the buddies or the hint'); }

// katakana, any group: always two or more, all from one group, all open
{ let seen = new Set();
  for (let k = 0; k < 12; k++){ const r = rig('katakana');
    const gen = r.F.monsters.find(m => m.boss), gc = r.P.LETTERS[gen.i][0], grp = groupOf(gc);
    const buds = r.F.monsters.filter(m => m.buddy).map(m => r.P.LETTERS[m.i][0]);
    ok(grp && buds.length >= 1 && buds.every(c => grp.includes(c)), `a general on ${gc} brought ${buds.join('')}`);
    if (grp) seen.add(grp); }
  ok(seen.size >= 2, `twelve generals brought only ${[...seen].join(' ')}`); }

// both: the buddies are katakana, the hiragana around them are as ever
{ const r = rig('both');
  ok(r.F.monsters.filter(m => m.buddy).every(m => /[゠-ヿ]/.test(r.P.LETTERS[m.i][0])), 'a buddy in both was not katakana'); }

// the tag (v0.1.80): what is being stroked, kana and romaji, in practice
// (guided) and in the game, hiragana and katakana; the voice hook hears each
// character once; a bare buddy under a romaji sign does not give the kana away
for (const [script, diff] of [['hiragana', 'guided'], ['katakana', 'guided'], ['hiragana', 'medium'], ['katakana', 'medium']]){
  const r = rig(script, { diff }); const { F, P } = r;
  const heard = []; F.voice.say = (c, rom) => heard.push(c + rom);
  F.retarget(true);
  const L = P.LETTERS[P.idx];
  ok(!F.kanaTag.hidden && F.kanaTag.innerHTML.startsWith(`<b>${L[0]}</b> · ${L[2]}`), `${script} ${diff}: the tag says ${F.kanaTag.innerHTML}, not ${L[0]} · ${L[2]}`);
  const other = F.roster().find(k => k !== P.idx); F.ask(other); F.retarget(true); F.retarget(true);
  ok(heard.length === 1 && heard[0] === P.LETTERS[other][0] + P.LETTERS[other][2], `${script} ${diff}: the voice heard ${JSON.stringify(heard)} for ${P.LETTERS[other][0]}`);
}
{ const r = rig('katakana', { sore:'シ' }); const { F, P, g } = r;
  F.setSign('romaji'); F.retarget(true);
  const c = P.LETTERS[P.idx][0], e = g.__hand.ledger.g[c] = g.__hand.ledger.g[c] || {n:0, clean:0, zaps:0, fizz:0, ms:0, rt:[], tr:0};
  e.sure = 6; F.retarget(true); g.load(P.idx);
  ok(P.SHADOW_MODE === 'none' && !F.kanaTag.innerHTML.includes(c) && F.kanaTag.innerHTML.includes(`<b>${P.LETTERS[P.idx][2]}</b>`), `a bare buddy under the romaji sign showed ${F.kanaTag.innerHTML}`); }

if (fail){ console.log(`  ${fail} failure(s)`); process.exit(1); }
console.log('  a katakana general brings his look-alikes; each one\'s shape fades with clean traces in a row and comes back whole on a miss; the hint shows once; hiragana and guided are untouched; the tag names what is stroked, kana and romaji');
