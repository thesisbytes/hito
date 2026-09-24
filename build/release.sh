#!/usr/bin/env bash
# Rebuild every build from its pack's version, drop the versioned files the
# packs no longer name, refresh the stable links and the title page. The
# one command a release is, whether a hand or the balance loop runs it.
#   build/release.sh            # then build/test/run.sh, then commit
set -euo pipefail
cd "$(dirname "$0")/.."
py=.venv/bin/python
ver=$($py -c "import json;print(json.load(open('scripts/hiragana/pack.json'))['version'])")
gver=$($py -c "import json;print(json.load(open('scripts/hiragana/game.json'))['version'])")
vver=$($py -c "import json;print(json.load(open('scripts/vocab/pack.json'))['version'])")
kver=$($py -c "import json;print(json.load(open('scripts/vocab/katakana.json'))['version'])")
[ "$ver" = "$gver" ] || { echo "hiragana pack.json ($ver) and game.json ($gver) disagree on the version"; exit 1; }
for f in dist/hiragana-v*.html dist/hiragana-game-v*.html dist/vocab-v*.html dist/katakana-game-v*.html; do
  case "$f" in
    "dist/hiragana-v$ver.html"|"dist/hiragana-v$ver-debug.html"|"dist/hiragana-game-v$ver.html"|"dist/vocab-v$vver.html"|"dist/katakana-game-v$kver.html") ;;
    *) git rm -q --cached "$f" 2>/dev/null || true; rm -f "$f"; echo "dropped $f";;
  esac
done
$py build/stitch.py build/engine.html scripts/hiragana "dist/hiragana-v$ver.html" >/dev/null
$py build/instrument.py "dist/hiragana-v$ver.html" "dist/hiragana-v$ver-debug.html" >/dev/null
$py build/stitch.py build/engine.html scripts/hiragana/game.json "dist/hiragana-game-v$ver.html" >/dev/null
$py build/stitch.py build/engine.html scripts/vocab "dist/vocab-v$vver.html" >/dev/null
$py build/stitch.py build/engine.html scripts/vocab/katakana.json "dist/katakana-game-v$kver.html" >/dev/null
cp "dist/hiragana-v$ver.html" dist/hiragana.html
cp "dist/hiragana-game-v$ver.html" dist/hiragana-game.html
cp "dist/vocab-v$vver.html" dist/vocab.html
cp "dist/katakana-game-v$kver.html" dist/katakana-game.html
$py build/make_index.py index.html >/dev/null
echo "built hiragana v$ver, vocab v$vver, katakana-game v$kver"
