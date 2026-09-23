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
| `shadowScale` | `2.4` | Width multiplier for the glow when a glyph is done. The `strokes` shadow itself is drawn flat at exactly the tolerance width, so the shape shown is the band the scorer forgives. |
| `strictFollow` | `false` | Enforce stroke order, require a pen lift between strokes, and require the path actually be traced. Off means the original permissive scoring. |
| `coverThreshold` | `0.85` | Fraction of path points the pen must pass near. Guards against reaching the end without tracing the middle. |
| `maxTravel` | `2.5` | Cap on pen distance ÷ path length. An honest trace runs about 1.0×; scribbles run 30–120×. This is what stops a scribble on single-stroke glyphs, which have no lift barrier. |
| `tailFraction` | `0.12` | How much of a stroke's own length counts as "at the end". Endpoint forgiveness is a fraction of the stroke it belongs to, never a fixed radius. |
| `minEndTolerance` | `0.02` | Absolute floor under `tailFraction`, as a fraction of canvas. A hand cannot land inside a few pixels, and shrinking the target and the tolerance together is what made level 4 unpassable in v0.1.5. |
| `startSlack` | `0.3` | How much of a stroke's start is forgiven, two ways. The pen may begin up to this fraction of the stroke's length from its first point (never more than the tolerance, never less than `minEndTolerance`), and until it has been there, travel within the stroke does not count. Progress into a stroke is capped by that travel plus the same fraction of its points, so a stroke smaller than the tolerance (the handakuten circle, the ticks on ふ) cannot be finished by a tap on its start or a jab at its end. A fraction rather than a point count, so a circle and a long sweep get the same slack. |
| `sequentialReveal` | `false` | Light one stroke at a time. Requires `strictFollow`. |
| `strayMode` | `drop` | What happens to a stroke that went nowhere — lifted without finishing its stroke or advancing the path more than `straySkid` points, having started off it. `drop`: it never happened; the ink and the scorer go back to the pen-down, and the hand does not record it. `restart`: the character starts again, as on a fizzle. `keep`: the old rule, every stroke stays. The game shells set it per difficulty (`stray` in their table: guided and easy drop, medium restarts). Requires `strictFollow`. |
| `straySkid` | `3` | How many path points a stroke may advance and still count as nowhere. A jab that grazes the start is nowhere; a stroke lifted early after real progress is not. |
| `headingGate` | `true` | Progress only advances through points whose direction agrees with the pen's own motion (smoothed over its last samples). A still pen advances nothing; a pen cutting across a loop advances only the loop's near half; going round the loop advances all of it. Pen-down is let in a few points ahead so a lift mid-stroke lands without a zap. This is what makes a loop smaller than a fingertip's reach traceable at all: on a phone the loops of ぬ め は ほ are 18-26px and the reach 35-43px, so without it every point of a loop is in reach at once. Requires `strictFollow`. |
| *(guided)* | | When the light is dragged, a stroke's end is within reach rather than within `tailFraction`: the light within `R` of the end along the stroke and the pen within `R` of it. A fingertip hides the end it is steering to; covering it is reaching it. Elsewhere the end test is unchanged. |

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
| `mode` | *(unset)* | `guided` — follow the light. The light is *dragged*: it moves only while the pen is on it, forward through points the pen is near, so a chord cannot cut a curve and a pen that arrives along the path has already brought it. No ink, no zaps, no wisps, a light big enough to hold, tolerance 1.5×, one size (the top of `sizeRange`), and the only test is that the light reached the end of every stroke. `easy` — path, dots, comet, numbered stroke badge. `medium` — the shape only; start points and order are on you. `hard` — nothing shown; **needs a scorer that does not exist yet**, see `CLAUDE.md`. In the `field` shell this is only the default the start page opens on; the player switches at runtime. |

Unset leaves whatever `shadow` specifies and the guide always on.

### Shell

