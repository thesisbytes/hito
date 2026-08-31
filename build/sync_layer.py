#!/usr/bin/env python3
"""Offline-first sync: a device identity and an outbox that survives reloads.

The project's constraint is that every deliverable opens from a double-click,
offline, on a tablet. Sync does not get to weaken that. So this is a
write-behind outbox, not a client: events are recorded locally and flushed
when the network happens to be there. With no endpoint configured — the
default — it is a no-op that still records, so a build with sync switched off
behaves exactly like one built before sync existed.

Nothing here ever blocks the game. A failed flush is not an error, it is
Tuesday: the events stay queued and go out later.

What this layer deliberately does NOT do:

  * assert authority over anything. It ships observations — "this happened
    here" — never totals. The economy layer will be server-authoritative
    precisely because a client that can claim its own resource count is a
    client that can be edited by anyone with devtools.
  * hold credentials. The endpoint is a public URL and is treated as one.
"""

LAYER = r"""
<script>
/* ---- offline outbox ----------------------------------------------------
   Events are appended locally and flushed opportunistically. Never blocks,
   never throws into the game, and works exactly as well with the network
   unplugged — it just queues.                                           */
(function(){
  const CFG = window.__SYNC_CFG || {endpoint:'', batch:40, cap:500};
  const DEV = 'hito-device', BOX = 'hito-outbox';

  function readJSON(k, dflt){
    try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : dflt; }
    catch(_){ return dflt; }
  }
  function writeJSON(k, v){
    try { localStorage.setItem(k, JSON.stringify(v)); return true; }
    catch(_){ return false; }          // private mode, quota — not fatal
  }

  // A device, not an account. Enough to group one tablet's history and to
  // let a link code merge devices later; deliberately not identifying.
  function deviceId(){
    let d = null;
    try { d = localStorage.getItem(DEV); } catch(_){}
    if (!d){
      d = 'd' + Array.from({length:16}, () =>
            Math.floor(Math.random()*16).toString(16)).join('');
      try { localStorage.setItem(DEV, d); } catch(_){}
    }
    return d;
  }

  let outbox = readJSON(BOX, []);
  let flushing = false, lastTry = 0, backoff = 0;

  function eventId(){
    return Date.now().toString(36) + '-'
      + Array.from({length:8}, () => Math.floor(Math.random()*16).toString(16)).join('');
  }

  // The cap matters: a device that is offline for a month must not fill its
  // own storage and take the game's mastery down with it. Oldest go first,
  // because the newest observations are the ones still worth having.
  function record(kind, body){
    outbox.push({id:eventId(), kind, at:new Date().toISOString(), body});
    if (outbox.length > CFG.cap) outbox = outbox.slice(-CFG.cap);
    writeJSON(BOX, outbox);
    flush();
    return outbox.length;
  }

  function flush(){
    if (flushing || !CFG.endpoint || !outbox.length) return Promise.resolve(false);
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return Promise.resolve(false);
    const now = Date.now();
    if (now < lastTry + backoff) return Promise.resolve(false);
    flushing = true; lastTry = now;
    const batch = outbox.slice(0, CFG.batch);
    const ids = batch.map(e => e.id);
    return fetch(CFG.endpoint, {
      method:'POST',
      headers:{'content-type':'application/json'},
      body: JSON.stringify({device:deviceId(), events:batch}),
      keepalive: true,
    })
    .then(r => r.ok ? r.json().catch(() => ({accepted:ids})) : Promise.reject(r.status))
    .then(res => {
      // Accepted ids are removed; anything the server declined stays queued
      // only if it declined for a retryable reason. A rejected *event* that
      // is retried forever is a queue that never drains.
      const done = new Set(res.accepted || ids);
      outbox = outbox.filter(e => !done.has(e.id));
      writeJSON(BOX, outbox);
      backoff = 0;
      return true;
    })
    .catch(() => {
      // Exponential, capped. Offline is the normal case, not an error.
      backoff = Math.min(5*60*1000, backoff ? backoff*2 : 15*1000);
      return false;
    })
    .finally(() => { flushing = false; });
  }

  addEventListener('online', () => { backoff = 0; flush(); });
  if (typeof document !== 'undefined' && document.addEventListener)
    document.addEventListener('visibilitychange', () => { if (!document.hidden) flush(); });

  window.__sync = {
    device: deviceId(),
    record, flush,
    get pending(){ return outbox.length; },
    get enabled(){ return !!CFG.endpoint; },
    clear(){ outbox = []; writeJSON(BOX, outbox); },
  };
  flush();
})();
</script>
"""


def config(pack):
    """Sync tuning, written into the page. No endpoint means no network."""
    s = pack.get("sync") or {}
    endpoint = s.get("endpoint", "")
    if endpoint and not endpoint.startswith("https://"):
        raise SystemExit(
            f"sync.endpoint must be https, got {endpoint!r} — the page is served "
            "over https and a mixed-content POST is blocked silently, which is "
            "the worst way for this to fail."
        )
    return (
        "<script>window.__SYNC_CFG={"
        f'endpoint:"{endpoint}",'
        f"batch:{int(s.get('batch', 40))},"
        f"cap:{int(s.get('cap', 500))}"
        "};</script>"
    )
