# Notes

Running log. Append at the bottom, don't rewrite history.

## 2026-08-25
- Repo seeded from the design chat. Engine named Hito (人).
- Decided: two per-glyph stats, mastery (ratchet) and potency (decays).
- Decided: save data keyed by codepoint.
- Decided: lore frame is unification (Nobunaga / Ramakien) over a haunted wild (phi / yokai). Not in the first build.
- ~~Open: the teacher's v0.9.2 recording JSON still needs baking into the Thai build.~~ RESOLVED: no such JSON ever existed — see the window.storage entry below.
- ~~Open: where does the last Thai build actually live?~~ RESOLVED: recovered, committed, and superseded by dist/thai-v0.9.4.html.
- Repo published: github.com/thesisbytes/hito (public). Personal names replaced with roles before pushing; unscrubbed brief kept locally as CLAUDE.local.md (gitignored).
- Correction: the 44 Thai consonants are NOT recorded. CLAUDE.md claimed the v0.9.2 session was complete and only needed baking in; that was wrong. No recording JSON has ever been committed. CLAUDE.md updated.
- Recording is blocked on the build — teacher mode lives inside the Thai HTML, so nothing can be captured until a build lands in dist/.
- ~~Open: replace the export-JSON button with a per-character save to disk.~~ MOVED: recording now happens in the Nira Thai dashboard and persists server-side. See the KhienThai repo.
- Pages enabled: https://thesisbytes.github.io/hito/ — builds will be at /hito/dist/<file>.html
- Removed the custom domain from thesisbytes.github.io (it was parked on a stub page). Project pages had been inheriting it and serving over plain HTTP, which breaks navigator.clipboard — the recording mode's Copy button needs a secure context. github.io gives HTTPS automatically.
- Added .nojekyll so Pages serves the single-file builds byte-for-byte instead of running them through Jekyll.
- Decided: record on desktop (File System Access API can write straight into the repo folder; Android has no equivalent), trace and test on the phone via Pages.
- v0.9.3 committed to dist/. [CORRECTED — the original entry here claimed the build had no embedded fonts and fetched one from nirathai.com at runtime. Both were wrong; see the correction entry below. Left rewritten rather than struck through so nobody acts on the false version.] The build is a correct single-file bundle: Sarabun, Kanit and Noto Sans Thai Looped are all embedded as base64 woff2, and the one nirathai.com font line is commented out.
- Priority: hiragana first. Thai is bottlenecked on instructor availability; hiragana is not bottlenecked at all, since KanjiVG supplies stroke order for all 46 gojuon.
- Correction to the v0.9.3 assessment above: the build DOES embed its fonts. All three decode to valid woff2 (Sarabun 9,188 B, Kanit 6,336 B, Noto Looped 10,468 B). They are loaded with `new FontFace(buffer)` from decoded base64 rather than a CSS @font-face rule or a data: URI, which is why grepping for @font-face and data:font found nothing and led to the wrong conclusion. The nirathai.com/fonts/kru-hand.woff2 line is commented out and never fetched. v0.9.3 opens offline with no external dependency, as designed.
- Lesson: check how a thing is loaded before concluding it is missing. `new FontFace()` is invisible to a CSS-shaped grep.
- Real (small) bug found in v0.9.3: APP_VERSION='0.9.0' while the title and boot toast both say 0.9.3, so the header badge shows the wrong version. CLAUDE.md's convention wants title, header and toast to agree.
- ROOT CAUSE of the lost recording sessions, found while forking the engine: `window.storage` is called 8 times and defined nowhere. It is not a browser API. Every call sits behind `if(window.storage)`, so persist/restore/persistM/restoreM are all silent no-ops in an ordinary browser — and saveCurrent() toasts "saved ✓" unconditionally, because persist() is fire-and-forget with no error path. The teacher recorded 44 consonants, saw a success message every time, and nothing was ever written. This was never a browser-settings problem or user error.
- The engine was presumably developed somewhere that injects window.storage, so it worked in preview and failed everywhere else. Anything relying on an ambient host API needs a fallback in the file itself, or it is not really a single-file build.
- Fixed in hiragana v0.1.0 via build/stitch.py: a real localStorage-backed window.storage, and a save that reports failure instead of always claiming success. The Thai build still has the bug — do not run a recording session on thai-v0.9.3.html.
- Built dist/hiragana-v0.1.0.html (427 KB): 46 gojuon, KanjiVG strokes baked in as the default book, Klee One + Noto Sans JP embedded, 5-column chart with ya/wa gaps preserved and ん on its own row. Verified: no Thai left, no nirathai references, no external URLs, both script blocks pass node --check, no grid collisions, every glyph has stroke data.
- build/stitch.py is the reusable path: engine + pack dir -> single HTML, with every substitution checked so a moved anchor fails the build instead of silently emitting the previous script.
- Baked KanjiVG (release r20250816) into scripts/hiragana/strokes.json via build/kanjivg_to_strokes.py. All 46 gojuon, 9311 points, 366 KB. Shape matches what teacher mode writes — TEACHER.fonts[<font>].letters[<char>].strokes = [[{x,y,p,t}]] — so it can be dropped in as the default book with no engine change.
- Verified: all 46 stroke counts match canonical textbook counts; all points inside 0..1; timestamps monotonic; no degenerate strokes.
- All 8 flagged hook characters came through correctly. そ looked like a miss at first — KanjiVG gives it as one stroke while the hookNote claimed a two-stroke textbook form — but the one-stroke form is what's taught in class, so KanjiVG is right and the note was wrong. hookNote dropped from そ; it isn't a print-vs-handwriting divergence at all. Both forms of そ exist in the wild; the curriculum here uses one stroke.
- Synthetic values in the conversion: p is always 1.0 (uniform width) and t is derived from arc length at a constant 0.7 units/sec, so the guide comet paces evenly. PEN_SPEED and SPACING are the tuning knobs in the script.
- strokes.json is a derivative of KanjiVG, which is CC BY-SA 3.0 — share-alike applies to that file, and attribution is required in the app footer.
- Consolidated to a single workspace. The design-chat / Claude Code split is retired: design, engine, builds, and commits all happen in this repo. CLAUDE.md's opening section and handoff convention rewritten to match; the "don't redesign the engine here" rule is gone, since there is no longer anywhere else to do it.
- ThaiVG idea: no open Thai stroke-order dataset exists. Searched twice — CJK is well covered (KanjiVG, Make Me a Hanzi, animCJK, strokesvg), Thai has only clipart and OCR training sets, nothing with ordered stroke centrelines per codepoint. The gap is real; the scarce input is a native expert willing to record, not the format.
- Decided: ThaiVG becomes its own project. hito consumes it as a dependency, exactly as it consumes KanjiVG for hiragana. That inverts the current Thai plan — the SVG dataset becomes the source of truth and strokes.json becomes a derived, regenerable artifact.
- Round-trip validated with zero instructor time: build/strokes_to_svg.py fits cubic Beziers (Schneider's algorithm) to point arrays and emits KanjiVG-shaped SVG. Ran KanjiVG -> points -> SVG over all 46 kana and compared against the originals. Max deviation 0.428 canvas units (0.39% of glyph width), mean 0.056, and every stroke count preserved. The record -> SVG path is proven before anyone sits down.
- Tolerance sweep (maxdev / curves vs KanjiVG's hand-authored 390): 0.15 -> 0.39/2.25x, 0.35 -> 0.43/1.64x, 0.6 -> 0.55/1.34x, 1.0 -> 0.95/1.17x, 1.6 -> 1.65/0.86x. ~0.6 looks like the sweet spot for the dataset.
- Worth knowing: fidelity below tolerance 0.35 stops improving because the floor is set by input point spacing (SPACING=0.01 in kanjivg_to_strokes.py), not by the fitting. For real recordings the floor is the device sample rate instead — so capture density matters more than fitting tolerance.
- Thai needs one thing KanjiVG has no concept of: combining marks. Vowels and tone marks stack above/below and attach before/after the base consonant, so ThaiVG needs anchor metadata that KanjiVG never needed. That is the genuinely novel design work.
- Thai codepoints (U+0E00-U+0E7F) fit KanjiVG's 5-hex-digit filename scheme unchanged: ก is 00e01.svg.
- Scaffolded /home/moopha/project-khienthai with a CLAUDE.md brief for whoever builds it, plus tools/strokes_to_svg.py and a format example. Not a git repo yet — waiting on name, visibility and licence, which all need deciding before the first publish rather than after.
- The ThaiVG brief carries forward the two hazards this project learned today: never trust an on-screen "saved" message without verifying persistence, and write each glyph to disk as it is finished rather than in one export at the end.
- Named the Thai dataset project KhienThai (เขียนไทย, "write Thai") rather than ThaiVG. VG just means Vector Graphics; naming it after the act of writing beats naming it after a file format, and it stops the project borrowing KanjiVG's identity. Tagline carries the compatibility signal instead: "Thai stroke order data, in KanjiVG format."
- Khien is a deliberate blend — kh from RTGS for the aspirated consonant, ien for English readability. Standard RTGS would be khian. Worth confirming with a native reader before publishing, since it is permanent afterwards.
- SVG id prefix is now kt: (KhienThai), the analogue of KanjiVG's kvg:. Renamed throughout, including build/strokes_to_svg.py here.
- Checked: no software or dataset uses either spelling. Nearest hit is an unrelated construction firm in Da Nang.
- KhienThai pushed: github.com/thesisbytes/khienthai (private). Private and licence-less on purpose — visibility flips with one command, a licence does not, so nothing is published under any terms until that is chosen.
- Shipped dist/thai-v0.9.4.html: window.storage shim, save that reports failure instead of always toasting success, and the three version stamps finally agreeing (APP_VERSION was 0.9.0 while title and toast said 0.9.3). 23 lines changed, everything else byte-identical to v0.9.3.
- Deleted dist/thai-v0.9.3.html. It silently destroys recordings while reporting success, and keeping a superseded data-eating build publicly linkable is a hazard, not an archive. Git history retains it.
- build/fix_persistence.py applies the persistence fix to any pre-existing build, separate from stitch.py which builds a new one from a pack.
- Caught while verifying: sub() replaces via a lambda, so regex backreferences never expand and the title became a literal \g<1>. The verify-every-substitution habit is what surfaced it before it shipped.
- KhienThai handed off to a separate worker. Repo github.com/thesisbytes/khienthai (private) is clean and self-describing: CLAUDE.md carries the format spec, the open combining-mark design, a state-of-play table, setup and command reference. Built there today: the capture module (TS, unit-tested, Kamvas-targeted), the calibration page, and a 12-font guide library with OFL licences.
- Decided there: one canonical form per character (the font she teaches with), variant naming reserved but not built. Recording UI will live in the Nira Thai admin dashboard; KhienThai keeps the dataset and the capture module. Dependency runs one way — KhienThai knows nothing about hito or Nira Thai.
- Still open on KhienThai: licence, visibility, the combining-mark spec, and her guide-font pick. None of them block hito.
- Guide/shadow misalignment reported and measured. Two separate causes, one fixed each way.
- (1) Scale: KanjiVG coords were normalised to the full canvas, but the engine stores teacher strokes in the space of the glyph as the font renders it — BASE_F of canvas height, textBaseline anchored, nudged 0.06 font sizes down. Guide came out 1.44x too large. Thai never hit this because its recordings were captured by tracing the rendered glyph. Fixed in kanjivg_to_strokes.py (v0.1.1).
- (2) Shape: even after aligning, only 55.9% of stroke points landed inside Klee One's ink. Grid-searched every scale and offset — the ceiling is 65.5%, so the rest is a genuine letterform difference. KanjiVG's centrelines describe KanjiVG's shapes, not Klee One's, and hooks diverge most. Not fixable by transform.
- Fix for (2): the shadow is now drawn from the stroke data instead of the font (v0.1.2, pack flag shadowFromStrokes). Guide and target come from one source, so they cannot disagree. The font shadow remains for record mode and for glyphs with no recording.
- Checked and harmless: computeGlyphMask builds the zap boundary from the font, but load() only calls it when there are no teacher strokes, and outsideGlyph is only reached on that same branch. The stale boot mask is never consulted in practice with a recording present.
- stitch.py's sub() replaces literally, so regex backreferences never expand. Tripped over this twice today; the shadow-scale substitution now reads the value out first. Also lost an edit to a trailing space in a search string — the edit silently no-opped and the build still reported success, which is why the output gets verified rather than the log trusted.
- Feedback: shadow + glowing trail together read as blurry, and the animation appeared to miss spots. Cause: a thick shadow (scale 2.4, ~38px) bulges on the outside of curves, so the thin trail running down its centreline cannot cover the bulge — and the stacked glows mush together.
- v0.1.3 makes the target presentation a pack setting: shadow = none | strokes | font. Default is now 'none' — only the trail (road ahead, dots, and the stroke already made), which is what the follow dot rides on. The completion flare still paints the full path.
- The debug build cycles all three live so they can be compared on one glyph instead of across deploys.
- Reported: the dot sometimes misleads, and a missed stroke still dinged complete. Same root cause — follow() searched prog..prog+LOOK (24) and kept any jump via prog=max(prog,best), so one lucky touch 24 points ahead skipped everything between. Enough leaps reached the end without tracing the middle, and the dot teleported on the way. SEGEND also auto-advanced, so one unbroken line satisfied a four-stroke glyph.
- v0.1.4 strict following: the progress search is clamped to the current stroke; coverage is recorded separately by sweeping the whole stroke (a hook curling back within LOOK would otherwise let prog leap past unmarked points); crossing a stroke boundary needs a real pen lift; completion needs coverage >= 85% rather than merely arriving at the last index.
- Added a travel-ratio check after finding 11 single-stroke glyphs still leaked (く し そ つ て の ひ へ る ろ ん). With one segment there is no lift barrier, and a dense scribble satisfies both progress and coverage. Distance travelled is what a scribble cannot disguise: an honest trace runs ~1.0x the path length, scribbles 30-120x. Cap is 2.5x.
- Travel accumulates only above TRAVEL_EPS (0.006) — summing raw samples would let digitizer noise inflate the ratio and fail an honest trace. Found because a test with per-sample white noise failed all 46; real wobble is smooth and correlated, and the test model was wrong before the algorithm was.
- Also fixed: reaching the end of a stroke set awaitLift while the pen was still finishing it, so correct strokes got zapped at their own end. Overshoot within 1.6x R_ON of the endpoint is now treated as finishing, not as running on.
- build/test/scoring.test.mjs exercises all of it offline: 46/46 correct traces conjure, 0/46 scribbles get through, and skipped strokes, wrong order, and unbroken lines are all rejected.
- Reported: せ at mastery level 4 is impossible. Cause is the difficulty curve compounding. Each level shrank the glyph 12% AND tightened tolerance in the same proportion, so both moved together — but a hand's precision does not shrink with the target. On a phone the finger contact stays the same size while the glyph halves, and by level 4 the finger covers what it is meant to trace.
- v0.1.5: shrink slowed to 7% per level with a 32% floor, and tolerance now falls with sqrt(scale) rather than scale, floored at 0.045. At level 4 that is a 46% glyph with 22px tolerance on a 360px canvas, against 37% and 15px before. Simulated pass rate at +/-20px hand error goes 63% -> 93% at level 4 and 40% -> 78% at level 6.
- Worth noting the simulations were consistently more optimistic than the hand: a faithful trace passed at every level, and even +/-14px absolute error passed. The model does not capture finger occlusion of a small target, which is probably the dominant effect. Trust the hand over the model here.
- Debug build gains mastery controls (level up/down, reset all). A glyph that becomes unpassable was also untestable, since nothing could take it back down.
- Longer-term thought, not implemented: difficulty that comes from showing less (fading the guide, hiding the dots) rather than from shrinking geometry would not fight the input device.
- Whole set traced with no breaks — strict scoring and the softened curve both hold up in the hand.
- v0.1.6 sequential reveal: the trail and comet show only the stroke being worked on. Strokes already made stay lit, the current one is drawn by the pen, later ones have not caught light yet. Finishing a stroke throws sparks along its length and buzzes, then the guide moves to the next stroke's start, so a lift is answered by an invitation rather than a repeat.
- Caught before shipping: _gi was read in the trail-cache check one line above its own const declaration — a temporal dead zone ReferenceError that would have fired every animation frame and killed the guide. node --check accepts it happily; it is a runtime fault, not a syntax one.
- Added build/test/smoke.test.mjs: runs a built engine in a stubbed DOM and drives animation frames. All five builds pass. This is the class of bug syntax checking cannot see.

## 2026-08-26 — cleanup
- Tracked build/engine.html. It had been gitignored as "recoverable from history", but it is the source every build comes from — a fresh clone could not build without it.
- Untracked build/__pycache__ and rewrote .gitignore. Note gitignore has no trailing-comment syntax: `CLAUDE.local.md  # note` matches a filename containing the comment, which silently unignored two files.
- README claimed Thai had "stroke paths recorded by a native teacher". Nothing has ever been recorded. Replaced with a state table and a link to the playable build.
- Added scripts/PACK.md — the pack format had grown to eight tracing and difficulty options with no documentation anywhere.
- Added build/test/run.sh: scoring tests, a stubbed-DOM smoke run over every build, and a check that the committed build rebuilds byte-identical from source. All pass.
- Resolved the three stale "Open" items at the top of this log.
- v0.1.7 difficulty modes: easy (path, dots, comet, numbered stroke badge), medium (shape only), hard (nothing). One `mode` key in the pack sets all three renderers; the debug build cycles them live.
- label() has drawn numbered stroke badges since the start but only ever in record mode. A learner on easy is mostly trying to recall stroke order, so the number of the stroke about to be drawn is now shown. Free feature that was already written.
- Hard mode drafted in CLAUDE.md rather than built — nobody here can freehand kana yet, so it could not be verified, and shipping an unverifiable scorer is how the last three bugs happened.
- Key finding for that plan: compare(u,t) already exists in the engine and is never called. It does per-stroke shape comparison with reversed-direction detection and human-readable failure reasons. Hard mode is verification against a known reference, not recognition over an open set — a recogniser would rediscover what strokes.json already states, and porting one (WASM, tf.js, cloud) would break the single-file offline constraint.
- Game-dynamics discussion cached into CLAUDE.md's lore section. Two decisions recorded because they constrain the data model: affinities map to gojuon structure rather than invented elements (glyphs.json already carries `row`, and structural affinity stops a player min-maxing away from the characters they are weakest at), and the hero cannot read (their ignorance is the player's; a scribe would contradict the play experience).
- Sketched but not decided: stroke-as-projectile with stroke count as damage, targeting by identifying rather than aiming, monsters as glyphs whose potency has decayed, and movement confined to the gaps between strokes.
- Open: whether the sign above a monster is the kana or the romaji. That may be the real difficulty axis rather than how much guide is shown.
- Feedback from paper practice: graph paper made length and position judgeable. The canvas had no reference frame at all — a stroke floating in empty space gives nothing to measure against.
- v0.1.8 adds a practice grid: the glyph's own em box with a dashed centre cross, optional quarter lines. Derived from the same transform the stroke data was baked with, so it frames the strokes with even margins (0.071-0.080 on all four sides) and means the same thing on every character. Shrinks with mastery.
- Deliberately independent of difficulty mode: a grid says where the box is, never what to draw, so it stays useful in medium and hard without giving anything away.
- Confirmed the grid shrinks with the glyph: gridBox() uses curF (mastery-scaled), not BASE_F. Verified across levels 0-20 — strokes stay inside the box and the margin holds at a constant 11.5% of glyph size rather than a fixed canvas distance.
- Added build/test/alignment.test.mjs. Stroke data, rendered glyph and grid all have to agree at every mastery level, and they have silently disagreed twice already: KanjiVG coordinates normalised to the canvas instead of the glyph box (guide 1.44x too large), and the grid being pinnable to BASE_F instead of curF. Now it is a check rather than something somebody remembered to look at.
- Bug reported from play: a stroke completed without its hook and advanced to the next. Cause was mine — stroke completion fired at prog >= seg[1] - END_SLACK, an absolute count of 4 path points, and the hook is the tail of a stroke. The next line then marked the skipped points as hit, so coverage could not catch it either. That fudge existed to tolerate sparse sampling and it forgave exactly the thing that matters.
- It worsened as glyphs shrank, which is what made it noticeable: path points scale with stroke length, so four points was 31% of the shortest stroke at level 0 and 67% by level 12.
- v0.1.9 adds a distance test alongside the index slack. The index says the stroke was traversed and still tolerates a sparse sample landing short; the distance says the pen actually arrived at the endpoint. A distance is scale-invariant, an index count is not. The hit-marking fudge is gone.
- Measured across き さ り お: cutting 10% or more off a stroke's tail is now rejected, 5% is still forgiven (a few pixels, right for a human endpoint). Was 31-67%.
- Scoring tests now cut tails proportionally rather than by fixed point count, since an absolute count means something different on a long stroke than a short one, and different again once mastery shrinks the glyph.
- Reported: around level 5 some glyphs (su and others) became impossible, but toggling to level 6 fixed them. Non-monotonic, which was the clue — if it were difficulty, 6 would be worse than 5.
- It was not the level. fizzle() reset smudge, offCount, prog, segIdx, awaitLift and hit, but not travel. Only load() did. So travel carried across fizzles: one bad attempt pushed travel/PATHLEN past MAX_TRAVEL, and every later attempt was rejected for wandering it had not done. Two failed attempts and the glyph was permanently unpassable. Toggling the level called load(), which cleared it — the level change was incidental.
- Surfaced around level 5 because that is where strays get frequent enough to fizzle once, and PATHLEN shrinks with the glyph so the ratio climbs faster at small sizes.
- Simulated a perfect trace at levels 0-9 for su, ki, a and nu first: all pass, everything monotonic. That ruled out the difficulty curve and pointed at state rather than scoring.
- Added build/test/state.test.mjs: fizzle() must clear every per-attempt accumulator, since it restarts an attempt. Checks the class, not just travel. Confirmed it fails the v0.1.9 build and passes v0.1.10.
- Level 6 still failing after the travel fix. Simulated overshoot past stroke ends, hand error to +/-14px, drain and fizzle, across levels 0-8: everything passed. That is the third time a simulation has been more forgiving than the hand — the model is not capturing whatever actually happens, so stop modelling and measure.
- v0.1.11 extends the telemetry to record what a bug report cannot: mastery level at the time, fizzle count, coverage at the moment of the outcome, and the engine's own toast text. The difference between "missed 40% of the path" and "too much wandering" identifies which check is rejecting the attempt, and neither is visible from outside.

## 2026-08-31 — size as its own axis
- Asked for: a random-size game mode, a way to loop through sizes to see which fail, and a button to flag which hiragana fails at what size. Built all three, plus the offline sweep that had to come first.
- Size used to be a pure function of mastery — `curF=glyphF(letter)` — so the only way to change it was to change the level. That is precisely why the level-6 report resisted three releases: nothing could tell "this size is too small" apart from "this level is broken", and toggling the level to test it also called load(), which cleared the state that was actually at fault.
- v0.1.12 puts one seam in: `sizeFor()`, intercepting the single line where curF is set. Everything scale-dependent (tolerance, grid, shadow, the stroke transform) already derives from curF, so pinning it there moves all of them together and cannot leave one behind. SIZE_PIN outranks everything; random mode draws per glyph; mastery still counts, and no longer sets the size.
- Pack keys `sizeMode` and `sizeRange`. Hiragana ships `random` over [0.32, 0.62].
- build/test/size.test.mjs sweeps 46 glyphs × 16 sizes offline. The point of it was to fix the modelling error the log keeps recording: the earlier simulations built the pen path by scaling the ideal path, so the simulated hand shrank with the target and travel/PATHLEN came out constant *by construction*. Sample spacing and wobble amplitude are now held constant in pixels, which is what actually happens.
- Result, and it is a negative one: the scoring is not what makes small glyphs hard. Travel ratio is flat across the whole range (1.06x → 1.01x against a 2.5x cap), because smooth wobble at a fixed spatial frequency adds arc length in proportion to path length. The hand budget — the largest stray that still passes — holds at ~32px while the glyph goes 223px → 115px. Tolerance falls 25px → 18px in absolute terms but *rises* 11.3% → 15.7% relative to the glyph, so the sqrt curve is doing what it was built to do.
- So the difficulty curve and the scorer are both cleared. Whatever makes level 6 impossible is not in them — occlusion of a small target by the hand is the standing suspect, and no model here can see it. That is the fourth time the simulation has been more forgiving than the hand, and it is now recorded in the test itself rather than in someone's memory.
- The in-hand harness is therefore the instrument, not the simulation. Debug build gains a size row (◀ − size ▶ +), a pin that survives glyph navigation so the alphabet can be walked at one fixed size, and a `✗ fails here` button. A fizzle is one bad attempt; "impossible here" is a judgement only the hand can make, so it gets a button rather than an inference.
- The flag captures size, glyph, mastery level, coverage, travel ratio, progress, stroke index, attempts, the engine's own toast and the difficulty mode — enough to separate the three suspects (curve / stroke data / state) at the moment the hand says no. Flags persist to localStorage, since a sweep spans sessions, and `__hito.matrix()` renders the glyph × size grid on the tablet without exporting first.
- Found while building it: instrument.py injected its layer as a re.sub *replacement string*, which expands escapes — the first `\n` in the layer (a `join('\n')`) became a real newline and broke the line it sat in. stitch.py had already learned this and replaces through a lambda; instrument.py never did. Third time this project has been bitten by re.sub replacement semantics.
- build/test/harness.test.mjs is new because smoke.test.mjs cannot catch that class of failure: it runs each <script> in its own `new Function` scope, so the telemetry layer never sees the engine's top-level `let` bindings there, and every read in the layer is inside a try/catch — a layer that touched nothing would still pass smoke. The new rig concatenates the blocks the way a browser shares scope between classic scripts, then drives the controls and checks the engine actually moved.
- Mutation-tested it rather than trusting a green line: a pin that silently does nothing, a random mode collapsed to a constant, and flags that stop persisting are each caught. A harness that reports success while doing nothing would make every sweep result a lie, and this project has shipped exactly that bug before.
- Open, and worth deciding before the economy work: under a flat random range, conjuring no longer visibly does anything — mastery increments a counter and nothing on screen changes. The progression has to reattach to something, and CLAUDE.md's economy layer is the obvious candidate.

## 2026-08-31 — the tail fix, from three flags
- Three flags came back from the hand: ぬ, pinned at the 0.32 floor, 113px glyph on a 353px canvas. Two were practice presses (coverage 0 and 0.164); the third was the report — "it passes me before I could complete the entire stroke".
- The harness worked end to end, and for the first time a simulation agreed with the hand: reconstructing a trace that stops where flag 3 stopped, at an 8px wobble, gives coverage 0.906 — the recorded value to three decimals. Every previous simulation here has been more forgiving than the hand; this one is not, because it was rebuilt to hold sample spacing and wobble constant in pixels.
- At the flagged instant the pen was at path point 96 of 128, with 88px of the second stroke untraced but only 16.6px straight-line from that stroke's endpoint — ぬ's loop curls back, so arc distance and straight-line distance disagree badly. The completion radius was 17.8px. The pen was already inside it.
- The final conjure did not actually fire there: prog was 96 against a required 123, so the index slack held the gate. But the *stroke* gate is what the report was about, and that one was genuinely loose.
- Measured properly: how much of a stroke had to be drawn before the engine called it finished. き stroke 1 went 85% at full size to 69% at the floor; き stroke 4 and あ stroke 1 the same shape; う stroke 1 bottomed out at 58%. 87 of 104 strokes forgave more than 20% of their tail somewhere in the size range.
- Cause is one level up from the v0.1.9 bug, and the same shape. v0.1.9 replaced a fixed index count with a distance test because four points meant a different arc length on every stroke — but the distance was a fixed *radius*, which is the same pixels on a 300px stroke and a 21px one. It was measured at full size only. As the glyph shrinks the radius eats a growing fraction of every short stroke. NOTES said at the time "a distance is scale-invariant, an index count is not"; the missing word is that neither is measured against the stroke's own length, which is the only frame that matters for a tail.
- v0.1.13: endpoint forgiveness is now `max(END_MIN, min(R_ON(), TAIL_FRAC * strokeLength))`, and the index slack is a proportion of the stroke's point count rather than a flat 4. Proportional above an absolute floor, absolute below it, never looser than the general tolerance. The floor exists because shrinking the target and the tolerance in lockstep is exactly what made level 4 unpassable in v0.1.5 — that mistake does not get made twice.
- Result: every stroke now needs at least 84% drawn at every size, drifting at most 6% between the largest glyph and the smallest. Was 58-95% and drifting up to 18%.
- Pack keys `tailFraction` (0.12) and `minEndTolerance` (0.02).
- build/test/tail.test.mjs measures the fraction of each stroke that must be drawn, at three sizes, and fails on either a stroke that forgives more than 20% or a drift over 10% across sizes. It models the flat-radius behaviour when a build predates the fix, so the same measurement runs on both and the regression reads as a number rather than a missing constant.
- Still open, and it is a playability question rather than a scoring one: at the 0.32 floor, お stroke 3 and や stroke 2 are 20px long on a 113px glyph, and 13 of 104 strokes are shorter than twice the endpoint radius. The scoring now handles them, but whether a hand can trace a 20px stroke on a touchscreen is not something any model here can answer. Pin 0.32 and try お and や. If they are not playable the fix is raising the bottom of `sizeRange`, not loosening the scorer again.
- Recorded the game's layout in CLAUDE.md: input in the bottom third, the field in the top two thirds, monsters advancing toward a protected centre with the sign in a speech bubble, upgrade tabs later. The current single-canvas screen is the workshop and stays that way.

## 2026-08-31 — the game shell
- Decided: `shell` is a pack key, one engine. The alternative was a second engine file, which would have put the scoring in two places or required extracting it first — and the extraction is the actual work. A flag keeps every scoring fix flowing to both builds automatically.
- Corrected on pacing, and the correction was right. The old note said "movement belongs in the gaps" — monsters freeze once the pen is down, because a moving screen fights the hand. That reasoning does not survive the split screen: the sketchbook is its own fixed rectangle in the bottom third and never scrolls, scales or reflows, so the field can march continuously without ever competing with the pen. Struck through in CLAUDE.md rather than deleted, since the reasoning is what changed.
- v0.1.14 builds two files from one pack directory. stitch.py now accepts a `.json` file as well as a directory, so `scripts/hiragana/game.json` is `pack.json` plus a shell and the 400KB stroke book is shared. Duplicating a pack to change one key is how two builds drift apart without anyone noticing.
- build/shell_field.py is appended as a layer, the way instrument.py is, rather than woven in with substitutions. Twenty new anchored regexes against a 436-line engine would have been fragile, and the layer only needs globals the engine already exposes. The tracer stays the single authority on what counts as a correct glyph — the game has no copy of the scoring to disagree with.
- The seam is load(). The field wraps it so every load the engine starts on its own — conjure()'s delayed advance, clear, a mode change — lands on the field's target instead of the next character in the chart. Get that wrong and the player traces one character to kill a monster carrying another.
- Which is exactly what the first version of the field test failed to catch. It asserted idx === target.i after boot, and that passes either way, because retarget() calls the unwrapped _load directly. Removing the redirect entirely left the test green. It now calls load() with a deliberately wrong index and checks where it lands.
- Two rig bugs surfaced, both the same shape as the instrument.py one, both hiding real failures. smoke.test.mjs ran each <script> in its own `new Function` scope, so an appended layer never saw the engine's top-level let/const — the exact thing a layer exists to use. And function declarations inside `new Function` do not land on window the way a classic script's do, so `window.load` was undefined and every wrapper wrapped nothing. Both rigs now concatenate the blocks and bridge the declarations, which is what a browser actually does.
- That means the old smoke runs were weaker than they read. A layer that touched nothing would have passed all of them.
- Field mechanics: monsters advance in polar coordinates around the ward, so the geometry is resolution independent and rotating the tablet changes nothing. Encounter rate biases toward glyphs whose mastery has gone quiet — a monster is a character you are forgetting, which is the spaced-repetition design the lore was already written around. Completing a glyph launches it at the target; a monster that reaches the centre costs a ward pip; five pips and the run ends.
- Not built, deliberately: upgrade tabs, damage above 1, and identification proper (choosing which of several monsters to answer). The last one needs a mode with no guide, because with the guide up the tracer has already given away the answer.

## 2026-08-31 — the sketchbook has to be square
- Reported straight away: the drawing canvas is stretched into a rectangle in the game shell. It is not a style problem. norm() divides x by W and y by H independently (engine.html:183), so the tracer has always assumed a square stage — every distance in normalised space is only isotropic while W equals H.
- On a rectangular stage the glyph stretches *and* the scoring skews with it: tolerance, coverage radius and travel ratio stop meaning one thing. At the 760x250 the field shell was producing, the pen was forgiven about three times as much sideways as vertically.
- Mine, and introduced by the shell: `body.field .stage` set `aspect-ratio:auto` to fill the bottom third. The engine's assumption was implicit and undocumented, so nothing objected.
- v0.1.15 sizes the sketchbook as an explicit square, `min(96vw, 34dvh)` on both axes, centred, with the field taking whatever is left. Still about a third of the height on a phone; it is now a square in the middle of that band rather than a full-width strip.
- field.test.mjs lints the built CSS for `aspect-ratio:1` on that rule. A lint rather than a measurement, because the geometry is not observable in a stubbed DOM — but it fails if the rule is deleted or set back to auto, which is the way this would regress.
- Worth recording as a general hazard: the engine has assumptions like this one that live in CSS rather than in code, and a shell is exactly the kind of change that walks into them. The square is now stated in a comment where the rule is, not just implied by the original `aspect-ratio:1`.

## 2026-08-31 — the target has to hold still
- Two reports from play, both real. "Sometimes I trace a hiragana and then it goes to a different one and destroys it." And: "I'm tracing faster than the next one loads up."
- First is a genuine bug and mine. target() returned whichever monster was nearest the ward *at that instant*, recomputed on every call. Monsters advance continuously, so one could overtake yours mid-glyph — and conjure() then fired at the newcomer. You drew あ and something carrying ぬ died for it. What is being answered cannot be allowed to change underneath the answer.
- v0.1.16 locks the target when the tracer loads its glyph. The lock holds until that monster dies, reaches the ward, or the player taps another. nearest() still exists and is only consulted when there is no live lock.
- Tap-to-target added, as asked. It is the identification mechanic arriving earlier than planned: with the guide up the tracer still shows the shape, but which monster you take is now the player's choice rather than the field's. Hit radius 44px, measured to the bubble rather than the body since that is what the eye is on.
- Second report is the engine's 1.9s celebration in conjure() before it advances. Fine in the workshop, dead time under a clock — a fast hand finishes the next glyph before the next glyph exists. Field now advances at `advanceMs` (460ms), just after the shot lands at ~385ms.
- No cancelling needed for the engine's own delayed load(idx+1): load() clears `done`, and that callback is guarded by `if(done)`, so an early advance disarms the late one. Worth stating because the alternative — letting it fire at 1.9s — would reload mid-trace and wipe strokes the player had already drawn.
- The field test's setTimeout was stubbed to a no-op, so the advance path was not being exercised at all. It now has a real timer queue on the fake clock. Mutation-checked: recomputing the target instead of locking it, and leaving the advance at 1900ms, are both caught.
- Also caught myself asserting the wrong thing: the first version checked the shot had landed by 300ms when it flies at t += dt*2.6 and lands at ~385ms. The test was wrong, not the code.

## 2026-08-31 — swarm report
- Two more from play, and the first turned out to be an engine bug rather than a shell one.
- "When I retarget manually, the old glyph remains until a new pen touch." The trail is cached on an offscreen canvas and invalidated only when `trailProg!==prog||trailSeg!==_gi`. load() resets prog to 0 — so switching away from a glyph that was *also* at 0 changed neither key, the cache stood, and the previous character stayed on screen until the first touch moved prog. resize() has always cleared trailProg; load() never did.
- That means the workshop had it too: press Next without drawing and the old trail lingers. Nobody noticed because in the workshop you almost always draw before moving on. Tapping a monster is the first thing that switches glyphs from a standing start, so the field is where it surfaced. Fixed in load() rather than in the shell.
- "It gets messy at auto targeting when there's a lot coming to the centre." Each arrival cleared the lock and retargeted, and every retarget reloads the tracer, which wipes whatever had been drawn. Under a swarm that is continuous — the attempts were dying to the churn rather than to the monsters.
- Two changes, and together they make the churn harmless rather than merely rarer.
- (1) A finished glyph now hits whichever monster is *carrying* it, nearest first, rather than whichever object was locked. This is "you identify, you do not aim" taken literally, and it is the more honest reading: what was drawn decides what is hit. If your target reached the ward mid-glyph the character is still correct and still finds a mark; if nothing carries it the shot dissipates.
- (2) A retarget never interrupts a trace in progress. It queues and applies once the pen is up and prog is back to 0. Tapping still wins immediately, because that is the player asking. A glyph that no monster carries any more also triggers a retarget once the hand is free, so nobody is stranded tracing a character that cannot hit anything.
- Test hygiene, learned the hard way: conjure() queues a forced advance on a timer, and one left over from an earlier block fired inside the deferral test and forced exactly the reload that block was checking does not happen. Spent a diagnosis on it before spotting that the code was right and the test was dirty. Blocks now reset the clock as well as the run.
- All three mutation-checked: retarget interrupting a live trace, the shot going to the nearest monster instead of the one carrying the glyph, and load() not clearing trailProg.

## 2026-08-31 — running dry, and the sound never arriving
- Three from play. One bug, one design observation that is the most useful note anyone has made about this project, and one legibility problem.
- The freeze: finish a glyph at the moment the field runs dry and the tracer is stranded on the celebration. conjure() leaves done=true with prog at the end of the last stroke; the forced advance then finds no target and gives up, and nothing ever asks again. Fixed three ways because each covers a different path — an empty field refills on the next frame rather than waiting out spawnMs, a spawn claims an idle tracer, and tracing() no longer counts a finished attempt as work in progress.
- Reproducing it in the test took three attempts and each failure was mine, not the code's. First the premise was wrong (the field now refills, so it cannot be caught empty). Then conjure() left prog at 0 because nothing had traced. Then restart() leaves spawnAt at 0, so the next frame spawned regardless and the dry field never happened. Only after letting the field settle first did the test fail against v0.1.17 behaviour, which is the proof it was ever testing anything.
- Worth keeping: a test that passes against the bug it claims to cover is worth less than no test, because it certifies the opposite of what it checks. Three of the guards here are individually redundant — removing any one alone still leaves the freeze fixed — so only the combined removal reproduces it. That is fine for the code and a trap for the test.
- "My brain is just tracing without really thinking of what it sounds like." This is the sharpest thing anyone has said about the design. The tracer teaches the hand a shape and nothing else; the reading never arrives, so a player can learn to draw ぬ perfectly and still not know it says nu. Every mechanic so far has been about accuracy of the stroke, which is necessary and not sufficient.
- First move on it: the romaji blooms where the monster falls, at the moment of success, when attention is highest. Cheap, and it attaches sound to the win rather than to a label nobody reads.
- Not enough on its own, and worth saying so: seeing the reading is recognition, not recall. `field.sign: 'romaji'` already exists and inverts it — the bubble asks for "nu" and the player has to produce ぬ. That tests the mapping in the direction that matters, and it is the difficulty axis CLAUDE.md flagged as open rather than "how much guide is shown". Left as a pack key rather than switched on, because it is a much harder game and that is the player's call.
- "When I mess up my trace, I could hardly see how I'm supposed to redo it." fizzle() clears the ink but only rewinds prog by half, so the canvas is empty while the guide resumes from the middle of a glyph and the toast says "back to the dot". The visual and the state disagreed. The attempt now restarts, which is what the message always claimed. Plus an explicit redo button, since auto-restart only fires on a fizzle and a trace can go wrong long before it trips one.

## 2026-08-31 — the third voice
- Asked for: not just romaji, but the sarcastic rendering of how a foreigner actually says it. Three voices now — kana, romaji, gaijin — as a `gaijin` field per glyph in glyphs.json.
- It is funnier than romaji and it also does more work, which is why it earned a place rather than being a gag bolted on. Each entry aims at a specific error instead of a generic accent: つ → SOO names the dropped t, ふ → FOO names the labiodental f that should be bilabial, り → RRREE names the American r standing in for a tap, and い → EYE, う → YOO, え → EE, け → KAY name the vowels read as their English letter names.
- That is the pedagogical case: a learner recognises the wrong one as *theirs*. "tsu" is a spelling you skim; "SOO" is an accusation. The correct reading alone was recognition at best, and the report that prompted all this was that the brain was tracing without hearing anything.
- The bloom now shows both — the reading in gold, the way you probably said it in teal underneath. `field.reading` takes romaji | gaijin | both | off, and `field.sign` gained gaijin as a third bubble voice.
- The joke is self-directed and that is what keeps it clean: the player is the foreigner, the monsters are farang, and the hero cannot read. Same joke as the one already decided in the lore, wearing a different hat.
- Flagged in PACK.md rather than assumed: a native reader should check the tone before this is anywhere public. Same care the KhienThai spelling got, and for the same reason — far easier to change now than after.
- Tested that the joke is actually present, not just the field: the check fails if every gaijin reading is merely the romaji uppercased, which is exactly what a lazy fallback would produce and what `g.get("gaijin", romaji.upper())` in stitch.py would silently give if the data went missing.

## 2026-08-31 — the sync spine
- Asked about a database, with $50 of Atlas credits. Two facts changed the shape of the answer before any code.
- MongoDB's Atlas Data API and HTTPS Endpoints reached end-of-life on 30 September 2025, along with App Services auth, Device Sync and GraphQL. A static page cannot reach Atlas directly any more, so a DB means a backend function holding the connection string. That is a real addition to a project whose entire deployment story was one HTML file on Pages, verified byte-identical.
- And M0 is free forever and would hold far more than this can generate. The credits are not what makes it work, and choosing a paid tier to spend them would be backwards. Said so rather than quietly building something bigger.
- Wanted: economy, cross-device progress, telemetry, leaderboards — all four — with the offline constraint kept. So the spine first, since all four need the same three things: a device identity, an outbox that survives being offline, and an endpoint contract that does not trust the client.
- The rule the whole design hangs on: a client sends observations, never totals. "banish, ぬ, 4200ms" is a fact; "score 9000" is a claim, and a claim from a client is worth nothing. Totals get derived server-side. Without that, a leaderboard ranks whoever edited hardest and the idle economy is free money.
- Merge rules decided now rather than discovered later, because each field wants different treatment: telemetry is append-only and dedupes by id, mastery is max() per glyph and therefore conflict-free (which is why the client can keep owning it and stay playable offline), and the economy has to be server-authoritative. That last one is why the economy is last — everything before it merges cleanly and it does not.
- build/sync_layer.py is always installed and does nothing without an endpoint. Deliberate: the offline build and the syncing build are then the same code path with the network stubbed out, rather than two behaviours that drift apart between releases.
- Guarantees are tested as absences, which is the only way this stays honest: no endpoint means no fetch, offline means queued not lost, a failed flush drops nothing, and localStorage throwing on every access (private mode is a real browser behaviour) does not throw into the game. All four mutation-checked.
- The queue is capped at 500, oldest dropped. A device offline for a month must not fill its own storage and take mastery down with it.
- Malformed events are answered 400 with their ids in `accepted`. Deliberate and worth remembering: the outbox drops whatever the server accepts, so an event that will never be valid has to be acknowledged or it blocks everything queued behind it forever. Only retryable failures leave events in the queue.
- Rate limiting counts in the database, not in process memory. Serverless instances do not share memory, so an in-process counter is theatre.
- server/ is written but not deployed — the credentials are the user's and do not belong in this repo. Flagged in its README that Atlas network access has to be 0.0.0.0/0 because serverless has no stable egress IP on a free plan, which makes the database password the only thing between the internet and the data.

## 2026-09-02 — hitodama
- Asked for: a status dash for a glyph's "hit points", spent by auto-casting at the monster that carries it. Named it hitodama (人魂), the ghost light — already the decided visual language for potency in the lore, and it happens to carry the project's name inside it.
- Every finished glyph kindles its character by `hitodamaGain`, plus `cleanBonus` if the attempt had no zaps. zap() is the only global that says how an attempt went, so the shell wraps it to count. A lit character throws a wisp at any monster carrying it, one charge per cast, on a `castMs` cooldown, and never at the monster the hand is answering mid-trace.
- The consequence that matters more than the dash: nearest() now prefers a monster whose character is dark. A lit one will be answered by its own wisp, so the tracer points the hand at what actually needs practice. That is the spaced-repetition design working in play without a schedule, and it is what stops the player farming あ.
- Charge is keyed by character, kept in localStorage under `hito-hitodama`, and restart() does not touch it. Losing a run does not unlearn anything. A trace with nothing on the field to hit is banked rather than wasted.
- Found a real dead spot while testing: retarget() returned early whenever the target's glyph was already loaded, which after a conjure meant `done` stayed set until the engine's own 1.9s timer. Two monsters carrying the same character arriving together left the tracer in its celebration for 1.4s. The early return now requires the tracer to be live on the glyph.
- Three flakes in field.test.mjs, one mine and two older than this change. Mine: the cast cooldown carried across restart(), so a block starting within 900ms of an earlier cast saw no wisp — restart() resets it. Older: the shot-target check compared identity when the code compares character, and one run in twenty spawned a second carrier; and a stale `done` from a previous block's conjure survived restart(), which the retarget fix above also cures. Measured on the old build before touching anything: six failures in sixty runs, all the first kind.
- Two test mistakes of my own worth remembering, both the same shape as the one already in these notes: asserting on a wisp after it had already landed, and a stale-done check that passed because the kindled charge emptied the field and the refill cleared `done` for the wrong reason. Both were passing against the bug. Seven mutations now caught, sixty runs clean.

## 2026-09-02 — nice to haves, from a brainstorm with chat
- Parked, not planned. Recorded with the verdicts so the reasoning survives.
- (1) Guide as a mastery-faded underlay. Half exists: the guide is already inside the pad and `shadow` draws the ghost from stroke data, just set to none in the game pack. Fade to *medium* (shape only), not to nothing — invisible guide plus path-following scoring is the hard-mode scorer problem. Drive it from mastery, never from hitodama charge, and give it its own axis with a debug pin the way size has one.
- (2) Ward glow bound to health, slow pulse under a quarter. Agreed, cheap. The ward is gold, not red; red is only the fallen state.
- (3) Three monster states with fog of war. Pushed back: the sign is the question and the tracer loads it at spawn, so hiding it until "in range" stops the player answering. Raise blob opacity ~15% and leave it. An unidentified state, if ever, belongs on the difficulty axis as the bubble voice.
- (4) Targeting polish. Mostly built (44px, snap, drawn-glyph-wins). Missing: a "you chose this" marker distinct from "the field chose this", tap empty space or the same monster to clear, and an enable flag.
- (5) Trace telemetry. Exists twice partially: instrument.py logs every attempt but only in the debug build; the sync outbox has banish/breach/kindle/cast but not the grade, and it is an outbox, not a log. Add a `trace` event on the sync spine from the field's conjure/fizzle wrappers. Log coverage, travel, zaps, ms, size, wave — there is no scalar score in the engine and one should not be invented.

## 2026-09-02 — the glyph changing under the pen, and the messy board
- Two from play. "When the auto cast happens, sometimes I'm in the middle of writing my glyph and it changes." The wisp never takes the locked monster while tracing, so the swap came through the deferred retarget: a wisp or a breach elsewhere queued one, and tracing() said the hand was free. It said so because it only looked at prog and the pointer — which misses the first stroke before it finds the path, and a hand that has just lifted to think. Both are the moment before the pen comes back down.
- tracing() now counts ink on the board and any contact with the pad in the last `holdMs` (1.5s). A hovering pen does not count, or a pen resting over the tablet would block every retarget forever.
- "When I go outside the lines my drawing board gets so messy." The orange runs of every miss stayed until a fizzle. A stroke that never found the path is now erased on pen-up with a puff. Cosmetic by construction: travel and coverage accumulate live in follow(), not from the stroke list, so this cannot weaken the scribble guard. Strokes that touched the path keep their orange tails — the ink there is a record of where the hand went wrong, and that is worth seeing.
- endStroke cannot be wrapped: the engine passes the function reference to addEventListener at registration, so reassigning the global changes nothing, unlike load() and conjure() which are looked up at call time. The shell registers its own pointerup after the engine's instead. Worth remembering before the next wrapper.
- The workshop's practice row and the "Easy mode" hint were still showing under the sketchbook. Hidden, with the redo button staying.

## 2026-09-02 — overdrawn lines, fat ink, and the circle
- "If I overdrew a line, that line persists and overlapping ones make it messy." The tidy from v0.1.22 only erased strokes that never touched the path, on the theory that an off-path tail on a good stroke was a record worth seeing. In play it is what let an overdrawn line stay: a second pass over stroke 1 grazes the path near the cursor, counts as touched, and its whole orange length survives. Now every off-path run is cut out of the finished stroke and the on-path runs are kept as separate pieces, so nothing joins across the gap. Still cosmetic — travel and coverage accumulate live in follow().
- "When the hiragana shrinks, the font thickness is too fat. I struggled with fu." Ink width was 3+13p pixels regardless of size, so at the 0.32 floor a 9px line sat on a 115px glyph and ふ's four small strokes disappeared under their own ink. widthFor and the glow now scale by curS^0.75, floored at 0.45: a large glyph's line is unchanged, a small one is about 60% — sub-linear so it never goes to hairline. Engine fix, since the workshop had it too. The comet and the road go through the same paintStroke, so they thin together.
- "I really like the drag the circle feature. We can make super beginner mode with that." The circle is the glowing dot at PATH[prog], which moves with the pen — so what is liked is the following itself, with the penalties being the part that hurts. The ask is a ladder: a mode where you only drag the dot and nothing can go wrong, which trains for the mode where straying restarts you. Not built yet. Sketch: a `guided` mode above easy — same guide, DRAIN 0, no fizzle, tolerance roughly doubled — and, more interesting, the mode chosen per glyph from mastery: guided until the first clean conjure or two, then easy. That is the brainstorm's mastery-fade on the penalty axis rather than the guide axis, and it wants the same rule: its own axis with a debug pin, never coupled to size.

## 2026-09-02 — the start page
- "I guess we should have a start page with the difficulties." Built as an overlay in the field shell with the two axes the game actually has — how much help, and what the sign says. The second one is the open question from CLAUDE.md (kana or romaji?) answered the only honest way: it is the player's call, per run.
- Difficulty had to become a runtime switch. `mode` was a build-time table writing SHADOW_MODE, GUIDE_ON and GUIDE_NUMBERS, which are already lets; the penalties R_ON0, DRAIN and FIZZ were consts, and a later script cannot reassign a const. stitch.py now writes them as lets, values untouched. The shell reads the base values off the engine at boot rather than carrying its own copy, so a pack that tunes them stays authoritative.
- `guided` is the "drag the circle" mode from earlier today: the easy guide with DRAIN 0, FIZZ infinite, tolerance doubled. The coverage and travel checks at the end of a glyph are not touched, so a scribble still fails in guided — it just cannot fizzle you halfway. Kindling is unchanged for now; whether guided should pay less is tuning, and worth deciding after someone has played it.
- `hard` is on the page, locked, with "the scribe has not written this page yet". Showing it is deliberate: the ladder should be visible even where it is not yet climbable.
- The field pauses under the page — no movement, no spawn, no wisp — and resumes from where it stopped. The ward falling now returns to the page rather than restarting blind, and a ☰ button reopens it mid-run.
- Tested before any restart, since restart() is what begins a run and the state under test is the one before a run has begun. Mutations: pause ignored, guided still draining, hard selectable — all caught.
- Credits page added behind the start page, asked for mid-build. The content is the reasoning behind the name — 人 is two strokes and neither stands alone — followed by pack `credits` lines and the licence line, so the KanjiVG attribution the licence requires is on a page a player can open, not only in a footer nobody scrolls to. The lines ship by role rather than by name: naming people in a public build is the maintainer's call, and the key is there for it.

## 2026-09-02 — guided is an objective, not a discount
- "We literally want a no trace mark, follow the circle pass mode. Right now it doesn't feel like my objective to drag the circle and win works." Right. v0.1.24's guided was easy with the drain and fizzle off, which still drew ink, still zapped, still asked for 85% coverage at the end, and still had a 7px light. The player's objective was the light and the game was still grading the ink.
- Now guided: no ink (redrawInk is looked up by name on every pointer move, so a wrapper catches the engine's own calls — unlike endStroke), no zap, the light 2.4x, and COVER_MIN 0 with MAX_TRAVEL infinite. Those two had to become lets. The reasoning for dropping the end checks: the light cannot reach the end of a stroke without the pen having gone the whole way with it, so the coverage test is redundant with the objective and the travel test only punishes a wobbly hand that got there anyway. Stroke boundaries still need a lift, so hooks are still taught.
- "Medium is horrible. All the hiragana is huge and blurred. Still relies on the bounds of easy mode." The strokes shadow was the path at 2.4x ink width with a glow and blur. It hid the centreline and had no relation to the tolerance, so the player was judged against a band they could not see. Now drawn flat at exactly 2·R_ON, no glow: the shape shown *is* the band. shadowScale only sizes the done-glow now.
- The ☰ button sat under the hand and is gone; the name in the header reopens the page. The redo button now belongs to the run and hides under the page.
- v0.1.26: guided holds one size, the top of the range. "No point in trying to calibrate the smaller versions as it doesn't get you better at hiragana." Guided teaches shape and order; a small glyph tests the hand. SIZE_PIN already outranked the random draw for the debug ladder, so guided sets it and the other modes clear it.

## 2026-09-02 — the light is dragged, not chased
- Two reports from guided, opposite faces of one rule. "I'm passing the stroke by cutting sometimes without finishing properly." And: "when I finish the stroke, the dot thinks I didn't finish and I have to poke it a bit."
- follow() advances prog to the *nearest* path point within a 24-point window ahead, inside R_ON. With guided's doubled R_ON a chord across a curve keeps finding a point ahead within reach, so the light rides the chord. And a fast pen outruns the 24-point window, so the light lags behind the hand and only catches up as more samples arrive — with the pen resting at the end there are no samples, hence the poke.
- Guided now sets DRAG_FOLLOW: the light moves only while the pen is within R of it, and then walks forward through consecutive points the pen is near, stopping where the path leaves the pen's reach. A chord stops it at the first point of the curve out of reach; a pen that arrives at the end along the path has already brought the light there. Tolerance dropped from 2× to 1.5× as well, since the walk makes reach mean something.
- Autocast off for guided, as asked. Went one further: nothing kindles in guided either, and the dash and bubble lights are hidden there. Guided is practice; a no-fail mode that banked charge to spend in easy would let a player coast on wisps they never earned. One flag if that is wrong.
- nearest() prefers a dark monster only while wisps answer lit ones; in guided a lit monster is just a monster.
- Tested with the engine's own follow() driven from the harness: the light stays put with the pen out of reach, a ten-sample chord does not finish the stroke, and a drag along the path does. Picks a stroke with a point out of reach of both its ends so the chord cannot be a legitimate short cut.

## 2026-09-08 — vocab, the first word-level realm
- Asked for: the Japanese class quizzes as practice. "college; university" — write it. That is meaning → word → kana, and the tracer only knows the last step. A flashcard shell supplies the first two and walks the tracer through the word's kana one at a time. This is the "layout step" the economy plan always said words would be: a word is a sequence of glyph recordings, and no new stroke format was needed.
- Decks are class content, not realm data, so they live in `vocab/` outside `scripts/`. Genki I Lesson 1, five sections split the way the class quizzes are — one per vocabulary page plus hours and minutes.
- The gojūon list was not enough: だいがく wants が, いっぷん wants っ and ぷ, and katakana turn up in Lesson 1. Rather than grow the list per lesson, `kana_glyphs.py` emits every hiragana and katakana (164) once, with KanjiVG strokes for all of them, so a new lesson is only ever a JSON edit. The stitch refuses a deck that uses a character with no glyph or no stroke data — a build failure rather than a toast at runtime, since the card would otherwise ask for a character the sketchbook cannot load.
- Fonts: the vocab subsets are `*-kana-all.woff2`, a separate name. make_fonts.py takes a suffix now. Overwriting the gojūon subsets would have broken the byte-identical rebuild of every hiragana build.
- Honesty about what it tests. On easy the guide draws the path, so the kana's shape is revealed the moment the pen is down. The card cannot measure recall of the shape; what it measures is whether the hand needed to peek *before starting*. Reading, kana and skip all count against the word, and the next round's queue weights peeked words first. Real free recall waits on the hard-mode scorer, same as everywhere else.
- Skip requeues the word once, to the back. Once, not forever: a word the hand cannot write today should come back today, but not turn the round into a loop.
- Progress is a per-word ledger (n, clean, peek, last), keyed by the word. Export/import on the credits page from day one, as the hard rule says, and import merges by max rather than replacing — a count only goes up.
- Same seam as the field: `load()` wrapped so every engine-initiated load lands on the kana the card is asking for, `conjure()` wrapped to advance the slot. While the word blooms or the round is summarised the engine's own late advance is swallowed rather than reloading a finished glyph out from under its celebration.
- **Drift risk, on purpose.** The shell carries a copy of the field's difficulty table (guided/easy/medium and which engine lets each one sets). Two copies of one table will drift. Folding them into a shared module means rebuilding the game shell, which is a separate change, so the copy is the honest state for now and this note is the reminder.
- Tested the seam directly, the way field.test.mjs does: a word walked kana by kana, the bloom, peeks counting, a skip requeueing exactly once, the round ending, and export → clear → import round-tripping the ledger. Rebuilds byte-identical alongside the hiragana builds.

## 2026-09-08 — links that do not change
- "Let's make it so our link does not change." Every release renamed the file, so every link handed out went stale a week later. Now `dist/<script>.html` is an unversioned byte-identical copy of the current build, the README points at those, and the version rides in the footer as well as the title, header and toast — the page has to say which build it is, since the URL no longer does.
- A copy rather than a redirect stub: a stub is two loads and is not the build if someone saves it, and git stores identical blobs once, so the copy is free. `run.sh` checks the copy against the versioned file and says which `cp` to run when it is stale, because "remember to copy it" is exactly the kind of rule that gets forgotten on a one-liner bump.
- Found by the flake, not by design: the vocab seam test failed one run in four, always on a word of five or more kana. The engine schedules `load(idx+1)` 1.9s after every conjure, guarded only by `done`. Conjure five kana faster than that and an earlier kana's timer lands while the current one is finished and waiting on the shell's 420ms advance — the wrapper redirected it to the *current* kana, which reloaded the finished glyph and killed its celebration. A quick hand can hit the same window in play, most visibly on the last kana, where the bloom would sit over an unfinished sketchbook.
- The wrapper now holds a finished glyph that is the card's kana; a finished *stray* glyph still comes back to the card, which the existing stray-conjure check enforces — the first version of the fix swallowed both and that check caught it. The race is now tested deterministically on every kana rather than left to the shuffle.
- The field's wrapper has the same shape and the same theoretical window, but its advance retargets to a fresh glyph so two conjures in 1.9s on the same target are needed to hit it. Not changed; noted.

## 2026-09-08 — the menu reaches the other realm
- "Make it so our menu page can access either games." A `realms` pack key: each start page gets an "other realms" row linking to sibling builds by bare filename — `vocab.html` from the game, `hiragana-game.html` from vocab. Bare filenames on purpose, and the stitch refuses a path or URL: the same link works on Pages and in any folder holding both files, and the engine stays free of any host. Where the other file is absent it is a dead link and nothing more; nothing waits on it, so the offline constraint is untouched.
- The stable names from earlier today are what make this possible at all. A link to `vocab-v0.1.1.html` would have been stale by the next bump, and a start page that points at a version that no longer exists is worse than no link.
- Both tests check the start page carries the href, so a pack that drops the key by accident is caught rather than discovered on the tablet.

## 2026-09-10 — easy mode lag: the blur was repainted per pen sample
- "The game is playable for vocabulary, but lags so much on easy mode." Every pen sample repainted the whole lit path from its first point, every stroke of ink on the board, and — whenever the light moved — the whole road ahead with its embers. Each of those is a stroke() with shadowBlur, and each blurred stroke is its own offscreen blur pass; late in a glyph that was hundreds per sample, several samples per frame. Easy is the only mode paying all three: guided draws no ink, medium has no comet or road. The convention already said "no per-frame shadow blur, cache trails offscreen"; the engine had never followed it on these paths.
- Now the same stroke() calls are made in the same order and remembered. The lit path grows from where it was last painted (paintLit); ink keeps finished strokes and appends only the current stroke's new segments (redrawInk); the road ahead is cached from a checkpoint 24 points in front of the pen to the end of the stroke, with only the stretch between pen and checkpoint painted live (renderTrail). The guide and ink composites run once per animation frame (paintLater) instead of once per sample.
- Two layers each for the ink and the lit path, glow on one and white core on the other, composited core-over-glow. Painting glow and core together per piece put each new glow over the previous core and tinted every joint gold — measured, not guessed: a pixel comparison of the old and new builds driving the same synthetic trace showed it, and the layered version brought the difference to rounding. When a stroke ends its core is folded into the glow layer so the next stroke's glow crosses over it as it always did.
- Verified in headless Chrome, old build and new side by side: the guide, ink and effects canvases are pixel-identical within 3/255 after every stroke, mid-stroke, on a finished glyph and after a fizzle. Frame-driven timing on the laptop's Intel GPU at device pixel ratio 3: ~34 ms per frame before, ~27 after; on the software rasterizer the two are equal. The real target is a tablet GPU, where each blur pass is a render-target switch and the cost is far higher than on a desktop — not measurable from here, so the tablet is the test that matters.
- One deliberate cosmetic change: the embers on the road ahead sit at fixed points of the stroke and are consumed as the pen passes, instead of being re-spaced from wherever the pen is. They used to crawl as prog moved.
- Two things learned about measuring canvas cost that will matter next time. Chrome records canvas commands and rasterizes at frame time, so a stopwatch around draw calls measures recording, not drawing — time frames, not calls. And getImageData demotes a canvas to software after a few reads, so any harness that reads pixels is no longer timing the GPU path. Sub-rectangle drawImage between canvases makes the software rasterizer snapshot the whole source first; whole-canvas copies are twenty times cheaper there.

## 2026-09-12 — guided: the light led the pen by a whole tolerance
- "On guided mode, the guiding circle is obviously too ahead of my stylus and completes the strokes before I can." The drag rule walked forward from the light through every consecutive path point within tolerance of the pen and rested the light on the *last* one — the far edge of the tolerance circle. On any straight run that is a full radius ahead, and guided's radius is 1.5x easy's, so the lead was worst in the one mode built around the light. The lit path is painted up to the same index, so it ran ahead too. The stroke's end test only asks that the light index be within slack of the end and the pen within the end tolerance; with the light already at the end, the stroke closed with the pen a radius short. Measured in the test: 13 points ahead at mid-stroke, closed 14 points early.
- The light now rests on the *nearest* point of the reachable run. The run is still walked forward from the light and stops where the path leaves the pen's reach, so the two reasons the drag rule exists — a chord cannot cut a curve, a fast pen cannot outrun the window — are untouched. Only where the light rests changed.
- The dot goes from 2.4x to 1.5x. "The circle is way too large": at 2.4x it covered the path under the pen, and a light you cannot see past is not a guide. Both shells' copies of the difficulty table changed, which is the drift risk from 2026-09-08 paying its first toll.
- field.test.mjs now drags to the middle of の and checks the light is there, then stops a radius short of the end and checks the stroke is still open. The v0.1.30 build fails both.

## 2026-09-12 — guided, second report: it was the comet, and the loop has to stop
- After v0.1.31: "guided mode is still giant circle always beating me to the finish line. The self trace is still big and blurry. Impossible to practice strokes. I also think the loop of guiding me should stop. When we see it over and over again it sometimes makes my brain think I should follow its speed." So the thing beating the hand to the end was never only the light — it was the comet, the blurred streak that runs from the light to the end of the stroke on a loop, every 2.2s plus 17ms a point. It is a demonstration, and it always wins the race because that is what it is for. In guided, where the whole objective is dragging one light at your own speed, a second light that keeps sprinting the same stroke sets a pace, and the hand starts following the pace instead of the path.
- The comet is now its own switch (`COMET_ON`), like the guide and the numbers, and guided turns it off. The road ahead still shows where the stroke goes; guided no longer shows how fast. Easy keeps the comet — it is the "ride the comet" mode and the pacing is the point there.
- The light drops to 1x, the same as easy's. It had gone 2.4x → 1.5x on the first report and was still "a giant circle", and easy's light drew no complaint. The rationale that the light should be "big enough to be the thing you are holding" did not survive the hand.
- A lesson for the notes: the first fix measured the light's index and found it a radius ahead, which was real and is still fixed, but the reporter's word "circle" covered two drawn things and the fix only reached one. When a report names what it sees rather than what the code calls it, list everything on screen that could match before choosing.

## 2026-09-12 — medium: the tolerance band is not a shape
- Screenshot from the phone, vocab v0.1.5, medium, は: four fat yellow blobs with darker discs along them, "impossible to trace correctly". Medium drew the shape as a flat band at exactly the tolerance width, on the reasoning that what you see should be the band you are judged in. Two things were wrong with it. The tolerance radius is 7% of the canvas, so the band is 14% of the canvas and about a fifth of the glyph's height: at that width the strokes of は merge and there is no line to put the pen on. And paintStroke draws a segment at a time with round caps, so at alpha .17 every joint stacked two caps into a darker disc — the string of discs in the screenshot, which read as blur even though nothing was blurred.
- Medium now draws what a textbook prints: a flat line down the centre of each stroke at the ink's own width (widthFor(.5), about 5% of the glyph), one path per stroke so nothing stacks, no glow. The tolerance is the scorer's business and the shape is the learner's; showing the band was conflating them, the same mistake as size-as-mastery in a different coat. Verified by rendering は in headless Chrome, not only by the test.
- The band-width rule had been judged against the 2.4x glowing shadow it replaced, on a sim canvas. Against that it was an improvement; against a phone with a hand on it, it was not. Same lesson as the guided light: the sim and the test say the numbers are right, and the hand says what the numbers look like.

## 2026-09-12 — the handakuten circle finished on a tap
- "The circle for the p sound is too sensitive. Just tapping on the initial point passes without doing the stroke." The circle is 0.081 across; the tolerance is 0.07 in easy and 0.105 in guided. So from its start, most (easy) or all (guided) of it is within reach at once, and its end point is its start point. In guided the drag walk ran round to the end from a single tap; in easy the LOOK window (24 points) put the tail in reach after a backward flick of a few points. Either way the end test — prog near the end, pen within endTol of the end — was met without the stroke being drawn. Every scale-honesty rule so far was about the *end* of a stroke; nothing said the middle had to be visited by the pen, only that it be within reach of it, and for a stroke smaller than the tolerance those are different things.
- Progress into a stroke is now capped by the pen's own travel within it, plus a free allowance of 30% of the stroke's points (`startSlack`, a fraction so a circle and a long sweep get the same slack; the tail needs 88%, so 30% can never reach it). Travel is the pen's actual path, so an honest trace always has at least the arc it covered and the cap never binds on it — the size sweep and the tail test are unchanged. A pen lift mid-stroke does not reset it; only a new stroke, a fizzle or a load does.
- What the test caught about the test: the segment indices were captured before each difficulty switch, and a switch reloads the glyph at a new size, which resamples the path and moves every index. And coverage is judged over the whole glyph at the end, so the honest check has to draw every stroke, not just the circle. Both were the rig, not the engine; both are the kind of thing that only shows up when the test drives the real build rather than a re-implementation of it.
- The game pack has no handakuten, so this lives in vocab.test.mjs, the build with all 164 kana. On v0.1.6 the tap and the flick both finish the circle in guided; easy needs a longer flick than the test makes, so the test only proves the guided case against the old build. Both pass on v0.1.7.
- Housekeeping: the CLAUDE.md build pointers had sat at v0.1.32 / v0.1.5 since the comet release, because the medium round's docs script aborted on a mismatched sentence before writing. Corrected here.

## 2026-09-12 — ふ's ticks finished on a jab at their end
- "Fu is cheatable. I can poke my stylus at the end of the tiny hooks and it completes them." The ticks are 0.16 long at full size, 0.08 at the smallest. The travel cap from earlier today asks for 58% of that — 0.05 to 0.09 — and a jab that skids, or a poke with a wiggle, covers it: a wiggle of ±0.012 twelve times is 0.2 of travel, more than the tick is long. Travel said the pen had moved enough; nothing said it had moved from the right place. The end of a stroke had a tolerance floored so a hand can find it; its start had no such thing — the window forgave up to 24 points, the cap forgave 30%, and neither asked where the pen came down.
- Now a stroke has a start the way it has an end. `startTol` is `startSlack` (30%) of the stroke's length, capped at the tolerance and floored at `minEndTolerance`, exactly endTol's shape. Until the pen has been within it of the first point, travel within the stroke does not count, so the cap holds prog at the free allowance and the stroke will not finish from its far end. A pen at the end of an unbegun stroke is told once that it starts at the other end, because a stroke that silently refuses to finish is a bug report, not a lesson. A fizzle keeps the stroke begun: the rewound point was reached from the start.
- For long strokes this tightens the forgiven late start from 30% of the stroke to the tolerance (0.07 of the canvas, about 14% of a 0.5 stroke). Medium tests where strokes start, so that is the point there; on easy the badge and the start dot show where, and 0.07 is the same distance the pen has to keep to the path anyway. If a young hand finds it tight, `startSlack` and `minEndTolerance` are the dials and this note is the reason.
- Tested on the game build, which has ふ: a jab skidding back along a tick and a wiggle at its end both fail on v0.1.34 and are refused on v0.1.35; a start a couple of points late still finishes, and ふ drawn honestly still finishes. The toast is checked by rebinding the engine's own `toast` from the probe — the engine calls it by name inside the rig's Function scope, so wrapping the window copy sees nothing.

## 2026-09-14 — a front door

- The Pages root was a 404. `.nojekyll` (2025) stops Jekyll rendering
  README.md as the index, and nothing was ever put at `/` in its place, so
  the only working links were the three deep ones in the README and "open
  the game" meant "know the filename". `index.html` at the repo root now
  serves https://thesisbytes.github.io/hito/ as a landing page: play
  (hiragana game, vocab), workshop, the offline note and the credits, on
  the same lacquer as the builds. Static, no dependencies, so it also opens
  from a double-click beside `dist/` like everything else.
- It links the stable names (`dist/hiragana-game.html` etc.), never a
  versioned file, so a bump does not touch it. `run.sh` now checks that
  every local href on the page exists — a dead link on the one page a
  visitor is handed is a shipping failure, not a surprise on a phone.
- Not done: a way back *from* a build to the homepage. The realms row links
  siblings by bare filename and the stitch refuses paths on purpose (see
  2026-09-08), and `../index.html` is a path. The browser's back button
  covers it for now; if it turns out to matter, the honest fix is a
  `home` pack key that names a bare filename in the same folder, which
  means moving `index.html` into `dist/` — decide then, not now.

## 2026-09-14 — Lesson 2 in the deck (vocab v0.1.9, hiragana v0.1.36)

- "We also need to update the vocabulary list for my current schedule." The
  Canvas modules show two Lesson 2 quizzes, L2-1 on p.58 and L2-2 on p.59,
  so the deck gains two sections named the way the L1 ones are. The deck
  file is now `vocab/genki-i.json`: it holds the class's running list, not
  one lesson, and the name was about to lie. Everything that pointed at
  `genki-l1.json` (pack, PACK.md, CLAUDE.md, the local study script) follows.
- The L1 pages are in Drive ("L1 Pages from Genki Textbook - 3E.pdf") and
  confirm the existing deck; the L2 pages are not, so Lesson 2 is written
  from the 3rd edition list and the page break is inferred. L1 runs about
  27 entries a printed page (p.38: 27, p.39: 26, p.40: 12), and L2 has 53,
  so p.58 is taken to end after じてんしゃ and p.59 to open with しんぶん.
  If the book disagrees, a word moves across a section boundary and
  nothing else changes. The deck's `source` string says the same.
- Tシャツ is written ティーシャツ, with a note, because the sketchbook
  traces kana and the stitch refuses a Latin letter — the right refusal,
  and this is the one word in two lessons that trips it. Suffix and
  particle entries (～えん, (～を)ください) follow L1's pattern: the bare
  word traced, the frame in the note. Six p.59 words (イギリス, かんこく,
  ちゅうごく, けいざい, おかあさん, おとうさん) were additional vocabulary
  on pp.39–40 and are kept in L2-2 with a note, since that is the page the
  quiz names.
- A returning player's saved section choice is honoured, so the new
  sections arrive unticked on the start page rather than silently joining
  the round. Tick them there.
- Found on the way: the page `<title>` was hand-typed in every pack and had
  drifted in all three (hiragana's said v0.1.29 at v0.1.35, vocab's said
  v0.1.2). The convention puts the version in the title precisely so a
  cached build is obvious, and the one place it was wrong was the tab. The
  stitch now stamps whatever `vX.Y.Z` the title carries with the pack's
  version, and `run.sh` checks the three current builds. That is the whole
  reason for hiragana v0.1.36: a title, nothing in the tracer.

## 2026-09-14 — A word the book prints twice is asked once (vocab v0.1.10)

- "Some words seem they repeat." They did: p.59 re-lists six words from
  pp.39–40 (イギリス, かんこく, ちゅうごく, けいざい, おかあさん,
  おとうさん), and いちじ is on both p.38 and the hours page. The deck keeps
  each on every page the book prints it, because a quiz on p.59 alone has
  to ask them — so a round over both pages asked each twice.
- The fix is where the round is assembled, not in the deck: `selected()`
  in the shell and the quiz in `vocab/study.py` both keep the first page a
  word appears on and drop the rest. The begin button's count follows.
  The ledger was never the problem — it is keyed by the word, so both
  copies already shared one entry.
- The test selects every section and expects the round to be the number of
  distinct words, and asserts the deck still has a repeat so the check
  cannot go quietly vacuous if someone dedupes the JSON instead.

## 2026-09-14 — The card times the recall and asks how it went (vocab v0.1.11)

- "A helpful metric would be how long it takes me to recall. I notice if
  I see the first hiragana I'll be able to get most words. Maybe after I
  trace, we have a button for I knew how to write this. Or if I needed
  the first letter. Or I had no idea what the word was." Built as said.
- The clock runs from the card being shown to the first thing the hand
  does — a pen-down on the sketchbook or a hint tap — and only the first
  counts, so a redo or a fizzle does not restart it. It is shown on the
  bloom ("pen down after 2.3 s"), kept per word in the ledger (`rt`, the
  last eight, only for words graded *knew it* — a hinted word was not
  recalled, so its time is not a recall time), summarised as the median
  and the slowest for the round, and shown per section on the start page.
- The hints are now the maintainer's own tiers. *first kana* lights the
  first slot and nothing else; *show word* fills every slot and shows the
  reading. The romaji *reading* button is gone: with the meaning as the
  prompt it was the whole answer in another alphabet, and it fit none of
  the three grades. The reading still blooms when the word is done.
- Grades: 2 knew it, 1 needed the first kana, 0 no idea. A hinted word
  grades itself and blooms for `wordPauseMs` as before. An unhinted word
  blooms until one of the three buttons is tapped — one more tap per
  word, deliberately, because the guide drew every shape once the pen was
  down and only the hand knows whether it needed that. The grade cannot
  be talked up past what the hints imply. Skip records a 0 straight away
  and still requeues the word once.
- Ordering next round: weight is 1 plus how far the last three grades sit
  below *knew it*, plus up to 1 for a slow recall (eight seconds weighs
  like a miss). A ledger from before grades falls back to the old
  peek-ratio weight, and imports without `g`/`rt` are accepted.
- Found on the way: the import merge wrote `b.last|0`, and a millisecond
  timestamp does not survive a 32-bit truncation, so every imported
  `last` had been landing as 0. Harmless while nothing read it; the grade
  history now comes from whichever side wrote last, so it is fixed and
  tested.
- "Don't really care for the categories to play with." The section
  picker on the start page is left as it is — it costs nothing and the
  class quizzes are per page — but nothing new was spent on it. If it is
  in the way, the honest change is a single "everything" round with the
  picker folded behind it.

## 2026-09-14 — The Lesson 1 quiz as cards (vocab v0.1.12)

- "I also put in a grammar quiz in google drive." It is the class's
  にほんご101 レッスンクイズ（1か）, in Drive as "Lesson Quiz_L.1". Four
  parts: I listening (phone numbers), II clock times, III six sentences
  to translate, IV four WH questions to ask きむらさん.
- Parts II–IV are in the deck as three sections after the L1 pages:
  `l1-quiz-time`, `l1-quiz-say`, `l1-quiz-ask`. A sentence is a longer
  run of kana and the shell walks it the same way — this is the
  words → sentences tier the economy plan named, and it cost a JSON
  edit. The answers are the maintainer's model answers in Lesson 1
  grammar (XはYです, の, か, なん/なんさい/なんねんせい), written without
  the 。 the tracer has no stroke for. The quiz's own instructions
  ("translate my", "write 25 in Japanese", "include Kimura-san") ride in
  the note field so the card asks the same thing the paper does. Part IV
  prompts with the exchange, blank on your side, since the reply is
  what the question has to fit.
- Part I is listening and needs audio the build does not have. Not here.
- As with Lesson 2, a returning player finds the new sections unticked on
  the start page. Tick them there.

## 2026-09-15 — Katakana words in the field, and the hiragana chart fills in (katakana-game v0.1.0, hiragana v0.1.37, vocab v0.1.13)

- "Let's make a katakana practice. I keep freezing on those words although
  sometimes I know what it sounds like." Then: "you could probably mix it
  with the hiragana game with the farang messing up the pronunciation."
  That second line is the design. A katakana loanword *is* English in a
  Japanese accent, so the farang's speech bubble saying "koohii" is the
  farang mangling "coffee", and the answer is コーヒー. Built as the field
  shell with a deck rather than a third shell: `shell_field.py` now takes
  the deck the vocab shell already took, and with one the farang carry
  words. The pack is `scripts/vocab/katakana.json` (the vocab pack's kana
  and strokes under the field shell), the deck `vocab/katakana.json`.
- How a word rides the seam: a word monster's `i` is always the kana it is
  waiting for, so `bearer`, `pick`, `retarget` and the tracer's load all
  work unchanged. `conjure` advances the monster (ci++, i = next kana) at
  the moment the kana is written, not when the shot lands — the shot's
  landing time depends on frame rate and the advance timer does not, and
  advancing on landing could reload the *same* kana under a fast hand. The
  lock holds on a half-written word so the next kana is its next kana.
  The loop's "nobody carries this glyph" retarget now waits while `done`
  is set, because after a word's kana the finished character is indeed
  carried by nobody, and the advance timer is what should move things.
- Each landed kana knocks the farang back (`field.knockback`, 0.07 radii);
  the last one banishes. Without that a six-kana word under the same clock
  as a single glyph is unfair, and the pack is also slower and sparser
  (`speed` 0.03, `spawnMs` 9000). Tuning by hand still to come.
- Ghost lights are kept by the word, not by its first kana, and a word
  kindles once, when whole, with clean meaning no zap anywhere in it. The
  sign axis reads for words: `kana` the word, `romaji` the reading (the
  farang's accent), `gaijin` the farang's own English word. Default is
  romaji, since knowing the sound and freezing on the shapes was the
  complaint; the English is one tap away for the fuller test. The kill
  blooms with whichever half the sign kept back. The start page remembers
  its sign under its own key (`hito-start-katakana`), because "gaijin"
  means something different here than in the hiragana game and the two
  builds share an origin on Pages.
- 101 words in three sections by what makes katakana hard: plain kana,
  the long-vowel bar, the small kana. Mostly Genki I's, romaji in the
  book's style. Tシャツ is ティーシャツ as in the vocab deck. The sections
  are in the JSON but the field has no picker: the roster is the deck.
- "Also, we should add the ゛ and the circles and the little hiraganas."
  The hiragana pack goes from 46 to 75: the five voiced rows and ゃゅょっ.
  Strokes lifted from the vocab book (the converter and source are the
  same; the 46 were verified identical first), fonts switched to the
  `-kana-all` subsets since the source fonts are not in the repo and the
  full-kana subsets are 12KB larger. っ gets its own chart row under つ's
  column rather than colliding with ゅ in the small row. ぁぃぅぇぉゎ are
  left out on purpose — they hardly occur in hiragana. Romaji for the
  small kana is "small ya" etc., which the field test's reading check now
  allows a space for. `probeChars` became あがっ so the font probe checks
  a voiced and a small glyph are really loaded.
- Found on the way: the tail test's 80% floor failed on every dakuten
  tick at 79.9997%. A tick is a six-point path with one point of slack,
  so it finishes at exactly 4/5 of its arc, and 4/5 in floating point sat
  on the wrong side of 0.80. The test now has an epsilon; nothing in the
  scorer changed. The scoring and size sweeps had "46" typed in and now
  count the book.

## 2026-09-17 — p.59 from the page itself (vocab v0.1.14)

- "This is on the quiz today", with a photo of p.59. The page and the deck
  disagreed, and the page wins: L2-2 had been written from memory and a
  guessed page break, and both were off.
- The page opens at ペン, so しんぶん, Tシャツ, とけい and ノート move back to
  L2-1. The break was guessed from L1's density; it is now where the book
  puts it.
- Places was wrong outright. The deck had カフェ, ほんや, レストラン — none of
  which are on the page (they are later lessons) — and was missing ぎんこう,
  コンビニ, としょかん, ゆうびんきょく. Majors was missing えいご, and the
  three p.39 re-lists (コンピューター, ビジネス, れきし) the dedupe in
  `selected()` already knows how to ask once.
- L2-2 is now the photographed page line for line, 27 entries. **p.58 has
  still not been checked against the book** — the 3rd edition lists スマホ
  under Things, and the deck does not have it. A photo settles it.
- Lesson for the deck: a section is only trusted once it has been read off
  the page. The `source` field now says which ones have been.

## 2026-09-17 — ろっぴゃく would not come (vocab v0.1.15)

- After the quiz: "couldn't for the life of me recall a number that has
  piyaku". That is 600 and 800 (ろっぴゃく, はっぴゃく), with 300 the other
  odd one (さんびゃく), and the thousands repeat the trick at さんぜん and
  はっせん.
- New section `l2-numbers`: 100–900, 1,000–9,000 and いちまん, the prompt
  being the numeral. The regular ones are in on purpose — a card that only
  ever shows irregulars teaches "this one is odd" before the pen is down,
  and spotting which ones are odd is the test. Notes name the sound change.
- Not read off a page, unlike the rest of the deck; the `source` field says
  so. These are facts of the language rather than of the book, so the
  2026-09-17 rule above bends rather than breaks.

## 2026-09-20 — A second front door: Appwrite Sites

- The maintainer connected the repo to an Appwrite Cloud site (`hito`, project
  `nira-hito`, sfo). Live at https://hito.appwrite.network/ — GitHub Pages
  stays; this is a second host, not a replacement, and nothing in `dist/`
  changed, so no version bump.
- The first deployment failed because the site was created with the defaults
  `npm install` / `npm run build`, and there is no `package.json` — nothing
  here is built on the host, the builds are committed. Both commands are now
  empty, output directory `./`, adapter `static`. The root is served rather
  than `dist/` because `index.html` lives at the root and links into `dist/`,
  same as Pages.
- `sites update` replaces the whole record: leave out `--installation-id` /
  `--provider-repository-id` and the GitHub link is gone. Pass everything.
- The first GitHub-triggered deployment after the fix built in under a second
  and then sat in `building` for good, never reaching edge distribution. A
  hand upload with identical settings went ready in 25s, and a second
  GitHub-triggered one went ready in 30s. Cause not established — it was
  created two seconds before the failed one was finalised, which is a guess,
  not a finding. If a push ever leaves the site stale, look for this first.
- Checked by fetching all 11 files from the live domain and comparing bytes
  with the commit, not by reading the status field — the status said
  `building` and `failed` about the same moment in two places.
- Static hosting only. The sync endpoint is still undeployed and
  `server/README.md` still describes Vercel + Atlas; whether Appwrite's
  functions and tables replace that is a design question, not decided here.

## 2026-09-20 — The hand: finger input, handwriting, stats, and a real endpoint (hiragana v0.1.38, vocab v0.1.16, katakana-game v0.1.1)

- The maintainer: "since appwrite handles databases and auth, lets go ahead
  and make our game log handwriting and cool stats to improve the user play.
  also, add in touch stroking instead of just stylus. maybe a toggle". That
  settles the question the entry above left open: the endpoint is an Appwrite
  function over an Appwrite table. The Vercel + Atlas draft in `server/` was
  never deployed and is gone; `server/README.md` is rewritten.
- **Touch was already in the engine.** `penOnly` has been a workshop button
  since the Thai tracer. What was missing was everything around it: the games
  hide the workshop, it defaulted to on, and nothing remembered it — so on a
  phone the public link opened a sketchbook that ignored the only input the
  device has. The work was a switch, a memory, a first guess and a nudge, not
  a second input path. Scoring is untouched.
- **The server draft had a bug that deploying it would have found the hard
  way.** It validated per batch and knew four kinds; the client was already
  sending `kindle`, `cast` and `word`. One of those answered 400 for the whole
  batch, and a 400 acknowledges every id (so poison cannot block the queue),
  so every batch with a kindle in it — most of them — would have been thrown
  away and reported as delivered. Refusal is now per event, and
  `server.test.mjs` scans `build/` for every kind the client records.
- **A keepalive fetch is capped at 64KB.** Forty traces is ~100KB. The browser
  rejects that before it leaves, which is indistinguishable from offline, so
  the outbox would have backed off forever with a full queue. It now batches
  by bytes as well as count, and keeps draining while the server takes
  everything it is handed.
- The old "partial acceptance" sync check had been passing for the wrong
  reason: `record()` flushes at once, so its two events never shared a request
  and the second simply sat there. It now queues offline first.
- **Tidy eats the evidence.** The field removes off-path ink from `strokes` at
  pen-up. Found by driving a real browser: a deliberately wandering finger
  produced an empty log. The hand keeps its own copy, taken between the
  engine's `endStroke` and the field's `tidy()` — listener order, which holds
  because the hand is appended before the shells.
- **Auth is deliberately not switched on.** A random device id asks nothing of
  the player. The first thing that needs an account is merging two devices;
  until then it is a login screen in front of a game that opens from a
  double-click. Sharing is on by default, said plainly on the ✋ page, and one
  tap turns it off. **That default is the maintainer's to overrule** — the
  testers include children, and the data is handwriting.
- Checked end to end: the built outbox flushed 31 real events to the live
  function in 2 requests and 31 rows came back out of the table; then a finger
  traced て in headless Chrome and the engine's own scorer landed it, logged
  as `input: touch` with the 3 zaps the wander earned. Test rows deleted.
- Not done: nothing reads the traces yet. They are there for hard mode's
  thresholds and for finding the strokes everyone gets wrong; both are a
  notebook and an afternoon, not an engine change.
- **A build with a live endpoint is live wherever it runs.** Driving the game
  in headless Chrome to check finger input put 9 rows in the production table
  — mine, from six throwaway device ids, recognisable by `ms: 0`, which no
  hand can do. Deleted by device id, not by wiping the table. Then the same
  question asked of `run.sh`: four tests boot a whole build, Node has a global
  `fetch`, and each was attempting a real POST. None had landed, which was
  luck. `build/test/offline.mjs` is now preloaded into every test. Anyone
  driving a build by hand should switch sharing off first, or expect to clean
  up after themselves.

## 2026-09-20 — The run: ink, four upgrades, farang that take more than one hit (hiragana v0.1.39, katakana-game v0.1.2, vocab v0.1.17)

- The maintainer: "I'm trying to make a game inspired by the tower defense
  game, The Tower", then, on what to keep: "I think it is important that we
  keep tracing. the idle portion should be like the characters we charged up..
  but as the stage increments, the farang become more than characters. they
  could be names, sentences, nouns". Both are now DECIDED in `CLAUDE.md`, with
  how the second one plays written out so it survives the chat it was said in.
- The field was already most of The Tower: a ward at the centre, enemies from
  every side in polar coordinates, and hitodama as an auto-firing tower. What
  it lacked was a reason for a run to get harder and something to spend.
- **Built:** `hp` was already on every monster and always 1; it now climbs
  with the wave for single characters. Ink is paid for the *trace*, not the
  kill, because the hand did the work whether or not anything was standing
  there; a wisp's kill pays 1 so the idle half earns without outearning the
  pen. Four upgrades on a DOM strip at the top of the field — the far end of
  the screen from the hand, since a button under a resting palm presses itself.
- **The arithmetic that makes the curve:** a clean trace is three hits (itself
  plus the two lights it kindles). So up to 3 HP one clean trace finishes a
  farang by itself a few seconds later; past that the pen has to come back, or
  `bright` has to have been bought. No tuning pass has been done by a hand —
  the numbers are a starting position.
- Deliberately absent: an upgrade that raises the charge cap. Charges persist
  across runs and upgrades do not, so a run-scoped cap would leave charges
  above the cap when it ended. That belongs with the permanent upgrades.
- The reading used to bloom on every hit. With 4-HP farang that is the same
  word four times, so it blooms when the hand lands a hit and when the farang
  finally goes, and not for a wisp in between.
- **Three faults only a real browser showed**, all mine: the engine styles
  every `button` as `flex:1; min-width:88px`, so the ✋ button was a bar across
  the header in the games (shipped that way in v0.1.38 — nobody had looked at
  a running field, only at the sheets laid over it); the HP pips were drawn on
  the farang's head; and the strip covered the `banished` tally, which moved
  to the bottom left and gained the wave number. The stub passed all three.
- The new field checks were run against two deliberately broken builds (ink
  surviving a restart; buying on credit) and failed both, as they should.
- `upgrade` is a new event kind; the function was redeployed and
  `server.test.mjs` would have failed the build had it not been added.
- Not done, in order: characters-as-charges for words (the `key()` change),
  in-order slot filling by wisps, named farang, then sentences with particles
  by hand. After that the persistent half: workshop upgrades, research, tiers.

## 2026-09-20 — "the japanese trace-ables are not showing up" (hiragana v0.1.40, katakana-game v0.1.3, vocab v0.1.18)

- Reported by the maintainer from a real device. A clean desktop profile drew
  the guide in every build at every density, so the first three guesses —
  hosting, screen density, the main page — were all wrong. What found it was
  the production table: one real device, five breaches in eighteen seconds,
  not one trace. Somebody had a field and nothing to trace. Then replaying
  saved state (a difficulty, high mastery, full lights) reproduced it.
- **Two bugs, one mine.**
  - *Mine, v0.1.39:* the run's currency was a variable called `ink` inside the
    field. `ink` is the engine's drawing context, and guided mode wipes the
    pen's mark with it on every pointer move. Guided threw on each one.
  - *Older, present in v0.1.37:* `drawImage` throws on a source canvas that is
    0 wide. If the stage has no layout box when the page boots — a race —
    `resize()` fits the offscreen canvases to 0 and throws halfway, and
    `ghostTick()` throws and takes the animation loop with it, because the
    loop re-arms on its last line. Nothing called `resize()` again until the
    window itself changed size. Sketchbook 0 pixels wide, nothing to trace,
    for the whole session. Now: nothing draws into no box, the loop waits
    rather than dies, and a ResizeObserver watches the stage and the field.
- **The class of the first bug, found by writing a lint for it:** the field
  also hid the engine's `loop`. `tidy()` calls `loop()` for the engine's
  particle loop and had been getting the field's game loop — so every tidied
  stray started another permanent game loop, and the puff it was for never
  animated. Shipped for months, passed every test. `shadow.test.mjs` now
  fails the build on any such name; the field's `hit`, `label`, `loop` and the
  currency are renamed, the hand's `ink`, and the telemetry layer's private
  `cur`, `strokes`, `t0` (not bugs — the same trap, not yet sprung).
- Both new checks were run against the live v0.1.39 build first and failed it.
- **Also in this release — the arsenal, step one of the farang growing up:**
  lights are kept by character in the word game too (they were kept by word).
  Every kana written lights that kana; a lit kana writes the slot a farang is
  waiting on, in order, and stops at a dark one; the pen is sent to the hole;
  a light does not knock a word back (or a lit arsenal holds it at the edge
  for ever and there is no clock); a teal slot in the bubble is one you hold.
  Lights kept by word before this are dropped on load — nothing could spend
  them — and only those: the store is shared with the other realms.
- Three word tests leaned on the random roster and broke the moment a light
  could write a doubled kana. They use a fixed three-kana word now. One was
  already flaky: "piano" is piano in both voices.

## 2026-09-20 — Guest or signed in, and a title screen (hiragana v0.1.41, katakana-game v0.1.4, vocab v0.1.19)

- The maintainer: "i'd like to login to see my stats. i auth'd the google sign
  in on my end", then "so guest mode, and login mode", and of the main page,
  "i want it to feel like the game title screen".
- **Two things stood between that and a working sign-in**, neither in this
  repo. The project had no web platforms registered, so Appwrite would have
  refused both the browser's calls and the redirect. And the Google client ID
  had been pasted with `https://` on the front; asked directly, Google answers
  that with `Error 401: invalid_client` and answers the bare ID with its
  sign-in page. Corrected through the CLI sending only the ID, with Appwrite's
  own credential validation switched on so a lost secret would have shown.
- **Not tested: the Google hop itself.** It needs the maintainer's password.
  Everything after it was run for real in Chrome with a throwaway user and the
  same one-use token the redirect carries: device A signed in, the token left
  the address bar, the save was written; device B, empty, signed in as the
  same player and came up with A's ぬ at 7 conjures and A's mastery. A
  stranger asking for the row got 404. User and row deleted afterwards.
- The session is a third-party cookie (page and API are different sites), and
  most browsers refuse those now. Appwrite's answer is an
  `X-Fallback-Cookies` header kept in localStorage; headless Chrome needed it,
  so that path is the tested one.
- No SDK. Five REST calls, and an SDK is a dependency in a project whose
  constraint is that there are none.
- The test found a real fault before it found anything else: with a remembered
  sign-in and no network, boot rejected with nothing to catch it.
- A cached name is not a session. With a stale `hito-user` the title screen
  asks, gets a real 401, and says "guest". Offline it keeps the name.
- The player's email address is never written to localStorage: the name is
  shown, and the id is needed; nothing else is kept.
- `index.html` is generated now, and `run.sh` fails if it is hand-edited.

## 2026-09-20 — Night, and room for a finger (hiragana v0.1.42, katakana-game v0.1.5, vocab v0.1.20)

- The maintainer: "i don't really fancy the gold. i like dark mode and my
  favorite colors are blue and green. the finger tracing is hard, cause i have
  fat fingers."
- **The theme is a table, not a refactor.** The colours were literals in six
  files and two languages (CSS, and rgba strings in canvas code), but a closed
  set of about forty. So the page is built gold and translated at the end.
  Blue takes gold's job, green takes teal's; nothing changes meaning. Warnings
  stay warm, and against blue they warn better.
- A screenshot found what the table had missed: the panels behind the field
  and the sketchbook (`--lacquer-2`) and the dots along the path were still
  brown and yellow. That scan is now `theme.test.mjs`, which promptly found
  the debug build's red "fails here" button — a warning, allowed by name.
- The upgrade strip cut its labels to "the l…" at phone width. It shows the
  cost alone there now; half a sentence is worse than none.
- **Fingers.** Three things give: size, room, tolerance. Not an offset cursor
  (drawing above the fingertip so it can be seen) — it solves the same
  problem and is the first thing to try if this is not enough, but it changes
  what tracing feels like and wants a hand to judge it, not a test.
- Only on a screen that can feel a finger. A mouse in finger mode is already
  precise and gets nothing.
- **Not verified by a hand.** Headless Chrome confirmed the numbers on a
  simulated touch phone (sketchbook 262px to 324px, glyph at 0.62, ease 1.5)
  and the tail guard holds at that ease. Whether it is *comfortable* is the
  fifth thing in this project only a hand can say.

## 2026-09-20 — A run ends, two hands, and the traces were lone ticks (hiragana v0.1.43, katakana-game v0.1.6, vocab v0.1.21)

- Google sign-in confirmed by the maintainer on their own account. The table
  agrees: one user, one save row readable by that user alone, their device
  linked, 22 conjured across 16 characters.
- **The handwriting log was broken for guided players, for two releases.** The
  maintainer's 24 traces had a median of 166ms and が was 3 points long. Guided
  wipes the engine's ink after every stroke; the hand read "no ink" as "new
  attempt" and started over each time, and the engine restarts its own clock
  whenever the ink is empty. So every character was logged as its last stroke.
  The hand now starts over only when a glyph loads, keeps its own clock, and a
  test fires real pointer events through the engine's handlers while wiping the
  ink between strokes. It failed the live build: "logged as 1 stroke(s)".
  Confirmed in Chrome under guided: 3 of 3 strokes. **Traces before v0.1.43 in
  guided are last-stroke-only**, and `traces_gallery.py` marks them.
- The fix had its own small bug, caught by the same test: `0` meant "not
  started" and the test's clock starts at 0. `null` is the sentinel now.
- "still hard to trace with the thickness of the hiragana". They play guided
  with a finger, so forgiveness was the wrong half of it — see CLAUDE.md. Also
  the cap on eased tolerance had been swallowing most of the finger's 1.5x in
  guided, which already runs at 1.5x; raised from 0.125 to 0.15.
- "touch / pen sizes should be optimized separately": two profiles.
- "make it so the game ends when i lose all health and saves that trace
  experience": the ending, the run record, the three places it is kept.
- "are we collecting the traces somewhere? we can totally make them svgs":
  yes — `hito.events`, kind `trace`. In the game the ✋ page draws them over the
  reference and saves a sheet as one SVG, offline, nothing uploaded. From the
  repo, `build/traces_gallery.py` writes `scratch/handwriting.html` (gitignored:
  it is people's handwriting) through the CLI's own login, so no key.
- **Ideas, the maintainer's, "maybe later":** "best stroke of the day" and "you
  could barely recognize this". Feasible as it stands: a trace and its
  reference share a coordinate space, so distance from the asked-for shape is a
  number per trace, and the same number is what hard mode's `compare()` needs.
- **Next, asked for:** "make it impossible to advance without unlocking stuff.
  so there needs to be a currency to use after each round" — The Tower's
  workshop. The accounting has to merge across devices without a server, so a
  balance cannot be stored: earnings are per-device totals merged by max,
  purchases are owned levels merged by max, and the balance is derived.

## 2026-09-20 — Stages, 魂, and the lantern workshop (hiragana v0.1.44, katakana-game v0.1.7, vocab v0.1.22)

- Asked for in one line and DECIDED in CLAUDE.md. What was chosen, and why:
  - **The gate is the curriculum.** What a stage unlocks is the next row of the
    chart, in the order the chart is learned. An arbitrary gate (pay to raise
    a number) would have been a grind; this one is the syllabus with a price
    on it, and the price is paid in tracing.
  - **Clearing, not just paying.** A gate is for sale only after the stage
    before it has been held to the end. Otherwise enough lost runs buy any
    gate, and "cannot advance without unlocking" quietly becomes "cannot
    advance without waiting".
  - **Guided pays half.** It cannot be zapped, so every guided trace would
    count as clean and guided would be the best-paying way to play. The
    maintainer plays guided; this is aimed at the rule, not at them, and the
    number is theirs to change (`DIFF.guided.tama`).
  - **The light cap finally has a home.** It was left out of the run's
    upgrades because lights outlive a run and a run-scoped cap would strand
    them. It is a lantern now, which lasts as long as they do.
- **No stored balance**, for the reason in CLAUDE.md. The known wart: the same
  level bought on two offline devices is paid for twice. It costs the player,
  never the game, and only if they go looking for it.
- The purse test first failed for a reason that was the test's: its two
  "devices" share a global, so A's earnings were credited to B. Real tablets
  do not share a `window`. One device at a time now.
- Checked against a mutant that sells the gate without the stage held: three
  checks fail. Won a stage in Chrome: "the ward held", + 魂 21, the gate on
  sale, the sixth heart from a bought lantern in force.
- **Not balanced by a hand.** Twelve farang, 30 tama a gate, 1.45x: a starting
  position. At these numbers a clean stage pays roughly 20-30, so about one
  gate per one or two held stages — by arithmetic, not by play.
- Existing players keep everything: mastery, lights and the ledger are
  untouched. They start at stage 1 with two rows on the field, which for
  somebody who knows the chart will be a quick climb, not a wall.
- The shadow lint caught its own author: the stage number was first a variable
  called `stage`, which is the engine's sketchbook element. Nothing was broken
  yet — which is what `ink` looked like for a release, too. The rename was done
  with a regex that was too clever: it rewrote labels ("gate to stageNo 2") and
  skipped a real use sitting before a colon, which would have put a DOM element
  in the run record. A stubbed test caught the label and the record; the real
  browser had only been asked about one button. Rename by hand.

## 2026-09-20 — Guided only gets you so far; recognisable pays more (hiragana v0.1.45, katakana-game v0.1.8, vocab v0.1.23)

- The maintainer's design, in their words, DECIDED in CLAUDE.md. Thresholds
  (stage 3 for easy, stage 8 for medium) are a starting position.
- **Played is not held.** A stage below its required mode still runs and still
  pays — guided stays a place to practise anything unlocked — but it does not
  clear, and the ending says why rather than letting the gate stay shut in
  silence.
- **The score is a symmetric chamfer distance**, because one direction alone
  lies: a tick drawn on the path is entirely "on the shape", and scored as a
  perfect あ until the other direction — how much of the shape has ink near it
  — was averaged in. There is a test for exactly that tick.
- In Chrome, three traces of one character with 0, 9 and 22px of wobble scored
  98%, 77% and 59%. So the scale has room at both ends, which is all that can
  be said without a hand.
- "best stroke of the run ✦" and "you could barely recognize this" went in
  after all, since the score they need now exists. The second only appears
  under 45%, and only when there is more than one trace to be the worst of.
- **A bug that the safety net hid.** The score's first version reused the name
  `last` inside `note()`, where it is already a const: every note threw after
  saving, the wrapper that stops a failed note costing a glyph swallowed it,
  and the only symptom was a score of null. The wrapper is right; the silence
  was not. It counts its faults now and the tests assert the count.
- Two intermittent test failures on the way out, and they were different
  things. One was the test: a fixed sideways drift is already off the scale for
  the smallest glyph at the smallest size, and the glyph is random. The other
  was the game: the field's zap counter is only cleared when a glyph loads, so
  a run that ended after a zap and restarted on the same character counted the
  new run's first trace as unclean. `restart()` clears it. Suite run three
  times clean before shipping, because one green run had stopped meaning much.

## 2026-09-23 — The agents: Strands wired up (agents/)

- **Why there is an `agents/` directory.** The maintainer's multi-agent
  systems class (Strands Agents SDK, OpenRouter) wants a project, and hito is
  the one they like. The semester's scope is **tracing only**; typing,
  speaking and reading layers wait until it ends. Each piece is meant to map
  to a named idea from the course — harness, hooks, memory, context window —
  so the writeup (LaTeX, later) can point at code.
- **The rule that shapes it: agents never run at play time.** A build opens
  offline from a double-click and no farang waits on OpenRouter. The agents
  read a pull of the events table from disk and write under `agents/out`.
  Nothing in `build/` or `dist/` knows they exist.
- **System 1 and System 2, in Kahneman's sense.** The tracer's scorer is
  already a System 1: deterministic, sub-millisecond, judging every pen
  sample. The plan is a fast decision model (Laya, the open-source Jev-
  compatible one: JSON state and typed questions in, calibrated probabilities
  out, ~33 ms, no text, runs locally via ONNX) labelling every trace row —
  honest, stopped short, poked, scribble, gave up — with the LLM called only
  when its confidence is low. Strands' `BeforeModelCallEvent` can `cancel` a
  model call, which is where that gate will sit. Not built. Laya reads
  numbers, not ink, so it never replaces the scorer; and it is a few hundred
  megabytes, so it never ships in a build.
- **Geometry in a script, judgment in a model.** `events.py` is pure Python:
  overview, per-character summary, hardest characters, and *consistency* —
  the mean chamfer distance between a hand's landed attempts at one
  character as a fraction of its size, the same measure the hand's
  `quality()` uses between ink and shape. An agent reads what it computed
  and never invents a number. The ground truth for any labelling is the
  `flag` events, the only human verdicts; there are none in the table yet.
- **Two hooks, both about trust.** `Ledger` writes one line per model and
  tool call to a file (nothing lives only in the terminal; it caught the
  first live failure, a 402, before anything else did). `Fence` cancels any
  tool call whose `name` or `path` lands outside `agents/out`; the test
  asks the agent to overwrite `build/engine.html` and checks the bytes.
- **Tested without a key.** A scripted `Model` plays the LLM's part, so the
  suite exercises tool dispatch, the ledger and the fence offline. `run.sh`
  runs it when `agents/.venv` exists.
- **Live, once.** With the class account's key (in the environment, from the
  course folder — never here) the analyst read the pull, called two tools
  and wrote a fair summary: 286 traces over 78 characters on 4 devices in two
  days, ふ the only character with enough attempts to trust, and — its one
  complaint — no trace carrying a quality score. That complaint was right and
  the fault was ours: the hand stores the score as `q`, the run record as
  `quality`, and the arithmetic looked for the second. Fixed. OpenRouter also
  refuses a request that reserves the model's whole output window against a
  small balance, so `max_tokens` defaults to 2000 (`HITO_MAX_TOKENS`).
- **Trust asymmetry, for later.** The game holds no key and only writes,
  through the sync function. The pipeline is the first process that reads
  events and will write something back (a derived table, one row per player,
  overwritten each run; never `hito.saves`, which merges by max; never a
  ranking). So it is the first holder of a real API key. Environment only,
  scopes limited, experiments against the file on disk.
- **Two tracer reports from the maintainer, diagnosed, not yet fixed.** (1)
  Easy mode: a poke a third of the way into a stroke lights the first third,
  because `startSlack` grants that much free progress and the lit paint
  follows the progress index rather than `hit[]`. Paint from what the pen
  touched; the allowance is a threshold to tune separately. (2) A hand that
  stops at the last visible ember can be up to three path points short of
  the scored end, which exceeds the 0.02 floor on a short stroke. Needs a
  running build to confirm it is the embers and not the finger. Both are
  drawing bugs before they are thresholds, and worth fixing by hand first so
  the labelling experiment has a before and after.

## 2026-09-23 — Bedrock, and mem0 as memory (agents/)

- **Bedrock by default.** The maintainer has credit there and Strands is
  AWS's SDK. A Bedrock API key in `.env` at the repo root (ignored by git,
  read by the agents themselves, never overriding the environment) picks it;
  the class's OpenRouter key stays as the fallback; `HITO_LLM` forces one.
  The key lists Sonnet 5 through its cross-region profile, which is the
  default id. The first real call was refused: the new account is under
  AWS verification ("normally less than 2 hours"). The ledger has the
  refusal, and the fallback ran meanwhile.
- **mem0 is a Strands memory store, not a tool bolted on.** Strands 1.57
  has a `MemoryManager` with pluggable stores; `Mem0Store` is one. The
  harness searches it with the question and prepends a `<memory>` block
  before each model call (the durable history is untouched), hands each
  finished turn to mem0 to distil with its own LLM, and registers
  `search_memory` / `add_memory` for when the model wants to look something
  up or write a decision down. This is the course's "memory" concept sitting
  in the harness where it belongs.
- **Scoped by `user_id`.** `maintainer` is the analyst's own notes across
  sessions; a device id is what was learned about one hand. mem0 2.x takes
  the scope as `user_id` on add and as `filters={"user_id": ...}` on search
  and list, which the first live run found the hard way (Strands logged the
  failed search and carried on, which is the right failure).
- **Embeddings are the awkward part.** Titan on Bedrock once verified;
  OpenRouter serves none, so the fallback is Gemini's embedding model with
  the key already on this machine. One Qdrant collection per embedder, on
  disk under `agents/out/memory`, because vectors from two models must never
  be searched together. `python -m hito_agents.memory` prints everything
  remembered: nothing lives only in a vector store.
- **Live, on the fallback.** Run one: the analyst stored the maintainer's
  play style and the known poke bug through `add_memory`, then answered
  from the table. Run two, a fresh process, was refused by OpenRouter's
  in-flight budget, and stayed refused on every retry: the class account
  is spent. So the live recall is not yet demonstrated; what is on disk is
  three memories — the two notes, and a third mem0 distilled by itself from
  the turn (む fizzles most, four traces, too thin to call). The recall
  itself is proven offline against the fake, and will be shown live on
  Bedrock once the account is verified. mem0's telemetry is switched off
  and its import-time warnings about optional extras are silenced.
- **Tests stay offline.** A fake mem0 with the 2.x calling convention
  (asserting that a top-level `user_id` is never passed to search) stands
  in; the suite checks the config follows the provider, both write paths
  (verbatim for `add`, distilled for a turn), scoping, that memory reaches
  the model and the turn reaches memory. Sixteen tests.

## 2026-09-23 — Bedrock answers, and memory recalls (agents/)

- **The gates, in the order a fresh account meets them:** account
  verification (about an hour, no email came), then Anthropic's use-case
  form, which the Bedrock API key cannot submit (its policy is invoke-only;
  `PutUseCaseForModelAccess` was refused), so it was filled in the console.
  About ten minutes after that the model answered. Titan embeddings needed
  nothing. Sonnet 5 and Opus 5 still say "not available for this account";
  Sonnet 4.6 through the global profile is the default.
- **Recall, live.** Run one stored two notes through `add_memory` and
  answered from the table. Run two, a fresh process, asked for memory only
  and got both back word for word: the maintainer plays guided by finger
  on a phone; the poke bug is known and unfixed. The Bedrock collection is
  separate from the Gemini one, as designed, so it started empty.
- The whole loop — pull, analyst, hooks, memory — now runs on one provider
  with credit behind it. Next is the experiment the layer was built for:
  Laya's labels against the flag events, once there are flags.

## 2026-09-23 — Laya, zero-shot, does not read trace geometry (agents/system1.py)

- **What was built.** `system1.py`: per-trace geometry in the stroke book's
  space (coverage of the path by the ink's segments, start and end gap as a
  fraction of the character's size, ink over path length, ink span, strokes
  drawn against strokes expected), Laya's typed questions over it (a
  five-way verdict — honest, stopped_short, poked, scribble, gave_up — and a
  yes/no "would a teacher accept this"), a batch labeller writing
  `agents/out/labels.jsonl`, a `triage` tool for the analyst, and
  `agree()`, the comparison against the flag events. Tests use a fake
  predictor; the model never loads in the suite.
- **The geometry separates the populations on its own.** Over 286 traces:
  landed ones cover a median 97% of the path with an end gap of 8%; fizzled
  ones cover 64% with a gap of 16% and travel 0.75 of the path — a hand that
  followed the line and stopped, not a scribble. The "template sticks out
  further" report is visible before any model looks.
- **Laya, zero-shot, is uninformative here.** Given the features as JSON it
  called all 286 traces honest; given them as prose it called the same
  sample all scribble. In both, the probabilities sat near uniform, the
  fizzled and landed rows drew the same label, and the median confidence
  was 0.02 (JSON) and 0.09 (prose). An エ trace covering 28% of the path
  and stopping two thirds of the character short was "honest" at 0.28. The
  model card says it ships over-confident and wants temperature scaling on
  your own data; on this data the trouble is not confidence but signal. It
  was trained on tickets, email and moderation, and it does not transfer to
  numbers about ink, however they are phrased. 286 rows took 555 s on this
  CPU with both questions, not 33 ms.
- **System 2 reads the same prose fine.** Sonnet 4.6 on Bedrock, one call,
  the same 24 narrations: the fizzles came back stopped_short, gave_up and
  honest, the landed ones honest, and each label matches its geometry. So
  the prose is separable and the gap is Laya's, not the features'.
- **The finding the baseline turned up.** Five of the thirteen fizzles are
  ふ with coverage 0.88–0.99, end gap 0.07–0.14 and travel 1.02–1.18: by
  the geometry, fair traces of all four strokes that the tracer rejected.
  That is the tick strokes of ふ (CLAUDE.md, "A stroke begins where it
  begins") refusing honest hands, and it is the first thing this layer has
  said that the maintainer did not already know. Worth a real look.
- **What the class experiment becomes.** Zero-shot failed; that is a
  result, not the end. Laya ships the pieces for the honest next step —
  `RLAgent`, `proper_reward`, `ece_score`: train or calibrate its heads on
  labels of our own under a proper scoring rule and measure calibration.
  The labels are the flag events (none yet) and the maintainer's own
  verdicts on the gallery. Until then the System 1 seat is empty and the
  LLM does the labelling, which costs more and is what the gate was meant
  to avoid. `HITO_LAYA_STATE` picks json or prose; prose is the default,
  being the natural input and a third faster.

## 2026-09-23 — The hand's first 24 verdicts (agents/labels/)

- **A private page instead of a local gallery.** `agents/verdicts_page.py`
  renders the 24-trace sample (every fizzle to date, eleven landed) as ink
  over the shape asked for, with the geometry, Laya's guess and six
  verdict buttons; the verdicts live in the page's own store and
  `agents/verdicts.py` reads them back. The maintainer judged all 24 on
  their phone. They are in `agents/labels/`, ids and verdicts only.
- **What the hand said.** Every fizzle: *stopped short*, thirteen of
  thirteen. Landed: eight fair, two scribbles (け at 2.18x travel with a
  redrawn stroke; す), one stopped short — ら, which turned out to be a
  guided trace from v0.1.41 holding only its last stroke, the old capture
  bug. Those are filtered out of labelling now (`partial()`); the table
  has 24 of them.
- **I was wrong about ふ, and the number was wrong first.** The five ふ
  fizzles I called fair had an end gap of 7-14% *of the character*. The
  engine judges a stroke's end against the stroke's own length (endTol),
  and against ふ's tick those gaps are 28-52% of the stroke: the hand
  stopped a third to a half of a tick short, and said so. `end_gap_stroke`
  is a feature now and the prose says both. This is the maintainer's
  "traced to the end I see, but the template sticks out further" report,
  measured: on the ticks of ふ, the visible end and the scored end
  disagree by a third of the tick. Fix the drawing before the threshold.
- **Laya against the hand: 8 of 24**, all from saying honest to
  everything. A one-line rule on the geometry would do far better, which
  is the baseline any tuned Laya has to beat.
- **The maintainer's second report: fizzling should clear the ink.** A
  fizzle halves progress and leaves the ink, so a redrawn stroke lands on
  top of the old one and the recorded trace is both. け's "scribble" is
  that. Whether a fizzle clears only the ink or restarts the character is
  a game-feel decision, open; the recording should in any case start fresh
  at a fizzle, or the labels are labels of a mess.

## 2026-09-23 — A stroke that went nowhere never happened (hiragana v0.1.46, katakana-game v0.1.9, vocab v0.1.24)

- **The maintainer: "we should clear when we fizzle"; then, given the
  choice, "restart the character"; then, given the numbers, the third
  option: drop strays in guided and easy, restart in medium and up.** The
  game shells already restarted on a fizzle (`fizzleRestarts`); the
  workshop halved progress. What made the recordings a mess was not
  fizzles but strokes that never fizzled: a stroke started off the path
  gets a zap, the hand lifts and redraws, and the first one stayed on the
  canvas (workshop) and in the record (everywhere) — 61 of the first 286
  traces, 30 of them in guided, where nothing zaps at all.
- **The rule.** The pen coming down snapshots the scorer (after the lift
  has advanced to the next stroke, before the first sample is scored). The
  pen lifting asks whether the stroke got anywhere: finished its stroke, or
  moved on, or advanced more than `straySkid` (3) path points. If not:
  `drop` puts the ink and the scorer back to the snapshot and the hand does
  not record it; `restart` fizzles; `keep` is the old rule. `strayMode` in
  the pack (default `drop`), `stray` per difficulty in the shells (medium:
  restart). And `fizzle()` restarts the character in every build now — the
  stitch's strict-state reset sets progress to zero instead of half.
- **The hand's note has a new case.** In a browser the engine's own
  `fizzle()` is the hand's wrapper, so on a stray restart the note is taken
  inside endStroke: the engine holds the stray, the hand has not heard the
  lift. The engine holding one stroke more than the hand, with the pen
  down, is now read as live. The stub cannot rebind the engine's internal
  call, so `stray.test.mjs` plays that order by hand: the engine's listener
  alone, then the note.
- **The harness moved to `build/test/dom.mjs`** so the stray test could
  share it. Two of the hand's tests draw strokes nowhere near the path on
  purpose (they are about the clock); they set `keep`.
- **Two flakes found on the way, both pre-existing.** `field.test.mjs`
  fails under the suite's offline preload far more than alone (5 of 8 on
  the previous build) on the 3-hit farang and the par checks; alone it
  passes 8 of 8. And in the stub the engine's first load waits on a fonts
  promise nobody awaits, so a field whose random first target is あ has an
  engine that names あ and holds no strokes. Neither is fixed here; the
  stray test loads explicitly to stay clear of the second.
- **Every realm's stroke book.** The System 1 geometry read the vocab book
  only; it now merges every `scripts/*/strokes.json`, as the gallery does.
  The maintainer: "make sure we don't have to repeat this process for
  katakana and kanji". The loop is keyed by character and stroke book, not
  by realm: a kanji pack is a glyph list and a KanjiVG-converted book, and
  the agents, the verdict page and the labels find it by existing.

## 2026-09-23 — The hand rates readability, 0 to 100 (agents/labels/readable-2026-09-23.jsonl)

- The maintainer: the five categories went unused; "I can 100% say I
  could read it, 0% not close at all". The page is a slider now, and the
  same 24 traces were rated. The ratings agree with the earlier verdicts:
  fair attempts 80-100, stopped short 0-50, scribbles 0. ふ's five fizzles
  sit at 30-50: half-read, which is what a tick missing a third of its
  length looks like.
- **What predicts the hand's rating.** Coverage of the path by the ink,
  Spearman +0.69 over all 24. The hand's own `quality()` score, +0.26 over
  the ten traces that have one — and the reason is す: the scorer's best
  trace of the sample (q 0.83, coverage 0.98) and the hand's 0, "scribble".
  Chamfer distance between ink and shape says the ink is on the shape; it
  cannot see that it got there the wrong way. That is the thing hard mode's
  "is this あ?" scorer has to be checked against, and the first evidence
  that distance alone will not do it. Laya's accept probability: −0.28,
  uninformative, as before.
- Ten of 24 have a `q` at all: the hand scores quality only for landed
  traces from v0.1.45. Scoring fizzles too would give the comparison its
  other half.
- Twenty-four ratings from one hand is a starting position, not a
  calibration set. The page can take another batch any time; the next
  should be a fresh sample rather than the fizzles again.

## 2026-09-23 — One size per hand, guided reaches the end, guided sees the chart (hiragana v0.1.47, katakana-game v0.1.10, vocab v0.1.25)

- **The maintainer, after a session on v0.1.46:** the random pen sizes are
  an annoyance ("one size canvas for stylus, and one size for finger");
  guided "recorded my stroke even after I dragged it too far" because
  "once I thought I reached the end point, it would not trigger the next
  stroke"; and under the stage gate guided never shows the whole chart.
- **The session's numbers.** 96 traces, all v0.1.46. Medium with the pen:
  63 traces, 7 fizzles, 3 with a redrawn stroke (it was 19 of 164 before
  the stray rule). Guided with the finger: 33, and 10 still carried a
  redrawn stroke, because a stroke that moved the light is not a stray. 54
  of 88 guided strokes ran on past the end, a median third of the stroke,
  against none in medium: the finger's centre had to land inside a pen's
  end tolerance while the finger visibly covered the end.
- **The pen at 0.52.** 239 medium traces by size band: 0.48-0.56 had the
  fewest zaps (0.85 a trace), the most clean traces (81%) and quality 0.69;
  larger was slightly worse, smaller clearly. `hand.pen.size` is
  `[0.52, 0.52]` in every pack; the finger stays at its largest. The random
  rule remains for packs that want it, and CLAUDE.md's "size is its own
  axis" still holds — it is just no longer sampled.
- **Guided closes a stroke when the finger covers its end.** In drag mode
  the end test is reach: the light within R of the end along the stroke,
  the pen within R of it; the light then snaps to the end. Elsewhere the
  end test is exactly as before, and the tail guard on the eased copy still
  passes. The stray test drives a finger to 0.6R and 1.6R short of あ's
  first end and checks one closes and the other does not.
- **Guided draws from every row** (`allRows` on the field's guided
  difficulty). It holds no stage past the second and earns no gate, so
  showing it the chart costs the progression nothing.
- **Left for later.** A tick's start in guided still asks for a landing
  within the floor of 2% of the canvas, which a finger cannot do on purpose;
  and the ten guided strokes redrawn after the light moved are the honest
  case of the rule, not strays, so they stay in the record.

## 2026-09-23 — Batch 2 of the hand's ratings: the hook, and the lift (agents/labels/readable-2026-09-23-b.jsonl)

- 24 traces from the v0.1.46 session, rated on the page. The maintainer,
  on the finger ones: "I failed all the ones that look like scribbles, and
  gave low percentages when they almost got it, but the hook was too long
  or the strokes connected when they were not supposed to." Both are
  measurable and are features now: `overshoot`, the ink drawn after the
  point nearest a stroke's end over the stroke's length (the worst stroke);
  `joined`, strokes the character has that the hand did not lift for.
- **Pen (19).** Coverage predicts the rating again (+0.73), the
  stroke-relative end gap (−0.60), then joined (−0.43) and overshoot
  (−0.39). The hand's own `q`: +0.08 on twelve traces. Two traces the tracer
  *landed* were rated 0: an あ with 26 zaps and an overshoot of 2.08 strokes,
  and a し with 46% coverage. The scorer let both through; the hand would
  not have.
- **Finger (5, all guided, all before the v0.1.47 end fix).** Coverage is
  high on every one (0.62-0.99) and says nothing (−0.30). Overshoot says
  it all: the four rated 0-20 ran on by 0.82-1.11 of a stroke past the end,
  the one rated 80 ran on by nothing. That is the "dragged it too far"
  report in the ratings, and it is what v0.1.47's end-within-reach should
  remove. The next guided batch is the test.
- **What this means for hard mode.** `quality()` is a chamfer distance:
  ink on the shape scores well however it got there and however much of
  it there is. Twice now the hand has rated its best-scoring traces 0. The
  scorer that answers "is this あ?" needs, at least: coverage, overshoot,
  the lift count, and the stroke-relative end gap — the four things the
  hand's ratings track — before any distance.

## 2026-09-23 — A finger's band, and a clean start to a run (hiragana v0.1.48, katakana-game v0.1.11, vocab v0.1.26)

- **The maintainer, after tracing medium with thumb, pointer and pinky:**
  "the canvas is likely too small, since our strokes don't seem to register
  with what I'm touching ... they're so cluttered together that I could do
  like a quarter to half circle and it'll pass as path completed". And:
  "an already traced path comes up once in a while on medium, typically
  when I'm progressing to the next round".
- **The band, measured.** On an 844px phone the sketchbook is 354px and a
  0.62 glyph 219px. With the finger's ease at 1.5 the scorer's radius is
  37px: a band 74px wide, 34% of the glyph. A pen at 0.52 gets 25%. Both
  the band and the glyph are fractions of the canvas, so a bigger canvas
  leaves the ratio alone; it shrinks the fingertip and its touch offset
  against the glyph, which is the other half of the report. So both
  levers, gently: `ease` 1.5 → 1.3 (28%), `stage` 42 → 46dvh. Guided is
  barely touched (its own 1.5x meets the 0.15 cap either way). A starting
  position for the next session, not a tuning.
- **The lit path at the start of a run.** Not reproduced in the stub: the
  engine's state after a same-character reload is clean, the trail cache
  is reset on load (a bug fixed long ago), and the engine's delayed advance
  is guarded by `done`. What remains is the hand-off: the last banish of a
  stage leaves the engine celebrating with the whole path lit, and if the
  new run's first target is the character already loaded, `retarget()` has
  nothing to change. `restart()` now reloads a celebrating engine, and the
  stray test conjures あ then restarts on it. If the path shows up again, a
  screenshot is the next step.
- The engine's own advance after a conjure — `if(done) load(idx+1)` after
  1.9s — was checked on the way: the field's reload clears `done` first, so
  a stroke begun on the next character within those 1.9s is safe.
- **A stale score, found by the flake.** When the hand had nothing to note
  (a conjure with no ink) it left the previous record in place, and the
  field, which pays a landed trace by the hand's last record when the
  character matches, paid from the previous trace's score. Only a test can
  conjure with no ink, but the record is cleared now. `field.test.mjs` still
  fails about one run in six on the 3-hit farang, alone or under the suite;
  that one is timing in the test's own clock and stays on the list.

## 2026-09-23 — Stroke order and the font, checked against the textbook

- The maintainer, with Genki I's charts (hiragana p.296, katakana p.300):
  "we should probably check if the stroke order is correct and the font
  type is what we are learning in this class."
- **Order and direction: 92 of 92 agree.** Counts were compared by script
  (all 46 + 46 match the chart's numbering); order and direction by eye,
  from `build/book_chart.py`'s rendering of our book beside the pages. The
  cells that textbooks differ on were looked at one by one: そ (Genki: one
  stroke, ours one), ふ (four, four), き and さ (the hook separate, as
  KanjiVG has it), も (vertical first), よ (the short stroke first), and in
  katakana シ/ツ and ソ/ン (the direction of the long stroke), ヒ (the
  short stroke first, right to left), ネ (four), ホ (four), ヲ (three).
- **The font.** Genki's charts are set in a textbook face (教科書体). What
  the tracer asks the hand to follow is not a font at all but KanjiVG's
  centrelines, which follow textbook forms (CLAUDE.md, "the hook problem");
  that is why the book agrees with the chart. Klee One, the trace font
  drawn beside it, is the closest textbook-like face on Google Fonts, and
  Noto Sans JP is shown small as the print form. No change needed.
- `book_chart.py` stays for the next realm: a kanji pack's book gets the
  same chart before it is trusted.

## 2026-09-23 — Progress goes the way the stroke goes (hiragana v0.1.49, katakana-game v0.1.12, vocab v0.1.27)

- **The maintainer, on v0.1.48 with a finger:** "I still think this size
  isn't suitable for fat fingers. I am headed towards a loop, it'll track
  multiple points and jump to complete."
- **Measured, and size cannot fix it.** On a 390px phone the sketchbook is
  the phone's width whatever its height. At today's largest size the ink of
  あ is 105px and the loops of ね, は and ほ are 18px; at 60dvh and size 0.9
  they are 26px. A fingertip is 50px and its reach 35-43px, growing with
  the size. Every point of a loop is in reach at once, so the scorer could
  not see whether the loop was drawn, and the LOOK window credited its far
  side the moment the finger approached.
- **The heading gate.** The pen's motion, smoothed over its last samples, is
  kept beside travel. Progress advances only through points whose tangent
  agrees with it (dot product above zero). A still pen advances nothing.
  Cutting across a loop advances only its near half; going round it
  advances all of it. Pen-down is let in a few points ahead, so a lift
  mid-stroke lands without a zap. Both the drag walk (guided) and the
  window search (everything else) honour it. `headingGate` in the pack,
  on by default, because the pen on a phone has the same problem at a
  smaller scale (reach 25px, loops 15px).
- **Checked.** Honest traces at every size (the size test's wobble did not
  trip it), the tail guard plain and eased, and a new check on め: the pen
  drawn to the mouth of the loop and then straight across it is credited
  less than the loop; a still pen on the far side advances nothing; the
  same pen going round the loop draws the stroke.
- What the gate cannot do is make a fingertip place a point inside an 18px
  loop. It makes the scorer honest about it. Whether the loops of ぬ め は
  ほ are traceable by finger on a phone at all is now a question for the
  hand, and the ratings page will say.

## 2026-09-23 — Guided is a sandbox; the finger after the heading gate (hiragana v0.1.50, katakana-game v0.1.13, vocab v0.1.28)

- **The maintainer, after a second finger session:** "guided is a lost cause
  for grading based on what I'm seeing. Maybe in terms of game dynamics, we
  leave that in the realm of sandbox practice. Guided should not allow the
  player to progress the game. But we're seeing a bit better results."
- **The better results, measured.** Finger on the loop characters (ぬ め は
  ほ ね よ ま む): before the heading gate, overshoot 0.61 of a stroke and
  travel 1.38x the path; on v0.1.49, overshoot 0.08, travel 0.99, coverage a
  median 1.00. Finger in medium on v0.1.49: 98 traces, 13 fizzles, coverage
  1.00, overshoot 0.11 — the finger now traces medium about as cleanly as
  the pen did. Guided by finger stayed where it was (overshoot 0.34,
  travel 0.98, a third of records missing strokes the drop rule took): the
  light is dragged, not drawn, and grading a drag was never going to say
  much about a hand.
- **So guided holds no stage and pays no 魂.** `easyFrom` is 1, guided's
  `tama` is 0, the start page says "practice only", the ending says nothing
  here counts. Any stage can still be practised in it, from every row, and
  the handwriting is still recorded. Easy is the first mode that counts.
- The CLAUDE.md decision of v0.1.45 ("guided only gets you so far") becomes
  "guided gets you nowhere in the game, and everywhere in practice".

## 2026-09-23 — Two modes, bosses, and a stroke you can see finish (hiragana v0.1.51, katakana-game v0.1.14, vocab v0.1.29)

- **Easy is gone from the games.** The maintainer, after rounds on medium:
  "noticed how crappy easy mode is, and it's pretty much guided mode.. so..
  let's just remove it. only score you can get is from medium." The shells'
  tables have guided (practice) and medium (the game); hard stays locked as
  the name for what a boss asks. The engine's own easy mode remains for
  the workshop. A saved start page that said easy falls back to medium.
  Every stage counts at medium (`needs()` says so; `easyFrom` and
  `mediumFrom` are gone from the config).
- **Bosses.** "Boss fights are when the trace disappears ... perhaps not
  completely blank canvas, just less help. Otherwise I feel like I'd be
  stroking over and over for no reason but to fill the template." The last
  farang of a stage is its boss: `bossHp` (2) more hits, a "将 · less help"
  label, and its character shown as `SHADOW_MODE` `faint` — the medium
  centreline at a third of the light, with the start dot of the current
  stroke kept, which the guide used to draw only in guided. The path is
  enforced underneath as ever; what the eyes lose is where the stroke goes
  after it starts. The full shape returns for the next farang, decided from
  who carries the character rather than on a reload, because the farang
  after a boss can carry the same character and then nothing reloads.
  Words are not bossed. This is not hard mode's scorer, which is still not
  built; it is medium with less to look at.
- **A finished stroke is unmissable.** "I really rely on haptics.. without
  it, I wouldn't know if the stroke is complete. maybe we should add
  something visually obvious." The shine along a finished stroke sat under
  the fingertip and the buzz is 12ms on devices that have one. Now the
  stroke's end throws a ring (18 → 88px, teal, on the fx canvas, riding the
  particle frame and the comet frame) and the sketchbook's frame flashes
  (`#stage.lift`, .45s). Both are bigger than a finger.
- The stray test gained a boss block (the last of twelve spawns is the boss,
  takes three hits, is shown faint when targeted, and the shape returns
  after it) and sets the drop rule explicitly, since the games now open on
  medium, whose rule is restart.

## 2026-09-24 — The hook, the shake, the retry, and the reflection (hiragana v0.1.52, katakana-game v0.1.15, vocab v0.1.30)

- **The session's numbers.** 386 finger traces in medium on v0.1.50-51, 65
  fizzles. ふ fizzled 19 of 41 times, then き 8 of 30, え 8 of 18, も 6 of
  24. The commonest fizzle is two strokes of four: ふ's hook. "It always
  takes me a trace, and poke until it allows me to get to the next stroke."
- **The hook was the end floor.** A stroke's end counts as reached within
  `max(END_MIN, min(R, 12% of the stroke))`, and END_MIN is 2% of the canvas
  — 8px on a phone. A pen lands there; a fingertip does not, so the finger
  traced the tick, watched it light, and had to poke its end. The floor is
  per hand now (`endFloor`: pen 0.02, finger 0.045 — the same 18px the
  reach floors at), for the start as well as the end. A tick shorter than a
  fingertip is a flick for a finger: it must be started, travelled in its
  direction past the heading gate, and reached; it cannot be required to be
  drawn to 80%, and the tail guard's eased copy does not model the finger
  floor. That guard covers the pen. Said plainly here so nobody reads the
  green run as covering a finger on ふ.
- **The offset after a fizzle was the shake.** `fizzle()` animates the
  sketchbook with a translate, and a pen that came down during the 0.4s of
  it read its position through the shifted rect. `pos()` now adds the
  stage's current transform back. "Sometimes" was "within 0.4s of the buzz".
- **The lit path after "again" was the half-traced character.** Reproduced
  once by the maintainer on the retry of a lost round: the ward fell
  mid-stroke, `restart()` retargeted to the same character with `done`
  false, and nothing reloaded. A run now starts on a clean character
  whenever anything was in progress, and the stray test restarts mid-trace.
- **The reflection, used against them.** "I always mess up も ... I feel
  like that reflection should be used against me." Half of spawns
  (`biteRate`) come from the characters the ledger marks shaky, which is
  the spaced-repetition design of the lore finally steering the roster
  rather than only avoiding mastered characters.
- "My own game is beating me": no run since the pull reached a boss. The
  stage's twelve farang at 46dvh by finger is a starting position, not a
  tuning; the numbers above are what to tune from.

## 2026-09-24 — Past the end, the stroke starts over; the ring goes (hiragana v0.1.53, katakana-game v0.1.16, vocab v0.1.31)

- **The maintainer, after rounds on v0.1.52:** the boss's faint template is
  enough; "that circle is annoying"; "ふ feels way better"; and "sometimes
  I'll mistrace some chars slightly, like just below or just above the end
  point, and then I poke to finish it. Maybe we could make them start the
  stroke over if on the first attempt passes beyond the end point and
  still is not complete."
- **The rule.** Near a stroke's end (the high-water mark within two slacks
  of it), then beyond the end along the stroke's own direction by more than
  `pastEnd` (1.5) end tolerances without having reached it: the stroke
  starts over. Progress back to its start, its coverage cleared, the stroke
  in hand dropped at the lift and not recorded, a zap and a toast. Not the
  character — the strokes before it stand. Guided is exempt: its end is
  reach. The stray test drives a pen to three points short of あ's first
  end, then past it to one side, and checks the stroke restarts, the ink
  is discarded, and the stroke drawn again completes.
