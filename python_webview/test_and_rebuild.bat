@echo off
REM Quick test to check if executable uses bundled FFmpeg
echo ============================================================
echo Testing Bundled FFmpeg in Executable
echo ============================================================
echo.

if not exist "dist\Bulk Audio Normalizer.exe" (
    echo ERROR: Executable not found
    pause
    exit /b 1
)

echo The application logs FFmpeg paths when it starts.
echo.
echo What to look for:
echo   1. When the app starts, check the console/log output
echo   2. Look for lines like:
echo      "Using FFmpeg: [path]"
echo      "Using FFprobe: [path]"
echo.
echo   3. If the paths contain "_MEI" followed by numbers:
echo      Example: C:\Users\...\AppData\Local\Temp\_MEI123456\bin\windows\ffmpeg.exe
echo      Then it IS using bundled FFmpeg ✓
echo.
echo   4. If the paths are in C:\Program Files or elsewhere:
echo      Then it is NOT using bundled FFmpeg ✗
echo.
echo.
echo IMPORTANT: Since this is a windowed app (no console), 
echo we need to rebuild it with console enabled temporarily.
echo.
echo Press any key to rebuild with console for testing...
pause > nul

echo.
echo Rebuilding with console enabled...
echo.

REM Backup the spec file
copy bulk_audio_normalizer.spec bulk_audio_normalizer.spec.backup > nul

REM Temporarily enable console
powershell -Command "(gc bulk_audio_normalizer.spec) -replace 'console=False', 'console=True' | Set-Content bulk_audio_normalizer.spec"

REM Rebuild
w:/bulk_audio_normalizer/.venv/Scripts/python.exe -m PyInstaller bulk_audio_normalizer.spec --clean --noconfirm

REM Restore spec file
move /Y bulk_audio_normalizer.spec.backup bulk_audio_normalizer.spec > nul

echo.
echo ============================================================
echo Build complete! Now running with console to see FFmpeg paths...
echo ============================================================
echo.

"dist\Bulk Audio Normalizer.exe"

echo.
echo ============================================================
echo.
echo Did you see the FFmpeg paths in the console?
echo Did they contain "_MEI" in the path?
echo.
echo Press any key to rebuild without console (final version)...
pause > nul

echo.
echo Rebuilding final version (no console)...
w:/bulk_audio_normalizer/.venv/Scripts/python.exe -m PyInstaller bulk_audio_normalizer.spec --clean --noconfirm

echo.
echo ============================================================
echo Final build complete!
echo ============================================================
pause
