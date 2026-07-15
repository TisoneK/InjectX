/**
 * Electron Main Process for InjectX v0.4.0
 * - Creates the application window
 * - Spawns the Python FastAPI backend as a child process
 * - Handles IPC between renderer and backend
 */

const { app, BrowserWindow, ipcMain, dialog, Menu } = require("electron");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");
const net = require("net");

// Read INJECTX_PORT from the environment with the same default the Python
// backend uses (backend/main.py: `int(os.environ.get("INJECTX_PORT", "8742"))`).
// Before this, the Electron main process hardcoded 8742 even when the user
// had set INJECTX_PORT — the spawned backend would bind to the custom port
// but main.js would keep proxying IPC to 8742, so the renderer's calls
// silently 404'd. Now both sides agree.
const BACKEND_PORT = parseInt(process.env.INJECTX_PORT || "8742", 10);
const BACKEND_HOST = process.env.INJECTX_HOST || "127.0.0.1";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let mainWindow = null;
let backendProcess = null;

// ── File Dialog Filter ────────────────────────────────────────────────────────
//
// Single source of truth for the config file extensions shown in the open-file
// dialog. MUST stay in sync with ALLOWED_EXTENSIONS in backend/main.py — the
// dialog is the user-facing filter; the backend's allowlist is the security
// boundary. Both lists must accept the same extensions or a user who picks a
// file from the dialog could still get a 400 from /parse.
//
// Earlier versions had this list duplicated inline in two places (handleOpenFile
// and the ipcMain.handle("open-file-dialog") handler) and were missing .ovpn
// and .conf — the dialog would hide OpenVPN/CONF files even though the backend
// accepts them. Now one constant feeds both call sites.
const CONFIG_EXTENSIONS = [
  "ehi", "hc", "hat", "ha", "dark", "drak", "dt", "darktunnel",
  "tls", "npv4", "inpv", "npv", "nsh", "vhd", "ovpn", "conf", "ziv",
];

function configOpenDialogOptions() {
  return {
    title: "Select Config File",
    filters: [
      { name: "VPN Config Files", extensions: CONFIG_EXTENSIONS },
      { name: "All Files", extensions: ["*"] },
    ],
    properties: ["openFile", "multiSelections"],
  };
}

// ── Backend Management ───────────────────────────────────────────────────────

function getPythonPath() {
  const venvPython = path.join(__dirname, "..", "backend", ".venv", "Scripts", "python.exe");
  const venvPythonLinux = path.join(__dirname, "..", "backend", ".venv", "bin", "python");
  const fs = require("fs");
  if (fs.existsSync(venvPython)) return venvPython;
  if (fs.existsSync(venvPythonLinux)) return venvPythonLinux;
  return "python";
}

function startBackend() {
  const pythonPath = getPythonPath();
  const mainPy = path.join(__dirname, "..", "backend", "main.py");
  console.log(`[Main] Starting backend: ${pythonPath} ${mainPy}`);

  backendProcess = spawn(pythonPath, [mainPy], {
    cwd: path.join(__dirname, "..", "backend"),
    stdio: ["pipe", "pipe", "pipe"],
  });

  backendProcess.stdout.on("data", (data) => console.log(`[Backend] ${data.toString().trim()}`));
  backendProcess.stderr.on("data", (data) => console.error(`[Backend Error] ${data.toString().trim()}`));
  backendProcess.on("close", (code) => { console.log(`[Backend] Process exited with code ${code}`); backendProcess = null; });
}

function stopBackend() {
  if (backendProcess) { backendProcess.kill(); backendProcess = null; }
}

function waitForBackend(maxRetries = 20, interval = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    function check() {
      const socket = new net.Socket();
      socket.setTimeout(1000);
      socket.on("connect", () => { socket.destroy(); resolve(true); });
      socket.on("error", () => { socket.destroy(); attempts++; if (attempts >= maxRetries) reject(new Error("Backend did not start")); else setTimeout(check, interval); });
      socket.on("timeout", () => { socket.destroy(); attempts++; if (attempts >= maxRetries) reject(new Error("Backend did not start")); else setTimeout(check, interval); });
      socket.connect(BACKEND_PORT, BACKEND_HOST);
    }
    check();
  });
}

// ── Window Creation ───────────────────────────────────────────────────────────

// Resolve the app icon path. The icon lives at assets/icons/icon.png
// (and icon.ico for Windows). We resolve relative to the project root
// (two levels up from frontend/main.js: frontend/ → project root).
const PROJECT_ROOT = path.join(__dirname, "..");
const ICON_PNG = path.join(PROJECT_ROOT, "assets", "icons", "icon.png");
const ICON_ICO = path.join(PROJECT_ROOT, "assets", "icons", "icon.ico");

function getIconPath() {
  // Windows prefers .ico; macOS/Linux prefer .png
  const isWindows = os.platform() === "win32";
  if (isWindows) {
    const fs = require("fs");
    if (fs.existsSync(ICON_ICO)) return ICON_ICO;
  }
  return ICON_PNG;
}

