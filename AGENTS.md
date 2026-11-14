# Agent Instructions — InjectX

<!-- Generated at bootstrap from .context_ledger/core/templates/AGENTS.md.
Refreshed on core updates (fill <PROJECT_NAME> again). Optionally also
copied to CLAUDE.md and .github/copilot-instructions.md so tools that
auto-load those paths get the same digest. -->

This repo uses the `.context_ledger/` protocol: persistent agent memory plus a
vendored copy of the full workflow, committed to git. **Before doing any
work, read `.context_ledger/kickoff.md` and follow it.** It routes you — local
IDE agent or cloud/sandbox agent — to the right instruction set in
`.context_ledger/core/rules/`.

If you read nothing else, obey these rules:

1. **Start at `.context_ledger/kickoff.md`.** Do not treat "start the context
   workflow" as running this project's app, and do not grep the codebase
   for "context" — the protocol lives in the `.context_ledger/` directory.
2. **Never write under `.context_ledger/core/`** — it is a read-only, versioned
   copy of the protocol. All project memory you write lives under
   `.context_ledger/memory/`.
3. **Pick your instruction set by YOUR agent type**, never by what a
   previous session recorded: local IDE agent →
   `.context_ledger/core/rules/ai-engineering-protocol-local.md`; cloud/sandbox
   agent → `.context_ledger/core/rules/ai-engineering-protocol.md`. Local
   agents never use PATs or clone this repo; cloud steps are not yours.
4. **Read memory before working:** at minimum
   `.context_ledger/memory/workflows/active.md`,
   `.context_ledger/memory/agents/sessions.md` (last entries),
   `.context_ledger/memory/tasks/current.md`, and
   `.context_ledger/memory/inefficiencies/log.md` (known traps). If the
   active session has detailed notes at
   `.context_ledger/memory/sessions/`, skim them for current state.
5. **One task at a time.** If `.context_ledger/memory/tasks/current.md` shows
   another live session in progress, do not start.
6. **Append-only files are append-only:** `agents/sessions.md`,
   `tasks/backlog.md`, `plans/decisions.md`, `flaws/log.md`,
   `inefficiencies/log.md`. Add at the bottom; never edit or delete
   past entries.
7. **No secrets in tracked files, ever.** Values go only in
   `.context_ledger/memory/secrets/` (self-gitignored). Never echo a secret or
   token in chat, logs, or commit messages.
8. **Two surfaces, two prefixes:** editing product code = normal commit
   prefixes; editing `.context_ledger/` = `chore(context):` (reports:
   `docs(review):`). Never mix both surfaces in one commit.
9. **The session is not done until everything is committed AND pushed**,
   the session is logged in `.context_ledger/memory/agents/sessions.md`, and
   `.context_ledger/memory/tasks/current.md` is cleared. If the user has to
   remind you to commit or push, that is a protocol failure — log it in
   `.context_ledger/memory/flaws/log.md`.
10. **Don't ask permission for the default next step.** Do it and
    report. Ask only on genuine ambiguity or destructive/irreversible
    actions.

Formats and file rules: `.context_ledger/core/schemas/ledger-schema.md` is
the single source of truth. Project-specific rule adjustments:
`.context_ledger/memory/overrides/rules.md` (they win over the edition).
