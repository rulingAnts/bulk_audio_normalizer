@echo off
REM Build script for Windows
REM Creates a portable .exe with PyInstaller

echo Building Bulk Audio Normalizer for Windows...

REM Check if we're in the right directory
if not exist "main.py" (
    echo Error: Run this script from the python_webview directory
    exit /b 1
)

REM Check if PyInstaller is installed
REM Prefer the project's virtualenv Python (if present) and use it to run
REM PyInstaller via "python -m PyInstaller" so we don't rely on pyinstaller
REM being on the global PATH.
set "VENV_PY=%~dp0..\.venv\Scripts\python.exe"
if exist %VENV_PY% (
    echo Using virtualenv Python at %VENV_PY%
    "%VENV_PY%" -m PyInstaller --version >nul 2>&1
    if errorlevel 1 (
        echo PyInstaller not found in venv. Installing into venv...
        "%VENV_PY%" -m pip install --upgrade pyinstaller
    )
) else (
    echo No project venv found. Falling back to system Python/pyinstaller.
    pyinstaller --version >nul 2>&1
    if errorlevel 1 (
        echo PyInstaller not found. Installing to user site-packages...
        python -m pip install --user --upgrade pyinstaller
    )
)

REM Check if FFmpeg binaries exist
if not exist "bin\windows\ffmpeg.exe" (
    echo FFmpeg binary not found at bin\windows\ffmpeg.exe
    echo Please copy Windows FFmpeg binaries to bin\windows\
    exit /b 1
)
if not exist "bin\windows\ffprobe.exe" (
    echo FFprobe binary not found at bin\windows\ffprobe.exe
    echo Please copy Windows FFmpeg binaries to bin\windows\
    exit /b 1
)

REM Clean previous Windows builds only
echo Cleaning previous Windows builds...
if exist "build\windows" rmdir /s /q build\windows
if exist "dist\windows" rmdir /s /q dist\windows

REM Build with PyInstaller
echo Building application...
if exist %VENV_PY% (
    echo Building application with venv Python...
    "%VENV_PY%" -m PyInstaller --distpath dist\windows --workpath build\windows bulk_audio_normalizer.spec
) else (
    echo Building application with system pyinstaller...
    pyinstaller --distpath dist\windows --workpath build\windows bulk_audio_normalizer.spec
)

REM Check if build was successful
if not exist "dist\windows\Bulk Audio Normalizer.exe" (
    echo Build failed - .exe not created
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Executable location: dist\windows\Bulk Audio Normalizer.exe
echo.
echo To test the application:
echo   "dist\windows\Bulk Audio Normalizer.exe"
echo.
