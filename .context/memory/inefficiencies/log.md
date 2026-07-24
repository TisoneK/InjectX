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

---
## 2026-07-26 — GitHub Copilot / DeepSeek V4 Flash Free

- **Problem 1: README stale across 6+ sections vs v0.4 reality.** The format table omitted ZIV/LNK rows, labelled DARK as "proprietary" (reality: scheme I1, cracked since Session 14), listed `dark_parser.py` in project structure (file deleted Session 14), and claimed DARK had "no public decryptor" in both Key Finding and Research Sources sections.
- **Cost:** ~15 minutes reading, diffing, and applying 4 sequential edit operations across 3 sections.
- **Cause:** README was never updated as new decryptors (DARK I1, ZIV H1, LNK detection, EHI v2 B2, HC v2.7 A5) were added over 14 prior improvement sessions. No protocol step enforces README sync on session completion.
- **Workaround / fix:** Applied the fixes manually (multi_replace_string_in_file). README now matches v0.4.
- **Prevent next time:** Add a Pitfall to the protocol: "After adding/changing any decryptor or format support, verify the README Supported Formats table, Key Finding section, Research Sources section, and Project Structure tree are in sync before closing the session." Or add an automated check: grep the README for stale scheme ranges vs actual `decrypt/` files.

- **Problem 2: `python -m ruff` fails on Windows venv.** The ruff entry point is at `.venv\Scripts\ruff.exe` but `python -m ruff` raises `ModuleNotFoundError` even with ruff installed. This is a Windows-specific venv quirk.
- **Cost:** ~3 minutes figuring out the correct invocation, then recording it in environments.md.
- **Cause:** On Windows, `python -m` looks for `__main__.py` in the ruff package's site-packages directory, but pip-installed ruff on this Python 3.13.1 venv doesn't expose a `__main__` module (ruff is installed as a console-script entry point, not a module).
- **Workaround / fix:** Use `.venv\Scripts\ruff.exe` directly (or activate the venv first so `ruff` is on PATH). Recorded in `environments.md` Windows block.
- **Prevent next time:** Already done — the environments entry warns future agents.
- **Workaround / fix:** Used `python main.py &` + `sleep 2` + `curl` + `kill` for each verification. Created a small `/tmp/test.ehi` ZIP file as a known-good sample.
- **Prevent next time:** Backlog N3 — add `pytest` + sample config files + happy-path tests per format. Highest-leverage next session.

---
## 2026-07-15 — Super Z / unknown

- **Problem 4:** The `npm install` postinstall script for `electron` was skipped by `npm`'s conservative `allow-scripts` default, but the electron binary was still installed in `node_modules/electron/`. There was no warning that the postinstall was skipped until I looked at the install output carefully.
- **Cost:** ~3 minutes verifying electron was actually installed.
- **Cause:** npm 11's `allow-scripts` feature defaults to skipping postinstall scripts unless explicitly approved.
- **Workaround / fix:** Verified electron was in `node_modules/electron/` and that `npx electron --version` would work locally (it would NOT work in this sandbox due to no display server, but the binary is present for desktop machines).
- **Prevent next time:** Document in `system/environments.md` that `npm install --no-audit --no-fund` works but electron postinstall is skipped — note this is fine because the binary still installs, and the postinstall script only handles native module rebuilds which aren't needed for this project.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 2)

- **Problem:** After editing `main.py`, I restarted the backgrounded backend with `pkill -f "python main.py"` + relaunch, but the OLD process survived the pkill and kept holding port 8799. The new process failed to bind (`Errno 48 address already in use`, visible only in its log) and I unknowingly kept cur/testing the STALE, unpatched backend — so my symlink fix appeared to "not work" (attack still returned 200).
- **Cost:** ~1 full test cycle + a few minutes of confusion diagnosing why a correct fix seemed ineffective, before checking `lsof` and finding the stale PID.
- **Cause:** `pkill -f` on a backgrounded process launched from a prior Bash tool call is unreliable in this harness (fresh shell per call; the background job isn't necessarily in pkill's match set or dies too slowly). uvicorn logs the bind failure but keeps the process alive serving nothing useful, and there's no foreground error.
- **Workaround / fix:** Always verify the port is actually free before restarting: `lsof -iTCP:<port> -sTCP:LISTEN -n -P`, then `kill -9 <specific-pid>`. Don't trust `pkill` alone. Recorded in `system/environments.md` quirks for this machine.
- **Prevent next time:** For iterative backend testing, either (a) kill by explicit PID captured from `$!` at launch and confirm with `lsof`, or (b) use a fresh port per restart. A stale-server check (health endpoint returning old behavior after a code change) should trigger an immediate `lsof` before further debugging.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 2)

