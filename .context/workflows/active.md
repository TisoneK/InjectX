# Active Workflow (overwrite when the workflow changes)

The workflow currently in force for this repo — which protocol edition
agents follow and the standing session parameters. Update only when the
user changes the rules; note the change in your session entry.

- **Protocol:** by agent type — local agents → `ai-engineering-protocol-local.md`; cloud/sandbox agents → `ai-engineering-protocol.md`. Both editions named here on purpose: the project's memory serves both agent types; an agent picks its own edition by its own type at session start, never by what's written here.
- **Protocol source (raw — for agent fetch):** https://raw.githubusercontent.com/TisoneK/.context/main/ai-engineering-protocol.md (cloud) | https://raw.githubusercontent.com/TisoneK/.context/main/ai-engineering-protocol-local.md (local)
- **Protocol source (blob — for human browsing):** https://github.com/TisoneK/.context/blob/main/ai-engineering-protocol.md (cloud) | https://github.com/TisoneK/.context/blob/main/ai-engineering-protocol-local.md (local)
- **Fallback:** if the raw URL 404s, clone `TisoneK/.context` with `--depth 1` and read the file locally — this is the reliable fallback.
- **Since:** 2026-07-15
- **Default role:** engineer — unless a session says otherwise; see the protocol package's `roles/`
- **Scope:** discovery + review + fix all safe issues
- **Target:** general sweep — scan everything, fix safe issues
- **Focus areas:** all — security, performance, UX, architecture, testing, docs
- **Findings handling:** fix safe issues; flag architectural changes
- **Push policy:** push to main directly after each commit
- **Commit style:** Conventional Commits with scope; `chore(context):` for the `.context/` directory
- **Commit granularity:** one logical change per commit
- **Deliverable:** report in `.context/reviews/` + chat summary
