# Notes

Running log. Append at the bottom, don't rewrite history.

## 2026-08-25
- Repo seeded from the design chat. Engine named Hito (人).
- Decided: two per-glyph stats, mastery (ratchet) and potency (decays).
- Decided: save data keyed by codepoint.
- Decided: lore frame is unification (Nobunaga / Ramakien) over a haunted wild (phi / yokai). Not in the first build.
- Open: the teacher's v0.9.2 recording JSON still needs baking into the Thai build.
- Open: where does the last Thai build actually live? Drop it in dist/ and update CLAUDE.md with the real version number.
- Repo published: github.com/thesisbytes/hito (public). Personal names replaced with roles before pushing; unscrubbed brief kept locally as CLAUDE.local.md (gitignored).
- Correction: the 44 Thai consonants are NOT recorded. CLAUDE.md claimed the v0.9.2 session was complete and only needed baking in; that was wrong. No recording JSON has ever been committed. CLAUDE.md updated.
- Recording is blocked on the build — teacher mode lives inside the Thai HTML, so nothing can be captured until a build lands in dist/.
- Open: replace the export-JSON button with a save that writes each character to disk as it's recorded, so a lost tab can't cost a session again.
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
