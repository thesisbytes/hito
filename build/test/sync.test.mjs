/**
 * Sync must never be able to hurt the game.
 *
 * The project's constraint is that every deliverable opens from a double-click,
 * offline, on a tablet. A sync layer is exactly the kind of addition that
 * erodes that quietly — one unguarded fetch, one throw on a missing
 * localStorage, and the game no longer starts on a plane. So what is checked
 * here is mostly absence: no network when none is configured, no throw when
 * storage is unavailable, no loss when the request fails.
 *
 * The queue cap matters more than it looks. A device offline for a month must
 * not fill its own storage and take mastery down with it.
 *
 *   node build/test/sync.test.mjs dist/hiragana-vX.Y.Z.html
 */
import { readFileSync } from 'fs';
const target = process.argv[2];
const html = readFileSync(target, 'utf8');
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
const layer = blocks.find(b => b.includes("'hito-outbox'") || b.includes('hito-outbox'));

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
ok(layer, 'no sync layer in this build');
if (!layer) process.exit(1);

// Run the layer alone against a controllable environment.
function boot({ endpoint = '', storage = true, online = true, fetchImpl } = {}){
  const store = {};
  const env = {
    localStorage: storage ? {
      getItem: k => (k in store ? store[k] : null),
      setItem: (k, v) => { store[k] = String(v); },
      removeItem: k => { delete store[k]; },
    } : {
      // private mode: every access throws, which is a real browser behaviour
      getItem(){ throw new Error('denied'); },
      setItem(){ throw new Error('denied'); },
      removeItem(){ throw new Error('denied'); },
    },
    navigator: { onLine: online },
    addEventListener(){},
    document: { addEventListener(){}, hidden: false },
    __SYNC_CFG: { endpoint, batch: 40, cap: 500 },
    calls: [],
  };
  env.window = env;
  env.fetch = fetchImpl || ((url, opt) => {
    env.calls.push({url, body: JSON.parse(opt.body)});
    const ids = JSON.parse(opt.body).events.map(e => e.id);
    return Promise.resolve({ok:true, json: () => Promise.resolve({accepted: ids})});
  });
  const fn = new Function('window','localStorage','navigator','addEventListener',
                          'document','fetch','__SYNC_CFG', layer);
  fn(env, env.localStorage, env.navigator, env.addEventListener,
     env.document, env.fetch, env.__SYNC_CFG);
  return {env, store, sync: env.__sync};
}

// ---- with no endpoint, nothing goes anywhere
{
  const {env, sync} = boot();
  ok(sync, 'the layer exposed no interface');
  ok(sync.enabled === false, 'sync reports enabled with no endpoint configured');
  sync.record('flag', {glyph:'ぬ'});
  ok(env.calls.length === 0, 'a build with no endpoint made a network request');
  ok(sync.pending === 1, 'the event was not recorded locally');
}

// ---- a device id is stable across reloads
{
  const first = boot({endpoint:'https://x/y'});
  const id = first.sync.device;
  ok(/^d[0-9a-f]{16}$/.test(id), `device id looks wrong: ${id}`);
  // re-boot against the same storage
  const store = first.store;
  ok(store['hito-device'] === id, 'the device id was not persisted');
}

// ---- events survive a reload
{
  const a = boot();
  a.sync.record('flag', {glyph:'ぬ'});
  a.sync.record('banish', {glyph:'き'});
  const saved = JSON.parse(a.store['hito-outbox']);
  ok(saved.length === 2, `outbox persisted ${saved.length} events, expected 2`);
  ok(saved.every(e => e.id && e.kind && e.at), 'a persisted event is missing id/kind/at');
  ok(new Set(saved.map(e => e.id)).size === 2, 'event ids collide');
}

// ---- offline: queued, not lost
{
  const {env, sync} = boot({endpoint:'https://x/y', online:false});
  sync.record('flag', {glyph:'ぬ'});
  ok(env.calls.length === 0, 'a request was attempted while offline');
  ok(sync.pending === 1, 'the event was dropped instead of queued');
}

// ---- a failed request loses nothing
const failing = boot({endpoint:'https://x/y', fetchImpl: () => Promise.reject(new Error('down'))});
failing.sync.record('flag', {glyph:'ぬ'});

// ---- a successful flush drains only what the server accepted
const partial = boot({endpoint:'https://x/y', fetchImpl: (url, opt) => {
  const ids = JSON.parse(opt.body).events.map(e => e.id);
  return Promise.resolve({ok:true, json: () => Promise.resolve({accepted: ids.slice(0,1)})});
}});
partial.sync.record('flag', {glyph:'ぬ'});
partial.sync.record('flag', {glyph:'き'});

// ---- private mode: storage throws on every access, and nothing breaks
let denied = null;
try { denied = boot({endpoint:'https://x/y', storage:false}); }
catch (e) { ok(false, `the layer threw when localStorage is denied: ${e.message}`); }
if (denied){
  ok(denied.sync, 'no interface when storage is denied');
  let threw = null;
  try { denied.sync.record('flag', {glyph:'ぬ'}); } catch(e){ threw = e; }
  ok(!threw, `record() threw with storage denied: ${threw && threw.message}`);
  ok(/^d[0-9a-f]{16}$/.test(denied.sync.device), 'no usable device id without storage');
}

// ---- the queue is capped, oldest dropped
{
  const capped = boot();
  capped.env.__SYNC_CFG.cap = 500;
  for (let i = 0; i < 620; i++) capped.sync.record('banish', {n:i});
  ok(capped.sync.pending === 500,
     `queue grew to ${capped.sync.pending}; an offline month would fill storage`);
  const kept = JSON.parse(capped.store['hito-outbox']);
  ok(kept[kept.length-1].body.n === 619, 'the newest event was dropped instead of the oldest');
  ok(kept[0].body.n === 120, `oldest kept is ${kept[0].body.n}, expected 120`);
}

await new Promise(r => setTimeout(r, 20));
ok(failing.sync.pending === 1,
   `a failed flush dropped the event (pending ${failing.sync.pending})`);
ok(partial.sync.pending === 1,
   `partial acceptance left ${partial.sync.pending} queued, expected 1 to remain`);

if (fail) { console.log(`  ${fail} sync check(s) failed`); process.exit(1); }
console.log('  no endpoint means no network, events survive reload and failure, '
  + 'storage denial is harmless, queue capped');
