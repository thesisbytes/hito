# Hito (人)

A stylus-first tracing engine for learning to write scripts, with an
idle game underneath. Every character you learn is a province you've taken;
hold it and it glows, neglect it and the spirits creep back in.

人 is two strokes. Neither stands on its own. That's the name and the point:
the people behind this — a native teacher recording strokes, a friend drawing
a font by hand, kids finding bugs — all lean on each other, and so will you.

Currently teaching:

- **Thai** — 44 consonants, stroke paths recorded by a native teacher
- **Hiragana** — 46 gojūon, stroke order from KanjiVG, textbook-style letterforms

Each realm ships as a single HTML file. No install, no server, no
dependencies. Open it on a tablet and start tracing.

## Layout

- `scripts/` — one folder per script: glyph lists, stroke data, fonts, theme
- `fonts/` — source woff2 files, embedded at build time
- `glyph-forge/` — companion tool for capturing handwritten letterforms into a font
- `build/` — stitches engine + script pack into a single file
- `dist/` — built, versioned outputs

See `CLAUDE.md` for the full project brief and lore direction.

## Credits & licences

- Fonts: Sarabun, Noto Sans Thai Looped, Kanit, Klee One, Noto Sans JP — SIL Open Font License
- Hiragana stroke data derived from [KanjiVG](https://kanjivg.tagaini.net/) — CC BY-SA 3.0
- Folklore: the Ramakien, Thai phi, Japanese yokai, and one Nobunaga
