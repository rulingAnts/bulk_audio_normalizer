/**
 * API adapter for Python WebView version.
 * 
 * This replaces the Electron IPC bridge (window.api) with REST API calls
 * to the Flask backend.
 */

const API_BASE = 'http://localhost:5000/api';

window.api = {
  /**
   * Select input folder
   */
  selectInputFolder: async (lastPath) => {
    // In WebView, we use pywebview's file dialog
    if (window.pywebview) {
      const result = await window.pywebview.api.select_folder('Select Input Folder');
      return result || null;
    }
    return null;
  },

  /**
   * Select output folder
   */
  selectOutputFolder: async (lastPath) => {
    if (window.pywebview) {
      const result = await window.pywebview.api.select_folder('Select Output Folder');
      return result || null;
    }
    return null;
  },

  /**
   * Scan input directory for WAV files
   */
  scanFiles: async (inputPath) => {
    const response = await fetch(`${API_BASE}/scan-files`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ inputPath })
    });
    const data = await response.json();
    return data.files || [];
  },

  /**
   * Check if output directory is empty
   */
  checkOutputEmpty: async (outputPath) => {
    const response = await fetch(`${API_BASE}/check-output-empty`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputPath })
    });
    const data = await response.json();
    return data.isEmpty;
  },

  /**
   * Create output directory
   */
  createOutputDir: async (outputPath) => {
    const response = await fetch(`${API_BASE}/create-output-dir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outputPath })
    });
    return response.ok;
  },

  /**
   * Start batch processing
   */
  processBatch: async (inputPath, outputPath, settings) => {
    const response = await fetch(`${API_BASE}/process-batch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ inputPath, outputPath, settings })
    });
    return response.ok;
  },

  /**
   * Cancel batch processing
   */
  cancelBatch: async () => {
    const response = await fetch(`${API_BASE}/cancel-batch`, {
      method: 'POST'
    });
    return response.ok;
  },

  /**
   * Reveal file in file manager
   */
  revealFile: async (filePath) => {
    const response = await fetch(`${API_BASE}/reveal-file`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filePath })
    });
    return response.ok;
  },

  /**
   * Event listeners (replaced with polling or WebSocket in production)
   */
  onProgress: (callback) => {
    window._progressCallback = callback;
  },

  onLog: (callback) => {
    window._logCallback = callback;
  },

  onPhaseEvent: (callback) => {
    window._phaseCallback = callback;
  },

  onBatchComplete: (callback) => {
    window._batchCompleteCallback = callback;
  },

  onBatchError: (callback) => {
    window._batchErrorCallback = callback;
  },

  onPreviewFileDone: (callback) => {
    window._previewFileCallback = callback;
  },

  onPreviewDone: (callback) => {
    window._previewDoneCallback = callback;
  },

  onDebugInfo: (callback) => {
    // Get FFmpeg info on load
    fetch(`${API_BASE}/ffmpeg-info`)
      .then(r => r.json())
      .then(info => callback(info))
      .catch(e => console.error('Failed to get FFmpeg info:', e));
  },

  /**
   * Open preview window
   */
  openPreviewWindow: async () => {
    if (window.pywebview) {
      return await window.pywebview.api.open_preview_window();
    }
    return false;
  },

  /**
   * Start preview processing
   */
  startPreview: async ({ inputDir, settings, sampleSize, concurrency }) => {
    const response = await fetch(`${API_BASE}/start-preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        inputPath: inputDir, 
        settings, 
        sampleSize, 
        concurrency 
      })
    });
    return await response.json();
  },

  /**
   * Get settings (stored in localStorage)
   */
  getSettings: async (key) => {
    return localStorage.getItem(key);
  },

  /**
   * Save settings (stored in localStorage)
   */
  saveSettings: async (key, value) => {
    localStorage.setItem(key, value);
    return true;
  }
};

// Helper to trigger callbacks from Python
window.triggerProgress = (fileId, completed, total) => {
  if (window._progressCallback) {
    window._progressCallback({ fileId, completed, total });
  }
};

window.triggerLog = (fileId, phase, line) => {
  if (window._logCallback) {
    window._logCallback({ fileId, phase, line });
  }
};

window.triggerPhaseEvent = (fileId, phase, status, pct) => {
  if (window._phaseCallback) {
    window._phaseCallback({ fileId, phase, status, pct });
  }
};

window.triggerBatchComplete = () => {
  if (window._batchCompleteCallback) {
    window._batchCompleteCallback();
  }
};

window.triggerBatchError = (error) => {
  if (window._batchErrorCallback) {
    window._batchErrorCallback(error);
  }
};

console.log('API adapter loaded for Python WebView version');
