"""The agents, offline. No key, no network, no model: a scripted stand-in
plays the model's part, so what is tested is the wiring — the tools reach
the numbers, the ledger sees every call, the fence refuses a write outside
agents/out — and the arithmetic in events.py against rows built here.

    agents/.venv/bin/python -m unittest discover -s agents/test -v
"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strands.models.model import Model  # noqa: E402

from hito_agents import analyst, events, tools  # noqa: E402
from hito_agents.hooks import Fence, Ledger  # noqa: E402


def stroke(pts, t0=0):
    flat = []
    for i, (x, y) in enumerate(pts):
        flat += [x, y, t0 + i * 10]
    return flat


def trace(glyph, ok=True, zaps=0, ms=500, size=0.5, diff="easy", prof="pen", quality=None, s=None, v="0.1.45"):
    body = {"glyph": glyph, "ok": ok, "ms": ms, "zaps": zaps, "size": size, "diff": diff, "prof": prof, "v": v,
            "s": s if s is not None else [stroke([(100, 100), (200, 100), (300, 100)])]}
    if quality is not None:
        body["q"] = quality   # the hand's name for it; the run record says quality
    return {"device": "dtest", "kind": "trace", "at": "2026-09-23T10:00:00.000+00:00", "glyph": glyph,
            "body": json.dumps(body), "$id": f"{glyph}-{ms}"}


def rows():
    line = [stroke([(100, 100), (300, 100)])]
    wobble = [stroke([(100, 120), (200, 80), (300, 130)])]
    return [
        trace("つ", ok=True, quality=0.9, s=line, ms=400),
        trace("つ", ok=True, quality=0.8, s=line, ms=450),
        trace("つ", ok=False, zaps=3, s=wobble, ms=900),
        trace("ふ", ok=False, zaps=2, ms=800, prof="finger", diff="guided"),
        trace("ふ", ok=False, zaps=4, ms=700, prof="finger", diff="guided"),
        trace("ふ", ok=True, ms=600, prof="finger", diff="guided", s=wobble),
        trace("ん", ok=True, ms=300),
        {"device": "dtest", "kind": "banish", "at": "2026-09-23T10:01:00.000+00:00", "glyph": "つ",
         "body": json.dumps({"glyph": "つ", "ms": 1000}), "$id": "b1"},
    ]


class Scripted(Model):
    """A model that says what it was told to, in the order it was told."""

    def __init__(self, turns):
        self.turns = list(turns)
        self.seen = []

    def update_config(self, **config):
        pass

    def get_config(self):
        return {}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kw):
        self.seen.append([m["role"] for m in messages])
        turn = self.turns.pop(0)
        yield {"messageStart": {"role": "assistant"}}
        if "tool" in turn:
            name, inp = turn["tool"]
            yield {"contentBlockStart": {"start": {"toolUse": {"toolUseId": f"t{len(self.seen)}", "name": name}}}}
            yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(inp)}}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "tool_use"}}
        else:
            yield {"contentBlockDelta": {"delta": {"text": turn["text"]}}}
            yield {"contentBlockStop": {}}
            yield {"messageStop": {"stopReason": "end_turn"}}
        yield {"metadata": {"usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2}, "metrics": {"latencyMs": 0}}}

    async def structured_output(self, output_model, prompt, system_prompt=None, **kw):
        raise NotImplementedError
        yield  # pragma: no cover


def parsed(rs):
    out = []
    for r in rs:
        r = dict(r)
        r["body"] = json.loads(r["body"])
        out.append(r)
    return out


class Arithmetic(unittest.TestCase):
    def setUp(self):
        self.rows = parsed(rows())

    def test_overview_counts_what_is_there(self):
        o = events.overview(self.rows)
        self.assertEqual(o["by_kind"], {"trace": 7, "banish": 1})
        self.assertEqual(o["characters_traced"], 3)
        self.assertEqual(o["traces_with_quality"], 2)
        self.assertEqual(o["flags"], 0)

    def test_summary_of_one_character(self):
        s = events.summarise(events.by_glyph(self.rows)["つ"])
        self.assertEqual((s["traces"], s["landed"], s["fizzled"]), (3, 2, 1))
        self.assertEqual(s["quality"], 0.85)
        self.assertEqual(s["by_hand"], {"pen": 3})
        self.assertEqual(s["consistency"], {"attempts": 2, "spread": 0.0})

    def test_spread_grows_when_the_ink_wanders(self):
        same = [{"ok": True, "s": [stroke([(0, 0), (100, 0)])]}] * 2
        apart = [{"ok": True, "s": [stroke([(0, 0), (100, 0)])]}, {"ok": True, "s": [stroke([(0, 20), (100, 20)])]}]
        self.assertEqual(events.consistency(same)["spread"], 0.0)
        self.assertGreater(events.consistency(apart)["spread"], 0.1)
        self.assertIsNone(events.consistency([{"ok": False, "s": [stroke([(0, 0), (1, 1)])]}])["spread"])

    def test_hardest_leaves_thin_data_out(self):
        h = events.hardest(self.rows, n=5, min_traces=3)
        self.assertEqual([t["glyph"] for t in h], ["ふ", "つ"])   # ん has one trace
        self.assertEqual(h[0]["fizzle_rate"], 0.67)

    def test_load_parses_body_text(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "events.jsonl"
            p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows()) + "\n", encoding="utf-8")
            got = events.load(p)
        self.assertEqual(len(got), 8)
        self.assertEqual(got[0]["body"]["glyph"], "つ")


class Wiring(unittest.TestCase):
    def setUp(self):
        tools.use(parsed(rows()))
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_agent(self, turns, question="how is it going?"):
        model = Scripted(turns)
        ledger, fence = Ledger(self.out / "ledger.jsonl"), Fence(self.out)
        agent = analyst.build(model=model, hooks=[ledger, fence], callback_handler=None)
        result = agent(question)
        return str(result), model, ledger, fence

    def test_a_tool_call_reaches_the_numbers_and_the_ledger_sees_it(self):
        text, model, ledger, fence = self.run_agent([
            {"tool": ("glyph_summary", {"glyph": "つ"})},
            {"text": "つ has landed twice and fizzled once."},
        ])
        self.assertIn("fizzled once", text)
        # the tool result went back to the model as a user turn
        self.assertEqual(model.seen[1][-1], "user")
        self.assertEqual(ledger.entries[3]["status"], "success")
        whats = [e["what"] for e in ledger.entries]
        self.assertEqual(whats, ["model", "model.done", "tool", "tool.done", "model", "model.done"])
        self.assertEqual(ledger.entries[2]["input"], {"glyph": "つ"})
        self.assertTrue((self.out / "ledger.jsonl").exists())

    def test_the_fence_refuses_a_write_outside_out(self):
        victim = Path(__file__).resolve().parents[2] / "build" / "engine.html"
        before = victim.read_bytes()
        text, model, ledger, fence = self.run_agent([
            {"tool": ("save_report", {"name": "../../build/engine.html", "text": "oops"})},
            {"text": "I was refused."},
        ])
        self.assertEqual(victim.read_bytes(), before)
        self.assertEqual(fence.refused, ["../../build/engine.html"])
        self.assertEqual(ledger.entries[3]["status"], "error")

    def test_a_write_inside_out_is_allowed(self):
        with unittest.mock.patch.object(tools, "OUT", self.out):
            text, model, ledger, fence = self.run_agent([
                {"tool": ("save_report", {"name": "note.md", "text": "つ is fine"})},
                {"text": "saved"},
            ])
        self.assertEqual((self.out / "note.md").read_text(encoding="utf-8"), "つ is fine")
        self.assertEqual(fence.refused, [])

    def test_no_key_means_no_agent_and_a_plain_message(self):
        env = {k: v for k, v in os.environ.items() if k not in ("OPENROUTER_API_KEY", "HITO_LLM_API_KEY")}
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(SystemExit) as cm:
                analyst.build()
        self.assertIn("OPENROUTER_API_KEY", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
