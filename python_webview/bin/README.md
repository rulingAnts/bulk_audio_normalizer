# FFmpeg Binaries Directory

This directory contains platform-specific FFmpeg and FFprobe binaries for PyInstaller builds.

## Directory Structure

```
bin/
├── macos/          # macOS binaries (Intel and Apple Silicon)
│   ├── ffmpeg
│   └── ffprobe
└── windows/        # Windows binaries (x64)
    ├── ffmpeg.exe
    └── ffprobe.exe
```

## macOS Binaries

Location: `bin/macos/`

**Setup:**
```bash
python3 setup_ffmpeg.py
```

This downloads platform-appropriate FFmpeg binaries and places them in `bin/macos/`.

**Source:**
- Downloaded via setup_ffmpeg.py from ffmpeg-static npm package or direct download

## Windows Binaries

Location: `bin/windows/`

**Setup:**
These are copied from the Electron version:
```bash
# From project root
cp build/win32-resources/ffmpeg-static/ffmpeg.exe python_webview/bin/windows/
cp node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe python_webview/bin/windows/
```

**Source:**
- `ffmpeg.exe`: From Electron build resources
- `ffprobe.exe`: From npm ffprobe-static package

## PyInstaller Integration

The `bulk_audio_normalizer.spec` file automatically selects the correct binaries based on the build platform:

- **macOS build:** Bundles `bin/macos/ffmpeg` and `bin/macos/ffprobe`
- **Windows build:** Bundles `bin/windows/ffmpeg.exe` and `bin/windows/ffprobe.exe`

During runtime, `backend/ffmpeg_paths.py` finds these binaries in the PyInstaller bundle.

## Development vs Production

**Development (running from source):**
- Looks in `bin/macos/` or `bin/windows/`
- Falls back to `bin/` (legacy location)
- Falls back to npm packages
- Falls back to system PATH

**Production (PyInstaller bundle):**
- Finds binaries in bundle's `bin/` directory
- Falls back to system PATH

## File Sizes

**macOS:**
- ffmpeg: ~43 MB
- ffprobe: ~59 MB

**Windows:**
- ffmpeg.exe: ~77 MB
- ffprobe.exe: ~60 MB

## Permissions

**macOS:** Binaries must be executable
```bash
chmod +x bin/macos/ffmpeg bin/macos/ffprobe
```

**Windows:** No special permissions needed

## Updating Binaries

To update to newer FFmpeg versions:

**macOS:**
```bash
# Rerun setup script
python3 setup_ffmpeg.py
# Or manually download and replace in bin/macos/
```

**Windows:**
```bash
# Update npm packages in main project
cd ..
npm update ffmpeg-static ffprobe-static
# Copy new binaries
cp build/win32-resources/ffmpeg-static/ffmpeg.exe python_webview/bin/windows/
cp node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe python_webview/bin/windows/
```

## Version Control

These binaries are typically excluded from git due to their large size. Users building from source should:

1. Run `python3 setup_ffmpeg.py` (macOS)
2. Copy binaries from Electron build (Windows)

Or download directly from [ffmpeg.org](https://ffmpeg.org/download.html).
