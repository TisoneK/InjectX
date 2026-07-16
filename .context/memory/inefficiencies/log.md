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
