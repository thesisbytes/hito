"""What the analyst can do: read the pull, and write under agents/out.

Every tool returns plain data. The numbers come from `events.py`; a tool
only decides which of them to hand over. `save_report` is the one write,
and the Fence hook watches it.
"""
from pathlib import Path

from strands import tool

from . import events
from .hooks import OUT

_rows = None


def rows():
    global _rows
    if _rows is None:
        _rows = events.load()
    return _rows


def use(rows_):
    """Point the tools at rows already in memory (tests, or a filtered pull)."""
    global _rows
    _rows = rows_


@tool
def trace_overview() -> dict:
    """What the pulled events table holds: row counts by kind, how many devices,
    the date range, which build versions, how many characters were traced, and
    how many traces carry a quality score. Start here."""
    return events.overview(rows())


@tool
def glyph_summary(glyph: str) -> dict:
    """Tracing stats for one character: traces, landed and fizzled, zaps per trace,
    median time, mean quality, sizes, split by difficulty and by pen or finger, and
    consistency (spread between the hand's own landed attempts; lower is steadier)."""
    bodies = events.by_glyph(rows()).get(glyph)
    if not bodies:
        return {"glyph": glyph, "traces": 0, "note": "no traces of this character in the pull"}
    return {"glyph": glyph, **events.summarise(bodies)}


@tool
def hardest_glyphs(n: int = 10, min_traces: int = 3) -> list:
    """Characters ranked by fizzle rate, then by spread. Characters with fewer
    than min_traces traces are left out: thin data is not a hard character."""
    return events.hardest(rows(), n=n, min_traces=min_traces)


@tool
def save_report(name: str, text: str) -> str:
    """Write a report to agents/out/<name>. name is a file name, not a path."""
    p = OUT / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return f"wrote {p.relative_to(Path(__file__).resolve().parents[2])} ({len(text)} chars)"


ALL = [trace_overview, glyph_summary, hardest_glyphs, save_report]
