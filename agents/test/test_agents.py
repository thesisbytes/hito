"""The agents, offline. No key, no network, no model: a scripted stand-in
plays the model's part, so what is tested is the wiring — the tools reach
the numbers, the ledger sees every call, the fence refuses a write outside
agents/out — and the arithmetic in events.py against rows built here.

    agents/.venv/bin/python -m unittest discover -s agents/test -v
"""
import contextlib
import json
import os
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from strands.models.model import Model  # noqa: E402

from hito_agents import analyst, events, memory, model, tools  # noqa: E402
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

if __name__ == "__main__":
    unittest.main()
