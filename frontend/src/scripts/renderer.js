/**
 * InjectX — Renderer v0.4.0
 *
 * IR-aware rendering: all views consume the NormalizedConfig IR structure.
 * Crypto Trace View: forensic-grade display of decrypt attempts.
 * Confidence meters: visual representation of decryption confidence.
 * Formats view: complete format/scheme taxonomy browser.
 */

const state = { configs: [], selectedConfig: null, currentView: "home" };

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

/** Safe string helpers */
function safeUpper(val) { return (val != null && typeof val === "string") ? val.toUpperCase() : (val != null ? String(val).toUpperCase() : "UNKNOWN"); }
function safeStr(val) { return val != null ? String(val) : ""; }

function el(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "className") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2).toLowerCase(), v);
    else e.setAttribute(k, v);
  }
  for (const c of children) {
    if (typeof c === "string") e.appendChild(document.createTextNode(c));
    else if (c) e.appendChild(c);
  }
  return e;
}

function showView(viewName) {
  state.currentView = viewName;
  $$(".view").forEach((v) => v.classList.remove("active"));
  const target = $(`#view-${viewName}`);
  if (target) target.classList.add("active");
  $$(".nav-item").forEach((item) => item.classList.remove("active"));
  const navItem = $(`.nav-item[data-view="${viewName}"]`);
  if (navItem) navItem.classList.add("active");
}


// ── UI Components ──────────────────────────────────────────────────────────────

function createConfidenceMeter(confidence) {
  const pct = Math.round(confidence * 100);
  let colorClass = "confidence-low";
  if (pct >= 80) colorClass = "confidence-high";
  else if (pct >= 50) colorClass = "confidence-medium";

  return el("div", { className: "confidence-meter" }, [
    el("div", { className: "confidence-bar" }, [
      el("div", { className: `confidence-fill ${colorClass}`, style: `width: ${pct}%` }),
    ]),
    el("span", { className: "confidence-label" }, [`${pct}%`]),
  ]);
}

function createDecryptStatusBadge(status) {
  const map = {
    success: { label: "Decrypted", css: "decrypt-success" },
    partial: { label: "Partial", css: "decrypt-partial" },
    failed: { label: "Failed", css: "decrypt-failed" },
    not_encrypted: { label: "Plain Text", css: "decrypt-plain" },
    no_decryptor: { label: "No Decryptor", css: "decrypt-nodc" },
  };
  const info = map[status] || { label: status, css: "decrypt-unknown" };
  return el("span", { className: `decrypt-badge ${info.css}` }, [info.label]);
}

function createSchemeBadge(scheme) {
  if (!scheme || scheme === "none" || scheme === "unsupported") return null;
  return el("span", { className: "scheme-badge" }, [`Scheme ${scheme}`]);
}


// ── Crypto Trace View ──────────────────────────────────────────────────────────

function createCryptoTraceView(trace) {
  if (!trace) return null;

  const attempts = trace.attempts || [];
  const winner = trace.winning_scheme;
  const totalMs = trace.total_elapsed_ms;

  const container = el("div", { className: "trace-panel" }, [
    el("div", { className: "trace-header" }, [
      el("h3", {}, ["Crypto Trace View"]),
      el("div", { className: "trace-summary" }, [
        el("span", { className: "trace-stat" }, [`${attempts.length} attempt${attempts.length !== 1 ? "s" : ""}`]),
        el("span", { className: "trace-stat" }, [`${totalMs.toFixed(1)}ms total`]),
        winner
          ? el("span", { className: "trace-winner" }, [`Winner: Scheme ${winner} (${trace.winning_key_label || "unknown key"})`])
          : el("span", { className: "trace-no-winner" }, ["No successful decryption"]),
      ]),
    ]),
  ]);

  if (attempts.length === 0) {
    container.appendChild(el("div", { className: "trace-empty" }, ["No decryption attempts recorded."]));
    return container;
  }

  const timeline = el("div", { className: "trace-timeline" });

  for (const attempt of attempts) {
    const isSuccess = attempt.result === "success";
    const isFail = attempt.result === "fail";
    const isError = attempt.result === "error";

    let resultIcon = "\u2717";
    let resultClass = "attempt-fail";
    if (isSuccess) { resultIcon = "\u2713"; resultClass = "attempt-success"; }
    if (isError) { resultIcon = "!"; resultClass = "attempt-error"; }

    timeline.appendChild(el("div", { className: `trace-attempt ${resultClass}` }, [
      el("div", { className: "attempt-icon" }, [resultIcon]),
      el("div", { className: "attempt-details" }, [
        el("div", { className: "attempt-top" }, [
          el("span", { className: "attempt-scheme" }, [`Scheme ${attempt.scheme}`]),
          attempt.key_label ? el("span", { className: "attempt-key" }, [`key: ${_truncateKey(attempt.key_label)}`]) : null,
          el("span", { className: "attempt-result-tag" }, [attempt.result]),
        ]),
        el("div", { className: "attempt-meta" }, [
          isSuccess ? createConfidenceMeter(attempt.confidence) : null,
          el("span", { className: "attempt-time" }, [`${attempt.elapsed_ms.toFixed(1)}ms`]),
          isError && attempt.error_message ? el("span", { className: "attempt-error-msg" }, [attempt.error_message]) : null,
        ]),
      ]),
    ]));
  }

  container.appendChild(timeline);
  return container;
}

