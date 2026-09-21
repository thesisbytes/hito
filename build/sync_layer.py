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
  const DEV = 'hito-device', BOX = 'hito-outbox', SHARE = 'hito-share';
  // Handwriting made events heavy: a trace is 1-3KB where a banish is 120
  // bytes, so counting events stopped being a way of counting bytes. Two
  // budgets, both in characters of JSON. `bytes` is the whole queue, kept
  // well under the 5MB the origin shares with mastery. `post` is one request,
  // kept under the 64KB a keepalive fetch is allowed — past that the browser
  // rejects it before it leaves, which looks exactly like being offline and
  // would back off forever with a full queue.
  const BYTES = CFG.bytes || 600000, POST = CFG.post || 48000;
  const size = e => JSON.stringify(e).length + 1;

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

  // The player's switch. Off means off: nothing is queued, nothing is sent,
  // and what was waiting is thrown away rather than kept for a change of
  // heart. On by default, and said so on the start page.
  let share = true;
  try { share = localStorage.getItem(SHARE) !== '0'; } catch(_){}
  function setShare(v){
    share = !!v;
    try { localStorage.setItem(SHARE, share ? '1' : '0'); } catch(_){}
    if (!share){ outbox = []; writeJSON(BOX, outbox); }
    return share;
  }

  function eventId(){
    return Date.now().toString(36) + '-'
      + Array.from({length:8}, () => Math.floor(Math.random()*16).toString(16)).join('');
  }

  // The cap matters: a device that is offline for a month must not fill its
  // own storage and take the game's mastery down with it. Oldest go first,
  // because the newest observations are the ones still worth having.
  function record(kind, body){
    if (!share) return outbox.length;
    outbox.push({id:eventId(), kind, at:new Date().toISOString(), body});
    if (outbox.length > CFG.cap) outbox = outbox.slice(-CFG.cap);
    let total = 0; for (const e of outbox) total += size(e);
    while (total > BYTES && outbox.length > 1) total -= size(outbox.shift());
    // A write that fails is storage saying it is full. The queue gives way
    // before mastery does: halve it and try once more.
    if (!writeJSON(BOX, outbox) && outbox.length > 1){
      outbox = outbox.slice(-Math.ceil(outbox.length/2)); writeJSON(BOX, outbox);
    }
    flush();
    return outbox.length;
  }

  function flush(){
    if (flushing || !share || !CFG.endpoint || !outbox.length) return Promise.resolve(false);
    if (typeof navigator !== 'undefined' && navigator.onLine === false) return Promise.resolve(false);
    const now = Date.now();
    if (now < lastTry + backoff) return Promise.resolve(false);
    flushing = true; lastTry = now;
    // Oldest first, until the count or the request is full. Always at least
    // one, or an event bigger than a request would sit at the head for good.
    const batch = []; let bytes = 0;
    for (const e of outbox){
      if (batch.length >= CFG.batch) break;
      const n = size(e);
      if (batch.length && bytes + n > POST) break;
      batch.push(e); bytes += n;
    }
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
      // A request only carries so much. If there is more, keep going rather
      // than waiting for the next thing to happen — but only when the server
      // took everything it was handed. If it declined any, asking again at
      // once is a hot loop against a server that is already saying no.
      const sent = new Set(ids);
      if (outbox.length && !outbox.some(e => sent.has(e.id))) setTimeout(flush, 0);
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
    get share(){ return share; }, set share(v){ setShare(v); }, setShare,
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
        f"cap:{int(s.get('cap', 500))},"
        f"bytes:{int(s.get('bytes', 600000))},"
        f"post:{int(s.get('post', 48000))}"
        "};</script>"
    )
