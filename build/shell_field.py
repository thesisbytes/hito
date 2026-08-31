#!/usr/bin/env python3
"""The game shell: a battle field above, a stationary sketchbook below.

The workshop screen — gojuon chart, stroke controls, size ladder — is the
instrument this project uses on itself. The game is not that. Here the bottom
third is the sketchbook and never moves, and the top two thirds is the field:
farang advance on a centre you are protecting, each carrying the sign you have
to answer. Finish the glyph and it flies up and hits them.

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
  body.field .grid { display:none !important; }

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

  const sign = m => CFG.sign === 'romaji' ? LETTERS[m.i][2] : LETTERS[m.i][0];

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
  }

  // The most urgent monster is the one being answered. Identification proper —
  // choosing which of several to answer — waits for a mode with no guide,
  // because with the guide up the tracer has already told you the answer.
  function target(){
    let best = null;
    for (const m of monsters) if (!best || m.d < best.d) best = m;
    return best;
  }
  function targetIdx(){ const t = target(); return t ? t.i : null; }

  // ---- drive the tracer from the field
  // Every load() lands on whatever the field is asking for. conjure()'s own
  // delayed load(idx+1) therefore advances to the next target rather than to
  // the next character in the chart.
  const _load = window.load;
  let loading = false;
  window.load = function(i){
    if (loading) return _load.apply(this, arguments);
    const t = targetIdx();
    return _load.call(this, t === null ? i : t);
  };
  function retarget(){
    const t = targetIdx();
    if (t === null || t === idx) return;
    loading = true; try { _load(t); } finally { loading = false; }
  }

  // ---- a finished glyph is the attack
  const _conjure = window.conjure;
  window.conjure = function(){
    const t = target();
    if (t){
      shots.push({from:{x:cx(), y:FH-6}, to:t, t:0, ch:LETTERS[t.i][0]});
      if (navigator.vibrate) navigator.vibrate([12,30,40]);
    }
    return _conjure.apply(this, arguments);
  };

  function hit(m){
    m.hp--;
    for (let k=0;k<18;k++)
      motes.push({x:px(m).x, y:px(m).y, vx:(Math.random()-.5)*2.4,
                  vy:(Math.random()-.5)*2.4, life:1});
    if (m.hp <= 0){
      monsters = monsters.filter(x => x !== m);
      killed++;
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
      if (now > spawnAt){
        spawn();
        spawnAt = now + Math.max(CFG.spawnMin, CFG.spawnMs - wave*CFG.spawnRamp);
      }
      for (const m of monsters){
        m.d -= m.speed*dt;
        if (m.d <= 0.06){
          monsters = monsters.filter(x => x !== m);
          ward--; retarget();
          if (navigator.vibrate) navigator.vibrate(90);
          if (ward <= 0){ over = true; toast('the ward falls ✦ tap to begin again'); }
        }
      }
      for (const s of shots){
        s.t += dt*2.6;
        if (s.t >= 1){ hit(s.to); }
      }
      shots = shots.filter(s => s.t < 1 && monsters.includes(s.to));
    }
    for (const p of motes){ p.x += p.vx; p.y += p.vy; p.life -= dt*1.6; }
    motes = motes.filter(p => p.life > 0);
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
    }

    // the glyph in flight
    for (const s of shots){
      const p = px(s.to);
      const t = s.t, e = t*t*(3-2*t);
      const x = s.from.x + (p.x - s.from.x)*e;
      const y = s.from.y + (p.y - s.from.y)*e - Math.sin(t*Math.PI)*46;
      g.save();
      g.globalAlpha = 0.9;
      g.shadowColor = 'rgba(233,196,106,.9)'; g.shadowBlur = 18;
      g.fillStyle = '#ffe9a8';
      g.font = '700 26px ui-sans-serif,system-ui,"Klee One",sans-serif';
      g.textAlign = 'center'; g.textBaseline = 'middle';
      g.fillText(s.ch, x, y);
      g.restore();
    }

    for (const p of motes){
      g.globalAlpha = Math.max(0, p.life);
      g.fillStyle = '#ffe9a8';
      g.fillRect(p.x, p.y, 2, 2);
    }
    g.globalAlpha = 1;

    g.fillStyle = 'rgba(233,196,106,.55)';
    g.font = '12px ui-sans-serif,system-ui'; g.textAlign = 'left';
    g.textBaseline = 'alphabetic';
    g.fillText(`banished ${killed}`, 12, 20);
  }

  function restart(){
    monsters = []; shots = []; motes = [];
    ward = CFG.wardHp; over = false; wave = 0; killed = 0;
    spawnAt = 0; tPrev = 0; spawn(); retarget();
  }
  fc.addEventListener('pointerdown', () => { if (over) restart(); });

  // A handle on the field, for the same reason the tracer has one: a game
  // loop that cannot be inspected can only be tested by playing it.
  window.__field = {
    get monsters(){ return monsters; },
    get shots(){ return shots; },
    get ward(){ return ward; },
    get over(){ return over; },
    get killed(){ return killed; },
    get target(){ return target(); },
    spawn, restart, retarget,
    frame(now){ step(now); },
  };

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
    if sign not in ("kana", "romaji"):
        raise SystemExit(f"field.sign must be 'kana' or 'romaji', not {sign!r}")
    return (
        "<script>window.__FIELD_CFG={"
        f"sign:{sign!r},"
        f"speed:{f.get('speed', 0.055)},"
        f"wardHp:{int(f.get('wardHp', 5))},"
        f"spawnMs:{int(f.get('spawnMs', 5200))},"
        f"spawnRamp:{int(f.get('spawnRamp', 140))},"
        f"spawnMin:{int(f.get('spawnMin', 1800))}"
        "};</script>"
    ).replace("'", '"')
