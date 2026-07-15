# Project Kickoff — `.context/` Workflow Entry Point (Inbound)

<!-- GENERATED AT BOOTSTRAP — the universal kickoff's Step 1c fills this in.
This file is DATA (project-owned, never overwritten by structural sync).

Generation rules for the bootstrapping agent:
1. Fill every fact <PLACEHOLDER> OUTSIDE this HTML comment — in "Project
   Facts", in the intro blockquote (the clone URL), AND in the Entry
   Steps code blocks (repo URLs, git identity) — from the external
   kickoff's Pre-Flight + what you verified on disk (git remote, default
   branch). Facts you verified beat facts the user typed — record what's
   true. Record each repo's privacy mode SEPARATELY — project and
   package each get their own field; never copy one repo's mode onto the
   other. The ONLY placeholders that stay symbolic are the token forms
   (`<..._WITH_TOKEN_IF_PRIVATE>`, `${GIT_TOKEN}`, `${PKG_TOKEN}`) —
   never a real token. After filling, scan:
   `grep -n "<PROJECT\|<GIT_\|<LIVE_\|<REPO>" .context/kickoff.md` —
   hits are allowed only inside this comment and in the token forms.
2. Do NOT copy session parameters here — they live in workflows/active.md
   (single source of truth). This file only points at them.
3. Do NOT put secrets, PATs, or tokens anywhere in this file. Ever.
4. Delete nothing else — the Entry Steps below are pre-written and
   correct for every post-bootstrap session. Fill their fact
   placeholders (rule 1) but change no step logic.
5. Keep facts current in later sessions: if a fact changes (repo renamed,
   new default branch, live URL added), update it in place and note the
   change in your session entry.
-->

> **This is the project's own kickoff file.** It was generated during the
> first `.context/` session and supersedes the external universal kickoff
> for this repo — no more carrying a copy around. To start a session,
> point any agent here:
>
> - **Local agent** (already inside the repo): *"Read `.context/kickoff.md`
>   and follow it."* Add a target description in the same message if you
>   have one.
> - **Cloud/sandbox agent** (empty workspace): *"Clone
>   `https://github.com/TisoneK/InjectX.git`, read `.context/kickoff.md`, follow it."* Paste
>   PAT access for every repo marked private in Project Facts below in
>   that same chat message — recommended: **one fine-grained PAT scoped
>   to all of this workflow's private repos** (say "covers both");
>   separate per-repo PATs work too, named. Never into any file.

---

## Project Facts (generated — keep current)

> **Privacy is per-repo.** Each repo below carries its own privacy mode —
> never infer one from the other. A public project with a private package
> (or the reverse) is a normal setup. Cloud/sandbox agents need PAT
> access for every repo marked private — and for **every push, even to a
> public project repo** — recommended as **one fine-grained PAT scoped
> to all of them** (Contents: Read and write for the project; Read-only
> suffices for the package). Ask for it up front, before any clone.
> Local agents need none.

- **Project name:** InjectX
- **Project repository URL:** https://github.com/TisoneK/InjectX.git
- **Project repo privacy:** Public
- **Default branch:** main
- **Live application:** N/A
- **Git identity:** Tisone Kironget `tisonkironget@gmail.com`
- **Package repo (the protocol):** https://github.com/TisoneK/.context.git
- **Package repo privacy:** Private (verified 2026-07-15 — unauthenticated clones 404; PAT auth via fine-grained PAT succeeds)
- **Protocol edition:** local agents → `ai-engineering-protocol-local.md`; cloud/sandbox agents → `ai-engineering-protocol.md`

## Session Parameters

Standing defaults live in [`workflows/active.md`](workflows/active.md) —
scope, target, push policy, deliverable, commit style. **A target in the
user's chat message overrides the standing Target.** If the chat message
is just "start," use the standing Target.

**Agent identity:** never guess your model version. If your system prompt
states the exact model ID, record that; otherwise ask the user once, or
record `unknown`.

---

## Entry Steps (every session after bootstrap)

`.context/` already exists in this repo — there is no bootstrap path here.
Every session is a **sync** session.

### Step 0 — Get both repos on disk

**Local agent** — the project repo is your cwd (never re-clone it). Get
the package as a sibling. **Identify the package by its REMOTE URL,
never by directory name** — local clones exist under different names
(`../context` is canonical; legacy `../.context` occurs):

