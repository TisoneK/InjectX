# Universal Agent Kickoff — `.context/` Protocol Entry Point

> **Hand this file to the agent at the start of a chat session.** It's the
> universal entry point to the `.context/` agent-memory protocol. The full
> protocol lives in the `TisoneK/.context` package on GitHub — this file
> gets the agent through the door: get both repos on disk (a **local**
> IDE agent is already inside the project repo and clones only the package;
> a **cloud/sandbox** agent clones both), bootstrap or sync `.context/`,
> push the initial state, then hand off to the protocol's phases.

You are joining a project as a senior software engineer. Your objective:
understand the project, follow the protocol, do good work, leave the
codebase and its `.context/` memory in a better state.

---

## Pre-Flight (USER FILLS IN COMPLETELY BEFORE STARTING)

> The agent reads this section once and never asks the user to clarify
> or supplement it. If a field is blank, the agent uses the documented
> default. Fill in everything you have an opinion on.

### Project

- **Project Name:** <PROJECT_NAME>
- **Project Repository URL:** https://github.com/<OWNER>/<REPO>.git
- **Is the project repo private?** <Yes / No>
- **Live Application (if available):** <LIVE_URL or N/A>
- **Local repo path (LOCAL agents only — the already-cloned working dir):** <e.g., /Users/you/Code/<REPO> — leave blank for cloud/sandbox agents>

### Git Identity

- **Name:** <GIT_NAME>
- **Email:** <GIT_EMAIL>

### Agent Identity (USER FILLS IN — AGENT COPIES, NEVER GUESSES)