| key | default | meaning |
|---|---|---|
| `shell` | `workshop` | `workshop` — the gojūon chart, stroke controls and everything else this project uses on itself. `field` — the game: sketchbook in the bottom third, battle in the top two thirds. `vocab` — a flashcard above the sketchbook: the card asks for a word, the tracer walks its kana one at a time. |
| `field.sign` | `kana` | What a monster's speech bubble shows. `kana` tests recall of the shape; `romaji` tests the reading → shape mapping, which is harder and only bites once the guide is off; `gaijin` asks in the learner's own broken accent. With a `deck` the farang carry words and the three voices turn around: `kana` is the word (コーヒー), `romaji` its reading in the farang's accent (koohii), `gaijin` the farang's own word (coffee), with the accent left to you. |
| `field.speed` | `0.055` | How fast a monster closes on the ward, in field-radii per second. |
| `field.wardHp` | `5` | How many monsters can reach the centre before the run ends. |
| `field.spawnMs` | `5200` | Gap between spawns, falling by `spawnRamp` each wave down to `spawnMin`. |
| `field.advanceMs` | `460` | Delay before the next target loads after a glyph is finished. The engine celebrates for 1.9s before advancing on its own, which is dead time under a clock — a fast hand finishes the next glyph before it exists. |
| `field.reading` | `both` | What blooms where a monster falls. `romaji`, `gaijin`, `both` (the reading with the mispronunciation under it), or `off`. Tracing a shape teaches the shape and nothing else: a hand can learn every stroke of ぬ without the sound ever arriving. Success is where attention is highest, so that is where the reading goes. |
| `field.hitodamaGain` | `1` | Ghost lights a finished glyph kindles on its character. See *Hitodama* below. |
| `field.cleanBonus` | `1` | Extra ghost lights for a trace with no zaps. Clean pays more, as the economy design says it should. |
| `field.hitodamaCap` | `6` | The most a character can hold. Tracing past it is not wasted (mastery still counts), it just does not bank. |
| `field.castMs` | `900` | Cooldown between wisps. One at a time, so a swarm of three ぬ is answered visibly rather than vanishing in a frame. |
| `field.knockback` | `0.07` | With a `deck`: how far, in field radii, a farang staggers back when one kana of its word lands. A six-kana word is a long answer under a clock; each kana buying a step back is what makes it fair. The last kana banishes it. |
| `realms` | `[]` | Other builds to offer on the start page, as `{label, file, kana?, blurb?}`. `file` is a sibling filename (`vocab.html`), never a path or URL: the link works on Pages and in any folder holding both files, and is simply a dead link where the other file is absent — nothing waits on it. Use the stable unversioned names so the link survives a bump. |
| `credits` | `[]` | Lines for the credits page behind the start page's "who this leans on" button, one paragraph each. The pack's `credit` (the licence line) is appended after them, so the KanjiVG attribution is on that page as well as in the footer. Name people here, by role or by name, as they prefer. |
| `field.holdMs` | `1500` | How long after the pen last touched the pad the tracer still counts as busy. A retarget queued in that window waits, so a wisp or a breach elsewhere cannot swap the glyph under a hand that has lifted to think, or that has started a stroke which has not yet found the path. |
| *(guided)* | | The field's guided difficulty sets `allRows`: its farang carry every row of the chart, not only the rows the stage has reached. Guided holds no stage past the second, so under the gate its rows never grew. |
| `field.tidyStrays` | `true` | Erase a stroke that never touched the path when the pen lifts. Cosmetic only: travel and coverage are accumulated live, so the scribble guard is unaffected. Stops the board filling with orange runs of every miss. |
| `field.fizzleRestarts` | `true` | Reload the glyph after a fizzle. Since v0.1.46 `fizzle()` itself restarts the character in every build; this reload on top of it re-rolls the size and clears the field's own zap counter, which is why it stays. |
| `deck` | *(required by `vocab`, optional for `field`)* | Path to the deck file, relative to the repo root. A deck is class content rather than realm data, so it lives outside `scripts/` (`vocab/genki-i.json`, `vocab/katakana.json`). `{deck, source, sections:[{id, title, words:[{ja, romaji, en, note?}]}]}`. The stitch refuses a deck that uses a character the pack has no glyph or no stroke data for — that is a build failure, not a runtime toast. Under the `field` shell a deck makes the farang carry its words (every section, flattened, each word once): the tracer walks a word's kana one at a time, the bubble shows a slot strip filling in, each kana knocks the farang back, the last banishes it, and the ghost light is kept by the word. `scripts/vocab/katakana.json` is that: the vocab pack's kana and strokes under the field shell with the katakana deck. |
| `vocab.prompt` | `en` | What the card asks with, as the default the start page opens on. `en` is the quiz (meaning → word → kana). `romaji` is the reading without the meaning. `kana` is copying, which is handwriting practice rather than vocabulary. |
| `vocab.advanceMs` | `420` | Delay before the next kana of the word loads after one is finished. |
| `vocab.wordPauseMs` | `1200` | How long the finished word blooms — reading and meaning together — before the next card. |
| `vocab.fizzleRestarts` | `true` | As `field.fizzleRestarts`. |
| `vocab.tidyStrays` | `true` | As `field.tidyStrays`. |

