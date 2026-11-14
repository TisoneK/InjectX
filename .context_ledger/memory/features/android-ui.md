# Android UI / UX design spec

> **Status:** **Proposed — not built.** Direction captured 2026-11-14 (Forge,
> Session 34) after the user's note: the UI "needs real work and creativity",
> and Decode shouldn't be the de-facto home — "home/main screen instead of
> treating decode as main… think outside the box for the design, tabs etc."
> The current app is the redesigned-but-flat version (branded theme + a top
> `Decode | SNI Hunter` segmented tab bar, Decode shown first). See
> `features/android-app.md` for the app as a whole; this doc is the UI rework.

## 1. Problem with the current UI
- **Decode is the implicit home.** The app opens straight into the Decode
  empty-state; SNI Hunter is a co-equal tab. There's no neutral landing that
  frames InjectX as a toolkit.
- **Top segmented tabs are flat.** They read as "two modes bolted together",
  not a product. No sense of place, no identity moment, no room to grow (a 3rd
  tool would crowd the bar).
- The brand (near-black, neon-green X, cyan circuit, red shield; a
  cyber/terminal feel) is only lightly expressed.

## 2. Goals
1. A real **Home** that is the app's center of gravity — identity + launcher.
2. Navigation that scales past two tools and feels intentional, not tabbed.
3. Lean into the brand: terminal/HUD aesthetic, monospace, restrained neon.
4. Keep it all compile-safe Compose (single-activity, no device to runtime-test
   here — correctness by construction + the existing `ui/` components).

## 3. Information architecture
**Hub-and-spoke** (recommended): `Home` is a launcher; tools are destinations
you enter and back out of.

```
Home (hub)
 ├─ Decode        (file → detect → decrypt → NormalizedConfig)
 └─ SNI Hunter    (seedlist/domain → scan → verdicts → export)
   (future: Tunnel, About/Responsible-use, Settings)
```
- Back from a tool returns to Home (system back + an in-app back affordance).
- Keep a lightweight top bar on tool screens (logo + screen title + back).
- **Alternative considered:** a bottom nav (`Home · Decode · SNI`). Simpler but
  less "hub"; good if the user prefers always-visible switching. Decision is the
  user's taste — see §7.

## 4. Home screen spec
- **Hero band:** the Canvas `HexLogo` (already built) at ~96dp with a subtle
  slow pulse/glow; `INJECTX` wordmark (monospace, tracked); one-line tagline
  ("VPN tunnel config toolkit"). Optional: a faint scanline/grid texture behind
  the hero for the HUD feel (drawn, flat — no heavy effects).
- **Tool modules:** large tappable cards, one per tool, styled like "modules"
  on a console:
  - leading mark (a small format-agnostic glyph or the tool's accent bar),
  - title + one-line description,
  - a status LED dot in the tool's accent (green for Decode, cyan for SNI),
  - press → navigate into the tool.
- **Recent strip (phase 2):** horizontally scrollable chips of recently decoded
  files (needs small on-device history persistence — DataStore/room-free JSON in
  filesDir). Tap re-opens the result. Omit until persistence exists.
- **Footer:** tiny version + a one-tap "Responsible use" note (the SNI/bug-host
  framing from the README) — keeps the dual-use framing visible.

## 5. Tool screens (mostly keep, reframe entry)
- **Decode:** the current empty/loading/result/error flow, but reached from Home
  (no tab bar). Result screen unchanged (header card + CONNECTION rows + warnings
  + JSON + export). Consider a brief "decrypting…" reveal animation on success.
- **SNI Hunter:** current Discover → scan → verdict rows → export, reached from
  Home. Add a "use this host as SNI" action that bridges a working host into a
  decoded config (ties into `features/android-app.md` next-steps).

## 6. "Outside the box" ideas (pick/trim to taste)
- **Console/HUD home**: the hub framed as a device console — modules as lit
  tiles, a blinking cursor in the wordmark, a status line ("core: ready ·
  schemes: A5/B2/H1/I1 · sni: armed").
- **Drag-and-drop decode**: a drop target on Home/Decode for config files.
- **Decrypt reveal**: on a successful decode, animate fields in as if being
  "cracked" (staggered reveal), nodding to the tool's nature.
- **Per-format identity**: each format keeps its accent throughout (badge →
  header tint), so a `.ziv` vs `.ehi` feels visually distinct.

## 7. Open decisions (need the user)
1. **Nav pattern:** hub-and-spoke (recommended) vs. bottom nav vs. both (home
   hub + bottom nav).
2. **How much "HUD":** restrained (clean cards) vs. full console/scanline vibe.
3. **Home content:** tools-only, or tools + recents + a small status/among-stats
   block.
4. Any reference app whose feel the user wants to match.

## 8. Build notes
- Reuse `ui/Brand.kt` (`HexLogo`, `formatColor`, `statusColor`, `verdictColor`),
  `ui/Components.kt` (`Pill`, `SectionCard`, `SegmentedTabs`), `ui/theme`.
- Navigation can be a simple `when(screen)` state machine in `MainActivity`
  (no Navigation-Compose dependency needed for 3 screens) — Home drives a
  `var screen by remember { mutableStateOf(Screen.Home) }`; system-back handled
  via `BackHandler`.
- When the pattern is chosen, record it as an ADR in `plans/decisions.md`.
