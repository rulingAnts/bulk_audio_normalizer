# PyInstaller Build Setup - Summary

This document summarizes the PyInstaller build setup for Bulk Audio Normalizer.

## Files Created

### Build Configuration
1. **bulk_audio_normalizer.spec** - Main PyInstaller configuration
   - Handles both Windows (onefile) and macOS (onedir) builds
   - Bundles frontend files, FFmpeg binaries, and all dependencies
   - Platform-specific executable settings (no console window)

### Build Scripts
2. **build_mac.sh** - macOS build automation script
   - Checks dependencies
   - Runs PyInstaller
   - Creates .app bundle in `dist/`

3. **create_dmg_mac.sh** - macOS DMG creation script
   - Requires `create-dmg` (via Homebrew)
   - Creates installer DMG from .app bundle

4. **build_windows.bat** - Windows build automation script
   - Checks dependencies
   - Runs PyInstaller
   - Creates portable .exe in `dist/`

### Testing Scripts
5. **test_build.sh** - macOS/Linux build verification
   - Checks Python, PyInstaller, FFmpeg
   - Verifies all required files present
   - Tests FFmpeg path resolution

6. **test_build.bat** - Windows build verification
   - Same checks as Unix version
   - Windows-compatible batch file

### Documentation
7. **BUILD.md** - Comprehensive build documentation
   - Complete prerequisites and setup instructions
   - Platform-specific build steps
   - Troubleshooting guide
   - Distribution recommendations

8. **BUILD_QUICK.md** - Quick reference guide
   - Essential commands only
   - Fast lookup for experienced users

9. **BUILD_CHECKLIST.md** - Pre-build verification checklist
   - Step-by-step validation
   - Common issues and solutions
   - Post-build testing procedures

10. **requirements-build.txt** - Build dependencies
    - PyInstaller 6.0+
    - pywebview 4.0+

### Code Updates
11. **backend/ffmpeg_paths.py** - Updated for PyInstaller support
    - Added `get_base_path()` function
    - Detects PyInstaller `_MEIPASS` directory
    - Works in development and bundled environments

12. **main.py** - Fixed deprecation warning
    - Changed `webview.FOLDER_DIALOG` to `FileDialog.FOLDER`

13. **README.md** - Updated with build information
    - Added build section
    - Links to build documentation
    - Development vs production notes

## How It Works

### FFmpeg Binary Resolution

The application finds FFmpeg in this order:

1. **Bundled `bin/` directory** (PyInstaller includes these)
   - Windows: `_MEIPASS/bin/ffmpeg.exe`
   - macOS: `BulkAudioNormalizer.app/Contents/Resources/bin/ffmpeg`

2. **Development `bin/` directory**
   - `python_webview/bin/ffmpeg`

3. **npm packages** (fallback for Electron compatibility)
   - `node_modules/ffmpeg-static/bin/...`

4. **System PATH** (last resort)

The `get_base_path()` function handles detection:
```python
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    return Path(sys._MEIPASS)  # PyInstaller bundle
else:
    return Path(__file__).parent.parent  # Development
```

### Build Types

**Windows (onefile):**
- Single portable .exe
- All dependencies embedded
- Temporary directory extraction at runtime
- ~15-20 MB size
- No console window

**macOS (onedir):**
- .app bundle with Contents/Resources/
- Faster startup (no extraction)
- ~20-25 MB size
- Can create DMG installer
- No terminal window

### What Gets Bundled

**Python Runtime:**
- Complete Python interpreter
- Standard library

**Dependencies:**
- pywebview
- All imported modules

**Application Files:**
- `frontend/` - HTML/CSS/JS UI
- `backend/` - Python modules
- `bin/` - FFmpeg/FFprobe binaries

**Configuration:**
- No external config files needed
- Everything self-contained

## Quick Start

### First Time Setup
```bash
# macOS
cd python_webview
pip3 install -r requirements-build.txt
python3 setup_ffmpeg.py
chmod +x *.sh

# Windows
cd python_webview
pip install -r requirements-build.txt
python setup_ffmpeg.py
```

### Build
```bash
# macOS
./test_build.sh       # Verify setup
./build_mac.sh        # Build .app
./create_dmg_mac.sh   # Create DMG (optional)

# Windows
test_build.bat        # Verify setup
build_windows.bat     # Build .exe
```

### Test
```bash
# macOS
open dist/BulkAudioNormalizer.app

# Windows
dist\BulkAudioNormalizer.exe
```

## Advantages Over Electron

1. **No HTTP Server:** Direct Python↔JavaScript bridge via pywebview
2. **Better Process Control:** Python subprocess management
3. **Smaller Bundle:** ~15-20 MB vs Electron's 50-100 MB
4. **No Firewall Prompts:** Not a web server, no network access needed
5. **Easier Distribution:** Single file (Windows) or standard .app (macOS)
6. **Python Ecosystem:** Access to powerful Python libraries

## Platform-Specific Notes

### macOS
- Application bundle follows Apple guidelines
- Info.plist included with proper metadata
- Can be code-signed for Gatekeeper (requires Apple Developer account)
- DMG provides drag-to-Applications installer experience

### Windows
- Single portable executable (no installation)
- No registry modifications
- Works on Windows 10 and 11
- x64 architecture only
- May trigger SmartScreen on first run (normal for unsigned apps)

## Support for Both Platforms

The spec file and FFmpeg path resolution automatically detect the platform:
```python
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'
```

Build scripts handle platform-specific details (file extensions, paths, etc.).

## Maintenance

When updating the application:

1. Make code changes
2. Test in development mode: `python3 main.py`
3. Run verification: `./test_build.sh` or `test_build.bat`
4. Build: `./build_mac.sh` or `build_windows.bat`
5. Test built application
6. Distribute

## Troubleshooting Reference

See `BUILD.md` for complete troubleshooting guide. Common issues:

- **Import errors:** Add to `hiddenimports` in spec file
- **FFmpeg not found:** Check `bin/` directory inclusion in spec
- **Large size:** Normal - includes Python runtime
- **Slow startup (Windows):** Expected with onefile - uses temp extraction
- **macOS "damaged":** Run `xattr -cr dist/BulkAudioNormalizer.app`

## Next Steps

1. **Test Builds:** Verify on clean systems (no Python/FFmpeg installed)
2. **Code Signing:** Consider signing for better user experience
3. **CI/CD:** Automate builds with GitHub Actions or similar
4. **Version Management:** Tag releases in git
5. **Distribution:** Upload to GitHub Releases or your own hosting

---

**Status:** ✅ Ready to build for both Windows and macOS

All necessary files are in place. Run the test scripts to verify, then build!