- **The ring is gone.** The frame flash stays; the shine along the stroke
  stays. A signal that annoys is worse than none.
- **What the agents are doing, asked point blank.** Nothing in this loop
  until asked. The arithmetic the analysis has run on all day is the
  agents' own module (`events.py`, `system1.py`), called by hand; the
  analyst agent was run once over this pull and quoted the tools' numbers
  correctly (ふ 39% fizzle, 2.81 zaps; も, え, さ, せ; き the least
  consistent), then dressed them in explanations it could not know
  ("finger-width contact blurs the close-loop endpoints") and correctly
  refused the before/after question because the v0.1.52 traces are not in
  the table yet. Laya's labels are stale and uninformative. mem0 holds
  four notes. The honest accounting for the report: the harness paid for
  itself as a measuring instrument and a labelling loop; the LLM as
  analyst is a narrator of numbers a script produced; the System 1 seat is
  still empty.

## 2026-09-24 — The fact fence: what the analyst measured, and what it made up (agents/hito_agents/factcheck.py)

- **The maintainer: "we can fact check the analyst."** The one place Laya
  fits is the analyst's prose, not the ink. Every answer is split into
  sentences and each is sorted — measurement, comparison, caveat, cause,
  suggestion, other — and every figure in it is checked, with no model,
  against the numbers the tools returned this invocation (39% for 0.39,
  rounding allowed, small integers pass as ordinal talk). Causes are marked
  "(guess)", figures the tools never returned "(unverified)", and the ledger
  keeps the tally per answer. A memory write that is a cause is refused at
  the hook: memory takes what was measured. The analyst is told so, and
  told to mark its own guesses.
