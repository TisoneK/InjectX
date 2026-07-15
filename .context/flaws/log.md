# Flaws Log (append-only — flows to the protocol package)

Friction caused by the `.context/` system or the protocol itself. See
`README.md` in this directory for the split between `flaws/` and
`inefficiencies/`.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model> (Session N)

- **Flaw:** <what in the protocol or .context/ system didn't work>
- **Symptom:** <what happened to the agent — the observable friction>
- **Root cause:** <why the protocol/.context/ let this happen>
- **Suggested fix:** <concrete change to the package — a step, a pitfall,
  a template, a rule>
- **Status:** open | fixed in package <commit-sha or date>
-->

---
## 2026-07-15 — Super Z / unknown (Session 1)

- **Flaw:** The Bash tool's description in the system prompt says "Executes a given bash command in a persistent shell session" — but in the Z.ai sandbox, env vars set via `export` in one Bash call are empty in the next. The protocol's Step 1 / Step 12 / Step 19 all assume `export GIT_TOKEN=...` persists across calls (the protocol says "DO NOT unset GIT_TOKEN yet — it's needed for all pushes. It stays as an env var for the entire session").
- **Symptom:** The first `git push` failed with "Invalid username or token" because `${GIT_TOKEN}` was empty in that Bash call. The PAT had been `export`-ed two calls earlier. Wasted ~5 minutes debugging before realizing the env var was lost.
- **Root cause:** The protocol assumes a Unix-true persistent shell, but the Z.ai sandbox's Bash tool implementation runs each command in a fresh shell. The protocol has no fallback for environments where env vars don't persist.
- **Suggested fix:** Add a note to the protocol's cloud/sandbox edition (Step 1 / Step 12) saying: "If your Bash tool does not preserve env vars across calls (verify by running `export FOO=bar` in one call and `echo $FOO` in the next — if empty, your shell is non-persistent), store the PAT at `.context/secrets/github-pat` once and read it back inline on each push: `GIT_TOKEN=$(head -1 .context/secrets/github-pat) && git ...`." Cross-reference the `system/environments.md` "Quirks" field as the place to record which environments have this behavior.
- **Status:** open

---
## 2026-07-15 — Super Z / unknown (Session 1)

- **Flaw:** The external kickoff file (`universal-kickoff.md`'s carried copy) was stale vs the package's fresh copy — specifically, the carried copy said `workflows/active.md` should record only the current agent's protocol edition, while the fresh package copy said both editions must be recorded keyed by agent type. The staleness handover step caught this, but the carried copy would have caused a wrong `workflows/active.md` entry if I hadn't diffed.
- **Symptom:** Diff at Step 0c showed 4 differing regions; one was a binding rule change about edition recording. I adopted the package's version, which added ~2 minutes of careful reading.
- **Root cause:** The bootloader note at the top of the carried copy does say "treat this copy as a bootloader" and "switch to the package's copy for every step from Step 1 on" — but in practice I had already started filling in Pre-Flight values from the carried copy before reaching Step 0c. The hand-off works, but it's brittle: any agent that doesn't read the bootloader note carefully will propagate the stale rule.
- **Suggested fix:** Move the "both editions keyed by agent type" rule into the `workflows/active.md` template's HTML comment (the package already did this — the issue is the carried copy doesn't have the updated template comment). The protocol's staleness handover step is correct; the only improvement would be to make the carried copy shorter so there's less to drift. Currently the carried copy is 668 lines — most of it duplicates the package's content. Could the carried copy be just Step 0 + Pre-Flight + a one-line "now read ../context/universal-kickoff.md" pointer?
- **Status:** open

---
## 2026-07-15 — Super Z / unknown (Session 1)

- **Flaw:** The protocol's Step 7 "Agent Discovery Phase" is a section inside the protocol file itself, not a file in `.context/`. The agent fills it in mentally (or in scratch) but there's no persistence — the next agent can't see what was discovered. The protocol says "This section becomes the project's quick-reference card for the rest of the session" but it's only quick-reference for THIS session.
- **Symptom:** I filled in the discovery phase mentally while reading the code, but didn't write it down anywhere durable. The findings went into the report (§2), but the structured "Tech Stack / Project Structure / Conventions" format was lost.
- **Root cause:** The discovery phase was designed as a thinking aid, not a durable artifact. But its content (tech stack, project structure, conventions) is exactly what the next agent needs at session start — currently they have to re-derive it from the code or read the prior session's report.
- **Suggested fix:** Either (a) make the discovery phase a `.context/discovery.md` file that gets updated each session (like `system/environments.md`), OR (b) explicitly say in the protocol that the discovery phase is for the current session's thinking only and the durable tech-stack info lives in `system/environments.md` + the README + the architecture doc. Option (a) is more useful; option (b) is simpler.
- **Status:** open
