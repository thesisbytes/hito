"""The analyst: the first agent, and the one the others will be measured by.

It reads a pull of the events table through its tools and answers questions
about how the tracing is going. It scores nothing and changes nothing in the
game; it is a reader of observations.

    agents/.venv/bin/python -m hito_agents.analyst "which characters fizzle most, and why might that be?"
"""
import os
import sys

from strands import Agent

from .factcheck import FactFence, report, tally
from .hooks import Fence, Ledger
from .tools import ALL

SYSTEM = """You are the analyst for hito 人, a stylus-first script tracer with a game around it.
Players trace characters (hiragana and katakana, from KanjiVG stroke data) on a tablet or phone;
every attempt is recorded as a trace: landed or fizzled, zaps (times the pen strayed), time,
size, difficulty (guided, easy, medium), pen or finger, and from v0.1.45 a quality score `q`
(how recognisable the ink is against the shape asked for, 0-1; older traces have none).

You have a pull of that table and tools that compute over it. Rules:
- Use the tools. Never invent a number; quote the ones you were given.
- Say plainly when the data is too thin to say anything (a handful of traces is not a trend).
- A trace is an observation about one hand. It is never a claim about anyone else, and nothing
  you write is a ranking of players.
- Be brief, concrete, and a little affectionate about the whole thing. The project's tone is silly.
- If asked to save a report, use save_report with a plain file name.
- You have a long-term memory. What earlier sessions learned arrives in a <memory> block; trust it as
  background, not as data. Use add_memory for a figure worth keeping, in one plain sentence; a memory
  that explains WHY is refused, because nothing here can measure a reason.
- Say what was measured. If you offer a reason, mark it as a guess yourself."""


FENCE = {}


def build(model=None, hooks=None, memory=None, **kw):
    """memory: a MemoryManager, None for the default mem0 one, False for none
    (HITO_MEMORY=0 does the same from the environment)."""
    if model is None:
        from .model import pick
        model = pick()
    if memory is None and os.environ.get("HITO_MEMORY", "1") != "0":
        from .memory import manager
        memory = manager()
    if hooks is None:
        ledger = Ledger()
        hooks = [ledger, Fence()]
        if os.environ.get("HITO_FACTCHECK", "mark") != "off":
            FENCE["last"] = FactFence(ledger=ledger)
            hooks.append(FENCE["last"])
    return Agent(model=model, tools=ALL, system_prompt=SYSTEM, name="analyst",
                 hooks=hooks, memory_manager=memory or None, **kw)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    question = " ".join(argv) or "Give me the overview, then the five hardest characters and one sentence on each."
    agent = build()
    agent(question)
    print()
    fence = FENCE.get("last")
    if fence and fence.rows:
        print("── fact fence ──", tally(fence.rows))
        print(report(fence.rows))
        if fence.refused:
            print("  refused memory:", fence.refused)


if __name__ == "__main__":
    main()
