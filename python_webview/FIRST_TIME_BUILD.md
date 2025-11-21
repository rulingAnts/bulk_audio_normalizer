# First-Time Build Guide

Never built a Python app before? This guide walks you through creating standalone executables for Windows and macOS from scratch.

## What You'll Create

- **Windows:** A single `.exe` file that runs without Python installed
- **macOS:** A `.app` bundle that works like any Mac application

## Prerequisites Check

### Do you have Python?

**macOS:**
```bash
python3 --version
```
Should show Python 3.8 or higher. If not:
```bash
brew install python3
```

**Windows:**
```batch
python --version
```
Should show Python 3.8 or higher. If not, download from [python.org](https://www.python.org/downloads/)

### Do you have pip?

**macOS:**
```bash
pip3 --version
```

**Windows:**
```batch
pip --version
```

Both should work. If not, reinstall Python with pip included.

## Step 1: Install Build Tools

Open terminal (macOS) or Command Prompt (Windows) and navigate to the project:

**macOS:**
```bash
cd /path/to/bulk_audio_normalizer/python_webview
pip3 install -r requirements-build.txt
```

**Windows:**
```batch
cd C:\path\to\bulk_audio_normalizer\python_webview
pip install -r requirements-build.txt
```

This installs PyInstaller, which creates the executable.

## Step 2: Setup FFmpeg

FFmpeg is the audio processing engine. Download the binaries:

**macOS:**
```bash
python3 setup_ffmpeg.py
```

**Windows:**
```batch
python setup_ffmpeg.py
```

You should see:
```
✓ Downloaded FFmpeg
✓ Downloaded FFprobe
✓ Setup complete
```

## Step 3: Verify Everything

Run the test script to check if you're ready to build:

**macOS:**
```bash
chmod +x test_build.sh
./test_build.sh
```

**Windows:**
```batch
test_build.bat
```

If all checks pass (✓), you're ready to build! If not, the script will tell you what's missing.

## Step 4: Build the Application

### macOS

```bash
chmod +x build_mac.sh
./build_mac.sh
```

Wait 1-2 minutes. You should see:
```
✅ Build complete!
Application built at: dist/BulkAudioNormalizer.app
```

### Windows

```batch
build_windows.bat
```

Wait 2-3 minutes. You should see:
```
Build complete!
Executable location: dist\BulkAudioNormalizer.exe
```

## Step 5: Test the Build

### macOS
```bash
open dist/BulkAudioNormalizer.app
```

The application should launch. Try processing a test audio file.

### Windows
```batch
dist\BulkAudioNormalizer.exe
```

The application should launch. Try processing a test audio file.

## Step 6: Create Installer (Optional)

### macOS DMG

First install create-dmg:
```bash
brew install create-dmg
```

Then create the DMG:
```bash
chmod +x create_dmg_mac.sh
./create_dmg_mac.sh
```

Creates: `dist/BulkAudioNormalizer.dmg`

### Windows Installer

Windows .exe is already portable (no installer needed). Users can just run it.

If you want a proper installer, you can use:
- [Inno Setup](https://jrsoftware.org/isinfo.php) (free)
- [NSIS](https://nsis.sourceforge.io/) (free)

## Common First-Time Issues

### "Permission denied" (macOS)

Scripts need execute permission:
```bash
chmod +x build_mac.sh create_dmg_mac.sh test_build.sh
```

### "command not found: pyinstaller"

PyInstaller not installed:
```bash
pip3 install pyinstaller  # macOS
pip install pyinstaller   # Windows
```

### "FFmpeg not found"

Run the setup script:
```bash
python3 setup_ffmpeg.py  # macOS
python setup_ffmpeg.py   # Windows
```

### Build succeeds but app won't run

Check terminal/console output for error messages. Common causes:
- Missing files (rerun test script)
- FFmpeg permission issues (macOS: `chmod +x bin/ffmpeg bin/ffprobe`)
- Antivirus blocking (Windows: add exception)

### "App is damaged" (macOS)

Apple's security blocking unsigned app:
```bash
xattr -cr dist/BulkAudioNormalizer.app
```

Then try opening again.

### Antivirus alerts (Windows)

Common with PyInstaller. The app is safe (it's your own code!). Add exception or submit to antivirus as false positive.

## Understanding the Build

### What just happened?

PyInstaller:
1. Analyzed your Python script
2. Found all imported modules
3. Bundled Python interpreter + your code + dependencies
4. Added FFmpeg binaries
5. Created an executable

### Where are the files?

**macOS:**
```
dist/
  BulkAudioNormalizer.app/
    Contents/
      MacOS/
        BulkAudioNormalizer  (executable)
      Resources/
        frontend/  (HTML/CSS/JS)
        bin/  (ffmpeg, ffprobe)
        ...  (Python runtime)
```

**Windows:**
```
dist/
  BulkAudioNormalizer.exe  (everything inside)
```

Windows extracts to temp directory at runtime. macOS keeps everything in the bundle.

## Distributing Your Build

### macOS
1. Share `BulkAudioNormalizer.dmg` (or zip the .app)
2. Users drag to Applications folder
3. Works on macOS 10.13+ (both Intel and Apple Silicon)

### Windows
1. Share `BulkAudioNormalizer.exe`
2. Users just run it (portable, no install needed)
3. Works on Windows 10+ (64-bit)

## Making Changes and Rebuilding

1. Edit the Python or JavaScript code
2. Test with: `python3 main.py` (macOS) or `python main.py` (Windows)
3. When satisfied, rebuild:
   - macOS: `./build_mac.sh`
   - Windows: `build_windows.bat`
4. The new version is in `dist/`

Old builds are automatically deleted before rebuilding.

## File Sizes

**macOS:**
- `.app` bundle: ~20-25 MB
- `.dmg` installer: ~20-25 MB

**Windows:**
- `.exe` file: ~15-20 MB

These sizes include:
- Complete Python interpreter
- All dependencies
- FFmpeg + FFprobe
- Your application code

## Security & Code Signing

### macOS

Without code signing, users see "unidentified developer" warning (can bypass with right-click → Open).

To properly sign:
1. Join Apple Developer Program ($99/year)
2. Get Developer ID certificate
3. Sign with: `codesign --deep --force --verify --verbose --sign "Developer ID" dist/BulkAudioNormalizer.app`

### Windows

Without code signing, SmartScreen may warn users.

To properly sign:
1. Get code signing certificate ($50-300/year)
2. Sign with `signtool.exe` (included in Windows SDK)

Code signing improves user trust but isn't required for personal/internal use.

## Getting Help

If stuck:
1. Check `BUILD.md` for detailed troubleshooting
2. Check `BUILD_CHECKLIST.md` for verification steps
3. Run test script: `./test_build.sh` or `test_build.bat`
4. Look at console output for error messages

## Success! 🎉

You've built a standalone application! Your users can run it without installing Python, pip, or any dependencies.

### Next Steps

- Test on a computer without Python installed
- Share with friends/colleagues
- Consider code signing for wider distribution
- Set up CI/CD for automated builds (GitHub Actions, etc.)

---

**Summary of Commands:**

macOS:
```bash
cd python_webview
pip3 install -r requirements-build.txt
python3 setup_ffmpeg.py
chmod +x *.sh
./test_build.sh
./build_mac.sh
./create_dmg_mac.sh  # optional
open dist/BulkAudioNormalizer.app
```

Windows:
```batch
cd python_webview
pip install -r requirements-build.txt
python setup_ffmpeg.py
test_build.bat
build_windows.bat
dist\BulkAudioNormalizer.exe
```

That's it!
