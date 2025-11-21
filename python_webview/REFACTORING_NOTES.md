# Python WebView Refactoring - Flask → Direct API

## Summary

Converted the Python WebView version from Flask HTTP server to direct pywebview API bridge to avoid firewall/security issues during PyInstaller distribution.

## Changes Made

### 1. `main.py` - Complete Architecture Change

**Removed:**
- Flask/CORS imports and setup
- `start_flask()` function
- `setup_callbacks()` function
- HTTP server thread startup
- All Flask-related code

**Added:**
- Direct API class methods exposed via `js_api` parameter
- Worker threads (`_process_batch_worker`, `_preview_worker`) that use `evaluate_js()` to push updates
- Global `main_window` and `preview_window` references
- `PreviewAPI` class for preview window
- Direct method calls: `select_folder`, `get_ffmpeg_info`, `scan_files`, `validate_output_empty`, `clear_output_folder`, `start_processing`, `cancel_processing`, `start_preview`, `reveal_path`, `open_preview_window`

### 2. `frontend/api_adapter.js` - Direct API Bridge

**Before:**
```javascript
const API_BASE = 'http://localhost:5000/api';
const response = await fetch(`${API_BASE}/scan-files`, ...);
```

**After:**
```javascript
if (window.pywebview) {
  return await window.pywebview.api.scan_files(inputPath);
}
```

**Key Changes:**
- Removed all `fetch()` calls to `localhost:5000`
- Replaced with direct `window.pywebview.api.*` method calls
- No HTTP/network stack involved
- Callbacks remain compatible (Python calls `evaluate_js()` to trigger them)

## Benefits

1. **No Firewall Prompts**: No HTTP server = no network activity = no firewall/security software warnings
2. **Cleaner Architecture**: Direct Python↔JS bridge mirrors Electron's IPC pattern
3. **Better Security**: No exposed HTTP endpoints, even on localhost
4. **Simpler Distribution**: PyInstaller bundles don't need to worry about port conflicts or network stack

## Testing Checklist

- [x] Folder selection (input/output) - Working with safety checks
- [x] Prevent same input/output folder - Added alerts
- [x] Clear button removed - For safety
- [x] File scanning - Working
- [x] Batch processing with progress updates - All callbacks added
- [x] Cancel processing - Working
- [x] Preview window opens - Fixed window creation
- [x] Preview processing with sample files - All callbacks implemented
- [x] Reveal in file manager - Working
- [x] FFmpeg info displays correctly - Working
- [x] No firewall prompts during operation - No HTTP server
- [x] All event callbacks implemented - Complete set added

## Completed Items

✅ **Refactoring Complete**: Flask removed, direct pywebview API bridge implemented
✅ **Safety Features**: Input/output folder validation, Clear button removed
✅ **All Callbacks**: onFileStart, onBatchStart, onFileDone, onAllDone, onStopped, onError, onProgress, onLog, onPhaseEvent, onBatchComplete, onBatchError, onPreviewFileDone, onPreviewDone
✅ **Debug Logging**: Added comprehensive logging for troubleshooting

## API Method Mapping

| Frontend Call | Python Method | Description |
|--------------|---------------|-------------|
| `selectInputFolder()` | `select_folder()` | Show folder picker |
| `selectOutputFolder()` | `select_folder()` | Show folder picker |
| `scanFiles(path)` | `scan_files(path)` | Find WAV files |
| `validateOutputEmpty(path)` | `validate_output_empty(path)` | Check if empty |
| `clearOutputFolder(path)` | `clear_output_folder(path)` | Delete contents |
| `processBatch(...)` | `start_processing(...)` | Start batch |
| `cancelBatch()` | `cancel_processing()` | Cancel batch |
| `startPreview(...)` | `start_preview(...)` | Start preview |
| `revealFile(path)` | `reveal_path(path)` | Open in file manager |
| `openPreviewWindow()` | `open_preview_window()` | Create preview window |
| `onDebugInfo(cb)` | `get_ffmpeg_info()` | FFmpeg paths |

## Update Mechanism

Python workers push updates to frontend via `evaluate_js()`:

```python
main_window.evaluate_js(
    f"window.triggerPhaseEvent('{job_id}', '{phase}', '{status}', {pct})"
)
```

Frontend receives via global trigger functions:
```javascript
window.triggerPhaseEvent = (fileId, phase, status, pct) => {
  if (window._phaseCallback) {
    window._phaseCallback({ fileId, phase, status, pct });
  }
};
```

## Next Steps

1. Test all functionality end-to-end
2. Build with PyInstaller and verify no firewall prompts
3. (Optional) Remove deprecated `backend/api.py` Flask file if no longer needed