The vocab shell is not a variant of the hiragana pack: it needs every kana a
deck might use, so `scripts/vocab/` carries its own glyph list — all 164
hiragana and katakana, written by `build/kana_glyphs.py` — and its own
stroke book and font subsets (`*-kana-all.woff2`). The card keeps a clock
from the moment it is shown to the first pen-down, and every word ends with
a grade: *knew it*, *needed the first kana*, or *no idea*. A hinted word
grades itself (the first-kana button is grade 1, the show-word button and
skip are grade 0); an unhinted word asks, because on easy the guide draws
each shape once the pen is down and only the hand knows whether it needed
that. The round's summary lists every word by grade and recall time, and
the next round puts the words not known first and the slow ones sooner.
Progress is a per-word ledger in localStorage with export/import on the
credits page.

The workshop and the field build from the same pack directory — pass a `.json` file to
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
tunes them stays authoritative. `guided` is a different objective rather
than easy turned down: the light is the thing you hold, the pen leaves no
mark, nothing zaps, and the coverage and travel checks are off because the
light cannot reach the end of a stroke without the pen having gone the whole
way with it.

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

### The run: ink and the workshop strip

```json
"field": { "hpEvery": 10, "hpMax": 5, "inkTrace": 2, "inkClean": 2, "inkKill": 1,
           "inkMastered": 6, "shoveStep": 0.025, "upgradeRamp": 1.6,
           "upgradeCost": { "quick": 8, "bright": 14, "shove": 6, "mend": 10 } }
```

| key | default | what it does |
|---|---|---|
| `hpEvery` | 10 | single characters take one more hit every this many waves. `0` switches it off. Words ignore it: a word is already as tough as it is long. |
| `hpMax` | 5 | and no more than this |
| `inkTrace` | 2 | ink for landing a trace, whether or not anything was standing there |
| `inkClean` | 2 | more, if it was clean |
| `inkMastered` | 6 | a character conjured this many times pays one less |
| `inkKill` | 1 | ink when a wisp finishes a farang. Small on purpose: the idle half earns its keep without outearning the pen. |
| `shoveStep` | 0.025 | how far one level of shove pushes a farang back per hit (the field is 1 across) |
| `upgradeCost` | see above | what level one costs |
| `upgradeRamp` | 1.6 | each level costs this many times the last |

Four upgrades, bought during a run from the strip at the top of the field, and
gone when the ward falls: **早 quick** (wisps fly 18% sooner per level, 5),
**灯 bright** (a trace lights one more, 3), **押 shove** (every hit pushes them
back, 5), **守 mend** (a heart now, and a bigger ward, 5).