function _truncateKey(keyLabel) {
  if (!keyLabel) return "";
  if (keyLabel.length <= 30) return keyLabel;
  return keyLabel.substring(0, 20) + "..." + keyLabel.substring(keyLabel.length - 6);
}


// ── Config List ────────────────────────────────────────────────────────────────

async function loadConfigs() {
  try {
    const result = await API.listConfigs();
    state.configs = result.configs || [];
    renderConfigList();
    updateConfigCountBadge();
  } catch (err) {
    showToast("Failed to load configs: " + err.message, "error");
  }
}

function updateConfigCountBadge() {
  const badge = $("#config-count-badge");
  if (!badge) return;
  if (state.configs.length > 0) {
    badge.textContent = state.configs.length;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}

function renderConfigList() {
  const container = $("#config-list");
  if (!container) return;
  container.innerHTML = "";

  if (state.configs.length === 0) {
    container.appendChild(el("div", { className: "empty-state" }, [
      el("div", { className: "empty-visual" }, [
        el("div", { className: "empty-shield" }, [
          el("svg", { viewBox: "0 0 48 48", fill: "none", stroke: "currentColor", "stroke-width": "1.5", "stroke-linecap": "round", "stroke-linejoin": "round" }, [
            el("path", { d: "M24 4L6 12v12c0 11.1 7.7 21.5 18 24 10.3-2.5 18-12.9 18-24V12L24 4z" }),
            el("path", { d: "M18 24l4 4 8-8", "stroke-width": "2" }),
          ]),
        ]),
      ]),
      el("p", { className: "empty-title" }, ["No configs loaded yet"]),
      el("p", { className: "empty-hint" }, ['Click ', el("strong", {}, ["Open Config"]), ' or drag and drop VPN config files here']),
      el("div", { className: "empty-formats" }, [
        ".hc", ".ehi", ".hat", ".tls", ".npv4", ".nsh", ".vhd", ".dark"
      ].map(ext => el("span", { className: "ef-chip" }, [ext]))),
    ]));
    return;
  }

  for (const config of state.configs) {
    const decryptBadge = config.decryption_status
      ? createDecryptStatusBadge(config.decryption_status)
      : (config.encrypted ? el("span", { className: "badge-encrypted" }, ["Encrypted"]) : null);

    const schemeBadge = config.scheme_used ? createSchemeBadge(config.scheme_used) : null;

    container.appendChild(el("div", { className: "config-card", onClick: () => showConfigDetail(config.id) }, [
      el("div", { className: "config-card-header" }, [
        el("span", { className: `format-badge format-${config.format || "unknown"}` }, [safeUpper(config.format)]),
        decryptBadge,
        schemeBadge,
        el("span", { className: "config-filename" }, [config.filename]),
      ]),
      el("div", { className: "config-card-actions" }, [
        el("button", { className: "btn-icon btn-delete", title: "Delete", onClick: (e) => { e.stopPropagation(); deleteConfig(config.id); } }, ["\u2715"]),
      ]),
    ]));
  }
}


// ── Config Detail ──────────────────────────────────────────────────────────────

async function showConfigDetail(configId) {
  try {
    const result = await API.getConfig(configId);
    if (result.error) { showToast(result.error, "error"); return; }
    state.selectedConfig = result;
    renderConfigDetail(result);
    showView("config-detail");
  } catch (err) {
    showToast("Failed to load config: " + err.message, "error");
  }
}

function renderConfigDetail(config) {
  const container = $("#config-detail-content");
  if (!container) return;
  container.innerHTML = "";

  // ── Header ───────────────────────────────────────────────────────────────
  const badges = [
    el("span", { className: `format-badge format-${config.format || "unknown"}` }, [safeUpper(config.format)]),
  ];

  if (config.encrypted) badges.push(createDecryptStatusBadge(config.decryption_status));
  if (config.scheme_used && config.scheme_used !== "none") badges.push(createSchemeBadge(config.scheme_used));
  if (config.confidence > 0) {
    badges.push(el("span", { className: "confidence-inline" }, [`Confidence: ${Math.round(config.confidence * 100)}%`]));
  }
  badges.push(el("span", { className: "ir-version-badge" }, [`IR v${config.ir_version || "1.0"}`]));

  container.appendChild(el("div", { className: "detail-header" }, [
    el("div", { className: "detail-title-row" }, [
      ...badges,
      el("h2", { className: "detail-filename" }, [config.filename]),
      el("button", { className: "btn btn-secondary btn-sm btn-back", onClick: () => { showView("home"); state.selectedConfig = null; } }, ["\u2190 Back"]),
    ]),
  ]));

  // ── Status Panels ────────────────────────────────────────────────────────
  if (config.encrypted || config.decryption_status !== "not_encrypted") {
    const status = config.decryption_status;

    if (status === "success") {
      container.appendChild(el("div", { className: "success-panel" }, [
        el("h3", {}, ["Decryption Successful"]),
        el("p", {}, [
          `This config was decrypted using Scheme ${config.scheme_used || "unknown"}.`,
          config.confidence > 0 ? ` Confidence: ${Math.round(config.confidence * 100)}%.` : "",
        ]),
        createConfidenceMeter(config.confidence),
      ]));
    } else if (status === "partial") {
      container.appendChild(el("div", { className: "warning-panel" }, [
        el("h3", {}, ["Partial Decryption"]),
        el("p", {}, ["This config was partially decrypted. Some fields may be obfuscated or missing."]),
        createConfidenceMeter(config.confidence),
      ]));
    } else if (status === "failed") {
      container.appendChild(el("div", { className: "error-panel" }, [
        el("h3", {}, ["Decryption Failed"]),
        el("p", {}, [
          "All known keys and schemes were tried but none produced a valid result. ",
          "This config may use a newer encryption key or a format not yet supported.",
        ]),
      ]));
    } else if (status === "no_decryptor") {
      container.appendChild(el("div", { className: "warning-panel" }, [
        el("h3", {}, ["No Decryptor Available"]),
        el("p", {}, [
          "This format uses proprietary encryption with no public decryptor. ",
          "Only file metadata is shown.",
        ]),
      ]));
    }
  }

  // ── Warnings ─────────────────────────────────────────────────────────────
  if (config.warnings && config.warnings.length > 0) {
    container.appendChild(el("div", { className: "warning-panel" }, [
      el("h3", {}, ["Warnings"]),
      ...config.warnings.map((w) => el("p", {}, [w])),
    ]));
  }

  // ── Errors ───────────────────────────────────────────────────────────────
  if (config.errors && config.errors.length > 0) {
    container.appendChild(el("div", { className: "error-panel" }, [
      el("h3", {}, ["Parse Errors"]),
      ...config.errors.map((err) => el("div", { className: "error-item" }, [err])),
    ]));
  }

  // ── Config Data (IR-based) ───────────────────────────────────────────────
  if (config.config) {
    const d = config.config;

    // Essential fields table
    const essentialFields = [
      { key: "host", label: "Host / Server" }, { key: "port", label: "Port" },
      { key: "protocol", label: "Protocol" }, { key: "sni", label: "SNI" },
      { key: "bug_host", label: "Bug Host" }, { key: "ssh_server", label: "SSH Server" },
      { key: "ssh_port", label: "SSH Port" }, { key: "ssh_user", label: "SSH Username" },
      { key: "ssh_pass", label: "SSH Password", mask: true },
      { key: "proxy_host", label: "Proxy Host" }, { key: "proxy_port", label: "Proxy Port" },
      { key: "dns", label: "DNS Server" }, { key: "remote_dns", label: "Remote DNS" },
      { key: "connection_type", label: "Connection Type" }, { key: "tunnel_type", label: "Tunnel Type" },
      { key: "tunnel_mode", label: "Tunnel Mode" }, { key: "inject_type", label: "Inject Type" },
      { key: "ssl_enabled", label: "SSL Enabled" },
    ];

    const values = essentialFields.filter((f) => d[f.key] !== null && d[f.key] !== undefined);

    if (values.length > 0) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("h3", {}, ["Essential Settings"]),
        el("table", { className: "config-table" }, [
          el("thead", {}, [el("tr", {}, [el("th", {}, ["Field"]), el("th", {}, ["Value"])])]),
          el("tbody", {}, values.map((f) => el("tr", {}, [
            el("td", { className: "field-label" }, [f.label]),
            el("td", { className: "field-value" }, [
              f.mask && String(d[f.key]).length > 3
                ? String(d[f.key]).substring(0, 3) + "***"
                : String(d[f.key]),
            ]),
          ]))),
        ]),
      ]));
    }

    // Payload
    if (d.payload) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("h3", {}, ["HTTP Payload"]),
        el("pre", { className: "payload-block" }, [d.payload]),
      ]));
    }

    // Parsed payload
    if (d.payload_parsed && d.payload_parsed.length > 0) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("h3", {}, ["Parsed Payload Structure"]),
        el("pre", { className: "payload-block" }, [JSON.stringify(d.payload_parsed, null, 2)]),
      ]));
    }

    // Custom headers
    if (d.custom_headers && Object.keys(d.custom_headers).length > 0) {
      container.appendChild(el("div", { className: "detail-section" }, [
        el("h3", {}, ["Custom Headers"]),
        el("pre", { className: "payload-block" }, [JSON.stringify(d.custom_headers, null, 2)]),
      ]));
    }

    // Protocol-specific configs
    for (const [key, label] of [
      ["v2ray", "V2Ray Config"], ["vmess_config", "VMess Config"],
      ["vless_config", "VLess Config"], ["websocket", "WebSocket Config"],
      ["xray", "Xray Config"], ["hysteria", "Hysteria Config"],
      ["shadowsocks", "Shadowsocks Config"], ["wireguard", "WireGuard Config"],
    ]) {
      if (d[key] && typeof d[key] === "object" && Object.keys(d[key]).length > 0) {
        container.appendChild(el("div", { className: "detail-section" }, [
          el("h3", {}, [label]),
          el("pre", { className: "payload-block" }, [JSON.stringify(d[key], null, 2)]),
        ]));
      }
    }

    // Raw JSON toggle
    container.appendChild(el("div", { className: "detail-section" }, [
      el("button", { className: "btn btn-secondary btn-sm", onClick: () => { const e = container.querySelector(".raw-json-block"); if (e) e.classList.toggle("hidden"); } }, ["Toggle Raw JSON"]),
      el("pre", { className: "payload-block raw-json-block hidden" }, [JSON.stringify(d, null, 2)]),
    ]));
  } else {
    container.appendChild(el("div", { className: "empty-state" }, [
      el("p", {}, ["No parsed data available for this config"]),
    ]));
  }

  // ── Crypto Trace ─────────────────────────────────────────────────────────
  if (config.decrypt_trace) {
    const traceView = createCryptoTraceView(config.decrypt_trace);
    if (traceView) container.appendChild(traceView);
  }

  // ── Actions ─────────────────────────────────────────────────────────────
  container.appendChild(el("div", { className: "detail-actions" }, [
    el("button", { className: "btn btn-primary", onClick: () => exportConfig(config.id) }, ["Export Normalized JSON"]),
  ]));
}


