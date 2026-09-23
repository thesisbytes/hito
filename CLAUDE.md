# Hito (人)

A stylus-first script-tracing engine with idle-game dynamics. Portable and
script-agnostic: Thai and Hiragana are the first two realms, others follow.
It is *used by* nirathai.com but is not owned by it — keep the engine free of
nirathai branding, URLs, or assumptions.

This file is the project's brain. All work happens in this repo — design,
engine, builds, and commits alike. It previously described a split between a
design chat and this workspace; that split is gone.

If something in the plan looks wrong, say so and fix it rather than working
around it, and record the decision in `NOTES.md` so the reasoning survives.
The plan below is a starting position, not a specification to be executed
literally — where reality disagrees with it, reality wins and the doc gets
updated.

---

## Repo layout

```
hito/
  CLAUDE.md            this file
  README.md            public-facing description
  NOTES.md             running log (append, don't rewrite)
  scripts/
    PACK.md            the pack format — read before adding a realm
    thai/              glyph list (stub; strokes not yet recorded)
    hiragana/          glyph list, KanjiVG-derived strokes, pack settings
    vocab/             every hiragana and katakana, strokes, pack settings
  fonts/               subset .woff2 files, embedded as base64 at build time
  glyph-forge/         handwriting capture tool (separate app, same aesthetic)
  build/
    engine.html        the tracer engine — the source everything builds from
    stitch.py          engine + pack -> a single self-contained HTML
    kanjivg_to_strokes.py   KanjiVG SVG -> the engine's stroke format
    strokes_to_svg.py       the inverse; belongs to KhienThai
    make_fonts.py           subset fonts down to a pack's characters
    instrument.py           add attempt telemetry to a build, for debugging
    fix_persistence.py      repair the window.storage bug in an old build
    test/run.sh             every check that does not need a browser
    test/size.test.mjs      every glyph x 16 sizes, offline
    test/harness.test.mjs   the debug controls actually reach the engine
    test/tail.test.mjs      a stroke's end cannot be skipped, at any size
    test/field.test.mjs     the game loop runs and the tracer seam holds
    shell_field.py          the game shell, appended as a layer
    sync_layer.py           offline outbox, appended as a layer
    test/sync.test.mjs      offline stays offline and nothing is lost
    hand_layer.py           pen or finger, the handwriting, the stats ledger
    account_layer.py        guest or signed in: Google through Appwrite, and a save that follows you
    make_index.py           writes index.html, the title screen (it shares the sign-in code)
    traces_gallery.py       the events table's traces as a page of SVGs over the shape asked for
    theme.py                one colour table, applied to a finished page (gold, night)
    test/theme.test.mjs     a night page has no warm colour in it but the warnings
    test/account.test.mjs   a file makes no request; merging never unlearns; a tunnel is not a sign-out
    test/hand.test.mjs      the switch reaches the engine; a note never costs a glyph
    test/server.test.mjs    what the endpoint refuses, checked without deploying
    test/offline.mjs        preloaded by run.sh: no test ever reaches the live endpoint
    test/shadow.test.mjs    no layer reuses one of the engine's names
    shell_vocab.py          the flashcard shell, appended as a layer
    kana_glyphs.py          writes the 164-kana glyph list the vocab realm traces
    test/vocab.test.mjs     a word is walked through the seam
    test/words.test.mjs     the farang carry words (the katakana game)
  vocab/                 decks: class content, not realm data (genki-i.json, katakana.json)
  agents/                the multi-agent layer (Strands): reads the events table, never runs at play time; see agents/README.md
  dist/                built single-file outputs, one per script, versioned
  server/sync/         the Appwrite function behind sync.endpoint (see server/README.md)
  appwrite.config.json the Appwrite project: table schema and function settings, no secrets
```

Run `build/test/run.sh` before shipping. It checks the scoring against
scripted attempts, executes each build in a stubbed DOM, and confirms the
committed build rebuilds byte-identical from source.

Single-file HTML with zero external dependencies is a deliberate constraint.
Every deliverable must open from a double-click, offline, on a tablet.

**Sync does not weaken this.** As of v0.1.20 there is an outbox layer, but it
is offline-first by construction: events are recorded locally and flushed
opportunistically, a build with no `sync.endpoint` makes no network calls at
all, and a failed or impossible request is the normal case rather than an
error. Nothing in the game ever waits on a response. If a network call ever
becomes load-bearing, the constraint above is gone — so it must not.

As of 2026-09-20 the builds ship with an endpoint (an Appwrite function, see
`server/README.md`), so they do talk to the network when there is one. The
paragraph above is what keeps that honest, and the player can switch it off
from **✋ hand** in the header. The stats on that page are computed on the
device from a ledger kept on the device; they never read from the server.

The one thing that will need a real exception is the idle economy, which
cannot be client-authoritative without being editable by anyone with devtools.
That is why it is last: everything before it merges cleanly offline, and it
does not. See `server/README.md`.

---

## Where things stand (Aug 2026)

### Thai tracer — `dist/thai-v0.9.4.html`

Built iteratively in chat as `nirathai-trace-vX.Y.Z.html`; being renamed into
the Hito scheme. Everything below already works:

