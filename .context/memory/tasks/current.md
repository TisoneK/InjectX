# Current Task (overwrite each session)

Holds exactly one task — the one being worked on right now.

- **Session:** idle — no task in progress.
- **Last session:** 2026-07-16 Session 18 (Claude Fable 5, local macOS) — **done.** User (Windows) said "only HC works as desired" (shared exported JSONs) + wanted copy icons. Root cause: `/api/config/export` DROPPED `raw_data`, and HC is the only format that maps data to top-level IR fields — EHI/ZIV/DARK keep it in `raw_data._all_fields`, so their exports were near-empty. Fixed export to keep raw_data minus debug keys (`3335c71`); ZIV export now 24 fields, EHI 21, DARK name/type. Also: the user's EHI shows FAILED because their **Windows backend venv is missing `argon2-cffi`** (scheme B2 needs it) — env, not code (EHI decodes 6/6 here); they must reinstall backend deps. Added copy-to-clipboard buttons (⧉) on hero tiles, all field values, and log lines (`629ee42`). 54/54 tests, verified in-browser. Left the user's untracked `electron-builder` ^25→^26 bump (package.json/lock) untouched. See `reviews/2026-07-16-review-2.md`.
