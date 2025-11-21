# Quick Build Reference

## macOS

```bash
cd python_webview
./build_mac.sh              # Build .app bundle
./create_dmg_mac.sh         # Create DMG (optional)
open dist/BulkAudioNormalizer.app  # Test
```

**Output:** `dist/BulkAudioNormalizer.app` (onedir bundle)  
**DMG:** `dist/BulkAudioNormalizer.dmg`

## Windows

```batch
cd python_webview
build_windows.bat           # Build .exe
dist\BulkAudioNormalizer.exe  # Test
```

**Output:** `dist\BulkAudioNormalizer.exe` (onefile portable)

## First Time Setup

```bash
# Install build dependencies
pip3 install -r requirements-build.txt  # macOS
pip install -r requirements-build.txt   # Windows

# Setup FFmpeg (if not already done)
python3 setup_ffmpeg.py  # macOS
python setup_ffmpeg.py   # Windows
```

## Verification

```bash
# Test build configuration (macOS)
./test_build.sh

# Clean previous builds
rm -rf build dist  # macOS
rmdir /s /q build dist  # Windows
```

## Key Files

- `bulk_audio_normalizer.spec` - PyInstaller configuration
- `build_mac.sh` - macOS build script
- `create_dmg_mac.sh` - macOS DMG creation
- `build_windows.bat` - Windows build script
- `BUILD.md` - Complete build documentation

## What Gets Bundled

✅ Python runtime  
✅ pywebview + dependencies  
✅ FFmpeg + FFprobe binaries  
✅ Frontend files (HTML/CSS/JS)  
✅ Backend modules (audio_processor, etc.)

## Troubleshooting

**FFmpeg not found in build:**
- Verify `bin/ffmpeg` and `bin/ffprobe` exist before building
- Run `python3 setup_ffmpeg.py` to download them

**Module not found:**
- Add to `hiddenimports` in `bulk_audio_normalizer.spec`

**Frontend files missing:**
- Check `frontend/` directory exists
- Verify spec file includes all frontend files

**macOS "App is damaged":**
```bash
xattr -cr dist/BulkAudioNormalizer.app
```

See `BUILD.md` for complete documentation.
