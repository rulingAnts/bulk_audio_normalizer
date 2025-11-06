import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('api', {
  selectInputFolder: (last) => ipcRenderer.invoke('select-input-folder', last),
  selectOutputFolder: (last) => ipcRenderer.invoke('select-output-folder', last),
  validateOutputEmpty: (outDir) => ipcRenderer.invoke('validate-output-empty', outDir),
  startProcessing: (payload) => ipcRenderer.invoke('start-processing', payload),
  cancelProcessing: () => ipcRenderer.invoke('cancel-processing'),

  onProgress: (cb) => ipcRenderer.on('progress-update', (_e, data) => cb(data)),
  onFileStart: (cb) => ipcRenderer.on('file-start', (_e, data) => cb(data)),
  onFileDone: (cb) => ipcRenderer.on('file-done', (_e, data) => cb(data)),
  onAllDone: (cb) => ipcRenderer.on('all-done', (_e, data) => cb(data)),
  onError: (cb) => ipcRenderer.on('error', (_e, data) => cb(data)),
  onLog: (cb) => ipcRenderer.on('log', (_e, data) => cb(data)),
});
