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
const FORMAT_META = {
  ehi:   { name: "HTTP Injector",  color: "var(--c-ehi)",   short: "EHI",   exts: [".ehi"] },
  hc:    { name: "HTTP Custom",    color: "var(--c-hc)",    short: "HC",    exts: [".hc"] },
  hat:   { name: "HA Tunnel Plus", color: "var(--c-hat)",   short: "HAT",   exts: [".hat", ".ha"] },
  dark:  { name: "DARK TUNNEL",    color: "var(--c-dark)",  short: "DARK",  exts: [".dark", ".drak", ".dt"] },
  tls:   { name: "TLS Tunnel",     color: "var(--c-tls)",   short: "TLS",   exts: [".tls"] },
  npv:   { name: "NapsternetV",    color: "var(--c-npv)",   short: "NPV",   exts: [".npv4", ".inpv", ".npv"] },
  nsh:   { name: "SocksHTTP",      color: "var(--c-nsh)",   short: "NSH",   exts: [".nsh"] },
  vhd:   { name: "V2Ray Tunnel",   color: "var(--c-vhd)",   short: "VHD",   exts: [".vhd"] },
  ovpn:  { name: "OpenVPN",        color: "var(--c-ovpn)",  short: "OVPN",  exts: [".ovpn"] },
  unknown: { name: "Unknown",      color: "var(--c-unk)",   short: "UNK",   exts: [] },
};

