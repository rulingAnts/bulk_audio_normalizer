/**
 * API adapter for Python WebView version.
 * 
 * Provides direct bridge to Python backend via pywebview's js_api.
 * No HTTP/network stack - all calls go through window.pywebview.api.
 */

window.api = {
  /**
   * Select input folder
   */
  selectInputFolder: async (lastPath) => {
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
    if (window.pywebview) {
      return await window.pywebview.api.scan_files(inputPath);
    }
    return [];
  },

  /**
   * Check if output directory is empty
   */
  checkOutputEmpty: async (outputPath) => {
    if (window.pywebview) {
      return await window.pywebview.api.validate_output_empty(outputPath);
    }
    return true;
  },

  /**
   * Validate output directory is empty (alias for compatibility)
   */
  validateOutputEmpty: async (outputPath) => {
    if (window.pywebview) {
      return await window.pywebview.api.validate_output_empty(outputPath);
    }
    return true;
  },

  /**
   * Clear (delete all contents of) output directory
   */
  clearOutputFolder: async (outputPath) => {
    if (window.pywebview) {
      return await window.pywebview.api.clear_output_folder(outputPath);
    }
    return false;
  },

  /**
   * Create output directory (handled automatically by Python backend)
   */
  createOutputDir: async (outputPath) => {
    // Directory creation is handled automatically during processing
    return true;
  },

  /**
   * Start batch processing
   */
  processBatch: async (inputPath, outputPath, settings) => {
    console.log('[API] processBatch called:', { inputPath, outputPath, settings });
    if (window.pywebview) {
      const result = await window.pywebview.api.start_processing(inputPath, outputPath, settings);
      console.log('[API] processBatch result:', result);
      return result.ok;
    }
    return false;
  },
  
  /**
   * Start batch processing (alternate interface)
   */
  startProcessing: async ({ inputDir, outputDir, settings, concurrency }) => {
    console.log('[API] startProcessing called:', { inputDir, outputDir, settings, concurrency });
    if (window.pywebview) {
      const result = await window.pywebview.api.start_processing(inputDir, outputDir, settings);
      console.log('[API] startProcessing result:', result);
      return result;
    }
    return { ok: false, error: 'pywebview not available' };
  },

  /**
   * Cancel batch processing
   */
  cancelBatch: async () => {
    if (window.pywebview) {
      const result = await window.pywebview.api.cancel_processing();
      return result.ok;
    }
    return false;
  },
  
  /**
   * Pause batch processing
   */
  pauseProcessing: async () => {
    console.log('[API] pauseProcessing called');
    if (window.pywebview) {
      const result = await window.pywebview.api.pause_processing();
      console.log('[API] pauseProcessing result:', result);
      return result.ok;
    }
    return false;
  },
  
  /**
   * Resume batch processing
   */
  resumeProcessing: async () => {
    console.log('[API] resumeProcessing called');
    if (window.pywebview) {
      const result = await window.pywebview.api.resume_processing();
      console.log('[API] resumeProcessing result:', result);
      return result.ok;
    }
    return false;
  },
  
  /**
   * Cancel batch processing
   */
  cancelProcessing: async () => {
    console.log('[API] cancelProcessing called');
    if (window.pywebview) {
      const result = await window.pywebview.api.cancel_processing();
      console.log('[API] cancelProcessing result:', result);
      return result.ok;
    }
    return false;
  },

  /**
   * Reveal file in file manager
   */
  revealFile: async (filePath) => {
    if (window.pywebview) {
      return await window.pywebview.api.reveal_path(filePath);
    }
    return false;
  },

  /**
   * Event listeners (callbacks set by frontend, triggered by Python via evaluate_js)
   */
  onFileStart: (callback) => {
    window._fileStartCallback = callback;
  },

  onBatchStart: (callback) => {
    window._batchStartCallback = callback;
  },

  onFileDone: (callback) => {
    window._fileDoneCallback = callback;
  },

  onAllDone: (callback) => {
    window._allDoneCallback = callback;
  },

  onStopped: (callback) => {
    window._stoppedCallback = callback;
  },

  onError: (callback) => {
    window._errorCallback = callback;
  },

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
    if (window.pywebview) {
      window.pywebview.api.get_ffmpeg_info().then(callback).catch(e => {
        console.error('Failed to get FFmpeg info:', e);
      });
    }
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
    if (window.pywebview) {
      return await window.pywebview.api.start_preview(inputDir, settings, sampleSize, concurrency);
    }
    return { ok: false, error: 'pywebview not available' };
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

// Helper functions to trigger callbacks from Python (via evaluate_js)
window.triggerFileStart = (fileId, name) => {
  if (window._fileStartCallback) {
    window._fileStartCallback({ fileId, name });
  }
};

window.triggerBatchStart = (total) => {
  if (window._batchStartCallback) {
    window._batchStartCallback({ total });
  }
};

window.triggerFileDone = (fileId) => {
  if (window._fileDoneCallback) {
    window._fileDoneCallback({ fileId });
  }
};

window.triggerAllDone = () => {
  if (window._allDoneCallback) {
    window._allDoneCallback();
  }
};

window.triggerStopped = () => {
  if (window._stoppedCallback) {
    window._stoppedCallback();
  }
};

window.triggerError = (message) => {
  if (window._errorCallback) {
    window._errorCallback({ message });
  }
};

window.triggerProgress = (fileId, filePct, overallPct, completed, total) => {
  if (window._progressCallback) {
    window._progressCallback({ fileId, filePct, overallPct, completed, total });
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

window.triggerPreviewFile = (original, preview, rel, tmpBase) => {
  if (window._previewFileCallback) {
    window._previewFileCallback({ original, preview, rel, tmpBase });
  }
};

window.triggerPreviewDone = (count, tmpBase) => {
  if (window._previewDoneCallback) {
    window._previewDoneCallback({ count, tmpBase });
  }
};

console.log('API adapter loaded for Python WebView version (direct pywebview.api bridge)');
