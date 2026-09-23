"""System 1: a fast, calibrated label on every trace, from Laya.

The tracer's scorer is already a System 1 for the pen: every sample judged
in under a millisecond, deterministically. This is the System 1 for the
*table*: one forward pass per trace row, no text generated, a choice with
a probability on each option, and a confidence that says how much to trust
it. The LLM (System 2) is for the rows Laya is unsure about, and for
saying what the labels mean.

Laya reads numbers, not ink. So the geometry is computed here first, in
the stroke book's own space (the hand keeps its ink there, so a trace lays
straight over `strokes.json`): how much of the path the ink covered, how
far the last point stopped from the stroke's end, how much more ink than
path there was, how many strokes were drawn against how many there are.
Those are the state; Laya answers typed questions over it.

Labels, in the maintainer's words for what goes wrong:

    honest          a fair attempt at the whole path, landed or not
    stopped_short   followed the path, stopped before a stroke's end
    poked           touched the path without travelling it
    scribble        far more ink than path
    gave_up         fewer strokes than the character has, little ink

**Calibration is a claim until checked.** Laya's probabilities were
calibrated on its own tasks; on trace rows they are a hypothesis. The
`flag` events — the hand pressing "✗ fails here" — are the only human
verdicts, and `agree()` compares against them. Until there are flags, the
labels are for looking at, not for acting on.

    python -m hito_agents.system1            # label the pull -> agents/out/labels.jsonl
    python -m hito_agents.system1 --glyph ふ  # one character
"""
import json
import math
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

from . import events
from .hooks import OUT

# Every realm's stroke book, merged: hiragana, the kana of the vocab and
# katakana realms, and whatever comes next (a kanji pack is a glyph list and
# a KanjiVG-converted book, and it is picked up here by existing). Keyed by
# character, so a trace from any realm finds its shape.
BOOKS = sorted((Path(__file__).resolve().parents[2] / "scripts").glob("*/strokes.json"))
LABELS = OUT / "labels.jsonl"
MODEL = os.environ.get("HITO_LAYA_MODEL", "convaiinnovations/laya")
SCALE = 1000.0      # the book is 0..1; the hand's ink is the same space x1000
REACH = 0.08        # "near the path", as a fraction of the character's size

VERDICTS = {
    "honest": "a fair attempt at the whole path: coverage high, travel_ratio near 1, gaps small; landed or not",
    "stopped_short": "followed the path but stopped before the end of a stroke: end_gap large, coverage otherwise good",
    "poked": "touched the path without travelling it: coverage low, ink_span small, quick",
    "scribble": "far more ink than path: travel_ratio well above 2, coverage may still be high",
    "gave_up": "fewer strokes drawn than the character has, and little ink",
}

QUESTIONS = {
    "verdict": {"type": "choice",
                "instructions": "A learner traced a Japanese character on a tablet over a guide path. "
                                "From these measurements, what happened in this attempt?",
                "criteria": VERDICTS},
    "accept": {"type": "noul",
               "instructions": "Would a patient teacher accept this as a genuine attempt at the character "
                               "(a fair try, not a perfect one)?"},
}

LEGEND = ("coverage, start_covered: fraction of the path (and of the first stroke's start) the ink came near; "
          "end_gap, start_gap: distance from where the ink stopped/started to where the stroke ends/starts, as a "
          "fraction of the character's size; travel_ratio: ink length over path length (1.0 is exact); "
          "ink_span: the ink's extent over the character's; q: recognisability 0-1 if scored; ms: time.")


def narrate(f):
    """The same features as a sentence or two. Laya's backbone is a text
    encoder; a row of floats and a paragraph are not the same input to it."""
    parts = [f"A learner traced the character {f['glyph']} in {f['difficulty']} mode with a {f['hand']}"
             + (f" at size {f['size']}" if f.get("size") is not None else "") + "."]
    parts.append(("The tracer accepted it" if f["landed"] else "The tracer rejected it")
                 + (f" after {f['zaps']} zaps" if f.get("zaps") else " with no zaps") + f", in {f['ms']} ms.")
    if f.get("strokes_expected") is not None:
        parts.append(f"The character has {f['strokes_expected']} strokes; the learner drew {f['strokes_drawn']}.")
    if "coverage" in f:
        parts.append(f"The ink came near {int(f['coverage'] * 100)}% of the path and {int(f['start_covered'] * 100)}% of the first stroke's start.")
        parts.append(f"It started {int(f['start_gap'] * 100)}% of the character's size from where the stroke starts and stopped "
                     f"{int(f['end_gap'] * 100)}% from where the stroke ends, which is {int(f['end_gap_stroke'] * 100)}% of that stroke's own length.")
        parts.append(f"There was {f['travel_ratio']:.2f} times as much ink as path, spanning {f['ink_span']:.2f} of the character's extent.")
    if f.get("q") is not None:
        parts.append(f"Recognisability was scored {f['q']:.2f} out of 1.")
    return " ".join(parts)


