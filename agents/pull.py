#!/usr/bin/env python3
"""Pull hito.events to agents/data/events.jsonl through the Appwrite CLI.

Read-only, paginated by cursor, one row per line with `body` left as the JSON
text the table holds. Experiments run against this file, so they can be
re-run offline and the live table only ever sees finished writes.

    agents/.venv/bin/python agents/pull.py            # everything
    agents/.venv/bin/python agents/pull.py trace      # one kind
"""
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

OUT = Path(__file__).with_name("data") / "events.jsonl"
PAGE = 100


def page(kind=None, cursor=None):
    cmd = ["appwrite", "tablesdb", "list-rows", "--database-id", "hito", "--table-id", "events",
           "--limit", str(PAGE), "--sort-asc", "$createdAt", "--json"]
    if kind:
        cmd += ["--filter", f"kind={kind}"]
    if cursor:
        cmd += ["--cursor-after", cursor]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    return json.loads(out).get("rows") or []


def main():
    kind = sys.argv[1] if len(sys.argv) > 1 else None
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows, cursor = [], None
    while True:
        batch = page(kind, cursor)
        rows.extend(batch)
        if len(batch) < PAGE:
            break
        cursor = batch[-1]["$id"]
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    kinds = Counter(r.get("kind") for r in rows)
    print(f"{len(rows)} rows -> {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")
    for k, n in sorted(kinds.items(), key=lambda kv: -kv[1]):
        print(f"  {k:8} {n}")


if __name__ == "__main__":
    main()