function formatMeta(fmt) {
  return FORMAT_META[fmt] || FORMAT_META.unknown;
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

function logEvent(tag, msg, type = "info") {
  const body = $("#console-body");
  if (!body) return;

  const line = el("div", { className: "console-line" }, [
    el("span", { className: "cl-time" }, [fmtTime()]),
    el("span", { className: `cl-tag cl-tag-${type}` }, [tag]),
    el("span", { className: "cl-msg" }, [msg]),
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
    ]));
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//   STATUS HEADER (clock, marquee)
// ═══════════════════════════════════════════════════════════════════════════

function startClock() {
  const tick = () => {
    const sh = $("#sh-clock");
    if (sh) sh.textContent = fmtUTC();
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

  // Apply filter
  const filtered = state.configs.filter((c) => {
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
      el("span", { className: "tc-format" }, [meta.short]),
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

  // ── Status panel ───────────────────────────────────────────────────────
  if (status === "decoded") {
    container.appendChild(el("div", { className: "detail-panel" }, [
      el("div", { className: "dp-title" }, ["EXTRACTION SUCCESSFUL"]),
      el("p", { className: "dp-msg" }, [
        "Payload successfully extracted. All configuration fields below are readable. ",
        "Sensitive values (passwords, secrets) are masked by default — hover to reveal.",
      ]),
    ]));
  } else if (status === "locked") {
    container.appendChild(el("div", { className: "detail-panel warn" }, [
      el("div", { className: "dp-title" }, ["ENVELOPE LOCKED"]),
      el("p", { className: "dp-msg" }, [
        "This configuration uses a proprietary encryption scheme with no public decryptor available. ",
        "Only basic metadata is shown. The underlying payload cannot be extracted.",
      ]),
    ]));
  } else if (status === "unknown") {
    container.appendChild(el("div", { className: "detail-panel err" }, [
      el("div", { className: "dp-title" }, ["EXTRACTION FAILED"]),
      el("p", { className: "dp-msg" }, [
        "All known extraction approaches were attempted but none produced a readable result. ",
        "This configuration may use a newer encryption variant or an unsupported structure.",
      ]),
    ]));
  }

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

function renderConfigData(container, d) {
  // ── Connection ─────────────────────────────────────────────────────────
  const connectionFields = [
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
  ];
  renderKVSection(container, "CONNECTION", connectionFields, d);

  // ── SSH ────────────────────────────────────────────────────────────────
  const sshFields = [
    { key: "ssh_server", label: "SSH Server" },
    { key: "ssh_port",   label: "SSH Port" },
    { key: "ssh_user",   label: "Username" },
    { key: "ssh_pass",   label: "Password", secret: true },
  ];
  renderKVSection(container, "SSH CREDENTIALS", sshFields, d);

  // ── Proxy ──────────────────────────────────────────────────────────────
  const proxyFields = [
    { key: "proxy_host", label: "Proxy Host" },
    { key: "proxy_port", label: "Proxy Port" },
  ];
  renderKVSection(container, "PROXY", proxyFields, d);

  // ── DNS ────────────────────────────────────────────────────────────────
  const dnsFields = [
    { key: "dns",         label: "DNS Server" },
    { key: "remote_dns",  label: "Remote DNS" },
  ];
  renderKVSection(container, "DNS", dnsFields, d);

  // ── Protections (HC v2.7+ — hwid/area/password/provider locks) ─────────
  // Protections may be at top level OR inside raw_data
  const protections = d.protections || (d.raw_data && d.raw_data.protections);
  if (protections && Object.keys(protections).length > 0) {
    const protFields = Object.entries(protections).map(([k, v]) => ({
      key: k, label: k.toUpperCase(), value: v,
    }));
    renderKVSection(container, "PROTECTIONS", protFields, protections);
  }

  // ── HTTP Payload (with [crlf] / [split] / [crlf][crlf] syntax highlighting) ─
  if (d.payload) {
    const highlighted = highlightPayload(String(d.payload));
    container.appendChild(el("div", { className: "detail-section" }, [
      el("div", { className: "detail-section-head" }, [
        el("span", { className: "detail-section-title" }, ["HTTP PAYLOAD"]),
        el("span", { className: "detail-section-hint" }, ["[crlf] = \\r\\n  ·  [split] = request separator  ·  [proxy] = injected host  ·  [ua] = user-agent"]),
      ]),
      el("div", { className: "detail-section-body" }, [
        el("pre", { className: "payload-block payload-highlighted" }),
      ]),
    ]));
    // Inject highlighted HTML into the pre (safer than innerHTML on a string)
    const pre = container.querySelector(".payload-highlighted:last-child");
    if (pre) pre.innerHTML = highlighted;
  }

  // ── Notes (HC v2.7+ — HTML content shown sanitized in an iframe-like sandbox) ──
  // Notes may be at top level OR inside raw_data._all_fields.notes
  const notes = d.notes
              || (d.raw_data && d.raw_data._all_fields && d.raw_data._all_fields.notes)
              || (d.raw_data && d.raw_data.notes);
  if (notes && typeof notes === "string" && notes.trim()) {
    container.appendChild(el("div", { className: "detail-section" }, [
      el("div", { className: "detail-section-head" }, [
        el("span", { className: "detail-section-title" }, ["NOTES (HTML)"]),
      ]),
      el("div", { className: "detail-section-body" }, [
        renderNotesSandboxed(notes),
      ]),
    ]));
  }

  // ── Custom headers ─────────────────────────────────────────────────────
  if (d.custom_headers && Object.keys(d.custom_headers).length > 0) {
    container.appendChild(el("div", { className: "detail-section" }, [
      el("div", { className: "detail-section-head" }, [
        el("span", { className: "detail-section-title" }, ["CUSTOM HEADERS"]),
      ]),
      el("div", { className: "detail-section-body" }, [
        el("pre", { className: "payload-block" }, [JSON.stringify(d.custom_headers, null, 2)]),
      ]),
    ]));
  }

  // ── Protocol-specific blocks ───────────────────────────────────────────
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
    if (d[key] && typeof d[key] === "object" && Object.keys(d[key]).length > 0) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("div", { className: "detail-section-head" }, [
          el("span", { className: "detail-section-title" }, [label]),
        ]),
        el("div", { className: "detail-section-body" }, [
          el("pre", { className: "payload-block" }, [JSON.stringify(d[key], null, 2)]),
        ]),
      ]));
    } else if (d[key] && typeof d[key] === "string" && d[key].trim()) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("div", { className: "detail-section-head" }, [
          el("span", { className: "detail-section-title" }, [label]),
        ]),
        el("div", { className: "detail-section-body" }, [
          el("pre", { className: "payload-block" }, [String(d[key])]),
        ]),
      ]));
    }
  }

  // ── Raw JSON (collapsible) ─────────────────────────────────────────────
  const rawToggle = el("button", { className: "action-btn" }, ["{} TOGGLE RAW JSON"]);
  const rawBlock = el("pre", { className: "payload-block hidden", style: "margin-top: 8px;" }, [JSON.stringify(d, null, 2)]);
  rawToggle.addEventListener("click", () => rawBlock.classList.toggle("hidden"));

  container.appendChild(el("div", { className: "detail-section" }, [
    el("div", { className: "detail-section-head" }, [
      el("span", { className: "detail-section-title" }, ["RAW PAYLOAD"]),
      rawToggle,
    ]),
    rawBlock,
  ]));
}

