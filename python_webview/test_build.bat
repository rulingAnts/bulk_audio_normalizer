@echo off
REM Test script to verify PyInstaller build configuration
REM Tests FFmpeg detection in bundled environment

echo Testing PyInstaller Build Configuration
echo ==========================================
echo.

REM Check Python
echo 1. Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo X Python not found
    exit /b 1
)
python --version
echo + Python OK
echo.

REM Check PyInstaller
echo 2. Checking PyInstaller...
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo X PyInstaller not found
    echo   Install with: pip install pyinstaller
    exit /b 1
)
pyinstaller --version
echo + PyInstaller OK
echo.

REM Check FFmpeg binaries
echo 3. Checking FFmpeg binaries...
set MISSING_FFMPEG=0
if not exist "bin\windows\ffmpeg.exe" (
    echo ! bin\windows\ffmpeg.exe not found
    echo   Please copy from: build/win32-resources/ffmpeg-static/ffmpeg.exe
    set MISSING_FFMPEG=1
) else (
    echo + bin\windows\ffmpeg.exe found
)

if not exist "bin\windows\ffprobe.exe" (
    echo ! bin\windows\ffprobe.exe not found
    echo   Please copy from: node_modules/ffprobe-static/bin/win32/x64/ffprobe.exe
    set MISSING_FFMPEG=1
) else (
    echo + bin\windows\ffprobe.exe found
)

if %MISSING_FFMPEG%==1 (
    echo.
    echo X Windows FFmpeg binaries missing
    echo   Cannot auto-download on Windows
    exit /b 1
)
echo.

REM Check frontend files
echo 4. Checking frontend files...
set MISSING_FILES=0
if not exist "frontend\index.html" (
    echo X Missing: frontend\index.html
    set MISSING_FILES=1
)
if not exist "frontend\styles.css" (
    echo X Missing: frontend\styles.css
    set MISSING_FILES=1
)
if not exist "frontend\renderer.js" (
    echo X Missing: frontend\renderer.js
    set MISSING_FILES=1
)
if not exist "frontend\api_adapter.js" (
    echo X Missing: frontend\api_adapter.js
    set MISSING_FILES=1
)
if not exist "frontend\preview.html" (
    echo X Missing: frontend\preview.html
    set MISSING_FILES=1
)
if not exist "frontend\preview.js" (
    echo X Missing: frontend\preview.js
    set MISSING_FILES=1
)
if not exist "frontend\preview_adapter.js" (
    echo X Missing: frontend\preview_adapter.js
    set MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    exit /b 1
)
echo + All frontend files present
echo.

REM Check backend files
echo 5. Checking backend files...
set MISSING_FILES=0
if not exist "backend\__init__.py" (
    echo X Missing: backend\__init__.py
    set MISSING_FILES=1
)
if not exist "backend\audio_processor.py" (
    echo X Missing: backend\audio_processor.py
    set MISSING_FILES=1
)
if not exist "backend\process_manager.py" (
    echo X Missing: backend\process_manager.py
    set MISSING_FILES=1
)
if not exist "backend\ffmpeg_paths.py" (
    echo X Missing: backend\ffmpeg_paths.py
    set MISSING_FILES=1
)

if %MISSING_FILES%==1 (
    exit /b 1
)
echo + All backend files present
echo.

REM Check spec file
echo 6. Checking spec file...
if not exist "bulk_audio_normalizer.spec" (
    echo X bulk_audio_normalizer.spec not found
    exit /b 1
)
echo + Spec file present
echo.

REM Test FFmpeg path resolution
echo 7. Testing FFmpeg path resolution...
python -c "from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path; ffmpeg = get_ffmpeg_path(); ffprobe = get_ffprobe_path(); print(f'+ FFmpeg: {ffmpeg}'); print(f'+ FFprobe: {ffprobe}')"
if errorlevel 1 (
    exit /b 1
)
echo.

REM Summary
echo ==========================================
echo + All checks passed!
echo.
echo Ready to build:
echo   Windows: build_windows.bat
echo.
