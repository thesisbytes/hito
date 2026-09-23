#!/usr/bin/env python3
"""A pack's stroke book as a chart: every character with its strokes numbered
at their starts and an arrow at their ends, for checking order and direction
against a textbook by eye. Checked against Genki I's hiragana and katakana
charts on 2026-09-23 (NOTES.md): 92 of 92 agreed, そ included.

    book_chart.py scripts/vocab/strokes.json out.html [characters]

Counts can be checked without eyes; order and direction cannot, and a chart
that puts both next to a textbook page is what a new realm (kanji next) needs
before its book is trusted.
"""
import html
import json
import math
import sys
from pathlib import Path


def cell(ch, strokes):
    out = []
    for n, s in enumerate(strokes, 1):
        pts = [(q["x"] * 100, q["y"] * 100) for q in s]
        d = "".join(f"{'L' if i else 'M'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(pts))
        (ax, ay), (bx, by) = (pts[-2] if len(pts) > 1 else pts[-1]), pts[-1]
        ang = math.degrees(math.atan2(by - ay, bx - ax))
        out.append(f'<path d="{d}" stroke="#222" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
                   f'<g transform="translate({bx:.1f},{by:.1f}) rotate({ang:.0f})"><path d="M-4,-2.5 L0,0 L-4,2.5" stroke="#d33" stroke-width="1.4" fill="none"/></g>'
                   f'<circle cx="{pts[0][0]:.1f}" cy="{pts[0][1]:.1f}" r="3.2" fill="#d33"/>'
                   f'<text x="{pts[0][0] - 9:.1f}" y="{pts[0][1] - 4:.1f}" font-size="7" fill="#d33" font-weight="700">{n}</text>')
    return f'<figure><svg viewBox="18 18 64 64">{"".join(out)}</svg><figcaption>{html.escape(ch)} · {len(strokes)}</figcaption></figure>'


def main():
    book, out = Path(sys.argv[1]), Path(sys.argv[2])
    only = sys.argv[3] if len(sys.argv) > 3 else None
    b = json.loads(book.read_text(encoding="utf-8"))
    letters = b["fonts"][b["activeFont"]]["letters"]
    chars = [c for c in (only or "".join(letters)) if c in letters]
    page = ('<!doctype html><meta charset="utf-8"><title>stroke book</title>'
            '<style>body{margin:8px;background:#fff;font:11px system-ui}.g{display:grid;grid-template-columns:repeat(10,96px);gap:4px}'
            'figure{margin:0;text-align:center}svg{width:96px;height:96px;border:1px solid #ddd}figcaption{font-size:14px}</style>'
            f'<h3>{html.escape(str(book))} — red dot: start, number: order, arrow: direction</h3><div class="g">'
            + "".join(cell(c, letters[c]["strokes"]) for c in chars) + '</div>')
    out.write_text(page, encoding="utf-8")
    print(f"{out}  {len(chars)} characters")


if __name__ == "__main__":
    main()
