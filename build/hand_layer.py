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
    margin-left:auto; margin-right:10px; white-space:nowrap;
    /* the engine styles every button as flex:1 with a min-width; in a header
       with the tabs hidden that is a bar the width of the screen */
    flex:none; min-width:0; letter-spacing:0; }
  /* A finger gets more room. In the games the sketchbook is a third of the
     screen because a pen needs no more; a fingertip hides what it is tracing,
     so it takes some of the field's height back. The field's canvas and the
     stage are both watched for size, so this is just a class. */
  body.field.hand-pen .stage, body.vocab.hand-pen .stage{ width:min(96vw,VAR_PEN_STAGE); height:min(96vw,VAR_PEN_STAGE); }
  body.field.hand-finger .stage, body.vocab.hand-finger .stage{ width:min(96vw,VAR_FINGER_STAGE); height:min(96vw,VAR_FINGER_STAGE); }
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
  .hand-thumbs figcaption em{ display:block; font-style:normal; font-size:10px; line-height:1.2; color:#bdf0e6; }
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
  const CFG = window.__HAND_CFG || {maxPoints:64, keep:60, minStep:4, pen:{size:null,ease:1,trail:1,halo:0}, finger:{size:[0.62,0.62],ease:1.5,trail:2.2,halo:36}, qualitySpan:0.09};
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
  // ---- a finger is not a pen ---------------------------------------------
  // The tolerance was tuned for a pen tip, which shows you the line as you
  // draw it. A fingertip is a centimetre wide and sits on top of the path, so
  // the hand is steering by memory of where the line was. Three things give:
  // the glyph is drawn at its largest, the sketchbook takes more of the screen,
  // and the path forgives more (HAND_EASE, the one seam in the scorer). Only on
  // a screen that can feel a finger — a mouse in finger mode is already precise
  // — and it lets go the moment a pen touches down.
  const touchy = () => { try { return (navigator.maxTouchPoints || 0) > 0; } catch(_){ return false; } };
  let penNow = false;
  const roomy = () => input === 'finger' && touchy() && !penNow;
  // Two profiles, tuned apart (the maintainer: "touch / pen sizes should be
  // optimized separately"). Neither is the other with a multiplier on it: each
  // has its own glyph sizes, sketchbook, forgiveness, road and halo, and every
  // trace says which it was drawn under, so each can be tuned from its own data.
  const prof = () => roomy() ? CFG.finger : CFG.pen;
  function applyRoom(){
    const on = roomy(), p = prof();
    try { HAND_EASE = p.ease; HAND_TRAIL = p.trail; HAND_HALO = p.halo;
          trailProg = -1; } catch(_){}   // the road ahead is cached; a new width is a new road
    try { const c = document.body.classList; c[on ? 'add' : 'remove']('hand-finger'); c[on ? 'remove' : 'add']('hand-pen'); c[on ? 'add' : 'remove']('roomy'); } catch(_){}
    return on;
  }
  // sizeFor() is the engine's single seam for size. A profile with its own
  // range draws from it; one without leaves the pack's rule alone. A size a
  // difficulty has pinned (guided: one big size) is nobody's to change.
  const _sizeFor = window.sizeFor;
  if (typeof _sizeFor === 'function') window.sizeFor = function(){
    const v = _sizeFor.apply(this, arguments), s = prof().size;
    if (!s || (typeof SIZE_PIN !== 'undefined' && SIZE_PIN != null)) return v;
    return s[0] + Math.random()*(s[1] - s[0]);
  };

  function setInput(v, quiet){
    input = v === 'finger' ? 'finger' : 'pen';
    penOnly = input === 'pen';
    const was = document.body.classList && document.body.classList.contains && document.body.classList.contains('roomy');
    if (applyRoom() !== !!was && !quiet){ try { if (typeof load === 'function' && typeof idx === 'number' && !done && !strokes.length) load(idx); } catch(_){} }
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
  let lastRec = null;   // the last note taken, for whoever asked the tracer to land it
  let mine = [], down = null, downAt = 0, began = null;   // null, not 0: 0 is a time
  // …and the hand's own clock. The engine restarts its clock whenever the ink
  // is empty, and guided mode empties the ink after every stroke, so by the
  // engine's watch each stroke of が began at zero and the whole character
  // took as long as its last tick.
  const shift = (s, at) => { const off = (at - began) - (s[0] ? s[0].t : 0); return s.map(q => ({x:q.x, y:q.y, p:q.p, t:q.t + off})); };
  function fresh(){ mine = []; down = null; began = null; }
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

  // ---- how recognisable was that? ------------------------------------------
  // The maintainer: "if your keys are recognizable, you end up with more
  // currency". A trace and the shape it was asked for are in the same space, so
  // this is geometry, not recognition: how far, on average, is the ink from the
  // shape, and the shape from the ink. Both directions, or a dot on the path
  // would score as a perfect が. Normalised by the glyph's own size, so つ and
  // ぼ are judged alike. Order and stroke count are not judged here — the tracer
  // already enforces both, and a stroke drawn in two pen-downs is still that
  // stroke. 0..1: 1 is the book, 0 is somewhere else entirely.
  // This is a measure of tidiness along a path the hand was shown. It is NOT
  // hard mode's "is this あ?" — but it is the distance that will need.
  const walk = (pts, step) => {          // points every `step` along a polyline
    const out = []; if (!pts.length) return out;
    out.push(pts[0]); let carry = 0;
    for (let i = 1; i < pts.length; i++){
      const [ax, ay] = pts[i-1], [bx, by] = pts[i], L = Math.hypot(bx-ax, by-ay);
      if (!L) continue;
      for (let d = step - carry; d <= L; d += step) out.push([ax + (bx-ax)*d/L, ay + (by-ay)*d/L]);
      carry = (carry + L) % step;
    }
    out.push(pts[pts.length-1]); return out;
  };
  const toward = (A, B) => { let s = 0; for (const [x, y] of A){ let m = 1e9; for (const [u, v] of B){ const d = (x-u)*(x-u) + (y-v)*(y-v); if (d < m) m = d; } s += Math.sqrt(m); } return s / A.length; };
  function quality(c, flats){
    try {
      const st = TEACHER.fonts[TEACHER.activeFont].letters[c].strokes;
      let R = [], U = [], x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      for (const s of st){ const pts = s.map(q => [q.x*1000, q.y*1000]); for (const [x, y] of pts){ x0 = Math.min(x0,x); y0 = Math.min(y0,y); x1 = Math.max(x1,x); y1 = Math.max(y1,y); } R = R.concat(walk(pts, 14)); }
      for (const f of flats){ const pts = []; for (let i = 0; i + 2 < f.length; i += 3) pts.push([+f[i], +f[i+1]]); U = U.concat(walk(pts, 14)); }
      const diag = Math.hypot(x1-x0, y1-y0);
      if (!R.length || U.length < 2 || !(diag > 0) || U.some(p => !isFinite(p[0]) || !isFinite(p[1]))) return null;
      const m = (toward(U, R) + toward(R, U)) / 2 / diag;
      return Math.max(0, Math.min(1, 1 - m / CFG.qualitySpan));
    } catch(_){ return null; }
  }
  const grade = q => q == null ? '' : q >= .8 ? 'crisp' : q >= .6 ? 'clear' : q >= .4 ? 'readable' : 'barely';

  // ---- the ledger ----------------------------------------------------------
  // Keyed by character. `tr` is trouble, smoothed: a zap is one, a fizzle is
  // three, and it decays with every clean attempt, so a character stops being
  // called shaky two clean traces after it stops being shaky.
  let LEDGER = read(K_LEDGER, null);
  if (!LEDGER || typeof LEDGER !== 'object' || !LEDGER.g) LEDGER = {v:1, g:{}, days:{}, by:{}};
  if (!Array.isArray(LEDGER.runs)) LEDGER.runs = [];
  if (!LEDGER.best || typeof LEDGER.best !== 'object') LEDGER.best = {};
  const purseOK = p => p && typeof p === 'object' && ['earned','spent','own','cleared'].every(k => p[k] && typeof p[k] === 'object');
  if (!purseOK(LEDGER.tama)) LEDGER.tama = { earned:{}, spent:{}, own:{}, cleared:{} };
  let HANDS = read(K_HANDS, []);
  if (!Array.isArray(HANDS)) HANDS = [];
  const today = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); };
  function save(){
    const ds = Object.keys(LEDGER.days).sort();
    while (ds.length > 60) delete LEDGER.days[ds.shift()];
    write(K_LEDGER, LEDGER);
    try { window.__account && window.__account.touch(); } catch(_){}
    if (!write(K_HANDS, HANDS)){ HANDS = HANDS.slice(-Math.ceil(HANDS.length/2)); write(K_HANDS, HANDS); }
  }
  function note(ok){
    attempt();
    const live = cur && cur.length ? [began !== null ? shift(cur, downAt) : cur] : [];
    const raw = (mine.length ? mine : strokes).concat(live);
    fresh();
    if (!raw.length || !ch){ if (ok) finished = true; return null; }
    const last = raw[raw.length - 1], first = raw[0];
    const ms = Math.max(0, Math.round(last[last.length - 1].t - first[0].t));
    const rec = {
      glyph: ch, ok, ms, zaps, tries, strokes: raw.length, at: Date.now(),
      size: Math.round(curF*1000)/1000, input: lastType || input,
      ease: (typeof HAND_EASE === 'number' && HAND_EASE !== 1) ? HAND_EASE : undefined,
      prof: roomy() ? 'finger' : 'pen',
      level: (typeof MASTERY !== 'undefined' && MASTERY[ch]) || 0,
      diff: (window.__field && window.__field.difficulty) || (window.__vocab && window.__vocab.difficulty) || '',
      v: typeof APP_VERSION !== 'undefined' ? APP_VERSION : '',
      s: pack(raw),
    };
    const q = ok ? quality(ch, rec.s) : null;
    if (q != null) rec.q = Math.round(q*100)/100;
    const e = LEDGER.g[ch] || (LEDGER.g[ch] = {n:0, clean:0, zaps:0, fizz:0, ms:0, rt:[], tr:0});
    const trouble = zaps + (ok ? 0 : 3);
    e.tr = Math.round(((e.tr || 0)*0.7 + trouble*0.3) * 100) / 100;
    e.zaps += zaps;
    if (ok){
      e.n++; if (!zaps && !tries) e.clean++;
      e.ms += ms; e.rt = (e.rt || []).concat(Math.round(ms / raw.length)).slice(-5);
      if (!e.best || ms < e.best) e.best = ms;
      if (rec.q != null) e.q = Math.round(((e.q == null ? rec.q : e.q*0.7 + rec.q*0.3)) * 100) / 100;
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
    zaps = 0; lastRec = rec;
    return rec;
  }
  // ---- runs ---------------------------------------------------------------
  // A run is written down when it ends: how far, how many, how cleanly. The
  // last twenty are kept, and the furthest wave per realm for good. These are
  // the player's own record of themselves and travel with their save; they are
  // not a score anyone else will ever be ranked by.
  const cleanRun = r => ({ at:+r.at||0, realm:String(r.realm||'').slice(0,24), wave:+r.wave||0, banished:+r.banished||0,
    traced:+r.traced||0, clean:+r.clean||0, sumi:+r.sumi||0, cast:+r.cast||0, ms:+r.ms||0,
    difficulty:String(r.difficulty||'').slice(0,12) });
  function bestOf(realm, r){
    const b = LEDGER.best[realm];
    if (!b || r.wave > b.wave || (r.wave === b.wave && r.banished > b.banished)){ LEDGER.best[realm] = { wave:r.wave, banished:r.banished, at:r.at }; return true; }
    return false;
  }
  function run(rec){
    const r = cleanRun(rec);
    const isBest = bestOf(r.realm, r);
    LEDGER.runs.push(r); LEDGER.runs = LEDGER.runs.slice(-20);
    save();
    const total = Object.values(LEDGER.g).reduce((a, e) => a + (e.n || 0), 0);
    return { isBest, wave: LEDGER.best[r.realm].wave, runs: LEDGER.runs.filter(x => x.realm === r.realm).length, total };
  }
  // ---- 魂 tama: what a run leaves behind ----------------------------------
  // Spent between rounds, on things that last. It has to survive being merged
  // from two tablets with no server to arbitrate, and a balance cannot: two
  // devices that each hold 40 do not make 40, or 80, without knowing what
  // happened in between. So no balance is ever stored. Each device keeps what
  // IT has earned and what IT has spent, as totals that only rise; those merge
  // by max, per device, with no conflict possible; and the balance is the
  // difference of the sums. What is owned merges by max level.
  // The one wart: buy the same level on two offline devices and both spends
  // count. It costs the player, never the game, and only if they try.
  const me = () => { try { return (window.__sync && window.__sync.device) || 'local'; } catch(_){ return 'local'; } };
  const sum = o => Object.values(o).reduce((a, b) => a + (+b || 0), 0);
  const tama = {
    get balance(){ return Math.max(0, sum(LEDGER.tama.earned) - sum(LEDGER.tama.spent)); },
    get earned(){ return sum(LEDGER.tama.earned); },
    own: id => +LEDGER.tama.own[id] || 0,
    cleared: realm => +LEDGER.tama.cleared[realm] || 0,
    earn(n){ n = Math.max(0, Math.floor(+n || 0)); if (n){ LEDGER.tama.earned[me()] = (+LEDGER.tama.earned[me()] || 0) + n; save(); } return n; },
    clear(realm, stage){ if (stage > tama.cleared(realm)){ LEDGER.tama.cleared[realm] = stage; save(); return true; } return false; },
    buy(id, cost, max){
      cost = Math.ceil(+cost); if (!(cost >= 0) || tama.balance < cost) return false;
      if (max != null && tama.own(id) >= max) return false;
      LEDGER.tama.spent[me()] = (+LEDGER.tama.spent[me()] || 0) + cost;
      LEDGER.tama.own[id] = tama.own(id) + 1; save(); return true;
    },
  };
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
  // A new glyph is a new attempt. This used to be inferred from the engine's
  // ink being empty, which in guided it always is: every character a guided
  // player wrote was logged as its last stroke alone, for two releases.
  const _load = window.load;
  if (typeof _load === 'function') window.load = function(){ fresh(); return _load.apply(this, arguments); };
  const _zap = window.zap;
  window.zap = function(){ attempt(); zaps++; return _zap.apply(this, arguments); };
  // Both of these empty `strokes` on their way through, so the note is taken
  // first. A note that throws must not stop a glyph from landing.
  const _fizzle = window.fizzle;
  // …but not silently. A note that threw every time once went unnoticed because
  // this catch is doing its job; the count is what a test can see.
  let faults = 0;
  window.fizzle = function(){ try { note(false); } catch(_){ faults++; } return _fizzle.apply(this, arguments); };
  const _conjure = window.conjure;
  window.conjure = function(){ try { note(true); } catch(_){ faults++; } return _conjure.apply(this, arguments); };

  const inkEl = document.getElementById('ink');   // not `ink`: that is the engine's context
  if (inkEl && inkEl.addEventListener){
    // Registered after the engine's own listener, so by now it has decided.
    inkEl.addEventListener('pointerdown', e => {
      if (e.pointerType === 'pen') seenPen = true;
      // a pen in finger mode is still a pen: no extra forgiveness for it
      const p = e.pointerType === 'pen'; if (p !== penNow){ penNow = p; applyRoom(); }
      if (typeof activeId !== 'undefined' && activeId === e.pointerId){
        lastType = e.pointerType || '';
        down = e.pointerId; downAt = performance.now();
        if (began === null) began = downAt;             // the first touch of this attempt
        return;
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
  if (inkEl && inkEl.addEventListener) for (const ev of ['pointerup', 'pointercancel']) inkEl.addEventListener(ev, e => {
    if (e.pointerId !== down) return;
    down = null;
    const s = strokes[strokes.length - 1];
    if (s && s.length) mine.push(shift(s, downAt));
  });
  // The workshop's own button still works; it just gets remembered now.
  for (const id of ['penOnly', 'rPenOnly']){
    const b = document.getElementById(id);
    if (b && b.addEventListener) b.addEventListener('click', () => setInput(penOnly ? 'pen' : 'finger'));
  }

  // ---- the sheet -----------------------------------------------------------
  const esc = t => String(t).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const secs = ms => ms >= 60000 ? Math.round(ms/60000) + 'm' : (ms/1000).toFixed(ms < 10000 ? 1 : 0) + 's';
  // The shape that was asked for, from the same book the tracer reads. The
  // trace is in that book's space already, so the two lie on each other with
  // no fitting: what is off in the picture is what was off in the hand.
  function asked(ch){
    try {
      const st = TEACHER.fonts[TEACHER.activeFont].letters[ch].strokes;
      return st.map(s => `<path d="${s.map((q, i) => (i ? 'L' : 'M') + Math.round(q.x*1000) + ' ' + Math.round(q.y*1000)).join('')}"/>`).join('');
    } catch(_){ return ''; }
  }
  const BOX = '150 150 700 760';
  function thumb(r, tag){
    const ref = asked(r.glyph);
    const paths = (r.s || []).map(f => {
      let d = '';
      for (let i = 0; i + 2 < f.length; i += 3) d += (i ? 'L' : 'M') + (+f[i] || 0) + ' ' + (+f[i+1] || 0);
      return `<path d="${d}"/>`;
    }).join('');
    return `<figure><svg viewBox="${BOX}" fill="none" stroke-linecap="round" stroke-linejoin="round">`
      + (ref ? `<g stroke="rgba(232,224,204,.16)" stroke-width="46">${ref}</g>` : '')
      + `<g stroke="${r.ok ? '#e9c46a' : '#dc5a3c'}" stroke-width="20">${paths}</g></svg>`
      + `<figcaption>${esc(r.glyph)} · ${r.ok ? (r.q != null ? Math.round(r.q*100) + '% ' + grade(r.q) : secs(r.ms)) : 'fizzled'}${tag ? `<em>${tag}</em>` : ''}</figcaption></figure>`;
  }
  // With `crown`, the best of them is named, and so — the maintainer's own
  // idea, and their own words — is the worst, if it earned it.
  const thumbs = (since, n, crown) => { const a = HANDS.filter(r => (r.at || 0) >= (since || 0)).slice(-(n || 12)).reverse();
    const scored = crown ? a.filter(r => r.ok && r.q != null) : [];
    const top = scored.length > 1 ? scored.reduce((x, y) => y.q > x.q ? y : x) : null;
    const low = scored.length > 1 ? scored.reduce((x, y) => y.q < x.q ? y : x) : null;
    const tag = r => r === top ? 'best stroke of the run ✦' : (r === low && r.q < .45) ? 'you could barely recognize this' : '';
    return a.length ? `<div class="hand-thumbs">${a.map(r => thumb(r, tag(r))).join('')}</div>` : ''; };
  // Every trace still on the device, as one SVG: a sheet to keep, print, or be
  // teased about. Built here and handed over as a file; nothing is uploaded.
  function sheetSVG(){
    const a = HANDS.slice().reverse(), cols = Math.min(6, Math.max(1, a.length)), cw = 240, chh = 290;
    const rows = Math.ceil(a.length / cols) || 1;
    const cells = a.map((r, i) => {
      const x = (i % cols)*cw, y = Math.floor(i / cols)*chh, k = 220/760;
      const paths = (r.s || []).map(f => { let d = ''; for (let j = 0; j + 2 < f.length; j += 3) d += (j ? 'L' : 'M') + (+f[j]||0) + ' ' + (+f[j+1]||0); return `<path d="${d}"/>`; }).join('');
      return `<g transform="translate(${x + 10},${y + 10})"><rect width="220" height="270" rx="12" fill="#1d1a16" stroke="#3d3324"/>`
        + `<g transform="scale(${k.toFixed(4)}) translate(-150,-150)" fill="none" stroke-linecap="round" stroke-linejoin="round">`
        + `<g stroke="rgba(232,224,204,.16)" stroke-width="46">${asked(r.glyph)}</g><g stroke="${r.ok ? '#e9c46a' : '#dc5a3c'}" stroke-width="20">${paths}</g></g>`
        + `<text x="110" y="258" text-anchor="middle" font-size="15" font-family="system-ui,sans-serif" fill="#e8e0cc">${esc(r.glyph)} · ${r.ok ? secs(r.ms) : 'fizzled'}${r.prof === 'finger' ? ' · finger' : ''}</text></g>`;
    }).join('');
    return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${cols*cw} ${rows*chh}" width="${cols*cw}" height="${rows*chh}"><rect width="100%" height="100%" fill="#15100d"/>${cells}</svg>`;
  }
  function saveSheet(){
    try {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([sheetSVG()], {type:'image/svg+xml'}));
      a.download = 'hito-handwriting-' + today() + '.svg'; a.click();
      say('handwriting saved as an SVG'); return true;
    } catch(_){ say('could not save the sheet here'); return false; }
  }
  const sheet = document.createElement('div');
  sheet.className = 'hand'; sheet.id = 'hand'; sheet.hidden = true;
  let markup = '', io = false;
  function render(){
    const s = stats(), sync = window.__sync, acct = window.__account;
    // Who is drawing. Guest is not a lesser mode and is not dressed as one:
    // it is the game, and signing in only adds a save that follows you.
    const who = !acct ? '' : `<div class="hand-h">who is drawing</div><div class="hand-row">` + (
      acct.user ? `<button data-acct="sync" aria-pressed="true"><b>${esc(acct.user.name)}</b><small>signed in. these stats and your mastery are kept, and follow you to any device you sign in on.${acct.lastSync ? ' saved just now.' : ''}</small></button>`
                + `<button data-acct="out"><b>sign out</b><small>back to a guest. nothing on this device is lost.</small></button>`
      : acct.state === 'working' ? `<button disabled><b>signing in…</b><small>one moment.</small></button>`
      : `<button data-acct="guest" aria-pressed="true"><b>a guest</b><small>no account. everything stays on this device, and it all works offline.</small></button>`
        + (acct.can ? `<button data-acct="in"><b>sign in with Google</b><small>keep these stats and your mastery, and see them on any device.${acct.note ? ' ' + esc(acct.note) + '.' : ''}</small></button>`
                    : `<button disabled><b>sign in</b><small>only from the web: a file on a tablet has nowhere for Google to send you back to.</small></button>`)
      ) + `</div>`;
    const opt = (v, cur, title, blurb) => `<button data-in="${v}" aria-pressed="${v === cur}"><b>${title}</b><small>${blurb}</small></button>`;
    const list = (a, f, none) => a.length ? `<div class="hand-list">${a.map(f).join('')}</div>` : `<div class="hand-empty">${none}</div>`;
    sheet.innerHTML = markup = `<div class="hand-card">
      <div class="hand-title">the hand ✋</div>
      <div class="hand-sub">what draws, and how it has been going</div>
      ${who}
      <div class="hand-h">draw with</div>
      <div class="hand-row">
        ${opt('pen', input, '✎ pen only', 'fingers and palms are ignored, so the hand can rest on the glass.')}
        ${opt('finger', input, '☝ finger', 'anything that touches draws, one at a time. on a touch screen it is tuned for a fingertip: a bigger glyph, a wider road, and a ring around the light so you can see it past your finger.')}
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
      ${Object.keys(LEDGER.best).length ? `<div class="hand-h">furthest you have held</div>`
        + list(Object.entries(LEDGER.best), ([realm, b]) => `<span><b>${b.wave}</b><small>waves · ${esc(realm)} · ${b.banished} banished</small></span>`, '') : ''}
      <div class="hand-h">these bite you most</div>
      ${list(s.bites, b => `<span><b>${esc(b.c)}</b><small>${b.zaps} zap${b.zaps === 1 ? '' : 's'}, ${b.fizz} fizzle${b.fizz === 1 ? '' : 's'}</small></span>`, 'nothing is biting. the phi pop are bored.')}
      <div class="hand-h">these take you longest, per stroke</div>
      ${list(s.slow, b => `<span><b>${esc(b.c)}</b><small>${secs(b.per)}</small></span>`, 'trace a character twice and it shows up here.')}
      <div class="hand-h">always clean</div>
      ${list(s.clean.slice(0, 24), c => `<span><b>${esc(c)}</b></span>`, 'three traces without a zap puts a character here.')}
      <div class="hand-h">the last few, as you wrote them</div>
      ${HANDS.length ? `<div class="hand-thumbs">${HANDS.slice(-12).reverse().map(thumb).join('')}</div>` : '<div class="hand-empty">nothing yet. go and draw something.</div>'}
      ${HANDS.length ? '<div class="hand-links"><button data-svg="1">save my handwriting as an SVG</button></div>' : ''}
      <div class="hand-links"><button data-io="export">export the ledger</button><button data-io="import">import</button></div>
      <textarea class="hand-io" spellcheck="false" ${io ? '' : 'hidden'} placeholder="paste an exported ledger here, then tap import again"></textarea>
      <div class="hand-sub" style="margin:10px 0 0">${s.total} conjured in all, across ${s.known} character${s.known === 1 ? '' : 's'} · kept on this device</div>
      <button class="hand-go">back</button>
    </div>`;
    if (!sheet.querySelectorAll) return;
    for (const b of sheet.querySelectorAll('button[data-in]')) b.onclick = () => { setInput(b.dataset.in); render(); };
    for (const b of sheet.querySelectorAll('button[data-acct]')) b.onclick = () => {
      const a = b.dataset.acct;
      if (a === 'in') acct.signIn(); else if (a === 'out') acct.signOut(); else if (a === 'sync') acct.sync();
    };
    for (const b of sheet.querySelectorAll('button[data-share]')) b.onclick = () => { sync.setShare(b.dataset.share === '1'); render(); };
    const sv = sheet.querySelector('button[data-svg]'); if (sv) sv.onclick = saveSheet;
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
    const seen = new Set(LEDGER.runs.map(r => r.at + '/' + r.realm));
    for (const r0 of (Array.isArray(o.ledger.runs) ? o.ledger.runs.slice(-40) : [])){
      if (!r0 || typeof r0 !== 'object') continue;
      const r = cleanRun(r0);
      if (!r.at || seen.has(r.at + '/' + r.realm)) continue;
      seen.add(r.at + '/' + r.realm); LEDGER.runs.push(r); bestOf(r.realm, r);
    }
    LEDGER.runs.sort((a, b) => a.at - b.at); LEDGER.runs = LEDGER.runs.slice(-20);
    for (const [realm, b] of Object.entries(o.ledger.best || {})){
      if (b && typeof b === 'object' && realm.length <= 24) bestOf(realm, { wave:+b.wave||0, banished:+b.banished||0, at:+b.at||0 });
    }
    if (purseOK(o.ledger.tama)){
      const up = (mine, theirs, ok) => { for (const [k, v] of Object.entries(theirs)) if (ok(k) && +v > (+mine[k] || 0) && +v < 1e9) mine[k] = Math.floor(+v); };
      const dev = k => /^(d[0-9a-f]{16}|local)$/.test(k), word = k => /^[a-z][a-z0-9-]{0,23}$/i.test(k);
      up(LEDGER.tama.earned, o.ledger.tama.earned, dev); up(LEDGER.tama.spent, o.ledger.tama.spent, dev);
      up(LEDGER.tama.own, o.ledger.tama.own, word);      up(LEDGER.tama.cleared, o.ledger.tama.cleared, word);
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

  // the page redraws itself when somebody signs in or out while it is open
  try { window.__account && window.__account.onChange(() => { if (!sheet.hidden) render(); }); } catch(_){}

  window.__hand = {
    get input(){ return input; }, setInput, guess, get roomy(){ return roomy(); }, applyRoom,
    pen(v){ penNow = !!v; return applyRoom(); },
    get ledger(){ return LEDGER; }, get hands(){ return HANDS; },
    get html(){ return markup; }, get shown(){ return !sheet.hidden; },
    show: open, close, render, note, pack, toBook, shaky, stats, streak, run, thumbs, sheetSVG, saveSheet, tama,
    quality, grade, get last(){ return lastRec; }, get faults(){ return faults; },
    exportText, importText,
    reset(){ LEDGER = {v:1, g:{}, days:{}, by:{}, runs:[], best:{}, tama:{earned:{}, spent:{}, own:{}, cleared:{}}}; HANDS = []; save(); },
  };
})();
</script>
"""


PEN = {"size": None, "stage": "34dvh", "ease": 1.0, "trail": 1.0, "halo": 0}
FINGER = {"size": [0.62, 0.62], "stage": "42dvh", "ease": 1.5, "trail": 2.2, "halo": 36}


def profiles(pack):
    """The two hands, each over its own defaults. Checked, because these reach CSS and the scorer."""
    import re
    h = pack.get("hand") or {}
    out = {}
    for name, base in (("pen", PEN), ("finger", FINGER)):
        p = {**base, **(h.get(name) or {})}
        if not re.fullmatch(r"\d{1,3}(?:\.\d+)?(?:dvh|vh|vmin|px)", str(p["stage"])):
            raise SystemExit(f"hand.{name}.stage must be a CSS length like 42dvh, not {p['stage']!r}")
        if p["size"] is not None:
            lo, hi = (float(x) for x in p["size"])
            if not (0.2 <= lo <= hi <= 0.62):
                raise SystemExit(f"hand.{name}.size must be [min, max] within 0.2..0.62 (the stroke book's own size), not {p['size']!r}")
            p["size"] = [lo, hi]
        if not (1 <= float(p["ease"]) <= 2):
            raise SystemExit(f"hand.{name}.ease must be 1..2, not {p['ease']!r}: past 2 it is no longer tracing")
        p.update(ease=float(p["ease"]), trail=float(p["trail"]), halo=int(p["halo"]))
        out[name] = p
    return out


def layer(pack):
    """The layer, with each hand's sketchbook size written into its CSS."""
    pr = profiles(pack)
    return LAYER.replace("VAR_PEN_STAGE", pr["pen"]["stage"]).replace("VAR_FINGER_STAGE", pr["finger"]["stage"])


def config(pack):
    """The hand's tuning, written into the page."""
    import json
    h = pack.get("hand") or {}
    pr = profiles(pack)
    js = lambda p: json.dumps({k: p[k] for k in ("size", "ease", "trail", "halo")}, separators=(",", ":"))
    return (
        "<script>window.__HAND_CFG={"
        f"maxPoints:{int(h.get('maxPoints', 64))},"
        f"keep:{int(h.get('keep', 60))},"
        f"minStep:{int(h.get('minStep', 4))},"
        f"qualitySpan:{float(h.get('qualitySpan', 0.09))},"
        f"pen:{js(pr['pen'])},finger:{js(pr['finger'])}"
        "};</script>"
    )
