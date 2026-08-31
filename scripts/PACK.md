# Script pack format

A pack is everything that makes one realm: its glyph list, its stroke data,
its fonts, and how strict the tracing should be. `build/stitch.py` combines a
pack with `build/engine.html` to produce one self-contained HTML file.

```
scripts/<name>/
  pack.json      build settings — this document
  glyphs.json    the character list and their metadata
  strokes.json   stroke paths, in the engine's recording format
```

## pack.json

### Identity

| key | meaning |
|---|---|
| `script` | folder name; informational |
| `version` | stamped into the title, the header badge, and the boot toast. Bump on **every** change — a cached build should be obvious. |
| `title` | browser tab |
| `brand` | header text, left of the version badge |
| `credit` | footer line. Required when the stroke data carries an attribution obligation — KanjiVG is CC BY-SA 3.0. |

### Fonts

`fontDir` plus a `fonts` array. Each entry: `id`, `key` (its name inside the
embedded blob), `label` (shown in the font row), `family` (CSS family name),
`file` (a woff2 under `fontDir`), `role`.

The first font is the default. Files are base64'd into the build, so a realm
never fetches anything at runtime.

`probeChars` are measured to detect whether a font really loaded. **They must
exist in the pack's fonts.** The engine shipped measuring Thai characters,
which a kana-only subset does not contain, so every font reported as blocked.

`exportName` is the filename recording mode offers when exporting.

### Tracing

| key | default | meaning |
|---|---|---|
| `shadow` | `none` | How the target is shown. `none` — only the trail, which is what the follow dot rides on. `strokes` — a thick faint path beneath it. `font` — the glyph in the trace font. |
| `shadowScale` | `2.4` | Width multiplier when `shadow` is `strokes`. |
| `strictFollow` | `false` | Enforce stroke order, require a pen lift between strokes, and require the path actually be traced. Off means the original permissive scoring. |
| `coverThreshold` | `0.85` | Fraction of path points the pen must pass near. Guards against reaching the end without tracing the middle. |
| `maxTravel` | `2.5` | Cap on pen distance ÷ path length. An honest trace runs about 1.0×; scribbles run 30–120×. This is what stops a scribble on single-stroke glyphs, which have no lift barrier. |
| `tailFraction` | `0.12` | How much of a stroke's own length counts as "at the end". Endpoint forgiveness is a fraction of the stroke it belongs to, never a fixed radius. |
| `minEndTolerance` | `0.02` | Absolute floor under `tailFraction`, as a fraction of canvas. A hand cannot land inside a few pixels, and shrinking the target and the tolerance together is what made level 4 unpassable in v0.1.5. |
| `sequentialReveal` | `false` | Light one stroke at a time. Requires `strictFollow`. |

A stroke's tail is where its hook is, and forgiving hooks is the reason this
pack takes stroke data from KanjiVG rather than a font. v0.1.9 replaced a flat
index count with a distance test for exactly that reason — then the distance
was itself a flat radius, which is the same pixels on a 300px stroke and a
21px one. Measured only at full size, it looked fine; at the 0.32 floor it was
forgiving a third of the short strokes. Both halves are now proportional.

### Practice grid

| key | default | meaning |
|---|---|---|
| `grid` | `none` | `cross` — the glyph's box with a dashed centre cross, like a practice sheet. `quarters` — adds quarter lines. `none` — off. |

The box is the glyph's own em square, derived from the same transform the
stroke data was baked with, so "starts left of centre, ends on the lower
line" means the same thing on every character. It shrinks with mastery.

Independent of `mode` on purpose: a grid says where the box is, never what to
draw, so it can stay on at any difficulty. It exists because paper practice
sheets have one, and a stroke floating in empty space gives a learner nothing
to judge length or position against.

### Difficulty mode

| key | default | meaning |
|---|---|---|
| `mode` | *(unset)* | `easy` — path, dots, comet, numbered stroke badge. `medium` — the shape only; start points and order are on you. `hard` — nothing shown; **needs a scorer that does not exist yet**, see `CLAUDE.md`. |

Unset leaves whatever `shadow` specifies and the guide always on.

### Glyph size

| key | default | meaning |
|---|---|---|
| `sizeMode` | `mastery` | `mastery` — size is a function of how often the glyph has been conjured, shrinking down the curve below. `random` — a fresh size is drawn per glyph from `sizeRange`, and mastery no longer sets it. |
| `sizeRange` | `[minGlyph, 0.62]` | The bounds `random` draws between, as a fraction of canvas height. |

`random` exists for two reasons that happen to want the same thing.

As a game, it is the honest test: a hand that can trace す at one size has not
learned much, and under `mastery` the only way to meet a small glyph was to
conjure it six times first. As a workshop, it means one session samples the
whole range — and every scale bug this project has shipped lived at the small
end, which was the end least likely to be reached.

Mastery still counts up and still shows under `random`. It just stops being
the thing that sets the size, which also means levelling can no longer be
confused with resizing. That confusion is why "level 6 is impossible" took
three releases to corner: changing the level was the only way to change the
size, so nothing could tell the two apart.

### Mastery

`difficulty` controls what mastery does to a glyph:

| key | default | meaning |
|---|---|---|
| `shrinkPerLevel` | `0.93` | Glyph scale multiplier per level. |
| `minGlyph` | `0.32` | Floor, as a fraction of canvas. |
| `minTolerance` | `0.045` | Floor on how close the pen must stay. |

Tolerance falls with the **square root** of the scale, not the scale.
Shrinking both together compounds: a smaller target is already harder to hit,
and a hand's precision does not shrink with it. At 12% per level with
proportional tolerance, level 4 became unpassable — a finger covers the glyph
it is meant to trace.

## Adding a realm

1. `scripts/<name>/glyphs.json` — `cp`, `char`, plus whatever the engine's
   metadata line should show.
2. Stroke data in the recording format:
   `TEACHER.fonts[<font>].letters[<char>].strokes = [[{x,y,p,t}, …], …]`,
   normalised 0..1 **in the coordinate space of the glyph as the font renders
   it** — not the full canvas. `build/kanjivg_to_strokes.py` shows the
   transform; getting this wrong is what made the first hiragana guide 1.44×
   too large.
3. Subset the fonts (`build/make_fonts.py`) and write `pack.json`.
4. Build, then run `build/test/smoke.test.mjs` against the output. It
   executes the engine in a stubbed DOM and catches runtime faults that a
   syntax check cannot.
