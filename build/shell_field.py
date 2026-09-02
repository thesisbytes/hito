#!/usr/bin/env python3
"""The game shell: a battle field above, a stationary sketchbook below.

The workshop screen — gojuon chart, stroke controls, size ladder — is the
instrument this project uses on itself. The game is not that. Here the bottom
third is the sketchbook and never moves, and the top two thirds is the field:
farang advance on a centre you are protecting, each carrying the sign you have
to answer. Finish the glyph and it flies up and hits them.

A finished glyph also *kindles* it: every clean trace of a character lights a
hitodama (人魂, a ghost light) over that character, and a lit character
defends itself. When a monster carrying it appears, a wisp flies on its own
and the charge burns down by one. Trace ぬ three times and the next few ぬ
die without the pen. This is the idle economy's potency stat given teeth
before the economy exists: the hand is pushed toward the characters whose
flame is out, which are exactly the ones that need practice.

The split is what makes real-time movement safe. Monsters can march
continuously because they never share space with the pen: the drawing surface
is a fixed rectangle that does not scroll, scale or reflow while the field
moves above it. "You identify, you do not aim" needs exactly that.

This is applied as an appended layer rather than woven into the engine with
substitutions. It touches the engine only through globals it already exposes
(load, conjure, LETTERS, idx, stage, toast), so the tracer and its scoring
stay the single source of truth for what counts as a correct glyph.
"""

STYLE = """
<style>
  /* The workshop's furniture, hidden. The engine still maintains all of it —
     nothing is torn out, so a pack can switch shells without a rebuild of the
     tracer. */
  body.field .tabs, body.field .count, body.field .meta, body.field .power,
  body.field .only-p, body.field .only-r, body.field #fontRow,
  body.field .grid, body.field .hint { display:none !important; }

  body.field { height:100dvh; overflow:hidden; justify-content:flex-start; }
  body.field header { padding:6px 0 2px; }

  /* Two thirds field, one third sketchbook. The stage loses its square aspect
     ratio here — resize() reads the element's box, so the tracer follows. */
  .field-wrap{ position:relative; width:min(96vw,760px); flex:2 1 0;
               min-height:0; margin-top:4px; }
  .field-wrap canvas{ position:absolute; inset:0; width:100%; height:100%;
    border-radius:18px;
    background:radial-gradient(70% 60% at 50% 70%,rgba(90,160,150,.07),transparent 70%),
               var(--lacquer-2);
    box-shadow:inset 0 0 0 1px rgba(233,196,106,.10),0 18px 50px rgba(0,0,0,.45); }
  /* The sketchbook MUST stay square. norm() in the engine divides x by W and
     y by H independently, so a rectangular stage does not merely stretch the
     glyph — it makes every distance in normalised space anisotropic, and the
     tolerance, coverage radius and travel ratio all stop meaning one thing.
     At 760x250 the pen would be forgiven three times as much sideways as
     vertically. The tracer has always assumed a square; this shell must not
     be the thing that quietly breaks that assumption. */
  body.field .stage{ flex:0 0 auto; aspect-ratio:1;
                     width:min(96vw,34dvh); height:min(96vw,34dvh);
                     margin:8px auto 10px; }
  body.field .field-wrap{ flex:1 1 auto; }
</style>
"""

