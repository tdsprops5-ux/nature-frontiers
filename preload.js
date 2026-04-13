const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  startBatchGeneration: (config) => ipcRenderer.invoke('start-batch-generation', config),
  getGenerationStatus: (batchId) => ipcRenderer.invoke('get-generation-status', batchId),
  getAllBatches: () => ipcRenderer.invoke('get-all-batches'),
});
