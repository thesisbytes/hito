#!/usr/bin/env python3
"""Guest, or signed in. Never required.

**Guest is the game.** No account, a made-up device id, everything kept on the
device, opens from a double-click with no network. Nothing here changes that,
and a build opened from a file has no sign-in at all: there is no origin for a
provider to send anybody back to.

**Signed in is a save file that follows you.** Google, through Appwrite. What
is kept is the hand's ledger and mastery, in one row that only its owner can
read. On every device the merge is the one `server/README.md` wrote down
before there was a server: counts only rise, so the fuller record wins per
character and mastery is `max()`. A tablet offline for a week merges without
asking anyone, and no device can lose what another one learned.

This is not the leaderboard and must not become one. It is client-written, so
it is exactly as trustworthy as a save file — fine for "how am I doing", and
worth nothing as a claim about anyone else. Ranked things are still derived
from the events table, server-side, later.

No SDK: it is five REST calls, and an SDK is an external dependency in a
project whose whole constraint is that there are none. The one subtlety is the
cookie. The page and the API are different sites, so the session cookie is a
third-party cookie and most browsers now refuse it; Appwrite answers that with
an `X-Fallback-Cookies` header, which is kept in localStorage and sent back.

`CORE` is shared with the title screen (`build/make_index.py`), which signs in
but has no tracer to sync.
"""

