/**
 * InjectX // CIPHER_OPS — Renderer v0.5.0
 *
 * Design goals:
 *   - Present a tactical "cipher ops" surface to the user.
 *   - HIDE backend internals: IR versions, scheme IDs (A1/B1/...), decrypt
 *     traces, attempt counts, elapsed-ms, key labels, decryptor source repos.
 *   - SHOW user-relevant data: filename, format, server host/port/protocol,
 *     SNI, payload, status (decoded / locked / unknown).
 *   - Simulated mission telemetry (radar, console log, telemetry strip) for
 *     visual complexity without leaking implementation details.
 */

// ── State ────────────────────────────────────────────────────────────────────
const state = {
  configs: [],
  selectedConfig: null,
  currentView: "targets",
  filter: "all",
  formatFilter: null,     // format id to filter targets by (set from Arsenal); null = all
  archive: [],
  consoleLines: 0,
  sessionStart: Date.now(),
  liveLogSince: 0,        // last seen log id from backend
  liveLogPolling: null,   // interval id for /api/logs polling
};

// Persisted archive (in-memory only; cleared on restart)
const ARCHIVE_KEY = "__injectx_archive__";

// ── Helpers ──────────────────────────────────────────────────────────────────
function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function safeUpper(v) {
  if (v == null) return "UNKNOWN";
  return String(v).toUpperCase();
}
function safeStr(v) { return v == null ? "" : String(v); }
function safeBool(v) { return v === true || v === "true"; }

function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v == null || v === false) continue;
    if (k === "className") e.className = v;
    else if (k === "style") e.setAttribute("style", v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2).toLowerCase(), v);
    else e.setAttribute(k, v);
  }
  for (const c of (Array.isArray(children) ? children : [children])) {
    if (c == null || c === false) continue;
    if (typeof c === "string" || typeof c === "number") e.appendChild(document.createTextNode(String(c)));
    else e.appendChild(c);
  }
  return e;
}