// ── Formats View ───────────────────────────────────────────────────────────────

function renderFormatsView() {
  const grid = $("#formats-grid");
  if (!grid) return;
  grid.innerHTML = "";

  const formats = [
    {
      id: "ehi", name: "HTTP Injector", ext: ".ehi",
      color: "var(--c-ehi)", encrypted: false, decryptable: true,
      schemes: ["B1"],
      desc: "ZIP archive with JSON config. May be locked/obfuscated with 2-stage AES-CBC decryption + field-level XOR deobfuscation using custom base64 charset and configSalt."
    },
    {
      id: "hc", name: "HTTP Custom", ext: ".hc",
      color: "var(--c-hc)", encrypted: true, decryptable: true,
      schemes: ["A1", "A2", "A3", "A4"],
      desc: "Encrypted HCUST format using XOR + AES-128-ECB with SHA1 key derivation. 76+ known ePro keys. v233 uses double-encryption layer. eProxy variant uses pisahConk delimiter."
    },
    {
      id: "hat", name: "HA Tunnel Plus", ext: ".hat / .ha",
      color: "var(--c-hat)", encrypted: true, decryptable: true,
      schemes: ["E1"],
      desc: "AES-128-ECB encrypted JSON with base64-encoded keys. Three known structures: profile (legacy), profilev4 (Pro), and configuration (ShellTun fork)."
    },
    {
      id: "tls", name: "TLS Tunnel", ext: ".tls",
      color: "var(--c-tls)", encrypted: true, decryptable: true,
      schemes: ["F1"],
      desc: "AES-256-GCM with structured build_number:base64_payload format. IV + ciphertext + MAC architecture. Colon-separated fields with base64-encoded subfields."
    },
    {
      id: "npv", name: "NapsternetV", ext: ".npv4 / .inpv",
      color: "var(--c-npv)", encrypted: true, decryptable: true,
      schemes: ["C1"],
      desc: "Subtraction cipher (NOT XOR) with cycling key. Key derived from ln(2) constant. Decrypted content is JSON with configType-based field extraction for V2Ray/VLess/VMess."
    },
    {
      id: "nsh", name: "SocksHTTP", ext: ".nsh",
      color: "var(--c-nsh)", encrypted: true, decryptable: true,
      schemes: ["D1"],
      desc: "AES-128-GCM with PBKDF2-HMAC-SHA256 key derivation (1000 iterations). Dot-separated salt.iv.ciphertext_mac format. Output is XML properties."
    },
    {
      id: "vhd", name: "V2Ray Tunnel", ext: ".vhd",
      color: "var(--c-vhd)", encrypted: true, decryptable: true,
      schemes: ["G1"],
      desc: "AES-128-CBC with raw ASCII key and IV. Base64-encoded ciphertext. Decrypted content is JSON with V2Ray/Xray outboundBean structure including streamSettings."
    },
    {
      id: "dark", name: "DARK TUNNEL VPN", ext: ".dark / .drak / .dt",
      color: "var(--c-dark)", encrypted: true, decryptable: false,
      schemes: [],
      desc: "Proprietary encryption with no publicly known decryptor. Config files cannot be decrypted. Only file metadata and basic detection is available."
    },
  ];

  for (const fmt of formats) {
    const tags = [];
    if (fmt.encrypted) tags.push(el("span", { className: "format-tag tag-encrypted" }, ["Encrypted"]));
    else tags.push(el("span", { className: "format-tag tag-plain" }, ["Plain"]));
    if (fmt.decryptable) tags.push(el("span", { className: "format-tag tag-decryptable" }, ["Decryptable"]));
    else tags.push(el("span", { className: "format-tag tag-no-decryptor" }, ["No Decryptor"]));

    const schemesEl = fmt.schemes.length > 0
      ? el("div", { className: "format-schemes" },
          fmt.schemes.map(s => el("span", { className: "scheme-chip" }, [s])))
      : null;

    grid.appendChild(el("div", { className: "format-card", style: `--card-accent: ${fmt.color}` }, [
      el("div", { className: "format-card-header" }, [
        el("span", { className: "format-card-name", style: `color: ${fmt.color}` }, [fmt.name]),
        el("span", { className: "format-card-ext" }, [fmt.ext]),
      ]),
      el("p", { className: "format-card-desc" }, [fmt.desc]),
      el("div", { className: "format-card-meta" }, tags),
      schemesEl,
    ]));
  }
}


