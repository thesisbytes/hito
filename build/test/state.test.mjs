/**
 * fizzle() restarts an attempt, so every per-attempt accumulator must clear
 * there — not only in load().
 *
 * travel did not. It carried across fizzles, so one bad attempt pushed
 * travel/PATHLEN past MAX_TRAVEL and every subsequent attempt was rejected
 * for wandering it had not done. The glyph stayed unpassable until something
 * called load(). This checks the whole class rather than that one variable.
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const s = readFileSync(target, 'utf8');

const fizzle = s.match(/function fizzle\(\)\{[\s\S]*?\n\}/)?.[0];
if (!fizzle) { console.log('  FAIL: no fizzle() found'); process.exit(1); }

// state that describes one attempt, and so must not survive a restart
const perAttempt = ['prog', 'segIdx', 'awaitLift', 'hit', 'smudge', 'offCount',
                    'travel', 'lastN'];
const missing = perAttempt.filter(v => !new RegExp(`\\b${v}\\b`).test(fizzle));

if (missing.length) {
  console.log(`  FAIL: fizzle() does not reset: ${missing.join(', ')}`);
  console.log('        these accumulate across attempts and will lock a glyph');
  process.exit(1);
}
console.log(`  fizzle() clears all ${perAttempt.length} per-attempt accumulators`);