LAYER = STYLE + r"""
<script>
/* ---- the field ---------------------------------------------------------
   Monsters advance in polar coordinates around the centre, so the geometry is
   resolution independent and a rotated tablet changes nothing about the game.
   d runs 1 at the edge to 0 at the ward.                                  */
(function(){
  const CFG = window.__FIELD_CFG;
  const $ = id => document.getElementById(id);

  document.body.classList.add('field');
  const wrap = document.createElement('div');
  wrap.className = 'field-wrap';
  const fc = document.createElement('canvas');
  fc.id = 'field';
  wrap.appendChild(fc);
  const stageEl = document.getElementById('stage');
  stageEl.parentNode.insertBefore(wrap, stageEl);

  const cx = () => fc.width / (2*DPRF());
  const cy = () => fc.height / (2*DPRF()) * 1.06;   // ward sits a touch low
  function DPRF(){ return Math.min(devicePixelRatio||1, 3); }
  let FW = 0, FH = 0;
  function sizeField(){
    const r = wrap.getBoundingClientRect(), d = DPRF();
    FW = Math.round(r.width); FH = Math.round(r.height);
    fc.width = Math.round(FW*d); fc.height = Math.round(FH*d);
    const g = fc.getContext('2d'); g.setTransform(d,0,0,d,0,0);
  }

  // ---- state
  let monsters = [], shots = [], motes = [];
  let ward = CFG.wardHp, over = false, wave = 0, killed = 0;
  let spawnAt = 0, tPrev = 0;

  // ---- hitodama
  // A ghost light per character, keyed by the character itself (a codepoint,
  // never a grid index — words and future scripts write to the same ledger).
  // Tracing kindles it; a monster carrying the character spends it. Kept in
  // localStorage rather than a run, because it is what was learned, and the
  // ward falling does not unlearn anything.
  const HKEY = 'hito-hitodama';
  let HITODAMA = {};
  try { HITODAMA = JSON.parse(localStorage.getItem(HKEY) || '{}') || {}; } catch(_){ HITODAMA = {}; }
  function saveH(){ try { localStorage.setItem(HKEY, JSON.stringify(HITODAMA)); } catch(_){} }
  const charge = ch => HITODAMA[ch] || 0;
  function kindle(ch, n){
    HITODAMA[ch] = Math.min(CFG.hitodamaCap, charge(ch) + n);
    saveH();
    try { window.__sync && window.__sync.record('kindle', { glyph: ch, charge: HITODAMA[ch] }); } catch(_){}
    return HITODAMA[ch];
  }
  function quench(){ HITODAMA = {}; saveH(); }
  // Zaps during the attempt, so a clean trace can pay more than a scrappy one.
  // conjure() does not say how it went; zap() is the only global that does.
  let zapped = 0;
  const _zap = window.zap;
  window.zap = function(){ zapped++; return _zap.apply(this, arguments); };

  // A lit character throws its own wisp. One at a time, on a cooldown, so a
  // swarm of three ぬ is answered visibly rather than vanishing in a frame.
  // Never at the monster the hand is answering right now: that one is yours.
  let castAt = 0;
  function dash(){ return { x: cx(), y: FH - 14 }; }
  function autocast(now){
    if (now - castAt < CFG.castMs) return null;
    let best = null;
    for (const m of monsters){
      if (charge(LETTERS[m.i][0]) < 1) continue;
      if (m === locked && tracing()) continue;
      if (shots.some(s => s.to === m)) continue;
      if (!best || m.d < best.d) best = m;
    }
    if (!best) return null;
    const ch = LETTERS[best.i][0];
    HITODAMA[ch] = charge(ch) - 1; saveH();
    shots.push({ from: dash(), to: best, t: 0, ch, auto: true });
    castAt = now;
    try { window.__sync && window.__sync.record('cast', { glyph: ch, left: HITODAMA[ch] }); } catch(_){}
    return best;
  }

  // Three ways a monster can ask. kana tests recall of the shape; romaji tests
  // the reading, which is the direction that actually matters; gaijin asks in
  // the learner's own broken accent, which is the same joke as the hero who
  // cannot read — the player is the foreigner here.
  const label = (i, which) =>
    which === 'romaji' ? LETTERS[i][2] :
    which === 'gaijin' ? (LETTERS[i][7] || LETTERS[i][2].toUpperCase()) :
    LETTERS[i][0];
  const sign = m => label(m.i, CFG.sign);

  function spawn(){
    // Bias toward glyphs whose flame has gone out: a monster is a character
    // you are forgetting, so the roster is the gojuon and the encounter rate
    // follows what actually needs review.
    let i, tries = 0;
    do { i = Math.floor(Math.random()*LETTERS.length); tries++; }
    while (tries < 8 && (MASTERY[LETTERS[i][0]]||0) > 2 && Math.random() < 0.7);
    monsters.push({
      i, a: Math.random()*Math.PI*2, d: 1.05,
      speed: CFG.speed * (0.8 + Math.random()*0.5),
      hp: 1, wob: Math.random()*6.28, born: performance.now(),
    });
    wave++;
    // If the tracer is idle or pointed at a glyph nobody carries, the arrival
    // is what it should be showing.
    if (!locked || !monsters.includes(locked)) retarget();
  }

  // The target is LOCKED once the tracer has loaded its glyph, and stays
  // locked until it dies, reaches the ward, or the player taps another.
  //
  // It used to be recomputed as "whichever is nearest right now", which is
  // wrong the moment anything moves: monsters advance while you trace, so one
  // could overtake yours mid-glyph and conjure() would fire at the newcomer.
  // You drew あ and something carrying ぬ died for it. What you are answering
  // cannot be allowed to change underneath the answer.
  let locked = null;
  // The hand goes where the flame is out. A monster carrying a lit character
  // will be answered by its own wisp, so the tracer is pointed at the nearest
  // one that will not — which is the character that actually needs practice.
  function nearest(){
    let best = null, dark = null;
    for (const m of monsters){
      if (!best || m.d < best.d) best = m;
      if (charge(LETTERS[m.i][0]) < 1 && (!dark || m.d < dark.d)) dark = m;
    }
    return dark || best;
  }
  function target(){
    if (locked && monsters.includes(locked)) return locked;
    locked = nearest();
    return locked;
  }
  function targetIdx(){ const t = target(); return t ? t.i : null; }

  // Tapping a monster is how you choose what to answer. This is the
  // identification mechanic arriving early: with the guide up the tracer still
  // shows you the shape, but which of them you take is yours.
  function pick(x, y){
    let best = null, bd = 44;
    for (const m of monsters){
      const p = px(m), d = Math.hypot(x-p.x, y-(p.y-14));
      if (d < bd){ bd = d; best = m; }
    }
    if (best && best !== locked){
      locked = best;
      pendingRetarget = false;
      loading = true; try { _load(best.i); } finally { loading = false; }
      return true;
    }
    return false;
  }

  // ---- drive the tracer from the field
  // Every load() lands on whatever the field is asking for. conjure()'s own
  // delayed load(idx+1) therefore advances to the next target rather than to
  // the next character in the chart.
  const _load = window.load;
  let loading = false;
  window.load = function(i){
    zapped = 0;
    if (loading) return _load.apply(this, arguments);
    const t = targetIdx();
    return _load.call(this, t === null ? i : t);
  };
  // A trace in progress is not to be interrupted. When several monsters land
  // at once the field churns — each arrival clears the lock and retargets —
  // and every one of those reloads wipes whatever the player had drawn. The
  // glyph changing under a working hand is what makes a swarm feel broken
  // rather than hard.
  // `done` matters here. After a conjure prog sits at the end of the last
  // stroke, so without that clause tracing() stayed true forever: the deferred
  // retarget never ran, and when the field emptied and refilled the tracer was
  // left frozen on the celebration of a glyph nothing was carrying any more.
  // "In progress" has to mean what the hand means by it. prog > 0 misses
  // the first stroke before it finds the path, and misses a hand that has
  // just lifted to think — both of which is when a wisp elsewhere would swap
  // the glyph under a pen that is about to come back down. So: ink on the
  // board counts, and so does any contact with the pad in the last holdMs.
  let penAt = -1e9;
  function tracing(){
    return !done && (activeId !== null || prog > 0 || strokes.length > 0 || !!cur
                     || performance.now() - penAt < CFG.holdMs);
  }
  const inkEl = document.getElementById('ink');
  for (const ev of ['pointerdown', 'pointermove', 'pointerup'])
    inkEl.addEventListener(ev, e => {
      if (ev === 'pointermove' && !e.buttons) return;   // a hovering pen is not a hand at work
      penAt = performance.now();
    }, true);

  // Ink that was off the path is a smudge, not an attempt. When the pen
  // lifts the finished stroke is cut down to the runs that were on the path;
  // the orange runs go, with a puff where they were. A stroke that never
  // found the path goes entirely. Keeping the off-path tails of an otherwise
  // good stroke was tried first and it is what let an overdrawn line stay
  // and pile up. Purely cosmetic: travel and coverage are accumulated live
  // in follow(), not read back from the stroke list, so the scribble guard
  // is untouched. Returns how many runs were erased.
  function tidy(){
    if (!CFG.tidyStrays || mode !== 'practice' || !PATH.length || !strokes.length) return 0;
    const s = strokes[strokes.length - 1];
    const keep = [], gone = [];
    let run = [];
    const flush = () => { if (run.length > 1) keep.push(run); run = []; };
    for (const q of s){
      if (q.on) run.push(q);
      else { flush(); gone.push(q); }
    }
    flush();
    if (!gone.length) return 0;
    strokes.pop(); strokes.push(...keep); redrawInk();
    const m = gone[Math.floor(gone.length / 2)];
    for (let k = 0; k < 10; k++){
      const a = Math.random()*6.283, v = .5 + Math.random()*1.5;
      parts.push({x:m.x, y:m.y, vx:Math.cos(a)*v, vy:Math.sin(a)*v, life:.6,
                  r:1 + Math.random()*1.5, c:'200,132,47'});
    }
    loop();
    return gone.length;
  }
  // Registered after the engine's own pointerup, so endStroke has already
  // pushed the stroke by the time this runs.
  inkEl.addEventListener('pointerup', () => tidy());
  inkEl.addEventListener('pointercancel', () => tidy());
  let pendingRetarget = false;
  function retarget(force){
    if (locked && !monsters.includes(locked)) locked = null;
    const t = targetIdx();
    // Already on the right glyph is only a reason to do nothing if the tracer
    // is live on it. After a conjure `done` is set, and if the next target
    // happens to carry the same character the old early return left the
    // tracer sitting in its celebration until the engine's own 1.9s timer
    // fired — a dead spot precisely when two of the same arrive together.
    if (t === null || (t === idx && !done)) { pendingRetarget = false; return; }
    if (!force && tracing()){ pendingRetarget = true; return; }
    pendingRetarget = false;
    zapped = 0;
    loading = true; try { _load(t); } finally { loading = false; }
  }

  // ---- a finished glyph is the attack
  // What was drawn decides what is hit — not which object happened to be
  // locked when the pen came up. "You identify, you do not aim" taken
  // literally: finish ぬ and the nearest ぬ on the field takes it. If the
  // monster you were answering reached the ward mid-glyph, the character is
  // still correct and still finds a mark; if nothing on the field carries it,
  // the shot has nowhere to go and dissipates.
  function bearer(ch){
    let best = null;
    for (const m of monsters)
      if (LETTERS[m.i][0] === ch && (!best || m.d < best.d)) best = m;
    return best;
  }

  const _conjure = window.conjure;
  window.conjure = function(){
    const drew = LETTERS[idx][0];
    const t = bearer(drew) || (monsters.includes(locked) ? locked : null);
    if (t){
      shots.push({from:{x:cx(), y:FH-6}, to:t, t:0, ch:drew});
      if (navigator.vibrate) navigator.vibrate([12,30,40]);
    }
    // And the character is kindled whether or not anything carried it — a
    // trace with nothing to hit is banked, not wasted. Clean pays more.
    const gain = CFG.hitodamaGain + (zapped ? 0 : CFG.cleanBonus);
    kindle(drew, gain);
    const d = dash();
    for (let k=0;k<14;k++)
      motes.push({x:d.x, y:d.y, vx:(Math.random()-.5)*1.8, vy:-Math.random()*2.2,
                  life:1, wisp:true});
    const r = _conjure.apply(this, arguments);
    // The engine celebrates for 1.9s before advancing, which is dead time in a
    // game with a clock running — a fast hand finishes the next glyph before
    // the next glyph exists. Advance as soon as the shot lands instead.
    //
    // The engine's own delayed load(idx+1) needs no cancelling: load() clears
    // `done`, and that callback is guarded by it, so an early advance disarms
    // the late one. Without that it would fire mid-trace and wipe the strokes.
    setTimeout(() => { locked = null; retarget(true); }, CFG.advanceMs);
    return r;
  };

  let readings = [];
  function hit(m){
    m.hp--;
    // The sound, attached to the kill. Tracing a shape teaches the shape and
    // nothing else — the hand can learn every stroke of ぬ without the reading
    // ever arriving. Success is the moment attention is highest, so that is
    // where the reading goes.
    // The correct reading, and underneath it the way you probably said it.
    // The joke is the teaching: "SOO" next to "tsu" names the dropped t far
    // better than the correct spelling does on its own, because the learner
    // recognises the wrong one as theirs.
    if (CFG.reading !== 'off'){
      const p = px(m);
      readings.push({
        x:p.x, y:p.y, life:1,
        text: CFG.reading === 'gaijin' ? label(m.i,'gaijin') : LETTERS[m.i][2],
        sub:  CFG.reading === 'both'   ? label(m.i,'gaijin') : null,
      });
    }
    for (let k=0;k<18;k++)
      motes.push({x:px(m).x, y:px(m).y, vx:(Math.random()-.5)*2.4,
                  vy:(Math.random()-.5)*2.4, life:1});
    if (m.hp <= 0){
      monsters = monsters.filter(x => x !== m);
      if (m === locked) locked = null;
      killed++;
      // An observation, not a claim: what was answered and how long it took.
      // Deliberately not a score — the client does not get to assert totals.
      try { window.__sync && window.__sync.record('banish', {
        glyph: LETTERS[m.i][0], level: MASTERY[LETTERS[m.i][0]] || 0,
        ms: Math.round(performance.now() - m.born), sign: CFG.sign,
      }); } catch(_){}
      retarget();
    }
  }

  const px = m => ({ x: cx() + Math.cos(m.a)*m.d*FW*0.52,
                     y: cy() + Math.sin(m.a)*m.d*FH*0.52 });

  // ---- the loop
  function step(now){
    if (!tPrev) tPrev = now;
    const dt = Math.min(0.05, (now - tPrev)/1000); tPrev = now;
    if (!over){
      // Nothing to answer is not a rest, it is a dead screen. Refill at once.
      if (!monsters.length) spawnAt = Math.min(spawnAt, now);
      if (now > spawnAt){
        spawn();
        spawnAt = now + Math.max(CFG.spawnMin, CFG.spawnMs - wave*CFG.spawnRamp);
      }
      for (const m of monsters){
        m.d -= m.speed*dt;
        if (m.d <= 0.06){
          monsters = monsters.filter(x => x !== m);
          if (m === locked) locked = null;
          ward--;
          try { window.__sync && window.__sync.record('breach', {
            glyph: LETTERS[m.i][0], wardLeft: ward, wave,
          }); } catch(_){}
          retarget();
          if (navigator.vibrate) navigator.vibrate(90);
          if (ward <= 0){ over = true; toast('the ward falls ✦ tap to begin again'); }
        }
      }
      autocast(now);
      for (const s of shots){
        s.t += dt*2.6;
        if (s.t >= 1){ hit(s.to); }
      }
      shots = shots.filter(s => s.t < 1 && monsters.includes(s.to));
    }
    // Deferred work, once the hand is free: a queued retarget, or a glyph that
    // no monster carries any more — which would otherwise strand the player
    // tracing a character that can no longer hit anything.
    if (!over && !tracing()){
      if (pendingRetarget) retarget();
      else if (monsters.length && !bearer(LETTERS[idx][0])) retarget();
    }
    for (const p of motes){ p.x += p.vx; p.y += p.vy; p.life -= dt*1.6; }
    motes = motes.filter(p => p.life > 0);
    for (const r of readings){ r.y -= dt*26; r.life -= dt*0.85; }
    readings = readings.filter(r => r.life > 0);
    draw();
  }
  function loop(now){ step(now); requestAnimationFrame(loop); }

  function draw(){
    const g = fc.getContext('2d');
    g.clearRect(0,0,FW,FH);
    const X = cx(), Y = cy();

    // the ward being protected
    const pulse = 0.6 + 0.4*Math.sin(performance.now()/700);
    g.save();
    g.shadowColor = 'rgba(233,196,106,.8)'; g.shadowBlur = 26*pulse;
    g.fillStyle = over ? 'rgba(120,60,50,.9)' : 'rgba(233,196,106,.92)';
    g.beginPath(); g.arc(X, Y, 13, 0, 6.284); g.fill();
    g.restore();
    g.strokeStyle = over ? 'rgba(200,90,70,.35)' : 'rgba(233,196,106,.22)';
    g.lineWidth = 1;
    g.beginPath(); g.arc(X, Y, 26 + 5*pulse, 0, 6.284); g.stroke();

    // ward health, as pips under it
    for (let k=0;k<CFG.wardHp;k++){
      g.fillStyle = k < ward ? 'rgba(233,196,106,.85)' : 'rgba(233,196,106,.14)';
      g.beginPath(); g.arc(X - (CFG.wardHp-1)*5 + k*10, Y + 34, 3, 0, 6.284); g.fill();
    }

    const tgt = target();
    for (const m of monsters){
      const p = px(m), isT = m === tgt;
      const bob = Math.sin(performance.now()/500 + m.wob)*2.5;

      // the farang: a pale drifting shape, brighter the closer it gets
      const near = 1 - m.d;
      g.save();
      g.globalAlpha = 0.5 + 0.5*near;
      g.shadowColor = isT ? 'rgba(127,209,196,.75)' : 'rgba(150,170,190,.4)';
      g.shadowBlur = isT ? 20 : 10;
      g.fillStyle = isT ? 'rgba(127,209,196,.30)' : 'rgba(170,185,200,.20)';
      g.beginPath(); g.ellipse(p.x, p.y+bob, 17, 21, 0, 0, 6.284); g.fill();
      g.restore();

      // the sign it carries
      const label = sign(m);
      g.font = (CFG.sign === 'romaji' ? '600 15px' : '600 22px')
        + ' ui-sans-serif,system-ui,"Klee One",sans-serif';
      const w = g.measureText(label).width + 18;
      const by = p.y + bob - 36;
      g.fillStyle = isT ? 'rgba(20,32,32,.92)' : 'rgba(22,24,28,.85)';
      g.strokeStyle = isT ? 'rgba(127,209,196,.65)' : 'rgba(180,195,210,.28)';
      g.lineWidth = 1;
      g.beginPath();
      if (g.roundRect) g.roundRect(p.x-w/2, by-16, w, 27, 8);
      else g.rect(p.x-w/2, by-16, w, 27);
      g.fill(); g.stroke();
      g.beginPath(); g.moveTo(p.x-5, by+11); g.lineTo(p.x, by+18); g.lineTo(p.x+5, by+11);
      g.fillStyle = isT ? 'rgba(20,32,32,.92)' : 'rgba(22,24,28,.85)'; g.fill();
      g.fillStyle = isT ? '#bdf0e6' : 'rgba(226,232,240,.8)';
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(label, p.x, by-2);
      // a lit character: its own wisp will answer this one
      if (charge(LETTERS[m.i][0]) >= 1){
        g.save();
        g.shadowColor = 'rgba(127,209,196,.9)'; g.shadowBlur = 10;
        g.fillStyle = 'rgba(160,230,215,.95)';
        g.beginPath(); g.arc(p.x + w/2 + 2, by-14, 3.2, 0, 6.284); g.fill();
        g.restore();
      }
    }

    // the glyph in flight
    for (const s of shots){
      const p = px(s.to);
      const t = s.t, e = t*t*(3-2*t);
      const x = s.from.x + (p.x - s.from.x)*e;
      const y = s.from.y + (p.y - s.from.y)*e - Math.sin(t*Math.PI)*46;
      g.save();
      if (s.auto){
        // the ghost light, cold and trailing, the character faint inside it
        for (let k=3;k>=1;k--){
          const tt = Math.max(0, t - k*0.05), ee = tt*tt*(3-2*tt);
          const tx = s.from.x + (p.x - s.from.x)*ee;
          const ty = s.from.y + (p.y - s.from.y)*ee - Math.sin(tt*Math.PI)*46;
          g.globalAlpha = 0.28 - k*0.07;
          g.fillStyle = 'rgba(127,209,196,1)';
          g.beginPath(); g.arc(tx, ty, 9 - k*1.5, 0, 6.284); g.fill();
        }
        g.globalAlpha = 0.95;
        g.shadowColor = 'rgba(127,209,196,.95)'; g.shadowBlur = 22;
        g.fillStyle = 'rgba(190,240,228,.9)';
        g.beginPath(); g.ellipse(x, y, 11, 13, 0, 0, 6.284); g.fill();
        g.shadowBlur = 0;
        g.fillStyle = 'rgba(20,40,40,.9)';
        g.font = '700 15px ui-sans-serif,system-ui,"Klee One",sans-serif';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(s.ch, x, y+1);
      } else {
        g.globalAlpha = 0.9;
        g.shadowColor = 'rgba(233,196,106,.9)'; g.shadowBlur = 18;
        g.fillStyle = '#ffe9a8';
        g.font = '700 26px ui-sans-serif,system-ui,"Klee One",sans-serif';
        g.textAlign = 'center'; g.textBaseline = 'middle';
        g.fillText(s.ch, x, y);
      }
      g.restore();
    }

    for (const r of readings){
      const a = Math.min(1, r.life*1.6);
      g.save();
      g.globalAlpha = a;
      g.shadowColor = 'rgba(233,196,106,.9)'; g.shadowBlur = 16;
      g.fillStyle = '#ffe9a8';
      g.font = `700 ${Math.round(26 + 10*(1-r.life))}px ui-sans-serif,system-ui`;
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(r.text, r.x, r.y);
      if (r.sub){
        g.globalAlpha = a*0.8;
        g.fillStyle = '#9fd8cc';
        g.font = `600 ${Math.round(15 + 5*(1-r.life))}px ui-sans-serif,system-ui`;
        g.fillText(r.sub, r.x, r.y + 26);
      }
      g.restore();
    }
    for (const p of motes){
      g.globalAlpha = Math.max(0, p.life);
      g.fillStyle = p.wisp ? '#a8ecdc' : '#ffe9a8';
      g.fillRect(p.x, p.y, 2, 2);
    }
    g.globalAlpha = 1;

    // ---- the hitodama dash: the character in the sketchbook and how many
    // ghost lights it holds. Sits on the seam between field and sketchbook,
    // which is where the wisps set out from.
    {
      const ch = LETTERS[idx][0], c = charge(ch), cap = CFG.hitodamaCap;
      const d = dash();
      const pipW = 14, w = 58 + cap*pipW;
      const x0 = d.x - w/2;
      g.fillStyle = 'rgba(16,22,24,.78)';
      g.strokeStyle = c >= 1 ? 'rgba(127,209,196,.45)' : 'rgba(233,196,106,.16)';
      g.lineWidth = 1;
      g.beginPath();
      if (g.roundRect) g.roundRect(x0, d.y-13, w, 26, 13); else g.rect(x0, d.y-13, w, 26);
      g.fill(); g.stroke();
      g.textBaseline = 'middle';
      g.fillStyle = c >= 1 ? '#bdf0e6' : 'rgba(226,232,240,.75)';
      g.font = '700 17px ui-sans-serif,system-ui,"Klee One",sans-serif';
      g.textAlign = 'left';
      g.fillText(ch, x0 + 11, d.y + 1);
      g.font = '10px ui-sans-serif,system-ui';
      g.fillStyle = 'rgba(160,190,185,.7)';
      g.fillText('人魂', x0 + 32, d.y + 1);
      const flick = 0.75 + 0.25*Math.sin(performance.now()/160);
      for (let k=0;k<cap;k++){
        const px = x0 + 58 + k*pipW + 4, lit = k < c;
        g.save();
        if (lit){ g.shadowColor = 'rgba(127,209,196,.95)'; g.shadowBlur = 9*flick; }
        g.fillStyle = lit ? 'rgba(170,236,220,.95)' : 'rgba(127,209,196,.14)';
        g.beginPath(); g.ellipse(px, d.y, 3.4, lit ? 4.6*flick+1 : 3.4, 0, 0, 6.284); g.fill();
        g.restore();
      }
    }

    g.fillStyle = 'rgba(233,196,106,.55)';
    g.font = '12px ui-sans-serif,system-ui'; g.textAlign = 'left';
    g.textBaseline = 'alphabetic';
    g.fillText(`banished ${killed}`, 12, 20);
  }

  function restart(){
    monsters = []; shots = []; motes = []; readings = [];
    ward = CFG.wardHp; over = false; wave = 0; killed = 0; locked = null;
    spawnAt = 0; tPrev = 0; castAt = 0; spawn(); retarget();
  }
  fc.addEventListener('pointerdown', e => {
    if (over){ restart(); return; }
    const r = fc.getBoundingClientRect();
    pick(e.clientX - r.left, e.clientY - r.top);
  });

  // A handle on the field, for the same reason the tracer has one: a game
  // loop that cannot be inspected can only be tested by playing it.
  window.__field = {
    get monsters(){ return monsters; },
    get shots(){ return shots; },
    get ward(){ return ward; },
    get over(){ return over; },
    get killed(){ return killed; },
    get target(){ return target(); },
    get locked(){ return locked; },
    get pending(){ return pendingRetarget; },
    get readings(){ return readings; },
    get hitodama(){ return HITODAMA; },
    charge, kindle, quench, autocast, tidy,
    touch(){ penAt = performance.now(); },
    bearer,
    spawn, restart, retarget, pick,
    posOf: px,
    frame(now){ step(now); },
  };

  // A fizzle already clears the ink, but only rewound prog by half — so the
  // player was left with an empty canvas and credit for a path they could no
  // longer see, the guide resuming from the middle of a glyph while the toast
  // said "back to the dot". Under a clock there is no time to work out where
  // that middle is. The attempt now restarts, which is what the message always
  // claimed and what the cleared ink already implied.
  const _fizzle = window.fizzle;
  window.fizzle = function(){
    const r = _fizzle.apply(this, arguments);
    if (CFG.fizzleRestarts) setTimeout(() => {
      if (!done) { loading = true; try { _load(idx); } finally { loading = false; } }
    }, 260);
    return r;
  };

  // And an explicit way out, because auto-restart only fires on a fizzle and a
  // trace can go wrong long before it trips one.
  const redo = document.createElement('button');
  redo.textContent = '↺ redo';
  redo.title = 'Start this glyph again';
  redo.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:9999;'
    + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
    + 'padding:9px 14px;font:13px ui-sans-serif,system-ui;cursor:pointer;opacity:.9';
  redo.onclick = () => { loading = true; try { _load(idx); } finally { loading = false; } };
  addEventListener('DOMContentLoaded', () => document.body.appendChild(redo));

  addEventListener('resize', sizeField);
  addEventListener('DOMContentLoaded', () => { sizeField(); resize(); });
  sizeField();
  spawn(); retarget();
  requestAnimationFrame(loop);
})();
</script>
"""