// ── File Operations ────────────────────────────────────────────────────────────

async function openConfig() {
  try {
    const filePaths = await API.openFileDialog();
    if (filePaths.length === 0) return;
    for (const filePath of filePaths) {
      const result = await API.parseConfig(filePath);
      if (result.error) {
        showToast("Error parsing " + filePath + ": " + result.error, "error");
      } else {
        const statusLabel = result.decryption_status === "success" ? "decrypted"
          : result.decryption_status === "partial" ? "partially decrypted"
          : result.encrypted ? "encrypted" : "";
        const schemeLabel = result.scheme_used && result.scheme_used !== "none" ? ` [${result.scheme_used}]` : "";
        showToast(`Parsed ${result.filename} (${safeUpper(result.format)}${statusLabel ? " " + statusLabel : ""}${schemeLabel})`, "success");
      }
    }
    await loadConfigs();
  } catch (err) {
    showToast("Failed to open config: " + err.message, "error");
  }
}

async function deleteConfig(configId) {
  try {
    await API.deleteConfig(configId);
    showToast("Config deleted", "success");
    if (state.selectedConfig && state.selectedConfig.id === configId) {
      state.selectedConfig = null;
      showView("home");
    }
    await loadConfigs();
  } catch (err) {
    showToast("Failed to delete: " + err.message, "error");
  }
}