- Gold glowing ink trail on a dark lacquer theme ("spell conjuring")
- Continuous path-following scoring (not per-stroke judging)
- Operation-style zap when straying: shake, red flash, haptic buzz, ember sparks
- Mastery/leveling: each successful conjure shrinks the outline and tightens
  tolerance ~12%
- Dotted glowing trail showing the remaining path, cached offscreen
- Teacher recording mode (teal UI): capture numbered stroke paths, export JSON,
  Copy button with clipboard fallbacks
- Per-font recording books keyed by font ID
- Three fonts embedded as base64 woff2 subsets: Sarabun, Noto Sans Thai Looped,
  Kanit
- Version stamp in `<title>`, header, and boot toast

**Pending:** The 44 consonants still need recording. Earlier sessions with
the project's native Thai teacher did not survive, and no recording JSON has
ever been committed.

The cause is now known, and it was not browser settings or user error.
`window.storage` is called throughout the engine and **defined nowhere** — it
is not a browser API. Every call sits behind `if(window.storage)`, so saving
and loading were silent no-ops, while the save button reported `saved ✓`
regardless. The recordings were never written anywhere.

Fixed in `dist/thai-v0.9.4.html` — a real localStorage-backed
`window.storage`, and a save that says `SAVE FAILED` instead of always
claiming success. v0.9.3 has been removed from `dist/` rather than left
sitting there: it silently destroys work, and a superseded build that eats
data is not worth keeping accessible. Git history has it if it is ever
needed.

`build/fix_persistence.py` applies the same fix to any build that predates
it.

The standing rule stays, and now has a second reason behind it: a recording
must become a file on disk the moment it is made.

### Glyph Forge — `glyph-forge/`

Capture tool for hand-drawing original Thai letterforms on a pen display
(pressure disabled at driver level, uniform stroke width). Same gold-on-lacquer
look. Exports 1024×1024 black-on-white PNGs named by codepoint (AGL style,
`uni0E01.png`) in a ZIP built with a hand-rolled writer, plus `metadata.json`
with baseline / body-top pixel positions. Covers all 80 Thai glyphs (44
consonants, vowel signs, tone marks, thanthakhat, numerals).

Next step, once the letterforms are done: a FontForge script that imports the PNGs and
places combining-mark anchors so tone marks stack correctly.

### Hiragana — `dist/hiragana-v0.1.50.html`

Playable, and traced end to end without a break. The 46 gojūon with KanjiVG
stroke order baked in, Klee One and Noto Sans JP embedded, laid out as a
proper gojūon chart with the ya and wa rows keeping their gaps and ん on its
own row. As of v0.1.37 the five voiced rows (が ざ だ ば ぱ) and the small
kana that matter (ゃ ゅ ょ っ) are in too: 75 glyphs, the strokes lifted from
the vocab pack's book (same converter, same source; the gojūon were
byte-identical), the chart gaining seven rows, and っ sitting under つ. The
other small kana (ぁぃぅぇぉ ゎ) are left out of the chart on purpose: they
hardly occur in hiragana, and the vocab realm already has them for the words
that need them.

What the tracing enforces, all of it learned by finding it broken:

- **Stroke order.** Progress is clamped to the current stroke, so a later one
  cannot be started early.
- **Separate strokes stay separate.** Crossing a boundary needs a real pen
  lift. Without this a single unbroken line satisfied a four-stroke glyph,
  which defeats the hook problem this pack exists for.
- **The whole path must be traced**, not merely reached — 85% coverage,
  measured by where the pen actually went.
- **Scribbles fail on distance.** An honest trace runs about the length of
  the path; scribbles run 30–120×. This is what stops single-stroke glyphs,
  which have no lift barrier.
- **A stroke has to be travelled, not touched.** Progress into a stroke is
  capped by the pen's own travel within it, plus a free start that is a
  fraction of the stroke (`startSlack`). Found on the handakuten circle,
  which is smaller than the tolerance: from its start every point was in
  reach and its end is its start, so a tap finished it.
- **A stroke begins where it begins.** Travel only counts once the pen has
  been within `startSlack` of the stroke's length from its first point
  (floored like the end tolerance). Found on ふ's ticks, which are shorter
  than a jab's skid: a wiggle at the end was more travel than the tick is
  long. The stroke's end and its start are now judged the same way.
- **A stroke that went nowhere never happened (v0.1.46).** Lifted without
  finishing its stroke or advancing the path, it is dropped from the ink
  and from the hand's record, or in medium and above it restarts the
  character. The maintainer: the recordings were a mess of redrawn
  lines — 61 of the first 286 traces carried one. **A fizzle restarts the
  character** in every build now, too; it used to rewind halfway.
- **Progress goes the way the stroke goes (v0.1.49).** The maintainer, with
  a finger: "I am headed towards a loop, it'll track multiple points and jump
  to complete." On a phone the loops of ぬ め は ほ are 18-26px and a
  fingertip's reach 35-43px, so every point of a loop was in reach at once,
  and no size fixes that: the canvas is the phone's width. Progress now
  advances only through points whose direction agrees with the pen's
  motion, so a loop is drawn by going round it. `headingGate` in the pack.

Presentation: one stroke lit at a time. Finished strokes stay shining, the
current one is drawn by the pen, later ones have not caught light yet.