- **Problem:** I skipped protocol Step 1's git-identity check and committed 6 times without verifying `git config user.name`. The machine has no identity configured, so git silently authored all 6 commits as `Bao Le <bao@Baos-Mac-mini.local>` (macOS account default) instead of the project identity `Tisone Kironget <tisonkironget@gmail.com>` recorded in `kickoff.md`/`user/identity.md`. The user caught it after the session ("why did you push as claude yet context had my credentials"). The `Co-Authored-By: Claude Fable 5` trailer added confusion — but that's just a message footer, not the author.
- **Cost:** Full history-rewrite recovery: set repo-local identity, `git rebase 8ce5782 --exec "git commit --amend --reset-author --no-edit"` to re-author all 6 commits, then `git push --force-with-lease`. Plus the user's trust hit from mis-attributed commits landing on `main`.
- **Cause:** Executed Phase 1 but treated the git-identity sub-step of Step 1 as skippable. The local protocol explicitly says: "If git identity is not configured (`git config user.name` returns empty), set it using the Pre-Flight values." I never ran that check. Local agents don't handle PATs, so I under-weighted the identity step as "not my concern" — but identity ≠ credentials; the local agent still owns setting the authoring identity.
- **Workaround / fix:** Re-authored to Tisone Kironget and force-pushed (new SHAs `636463c`..`3a97003`, replacing `3d12269`..`8f916d4`). Set repo-local identity so future commits are correct. Recorded the identity requirement in `system/environments.md` (this machine's block).
- **Prevent next time:** Step 1's identity check is now flagged in bold in this machine's `environments.md` block. Rule of thumb: **run `git config --local user.name` as the very first thing after confirming the repo, before any commit** — an unset identity on a shared repo produces mis-attributed history that costs a force-push to fix. This is the machine-account-vs-project-owner trap (Pitfall #43 territory: `.context/` recorded the right identity; the machine didn't have it, and I didn't bridge the gap).

---
## 2026-07-15 — Super Z / unknown (Session 3 — migration)

- **Problem:** When the workspace is restored between sessions (e.g., the user comes back the next day), many files show as "modified" in `git status` even though their content is byte-identical to HEAD. Root cause: file mode bits drifted from `100644` (non-executable) to `100755` (executable) — likely from a filesystem sync that doesn't preserve mode bits (zip transfer, Windows intermediary, etc.).
- **Cost:** ~3 minutes diagnosing; first instinct was "someone else committed changes I don't have" before checking `git diff --summary` and seeing only `mode change` lines.
- **Cause:** Cross-filesystem sync (probably the sandbox restoring from a snapshot) doesn't preserve Unix mode bits.
- **Workaround / fix:** `git diff --summary` reveals only `mode change 100644 => 100755` lines (no content changes). Safe to `git reset --hard HEAD` to restore the recorded mode bits — no work is lost because content is identical. Always run `git diff --stat` first to confirm 0 insertions / 0 deletions before resetting.
- **Prevent next time:** Documented in `system/environments.md` "Quirks" — at session start, if `git status` shows many unexpected modifications, run `git diff --stat` first; if all show `0 insertions, 0 deletions`, it's mode-bit drift, reset with `git reset --hard HEAD`.

---
## 2026-07-15 — Super Z / unknown (Session 3 — migration)

- **Problem:** Git's rename detection during the 0.2.0 migration initially confused two sets of identical-content files: the renamed data files (`.context/secrets/.gitignore` → `.context/memory/secrets/.gitignore`) and the freshly-vendored template files (`.context/core/templates/memory/secrets/.gitignore`). Without `--find-renames`, git matched the old data file to the template file instead of to the renamed data file, making it look like the data file was deleted and a separate new file was created.
- **Cost:** ~5 minutes verifying that history was actually preserved.
- **Cause:** Git's default rename detection picks the highest-similarity new file for each deleted file. When two new files have identical content (the data file's rename target AND the template), git may pick the wrong one.
- **Workaround / fix:** Use `git status --find-renames=50` (or `git diff --cached -M`) to see rename detection with explicit threshold. In this case, both targets were 100% similar so git picked one consistently; the actual file content at `.context/memory/secrets/.gitignore` is correct regardless of which path git reports as the rename source. `git log --follow --find-renames` tracks history through either path.
- **Prevent next time:** When migrating a layout where data files have identical-content template siblings, verify the actual file contents at the destination paths rather than trusting git's rename display. Content correctness is what matters; rename display is cosmetic.

---
## 2026-07-15 — Super Z / unknown (Session 4)

- **Problem:** mypy 1.18+ refuses to run when `python_version = "3.8"` is set in `pyproject.toml` — it errors with `python_version: Python 3.8 is not supported (must be 3.10 or higher)`. The InjectX README claims Python 3.8+ and the macOS env runs 3.9.6, so I initially set `python_version = "3.8"` to match.
- **Cost:** ~2 minutes diagnosing + fixing.
- **Cause:** mypy 1.18 dropped support for type-checking code targeting Python < 3.10. The `python_version` setting in mypy config is the *target* Python version (what mypy assumes for type semantics), not the runtime requirement — but mypy won't run if it's set below 3.10.
- **Workaround / fix:** Set `python_version = "3.10"` in `[tool.mypy]`. The runtime target stays 3.8+ (the README claim is unchanged; the codebase uses `from __future__ import annotations` so PEP 585/604 syntax in annotations is fine at runtime on 3.8). mypy's `python_version` is just what it assumes for type-checking semantics.
- **Prevent next time:** Documented in `system/environments.md` (Z.ai cloud sandbox block, Quirks). Future sessions setting up mypy config on this project should use `python_version = "3.10"` from the start.

---
## 2026-07-15 — Super Z / unknown (Session 4)

- **Problem:** Shipping a `pyproject.toml` with `ruff` config that passes today was harder than expected. The natural starting rule set (E + F + W + I + UP + B) reports 119 errors — 61 UP045 (`Optional[X]` → `X | None`), 26 I001 (unsorted imports), 15 F401 (unused imports), 6 E402 (main.py's sys.path manipulation), 5 B904 (raise without `from`), 3 F841 (unused vars), 1 B007, 1 F601, 1 UP015. None are runtime bugs, but they all fail `ruff check` and would break CI.
- **Cost:** ~10 minutes iterating the config (select → check statistics → ignore → per-file-ignore) to find a set that passes today while still being useful.
- **Cause:** The codebase was written without a linter; ruff's modern rule sets flag patterns that are pervasive (UP045 especially — the codebase uses both `Optional[X]` and `X | None` forms).
- **Workaround / fix:** Shipped `pyproject.toml` with `select = ["E", "F", "W"]`, `ignore = ["E501", "F401"]`, and `per-file-ignores = {"main.py" = ["E402"]}`. This passes clean today. Also fixed the 5 real-bug issues (F841 ×3, F601 ×1, B007 ×1) in a separate commit so the F841/F601/B007 rules could be enabled if a future session wants them. The 15 F401 unused-import cleanups are flagged in the backlog as a follow-up — once done, the `F401` ignore can be dropped. Tightening ruff to add I/UP/B is a future N6 sub-task.
- **Prevent next time:** When shipping a new linter config to a project that didn't have one, run `ruff check . --statistics` FIRST to see the violation counts by rule, then pick a rule set that either (a) passes today or (b) is paired with a cleanup commit. Don't ship a config that fails — CI will break the moment it's wired up.

---
## 2026-07-15 — Super Z / unknown (Session 4)

- **Problem:** When cleaning up `best_stage1_confidence` in `decrypt/ehi_decrypt.py`, ruff reported the variable as unused at line 207 (inside the success branch) — I removed that assignment, but ruff STILL reported it because the variable was ALSO initialized at line 181 (`best_stage1_confidence = 0.0`). I had to make a second pass to remove the initialization too.
- **Cost:** ~2 minutes (one extra edit + re-run ruff).
- **Cause:** I read the first ruff error, jumped to the cited line, removed the assignment there, and re-ran without checking whether the variable was referenced anywhere else. The init at line 181 was a few lines above the cited location and didn't appear in the error's context window.
- **Workaround / fix:** Removed the init too. Final state: the variable is gone entirely; the explanatory comment now says "we don't need a separate confidence tracker here because each successful attempt is already recorded with confidence=0.3 in the trace, and the router selects the overall best."
- **Prevent next time:** When a linter reports an unused variable, grep for ALL occurrences of that variable name in the file before editing — the cited line is one site, but the variable may be initialized, assigned, or referenced elsewhere. `grep -n <varname> <file>` is the cheapest pre-check.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 11)

- **Problem:** The in-app Chromium browser tool (`mcp__Claude_Browser__preview_start`) timed out after 300s trying to open a local `file://` test page, then again on a second attempt. I wanted it to verify iframe `sandbox="allow-same-origin"` rendering/scripting behavior (for the notes-iframe hardening) without launching the full Electron app.
- **Cost:** ~6 minutes (two 300s timeouts) + had to abandon the verification path and defer the sandbox-attr change to a backlog item (N8) instead of shipping it this session.
- **Cause:** Unknown — the preview/browser backend was unresponsive this session (CDP/extension stuck). Not project-specific.
- **Workaround / fix:** Reasoned from the well-specified `sandbox` semantics + the fact that the parent CSP already closes the actual hole, and deferred the runtime change to a session that can drive the real Electron GUI. Corrected the misleading comment (no runtime change) instead.
- **Prevent next time:** For quick DOM/iframe-behavior checks, don't assume the in-app browser is available — it can hang. A headless check via `node`/jsdom, or accepting that Electron-specific rendering needs the real app, is more reliable. Electron GUI verification on this machine (file dialogs, IPC, DevTools, iframe rendering) remains the gap blocking N8 and the `webPreferences sandbox:true` change — neither was runnable this session.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 11)

- **Problem:** The local `backend/.venv` predated Session 9 and was missing `argon2-cffi` (added to `requirements.txt` that session for the EHI v2 / scheme B2 decryptor). `import argon2` failed. Also `ruff`/`mypy` weren't in the venv, so the lint baseline couldn't run until installed.
- **Cost:** ~2 minutes to notice and re-sync.
- **Cause:** A venv created in an earlier session isn't auto-updated when a later (cloud) session adds a dependency to `requirements.txt`. The local and cloud agents don't share the venv.
- **Workaround / fix:** `pip install -r requirements.txt` (picks up argon2-cffi 25.1.0) + `pip install ruff mypy` at session start.
- **Prevent next time:** At Step 4 (install deps), always run `pip install -r requirements.txt` against the existing venv rather than assuming it's current — a prior session's venv can be stale if a later session added deps. Cheap to run; catches silent import failures in the decrypt path before they surface as a mysterious test/parse error.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 12)

