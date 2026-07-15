# User Preferences (update in place)

How the user likes things done **on this project**. Seeded from
Pre-Flight at bootstrap; grows as sessions reveal preferences —
corrections the user gives, patterns they approve, things they state
outright. This file exists so the user never has to give the same
correction twice.

## Learning rules

1. **Record preferences, not instructions.** A preference is standing:
   it would apply to future sessions ("plain-language changelog
   entries"). An instruction is one-off ("skip the tests this once") —
   it dies with the session and does not belong here.
2. **Every bullet carries provenance** — how and when it was learned:
   `(pre-flight)`, `(stated, YYYY-MM-DD)`, `(correction, YYYY-MM-DD)`,
   `(approved pattern, YYYY-MM-DD)`. An explicit statement or correction
   outranks an inferred pattern.
3. **Current-state file.** When the user changes their mind, update the
   bullet in place and refresh its provenance — don't keep the stale
   version. History lives in the session log, not here.
4. **A session instruction beats a recorded preference for that
   session.** Follow the instruction; afterwards, if it looked like a
   standing change of mind, update this file.
5. **Committed to git — keep it professional.** Working-style facts
   only. Never personal details, never opinions about people, never
   credentials.

## Workflow

- Push to main directly after each commit (pre-flight, 2026-07-15)
- One logical change per commit (pre-flight, 2026-07-15)
- Scope: discovery + review + fix all safe issues (pre-flight, 2026-07-15)

## Communication

- Deliverable: report in `.context/reviews/` + chat summary (pre-flight, 2026-07-15)

## Code style

- Conventional Commits with scope: `fix(security):`, `feat(api):`, `docs:`, `chore(context):`, `refactor(api):`, `improve(backend):`, `chore(deps):` (approved pattern, 2026-07-15)
- Commit message body explains WHY (not what) — context for future readers and the `.context/reviews/` report (approved pattern, 2026-07-15)
- Inline comments explain non-obvious decisions; docstrings on public functions (approved pattern, 2026-07-15)
- Pydantic v2 idioms — `model_dump()` not `.dict()` (correction, 2026-07-15)

## Review depth

- Fix safe issues; flag architectural changes for approval (pre-flight, 2026-07-15)
- Verify each fix end-to-end (curl + actual HTTP response) before commit — never claim "tests pass" without the exact command and observed result (approved pattern, 2026-07-15)
- Deep-scan for similar patterns when fixing one instance (e.g., bare `except Exception:` was found in 60+ places — flagged in backlog rather than fixed piecemeal) (approved pattern, 2026-07-15)

## Risk & approvals

- Security fixes are auto-applied if safe (no behavior change for legitimate inputs); architectural changes flagged to backlog (approved pattern, 2026-07-15)
- Don't bump versions without explicit user approval — flagged in report (approved pattern, 2026-07-15)
- Two-surfaces rule: never mix project code and `.context/` updates in one commit (correction, 2026-07-15)
