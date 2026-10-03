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

Location: `bin/windows/` (`ffmpeg.exe`, `ffprobe.exe`, `COPYING.LGPLv2.1`, `FFMPEG-NOTICE.txt`)

**Setup (release builds):**
```bash
# On Linux (or MSYS2) with mingw-w64 and nasm:
#   sudo apt-get install gcc-mingw-w64-x86-64 nasm
./build_ffmpeg_windows.sh
```

This cross-compiles the same FFmpeg 6.1.6 as the macOS build (pinned commit, LGPL v2.1+, no
external libraries) into 64-bit `ffmpeg.exe` / `ffprobe.exe` that need only DLLs that come with
Windows, writes the license text and notice (the spec bundles both), and
`build/ffmpeg-windows/ffmpeg-<version>-source-windows.tar.xz`, the exact source, which is attached
to the release next to the `.exe`. `.github/workflows/build-windows.yml` runs it on ubuntu-latest.

**Local development only:** `python setup_ffmpeg.py` (after `npm install`) copies the npm
ffmpeg-static / ffprobe-static builds. Those are GPLv3 builds: never ship an exe built with them.

## PyInstaller Integration

The `bulk_audio_normalizer.spec` file automatically selects the correct binaries based on the build platform:

- **macOS build:** Bundles `bin/macos/ffmpeg`, `bin/macos/ffprobe` and their license files
- **Windows build:** Bundles `bin/windows/ffmpeg.exe`, `bin/windows/ffprobe.exe` and their license files

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
# Change FFMPEG_TAG and FFMPEG_COMMIT, then
./build_ffmpeg_windows.sh
```

## Version Control

These binaries are typically excluded from git due to their large size. Users building from source should:

1. Run `./build_ffmpeg_mac.sh` (macOS)
2. Run `./build_ffmpeg_windows.sh` (Windows binaries, on Linux or MSYS2)

Or download directly from [ffmpeg.org](https://ffmpeg.org/download.html).