/**
 * Highlight HC payload syntax: [crlf], [crlf][crlf], [split], [proxy], [ua],
 * HTTP methods (GET/POST/CONNECT/...), and HTTP version (HTTP/1.1).
 * Returns an HTML string safe to assign to a pre.innerHTML.
 *
 * Input is escaped first, then markers are wrapped in <span> tags — so
 * user-controlled payload content can never break out of the pre element.
 */
function highlightPayload(payload) {
  // 1. HTML-escape everything
  const esc = (s) => s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  let html = esc(payload);

  // 2. Highlight [crlf], [split], [proxy], [ua] markers
  html = html.replace(
    /\[(crlf|split|proxy|ua|host|raw|method|proto)\]/gi,
    '<span class="pl-mark pl-mark-$1">$&amp;</span>'
  );
  // 3. Highlight HTTP methods at line start
  html = html.replace(
    /^(GET|POST|PUT|CONNECT|HEAD|OPTIONS|PATCH|UNLOCK|PROPFIND|REPORT) /gm,
    '<span class="pl-method">$1</span> '
  );
  // 4. Highlight HTTP version
  html = html.replace(
    /(HTTP\/[0-9.]+)/g,
    '<span class="pl-version">$1</span>'
  );
  // 5. Highlight "Host: ..." lines
  html = html.replace(
    /^(Host: .+)$/gm,
    '<span class="pl-host">$1</span>'
  );

  return html;
}

/**
 * Render HC v2.7 notes (raw HTML from the config author) in a sandboxed
 * iframe so it can't affect the rest of the app.
 */
