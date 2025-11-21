# Building Bulk Audio Normalizer

This guide covers building portable executables for Windows and macOS using PyInstaller.

## Prerequisites

### All Platforms
- Python 3.8 or higher
- FFmpeg binaries (automatically downloaded by `setup_ffmpeg.py`)

### macOS
```bash
# Install PyInstaller
pip3 install -r requirements-build.txt

# Optional: For creating DMG installers
brew install create-dmg
```

### Windows
```batch
REM Install PyInstaller
pip install -r requirements-build.txt
```

## Building

### macOS (.app bundle and DMG)

1. **Navigate to the python_webview directory:**
   ```bash
   cd python_webview
   ```

2. **Make build scripts executable:**
   ```bash
   chmod +x build_mac.sh create_dmg_mac.sh
   ```

3. **Build the .app bundle:**
   ```bash
   ./build_mac.sh
   ```
   
   This creates: `dist/BulkAudioNormalizer.app`

4. **Create DMG installer (optional):**
   ```bash
   ./create_dmg_mac.sh
   ```
   
   This creates: `dist/BulkAudioNormalizer.dmg`

5. **Test the application:**
   ```bash
   open dist/BulkAudioNormalizer.app
   ```

### Windows (Portable .exe)

1. **Navigate to the python_webview directory:**
   ```batch
   cd python_webview
   ```

2. **Run the build script:**
   ```batch
   build_windows.bat
   ```
   
   This creates: `dist\BulkAudioNormalizer.exe`

3. **Test the application:**
   ```batch
   dist\BulkAudioNormalizer.exe
   ```

## Build Configuration

The build is configured in `bulk_audio_normalizer.spec`:

### Windows Build
- **Type:** Single executable file (onefile)
- **Architecture:** x64
- **Console:** Hidden (no console window)
- **Output:** `dist/BulkAudioNormalizer.exe`
- **Size:** ~15-20 MB

### macOS Build
- **Type:** Application bundle (onedir)
- **Architecture:** Universal (works on Intel and Apple Silicon)
- **Console:** Hidden (no terminal window)
- **Output:** `dist/BulkAudioNormalizer.app`
- **DMG:** ~25-30 MB

## What Gets Bundled

1. **Python Runtime:** Entire Python interpreter
2. **Dependencies:** All required packages (pywebview, etc.)
3. **Frontend:** HTML, CSS, JavaScript files
4. **FFmpeg Binaries:** ffmpeg and ffprobe executables
5. **Backend:** Python audio processing modules

## FFmpeg Binary Resolution

The application finds FFmpeg binaries in this order:

1. **Bundled binaries** in the application directory (`bin/ffmpeg`, `bin/ffprobe`)
2. **System PATH** (fallback if bundled binaries not found)

The `backend/ffmpeg_paths.py` module handles detection for:
- Development (running from source)
- PyInstaller onefile bundle (Windows)
- PyInstaller onedir bundle (macOS .app)

## Troubleshooting

### Build Fails

**Issue:** PyInstaller not found
```bash
# macOS/Linux
pip3 install pyinstaller

# Windows
pip install pyinstaller
```

**Issue:** FFmpeg binaries missing
```bash
# Run the setup script
python3 setup_ffmpeg.py  # macOS/Linux
python setup_ffmpeg.py   # Windows
```

**Issue:** Module not found in built app
- Check `bulk_audio_normalizer.spec` hidden imports
- Add missing module to `hiddenimports` list

### App Won't Run

**Issue:** "FFmpeg not found" error
- Verify `bin/ffmpeg` and `bin/ffprobe` exist in build
- Check they have execute permissions (macOS/Linux)

**Issue:** App opens but crashes immediately
- Run from terminal to see error messages:
  ```bash
  # macOS
  dist/BulkAudioNormalizer.app/Contents/MacOS/BulkAudioNormalizer
  
  # Windows (in cmd)
  dist\BulkAudioNormalizer.exe
  ```

**Issue:** Frontend not loading
- Check `frontend/` directory is included in build
- Verify all HTML/CSS/JS files are in `dist/` or `.app/Contents/Resources/`

### macOS Specific

**Issue:** "App is damaged and can't be opened"
```bash
# Remove quarantine attribute
xattr -cr dist/BulkAudioNormalizer.app
```

**Issue:** Permission denied when running FFmpeg
```bash
# Ensure binaries have execute permission
chmod +x bin/ffmpeg bin/ffprobe
# Rebuild
./build_mac.sh
```

**Issue:** DMG creation fails
```bash
# Install create-dmg
brew install create-dmg

# Or create manually
hdiutil create -volname "Bulk Audio Normalizer" \
  -srcfolder dist/BulkAudioNormalizer.app \
  -ov -format UDZO \
  dist/BulkAudioNormalizer.dmg
```

### Windows Specific

**Issue:** Antivirus flags the .exe
- This is common with PyInstaller builds
- Submit to antivirus vendor as false positive
- Or code-sign the executable (requires certificate)

**Issue:** Missing DLL errors
- Ensure Visual C++ Redistributable is installed
- Or include runtime DLLs in build directory

## Distribution

### macOS
- Distribute the `.dmg` file for easy installation
- Or zip the `.app` bundle directly
- Consider code signing for Gatekeeper (requires Apple Developer account)

### Windows
- Distribute the `.exe` file as-is (portable, no installation needed)
- Or create an installer with Inno Setup or NSIS
- Consider code signing to avoid SmartScreen warnings (requires certificate)

## Clean Build

To start fresh:

```bash
# macOS/Linux
rm -rf build dist __pycache__ backend/__pycache__

# Windows
rmdir /s /q build dist __pycache__ backend\__pycache__
```

Then rebuild from scratch.

## Development vs Production

### Development
```bash
# Run directly with Python
python3 main.py  # macOS/Linux
python main.py   # Windows
```

### Production
```bash
# Run the built application
open dist/BulkAudioNormalizer.app  # macOS
dist\BulkAudioNormalizer.exe       # Windows
```

The application automatically detects whether it's running as:
- Python script (development)
- PyInstaller bundle (production)

And adjusts file paths accordingly.