> **The user fills in the model version.** The agent must never *guess*
> its own model — a guess propagates as wrong data across sessions.
> Precedence for recording the model: (1) if the user filled it in below,
> copy that verbatim; (2) else, if your own system prompt states your exact
> model ID, record that (it's a fact, not a guess); (3) else ask the user
> once in chat; (4) if still unknown, record `unknown` — never fabricate a
> version number. Note: many agents' system prompts do NOT state the model,
> so (2) often doesn't apply — don't infer from marketing names or your
> family (e.g. "Claude" ≠ a version).

- **Agent name:** <e.g., Super Z, Claude Code, GitHub Copilot>
- **Model:** <e.g., glm-5.2, claude-sonnet-4, gpt-5, deepseek-v4-flash-free>
- **Platform:** <e.g., Z.ai cloud sandbox, local Windows machine, GitHub Actions>

### Session Parameters

> Defaults are shown in brackets — change if you want something different.

- **Scope:** discovery + review + fix all safe issues _[default]_
- **Target:** general sweep _[default — scan everything, fix safe issues. Other values: `refactor <path>`, `fix <bug>`, `feature <description>`, `review <area>`, or free text.]_
- **Focus areas:** all _[default]_
- **Findings handling:** fix safe issues; flag architectural changes _[default]_
- **Push policy:** push to main directly after each commit _[default]_
- **Deliverable:** report in `.context/reviews/` + chat summary _[default]_
- **Commit granularity:** one logical change per commit _[default]_

### GitHub PAT (PRIVATE REPOS ONLY)

> **⚠️ DO NOT PUT THE PAT IN THIS FILE.** The file upload pipeline redacts
> secrets — if you paste it here, the agent receives `[REDACTED:github_token]`
> and cannot clone.
>
> **Instead:** Paste the PAT directly in your first chat message after
> uploading this file. Say:
>
> > "Here's the PAT for the repo: `github_pat_...`"
>
> The agent will use it as a transient env var and never write it to any
> file. **Rotate the PAT after the session ends.**

### Package Repository (where the protocol lives)

- **Package repo URL:** https://github.com/TisoneK/.context.git
- **Is the package repo private?** No — it's public. Clone directly, no PAT needed.

---

## The Two-Repo Model

> **Read this before Step 0.** This protocol uses two repos. The agent
> needs both **on disk** before it can start work — but how many it clones
> depends on the agent type (see Step 0):
>
> - **Local agent** (IDE-integrated, runs on the developer's machine): the
>   project repo is **already cloned** — you're working inside it. You clone
>   **only** the package repo, as a sibling.
> - **Cloud/sandbox agent** (ephemeral sandbox, CI runner): you start empty
>   and clone **both**.

| Repo | What it holds | Cloned where |
|------|---------------|--------------|
| **Project repo** (the "root repo") | The product code + its `.context/` memory | `<workspace>/<REPO>` |
| **Package repo** (`TisoneK/.context`) | The protocol editions + skeleton + roles + consolidated flaws | `<workspace>/.context` |

The package repo is a **reference** — the agent reads the protocol from
it and copies the skeleton to bootstrap `.context/` in the project repo.
The package repo is NOT a submodule of the project repo; it's a sibling.
The agent never pushes to the package repo unless explicitly asked.

---

## How to use this file (two ways to set the Target)

1. **Pre-fill the Target field below** — set it once in the kickoff file
   before uploading. Good for repeat sessions where you know the target
   in advance.

2. **Include a target description in your chat message** — upload the
   kickoff file as-is (Target = general sweep), then in your first chat
   message describe what you want: "Fix the file upload 413 error" or
   "Refactor the agent loop" or "Add a settings export feature." The
   agent reads your chat message, extracts the target, and uses it as
   the session's Target — overriding the kickoff file's default. This is
   the natural flow for ad-hoc sessions where the target changes each
   time.

**The chat-message target wins.** If the kickoff file says "general
sweep" but your chat message says "fix the SSRF bug," the agent treats
the session as `Target: fix SSRF bug`. If the kickoff file says
"refactor loop.py" and your chat message is just "start," the agent
uses the kickoff file's Target. If both are set, the chat message
overrides.

---

## Step 0 — Get Both Repos on Disk

> **Do this before reading `.context/` or fetching the protocol.** The agent
> needs both repos on disk to proceed. **How you get there depends on your
> agent type — pick your branch first, then ignore the other one entirely.**

### 0a. Identify your agent type

- **Local agent** — IDE-integrated (Claude Code, Cursor, GitHub Copilot,
  Continue, …). Runs on the developer's machine, uses the user's existing
  git credentials, and the project repo is **already cloned on disk**.
  → Do **Local — Step 0** below. **Ignore every PAT / `GIT_TOKEN` instruction
  in this whole file** — they never apply to you.
- **Cloud/sandbox agent** — runs in an ephemeral sandbox (Z.ai, a CI runner,
  …), starts with **no repo on disk**, authenticates via a PAT.
  → Do **Cloud/sandbox — Step 0** below.

> **Unsure which you are?** Run `git remote get-url origin`. If it returns the
> Project Repository URL, you're already inside the repo — you're **local**,
> don't clone it again. If there's no repo (empty workspace, command errors),
> you're **cloud/sandbox**.

---

### Local — Step 0

**0-L.1 — Confirm you're in the project repo (do NOT clone it).**
```bash
pwd                          # should be <LOCAL_REPO_PATH>; cd there if not
git remote get-url origin    # should match the Project Repository URL
git status                   # tree should be clean before you start
```
- The repo is already on disk. **Never re-clone it.** If `pwd` isn't the repo,
  `cd` to the Pre-Flight **Local repo path**.
- **No PAT, ever.** `git push` / `git pull` already work with the user's
  configured credentials (SSH key, credential manager, `gh` CLI). If a push
  later fails with an auth error, **stop and tell the user** — it's their
  machine config, not yours to fix. Don't generate tokens or edit `.git/config`.
- **Don't set git identity** unless `git config user.name` returns empty. If it
  is empty, set it from Pre-Flight; otherwise leave the user's config untouched.

**0-L.2 — Clone ONLY the package repo, as a sibling of the project repo.**
```bash
cd ..                                                        # parent of the project repo
git clone https://github.com/TisoneK/.context.git .context
cd -                                                         # back into the project repo
```
- If `.context` already exists beside the repo, don't re-clone —
  freshen it: `git -C ../.context pull --ff-only`.
- **Heads-up on the name:** this clones the package one level **above** the
  project as `../.context` (matching the remote repo `TisoneK/.context`). That
  is a different directory from the project's own in-repo `.context/` memory
  dir — same basename, different location. Package = `../.context` (sibling);
  memory = `./.context` (inside the repo).

→ Go to **0c. Verify**.

---

### Cloud/sandbox — Step 0

**0-C.1 — Set up the PAT (if the project repo is private).**
```bash
# Get the PAT from the user's first chat message. Export as env var.
# Never write it to any file. Never echo it.
export GIT_TOKEN='<from-chat>'
```

**0-C.2 — Clone the project repo (the "root repo").**
```bash
cd <workspace>  # e.g., /home/z/my-project or C:\Users\tison\Dev

# If private:
git clone "https://x-access-token:${GIT_TOKEN}@github.com/<OWNER>/<REPO>.git" <REPO>
cd <REPO>
# IMMEDIATELY strip the token from .git/config
git remote set-url origin https://github.com/<OWNER>/<REPO>.git

# If public:
git clone https://github.com/<OWNER>/<REPO>.git <REPO>
cd <REPO>
```

Configure git identity (a fresh sandbox has none):
```bash
git config user.name "<GIT_NAME>"
git config user.email "<GIT_EMAIL>"
```

**0-C.3 — Clone the package repo (public — no PAT).**
```bash
cd <workspace>
git clone https://github.com/TisoneK/.context.git .context
```

> **DO NOT unset `GIT_TOKEN` yet** — it's needed for every push this session.
> It stays an env var for the whole session and is unset at the very end
> (protocol Step 19). *(Cloud/sandbox only — local agents have no token.)*

→ Go to **0c. Verify**.

---

### 0c. Verify both repos are present

```bash
# Local agent — project repo is the cwd; package is a sibling:
ls .                       # project repo (your working dir)
ls ../.context     # package repo with protocol + skeleton

# Cloud/sandbox agent — both live under the workspace:
ls <workspace>/<REPO>
ls <workspace>/.context
```

You should see:
- the project repo — its code (and `.context/` if it already exists)
- `.context/ai-engineering-protocol.md` — cloud/sandbox edition
- `.context/ai-engineering-protocol-local.md` — local agent edition
- `.context/context-skeleton/` — the 17-file stub tree
- `.context/roles/` — role overlays
- `.context/QUICKSTART.md` — the two-repo mental model

> **Paths from here on.** After Step 0 your cwd is the **project repo root**
> for both agent types, and the package repo is a **sibling** of it. So
> wherever the steps below write `<workspace>/<REPO>`, read "the repo root
> (your cwd)", and wherever they write `<workspace>/.context`, read
> **`../.context`** — that relative path is correct for local and
> cloud/sandbox agents alike.
>
> **Two `.context` names, don't conflate them:** `../.context` (one level
> **up**, a sibling of the project) is the **package clone**; `./.context`
> (**inside** the project) is that project's **memory dir**. Package paths in
> the steps below are always `../.context/...`; memory paths are always
> `.context/...`.

---

## Step 1 — Check if `.context/` Exists in the Project Repo

> **Two paths.** Follow ONLY ONE based on whether `.context/` already
> exists in the project repo.

### Path A: `.context/` does NOT exist (first session on this project)

This is a **bootstrap**. Create `.context/` from the skeleton, fill in
the initial data, commit, and push — BEFORE starting the protocol phases.

#### 1a. Copy the skeleton into the project repo

```bash
# From the project repo root (your cwd). The package is a sibling, so
# ../.context works for both local and cloud/sandbox agents.
cp -r ../.context/context-skeleton .context
```

Verify the skeleton landed (17 files including the self-gitignored `secrets/`):
```bash
find .context -type f | sort
# Should include: README.md, SYNC.md, agents/sessions.md, flaws/,
# inefficiencies/, plans/, reviews/, secrets/.gitignore, secrets/README.md,
# system/, tasks/, user/, workflows/
```

#### 1b. Fill in the initial `.context/` data

Using the Pre-Flight values above, fill in these files (overwrite the
placeholder content):

- **`.context/user/identity.md`** — name, git identity, GitHub username, role, timezone
- **`.context/user/preferences.md`** — workflow, communication, code style, review depth, risk & approvals (seeded from Pre-Flight session parameters)
- **`.context/workflows/active.md`** — protocol edition (cloud vs local), protocol source URL, scope, focus areas, push policy, commit style, deliverable
- **`.context/system/environments.md`** — this machine/sandbox: OS, runtimes, package manager, verified commands, quirks
- **`.context/system/ai-models.md`** — this agent + model: first row in the registry
- **`.context/tasks/current.md`** — set to this session's task (or "idle" if just bootstrapping)
- **`.context/agents/sessions.md`** — first session entry

For the **protocol source** field in `workflows/active.md`, use:
- Cloud/sandbox agent: `https://github.com/TisoneK/.context/blob/main/ai-engineering-protocol.md`
- Local agent: `https://github.com/TisoneK/.context/blob/main/ai-engineering-protocol-local.md`

Read each file's HTML-comment template before filling it in — don't
invent formats.

#### 1c. Commit and push the bootstrap

```bash
cd <workspace>/<REPO>
git add .context/
git commit -m "chore(context): bootstrap .context/ directory with initial session data

Bootstrapped from TisoneK/.context context-skeleton. Filled in:
- user/identity.md, user/preferences.md
- workflows/active.md (protocol edition + source URL)
- system/environments.md, system/ai-models.md
- tasks/current.md, agents/sessions.md

First agent session on this repo."
```

Push:
```bash
# LOCAL agent — credentials already configured, no token dance:
git pull --ff-only && git push origin main

# CLOUD/SANDBOX agent, private repo — re-add token for the push, then strip it:
git remote set-url origin "https://x-access-token:${GIT_TOKEN}@github.com/<OWNER>/<REPO>.git"
git push origin main
git remote set-url origin https://github.com/<OWNER>/<REPO>.git

# CLOUD/SANDBOX agent, public repo:
git push origin main
```

**Why push before starting the phases:** if the session dies during
Phase 1, the `.context/` memory is already on remote — the next agent
picks up where this one left off, not from scratch.

#### 1d. Proceed to Step 2

### Path B: `.context/` already exists (subsequent session)

This is a **sync**. Pull the latest, read the existing memory, then
proceed to the protocol phases.

```bash
cd <workspace>/<REPO>
git pull --ff-only
```

If pull fails (non-fast-forward), STOP and report: "Local branch has
diverged from remote. Please sync manually before I start."

If the working tree has unexpected changes (files you didn't touch),
STOP and report — don't stash or discard someone else's work.

**Proceed to Step 2.**

---

## Step 2 — Read `.context/` (Agent Memory)

> **Now `.context/` exists and is synced.** Read it before fetching the
> protocol or doing any work.

Read in this order:
1. `.context/README.md` — orientation
2. `.context/workflows/active.md` — which protocol edition to follow + where to fetch it
3. `.context/agents/sessions.md` — who worked here before, with which model, on which machine (read the last 3–5 entries)
4. `.context/tasks/current.md` — is a task marked in-progress? A prior session may have died mid-task.
5. `.context/tasks/backlog.md` — open items waiting for a session like this one
6. `.context/inefficiencies/log.md` — known traps (tool failures, flaky tests, env quirks). **Don't re-hit a logged trap.**
7. `.context/flaws/log.md` — workflow-level problems already found. **Don't repeat them.**
8. `.context/plans/decisions.md` — architectural decisions already made. **Don't relitigate them; don't "fix" code into violating them.**
9. `.context/system/environments.md` + `.context/system/ai-models.md` — environments and agents seen before
10. `.context/user/identity.md` + `.context/user/preferences.md` — who the user is and how they like things done
11. `.context/secrets/` — local-only secret values available on this machine (never tracked; empty on a fresh clone). Note what's available — never print values.

---

## Step 3 — Load the Protocol

> **Reading `workflows/active.md` is a binding instruction, not passive
> documentation.** After reading it, immediately load the protocol file
> it references before any other tool use.

The protocol file is in the package repo you cloned in Step 0c. You
don't need to fetch it from GitHub — read it from disk:

```bash
# Cloud/sandbox agent:
cat <workspace>/.context/ai-engineering-protocol.md

# Local agent:
cat <workspace>/.context/ai-engineering-protocol-local.md
```

If `workflows/active.md` says to use a role overlay, also read:
```bash
cat <workspace>/.context/roles/<role>.md
```

**Read the full protocol before proceeding.** It's ~800 lines. Take the
time. The protocol is the instruction set for this session — don't
skim it.

---

## Step 4 — Follow the Protocol

You now have:
- ✅ Both repos on disk — package cloned; project cloned too if cloud/sandbox (Step 0)
- ✅ `.context/` bootstrapped or synced (Step 1)
- ✅ `.context/` read (Step 2)
- ✅ Protocol loaded (Step 3)

**Now follow the protocol's 19 steps across 4 phases:**
- Phase 1: Setup (the protocol's Step 1 picks up from here — install deps, read docs, discovery, baseline)
- Phase 2: Review
- Phase 3: Fix
- Phase 4: Report & Context

The protocol is binding. Follow it in order. Don't skip Phase 1 because
the task seems small. Don't ask the user for confirmation on default
next steps. Don't forget the Exit checklist.

---

## Two Surfaces — Know Which One You're On

> Every repo managed by this protocol has two surfaces. An agent edits
> one or the other — never both in the same commit — and must know which
> one it's on at all times.

1. **The project** — product code, docs, tests, config. Commits use
   normal prefixes (`fix:`, `feat:`, `docs:`). Friction with the project
   goes in `.context/inefficiencies/log.md`.
2. **`.context/`** — agent memory. Commits use `chore(context):`. Friction
   with the `.context/` system or the protocol itself goes in
   `.context/flaws/log.md`.

If you're editing a file under `.context/`, you're in **memory mode**.
If you're editing anything else, you're in **project mode**.

---

## Session Lifecycle

- **ENTRY (Steps 0–3 above):** Get both repos on disk — local agents clone only the package (the project is already there); cloud/sandbox agents clone both → bootstrap or sync `.context/` → read `.context/` → load the protocol. Don't edit any project file until the protocol's Phase 1 is complete.
- **WORK (protocol Phases 1–4):** Follow the 19 steps in order. Don't skip. Don't ask for confirmation on defaults.
- **EXIT (protocol Step 19):** All commits pushed, report written and pushed, `.context/` updated and pushed, `tasks/current.md` cleared, PAT unset (cloud/sandbox only), chat summary delivered. **If the user has to remind you to commit or push, the protocol failed — log it as a flaw.**

---

## Don't

- **Don't start the project's server** unless the task requires it. "Start context workflow" means follow this protocol, not run the app.
- **Don't grep the codebase for "context"** to find the protocol — that finds the project's context features, not the `.context/` protocol directory. Read `.context/` directly.
- **Don't guess your model version.** Ask the user or record `unknown`.
- **Don't skip Phase 1** because the task seems small.
- **Don't forget the Exit checklist** — a session isn't done until everything is committed, pushed, and logged.
- **Don't push to the package repo** (`TisoneK/.context`) unless explicitly asked. It's a reference, not your workspace.
- **Don't unset `GIT_TOKEN`** until the protocol's Step 19 (the very last step). It's needed for every push. *(Cloud/sandbox only — local agents never use a PAT; `git push` uses the user's existing credentials.)*

---

## Quick Reference

| If you need... | Look in... |
|---|---|
| The protocol file | `<workspace>/.context/ai-engineering-protocol.md` (or `-local.md`) |
| The skeleton (for bootstrapping) | `<workspace>/.context/context-skeleton/` |
| Role overlays | `<workspace>/.context/roles/` |
| The two-repo mental model | `<workspace>/.context/QUICKSTART.md` |
| Prior agent sessions | `<REPO>/.context/agents/sessions.md` |
| Open tasks | `<REPO>/.context/tasks/backlog.md` |
| Known traps | `<REPO>/.context/inefficiencies/log.md` |
| Protocol problems found | `<REPO>/.context/flaws/log.md` |
| Architectural decisions | `<REPO>/.context/plans/decisions.md` |
| Your environment's quirks | `<REPO>/.context/system/environments.md` |
| Which models have worked here | `<REPO>/.context/system/ai-models.md` |
| User preferences | `<REPO>/.context/user/preferences.md` |
| Secret values (local agents only) | `<REPO>/.context/secrets/` (gitignored, never tracked) |

---

## Final Note

This file is a **universal pointer**. It works for any project using the
`.context/` protocol — fill in the Pre-Flight, hand it to the agent, and
the agent will clone both repos, bootstrap or sync `.context/`, load the
protocol, and follow it. The real protocol is 800+ lines and lives in
`TisoneK/.context`. This file just gets the agent through the door.
