"""The fact fence: what in the analyst's answer was measured, and what was
made up to explain it.

Asked what the data said, the analyst quoted the tools' numbers correctly
and then dressed them in causes it could not know ("finger-width contact
blurs the close-loop endpoints"), and saved one of those to memory as a
fact (NOTES.md, 2026-09-24). Telling a measured sentence from an invented
one is a typed decision over text, which is what Laya was trained on — so
this is the System 1 seat, filled where it fits: not over the ink, over the
prose.

Two checks per sentence, one with a model and one without:

- **kind** (Laya): measurement, comparison, caveat, cause, suggestion, or
  other. A cause is an explanation — a mechanism, a reason — that no tool
  returned.
- **grounded** (arithmetic): every figure in the sentence appears in some
  tool result of this invocation, allowing 39% for 0.39 and rounding.

Then the answer is marked — "(guess)" before a cause, "(unverified)" before
a figure the tools never returned — and the ledger gets the counts. And a
memory write that is a cause is refused at the hook: memory takes what
was measured.

`HITO_FACTCHECK=off` switches it off; `strict` drops causes instead of
marking them. `HITO_FACTCHECK_MODEL=laya` lets Laya decide the kind instead
of the rule; either way the rule's kind is logged beside it, so the
comparison grows with every answer.
"""
import json
import os
import re

from strands.hooks import (AfterInvocationEvent, AfterModelCallEvent, AfterToolCallEvent, BeforeInvocationEvent,
                           BeforeToolCallEvent, HookProvider, HookRegistry)

KINDS = {
    "measurement": "states a figure, count, rate or time that a tool returned (e.g. 'ふ fizzled 19 of 41 times')",
    "comparison": "compares or ranks figures the tools returned, without saying why (e.g. 'も is next, then え')",
    "caveat": "says what the data cannot say: too few traces, missing builds, a limit of the measure",
    "cause": "explains WHY — a mechanism, a reason, what the hand or the finger is doing — that no tool returned",
    "suggestion": "says what to do next, what to check, or what would be needed",
    "other": "framing, a greeting, tool talk, a heading, or a sentence about the answer itself",
}
QUESTION = {"kind": {"type": "choice",
                     "instructions": "One sentence from an analyst's written answer about handwriting-practice data "
                                     "(a game where players trace Japanese characters; tools returned counts, rates and "
                                     "distances). What kind of sentence is it?",
                     "criteria": KINDS}}

NUM = re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)(\s*%)?")
SPLIT = re.compile(r"(?<=[.!?。])\s+(?=[A-Z぀-ヿ一-鿿\"'(\[*])|\n+")


def sentences(text):
    """Sentences and bullet lines, without markdown furniture."""
    out = []
    for raw in SPLIT.split(text or ""):
        s = re.sub(r"^[\s\-*•#>]+|[*_`]+", "", raw).strip()
        if len(s) >= 12 and re.search(r"[A-Za-z぀-ヿ]", s):
            out.append(s)
    return out


def figures(text):
    """Numbers in a sentence, as floats; a percent as its fraction too."""
    out = set()
    for m in NUM.finditer(text or ""):
        v = float(m.group(1))
        out.add(round(v, 3))
        if m.group(2):
            out.add(round(v / 100, 3))
    return out


def pool_from(results):
    """Every number a tool returned, in the forms a sentence might quote it."""
    pool = set()
    for text in results:
        for m in NUM.finditer(text or ""):
            v = float(m.group(1))
            for f in (v, v * 100, v / 100):
                pool.add(round(f, 3))
                pool.add(round(f, 2))
                pool.add(round(f, 1))
                pool.add(float(round(f)))
    return pool


def grounded(sentence, pool):
    """The figures in the sentence the tools never returned (empty: grounded).
    Small integers up to 12 are ordinal talk (two, four strokes) and pass."""
    missing = set()
    for f in figures(sentence):
        if f <= 12 and f == int(f):
            continue
        if not any(round(f, d) in pool for d in (3, 2, 1, 0)):
            missing.add(f)
    return sorted(missing)


class Rule:
    """A predictor with no model: a sentence with a figure is a measurement,
    'because'/'since'/'means' makes a cause, 'cannot'/'only'/'too few' a
    caveat, 'need'/'should'/'next' a suggestion. The baseline Laya has to beat,
    and the fallback when it is not installed."""

    def predict(self, state, questions):
        s = state.lower()
        if re.search(r"\b(because|since|so that|which means|meaning|confirms|the reason|due to|blurs|drift)\b", s):
            k = "cause"
        elif re.search(r"\b(cannot|can't|too few|too thin|impossible|not present|not in this|only contains|no way to)\b", s):
            k = "caveat"
        elif re.search(r"\b(you'd need|would need|should|next step|check|try|worth)\b", s):
            k = "suggestion"
        elif figures(state):
            k = "measurement"
        elif re.search(r"\b(than|next|behind|leads|highest|lowest|most|least|widest)\b", s):
            k = "comparison"
        else:
            k = "other"
        return {"answers": {"kind": {"choice": k, "probabilities": {k: 0.7}, "confidence": 0.3}}}


