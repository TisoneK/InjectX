# Architectural Decisions (append-only, ADR-style)

Decisions already made — future agents respect these rather than
relitigating them. To reverse one, append a new ADR that supersedes it.

<!-- TEMPLATE — copy below the last entry:
---
## ADR-N: <short title> (YYYY-MM-DD)
- **Status:** accepted | superseded by ADR-M
- **Context:** <what forced the decision>
- **Decision:** <what was decided>
- **Consequences:** <trade-offs accepted; what future agents must respect>
-->

---
## ADR-1: Path validation at the API boundary (2026-07-15)

- **Status:** accepted
- **Context:** The `/api/config/parse` and `/api/config/detect` endpoints accepted arbitrary absolute filepaths and read the file at that path with no validation. The backend binds to `127.0.0.1`, but any local process could call the HTTP endpoint — verified by reading `/etc/passwd` through `/parse`. The architecture doc treated this as acceptable ("backend only binds to 127.0.0.1"), but in practice loopback binds do not protect against other local processes or browser-based CSRF (given the prior wildcard CORS).
- **Decision:** Validate all user-supplied filepaths at the API boundary via a shared `_validate_config_path` helper. Require (1) absolute path, (2) extension in `ALLOWED_EXTENSIONS` allowlist (`.ehi`, `.hc`, `.hat`, `.ha`, `.dark`, `.drak`, `.dt`, `.darktunnel`, `.tls`, `.npv4`, `.inpv`, `.npv`, `.nsh`, `.vhd`, `.ovpn`, `.conf`), (3) `Path.resolve(strict=True)` to collapse `..` segments and reject broken symlinks, (4) file size ≤ 50 MiB. Apply the same validation to `/parse`, `/detect`, and `/upload` (extension + size only — `/upload` already controls the destination path).
- **Consequences:**
  - The `/parse` endpoint can no longer be used as a generic file-read oracle. Legitimate use cases (Electron's file dialog → POST to `/parse`) are unaffected because the dialog already filters by extension.
  - Future agents adding a new config format MUST add its extension to `ALLOWED_EXTENSIONS` in `backend/main.py` or the format's files will be rejected at the API boundary.
  - The 50 MiB cap is generous (config files are kilobyte-scale) but leaves headroom for unusually large `.ovpn` files with embedded `<ca>`/`<cert>`/`<key>` blocks. If a legitimate use case exceeds 50 MiB, raise `MAX_UPLOAD_BYTES` rather than removing the cap.

---
## ADR-2: CORS restricted to file:// and loopback (2026-07-15)

- **Status:** accepted
- **Context:** The backend used `allow_origins=["*"]` with `allow_credentials=True` — an invalid combination per the CORS spec (browsers reject it) and overly permissive even on a loopback bind. Any local web page could issue cross-origin requests to the backend.
- **Decision:** Restrict CORS origins to `file://` (Electron's default `loadFile` origin), `http://127.0.0.1:8742`, and `http://localhost:8742`. Disable `allow_credentials` (no cookies/auth used). Restrict methods to `GET`, `POST`, `DELETE` (the only ones the API exposes). Restrict headers to `Content-Type`.
- **Consequences:**
  - The Electron renderer (loaded via `loadFile`) can call the backend. Local web pages cannot.
  - Future agents must NOT relax this back to `allow_origins=["*"]` without an explicit user decision — log it as a flaw if a code review finds it reverted.
  - If the project ever adds browser-based access (e.g., a web UI), add the new origin explicitly rather than going wildcard.

---
## ADR-3: Idempotent endpoints use GET, not POST (2026-07-15)

- **Status:** accepted
- **Context:** The architecture doc specified `POST /api/config/detect` and `POST /api/config/export`, but the Electron frontend's IPC handlers call them with default-fetch GET (`fetch(url)` with no method option). The mismatch was latent — `/detect` was shadowed by `/{config_id}` and `/export` was shadowed after the GET migration — but the underlying issue was that the architecture doc's POST choice was wrong for idempotent operations.
- **Decision:** `/api/config/detect` and `/api/config/export` are `GET` endpoints. Detection and export do not mutate server state; GET is the correct semantic. `/api/config/parse` was already `GET` (despite the architecture doc saying `POST`); left as-is. `/api/config/upload` remains `POST` because it accepts a file body.
- **Consequences:**
  - The frontend's existing IPC handlers (which use default-fetch GET) work without modification.
  - Future agents adding idempotent endpoints should default to GET, not POST, unless the operation has side effects.
  - The architecture doc is stale on this point (see backlog item N1).

---
## ADR-4: Two-surfaces rule — project vs .context/ commits (2026-07-15)

- **Status:** accepted (inherited from the `.context/` protocol — recorded here because it constrained every commit this session)
- **Context:** The `.context/` protocol mandates that project code and `.context/` memory updates are staged and committed separately — never both in one commit. Project commits use `fix:`/`feat:`/`docs:`; `.context/` commits use `chore(context):` (with the exception of `docs(review):` for review reports).
- **Decision:** Apply the rule strictly. Stage per-surface: `git add .context/` for memory commits, explicit paths (`backend/main.py`, `package-lock.json`) for project commits. Verify with `git status` before every commit that the two surfaces aren't mixed.
- **Consequences:**
  - The git log is a clean record of "what changed in the product" vs "what changed in the agent memory" — useful for reviewers who care about only one.
  - Future agents must continue this discipline. A mixed commit is a protocol violation; log it as a flaw.

---
## ADR-5: Path validation re-checks the RESOLVED target's extension (2026-07-15)

- **Status:** accepted (hardens ADR-1; does not supersede it)
- **Context:** ADR-1 added `_validate_config_path` with an extension allowlist and `Path.resolve(strict=True)`. Session 2 verified live that the check was incomplete: the allowlist was applied to the *caller-supplied* path's extension, but `resolve()` follows symlinks, so a link named `x.ehi` pointing at `/etc/passwd` passed the check and the endpoint read the target file. This reopened C1's arbitrary-local-file-read for any process that can plant a symlink (trivial under the established threat model — any local process can call the loopback API).
- **Decision:** After `raw.resolve(strict=True)`, re-check `resolved.suffix.lower()` against `ALLOWED_EXTENSIONS` and reject (400) if the resolved target has a disallowed extension. The pre-resolution extension check stays (fast reject before touching the filesystem); the post-resolution check is the authoritative one.
- **Consequences:**
  - Legitimate same-extension symlinks (`config.ehi -> archive.ehi`) still work. Only cross-extension links (the attack) are rejected. A legitimate symlink to a file with a *different but still-allowed* extension also works; a symlink to a no-extension or disallowed-extension file is rejected — acceptable, since a real config always carries a supported extension.
  - Future agents must NOT remove the resolved-extension re-check. `_validate_config_path` has now been the site of two related traversal bugs (C1, S2-1); treat any change to it as security-sensitive and add a traversal test (including the symlink-with-allowed-extension vector) before merging.
  - Regression coverage lives in `backend/tests/test_path_validation.py`.

---
## ADR-6: SNI Host Hunter is a loopback-bound research tool, not a network scanner (2026-07-24)

- **Status:** accepted (ratified Session 24 from the proposal in `features/sni-host-hunter.md` §10)
- **Context:** The SNI Host Hunter feature (backlog N14) introduces an async prober that can issue hundreds of TLS handshakes per second. Without constraints, the same machinery could be misused as a network scanner or for low-grade flooding. The project's existing security stance (ADRs 1, 2, 5) is "loopback-only backend, extension allowlist, path validation" — the prober must inherit that stance.
- **Decision:**
  1. The prober runs only from the user's machine against the public internet — it is not a LAN/IP-range scanner.
  2. Concurrency is hard-capped at `SNI_MAX_CONCURRENCY = 200` (SNIbugtester's default). Requests above the cap are clamped, not honoured. Default concurrency is 50.
  3. Per-target dedupe: each unique hostname is probed at most once per job (candidates are deduped before scanning). This satisfies the "≤1 req/sec per hostname" intent without a timing lock, since a host is never re-probed within a job.
  4. No IP-range enumeration in MVP — only explicit hostname lists (seedlists) or crt.sh-discovered hostnames. Reverse-IP lookup (Phase 2) will use public APIs, not active scanning.
  5. The feature's README section documents these constraints and the responsible-use rationale.
- **Consequences:**
  - Future agents MUST NOT raise `SNI_MAX_CONCURRENCY` above 200 without a new superseding ADR and explicit user decision.
  - Future agents MUST NOT add IP-range scanning without an explicit user decision — the "research tool" framing depends on it.
  - The cap + dedupe live in `backend/snihunter/probe.py`; treat changes to them as security-sensitive.

---
## ADR-7: SNI Hunter frontend routes through Electron IPC, not direct renderer fetch (2026-07-24)

- **Status:** accepted (Session 24)
- **Context:** The design doc (`features/sni-host-hunter.md` §6.3) proposed adding a `sni` namespace to `frontend/src/scripts/api.js` that calls `fetch()` directly from the renderer. But every existing backend call in this app is proxied through Electron IPC: renderer → `window.API` (api.js) → `window.vpnAPI` (preload.js) → `ipcRenderer.invoke` → `ipcMain.handle` → `fetch(BACKEND_URL...)` in main.js. Direct renderer `fetch` would be the only exception and would fragment the pattern.
- **Decision:** Implement the SNI surface the same way as every other backend call — new `ipcMain.handle("sni-*")` handlers in `main.js`, matching bridge methods in `preload.js`, an `API.sni.*` namespace in `api.js`, and the `CMD.sni` subtree in `renderer.js` calling `API.sni.*`. Deviate from the design doc's §6.3 direct-fetch sketch in favour of the established convention.
- **Consequences:**
  - The renderer keeps a single, uniform backend-access path; no renderer-origin CORS surface is added (all HTTP originates in the Electron main process).
  - Future agents extending SNI Hunter add IPC handlers, not renderer `fetch` calls.

---
## ADR-8: Bundled seedlists ship in-tree, curated from public zero-rating sources (2026-07-24)

- **Status:** accepted (Session 24 — answers `features/sni-host-hunter.md` §9 Q1)
- **Context:** Phase 1 ships per-ISP seed lists for the user's home market (Safaricom/Airtel/Telkom Kenya). §9 Q1 asked whether they should be committed in-tree or pulled from a separate `injectx-seedlists` repo. The lists are *publicly published zero-rated domains* (Free Basics infrastructure, educational/government portals) — not secret working exploits — so committing them carries no secret-handling concern (ADR-4/secrets rule untouched).
- **Decision:** Ship seedlists in-tree under `backend/snihunter/data/seedlists/*.txt`, curated from the public sources catalogued in the design doc §3.4/§11.5 (Techfoe, aimtuto, snihost.com, UNESCO/Advox zero-rating reports). Each file carries a header comment naming its provenance and a responsible-use note. They are *seed* domains (starting fuel for discovery/probing), explicitly not a guarantee any host currently works.
- **Consequences:**
  - Seedlists ship with every release; updating them is a normal product commit, not a separate-repo pull. A separate `injectx-seedlists` repo remains an option if the lists grow large or need frequent updates (revisit then).
  - Seedlists must never contain credentials, tokens, or per-user data — only public hostnames. Enforced by review, not code.