- **Problem:** The session logs disagreed with reality on per-format decode status. Session 9 claimed "EHI 6/6 ✅" but the user reported "only hc works e2e," and I couldn't tell from the logs alone which was true (session entries record decode status but it can drift as samples/keys change). I had to write a full-pipeline probe (`parse_config` over every sample, dumping `decryption_status` + extracted fields) to get ground truth: EHI does decode 6/6, but yields `proxy_host`/`payload`/`sni` and NO top-level `host`, which is why a `host`-keyed UI (and my first probe) made it look empty.
- **Cost:** ~10 minutes writing/running the probe and dumping full NormalizedConfigs before I could trust any format's status.
- **Cause:** Decode status is scattered across prose session entries and isn't machine-checkable; a probe is the only reliable source of truth, and a naive probe keyed only on `host` under-reports formats that use `proxy_host` (EHI).
- **Workaround / fix:** Wrote a probe that parses all samples and prints status + several possible host fields; then dumped the FULL model for one sample per suspicious format. Kept it in scratchpad. Recommend a committed `scripts/decode_status.py` (or a test) that prints a per-format decode matrix so the next agent gets ground truth in one command instead of re-deriving it.
- **Prevent next time:** Don't trust prose "N/N decode" claims in session logs — run a pipeline probe. And when judging whether a format "works," dump ALL extracted fields, not just `host` (EHI/proxy-based formats populate `proxy_host`, not `host`).

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 12)