- **Laya against a rule, on prose.** On the eight sentences of the first
  answer checked, Laya agreed with the hand's labels four times, a keyword
  rule seven — but the rule was written after reading those sentences.
  Unlike on the ink, Laya's probabilities carry signal here: 0.99 on the
  sentence that says "because", 0.3 where the kind is arguable; it reads
  table rows as caveats. So the rule decides by default, Laya decides with
  `HITO_FACTCHECK_MODEL=laya`, and either way both verdicts are logged for
  every sentence of every answer. Live on Bedrock, first run with Laya
  deciding: model Laya, 3 of 12 sentences agree with the rule; causes 2, unverified 0. Both causes were caught, the analyst marked one of them
  as a guess itself, and what reached memory was "ふ medium-finger fizzle
  rate = 39%" and nothing else.
- This is the course's hooks and System 1 in one piece, doing a job the
  session showed needed doing. The comparison it logs is the experiment:
  when there are a few hundred sentences, Laya's kinds and the rule's kinds
  against a hand's can be scored, and calibrated against `ece_score`.
- **Late arrival, and the ふ before-and-after.** The maintainer's v0.1.52
  rounds reached the table an hour after they were played — the outbox
  flushes when it can, and no sign-in is involved. Finger in medium, all
  characters: v0.1.50 386 traces, 17% fizzled, 1.47 zaps a trace, overshoot
  0.13; v0.1.52 62 traces, 10% fizzled, 0.87 zaps, overshoot 0.08. ふ on
  v0.1.52: three of three landed with no zaps, against 19 of 41 fizzled
  before — three is not a verdict, but it is the right direction. も still
  fizzles one in four. The runs: stage 7 with 30 farang fell four times
  and was held once; stage 8 with 33 farang fell three times. No boss has
  been reached because the boss is the last farang of the stage.
  `stages.count` 12 and `countStep` 3 are the numbers that make stage 8 a
  33-farang wall for a finger; they were set by arithmetic, not by a hand.

