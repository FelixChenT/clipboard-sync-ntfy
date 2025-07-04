const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Sync control
  startSync: (config) => ipcRenderer.invoke('start-sync', config),
  stopSync: () => ipcRenderer.invoke('stop-sync'),
  getSyncStatus: () => ipcRenderer.invoke('get-sync-status'),

  // Configuration
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (config) => ipcRenderer.invoke('save-config', config),

  // Event listeners
  onSyncStatusChanged: (callback) => {
    ipcRenderer.on('sync-status-changed', callback);
    // Return a function to remove the listener
    return () => ipcRenderer.removeListener('sync-status-changed', callback);
  },

  onPythonOutput: (callback) => {
    ipcRenderer.on('python-output', callback);
    // Return a function to remove the listener
    return () => ipcRenderer.removeListener('python-output', callback);
  },

  // Utility
  openExternal: (url) => ipcRenderer.invoke('open-external', url)
});
