/**
 * Guest, or signed in — and never required.
 *
 * What is defended here is mostly what signing in must NOT be able to do:
 * make a request from a file, leave a token in the address bar, sign somebody
 * out because the train went into a tunnel, let one device unlearn what
 * another learned, write a row anyone else can read, or throw into the game.
 *
 *   node build/test/account.test.mjs index.html dist/<build>.html
 */
import { readFileSync } from 'fs';

let fail = 0;
const ok = (c, m) => { if (!c) { console.log(`  FAIL: ${m}`); fail++; } };
const core = file => {
  const b = [...readFileSync(file, 'utf8').matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1])
    .find(s => s.includes('guest, or signed in'));
  if (!b) { console.log(`  FAIL: no account layer in ${file}`); process.exit(1); }
  return b;
};

function boot(src, { href = 'https://hito.example/dist/game.html', stored = {}, routes = {}, offline = false, hand = true } = {}){
  const store = {...stored}, calls = [], url = new URL(href);
  let replaced = null, assigned = null;
  const env = {
    __ACCOUNT_CFG: { endpoint: 'https://api.example/v1', project: 'P', db: 'hito', table: 'saves', saveMs: 5 },
    localStorage: { getItem: k => k in store ? store[k] : null, setItem: (k, v) => { store[k] = String(v); }, removeItem: k => { delete store[k]; } },
    location: { protocol: url.protocol, origin: url.origin, pathname: url.pathname, search: url.search, hash: '', assign: u => { assigned = u; } },
    history: { replaceState: (_a, _b, u) => { replaced = u; } },
    document: { addEventListener(){}, hidden: false },
    setTimeout: (f, ms) => setTimeout(f, ms), URLSearchParams,
    MASTERY: { 'ぬ': 2 }, persisted: 0,
  };
  env.persistM = () => { env.persisted++; };
  env.window = env;
  env.__sync = { device: 'd0123456789abcdef' };
  let ledger = { v:1, g: { 'ぬ': { n:2, fizz:0 } }, days: {}, by: {} };
  if (hand) env.__hand = {
    exportText: () => JSON.stringify({ hito:'ledger', ledger }),
    importText: t => { const o = JSON.parse(t); for (const [c, e] of Object.entries(o.ledger.g)) if (!ledger.g[c] || (e.n||0) > (ledger.g[c].n||0)) ledger.g[c] = e; return true; },
  };
  env.fetch = (u, opt) => {
    const path = u.replace('https://api.example/v1', ''), key = `${opt.method} ${path}`;
    calls.push({ key, headers: opt.headers, body: opt.body ? JSON.parse(opt.body) : undefined, credentials: opt.credentials });
    if (offline) return Promise.reject(new Error('offline'));
    const r = routes[key] || { status: 404, body: { message: 'nope' } };
    return Promise.resolve({ status: r.status, ok: r.status >= 200 && r.status < 300,
      headers: { get: h => h === 'x-fallback-cookies' ? (r.cookie || null) : null },
      text: () => Promise.resolve(JSON.stringify(r.body ?? null)) });
  };
  let threw = null;
  try {
    new Function('window','localStorage','location','history','document','fetch','setTimeout','URLSearchParams','MASTERY','persistM','__ACCOUNT_CFG',
      src)(env, env.localStorage, env.location, env.history, env.document, env.fetch, env.setTimeout, URLSearchParams, env.MASTERY, env.persistM, env.__ACCOUNT_CFG);
  } catch (e) { threw = e; }
  return { A: env.__account, env, store, calls, threw, get replaced(){ return replaced; }, get assigned(){ return assigned; }, get ledger(){ return ledger; } };
}
const settle = () => new Promise(r => setTimeout(r, 40));
const ME = { status: 200, body: { $id: 'u1', name: 'Scribe', email: 'scribe@example.invalid' } };

