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

- (to be learned across sessions)

## Review depth

- Fix safe issues; flag architectural changes for approval (pre-flight, 2026-07-15)

## Risk & approvals

- (to be learned across sessions)
