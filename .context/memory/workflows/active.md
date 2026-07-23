# Active Workflow (overwrite when the workflow changes)

The workflow currently in force for this repo — which protocol edition
agents follow and the standing session parameters. Update only when the
user changes the rules; note the change in your session entry.

- **Protocol:** by agent type — local agents → `.context/core/rules/ai-engineering-protocol-local.md`; cloud/sandbox agents → `.context/core/rules/ai-engineering-protocol.md`. Both editions named here on purpose: the project's memory serves both agent types; an agent picks its own edition by its own type at session start, never by what's written here.
- **Protocol location:** on disk — vendored in `.context/core/` (no network fetch needed; version in `.context/core/VERSION` = `0.3.0` (updated from 0.2.0 in Session 24, 2026-07-23; harvest release, no migration), last verified in `memory/core.lock`)
- **Package upstream (for flaw back-ports + core updates):** https://github.com/TisoneK/.context.git
- **Since:** 2026-07-15
- **Default role:** engineer — unless a session says otherwise; see `.context/core/roles/`
- **Scope:** discovery + review + fix all safe issues
- **Target:** general sweep — scan everything, fix safe issues
- **Focus areas:** all — security, performance, UX, architecture, testing, docs
- **Findings handling:** fix safe issues; flag architectural changes
- **Push policy:** push to main directly after each commit
- **Commit style:** Conventional Commits with scope; `chore(context):` for the `.context/` directory
- **Commit granularity:** one logical change per commit
- **Deliverable:** report in `.context/memory/reviews/` + chat summary