## 2026-09-24 — Direction, from the maintainer, not decided: the gauge, the queue, farang that learn

- On game feel after v0.1.53: "I like that I'm focused on writing script.
  But I'd like to look up once in a while to be visually stimulated by my
  character turning farang. Maybe the tracing fills up an energy gauge. Not
  necessarily the order of the closest farang with the script, but in the
  order of our analyst feedback of which chars make me struggle. We can
  even make tiered levels of farang. At first yes, they are only capable of
  shouting the character out incorrectly. They start being able to shout
  small words with the learned hiragana. Still farangy, but they're
  learning."
- **The gauge.** The run's ink already accrues per trace but lives in the
  upgrade strip nobody watches mid-trace. As a gauge on the seam, filling
  per landed stroke, with a *release* when full — every lit character
  throws at once, the field pauses a beat — it makes the look-up moment a
  reward and a rhythm: trace, look, trace. Fits "nothing draws for you":
  the release only spends what the hand lit.
- **The queue by struggle.** `biteRate` (v0.1.52) already draws half the
  spawns from the ledger's shaky characters. The next step is the
  sketchbook queuing by struggle rather than by the nearest farang; since
  what is drawn hits whichever farang carries it, proximity stops
  mattering, and the field becomes a display of what the analyst thinks
  the hand should practise.
