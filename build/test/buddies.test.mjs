/* Buddies (v0.1.78): katakana's look-alikes, side by side.
 * Medium draws the shape asked for, so シ and ツ were copied, never told
 * apart. A general whose chart holds a look-alike group brings it along:
 * he carries one, a buddy carries each of the others behind a phrasebook,
 * the sketchbook asks for each of them with no shape shown, and two misses
 * on one bring its shape back faint. A group with a hint shows it once a
 * run, on its first miss. Hiragana and guided are untouched.
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
  // the sketchbook asks for one of them, and shows no shape
  F.retarget(true);
  const first = P.LETTERS[P.idx][0];
  ok(grp.includes(first), `the sketchbook asked for ${first}, not one of ${grp}`);
  ok(P.SHADOW_MODE === 'none', `a buddy was shown a shape (${P.SHADOW_MODE})`);
  ok(F.buddyAsk && !F.buddyAsk.hidden && F.buddyAsk.innerHTML.includes(`<b>${first}</b>`), `a bare sketchbook did not say to write ${first} (${F.buddyAsk && F.buddyAsk.innerHTML})`);
  // a miss: the hint, once; two misses: the shape comes back faint
  g.fizzle();
  ok(F.buddyMiss[P.idx] === 1, `a miss on ${first} was not counted (${JSON.stringify(F.buddyMiss)})`);
  ok(F.buddyHint && F.hinted[F.buddyHint] === 1, 'the first miss showed no hint');
  ok(/シ shi.*し.*ツ tsu.*つ/.test(F.buddyHint || ''), `the hint is not the twins' rule: ${F.buddyHint}`);
  F.retarget(true);
  ok(P.SHADOW_MODE === 'none', `one miss brought the shape back (${P.SHADOW_MODE})`);
  g.fizzle(); F.retarget(true); g.load(P.idx);
  ok(P.SHADOW_MODE === 'faint', `two misses did not bring the shape back faint (${P.SHADOW_MODE})`);
  ok(F.buddyAsk.hidden, 'the label stayed up over a faint shape');
  // written: the next one is asked for, still with no shape
  g.conjure(); F.retarget(true);
  const second = P.LETTERS[P.idx][0];
  ok(!F.buddyQ.includes(P.LETTERS.findIndex(L => L[0] === first)), `${first} was written and is still owed`);
  ok(second !== first && grp.includes(second), `after ${first} the sketchbook asked for ${second}`);
  ok(P.SHADOW_MODE === 'none', `the second buddy was shown a shape (${P.SHADOW_MODE})`);
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

if (fail){ console.log(`  ${fail} failure(s)`); process.exit(1); }
console.log('  a katakana general brings his look-alikes, asked for with no shape; two misses bring it back faint; the hint shows once; hiragana and guided are untouched');
