#!/usr/bin/env python3
"""Add attempt telemetry to a build, so a trace session leaves evidence.

The engine scores attempts but records nothing about them. This appends a
capture layer that logs what was actually drawn — every stroke, every pen
lift, every zap, and whether the glyph was accepted — so the scoring can be
argued about with data instead of impressions.

It attaches its own pointer listeners in the capture phase rather than
reaching into the engine's internals, so it does not depend on any of the
engine's local bindings and cannot perturb its behaviour. The only functions
it wraps are the global ones whose calls mark an outcome.

    instrument.py <in.html> <out.html>
"""

import re
import sys
from pathlib import Path

LAYER = r"""
<script>
/* ---- attempt telemetry -------------------------------------------------
   Records what was drawn and what the engine decided. Export with the button
   in the corner, or from the console: __hito.export()
   Nothing here changes scoring; it only observes.                        */
(function(){
  const KEY = 'hito-attempts';
  const log = [];
  let cur = null, strokes = [], stroke = null, zaps = 0, t0 = 0;
  let level = 0, fizzles = 0, lastToast = null;

  function expected(ch){
    try { return DEFAULT_BOOK.fonts[TEACHER.activeFont].letters[ch].strokes.length; }
    catch(_){ return null; }
  }

  function flush(outcome){
    if (!cur || !strokes.length) { reset(); return; }
    let coverage = null;
    try { coverage = +covered().toFixed(3); } catch(_){}
    log.push({
      char: cur,
      level,                         // mastery level at the time
      expectedStrokes: expected(cur),
      drawnStrokes: strokes.length,
      penLifts: strokes.length - 1,
      points: strokes.map(s => s.length),
      zaps,
      fizzles,                       // attempt restarts before this outcome
      reason: lastToast,             // why the engine complained, if it did
      coverage,
      outcome,
      ms: Math.round(performance.now() - t0),
      at: new Date().toISOString(),
      strokes,                       // normalised 0..1, for offline analysis
    });
    save();
    reset();
  }
  function reset(){
    strokes = []; stroke = null; zaps = 0; fizzles = 0; lastToast = null;
    t0 = performance.now();
    try { level = MASTERY[LETTERS[idx][0]] || 0; } catch(_){ level = 0; }
  }

  function save(){
    try { localStorage.setItem(KEY, JSON.stringify(log)); } catch(_){}
    const b = document.getElementById('__tel');
    if (b) b.textContent = `● ${log.length} attempt${log.length===1?'':'s'}`;
  }

  // ---- outcomes: wrap the globals whose calls mean something happened
  // The toast text is the engine's own explanation of a refusal — the
  // difference between "missed 40% of the path" and "too much wandering" is
  // exactly what a bug report cannot tell us, so capture it.
  const _toast = window.toast, _fizzle = window.fizzle;
  window.toast = function(m){ lastToast = m; return _toast.apply(this, arguments); };
  window.fizzle = function(){ fizzles++; return _fizzle.apply(this, arguments); };

  const _conjure = window.conjure, _zap = window.zap, _load = window.load;
  window.conjure = function(){ flush('conjured'); return _conjure.apply(this, arguments); };
  window.zap     = function(){ zaps++;            return _zap.apply(this, arguments); };
  window.load    = function(i){
    if (cur !== null) flush('abandoned');
    const r = _load.apply(this, arguments);
    try { cur = LETTERS[idx][0]; } catch(_){ cur = null; }
    reset();
    return r;
  };

  // ---- what was drawn: our own listeners, capture phase, passive
  const pad = document.getElementById('ink');
  const box = () => pad.getBoundingClientRect();
  const at = e => { const r = box();
    return [ +(((e.clientX-r.left)/r.width).toFixed(4)),
             +(((e.clientY-r.top )/r.height).toFixed(4)) ]; };

  pad.addEventListener('pointerdown', e => { stroke = [at(e)]; }, true);
  pad.addEventListener('pointermove', e => {
    if (!stroke) return;
    const c = e.getCoalescedEvents ? e.getCoalescedEvents() : [];
    (c.length ? c : [e]).forEach(s => stroke.push(at(s)));
  }, true);
  const up = () => { if (stroke && stroke.length > 1) strokes.push(stroke); stroke = null; };
  pad.addEventListener('pointerup', up, true);
  pad.addEventListener('pointercancel', up, true);

  // ---- grid toggle
  const GRIDS = ['cross','quarters','none'];
  function cycleGrid(){
    try {
      GRID_MODE = GRIDS[(GRIDS.indexOf(GRID_MODE)+1) % GRIDS.length];
      const b = document.getElementById('__gr');
      if (b) b.textContent = 'grid: ' + GRID_MODE;
      drawGuide();
      return GRID_MODE;
    } catch(_){ return null; }
  }

  // ---- mastery control
  // A glyph that becomes unpassable is also untestable, because there is no
  // way back down. This sets the level for the current character directly.
  function setLevel(n){
    try {
      const ch = LETTERS[idx][0];
      if (n <= 0) delete MASTERY[ch]; else MASTERY[ch] = n;
      persistM(); load(idx);
      const b = document.getElementById('__lv');
      if (b) b.textContent = 'lv ' + (MASTERY[ch] || 0) + ' ▲▼';
      return MASTERY[ch] || 0;
    } catch(_){ return null; }
  }

  // ---- shadow mode toggle
  // Three ways to show the target, cycled live so they can be compared on the
  // same glyph instead of across deploys:
  //   none    only the trail — road ahead, dots, and the stroke already made
  //   strokes a thick faint path under the trail
  //   font    the glyph drawn in the trace font (misaligned by design: the
  //           stroke data describes KanjiVG's letterforms, not this font's)
  // easy / medium / hard, matching the pack's `mode` presets.
  const MODES = [
    {name:'easy',   shadow:'none',    guide:true,  numbers:true},
    {name:'medium', shadow:'strokes', guide:false, numbers:false},
    {name:'hard',   shadow:'none',    guide:false, numbers:false},
  ];
  let modeIdx = 0;
  function cycleShadow(){
    try {
      modeIdx = (modeIdx+1) % MODES.length;
      const m = MODES[modeIdx];
      SHADOW_MODE = m.shadow; GUIDE_ON = m.guide; GUIDE_NUMBERS = m.numbers;
      const b = document.getElementById('__sm');
      if (b) b.textContent = 'mode: ' + m.name;
      drawGuide();
      return m.name;
    } catch(_){ return null; }
  }

  // ---- alignment nudge
  // The baked coordinates assume canvas anchors textBaseline='middle' at the
  // em-square middle (0.38 em above the baseline for Klee One). Chrome may
  // instead use hhea metrics, which would put it at 0.436. Rather than guess,
  // this lets the alignment be corrected by eye and the numbers reported back.
  const ALIGN = (function(){
    try { return DEFAULT_BOOK.alignment || {baseF:0.62, glyphCy:0.44}; }
    catch(_){ return {baseF:0.62, glyphCy:0.44}; }
  })();
  const PRISTINE = JSON.parse(JSON.stringify(
    (function(){ try { return DEFAULT_BOOK.fonts; } catch(_){ return {}; } })()));

  function realign(scale, cy){
    for (const fid in PRISTINE){
      const src = PRISTINE[fid].letters, dst = TEACHER.fonts[fid];
      if (!dst) continue;
      for (const ch in src){
        dst.letters[ch] = { strokes: src[ch].strokes.map(st => st.map(q => {
          // undo the baked transform, then re-apply the nudged one
          const kx = (q.x - 0.5) / ALIGN.baseF + 0.5;
          const ky = (q.y - 0.5) / ALIGN.baseF + ALIGN.glyphCy;
          return { x: +(0.5 + scale*(kx - 0.5)).toFixed(4),
                   y: +(0.5 + scale*(ky - cy)).toFixed(4), p: q.p, t: q.t };
        })) };
      }
    }
    try { load(idx); } catch(_){}
  }

  // ---- size control
  // The whole point of separating size from mastery. SIZE_PIN holds one size
  // while the alphabet is walked, so the question becomes "which glyph fails
  // at which size" instead of "which level was I on", which is what made the
  // last bug take three releases to corner.
  const SIZE_LADDER = (function(){
    const out = [];
    try {
      for (let f = SIZE_MAX; f >= SIZE_MIN - 1e-9; f -= 0.02) out.push(Math.round(f*1000)/1000);
      if (!out.length || out[out.length-1] > SIZE_MIN) out.push(SIZE_MIN);
    } catch(_){ }
    return out.length ? out : [0.62];
  })();
  let sizeIdx = 0;

  const glyphPx = () => { try { return Math.round(document.getElementById('ink').getBoundingClientRect().height * curF); }
                          catch(_){ return null; } };
  function syncSize(){
    const b = document.getElementById('__sz');
    if (!b) return;
    let f = null; try { f = curF; } catch(_){}
    const pinned = (function(){ try { return SIZE_PIN != null; } catch(_){ return false; } })();
    b.textContent = (pinned ? 'pinned ' : 'size ') + (f==null ? '?' : f.toFixed(2))
      + (glyphPx()==null ? '' : ` · ${glyphPx()}px`);
    b.style.color = pinned ? '#7fd1c4' : '#ece4d8';
  }
  function setSizeIdx(i){
    try {
      sizeIdx = Math.max(0, Math.min(SIZE_LADDER.length-1, i));
      SIZE_PIN = SIZE_LADDER[sizeIdx];
      load(idx); syncSize();
      return SIZE_PIN;
    } catch(_){ return null; }
  }
  function unpinSize(){
    try { SIZE_PIN = null; load(idx); syncSize(); } catch(_){}
  }
  // Walking the alphabet at a fixed size is the sweep. Navigation already
  // calls load(), and a pinned size survives it, so next/prev is the loop.
  function stepGlyph(d){ try { load(idx + d); syncSize(); } catch(_){} }

  // ---- the fail flag
  // A fizzle is one bad attempt; "this is impossible here" is a judgement only
  // the hand can make, after several. The engine cannot infer it, so it gets a
  // button. Everything needed to tell the three suspects apart is captured at
  // the moment it is pressed: the size (difficulty curve), the glyph (stroke
  // data), and the live accumulators (state).
  const flags = [];
  const FKEY = 'hito-size-flags';
  try { const r = localStorage.getItem(FKEY); if (r) flags.push(...JSON.parse(r)); } catch(_){}
  function saveFlags(){
    try { localStorage.setItem(FKEY, JSON.stringify(flags)); } catch(_){}
    const b = document.getElementById('__fl');
    if (b) b.textContent = `✗ fails here (${flags.length})`;
  }
  function flagFail(){
    let rec = {at: new Date().toISOString()};
    try { rec.char = LETTERS[idx][0]; } catch(_){}
    try { rec.romaji = LETTERS[idx][2]; } catch(_){}
    try { rec.size = +curF.toFixed(3); } catch(_){}
    try { rec.px = glyphPx(); } catch(_){}
    try { rec.pinned = SIZE_PIN != null; } catch(_){}
    try { rec.level = MASTERY[LETTERS[idx][0]] || 0; } catch(_){}
    try { rec.coverage = +covered().toFixed(3); } catch(_){}
    try { rec.travel = PATHLEN ? +(travel/PATHLEN).toFixed(2) : null; } catch(_){}
    try { rec.progress = prog; rec.stroke = segIdx; } catch(_){}
    try { rec.attempts = fizzles; } catch(_){}
    rec.reason = lastToast;
    try { rec.mode = MODES[modeIdx].name; } catch(_){}
    flags.push(rec); saveFlags();
    // Also into the outbox, so a flag can reach a machine without the
    // mobile-devtools detour that reading the first three of these took.
    try { window.__sync && window.__sync.record('flag', rec); } catch(_){}
    // _toast, not toast: the wrapper records lastToast, and a flag
    // confirmation is not the engine's explanation of anything.
    try { _toast(`flagged: ${rec.char} at ${rec.size} (${rec.px}px)`); } catch(_){}
    return rec;
  }

  // A glyph × size grid is the thing the flags are for; rendering it here
  // means it can be read on the tablet without exporting anything first.
  function matrix(){
    if (!flags.length) return '(nothing flagged yet)';
    const sizes = [...new Set(flags.map(f=>f.size))].sort((a,b)=>b-a);
    const chars = [...new Set(flags.map(f=>f.char))];
    const head = 'glyph  ' + sizes.map(s=>s.toFixed(2)).join(' ');
    const rows = chars.map(c => {
      const cells = sizes.map(s => {
        const n = flags.filter(f=>f.char===c && f.size===s).length;
        return String(n || '·').padStart(4);
      });
      return `  ${c}   ${cells.join(' ')}`;
    });
    return [head, ...rows].join('\n');
  }

  // ---- export
  window.__hito = {
    realign,
    cycleShadow,
    cycleGrid,
    setLevel,
    setSize: f => setSizeIdx(SIZE_LADDER.indexOf(
      SIZE_LADDER.reduce((a,b)=>Math.abs(b-f)<Math.abs(a-f)?b:a))),
    sizeUp: () => setSizeIdx(sizeIdx-1),
    sizeDown: () => setSizeIdx(sizeIdx+1),
    unpinSize,
    sizes: SIZE_LADDER,
    flagFail,
    matrix,
    alignment: ALIGN,
    get log(){ return log; },
    get flags(){ return flags; },
    clearFlags(){ flags.length = 0; saveFlags(); },
    export(){
      const payload = {
        exported: new Date().toISOString(),
        canvasPx: (function(){ try { return Math.round(
          document.getElementById('ink').getBoundingClientRect().height); } catch(_){ return null; } })(),
        sizeLadder: SIZE_LADDER,
        flags,                         // "impossible here", judged by the hand
        matrix: matrix(),              // the same thing, readable
        attempts: log,
      };
      const blob = new Blob([JSON.stringify(payload, null, 1)], {type:'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `hito-attempts-${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.json`;
      a.click();
    },
    clear(){ log.length = 0; try{ localStorage.removeItem(KEY); }catch(_){} save(); },
    stepGlyph,
  };

  addEventListener('DOMContentLoaded', () => {
    const b = document.createElement('button');
    b.id = '__tel';
    b.textContent = '● 0 attempts';
    b.title = 'Download this session\'s attempts';
    b.style.cssText = 'position:fixed;right:10px;bottom:10px;z-index:9999;'
      + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
      + 'padding:7px 12px;font:12px ui-sans-serif,system-ui;cursor:pointer;opacity:.85';
    b.onclick = () => window.__hito.export();
    document.body.appendChild(b);

    const sb = document.createElement('button');
    sb.id = '__sm';
    sb.textContent = 'mode: easy';
    sb.title = 'Cycle easy / medium / hard';
    sb.style.cssText = 'position:fixed;left:10px;bottom:10px;z-index:9999;'
      + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
      + 'padding:7px 12px;font:12px ui-sans-serif,system-ui;cursor:pointer;opacity:.85';
    sb.onclick = cycleShadow;
    document.body.appendChild(sb);

    const gb = document.createElement('button');
    gb.id = '__gr';
    gb.textContent = 'grid: ' + (typeof GRID_MODE !== 'undefined' ? GRID_MODE : '?');
    gb.title = 'Cycle the practice grid';
    gb.style.cssText = 'position:fixed;left:120px;bottom:10px;z-index:9999;'
      + 'background:#1d1a16;color:#e9c46a;border:1px solid #57492f;border-radius:7px;'
      + 'padding:7px 12px;font:12px ui-sans-serif,system-ui;cursor:pointer;opacity:.85';
    gb.onclick = cycleGrid;
    document.body.appendChild(gb);

    const lv = document.createElement('div');
    lv.style.cssText = 'position:fixed;left:10px;bottom:48px;z-index:9999;display:flex;gap:4px';
    const mk = (t, fn) => { const b=document.createElement('button');
      b.textContent=t; b.onclick=fn;
      b.style.cssText='background:#1d1a16;color:#e9c46a;border:1px solid #57492f;'
        +'border-radius:7px;padding:7px 10px;font:12px ui-sans-serif,system-ui;'
        +'cursor:pointer;opacity:.85'; return b; };
    const lab = document.createElement('button');
    lab.id='__lv'; lab.textContent='lv ?';
    lab.style.cssText='background:#1d1a16;color:#ece4d8;border:1px solid #2f2a24;'
      +'border-radius:7px;padding:7px 10px;font:12px ui-sans-serif,system-ui;cursor:default';
    lv.append(mk('−', ()=>setLevel((MASTERY[LETTERS[idx][0]]||0)-1)), lab,
                mk('+', ()=>setLevel((MASTERY[LETTERS[idx][0]]||0)+1)),
                mk('reset all', ()=>{ for(const k in MASTERY) delete MASTERY[k];
                  persistM(); load(idx); setLevel(0); }));
    document.body.appendChild(lv);
    const sync=()=>{ lab.textContent='lv '+(MASTERY[LETTERS[idx][0]]||0); };
    sync(); setInterval(() => { sync(); syncSize(); }, 400);

    // ---- size row: the sweep controls
    // Deliberately a row of its own above the mastery row. They look alike but
    // they are no longer the same axis, and conflating them is the mistake
    // this whole build exists to stop making.
    const sz = document.createElement('div');
    sz.style.cssText = 'position:fixed;left:10px;bottom:86px;z-index:9999;display:flex;gap:4px';
    const szLab = document.createElement('button');
    szLab.id = '__sz'; szLab.textContent = 'size ?';
    szLab.title = 'Tap to release the pin and let the mode choose again';
    szLab.style.cssText = 'background:#1d1a16;color:#ece4d8;border:1px solid #2f2a24;'
      + 'border-radius:7px;padding:7px 10px;font:12px ui-sans-serif,system-ui;cursor:pointer';
    szLab.onclick = unpinSize;
    sz.append(mk('◀', ()=>stepGlyph(-1)),
              mk('−', ()=>setSizeIdx(sizeIdx+1)),   // down the ladder = smaller
              szLab,
              mk('+', ()=>setSizeIdx(sizeIdx-1)),
              mk('▶', ()=>stepGlyph(1)));
    document.body.appendChild(sz);

    // ---- the fail flag, put where a thumb already is
    const fb = document.createElement('button');
    fb.id = '__fl';
    fb.textContent = `✗ fails here (${flags.length})`;
    fb.title = 'This glyph cannot be traced at this size';
    fb.style.cssText = 'position:fixed;right:10px;bottom:48px;z-index:9999;'
      + 'background:#2a1614;color:#ef8a7a;border:1px solid #6b3129;border-radius:7px;'
      + 'padding:7px 12px;font:12px ui-sans-serif,system-ui;cursor:pointer;opacity:.9';
    fb.onclick = flagFail;
    document.body.appendChild(fb);

    syncSize();

  });

  reset();
})();
</script>
"""


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dest = Path(sys.argv[1]), Path(sys.argv[2])
    s = src.read_text(encoding="utf-8")

    if "hito-attempts" in s:
        sys.exit(f"{src.name} is already instrumented.")
    for name in ("function conjure", "function zap", "function load"):
        if name not in s:
            sys.exit(f"cannot find {name} — the engine has changed shape.")

    # Must land after the engine's own script, so the globals exist to wrap.
    #
    # Replaced through a lambda, because re.sub expands escapes in a
    # replacement *string*: a literal \n anywhere in the layer would become a
    # real newline and break whatever line it landed in. stitch.py learned
    # this the same way. The layer must go in exactly as written.
    s, n = re.subn(r"</body>", lambda _: LAYER + "</body>", s, count=1)
    if n != 1:
        sys.exit("no </body> to append to.")

    dest.write_text(s, encoding="utf-8")
    print(f"{dest}  {dest.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
