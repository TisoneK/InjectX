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

  // SNI Host Hunter — discover + probe SNI bug hosts (all via IPC, ADR-7).
  sni: {
    discover(domain) { return window.vpnAPI.sniDiscover(domain); },
    scan(opts) { return window.vpnAPI.sniScan(opts); },
    stop(jobId) { return window.vpnAPI.sniScanStop(jobId); },
    export(jobId, format) { return window.vpnAPI.sniExport(jobId, format); },
    jobs() { return window.vpnAPI.sniJobs(); },
    job(jobId) { return window.vpnAPI.sniJob(jobId); },
    seedlists() { return window.vpnAPI.sniSeedlists(); },
  },
  isDev() { return window.vpnAPI && window.vpnAPI.isDev ? window.vpnAPI.isDev() : Promise.resolve(false); },
  openFolderDialog() { return window.vpnAPI && window.vpnAPI.openFolderDialog ? window.vpnAPI.openFolderDialog() : Promise.resolve({ canceled: true, folder: null }); },
  listConfigFiles(folder) { return window.vpnAPI && window.vpnAPI.listConfigFiles ? window.vpnAPI.listConfigFiles(folder) : Promise.resolve({ files: [] }); },
  getLastFolder() { return window.vpnAPI && window.vpnAPI.getLastFolder ? window.vpnAPI.getLastFolder() : Promise.resolve(null); },
  setLastFolder(folder) { return window.vpnAPI && window.vpnAPI.setLastFolder ? window.vpnAPI.setLastFolder(folder) : Promise.resolve(); },
  onFilesSelected(callback) { window.vpnAPI.onFilesSelected(callback); },

  // Window controls for CustomTitleBar
  windowMinimize() { return window.vpnAPI.windowMinimize(); },
  windowMaximize() { return window.vpnAPI.windowMaximize(); },
  windowClose() { return window.vpnAPI.windowClose(); },
  windowIsMaximized() { return window.vpnAPI.windowIsMaximized(); },
  onWindowStateChanged(callback) { window.vpnAPI.onWindowStateChanged(callback); },
};

window.API = API;
