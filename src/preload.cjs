'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  selectInputFolder: (last) => ipcRenderer.invoke('select-input-folder', last),
  selectOutputFolder: (last) => ipcRenderer.invoke('select-output-folder', last),
  validateOutputEmpty: (outDir) => ipcRenderer.invoke('validate-output-empty', outDir),
  startProcessing: (payload) => ipcRenderer.invoke('start-processing', payload),
  startPreview: (payload) => ipcRenderer.invoke('start-preview', payload),
  openPreviewWindow: () => ipcRenderer.invoke('open-preview-window'),
  cancelProcessing: () => ipcRenderer.invoke('cancel-processing'),
  revealPath: (filePath) => ipcRenderer.invoke('reveal-path', filePath),
  clearOutputFolder: (outDir) => ipcRenderer.invoke('clear-output-folder', outDir),

  onProgress: (cb) => ipcRenderer.on('progress-update', (_e, data) => cb(data)),
  onFileStart: (cb) => ipcRenderer.on('file-start', (_e, data) => cb(data)),
  onFileDone: (cb) => ipcRenderer.on('file-done', (_e, data) => cb(data)),
  onAllDone: (cb) => ipcRenderer.on('all-done', (_e, data) => cb(data)),
  onBatchStart: (cb) => ipcRenderer.on('batch-start', (_e, data) => cb(data)),
  onError: (cb) => ipcRenderer.on('error', (_e, data) => cb(data)),
  onLog: (cb) => ipcRenderer.on('log', (_e, data) => cb(data)),
  onPhaseEvent: (cb) => ipcRenderer.on('phase-event', (_e, data) => cb(data)),
  onPreviewFileDone: (cb) => ipcRenderer.on('preview-file-done', (_e, data) => cb(data)),
  onPreviewDone: (cb) => ipcRenderer.on('preview-done', (_e, data) => cb(data)),
  onThrottleEvent: (cb) => ipcRenderer.on('throttle-event', (_e, data) => cb(data)),
  onStopped: (cb) => ipcRenderer.on('stopped', (_e, data) => cb(data)),
  onDebugInfo: (cb) => ipcRenderer.on('debug-info', (_e, data) => cb(data)),
});