The rule they all obey: **an upgrade multiplies what a trace is worth and
never lights a character the hand has not written.** A clean trace is three
hits — itself and the two lights it kindles — so a farang past three hits
needs the pen again or a brighter workshop. That is the whole curve.

### Stages, 魂 tama and the lantern workshop

```json
"field": { "stages": { "rows": 2, "count": 12, "countStep": 3, "gate": 30, "gateRamp": 1.45,
                       "hpEvery": 4, "speedStep": 0.03 },
           "tamaClean": 2, "tamaTrace": 1, "tamaWaves": 3, "inkwellStep": 6,
           "lanternCost": { "heart": 20, "lamp": 30, "inkwell": 15 }, "lanternRamp": 1.6 }
```

| key | default | what it does |
|---|---|---|
| `stages` | see above | `false` switches stages off. A deck is never staged whatever this says. |
| `stages.rows` | 2 | rows of the chart on the field at stage 1; each stage adds one |
| `stages.count`, `countStep` | 12, 3 | farang in stage 1, and how many more each stage. Hold the ward through all of them and the stage is cleared. |
| `stages.gate`, `gateRamp` | 30, 1.45 | what the gate to stage 2 costs, and how each gate grows. A gate is only for sale once the stage before it has been held. |
| `stages.easyFrom`, `mediumFrom` | 1, 8 | from these stages on, a stage only counts toward its gate if it was held at that difficulty or harder. `easyFrom` is 1 since v0.1.50: guided is a sandbox that holds no stage and pays no 魂 (its `tama` is 0), and any stage can still be practised in it. |
| `stages.hpEvery` | 4 | farang take one more hit every this many stages, on top of the run's own ramp |
| `stages.speedStep` | 0.03 | and come this much faster per stage |
| `tamaClean`, `tamaTrace` | 2, 1 | tama for a clean trace, and for one that was zapped |
| `tamaWaves` | 3 | one tama per this many farang faced |
| `inkwellStep` | 6 | ink in hand at the start of a run, per inkwell |
| `lanternCost`, `lanternRamp` | see above | level one of each lantern, and how each level grows |

A difficulty can carry a `tama` multiplier (guided 0.5, medium 2). Holding a
stage to the end pays half again. Each trace's share is scaled by how
recognisable it was, from half (nobody could read it) to half again (it could
be the book); `hand.qualitySpan` (0.09) is the mean distance, as a fraction of
the glyph's diagonal, at which a trace scores zero.

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

### Sync

```json
"sync": { "endpoint": "https://hito-sync.sfo.appwrite.run", "batch": 40, "cap": 500,
          "bytes": 600000, "post": 48000 }
```

| key | default | what it does |
|---|---|---|
| `endpoint` | `""` | where the outbox flushes. Empty means the build makes no network calls at all. Must be `https` — the stitch refuses anything else. |
| `batch` | 40 | most events in one request |
| `cap` | 500 | most events kept while offline; the oldest go first |
| `bytes` | 600000 | most characters of JSON the whole queue may hold. Handwriting made events heavy, so counting them stopped being a way of weighing them. |
| `post` | 48000 | most characters in one request. A `keepalive` fetch over 64KB is rejected by the browser before it leaves, which looks exactly like being offline. |

The player can switch all of it off from **✋ hand** in the header
(`hito-share` in localStorage). Off means nothing is queued and nothing is
sent; the stats on that page are local and keep working. See
`server/README.md` for what the endpoint does with what it is sent.

### Theme

```json
"theme": "night"
```

