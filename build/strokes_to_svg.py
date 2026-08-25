#!/usr/bin/env python3
"""Turn recorded stroke point-arrays into KanjiVG-shaped SVG.

This is the inverse of kanjivg_to_strokes.py, and it is the piece KhienThai
needs: a recording session produces sampled points, and the dataset wants
smooth cubic Beziers in stroke order, one <path> per stroke, on the same
109x109 canvas KanjiVG uses. Matching that shape means renderers and
animation libraries built for KanjiVG work on Thai unmodified.

Curve fitting is Schneider's algorithm (Graphics Gems, 1990): fit one cubic
to the whole stroke, measure the worst deviation, reparameterise if close,
split and recurse if not. The result follows the pen rather than
interpolating every sample, which is what keeps recorded jitter out of the
dataset.

    strokes_to_svg.py <strokes.json> <out-dir> [--tolerance N] [--smooth N]

Destined for the KhienThai project; it lives here until that repo exists.
"""

import json
import math
import sys
from pathlib import Path

VIEWBOX = 109.0
DEFAULT_TOLERANCE = 0.35   # canvas units; KanjiVG coords sit on ~0.01 precision


# ---------------------------------------------------------------- vectors

def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def add(a, b):
    return (a[0] + b[0], a[1] + b[1])


def mul(a, s):
    return (a[0] * s, a[1] * s)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def norm(a):
    m = math.hypot(*a)
    return (0.0, 0.0) if m == 0 else (a[0] / m, a[1] / m)


# ---------------------------------------------------------------- bezier

def bezier(p, t):
    """Point on a cubic at parameter t."""
    u = 1 - t
    return (u*u*u*p[0][0] + 3*u*u*t*p[1][0] + 3*u*t*t*p[2][0] + t*t*t*p[3][0],
            u*u*u*p[0][1] + 3*u*u*t*p[1][1] + 3*u*t*t*p[2][1] + t*t*t*p[3][1])


def bezier_prime(p, t):
    u = 1 - t
    return (3*u*u*(p[1][0]-p[0][0]) + 6*u*t*(p[2][0]-p[1][0]) + 3*t*t*(p[3][0]-p[2][0]),
            3*u*u*(p[1][1]-p[0][1]) + 6*u*t*(p[2][1]-p[1][1]) + 3*t*t*(p[3][1]-p[2][1]))


def bezier_double_prime(p, t):
    return (6*(1-t)*(p[2][0]-2*p[1][0]+p[0][0]) + 6*t*(p[3][0]-2*p[2][0]+p[1][0]),
            6*(1-t)*(p[2][1]-2*p[1][1]+p[0][1]) + 6*t*(p[3][1]-2*p[2][1]+p[1][1]))


def chord_length_parameterize(pts):
    u = [0.0]
    for i in range(1, len(pts)):
        u.append(u[-1] + math.hypot(*sub(pts[i], pts[i-1])))
    total = u[-1]
    return [x / total for x in u] if total else [0.0] * len(pts)


def generate_bezier(pts, u, t1, t2):
    """Least-squares fit of one cubic to pts, with fixed end tangents."""
    n = len(pts)
    a = [(mul(t1, 3*(1-t)**2*t), mul(t2, 3*(1-t)*t*t)) for t in u]

    c = [[0.0, 0.0], [0.0, 0.0]]
    x = [0.0, 0.0]
    for i in range(n):
        c[0][0] += dot(a[i][0], a[i][0])
        c[0][1] += dot(a[i][0], a[i][1])
        c[1][0] = c[0][1]
        c[1][1] += dot(a[i][1], a[i][1])
        t = u[i]
        tmp = sub(pts[i], add(
            add(mul(pts[0], (1-t)**3), mul(pts[0], 3*(1-t)**2*t)),
            add(mul(pts[-1], 3*(1-t)*t*t), mul(pts[-1], t**3))))
        x[0] += dot(a[i][0], tmp)
        x[1] += dot(a[i][1], tmp)

    det_c = c[0][0]*c[1][1] - c[1][0]*c[0][1]
    det_x = x[0]*c[1][1] - x[1]*c[0][1]
    det_y = c[0][0]*x[1] - c[1][0]*x[0]

    alpha_l = 0.0 if abs(det_c) < 1e-12 else det_x / det_c
    alpha_r = 0.0 if abs(det_c) < 1e-12 else det_y / det_c

    seg = math.hypot(*sub(pts[-1], pts[0]))
    if alpha_l < 1e-6 or alpha_r < 1e-6:
        # Degenerate fit — fall back to Wu/Barsky heuristic
        alpha_l = alpha_r = seg / 3.0
    return [pts[0], add(pts[0], mul(t1, alpha_l)),
            add(pts[-1], mul(t2, alpha_r)), pts[-1]]


def max_error(pts, bez, u):
    worst, at = 0.0, len(pts) // 2
    for i in range(1, len(pts) - 1):
        d = sub(bezier(bez, u[i]), pts[i])
        dist = d[0]*d[0] + d[1]*d[1]
        if dist > worst:
            worst, at = dist, i
    return math.sqrt(worst), at


