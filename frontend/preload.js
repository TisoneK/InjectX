/**
 * Preload Script — Secure context bridge for InjectX v0.4.0
 * Includes window control APIs for the CustomTitleBar.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("vpnAPI", {
  openFileDialog: () => ipcRenderer.invoke("open-file-dialog"),
  parseConfig: (filePath) => ipcRenderer.invoke("parse-config", filePath),
  getConfig: (configId) => ipcRenderer.invoke("get-config", configId),
  listConfigs: () => ipcRenderer.invoke("list-configs"),
  deleteConfig: (configId) => ipcRenderer.invoke("delete-config", configId),
  exportConfig: (configId) => ipcRenderer.invoke("export-config", configId),
  detectFormat: (filePath) => ipcRenderer.invoke("detect-format", filePath),
  getFormats: () => ipcRenderer.invoke("get-formats"),
  checkHealth: () => ipcRenderer.invoke("check-health"),
  getDecryptTrace: (configId) => ipcRenderer.invoke("get-decrypt-trace", configId),
  getLogs: (since) => ipcRenderer.invoke("get-logs", since),
  importAssets: () => ipcRenderer.invoke("import-assets"),
  listAssets: () => ipcRenderer.invoke("list-assets"),
  onFilesSelected: (callback) => { ipcRenderer.on("files-selected", (_event, filePaths) => callback(filePaths)); },

  // Window controls for CustomTitleBar
  windowMinimize: () => ipcRenderer.invoke("window-minimize"),
  windowMaximize: () => ipcRenderer.invoke("window-maximize"),
  windowClose: () => ipcRenderer.invoke("window-close"),
  windowIsMaximized: () => ipcRenderer.invoke("window-is-maximized"),
  onWindowStateChanged: (callback) => { ipcRenderer.on("window-state-changed", (_event, state) => callback(state)); },
});
