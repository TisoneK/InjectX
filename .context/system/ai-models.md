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
