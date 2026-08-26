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

  // ---- export
  window.__hito = {
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
