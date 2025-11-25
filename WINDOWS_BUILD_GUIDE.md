# Windows Build Guide for AI Agent

**⚠️ CRITICAL**: Use Command Prompt (cmd.exe) for ALL terminal operations, NOT PowerShell.

**IMPORTANT**: This guide is for building the Windows executable on a Windows x64 system.

## Build Context

- **Build Environment**: Windows x64 (64-bit)
- **Target Architecture**: x64 (64-bit Intel/AMD)
- **Build Tool**: PyInstaller
- **Output**: Single portable .exe file (~20-30 MB)

## Prerequisites to Install

### 1. Python for Windows (x64)
```
Download from: https://www.python.org/downloads/
Version: Python 3.8 or higher (64-bit)
Important: Check "Add Python to PATH" during installation
```

**Open Command Prompt (cmd.exe)** - Press `Win+R`, type `cmd`, press Enter.

**DO NOT use PowerShell** - Use cmd.exe for all commands in this guide.

Verify installation:
```cmd
python --version
pip --version
```

### 2. Install Python Dependencies
Navigate to the python_webview directory:
```cmd
cd python_webview
pip install -r requirements.txt
pip install -r requirements-build.txt
```

This installs:
- pywebview>=4.0.0 (GUI framework)
- pyinstaller>=6.0.0 (bundler)
- All other runtime dependencies

## FFmpeg Binaries

**Location**: `python_webview/bin/windows/`

The repository already contains Windows x64 FFmpeg binaries:
- `ffmpeg.exe` (~77 MB)
- `ffprobe.exe` (~60 MB)

**Verify they exist**:
```cmd
dir bin\windows\ffmpeg.exe
dir bin\windows\ffprobe.exe
```

If missing, run:
```cmd
python setup_ffmpeg.py
```

This will download and extract Windows x64 binaries automatically.

## Icon File

**Location**: `python_webview/assets/icon.ico` (123 KB)

Verify it exists:
```cmd
dir assets\icon.ico
```

This icon is already converted from the macOS .icns and ready for Windows builds.

## Build Process

**⚠️ REMINDER**: Use Command Prompt (cmd.exe), NOT PowerShell.

### Quick Build (Recommended)

From the `python_webview` directory, run:
```cmd
build_windows.bat
```

This automated script will:
1. Verify Python and PyInstaller are installed
2. Check FFmpeg binaries exist
3. Clean previous builds
4. Run PyInstaller with the spec file
5. Create `dist\Bulk Audio Normalizer.exe`

### Manual Build (If Needed)

If the batch script fails, run PyInstaller directly:
```cmd
pyinstaller bulk_audio_normalizer.spec
```

## Build Configuration

**File**: `bulk_audio_normalizer.spec`

Key Windows-specific settings:
- **Architecture**: x64 (automatically detected by PyInstaller on x64 Windows)
- **Output Format**: Single file (onefile) executable
- **Console**: Disabled (no console window)
- **Icon**: `assets/icon.ico`
- **FFmpeg Binaries**: Bundled from `bin/windows/`
- **Compression**: UPX enabled for smaller file size

## Expected Output

**Success**:
```
✅ Build complete!
Application built at: dist\Bulk Audio Normalizer.exe
Size: ~20-30 MB
```

**Output File**: `dist\Bulk Audio Normalizer.exe`
- Single portable executable
- No installation required
- Includes Python runtime, pywebview, and FFmpeg

## Testing the Build

### Basic Test
```cmd
dist\"Bulk Audio Normalizer.exe"
```

The application window should open with:
- Title: "Bulk Audio Normalizer"
- Application icon visible
- No console window
- Browse buttons functional

### Verify Bundled FFmpeg

Check the application logs or use the app to process a test file. The bundled FFmpeg should be used automatically.

To verify paths being used, you can temporarily enable debug logging by running from command line and checking console output.

## Architecture Notes (IMPORTANT)

### Current Setup: x64 Build on x64 Windows VM

Since you're running **Windows x64** in Parallels:
- PyInstaller will automatically create **x64 executables**
- This is correct and works on all modern Windows PCs (Intel/AMD 64-bit)
- The .exe will NOT run on 32-bit Windows (rare in 2025)
- The .exe will run fine on Windows 10/11 x64

### What About ARM64 Windows?

If you needed to target ARM64 Windows (Surface Pro X, etc.):
- Would require ARM64 Windows Python installation
- Different FFmpeg binaries (ARM64 builds)
- Separate build environment
- **Current approach (x64) is recommended for maximum compatibility**

