# .context/ ↔ package sync — structural vs data

<!-- STRUCTURAL FILE — synced from the package skeleton (context-skeleton/SYNC.md).
Do NOT put project-specific notes here; they belong in a data file. The next
sync will overwrite this file from the package. -->

How `.context/` stays current with the protocol package (`TisoneK/.context`)
**without ever overwriting this project's own memory.**

## The problem

`.context/` holds two kinds of files: **structure** that should track the
package (the spec — READMEs, ignore rules) and **data** that is owned by this
project and must never be overwritten (session logs, tasks, decisions, user
prefs, reviews, secrets). Copying the whole skeleton over `.context/` to pick
up a structural update clobbers the data. This file makes the split explicit
so sync is mechanical and safe.

## The rule (how to tell them apart)

In `context-skeleton/`, a file is **structural** if and only if its basename
is `README.md` or `.gitignore`. Everything else is **data**.

- **Structural → sync.** Package-owned. Add if missing, update if it differs.
- **Data → never touch.** Project-owned. Sync must not overwrite it.

The rule is deliberately mechanical so nobody maintains a per-file list: a new
structural file that follows the convention (another `README.md`) is picked up
automatically.

### Exceptions (non-README/.gitignore structural files)

Any structural file whose basename is NOT `README.md` or `.gitignore` must be
listed here explicitly so agents know to sync it. **Currently: none.** If the
package ever adds one (e.g. a root `.context/AGENTS.md`), add its path here.

## The two lists (reference)

**Structural — synced from the package:**

- `README.md`
- `reviews/README.md`
- `secrets/README.md`
- `secrets/.gitignore`
- `flaws/README.md`
- `SYNC.md` (this file)

**Data — never synced (project-owned):**

- append-only: `agents/sessions.md`, `inefficiencies/log.md`, `flaws/log.md`,
  `tasks/backlog.md`, `plans/decisions.md`
- current-state (overwrite): `tasks/current.md`, `workflows/active.md`
- update-in-place: `system/environments.md`, `system/ai-models.md`,
  `user/identity.md`, `user/preferences.md`, `kickoff.md` (generated at
  bootstrap from the skeleton template; project-owned after that)
- per-session: `reviews/YYYY-MM-DD-*.md`
- local-only, never tracked: `secrets/<slug>`

## How an agent syncs (protocol Step 3, Path B)

When `.context/` already exists **and** the package skeleton is on disk
(`../context/context-skeleton/`, freshened by the kickoff):

1. For each **structural** file, compare `.context/<path>` to
   `context-skeleton/<path>`. **Add** missing ones; **update** differing ones.
2. **Do not read, diff, or write any data file.**
3. Commit the differences as `chore(context): sync structure from package`.
4. If the skeleton isn't on disk, **skip and note it** — never fail the session.

## Notes

- The HTML-comment *templates* inside data files (e.g. the entry template atop
  `agents/sessions.md`) are **not** synced — those files are data. The
  authoritative format always lives in the READMEs, which do sync.
- **No "last synced" version is tracked.** Diffing the handful of structural
  files each session is cheap and needs no bookkeeping.
- Structural files are **package-owned**. If this project needs a bespoke rule,
  put it in a data file — never edit a structural README, or the next sync
  overwrites it.
