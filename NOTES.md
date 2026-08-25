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
- v0.9.3 committed to dist/. It does NOT match CLAUDE.md's description: zero @font-face blocks and zero embedded fonts (CLAUDE.md claims three base64 woff2 subsets), and it fetches https://nirathai.com/fonts/kru-hand.woff2 at runtime — which breaks the offline/zero-dependency rule, breaks the no-nirathai-URLs rule, and 404s anyway. Net effect: the tracer falls back to whatever Thai font the device has.
- Priority: hiragana first. Thai is bottlenecked on instructor availability; hiragana is not bottlenecked at all, since KanjiVG supplies stroke order for all 46 gojuon.
- Note for the hiragana build: font embedding is the step that silently didn't happen in v0.9.3. Klee One and Noto Sans JP must be verified as embedded, not linked.
