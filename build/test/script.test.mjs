/**
 * Which script the kana game opens on (v0.1.76).
 *
 * The URL decides first (the title page's level cards), then the file's own
 * name (hiragana-game.html and katakana-game.html are copies of the kana
 * game and still mean what they meant, even downloaded and opened alone),
 * then what was chosen last, which is all a page coming back from sign-in
 * has, since that return drops the query. A script not yet open is never
 * opened by any of them. One boot per process: each case is a child.
 *
 *   node build/test/script.test.mjs dist/kana-game-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';

const [target, mode, href, storeJson] = process.argv.slice(2);

if (mode === '--child'){
  const html = readFileSync(target, 'utf8');
  const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
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
      }, set(t,k,v){ t[k]=v; return true; } });
  globalThis.document = { getElementById:el, createElement:el, body:el(), addEventListener(){},
    documentElement:el(), fonts:{ready:Promise.resolve(), add(){}} };
  globalThis.window = globalThis;
  globalThis.addEventListener = () => {};
  globalThis.setTimeout = () => 0; globalThis.setInterval = () => 0; globalThis.clearTimeout = () => {};
  globalThis.Blob = class {};
  const store = JSON.parse(storeJson);
  globalThis.localStorage = { getItem: k => k in store ? store[k] : null, setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } };
  const u = new URL(href);
  Object.defineProperty(globalThis, 'location', { value: { protocol: u.protocol, origin: u.origin, href: u.href, pathname: u.pathname, search: u.search, hash: '', assign(){}, replace(){} }, configurable: true });
  globalThis.history = { replaceState(){} };
  globalThis.requestAnimationFrame = () => 0;
  globalThis.performance = { now: () => 0 };
  Object.defineProperty(globalThis, 'navigator', { value: { vibrate(){} }, configurable: true });
  globalThis.FontFace = class { load(){ return Promise.resolve(this); } };
  globalThis.atob = s => Buffer.from(s, 'base64').toString('binary');
  globalThis.matchMedia = () => ({ matches:false, addEventListener(){} });
  globalThis.devicePixelRatio = 1;
  globalThis.fetch = () => Promise.reject(new Error('offline'));
  // the engine's top-level functions, as a browser would put them on window
  const bridge = src => { const n = [...src.matchAll(/^function\s+([A-Za-z_$][\w$]*)/gm)].map(m => m[1]); return n.length ? `\n;${n.map(x => `try{window.${x}=${x};}catch(_){}`).join('')}\n` : ''; };
  new Function(blocks.map(b => b + bridge(b)).join('\n;\n'))();
  const F = globalThis.__field;
  process.stdout.write(JSON.stringify({ script: F.script, realm: F.realm, kept: (JSON.parse(store['hito-start'] || '{}') || {}).script }));
  process.exit(0);
}

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const open = { 'hito-ledger': JSON.stringify({ v:1, g:{}, days:{}, by:{}, runs:[], best:{ hiragana:{ wave:100, banished:1, at:1 } } }) };
const remember = s => JSON.stringify({ difficulty:'medium', sign:'kana', script:s });
const run = (href, store) => JSON.parse(execFileSync(process.execPath, [fileURLToPath(import.meta.url), target, '--child', href, JSON.stringify(store)], { encoding: 'utf8' }));
const W = 'https://hito.example/dist/';
const cases = [
  ['a new player, no say', W + 'kana-game.html', {}, 'hiragana'],
  ['the URL, once katakana is open', W + 'kana-game.html?script=katakana&go=medium', open, 'katakana'],
  ['the URL, before it is', W + 'kana-game.html?script=katakana', {}, 'hiragana'],
  ['the URL: both', W + 'kana-game.html?script=both', open, 'both'],
  ['the old katakana link', W + 'katakana-game.html', open, 'katakana'],
  ['the old katakana link, downloaded and opened alone', 'file:///sdcard/Download/katakana-game.html', open, 'katakana'],
  ['the old hiragana link beats what was chosen last', W + 'hiragana-game.html', { ...open, 'hito-start': remember('katakana') }, 'hiragana'],
  ['back from sign-in: what was chosen last', W + 'kana-game.html', { ...open, 'hito-start': remember('both') }, 'both'],
  ['remembered, but not open on this device', W + 'kana-game.html', { 'hito-start': remember('katakana') }, 'hiragana'],
  ['nonsense in the URL', W + 'kana-game.html?script=kanji', open, 'hiragana'],
];
const realm = { hiragana: 'hiragana', katakana: 'katakana-chars', both: 'kana-both' };
for (const [what, href, store, want] of cases){
  let got;
  try { got = run(href, store); } catch (e) { ok(false, `${what}: the page threw: ${String(e.stderr || e).split('\n').slice(0, 3).join(' ')}`); continue; }
  ok(got.script === want && got.realm === realm[want], `${what}: opened on ${got.script} (${got.realm}), not ${want}`);
  ok(got.kept === want, `${what}: saved ${got.kept}, not ${want}, for the return from sign-in`);
}
if (fail){ console.log(`  ${fail} script check(s) failed`); process.exit(1); }
console.log(`  ${cases.length} ways in: the URL, then the file's name, then what was chosen last; nothing opens a locked script, and the choice is saved for the return from sign-in`);
