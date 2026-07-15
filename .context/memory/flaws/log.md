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

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 2)

- **Flaw:** Pitfall #35 (local & cloud editions) tells agents to test path-traversal fixes against `..`, `..%2f`, `%2e%2e%2f`, `%2e%2e` and to check containment with `resolve()` + `is_relative_to(base)`. It does **not** mention the **symlink-with-an-allowed-extension** vector: a link named `x.ehi` pointing at `/etc/passwd`. This is precisely the vector that made Session 1's C1 fix incomplete — the fix (and its ADR-1 and review) checked the supplied path's extension and used `resolve(strict=True)`, and the review claimed it "tested the encoded forms," but nobody tested a symlink whose name has an allowed extension resolving OUTSIDE the allowlist. `resolve()` silently follows the link, so the encoded-form tests all pass while the file-read oracle stays open.
- **Symptom:** A confidently-"fixed" and ADR-documented Critical vuln (C1) was still exploitable one session later; Session 2 had to re-discover it live. Pitfall #31 ("don't apply a review finding without reproducing it") saved the day in reverse — reproducing the *fix's* claim (not a finding) exposed the gap.
- **Root cause:** Pitfall #35's checklist enumerates URL-encoding traversal tricks but omits filesystem-level indirection (symlinks, hardlinks). An allowlist that filters on a path string is trivially bypassed when the string points at something else. The guidance conflates "collapse `..` with resolve()" (which `resolve` does) with "constrain what resolve() lands on" (which it does not, for extension/containment checks against the *resolved* path).
- **Suggested fix:** Amend Pitfall #35 to add: "If your validation relies on the path's **name/extension**, re-apply that check to the **resolved** path (`resolve()` follows symlinks) — a link named `ok.ehi` → `/etc/passwd` passes a name check but resolves to a disallowed target. Add a symlink-to-disallowed-target case to the traversal test, alongside the encoded forms." Cross-reference: any allowlist/denylist decision made on a user-supplied path must be re-made on the resolved path, or made purely on resolved-path containment.
- **Status:** open

---
## 2026-07-15 — Super Z / unknown (Session 3 — migration)

- **Flaw:** The 0.1.x → 0.2.0 migration is a substantial structural change (flat `.context/` → two-zone `core/` + `memory/`), but the protocol's `SYNC.md` (which governed 0.1.x structural sync) said nothing about how to detect that a migration is needed. An agent following the 0.1.x SYNC.md rules would try to sync structural files (README/.gitignore/SYNC.md) and find that `context-skeleton/` no longer exists in the package — at which point the SYNC.md rule "If the package/skeleton isn't on disk, skip and note it" kicks in and the agent skips the sync entirely, missing the migration.
- **Symptom:** I almost missed the migration. The user said "Context repo has been updated, pull and syncronize" — I pulled the package repo, saw 8 new commits, noticed `context-skeleton/` was renamed to `core/templates/memory/`, and only then realized this was a MAJOR upgrade requiring `MIGRATION.md` rather than a routine structural sync. If I had followed SYNC.md mechanically, I would have skipped the sync (per its "skip if skeleton missing" rule) and left InjectX on 0.1.x.
- **Root cause:** The 0.1.x SYNC.md has no concept of "the package itself had a MAJOR upgrade — go read MIGRATION.md". The 0.2.0 model fixes this with `context-sync status` (drift detection) and `core/VERSION` + `memory/core.lock` (recorded version), but a pre-0.2.0 project can't use those tools until after migration.
- **Suggested fix:** The package's `universal-kickoff.md` (the bootloader) should detect at Step 0 whether the project's `.context/` is pre-0.2.0 (flat layout, has `SYNC.md`, no `core/`) and print a one-line warning: "This project is on 0.1.x — the package is now 0.2.0. Read MIGRATION.md before doing a structural sync." This would catch agents that pull the package and try to sync without realizing the layout changed.
- **Status:** open (relevant for any pre-0.2.0 project that hasn't migrated yet; moot for projects already on 0.2.0 since `context-sync status` handles drift detection)

---
## 2026-07-15 — Super Z / unknown (Session 4)

- **Flaw:** Session 1's flaw entry (about env vars not persisting across Bash tool calls in the Z.ai sandbox) suggested storing the PAT at `.context/memory/secrets/github-pat` and reading it back inline at the start of every push command: `GIT_TOKEN=$(head -1 .context/memory/secrets/github-pat) && git ...`. That works but is awkward — every push command must repeat the `$(head ...)` dance, and the protocol's cloud edition still says "re-add token via `git remote set-url origin "https://x-access-token:${GIT_TOKEN}@github.com/..."`, push, then strip" which is even more verbose. There's a cleaner pattern that the protocol doesn't mention: git's `credential.helper`.
- **Symptom:** I followed Session 1's workaround for the first push, found it clunky, and switched to a `credential.helper` that reads the PAT from `.context/memory/secrets/github-pat` on demand. After a one-time `git config credential.helper '!f() { ...; }; f'`, every subsequent `git push` worked transparently — no URL manipulation, no env-var juggling, no `.git/config` token residue. The PAT stays out of `.git/config` permanently (verified by `git remote get-url origin` showing the clean HTTPS URL after every push).
- **Root cause:** The protocol's cloud edition was written assuming the only way to authenticate a push is to bake the token into the remote URL (and then strip it). Git's `credential.helper` mechanism is older and cleaner but not mentioned anywhere in the protocol.
- **Suggested fix:** Add a sub-step to the cloud edition's Step 2 (clone) and Step 12 (push) recommending the `credential.helper` pattern as the preferred way to handle the PAT across multiple pushes. Something like: "After cloning and stripping the token from `.git/config`, configure a `credential.helper` that reads the PAT from `.context/memory/secrets/github-pat` on demand: `git config credential.helper '!f() { test -r .context/memory/secrets/github-pat && echo "username=<owner>" && echo "password=$(head -n1 .context/memory/secrets/github-pat)"; }; f'`. Subsequent `git push` commands work transparently without re-adding the token to the URL. This is cleaner than the re-add-strip dance and works in non-persistent-shell environments (where `export GIT_TOKEN=...` doesn't survive across Bash calls)." Cross-reference the existing `system/environments.md` Quirks block.
- **Status:** open (the protocol works without this, but the helper pattern is strictly better for cloud/sandbox agents)
