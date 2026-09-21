/**
 * A layer must not reuse one of the engine's names.
 *
 * The layers are appended scripts that reach the engine through its globals.
 * Inside a layer's own function, declaring `ink` or `loop` does not replace
 * the engine's — it hides it, from that layer only, silently. Twice that has
 * been a bug that every other test passed:
 *
 *   - v0.1.39 called the run's currency `ink`. Guided mode wipes the pen's mark
 *     with the engine's `ink` context, so guided threw on every repaint.
 *   - tidy() called `loop()` for the engine's particle loop and got the field's
 *     own game loop, so every tidied stray started another permanent game
 *     loop, and the puff it was for never animated. That one shipped for months.
 *
 * The stubbed DOM cannot see either: its contexts answer to any name. So this
 * reads the source instead.
 *
 *   node build/test/shadow.test.mjs dist/<build>.html [...]
 */
import { readFileSync } from 'fs';

// `$` is the same one-line getElementById in both, and is the only exception.
const ALLOWED = new Set(['$']);

function declared(src, indent){
  const out = new Set();
  const strip = s => s.replace(/\([^()]*\)|\[[^\[\]]*\]|\{[^{}]*\}|'[^']*'|"[^"]*"|`[^`]*`/g, '');
  for (const m of src.matchAll(new RegExp(`^${indent}(?:async\\s+)?function\\s+([A-Za-z_$][\\w$]*)`, 'gm'))) out.add(m[1]);
  for (const m of src.matchAll(new RegExp(`^${indent}(?:let|const|var)\\s+(.+)$`, 'gm'))){
    let line = m[1]; for (let i = 0; i < 4; i++) line = strip(line);
    for (const part of line.split(',')){
      const n = part.match(/^\s*([A-Za-z_$][\w$]*)\s*(=|;|$)/);
      if (n) out.add(n[1]);
    }
  }
  return out;
}

let fail = 0, checked = 0;
for (const file of process.argv.slice(2)){
  const blocks = [...readFileSync(file, 'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
  const engine = blocks.reduce((a, b) => b.length > a.length ? b : a, '');
  const E = declared(engine, '');
  if (E.size < 50){ console.log(`  FAIL: only found ${E.size} engine names in ${file} — the scan is broken`); fail++; continue; }
  for (const b of blocks){
    if (b === engine || !/^\(function\(\)\{/m.test(b)) continue;
    checked++;
    const clash = [...declared(b, '  ')].filter(n => E.has(n) && !ALLOWED.has(n));
    if (clash.length){
      const what = (b.match(/\/\* ---- ([^-\n]+?) -/) || [, 'a layer'])[1].trim();
      console.log(`  FAIL: ${what} in ${file} hides the engine's ${clash.join(', ')}`); fail++;
    }
  }
}
if (fail) { console.log(`  ${fail} shadowing problem(s)`); process.exit(1); }
console.log(`  no layer hides an engine name (${checked} layers read)`);