- **Farang that learn what you learn.** A twist on "the farang grow up"
  (CLAUDE.md, decided in direction): tier one shouts single characters,
  wrongly; tier two shouts small words made only of kana the player has
  kindled — learning from the player, accent intact. The decks exist, so
  this is a filter over them, and it guarantees a farang never carries a
  word the hand could not answer. Tiers keyed to the player's lit set
  rather than to the stage number.
- Then: "maybe like all strokes fill an energy gauge. Something like that
  is upgradable." Every stroke charges it, landed or not — the hand did
  the work either way. The gauge is a fifth axis for the upgrade strip,
  about rhythm rather than power: capacity and charge per stroke within
  the run, like quick and bright; what a full gauge releases as a lantern
  that lasts, like hearts and lights.
- And: "the other upgrades I didn't even notice much. Like ok the health
  one cool. But the more ink or whatever didn't really make me more
  urgent." Quick, bright and shove act above the seam while the eyes are
  below it; nobody sees them work, so buying one feels like nothing. Mend
  acts on hearts, the one number that hurts. So the strip should fold
  into the gauge: those three become what a full gauge releases, and the
  upgrade shows itself in the moment the hand looks up. Urgency has to
  come from the seam too — a gauge that drains on a breach, or a release
  needed before the next wave.
