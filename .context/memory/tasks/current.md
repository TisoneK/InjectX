# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-16 Session 17 (Claude Fable 5, local macOS) — **done.** UI refinement. Root-caused "decoded page is messed up / must export JSON": (1) the user's app was on a STALE backend (fresh backend decodes EHI 6/6, HC 13/13, ZIV 6/6, DARK 4/4 — restart fixes it), and (2) EHI/ZIV keep most data in `raw_data._all_fields`, unmapped to IR slots, so the detail view rendered near-empty (1 row for a 21-field EHI). Shipped `feat(ui)` (`6d09419`): activity log → 340px right dock; output redesign with compact status strip, hero tiles (host/port/protocol), 2-col card grid, a full-width "DECODED FIELDS" table showing every extracted field, notes that pick up `configMessage`/`file.msg`, and a fix for a latent `.hidden` bug (raw-JSON never collapsed). Verified in-browser vs real HC/EHI. Backlog N9 DONE. **Tell the user to restart the app** for the current backend. See `reviews/2026-07-16-review.md`.
