# Labels of our own

The hand's verdicts on traces, one JSON line each: the trace's id in the
events table, the verdict, the character, and whether the tracer landed it.
No ink is here; the traces themselves stay in the table.

These are the ground truth Laya is measured against and, later, tuned on.
They were collected on a private page (`agents/verdicts_page.py`) and read
back with `agents/verdicts.py`.

| file | traces | who | notes |
|---|---|---|---|
| `verdicts-2026-09-23.jsonl` | 24 | the maintainer | every fizzle to date and 11 landed traces; the 24-trace sample of NOTES.md 2026-09-23; five categories |
| `readable-2026-09-23.jsonl` | 24 | the maintainer | the same 24, rated 0-100 for readability ("100: I could read it; 0: not close"), joined to the category, the geometry, the hand's `q` and Laya's accept |
| `readable-2026-09-23-b.jsonl` | 24 | the maintainer | batch 2: traces from the v0.1.46 session (19 pen medium, 5 finger guided), rated 0-100, with `overshoot` and `joined` |
