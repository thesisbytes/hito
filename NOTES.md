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
