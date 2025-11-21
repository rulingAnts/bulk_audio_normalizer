# Bulk Audio Normalizer - Python WebView Version

This is a Python implementation of the Bulk Audio Normalizer using WebView for the UI and Python for the backend. It can be run as a Python script or built into standalone executables for Windows and macOS.

## Why Python?

The Python version was created to address subprocess management and task kill issues encountered with npm/Electron. Python's `subprocess` module provides more reliable process control and cleanup.

## Features

Same features as the Electron version:
- Peak dBFS or LUFS normalization
- Flexible bit depth (16-bit, 24-bit, or preserve original)
- Auto-trim silence with adjustable parameters
- Batch processing with pause/resume capability
- Preview mode with waveform visualization (A/B comparison)
- Cancel processing with output cleanup
- Responsive UI with progress tracking

## Requirements

### Running from Source
- Python 3.8 or higher
- FFmpeg and FFprobe binaries

### Building Executables
- PyInstaller 6.0+
- macOS: `create-dmg` (optional, for DMG creation)
- Windows: No additional tools needed

## Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Setup FFmpeg binaries:
```bash
python3 setup_ffmpeg.py  # macOS/Linux
python setup_ffmpeg.py   # Windows
```

## Running from Source

```bash
python3 main.py  # macOS/Linux
python main.py   # Windows
```

This will launch the WebView application with direct Python↔JavaScript communication (no HTTP server).

## Building Executables

### Quick Build

**macOS:**
```bash
./build_mac.sh              # Creates .app bundle
./create_dmg_mac.sh         # Creates DMG installer (optional)
```

**Windows:**
```batch
build_windows.bat           # Creates portable .exe
```

### Build Output

- **macOS:** `dist/BulkAudioNormalizer.app` (application bundle)
- **macOS DMG:** `dist/BulkAudioNormalizer.dmg` (installer)
- **Windows:** `dist/BulkAudioNormalizer.exe` (portable executable)

### Complete Build Documentation

See [BUILD.md](BUILD.md) for comprehensive build instructions, troubleshooting, and distribution guidance.

See [BUILD_QUICK.md](BUILD_QUICK.md) for a quick reference.

## Architecture

- **main.py**: Entry point with pywebview window and JS API bridge
- **backend/audio_processor.py**: Core audio processing logic using FFmpeg
- **backend/process_manager.py**: Subprocess management with proper cleanup
- **backend/ffmpeg_paths.py**: FFmpeg binary detection (development and bundled)
- **frontend/**: HTML/CSS/JS UI with direct Python API calls
- **bulk_audio_normalizer.spec**: PyInstaller build configuration

## Differences from Electron Version

1. **Backend**: Python instead of Node.js
2. **UI Framework**: PyWebView instead of Electron
3. **Subprocess Management**: Python's subprocess module with better process tree cleanup
4. **IPC**: Direct JS API bridge instead of HTTP or Electron IPC
5. **Binary Resolution**: Supports both development and PyInstaller bundled environments
6. **Distribution**: Simpler deployment - no firewall prompts, smaller bundle size

## Development vs Production

The application automatically detects its environment:

**Development (Python script):**
- Looks for FFmpeg in `python_webview/bin/`
- Falls back to system PATH or npm packages
- Console output visible

**Production (PyInstaller bundle):**
- Looks for FFmpeg in bundled `bin/` directory
- Falls back to system PATH
- No console window (GUI only)
- Self-contained executable

## License

Same as parent project: AGPL-3.0-only