function pad(n, len = 2) { return String(n).padStart(len, "0"); }
function fmtTime(d = new Date()) {
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
function fmtUTC(d = new Date()) {
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`;
}
function shortId(id) {
  if (!id) return "----";
  return id.substring(0, 4).toUpperCase();
}
function genSessionId() {
  return Math.random().toString(16).substring(2, 10).toUpperCase();
}

// ── Format metadata (user-facing; no scheme IDs, no decryptor sources) ───────
// icon: path to the format's app icon (copied to frontend/src/assets/ for
//       CSP-safe same-origin loading). Used on target cards + detail view.
const FORMAT_META = {
  ehi:   { name: "HTTP Injector",  color: "var(--c-ehi)",   short: "EHI",   exts: [".ehi"],   icon: "src/assets/icon-ehi.jpg" },
  hc:    { name: "HTTP Custom",    color: "var(--c-hc)",    short: "HC",    exts: [".hc"],    icon: "src/assets/icon-hc.png" },
  hat:   { name: "HA Tunnel Plus", color: "var(--c-hat)",   short: "HAT",   exts: [".hat", ".ha"], icon: "src/assets/icon-ha.jpg" },
  dark:  { name: "DARK TUNNEL",    color: "var(--c-dark)",  short: "DARK",  exts: [".dark", ".drak", ".dt"], icon: "src/assets/icon-dark.png" },
  tls:   { name: "TLS Tunnel",     color: "var(--c-tls)",   short: "TLS",   exts: [".tls"],   icon: null },
  npv:   { name: "NapsternetV",    color: "var(--c-npv)",   short: "NPV",   exts: [".npv4", ".inpv", ".npv"], icon: "src/assets/icon-npv.png" },
  nsh:   { name: "SocksHTTP",      color: "var(--c-nsh)",   short: "NSH",   exts: [".nsh"],   icon: null },
  vhd:   { name: "V2Ray Tunnel",   color: "var(--c-vhd)",   short: "VHD",   exts: [".vhd"],   icon: null },
  ziv:   { name: "ZIVPN",          color: "var(--c-vhd)",   short: "ZIV",   exts: [".ziv"],   icon: "src/assets/icon-ziv.png" },
  lnk:   { name: "LNK Config",     color: "var(--c-unk)",   short: "LNK",   exts: [".lnk"],   icon: "src/assets/icon-lnk.jpg" },
  ovpn:  { name: "OpenVPN",        color: "var(--c-ovpn)",  short: "OVPN",  exts: [".ovpn"],  icon: null },
  unknown: { name: "Unknown",      color: "var(--c-unk)",   short: "UNK",   exts: [],         icon: null },
};

function formatMeta(fmt) {
  return FORMAT_META[fmt] || FORMAT_META.unknown;
}

/**
 * Create a format icon element. If the format has an app icon, show it
 * as an <img>. Otherwise fall back to the short text badge.
 */
function createFormatIcon(fmt, size = 32) {
  const meta = formatMeta(fmt);
  if (meta.icon) {
    return el("img", {
      src: meta.icon,
      alt: meta.short,
      className: "format-icon-img",
      style: `width: ${size}px; height: ${size}px;`,
      title: meta.name,
      onerror: function () {
        // If the icon fails to load, replace with text badge
        const badge = el("span", {
          className: `format-badge format-${fmt || "unknown"}`,
          style: `--card-accent: ${meta.color}; width: ${size}px; height: ${size}px; display: inline-flex; align-items: center; justify-content: center;`,
        }, [meta.short]);
        this.replaceWith(badge);
      },
    });
  }
  // No icon — use text badge
  return el("span", {
    className: `format-badge format-${fmt || "unknown"}`,
    style: `--card-accent: ${meta.color}; width: ${size}px; height: ${size}px; display: inline-flex; align-items: center; justify-content: center;`,
  }, [meta.short]);
}

// Translate raw decryption_status into a user-facing tri-state
function classifyStatus(config) {
  // not_encrypted -> decoded (plain text, no crypto)
  // success       -> decoded
  // partial       -> decoded (still extractable)
  // no_decryptor  -> locked (proprietary encryption, can't read)
  // failed        -> unknown (tried but failed)
  // unknown/null  -> unknown
  const s = config.decryption_status;
  if (s === "success" || s === "not_encrypted" || s === "partial") return "decoded";
  if (s === "no_decryptor") return "locked";
  if (s === "failed") return "unknown";
  return "unknown";
}

const STATUS_LABEL = {
  decoded: "DECODED",
  locked: "LOCKED",
  unknown: "UNKNOWN",
};

// ═══════════════════════════════════════════════════════════════════════════
//   CONSOLE / ACTIVITY LOG
// ═══════════════════════════════════════════════════════════════════════════

// Small copy-to-clipboard control. `get` is a string or a function → string.
// Uses the async Clipboard API when available (Electron/localhost), with an
// execCommand fallback for plain file:// contexts.
function copyBtn(get, extraClass = "") {
  const b = el("button", { className: "copy-btn " + extraClass, type: "button", title: "Copy" }, ["⧉"]);
  b.addEventListener("click", (e) => {
    e.stopPropagation();
    copyText(String(typeof get === "function" ? get() : get), () => {
      b.classList.add("copied"); b.textContent = "✓";
      setTimeout(() => { b.classList.remove("copied"); b.textContent = "⧉"; }, 1000);
    });
  });
  return b;
}
// Copy text to the clipboard: async Clipboard API where available
// (Electron/localhost), execCommand fallback for plain file:// contexts.
function copyText(text, done) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done || (() => {})).catch(() => fallbackCopy(text, done));
  } else {
    fallbackCopy(text, done);
  }
}
function fallbackCopy(text, done) {
  const ta = document.createElement("textarea");
  ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
  document.body.appendChild(ta); ta.select();
  try { document.execCommand("copy"); if (done) done(); } catch (_) { /* ignore */ }
  ta.remove();
}

function logEvent(tag, msg, type = "info") {
  const body = $("#console-body");
  if (!body) return;

  const line = el("div", { className: "console-line" }, [
    el("span", { className: "cl-time" }, [fmtTime()]),
    el("span", { className: `cl-tag cl-tag-${type}` }, [tag]),
    el("span", { className: "cl-msg" }, [msg]),
    copyBtn(msg, "cl-copy"),
  ]);
  body.appendChild(line);
  body.scrollTop = body.scrollHeight;

  state.consoleLines += 1;
  const counter = $("#console-line-count");
  if (counter) counter.textContent = `${state.consoleLines} EVENTS`;

  // Keep last 200 lines
  while (body.children.length > 200) body.removeChild(body.firstChild);

  // Mirror to archive
  pushArchive(tag, msg, type);
}

function pushArchive(tag, msg, type) {
  state.archive.unshift({ time: new Date().toISOString(), tag, msg, type });
  if (state.archive.length > 100) state.archive.length = 100;
  renderArchive();
}

// ═══════════════════════════════════════════════════════════════════════════
//   LIVE LOG STREAMING (real backend decrypt steps)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Start polling /api/logs every 250ms. New entries from the backend
 * (real decryption steps: "Applying initial XOR layer", "ChaCha20 outer
 * envelope decrypt", "Main block decrypted · 32 fields", etc.) are
 * streamed into the activity console in real time.
 *
 * The polling auto-stops after `maxMs` (default 30s) as a safety net.
 */
function startLiveLogPolling(maxMs = 30000) {
  stopLiveLogPolling();
  const startedAt = Date.now();

  const poll = async () => {
    if (Date.now() - startedAt > maxMs) {
      stopLiveLogPolling();
      return;
    }
    try {
      const result = await API.getLogs(state.liveLogSince);
      if (result && result.entries && result.entries.length > 0) {
        for (const e of result.entries) {
          // Map backend type → console tag type
          let type = "info";
          if (e.type === "warn" || e.type === "error") type = e.type;
          else if (e.tag === "OK") type = "ok";
          else if (e.tag === "ERR") type = "err";
          else if (e.tag === "SYS") type = "sys";
          logEvent(e.tag, e.msg, type);
          state.liveLogSince = Math.max(state.liveLogSince, e.id);
        }
      }
    } catch (err) {
      // Backend might be briefly unreachable during startup — ignore
    }
  };
  // Poll immediately, then every 250ms
  poll();
  state.liveLogPolling = setInterval(poll, 250);
}

function stopLiveLogPolling() {
  if (state.liveLogPolling) {
    clearInterval(state.liveLogPolling);
    state.liveLogPolling = null;
  }
}

function renderArchive() {
  const list = $("#archive-list");
  if (!list) return;
  list.innerHTML = "";

  if (state.archive.length === 0) {
    list.appendChild(el("div", { className: "empty-state" }, [
      el("p", { className: "empty-hint" }, ["No archive entries yet."]),
    ]));
    return;
  }

  for (const entry of state.archive) {
    const d = new Date(entry.time);
    list.appendChild(el("div", { className: "archive-entry" }, [
      el("span", { className: "ae-time" }, [fmtTime(d)]),
      el("span", { className: `ae-tag ${entry.type}` }, [entry.tag]),
      el("span", { className: "ae-msg" }, [entry.msg]),
      copyBtn(`${fmtTime(d)} [${entry.tag}] ${entry.msg}`, "ae-copy"),
    ]));
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   STATUS HEADER (clock, marquee)
// ═══════════════════════════════════════════════════════════════════════════

function startClock() {
  const tick = () => {
    const sh = $("#sh-clock");
    if (sh) sh.textContent = fmtTime();
  };
  tick();
  setInterval(tick, 1000);
}

function setStatusPill(state_, text) {
  const pill = $("#sh-status-pill");
  const txt = $("#sh-status-text");
  if (!pill || !txt) return;
  pill.className = "sh-status-pill";
  if (state_ === "ok") pill.classList.add("ok"); // default styling already ok
  if (state_ === "warn") pill.classList.add("warn");
  if (state_ === "err") pill.classList.add("err");
  txt.textContent = text;
}

// ═══════════════════════════════════════════════════════════════════════════
//   SIDEBAR STATUS (simulated uplink)
// ═══════════════════════════════════════════════════════════════════════════

function setSidebarStatus(connected) {
  const dot = $("#sb-status-dot");
  const text = $("#sb-status-text");
  const nodeId = $("#sb-node-id");
  const uplink = $("#sb-uplink");

  if (!dot || !text) return;

  if (connected) {
    dot.classList.add("connected");
    text.textContent = "LINK · ESTABLISHED";
    if (nodeId) nodeId.textContent = genSessionId();
    if (uplink) {
      const pingMs = (8 + Math.random() * 12).toFixed(0);
      uplink.textContent = `${pingMs}ms`;
      // Drift the uplink value periodically for "live" feel
      setInterval(() => {
        const v = (6 + Math.random() * 18).toFixed(0);
        if (uplink) uplink.textContent = `${v}ms`;
      }, 4000);
    }
  } else {
    dot.classList.remove("connected");
    text.textContent = "LINK · OFFLINE";
    if (nodeId) nodeId.textContent = "----";
    if (uplink) uplink.textContent = "N/A";
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   VIEWS
// ═══════════════════════════════════════════════════════════════════════════

function showView(viewName) {
  state.currentView = viewName;
  $$(".view").forEach((v) => v.classList.remove("active"));
  const target = $(`#view-${viewName}`);
  if (target) target.classList.add("active");
  $$(".sb-nav-item").forEach((item) => item.classList.remove("active"));
  const navItem = $(`.sb-nav-item[data-view="${viewName}"]`);
  if (navItem) navItem.classList.add("active");

  if (viewName === "archive") renderArchive();
  if (viewName === "system") renderSystemView();
  if (viewName === "terminal") {
    const ti = $("#terminal-input");
    if (ti) setTimeout(() => ti.focus(), 60);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   TARGETS VIEW (home)
// ═══════════════════════════════════════════════════════════════════════════

async function loadConfigs() {
  try {
    const result = await API.listConfigs();
    state.configs = result.configs || [];
    renderTargetGrid();
    updateTargetCount();
    updateTelemetryStrip();
  } catch (err) {
    logEvent("ERR", `Failed to load targets: ${err.message}`, "err");
    showToast("Failed to load targets", "error");
  }
}

function updateTargetCount() {
  const badge = $("#target-count");
  if (!badge) return;
  if (state.configs.length > 0) {
    badge.textContent = state.configs.length;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

function renderTargetGrid() {
  const grid = $("#target-grid");
  if (!grid) return;
  grid.innerHTML = "";

  // Apply filters: format (from Arsenal) + status (from pills)
  const filtered = state.configs.filter((c) => {
    if (state.formatFilter && c.format !== state.formatFilter) return false;
    if (state.filter === "all") return true;
    return classifyStatus(c) === state.filter;
  });

  if (state.configs.length === 0) {
    grid.appendChild(renderEmptyState());
    return;
  }

  if (filtered.length === 0) {
    grid.appendChild(el("div", { className: "empty-state" }, [
      el("p", { className: "empty-title" }, ["NO MATCHES"]),
      el("p", { className: "empty-hint" }, [`No targets match filter: ${state.filter.toUpperCase()}`]),
    ]));
    return;
  }

  for (const cfg of filtered) {
    grid.appendChild(renderTargetCard(cfg));
  }
}

function renderEmptyState() {
  return el("div", { className: "empty-state" }, [
    el("div", { className: "empty-radar" }, [
      el("div", { className: "empty-radar-ring r1" }),
      el("div", { className: "empty-radar-ring r2" }),
      el("div", { className: "empty-radar-ring r3" }),
      el("div", { className: "empty-radar-cross" }),
    ]),
    el("p", { className: "empty-title" }, ["NO TARGETS ACQUIRED"]),
    el("p", { className: "empty-hint" }, [
      "Click ", el("strong", {}, ["ACQUIRE TARGET"]),
      " or drag-drop VPN config files into the viewport to begin analysis.",
    ]),
    el("div", { className: "empty-formats" }, [
      ".hc", ".ehi", ".hat", ".tls", ".npv4", ".nsh", ".vhd", ".dark",
    ].map(ext => el("span", { className: "ef-chip" }, [ext]))),
  ]);
}

function renderTargetCard(cfg) {
  const meta = formatMeta(cfg.format);
  const status = classifyStatus(cfg);
  const statusLabel = STATUS_LABEL[status];

  // Pull a few user-relevant preview fields if available
  const preview = cfg.config || {};
  const host = preview.host || preview.ssh_server || preview.proxy_host || "—";
  const port = preview.port || preview.ssh_port || preview.proxy_port || "—";
  const protocol = preview.protocol || "—";

  return el("div", {
    className: "target-card",
    style: `--card-accent: ${meta.color}`,
    onClick: () => showConfigDetail(cfg.id),
  }, [
    el("div", { className: "tc-head" }, [
      el("div", { className: "tc-format-row" }, [
        createFormatIcon(cfg.format, 28),
        el("span", { className: "tc-format" }, [meta.short]),
      ]),
      el("span", { className: `tc-status ${status}` }, [
        el("span", { className: "tc-status-dot" }),
        statusLabel,
      ]),
    ]),
    el("div", { className: "tc-filename" }, [cfg.filename || "unnamed"]),
    el("div", { className: "tc-meta" }, [
      el("div", { className: "tc-meta-item" }, [
        el("span", { className: "tc-meta-label" }, ["HOST"]),
        el("span", { className: "tc-meta-value" }, [String(host)]),
      ]),
      el("div", { className: "tc-meta-item" }, [
        el("span", { className: "tc-meta-label" }, ["PORT"]),
        el("span", { className: "tc-meta-value" }, [String(port)]),
      ]),
      el("div", { className: "tc-meta-item" }, [
        el("span", { className: "tc-meta-label" }, ["PROTO"]),
        el("span", { className: "tc-meta-value" }, [safeUpper(protocol)]),
      ]),
      el("div", { className: "tc-meta-item" }, [
        el("span", { className: "tc-meta-label" }, ["FORMAT"]),
        el("span", { className: "tc-meta-value" }, [meta.name]),
      ]),
    ]),
    el("div", { className: "tc-foot" }, [
      el("span", { className: "tc-id" }, [`TGT_${shortId(cfg.id)}`]),
      el("div", { className: "tc-actions" }, [
        el("button", {
          className: "tc-btn tc-btn-export",
          title: "Export",
          onClick: (e) => { e.stopPropagation(); exportConfig(cfg.id); },
        }, ["↓"]),
        el("button", {
          className: "tc-btn",
          title: "Purge target",
          onClick: (e) => { e.stopPropagation(); deleteConfig(cfg.id); },
        }, ["✕"]),
      ]),
    ]),
  ]);
}

function updateTelemetryStrip() {
  const total = state.configs.length;
  let decoded = 0, locked = 0, unknown = 0;
  const byFormat = {};

  for (const c of state.configs) {
    const s = classifyStatus(c);
    if (s === "decoded") decoded++;
    else if (s === "locked") locked++;
    else unknown++;
    const key = c.format || "unknown";
    byFormat[key] = (byFormat[key] || 0) + 1;
  }

  const setVal = (id, v) => { const e = $(id); if (e) e.textContent = String(v); };
  const setBar = (id, v, max) => {
    const e = $(id); if (!e) return;
    e.style.width = (max > 0 ? (v / max) * 100 : 0) + "%";
  };

  setVal("#ts-total", total);
  setVal("#ts-decoded", decoded);
  setVal("#ts-locked", locked);
  setVal("#ts-unknown", unknown);

  setBar("#ts-bar-total", total, Math.max(total, 1));
  setBar("#ts-bar-decoded", decoded, Math.max(total, 1));
  setBar("#ts-bar-locked", locked, Math.max(total, 1));
  setBar("#ts-bar-unknown", unknown, Math.max(total, 1));

  // Format breakdown chips
  const fmtContainer = $("#ts-formats");
  if (fmtContainer) {
    fmtContainer.innerHTML = "";
    const entries = Object.entries(byFormat).sort((a, b) => b[1] - a[1]);
    if (entries.length === 0) {
      fmtContainer.appendChild(el("span", { className: "ef-chip" }, ["— none —"]));
    } else {
      for (const [fmt, count] of entries) {
        const m = formatMeta(fmt);
        fmtContainer.appendChild(el("span", { className: "ts-format-chip" }, [
          el("span", { className: "ffc-dot", style: `background:${m.color}` }),
          m.short,
          el("span", { className: "ffc-count" }, [String(count)]),
        ]));
      }
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   TARGET DETAIL VIEW
// ═══════════════════════════════════════════════════════════════════════════

async function showConfigDetail(configId) {
  logEvent("SCAN", `Opening target TGT_${shortId(configId)} for inspection...`, "info");

  try {
    const result = await API.getConfig(configId);
    if (result.error) {
      logEvent("ERR", result.error, "err");
      showToast(result.error, "error");
      return;
    }
    state.selectedConfig = result;
    renderConfigDetail(result);
    showView("target-detail");

    // Log the outcome with REAL field count from the backend
    const status = classifyStatus(result);
    const fieldCount = result.config ? Object.keys(result.config).length : 0;
    if (status === "decoded") {
      logEvent("OK", `Target decoded · ${fieldCount} fields extracted`, "ok");
    } else if (status === "locked") {
      logEvent("LOCK", `Target locked · proprietary encryption, no decryptor`, "warn");
    } else {
      logEvent("FAIL", `Target resisted decryption · envelope unbroken`, "err");
    }
  } catch (err) {
    logEvent("ERR", `Failed to load target: ${err.message}`, "err");
    showToast("Failed to load target", "error");
  }
}

function renderConfigDetail(config) {
  const container = $("#target-detail-content");
  if (!container) return;
  container.innerHTML = "";

  const meta = formatMeta(config.format);
  const status = classifyStatus(config);
  const statusLabel = STATUS_LABEL[status];
  const d = config.config || {};

  // ── Header ─────────────────────────────────────────────────────────────
  container.appendChild(el("div", { className: "detail-header" }, [
    el("div", { className: "detail-title-block" }, [
      el("div", { className: "detail-format-row" }, [
        createFormatIcon(config.format, 40),
        el("span", {
          className: "detail-format-badge",
          style: `--card-accent: ${meta.color}; color: ${meta.color}`,
        }, [meta.short]),
        el("span", { className: `detail-status-badge ${status}` }, [
          el("span", { className: "dsb-dot" }),
          statusLabel,
        ]),
      ]),
      el("h2", { className: "detail-filename" }, [config.filename || "unnamed"]),
      el("div", { className: "detail-meta-line" }, [
        el("span", {}, ["TARGET_ID: ", el("strong", {}, [`TGT_${shortId(config.id)}`])]),
        el("span", {}, ["FORMAT: ", el("strong", {}, [meta.name])]),
        el("span", {}, ["ACQUIRED: ", el("strong", {}, [new Date().toLocaleTimeString()])]),
      ]),
    ]),
    el("button", {
      className: "detail-back",
      onClick: () => { showView("targets"); state.selectedConfig = null; },
    }, ["◀ BACK"]),
  ]));

  // ── Status strip (compact) ─────────────────────────────────────────────
  const STATUS_STRIP = {
    decoded: { cls: "ok",   label: "DECODED",  msg: "Payload extracted — sensitive values masked, click to reveal." },
    locked:  { cls: "warn", label: "LOCKED",   msg: "Credentials sealed by the config author. Metadata only." },
    unknown: { cls: "err",  label: "NO OUTPUT", msg: "Decryption failed — newer variant or missing key." },
  };
  const ss = STATUS_STRIP[status] || STATUS_STRIP.unknown;
  container.appendChild(el("div", { className: `detail-status-strip ${ss.cls}` }, [
    el("span", { className: "dss-label" }, [ss.label]),
    el("span", { className: "dss-msg" }, [ss.msg]),
  ]));

  // ── Errors ─────────────────────────────────────────────────────────────
  if (config.errors && config.errors.length > 0) {
    container.appendChild(el("div", { className: "detail-panel err" }, [
      el("div", { className: "dp-title" }, ["ERRORS"]),
      ...config.errors.map((e) => el("p", { className: "dp-msg" }, [e])),
    ]));
  }

  // ── Config data ────────────────────────────────────────────────────────
  if (d && Object.keys(d).length > 0) {
    renderConfigData(container, d);
  } else if (status !== "decoded") {
    container.appendChild(el("div", { className: "detail-section" }, [
      el("div", { className: "detail-section-head" }, [
        el("span", { className: "detail-section-title" }, ["NO EXTRACTABLE DATA"]),
      ]),
      el("div", { className: "detail-section-body" }, [
        el("p", { className: "dp-msg" }, ["No payload was extracted from this target."]),
      ]),
    ]));
  }

  // ── Actions ────────────────────────────────────────────────────────────
  container.appendChild(el("div", { className: "detail-actions" }, [
    el("button", {
      className: "action-btn primary",
      onClick: () => exportConfig(config.id),
    }, ["↓ EXPORT JSON"]),
    el("button", {
      className: "action-btn",
      onClick: () => { deleteConfig(config.id); },
    }, ["✕ PURGE TARGET"]),
  ]));
}

// Build a full-width section shell (header + body) for wide blocks.
function wideSection(title, hint, bodyChildren) {
  const head = [el("span", { className: "detail-section-title" }, [title])];
  if (hint) head.push(el("span", { className: "detail-section-hint" }, [hint]));
  return el("div", { className: "detail-section span-all" }, [
    el("div", { className: "detail-section-head" }, head),
    el("div", { className: "detail-section-body" }, bodyChildren),
  ]);
}

// Primary decoded values as big, scannable tiles at the top of the output.
function renderHeroStrip(container, d) {
  const af = (d.raw_data && d.raw_data._all_fields) || {};
  const host  = d.host || d.ssh_server || d.proxy_host || af.udpserver || null;
  const port  = d.port || d.ssh_port || d.proxy_port || null;
  const proto = d.protocol || null;
  const sni   = d.sni || af.sniHostname || null;

  const tiles = [];
  if (host)  tiles.push({ label: "Server / Host", value: String(host), accent: true, mono: true });
  if (port)  tiles.push({ label: "Port", value: String(port), mono: true });
  if (proto) tiles.push({ label: "Protocol", value: String(proto).toUpperCase() });
  if (sni)   tiles.push({ label: "SNI", value: String(sni), mono: true });
  if (d.ssh_user) tiles.push({ label: "Username", value: String(d.ssh_user), mono: true });
  if (tiles.length === 0) return;

  container.appendChild(el("div", { className: "hero-strip" },
    tiles.map((t) => el("div", { className: "hero-tile" + (t.accent ? " accent" : "") }, [
      el("div", { className: "ht-head" }, [
        el("div", { className: "ht-label" }, [t.label]),
        copyBtn(t.value, "ht-copy"),
      ]),
      el("div", { className: "ht-value" + (t.mono ? " mono" : "") }, [t.value]),
    ]))
  ));
}

function renderConfigData(container, d) {
  // Hero tiles first (outside the grid, full width).
  renderHeroStrip(container, d);

  // Everything else flows into a responsive grid: narrow field cards sit
  // side-by-side to use the width; wide blocks (payload, notes, all fields)
  // span the full row.
  const grid = el("div", { className: "detail-grid" });

  // ── Narrow cards ───────────────────────────────────────────────────────
  renderKVSection(grid, "CONNECTION", [
    { key: "host",          label: "Server Host" },
    { key: "port",          label: "Server Port" },
    { key: "protocol",      label: "Protocol" },
    { key: "sni",           label: "SNI" },
    { key: "bug_host",      label: "Bug Host" },
    { key: "connection_type", label: "Connection Type" },
    { key: "tunnel_type",   label: "Tunnel Type" },
    { key: "tunnel_mode",   label: "Tunnel Mode" },
    { key: "inject_type",   label: "Injection Method" },
    { key: "ssl_enabled",   label: "SSL" },
  ], d);

  renderKVSection(grid, "SSH CREDENTIALS", [
    { key: "ssh_server", label: "SSH Server" },
    { key: "ssh_port",   label: "SSH Port" },
    { key: "ssh_user",   label: "Username" },
    { key: "ssh_pass",   label: "Password", secret: true },
  ], d);

  renderKVSection(grid, "PROXY", [
    { key: "proxy_host", label: "Proxy Host" },
    { key: "proxy_port", label: "Proxy Port" },
  ], d);

  renderKVSection(grid, "DNS", [
    { key: "dns",        label: "DNS Server" },
    { key: "remote_dns", label: "Remote DNS" },
  ], d);

  // Protections (HC v2.7+ hwid/area/password locks) — top level or raw_data.
  const protections = d.protections || (d.raw_data && d.raw_data.protections);
  if (protections && Object.keys(protections).length > 0) {
    renderKVSection(grid, "PROTECTIONS", Object.entries(protections).map(([k, v]) => ({
      key: k, label: k.toUpperCase(), value: v,
    })), protections);
  }

  // ── Wide blocks (span full width) ──────────────────────────────────────
  // HTTP payload with [crlf]/[split] syntax highlighting.
  if (d.payload) {
    const preEl = el("pre", { className: "payload-block payload-highlighted" });
    preEl.innerHTML = highlightPayload(String(d.payload));
    grid.appendChild(wideSection(
      "HTTP PAYLOAD",
      "[crlf]=\\r\\n  ·  [split]=request separator  ·  [proxy]=injected host  ·  [ua]=user-agent",
      [preEl],
    ));
  }

  // Notes — HTML from the config author (HC `notes`, HTTP Injector
  // `configMessage`, ZIVPN `file.msg`), rendered in a sandboxed iframe.
  const af = (d.raw_data && d.raw_data._all_fields) || {};
  const notes = d.notes || af.notes || af.configMessage || af["file.msg"]
              || (d.raw_data && d.raw_data.notes);
  if (notes && typeof notes === "string" && notes.trim()) {
    grid.appendChild(wideSection("NOTES", "rendered as-is from the config author",
      [renderNotesSandboxed(notes)]));
  }

  // Every field the decoder extracted (raw_data._all_fields).
  renderExtractedFields(grid, d);

  // Custom headers.
  if (d.custom_headers && Object.keys(d.custom_headers).length > 0) {
    grid.appendChild(wideSection("CUSTOM HEADERS", null,
      [el("pre", { className: "payload-block" }, [JSON.stringify(d.custom_headers, null, 2)])]));
  }

  // Protocol-specific config blocks.
  const protoBlocks = [
    { key: "v2ray",       label: "V2RAY CONFIG" },
    { key: "vmess_config", label: "VMESS CONFIG" },
    { key: "vless_config", label: "VLESS CONFIG" },
    { key: "websocket",   label: "WEBSOCKET CONFIG" },
    { key: "xray",        label: "XRAY CONFIG" },
    { key: "hysteria",    label: "HYSTERIA CONFIG" },
    { key: "shadowsocks", label: "SHADOWSOCKS CONFIG" },
    { key: "wireguard",   label: "WIREGUARD CONFIG" },
    { key: "openvpn_config", label: "OPENVPN CONFIG" },
  ];
  for (const { key, label } of protoBlocks) {
    const v = d[key];
    if (v && typeof v === "object" && Object.keys(v).length > 0) {
      grid.appendChild(wideSection(label, null,
        [el("pre", { className: "payload-block" }, [JSON.stringify(v, null, 2)])]));
    } else if (v && typeof v === "string" && v.trim()) {
      grid.appendChild(wideSection(label, null,
        [el("pre", { className: "payload-block" }, [String(v)])]));
    }
  }

  // Raw JSON (collapsible).
  const rawToggle = el("button", { className: "action-btn" }, ["{} TOGGLE RAW JSON"]);
  const rawBlock = el("pre", { className: "payload-block hidden", style: "margin-top: 8px;" }, [JSON.stringify(d, null, 2)]);
  rawToggle.addEventListener("click", () => rawBlock.classList.toggle("hidden"));
  grid.appendChild(el("div", { className: "detail-section span-all" }, [
    el("div", { className: "detail-section-head" }, [
      el("span", { className: "detail-section-title" }, ["RAW JSON"]),
      rawToggle,
    ]),
    rawBlock,
  ]));

  container.appendChild(grid);
}

/**
 * Highlight HC payload syntax: [crlf], [crlf][crlf], [split], [proxy], [ua],
 * HTTP methods (GET/POST/CONNECT/...), and HTTP version (HTTP/1.1).
 *
 * [crlf] markers are converted to actual line breaks (with a visual ↵ badge)
 * so the payload reads like a real HTTP request instead of one long line.
 * [split] markers get a full-width separator line.
 *
 * Returns an HTML string safe to assign to a pre.innerHTML.
 */
function highlightPayload(payload) {
  // 1. HTML-escape everything
  const esc = (s) => s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  let html = esc(payload);

  // 2. Convert [crlf] → line break with visual marker
  //    [crlf][crlf] (double) → blank line between requests
  html = html.replace(
    /\[crlf\]\[crlf\]/gi,
    '<span class="pl-mark pl-mark-crlf">↵↵</span>\n\n'
  );
  html = html.replace(
    /\[crlf\]/gi,
    '<span class="pl-mark pl-mark-crlf">↵</span>\n'
  );

  // 3. Convert [split] → full-width separator
  html = html.replace(
    /\[split\]/gi,
    '\n<span class="pl-mark pl-mark-split">──── SPLIT ────</span>\n'
  );

  // 4. Highlight remaining markers: [proxy], [ua], [host], etc.
  html = html.replace(
    /\[(proxy|ua|host|raw|method|proto)\]/gi,
    '<span class="pl-mark pl-mark-$1">$&</span>'
  );

  // 5. Highlight HTTP methods at line start
  html = html.replace(
    /^(GET|POST|PUT|CONNECT|HEAD|OPTIONS|PATCH|UNLOCK|PROPFIND|REPORT) /gm,
    '<span class="pl-method">$1</span> '
  );

  // 6. Highlight HTTP version
  html = html.replace(
    /(HTTP\/[0-9.]+)/g,
    '<span class="pl-version">$1</span>'
  );

  // 7. Highlight "Host: ..." lines
  html = html.replace(
    /^(Host: .+)$/gm,
    '<span class="pl-host">$1</span>'
  );

  return html;
}

/**
 * Render HC v2.7 notes (raw HTML from an untrusted config author) in an
 * iframe. The notes HTML is config-author content (colored fonts, h1,
 * spans) — we want it to display as-is.
 *
 * SECURITY: a srcdoc iframe is NOT origin-isolated on its own — it inherits
 * the embedder's origin (file://) AND its Content-Security-Policy. What
 * actually stops a malicious notes payload from running script or
 * exfiltrating the decrypted config is the parent CSP in index.html
 * (`script-src 'self'` with no 'unsafe-inline' blocks inline <script> and
 * onerror= handlers; `img-src`/`connect-src` restrict network to loopback),
 * which the srcdoc frame inherits. A `sandbox="allow-same-origin"` attribute
 * (scripts disabled, same-origin kept for the auto-resize read below) would
 * add belt-and-suspenders isolation — see backlog N8; it needs a run in the
 * real Electron app to confirm it doesn't regress rendering before shipping.
 */
function renderNotesSandboxed(html) {
  const wrapper = el("div", { className: "notes-sandbox-wrap" });
  const iframe = document.createElement("iframe");
  iframe.className = "notes-sandbox";
  // No sandbox attr for now — see the SECURITY note above (N8).
  // Adding sandbox="allow-same-origin" was reported to prevent the content from
  // rendering in some browsers.
  const doc = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
    body { background: #070a0c; color: #d4f1e4; font-family: monospace; padding: 12px; margin: 0; font-size: 11px; line-height: 1.5; }
    h1, h2, h3 { color: #d4f1e4; }
    font { display: inline; }
  </style></head><body>${html}</body></html>`;
  iframe.setAttribute("srcdoc", doc);
  // Auto-resize the iframe to fit its content once loaded
  iframe.addEventListener("load", () => {
    try {
      const h = iframe.contentDocument
        ? iframe.contentDocument.body.scrollHeight
        : 0;
      if (h > 0) iframe.style.height = (h + 24) + "px";
    } catch (e) { /* cross-origin — leave default height */ }
  });
  wrapper.appendChild(iframe);
  return wrapper;
}

// Turn a raw config key (camelCase / snake_case / dotted) into a readable
// label: "overwriteServerData" -> "Overwrite Server Data", "file.msg" -> "File Msg".
function prettifyKey(k) {
  return String(k)
    .replace(/^_+/, "")
    .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
    .replace(/[_.]+/g, " ")
    .trim()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function looksLikeHtml(v) {
  return typeof v === "string" && /<\/?[a-z][\s\S]*>/i.test(v);
}

// Render EVERY field the decoder extracted (raw_data._all_fields) as a clean
// key/value table. This is the fix for "the decoded page is empty, I have to
// export JSON": the structured sections only show mapped IR fields, but the
// full decoded config lives here. Scalars render inline, nested objects as
// pretty JSON, and HTML-ish values are skipped (they render in NOTES).
function renderExtractedFields(container, d) {
  const all = d.raw_data && d.raw_data._all_fields;
  if (!all || typeof all !== "object" || Array.isArray(all)) return;

  const rows = [];
  for (const [k, v] of Object.entries(all)) {
    if (v === null || v === undefined || v === "") continue;
    if (looksLikeHtml(v)) continue; // shown in the NOTES section instead
    let valEl, copyText;
    if (v && typeof v === "object") {
      copyText = JSON.stringify(v, null, 2);
      valEl = el("pre", { className: "kv-val kv-json" }, [copyText]);
    } else if (typeof v === "boolean" || typeof v === "number") {
      copyText = String(v);
      valEl = el("span", { className: "kv-val mono" }, [copyText]);
    } else {
      copyText = String(v);
      valEl = el("span", { className: "kv-val" }, [copyText]);
    }
    rows.push(el("div", { className: "kv-row" }, [
      el("div", { className: "kv-key" }, [prettifyKey(k)]),
      kvCell(valEl, copyText),
    ]));
  }
  if (rows.length === 0) return;

  container.appendChild(el("div", { className: "detail-section span-all" }, [
    el("div", { className: "detail-section-head" }, [
      el("span", { className: "detail-section-title" }, ["DECODED FIELDS"]),
      el("span", { className: "detail-section-hint" }, [`${rows.length} fields extracted`]),
    ]),
    el("div", { className: "detail-section-body", style: "padding: 0;" }, [
      el("div", { className: "kv-table kv-table-wide" }, rows),
    ]),
  ]));
}

// Wrap a value element in a grid cell that carries a copy button. Keeps the
// value's own color classes (mono/secret/kv-json) but moves cell padding to
// the wrapper so the copy button can sit at the right edge.
function kvCell(valEl, copyText) {
  return el("div", { className: "kv-val-cell" }, [valEl, copyBtn(copyText, "kv-copy")]);
}

function renderKVSection(container, title, fields, d) {
  const rows = [];
  for (const f of fields) {
    const v = d[f.key];
    if (v === null || v === undefined || v === "") continue;
    let valEl;
    if (f.secret) {
      valEl = el("span", { className: "kv-val secret", title: "Hover to blur · click to reveal" }, [String(v)]);
      valEl.addEventListener("click", () => {
        valEl.classList.toggle("revealed");
        valEl.style.filter = valEl.classList.contains("revealed") ? "blur(0)" : "blur(4px)";
      });
      // Default blurred
      valEl.style.filter = "blur(4px)";
    } else if (typeof v === "boolean") {
      valEl = el("span", { className: "kv-val mono" }, [v ? "true" : "false"]);
    } else if (typeof v === "number") {
      valEl = el("span", { className: "kv-val mono" }, [String(v)]);
    } else {
      valEl = el("span", { className: "kv-val" }, [String(v)]);
    }
    rows.push(el("div", { className: "kv-row" }, [
      el("div", { className: "kv-key" }, [f.label]),
      kvCell(valEl, String(v)),
    ]));
  }

  if (rows.length === 0) return;

  container.appendChild(el("div", { className: "detail-section" }, [
    el("div", { className: "detail-section-head" }, [
      el("span", { className: "detail-section-title" }, [title]),
    ]),
    el("div", { className: "detail-section-body", style: "padding: 0;" }, [
      el("div", { className: "kv-table" }, rows),
    ]),
  ]));
}

// ═══════════════════════════════════════════════════════════════════════════
//   ARSENAL VIEW (formats — minus scheme IDs / decryptor sources)
// ═══════════════════════════════════════════════════════════════════════════

// Per-format capability intel. Status reflects the real state of each
// decryptor (see .context reviews): operational = decodes today; partial =
// envelope only; needs-key = correct algorithm, key rotated; untested =
// implemented but no sample verified; no-decryptor / plain as named.
const ARSENAL = [
  { id: "hc",   scheme: "A5", status: "operational",  note: "HTTP Custom v2.7+ — ChaCha20 multi-layer + per-field decode. Fully decoding." },
  { id: "ehi",  scheme: "B2", status: "operational",  note: "HTTP Injector v6.3+ — Argon2id + ChaCha20-Poly1305 (needs argon2-cffi installed)." },
  { id: "ziv",  scheme: "H1", status: "operational",  note: "ZIVPN — PBKDF2-SHA256 + AES-GCM. Current v2.1.5 password recovered." },
  { id: "dark", scheme: "I1", status: "partial",      note: "DARK Tunnel — darktunnel:// base64(JSON) envelope decoded; author-locked configs keep credentials sealed." },
  { id: "tls",  scheme: "F1", status: "needs-key",    note: "TLS Tunnel — AES-256-GCM. Key rotated in newer (DexProtector) builds; supply one via a keyfile." },
  { id: "hat",  scheme: "E1", status: "untested",     note: "HA Tunnel Plus — AES-128-ECB. Implemented; no sample verified yet." },
  { id: "npv",  scheme: "C1", status: "untested",     note: "NapsternetV — charCode-subtraction cipher. Implemented; no sample verified yet." },
  { id: "nsh",  scheme: "D1", status: "untested",     note: "SocksHTTP — AES-128-GCM + PBKDF2. Implemented; no sample verified yet." },
  { id: "vhd",  scheme: "G1", status: "untested",     note: "V2Ray / Xray VHD — AES-128-CBC. Implemented; no sample verified yet." },
  { id: "lnk",  scheme: "—",  status: "no-decryptor", note: "Unknown / renamed config format. No decryptor available." },
  { id: "ovpn", scheme: "—",  status: "plain",        note: "OpenVPN plaintext. No encryption envelope; parsed directly." },
];
const ARSENAL_STATUS = {
  operational:    { label: "OPERATIONAL",  cls: "ok" },
  partial:        { label: "PARTIAL",      cls: "warn" },
  "needs-key":    { label: "NEEDS KEY",    cls: "warn" },
  untested:       { label: "UNTESTED",     cls: "info" },
  "no-decryptor": { label: "NO DECRYPTOR", cls: "danger" },
  plain:          { label: "PLAIN",        cls: "info" },
};

function arsStat(val, label) {
  return el("div", { className: "ars-stat" }, [
    el("div", { className: "ars-stat-val" }, [val]),
    el("div", { className: "ars-stat-label" }, [label]),
  ]);
}

function openTargetsFiltered(fmtId) {
  showView("targets");
  state.formatFilter = fmtId;
  state.filter = "all";
  $$(".filter-pill").forEach((p) => p.classList.toggle("active", p.dataset.filter === "all"));
  renderTargetGrid();
  showToast(`Showing ${formatMeta(fmtId).short} targets`, "info");
}

function renderArsenalView() {
  const grid = $("#arsenal-grid");
  if (!grid) return;
  grid.innerHTML = "";

  // Live counts from the loaded targets.
  const loaded = {}, decoded = {};
  for (const c of state.configs) {
    loaded[c.format] = (loaded[c.format] || 0) + 1;
    if (classifyStatus(c) === "decoded") decoded[c.format] = (decoded[c.format] || 0) + 1;
  }
  const opCount = ARSENAL.filter((f) => f.status === "operational").length;
  const decodedTotal = state.configs.filter((c) => classifyStatus(c) === "decoded").length;

  // Summary strip.
  grid.appendChild(el("div", { className: "arsenal-summary" }, [
    arsStat(String(ARSENAL.length), "FORMATS"),
    arsStat(String(opCount), "OPERATIONAL"),
    arsStat(String(state.configs.length), "TARGETS LOADED"),
    arsStat(String(decodedTotal), "DECODED"),
  ]));

  // Format cards.
  const cards = el("div", { className: "arsenal-cards" });
  for (const fmt of ARSENAL) {
    const meta = formatMeta(fmt.id);
    const st = ARSENAL_STATUS[fmt.status];
    const n = loaded[fmt.id] || 0, m = decoded[fmt.id] || 0;

    const card = el("div", { className: "arsenal-card", style: `--card-accent: ${meta.color}` }, [
      el("div", { className: "ac-head" }, [
        el("div", { className: "ac-head-left" }, [
          createFormatIcon(fmt.id, 32),
          el("div", { className: "ac-title" }, [
            el("span", { className: "ac-name", style: `color: ${meta.color}` }, [meta.name]),
            el("span", { className: "ac-ext" }, [meta.exts.join(" / ")]),
          ]),
        ]),
        el("span", { className: `ac-status ${st.cls}` }, [st.label]),
      ]),
      el("p", { className: "ac-desc" }, [fmt.note]),
      el("div", { className: "ac-foot" }, [
        el("span", { className: "ac-scheme" }, ["SCHEME ", el("strong", {}, [fmt.scheme])]),
        el("span", { className: "ac-counts" + (n ? " live" : "") }, [`LOADED ${n} · DECODED ${m}`]),
      ]),
    ]);

    if (n > 0) {
      card.classList.add("clickable");
      card.title = `Show ${n} ${meta.short} target(s)`;
      card.addEventListener("click", () => openTargetsFiltered(fmt.id));
    }
    cards.appendChild(card);
  }
  grid.appendChild(cards);
}

// ═══════════════════════════════════════════════════════════════════════════
//   SYSTEM VIEW
// ═══════════════════════════════════════════════════════════════════════════

function renderSystemView() {
  // Status rows
  const statusRows = $("#sys-rows-status");
  if (statusRows) {
    statusRows.innerHTML = "";
    const uptimeMs = Date.now() - state.sessionStart;
    const uptimeMin = Math.floor(uptimeMs / 60000);
    const uptimeSec = Math.floor((uptimeMs % 60000) / 1000);

    const rows = [
      ["State",        "OPERATIONAL", "ok"],
      ["Session ID",   genSessionId(), "mono"],
      ["Uptime",       `${uptimeMin}m ${uptimeSec}s`, ""],
      ["Channel",      "LOCAL · 127.0.0.1", "mono"],
      ["Threat Level", "NOMINAL", "ok"],
    ];
    for (const [k, v, cls] of rows) {
      statusRows.appendChild(el("div", { className: "sys-row" }, [
        el("span", { className: "sys-row-key" }, [k]),
        el("span", { className: `sys-row-val ${cls}` }, [v]),
      ]));
    }
  }

  // Stats rows
  const statsRows = $("#sys-rows-stats");
  if (statsRows) {
    statsRows.innerHTML = "";
    const decoded = state.configs.filter(c => classifyStatus(c) === "decoded").length;
    const locked = state.configs.filter(c => classifyStatus(c) === "locked").length;
    const unknown = state.configs.filter(c => classifyStatus(c) === "unknown").length;
    const successRate = state.configs.length > 0
      ? Math.round((decoded / state.configs.length) * 100)
      : 0;

    const rows = [
      ["Targets Acquired",  String(state.configs.length), ""],
      ["Decoded",           String(decoded), "ok"],
      ["Locked",            String(locked), "warn"],
      ["Unknown",           String(unknown), "err"],
      ["Success Rate",      `${successRate}%`, decoded > 0 ? "ok" : ""],
      ["Archive Events",    String(state.archive.length), ""],
    ];
    for (const [k, v, cls] of rows) {
      statsRows.appendChild(el("div", { className: "sys-row" }, [
        el("span", { className: "sys-row-key" }, [k]),
        el("span", { className: `sys-row-val ${cls}` }, [v]),
      ]));
    }
  }

  // About rows
  const aboutRows = $("#sys-rows-about");
  if (aboutRows) {
    aboutRows.innerHTML = "";
    const rows = [
      ["Codename",    "CIPHER_OPS"],
      ["Build",       "v0.5.0"],
      ["Modules",     "Targets · Arsenal · Archive · System"],
      ["Formats",     "EHI · HC · HAT · DARK · TLS · NPV · NSH · VHD · OVPN"],
      ["Engine",      "Local-only · no telemetry"],
    ];
    for (const [k, v] of rows) {
      aboutRows.appendChild(el("div", { className: "sys-row" }, [
        el("span", { className: "sys-row-key" }, [k]),
        el("span", { className: "sys-row-val" }, [v]),
      ]));
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   FILE OPERATIONS
// ═══════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════
//   ASSETS IMPORT — batch import from assets/configs/{format}/
// ═══════════════════════════════════════════════════════════════════════════

async function refreshAssetsCount() {
  const badge = $("#assets-count-badge");
  if (!badge) return;
  try {
    const result = await API.listAssets();
    if (result && typeof result.total === "number") {
      badge.textContent = String(result.total);
      badge.classList.toggle("empty", result.total === 0);
    }
  } catch (e) {
    // Backend may briefly be unreachable during init — ignore
  }
}

async function importAssets() {
  const btn = $("#btn-import-assets");
  if (!btn) return;

  // Check what's available first
  let list;
  try {
    list = await API.listAssets();
  } catch (e) {
    showToast("Failed to query assets", "error");
    logEvent("ERR", `Assets query failed: ${e.message}`, "err");
    return;
  }
  if (!list || !list.total) {
    showToast("No files in assets/configs/", "info");
    logEvent("INFO", "No files found in assets/configs/ — drop files into assets/configs/{format}/ and try again", "info");
    return;
  }

  logEvent("CMD", `Batch importing ${list.total} file(s) from assets/configs/...`, "info");
  btn.classList.add("importing");

  // Start live-log polling so the user sees each import as it happens
  startLiveLogPolling(60000);

  try {
    const result = await API.importAssets();
    stopLiveLogPolling();
    // Drain final entries
    try {
      const tail = await API.getLogs(state.liveLogSince);
      if (tail && tail.entries) {
        for (const e of tail.entries) {
          const type = (e.tag === "OK") ? "ok" : (e.tag === "ERR") ? "err" : (e.tag === "SKIP") ? "warn" : "info";
          logEvent(e.tag, e.msg, type);
          state.liveLogSince = Math.max(state.liveLogSince, e.id);
        }
      }
    } catch (e) { /* ignore */ }

    if (result && result.error) {
      logEvent("ERR", `Batch import failed: ${result.error}`, "err");
      showToast("Import failed", "error");
    } else {
      const n = result?.imported ?? 0;
      logEvent("OK", `Batch import complete · ${n} config(s) imported`, "ok");
      showToast(`Imported ${n} config(s) from assets/`, "success");
      await loadConfigs();
    }
  } catch (err) {
    stopLiveLogPolling();
    logEvent("ERR", `Batch import failed: ${err.message}`, "err");
    showToast("Import failed", "error");
  } finally {
    btn.classList.remove("importing");
    await refreshAssetsCount();
  }
}

async function openConfig() {
  try {
    logEvent("CMD", "Opening file picker...", "info");
    const filePaths = await API.openFileDialog();
    if (filePaths.length === 0) {
      logEvent("INFO", "File picker canceled", "info");
      return;
    }

    // Start live log polling BEFORE we kick off decryption, so the user
    // sees real-time decrypt steps as they happen on the backend.
    startLiveLogPolling(30000);

    for (const filePath of filePaths) {
      const fname = filePath.split(/[\\/]/).pop();
      logEvent("ACQUIRE", `Importing target: ${fname}`, "info");
      const result = await API.parseConfig(filePath);
      if (result.error) {
        logEvent("ERR", `Failed to import ${fname}: ${result.error}`, "err");
        showToast(`Failed: ${fname}`, "error");
      } else {
        const status = classifyStatus(result);
        const meta = formatMeta(result.format);
        const fields = result.config ? Object.keys(result.config).length : 0;
        logEvent("OK", `Target acquired · ${meta.short} · ${fname} · ${STATUS_LABEL[status]} · ${fields} fields`, "ok");
        showToast(`Acquired: ${fname} (${meta.short})`, "success");
      }
    }
    stopLiveLogPolling();
    // Drain any final log entries that arrived after parseConfig returned
    try {
      const tail = await API.getLogs(state.liveLogSince);
      if (tail && tail.entries) {
        for (const e of tail.entries) {
          const type = (e.tag === "OK") ? "ok" : (e.tag === "ERR") ? "err" : "info";
          logEvent(e.tag, e.msg, type);
          state.liveLogSince = Math.max(state.liveLogSince, e.id);
        }
      }
    } catch (e) { /* ignore */ }

    await loadConfigs();
  } catch (err) {
    logEvent("ERR", `Acquire failed: ${err.message}`, "err");
    showToast("Failed to acquire target", "error");
    stopLiveLogPolling();
  }
}

async function deleteConfig(configId) {
  try {
    await API.deleteConfig(configId);
    logEvent("PURGE", `Target TGT_${shortId(configId)} purged`, "warn");
    showToast("Target purged", "warn");
    if (state.selectedConfig && state.selectedConfig.id === configId) {
      state.selectedConfig = null;
      showView("targets");
    }
    await loadConfigs();
  } catch (err) {
    logEvent("ERR", `Purge failed: ${err.message}`, "err");
    showToast("Failed to purge", "error");
  }
}

async function exportConfig(configId) {
  try {
    logEvent("CMD", `Exporting target TGT_${shortId(configId)}...`, "info");
    const result = await API.exportConfig(configId);
    if (result.error) {
      logEvent("ERR", result.error, "err");
      showToast(result.error, "error");
      return;
    }
    const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `injectx-${configId}.json`;
    a.click();
    URL.revokeObjectURL(url);
    logEvent("OK", `Export complete · injectx-${configId}.json`, "ok");
    showToast("Export complete", "success");
  } catch (err) {
    logEvent("ERR", `Export failed: ${err.message}`, "err");
    showToast("Export failed", "error");
  }
}

// Import every config file inside a folder (IDE-style "open project folder").
// `quiet` skips toasts (used for the silent reopen-last-folder on startup).
async function importFolder(folder, quiet = false) {
  if (!folder || !API.listConfigFiles) return 0;
  const res = await API.listConfigFiles(folder);
  if (res && res.error) { logEvent("ERR", `Folder read failed: ${res.error}`, "err"); return 0; }
  const files = (res && res.files) || [];
  if (!files.length) {
    if (!quiet) { logEvent("SYS", `No config files in ${folder}`, "sys"); showToast("No configs in that folder", "info"); }
    return 0;
  }
  logEvent("ACQUIRE", `Importing ${files.length} config(s) from folder`, "info");
  let ok = 0;
  for (const f of files) {
    const r = await API.parseConfig(f);
    if (r && !r.error) ok++;
  }
  if (API.setLastFolder) await API.setLastFolder(folder);
  await loadConfigs();
  logEvent("OK", `Loaded ${ok}/${files.length} from ${folder.split(/[\\/]/).pop()}`, "ok");
  if (!quiet) showToast(`Loaded ${ok} config(s) from folder`, "success");
  return ok;
}

// Open the native folder picker and import the chosen folder.
async function openFolder() {
  if (!API.openFolderDialog) { showToast("Folder picker needs the desktop app", "info"); return; }
  const res = await API.openFolderDialog();
  if (!res || res.canceled || !res.folder) return;
  await importFolder(res.folder);
}

async function clearAllConfigs() {
  if (state.configs.length === 0) {
    showToast("No targets to purge", "info");
    return;
  }
  logEvent("PURGE", `Purging all ${state.configs.length} targets...`, "warn");
  for (const config of state.configs) {
    try { await API.deleteConfig(config.id); } catch (e) { /* ignore */ }
  }
  state.configs = [];
  state.selectedConfig = null;
  renderTargetGrid();
  updateTargetCount();
  updateTelemetryStrip();
  logEvent("OK", "All targets purged", "ok");
  showToast("All targets purged", "warn");
}

// ═══════════════════════════════════════════════════════════════════════════
//   DRAG & DROP
// ═══════════════════════════════════════════════════════════════════════════

function setupDragDrop() {
  const dropZone = $("#drop-zone");
  if (!dropZone) return;

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault(); e.stopPropagation();
    dropZone.classList.add("drag-over");
  });
  dropZone.addEventListener("dragleave", (e) => {
    e.preventDefault(); e.stopPropagation();
    dropZone.classList.remove("drag-over");
  });
  dropZone.addEventListener("drop", async (e) => {
    e.preventDefault(); e.stopPropagation();
    dropZone.classList.remove("drag-over");
    showToast("Drag-drop not supported in Electron — use ACQUIRE TARGET", "info");
    logEvent("INFO", "Drag-drop rejected · use ACQUIRE TARGET button", "info");
  });
}

// ═══════════════════════════════════════════════════════════════════════════
//   TOASTS
// ═══════════════════════════════════════════════════════════════════════════

function showToast(message, type = "info") {
  const container = $("#toast-container");
  if (!container) return;
  const toast = el("div", { className: `toast ${type}` }, [
    el("span", { className: "toast-message" }, [message]),
    el("button", {
      className: "toast-close",
      onClick: () => toast.remove(),
    }, ["✕"]),
  ]);
  container.appendChild(toast);
  setTimeout(() => {
    if (toast.parentNode) {
      toast.classList.add("toast-fade");
      setTimeout(() => toast.remove(), 250);
    }
  }, 3500);
}

// ═══════════════════════════════════════════════════════════════════════════
//   BOOT SEQUENCE
// ═══════════════════════════════════════════════════════════════════════════

const BOOT_LINES = [
  { text: "[BOOT] InjectX // CIPHER_OPS kernel loading...",         cls: "bl-info" },
  { text: "[ OK ]  Initializing crypto primitives... ",              cls: "bl-ok" },
  { text: "[ OK ]  Loading format detectors (9 formats)... ",        cls: "bl-ok" },
  { text: "[ OK ]  Mounting key dictionary [76 entries]... ",        cls: "bl-ok" },
  { text: "[ OK ]  Establishing local link 127.0.0.1:8742... ",      cls: "bl-ok" },
  { text: "[WARN]  External uplink disabled (air-gapped mode)",      cls: "bl-warn" },
  { text: "[ OK ]  Console channels online",                         cls: "bl-ok" },
  { text: "[ OK ]  Tactical UI shell ready",                         cls: "bl-ok" },
  { text: "[BOOT] CIPHER_OPS engaged · awaiting targets",            cls: "bl-info" },
];

async function runBootSequence() {
  const overlay = $("#boot-overlay");
  const log = $("#boot-log");
  const barFill = $("#boot-bar-fill");
  const hint = $("#boot-hint");
  if (!overlay || !log || !barFill) return;

  for (let i = 0; i < BOOT_LINES.length; i++) {
    const line = BOOT_LINES[i];
    const lineEl = el("div", { className: "bl-line" }, [
      el("span", { className: line.cls }, [line.text]),
    ]);
    log.appendChild(lineEl);
    log.scrollTop = log.scrollHeight;
    barFill.style.width = `${((i + 1) / BOOT_LINES.length) * 100}%`;
    await new Promise((r) => setTimeout(r, 120 + Math.random() * 80));
  }

  hint.textContent = "READY";
  await new Promise((r) => setTimeout(r, 300));
  overlay.classList.add("hidden");
  setTimeout(() => overlay.remove(), 500);

  // First console logs
  logEvent("SYS", "CIPHER_OPS shell initialized", "sys");
  logEvent("SYS", "All modules online · awaiting target acquisition", "sys");
}

// ═══════════════════════════════════════════════════════════════════════════
//   CONSOLE INPUT (fake command line — for flavor)
// ═══════════════════════════════════════════════════════════════════════════

// ── Command system ─────────────────────────────────────────────────────────
// A small namespaced command tree shared by the Terminal view and the
// activity-log input. Handlers receive (args, io); io writes output:
//   io.echo(line)          — echo the entered command
//   io.print(text, type?)  — a result line ("info" | "err")
//   io.error(text)         — an error line
//   io.table(headers,rows) — an aligned table
//   io.clear()             — clear the current surface

const STATUS_SHORT = { decoded: "DECODED", locked: "LOCKED", unknown: "FAILED" };

// Resolve a target by id (full or 8-char short) or filename substring.
// Returns a config, {_ambiguous:[...]}, or null.
function resolveTarget(query) {
  if (!query) return null;
  const q = String(query).toLowerCase();
  const byId = state.configs.find(
    (c) => c.id.toLowerCase() === q || shortId(c.id).toLowerCase() === q,
  );
  if (byId) return byId;
  const matches = state.configs.filter((c) => (c.filename || "").toLowerCase().includes(q));
  if (matches.length === 1) return matches[0];
  if (matches.length > 1) return { _ambiguous: matches };
  return null;
}

function pickTarget(query, io) {
  if (!query) { io.error("Specify a target id or filename."); return null; }
  const r = resolveTarget(query);
  if (!r) { io.error(`No target matches '${query}'.`); return null; }
  if (r._ambiguous) {
    io.error(`'${query}' matches ${r._ambiguous.length} targets — be more specific:`);
    r._ambiguous.forEach((c) => io.print(`  ${shortId(c.id)}  ${c.filename}`));
    return null;
  }
  return r;
}

function looksLikePath(s) {
  return typeof s === "string" && (/[\\/]/.test(s) || /\.[a-z0-9]{2,6}$/i.test(s));
}

// Resolve to a full config for inspection: a loaded target (by id/filename)
// OR, when the argument is an absolute path on the user's machine, parse the
// file fresh via the backend. This is what lets the terminal work with the
// user's own files (Downloads, etc.), not just the loaded set.
async function resolveOrParse(query, io) {
  if (!query) { io.error("Specify a target id, filename, or filepath."); return null; }
  const r = resolveTarget(query);
  if (r && !r._ambiguous) return await API.getConfig(r.id);
  if (r && r._ambiguous && !looksLikePath(query)) {
    io.error(`'${query}' matches ${r._ambiguous.length} targets — be more specific:`);
    r._ambiguous.forEach((c) => io.print(`  ${shortId(c.id)}  ${c.filename}`));
    return null;
  }
  if (looksLikePath(query)) {
    io.print(`Parsing ${query} ...`);
    const res = await API.parseConfig(query);
    if (!res || res.error) { io.error(res && res.error ? res.error : "Parse failed."); return null; }
    await loadConfigs();
    return res;
  }
  io.error(`No target matches '${query}'.`);
  return null;
}

function targetHost(d) {
  const af = (d.raw_data && d.raw_data._all_fields) || {};
  return d.host || d.ssh_server || d.proxy_host || af.udpserver || af.sniHostname || null;
}

const CMD = {
  help(args, io) {
    io.print("InjectX // CIPHER_OPS — command reference:");
    io.table(["COMMAND", "DESCRIPTION"], [
      ["help", "this list"],
      ["clear", "clear the console"],
      ["version", "show app version"],
      ["targets <sub>", "manage loaded configs — 'targets help'"],
      ["logs <sub>", "activity log — 'logs help'"],
      ["system <sub>", "backend + environment — 'system help'"],
      ["assets import", "import all bundled sample configs"],
      ["sni <sub>", "discover + probe SNI bug hosts — 'sni help'"],
    ]);
  },
  version(args, io) { io.print("InjectX // CIPHER_OPS v0.5.0 — local-only, no telemetry."); },
  about(args, io) { io.print("InjectX — tactical VPN config inspector. Local-only, no telemetry."); },
  clear(args, io) { io.clear(); },
  // aliases for the old flat commands
  status(args, io) { return CMD.system.status(args, io); },
  purge(args, io) { return CMD.targets.purge(args, io); },

  targets: {
    help(args, io) {
      io.print("targets — manage configs (accepts a loaded target id/name, or a filepath on your machine):");
      io.table(["SUBCOMMAND", "DESCRIPTION"], [
        ["targets [list]", "list all loaded targets"],
        ["targets pick", "open the file picker to add config(s) from your machine"],
        ["targets openfolder", "pick a folder and import every config in it"],
        ["targets import <folder>", "import every config in a folder by path"],
        ["targets info <id|file|path>", "summary of one target or a file"],
        ["targets debug <id|file|path>", "scheme, file location, decrypt trace"],
        ["targets open <id|file>", "open a loaded target's detail view"],
        ["targets export <id|file>", "download a target's JSON"],
        ["targets purge [id|file|all]", "delete one, or all if omitted"],
        ["targets import <filepath>", "parse a config file by absolute path"],
        ["targets count", "counts by format and status"],
      ]);
    },
    _default(args, io) { return CMD.targets.list(args, io); },
    async pick(args, io) {
      if (!API.openFileDialog) { io.error("File picker is only available in the desktop app."); return; }
      io.print("Opening file picker...");
      const paths = await API.openFileDialog();
      if (!paths || !paths.length) { io.print("No file selected."); return; }
      for (const p of paths) {
        const r = await API.parseConfig(p);
        if (r && !r.error) io.print(`Added ${r.filename} — ${r.format} [${r.decryption_status}]`);
        else io.error(`Failed: ${p.split(/[\\/]/).pop()}${r && r.error ? " · " + r.error : ""}`);
      }
      await loadConfigs();
    },
    list(args, io) {
      if (!state.configs.length) { io.print("No targets loaded. Drop a config or run 'assets import'."); return; }
      io.table(["#", "ID", "FMT", "STATUS", "FILE"], state.configs.map((c, i) => [
        i + 1, shortId(c.id), (c.format || "?").toUpperCase(),
        STATUS_SHORT[classifyStatus(c)] || "?", c.filename || "unnamed",
      ]));
      io.print(`${state.configs.length} target(s).`);
    },
    async info(args, io) {
      const full = await resolveOrParse(args.join(" ").trim(), io); if (!full) return;
      const d = full.config || {};
      io.print(`TGT_${shortId(full.id || "")}  ${full.filename}`);
      io.print(`  format ${full.format}  ·  scheme ${full.scheme_used || "—"}  ·  status ${full.decryption_status}`);
      const host = targetHost(d);
      if (host) io.print(`  host      ${host}`);
      if (d.port) io.print(`  port      ${d.port}`);
      if (d.protocol) io.print(`  protocol  ${d.protocol}`);
      if (d.sni) io.print(`  sni       ${d.sni}`);
      if (d.ssh_user) io.print(`  ssh user  ${d.ssh_user}`);
    },
    open(args, io) {
      const c = pickTarget(args[0], io); if (!c) return;
      io.print(`Opening TGT_${shortId(c.id)} — ${c.filename}`);
      showConfigDetail(c.id);
    },
    async debug(args, io) {
      const full = await resolveOrParse(args.join(" ").trim(), io); if (!full) return;
      io.print(`DEBUG TGT_${shortId(full.id || "")}  ${full.filename}`);
      io.print(`  location   ${full.filepath || "—"}`);
      io.print(`  format ${full.format}  ·  scheme ${full.scheme_used || "—"}  ·  confidence ${full.confidence ?? "—"}`);
      io.print(`  status     ${full.decryption_status}`);
      const tr = full.decrypt_trace;
      const attempts = (tr && tr.attempts) || [];
      if (attempts.length) {
        // Surface the interesting attempts (success/error) first, then fill
        // with the rest up to a cap so a 200-key brute-force doesn't flood.
        const CAP = 20;
        const ranked = attempts.slice().sort((a, b) =>
          (a.result === "fail" ? 1 : 0) - (b.result === "fail" ? 1 : 0));
        const shown = ranked.slice(0, CAP);
        const okN = attempts.filter((a) => a.result === "success").length;
        io.print(`  decrypt attempts: ${attempts.length} total · ${okN} success (showing ${shown.length})`);
        io.table(["SCHEME", "RESULT", "KEY", "TIME"], shown.map((a) => [
          a.scheme || "?", a.result || "?", (a.key_label || "").slice(0, 24),
          a.elapsed_ms != null ? a.elapsed_ms.toFixed(1) + "ms" : "",
        ]));
        if (attempts.length > CAP) io.print(`  … ${attempts.length - CAP} more attempt(s) omitted.`);
      } else {
        io.print("  no decrypt attempts recorded.");
      }
      if (full.errors && full.errors.length) io.print("  errors: " + full.errors.join("; "));
    },
    export(args, io) {
      const c = pickTarget(args[0], io); if (!c) return;
      io.print(`Exporting TGT_${shortId(c.id)}...`);
      exportConfig(c.id);
    },
    async purge(args, io) {
      const q = args[0];
      if (!q || q.toLowerCase() === "all") {
        if (!state.configs.length) { io.print("No targets to purge."); return; }
        const n = state.configs.length;
        await clearAllConfigs();
        io.print(`Purged ${n} target(s).`);
        return;
      }
      const c = pickTarget(q, io); if (!c) return;
      await deleteConfig(c.id);
      io.print(`Purged TGT_${shortId(c.id)} — ${c.filename}`);
    },
    async import(args, io) {
      const p = args.join(" ").trim();
      if (!p) { io.error("Usage: targets import <filepath | folder path>"); return; }
      // A path whose last segment has no dot is treated as a folder.
      const isFolder = !p.split(/[\\/]/).pop().includes(".");
      if (isFolder) {
        io.print(`Scanning folder ${p} ...`);
        const res = await API.listConfigFiles(p);
        if (!res || res.error) { io.error(res && res.error ? res.error : "Could not read folder."); return; }
        const files = res.files || [];
        if (!files.length) { io.print("No config files found in that folder."); return; }
        let ok = 0;
        for (const f of files) { const r = await API.parseConfig(f); if (r && !r.error) ok++; }
        if (API.setLastFolder) await API.setLastFolder(p);
        await loadConfigs();
        io.print(`Imported ${ok}/${files.length} config(s) from the folder.`);
        return;
      }
      io.print(`Parsing ${p} ...`);
      const res = await API.parseConfig(p);
      if (!res || res.error) { io.error(res && res.error ? res.error : "Parse failed."); return; }
      await loadConfigs();
      io.print(`Imported TGT_${shortId(res.id)} — ${res.filename} [${res.decryption_status}]`);
    },
    async openfolder(args, io) {
      if (!API.openFolderDialog) { io.error("Folder picker is only available in the desktop app."); return; }
      io.print("Opening folder picker...");
      const res = await API.openFolderDialog();
      if (!res || res.canceled || !res.folder) { io.print("No folder selected."); return; }
      const n = await importFolder(res.folder);
      io.print(`Imported ${n} config(s) from ${res.folder}.`);
    },
    count(args, io) {
      const byFmt = {}, byStatus = { decoded: 0, locked: 0, unknown: 0 };
      for (const c of state.configs) {
        byFmt[c.format] = (byFmt[c.format] || 0) + 1;
        byStatus[classifyStatus(c)]++;
      }
      io.print(`Total ${state.configs.length}  ·  decoded ${byStatus.decoded}  ·  locked ${byStatus.locked}  ·  failed ${byStatus.unknown}`);
      const rows = Object.entries(byFmt).sort().map(([f, n]) => [f.toUpperCase(), n]);
      if (rows.length) io.table(["FMT", "COUNT"], rows);
    },
  },

  logs: {
    help(args, io) { io.print("logs [list [n]]  ·  logs clear  ·  logs copy"); },
    _default(args, io) { return CMD.logs.list(args, io); },
    list(args, io) {
      const n = parseInt(args[0], 10) || 20;
      const entries = state.archive.slice(0, n); // newest-first
      if (!entries.length) { io.print("No log entries."); return; }
      entries.slice().reverse().forEach((e) => io.print(`${fmtTime(new Date(e.time))} [${e.tag}] ${e.msg}`));
    },
    clear(args, io) {
      state.archive = [];
      renderArchive();
      const cb = $("#console-body"); if (cb) cb.innerHTML = "";
      state.consoleLines = 0;
      const cnt = $("#console-line-count"); if (cnt) cnt.textContent = "0 EVENTS";
      io.print("Logs cleared.");
    },
    copy(args, io) {
      if (!state.archive.length) { io.print("No logs to copy."); return; }
      copyText(archiveAsText());
      io.print(`Copied ${state.archive.length} log line(s) to the clipboard.`);
    },
  },

  system: {
    help(args, io) { io.print("system [status]  ·  system formats  ·  system health"); },
    _default(args, io) { return CMD.system.status(args, io); },
    async status(args, io) {
      const total = state.configs.length;
      const dec = state.configs.filter((c) => classifyStatus(c) === "decoded").length;
      let backend = "offline";
      try { const h = await API.checkHealth(); if (h && h.status === "ok") backend = "online"; } catch (e) { /* offline */ }
      io.print("InjectX // CIPHER_OPS v0.5.0");
      io.print(`  targets ${total}  ·  decoded ${dec}`);
      io.print(`  backend ${backend}  ·  127.0.0.1:8742`);
    },
    async formats(args, io) {
      const r = await API.getFormats();
      const fmts = (r && (r.formats || r)) || [];
      io.table(["FMT", "SCHEMES", "DECRYPT"], fmts.map((f) => [
        (f.id || f.name || "?").toUpperCase(),
        (f.schemes || []).join(",") || "—",
        f.decryptable ? "yes" : "no",
      ]));
    },
    async health(args, io) {
      try { const h = await API.checkHealth(); io.print(h && h.status === "ok" ? "Backend link: OK" : "Backend link: DEGRADED"); }
      catch (e) { io.error("Backend link: OFFLINE — start the backend."); }
    },
  },

  assets: {
    help(args, io) { io.print("assets import — import all bundled sample configs from assets/configs/"); },
    _default(args, io) { return CMD.assets.import(args, io); },
    async import(args, io) {
      io.print("Importing bundled assets...");
      await importAssets();
      io.print("Import complete. Run 'targets list'.");
    },
  },

  // SNI HOST HUNTER — discover + probe candidate SNI "bug hosts".
  sni: {
    help(args, io) {
      io.print("sni — discover and probe SNI bug hosts (research/verification):");
      io.table(["SUBCOMMAND", "DESCRIPTION"], [
        ["sni find <domain>", "discover candidates via crt.sh (Certificate Transparency)"],
        ["sni scan <seedlist|host...>", "probe a bundled/seedlist path or inline host(s)"],
        ["sni scan --cf-only <seedlist>", "scan only cloudflare:true entries (csv/json)"],
        ["sni seedlists", "list bundled per-ISP seed lists"],
        ["sni jobs", "list scan jobs"],
        ["sni stop <jobId>", "stop a running scan"],
        ["sni export <jobId> <txt|csv|json>", "download scan results"],
      ]);
    },
    _default(args, io) { return CMD.sni.help(args, io); },
    async find(args, io) {
      const domain = (args[0] || "").trim();
      if (!domain) { io.error("Usage: sni find <domain>"); return; }
      io.print(`Querying crt.sh for ${domain} ...`);
      const r = await API.sni.discover(domain);
      if (!r || r.error) { io.error(r && r.error ? r.error : "Discovery failed."); return; }
      const cands = r.candidates || [];
      if (!cands.length) { io.print("No candidates found."); return; }
      io.table(["#", "HOSTNAME"], cands.slice(0, 100).map((c, i) => [i + 1, c.hostname]));
      io.print(`${r.count} candidate(s). Scan them with: sni scan ${domain > "" ? cands[0].hostname : ""} ...`);
    },
    async seedlists(args, io) {
      const r = await API.sni.seedlists();
      if (!r || r.error) { io.error(r && r.error ? r.error : "Could not list seedlists."); return; }
      const lists = r.seedlists || [];
      if (!lists.length) { io.print("No bundled seedlists."); return; }
      io.table(["NAME", "HOSTS", "PATH"], lists.map((s) => [s.name, s.hosts, s.path]));
    },
    async jobs(args, io) {
      const r = await API.sni.jobs();
      if (!r || r.error) { io.error(r && r.error ? r.error : "Could not list jobs."); return; }
      const jobs = r.jobs || [];
      if (!jobs.length) { io.print("No scan jobs."); return; }
      io.table(["JOB", "STATUS", "DONE", "FOUND"], jobs.map((j) => [
        j.job_id, j.status, `${j.done}/${j.total}`, j.found,
      ]));
    },
    async stop(args, io) {
      const jid = (args[0] || "").trim();
      if (!jid) { io.error("Usage: sni stop <jobId>"); return; }
      const r = await API.sni.stop(jid);
      if (!r || r.error) { io.error(r && r.error ? r.error : "Stop failed."); return; }
      io.print(`Stopping ${jid} (in-flight probes finish; queued ones skip).`);
    },
    async export(args, io) {
      const jid = (args[0] || "").trim();
      const fmt = (args[1] || "txt").trim().toLowerCase();
      if (!jid) { io.error("Usage: sni export <jobId> <txt|csv|json>"); return; }
      const r = await API.sni.export(jid, fmt);
      if (!r || r.error) { io.error(r && r.error ? r.error : "Export failed."); return; }
      // Same Blob-download pattern as config export.
      const blob = new Blob([r.content || ""], { type: r.media_type || "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = r.filename || `sni-${jid}.${fmt}`;
      a.click();
      URL.revokeObjectURL(url);
      io.print(`Exported ${r.filename}.`);
    },
    async scan(args, io) {
      // Optional --cf-only flag anywhere in the args.
      let cfOnly = false;
      const rest = [];
      for (const a of args) {
        if (a === "--cf-only" || a === "--cloudflare-only") cfOnly = true;
        else rest.push(a);
      }
      if (!rest.length) { io.error("Usage: sni scan <seedlist-path | seedlist-name | host...> [--cf-only]"); return; }

      const opts = { concurrency: 50, timeout_s: 5.0, cloudflare_only: cfOnly };
      const first = rest[0];
      const hasSlash = /[\\/]/.test(first);
      if (hasSlash) {
        // An absolute path (possibly with spaces) — a seedlist file on disk.
        opts.seedlist_path = rest.join(" ");
      } else if (rest.length === 1 && /\.(txt|csv|json)$/i.test(first)) {
        // A bundled seedlist by name (no slash) — resolve to its absolute path.
        const sr = await API.sni.seedlists();
        const match = (sr && sr.seedlists || []).find((s) => s.name === first);
        if (!match) { io.error(`No bundled seedlist named '${first}'. Try 'sni seedlists'.`); return; }
        opts.seedlist_path = match.path;
      } else {
        // One or more bare hostnames to probe directly.
        opts.candidates = rest;
      }

      const started = await API.sni.scan(opts);
      if (!started || started.error) { io.error(started && started.error ? started.error : "Scan failed to start."); return; }
      const jid = started.job_id;
      io.print(`Scan ${jid} started — ${started.total} host(s), concurrency ${started.concurrency}. Progress streams to the activity log.`);

      // Poll until the job finishes (cap the wait so the terminal never hangs).
      for (let i = 0; i < 600; i++) {
        await new Promise((res) => setTimeout(res, 1000));
        const j = await API.sni.job(jid);
        if (!j || j.error) { io.error(j && j.error ? j.error : "Lost the job."); return; }
        if (["done", "stopped", "failed"].includes(j.status)) {
          if (j.status === "failed") { io.error(`Scan failed: ${j.error || "unknown"}`); return; }
          const rows = (j.results || []).map((r) => [
            r.hostname, r.verdict, r.http_status ?? "—", r.server_header || "—", r.target_ip || "—",
          ]);
          io.table(["HOSTNAME", "VERDICT", "HTTP", "SERVER", "IP"], rows);
          io.print(`${j.status}: ${j.found} working / ${j.total}. Export with: sni export ${jid} txt`);
          return;
        }
      }
      io.print(`Still running — check 'sni jobs' or the activity log (job ${jid}).`);
    },
  },
};

function archiveAsText() {
  return state.archive.slice().reverse()
    .map((e) => `${fmtTime(new Date(e.time))} [${e.tag}] ${e.msg}`).join("\n");
}

// Format an aligned text table (monospace).
function fmtTable(headers, rows) {
  const widths = headers.map((h, i) =>
    Math.max(String(h).length, ...rows.map((r) => String(r[i] ?? "").length)));
  const line = (cells) => cells.map((c, i) => String(c ?? "").padEnd(widths[i])).join("  ").trimEnd();
  return [line(headers), ...rows.map(line)];
}

// Split a command line into tokens, honouring "double" and 'single' quotes so
// that paths with spaces (e.g. "C:\Users\me\My Configs\a.hc") stay one token.
function tokenize(raw) {
  const out = [];
  const re = /"([^"]*)"|'([^']*)'|(\S+)/g;
  let m;
  while ((m = re.exec(raw)) !== null) {
    out.push(m[1] !== undefined ? m[1] : (m[2] !== undefined ? m[2] : m[3]));
  }
  return out;
}

async function runCommand(raw, io) {
  io.echo(raw);
  const tokens = tokenize(raw.trim());
  const name = (tokens[0] || "").toLowerCase();
  const node = CMD[name];
  if (!node) { io.error(`Unknown command: ${name}. Type 'help'.`); return; }
  try {
    if (typeof node === "function") { await node(tokens.slice(1), io); return; }
    const sub = (tokens[1] || "").toLowerCase();
    const handler = (sub && node[sub]) || node._default;
    const args = (sub && node[sub]) ? tokens.slice(2) : tokens.slice(1);
    if (!handler) { io.error(`Unknown subcommand '${name} ${sub}'. Try '${name} help'.`); return; }
    await handler(args, io);
  } catch (e) {
    io.error(`Error: ${e && e.message ? e.message : e}`);
  }
}

// IO surface for the Terminal view.
function terminalIO() {
  return {
    echo: (line) => termWrite(`> ${line}`, "cmd"),
    print: (t, type) => termWrite(t, type),
    error: (t) => termWrite(t, "err"),
    clear: () => { const b = $("#terminal-body"); if (b) b.innerHTML = ""; },
    table: (headers, rows) => fmtTable(headers, rows).forEach((l) => termWrite(l, "out")),
  };
}
// IO surface for the activity-log input (single-line entries).
function consoleIO() {
  return {
    echo: (line) => logEvent("CMD", `> ${line}`, "info"),
    print: (t, type) => logEvent(type === "err" ? "ERR" : "OUT", t, type || "info"),
    error: (t) => logEvent("ERR", t, "err"),
    clear: () => {
      const b = $("#console-body"); if (b) b.innerHTML = "";
      state.consoleLines = 0;
      const c = $("#console-line-count"); if (c) c.textContent = "0 EVENTS";
    },
    table: (headers, rows) => fmtTable(headers, rows).forEach((l) => logEvent("OUT", l, "info")),
  };
}

function setupConsoleInput() {
  const input = $("#console-input");
  if (input) {
    input.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      const raw = input.value.trim();
      if (!raw) return;
      input.value = "";
      runCommand(raw, consoleIO());
    });
    const ciRow = $(".console-input");
    if (ciRow) ciRow.addEventListener("click", () => input.focus());
  }

  // Collapse / expand the activity-log dock.
  const toggle = $("#btn-toggle-console");
  const consoleEl = $(".console");
  if (toggle && consoleEl) {
    toggle.addEventListener("click", () => {
      const collapsed = consoleEl.classList.toggle("collapsed");
      toggle.textContent = collapsed ? "⟨" : "⟩";
      toggle.title = collapsed ? "Expand activity log" : "Collapse activity log";
    });
  }
}

// Terminal view — a full-size command console.
function termWrite(text, type) {
  const body = $("#terminal-body");
  if (!body) return;
  const cls = type === "err" ? "term-err" : (type === "cmd" ? "term-cmd" : "term-out");
  body.appendChild(el("div", { className: "term-line" }, [
    el("span", { className: cls }, [String(text)]),
    copyBtn(String(text), "term-copy"),
  ]));
  body.scrollTop = body.scrollHeight;
}

function terminalAsText() {
  return [...$$("#terminal-body .term-line span:first-child")].map((s) => s.textContent).join("\n");
}

function setupTerminal() {
  const input = $("#terminal-input");
  if (!input) return;
  input.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const raw = input.value.trim();
    if (!raw) return;
    input.value = "";
    runCommand(raw, terminalIO());
  });
  const row = $(".terminal-input-row");
  if (row) row.addEventListener("click", () => input.focus());

  const copyBtnEl = $("#btn-copy-terminal");
  if (copyBtnEl) copyBtnEl.addEventListener("click", () => {
    const text = terminalAsText();
    if (!text.trim()) { showToast("Terminal is empty", "info"); return; }
    copyText(text, () => showToast("Terminal output copied", "success"));
  });
  const clearBtnEl = $("#btn-clear-terminal");
  if (clearBtnEl) clearBtnEl.addEventListener("click", () => { const b = $("#terminal-body"); if (b) b.innerHTML = ""; });
}

// ═══════════════════════════════════════════════════════════════════════════
//   INIT
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[Renderer] InjectX // CIPHER_OPS v0.5.0 initializing...");

  // Session ID in titlebar
  const sessEl = $("#session-id");
  if (sessEl) sessEl.textContent = genSessionId();

  // Boot sequence first
  await runBootSequence();

  // Clock
  startClock();

  // Backend health check
  try {
    const health = await API.checkHealth();
    if (health && health.status === "ok") {
      setSidebarStatus(true);
      setStatusPill("ok", "OPERATIONAL");
      logEvent("OK", "Backend link established", "ok");
    } else {
      throw new Error("bad status");
    }
  } catch (err) {
    setSidebarStatus(false);
    setStatusPill("err", "OFFLINE");
    logEvent("ERR", "Backend link failed — start backend first", "err");
    showToast("Backend offline", "error");
  }

  // Load existing configs
  await loadConfigs();

  // Reopen the last folder the user worked in (IDE-style "last project").
  // The backend's store is cleared on restart, so re-import to restore it.
  try {
    if (API.getLastFolder) {
      const last = await API.getLastFolder();
      if (last) { logEvent("SYS", `Reopening last folder: ${last}`, "sys"); await importFolder(last, true); }
    }
  } catch (e) { /* no last folder or not in desktop app */ }

  // Setup
  setupDragDrop();
  renderArsenalView();
  renderArchive();
  setupConsoleInput();
  setupTerminal();

  // "Import Assets" loads the bundled dev sample configs — hide it in the
  // packaged app so real users work only from their own file selections.
  try {
    const dev = await API.isDev();
    const assetsBtn = $("#btn-import-assets");
    if (assetsBtn && !dev) assetsBtn.style.display = "none";
  } catch (e) { /* keep the button if we can't tell */ }

  // Navigation
  $$(".sb-nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      const view = item.dataset.view;
      if (view) showView(view);
    });
  });

  // Filter pills
  $$(".filter-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      $$(".filter-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      state.filter = pill.dataset.filter;
      state.formatFilter = null; // status pills clear any Arsenal format filter
      renderTargetGrid();
    });
  });

  // Action buttons
  const openBtn = $("#btn-open-config");
  if (openBtn) openBtn.addEventListener("click", openConfig);

  const openFolderBtn = $("#btn-open-folder");
  if (openFolderBtn) openFolderBtn.addEventListener("click", openFolder);

  const importAssetsBtn = $("#btn-import-assets");
  if (importAssetsBtn) importAssetsBtn.addEventListener("click", importAssets);

  const clearBtn = $("#btn-clear-all");
  if (clearBtn) clearBtn.addEventListener("click", clearAllConfigs);

  // Initial assets count badge
  refreshAssetsCount();
  // Refresh assets count periodically (so dropping a new file shows up)
  setInterval(refreshAssetsCount, 5000);

  const copyArchiveBtn = $("#btn-copy-archive");
  if (copyArchiveBtn) copyArchiveBtn.addEventListener("click", () => {
    if (!state.archive.length) { showToast("No logs to copy", "info"); return; }
    copyText(archiveAsText(), () => showToast(`Copied ${state.archive.length} log line(s)`, "success"));
  });

  const clearArchiveBtn = $("#btn-clear-archive");
  if (clearArchiveBtn) clearArchiveBtn.addEventListener("click", () => {
    state.archive = [];
    renderArchive();
    logEvent("SYS", "Archive cleared", "sys");
  });

  const clearConsoleBtn = $("#btn-clear-console");
  if (clearConsoleBtn) clearConsoleBtn.addEventListener("click", () => {
    $("#console-body").innerHTML = "";
    state.consoleLines = 0;
    $("#console-line-count").textContent = "0 EVENTS";
  });

  // Files selected from Electron menu
  API.onFilesSelected(async (filePaths) => {
    for (const filePath of filePaths) {
      const fname = filePath.split(/[\\/]/).pop();
      logEvent("ACQUIRE", `Importing target: ${fname}`, "info");
      const result = await API.parseConfig(filePath);
      if (result.error) {
        logEvent("ERR", `Failed: ${result.error}`, "err");
      } else {
        const meta = formatMeta(result.format);
        logEvent("OK", `Acquired ${meta.short} · ${fname}`, "ok");
        showToast(`Acquired: ${fname}`, "success");
      }
    }
    await loadConfigs();
  });

  // ── CustomTitleBar window controls ────────────────────────────────────
  const btnMinimize = $("#btn-minimize");
  const btnMaximize = $("#btn-maximize");
  const btnClose = $("#btn-close");
  const iconMaximize = $("#icon-maximize");
  const iconRestore = $("#icon-restore");

  if (btnMinimize) btnMinimize.addEventListener("click", () => API.windowMinimize());
  if (btnMaximize) btnMaximize.addEventListener("click", () => API.windowMaximize());
  if (btnClose) btnClose.addEventListener("click", () => API.windowClose());

  async function syncMaximizeIcon() {
    try {
      const isMax = await API.windowIsMaximized();
      if (iconMaximize && iconRestore) {
        iconMaximize.style.display = isMax ? "none" : "";
        iconRestore.style.display = isMax ? "" : "none";
      }
    } catch (e) { /* ignore */ }
  }
  syncMaximizeIcon();

  API.onWindowStateChanged((windowState) => {
    if (iconMaximize && iconRestore) {
      const isMax = windowState === "maximized";
      iconMaximize.style.display = isMax ? "none" : "";
      iconRestore.style.display = isMax ? "" : "none";
    }
  });

  console.log("[Renderer] CIPHER_OPS ready");
});
