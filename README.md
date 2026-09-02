# Hito (人)

A stylus-first tracing engine for learning to write scripts, with an
idle game underneath. Every character you learn is a province you've taken;
hold it and it glows, neglect it and the spirits creep back in.

人 is two strokes. Neither stands on its own. That's the name and the point:
the people behind this — a native teacher recording strokes, a friend drawing
a font by hand, kids finding bugs — all lean on each other, and so will you.

| realm | state |
|---|---|
| **Hiragana** — 46 gojūon | playable. Stroke order from KanjiVG, textbook letterforms, one stroke revealed at a time. |
| **Thai** — 44 consonants | engine works; no stroke data yet. Waiting on a recording session — see [KhienThai](https://github.com/thesisbytes/khienthai). |

Each realm ships as a single HTML file. No install, no server, no
dependencies. Open it on a tablet and start tracing:

**[Play](https://thesisbytes.github.io/hito/dist/hiragana-game-v0.1.22.html)** — the game: draw below, farang advance above.  
**[Workshop](https://thesisbytes.github.io/hito/dist/hiragana-v0.1.22.html)** — the full gojūon chart and every control, which is what this project uses on itself.

## How the tracing works

You follow one stroke at a time. Strokes already made stay lit; the one you
are on is drawn by your pen; the rest have not caught light yet. Finishing a
stroke throws sparks along it.

It is strict on purpose, because a tracer that accepts anything teaches
nothing:

- **Stroke order is enforced** — you cannot start a later stroke early.
- **Separate strokes must be separate.** き is four strokes, and drawing it
  as one line is refused. This is the whole reason the hiragana data comes
  from KanjiVG rather than from a font: print fonts join hooks that
  handwriting keeps apart.
- **You have to trace the whole path**, not just reach the end of it.
- **Scribbling does not work.** An honest trace covers about the length of
  the path; a scribble covers many times it, and that is measured.

Each glyph appears at a size drawn at random, rather than shrinking as you
master it. A hand that can only trace す at one size has not learned much.

## Layout

- `scripts/` — one folder per script: glyph lists, stroke data, fonts, theme
- `fonts/` — source woff2 files, embedded at build time
- `glyph-forge/` — companion tool for capturing handwritten letterforms into a font
- `build/` — stitches engine + script pack into a single file
- `dist/` — built, versioned outputs

`build/` holds the engine and the stitch script that combines it with a
script pack. `CLAUDE.md` has the full brief; `NOTES.md` is the running log.

## Building

```sh
python3 -m venv .venv && .venv/bin/pip install 'fonttools[woff]'
.venv/bin/python build/stitch.py build/engine.html scripts/hiragana dist/hiragana-vX.Y.Z.html
node build/test/smoke.test.mjs dist/hiragana-vX.Y.Z.html
```

## Credits & licences

- Fonts: Sarabun, Noto Sans Thai Looped, Kanit, Klee One, Noto Sans JP — SIL Open Font License
- Hiragana stroke data derived from [KanjiVG](https://kanjivg.tagaini.net/) — CC BY-SA 3.0
- Folklore: the Ramakien, Thai phi, Japanese yokai, and one Nobunaga