async function exportConfig(configId) {
  try {
    const result = await API.exportConfig(configId);
    if (result.error) { showToast(result.error, "error"); return; }
    const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "injectx-" + configId + "-normalized.json"; a.click();
    URL.revokeObjectURL(url);
    showToast("Config exported", "success");
  } catch (err) {
    showToast("Export failed: " + err.message, "error");
  }
}

async function clearAllConfigs() {
  for (const config of state.configs) {
    try { await API.deleteConfig(config.id); } catch (e) { /* ignore */ }
  }
  state.configs = [];
  state.selectedConfig = null;
  renderConfigList();
  updateConfigCountBadge();
  showToast("All configs cleared", "success");
}


// ── Drag & Drop ────────────────────────────────────────────────────────────────

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
    showToast("Drag and drop: use the Open Config button instead (path access restricted in Electron)", "info");
  });
}


// ── Toast ──────────────────────────────────────────────────────────────────────

function showToast(message, type = "info") {
  const container = $("#toast-container");
  if (!container) return;
  const toast = el("div", { className: `toast toast-${type}` }, [
    el("span", { className: "toast-message" }, [message]),
    el("button", { className: "toast-close", onClick: () => toast.remove() }, ["\u2715"]),
  ]);
  container.appendChild(toast);
  setTimeout(() => {
    if (toast.parentNode) {
      toast.classList.add("toast-fade");
      setTimeout(() => toast.remove(), 250);
    }
  }, 4000);
}


