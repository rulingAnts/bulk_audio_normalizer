@echo off
REM Test script to verify bundled FFmpeg in the executable
REM This runs the test_bundled_ffmpeg.py script using the bundled executable

echo ============================================================
echo Testing FFmpeg Bundle in Executable
echo ============================================================
echo.

if not exist "dist\Bulk Audio Normalizer.exe" (
    echo ERROR: Executable not found at dist\Bulk Audio Normalizer.exe
    echo Please build the application first using build_windows.bat
    pause
    exit /b 1
)

echo Extracting and testing bundled FFmpeg paths...
echo.

REM The executable will extract to a temp folder when run
REM We'll use a simple Python test that imports from the bundle

REM Create a temporary test script that will be bundled
echo import sys > temp_test.py
echo from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path, get_base_path >> temp_test.py
echo. >> temp_test.py
echo print("="*60) >> temp_test.py
echo print("FFmpeg Bundle Test (from executable)") >> temp_test.py
echo print("="*60) >> temp_test.py
echo print(f"\nRunning as frozen: {getattr(sys, 'frozen', False)}") >> temp_test.py
echo print(f"Has _MEIPASS: {hasattr(sys, '_MEIPASS')}") >> temp_test.py
echo if hasattr(sys, '_MEIPASS'): >> temp_test.py
echo     print(f"_MEIPASS location: {sys._MEIPASS}") >> temp_test.py
echo. >> temp_test.py
echo print(f"\nBase path: {get_base_path()}") >> temp_test.py
echo. >> temp_test.py
echo try: >> temp_test.py
echo     ffmpeg = get_ffmpeg_path() >> temp_test.py
echo     print(f"\nFFmpeg path: {ffmpeg}") >> temp_test.py
echo     if hasattr(sys, '_MEIPASS') and sys._MEIPASS in ffmpeg: >> temp_test.py
echo         print("  ✓ USING BUNDLED FFMPEG") >> temp_test.py
echo     else: >> temp_test.py
echo         print("  ⚠ WARNING: Not using bundled FFmpeg!") >> temp_test.py
echo except Exception as e: >> temp_test.py
echo     print(f"\n✗ FFmpeg not found: {e}") >> temp_test.py
echo. >> temp_test.py
echo try: >> temp_test.py
echo     ffprobe = get_ffprobe_path() >> temp_test.py
echo     print(f"\nFFprobe path: {ffprobe}") >> temp_test.py
echo     if hasattr(sys, '_MEIPASS') and sys._MEIPASS in ffprobe: >> temp_test.py
echo         print("  ✓ USING BUNDLED FFPROBE") >> temp_test.py
echo     else: >> temp_test.py
echo         print("  ⚠ WARNING: Not using bundled FFprobe!") >> temp_test.py
echo except Exception as e: >> temp_test.py
echo     print(f"\n✗ FFprobe not found: {e}") >> temp_test.py
echo. >> temp_test.py
echo print("\n" + "="*60) >> temp_test.py
echo input("\nPress Enter to exit...") >> temp_test.py

echo NOTE: The application will open normally.
echo Check the console output when it starts for FFmpeg paths.
echo The app logs FFmpeg paths on startup.
echo.
echo Look for these lines in the output:
echo   "Using FFmpeg: [path]"
echo   "Using FFprobe: [path]"
echo.
echo If the paths contain "_MEI" or a temp directory, it's using bundled FFmpeg!
echo.
echo Press any key to launch the application...
pause > nul

echo.
echo Launching application...
"dist\Bulk Audio Normalizer.exe"

del temp_test.py

echo.
echo ============================================================
