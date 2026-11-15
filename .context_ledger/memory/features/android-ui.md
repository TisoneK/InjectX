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

## 9. Visual direction — REVISED (2026-11-14, after "looks AI-generated")
The first built pass (neon green/cyan on black, glowing borders, LED dots,
accent bars, a pulsing hex logo + a fake HUD status line) read as the generic
AI "hacker template" — the user's words: "vibe coded website", "looks ai
generated… it should feel natural". Corrected toward a calm, crafted feel:
- **Palette:** soft near-black (#15161A), ONE muted sage-green accent (#74B995),
  neutral text. No second neon accent; status uses muted tones only.
- **No decoration:** removed glows, LED dots, accent bars, pulse, HUD line,
  pill-spam, ALL-CAPS and wide tracking. Format tags are neutral; only status
  carries a muted colour. Flat single-tone logo.
- **Home:** modest left-aligned header (flat logo + name + one line) and a plain
  divider-separated tool list (title + subtitle + quiet chevron). Utility, not
  splash. (`app/ui/theme/*`, `ui/Brand.kt`, `ui/Components.kt`, `HomeScreen.kt`.)
- **Lesson:** the neon-cyber + decoration look is the AI-UI tell; craft comes
  from restraint, type hierarchy and intentional spacing — not more colour.
  Shipped as a CALIBRATION pass; a reference app from the user would anchor it
  best. Decode/SNI screens inherit the new theme; their components still get a
  de-decoration pass next.

## 10. Visual direction — v3 (2026-11-14, user reversed the calm pass)
The calm/non-neon pass (§9) was judged a regression: "cleaner layout but dropped
most of what made it feel like a product… keep the green/teal identity." Final
direction = **the neon identity + the calm pass's descriptions & disclaimer**:
- **Restore** the near-black green-tinted ground + neon-green/cyan identity and
  the color-coded format chips and a bold accent primary action (focal point).
- **Keep** from the calm pass: plain-language tool descriptions, the honest
  responsible-use disclaimer, and ONE navigation pattern throughout
  (hub-and-spoke; no mixing a menu-list home with tabbed tool screens).
- **Format list:** show ALL NINE formats (ehi, hc, ziv, dark, tls, npv, nsh,
  vhd, hat) — the calm pass showed only 5 (content inconsistency).
- **Empty states:** give a hint of the output (a sample decoded result / a
  "last scan" card) instead of a logo in a void.

### LOGO — the real fix (critical)
Every screen currently **hand-draws its own hexagon** (the Canvas `HexLogo`),
so they drift (thick-glow vs thin-muted). **None uses the real app icon.**
- Use the actual icon artwork (`assets/icons/icon.png`) as the ONE source for
  every placement (header, cards, Decode empty state) via a drawable + `Image`
  — NO Canvas redraws. Scale the same asset; never redraw.
- Logo appears **once per screen** (not header AND card).
- Done this session: added `res/drawable/injectx_logo.png` (the real icon) and
  replaced the Canvas logo with it.

## 11. SNI Hunter — functional rework (DONE 2026-11-14, commit aecaa96)
A universal tool must not ship carrier names. Rework:
1. **Remove hardcoded carriers** (safaricom/airtel/telkom seedlists). Seedlists
   are USER-supplied, saved + named by the user — no carrier presets.
2. **Network label:** user names the network they're testing ("Work SIM",
   "Dataless Airtel"); every result is tagged with it (a host that works on one
   network isn't assumed to work on another).
3. **One input** replaces the Seedlist/Domain toggle — accepts: a single domain;
   several separated by `;` / commas / spaces / newlines; or an imported `.txt`
   (one per line, rockyou-style, possibly huge).
4. **Cleanup on parse:** trim, lowercase, dedupe, strip `https://`, paths, ports
   and `*.` prefixes; ignore blank lines and `#` comments.
5. **Live count** before scan: "212 valid, 3 skipped", with a way to view the
   skipped lines. Large files: show line count on import.
6. **Start disabled** until ≥1 valid domain, and SAY why it's disabled.
7. **Two phases on two networks** (treat as separate steps, not one button):
   - **Discover** (real network): fetch subdomains (crt.sh) → candidate list.
   - **Test** (dataless network): user switches networks, tests which candidates
     actually work. Handoff copy: "Candidates saved. Switch to your dataless
     network, then run the test."
8. **Persist the candidate list** across the network switch, app restart and a
   dropped connection (filesDir JSON / DataStore).
9. **Network indicator** on the Test step (connected? which net?).
10. **Resume** a test from where it stopped if the connection drops.
11. **Results in 3 states:** works / fails / timed out. Export = working only,
    tagged with the network label.
12. SNI Hunter description should mention the two-step flow.

**Implementation (aecaa96).** All 12 points shipped:
- Core (pure, `SniHunterTest` 12 green): `DomainInput` (one flexible input →
  clean/dedupe/count + reasoned skips), `HuntSession`+`HuntCodec` (two-phase
  state, 3-state results, network labels, `pending()` resume frontier, JSON
  round-trip), carriers + `Seedlist.loadBundled`/`BUNDLED` + the bundled
  resource lists removed, `SniNetwork.probeOne` tags socket timeouts so results
  are 3-state, `Export.working(session)` = working-only tagged with the label.
- App: `HuntStore` (filesDir JSON after every probe — survives switch/restart/
  drop), `NetworkStatus`/`rememberNetworkInfo` (live Wi-Fi/Cellular/Offline
  chip), `SniScreen` rewritten as Step 1 Discover (input + `.txt` import + live
  count + skipped viewer + optional crt.sh) / handoff / Step 2 Test (network
  chip + label + start/pause/resume + 3-state rows + export). Start disabled
  until ≥1 valid host, with reason. Home subtitle mentions the two steps.
- **Honest limit:** network probing + persistence are compile-verified only
  (no device here). The pure logic is unit-tested. Deferred niceties: a saved,
  user-named seedlist *library* (§11.1 "saved + named") — currently a list is
  entered/imported per hunt, not persisted as a named library; and concurrency
  (probes run sequentially). Next: de-decorate Decode/SNI to neon v3; empty-state
  output previews; device run.

## 12. Home screen — finished product (DONE 2026-11-15, commit 492232f)
From a user concept screenshot + critique (the plain tool-list Home "feels
unfinished"): too much empty space, weak hierarchy, plain text rows, no
status/context. Target = a finished VPN-toolkit home, **keeping** the neon/
teal identity. Concept image kept at `features/home-concept.webp` (it is a
*visual concept*, not a spec to trace).

**Hard rule (user):** the network status and recent activity must show REAL
application data, never decorative placeholders.

**Shipped:**
- `HeroBanner` — "Your VPN toolkit" welcome, real app icon, subtle teal gradient.
- `ToolCard` — Decode / SNI Hunter as individual bordered cards: tinted icon
  tile (material-icons-extended: Description / CellTower) + description +
  chevron. Reused on the Tools tab.
- `NetworkPanel` — REAL connectivity (`rememberNetworkInfo`: Wi-Fi / Cellular /
  Offline), colored, Wi-Fi/cell/off icon, Check action.
- Recent activity — REAL: `:core` `ActivityLog` (ActivityEvent/Kind + codec +
  prepend/cap, `ActivityLogTest` 3 green) + app `ActivityStore` (filesDir).
  Rows written only on a real decode or finished SNI test; system relative time
  ("2 hours ago"); honest empty state.
- Bottom nav Home / Tools / Settings. Settings is real: version, Clear recent
  activity, Clear saved SNI hunt, responsible-use statement. Decode/SNI are
  pushed full screens (back returns to the tab).
- Decode + SNI report completion → the log reflects real use.

**Cost / limits:** material-icons-extended (BOM-versioned) bloats the DEBUG APK
~13M→20M (unshrunk); a release build with minifying strips unused icons.
Compile-verified only — the layout, network panel and activity need a device.
Next: device run to react to the real render; then de-decorate Decode result
view + SNI to match; empty-state output previews.