// ── Init ───────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  console.log("[Renderer] Initializing InjectX v0.4.0...");

  // Check backend health
  try {
    const health = await API.checkHealth();
    if (health.status === "ok") {
      const el1 = $("#backend-status");
      if (el1) { el1.querySelector(".status-text").textContent = `Online (IR v${health.ir_version || "1.0"})`; el1.className = "backend-status connected"; }
      const el2 = $("#settings-backend-status");
      if (el2) { el2.textContent = "Connected"; el2.className = "status-badge status-connected"; }
    }
  } catch (err) {
    const el1 = $("#backend-status");
    if (el1) { el1.querySelector(".status-text").textContent = "Backend Offline"; el1.className = "backend-status disconnected"; }
    const el2 = $("#settings-backend-status");
    if (el2) { el2.textContent = "Disconnected"; el2.className = "status-badge status-disconnected"; }
  }

  await loadConfigs();
  setupDragDrop();
  renderFormatsView();

  // Navigation clicks
  $$(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      const view = item.dataset.view;
      if (view) showView(view);
    });
  });

  // Open Config button
  const openBtn = $("#btn-open-config");
  if (openBtn) openBtn.addEventListener("click", openConfig);

  // Clear All button
  const clearBtn = $("#btn-clear-all");
  if (clearBtn) clearBtn.addEventListener("click", clearAllConfigs);

  // Files selected from Electron menu
  API.onFilesSelected(async (filePaths) => {
    for (const filePath of filePaths) {
      const result = await API.parseConfig(filePath);
      if (result.error) {
        showToast("Error: " + result.error, "error");
      } else {
        const encLabel = result.encrypted ? " [encrypted]" : "";
        showToast("Parsed " + result.filename + " (" + safeUpper(result.format) + encLabel + ")", "success");
      }
    }
    await loadConfigs();
  });

  // ── CustomTitleBar window controls ──────────────────────────────────────────
  const btnMinimize = $("#btn-minimize");
  const btnMaximize = $("#btn-maximize");
  const btnClose = $("#btn-close");
  const iconMaximize = $("#icon-maximize");
  const iconRestore = $("#icon-restore");

  if (btnMinimize) btnMinimize.addEventListener("click", () => API.windowMinimize());
  if (btnMaximize) btnMaximize.addEventListener("click", () => API.windowMaximize());
  if (btnClose) btnClose.addEventListener("click", () => API.windowClose());

  // Sync maximize/restore icon with current window state
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

  console.log("[Renderer] Ready");
});
