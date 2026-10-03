# FFmpeg Binaries Directory

This directory contains platform-specific FFmpeg and FFprobe binaries for PyInstaller builds.

## Directory Structure

```
bin/
├── macos/          # macOS binaries (built for the build Mac's architecture)
│   ├── ffmpeg
│   └── ffprobe
└── windows/        # Windows binaries (x64)
    ├── ffmpeg.exe
    └── ffprobe.exe
```

## macOS Binaries

Location: `bin/macos/` (`ffmpeg`, `ffprobe`, `COPYING.LGPLv2.1`, `FFMPEG-NOTICE.txt`)

**Setup:**
```bash
./build_ffmpeg_mac.sh
```

This builds FFmpeg 6.1.6 from FFmpeg's own source (pinned commit) for this Mac's architecture:
LGPL v2.1+, no external libraries, linked only against macOS system libraries. It also writes
the license text and a notice (the spec bundles both) and `build/ffmpeg/ffmpeg-<version>-source.tar.xz`,
the exact source, which must be attached to the release next to the `.dmg`. It needs the Xcode
Command Line Tools. `build_mac.sh` runs it when any of the four files is missing.

**Never** use the npm `ffmpeg-static` macOS binary: it is configured with `--enable-nonfree`
("not legally redistributable"), and `ffprobe-static` has no arm64 ffprobe. `setup_ffmpeg.py`
refuses to run on macOS for that reason.

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
# Change FFMPEG_TAG and FFMPEG_COMMIT (see the script's header), then
./build_ffmpeg_mac.sh
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

1. Run `./build_ffmpeg_mac.sh` (macOS)
2. Copy binaries from Electron build (Windows)

Or download directly from [ffmpeg.org](https://ffmpeg.org/download.html).
