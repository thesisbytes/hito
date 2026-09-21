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
