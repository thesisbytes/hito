#!/usr/bin/env bash
# Every check that does not need a browser. Run before shipping a build.
set -euo pipefail
cd "$(dirname "$0")/../.."

fail=0
echo "── scoring ─────────────────────────────────────────"
node build/test/scoring.test.mjs | sed 's/^/  /' || fail=1

echo
echo "── smoke (engine executes, frames run) ─────────────"
for f in dist/*.html; do
  node build/test/smoke.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── build reproducibility ───────────────────────────"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
ver=$(python3 -c "import json;print(json.load(open('scripts/hiragana/pack.json'))['version'])")
.venv/bin/python build/stitch.py build/engine.html scripts/hiragana "$tmp/out.html" >/dev/null
if cmp -s "$tmp/out.html" "dist/hiragana-v$ver.html"; then
  echo "  hiragana v$ver rebuilds byte-identical"
else
  echo "  MISMATCH: dist/hiragana-v$ver.html differs from a fresh build"
  fail=1
fi

echo
[ "$fail" = 0 ] && echo "all checks passed" || { echo "FAILURES above"; exit 1; }