**Size is its own axis** as of v0.1.12, and no longer a function of mastery.
`sizeFor()` is the single seam — everything scale-dependent already derives
from `curF`, so intercepting the one line that sets it moves tolerance, the
grid, the shadow and the stroke transform together. The pack ships
`sizeMode: random` over `[0.32, 0.62]`: a fresh size per glyph, so a hand has
to handle any of them and a session samples the whole range instead of
walking down it six conjures at a time. Mastery still counts; it just no
longer sets the size.

As of v0.1.47 the pen is pinned at 0.52 and the finger at the largest: one
size per hand (`hand.pen.size`, `hand.finger.size`). The maintainer found the
random sizes an annoyance, and 239 medium traces agreed on the band. The
random rule is still there for any pack that wants it.

That separation is the point. While size *was* mastery, "this size is too
small" and "this level is broken" were the same observation, which is why the
level-6 report survived three releases — and why changing the level to test it
also called `load()`, clearing the very state that was at fault.

The debug build carries the sweep: a size row with a pin that survives glyph
navigation (so the alphabet can be walked at one fixed size), and a
`✗ fails here` button. A fizzle is one bad attempt; *impossible here* is a
judgement only the hand can make, so it is a button rather than an inference.
The flag records size, glyph, level, coverage, travel, progress, attempts and
the engine's own toast — enough to tell the difficulty curve, the stroke data
and the state apart at the moment the hand says no. `__hito.matrix()` renders
the glyph x size grid on the tablet.

**What the offline sweep settled, and what it did not.** `size.test.mjs` holds
sample spacing and wobble amplitude constant *in pixels* — the earlier
simulations scaled the pen path along with the ideal path, so their simulated
hand shrank with the target and the travel ratio was constant by construction.
With that fixed: travel is flat across the range (1.06x -> 1.01x against a
2.5x cap), and the hand budget holds near 32px while the glyph goes 223px ->
115px. Tolerance falls 25px -> 18px absolutely but *rises* from 11.3% to 15.7%
of the glyph. So neither the curve nor the scorer explains a small glyph being
impossible. Occlusion of the target by the hand is the standing suspect and no
model here can see it. This is the fourth time a simulation has been more
forgiving than the hand: it is a regression guard, not evidence of comfort.

The shadow is drawn from the stroke data rather than the font. KanjiVG's
centrelines describe KanjiVG's letterforms, and only 66% of the path fell
inside Klee One's ink even at the best possible alignment — a shape
difference, not a misalignment. Deriving the target from the same data as the
guide is what makes them agree.

Not yet implemented: the economy stubs called for below.

### Guest, or signed in — every build and the title screen, as of v0.1.41

**Guest is the game** and is not dressed as a lesser mode: no account, a
made-up device id, everything on the device, opens from a double-click. A
build opened from a file has no sign-in at all, because a provider has nowhere
to send anybody back to, and the page says that instead of showing a button
that cannot work.

**Signed in is a save file that follows you**: Google, through Appwrite, no
SDK (`build/account_layer.py`). One row per player in `hito.saves`, readable
by its owner only, holding the hand's ledger and mastery. The merge is the
rule `server/README.md` wrote down before there was a server — the fuller
record wins per character, mastery is `max()` — so no device can unlearn what
another learned and nothing ever asks the player which copy to keep.

It is client-written, so it is exactly as trustworthy as a save file: right
for "how am I doing", worthless as a claim about anyone else. **It is not the
leaderboard and must not become one.**

`index.html` is the title screen and is generated (`build/make_index.py`),
because it signs people in and must run the same code the realms do. 人 is
drawn in its two strokes, Begin goes to the realm you were last in, and the
tally under it is read off the ledger the realms keep.

### The hand — every build, as of hiragana v0.1.38

`build/hand_layer.py`, appended like the field and for the same reason: it
reaches the engine through `conjure`, `fizzle` and `zap`, calls every one of
them through, and scores nothing. Three things that are all about the hand
rather than the glyph:

- **Pen or finger.** `penOnly` had been a workshop button since the Thai
  tracer — on by default, remembered by nothing, and hidden in the games, so a
  phone met a sketchbook that ignored it. It is now a remembered switch on the
  start page and the ✋ page, with a first guess that only has to avoid a dead
  sketchbook. Scoring is identical for both; a finger hides more of the target
  than a pen does, and no model here can see that either.
- **Two hands, tuned apart (v0.1.43).** The maintainer: "touch / pen sizes
  should be optimized separately". `hand.pen` and `hand.finger` are separate
  profiles — glyph size range, sketchbook size, forgiveness, width of the road
  ahead, halo — and neither is the other with a multiplier on it. Every trace
  records which it was drawn under (`prof`), so each can be tuned from its own
  data. What the finger profile is really for is **seeing**: the maintainer
  plays guided, which is "drag the light", and the light was 4-7px across on a
  9px road under a fingertip that covers 50. The road is drawn wider than the
  finger hides and the light wears a ring that shows around it.
- **A finger is not a pen (v0.1.42).** The maintainer, of finger tracing:
  "hard, cause i have fat fingers". The tolerance was tuned for a pen tip,
  which shows you the line as you draw it; a fingertip sits on top of the
  path. So in finger mode on a touch screen the glyph is drawn at its
  largest, the sketchbook grows from 34 to 42dvh, and the path forgives 1.5x
  through `HAND_EASE` — one seam in the scorer, capped, and let go the
  moment a pen touches down. `run.sh` runs the stroke-end guard on an eased
  copy: forgiving a finger must not let a stroke's end be skipped. A trace
  records its `ease`, or nobody reading the table could compare the two.