function createWindow() {
  const isWindows = os.platform() === "win32";
  const isMac = os.platform() === "darwin";

  mainWindow = new BrowserWindow({
    width: 1100, height: 750, minWidth: 800, minHeight: 600,
    title: "InjectX",
    frame: false,
    titleBarStyle: isMac ? "hidden" : undefined,
    trafficLightPosition: isMac ? { x: 12, y: 12 } : undefined,
    icon: getIconPath(),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true, nodeIntegration: false, sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));
  if (process.env.NODE_ENV === "development") mainWindow.webContents.openDevTools();
  mainWindow.on("closed", () => { mainWindow = null; });

  // Set the dock/taskbar icon (macOS dock, Linux taskbar).
  // On Windows the BrowserWindow `icon` option above handles this.
  if (isMac && app.dock) {
    try { app.dock.setIcon(ICON_PNG); } catch (e) { /* ignore */ }
  }

  const menuTemplate = [
    { label: "File", submenu: [
      { label: "Open Config File", accelerator: "CmdOrCtrl+O", click: () => handleOpenFile() },
      { type: "separator" }, { role: "quit" },
    ]},
    { label: "View", submenu: [
      { role: "reload" }, { role: "forceReload" }, { role: "toggleDevTools" },
      { type: "separator" }, { role: "resetZoom" }, { role: "zoomIn" }, { role: "zoomOut" },
    ]},
  ];
  Menu.setApplicationMenu(Menu.buildFromTemplate(menuTemplate));
}

async function handleOpenFile() {
  const result = await dialog.showOpenDialog(mainWindow, configOpenDialogOptions());
  if (!result.canceled && result.filePaths.length > 0) mainWindow.webContents.send("files-selected", result.filePaths);
}

// ── IPC Handlers ──────────────────────────────────────────────────────────────

function setupIPC() {
  ipcMain.handle("open-file-dialog", async () => {
    const result = await dialog.showOpenDialog(mainWindow, configOpenDialogOptions());
    return result.canceled ? { canceled: true, filePaths: [] } : { canceled: false, filePaths: result.filePaths };
  });

  const proxyGet = (endpoint) => async () => { try { return (await fetch(`${BACKEND_URL}${endpoint}`)).json(); } catch (err) { return { error: err.message }; } };

  ipcMain.handle("parse-config", async (_e, filePath) => { try { return (await fetch(`${BACKEND_URL}/api/config/parse?filepath=${encodeURIComponent(filePath)}`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("get-config", async (_e, configId) => { try { return (await fetch(`${BACKEND_URL}/api/config/${configId}`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("list-configs", proxyGet("/api/configs"));
  ipcMain.handle("delete-config", async (_e, configId) => { try { return (await fetch(`${BACKEND_URL}/api/config/${configId}`, { method: "DELETE" })).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("export-config", async (_e, configId) => { try { return (await fetch(`${BACKEND_URL}/api/config/export?config_id=${configId}`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("detect-format", async (_e, filePath) => { try { return (await fetch(`${BACKEND_URL}/api/config/detect?filepath=${encodeURIComponent(filePath)}`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("get-formats", proxyGet("/api/formats"));
  ipcMain.handle("check-health", proxyGet("/api/health"));
  ipcMain.handle("get-decrypt-trace", async (_e, configId) => { try { return (await fetch(`${BACKEND_URL}/api/config/${configId}/trace`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("get-logs", async (_e, since = 0) => { try { return (await fetch(`${BACKEND_URL}/api/logs?since=${since}`)).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("import-assets", async () => { try { return (await fetch(`${BACKEND_URL}/api/configs/import-assets`, { method: "POST" })).json(); } catch (err) { return { error: err.message }; } });
  ipcMain.handle("list-assets", proxyGet("/api/configs/assets"));

  // ── Window Control IPC ─────────────────────────────────────────────────────
  ipcMain.handle("window-minimize", () => { if (mainWindow) mainWindow.minimize(); });
  ipcMain.handle("window-maximize", () => { if (mainWindow) { mainWindow.isMaximized() ? mainWindow.unmaximize() : mainWindow.maximize(); } });
  ipcMain.handle("window-close", () => { if (mainWindow) mainWindow.close(); });
  ipcMain.handle("window-is-maximized", () => mainWindow ? mainWindow.isMaximized() : false);

  mainWindow.on("maximize", () => { mainWindow.webContents.send("window-state-changed", "maximized"); });
  mainWindow.on("unmaximize", () => { mainWindow.webContents.send("window-state-changed", "normal"); });
}

// ── App Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  startBackend();
  try { await waitForBackend(); console.log("[Main] Backend is ready"); } catch (err) { console.error("[Main] Backend failed:", err.message); }
  createWindow();
  setupIPC();
});

app.on("window-all-closed", () => { stopBackend(); app.quit(); });
app.on("before-quit", () => { stopBackend(); });
app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
