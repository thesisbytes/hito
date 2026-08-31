#!/usr/bin/env bash
# Every check that does not need a browser. Run before shipping a build.
set -euo pipefail
cd "$(dirname "$0")/../.."

fail=0
ver=$(python3 -c "import json;print(json.load(open('scripts/hiragana/pack.json'))['version'])")

echo "── scoring ─────────────────────────────────────────"
node build/test/scoring.test.mjs | sed 's/^/  /' || fail=1

echo
echo "── alignment (strokes, glyph and grid agree) ───────"
for f in dist/hiragana-*.html; do
  case "$f" in *-debug.html) continue;; esac
  node build/test/alignment.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── state (an attempt restart clears everything) ────"
for f in dist/hiragana-*.html; do
  case "$f" in *-debug.html) continue;; esac
  node build/test/state.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── tail (a stroke's end cannot be skipped) ─────────"
node build/test/tail.test.mjs "dist/hiragana-v$ver.html" | sed 's/^/  /' || fail=1

echo
echo "── size (an honest trace passes at every size) ─────"
# Only the current build, and only the verdict. The full glyph x size table is
# what you want when investigating, not when shipping:
#   node build/test/size.test.mjs dist/hiragana-vX.Y.Z.html
node build/test/size.test.mjs "dist/hiragana-v$ver.html" --brief | sed 's/^/  /' || fail=1

echo
echo "── harness (the debug controls reach the engine) ───"
node build/test/harness.test.mjs "dist/hiragana-v$ver-debug.html" | sed 's/^/  /' || fail=1

echo
echo "── smoke (engine executes, frames run) ─────────────"
for f in dist/*.html; do
  node build/test/smoke.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── build reproducibility ───────────────────────────"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
.venv/bin/python build/stitch.py build/engine.html scripts/hiragana "$tmp/out.html" >/dev/null
if cmp -s "$tmp/out.html" "dist/hiragana-v$ver.html"; then
  echo "  hiragana v$ver rebuilds byte-identical"
else
  echo "  MISMATCH: dist/hiragana-v$ver.html differs from a fresh build"
  fail=1
fi

echo
[ "$fail" = 0 ] && echo "all checks passed" || { echo "FAILURES above"; exit 1; }