- **The handwriting.** Every attempt, landed or fizzled, kept in the stroke
  book's own space so it lays straight over `strokes.json` at any size. It is
  the hand's copy taken at pen-up: the field tidies strays out of the engine's
  ink a moment later, and a log with the mistakes swept out is a log of the
  stroke book. This is the data hard mode's `compare()` thresholds have been
  waiting for — what genuine freehand looks like.
- **The ledger.** Per character, on the device, with export and import. A
  character that still bites (`shaky`) is not passed over by the field however
  high its mastery, which is the first time the game has steered by how the
  tracing went rather than by whether it was done.

Checked in a real browser as well as the stub, because the stub cannot see
whether a second script can reassign the engine's `penOnly` (it can). Headless
Chrome driven with synthetic pointer events needs two allowances that are
about the fakery and not the game: `setPointerCapture` refuses a synthetic
pointer, and `getCoalescedEvents()` is empty for one.

### Katakana — `dist/katakana-game-v0.1.13.html`

The field shell with a deck: the farang carry katakana loanwords. The
maintainer's own report was freezing on katakana words "although sometimes I
know what it sounds like", and the suggestion that followed was the design:
mix it with the game, with the farang mangling the pronunciation. A loanword
is exactly that — English said in a Japanese accent — so the sign axis turns
around: `romaji` is the farang's accent (koohii), `gaijin` is the farang's own
word (coffee) with the accent left to you, `kana` is copying. The default is
the accent, since knowing the sound and still freezing on the shapes was the
complaint.

The pack is `scripts/vocab/katakana.json`: the vocab pack's 164 kana and
strokes under the field shell, with `vocab/katakana.json` — 101 words in
three sections by what makes katakana hard (plain, the long-vowel bar, the
small kana). The tracer walks a word's kana one at a time, the bubble shows a
slot strip filling in, each landed kana knocks the farang back a step
(`field.knockback`), the last banishes it and blooms the half the sign kept
back, and the ghost light is kept by the word. Slower and sparser than the
hiragana field, because a word is a longer answer.

### Vocab — `dist/vocab-v0.1.28.html`

The first word-level realm, and the "layout step" the economy plan always
said words would be: a word is a sequence of glyph recordings, no new stroke
format. A flashcard sits above the sketchbook. It shows the prompt (the
English by default), a strip of blank slots the length of the word, and the
tracer is walked through the word's kana one at a time. Finish a kana and
its slot lights; finish the word and the reading and meaning bloom together.

Decks are class content rather than realm data, so they live in `vocab/`
outside `scripts/`. The first is Genki I, Lessons 1 and 2, sectioned one per
quiz page. The pack's glyph list is every hiragana and katakana (164, from
`build/kana_glyphs.py`) so a new lesson is only ever a JSON edit, and the
stitch refuses a deck that uses a character with no stroke data.

