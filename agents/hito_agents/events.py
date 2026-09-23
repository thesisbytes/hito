"""Read a pull of hito.events and say what the tracing in it looks like.

Pure Python on purpose: no model, no network, no Strands. Everything here is
arithmetic over observations, so that the judgments an agent makes later sit
on numbers a test can check. The geometry is computed here; the judgment is
not (see NOTES.md, 2026-09-23).

A trace row's body is what the hand recorded at pen-up: `glyph`, `ok`, `ms`,
`zaps`, `size`, `diff`, `prof` (pen or finger, from v0.1.43; `input` before
that), `q` (the quality score, from v0.1.45; `quality` is the run's name for the
same number), and `s`, the ink itself as one flat
[x, y, t, x, y, t, ...] list per stroke in the stroke book's own space.
"""
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "events.jsonl"

RESAMPLE = 64        # points per attempt when comparing attempts
MAX_PAIRS_FROM = 20  # attempts compared pairwise per character, at most


def load(path=DATA):
    """Rows as the CLI pulled them, with `body` parsed from its JSON text."""
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            body = r.get("body")
            if isinstance(body, str):
                try:
                    r["body"] = json.loads(body)
                except ValueError:
                    r["body"] = {}
            elif body is None:
                r["body"] = {}
            rows.append(r)
    return rows


def traces(rows):
    return [r for r in rows if r.get("kind") == "trace"]


def hand_of(body):
    return body.get("prof") or body.get("input") or "?"


def quality_of(body):
    q = body.get("q", body.get("quality"))
    return q if isinstance(q, (int, float)) else None


def strokes_of(body):
    """The ink as a list of strokes, each a list of (x, y)."""
    out = []
    for s in body.get("s") or []:
        n = len(s) - len(s) % 3
        out.append([(s[i], s[i + 1]) for i in range(0, n, 3)])
    return out


def resample(pts, n=RESAMPLE):
    """`n` points evenly spaced along the polyline `pts`."""
    if not pts:
        return []
    if len(pts) == 1:
        return [pts[0]] * n
    acc = [0.0]
    for a, b in zip(pts, pts[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    total = acc[-1]
    if total == 0:
        return [pts[0]] * n
    out, j = [], 0
    for k in range(n):
        t = total * k / (n - 1)
        while j < len(acc) - 2 and acc[j + 1] < t:
            j += 1
        span = acc[j + 1] - acc[j] or 1.0
        u = (t - acc[j]) / span
        out.append((pts[j][0] + (pts[j + 1][0] - pts[j][0]) * u,
                    pts[j][1] + (pts[j + 1][1] - pts[j][1]) * u))
    return out


def chamfer(a, b):
    """Mean nearest distance, both ways. The hand's quality() uses the same
    measure between ink and the shape asked for; here it is between two of
    the hand's own attempts."""
    def one(p, q):
        return sum(min(math.dist(x, y) for y in q) for x in p) / len(p)
    return (one(a, b) + one(b, a)) / 2


def consistency(bodies):
    """How alike a hand's landed attempts at one character are.

    `spread` is the mean distance between any two attempts as a fraction of
    the character's size (the diagonal of the box all attempts fit in), so
    0 is the same ink every time and 0.1 is wandering a tenth of the glyph.
    Lower is more consistent. None until there are two landed attempts.
    """
    inked = []
    for b in bodies:
        if not b.get("ok"):
            continue
        flat = [p for s in strokes_of(b) for p in s]
        if len(flat) >= 2:
            inked.append(resample(flat))
    inked = inked[:MAX_PAIRS_FROM]
    if len(inked) < 2:
        return {"attempts": len(inked), "spread": None}
    xs = [p[0] for a in inked for p in a]
    ys = [p[1] for a in inked for p in a]
    diag = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    ds = [chamfer(inked[i], inked[j]) / diag
          for i in range(len(inked)) for j in range(i + 1, len(inked))]
    return {"attempts": len(inked), "spread": round(statistics.mean(ds), 3)}


def by_glyph(rows):
    out = defaultdict(list)
    for r in traces(rows):
        b = r["body"]
        out[b.get("glyph") or r.get("glyph")].append(b)
    return out


def summarise(bodies):
    """One character's tracing, as numbers."""
    n = len(bodies)
    landed = sum(1 for b in bodies if b.get("ok"))
    q = [quality_of(b) for b in bodies if quality_of(b) is not None]
    sizes = [b["size"] for b in bodies if isinstance(b.get("size"), (int, float))]
    return {
        "traces": n,
        "landed": landed,
        "fizzled": n - landed,
        "fizzle_rate": round((n - landed) / n, 2) if n else None,
        "zaps_per_trace": round(sum(b.get("zaps") or 0 for b in bodies) / n, 2) if n else None,
        "median_ms": int(statistics.median(b.get("ms") or 0 for b in bodies)) if n else None,
        "quality": round(statistics.mean(q), 2) if q else None,
        "quality_n": len(q),
        "size_range": [min(sizes), max(sizes)] if sizes else None,
        "by_difficulty": dict(Counter(b.get("diff") or "?" for b in bodies)),
        "by_hand": dict(Counter(hand_of(b) for b in bodies)),
        "consistency": consistency(bodies),
    }


def overview(rows):
    """What the pull holds, before anyone asks a question of it."""
    kinds = Counter(r.get("kind") for r in rows)
    ats = sorted(r.get("at") for r in rows if r.get("at"))
    ts = traces(rows)
    return {
        "rows": len(rows),
        "by_kind": dict(kinds),
        "devices": len({r.get("device") for r in rows}),
        "from": ats[0] if ats else None,
        "to": ats[-1] if ats else None,
        "versions": dict(Counter(b["body"].get("v") or "?" for b in ts)),
        "characters_traced": len(by_glyph(rows)),
        "traces_with_quality": sum(1 for r in ts if quality_of(r["body"]) is not None),
        "flags": kinds.get("flag", 0),
    }


def hardest(rows, n=10, min_traces=3):
    """Characters ranked by fizzle rate, then by spread. Thin data is left
    out rather than ranked, because one fizzle is not a hard character."""
    table = []
    for g, bodies in by_glyph(rows).items():
        if len(bodies) < min_traces:
            continue
        s = summarise(bodies)
        table.append({"glyph": g, "traces": s["traces"], "fizzle_rate": s["fizzle_rate"],
                      "zaps_per_trace": s["zaps_per_trace"], "quality": s["quality"],
                      "spread": s["consistency"]["spread"]})
    table.sort(key=lambda t: (-(t["fizzle_rate"] or 0), -(t["spread"] or 0)))
    return table[:n]