- **Problem:** Raw GitHub `raw.githubusercontent.com` fetches for the reference decryptors mostly 404'd until I found the right org/repo/branch — the TLS/ZIV algorithm comments in the code cited "Pancho7532/HCDecryptor" and "EstebanZxx/X-Tools" but the actual TLS decryptor lives on **GitLab** under `PANCHO7532/HCDecryptor` (the GitHub mirror is `PANCHO7532B/HCDecryptor`), and X-Tools's crypto is in `Main.py` reached via a Node shim (`X/ZIV.js`), not an obvious path.
- **Cost:** ~8 minutes probing candidate raw URLs and using the GitLab/GitHub tree APIs to locate the real files.
- **Cause:** Code comments named the research source loosely (wrong host, no path); the canonical repo moved to GitLab.
- **Workaround / fix:** Used `https://gitlab.com/api/v4/projects/<url-encoded-path>/repository/tree?recursive=true` and `https://api.github.com/repos/<owner>/<repo>/git/trees/<branch>?recursive=1` to list the tree, then fetched `-/raw/master/<path>` (GitLab) / `raw.githubusercontent.com/<owner>/<repo>/<branch>/<path>` (GitHub). Recorded the exact paths in `reviews/2026-07-15-review-5.md` so the next agent doesn't re-hunt.
- **Prevent next time:** The decryptor module docstrings should cite the exact repo host + path + branch of their reference (e.g. `gitlab.com/PANCHO7532/HCDecryptor lib/methods/tlsDecryptor.lib.js @ master`). Fold into a future N6-style cleanup.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 14)

- **Problem:** DARK Tunnel was recorded across ~6 sessions as "proprietary encryption, no public decryptor" — an assertion that was NEVER checked against the file bytes. `xxd` on any `.dark` sample shows `darktunnel://eyJ0eXBlIjoi…` in the first 16 bytes; `eyJ` is literally `{"` in base64. The outer layer is plaintext base64 JSON. The false claim propagated because (a) the cloud sessions couldn't/didn't hexdump the samples, (b) an orphaned `dark_parser.py` (never imported) documented "proprietary encryption" in its docstring and Step-5 warning, and (c) each session copied the prior session's "DARK = proprietary" line into its notes.
- **Cost:** ~0 this session (spotting it took one `xxd`), but the wrong belief blocked DARK support for every prior session — the highest-leverage decryption win in the project sat behind a two-second check nobody ran.
- **Cause:** A confident, repeated prose claim in session logs + a dead-code docstring, none of it verified against bytes. Exactly the "don't trust prose 'N/N decode' claims" trap from Session 12's inefficiency entry — extended: don't trust prose *"format X is unbreakable"* claims either. Hexdump the actual file first.
- **Workaround / fix:** `head -c 64 file | xxd` on the samples immediately revealed the `darktunnel://` + base64-JSON envelope. Implemented scheme I1. Deleted the orphaned `dark_parser.py` so the false narrative can't reinfect a future session.
- **Prevent next time:** For ANY format claimed to be "encrypted / proprietary / no decryptor," the first action is a raw hexdump of a real sample — look for scheme prefixes (`xxx://`), base64 (`eyJ`=`{"`, `PD94`=`<?x`), gzip (`1f 8b`), ZIP (`PK`), or plaintext. Only after the bytes rule out trivial encodings does "encrypted, needs a key" become the working hypothesis. A cheap `scripts/inspect_sample.py` that prints prefix/entropy/base64-attempt per file would institutionalize this.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 15)