CORE = r"""
/* ---- guest, or signed in ------------------------------------------------
   Optional by construction: every call can fail and the game does not notice. */
(function(){
  const CFG = window.__ACCOUNT_CFG || {};
  const K_SESSION = 'hito-session', K_USER = 'hito-user';
  const loc = typeof location !== 'undefined' ? location : null;
  // A provider has to send the player back to somewhere. A file has no somewhere.
  const can = !!(CFG.endpoint && CFG.project && loc && /^https?:$/.test(loc.protocol) && typeof fetch === 'function');
  const get = k => { try { return localStorage.getItem(k); } catch(_){ return null; } };
  const put = (k, v) => { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch(_){} };
  let user = null;
  try { user = JSON.parse(get(K_USER) || 'null'); } catch(_){ user = null; }
  let state = user ? 'signed' : 'guest', note = '';
  const listeners = [];
  const changed = () => { for (const f of listeners) try { f(); } catch(_){} };

  function api(method, path, body){
    const headers = { 'X-Appwrite-Project': CFG.project, 'content-type': 'application/json' };
    const fb = get(K_SESSION); if (fb) headers['X-Fallback-Cookies'] = fb;
    return fetch(CFG.endpoint + path, { method, headers, credentials: 'include',
                                        body: body === undefined ? undefined : JSON.stringify(body) })
      .then(r => {
        const c = r.headers && r.headers.get && r.headers.get('x-fallback-cookies');
        if (c) put(K_SESSION, c);
        return r.text().then(t => { let j = null; try { j = t ? JSON.parse(t) : null; } catch(_){}
                                    return { status: r.status, ok: r.ok, json: j }; });
      });
  }

  function signIn(){
    if (!can) return false;
    const here = loc.origin + loc.pathname;
    loc.assign(CFG.endpoint + '/account/tokens/oauth2/google?project=' + encodeURIComponent(CFG.project)
      + '&success=' + encodeURIComponent(here) + '&failure=' + encodeURIComponent(here + '?signin=failed'));
    return true;
  }
  function forget(){ user = null; put(K_USER, null); put(K_SESSION, null); state = 'guest'; }
  function signOut(){
    const done = () => { forget(); note = ''; changed(); };
    if (!can) { done(); return Promise.resolve(); }
    return api('DELETE', '/account/sessions/current').catch(() => {}).then(done);
  }
  function me(){
    return api('GET', '/account').then(r => {
      if (r.ok && r.json && r.json.$id){
        user = { id: r.json.$id, name: r.json.name || (r.json.email || '').split('@')[0] || 'you' };
        put(K_USER, JSON.stringify(user)); state = 'signed'; changed();
        return user;
      }
      // Only a real "no" signs anybody out. Offline is not a no.
      if (r.status === 401){ forget(); changed(); }
      return null;
    }).catch(() => null);   // a tunnel: still whoever they were, just not reachable
  }
  // Back from the provider: the address carries a one-use token, which buys a session.
  function finish(){
    if (!can) return Promise.resolve(null);
    const q = new URLSearchParams(loc.search);
    const clean = () => { try { history.replaceState(null, '', loc.pathname + loc.hash); } catch(_){} };
    if (q.get('signin') === 'failed'){ clean(); note = 'that sign-in did not go through'; changed(); return Promise.resolve(null); }
    const userId = q.get('userId'), secret = q.get('secret');
    if (!userId || !secret) return Promise.resolve(null);
    clean();   // before anything else: a token in the address bar is a token in a screenshot
    state = 'working'; changed();
    return api('POST', '/account/sessions/token', { userId, secret })
      .then(r => r.ok ? me() : (state = 'guest', note = 'that sign-in did not go through', changed(), null))
      .catch(() => { state = 'guest'; note = 'no network to finish signing in'; changed(); return null; });
  }

  // ---- the save file ------------------------------------------------------
  const DB = CFG.db || 'hito', TABLE = CFG.table || 'saves';
  const rowPath = () => '/tablesdb/' + DB + '/tables/' + TABLE + '/rows/' + user.id;
  let syncing = false, dirty = false, timer = 0, lastSync = 0;
  function local(){
    const H = window.__hand;
    const out = { hito: 'save', v: 1, at: new Date().toISOString() };
    try { if (H) out.ledger = JSON.parse(H.exportText()).ledger; } catch(_){}
    try { if (typeof MASTERY !== 'undefined') out.mastery = MASTERY; } catch(_){}
    return out;
  }
  // Counts only rise, so merging is never a question: the fuller record per
  // character, and the higher mastery. Returns whether this device learned anything.
  function merge(remote){
    let learned = false;
    const H = window.__hand;
    try {
      if (H && remote.ledger){
        const before = H.exportText();
        H.importText(JSON.stringify({ hito: 'ledger', ledger: remote.ledger }));
        if (H.exportText() !== before) learned = true;
      }
    } catch(_){}
    try {
      if (typeof MASTERY !== 'undefined' && remote.mastery && typeof remote.mastery === 'object'){
        for (const [c, n] of Object.entries(remote.mastery)){
          if ([...c].length > 8 || !(+n > (MASTERY[c] || 0))) continue;
          MASTERY[c] = Math.min(9999, Math.floor(+n)); learned = true;
        }
        if (learned && typeof persistM === 'function') persistM();
      }
    } catch(_){}
    return learned;
  }
  function sync(){
    if (!can || !user || syncing) return Promise.resolve(false);
    syncing = true; dirty = false;
    const device = (window.__sync && window.__sync.device) || null;
    return api('GET', rowPath()).then(r => {
      if (r.status === 401){ forget(); changed(); return false; }
      if (r.status !== 200 && r.status !== 404) return false;          // not now; later
      let remote = null, devices = [];
      if (r.status === 200){
        try { remote = JSON.parse(r.json.data || 'null'); } catch(_){}
        devices = Array.isArray(r.json.devices) ? r.json.devices : [];
        if (remote) merge(remote);
      }
      if (device && !devices.includes(device)) devices = devices.concat(device).slice(-20);
      const body = { data: JSON.stringify(local()), devices };
      const me_ = 'user:' + user.id;
      return (r.status === 404
        ? api('POST', '/tablesdb/' + DB + '/tables/' + TABLE + '/rows', { rowId: user.id, data: body,
              permissions: ['read("' + me_ + '")', 'update("' + me_ + '")', 'delete("' + me_ + '")'] })
        : api('PATCH', rowPath(), { data: body })
      ).then(w => { if (w.ok){ lastSync = Date.now(); changed(); } return w.ok; });
    }).catch(() => false).then(v => { syncing = false; return v; });
  }
  // Something was learned here. Not at once: a run lands a glyph every few
  // seconds, and the save only has to be roughly current.
  function touch(){
    dirty = true;
    if (!can || !user || timer) return;
    timer = setTimeout(() => { timer = 0; if (dirty) sync(); }, CFG.saveMs || 20000);
  }

  window.__account = {
    get can(){ return can; }, get user(){ return user; }, get state(){ return state; },
    get note(){ return note; }, get lastSync(){ return lastSync; },
    signIn, signOut, me, finish, sync, touch, merge, local,
    onChange(f){ listeners.push(f); },
  };

  if (can){
    finish().then(u => { if (u) return sync(); if (user) return me().then(v => v && sync()); }).catch(() => {});
    if (typeof document !== 'undefined' && document.addEventListener)
      document.addEventListener('visibilitychange', () => { if (document.hidden && dirty) sync(); });
  }
})();
"""

LAYER = "\n<script>" + CORE + "</script>\n"


def values(pack):
    import json
    a = pack.get("account") or {}
    endpoint = a.get("endpoint", "")
    if endpoint and not endpoint.startswith("https://"):
        raise SystemExit(f"account.endpoint must be https, got {endpoint!r}")
    return {"endpoint": endpoint, "project": a.get("project", ""), "db": a.get("db", "hito"),
            "table": a.get("table", "saves"), "saveMs": int(a.get("saveMs", 20000))}


def config(pack):
    """Where accounts live, written into the page. No endpoint means guests only."""
    import json
    return "<script>window.__ACCOUNT_CFG=" + json.dumps(values(pack), separators=(",", ":")) + ";</script>"
