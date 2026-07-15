# Inefficiency Log (append-only, mandatory)

Every session appends one block — honestly. Friction you absorb silently
is friction the next agent hits blind. "None this session" is valid only
if literally nothing slowed you down.

<!-- TEMPLATE — copy below the last entry:
---
## YYYY-MM-DD — <agent> / <model>
- **Problem:** <what went wrong or was slower than it should be>
- **Cost:** <rough time/effort wasted>
- **Cause:** <root cause if known>
- **Workaround / fix:** <what worked, or "unresolved">
- **Prevent next time:** <protocol/context change that would have avoided it>
-->

---
## 2026-07-15 — Super Z / unknown

- **Problem 1:** Env vars set via `export GIT_TOKEN=...` in one Bash tool call do NOT persist to subsequent Bash calls in the Z.ai sandbox. Each call starts a fresh shell. The Bash tool description says "persistent shell session" but that's misleading.
- **Cost:** ~5 minutes wasted before discovering the cause; then re-pasting the PAT inline on every push command for the rest of the session (8 pushes = 8 redundant `GIT_TOKEN='...'` lines).
- **Cause:** The sandbox's Bash tool wraps each command in a fresh non-interactive shell — env vars don't survive.
- **Workaround / fix:** Two options: (a) re-export the env var inline at the start of every Bash command that uses it (`GIT_TOKEN='github_pat_...' && git ...`); (b) store the PAT at `.context/secrets/github-pat` (gitignored, 0600 perms) once, then read it back inline: `GIT_TOKEN=$(head -1 .context/secrets/github-pat) && git ...`. This session used (b) — stored the PAT once and read it back on each push.
- **Prevent next time:** Documented in `system/environments.md` "Quirks" section — future Z.ai sandbox agents on this project will see the warning and skip the discovery phase.

---
## 2026-07-15 — Super Z / unknown

- **Problem 2:** The architecture doc (`docs/InjectX-Architecture.md`) is significantly stale vs the v0.4 implementation — describes HAT/DARK/TLS as having "no public decryptor" but the code has working decryptors for HAT (E1) and TLS (F1); says EHI uses "base64 unlock" but code uses 2-stage AES (B1); lists `python-magic` in requirements but it's neither in `requirements.txt` nor imported.
- **Cost:** ~10 minutes reconciling doc-vs-code claims during the discovery phase; would have been worse if I had trusted the doc and skipped reading the actual decrypt files.
- **Cause:** The doc was written for a proposed v1.0 redesign and never updated as the v0.4 implementation surpassed it.
- **Workaround / fix:** Read the actual code (`backend/decrypt/*.py`) and ignored the doc's claims for any factual question. Flagged the doc rewrite as backlog item N1.
- **Prevent next time:** Backlog N1 — rewrite the architecture doc to match v0.4 (or mark it explicitly as "historical proposal — see code").

---
## 2026-07-15 — Super Z / unknown

- **Problem 3:** No test infrastructure exists — no `tests/`, no `pytest` config, no sample config files to verify decryption against. Each fix had to be verified by ad-hoc `curl` calls against a freshly-started backend.
- **Cost:** ~15 minutes total spent starting/stopping the backend and crafting test inputs for each fix verification.
- **Cause:** Project never had test infrastructure; the team relied on manual testing through the Electron UI.
- **Workaround / fix:** Used `python main.py &` + `sleep 2` + `curl` + `kill` for each verification. Created a small `/tmp/test.ehi` ZIP file as a known-good sample.
- **Prevent next time:** Backlog N3 — add `pytest` + sample config files + happy-path tests per format. Highest-leverage next session.

---
## 2026-07-15 — Super Z / unknown

- **Problem 4:** The `npm install` postinstall script for `electron` was skipped by `npm`'s conservative `allow-scripts` default, but the electron binary was still installed in `node_modules/electron/`. There was no warning that the postinstall was skipped until I looked at the install output carefully.
- **Cost:** ~3 minutes verifying electron was actually installed.
- **Cause:** npm 11's `allow-scripts` feature defaults to skipping postinstall scripts unless explicitly approved.
- **Workaround / fix:** Verified electron was in `node_modules/electron/` and that `npx electron --version` would work locally (it would NOT work in this sandbox due to no display server, but the binary is present for desktop machines).
- **Prevent next time:** Document in `system/environments.md` that `npm install --no-audit --no-fund` works but electron postinstall is skipped — note this is fine because the binary still installs, and the postinstall script only handles native module rebuilds which aren't needed for this project.