function renderNotesSandboxed(html) {
  const wrapper = el("div", { className: "notes-sandbox-wrap" });
  const iframe = document.createElement("iframe");
  iframe.className = "notes-sandbox";
  iframe.sandbox = "allow-same-origin";
  iframe.setAttribute("srcdoc", `<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{background:#070a0c;color:#d4f1e4;font-family:monospace;padding:12px;margin:0;font-size:11px;line-height:1.5;}</style></head><body>${html}</body></html>`);
  wrapper.appendChild(iframe);
  return wrapper;
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
      valEl,
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

function renderArsenalView() {
  const grid = $("#arsenal-grid");
  if (!grid) return;
  grid.innerHTML = "";

  const formats = [
    { id: "ehi",  desc: "HTTP Injector configuration archive. Plain JSON inside a ZIP wrapper; may be locked with an obfuscation layer." },
    { id: "hc",   desc: "HTTP Custom encrypted format. Widely-used in mobile proxy configs. Supported via known-key dictionary." },
    { id: "hat",  desc: "HA Tunnel Plus configuration. Encrypted JSON envelope; multiple profile structures supported." },
    { id: "tls",  desc: "TLS Tunnel configuration file. Modern authenticated-encryption envelope with versioned build metadata." },
    { id: "npv",  desc: "NapsternetV configuration file. Lightweight encoding wrapping V2Ray/VLess/VMess configurations." },
    { id: "nsh",  desc: "SocksHTTP configuration file. Password-derived encryption with salted key derivation." },
    { id: "vhd",  desc: "V2Ray / Xray tunnel configuration. Encrypted envelope around an outboundBean JSON structure." },
    { id: "dark", desc: "DARK TUNNEL VPN proprietary configuration. Encryption envelope is closed-source; payload cannot be extracted." },
    { id: "ovpn", desc: "OpenVPN plain-text configuration file. No encryption envelope; parser support is limited." },
  ];

  for (const fmt of formats) {
    const meta = formatMeta(fmt.id);
    const decryptable = fmt.id !== "dark" && fmt.id !== "ovpn";
    const encrypted = fmt.id !== "ehi" && fmt.id !== "ovpn";

    const tags = [];
    if (encrypted) {
      tags.push(el("span", { className: "ac-tag warn" }, ["ENCRYPTED"]));
    } else {
      tags.push(el("span", { className: "ac-tag info" }, ["PLAIN"]));
    }
    if (decryptable) {
      tags.push(el("span", { className: "ac-tag ok" }, ["EXTRACTABLE"]));
    } else if (fmt.id === "dark") {
      tags.push(el("span", { className: "ac-tag danger" }, ["NO ACCESS"]));
    } else {
      tags.push(el("span", { className: "ac-tag warn" }, ["STUB"]));
    }

    grid.appendChild(el("div", {
      className: "arsenal-card",
      style: `--card-accent: ${meta.color}`,
    }, [
      el("div", { className: "ac-head" }, [
        el("span", { className: "ac-name", style: `color: ${meta.color}` }, [meta.name]),
        el("span", { className: "ac-ext" }, [meta.exts.join(" / ")]),
      ]),
      el("p", { className: "ac-desc" }, [fmt.desc]),
      el("div", { className: "ac-tags" }, tags),
    ]));
  }
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

const CONSOLE_COMMANDS = {
  help:   "Available: help · status · targets · clear · purge · about",
  status: () => {
    const total = state.configs.length;
    const decoded = state.configs.filter(c => classifyStatus(c) === "decoded").length;
    return `OP: CIPHER_OPS · TARGETS: ${total} · DECODED: ${decoded} · LINK: ESTABLISHED`;
  },
  targets: () => `${state.configs.length} target(s) loaded`,
  clear:   () => { $("#console-body").innerHTML = ""; state.consoleLines = 0; $("#console-line-count").textContent = "0 EVENTS"; return "Console flushed"; },
  purge:   () => { clearAllConfigs(); return "Purging all targets..."; },
  about:   "InjectX // CIPHER_OPS — tactical VPN config inspector. Local-only, no telemetry.",
};

function setupConsoleInput() {
  const input = $("#console-input");
  if (!input) return;

  input.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    const raw = input.value.trim();
    if (!raw) return;
    const cmd = raw.toLowerCase();
    input.value = "";

    logEvent("CMD", `> ${raw}`, "info");

    const handler = CONSOLE_COMMANDS[cmd];
    if (!handler) {
      logEvent("ERR", `Unknown command: ${cmd} (type 'help')`, "err");
      return;
    }
    const out = typeof handler === "function" ? handler() : handler;
    logEvent("OUT", out, "info");
  });

  // Keep cursor visible — focus when clicking anywhere on the input row
  const ciRow = $(".console-input");
  if (ciRow) ciRow.addEventListener("click", () => input.focus());
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

  // Setup
  setupDragDrop();
  renderArsenalView();
  renderArchive();
  setupConsoleInput();

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
      renderTargetGrid();
    });
  });

  // Action buttons
  const openBtn = $("#btn-open-config");
  if (openBtn) openBtn.addEventListener("click", openConfig);

  const clearBtn = $("#btn-clear-all");
  if (clearBtn) clearBtn.addEventListener("click", clearAllConfigs);

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
