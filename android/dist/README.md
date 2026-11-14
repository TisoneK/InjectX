# Debug APK archive

Version-controlled debug builds, so a build is never lost by overwriting the
Desktop copy. Each file is named `injectx-debug-v<versionName>-<shortsha>.apk`
(a `-dirty` suffix means it was built from an uncommitted tree).

Build + archive + copy-to-Desktop in one step:

```bash
android/scripts/export-apk.sh
```

Notes:
- These are debug-signed (v1 + v2 + v3) and installable via sideload; they are
  NOT release builds.
- The APKs are committed directly (no git-lfs on this machine). If the archive
  grows large, switch to git-lfs (`git lfs track 'android/dist/*.apk'`) or move
  to GitHub Releases, and prune old blobs.
