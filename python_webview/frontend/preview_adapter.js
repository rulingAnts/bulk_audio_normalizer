/**
 * API adapter for preview window in Python WebView version.
 */

// Wait for pywebview to be ready
function waitForPywebview() {
  return new Promise((resolve) => {
    const checkReady = () => {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.get_audio_file) {
        console.log('pywebview.api ready with methods:', Object.keys(window.pywebview.api));
        resolve();
      } else {
        console.log('Waiting for pywebview.api... Current state:', {
          hasWindow: !!window.pywebview,
          hasApi: !!(window.pywebview && window.pywebview.api),
          apiKeys: window.pywebview && window.pywebview.api ? Object.keys(window.pywebview.api) : []
        });
        setTimeout(checkReady, 100);
      }
    };
    checkReady();
  });
}

window.api = {
  /**
   * Get audio file as data URL (for loading in webview)
   */
  getAudioFile: async (filePath) => {
    await waitForPywebview();
    if (window.pywebview && window.pywebview.api && window.pywebview.api.get_audio_file) {
      return await window.pywebview.api.get_audio_file(filePath);
    }
    console.error('pywebview.api.get_audio_file not available');
    return null;
  },

  /**
   * Reveal file/folder in file manager
   */
  revealPath: async (filePath) => {
    await waitForPywebview();
    if (window.pywebview && window.pywebview.api && window.pywebview.api.reveal_path) {
      await window.pywebview.api.reveal_path(filePath);
    }
  },

  /**
   * Event listeners for preview updates
   */
  onPreviewFileDone: (callback) => {
    window._previewFileCallback = callback;
  },

  onPreviewDone: (callback) => {
    window._previewDoneCallback = callback;
  }
};

// Helper functions called from Python
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

console.log('Preview API adapter loaded for Python WebView version');