The recall test is honest only as far as the tracer lets it be: on easy the
guide reveals each kana's shape once the pen is down. So the card measures
what happens *before* the pen touches (v0.1.11): a clock from card shown to
first pen-down, and a grade per word — knew it, needed the first kana, no
idea — which the maintainer named from their own recall ("if I see the
first hiragana I'll get most words"). A hint grades the word itself; an
unhinted word asks, since only the hand knows whether it needed the guide.
The summary lists the round by grade and time, and the next round puts
the words not known first and the slow ones sooner. Real free recall
waits on the hard-mode scorer, like everything else.

The shell carries a copy of the field's difficulty table. See `NOTES.md`
(2026-09-08) for why that is a known drift risk rather than an oversight.

---

## Hiragana plan (delivered — kept for the reasoning)

Scope: the 46 gojūon only. No dakuten, handakuten, or yōon yet.
Glyph list with row/order/romaji is in `scripts/hiragana/glyphs.json`.

**The hook problem.** Print Gothic fonts join strokes that handwriting keeps
separate (き, さ, ふ, り are the obvious ones — see `hookNote` fields).
Learners who trace a print font learn wrong shapes. So:

- **Trace font:** Klee One (SIL OFL). Textbook-style, separated hooks.
- **Print font:** Noto Sans JP (SIL OFL). Shown small beside the trace glyph
  so the learner sees what the character looks like in the wild.
- **Stroke data:** KanjiVG (CC BY-SA 3.0), converted by
  `build/kanjivg_to_strokes.py` into `scripts/hiragana/strokes.json` and baked
  in as the default book. Recording mode stays
  available so contributors can override any stroke. KanjiVG requires a credit
  line in the app footer.
- **Layout:** 5×10 gojūon grid replaces the Thai consonant list.
- **Engine:** shared. Everything above is delivered by `build/stitch.py`
  applying pack settings to `build/engine.html`; see `scripts/PACK.md`.

---

## Difficulty modes

Set per pack as `mode` (see `scripts/PACK.md`).

| mode | shows | tests |
|---|---|---|
| **easy** | path, dots, comet, and a numbered badge on the stroke you are about to draw | the motion — can you make the shape |
| **medium** | the shape only | where each stroke starts and what order they go in |
| **hard** | nothing | recall of the whole character |

`label()` had drawn numbered stroke badges since the beginning but only ever
in record mode. Stroke order is precisely what a learner is trying to recall,
so on easy the number now appears on the stroke about to be drawn.

### Hard mode — planned, not built

Free draw needs a different scorer. Path-following asks *"did you follow this
line"*, which a glyph drawn from memory will always fail — not because it is
wrong but because it was never tracing. The question has to become **"is what
you drew あ?"**

**This is verification, not recognition.** Recognition is "which of 2,000+
characters is this", an open-set problem needing a trained model.
Verification is binary against a reference already in hand: the expected
stroke count, the expected order, and the exact geometry of every stroke.
A recogniser would be rediscovering what `strokes.json` already states.

Porting one would also fight the architecture — Zinnia or Tegaki means WASM
and GPL, a tf.js model is megabytes, a cloud API breaks offline. All three
break "single file, opens from a double-click, works offline", which is the
constraint the whole project is built on.

The engine already contains most of the scorer. `compare(u, t)` compares two
normalised strokes and returns `{ok, reason}`, catching reversed direction,
a wrong starting point, and a stroke cut short or run long — with the failure
messages already written for a human. **It is dead code today; nothing calls
it.**

What hard mode still needs:

1. **Normalise** the drawn glyph's bounding box onto the reference's. This is
   what makes size and position free, which is how writing actually works.
2. **Stroke count must match**, checked at the glyph level. This is where
   hooks are enforced: き drawn as three strokes is wrong even if it looks
   right, and that is the entire reason the data comes from KanjiVG.
3. **Stroke order**, by comparing drawn stroke *i* against reference stroke
   *i* rather than searching for a best match. Order is not a bonus check —
   it is half of what the dataset knows.
4. **Per-stroke `compare()`** with loosened thresholds. The current ones
   assume tracing; how they behave on genuine freehand is unknown until
   somebody draws at them. That is a tuning session, not research.
5. **A completion signal.** There is no path to finish, so evaluate after a
   short pause following a pen lift — *not* on reaching the expected stroke
   count, because the moment of evaluation would itself reveal the count,
   and the count is part of what hard mode tests.

Medium is the honest next step regardless: it already tests start points and
stroke order, and it works with the scorer that exists.

---

## The name

人 (hito, "person") is two strokes, and neither can stand on its own — each
leans on the other, and if you take one away the character falls. A mentor
taught the kanji that way: we depend on one another. That's the project.
One person records the strokes, another draws the letterforms, testers find
the bugs, someone builds it, and every learner leans on all of them.

人 is the first kanji past the kana border. Two strokes. It should be the
first thing a learner traces once hiragana is done.

## The world (lore direction)

Not for the first build. Written down so it survives.

Two traditions, both load-bearing:

- **Unification** — Nobunaga's *tenka fubu* and Rama's campaign to Lanka in
  the Ramakien. Each script is a realm; each character is a province.
  Trace it cleanly to take it. Hold it (potency) or it drifts back to the
  wild. Unify it (mastery) and it stops rebelling for good.
- **The wild** — Thai phi (khamot, kong koi, pop, krasue) and Japanese yokai
  haunt unconquered provinces. Ghost lights (phi khamot / hitodama) are the
  visual language for potency: a lit glyph is a flame you tend.

### Combat, as far as it is decided

Sketched in discussion, not built. Two of these constrain the data model, so
they are recorded as decisions; the rest is explicitly open.

**DECIDED — affinity is linguistic structure, not invented elements.**
A monster weak to the k-row must be killed with か き く け こ. Affinities map
to the gojūon grid: rows, vowel columns, stroke count. Two reasons, and the
second is the one that matters:

- Learning the type chart *is* learning that か き く け こ are siblings
  because they share a consonant. That is a real fact about the language.
- Arbitrary affinities let a player min-max toward the characters they
  already know. A learner needs the opposite — practice on their weakest
  glyphs. Structural affinity makes a monster demand a specific row, so
  nothing can be substituted.

It is also the cheap option: `glyphs.json` already carries `row`, so no pack
needs a new field and nobody hand-authors 46 assignments per script forever.

**DECIDED — the hero cannot read.** A villager who finds a tablet, not a
scribe. This is mechanical rather than sentimental: the player starts unable
to read, so the hero's ignorance is the player's ignorance and every glyph
they learn, the player learns. A scribe already knows the characters, which
makes the fiction and the mechanics tell opposite stories.

**DECIDED — the screen splits: you draw below, the battle happens above.**
The bottom third is the input surface and nothing else. The top two thirds is
the field: farang monsters advance from the edges toward a centre you are
protecting, each carrying a speech bubble with the sign you have to answer.
Upgrade tabs come later and belong to the shell, not the field.

Two things follow from the split, and both were already decided for other
reasons:

- The pen never chases anything. Monsters move in the top two thirds; the
  hand works in the bottom third, on a surface that never scrolls or scales
  under it. This is what "you identify, you do not aim" needs in order to
  hold — tracing accuracy survives a moving screen only if the tracing area
  does not move.
- The sign lives in the bubble, so the open kana-or-romaji question is a
  property of one text field rather than of the layout. It can be flipped per
  difficulty, or per monster, without redrawing anything. There are now three
  voices, not two — `kana`, `romaji`, and `gaijin`, the learner's own broken
  accent. See `scripts/PACK.md`.

The monsters being farang is the same joke as the hero who cannot read: the
player is the one who cannot read the sign yet.

Built in v0.1.20 as `build/shell_field.py`, appended as a layer rather than
woven into the engine with substitutions. It reaches the engine only through
globals the engine already exposes — `load`, `conjure`, `LETTERS`, `idx` — so
the tracer and its scoring stay the single authority on what counts as a
correct glyph. The game cannot disagree with the workshop about that, because
it does not carry its own copy of it.

The seam is `load()`. The field wraps it so every load the *engine* initiates
on its own — `conjure()`'s delayed advance, the clear button, a mode change —
lands on whatever the field is asking for rather than the next character in
the chart. If that slips, the player traces one character to kill a monster
carrying another, so `field.test.mjs` tests the wrapper directly rather than
the boot state, which passes either way.

Monsters advance in polar coordinates around the ward, so the geometry is
resolution independent and rotating a tablet changes nothing. Encounter rate
is biased toward glyphs whose mastery has gone quiet — a monster is a
character you are forgetting, which is the spaced-repetition design already
written into the lore.

**Hitodama (v0.1.21)** is the first piece of the economy in play. Every
finished glyph kindles a ghost light (人魂) on its character, and a lit
character throws its own wisp at any monster carrying it, one charge per
cast. The tracer is pointed at the nearest *dark* character, so the hand goes
where the flame is out — which is the spaced-repetition design doing its job
without a schedule. A dash on the seam between field and sketchbook shows the
loaded character and its charge. Keyed by character, kept in localStorage,
and it survives the ward falling. Tuning lives in `field.hitodama*` and
`field.castMs`; see `scripts/PACK.md`.

**The start page (v0.1.24)** opens the game on its two real axes: how much
help (`guided`, `easy`, `medium`, with `hard` locked until its scorer
exists) and what the sign says (`kana`, `romaji`, `gaijin`). Difficulty is
a runtime switch — the penalties became engine state so the shell can
reassign them. `guided` is the "drag the circle" mode a player asked for,
and it is a different objective rather than easy turned down: no ink, no
zaps, no comet, and the only test is that the light reached the end of
every stroke. The light rests on the nearest reachable point, so it sits
under the pen and the stroke closes only when the hand arrives (v0.1.31 —
before that it rested on the farthest, a full tolerance ahead). The comet
that loops the rest of the stroke is off in guided (v0.1.32): it set a
pace, and the hand chased it instead of dragging at its own. Medium draws
the shape as a flat centreline at the ink width, one path per stroke
(v0.1.33 — the tolerance-width band before it was a fifth of the glyph wide
and unreadable as a shape). The field holds still while
the page is up, and the name in the header reopens it.

**The run (v0.1.39)** is the first piece of The Tower in play, which is the
shape the maintainer wants the game to grow into: the ward is the tower, the
farang close from every side, and a lit character already fires by itself.
Single characters take more hits as the waves climb; tracing earns ink (墨),
clean tracing most; and ink buys four upgrades from a strip at the top of the
field, all of which end with the run. See `scripts/PACK.md`.

**A run ends (v0.1.43).** The ward falling was a toast and a field that went
quiet. It is an ending now: a page that says how far, how many, how cleanly,
shows the run's handwriting over the shapes that were asked for, and offers
another go. The run is written to the hand's ledger (the last twenty, and the
furthest wave per realm for good), travels with a signed-in player's save, and
goes to the events table as a `run`. These are the player's record of
themselves, never a score anyone is ranked by.