def load_book(paths=None):
    book = {}
    for path in (paths or BOOKS):
        b = json.loads(Path(path).read_text(encoding="utf-8"))
        letters = b["fonts"][b["activeFont"]]["letters"]
        for ch, v in letters.items():
            book.setdefault(ch, [[(q["x"] * SCALE, q["y"] * SCALE) for q in s] for s in v["strokes"]])
    return book


def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def seg_dist(p, a, b):
    """Distance from point p to segment ab."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0:
        return math.dist(p, a)
    t = max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.dist(p, (ax + t * dx, ay + t * dy))


def diag(pts):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return math.hypot(max(xs) - min(xs), max(ys) - min(ys)) if pts else 0.0


def features(body, book):
    """The numbers Laya reads for one trace. Geometry only where the book
    knows the character and the trace carries ink."""
    glyph = body.get("glyph")
    ink = [s for s in events.strokes_of(body) if len(s) >= 1]
    exp = book.get(glyph)
    f = {
        "glyph": glyph, "landed": bool(body.get("ok")), "zaps": body.get("zaps") or 0, "ms": body.get("ms") or 0,
        "size": body.get("size"), "difficulty": body.get("diff") or "?", "hand": events.hand_of(body),
        "q": events.quality_of(body),
        "strokes_expected": len(exp) if exp else None, "strokes_drawn": len(ink),
    }
    if not exp or not ink:
        return f
    E = [p for s in exp for p in s]
    D = diag(E) or 1.0
    I = [p for s in ink for p in s]
    # The hand thins its ink to at most 64 points a stroke, so a long stroke
    # has gaps between samples; "near the ink" is near the line it drew, not
    # near one of the points it kept.
    segs = [(s[i], s[i + 1]) for s in ink for i in range(len(s) - 1)] or [(I[0], I[0])]
    path = sum(length(s) for s in exp) or 1.0
    reach = REACH * D

    def near(p):
        return any(seg_dist(p, a, b) < reach for a, b in segs)

    P = [p for s in exp for p in events.resample(s, 24)]
    first = events.resample(exp[0], 24)[:8]
    k = min(len(ink), len(exp)) - 1
    last_len = length(exp[k]) or 1.0
    end = math.dist(ink[-1][-1], exp[k][-1])
    f.update({
        "travel_ratio": round(sum(length(s) for s in ink) / path, 2),
        "coverage": round(sum(map(near, P)) / len(P), 2),
        "start_covered": round(sum(map(near, first)) / len(first), 2),
        "start_gap": round(math.dist(ink[0][0], exp[0][0]) / D, 3),
        "end_gap": round(end / D, 3),
        # The engine judges a stroke's end against the stroke's own length
        # (endTol, PACK.md): 7% of the character is most of one of ふ's ticks.
        # The hand's verdicts (2026-09-23) said so before the number did.
        "end_gap_stroke": round(end / last_len, 2),
        "ink_span": round(diag(I) / D, 2),
    })
    return f


def partial(body):
    """Guided traces from builds before v0.1.43 hold only their last stroke
    (a capture bug, fixed). They are not attempts and must not be labelled."""
    try:
        v = tuple(int(x) for x in str(body.get("v", "")).split("."))
    except ValueError:
        return False
    return body.get("diff") == "guided" and v < (0, 1, 43)


class Laya:
    """The model, loaded on first use. `predict(state, questions)` is the
    whole interface, so a test can hand in a function instead."""

    def __init__(self, model=MODEL):
        self.model = model
        self._agent = None

    @property
    def agent(self):
        if self._agent is None:
            import laya
            self._agent = laya.load(self.model)
        return self._agent

    def predict(self, state, questions):
        return self.agent.predict(state, questions)

    def predict_many(self, states, questions, batch_size=16):
        return self.agent.predict_batch(states, questions, batch_size=batch_size)


def read(answer):
    """One question's answer, flattened: the choice or P(true), the
    per-option probabilities, and Laya's confidence."""
    if answer.get("type") == "noul" or "noul" in answer:
        return {"value": round(float(answer.get("noul", 0.0)), 3), "confidence": answer.get("confidence")}
    return {"value": answer.get("choice"), "p": {k: round(float(v), 3) for k, v in (answer.get("probabilities") or {}).items()},
            "confidence": answer.get("confidence")}