- "So we got hit points and mana" — the ward and the gauge, hearts and
  墨. And: "if a user wanted to farm a level, they would have to make sure
  their energy gauge is big enough to last the time they are away?" Yes,
  in spirit: active fills, idle spends, the candle of the lore. Two rules
  from before the gauge hold it: nothing happens while the app is closed
  (a run is live; away is between runs, computed on return from a
  timestamp), and away gains are the server's to compute, never the
  client's to claim. The gauge only ever fills by hand.
- None of it built. Recorded so the reasoning survives.

## 2026-09-24 — The tower (hiragana v0.1.54, katakana-game v0.1.17, vocab v0.1.32)

- **The maintainer:** "Should we go in the tower direction then? There is no
  completing a level. You just keep going until the swarm consumes you." And,
  on the boss: "throughout round 10, all the characters you stroke are
  affected by the debuff from the boss."
- **What changed.** The stage table, its count and gate, `stageNo`, the
  win, `held`, `needs`/`counts` and the stage buttons are gone. A run is
  waves without end until the ward falls. Rows of the chart open every
  `rowWaves` (10) waves, counted from the furthest wave the realm has ever
  reached (the hand's ledger already kept it) or the current run's,
  whichever is further — so the curriculum gate is distance now, and it
  opens live during a deep run. Every tenth wave is a boss with `bossHp`
  extra hits, and while any boss lives the shape is faint for every
  character; `applyShadow()` decides it from `bossAlive()` on retarget, on
  spawn and on a kill. Tama pays by traces and waves, with no "held" bonus;
  the lantern workshop is unchanged; the gate is not for sale. A guided run
  is kept in the ledger as `practice` and never a furthest wave. The ending
  says "the ward fell · wave N · your furthest yet"; the start page says the
  furthest wave and when the next row opens.
- **Why the data said so.** The last eight medium runs fell at 30 and 33
  farang, with one held stage among them. As waves those are a record that
  only rises. And no run had reached a boss because the boss was the last
  farang of a stage nobody finished; now one arrives at wave 10.
- The field test's stage and gate blocks are tower blocks now: rows open by
  wave and by record, no win, one boss per ten waves that dims the shape for
  all and lifts it when it falls, a lost run pays and keeps its wave, guided
  pays nothing and sets no record. The config key is `tower`; `stages` is
  read as an alias.

## 2026-09-24 — The dashboard (hiragana v0.1.55, katakana-game v0.1.18, vocab v0.1.33)

- **The maintainer:** "Instead of having the gauges show right at the center,
  create a dashboard for the hp and mana. We could even start our tabs for
  the different kinds of upgrades ... The crazy part of the game is knowing
  when you can relax the stroke practice and tab out into your upgrades."
- **Built.** A bar on the seam between field and sketchbook: hearts (the
  ward, with the empty ones dimmed), 墨 (the run's ink), 魂 (the purse) and
  the wave, and two tabs. 技 opens this run's skills — the upgrade strip
  that used to sit across the top of the field, where nobody looked. 灯
  opens the lantern workshop that was only on the ending page, so what
  lasts can be bought mid-run from the 魂 already in hand. The panel covers
  the field, not the sketchbook, and the run does not pause: the waves keep
  coming while you shop. The hitodama dash on the canvas moved up to sit
  above the bar. The 技 tab lights up when something is affordable.
- Mana proper — the gauge every stroke fills, and the release — is still
  the note of 2026-09-24. The bar has its place kept: 墨 sits where mana
  will, and the release is what 技 should become.

## 2026-09-24 — Bars, and 気 (hiragana v0.1.56, katakana-game v0.1.19, vocab v0.1.34)

- **The maintainer:** "Let's not do hearts. I like bars. For both the life
  and energy for casting. The stroke does not depend on which enemy is
  present. All strokes go into one bag of energy." And: the hiragana and
  the romaji stay as they are — the voice-over comes later.
- **気.** One bag per run (`energyMax` 24, `energyStart` 6). Every stroke
  the hand completes fills it by `energyPerStroke` (1): the field wraps the
  engine's `shine()`, which is the stroke-complete and reaches the layer as
  a global; a conjure credits any strokes the shine did not, so a trace is
  worth its strokes however the stub scored it. Every wisp a lit character
  throws spends `castCost` (2): a lit character with an empty bag waits.
  Lights still say which characters can answer for themselves; 気 is what
  they answer with. Nothing fills it but the hand — the rule of the lore,
  now a number.
- **Bars.** 命 for the ward and 気 for the bag, on the seam, with the count
  in small figures; hearts are gone. 墨, 魂, the wave and the two tabs stay.
- The lights' tests are about targeting, not fuel, so their `fresh()`
  fills the bag; the bag has its own test: a run starts with 6, three
  strokes conjured add 3, it overflows at 24, a cast spends 2, an empty bag
  casts nothing, two 気 cast once.
- Not yet: a lantern for a bigger bag, and the release — a full bag thrown
  at once, the moment to look up. That is the next of the gauge notes.

## 2026-09-24 — The front page is a level switcher (hiragana v0.1.57, katakana-game v0.1.20, vocab v0.1.35)

- **The maintainer:** "Let's makeover the front page. No more toggles to
  hiragana, flashcards, or katakana. We just get right into the game. So
  basically a level switcher. We can go like every 100 rounds you unlock a
  new level."
- **Built.** `index.html` shows 人, Begin, and the levels in order: ひらがな,
  then カタカナ, which opens when ひらがな's furthest wave — the hand's
  ledger has kept it for good since v0.1.43 — reaches `LEVEL_WAVES` (100).
  A locked level says what opens it; an open one says its furthest wave.
  Begin goes to the level you were last in if it is still open, else the
  furthest open one. The next level (kanji, one day) is a line in `LEVELS`
  with the realm it keeps its wave under.
- The three game packs lost their `realms` rows, so the in-game start pages
  no longer offer the other realms: the front page is where a level is
  chosen. The flashcards (`vocab.html`) are practice, not a level, and are
  off the front page; the workshop stays as a footer link. Both still build
  and both still open from a double-click.
- 100 waves is the maintainer's number and a first one: the furthest wave
  in the table today is 33.

## 2026-09-24 — What the tracer asks for is its own (hiragana v0.1.58, katakana-game v0.1.21, vocab v0.1.36)

- **The maintainer, four things:** Chrome shrank the title page after sign-in
  — "so let's have the game begin from the title page. The practice button
  can exist on title." "Boss mode still has a guide circle." "Too much repeat
  on the hiragana words. I wrote tsu like four times in a row. Don't base
  what I trace on what enemies populate."
- **The queue.** The sketchbook asked for whatever the nearest farang
  carried, and with spawns biased toward shaky characters that meant the
  same one four times running. Now a character realm asks from its own
  queue over the open rows — shaky first, then least recently written by
  the ledger's `last`, random within ties — and nothing comes round again
  until `noRepeat` (4) others have. What is drawn hits whichever farang
  carries it (`bearer()`), nearest first, or hits nothing and is kept as a
  light; the fallback that sent a shot at the locked farang whatever was
  drawn is gone. Arrivals and breaches no longer swap the character under
  the hand, which closes a whole class of "the glyph changed under my pen"
  bugs the tests used to guard one at a time. A tap on a farang asks for
  its character (`ask()`), and the tests aim the tracer the same way. Word
  realms are untouched: a word is walked in order.
- **Begin from the title.** `?go=medium` and `?go=guided` start the run at
  once; the title page's Begin and its new Practice button carry them, and
  the URL is cleaned after. The game's own start page still exists behind
  the ending's "difficulty and the sign". The sign-in shrink in Chrome was
  the address bar returning after the redirect; the title page is the only
  page that signs in now, and a game is a fresh navigation.
- **The boss shows its faint shape and nothing else.** The start dot was
  kept as a hint in v0.1.51; it read as a guide circle. Gone.
- Nine field tests were written when the tracer followed the nearest farang
  and are rewritten for the queue; the run.sh homepage link check now
  strips a query.

## 2026-09-24 — The lag (hiragana v0.1.59, katakana-game v0.1.22, vocab v0.1.37)

- **The maintainer, on v0.1.58:** "Seems a bit laggy too. This round the
  trace seems to think my finger is a couple cm away from my actual touch."
- **The lag was v0.1.52's shake compensation:** `pos()` read the
  sketchbook's computed transform on every pointer sample, which forces a
  style recalculation per sample — a phone at 120 samples a second felt
  it. It now reads it only while the shake is running (`shaking`, set by
  `fizzle()`, cleared on `animationend`).
- **The offset is not reproduced.** The sketchbook carries no transform at
  rest, and a size observer already re-syncs the canvas when its box
  changes, so a stretched canvas is not it either. An autostarted run now
  re-sizes the field and the sketchbook right before it begins, in case
  the layout had not settled at script time. Two questions went back to
  the hand: is the offset there from the first stroke or only after a
  fizzle or a zap, and is it the same direction every time.
- On v0.1.59, played "as accurate as I can": the offset did not come back
  ("might've been operator error. At least my hiragana is looking better").
  Closed as not reproduced; the lag fix stands on its own.

## 2026-09-24 — Intent: the upgrade tabs (hiragana v0.1.60, katakana-game v0.1.23, vocab v0.1.38)

- **The maintainer:** "I'd like to implement our upgrade tabs. We should
  decide on some simple things. Like raising cast power. 'Intention' maybe.
  Following that idea that we forge and sharpen our intent to cut through
  farangs' mindset of sticking to their old ways."
- **技, this run, bought with 墨:** 意 intent (every light cuts one hit
  deeper per level, max 3 — a boss at three hits falls to two casts at
  intent 1), 早 quick (as before), 息 breath (every stroke fills 気 by one
  more per level, max 3), 押 shove and 守 mend (as before). Bright is gone:
  "a trace lights one more" was the weakest thing on the strip and intent
  does its job with a point.
- **灯, lasting, bought with 魂:** 器 vessel joins heart, lamp and inkwell —
  the bag of 気 holds six more per level, max 3.
- Every one of them still multiplies the hand's strokes; none writes a
  character. Costs: intent 12, breath 9, vessel 25 — arithmetic, not play.
- The tests: intent's hit takes two, breath's two strokes fill four, a
  vessel grows the bag by six, the ceiling and the maxed button as before.

## 2026-09-24 — Direction, not decided: persistence and motivation

- The maintainer, after the intent tabs: "Persistence may be another tab..
  where we develop defensive upgrades. And motivation.. where it sort of
  resembles, fall seven get up eight."
- **耐 persistence** (墨, this run, defensive): 守 mend moves here, leaving 技
  purely about cutting; 壁 wall (a breach costs less, or the farang slow in
  the last stretch); 癒 tend (a life back every so many waves held); 鎮 calm
  (a breach does not drain 気, once that drain exists).
- **志 motivation** (魂, lasting): 七転び八起き as the between-runs economy —
  what a fall leaves for the next climb. 起 rise (the next run starts with
  the 気 the ward fell with, capped); 継 carry (one lit character keeps its
  lights through a fall); 八 the eighth (falls counted, and the run after a
  fall pays a little more 魂). The lanterns fold into 志: they are lasting
  too.
- Four tabs then: 技, 耐, 志, and the lanterns inside 志. Two currencies,
  two halves of the screen. Not built.

## 2026-09-24 — Persistence: the farang bite harder, and 耐 stands against it (hiragana v0.1.61, katakana-game v0.1.24)

- The maintainer, on the persistence tab: "Every increment in round they get
  stronger. Both in attack and health." Health already climbed (`hpEvery`).
  Attack now does: a breach costs the ward `biteFor(wave)` — one life at the
  foot, one more every `biteEvery` (20) waves up to `biteMax` (4), a boss
  `tower.bossBite` (1) more. A breach event records its `bite`. Words bite
  like anything else: a word at the ward is a word not answered.
- **耐 persistence**, the second tab bought with 墨 during the run: 守 mend
  moves here from 技 (which is now purely intent: 意 早 息 押); 壁 wall (a
  breach costs one less, never below one, 3); 癒 tend (a life back per level
  every `tendEvery` (10) waves held, paid when the wave comes, 3). Upgrades
  carry a `tab`; `freshUpg()` builds the empty set from the table so a new
  upgrade cannot be forgotten in a restart.
- **A bug found by looking: the dashboard's tabs were never visible.** The
  shell hides the workshop's furniture with `body.field .tabs { display:none
  !important }`, and the dashboard's tab strip was `<span class="tabs">`. So
  from v0.1.55 to v0.1.60 the 技 and 灯 buttons existed in the markup, passed
  every test, and were invisible in every real browser. The stub DOM has no
  stylesheet. Renamed `dash-tabs`; and the engine's generic `button{flex:1;
  min-width:88px}` had to be overridden too, or three tabs ate the bars at
  phone width. Checked with headless Chrome at 390px, sharing off. This is
  the CSS cousin of the "a layer must not reuse an engine name" rule, and
  the "look at a running build before shipping UI" rule earning its place:
  a layer's class names are engine names too.
- What this may explain: "the other upgrades I didn't even notice much" and
  the request to "implement our upgrade tabs" after they had shipped.
- 志 motivation is still direction. Rethought: lights already survive the
  ward falling, so "one lit character keeps its lights through a fall" is
  already true and is not an upgrade. What is left for 志: the next run
  starting with the 気 the ward fell with, and a run after a fall paying
  more 魂. Neither built.
- Test: `field.test.mjs` reads a bite at the foot, at `biteEvery`, past the
  ceiling, a boss's; a wall's discount and its floor; a real breach taking
  what `biteFor` says; tend at a tend wave; the 耐 strip and tab. The 気
  fill test now reads before the wait, like breath's: a light may spend some
  on a farang carrying the character.

## 2026-09-24 — Motivation is currency gain: 志 (hiragana v0.1.62, katakana-game v0.1.25)

- The maintainer: "Motivation tab should be upgrades for currency gain." So
  志 is the third in-run tab bought with 墨, and the three are the way a
  tower is run — 技 cuts, 耐 lasts, 志 earns. 勤 diligence (every trace pays
  one more 墨, 5), 収 harvest (every farang the lights finish pays one more
  墨, 5), 起 rise (the fall pays `riseStep` (0.2) more 魂 per level, 3 —
  七転び八起き kept as the one that pays out when you get up). None writes a
  character; rise is worthless in guided because guided pays no 魂, which
  is right.
- The earlier 志 sketch (the next run keeping its 気, a run after a fall
  paying more) is retired by this: the maintainer's word for motivation
  was currency, and rise is the piece of it that survived.
- Four tabs and two bars on a 374px seam: spacing tightened (gap 6, tab
  padding 7px, bar min-width 46). Checked at 390 and 360px; 灯 was off the
  right edge before the tightening. The stubbed DOM would have passed it.
- Test: diligence on a clean trace, harvest on a light's banish, rise on a
  fallen run's 魂 against the same run without it, and the tab on the seam.

## 2026-09-24 — The sketchbook is a tab (hiragana v0.1.62, katakana-game v0.1.25, same release)

- The maintainer: "I also meant the tracing is another tab. So the player
  has to wait for opportunities to switch out to upgrade." So the seam's
  tabs are 筆 技 耐 志 灯, and a shop stands where the sketchbook stood,
  in its own box (measured as it is hidden, so the page does not jump).
  While a shop is open there is nothing to trace on: the lit characters'
  own lights are all that holds the ward, and the farang do not wait. That
  is the cost of an upgrade, which is what the maintainer wanted the
  decision to be — "knowing when you can relax the stroke practice and
  tab out".
- A shop does not open under a pen that is down (`tracing()`, including
  the hold after a lift): lift, and find the gap. A run's start and end
  close it.
- The field test's own DOM stub discarded every property write (`set(){
  return true; }`), unlike `dom.mjs`; it keeps them now, or a `hidden` the
  shell sets could not be read back. `F.sketchbook` hands the shell's own
  element to a test, because the stub gives a fresh one to every lookup.
- Five tabs on a 344px seam: the wave's label is 波 now, the bars go down
  to 40px and the spacing is at its tightest. Checked at 360 and 390px in
  headless Chrome; below 360 the last tab will clip, and the next thing to
  give would be the numbers' labels.

## 2026-09-24 — The lag, and the wall at wave 30 (hiragana v0.1.63, katakana-game v0.1.26, vocab v0.1.39)

- The maintainer: "Still a touch laggy. The game's current state I'll never
  reach the next advancement."
- **The lag.** The field broke CLAUDE.md's oldest performance rule — "no
  per-frame shadow blur" — ten times a frame: the ward's pulse (26px), every
  farang (10-20), every lit marker, every wisp (22), every thrown character
  (18), every reading (16), every lit pip. A blurred shadow is rasterised
  afresh on each draw, on a canvas a phone wide at 3x, sixty times a second.
  `glowAt()` now paints a radial gradient once into a 64px sprite per colour
  and stretches it; the solid shape goes over it as before. Both canvases
  are capped at 2x (the sketchbook copies its whole ink twice on every pen
  move; 3x is 2.25x the pixels for nothing a reader could see). Not measured
  on the phone — there is no phone here — so this is the removal of the
  known offender, not a proven fix. A `//` comment in the engine's one-line
  `resize()` swallowed the rest of the line and set W and H to nothing; the
  hand and stray tests caught it before the build shipped.
- **The wall.** 61 runs in the events table. Medium by finger ends at wave
  27-43, every run 80-105 s, ~3.6 s per trace, and until yesterday no run
  had bought a single upgrade (the tabs were invisible). The spawn floor of
  1.8 s was reached at wave 24 and with hp 3-4 by then, holding needed two
  hits a second against a hand that supplies 0.28. Nobody could pass wave
  ~35 whatever they learned, and the next level sits at 100. Anchored to
  the measured hand: `spawnMin` 3400 (a farang per 3.4 s, about one trace),
  `spawnRamp` 45 (the floor at wave 40), `hpEvery` 30, `biteEvery` 30. The
  arithmetic says a hand alone holds to ~30, hand plus lights to ~60, and
  100 wants lanterns and a lit chart — which is what the lanterns are for.
  A guess with a reason behind it, to be corrected by the next runs.
- Katakana's pace was already gentler (words); left.

## 2026-09-24 — 仏 and 鬼: an agent to buff, an agent to nerf (hiragana v0.1.64, katakana-game v0.1.27)

- The maintainer, after v0.1.63: an iPhone was "almost like butter compared
  to my pixel 9", and "wouldn't it be cool to have an agent to buff and one
  agent to nerf?"
- **The phone.** Two phones, one build, opposite reports: the raster path,
  not the game. There is no Pixel here, so the build now counts its frames
  — every run's record carries `frames` (n, over 25 ms, over 50 ms) and
  `plat` (the platform string, which is a device class and not a person) —
  and `state_of_play` sums them. The next Pixel run will say what it saw.
- **The pair.** `agents/hito_agents/balance.py`: 仏 hotoke, the learner's
  advocate, and 鬼 oni, the farang's, two Strands agents with the same four
  tools (the state of play, the current config, the pace model, propose)
  and opposite standing orders. `pace.py` is the judge: need against
  supply wave by wave (hits the farang need a second vs. the hand's trace
  rate plus the lights its 気 can pay for), the wall, and the predicted end
  — farang by farang, what the hand cannot answer in the gap reaches the
  ward and bites. Calibration: the config before v0.1.63 ends near 25 here
  against measured 27 (median) and 43 (furthest). Defaults are read out of
  `shell_field.py` with a regex so the model cannot drift from the game.
  The judge keeps only a value that holds a bare hand's predicted end
  inside 55..120 (100 is the next level; lanterns should be what gets past
  it), closest to the middle. Proposals outside the bounds are refused
  before anyone argues.
- **First live run** (Bedrock, Sonnet 4.6, one call each): 仏 proposed
  hpEvery 45, spawnMs 5800, spawnRamp 30 (predicted end 69). 鬼 proposed
  hpEvery 60, biteEvery 40, castCost 3 — and called the first two "the wall
  moved out", which is a loosening dressed as a nerf; the LLM argued its
  brief and lost the thread of its own side. The judge took hpEvery 60 (end
  59), spawnMs 5800 (63), spawnRamp 30 (72), biteEvery 40 (78) and kept
  castCost. Applied by hand with `--apply`: the hiragana game's pace is now
  that verdict, predicted end 78 for the measured hand against 45 for
  v0.1.63's guess. For the report: the arithmetic is the value, the
  advocates choose knobs and narrate, and a nerf agent that argues a buff
  is exactly why the judge is not a model.
- The pack's `hand` block came back from `--apply` re-indented (json.dumps);
  cosmetic. The judge's tests are pinned to a fixed base config, because
  the agents edit the pack the tests would otherwise read.

## 2026-09-24 — The loop runs itself, and the ceilings go up (hiragana v0.1.65, katakana-game v0.1.28)

- The maintainer: "I don't feel like running anything manually. Can't we
  sort of set up a hook to balance the game after a valuable amount of data
  has been provided? And in this state, we end up maxing out the upgrades
  so early. And I can't make it to 100."
- **The hook.** `balance --auto` and `.github/workflows/balance.yml`, daily.
  A valuable amount of data is twelve medium runs on the *current* build —
  runs now carry `v` — and a build is judged once: the verdict is committed
  as `agents/balance/v<version>.json`, applied, bumped, rebuilt with
  `build/release.sh`, checked with `run.sh`, pushed. Nothing to change is
  still a verdict, so a build that is fine is not judged again tomorrow. The
  Fence still holds: the agents write under `agents/out`; the applying and
  the bumping are `auto()`, which is code with a test, not a tool a model
  calls. Two repository secrets are needed (Appwrite rows-read key, Bedrock
  key) and are the one manual step left; they are the maintainer's to add.
  The v0.1.63 verdict is committed as the first entry so the ledger of
  verdicts starts where the loop did.
- **The ceilings.** upgradeRamp 1.85 in the hiragana game and every cap
  raised (intent 5, quick 8, breath 5, shove 8, mend 8, wall 5, tend 5,
  diligence 8, harvest 8, rise 5). At 1.6 with caps of 3-5 a long run bought
  everything by its middle; now the top levels cost hundreds and a run ends
  with choices left. Not modelled by the judge, which knows nothing of 墨;
  it is the next thing pace.py should learn.
- **100.** The judge's band aims a bare hand's predicted end at 55..120 and
  the applied verdict predicts 78; the lanterns are meant to be the rest.
  Nobody has played v0.1.64+ yet, so "I can't make it to 100" is about the
  ramp before the verdict. If the next twelve runs still stop short, the
  loop will move it again — and if they do not reach 100 with lanterns
  either, the band's floor should rise, or the level gate should count
  something a learner can accumulate.
- `build/release.sh` exists now because the loop needed the release to be
  one command; the hand gets it too.

## 2026-09-24 — The tabs read, the bag releases, the door is answered (hiragana v0.1.66, katakana-game v0.1.29)

- The maintainer: "The tabs are not so obvious... Make the scratchpad tab
  more obvious by making it larger than its friends. Maybe add icons to each
  upgrade tab... Also, the way our base attacks things is sort of boring. And
  it targets weirdly allowing the closer farang to attack it."
- **The tabs.** On a phone they take a row of their own under the bars
  (`flex-wrap`, under 560px), so the bars get the width back too. 筆 is
  19px with a 2px border; 技 耐 志 灯 wear a sword, a shield, a five-yen
  coin and a flame — inline SVG in `currentColor`, so the theme table paints
  them and the theme test has nothing new to object to. Every tab has an
  aria-label saying what it upgrades.
- **The release.** A bag filled to the brim is thrown at once: every lit
  character at its nearest bearer, nearest first, until the 気 runs out;
  a ring leaves the ward; the phone buzzes. A tap on the ward throws what is
  there. Every stroke's 気 goes in through `topUp()`, whether it shone or
  was credited at the conjure, because the first version checked only the
  shine wrapper and the stub's conjure credits strokes the other way.
  Still nothing but characters the hand has written.
- **The targeting.** Since the queue (v0.1.58) the tracer is on its own
  character, so `locked` was stale in the character game and the old "leave
  the locked one to the hand" rule was mostly dead — and `F.target` in the
  old test set it as a side effect, which is why the test passed. The rule
  is now about the bearer of the character the tracer is on, and it has a
  limit: inside `rescue` (0.3) of the ward the lights answer that one too.
- **The door.** The real "weird" case was a farang at the door carrying a
  dark character while the queue asked for something else. `door()` is the
  one exception to the queue: a dark character inside `rescue` is what the
  tracer asks for next, and the queue resumes after. A lit one at the door
  is the lights' business and does not pull the pen.
- `burst` is an engine name; the field's is `flareAt`. The shadow test
  caught it before the build shipped, again.

## 2026-09-24 — Every upgrade wears a mark (hiragana v0.1.67, katakana-game v0.1.30)

- The maintainer: "the upgrades should include an icon by its side too.
  Since I don't know any kanji it's hard for me to decide what to upgrade."
  Which is the hero who cannot read, at the shop counter. Fourteen marks in
  `MARK`, inline SVG in `currentColor` (bullseye, bolt, wind, arrow into a
  wall, heart with a plus, bricks, medic's cross, ink drop, sickle, sunrise;
  heart, lantern, inkwell, jar). The mark leads, the kanji is 10px beside it,
  the English name and the blurb follow. The blurb had been hidden under
  560px since the strip sat at the top of the field; the shop has the
  sketchbook's box now, so it shows everywhere.
- Rule for the file: new UI that names a thing in kanji names it in a mark
  too. The tabs got theirs the release before.

## 2026-09-24 — Lost taps, and wave 230 (hiragana v0.1.68, katakana-game v0.1.31)

- The maintainer: "I noticed I had to tap a couple times before my tab
  would change. And right now it's hella OP lol. I got to like round 230."
- **The taps.** `renderDash()` replaces the seam's innerHTML whenever its
  markup changes — 気, 墨, the wave, the `can` outline — which during play
  is most frames, and `renderUpg()` does the same to the strips on every
  earn. A handler set on a button was set on an element that was often gone
  between finger-down and the click, and the click went nowhere. `tapOn()`
  puts one listener on the container (the seam, the panel) and acts on
  pointerdown, before any re-render can get between; Enter and Space still
  work. `touch-action: manipulation` on the buttons too, against the
  double-tap delay. The stub cannot dispatch an event, so `F.tap(sel)` hands
  a stand-in element with the selector's data attribute to the same
  handlers; the test taps 耐 open, re-renders, and taps it shut.
- **230.** Two causes, both mine. The v0.1.65 ceilings let intent reach 5
  and breath 5: six hits a cast on six 気 a stroke, thirty-six times a bare
  hand, and `hpMax` 5 meant the swarm stopped growing at wave 240 while the
  hand did not. Intent and breath are back to 3 (they multiply each other;
  the other caps stay), and the hiragana game sets `hpMax` 99 and `biteMax`
  6, so the swarm always wins in the end, which is what a tower is.
- **The judge was blind to it.** `pace.py` prices a bare hand — no
  upgrades, no release, no lanterns — and said 78 for the config that went
  to 230. It would have judged v0.1.67 "in band" and changed nothing.
  `calibration()` is the measured median wave over the model's end for the
  same config (5.0 here against the test's base), `predicted()` is the
  model scaled by it, and the judge holds *that* in band; `hand_of` uses
  the judged version's own runs once it has five. A hand that went to 230
  is judged at 230. The calibration table for the record: at k=5, hpEvery
  5→100, 6→115, 8→135, 10→150, 30→230. hpEvery is a blunt lever at that
  scale, which is the arithmetic saying the caps were the real fault.
- A loop variable `k` shadowed the calibration `k` in the judge and
  multiplied the model by a key name; the test caught it as a type error.
- For the report: this is the model being wrong in the useful direction —
  it could not see the upgrades, the runs could, and the fix is to let the
  measurement correct the model rather than to model everything.

## 2026-09-24 — 点々: a stroke shorter than a fingertip is a flick (hiragana v0.1.69, katakana-game v0.1.32, vocab v0.1.40)

- The maintainer: "The ten ten are pretty hard to get right."
- **What the table said.** Voiced kana by finger on medium: 61 traces, 33%
  fizzled, against 13% for plain kana by the same hand. The dakuten strokes
  are 0.14-0.16 of their glyph's span (ふ's ticks are 0.36); at the
  finger's size on a phone that is 20-40px under a fingertip covering 50.
  The gallery of だ shows the fizzles with the body drawn well and the ticks
  drawn as short dashes.
- **What the engine said.** Synthetic finger ticks on だ, fed through the
  seam: exact lands; 60% of the length RESTARTS the character; 14px off
  RESTARTS; a dab RESTARTS; backwards RESTARTS; 150% lands. A tick that
  fell short of the travel cap was "a stroke that went nowhere", and in
  medium that rule wipes the character. So a clean た and one short dash
  cost the whole thing, six strokes in.
- **The rule.** `HAND_FLICK`, per hand profile (`flick`: finger 0.12 of the
  canvas, pen 0). A stroke shorter than it is judged as a flick: `segStarted`
  (within 1.25× the start tolerance), travel of at least a third of its
  length, the smoothed motion agreeing with the stroke's own direction, and
  the pen within 1.25× the end tolerance of the end. Its coverage is
  granted whole. A flick that went nowhere is dropped in every stray mode;
  the character does not restart for it. The pen is unchanged: it can see.
- `flick.test.mjs` (in run.sh): by finger, 60% and 14px-off land, a dab and
  a backwards tick are dropped without a restart, the real tick then lands;
  by pen the 60% tick is still a stroke that went nowhere. The tail guard
  is unaffected: the workshop build carries no flick.
- Not tried on the phone. If the voiced fizzle rate does not come down in
  the next pull, the next suspects are the heading gate on a 20px stroke
  and the second tick starting inside the first's end tolerance.

## 2026-09-24 — The workshop is between runs (hiragana v0.1.70, katakana-game v0.1.33, vocab v0.1.41)

- The maintainer: "The game should rely on after game currency to level up
  the upgrades like in the tower. And maybe not so cluttered like it is
  now. The navigation is sort of messy dev mode. Should have after round
  tabs for upgrades, we can add a tab for credits, and so in the game, the
  teacher font title and kanjiVG can be removed to give us more play room."
- **Levels that last.** Every upgrade (intent … rise) has a lasting level
  bought with 魂 (`tamaCost`, growing by `lanternRamp`) through the purse
  the lanterns already used (`LEDGER.tama.own[id]`, merged by max, travels
  with a signed-in save). The run's 墨 buys the rungs above it: `lvl(id) =
  own(id) + upg[id]`, capped at the ceiling, so a maxed lasting level leaves
  the run nothing to buy, which is the Tower's shape exactly.
- **The pages.** Start and ward-fell pages: title, the tower line or the
  run's numbers, the begin/again button, then the workshop — tabs attack,
  defend, earn, lanterns, more — with every panel in the page and only one
  shown, so a tab switch rebuilds nothing. "more" holds how much help, the
  sign, draw with, the hand, the run's handwriting, and who this leans on
  (KanjiVG's credit lives there now). The last tab is remembered.
- **The run.** Two tabs on the seam, 筆 write and 墨 boosts; the boosts are
  one panel with three sections and the ink at the top; 魂 is off the seam.
  The sketchbook's "teacher guide · device font" badge and the credit
  footer are hidden in the field, and the sketchbook grows to 38/50dvh.
- Tests: the boosts tab (the old names alias to it), the workshop's five
  tabs and what they sell, a lasting intent carrying into a run and taking
  its hit, the run buying only up to the ceiling above it. `F.inkHtml` for
  the boosts' header.

## 2026-09-24 — The lights are the run's, and the ending is its own page (hiragana v0.1.71, katakana-game v0.1.34)

- The maintainer: "My energy gauge should not persist between games. Also,
  the game over page should be separated. So again button is cool, but
  have a go back home button too. I think the layout is just too cluttered."
- **What persisted.** Through the real ending path in the stub — the ward
  falls, the page opens, again — 気 came back at `energyStart` (6), but the
  lights did: a character lit in one run was lit in the next, by design
  since v0.1.21 ("it survives the ward falling"). On the seam the lights
  are the 人魂 pips beside the loaded character, and with the 気 bar
  starting a quarter full the whole gauge looked carried over. Reversed:
  `restart()` quenches the lights, and the hiragana game starts the bag at
  0. In the Tower nothing carries but the workshop; what lasts is bought.
  This also takes a hidden multiplier out of the calibrated judge's hands.
- **The ending.** Its own page now: the run's numbers, the pay, again, a
  workshop button (to the start page, where the tabs are), a home link
  (`../index.html`, the level switcher), the run's handwriting under. The
  start page keeps the workshop and gains the same home link.

## 2026-09-24 — The tabs, second cause (hiragana v0.1.72, katakana-game v0.1.35)

- The maintainer, after v0.1.68's fix: "still happening with the tabs in
  game. gotta push it a couple times before it changes."
- The first cause was real (handlers on rebuilt buttons) and is fixed. The
  second was a rule of mine: a shop refuses to open while `tracing()`, and
  the engine's `tracing()` is true for `holdMs` (1.5 s) after every lift —
  the hold the retarget waits on so a hand between strokes is not moved off
  its character. So a tap on the seam right after finishing a character was
  refused, silently, and the tap a moment later worked. The refusal is now
  `penDown()` — a pointer captured on the sketchbook, or a stroke in
  progress — which is what "under a pen that is down" meant.
- Tests: the field test taps in the hold and expects the shop; the hand test
  puts a real pointer down on the sketchbook and expects a refusal, lifts it
  and expects the shop. The order of the field tests mattered once more: a
  hold left running made a later light leave the hand's target alone.
- **And a targeting bug the flake was pointing at.** The field test's
  "3-hit farang" failed one run in six, and the instrumented copy showed
  why: the hand's own hit flies as a shot, and while it was in the air the
  lights skipped that farang ("a shot already in flight") and threw at a
  farther one carrying the same character. `owed(m)` counts the hits in
  flight against the farang's hp; a light is withheld only from one that
  is already finished. Two effects: the flake is gone, and a light no
  longer goes the long way round while the hand's hit is still flying.
