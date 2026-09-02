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
| `mode` | *(unset)* | `guided` — easy with the drain and the fizzle off and the tolerance doubled: drag the light, nothing can go wrong. `easy` — path, dots, comet, numbered stroke badge. `medium` — the shape only; start points and order are on you. `hard` — nothing shown; **needs a scorer that does not exist yet**, see `CLAUDE.md`. In the `field` shell this is only the default the start page opens on; the player switches at runtime. |

Unset leaves whatever `shadow` specifies and the guide always on.

### Shell

| key | default | meaning |
|---|---|---|
| `shell` | `workshop` | `workshop` — the gojūon chart, stroke controls and everything else this project uses on itself. `field` — the game: sketchbook in the bottom third, battle in the top two thirds. |
| `field.sign` | `kana` | What a monster's speech bubble shows. `kana` tests recall of the shape; `romaji` tests the reading → shape mapping, which is harder and only bites once the guide is off; `gaijin` asks in the learner's own broken accent. |
| `field.speed` | `0.055` | How fast a monster closes on the ward, in field-radii per second. |
| `field.wardHp` | `5` | How many monsters can reach the centre before the run ends. |
| `field.spawnMs` | `5200` | Gap between spawns, falling by `spawnRamp` each wave down to `spawnMin`. |
| `field.advanceMs` | `460` | Delay before the next target loads after a glyph is finished. The engine celebrates for 1.9s before advancing on its own, which is dead time under a clock — a fast hand finishes the next glyph before it exists. |
| `field.reading` | `both` | What blooms where a monster falls. `romaji`, `gaijin`, `both` (the reading with the mispronunciation under it), or `off`. Tracing a shape teaches the shape and nothing else: a hand can learn every stroke of ぬ without the sound ever arriving. Success is where attention is highest, so that is where the reading goes. |
| `field.hitodamaGain` | `1` | Ghost lights a finished glyph kindles on its character. See *Hitodama* below. |
| `field.cleanBonus` | `1` | Extra ghost lights for a trace with no zaps. Clean pays more, as the economy design says it should. |
| `field.hitodamaCap` | `6` | The most a character can hold. Tracing past it is not wasted (mastery still counts), it just does not bank. |
| `field.castMs` | `900` | Cooldown between wisps. One at a time, so a swarm of three ぬ is answered visibly rather than vanishing in a frame. |
| `credits` | `[]` | Lines for the credits page behind the start page's "who this leans on" button, one paragraph each. The pack's `credit` (the licence line) is appended after them, so the KanjiVG attribution is on that page as well as in the footer. Name people here, by role or by name, as they prefer. |
| `field.holdMs` | `1500` | How long after the pen last touched the pad the tracer still counts as busy. A retarget queued in that window waits, so a wisp or a breach elsewhere cannot swap the glyph under a hand that has lifted to think, or that has started a stroke which has not yet found the path. |
| `field.tidyStrays` | `true` | Erase a stroke that never touched the path when the pen lifts. Cosmetic only: travel and coverage are accumulated live, so the scribble guard is unaffected. Stops the board filling with orange runs of every miss. |
| `field.fizzleRestarts` | `true` | Put the glyph back to the start after a fizzle. `fizzle()` already clears the ink but only rewinds progress halfway, leaving an empty canvas with credit for a path that is no longer visible — and under a clock there is no time to work out where the middle was. |

Both shells build from the same pack directory — pass a `.json` file to
`stitch.py` instead of a directory to use a variant. `scripts/hiragana/game.json`
is `pack.json` plus a shell, sharing one 400KB stroke book, because duplicating
the data to change one key is how two builds silently drift apart.

A finished glyph hits **whichever monster is carrying it**, nearest first —
not whichever object happened to be locked. "You identify, you do not aim,"
taken literally: finish ぬ and a ぬ takes it. If the monster you were answering
reached the ward mid-glyph the character is still correct and still finds a
mark, and if nothing on the field carries it the shot dissipates.

The target is **locked** once the tracer loads its glyph, and stays locked
until it dies, reaches the ward, or the player taps another monster. A
retarget never interrupts a trace already in progress — it queues and applies
when the hand is free, because a reload wipes whatever had been drawn, and
under a swarm that means every attempt dies to the churn rather than to the
monsters. It cannot
be "whichever is nearest right now": monsters advance while you trace, so one
would overtake yours mid-glyph and the finished character would kill the
newcomer instead. What you are answering must not change underneath the answer.

### The start page

The game opens on a start page with the two axes it actually has: *how much
help* (`guided`, `easy`, `medium`; `hard` is shown locked until its scorer
exists) and *what the sign says* (`kana`, `romaji`, `gaijin`). The pack's
`mode` and `field.sign` are the defaults; the last choice is remembered in
localStorage. The field holds still while the page is up — nothing moves,
spawns or casts — and the ☰ button reopens it mid-run. When the ward falls, a
tap on the field returns to the page rather than restarting blind.

Difficulty is a runtime switch because the penalties are engine state: the
tolerance, drain and fizzle threshold are reassigned by the shell, and the
values it restores for `easy` are read off the engine at boot, so a pack that
tunes them stays authoritative. `guided` is the same easy guide with the
penalties off; the coverage and travel checks at the end of a glyph still
apply, so a scribble still fails there.

### Hitodama

Every finished glyph *kindles* its character: a hitodama (人魂, a ghost
light) is lit over it, and a lit character defends itself. When a monster
carrying it appears, a wisp flies from the dash on its own and one charge
burns down. Trace ぬ twice and the next few ぬ die without the pen.

This is the economy's potency stat given teeth before the economy exists.
It also does the spaced-repetition job in play: the tracer is pointed at the
nearest monster whose character is *dark*, because a lit one will be answered
by its wisp, so the hand is pushed toward exactly the characters that need
practice. The monster under the pen is never taken by a wisp mid-trace — the
one you are answering is yours.

The dash sits on the seam between field and sketchbook and shows the
character loaded in the sketchbook with its charge as a row of flames. A
small teal light on a monster's bubble means its character is lit and it
will be handled. Charge is keyed by character, persists in localStorage, and
survives the ward falling: it is what was learned, and losing a run does not
unlearn anything. A trace with nothing to hit is banked, not wasted.

The split screen is what makes real-time movement safe. Monsters march
continuously because they never share space with the pen: the sketchbook is a
fixed rectangle that does not scroll, scale or reflow while the field moves
above it.

### The three voices

Each glyph carries three labels, and they ask for different things:

| voice | ぬ | what it tests |
|---|---|---|
| `kana` | ぬ | the shape, by copying it |
| `romaji` | `nu` | the reading → shape mapping, which is the direction that matters |
| `gaijin` | `NEW` | nothing, and that is the point — it is the joke |

The third is a `gaijin` field per glyph in `glyphs.json`: the English speaker's
rendering, exaggerated the way a Japanese friend would tease you with it. It is
self-directed humour, the same joke as the hero who cannot read — the player is
the foreigner here, and the monsters are farang.

It also does real work, which is why it earns its place beside the other two.
Each entry aims at a specific error rather than a generic accent: `つ` → `SOO`
names the dropped t, `ふ` → `FOO` names the labiodental f that should be
bilabial, `り` → `RRREE` names the American r standing in for a tap, and `い` →
`EYE`, `う` → `YOO`, `え` → `EE` name the vowels read as their English letter
names. A learner recognises the wrong one as *theirs* in a way a correct
spelling never quite manages.

Worth a native reader's eye on the tone before this goes anywhere public — the
same care the KhienThai spelling got, and for the same reason: it is much
easier to change now than after.

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
