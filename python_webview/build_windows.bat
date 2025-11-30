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
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo PyInstaller not found. Installing...
    pip install pyinstaller
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
pyinstaller bulk_audio_normalizer.spec

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
echo Executable location: dist\windows\Bulk Audio Normalizer.exeizer.exe
echo.
echo To test the application:
echo   "dist\windows\Bulk Audio Normalizer.exe"
echo.
