#!/usr/bin/env python3
"""Convert KanjiVG stroke-order SVGs into the tracer's recording format.

KanjiVG gives us stroke centrelines as cubic Beziers on a 109x109 grid, in
stroke order. The tracer wants what the teacher-recording mode produces: a
list of strokes, each a list of {x, y, p, t} samples normalised to 0..1.

    TEACHER.fonts[fontId].letters[char] = {strokes: [[{x,y,p,t}, ...], ...]}

Pressure is synthetic (the pen display records at uniform width anyway) and
timestamps are derived from arc length at a constant pen speed, so the guide
comet moves evenly rather than racing the curvy parts.

Usage:  kanjivg_to_strokes.py <kanjivg-kanji-dir> <glyphs.json> <out.json>

KanjiVG is CC BY-SA 3.0 and requires attribution in the app footer.
"""

import json
import re
import sys
from pathlib import Path

VIEWBOX = 109.0        # KanjiVG canvas, both axes
SPACING = 0.01         # resample every 1% of the canvas (~1.1px)
PEN_SPEED = 0.7        # normalised units per second; low = beginner pacing
MIN_SAMPLES = 4        # keep even a tick like the one in う traceable

NUM = re.compile(r"-?\d*\.?\d+(?:e-?\d+)?")


def parse_path(d):
    """KanjiVG uses only 'M' (absolute move) and 'c' (relative cubic)."""
    tokens = re.findall(r"[MmCcLlZz]|" + NUM.pattern, d)
    cubics, pos, start, i, cmd = [], (0.0, 0.0), None, 0, None

    def take(n):
        nonlocal i
        vals = [float(tokens[i + k]) for k in range(n)]
        i += n
        return vals

    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd, i = t, i + 1
            if cmd in "Zz":
                continue
        if cmd is None:
            raise ValueError(f"path data starts without a command: {d[:40]}")

        if cmd == "M":
            x, y = take(2)
            pos = (x, y)
            start = pos
            cmd = "L"          # per SVG spec, extra pairs after M are lineto
        elif cmd == "m":
            dx, dy = take(2)
            pos = (pos[0] + dx, pos[1] + dy)
            start = pos
            cmd = "l"
        elif cmd in "Ll":
            a, b = take(2)
            nxt = (a, b) if cmd == "L" else (pos[0] + a, pos[1] + b)
            cubics.append((pos, pos, nxt, nxt))   # a line is a degenerate cubic
            pos = nxt
        elif cmd in "Cc":
            v = take(6)
            if cmd == "c":
                c1 = (pos[0] + v[0], pos[1] + v[1])
                c2 = (pos[0] + v[2], pos[1] + v[3])
                end = (pos[0] + v[4], pos[1] + v[5])
            else:
                c1, c2, end = (v[0], v[1]), (v[2], v[3]), (v[4], v[5])
            cubics.append((pos, c1, c2, end))
            pos = end
        else:
            raise ValueError(f"unhandled path command {cmd!r} in {d[:40]}")

    return cubics


def flatten(cubics, steps=48):
    """Dense polyline through every cubic, duplicates dropped."""
    pts = []
    for p0, c1, c2, p3 in cubics:
        for s in range(steps + 1):
            t = s / steps
            u = 1 - t
            x = (u * u * u * p0[0] + 3 * u * u * t * c1[0]
                 + 3 * u * t * t * c2[0] + t * t * t * p3[0])
            y = (u * u * u * p0[1] + 3 * u * u * t * c1[1]
                 + 3 * u * t * t * c2[1] + t * t * t * p3[1])
            if not pts or abs(x - pts[-1][0]) > 1e-9 or abs(y - pts[-1][1]) > 1e-9:
                pts.append((x, y))
    return pts


def resample(pts, spacing):
    """Even arc-length spacing, with cumulative length carried along."""
    if len(pts) < 2:
        return [(pts[0][0], pts[0][1], 0.0)] if pts else []

    cum, total = [0.0], 0.0
    for a, b in zip(pts, pts[1:]):
        total += ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
        cum.append(total)

    n = max(MIN_SAMPLES, int(total / spacing) + 1)
    out, j = [], 0
    for k in range(n + 1):
        target = total * k / n
        while j < len(cum) - 2 and cum[j + 1] < target:
            j += 1
        span = cum[j + 1] - cum[j]
        f = 0.0 if span <= 0 else (target - cum[j]) / span
        x = pts[j][0] + (pts[j + 1][0] - pts[j][0]) * f
        y = pts[j][1] + (pts[j + 1][1] - pts[j][1]) * f
        out.append((x, y, target))
    return out


def convert(svg_path):
    text = svg_path.read_text(encoding="utf-8")
    # Read raw rather than via a parser: the DOCTYPE carries an external DTD
    # reference, and resolving it would mean a network fetch per file.
    body = text.split("<svg", 1)[1]
    ds = re.findall(r'<path[^>]*\sd="([^"]+)"', body)
    if not ds:
        raise ValueError(f"no path data in {svg_path.name}")

    strokes = []
    for d in ds:
        pts = resample(flatten(parse_path(d)), SPACING * VIEWBOX)
        strokes.append([
            {
                "x": round(x / VIEWBOX, 4),
                "y": round(y / VIEWBOX, 4),
                "p": 1.0,
                "t": int(round(dist / VIEWBOX / PEN_SPEED * 1000)),
            }
            for x, y, dist in pts
        ])
    return strokes


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    kanji_dir, glyphs_file, out_file = (Path(a) for a in sys.argv[1:])

    glyphs = json.loads(glyphs_file.read_text(encoding="utf-8"))["glyphs"]
    font_id = json.loads(glyphs_file.read_text(encoding="utf-8"))["traceFont"]

    letters, total_pts, missing = {}, 0, []
    for g in glyphs:
        cp = int(g["cp"][2:], 16)
        svg = kanji_dir / f"{cp:05x}.svg"
        if not svg.exists():
            missing.append(g["char"])
            continue
        strokes = convert(svg)
        letters[g["char"]] = {"strokes": strokes}
        total_pts += sum(len(s) for s in strokes)
        print(f"  {g['char']}  {g['romaji']:<3} {len(strokes)} strokes, "
              f"{sum(len(s) for s in strokes)} pts")

    if missing:
        sys.exit(f"missing KanjiVG source for: {' '.join(missing)}")

    book = {
        "version": 2,
        "activeFont": font_id,
        "fonts": {font_id: {"letters": letters}},
        "customFonts": [],
        "source": "KanjiVG (https://kanjivg.tagaini.net), CC BY-SA 3.0",
        "note": ("Generated by build/kanjivg_to_strokes.py. Stroke centrelines "
                 "are KanjiVG's, not Klee One's outlines — they follow the same "
                 "textbook forms but are not glyph-exact."),
    }
    out_file.write_text(json.dumps(book, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    print(f"\n{len(letters)} glyphs, {total_pts} points -> {out_file} "
          f"({out_file.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
