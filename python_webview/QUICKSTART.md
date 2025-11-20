# Quick Start Guide - Python WebView Version

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- FFmpeg binaries (automatically available if you've installed the Electron version)

## Installation

### Option 1: Using the Electron version's FFmpeg (Recommended)

If you already have the Electron version installed:

```bash
# From the python_webview directory
pip install -r requirements.txt
python main.py
```

The Python version will automatically use the FFmpeg binaries from the Electron version's `node_modules` directory.

### Option 2: Using system FFmpeg

If you don't have the Electron version installed, install FFmpeg on your system:

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt-get install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

Then install Python dependencies:
```bash
pip install -r requirements.txt
python main.py
```

## Verifying Installation

Run the test script to verify everything is set up correctly:

```bash
python test_setup.py
```

All tests should pass before running the main application.

## Running

```bash
python main.py
```

This will:
1. Start a Flask backend server on localhost:5000
2. Open a WebView window with the UI
3. Process audio files using Python subprocess management

## Features

The Python version has the same features as the Electron version:
- Peak dBFS or LUFS normalization
- Flexible bit depth (16-bit, 24-bit, or preserve original)
- Auto-trim silence with adjustable parameters
- Batch processing with adaptive throttling
- Preview mode for random sampling

## Advantages Over Electron Version

1. **Better subprocess management**: Python's `subprocess` module with `psutil` provides more reliable process tree cleanup
2. **Cross-platform process control**: Proper process groups on Unix and job objects on Windows
3. **Easier debugging**: Python stack traces are clearer than Node.js async traces
4. **Lower memory footprint**: No Chromium overhead (WebView uses system browser engine)

## Troubleshooting

### "FFmpeg not found"
- Make sure you've run `npm install` in the parent directory, or
- Install FFmpeg on your system using your package manager

### "No module named 'psutil'" or other import errors
- Run `pip install -r requirements.txt` to install dependencies

### Window doesn't open
- Make sure port 5000 is not in use by another application
- Check the console output for errors

### Process cleanup issues (Windows)
The Python version should handle process cleanup better than the Electron version. If you still have zombie FFmpeg processes:
- Use Task Manager to kill them manually
- Report an issue with details about your setup

## Development

The Python version mirrors the Electron version's architecture:

```
python_webview/
├── main.py                 # Entry point (replaces Electron main.js)
├── backend/
│   ├── api.py             # Flask REST API (replaces Electron IPC)
│   ├── audio_processor.py # Audio processing logic
│   ├── process_manager.py # Subprocess management (key improvement)
│   └── ffmpeg_paths.py    # FFmpeg binary resolution
└── frontend/
    ├── index.html         # UI (copied from Electron version)
    ├── styles.css         # Styles (copied from Electron version)
    ├── renderer.js        # UI logic (copied from Electron version)
    └── api_adapter.js     # Bridges Electron IPC to REST API
```

## License

Same as parent project: AGPL-3.0-only
