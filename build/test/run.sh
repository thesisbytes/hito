#!/usr/bin/env bash
# Every check that does not need a browser. Run before shipping a build.
set -euo pipefail
cd "$(dirname "$0")/../.."

fail=0
ver=$(python3 -c "import json;print(json.load(open('scripts/hiragana/pack.json'))['version'])")
vver=$(python3 -c "import json;print(json.load(open('scripts/vocab/pack.json'))['version'])")

echo "── scoring ─────────────────────────────────────────"
node build/test/scoring.test.mjs | sed 's/^/  /' || fail=1

echo
echo "── alignment (strokes, glyph and grid agree) ───────"
for f in dist/hiragana-*-v*.html dist/hiragana-v*.html; do
  case "$f" in *-debug.html) continue;; esac
  node build/test/alignment.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── state (an attempt restart clears everything) ────"
for f in dist/hiragana-*-v*.html dist/hiragana-v*.html; do
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
echo "── sync (offline stays offline, nothing is lost) ───"
node build/test/sync.test.mjs "dist/hiragana-v$ver.html" | sed 's/^/  /' || fail=1

echo
echo "── field (the game loop runs and the seam holds) ───"
node build/test/field.test.mjs "dist/hiragana-game-v$ver.html" | sed 's/^/  /' || fail=1

echo
echo "── vocab (a word is walked through the seam) ───────"
node build/test/vocab.test.mjs "dist/vocab-v$vver.html" | sed 's/^/  /' || fail=1

echo
echo "── smoke (engine executes, frames run) ─────────────"
for f in dist/*-v*.html; do
  node build/test/smoke.test.mjs "$f" | sed 's/^/  /' || fail=1
done

echo
echo "── build reproducibility ───────────────────────────"
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
for pack in "scripts/hiragana:hiragana-v$ver" "scripts/hiragana/game.json:hiragana-game-v$ver" "scripts/vocab:vocab-v$vver"; do
  src=${pack%%:*}; name=${pack##*:}
  .venv/bin/python build/stitch.py build/engine.html "$src" "$tmp/$name.html" >/dev/null
  if cmp -s "$tmp/$name.html" "dist/$name.html"; then
    echo "  $name rebuilds byte-identical"
  else
    echo "  MISMATCH: dist/$name.html differs from a fresh build"
    fail=1
  fi
done

echo
echo "── stable links (dist/<script>.html is the current build) ──"
# The public links carry no version, so the page has to: the unversioned
# file is a byte-for-byte copy of the current versioned build, nothing else.
for pair in "hiragana:hiragana-v$ver" "hiragana-game:hiragana-game-v$ver" "vocab:vocab-v$vver"; do
  alias=${pair%%:*}; name=${pair##*:}
  if cmp -s "dist/$alias.html" "dist/$name.html"; then
    echo "  dist/$alias.html is $name"
  else
    echo "  STALE: dist/$alias.html is not $name — cp dist/$name.html dist/$alias.html"
    fail=1
  fi
done

echo
echo "── homepage (every local link on index.html resolves) ──"
# The Pages root is index.html, and it links to the stable names above. A
# link to a file that is not there is a 404 on the one page a visitor is
# handed, so it is a failure here rather than a surprise on a phone.
for href in $(grep -o 'href="[^"]*"' index.html | sed 's/href="//;s/"$//' | grep -v '^[a-z]*:'); do
  if [ -f "$href" ]; then
    echo "  $href"
  else
    echo "  MISSING: index.html links to $href, which does not exist"
    fail=1
  fi
done

echo
[ "$fail" = 0 ] && echo "all checks passed" || { echo "FAILURES above"; exit 1; }
