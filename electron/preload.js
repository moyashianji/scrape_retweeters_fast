const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendPort: () => process.env.BACKEND_PORT,
})
