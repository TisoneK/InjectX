# Agent + Model Registry (update in place)

Which agents and models have worked on this repo — and what they've
shown they can and can't do here. Update your row each session (last
seen + session count); add a row if you're new. The Observations
section is how the user learns which agent to hand which task, and how
agents learn a predecessor's blind spots (and verify its work
accordingly).

| Agent | Model | First seen | Last seen | Sessions |
|---|---|---|---|---|
| Super Z | unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | 2026-07-15 | 2026-07-15 | 3 |
| Claude Code | claude-fable-5 (Claude Fable 5; exact model ID stated in the system prompt) | 2026-07-15 | 2026-07-15 | 2 |

## Observations

Concrete, evidence-based capabilities and limits — things demonstrated
in this repo's sessions, not marketing claims or self-assessment.
Update in place when a newer session contradicts an old observation.

- **Super Z / unknown:** The Bash tool wraps commands in a non-persistent shell — env vars (`export GIT_TOKEN=...`) do NOT survive between Bash calls. Re-export inline each call. (2026-07-15)
- **Super Z / unknown:** Validated a GitHub fine-grained PAT against `https://api.github.com/user` with `Authorization: Bearer` — both `Bearer` and `token` headers work for fine-grained PATs; classic `Basic` auth with `x-access-token` does not. (2026-07-15)
- **Super Z / unknown:** Discovered and fixed a critical path-traversal vulnerability in InjectX's `/api/config/parse` and `/api/config/detect` endpoints by reading the code in Phase 1 and verifying the exploit with `curl http://127.0.0.1:8742/api/config/parse?filepath=/etc/passwd` returning 200 OK. Fix verified end-to-end with 6 test cases. (2026-07-15)
- **Super Z / unknown:** Diagnosed a FastAPI route-shadowing bug (`/{config_id}` registered before `/detect` and `/export`) by noticing that `/parse` worked but `/detect` and `/export` 404'd — root cause was registration order, not path matching logic. (2026-07-15)
- **Super Z / unknown:** Cannot launch Electron in the sandbox (no display server). Frontend testing is limited to code review; end-to-end desktop testing must happen on a local machine. (2026-07-15)
- **Super Z / unknown:** Configured a git `credential.helper` (Session 4) that reads the PAT from `.context/memory/secrets/github-pat` on demand — sidesteps the non-persistent-shell env-var problem entirely and keeps the PAT out of `.git/config` permanently. Future Z.ai cloud sessions should use this pattern instead of re-adding the token to the URL before each push. (2026-07-15)
- **Super Z / unknown:** Diagnosed a Medium-severity frontend/backend port mismatch (Session 4) by reading `main.js` and noticing `BACKEND_PORT = 8742` was a literal even though the backend reads `INJECTX_PORT` from env (Session 1's N7 fix). The bug was silent on the default port — only manifested when a user set a custom port. Couldn't reproduce live (Electron can't launch in the cloud sandbox) but the fix was straightforward env-var wiring. (2026-07-15)
- **Super Z / unknown:** Diagnosed a silent bug in `audit/trace.py` (Session 4): `trace.json(indent=2)` raises `TypeError` on Pydantic v2 (`dumps_kwargs` no longer supported), but the surrounding `try/except Exception: pass` swallowed the error. Verified by `python -W all -c "import warnings; warnings.simplefilter('always'); ..."` which showed both the deprecation warning and the TypeError. Lesson: when a function is wrapped in bare `except Exception: pass`, test the inner code in isolation to confirm it actually works. (2026-07-15)
- **Claude Code / claude-fable-5:** First LOCAL-agent session on this repo (all prior work was the Z.ai cloud agent). Correctly identified its own edition (local) and ignored the cloud agent's PAT/token records in `.context/` as not applying to it. (2026-07-15)
- **Claude Code / claude-fable-5:** Found that Session 1's C1 path-traversal fix was incomplete — verified live that a symlink with an allowed extension (`evil.ehi -> /etc/passwd`) bypassed `_validate_config_path` and read arbitrary files, then fixed it by re-checking the resolved target's extension and shipped 8 regression tests. Demonstrates verifying a prior agent's "fixed" claim by reproducing the exploit rather than trusting the ADR. (2026-07-15)
- **Claude Code / claude-fable-5:** Lost ~1 test cycle when a backgrounded `python main.py` survived `pkill -f` and kept holding its port, so a "restarted" server silently failed to bind and testing continued against the stale unpatched process. Lesson: verify a background kill with `lsof`/`kill -9 <pid>` before trusting a restart. (2026-07-15)
- **Claude Code / claude-fable-5 (Session 11):** Shipped the per-format parser test suite backlog N3 had wanted since Session 1 — parametrized over the 32 real bundled samples rather than hand-writing fixtures (suite 9→41). Chose NOT to assert decryption success (rotated/proprietary keys make "locked" valid), testing only the parser contract. Also caught that a security comment on the notes iframe asserted a false property (srcdoc auto-isolation) and corrected it to name the real protection (inherited CSP). (2026-07-15)
- **Claude Code / claude-fable-5 (Session 11):** Blocked on GUI verification — the in-app Chromium browser tool timed out (2×300s), so the notes-iframe `sandbox` hardening (N8) and the `webPreferences sandbox:true` change could not be verified and were deferred rather than shipped blind. Pattern: this repo's frontend security changes need a real Electron run, which neither the cloud sandbox (no display) nor an unresponsive in-app browser can provide. (2026-07-15)