STYLE = os.environ.get("HITO_LAYA_STATE", "prose")   # prose | json


def state_of(f, style=None):
    style = style or STYLE
    return narrate(f) if style == "prose" else {**f, "legend": LEGEND}


def label(rows, predictor=None, book=None, glyph=None, log=None, style=None, only=None):
    """Every trace in `rows`, labelled. One row out per trace in. `only`
    keeps the rows whose $id is in it (an experiment on a sample)."""
    predictor = predictor or Laya()
    book = book or load_book()
    t0 = time.time()
    ts = [r for r in events.traces(rows) if not glyph or (r["body"].get("glyph") or r.get("glyph")) == glyph]
    ts = [r for r in ts if not partial(r["body"])]
    if only is not None:
        ts = [r for r in ts if r.get("$id") in only]
    feats = [features(r["body"], book) for r in ts]
    states = [state_of(f, style) for f in feats]
    if hasattr(predictor, "predict_many"):
        results = predictor.predict_many(states, QUESTIONS)
    elif hasattr(predictor, "predict"):
        results = [predictor.predict(s, QUESTIONS) for s in states]
    else:
        results = [predictor(s, QUESTIONS) for s in states]
    out = []
    for r, f, res in zip(ts, feats, results):
        a = res.get("answers", res)
        v, acc = read(a["verdict"]), read(a["accept"])
        out.append({"id": r.get("$id"), "device": r.get("device"), "at": r.get("at"), **f,
                    "verdict": v["value"], "p": v.get("p"), "confidence": v["confidence"],
                    "accept": acc["value"], "accept_confidence": acc["confidence"]})
    if log:
        log(f"  {len(out)} traces in {time.time() - t0:.0f}s")
    return out


def summary(labels):
    """By character: how many of each verdict, and the least confident rows."""
    by = defaultdict(list)
    for l in labels:
        by[l["glyph"]].append(l)
    table = {}
    for g, ls in by.items():
        table[g] = {"traces": len(ls), "verdicts": dict(Counter(l["verdict"] for l in ls)),
                    "accept": round(statistics.mean(l["accept"] for l in ls), 2),
                    "confidence": round(statistics.mean(l["confidence"] or 0 for l in ls), 2)}
    unsure = sorted(labels, key=lambda l: l["confidence"] or 0)[:10]
    return {"characters": table, "totals": dict(Counter(l["verdict"] for l in labels)),
            "least_confident": [{"id": l["id"], "glyph": l["glyph"], "verdict": l["verdict"], "confidence": l["confidence"]}
                                for l in unsure]}


def agree(labels, rows, size_tolerance=0.05):
    """Laya against the hand. A flag says 'impossible here' about a character
    at a size on a device; the traces around it should not read as scribbles
    or giving up. No flags, no verdict — only the note that there are none."""
    flags = [r for r in rows if r.get("kind") == "flag"]
    if not flags:
        return {"flags": 0, "note": "no flag events yet: play the debug build and press ✗ fails here"}
    report = []
    for fl in flags:
        b = fl["body"]
        g, dev, size = b.get("glyph") or fl.get("glyph"), fl.get("device"), b.get("size")
        near = [l for l in labels if l["glyph"] == g and l["device"] == dev
                and (size is None or l["size"] is None or abs(l["size"] - size) <= size_tolerance)]
        report.append({"glyph": g, "size": size, "device": dev, "traces_near": len(near),
                       "verdicts": dict(Counter(l["verdict"] for l in near)),
                       "hand_says": "impossible here", "laya_agrees": bool(near) and all(l["verdict"] in ("honest", "stopped_short") for l in near)})
    agreed = sum(1 for r in report if r["laya_agrees"])
    return {"flags": len(flags), "agreed": agreed, "rate": round(agreed / len(flags), 2), "per_flag": report}


def load_labels(path=LABELS):
    if not Path(path).is_file():
        return None
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    glyph = argv[argv.index("--glyph") + 1] if "--glyph" in argv else None
    rows = events.load()
    labels = label(rows, glyph=glyph, log=print)
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    with open(LABELS, "w", encoding="utf-8") as f:
        for l in labels:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    s = summary(labels)
    print(f"{len(labels)} traces labelled -> {LABELS.relative_to(Path.cwd()) if LABELS.is_relative_to(Path.cwd()) else LABELS}")
    print("  totals:", s["totals"])
    print("  least confident:", [(u["glyph"], u["verdict"], u["confidence"]) for u in s["least_confident"][:5]])
    print("  against the hand:", json.dumps(agree(labels, rows), ensure_ascii=False)[:300])


if __name__ == "__main__":
    main()