def reparameterize(pts, u, bez):
    out = []
    for p, t in zip(pts, u):
        d = sub(bezier(bez, t), p)
        num = dot(d, bezier_prime(bez, t))
        den = (dot(bezier_prime(bez, t), bezier_prime(bez, t))
               + dot(d, bezier_double_prime(bez, t)))
        out.append(t if abs(den) < 1e-12 else t - num / den)
    return out


def fit_cubic(pts, t1, t2, tol, depth=0):
    if len(pts) == 2:
        d = math.hypot(*sub(pts[1], pts[0])) / 3.0
        return [[pts[0], add(pts[0], mul(t1, d)), add(pts[1], mul(t2, d)), pts[1]]]

    u = chord_length_parameterize(pts)
    bez = generate_bezier(pts, u, t1, t2)
    err, split = max_error(pts, bez, u)

    if err < tol:
        return [bez]

    if err < tol * tol and depth < 20:
        for _ in range(20):
            u = reparameterize(pts, u, bez)
            bez = generate_bezier(pts, u, t1, t2)
            err, split = max_error(pts, bez, u)
            if err < tol:
                return [bez]

    if depth > 24:                       # stop recursing on pathological input
        return [bez]

    centre = norm(sub(pts[split-1], pts[split+1]))
    return (fit_cubic(pts[:split+1], t1, centre, tol, depth+1)
            + fit_cubic(pts[split:], mul(centre, -1), t2, tol, depth+1))


# ---------------------------------------------------------------- output

def fmt(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def to_path_data(curves):
    """Absolute M plus relative c, exactly the shape KanjiVG emits."""
    d = f"M{fmt(curves[0][0][0])},{fmt(curves[0][0][1])}"
    cur = curves[0][0]
    for c in curves:
        d += "c" + ",".join(
            fmt(v) for v in (c[1][0]-cur[0], c[1][1]-cur[1],
                             c[2][0]-cur[0], c[2][1]-cur[1],
                             c[3][0]-cur[0], c[3][1]-cur[1]))
        cur = c[3]
    return d


def smooth(pts, window):
    if window < 2 or len(pts) <= window:
        return pts
    half, out = window // 2, []
    for i in range(len(pts)):
        if i == 0 or i == len(pts) - 1:
            out.append(pts[i])
            continue
        lo, hi = max(0, i-half), min(len(pts), i+half+1)
        seg = pts[lo:hi]
        out.append((sum(p[0] for p in seg)/len(seg), sum(p[1] for p in seg)/len(seg)))
    return out


def stroke_to_curves(stroke, tol, smooth_window):
    pts = [(p["x"] * VIEWBOX, p["y"] * VIEWBOX) for p in stroke]
    # drop consecutive duplicates — a held pen produces them and they make
    # tangent estimation blow up
    dedup = [pts[0]]
    for p in pts[1:]:
        if math.hypot(*sub(p, dedup[-1])) > 1e-6:
            dedup.append(p)
    if len(dedup) < 2:
        return None
    dedup = smooth(dedup, smooth_window)
    t1 = norm(sub(dedup[1], dedup[0]))
    t2 = norm(sub(dedup[-2], dedup[-1]))
    return fit_cubic(dedup, t1, t2, tol)


SVG = """<?xml version="1.0" encoding="UTF-8"?>
<!--
Stroke order data for {char} (U+{cp:04X}).
{credit}
-->
<svg xmlns="http://www.w3.org/2000/svg" width="109" height="109" viewBox="0 0 109 109">
<g id="kt:{cpl}" style="fill:none;stroke:#000000;stroke-width:3;\
stroke-linecap:round;stroke-linejoin:round;">
{paths}
</g>
</svg>
"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a.split("=")[0]: a.split("=")[1] for a in sys.argv[1:] if "=" in a}
    if len(args) != 2:
        sys.exit(__doc__)
    src, out_dir = Path(args[0]), Path(args[1])
    tol = float(flags.get("--tolerance", DEFAULT_TOLERANCE))
    smooth_window = int(flags.get("--smooth", 0))
    out_dir.mkdir(parents=True, exist_ok=True)

    book = json.loads(src.read_text(encoding="utf-8"))
    letters = book["fonts"][book["activeFont"]]["letters"]
    credit = book.get("source", "")

    total_curves = 0
    for char, rec in letters.items():
        cp = ord(char)
        paths = []
        for i, stroke in enumerate(rec["strokes"], 1):
            curves = stroke_to_curves(stroke, tol, smooth_window)
            if curves is None:
                continue
            total_curves += len(curves)
            paths.append(f'\t<path id="kt:{cp:05x}-s{i}" d="{to_path_data(curves)}"/>')
        (out_dir / f"{cp:05x}.svg").write_text(
            SVG.format(char=char, cp=cp, cpl=f"{cp:05x}",
                       credit=credit, paths="\n".join(paths)),
            encoding="utf-8")

    print(f"{len(letters)} glyphs -> {out_dir}  ({total_curves} curves, "
          f"tolerance {tol})")


if __name__ == "__main__":
    main()
