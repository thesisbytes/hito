"""Hooks: what the harness does around every call, whatever the agent asks.

Two, both small, both about trust rather than cleverness:

- `Ledger` writes one line per model call and per tool call to
  agents/out/ledger.jsonl. Nothing lives only in the terminal — the same
  rule the game keeps for its own data.
- `Fence` refuses any tool call that would write outside agents/out. The
  agent is a guest in this repo; the builds, the packs and the stroke data
  are not its to touch. A refused call comes back to the model as an error,
  so it can say so instead of pretending.

The gate that will one day let a fast model answer instead of the LLM is a
third hook on BeforeModelCallEvent, which can `cancel` the call. It is not
built; see NOTES.md, 2026-09-23.
"""
import json
import time
from pathlib import Path

from strands.hooks import (AfterModelCallEvent, AfterToolCallEvent, BeforeModelCallEvent,
                           BeforeToolCallEvent, HookProvider, HookRegistry)

OUT = Path(__file__).resolve().parents[1] / "out"


class Ledger(HookProvider):
    def __init__(self, path=None):
        self.path = Path(path) if path else OUT / "ledger.jsonl"
        self.t0 = None
        self.entries = []   # kept in memory too, so a test can read them back

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeModelCallEvent, self.before_model)
        registry.add_callback(AfterModelCallEvent, self.after_model)
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    def note(self, **entry):
        entry = {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), **entry}
        self.entries.append(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def before_model(self, e: BeforeModelCallEvent):
        self.t0 = time.time()
        self.note(what="model", agent=e.agent.name, messages=len(e.agent.messages),
                  projected_tokens=e.projected_input_tokens)

    def after_model(self, e: AfterModelCallEvent):
        stop = getattr(e, "stop_response", None)
        reason = getattr(stop, "stop_reason", None) if stop else None
        err = getattr(e, "exception", None)
        self.note(what="model.done", agent=e.agent.name, stop=reason,
                  ms=int((time.time() - (self.t0 or time.time())) * 1000),
                  error=repr(err) if err else None)

    def before_tool(self, e: BeforeToolCallEvent):
        self.note(what="tool", agent=e.agent.name, name=e.tool_use.get("name"),
                  input=e.tool_use.get("input"))

    def after_tool(self, e: AfterToolCallEvent):
        res = getattr(e, "result", None) or {}
        self.note(what="tool.done", agent=e.agent.name, name=e.tool_use.get("name"),
                  status=res.get("status"))


class Fence(HookProvider):
    """A tool call whose `name` or `path` input would land outside `root`
    is cancelled before it runs."""
    KEYS = ("path", "name")

    def __init__(self, root=OUT):
        self.root = Path(root).resolve()
        self.refused = []

    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.check)

    def check(self, e: BeforeToolCallEvent):
        inp = e.tool_use.get("input") or {}
        for k in self.KEYS:
            v = inp.get(k)
            if not isinstance(v, str) or "/" not in v and ".." not in v:
                continue
            target = (self.root / v).resolve()
            if self.root not in target.parents and target != self.root:
                self.refused.append(v)
                e.cancel_tool = f"refused: {k}={v!r} is outside agents/out, and that is the only place an agent writes"
                return
