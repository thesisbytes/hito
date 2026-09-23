#!/usr/bin/env python3
"""The hand's verdicts, read back from the verdicts page into
agents/data/verdicts.jsonl, joined to the trace they judge.

The page (agents/verdicts_page.py) keeps its verdicts in the artifact's
own store; Claude Code reads that store with the ArtifactData tool and
saves each document as JSON under a directory. This script folds that
directory into one file per line, so the labels sit beside the pull and
the experiment can be re-run offline.

    agents/.venv/bin/python agents/verdicts.py <dir-of-json-docs>
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hito_agents import events  # noqa: E402

OUT = Path(__file__).with_name("data") / "verdicts.jsonl"


def main():
    src = Path(sys.argv[1])
    by_id = {r["$id"]: r for r in events.traces(events.load())}
    rows = []
    for f in sorted(src.rglob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        tid = f.stem
        t = by_id.get(tid)
        rows.append({"id": tid, "verdict": d.get("verdict"), "readable": d.get("readable"), "at": d.get("at"),
                     "glyph": d.get("glyph") or (t and t["body"].get("glyph")),
                     "landed": bool(t and t["body"].get("ok")) if t else None, "device": t and t.get("device")})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"{len(rows)} verdicts -> {OUT}")


if __name__ == "__main__":
    main()
