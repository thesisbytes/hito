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
  NOTES.md             running log / open questions (append, don't rewrite)
  scripts/
    thai/              glyph list, teacher's stroke recordings, theme, font refs
    hiragana/          glyph list, KanjiVG-derived strokes, font refs
  fonts/               source .woff2 files (embedded as base64 at build time)
  glyph-forge/         handwriting capture tool (separate app, same aesthetic)
  build/               stitch script: engine + one script pack -> single HTML
  dist/                built single-file outputs, one per script, versioned
```

Single-file HTML with zero external dependencies is a deliberate constraint.
Every deliverable must open from a double-click, offline, on a tablet.

---

## Where things stand (Aug 2026)

### Thai tracer — `dist/thai-v0.9.3.html` (last known build)

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
the project's native Thai teacher did not survive — nothing usable exists in
the repo today, and no recording JSON has ever been committed. The loss point
each time was non-persistent browser storage, so the fix is at the export
step, not the capture step: a recording must become a file on disk the
moment it is made. Nothing may ever again exist only in browser storage.

Recording requires the built HTML (teacher mode lives inside it), so this is
blocked on getting a build into `dist/`.

### Glyph Forge — `glyph-forge/`

Capture tool for hand-drawing original Thai letterforms on a pen display
(pressure disabled at driver level, uniform stroke width). Same gold-on-lacquer
look. Exports 1024×1024 black-on-white PNGs named by codepoint (AGL style,
`uni0E01.png`) in a ZIP built with a hand-rolled writer, plus `metadata.json`
with baseline / body-top pixel positions. Covers all 80 Thai glyphs (44
consonants, vowel signs, tone marks, thanthakhat, numerals).

Next step, once the letterforms are done: a FontForge script that imports the PNGs and
places combining-mark anchors so tone marks stack correctly.

### Hiragana — not yet built

First build target: `dist/hiragana-v0.1.0.html`. See "Hiragana plan" below.

---

## Hiragana plan (first build)

Scope: the 46 gojūon only. No dakuten, handakuten, or yōon yet.
Glyph list with row/order/romaji is in `scripts/hiragana/glyphs.json`.

**The hook problem.** Print Gothic fonts join strokes that handwriting keeps
separate (き, さ, ふ, り are the obvious ones — see `hookNote` fields).
Learners who trace a print font learn wrong shapes. So:

- **Trace font:** Klee One (SIL OFL). Textbook-style, separated hooks.
- **Print font:** Noto Sans JP (SIL OFL). Shown small beside the trace glyph
  so the learner sees what the character looks like in the wild.
- **Stroke data:** KanjiVG (CC BY-SA 3.0). Has official stroke-order SVGs for
  all kana. Convert each stroke path to the same point-array format the Thai
  recordings use and bake them in as the default book. Recording mode stays
  available so contributors can override any stroke. KanjiVG requires a credit
  line in the app footer.
- **Layout:** 5×10 gojūon grid replaces the Thai consonant list.
- **Engine:** unchanged. Zap, scoring, trail caching, mastery all carry over.

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