```bash
git remote get-url origin        # confirm it matches the Project repository URL

# Find an existing package clone among the siblings:
PKG=""
for d in ../context ../.context; do
  git -C "$d" remote get-url origin 2>/dev/null | grep -q "TisoneK/.context" \
    && PKG="$d" && break
done

if [ -n "$PKG" ]; then
  # Found — freshen it. A FAILED PULL IS NOT A MISSING PACKAGE:
  # use the on-disk copy as-is and note the stale pull in your session log.
  git -C "$PKG" pull --ff-only || echo "pull failed — continuing with on-disk copy at $PKG"
else
  git clone https://github.com/TisoneK/.context.git ../context && PKG=../context
fi
echo "package clone: $PKG"
```

**Never clone when a package clone already exists** — cloning into an
existing directory fails, and retrying that failure loops forever. One
find → one decision → move on. No PAT, ever — clones and pushes both
use the user's existing credentials, whatever either repo's privacy
mode. If one fails with an auth error, stop and tell the user.

**Cloud/sandbox agent** — clone both into the workspace. Each repo's
clone follows **its own** privacy field in Project Facts above:

```bash
# Project repo (public — no PAT needed for the clone, but PAT IS needed for every push):
git clone https://github.com/TisoneK/InjectX.git InjectX && cd InjectX
git config user.name "Tisone Kironget" && git config user.email "tisonkironget@gmail.com"

# Package repo (PRIVATE — PAT from chat covers it; strip token from .git/config right after;
# the package is read-only reference, never pushed to — drop PKG_TOKEN after this clone):
git clone "https://x-access-token:${PKG_TOKEN}@github.com/TisoneK/.context.git" ../context
git -C ../context remote set-url origin https://github.com/TisoneK/.context.git
unset PKG_TOKEN
```

Ask for PATs **up front, before any clone** — you need one for every
push (even to a public project repo) and for every private clone; a
missing credential is a missing input, not a permission question. If a
repo is marked private and no PAT covering it arrived in chat, stop
and ask for one by repo name. When one shared fine-grained PAT covers
both, `PKG_TOKEN` is just `GIT_TOKEN` — still drop `PKG_TOKEN` after the
package clone, and keep `GIT_TOKEN` as an env var for the session's
pushes, unset only at the protocol's final step. Never write any token
to any file.

### Step 1 — Sync

```bash
git pull --ff-only
```

If the pull fails (diverged) or the tree has changes you didn't make,
**stop and report** — don't stash or discard someone else's work. Then
sync structural files from the package skeleton per [`SYNC.md`](SYNC.md)
(add missing, update differing; never touch data files).

### Step 2 — Read `.context/` (this directory)

In order: `README.md` → `workflows/active.md` → `agents/sessions.md`
(last 3–5 entries) → `tasks/current.md` → `tasks/backlog.md` →
`inefficiencies/log.md` → `flaws/log.md` → `plans/decisions.md` →
`system/` → `user/` → note what's in `secrets/` (never print values).

### Step 3 — Load the protocol

Pick the edition by **YOUR agent type** (identified in Step 0), from the
package clone found there (`$PKG`, canonically `../context`):
- **Local agent** → `$PKG/ai-engineering-protocol-local.md`
- **Cloud/sandbox agent** → `$PKG/ai-engineering-protocol.md`

`workflows/active.md` gives you the protocol *source/version* and any
role overlay — it does **not** choose your edition. If it names a single
edition, that's whichever agent type wrote it last; ignore that and
follow your own type (a local agent must never run the cloud edition's
PAT/clone steps, whatever the memory says). Also read any role overlay
from `$PKG/roles/`. Read your edition in full; it is the instruction
set for this session.

### Step 4 — Follow the protocol

All 19 steps, all 4 phases, in order. Don't skip Phase 1 because the task
seems small. Don't forget the Exit checklist: everything committed and
pushed, session logged, `tasks/current.md` cleared, chat summary
delivered.

---

## If this file is stale or missing

The template lives in the package at `context-skeleton/kickoff.md`.
Regenerate by copying that template and filling **Project Facts** from
this directory's own memory (`user/identity.md`, `workflows/active.md`,
`git remote get-url origin`). Commit as
`chore(context): regenerate kickoff.md`.
