const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendPort: () => process.env.BACKEND_PORT,
  getBackendInfo: () => ipcRenderer.invoke('get-backend-info'),
})