`gold` (the default, and the Thai realm's) or `night`. Applied by
`build/theme.py` as the last step of the stitch: it translates the colours of
the finished page, layers and all, and leaves its name in a `<meta>` so the
debug build can paint what it adds the same way. New UI is written in the
gold palette; the table does the rest, and a colour it does not know fails
`theme.test.mjs`.

### Account

```json
"account": { "endpoint": "https://sfo.cloud.appwrite.io/v1", "project": "…", "db": "hito",
             "table": "saves", "saveMs": 20000 }
```

Where signing in happens. No `endpoint` means guests only and no request is
ever made. `saveMs` is how long after something is learned the save is written
(it only has to be roughly current). The hostname a build is served from must
be a registered **web platform** in the Appwrite project, or the browser's
calls and the provider's redirect are both refused. See `server/README.md`.

### The hand

```json
"hand": { "maxPoints": 64, "keep": 60, "minStep": 4,
          "pen":    { "size": [0.52, 0.52], "stage": "34dvh", "ease": 1,   "trail": 1,   "halo": 0 },
          "finger": { "size": [0.62, 0.62], "stage": "46dvh", "ease": 1.3, "trail": 2.2, "halo": 36 } }
```

`build/hand_layer.py`, appended to every build. It owns three things: the
pen/finger switch, the handwriting, and the ledger.

| key | default | what it does |
|---|---|---|
| `maxPoints` | 64 | most points kept per stroke in a stored trace. Ends are always kept. |
| `keep` | 24 | how many recent traces stay on the device, for the thumbnails |
| `pen`, `finger` | see above | the two hands, tuned apart. `size` is a `[min, max]` glyph size for that hand, or `null` to leave the pack's own rule alone (a size a difficulty pins, like guided's, is never overridden). The packs pin the pen at 0.52 since v0.1.47: over 239 medium traces the 0.48–0.56 band had the fewest zaps and the most clean traces, and the maintainer found the random sizes an annoyance. `stage` is the sketchbook's size in the games. `ease` multiplies the path's forgiveness (1–2; the scorer caps the result and every end-of-stroke guard is still bound by the stroke's own length). `trail` widens the road ahead, and `halo` is the radius in px of a ring around the light — both so a fingertip does not hide what it is steering by. The finger profile applies in finger mode on a touch screen, and lets go while a pen is down. The finger's `ease` went 1.5 → 1.3 and its `stage` 42 → 46dvh in v0.1.48 after the maintainer traced medium with three different fingers: at 1.5 the band the scorer forgives was 34% of the glyph wide (a quarter circle passed for a loop); at 1.3 it is 28%, against a pen's 25%. A bigger sketchbook leaves that ratio alone — the band and the glyph are both fractions of the canvas — but shrinks the fingertip and its touch offset relative to the glyph, which is what "my strokes don't register where I'm touching" is. |
| `minStep` | 4 | points closer than this (thousandths of the stroke book's box) to the last kept one are dropped, so a slow stroke is not all samples from its first centimetre |

**Pen or finger.** `pen` is the engine's `penOnly`: fingers, palms and mice
are ignored so a hand can rest on the glass. `finger` takes whatever touches,
one pointer at a time. The choice is kept in `hito-input`. With no choice
made, a screen with no touch points starts on `finger` (there is no palm to
reject, and a pen still draws), a phone starts on `finger`, and everything
else starts on `pen`. A finger on a pen-only sketchbook that has never seen a
pen gets a nudge toward the switch.

**A trace** is one attempt — landed or fizzled — as `{glyph, ok, ms, zaps,
tries, strokes, size, input, level, diff, v, s}`. `s` is one flat
`[x,y,t, x,y,t, …]` per stroke: `x,y` in thousandths of the **stroke book's
own space** (size and position undone, so it lays straight over
`strokes.json`), `t` in ms from the first pen-down. It is the hand's own copy
taken at pen-up, before the field tidies strays out of the engine's ink.

**The ledger** (`hito-ledger`) is keyed by character: conjures, clean ones,
zaps, fizzles, time, and `tr` — trouble, smoothed, a zap counting one and a
fizzle three. A character with `tr >= 1.5` over at least three attempts is
*shaky*, and the field stops passing it over however high its mastery. Two
clean traces clear it. Export and import are on the ✋ page; import merges,
and the fuller record wins.

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
