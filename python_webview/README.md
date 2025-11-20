# Bulk Audio Normalizer - Python WebView Version

This is a Python implementation of the Bulk Audio Normalizer using WebView for the UI and Python for the backend.

## Why Python?

The Python version was created to address subprocess management and task kill issues encountered with npm/Electron. Python's `subprocess` module provides more reliable process control and cleanup.

## Features

Same features as the Electron version:
- Peak dBFS or LUFS normalization
- Flexible bit depth (16-bit, 24-bit, or preserve original)
- Auto-trim silence with adjustable parameters
- Batch processing with adaptive throttling
- Preview mode for random sampling
- Responsive UI with progress tracking

## Requirements

- Python 3.8 or higher
- FFmpeg and FFprobe (will use ffmpeg-static binaries from the Electron version)

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Install FFmpeg binaries (if not already available from Electron version):
```bash
cd ..
npm install
```

## Running

```bash
python main.py
```

This will launch the WebView application with the UI from the Electron version, but with Python handling all backend processing.

## Architecture

- **main.py**: Entry point that starts the Flask backend and WebView window
- **backend/api.py**: Flask API endpoints for file operations
- **backend/audio_processor.py**: Core audio processing logic using FFmpeg
- **backend/process_manager.py**: Subprocess management with proper cleanup
- **frontend/**: HTML/CSS/JS UI (recycled from Electron version)

## Differences from Electron Version

1. **Backend**: Python instead of Node.js
2. **UI Framework**: PyWebView instead of Electron
3. **Subprocess Management**: Python's subprocess module with better process tree cleanup
4. **IPC**: REST API instead of Electron IPC
5. **Binary Resolution**: Uses FFmpeg/FFprobe from npm packages or system installation

## Development

The UI files are copied from the Electron version's `src/renderer/` directory. Any UI changes should be made in the Electron version first, then copied here.

## License

Same as parent project: AGPL-3.0-only