## Troubleshooting

### "Python not found"
```cmd
# Make sure Python is in PATH
python --version

# If not found, add Python to PATH manually or reinstall with "Add to PATH" checked
```

### "pyinstaller not found"
```cmd
pip install pyinstaller
# Or
python -m pip install pyinstaller
```

### "FFmpeg binaries missing"
```cmd
# Run setup script
python setup_ffmpeg.py
```

### Build fails with import errors
```cmd
# Reinstall dependencies
pip install -r requirements.txt -r requirements-build.txt --force-reinstall
```

### UPX warnings
UPX compression warnings are normal and can be ignored. The build will complete successfully.

### File path issues
**IMPORTANT**: PyInstaller may fail on shared/network file systems (including Parallels shared folders).

**If build fails with path or permission errors:**

1. **Copy repository to native Windows filesystem**:
   ```cmd
   xcopy /E /I /H /Y "\\Mac\Home\GIT\bulk_audio_normalizer" "%USERPROFILE%\git\bulk_audio_normalizer"
   ```
   Or copy to any local path like:
   ```cmd
   C:\Users\YourName\git\bulk_audio_normalizer
   ```

2. **Navigate to the copied location**:
   ```cmd
   cd "%USERPROFILE%\git\bulk_audio_normalizer\python_webview"
   ```

3. **Run build script**:
   ```cmd
   build_windows.bat
   ```

4. **Copy .exe back** (if needed):
   ```cmd
   copy "dist\Bulk Audio Normalizer.exe" "\\Mac\Home\GIT\bulk_audio_normalizer\python_webview\dist\"
   ```

**Symptoms that indicate you need native filesystem**:
- "Cannot find module" errors despite dependencies installed
- Permission denied errors during build
- Build hangs or fails silently
- Temporary file creation errors

**Try building in-place first**, but if you encounter issues, copy to native Windows filesystem and rebuild there.

## Distribution

After successful build:

1. **Test the .exe** on the Windows system thoroughly
2. **Verify functionality**: Test processing audio files
3. **Upload to GitHub**: Both the macOS .dmg and Windows .exe can be attached to a GitHub release

**File to Distribute**: `dist/Bulk Audio Normalizer.exe`
- No additional files needed
- Users just download and run
- All dependencies bundled

## Build Output Location

After running `build_windows.bat`, you'll find:

```
python_webview/
├── build/                          # Temporary build files (can delete)
├── dist/
│   ├── Bulk Audio Normalizer.app   # macOS build (if built on Mac)
│   ├── Bulk Audio Normalizer.dmg   # macOS DMG (if created on Mac)
│   └── Bulk Audio Normalizer.exe   # Windows build (created here) ✓
└── bulk_audio_normalizer.spec      # Build configuration
```

## Security Notes

**Windows SmartScreen Warning**: 

When distributing the .exe, users may see a "Windows protected your PC" warning. This is normal for unsigned executables. To avoid this:

1. **Code Signing** (recommended for public distribution):
   - Requires a code signing certificate ($50-300/year)
   - Certificate vendors: DigiCert, Sectigo, SSL.com
   - Signs the .exe to verify publisher identity

2. **User Instructions** (for unsigned builds):
   - Click "More info"
   - Click "Run anyway"
   - This is a limitation of distributing unsigned Windows apps

For internal use or small-scale distribution, unsigned is fine.

## Next Steps After Build

1. Test the .exe thoroughly on Windows
2. Test on a clean Windows machine (without Python installed) to verify standalone functionality
3. Create a GitHub release with both macOS .dmg and Windows .exe
4. Update release notes with platform-specific instructions

## Summary Checklist for AI Agent

- [ ] **Open Command Prompt (cmd.exe)** - NOT PowerShell
- [ ] Verify Windows x64 Python installed (python --version)
- [ ] Install build dependencies (pip install -r requirements-build.txt)
- [ ] Verify FFmpeg binaries exist (dir bin\windows\ffmpeg.exe)
- [ ] Verify icon exists (dir assets\icon.ico)
- [ ] Run build script (build_windows.bat)
- [ ] Check output file exists (dir dist\"Bulk Audio Normalizer.exe")
- [ ] Test the .exe launches and shows correct window title
- [ ] Verify bundled FFmpeg works by processing a test file
- [ ] Report file size and any warnings/errors

---

**Last Updated**: 2025-11-25
**Build Target**: Windows x64
**Expected Output Size**: 20-30 MB
**Python Version**: 3.8+
