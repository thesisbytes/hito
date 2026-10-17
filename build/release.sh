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
[ "$ver" = "$gver" ] || { echo "hiragana pack.json ($ver) and game.json ($gver) disagree on the version"; exit 1; }
# The kana game (v0.1.76) is the hiragana game and the katakana game in one,
# built from the hiragana game's pack over the kana's glyphs. The old stable
# links stay whole copies of it, so a downloaded one still opens offline; it
# reads its own file name to know which script it meant. The loanword game's
# pack stays, built only by run.sh for its test, for the word tier to come.
$py build/kana_game.py >/dev/null
for f in dist/hiragana-v*.html dist/hiragana-game-v*.html dist/kana-game-v*.html dist/vocab-v*.html dist/katakana-game-v*.html; do
  case "$f" in
    "dist/hiragana-v$ver.html"|"dist/hiragana-v$ver-debug.html"|"dist/kana-game-v$ver.html"|"dist/kana-game-v$ver-debug.html"|"dist/vocab-v$vver.html") ;;
    *) git rm -q --cached "$f" 2>/dev/null || true; rm -f "$f"; echo "dropped $f";;
  esac
done
$py build/stitch.py build/engine.html scripts/hiragana "dist/hiragana-v$ver.html" >/dev/null
$py build/instrument.py "dist/hiragana-v$ver.html" "dist/hiragana-v$ver-debug.html" >/dev/null
$py build/stitch.py build/engine.html scripts/hiragana/game.json "dist/kana-game-v$ver.html" >/dev/null
# The test build: every script open without the hiragana unlock, no sign-in,
# no sync (game.json's "debug"). Not linked from anywhere.
$py build/stitch.py build/engine.html scripts/hiragana/game.json "dist/kana-game-v$ver-debug.html" --debug >/dev/null
$py build/stitch.py build/engine.html scripts/vocab "dist/vocab-v$vver.html" >/dev/null
cp "dist/hiragana-v$ver.html" dist/hiragana.html
cp "dist/kana-game-v$ver.html" dist/kana-game.html
cp "dist/kana-game-v$ver.html" dist/hiragana-game.html
cp "dist/kana-game-v$ver.html" dist/katakana-game.html
cp "dist/vocab-v$vver.html" dist/vocab.html
$py build/make_index.py index.html >/dev/null
echo "built hiragana and kana-game v$ver (and its debug build), vocab v$vver"
