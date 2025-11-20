/**
 * API adapter for preview window in Python WebView version.
 */

window.api = {
  /**
   * Reveal file/folder in file manager
   */
  revealPath: async (filePath) => {
    if (window.pywebview) {
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