def config(pack):
    """The field's tuning, as a JS object literal written into the page."""
    f = pack.get("field") or {}
    sign = f.get("sign", "kana")
    if sign not in ("kana", "romaji", "gaijin"):
        raise SystemExit(f"field.sign must be kana, romaji or gaijin, not {sign!r}")
    reading = f.get("reading", "both")
    if reading not in ("romaji", "gaijin", "both", "off"):
        raise SystemExit(f"field.reading must be romaji, gaijin, both or off, not {reading!r}")
    return (
        "<script>window.__FIELD_CFG={"
        f"sign:{sign!r},"
        f"speed:{f.get('speed', 0.055)},"
        f"wardHp:{int(f.get('wardHp', 5))},"
        f"spawnMs:{int(f.get('spawnMs', 5200))},"
        f"spawnRamp:{int(f.get('spawnRamp', 140))},"
        f"spawnMin:{int(f.get('spawnMin', 1800))},"
        f"advanceMs:{int(f.get('advanceMs', 460))},"
        f"reading:{reading!r},"
        f"fizzleRestarts:{'true' if f.get('fizzleRestarts', True) else 'false'},"
        f"hitodamaGain:{int(f.get('hitodamaGain', 1))},"
        f"cleanBonus:{int(f.get('cleanBonus', 1))},"
        f"hitodamaCap:{int(f.get('hitodamaCap', 6))},"
        f"castMs:{int(f.get('castMs', 900))},"
        f"holdMs:{int(f.get('holdMs', 1500))},"
        f"tidyStrays:{'true' if f.get('tidyStrays', True) else 'false'}"
        "};</script>"
    ).replace("'", '"')
