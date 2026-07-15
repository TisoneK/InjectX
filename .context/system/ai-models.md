# Agent + Model Registry (update in place)

Which agents and models have worked on this repo — and what they've
shown they can and can't do here. Update your row each session (last
seen + session count); add a row if you're new. The Observations
section is how the user learns which agent to hand which task, and how
agents learn a predecessor's blind spots (and verify its work
accordingly).

| Agent | Model | First seen | Last seen | Sessions |
|---|---|---|---|---|
| Super Z | unknown (GLM family; system prompt states "GLM model developed by Z.ai" without a specific version — recorded as `unknown` per the protocol's no-guess rule) | 2026-07-15 | 2026-07-15 | 1 |

## Observations

Concrete, evidence-based capabilities and limits — things demonstrated
in this repo's sessions, not marketing claims or self-assessment.
Update in place when a newer session contradicts an old observation.

- **Super Z / unknown:** The Bash tool wraps commands in a non-persistent shell — env vars (`export GIT_TOKEN=...`) do NOT survive between Bash calls. Re-export inline each call. (2026-07-15)
- **Super Z / unknown:** Validated a GitHub fine-grained PAT against `https://api.github.com/user` with `Authorization: Bearer` — both `Bearer` and `token` headers work for fine-grained PATs; classic `Basic` auth with `x-access-token` does not. (2026-07-15)
- **Super Z / unknown:** Discovered and fixed a critical path-traversal vulnerability in InjectX's `/api/config/parse` and `/api/config/detect` endpoints by reading the code in Phase 1 and verifying the exploit with `curl http://127.0.0.1:8742/api/config/parse?filepath=/etc/passwd` returning 200 OK. Fix verified end-to-end with 6 test cases. (2026-07-15)
- **Super Z / unknown:** Diagnosed a FastAPI route-shadowing bug (`/{config_id}` registered before `/detect` and `/export`) by noticing that `/parse` worked but `/detect` and `/export` 404'd — root cause was registration order, not path matching logic. (2026-07-15)
- **Super Z / unknown:** Cannot launch Electron in the sandbox (no display server). Frontend testing is limited to code review; end-to-end desktop testing must happen on a local machine. (2026-07-15)
