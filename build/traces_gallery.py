#!/usr/bin/env python3
"""Every trace in the events table, as a page of SVGs over the shape that was asked for.

    traces_gallery.py [out.html] [--device dXXXXXXXXXXXXXXXX] [--glyph つ] [--limit 500]

Reads the table through the Appwrite CLI you are already logged in with, so it
needs no key and only works for somebody who could read the table anyway. The
default output is scratch/handwriting.html, which is gitignored on purpose:
this is people's handwriting, and it does not belong in a public repository.

A trace is in the stroke book's own space (see scripts/PACK.md, "The hand"),
so it is drawn straight over the reference with no fitting. What looks off in
the picture is what was off in the hand.

Traces from builds before v0.1.43 drawn in guided mode hold only their last
stroke — a capture bug, fixed — and are marked so nobody mistakes a lone
dakuten for somebody's が.
"""

import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def rows(args):
    cmd = ["appwrite", "tablesdb", "list-rows", "--database-id", "hito", "--table-id", "events",
           "--filter", "kind=trace", "--sort-desc", "$createdAt", "--limit", "100", "--raw"]
    if args.get("device"):
        cmd += ["--filter", f"device={args['device']}"]
    if args.get("glyph"):
        cmd += ["--filter", f"glyph={args['glyph']}"]
    out, cursor, want = [], None, int(args.get("limit", 500))
    while len(out) < want:
        page = json.loads(subprocess.run(cmd + (["--cursor-after", cursor] if cursor else []),
                                         capture_output=True, text=True, check=True).stdout)["rows"]
        if not page:
            break
        out += page
        cursor = page[-1]["$id"]
        if len(page) < 100:
            break
    return out[:want]


def book():
    letters = {}
    for pack in ("hiragana", "vocab"):
        fonts = json.loads((ROOT / "scripts" / pack / "strokes.json").read_text(encoding="utf-8")).get("fonts", {})
        for f in fonts.values():
            for ch, rec in f.get("letters", {}).items():
                letters.setdefault(ch, rec["strokes"])
    return letters


def path(flat):
    pts = [(flat[i], flat[i + 1]) for i in range(0, len(flat) - 2, 3)]
    return "".join(f"{'L' if i else 'M'}{int(x)} {int(y)}" for i, (x, y) in enumerate(pts))


def older(v):
    try:
        return tuple(int(x) for x in v.split(".")) < (0, 1, 43)
    except Exception:
        return False


def main():
    argv, args, out = sys.argv[1:], {}, None
    while argv:
        a = argv.pop(0)
        if a.startswith("--"):
            args[a[2:]] = argv.pop(0)
        else:
            out = Path(a)
    out = out or ROOT / "scratch" / "handwriting.html"
    letters, cells = book(), []
    for r in rows(args):
        b = json.loads(r.get("body") or "{}")
        ch, s = b.get("glyph", "?"), b.get("s") or []
        ref = "".join(f'<path d="{"".join(("L" if i else "M") + str(round(q["x"]*1000)) + " " + str(round(q["y"]*1000)) for i, q in enumerate(st))}"/>'
                      for st in letters.get(ch, []))
        partial = b.get("diff") == "guided" and older(str(b.get("v", "")))
        note = "last stroke only (old capture bug)" if partial else ("fizzled" if not b.get("ok") else f"{b.get('ms', 0)/1000:.1f}s")
        tags = " · ".join(x for x in (b.get("prof") or b.get("input"), b.get("diff"), f"v{b.get('v')}") if x)
        cells.append(
            f'<figure class="{"ok" if b.get("ok") else "no"}{" part" if partial else ""}"><svg viewBox="150 150 700 760" fill="none" stroke-linecap="round" stroke-linejoin="round">'
            f'<g class="ref" stroke-width="46">{ref}</g><g class="ink" stroke-width="18">{"".join(f"<path d=\"{path(f)}\"/>" for f in s)}</g></svg>'
            f'<figcaption><b>{html.escape(ch)}</b> {html.escape(note)}<small>{html.escape(tags)} · {html.escape(r["device"][:6])}… · {html.escape(r["$createdAt"][:16])}</small></figcaption></figure>')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""<!doctype html><meta charset="utf-8"><title>hito · handwriting</title>
<style>body{{background:#0a0f15;color:#dce8f2;font:13px system-ui;margin:20px}}h1{{color:#6cb8ff;font-size:20px}}
.g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}}figure{{margin:0;background:#101820;border:1px solid #1e2f3e;border-radius:10px;padding:6px;text-align:center}}
svg{{width:100%;height:auto}}.ref{{stroke:rgba(220,232,242,.14)}}.ok .ink{{stroke:#6cb8ff}}.no .ink{{stroke:#dc5a3c}}.part{{opacity:.45}}
b{{font-size:17px;color:#5fe3a1}}small{{display:block;color:rgba(220,232,242,.5);font-size:10.5px}}</style>
<h1>hito · {len(cells)} traces, newest first</h1><p>Blue landed, red fizzled, grey is the shape that was asked for. Same coordinate space, no fitting.</p>
<div class="g">{''.join(cells)}</div>""", encoding="utf-8")
    print(f"{out}  {len(cells)} traces")


if __name__ == "__main__":
    main()
