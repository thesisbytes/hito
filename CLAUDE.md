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
    test/size.test.mjs      46 glyphs x 16 sizes, offline
    test/harness.test.mjs   the debug controls actually reach the engine
    test/tail.test.mjs      a stroke's end cannot be skipped, at any size
    test/field.test.mjs     the game loop runs and the tracer seam holds
    shell_field.py          the game shell, appended as a layer
    sync_layer.py           offline outbox, appended as a layer
    test/sync.test.mjs      offline stays offline and nothing is lost
  dist/                built single-file outputs, one per script, versioned
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

### Hiragana — `dist/hiragana-v0.1.27.html`

Playable, and traced end to end without a break. 46 gojūon with KanjiVG
stroke order baked in, Klee One and Noto Sans JP embedded, laid out as a
proper gojūon chart with the ya and wa rows keeping their gaps and ん on its
own row.

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
zaps, a big light, and the only test is that the light reached the end of
every stroke. Medium draws the shape flat at exactly the tolerance width, so
what is shown is the band the scorer forgives. The field holds still while
the page is up, and the name in the header reopens it.

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
  one-liners. Stamp the version in `<title>`, the header, and the boot toast
  so a cached build is obvious.
- **Nothing lives only in browser storage.** Fonts, stroke data, and defaults
  are embedded in the HTML. User progress has export/import.
- **Performance:** no per-frame shadow blur. Cache trails offscreen.
- **Beginner pacing:** comet/guide speed stays slow. Tested with young
  learners; keep it.
- **Aesthetic:** traditional/classic first, modern refinements later. Gold on
  dark lacquer is the Thai theme; hiragana may share it or get its own.
- **Fonts and licences:**
  - Sarabun, Noto Sans Thai Looped, Noto Sans JP, Klee One — SIL OFL, fine
    for commercial use.
  - Kanit — SIL OFL.
  - Avoid commercial Thai foundry families (DB, PSL).
  - KanjiVG stroke data — CC BY-SA 3.0, credit required in-app.
- **Builds are made here and committed here.** A build that exists only as a
  download is not a build yet — `dist/` is the only place one counts. This
  has already cost the project a tracer and two recording sessions.
- **Testing:** GitHub Pages serves `dist/` over HTTPS at
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
