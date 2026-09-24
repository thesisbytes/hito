"""The agents, offline. No key, no network, no model: a scripted stand-in
plays the model's part, so what is tested is the wiring — the tools reach
the numbers, the ledger sees every call, the fence refuses a write outside
agents/out — and the arithmetic in events.py against rows built here.

    agents/.venv/bin/python -m unittest discover -s agents/test -v
"""
import contextlib
import json
import os
import re
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strands.models.model import Model  # noqa: E402

from hito_agents import analyst, events, factcheck, memory, model, system1, tools  # noqa: E402
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
        self.seen = []    # roles per call
        self.msgs = []    # the full messages per call

    def update_config(self, **config):
        pass

    def get_config(self):
        return {}

    async def stream(self, messages, tool_specs=None, system_prompt=None, **kw):
        self.seen.append([m["role"] for m in messages])
        self.msgs.append(messages)
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


KEYS = ("OPENROUTER_API_KEY", "HITO_LLM_API_KEY", "AWS_BEARER_TOKEN_BEDROCK", "HITO_LLM", "HITO_MODEL",
        "HITO_MEMORY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_PROFILE", "AWS_REGION")


def clean_env(**extra):
    """A clean environment, and no real .env files: the tests must not pick
    up whichever key the maintainer has on this machine."""
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env.update(extra)
    stack = contextlib.ExitStack()
    stack.enter_context(unittest.mock.patch.dict(os.environ, env, clear=True))
    stack.enter_context(unittest.mock.patch.object(model, "ENV_FILES", ()))
    return stack


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
        agent = analyst.build(model=model, hooks=[ledger, fence], callback_handler=None, memory=False)
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

    def env(self, **extra):
        return clean_env(**extra)

    def test_no_key_means_no_agent_and_a_plain_message(self):
        with self.env(), unittest.mock.patch.object(model, "aws_credentials", return_value=False):
            with self.assertRaises(SystemExit) as cm:
                analyst.build(memory=False)
        self.assertIn("AWS_BEARER_TOKEN_BEDROCK", str(cm.exception))
        self.assertIn("OPENROUTER_API_KEY", str(cm.exception))

    def test_an_env_file_is_read_but_never_overrides(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / ".env"
            f.write_text("# keys\nAWS_BEARER_TOKEN_BEDROCK='from-file'\nexport AWS_REGION=eu-west-1\nHITO_MAX_TOKENS=5\n", encoding="utf-8")
            with self.env(AWS_REGION="us-west-2"):
                loaded = model.load_env([f, Path(d) / "missing.env"])
                self.assertEqual(loaded, ["AWS_BEARER_TOKEN_BEDROCK", "HITO_MAX_TOKENS"])
                self.assertEqual(os.environ["AWS_BEARER_TOKEN_BEDROCK"], "from-file")
                self.assertEqual(os.environ["AWS_REGION"], "us-west-2")
                self.assertEqual(model.max_tokens(), 5)

    def test_a_bedrock_key_picks_bedrock(self):
        from strands.models.bedrock import BedrockModel
        with self.env(AWS_BEARER_TOKEN_BEDROCK="not-a-real-key", AWS_REGION="us-west-2"):
            m = model.pick()
        self.assertIsInstance(m, BedrockModel)
        self.assertEqual(m.get_config()["max_tokens"], 2000)

    def test_only_an_openrouter_key_picks_openrouter(self):
        from strands.models.openai import OpenAIModel
        with self.env(OPENROUTER_API_KEY="not-a-real-key"), \
                unittest.mock.patch.object(model, "aws_credentials", return_value=False):
            m = model.pick()
        self.assertIsInstance(m, OpenAIModel)
        self.assertEqual(m.get_config()["model_id"], model.OPENROUTER_MODEL)

    def test_hito_llm_forces_a_provider(self):
        from strands.models.openai import OpenAIModel
        with self.env(AWS_BEARER_TOKEN_BEDROCK="x", OPENROUTER_API_KEY="y", HITO_LLM="openrouter"):
            self.assertIsInstance(model.pick(), OpenAIModel)
        with self.env(HITO_LLM="bedrock", AWS_BEARER_TOKEN_BEDROCK="x", OPENROUTER_API_KEY="y", HITO_MODEL="us.anthropic.something"):
            self.assertEqual(model.pick().get_config()["model_id"], "us.anthropic.something")


class FakeMem0:
    """mem0's add / search / get_all, in memory, by substring."""

    def __init__(self):
        self.rows = []
        self.adds = []

    def add(self, messages, *, user_id=None, metadata=None, infer=True, **kw):
        self.adds.append({"messages": messages, "user_id": user_id, "infer": infer})
        texts = [messages] if isinstance(messages, str) else [m["content"] for m in messages]
        for t in texts:
            self.rows.append({"id": f"m{len(self.rows)}", "memory": t, "user_id": user_id})
        return {"results": [{"event": "ADD"}]}

    def search(self, query, *, filters=None, top_k=5, **kw):
        assert "user_id" not in kw, "mem0 2.x rejects a top-level user_id on search"
        user_id = (filters or {}).get("user_id")
        words = [w for w in query.lower().split() if len(w) > 3]
        hits = [r for r in self.rows if r["user_id"] == user_id and any(w in r["memory"].lower() for w in words)]
        return {"results": [{**r, "score": 0.9} for r in hits[:top_k]]}

    def get_all(self, *, filters=None, top_k=100, **kw):
        assert "user_id" not in kw, "mem0 2.x rejects a top-level user_id on get_all"
        user_id = (filters or {}).get("user_id")
        return {"results": [r for r in self.rows if r["user_id"] == user_id][:top_k]}


class Memory(unittest.TestCase):
    def setUp(self):
        tools.use(parsed(rows()))
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_config_follows_the_provider(self):
        with clean_env(AWS_BEARER_TOKEN_BEDROCK="x", AWS_REGION="eu-west-1"):
            c = memory.mem0_config()
        self.assertEqual((c["llm"]["provider"], c["embedder"]["provider"]), ("aws_bedrock", "aws_bedrock"))
        self.assertEqual(c["llm"]["config"]["aws_region"], "eu-west-1")
        self.assertEqual(c["vector_store"]["config"]["embedding_model_dims"], 1024)
        with clean_env(OPENROUTER_API_KEY="y", GEMINI_API_KEY="z"), \
                unittest.mock.patch.object(model, "aws_credentials", return_value=False):
            c2 = memory.mem0_config()
        self.assertEqual((c2["llm"]["provider"], c2["embedder"]["provider"]), ("openai", "gemini"))
        self.assertEqual(c2["llm"]["config"]["openrouter_base_url"], model.OPENROUTER_URL)
        # vectors from different embedders never share a collection
        self.assertNotEqual(c["vector_store"]["config"]["collection_name"], c2["vector_store"]["config"]["collection_name"])
        with clean_env(OPENROUTER_API_KEY="y"), \
                unittest.mock.patch.object(model, "aws_credentials", return_value=False):
            with self.assertRaises(SystemExit) as cm:
                memory.mem0_config()
        self.assertIn("GEMINI_API_KEY", str(cm.exception))

    def test_the_store_speaks_both_dialects(self):
        fake = FakeMem0()
        store = memory.Mem0Store(client=fake, scope="maintainer")
        asyncio.run(store.add("The poke bug in easy mode is known and unfixed."))
        self.assertEqual(fake.adds[-1]["infer"], False)     # written as written
        asyncio.run(store.add_messages([
            {"role": "user", "content": [{"text": "how is ふ going?"}]},
            {"role": "assistant", "content": [{"toolUse": {"name": "x"}}]},   # no text: dropped
            {"role": "assistant", "content": [{"text": "ふ fizzles a third of the time."}]},
        ]))
        self.assertEqual(fake.adds[-1]["infer"], True)      # mem0 distils a conversation
        self.assertEqual([m["role"] for m in fake.adds[-1]["messages"]], ["user", "assistant"])
        hits = asyncio.run(store.search("is the poke bug known?"))
        self.assertEqual([h.content for h in hits], ["The poke bug in easy mode is known and unfixed."])
        self.assertEqual(hits[0].metadata["id"], "m0")
        self.assertEqual(len(store.everything()), 3)
        # a different scope sees nothing of this
        self.assertEqual(asyncio.run(memory.Mem0Store(client=fake, scope="d123").search("poke bug")), [])

    def test_memory_reaches_the_model_and_the_turn_reaches_memory(self):
        fake = FakeMem0()
        store = memory.Mem0Store(client=fake, scope="maintainer")
        asyncio.run(store.add("The maintainer plays guided, by finger, on a phone."))
        scripted = Scripted([{"text": "Finger, guided, phone: noted."}])
        mm = memory.manager(store)
        agent = analyst.build(model=scripted, hooks=[Ledger(self.out / "l.jsonl"), Fence(self.out)],
                              callback_handler=None, memory=mm)
        self.assertIn("search_memory", agent.tool_names)
        self.assertIn("add_memory", agent.tool_names)
        agent("how does the maintainer play, and does the finger struggle?")
        shown = json.dumps(scripted.msgs[0], ensure_ascii=False)
        self.assertIn("<memory>", shown)
        self.assertIn("plays guided, by finger", shown)
        # the durable history is untouched by the injection
        self.assertNotIn("<memory>", json.dumps(agent.messages, ensure_ascii=False))
        # extraction ran after the invocation: the turn went to mem0 to distil
        asyncio.run(mm.flush())
        distilled = [a for a in fake.adds if a["infer"]]
        self.assertEqual(len(distilled), 1)
        self.assertIn("how does the maintainer play", distilled[0]["messages"][0]["content"])


import asyncio  # noqa: E402

def line_book():
    """One character, 一: a single stroke from (200,500) to (800,500)."""
    return {"一": [[(200.0, 500.0), (800.0, 500.0)]]}


def ink(*strokes):
    return [stroke(s) for s in strokes]


class SystemOne(unittest.TestCase):
    def setUp(self):
        self.book = line_book()

    def feat(self, s, **kw):
        body = {"glyph": "一", "ok": True, "ms": 500, "zaps": 0, "size": 0.5, "diff": "easy", "prof": "pen", "s": s}
        body.update(kw)
        return system1.features(body, self.book)

    def test_geometry_tells_the_stories_apart(self):
        whole = self.feat(ink([(200, 500), (400, 500), (600, 500), (800, 500)]))
        short = self.feat(ink([(200, 500), (350, 500), (500, 500)]))
        poke = self.feat(ink([(500, 500), (505, 502)]), ms=80)
        scribble = self.feat(ink([(200, 500), (800, 480), (200, 520), (800, 500), (200, 500), (800, 500)]))
        self.assertEqual((whole["coverage"], whole["end_gap"]), (1.0, 0.0))
        self.assertAlmostEqual(whole["travel_ratio"], 1.0)
        self.assertGreater(short["end_gap"], 0.4)              # stopped halfway along a 600-wide stroke
        self.assertLess(short["coverage"], 0.7)
        self.assertLess(poke["coverage"], 0.3)
        self.assertLess(poke["ink_span"], 0.05)
        self.assertGreater(scribble["travel_ratio"], 4)
        self.assertEqual(whole["strokes_expected"], 1)
        # a short last stroke: a small gap against the character is a large one against the stroke
        tick_book = {"ふ": [[(200.0, 200.0), (800.0, 800.0)], [(700.0, 300.0), (740.0, 340.0)]]}
        f = system1.features({"glyph": "ふ", "ok": False, "s": ink([(200, 200), (800, 800)], [(700, 300), (705, 305)])}, tick_book)
        self.assertLess(f["end_gap"], 0.06)
        self.assertGreater(f["end_gap_stroke"], 0.8)
        # a hook run long: ink past the end, as a fraction of the stroke
        long = self.feat(ink([(200, 500), (800, 500), (1100, 500)]))
        self.assertAlmostEqual(long["overshoot"], 0.5, places=1)
        self.assertEqual(whole["overshoot"], 0.0)
        # two strokes drawn as one: joined counts the missing lift
        two = {"二": [[(200.0, 300.0), (800.0, 300.0)], [(200.0, 700.0), (800.0, 700.0)]]}
        j = system1.features({"glyph": "二", "ok": True, "s": ink([(200, 300), (800, 300), (200, 700), (800, 700)])}, two)
        self.assertEqual((j["joined"], j["strokes_drawn"]), (1, 1))

    def test_old_partial_captures_are_left_out(self):
        self.assertTrue(system1.partial({"diff": "guided", "v": "0.1.41"}))
        self.assertFalse(system1.partial({"diff": "guided", "v": "0.1.43"}))
        self.assertFalse(system1.partial({"diff": "easy", "v": "0.1.41"}))
        rows = [{"$id": "old", "kind": "trace", "body": {"glyph": "一", "ok": True, "diff": "guided", "v": "0.1.41", "s": ink([(200, 500), (800, 500)])}},
                {"$id": "new", "kind": "trace", "body": {"glyph": "一", "ok": True, "diff": "guided", "v": "0.1.45", "s": ink([(200, 500), (800, 500)])}}]
        fake = lambda s, q: {"answers": {"verdict": {"choice": "honest", "probabilities": {}, "confidence": 0.5}, "accept": {"noul": 0.5, "confidence": 0.5}}}
        self.assertEqual([l["id"] for l in system1.label(rows, predictor=fake, book=self.book)], ["new"])

    def test_unknown_character_or_no_ink_keeps_the_plain_fields(self):
        f = system1.features({"glyph": "龍", "ok": False, "zaps": 2, "ms": 300, "s": [stroke([(1, 1), (2, 2)])]}, self.book)
        self.assertEqual((f["glyph"], f["landed"], f["zaps"], f["strokes_expected"]), ("龍", False, 2, None))
        self.assertNotIn("coverage", f)
        g = system1.features({"glyph": "一", "ok": True}, self.book)
        self.assertEqual(g["strokes_drawn"], 0)
        self.assertNotIn("end_gap", g)

    def test_labels_read_layas_answer_and_the_flags_compare(self):
        def fake(state, questions):
            self.assertIsInstance(state, str)            # prose by default
            self.assertIn("near", state)
            self.assertEqual(set(questions), {"verdict", "accept"})
            gap = int(re.search(r"stopped (\d+)% from where the stroke ends", state).group(1))
            v = "stopped_short" if gap > 30 else "honest"
            return {"answers": {
                "verdict": {"type": "choice", "choice": v, "probabilities": {v: 0.8, "scribble": 0.2}, "confidence": 0.61},
                "accept": {"type": "noul", "noul": 0.9, "confidence": 0.7}}}
        rows = [
            {"$id": "a", "device": "d1", "kind": "trace", "at": "t", "body": {"glyph": "一", "ok": True, "size": 0.5,
             "s": ink([(200, 500), (500, 500), (800, 500)])}},
            {"$id": "b", "device": "d1", "kind": "trace", "at": "t", "body": {"glyph": "一", "ok": False, "size": 0.5,
             "s": ink([(200, 500), (400, 500)])}},
        ]
        labels = system1.label(rows, predictor=fake, book=self.book)
        self.assertEqual([l["verdict"] for l in labels], ["honest", "stopped_short"])
        self.assertEqual(labels[1]["p"]["stopped_short"], 0.8)
        self.assertEqual(labels[0]["accept"], 0.9)
        s = system1.summary(labels)
        self.assertEqual(s["totals"], {"honest": 1, "stopped_short": 1})
        self.assertEqual(s["characters"]["一"]["traces"], 2)
        # no flags: no verdict, only the note
        self.assertEqual(system1.agree(labels, rows)["flags"], 0)
        # a flag at this size on this device: both traces near it read as fair, so Laya agrees with the hand
        flagged = rows + [{"kind": "flag", "device": "d1", "glyph": "一", "body": {"glyph": "一", "size": 0.52}}]
        a = system1.agree(labels, flagged)
        self.assertEqual((a["flags"], a["agreed"]), (1, 1))
        self.assertEqual(a["per_flag"][0]["traces_near"], 2)

    def test_prose_says_what_the_numbers_say(self):
        f = self.feat(ink([(200, 500), (350, 500), (500, 500)]), ok=False, zaps=2)
        text = system1.narrate(f)
        self.assertIn("rejected it after 2 zaps", text)
        self.assertIn("has 1 strokes; the learner drew 1", text)
        self.assertIn(f"stopped {int(f['end_gap'] * 100)}% from where the stroke ends", text)
        self.assertIn("legend", system1.state_of(f, "json"))

    def test_the_real_book_loads_every_kana(self):
        book = system1.load_book()
        self.assertGreaterEqual(len(book), 164)
        self.assertEqual(len(book["ふ"]), 4)
        self.assertTrue(all(0 < p[0] < 1000 for s in book["あ"] for p in s))

    def test_triage_says_so_when_there_are_no_labels(self):
        with unittest.mock.patch.object(system1, "load_labels", return_value=None):
            self.assertIn("note", tools.triage())
        fake_labels = [{"id": "x", "glyph": "ふ", "device": "d", "size": 0.4, "verdict": "poked", "p": {}, "confidence": 0.5,
                        "accept": 0.3, "accept_confidence": 0.5}]
        tools.use(parsed(rows()))
        with unittest.mock.patch.object(system1, "load_labels", return_value=fake_labels):
            t = tools.triage(glyph="ふ")
            self.assertEqual(t["verdicts"], {"poked": 1})
            self.assertEqual(tools.triage()["totals"], {"poked": 1})


class FactCheck(unittest.TestCase):
    RESULTS = ['{"ふ": {"traces": 41, "fizzle_rate": 0.46, "zaps_per_trace": 3.1}, "き": {"spread": 0.063}}']

    def test_sentences_and_figures(self):
        ss = factcheck.sentences("ふ fizzled 19 of 41 times. **Behind it:** き.\n- a bullet about も that is long enough\nok")
        self.assertEqual(len(ss), 3)
        self.assertEqual(factcheck.figures("46 % fizzle, 3.1 zaps"), {46.0, 0.46, 3.1})

    def test_grounding_allows_the_tools_forms_and_catches_invention(self):
        pool = factcheck.pool_from(self.RESULTS)
        self.assertEqual(factcheck.grounded("ふ fizzles 46% of the time, 3.1 zaps a trace, over 41 traces", pool), [])
        self.assertEqual(factcheck.grounded("き's spread is 0.06", pool), [])          # rounding
        self.assertEqual(factcheck.grounded("it fizzled 55 times in two rounds", pool), [55.0])   # 55 invented; two is ordinal

    def test_the_rule_sorts_the_kinds(self):
        rows = factcheck.check("ふ fizzled 46% of the time. That is because the finger is wide. "
                               "The data cannot say why. You should pull again. も is the next worst after ふ.", self.RESULTS)
        self.assertEqual([r["kind"] for r in rows], ["measurement", "cause", "caveat", "suggestion", "comparison"])
        marked = factcheck.annotate("ふ fizzled 46% of the time. That is because the finger is wide.", rows[:2])
        self.assertIn("(guess) That is because", marked)
        self.assertNotIn("because", factcheck.annotate("That is because the finger is wide.", rows[1:2], "strict"))
        self.assertEqual(factcheck.tally(rows)["cause"], 1)

    def test_the_fence_marks_the_answer_and_refuses_a_cause_in_memory(self):
        tools.use(parsed(rows()))
        fake = FakeMem0(); store = memory.Mem0Store(client=fake, scope="t")
        scripted = Scripted([
            {"tool": ("glyph_summary", {"glyph": "つ"})},
            {"tool": ("add_memory", {"entries": ["つ fizzles because the pen slips on the curve."]})},
            {"tool": ("add_memory", {"entries": ["つ fizzled 1 of 3 traces."]})},
            {"text": "つ fizzled 1 of 3 traces. That is because the pen slips. It fizzled 55 times."},
        ])
        out = Path(self.__class__.__name__ + "_tmp"); out.mkdir(exist_ok=True)
        try:
            ledger = Ledger(out / "l.jsonl"); fence = factcheck.FactFence(predictor=factcheck.Rule(), ledger=ledger)
            agent = analyst.build(model=scripted, hooks=[ledger, Fence(out), fence], callback_handler=None, memory=memory.manager(store))
            agent("how is つ?")
            self.assertEqual(fence.refused, ["つ fizzles because the pen slips on the curve."])
            # the tool's own writes (the manager's after-turn extraction writes too, with infer on)
            self.assertEqual([a["messages"] for a in fake.adds if not a["infer"]], ["つ fizzled 1 of 3 traces."])
            self.assertEqual([r["kind"] for r in fence.rows], ["measurement", "cause", "measurement"])
            self.assertEqual(fence.rows[2]["missing"], [55.0])
            self.assertIn("(guess) That is because", fence.marked)
            self.assertIn("(unverified: 55)", fence.marked)
            notes = [e for e in ledger.entries if e["what"] == "factcheck"]
            self.assertEqual((notes[-1]["cause"], notes[-1]["unverified"]), (1, 1))
        finally:
            import shutil; shutil.rmtree(out, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


# ---- the balance: two advocates and a judge that is arithmetic
from hito_agents import balance, pace


def run_row(wave, traced=20, ms=80000, diff="medium", frames=None, upgrades=None):
    body = {"realm": "hiragana", "difficulty": diff, "wave": wave, "traced": traced, "clean": int(traced * 0.7),
            "ms": ms, "banished": wave - 5, "cast": 10, "v": "0.1.64", "upgrades": upgrades or {}}
    if frames:
        body["frames"] = frames
    return {"device": "dtest", "kind": "run", "at": "2026-09-24T10:00:00.000+00:00", "body": body, "$id": f"r{wave}"}


HAND = {"s_per_trace": 3.8, "strokes_per_trace": 2.5}
OLD = {"spawnMin": 1800, "spawnRamp": 140, "hpEvery": 10, "biteEvery": 20}
# v0.1.63's hand-tuned ramp, fixed here so the tests do not move when the
# pack does (the balance agents edit the pack; the judge's tests must not
# read their own verdict back)
BASE = {"spawnMs": 5200, "spawnMin": 3400, "spawnRamp": 45, "hpEvery": 30, "biteEvery": 30}


def base_cfg():
    cfg, refused = pace.with_changes(pace.current(), BASE)
    assert not refused
    return cfg


class Pace(unittest.TestCase):
    def test_the_defaults_are_read_from_the_shell_itself(self):
        d = pace.shell_defaults()
        self.assertEqual(d["spawnMs"], 5200)
        self.assertEqual(d["wardHp"], 5)
        self.assertEqual(d["tower"]["rows"], 2)
        self.assertIn("bossHp", d["tower"])

    def test_changes_are_bounded_and_named(self):
        cfg = pace.current()
        out, refused = pace.with_changes(cfg, {"spawnMin": 3000, "spawnMin2": 1, "hpEvery": 1000, "tower.bossHp": 1, "tower.rows": 9})
        self.assertEqual(out["spawnMin"], 3000)
        self.assertEqual(out["tower"]["bossHp"], 1)
        self.assertEqual(set(refused), {"spawnMin2", "hpEvery", "tower.rows"})
        self.assertEqual(cfg["tower"]["bossHp"], 2, "with_changes wrote into the config it was given")

    def test_the_old_ramp_ends_where_the_runs_did_and_the_new_one_later(self):
        cur = base_cfg()
        old, _ = pace.with_changes(cur, OLD)
        e_old, e_new = pace.end_of(old, HAND), pace.end_of(cur, HAND)
        self.assertTrue(18 <= e_old <= 40, f"the old ramp is predicted to end at {e_old}; the runs ended 27-43")
        self.assertGreater(e_new, e_old)
        self.assertLess(pace.wall_of(old, HAND), pace.wall_of(cur, HAND))
        slower, _ = pace.with_changes(cur, {"spawnMin": 5000})
        self.assertGreaterEqual(pace.end_of(slower, HAND), e_new)

    def test_the_model_is_scaled_by_what_was_measured(self):
        cur = base_cfg()
        bare = pace.end_of(cur, HAND)
        far = {**HAND, "wave_p50": bare * 3}
        self.assertAlmostEqual(pace.calibration(cur, far), 3.0)
        self.assertEqual(pace.predicted(cur, far, 3.0), bare * 3)
        self.assertEqual(pace.calibration(cur, HAND), 1.0, "nothing measured, nothing scaled")
        # a version's own runs are what count once there are enough of them
        rs = [dict(run_row(20)["body"], v="0.1.1")] * 6 + [dict(run_row(200)["body"], v="0.1.2")] * 6
        self.assertEqual(pace.hand_of(rs, "0.1.2")["wave_p50"], 200)
        self.assertEqual(pace.hand_of(rs, "0.1.9")["version"], None)

    def test_a_faster_hand_goes_further(self):
        cur = base_cfg()
        self.assertGreater(pace.end_of(cur, {"s_per_trace": 2.0, "strokes_per_trace": 2.5}), pace.end_of(cur, HAND))


class Balance(unittest.TestCase):
    def setUp(self):
        balance.use(parsed_runs())
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_state_of_play_measures_the_hand_and_the_phone(self):
        s = balance.state_of_play()
        self.assertEqual(s["runs"], 4)
        self.assertEqual(s["hand"]["runs"], 3, "a practice run was counted")
        self.assertAlmostEqual(s["hand"]["s_per_trace"], 4.0)
        self.assertEqual(s["hand"]["wave_max"], 43)
        self.assertEqual(s["upgrades_bought"], {"quick": 1})
        self.assertEqual(s["frames"]["runs"], 1)
        self.assertAlmostEqual(s["frames"]["jank"], 0.05)

    def test_the_judge_keeps_what_no_side_can_hold_in_band(self):
        cur = base_cfg()
        props = {"hotoke": {"changes": {"spawnMin": 6000}}, "oni": {"changes": {"spawnMin": 1200}}}
        # a hand so slow that nothing holds, and one so quick that nothing bites: the judge changes nothing
        for hand in ({"s_per_trace": 30.0}, {"s_per_trace": 0.3}):
            v = balance.judge(cur, hand, props)
            self.assertEqual(v["changes"], {}, v)
            self.assertIn("kept", v["why"]["spawnMin"])

    def test_a_hand_that_went_to_230_is_judged_at_230(self):
        cur = base_cfg()
        hand = {**HAND, "wave_p50": 230}
        props = {"hotoke": {"changes": {"hpEvery": 60}}, "oni": {"changes": {"hpEvery": 6}}}
        v = balance.judge(cur, hand, props)
        self.assertEqual(v["end_before"], 230)
        self.assertGreater(v["calibration"], 2)
        self.assertEqual(v["changes"].get("hpEvery"), 6, v)
        self.assertTrue(balance.BAND[0] <= v["end_after"] <= balance.BAND[1], v)

    def test_the_judge_takes_the_value_that_lands_in_band(self):
        cur = base_cfg()
        e0 = pace.end_of(cur, HAND)
        v = balance.judge(cur, HAND, {"hotoke": {"changes": {"spawnMin": 6000}}, "oni": {"changes": {"spawnMin": 1200}}})
        self.assertEqual(v["changes"], {"spawnMin": 6000}, v)
        self.assertTrue(balance.BAND[0] <= v["end_after"] <= balance.BAND[1], v)
        self.assertEqual(v["end_before"], e0)
        self.assertIn("hotoke", v["why"]["spawnMin"])

    def test_two_advocates_argue_and_the_verdict_is_a_file(self):
        model = Scripted([
            {"tool": ("state_of_play", {})},
            {"tool": ("pace_model", {"changes": {"spawnMin": 3800}})},
            {"tool": ("propose", {"changes": {"spawnMin": 3800, "nonsense": 1}, "because": "runs end at 27, the hand takes 4.0 s a trace"})},
            {"text": "仏: slower spawns, so the later rows are seen."},
            {"tool": ("state_of_play", {})},
            {"tool": ("propose", {"changes": {"hpEvery": 25}, "because": "nobody has bought a heart; the tower should bite"})},
            {"text": "鬼: sooner health, so the lanterns matter."},
        ])
        ledger, fence = Ledger(self.out / "ledger.jsonl"), Fence(self.out)
        rec = balance.argue(model=model, out_dir=self.out, hooks=[ledger, fence], quiet=True)
        self.assertEqual(rec["hotoke"]["changes"], {"spawnMin": 3800})
        self.assertEqual(list(rec["hotoke"]["refused"]), ["nonsense"])
        self.assertEqual(rec["oni"]["changes"], {"hpEvery": 25})
        self.assertIn("仏", rec["hotoke"]["said"])
        v = rec["verdict"]
        self.assertTrue(set(v["changes"]) <= {"spawnMin", "hpEvery"})
        self.assertTrue(v["end_after"] is None or balance.BAND[0] <= v["end_after"] <= balance.BAND[1] or v["changes"] == {})
        p = Path(rec["file"])
        self.assertTrue(p.exists() and p.parent == self.out)
        self.assertEqual(json.loads(p.read_text())["verdict"]["changes"], v["changes"])
        whats = [e["what"] for e in ledger.entries if e["what"] == "tool"]
        self.assertEqual(len(whats), 5)

    def test_apply_is_a_human_command_that_edits_the_pack(self):
        game = self.out / "game.json"
        game.write_text(json.dumps({"version": "0.0.0", "field": {"spawnMin": 3400, "tower": {"rows": 2}}}), encoding="utf-8")
        verdict = self.out / "v.json"
        verdict.write_text(json.dumps({"verdict": {"changes": {"spawnMin": 3800, "tower.bossHp": 1}}}), encoding="utf-8")
        balance.apply(verdict, game=game)
        pack = json.loads(game.read_text())
        self.assertEqual(pack["field"]["spawnMin"], 3800)
        self.assertEqual(pack["field"]["tower"], {"rows": 2, "bossHp": 1})
        self.assertEqual(pack["version"], "0.0.0")


class Loop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.game = self.out / "game.json"
        self.pack = self.out / "pack.json"
        self.game.write_text(json.dumps({"version": "0.1.65", "field": {"spawnMin": 3400}}), encoding="utf-8")
        self.pack.write_text(json.dumps({"version": "0.1.65"}), encoding="utf-8")
        self.calls = 0

    def tearDown(self):
        self.tmp.cleanup()

    def fake_argue(self, changes):
        def argue_fn(out_dir=None, version=None):
            self.calls += 1
            self.version = version
            return {"verdict": {"changes": changes, "end_before": 45, "end_after": 78}, "file": None}
        return argue_fn

    def played(self, n, v="0.1.65"):
        return [dict(run_row(30 + i, traced=20), body=dict(run_row(30 + i)["body"], v=v)) for i in range(n)]

    def go(self, rows_, changes=None):
        return balance.auto(rows_, threshold=3, balance_dir=self.out / "balance", argue_fn=self.fake_argue(changes or {}),
                            game=self.game, packs=[self.game, self.pack])

    def test_too_few_runs_on_this_build_and_nobody_is_called(self):
        r = self.go(self.played(2) + self.played(10, v="0.1.60"))
        self.assertEqual(r["status"], "thin")
        self.assertEqual(r["runs"], 2)
        self.assertEqual(self.calls, 0)

    def test_enough_runs_judge_apply_bump_and_never_twice(self):
        r = self.go(self.played(3), {"spawnMin": 3800})
        self.assertEqual(r["status"], "changed", r)
        self.assertEqual(self.version, "0.1.65", "the advocates were not told which build they judge")
        self.assertEqual((r["version"], r["new"]), ("0.1.65", "0.1.66"))
        self.assertEqual(json.loads(self.game.read_text())["field"]["spawnMin"], 3800)
        self.assertEqual(json.loads(self.game.read_text())["version"], "0.1.66")
        self.assertEqual(json.loads(self.pack.read_text())["version"], "0.1.66")
        rec = json.loads((self.out / "balance" / "v0.1.65.json").read_text())
        self.assertEqual(rec["applied_as"], "0.1.66")
        r2 = balance.auto(self.played(30), version="0.1.65", threshold=3, balance_dir=self.out / "balance",
                          argue_fn=self.fake_argue({"spawnMin": 9}), game=self.game, packs=[self.game, self.pack])
        self.assertEqual(r2["status"], "done")
        self.assertEqual(self.calls, 1)

    def test_a_verdict_with_nothing_to_change_is_still_a_verdict(self):
        r = self.go(self.played(3), {})
        self.assertEqual(r["status"], "unchanged")
        self.assertTrue((self.out / "balance" / "v0.1.65.json").exists())
        self.assertEqual(json.loads(self.game.read_text())["version"], "0.1.65")


def parsed_runs():
    return [
        run_row(27, traced=20, ms=80000),
        run_row(43, traced=25, ms=100000, frames={"n": 1000, "slow": 200, "jank": 50}, upgrades={"quick": 2, "mend": 0}),
        run_row(30, traced=20, ms=80000),
        run_row(19, traced=22, ms=65000, diff="guided"),
    ] + [dict(r, body=r["body"]) for r in []]
