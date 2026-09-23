#!/usr/bin/env python3
"""A page of traces for the hand to judge: the ink over the shape asked for,
the geometry, Laya's guess, and a row of verdict buttons. The verdicts are
the first labels of our own (NOTES.md, 2026-09-23), so the page keeps them
in its own store and `agents/verdicts.py` reads them back into
agents/data/verdicts.jsonl.

    agents/.venv/bin/python agents/verdicts_page.py out.html   # the 24-trace sample

The output is somebody's handwriting; it goes to a private page, never the
repository, so the default output is the scratch directory.
"""
import html
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hito_agents import events, system1  # noqa: E402

VERDICTS = [("honest", "fair attempt"), ("stopped_short", "stopped short"), ("poked", "poked, not travelled"),
            ("scribble", "scribble"), ("gave_up", "gave up"), ("unsure", "can't tell")]


def sample(rows):
    ts = events.traces(rows)
    fizz = [r for r in ts if not r["body"].get("ok")]
    land = [r for r in ts if r["body"].get("ok")][::25][:11]
    return fizz + land


def svg_path(pts):
    return "".join(f"{'L' if i else 'M'}{int(x)} {int(y)}" for i, (x, y) in enumerate(pts))


def card(r, f, lab, book):
    b = r["body"]
    ch = f["glyph"]
    ref = "".join(f'<path d="{svg_path(s)}"/>' for s in book.get(ch, []))
    ink = "".join(f'<path d="{svg_path(s)}"/>' for s in events.strokes_of(b))
    status = "landed" if f["landed"] else "fizzled"
    tags = " · ".join(str(x) for x in (f["hand"], f["difficulty"], f"size {f['size']}" if f.get("size") is not None else None, f"v{b.get('v', '?')}") if x)
    geo = (f"covered <b>{int(f['coverage'] * 100)}%</b> · stopped <b>{int(f['end_gap'] * 100)}%</b> short · ink <b>{f['travel_ratio']:.2f}×</b> path · strokes <b>{f['strokes_drawn']}/{f['strokes_expected']}</b>"
           if "coverage" in f else "no geometry")
    laya = f"Laya: {lab['verdict'].replace('_', ' ')} {lab['p'].get(lab['verdict'], 0):.2f}, confidence {lab['confidence']:.2f}" if lab else "Laya: not run"
    btns = "".join(f'<button type="button" class="v" data-id="{r["$id"]}" data-v="{k}" id="b-{r["$id"][:8]}-{k}">{html.escape(t)}</button>' for k, t in VERDICTS)
    return (f'<article class="card {status}" data-id="{r["$id"]}"><div class="pic"><svg viewBox="150 150 700 760" fill="none" stroke-linecap="round" stroke-linejoin="round" aria-label="trace of {html.escape(ch)}">'
            f'<g class="ref" stroke-width="46">{ref}</g><g class="ink" stroke-width="18">{ink}</g></svg></div>'
            f'<div class="meta"><div class="head"><span class="glyph">{html.escape(ch)}</span><span class="chip {status}">{status}</span>'
            f'{"<span class=\"chip zaps\">" + str(f["zaps"]) + " zaps</span>" if f.get("zaps") else ""}</div>'
            f'<p class="tags">{html.escape(tags)} · {(f["ms"] or 0) / 1000:.1f}s</p><p class="geo">{geo}</p><p class="laya">{html.escape(laya)}</p>'
            f'<div class="verdicts" role="group" aria-label="your verdict">{btns}</div></div></article>')


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("scratch") / "verdicts.html"
    rows = events.load()
    book = system1.load_book()
    labels = {l["id"]: l for l in (system1.load_labels() or [])}
    cards = [card(r, system1.features(r["body"], book), labels.get(r["$id"]), book) for r in sample(rows)]
    n = len(cards)
    page = f'''<title>Hito Verdicts</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&display=swap">
<style>
:root{{--bg:#f3f6f9;--panel:#ffffff;--line:#d5dee8;--ink:#17242f;--dim:#5b6b7a;--blue:#1f6fd6;--red:#c2482a;--green:#1f9a63;--green-soft:#e2f5ec;--ref:rgba(23,36,47,.14)}}
@media (prefers-color-scheme: dark){{:root:not([data-theme="light"]){{--bg:#0a0f15;--panel:#101820;--line:#1e2f3e;--ink:#dce8f2;--dim:#8a9bab;--blue:#6cb8ff;--red:#dc5a3c;--green:#5fe3a1;--green-soft:#123326;--ref:rgba(220,232,242,.14);color-scheme:dark}}}}
:root[data-theme="dark"]{{--bg:#0a0f15;--panel:#101820;--line:#1e2f3e;--ink:#dce8f2;--dim:#8a9bab;--blue:#6cb8ff;--red:#dc5a3c;--green:#5fe3a1;--green-soft:#123326;--ref:rgba(220,232,242,.14);color-scheme:dark}}
body{{background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding-block:20px 40px;padding-inline:16px;max-width:1100px;margin:0 auto}}
h1{{font-family:"Klee One","Hiragino Maru Gothic ProN","Yu Gothic",sans-serif;font-weight:600;font-size:26px;margin:0 0 4px;text-wrap:balance}}
.lede{{color:var(--dim);max-width:62ch;margin:0 0 14px}}
.bar{{position:sticky;top:env(safe-area-inset-top,0px);background:var(--bg);padding-block:8px;margin-bottom:14px;border-bottom:1px solid var(--line);display:flex;gap:12px;align-items:baseline;flex-wrap:wrap;font-variant-numeric:tabular-nums}}
.bar b{{color:var(--green)}} .bar .note{{color:var(--dim);font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}}
.card{{display:grid;grid-template-columns:120px 1fr;gap:12px;background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px}}
@media (max-width:420px){{.card{{grid-template-columns:100px 1fr}}}}
.pic svg{{width:100%;height:auto;display:block;border-radius:8px;background:var(--bg)}}
.ref{{stroke:var(--ref)}} .landed .ink{{stroke:var(--blue)}} .fizzled .ink{{stroke:var(--red)}}
.head{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.glyph{{font-family:"Klee One","Hiragino Maru Gothic ProN","Yu Gothic",sans-serif;font-size:30px;line-height:1;font-weight:600}}
.chip{{font-size:11px;letter-spacing:.04em;text-transform:uppercase;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}}
.chip.landed{{color:var(--blue);border-color:var(--blue)}} .chip.fizzled{{color:var(--red);border-color:var(--red)}}
.tags,.geo,.laya{{margin:4px 0 0;font-size:13px;color:var(--dim)}} .geo b{{color:var(--ink);font-weight:600}}
.verdicts{{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}}
.v{{font:inherit;font-size:13px;padding:6px 10px;border-radius:8px;border:1px solid var(--line);background:transparent;color:var(--ink);cursor:pointer}}
.v:hover{{border-color:var(--blue)}} .v:focus-visible{{outline:2px solid var(--blue);outline-offset:2px}}
.v[aria-pressed="true"]{{background:var(--green-soft);border-color:var(--green);color:var(--green);font-weight:600}}
.v:disabled{{opacity:.5;cursor:default}}
@media (prefers-reduced-motion:no-preference){{.v{{transition:border-color .15s,background .15s}}}}
</style>
<h1>Hito Verdicts</h1>
<p class="lede">{n} traces from the table: every fizzle so far, and a spread of landed ones. Grey is the shape that was asked for, blue landed, red fizzled, same coordinate space, no fitting. Say what the hand did. Your verdicts are the first labels Laya will be tuned on.</p>
<div class="bar"><span><b id="done">0</b> of {n} judged</span><span class="note" id="note">Verdicts save as you tap.</span></div>
<div class="grid">{"".join(cards)}</div>
<script>
(function(){{
  const N = {n};
  const state = {{}};
  let db = null, writable = true;
  const doneEl = document.getElementById("done"), noteEl = document.getElementById("note");
  function paint(){{
    document.querySelectorAll(".v").forEach(b => b.setAttribute("aria-pressed", String(state[b.dataset.id] === b.dataset.v)));
    doneEl.textContent = Object.keys(state).length;
  }}
  document.querySelectorAll(".v").forEach(b => b.addEventListener("click", async () => {{
    const id = b.dataset.id, v = b.dataset.v;
    if (state[id] === v) return;
    state[id] = v; paint();
    if (!db || !writable) return;
    const card = b.closest(".card");
    try {{
      await db.doc("verdicts/" + id).set({{verdict: v, glyph: card.querySelector(".glyph").textContent, at: new Date().toISOString()}});
    }} catch (e) {{
      if (e && e.code === "invalid_argument") {{ writable = false; noteEl.textContent = "This view can't save verdicts; they stay on this screen only."; }}
      else noteEl.textContent = "Couldn't save that one; tap it again in a moment.";
    }}
  }}));
  paint();
  (async () => {{
    try {{ db = await window.claude.use("db"); }} catch (e) {{ db = null; }}
    if (!db) {{ noteEl.textContent = "Verdicts can't be saved in this view; they stay on this screen only."; return; }}
    db.collection("verdicts").onSnapshot(snap => {{
      snap.docs.forEach(d => {{ const x = d.data(); if (x && x.verdict) state[d.id] = x.verdict; }});
      paint();
      noteEl.textContent = Object.keys(state).length ? "Saved. Tap again to change one." : "Verdicts save as you tap.";
    }}, err => {{ noteEl.textContent = "Saved verdicts can't be read right now."; }});
  }})();
}})();
</script>
'''
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{out}  {n} traces, {sum(1 for c in cards if 'fizzled' in c.split('class=\"card ')[1][:8])} fizzled")


if __name__ == "__main__":
    main()
