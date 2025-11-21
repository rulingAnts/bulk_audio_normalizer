# PyInstaller Build Checklist

Use this checklist before building to ensure everything is ready.

## Pre-Build Checklist

### Environment Setup
- [ ] Python 3.8+ installed
- [ ] PyInstaller installed (`pip install pyinstaller`)
- [ ] FFmpeg binaries present in `bin/` directory
- [ ] All dependencies installed (`pip install -r requirements.txt`)

### File Verification
- [ ] `main.py` exists and runs without errors
- [ ] `bulk_audio_normalizer.spec` exists
- [ ] All frontend files present in `frontend/`:
  - [ ] `index.html`
  - [ ] `styles.css`
  - [ ] `renderer.js`
  - [ ] `api_adapter.js`
  - [ ] `preview.html`
  - [ ] `preview.js`
  - [ ] `preview_adapter.js`
- [ ] All backend files present in `backend/`:
  - [ ] `__init__.py`
  - [ ] `audio_processor.py`
  - [ ] `process_manager.py`
  - [ ] `ffmpeg_paths.py`

### FFmpeg Setup
- [ ] `bin/ffmpeg` exists (macOS/Linux)
- [ ] `bin/ffprobe` exists (macOS/Linux)
- [ ] `bin/ffmpeg.exe` exists (Windows)
- [ ] `bin/ffprobe.exe` exists (Windows)
- [ ] FFmpeg binaries have execute permissions (macOS/Linux: `chmod +x bin/ffmpeg bin/ffprobe`)

### Test Run
- [ ] Application runs from source: `python3 main.py`
- [ ] Can select input/output folders
- [ ] Can process at least one file successfully
- [ ] Preview window opens and displays waveforms
- [ ] No Python errors in console

## Build Process

### macOS
- [ ] Run `./build_mac.sh`
- [ ] Check for build errors
- [ ] Verify `dist/BulkAudioNormalizer.app` exists
- [ ] Test the app: `open dist/BulkAudioNormalizer.app`
- [ ] Verify FFmpeg works in bundled app
- [ ] Process test file successfully
- [ ] (Optional) Create DMG: `./create_dmg_mac.sh`

### Windows
- [ ] Run `build_windows.bat`
- [ ] Check for build errors
- [ ] Verify `dist\BulkAudioNormalizer.exe` exists
- [ ] Test the exe: `dist\BulkAudioNormalizer.exe`
- [ ] Verify FFmpeg works in bundled exe
- [ ] Process test file successfully

## Post-Build Testing

### Basic Functionality
- [ ] Application launches without console window (or hidden console)
- [ ] UI renders correctly
- [ ] Can select folders using file dialogs
- [ ] Settings controls work (dB target, bit depth, etc.)

### FFmpeg Integration
- [ ] FFmpeg/FFprobe detected correctly
- [ ] Can scan input folder for WAV files
- [ ] File list displays with correct paths

### Processing
- [ ] Can start batch processing
- [ ] Progress bar updates correctly
- [ ] File-by-file progress shows
- [ ] Can pause processing
- [ ] Can resume after pause
- [ ] Can cancel processing
- [ ] Output files created successfully
- [ ] Verification passes after completion

### Preview
- [ ] Preview window opens
- [ ] Original waveform loads
- [ ] Processed waveform loads
- [ ] Audio playback works
- [ ] Can close and reopen preview

### Edge Cases
- [ ] Empty input folder handled gracefully
- [ ] Invalid output folder shows error
- [ ] Missing FFmpeg shows error (test by temporarily renaming bin/)
- [ ] Large batch (50+ files) processes without crashes
- [ ] App can be quit mid-processing

## Distribution Checklist

### macOS
- [ ] .app bundle tested on clean system
- [ ] No "damaged app" warnings (or fixed with `xattr -cr`)
- [ ] Works without system FFmpeg installed
- [ ] DMG mounts and installs correctly
- [ ] Application icon displays correctly

### Windows
- [ ] .exe tested on clean system
- [ ] No antivirus false positives (or documented)
- [ ] Works without system FFmpeg installed
- [ ] Portable (no installation required)
- [ ] Application icon displays correctly (if included)

## Common Issues

### Build fails with import errors
- Check `hiddenimports` in spec file
- Add missing modules to `hiddenimports` list

### FFmpeg not found in built app
- Verify `bin/ffmpeg` included in `datas` in spec file
- Check `backend/ffmpeg_paths.py` `get_base_path()` function

### Frontend not loading
- Verify `frontend/` directory included in `datas` in spec file
- Check paths use `get_base_path()` for file loading

### Large executable size
- Normal for onefile builds (includes Python runtime)
- macOS onedir is smaller but multiple files
- Windows onefile: ~15-20 MB is expected

### App crashes on launch
- Run from terminal to see error messages
- Check all dependencies included
- Verify Python version compatibility

## Automation Test Script

Run the automated test before building:

**macOS/Linux:**
```bash
./test_build.sh
```

**Windows:**
```batch
test_build.bat
```

This will verify all prerequisites automatically.

## Version Control

Before building a release:
- [ ] Update version number in code
- [ ] Update CHANGELOG (if exists)
- [ ] Commit all changes
- [ ] Tag release: `git tag v1.0.0`
- [ ] Push tags: `git push --tags`

## Documentation

For users:
- [ ] Include README with system requirements
- [ ] Document known issues
- [ ] Provide usage instructions
- [ ] Include license information

---

**Ready to Build?** If all checks pass, you're ready to create distributable builds!