def check(text, results, predictor=None):
    """One row per sentence: the kind that decides, the rule's kind beside
    it (so a model can be compared with the rule on every answer), the
    model's probability and confidence, and the figures the tools never
    returned. The rule decides unless a model is given: on eight sentences
    of the first answer checked (2026-09-24) Laya agreed with the hand four
    times and the rule seven, and the rule was written after reading them."""
    predictor = predictor or Rule()
    pool = pool_from(results)
    rows = []
    ss = sentences(text)
    if not ss:
        return rows
    if hasattr(predictor, "predict_many"):
        res = predictor.predict_many(ss, QUESTION)
    else:
        res = [predictor.predict(s, QUESTION) for s in ss]
    rule = Rule()
    for s, r in zip(ss, res):
        a = (r.get("answers", r))["kind"]
        rk = rule.predict(s, QUESTION)["answers"]["kind"]["choice"]
        rows.append({"sentence": s, "kind": a.get("choice"), "rule": rk,
                     "p": round(float((a.get("probabilities") or {}).get(a.get("choice"), 0)), 3),
                     "confidence": a.get("confidence"), "missing": grounded(s, pool)})
    return rows


def annotate(text, rows, mode="mark"):
    """The answer with its guesses marked (or dropped) and its unverified figures flagged."""
    out = text
    for r in rows:
        s = r["sentence"]
        if s not in out:
            continue
        if r["kind"] == "cause":
            out = out.replace(s, "" if mode == "strict" else "(guess) " + s, 1)
        elif r["missing"]:
            out = out.replace(s, "(unverified: " + ", ".join(f"{m:g}" for m in r["missing"]) + ") " + s, 1)
    return out


def tally(rows):
    t = {k: 0 for k in KINDS}
    t["unverified"] = 0
    for r in rows:
        t[r["kind"] or "other"] = t.get(r["kind"] or "other", 0) + 1
        if r["missing"]:
            t["unverified"] += 1
    return t


class FactFence(HookProvider):
    """Collects the invocation's tool results, checks the final answer, marks
    it, notes the tally, and refuses a memory write that is a cause."""

    def __init__(self, predictor=None, mode=None, ledger=None):
        self.predictor = predictor
        self.mode = mode or os.environ.get("HITO_FACTCHECK", "mark")
        self.ledger = ledger
        self.results = []
        self.rows = []
        self.marked = None
        self.refused = []

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeInvocationEvent, self.start)
        registry.add_callback(AfterToolCallEvent, self.tool_done)
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterModelCallEvent, self.model_done)
        registry.add_callback(AfterInvocationEvent, self.done)

    def _pred(self):
        if self.predictor is None:
            if os.environ.get("HITO_FACTCHECK_MODEL", "rule") == "laya":
                try:
                    from .system1 import Laya
                    self.predictor = Laya()
                except Exception:
                    self.predictor = Rule()
            else:
                self.predictor = Rule()
        return self.predictor

    def start(self, e: BeforeInvocationEvent):
        self.results, self.rows, self.marked = [], [], None

    def tool_done(self, e: AfterToolCallEvent):
        res = getattr(e, "result", None) or {}
        for c in res.get("content") or []:
            if isinstance(c, dict) and "text" in c:
                self.results.append(c["text"])

    def before_tool(self, e: BeforeToolCallEvent):
        if self.mode == "off" or e.tool_use.get("name") != "add_memory":
            return
        inp = e.tool_use.get("input") or {}
        entries = inp.get("entries")
        if not isinstance(entries, list):
            entries = [inp.get("content") or ""]
        content = "\n".join(str(x) for x in entries)
        rows = check(content, self.results, self._pred())
        bad = [r for r in rows if r["kind"] == "cause"]
        if bad:
            self.refused.append(content)
            e.cancel_tool = ("refused: memory takes what was measured, and this is an explanation "
                             f"({bad[0]['sentence'][:80]!r}). Save the figure, not the reason.")

    def model_done(self, e: AfterModelCallEvent):
        if self.mode == "off":
            return
        stop = getattr(e, "stop_response", None)
        if not stop or getattr(stop, "stop_reason", None) != "end_turn":
            return
        msg = getattr(stop, "message", None) or {}
        text = "\n".join(c.get("text", "") for c in (msg.get("content") or []) if isinstance(c, dict) and "text" in c)
        self.rows = check(text, self.results, self._pred())
        self.marked = annotate(text, self.rows, self.mode)
        if self.ledger is not None:
            self.ledger.note(what="factcheck", agent=e.agent.name, model=type(self._pred()).__name__,
                             agree_with_rule=sum(1 for r in self.rows if r["kind"] == r["rule"]), sentences=len(self.rows),
                             rows=[{"kind": r["kind"], "rule": r["rule"], "confidence": r["confidence"], "missing": r["missing"],
                                    "sentence": r["sentence"][:120]} for r in self.rows], **tally(self.rows))

    def done(self, e: AfterInvocationEvent):
        pass


def report(rows):
    lines = []
    for r in rows:
        tag = r["kind"] or "?"
        if r["missing"]:
            tag += " · unverified " + ", ".join(f"{m:g}" for m in r["missing"])
        lines.append(f"  [{tag:11}] {r['sentence'][:110]}")
    return "\n".join(lines)
