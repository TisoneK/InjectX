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
- **Verified commands (all run successfully this session on InjectX):**
  - `git clone <url>` works for public repos and PAT-authenticated private repos (with `x-access-token:${TOKEN}@` URL form; strip via `git remote set-url origin <clean-url>` immediately after).
  - `curl -s -H "Authorization: Bearer <fine-grained-PAT>" https://api.github.com/user` validates GitHub fine-grained PATs.
  - Backend deps: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` — installs `fastapi 0.139.0, uvicorn 0.51.0, python-multipart 0.0.32, pycryptodome 3.23.0, pydantic 2.13.4` cleanly.
  - Frontend deps: `npm install --no-audit --no-fund` at project root — 70 packages, ~17s, electron postinstall skipped by allow-scripts but binary installs.
  - Backend start: `cd backend && source .venv/bin/activate && python main.py` — binds to `127.0.0.1:8742`, lifespan logs via `logging` module.
  - Backend smoke: `curl http://127.0.0.1:8742/api/health` → `{"status":"ok","version":"0.4.0","ir_version":"1.0"}`.
  - Git push (cloud/sandbox workflow): re-add token via `git remote set-url origin "https://x-access-token:${GIT_TOKEN}@github.com/..."`, `git pull --ff-only`, `git push origin main`, then `git remote set-url origin https://github.com/...` to strip. Run for every push.
- **Quirks:**
  - **Env vars do NOT persist across separate Bash tool calls** in this sandbox. Each Bash invocation starts a fresh shell — re-`export` `GIT_TOKEN` (and any other needed env var) inline at the start of every command that uses it. Never write the token to a tracked file.
  - The Bash tool description says "persistent shell session" but in practice env vars set in one call are empty in the next — verified empirically 2026-07-15.
  - `GIT_TOKEN` may be stored at `.context/secrets/github-pat` (0600 perms, gitignored — verified via `git check-ignore`) for convenience within a session. Read it back inline at the start of each push command: `GIT_TOKEN=$(head -1 .context/secrets/github-pat)`.
  - Workspace has predefined subdirs: `scripts/`, `download/`, `upload/`, `skills/`, `tool-results/`. Project repos should clone directly into `/home/z/my-project/<REPO>` (sibling to those), not into a subdir.
  - **Electron cannot launch in this sandbox** (no display server). `npm start` will fail. Test the backend in isolation with `python main.py` + `curl`; test frontend logic by reading the JS, not by running the app.

---
## Local macOS dev machine (last verified 2026-07-15)

- **Identify by:** `$USER=bao`; repo cwd `/Users/bao/Code/InjectX`; package clone sibling at `/Users/bao/Code/context` (canonical name, NOT `.context`); shell reports `PDT`/`PST` timezone. macOS.
- **OS:** Darwin 24.6.0 (macOS).
- **Runtimes:** system Python **3.9.6** (`/usr/bin/python3`; older than the Z.ai sandbox's 3.12). The codebase imports and runs fine on 3.9: the module-level `frozenset[str]` / `dict[str, dict]` annotations in `main.py` evaluate because builtin generics gained `__class_getitem__` in Python 3.9 (PEP 585). Node **v24.17.0**, npm 11.13.0, git 2.39.5 (Apple Git-154). No bare `python` on PATH — only `python3`; inside an activated venv `python` resolves.
- **Package managers:** `pip` in a project venv; `npm` for frontend.
- **Agent type:** LOCAL agent (IDE-integrated). Uses the user's existing git credentials — **no PAT, no cloning, no token dance.** The cloud-edition PAT steps in `.context/inefficiencies/log.md` and `flaws/log.md` do NOT apply here.
- **Verified commands (all run successfully this session on InjectX):**
  - Backend deps: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` — installs `fastapi 0.128.8, uvicorn 0.39.0, pydantic 2.13.4, pycryptodome 3.23.0, python-multipart 0.0.20` cleanly on Python 3.9.6.
  - Tests: `cd backend && source .venv/bin/activate && pip install pytest && python -m pytest tests/ -q` → 9 passed.
  - Backend start (isolated, does NOT touch the user's real `~/.injectx`): `INJECTX_PORT=8799 INJECTX_UPLOAD_DIR=<scratch>/uploads python main.py` → binds `127.0.0.1:8799`; `curl http://127.0.0.1:8799/api/health` → `{"status":"ok","version":"0.4.0","ir_version":"1.0"}`.
  - `git push origin main` — works out of the box with the user's credentials (no PAT).
- **Quirks:**
  - **Env vars DO persist within a single Bash tool call** (`export X=y && cmd`) but the Claude Code harness starts a fresh shell per call, so exports do NOT carry across separate calls — same net effect as the Z.ai sandbox, different cause. Chain `export`s inline within one call, or set them on the same command line.
  - **`pkill -f "python main.py"` is unreliable for killing a backgrounded backend here** — a launched backend can survive the pkill and keep holding its port, so a restarted server fails to bind (`Errno 48 address already in use`) and you unknowingly keep testing the OLD process. **Verify the kill:** `lsof -iTCP:<port> -sTCP:LISTEN -n -P` and `kill -9 <pid>` the specific PID before restarting. Cost this session: ~1 wasted test cycle (tested a stale unpatched backend, saw the "fix" apparently fail).
  - Local wall-clock date can differ from `date -u`: this machine is PDT (UTC-7), so late-evening local time is already the next UTC day. Session dates follow `date -u +%F` (protocol Pitfall #41) → 2026-07-15 here even though local was 2026-07-14 evening. Session 1 (cloud) used the same UTC convention, so dates stay consistent.
