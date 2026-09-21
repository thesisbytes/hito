#!/usr/bin/env python3
"""The hand: what draws, what it drew, and how it has been going.

Three things that turned out to be one thing, because all of them are about
the hand rather than about the glyph:

  * **Pen or finger.** The engine has had `penOnly` since the Thai tracer, but
    only as a workshop button, defaulting to on, remembered by nothing. The
    games hide the workshop, so a visitor on a phone met a sketchbook that
    ignored them completely. The switch now lives here, is remembered, and
    guesses sensibly the first time.
  * **The handwriting.** Every attempt — the ones that land and the ones that
    fizzle — is kept as strokes in the stroke book's own coordinate space, so
    what a hand drew can be laid straight over what it was asked to draw.
  * **The ledger.** Per character, keyed by the character (the codepoint rule),
    kept on the device and computed on the device. It works on a plane. The
    server gets a copy of the observations if the player allows it; the stats
    never wait for it and never read from it.

Appended as a layer, like the field. It reaches the engine through `conjure`,
`fizzle` and `zap`, which it wraps and always calls through, and it reads
`strokes` and `cur` on the way past. It never scores anything: the tracer is
still the only authority on what counts as a correct glyph, and this only
writes down what the tracer said.
"""

LAYER = r"""
<style>
  .hand-btn{ background:transparent; color:rgba(233,196,106,.8); border:1px solid #3d3324;
    border-radius:7px; padding:4px 9px; font:12px ui-sans-serif,system-ui; cursor:pointer;
    margin-left:auto; margin-right:10px; white-space:nowrap; }
  .hand-btn.nudge{ border-color:#7fd1c4; color:#bdf0e6; box-shadow:0 0 14px rgba(127,209,196,.45); }
  .hand{ position:fixed; inset:0; z-index:10000; display:flex; align-items:center;
    justify-content:center; background:rgba(12,10,8,.93); font:13px ui-sans-serif,system-ui; color:#e8e0cc; }
  .hand[hidden]{ display:none; }
  .hand-card{ width:min(94vw,520px); max-height:94dvh; overflow:auto; background:#15120f;
    border:1px solid #57492f; border-radius:12px; padding:20px 18px; box-sizing:border-box; }
  .hand-title{ font-size:26px; font-weight:700; color:#e9c46a; }
  .hand-sub{ color:rgba(232,224,204,.55); margin:2px 0 14px; font-size:12px; }
  .hand-h{ font-size:11px; letter-spacing:.14em; text-transform:uppercase;
    color:rgba(233,196,106,.7); margin:16px 0 7px; }
  .hand-row{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:8px; }
  .hand-row button{ text-align:left; background:#1d1a16; color:#e8e0cc; border:1px solid #57492f;
    border-radius:9px; padding:10px 11px; cursor:pointer; font:inherit; }
  .hand-row button b{ display:block; font-size:15px; color:#e9c46a; margin-bottom:3px; }
  .hand-row button small{ display:block; color:rgba(232,224,204,.7); line-height:1.35; }
  .hand-row button[aria-pressed="true"]{ border-color:#7fd1c4; background:#172422; }
  .hand-nums{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; text-align:center; }
  .hand-nums div{ background:#1d1a16; border:1px solid #3d3324; border-radius:9px; padding:9px 4px; }
  .hand-nums b{ display:block; font-size:20px; color:#bdf0e6; }
  .hand-nums small{ color:rgba(232,224,204,.6); font-size:11px; }
  .hand-list{ display:flex; flex-wrap:wrap; gap:6px; }
  .hand-list span{ background:#1d1a16; border:1px solid #3d3324; border-radius:8px; padding:5px 9px; }
  .hand-list span b{ font-size:19px; color:#e9c46a; margin-right:6px; }
  .hand-list span small{ color:rgba(232,224,204,.65); }
  .hand-empty{ color:rgba(232,224,204,.5); }
  .hand-thumbs{ display:grid; grid-template-columns:repeat(auto-fill,minmax(72px,1fr)); gap:8px; }
  .hand-thumbs figure{ margin:0; background:#1d1a16; border:1px solid #3d3324; border-radius:8px;
    padding:4px; text-align:center; }
  .hand-thumbs svg{ width:100%; height:auto; display:block; }
  .hand-thumbs figcaption{ font-size:11px; color:rgba(232,224,204,.65); }
  .hand-io{ width:100%; height:70px; margin-top:8px; background:#0f0d0b; color:#e8e0cc;
    border:1px solid #3d3324; border-radius:7px; font:11px ui-monospace,monospace; box-sizing:border-box; }
  .hand-io[hidden]{ display:none; }
  .hand-links{ display:flex; gap:8px; margin-top:10px; }
  .hand-links button{ flex:1; background:transparent; color:rgba(233,196,106,.75);
    border:1px solid #3d3324; border-radius:8px; padding:8px; cursor:pointer; font:inherit; }
  .hand-go{ width:100%; margin-top:16px; background:#e9c46a; color:#1d1a16; border:0;
    border-radius:9px; padding:12px; font-size:15px; font-weight:700; cursor:pointer; }
</style>
<script>
/* ---- the hand -----------------------------------------------------------
   Pen or finger, what was drawn, and how it has been going. Writes down what
   the tracer decided; decides nothing itself.                              */
(function(){
  const CFG = window.__HAND_CFG || {maxPoints:64, keep:24, minStep:4};
  const K_INPUT = 'hito-input', K_LEDGER = 'hito-ledger', K_HANDS = 'hito-hands';
  const read = (k, d) => { try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : d; } catch(_){ return d; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch(_){ return false; } };
  const say = m => { try { if (typeof toast === 'function') toast(m); } catch(_){} };

  // ---- pen or finger ------------------------------------------------------
  // 'pen' is the engine's penOnly: fingers, palms and mice are ignored, which
  // is what lets a hand rest on the glass. 'finger' takes whatever touches.
  // The first guess only has to avoid a dead sketchbook. Pen-only exists to
  // reject a palm, and a screen that cannot feel a palm has nothing to reject:
  // with no touch points at all, taking everything is always safe, and a pen
  // display on a desk still draws because 'finger' does not refuse a pen.
  function guess(){
    try {
      const mq = q => typeof matchMedia === 'function' && matchMedia(q).matches;
      const touch = (navigator.maxTouchPoints || 0) > 0;
      if (!touch) return 'finger';                                         // a mouse, or a pen display
      if (mq('(pointer:coarse)') && Math.min(screen.width, screen.height) < 500) return 'finger';  // a phone
    } catch(_){}
    return 'pen';
  }
  let stored = null;
  try { stored = localStorage.getItem(K_INPUT); } catch(_){}
  let input = stored === 'pen' || stored === 'finger' ? stored : guess();
  function showInput(){
    for (const id of ['penOnly', 'rPenOnly']){
      const b = document.getElementById(id);
      if (b && b.setAttribute) b.setAttribute('aria-pressed', input === 'pen');
    }
  }
  function setInput(v, quiet){
    input = v === 'finger' ? 'finger' : 'pen';
    penOnly = input === 'pen';
    if (!quiet){ try { localStorage.setItem(K_INPUT, input); } catch(_){} }
    showInput();
    return input;
  }
  setInput(input, true);   // a guess is not a choice, so it is not saved as one

  // ---- what the hand is doing right now ------------------------------------
  let ch = null, finished = true, zaps = 0, tries = 0, seenPen = false, lastType = '', nudged = 0;
  // The hand's own copy of the ink, taken at pen-up. The field tidies strays
  // out of `strokes` a moment later, and a log of handwriting with the
  // mistakes swept out of it is a log of the stroke book.
  let mine = [], down = null;
  const glyph = () => { try { return LETTERS[idx][0]; } catch(_){ return null; } };
  function attempt(){
    const g = glyph();
    if (g !== ch || finished){ ch = g; finished = false; tries = 0; zaps = 0; }
  }

  // Into the stroke book's space: undo the canvas, then undo the shrink that
  // size applies. A つ drawn at 0.32 and one drawn at 0.62 come out the same
  // shape in the same place, which is the only way two of them can be compared.
  function toBook(q){
    const s = curS || 1, cy0 = .5 + BASE_F*.06, cyN = .5 + curF*.06;
    return [Math.round((.5 + (q.x/W - .5)/s) * 1000), Math.round((cy0 + (q.y/H - cyN)/s) * 1000)];
  }
  function pack(raw){
    const t00 = raw.length && raw[0].length ? raw[0][0].t : 0;
    let cap = CFG.maxPoints, out;
    // Thinned by distance first, so a slow careful stroke is not all samples
    // from the first centimetre; then by count. Ends are always kept: where a
    // stroke starts and stops is most of what a stroke is.
    for (let pass = 0; pass < 3; pass++){
      out = raw.slice(0, 12).filter(s => s && s.length).map(s => {
        const pts = [];
        let lx = 1e9, ly = 1e9;
        s.forEach((q, i) => {
          const [x, y] = toBook(q);
          if (i === s.length - 1 || Math.hypot(x - lx, y - ly) >= CFG.minStep){ pts.push([x, y, Math.max(0, Math.round(q.t - t00))]); lx = x; ly = y; }
        });
        let keep = pts;
        if (pts.length > cap){
          keep = [];
          for (let k = 0; k < cap; k++) keep.push(pts[Math.round(k*(pts.length - 1)/(cap - 1))]);
        }
        return [].concat(...keep);
      });
      if (JSON.stringify(out).length <= 6000) break;
      cap = Math.max(8, cap >> 1);
    }
    return out;
  }

  // ---- the ledger ----------------------------------------------------------
  // Keyed by character. `tr` is trouble, smoothed: a zap is one, a fizzle is
  // three, and it decays with every clean attempt, so a character stops being
  // called shaky two clean traces after it stops being shaky.
  let LEDGER = read(K_LEDGER, null);
  if (!LEDGER || typeof LEDGER !== 'object' || !LEDGER.g) LEDGER = {v:1, g:{}, days:{}, by:{}};
  let HANDS = read(K_HANDS, []);
  if (!Array.isArray(HANDS)) HANDS = [];
  const today = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); };
  function save(){
    const ds = Object.keys(LEDGER.days).sort();
    while (ds.length > 60) delete LEDGER.days[ds.shift()];
    write(K_LEDGER, LEDGER);
    if (!write(K_HANDS, HANDS)){ HANDS = HANDS.slice(-Math.ceil(HANDS.length/2)); write(K_HANDS, HANDS); }
  }
  function note(ok){
    attempt();
    const raw = (mine.length ? mine : strokes).concat(cur && cur.length ? [cur] : []);
    mine = []; down = null;
    if (!raw.length || !ch){ if (ok) finished = true; return null; }
    const last = raw[raw.length - 1], first = raw[0];
    const ms = Math.max(0, Math.round(last[last.length - 1].t - first[0].t));
    const rec = {
      glyph: ch, ok, ms, zaps, tries, strokes: raw.length,
      size: Math.round(curF*1000)/1000, input: lastType || input,
      level: (typeof MASTERY !== 'undefined' && MASTERY[ch]) || 0,
      diff: (window.__field && window.__field.difficulty) || (window.__vocab && window.__vocab.difficulty) || '',
      v: typeof APP_VERSION !== 'undefined' ? APP_VERSION : '',
      s: pack(raw),
    };
    const e = LEDGER.g[ch] || (LEDGER.g[ch] = {n:0, clean:0, zaps:0, fizz:0, ms:0, rt:[], tr:0});
    const trouble = zaps + (ok ? 0 : 3);
    e.tr = Math.round(((e.tr || 0)*0.7 + trouble*0.3) * 100) / 100;
    e.zaps += zaps;
    if (ok){
      e.n++; if (!zaps && !tries) e.clean++;
      e.ms += ms; e.rt = (e.rt || []).concat(Math.round(ms / raw.length)).slice(-5);
      if (!e.best || ms < e.best) e.best = ms;
    } else e.fizz++;
    e.last = Date.now();
    const d = LEDGER.days[today()] || (LEDGER.days[today()] = [0, 0, 0]);
    if (ok){ d[0]++; if (!zaps && !tries) d[2]++; }
    d[1] += ms;
    LEDGER.by[rec.input] = (LEDGER.by[rec.input] || 0) + 1;
    HANDS.push(rec); HANDS = HANDS.slice(-CFG.keep);
    save();
    try { window.__sync && window.__sync.record('trace', rec); } catch(_){}
    if (ok) finished = true; else { tries++; }
    zaps = 0;
    return rec;
  }
  const attempts = e => (e.n || 0) + (e.fizz || 0);
  const shaky = c => { const e = LEDGER.g[c]; return !!e && attempts(e) >= 3 && (e.tr || 0) >= 1.5; };
  const median = a => { const s = a.slice().sort((x, y) => x - y); return s.length ? s[s.length >> 1] : 0; };
  function streak(){
    let n = 0; const d = new Date();
    const key = () => d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
    if (!(LEDGER.days[key()] || [0])[0]) d.setDate(d.getDate() - 1);   // today not traced yet does not break it
    while ((LEDGER.days[key()] || [0])[0]){ n++; d.setDate(d.getDate() - 1); }
    return n;
  }
  function stats(){
    const all = Object.entries(LEDGER.g), t = LEDGER.days[today()] || [0, 0, 0];
    const total = all.reduce((a, [, e]) => a + (e.n || 0), 0);
    const bites = all.filter(([c]) => shaky(c)).sort((a, b) => b[1].tr - a[1].tr).slice(0, 6)
      .map(([c, e]) => ({c, tr: e.tr, zaps: e.zaps, fizz: e.fizz, n: e.n}));
    const slow = all.filter(([, e]) => (e.rt || []).length >= 2).map(([c, e]) => ({c, per: median(e.rt)}))
      .sort((a, b) => b.per - a.per).slice(0, 6);
    const clean = all.filter(([, e]) => e.n >= 3 && e.clean === e.n).map(([c]) => c);
    return { today: {traced: t[0], ms: t[1], clean: t[2]}, streak: streak(), total, known: all.length, bites, slow, clean, by: LEDGER.by };
  }

  // ---- hooks ---------------------------------------------------------------
  const _zap = window.zap;
  window.zap = function(){ attempt(); zaps++; return _zap.apply(this, arguments); };
  // Both of these empty `strokes` on their way through, so the note is taken
  // first. A note that throws must not stop a glyph from landing.
  const _fizzle = window.fizzle;
  window.fizzle = function(){ try { note(false); } catch(_){} return _fizzle.apply(this, arguments); };
  const _conjure = window.conjure;
  window.conjure = function(){ try { note(true); } catch(_){} return _conjure.apply(this, arguments); };

  const ink = document.getElementById('ink');
  if (ink && ink.addEventListener){
    // Registered after the engine's own listener, so by now it has decided.
    ink.addEventListener('pointerdown', e => {
      if (e.pointerType === 'pen') seenPen = true;
      if (typeof activeId !== 'undefined' && activeId === e.pointerId){
        lastType = e.pointerType || '';
        if (strokes.length < mine.length || !strokes.length) mine = [];   // the engine started over, so does this
        down = e.pointerId; return;
      }
      // Refused. If no pen has ever touched this sketchbook, that was probably
      // not a palm — it was somebody trying to draw. Say so, but not every time.
      if (penOnly && e.pointerType !== 'pen' && !seenPen && !done && (nudged++ % 3 === 0)){
        say('pen only ✎ — tap ✋ up top to draw with a finger');
        if (btn && btn.classList){ btn.classList.add('nudge'); setTimeout(() => btn.classList.remove('nudge'), 2600); }
      }
    });
  }
  // After the engine's endStroke and before the field's tidy(): listeners run
  // in the order they were added, and this layer sits between the two.
  if (ink && ink.addEventListener) for (const ev of ['pointerup', 'pointercancel']) ink.addEventListener(ev, e => {
    if (e.pointerId !== down) return;
    down = null;
    const s = strokes[strokes.length - 1];
    if (s && s.length) mine.push(s.slice());
  });
  // The workshop's own button still works; it just gets remembered now.
  for (const id of ['penOnly', 'rPenOnly']){
    const b = document.getElementById(id);
    if (b && b.addEventListener) b.addEventListener('click', () => setInput(penOnly ? 'pen' : 'finger'));
  }

  // ---- the sheet -----------------------------------------------------------
  const esc = t => String(t).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const secs = ms => ms >= 60000 ? Math.round(ms/60000) + 'm' : (ms/1000).toFixed(ms < 10000 ? 1 : 0) + 's';
  function thumb(r){
    const paths = (r.s || []).map(f => {
      let d = '';
      for (let i = 0; i + 2 < f.length; i += 3) d += (i ? 'L' : 'M') + (+f[i] || 0) + ' ' + (+f[i+1] || 0);
      return `<path d="${d}"/>`;
    }).join('');
    return `<figure><svg viewBox="150 150 700 760" fill="none" stroke="${r.ok ? '#e9c46a' : '#dc5a3c'}" stroke-width="22" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`
      + `<figcaption>${esc(r.glyph)} · ${r.ok ? secs(r.ms) : 'fizzled'}</figcaption></figure>`;
  }
  const sheet = document.createElement('div');
  sheet.className = 'hand'; sheet.id = 'hand'; sheet.hidden = true;
  let markup = '', io = false;
  function render(){
    const s = stats(), sync = window.__sync;
    const opt = (v, cur, title, blurb) => `<button data-in="${v}" aria-pressed="${v === cur}"><b>${title}</b><small>${blurb}</small></button>`;
    const list = (a, f, none) => a.length ? `<div class="hand-list">${a.map(f).join('')}</div>` : `<div class="hand-empty">${none}</div>`;
    sheet.innerHTML = markup = `<div class="hand-card">
      <div class="hand-title">the hand ✋</div>
      <div class="hand-sub">what draws, and how it has been going</div>
      <div class="hand-h">draw with</div>
      <div class="hand-row">
        ${opt('pen', input, '✎ pen only', 'fingers and palms are ignored, so the hand can rest on the glass.')}
        ${opt('finger', input, '☝ finger', 'anything that touches draws: a finger, a mouse, a pen. one at a time.')}
      </div>
      ${sync && sync.enabled ? `<div class="hand-h">notes to the workshop</div>
      <div class="hand-row">
        <button data-share="1" aria-pressed="${!!sync.share}"><b>send them</b><small>what you drew and how it went — strokes, times, zaps — under a made-up device name. no account, no name. this is how the tracer gets fairer.</small></button>
        <button data-share="0" aria-pressed="${!sync.share}"><b>keep them here</b><small>nothing leaves this device. everything on this page still works.</small></button>
      </div>` : ''}
      <div class="hand-h">today</div>
      <div class="hand-nums">
        <div><b>${s.today.traced}</b><small>conjured</small></div>
        <div><b>${s.today.traced ? Math.round(100*s.today.clean/s.today.traced) + '%' : '—'}</b><small>clean</small></div>
        <div><b>${secs(s.today.ms)}</b><small>pen down</small></div>
        <div><b>${s.streak}</b><small>day${s.streak === 1 ? '' : 's'} running</small></div>
      </div>
      <div class="hand-h">these bite you most</div>
      ${list(s.bites, b => `<span><b>${esc(b.c)}</b><small>${b.zaps} zap${b.zaps === 1 ? '' : 's'}, ${b.fizz} fizzle${b.fizz === 1 ? '' : 's'}</small></span>`, 'nothing is biting. the phi pop are bored.')}
      <div class="hand-h">these take you longest, per stroke</div>
      ${list(s.slow, b => `<span><b>${esc(b.c)}</b><small>${secs(b.per)}</small></span>`, 'trace a character twice and it shows up here.')}
      <div class="hand-h">always clean</div>
      ${list(s.clean.slice(0, 24), c => `<span><b>${esc(c)}</b></span>`, 'three traces without a zap puts a character here.')}
      <div class="hand-h">the last few, as you wrote them</div>
      ${HANDS.length ? `<div class="hand-thumbs">${HANDS.slice(-12).reverse().map(thumb).join('')}</div>` : '<div class="hand-empty">nothing yet. go and draw something.</div>'}
      <div class="hand-links"><button data-io="export">export the ledger</button><button data-io="import">import</button></div>
      <textarea class="hand-io" spellcheck="false" ${io ? '' : 'hidden'} placeholder="paste an exported ledger here, then tap import again"></textarea>
      <div class="hand-sub" style="margin:10px 0 0">${s.total} conjured in all, across ${s.known} character${s.known === 1 ? '' : 's'} · kept on this device</div>
      <button class="hand-go">back</button>
    </div>`;
    if (!sheet.querySelectorAll) return;
    for (const b of sheet.querySelectorAll('button[data-in]')) b.onclick = () => { setInput(b.dataset.in); render(); };
    for (const b of sheet.querySelectorAll('button[data-share]')) b.onclick = () => { sync.setShare(b.dataset.share === '1'); render(); };
    const ta = sheet.querySelector('.hand-io');
    for (const b of sheet.querySelectorAll('button[data-io]')) b.onclick = () => {
      if (b.dataset.io === 'export'){ io = true; render(); const t = sheet.querySelector('.hand-io'); t.value = exportText(); t.select(); say('ledger exported — copy it somewhere safe'); }
      else if (!io || !ta.value.trim()){ io = true; render(); sheet.querySelector('.hand-io').focus(); }
      else { say(importText(ta.value) ? 'ledger imported ✓' : 'that is not a ledger'); io = false; render(); }
    };
    const go = sheet.querySelector('.hand-go'); if (go) go.onclick = close;
  }
  function exportText(){ return JSON.stringify({hito:'ledger', v:1, ledger:LEDGER, hands:HANDS}); }
  // Merged, not replaced: counts only ever grow, so the larger one is the one
  // that has seen more. The same rule the server will use for mastery.
  function importText(txt){
    let o; try { o = JSON.parse(txt); } catch(_){ return false; }
    if (!o || o.hito !== 'ledger' || !o.ledger || typeof o.ledger.g !== 'object') return false;
    for (const [c, e] of Object.entries(o.ledger.g)){
      if (!e || typeof e !== 'object' || [...c].length > 8) continue;
      const mine = LEDGER.g[c];
      if (!mine || attempts(e) > attempts(mine)) LEDGER.g[c] = {
        n:+e.n||0, clean:+e.clean||0, zaps:+e.zaps||0, fizz:+e.fizz||0, ms:+e.ms||0,
        rt:(Array.isArray(e.rt) ? e.rt : []).map(Number).filter(isFinite).slice(-5),
        tr:+e.tr||0, best:+e.best||0, last:+e.last||0 };
    }
    for (const [d, v] of Object.entries(o.ledger.days || {})){
      if (!/^\d{4}-\d\d-\d\d$/.test(d) || !Array.isArray(v)) continue;
      const m = LEDGER.days[d];
      if (!m || (+v[0]||0) > m[0]) LEDGER.days[d] = [+v[0]||0, +v[1]||0, +v[2]||0];
    }
    save();
    return true;
  }
  function open(){
    // The farang do not wait, so a field has to be stopped before anything
    // is laid over it. Its own start page is what stops it.
    try { if (window.__field && !window.__field.paused) window.__field.openStart(); } catch(_){}
    io = false; render(); sheet.hidden = false;
  }
  function close(){ sheet.hidden = true; try { window.__field && window.__field.openStart(); } catch(_){} }

  const btn = document.createElement('button');
  btn.className = 'hand-btn'; btn.textContent = '✋ hand'; btn.title = 'Pen or finger, and how it has been going';
  btn.onclick = open;
  addEventListener('DOMContentLoaded', () => {
    document.body.appendChild(sheet);
    const count = document.getElementById('count');
    if (count && count.parentNode && count.parentNode.insertBefore) count.parentNode.insertBefore(btn, count);
    showInput();
  });

  window.__hand = {
    get input(){ return input; }, setInput, guess,
    get ledger(){ return LEDGER; }, get hands(){ return HANDS; },
    get html(){ return markup; }, get shown(){ return !sheet.hidden; },
    show: open, close, render, note, pack, toBook, shaky, stats, streak,
    exportText, importText,
    reset(){ LEDGER = {v:1, g:{}, days:{}, by:{}}; HANDS = []; save(); },
  };
})();
</script>
"""


def config(pack):
    """The hand's tuning, written into the page."""
    h = pack.get("hand") or {}
    return (
        "<script>window.__HAND_CFG={"
        f"maxPoints:{int(h.get('maxPoints', 64))},"
        f"keep:{int(h.get('keep', 24))},"
        f"minStep:{int(h.get('minStep', 4))}"
        "};</script>"
    )
