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

  function expected(ch){
    try { return DEFAULT_BOOK.fonts[TEACHER.activeFont].letters[ch].strokes.length; }
    catch(_){ return null; }
  }

  function flush(outcome){
    if (!cur || !strokes.length) { reset(); return; }
    log.push({
      char: cur,
      expectedStrokes: expected(cur),
      drawnStrokes: strokes.length,
      penLifts: strokes.length - 1,
      points: strokes.map(s => s.length),
      zaps,
      outcome,
      ms: Math.round(performance.now() - t0),
      at: new Date().toISOString(),
      strokes,                       // normalised 0..1, for offline analysis
    });
    save();
    reset();
  }
  function reset(){ strokes = []; stroke = null; zaps = 0; t0 = performance.now(); }

  function save(){
    try { localStorage.setItem(KEY, JSON.stringify(log)); } catch(_){}
    const b = document.getElementById('__tel');
    if (b) b.textContent = `● ${log.length} attempt${log.length===1?'':'s'}`;
  }

  // ---- outcomes: wrap the globals whose calls mean something happened
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

  // ---- export
  window.__hito = {
    realign,
    alignment: ALIGN,
    get log(){ return log; },
    export(){
      const blob = new Blob([JSON.stringify(log, null, 1)], {type:'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `hito-attempts-${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.json`;
      a.click();
    },
    clear(){ log.length = 0; try{ localStorage.removeItem(KEY); }catch(_){} save(); },
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

    const panel = document.createElement('div');
    panel.style.cssText = 'position:fixed;left:10px;bottom:10px;z-index:9999;'
      + 'background:#1d1a16;border:1px solid #2f2a24;border-radius:8px;padding:10px 12px;'
      + 'font:12px ui-sans-serif,system-ui;color:#ece4d8;opacity:.9;min-width:210px';
    panel.innerHTML =
      '<div style="color:#8d8378;margin-bottom:7px">guide alignment</div>'
      + '<label style="display:block;margin-bottom:5px">size '
      + '<input id="__as" type="range" min="0.35" max="0.95" step="0.005" '
      + `value="${ALIGN.baseF}" style="width:100%"></label>`
      + '<label style="display:block">height '
      + '<input id="__ac" type="range" min="0.25" max="0.65" step="0.005" '
      + `value="${ALIGN.glyphCy}" style="width:100%"></label>`
      + '<div id="__av" style="margin-top:7px;font-family:ui-monospace,monospace;'
      + `color:#e9c46a">baseF ${ALIGN.baseF}  cy ${ALIGN.glyphCy}</div>`;
    document.body.appendChild(panel);
    const as = panel.querySelector('#__as'), ac = panel.querySelector('#__ac');
    const apply = () => {
      const s = +as.value, c = +ac.value;
      panel.querySelector('#__av').textContent = `baseF ${s.toFixed(3)}  cy ${c.toFixed(3)}`;
      realign(s, c);
    };
    as.oninput = apply; ac.oninput = apply;
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
    s, n = re.subn(r"</body>", LAYER + "</body>", s, count=1)
    if n != 1:
        sys.exit("no </body> to append to.")

    dest.write_text(s, encoding="utf-8")
    print(f"{dest}  {dest.stat().st_size/1024:.0f} KB")


if __name__ == "__main__":
    main()