**DECIDED — you cannot advance without unlocking (v0.1.44).** The
maintainer: "make it impossible to advance without unlocking stuff. so there
needs to be a currency to use after each round". A run in the hiragana game is
a **stage**: a fixed number of farang, carrying only the rows of the chart that
stage has reached (two rows at stage 1, one more each stage — the order the
chart is learned in, so the gate is the curriculum). Hold the ward through all
of them and the stage is cleared, which is the only thing that lets the gate
to the next be bought. It is bought with **魂 tama**, which only a finished run
pays: most for clean traces, half again for holding to the end, less in guided
(it cannot be zapped, so every trace there would count as clean). Tama also
buys what lasts, in the lantern workshop shown where a round ends and where one
begins: 心 hearts, 灯 how many lights a character holds, 硯 ink in hand at the
start. Word decks are not staged — a deck is class content with its own order
— and the workshop page is never gated, so anything can always be practised.

**Guided only gets you so far, and recognisable pays more (v0.1.45).** The
maintainer: "guided play only gets you so far. then the tracing happens. if
your keys are recognizable, you end up with more currency. medium, up the
ante." Any stage can be *played* in any mode and pays; but from stage 3 a stage
is only *held* — only counts toward its gate — at easy or harder, and from
stage 8, at medium. Guided teaches the motion; the chart past its first rows
is earned with ink. Guided itself draws from every row (v0.1.47): holding no
stage past the second, it could never meet half the chart under the gate.
**As of v0.1.50 guided is a sandbox**: it holds no stage at all and pays no
魂. The maintainer, after two sessions of finger data: "guided is a lost cause
for grading ... we leave that in the realm of sandbox practice. guided should
not allow the player to progress the game." The handwriting is still recorded. Every landed trace is scored for how recognisable it is
(`quality()` in the hand: the mean distance between the ink and the shape asked
for, both ways, over the glyph's own size) and pays between half and half
again by that score. Medium pays double.

That score measures tidiness along a path the hand was shown. It is **not**
hard mode's "is this あ?" — order and stroke count are the tracer's business,
and nothing here could tell a confident wrong character from a shaky right one
without the path. It is, though, the distance hard mode will need.

**No balance is stored.** A purse has to merge from two tablets with no server
to arbitrate, and a balance cannot. Each device keeps what *it* earned and
spent as totals that only rise; those merge by max per device; the balance is
the difference of the sums. This is the first piece of the economy, and it is
client-written: fine for a single player's own progress, and exactly the
reason nothing ranked may ever be built on it.

**DECIDED — nothing draws for you.** This is the one rule The Tower does not
have, and the maintainer's words for it were "it is important that we keep
tracing". The idle half of the game is *the characters you charged*: a wisp
only ever flies from a character the hand has written. Every upgrade
multiplies what a trace is worth — how fast its lights are thrown, how many it
kindles, how hard a hit shoves — and none of them lights a character, skips a
kana, or answers a farang whose character is dark.

**DECIDED in direction, not built — the farang grow up.** As the stage climbs
they stop carrying characters and start carrying words, then names, then
sentences. How that plays, as far as it has been thought through:

- *A long farang is answered by your whole arsenal, and the pen goes to the
  holes.* A word is a row of slots. Each slot whose kana you hold lit is
  answered by that kana's own wisp, spending a charge; the hand is only needed
  for the kana that are dark. So a sentence is mostly dissolved by what you
  already know, and what is left for the pen is exactly the characters you are
  forgetting — the spaced-repetition design, scaled up rather than replaced.
  **Built in katakana-game v0.1.3:** lights are kept by character everywhere,
  every kana written in a word lights that kana, and a teal slot in the bubble
  is one your own light will write.
- *In order (built).* The wisp for slot 3 waits for slots 1 and 2. A dark kana at the
  front of a word holds up everything lit behind it, which is the right
  pressure, and it keeps "writing the word" meaning writing it.
- *Common kana drain first.* ん い う ー are in everything, so their charges go
  fastest and they come back to the pen most often. Practice ends up weighted
  by how often the language uses a character, without anyone scheduling it.
- *Names belong to the farang.* They are foreigners; their names are katakana.
  A named farang (マイケル, サラ) is a natural mid-boss, and Thotsakan's
  generals are the named ones at the end of a stage.
- *Sentences are where grammar gets in.* A sentence is words joined by
  particles, and particles are what a learner gets wrong. Proposed, not
  decided: **particles are never thrown for you** — は を に で are always
  blank and always by hand, even when everything else is lit. The arsenal
  handles vocabulary; the hand handles grammar.
- *Row resonance*, as the set bonus: all five of a row lit and that row's
  wisps fly harder. It rewards breadth and teaches the rows, which is the
  DECIDED affinity rule paying out. It must not light a sibling that was not
  traced — that would be a character learned by standing near one that was.

Permanent upgrades between runs, research that ticks in real time (Hanuman's
army), and tiers (Honnō-ji) are the rest of The Tower's loop and the rest of
the economy section below. They are persistent, so they are where
client-authority starts to matter; the run is not, which is why it came first.

**The current single-canvas screen is the workshop, not the game.** Everything
in `dist/hiragana-*.html` today — the gojūon chart, the stroke controls, the
size ladder, the flag button — is the instrument this project uses on itself.
The game does not look like it. That is a deliberate split rather than a
redesign pending: the workshop wants every control visible at once, and the
game wants almost none of them.

**Sketched, not decided:**

- **The stroke is the attack.** Each completed stroke fires along its own
  direction, so the character's shape is the attack pattern and stroke count
  is damage. つ is a jab, き is four shots, の is one long spiral. Stroke
  order becomes tactical as well as pedagogical.
- **You identify, you do not aim.** Draw the kana above a monster's head and
  it hits that monster. The skill under test is reading the sign, and nothing
  is ever chased with the pen — which is what keeps tracing accurate while
  the screen moves.
- **Monsters are the glyphs you are forgetting.** Potency decays; a glyph
  whose flame has gone out comes back as something to fight. Encounter rate
  then follows what actually needs review, and the roster needs no content —
  it is the gojūon. This is the existing spaced-repetition design wearing the
  lore it was already written in.
- ~~**Movement belongs in the gaps.**~~ Superseded by the split screen.
  Monsters move continuously, including while the pen is down. The reason to
  freeze them was that a moving screen fights the hand — but the sketchbook is
  its own fixed rectangle in the bottom third and never moves, so the two
  never compete. Continuous movement is what makes the clock mean anything.

**Open question worth settling early:** is the sign above a monster's head the
kana or the romaji? Kana tests recall of the shape; romaji tests the reading →
shape mapping, which is harder and probably more useful. It may be the
difficulty axis rather than how much guide is shown.

Cast, roughly:

- Hanuman's monkey army is the idle workforce — they gather while you're away.
- Thotsakan and his generals guard the boss provinces (ฒ, ฬ, ฐ, and
  whatever testers find hardest).
- The guide comet is a kodama or a hopping kong koi leading the stroke.
- Zaps are the biters: stray off the path and a phi pop takes a bite.
- A mastered glyph is a tsukumogami — a thing used so long it woke up.
- Prestige is Honnō-ji: Nobunaga never finished. Unify, fall, begin again as
  the next lord with a permanent edge.

All of this is folklore and history. No IP shadow.

Aesthetic: gold on dark lacquer for the Thai realm stays. The shared engine
leans night-forest — cold blue-green wisps against dark — so the ghost
lights read.

---

## The economy (idle-game layer)

Designed, not yet implemented. Ship it stubbed (counters, no polish) in the
first hiragana build.

**Two stats per glyph, never conflated:**

| stat     | behaviour                         | drives                              |
|----------|-----------------------------------|-------------------------------------|
| mastery  | ratchet. Only goes up.            | tolerance tightening, unlocks       |
| potency  | charge. Decays over days.         | idle income, glow brightness        |

Mastery is "you learned it". Potency is "you still remember it". The decay
*is* spaced repetition, dressed as a candle that wants tending. Nobody loses
mastery; a dim glyph just needs a quick re-trace to reignite.

**Loop:**

- Active: a clean trace earns ink. Clean (no zaps) pays more. Mastered glyphs
  pay less per trace, so the game pushes toward new characters rather than
  farming あ.
- Idle: glyphs with potency generate ink while away. Offline gains computed
  from a timestamp on return.
- Spend: ink buys wider tolerance early (training wheels), then cosmetics
  (ink colours, trail effects), then new realms/fonts.
- Prestige (later): reset and re-trace everything at tighter tolerances for a
  permanent multiplier.

**Progression tiers (later):** glyphs → words → sentences. A character traced
inside a word feeds that character's potency. Word tracing is also where Thai
vowel placement and tone-mark stacking finally get practised. A word is a
sequence of glyph recordings laid out with the font's advance widths; no new
stroke format, only a layout step.

**Hard rule:** save data is keyed by **Unicode codepoint**, not grid position
or index. Words, sentences, and future scripts all write to the same
per-character ledger. Save data must have export/import from day one.

---

## Conventions

- **Versioning:** `dist/<script>-vX.Y.Z.html`. Bump on *every* change, even
  one-liners. Stamp the version in `<title>`, the header, the footer and the
  boot toast so a cached build is obvious.
- **Stable links:** `dist/<script>.html` (`vocab.html`, `hiragana.html`,
  `hiragana-game.html`, `katakana-game.html`) is a byte-identical copy of the current versioned
  build, so the Pages URL never changes between releases. Copy it on every
  bump — `run.sh` fails if it is stale. Git stores identical content once,
  so the copy costs nothing.
- **Nothing lives only in browser storage.** Fonts, stroke data, and defaults
  are embedded in the HTML. User progress has export/import.
- **Performance:** no per-frame shadow blur. Cache trails offscreen.
- **Beginner pacing:** comet/guide speed stays slow. Tested with young
  learners; keep it.
- **Aesthetic:** traditional/classic first, modern refinements later. Gold on
  dark lacquer is the Thai theme and stays. The Japanese realms and the title
  screen are **night** as of v0.1.42 — dark, blue for the ink and the thing to
  press, green for whatever is lit or chosen — which is the night-forest this
  file always said the shared engine should lean toward, and the maintainer's
  own colours. Set per pack (`theme`), applied by `build/theme.py` to the
  finished page. **Write new UI in the gold palette**: the table translates
  it, and `theme.test.mjs` fails on any warm colour it has not been told
  about. Warnings (a zap, strayed ink, a fallen ward) stay warm on purpose.
- **Fonts and licences:**
  - Sarabun, Noto Sans Thai Looped, Noto Sans JP, Klee One — SIL OFL, fine
    for commercial use.
  - Kanit — SIL OFL.
  - Avoid commercial Thai foundry families (DB, PSL).
  - KanjiVG stroke data — CC BY-SA 3.0, credit required in-app.
- **Builds are made here and committed here.** A build that exists only as a
  download is not a build yet — `dist/` is the only place one counts. This
  has already cost the project a tracer and two recording sessions.
- **A layer must not reuse an engine name.** Inside a layer's function,
  `let ink` does not replace the engine's `ink`, it hides it from that layer,
  silently, and the stubbed DOM cannot tell. `shadow.test.mjs` reads the
  source for it. It has been a shipped bug twice.
- **Look at a running build before shipping UI.** Headless Chrome is on this
  machine (`google-chrome --headless=new --screenshot`). Switch sharing off
  first (`hito-share` = `0`) or the run lands in the production table.
- **Testing:** the repo is served over HTTPS at https://hito.appwrite.network/
  (Appwrite Sites, redeployed on every push to `main`) and by GitHub Pages at
  https://thesisbytes.github.io/hito/ — open a build there to test on a
  phone or tablet. Secure context matters: `navigator.clipboard` and the
  File System Access API both need it.

---

## Roles

- **Maintainer** — owns the project and decides direction.
- **Thai teacher** — a native speaker who records the official stroke paths.
  Their recordings are the ground truth for Thai; don't second-guess them
  against a font.
- **Letterform artist** — draws the Thai handwriting font in Glyph Forge.
- **Testers** — try builds and find bugs (one caught ink persisting across
  letter transitions). Their feedback counts.

Tone of the project is affectionate and a bit silly. Keep it that way in
comments and UI copy.