- **Problem:** Tried to download the ZIVPN / TLS Tunnel APKs via `curl` to statically extract the rotated keys (user granted permission). The APK-mirror sites actively block automated download: **APKPure** returns HTTP 403 anti-bot HTML to curl; **Uptodown**'s direct-download token (`dw.uptodown.com/dwn/<token>`) returned a real 15 MB APK but it was Uptodown's OWN installer app (`com.uptodown.account`, 0 occurrences of "zivpn" in the dex, native libs `libuptodown-native.so`), not the target; **APKCombo** generates the real `download.apkcombo.com` links via JS/XHR gated behind a `/checkin` fingerprint token, so curl only sees the page shell (only the apkcombo-installer.apk is in the static HTML).
- **Cost:** ~20 minutes across 4 download strategies + a browser attempt; net zero APK obtained.
- **Cause:** APK mirrors deliberately gate real downloads behind anti-bot / JS / installer wrappers. Pushing past APKCombo's fingerprint-token flow crosses into bot-detection-bypass, which is out of bounds. This machine also has NO decompiler/Frida/adb (only java+unzip+curl), so even a downloaded APK only supports a `strings`/grep static pass, not a proper jadx decompile or dynamic hook, without first fetching jadx.
- **Workaround / fix:** Unresolved for automated download. The reliable path is the USER downloading the APK on a browser/device and dropping the `.apk` on disk; then a local agent can `unzip` + `strings`/grep the dex (and, with the user's OK, fetch standalone jadx into scratchpad to run with the existing `java`). Dynamic Frida extraction is impossible on this machine (no emulator/rooted device).
- **Prevent next time:** Don't burn time re-attempting curl/browser APK downloads from APKPure/Uptodown/APKCombo — they're gated. Ask the user to supply the APK file directly. Verify any obtained APK is the RIGHT one before analysis: `grep -c <expected-package/keyword> classes*.dex` and check `resources.arsc`/manifest for the package id — a 15 MB "success" can still be the mirror's own installer.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 15) — METHODOLOGY

- **Problem:** Sessions 9–14 recorded ZIV (and TLS) as "key rotated, not publicly reversed, NOT fixable in-repo" and treated it as a permanent wall. That framing was WRONG and cost ~5 sessions of the format sitting at 0/6. Once the user supplied the APK, extracting the current key took under an hour of static analysis. "Blocked on external key material" does NOT mean unfixable — it means nobody had extracted it yet. For an app-locked config format the key is IN the app; recovering it is routine RE, not a research dead end.
- **Cost:** 5 sessions of deferral (the format could have worked much earlier if an APK had been requested in Session 9).
- **Cause:** Over-trusting the "publicly reversed" heuristic — because the public decryptors (KMKZ/HCDecryptor) hadn't published the new key, we assumed it was unobtainable. But we can BE the ones who extract it.
- **Workaround / fix:** androguard static analysis of the config-import call graph. Two non-obvious pitfalls that wasted ~30 min: (1) androguard's `DEX.get_methods()` returns method-ID items with NO code — must iterate `DEX.get_classes()` → `ClassDefItem.get_methods()` → `EncodedMethod.get_code().get_bc().get_instructions()`; and `ClassDefItem` uses `.get_name()`, while `EncodedMethod` uses `.get_class_name()`. (2) The app used BouncyCastle's PKCS5S2 (obfuscated to classes `u3.c`/`v3.b`), so grepping the dex/.so for the string "pbkdf2"/"PBEKeySpec" found NOTHING and briefly (wrongly) suggested "the app doesn't use PBKDF2." Follow the call graph from the config-import Activity, don't string-grep for algorithm names.
- **Prevent next time:** When a format is "blocked on a rotated key," ask the user for the app APK and extract it — don't mark it unfixable. Method: find the config import/export Activity (`grep dex for ConfigImport/Export`), trace its call graph to the crypto helper class, read the password/salt/iteration/cipher from that class's `<clinit>` and decrypt method. androguard (pure Python, `pip install --only-binary :all: cryptography androguard`) works with NO JVM — useful because macOS `/usr/bin/java` is a stub and jadx can't run without a real JDK. **BUT** static extraction only works on UNPROTECTED apps — see the next entry.

---
## 2026-07-15 — Claude Code / claude-fable-5 (Session 16) — packers defeat static extraction

- **Problem:** Applied the ZIVPN static-extraction method to TLS Tunnel v8.0.6 and it failed after ~15 tool calls of tracing. Root cause: the app ships **DexProtector** (`libdexprotector.so`), a commercial packer that encrypts the app's own string pool and class code, decrypting only at runtime. Every AES/GCM/SecretKeySpec reference statically visible in the dex belonged to an unprotected third-party ad SDK (Digital Turbine Ignite `Lhm`, Conscrypt `Lo30`, Google Tink `zzhkh`, Mintegral `mbridge`) — all red herrings that looked plausible (`Lhm` even had `EncryptionManager`/AndroidKeyStore). A brute force of 148k extracted strings × 5 key derivations found nothing.
- **Cost:** ~15-20 tool calls chasing SDK crypto classes and a broad brute force, all dead ends.
- **Cause:** Didn't check for a packer FIRST. `ls lib/*/` would have shown `libdexprotector.so` immediately and set expectations before I traced anything.
- **Workaround / fix:** None static — DexProtector is designed to defeat this. The correct path is dynamic Frida on a rooted device/emulator (hook the cipher after the packer decrypts), which needs the user's device.
- **Prevent next time:** **FIRST step on any APK key hunt: `ls lib/*/` and grep for a packer** — `libdexprotector.so`, `libjiagu*.so` (360), `libAPKProtect*.so`, `libexec*.so`/`libapp-*.so`. If a packer is present, static extraction is futile for the app's OWN code — go straight to dynamic Frida (`docs/key-extraction.md` Method 2, on the user's device). Also: when static-searching for the config crypto, IGNORE ad-SDK packages (Digital Turbine/`dtx`/`ignite`/`OneDT`, mbridge/Mintegral, fyber, ironsource, inmobi, vungle, applovin, Google `gms.internal.ads`/Tink, Conscrypt) — they all use AES/GCM and will flood the results.

