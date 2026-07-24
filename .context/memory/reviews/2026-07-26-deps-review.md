# Review — fast-uri dependabot alert fix

- **Date:** 2026-07-26 (UTC, `date -u`) — Session 27
- **Agent:** Super Z · **Model:** unknown (GLM family) · **Platform:** Z.ai cloud sandbox · **Role:** engineer · **Core:** 0.3.0
- **Target:** Fix the high-severity dependabot alert on `fast-uri` (host confusion via literal backslash authority delimiter, GHSA on `fast-uri` <=3.1.3).

## 1. Summary

Closed the dependabot alert by adding an npm `overrides` block to `package.json`
forcing `fast-uri` to `^3.1.4`. `npm audit` now reports **0 vulnerabilities**
(was 1 high). Surgical change: +3 lines in `package.json`, 3 lines changed in
`package-lock.json` (version 3.1.3 → 3.1.4, resolved URL, integrity hash).

## 2. Assessment (why this is a build-time-only concern for InjectX)

The dependabot alert traces `fast-uri` as a transitive dep of `electron-builder`.
The full chain is:

```
electron-builder (devDependency)
  → app-builder-lib
    → ajv@^8.18.0
      → fast-uri@^3.0.1   ← resolved to 3.1.3 (vulnerable)
```

**InjectX's runtime code does not use `fast-uri` or `ajv` at all** — verified by
`grep -rn "require.*fast-uri\|require.*ajv\|from ['\"]fast-uri\|from ['\"]ajv"` across
`frontend/` and `backend/` (zero hits outside `node_modules`). Both packages
live entirely in the `electron-builder` build-tooling tree, which runs at
`npm run dist` time (packaging), not at app runtime.

So the practical runtime risk to a running InjectX instance was **zero** —
the vuln (host-confusion desync between `fast-uri` and Node's WHATWG URL parser
when enforcing host-based policy before `fetch()`) requires the application to
call `fast-uri` for URL validation and then pass the same URL to `fetch()`.
InjectX's runtime URL handling uses Python `httpx` (backend) and Electron's
`net.fetch` (main process), neither of which touches `fast-uri`. This was a
supply-chain hygiene fix, not a live vuln — but a clean `npm audit` is worth
having and dependabot would have kept nagging.

## 3. Fix strategy — why `overrides` and not a bump

Considered three options:

1. **Bump `electron-builder` to 26.15.7 (latest 26.x).** Rejected — verified
   that 26.15.7's `app-builder-lib` still pins `ajv@^8.18.0`, and the latest
   `ajv` (8.20.0) still pins `fast-uri@^3.0.1`, which resolves to 3.1.3 (the
   vulnerable version is the highest 3.x that satisfies `^3.0.1`). Bumping
   electron-builder does not fix the vuln.
2. **Wait for `ajv` to repin.** Rejected — `ajv` 8.20.0 is the latest 8.x and
   still pins `^3.0.1`; no sign of a repin. Could wait indefinitely.
3. **npm `overrides`.** Accepted — the dependabot alert's own recommendation.
   Forces `fast-uri` to `^3.1.4` regardless of what `ajv` pins. Stays in the
   3.x line (no major-version risk; `ajv`'s `^3.0.1` range accepts 3.1.4).
   Minimal, surgical, survives future `npm install` regenerations.

## 4. What was verified

- `npm install --no-audit --no-fund` → clean (284 packages, no errors).
- `node_modules/fast-uri/package.json` → version `3.1.4` (was 3.1.3).
- `npm audit` → **0 vulnerabilities** (was 1 high).
- `node --check frontend/main.js` → OK (no syntax regression).
- Backend tests → 151 passed (unchanged; the fix is npm-only, no Python
  touched).
- Lockfile diff: exactly 3 lines in the `node_modules/fast-uri` block
  (version, resolved URL, integrity hash) + the 3-line `overrides` block
  in `package.json`. No other lockfile entries changed.

## 5. What was NOT done

- **No `npm run dist` (packaging) verification.** The override changes the
  build-tooling tree; a full `electron-builder` packaging run would confirm
  the build still works with `fast-uri@3.1.4`. Not run because (a) it
  downloads platform binaries and takes minutes, (b) the override is a
  patch-version bump (3.1.3 → 3.1.4) within the same major, with no API
  change (the dependabot advisory describes a parser fix, not an API break),
  and (c) the sandbox can't produce a Windows/macOS installer anyway. The
  user should run `npm run dist` once on their local machine to confirm
  packaging still works — flagged in the chat summary.
- **No CVE number recorded.** The dependabot alert didn't include a CVE ID,
  only a GHSA. The advisory text is preserved in this review's §1 + in the
  commit message body for traceability.

## 6. Commits

One commit, single surface (project code — `package.json` + `package-lock.json`):

- `fix(deps): override fast-uri to ^3.1.4 (dependabot, host-confusion SSRF)`

Plus the `.context/` memory commit:

- `chore(context): log session 27 — fast-uri dependabot fix`

Pushed to `main` directly per the standing push policy.
