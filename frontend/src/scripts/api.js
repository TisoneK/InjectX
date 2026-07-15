/**
 * InjectX — API Client v0.4.0
 *
 * Wraps all window.vpnAPI (Electron IPC) calls for the renderer process.
 * Includes window control methods for the CustomTitleBar.
 */

const API = {
  openFileDialog() {
    return window.vpnAPI.openFileDialog()
      .then(result => result.canceled ? [] : result.filePaths);
  },
  parseConfig(filePath) { return window.vpnAPI.parseConfig(filePath); },
  getConfig(configId) { return window.vpnAPI.getConfig(configId); },
  listConfigs() { return window.vpnAPI.listConfigs(); },
  deleteConfig(configId) { return window.vpnAPI.deleteConfig(configId); },
  exportConfig(configId) { return window.vpnAPI.exportConfig(configId); },
  detectFormat(filePath) { return window.vpnAPI.detectFormat(filePath); },
  getFormats() { return window.vpnAPI.getFormats(); },
  checkHealth() { return window.vpnAPI.checkHealth(); },
  getDecryptTrace(configId) { return window.vpnAPI.getDecryptTrace(configId); },
  getLogs(since = 0) { return window.vpnAPI.getLogs(since); },
  importAssets() { return window.vpnAPI.importAssets(); },
  listAssets() { return window.vpnAPI.listAssets(); },
  onFilesSelected(callback) { window.vpnAPI.onFilesSelected(callback); },

  // Window controls for CustomTitleBar
  windowMinimize() { return window.vpnAPI.windowMinimize(); },
  windowMaximize() { return window.vpnAPI.windowMaximize(); },
  windowClose() { return window.vpnAPI.windowClose(); },
  windowIsMaximized() { return window.vpnAPI.windowIsMaximized(); },
  onWindowStateChanged(callback) { window.vpnAPI.onWindowStateChanged(callback); },
};

window.API = API;