for (const file of process.argv.slice(2)){
  const src = core(file);

  // ---- from a file there is no sign-in, and no request of any kind
  {
    const g = boot(src, { href: 'file:///sdcard/hito/hiragana-game.html?userId=u1&secret=s' });
    await settle();
    ok(!g.threw && g.A, `${file}: the layer threw or exposed nothing from a file`);
    ok(g.A.can === false && g.A.state === 'guest', 'a build opened from a file offers sign-in');
    ok(g.calls.length === 0, `a build opened from a file made ${g.calls.length} request(s)`);
    ok(g.A.signIn() === false && !g.assigned, 'signIn() went somewhere from a file');
  }

  // ---- a guest on the web makes no request either, until they ask
  {
    const g = boot(src);
    await settle();
    ok(g.A.can === true && g.calls.length === 0, `a guest who never signed in made ${g.calls.length} request(s)`);
    g.A.signIn();
    ok(/\/account\/tokens\/oauth2\/google\?project=P&success=https%3A%2F%2Fhito\.example%2Fdist%2Fgame\.html&failure=/.test(g.assigned || ''), `sign-in goes to ${g.assigned}`);
  }

  // ---- back from the provider: the token is used once and leaves the address bar
  {
    const g = boot(src, { href: 'https://hito.example/?userId=u1&secret=s3cret', routes: {
      'POST /account/sessions/token': { status: 201, body: { $id: 'sess' }, cookie: '{"a_session":"x"}' },
      'GET /account': ME,
      'GET /tablesdb/hito/tables/saves/rows/u1': { status: 404, body: {} },
      'POST /tablesdb/hito/tables/saves/rows': { status: 201, body: {} } } });
    ok(g.replaced === '/', `the token is still in the address after load (replaceState got ${g.replaced})`);
    await settle();
    ok(g.A.state === 'signed' && g.A.user && g.A.user.name === 'Scribe', `after the exchange the state is ${g.A.state}`);
    ok(g.calls[0].body.userId === 'u1' && g.calls[0].body.secret === 's3cret' && g.calls[0].credentials === 'include', 'the token was not exchanged for a session');
    ok(g.store['hito-session'] === '{"a_session":"x"}', 'the fallback cookie was not kept: on most browsers that is the only session there is');
    ok(g.calls.slice(1).every(c => c.headers['X-Fallback-Cookies'] === '{"a_session":"x"}'), 'later requests did not send the fallback cookie back');
    ok(!/scribe@/.test(JSON.stringify(g.store)), 'the player\'s email address was written to localStorage');
    const made = g.calls.find(c => c.key === 'POST /tablesdb/hito/tables/saves/rows');
    ok(made, 'a first sign-in did not create the save');
    if (made){
      ok(made.body.rowId === 'u1', 'the save is not filed under the player');
      ok(JSON.stringify(made.body.permissions) === JSON.stringify(['read("user:u1")','update("user:u1")','delete("user:u1")']), `the save's permissions are ${JSON.stringify(made.body.permissions)}`);
      ok(made.body.data.devices.includes('d0123456789abcdef'), 'this device was not linked to the player');
      ok(JSON.parse(made.body.data.data).mastery['ぬ'] === 2, 'mastery is not in the save');
    }
  }

  // ---- a save that exists is merged, then written back: nothing is unlearned
  {
    const remote = { hito:'save', v:1, ledger: { g: { 'ぬ': { n:9 }, 'き': { n:4 } } }, mastery: { 'ぬ': 1, 'き': 6, ['x'.repeat(40)]: 5, 'あ': 'lots' } };
    const g = boot(src, { stored: { 'hito-user': JSON.stringify({ id:'u1', name:'Scribe' }), 'hito-session': 'c' }, routes: {
      'GET /account': ME,
      'GET /tablesdb/hito/tables/saves/rows/u1': { status: 200, body: { data: JSON.stringify(remote), devices: ['d1111111111111111'] } },
      'PATCH /tablesdb/hito/tables/saves/rows/u1': { status: 200, body: {} } } });
    await settle();
    ok(g.ledger.g['ぬ'].n === 9 && g.ledger.g['き'].n === 4, 'the fuller ledger did not win the merge');
    ok(g.env.MASTERY['き'] === 6, 'mastery learned on another device did not arrive');
    ok(g.env.MASTERY['ぬ'] === 2, `mastery went DOWN to ${g.env.MASTERY['ぬ']}: a device unlearned something`);
    ok(!('x'.repeat(40) in g.env.MASTERY) && !('あ' in g.env.MASTERY), 'junk in the save reached mastery');
    ok(g.env.persisted >= 1, 'merged mastery was not persisted');
    const w = g.calls.find(c => c.key.startsWith('PATCH'));
    ok(w && JSON.parse(w.body.data.data).mastery['ぬ'] === 2 && JSON.parse(w.body.data.data).mastery['き'] === 6, 'the merged result was not written back');
    ok(w && w.body.data.devices.length === 2, 'the other device was dropped from the save');
    ok(w && !w.body.permissions, 'an update rewrote the save\'s permissions');
  }

  // ---- a tunnel is not a sign-out; a real no is
  {
    const stored = { 'hito-user': JSON.stringify({ id:'u1', name:'Scribe' }), 'hito-session': 'c' };
    const t = boot(src, { stored, offline: true });
    await settle();
    ok(!t.threw && t.A.user && t.A.state === 'signed', 'losing the network signed the player out');
    const no = boot(src, { stored, routes: { 'GET /account': { status: 401, body: {} } } });
    await settle();
    ok(!no.A.user && no.A.state === 'guest' && !no.store['hito-session'], 'an expired session was kept');
  }

  // ---- a failed sign-in says so and cleans up after itself
  {
    const f = boot(src, { href: 'https://hito.example/?signin=failed' });
    await settle();
    ok(f.replaced === '/' && /did not go through/.test(f.A.note) && f.calls.length === 0, 'a failed sign-in was not reported, or left its mark in the address');
  }

  // ---- touch() saves later, once, and only for somebody signed in
  {
    const g = boot(src); g.A.touch(); await settle();
    ok(g.calls.length === 0, 'a guest\'s progress was sent somewhere');
    // a build with no tracer in it (the title screen) has nothing to merge and must not mind
    const bare = boot(src, { hand: false, stored: { 'hito-user': JSON.stringify({ id:'u1', name:'S' }) }, routes: { 'GET /account': ME,
      'GET /tablesdb/hito/tables/saves/rows/u1': { status: 200, body: { data: '{"ledger":{"g":{}}}', devices: [] } }, 'PATCH /tablesdb/hito/tables/saves/rows/u1': { status: 200, body: {} } } });
    await settle();
    ok(!bare.threw, 'the layer needs a tracer to be present');
  }
}

if (fail) { console.log(`  ${fail} account check(s) failed`); process.exit(1); }
console.log('  a file offers no sign-in and makes no request, a guest makes none, the token leaves the address bar, '
  + 'the save is the owner\'s alone, merging never unlearns, and a tunnel is not a sign-out');
