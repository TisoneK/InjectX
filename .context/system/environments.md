# Environments (update in place)

Machines and sandboxes agents have run on, and what it takes to work on
this project from each. One block per environment; update the matching
block (and its "last verified" date) every time you run on it again.

## Rules

1. **Match before you add.** At session start, check whether the machine
   you're on already has a block (use its "Identify by" line). Update the
   match; add a new block only for a genuinely new environment.
2. **Record what you verified, not what you assume.** A command belongs
   under "Verified commands" only after it ran successfully on this
   environment, this project.
3. **Agents never delete blocks.** An environment the project no longer
   uses may be pruned by the user; if you can't verify a block, leave it
   alone — its last-verified date already says how stale it is.
4. **Machine facts only.** Secret values go in `secrets/`; user
   preferences in `user/`; project-wide decisions in `plans/`.

---
## Z.ai cloud sandbox (last verified 2026-07-15)

- **Identify by:** hostname pattern `c-<hex>-<hex>-<hex>`; `$USER=z`; workspace root `/home/z/my-project`; ephemeral — starts empty each session.
- **OS:** Debian GNU/Linux 13 (trixie)
- **Runtimes:** Python 3.12.13 (system `python3`), Node.js v24.18.0, npm 11.16.0, git 2.47.3, curl 8.14.1, pip 25.0.1 (inside `/home/z/.venv`)
- **Package manager:** `pip3` for Python (project uses `backend/requirements.txt`); `npm` for Node.js (project root `package.json`)
- **Verified commands:**
  - `git clone <url>` works for public repos and PAT-authenticated private repos (with `x-access-token:${TOKEN}@` URL form; strip via `git remote set-url origin <clean-url>` immediately after).
  - `curl -s -H "Authorization: Bearer <fine-grained-PAT>" https://api.github.com/user` works to validate GitHub fine-grained PATs.
  - Backend deps: `cd backend && pip install -r requirements.txt` (not yet exercised this session — Phase 1 will verify).
  - Frontend deps: `npm install` at project root (not yet exercised — Phase 1 will verify).
- **Quirks:**
  - **Env vars do NOT persist across separate Bash tool calls** in this sandbox. Each Bash invocation starts a fresh shell — re-`export` `GIT_TOKEN` (and any other needed env var) inline at the start of every command that uses it. Never write the token to a file.
  - The Bash tool description says "persistent shell session" but in practice env vars set in one call are empty in the next — verified empirically 2026-07-15.
  - `GIT_TOKEN` must remain available throughout the session for pushes; re-set inline on each push command, then conceptually "unset" only at protocol Step 19.
  - Workspace has predefined subdirs: `scripts/`, `download/`, `upload/`, `skills/`, `tool-results/`. Project repos should clone directly into `/home/z/my-project/<REPO>` (sibling to those), not into a subdir.