---
## 2026-07-16 — Claude Code / claude-fable-5 (Session 17) — previewing the frontend

- **Problem:** Verifying frontend UI changes visually is awkward on this repo. The in-app Chromium preview tool refuses `file://` URLs (rewrites to `https://file` and denies), so the Electron `loadFile` entry can't be opened directly. Serving the frontend over `python -m http.server` works, BUT the app's background config-poll (`loadConfigs` on an interval) hits the FastAPI backend, which — per ADR-2 CORS — only allows `file://`/`127.0.0.1:8742` origins, so from the `127.0.0.1:8090+` preview origin every poll fails and the failure path periodically re-rendered/cleared the DOM I'd injected (a decoded config), making measurements flip between correct (689px) and collapsed (43px). Also `python -m http.server` sends no-cache-defeating headers, so edited JS/CSS was served stale until I switched ports.
- **Cost:** ~20 min of confusion chasing a "collapsing section" that was actually the poll wiping injected DOM, plus several port switches to bust the JS cache.
- **Cause:** (a) preview tool blocks file://; (b) CORS (correctly) blocks the preview origin, so the app's polling errors and its error path disturbs the view; (c) http.server caches JS.
- **Workaround / fix:** Serve on a FRESH port after every JS/CSS edit (new origin = no cache). Before each injected render, run `for(let i=1;i<99999;i++){clearInterval(i);clearTimeout(i);}` and remove the boot overlay, so nothing re-renders under you. Inject a real config via `fetch('/_preview_X.json').then(...=>renderConfigDetail(cfg))` (copy the API's `/api/config/<id>` JSON into the frontend dir so it's same-origin) rather than relying on the app's own data load. Measure via DOM (`getBoundingClientRect`, row counts) — more reliable than screenshots, which can catch a transient pre-render/clobbered frame.
- **Prevent next time:** For a faithful visual check, the cleanest option is the REAL Electron app (file:// origin reaches the backend fine). For quick iteration without Electron: fresh-port http.server + clear-all-timers + inject-real-JSON, and trust DOM measurements over screenshots. A tiny `frontend/_preview.html` harness that clears timers and loads a fixture could institutionalize this. Remember to delete any `frontend/_preview_*.json` fixtures before committing (they're temp).

---
## 2026-07-24 — Super Z / unknown (Session 23)

- **Problem:** Fetching GitHub README pages via the `page_reader` function returns pages full of CSS noise and React data attributes (the GitHub SPA shell), not the rendered README. The signal-to-noise ratio was so low that the BugScanX PyPI page text came out as one giant CSS blob.
- **Cost:** ~10 minutes wasted trying to parse noise before switching strategy.
- **Cause:** `page_reader` returns the static HTML GitHub serves to non-JS clients, which is mostly stylesheet + JSON feature-flag payload — the actual README content is in a `<article>` tag buried in the noise.
- **Workaround / fix:** For GitHub README content, `curl -s -L https://raw.githubusercontent.com/<owner>/<repo>/<branch>/README.md` returns the raw Markdown directly — clean, parseable, no noise. This worked perfectly for both BugScanX and SNIbugtester READMEs.
- **Prevent next time:** Add to `system/environments.md` "Quirks" section: "For GitHub README content, prefer `curl https://raw.githubusercontent.com/...` over `page_reader` — page_reader returns GitHub's SPA shell, not the rendered README."

---
## 2026-07-24 — Super Z / unknown (Session 23)

- **Problem:** The `web_search` function returns snippets that are sometimes truncated mid-sentence or strip the most important keywords (the "Missing: …" suffix the search engine adds is misleading).
- **Cost:** ~5 minutes re-running searches with different query phrasing to confirm ECH had actually graduated from a draft to RFC 9849.
- **Cause:** The underlying search engine truncates snippets to a fixed length and tags missing query terms with "Missing: …" — which initially made me think ECH RFC results were about something else.
- **Workaround / fix:** When a search snippet shows "Missing: …" for terms that should be in the result, click through to the URL with `page_reader` (or `curl`) and read the actual page title — the snippet is misleading but the page itself is correct. For authoritative standards, prefer IETF Datatracker URLs (datatracker.ietf.org/doc/<rfc-number>) over blog posts — they have the canonical status.
- **Prevent next time:** No protocol change needed — this is just a search-result-formatting quirk. Future Z.ai sandbox agents should treat "Missing: …" in a snippet as a hint to verify by reading the page, not as evidence the result is wrong.

---
## 2026-07-23 — Claude Code / claude-opus-4-8 (Session 24)

- **Problem:** Electron can't be launched on this machine for headless UI verification (no display server — same limit prior local sessions hit). The SNI Host Hunter frontend has real logic (terminal arg-routing, job polling, Blob export) that `node --check` alone doesn't exercise.
- **Cost:** ~0 net — but a naive "syntax-check only" pass would have shipped a real bug: `looksLikePath("example.com")` returns true (its regex matches the `.com` suffix), so `sni scan example.com` would have misrouted a bare hostname into `seedlist_path` and 400'd.
- **Cause:** No Electron GUI + a heuristic (`looksLikePath`) borrowed from the `targets` command that doesn't fit hostnames.
- **Workaround / fix:** Built a small Node harness (`scratchpad/fe_harness.mjs`) that replicates the `main.js` IPC proxy handlers with `fetch` against the live backend, then `eval`s the real `frontend/src/scripts/api.js` (it only touches `window.vpnAPI`/`window.API`, no DOM) and drives `API.sni.*` end-to-end. This verified the api.js chain + response shapes and caught the arg-routing bug (fixed to a has-a-slash discriminator). Electron IPC *registration* + terminal DOM still need the packaged app — flagged for the user.
- **Prevent next time:** For frontend backend-call logic on this repo, the Node-harness-over-live-backend trick (mock `window.vpnAPI` = fetch, eval api.js) is a cheap, reliable way to verify the renderer→api→IPC contract without Electron. Consider a committed `frontend/test/` harness. renderer.js itself can't be loaded standalone (heavy DOM deps at module scope), so review its handlers by eye.

---
## 2026-07-23 — Claude Code / claude-opus-4-8 (Session 24)

- **Problem:** (minor) `python` is not on PATH on this machine (only `python3`), and each Bash tool call is a fresh shell — so a `curl | python -c ...` pipeline in a call that didn't `source .venv/bin/activate` failed with `python: command not found`, blanking a whole verification run.
- **Cost:** ~2 min (one re-run).
- **Cause:** Documented machine quirk (no bare `python`; venv gives `python` only when activated; exports don't cross Bash calls). I used `python` in a call that hadn't activated the venv.
- **Workaround / fix:** Use `python3` explicitly in any call that isn't inside an activated venv (or activate the venv at the top of every call that needs `python`). Backgrounded backends DO survive across calls, so the server stayed up while the parsing shell failed.
- **Prevent next time:** Already in `system/environments.md` (this machine's block). Reminder: default to `python3` in throwaway curl-parsing one-liners.

---
## 2026-07-23 — Claude Code / claude-opus-4-8 (Session 24)

- **Problem:** crt.sh (the CT-log discovery source) intermittently returns HTTP 502 Bad Gateway under its own load — one query 200, the next 502/timeout within seconds. During live testing the `/api/sni/discover` call hit a 502.
- **Cost:** ~0 — the endpoint's error path surfaced it cleanly (502 + logged), which is exactly the intended behaviour, so this doubled as verifying the error path. But it means "discover returned nothing" is ambiguous.
- **Cause:** crt.sh is a free, frequently-overloaded public service; 502/timeout is common, not a bug in InjectX.
- **Workaround / fix:** Treat crt.sh 502/timeout as transient — retry, or fall back to seedlist scanning. The prober half of the feature is independent of crt.sh, so a crt.sh outage never blocks `sni scan`.
- **Prevent next time:** Documented here + in the feature report. A Phase-2 improvement: retry crt.sh a couple of times with backoff before surfacing the error.

---
## 2026-07-23 — Claude Code / claude-opus-4-8 (Session 24)

- **Problem:** Session 23 (cloud) is logged 2026-07-24, but `date -u +%F` on this machine today is 2026-07-23 — so this session (24) legitimately *predates* session 23 by calendar date. Briefly confusing when picking the report filename and session date.
- **Cost:** ~2 min deciding how to date honestly without contradicting the existing memory.
- **Cause:** The Z.ai cloud sandbox clock ran ~a day ahead of real UTC during Session 23.
- **Workaround / fix:** Followed protocol Pitfall #41 (use `date -u`) — dated this session/report 2026-07-23 (true), and noted the ordering anomaly in the session entry + report so the next agent isn't confused. Kept the ADR-6/7/8 + feature-doc "2026-07-24" labels for continuity with the design proposal.
- **Prevent next time:** When session dates look out of order, check `date -u` on both environments — a cloud sandbox clock can drift. Trust `date -u`, document the skew, don't retro-edit prior entries.

---
## 2026-07-24 — Super Z / unknown (Session 26)

- **Problem:** Backgrounded backend processes (`python backend/main.py &` with `disown` or even `setsid`) are killed by the Z.ai sandbox between Bash tool calls. The backend would start fine, respond to a health check in the same call, then be dead by the next call — making multi-call verification impossible.
- **Cost:** ~10 minutes and 2-3 false "connection refused" failures before I switched strategy.
- **Cause:** The sandbox reaps background processes when the Bash tool call returns, even with `setsid` + `disown`. The `nohup` trick from the inefficiencies log doesn't help either.
- **Workaround / fix:** Run the backend AND the verification in a SINGLE Bash call. I wrote a self-contained Python script (`/home/z/my-project/scripts/verify_phase2.py`) that uses `subprocess.Popen` with `preexec_fn=os.setsid` to start the backend, runs every curl check in-process, and tears the backend down in a `finally` block. The backend stays alive for the duration of the script because the script itself is the foreground process. Same pattern for the Node harness (`verify_phase2_frontend.py`). This is the canonical way to do live backend verification in this sandbox.
- **Prevent next time:** Already documented in `system/environments.md` "Quirks" since Session 1 ("Electron cannot launch in this sandbox"). Add a sub-note: "Backgrounded Python backends are also killed between Bash calls — use `subprocess.Popen` in a single-call Python script for live verification."

---
## 2026-07-24 — Super Z / unknown (Session 26)

- **Problem:** dnspython's SVCB/HTTPS RR `params` dict is keyed by `ParamKey` enum instances, and `str(ParamKey.ECH)` returns `"5"` (the IANA numeric value), not `"ech"`. My first implementation of `extract_ech_config` matched on `str(k).lower() == "ech"`, which passed the unit tests (they used plain-string-keyed fixture objects) but missed every real ECH record. The live check against `crypto.cloudflare.com` returned `ech_capable=False` even though the host has a real `ech=` param.
- **Cost:** ~15 minutes of debugging (inspecting the live RR, comparing against the unit-test fixture, realizing the key-shape mismatch).
- **Cause:** Unit tests used synthetic RR objects with plain-string keys (`{"ech": "..."}`), which matched my string-comparison logic. The real dnspython RR uses enum-keyed params where `str(key)` is the numeric value. The unit tests couldn't catch this because they didn't use the real dnspython types.
- **Workaround / fix:** Changed `extract_ech_config` to iterate `params.items()` and match on `k.name.lower() == "ech"` (the enum's `.name` attribute is "ECH"). Added a live check against `crypto.cloudflare.com` to the verification script to confirm the enum-keyed path works. The unit tests still pass (the plain-string-keyed fixtures fall into the `else` branch which also works).
- **Prevent next time:** When unit-testing against a third-party library's types, include at least one integration test that uses the REAL type (not a synthetic stand-in). The protocol's "verify each fix end-to-end" preference caught this — the live curl against `crypto.cloudflare.com` surfaced the bug that the unit tests couldn't. Future agents: don't trust unit tests alone for third-party-type integration; always verify live.

---
## 2026-07-24 — Super Z / unknown (Session 26)

- **Problem:** The `certstream` package wasn't installed in the cloud sandbox venv when I went to verify the WATCH endpoint. The endpoint correctly returned 503 with the install hint (which is the designed behavior), but I had to `pip install certstream` separately to confirm the happy path would work — and even then, CertStream's websocket feed is unreliable from cloud sandboxes (it needs a persistent outbound websocket which corporate proxies often block).
- **Cost:** ~5 minutes; decided NOT to verify the certstream happy path live and instead rely on the unit tests for the parsing logic + the 503 path being curl-verified.
- **Cause:** `certstream` is an optional dep by design (the module raises `ImportError` if absent, the API layer surfaces it as 503). The cloud sandbox can't reliably maintain a websocket to the public CertStream feed.
- **Workaround / fix:** Documented in the review that the WATCH happy path is unit-tested but not live-verified, and that `pip install certstream` is the user's action to enable it. The 503 path IS live-verified.
- **Prevent next time:** For optional-dep features, always verify the "dep absent" path live (the 503) and the "dep present" path via unit tests + a documented manual verification step. Don't block shipping on live verification of an optional feature that depends on external network conditions the sandbox can't reproduce.
