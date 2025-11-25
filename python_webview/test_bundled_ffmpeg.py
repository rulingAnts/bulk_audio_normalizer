"""
Test script to verify the bundled executable uses included FFmpeg binaries.

This script checks that the application is using the bundled FFmpeg/FFprobe
and not the system versions.
"""
import sys
import os
from pathlib import Path

# Add the backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path, get_base_path

def test_bundled_ffmpeg():
    """Test that bundled FFmpeg paths are correct."""
    
    print("=" * 60)
    print("FFmpeg Bundle Test")
    print("=" * 60)
    
    # Check if running in PyInstaller bundle
    is_frozen = getattr(sys, 'frozen', False)
    has_meipass = hasattr(sys, '_MEIPASS')
    
    print(f"\nRunning as frozen executable: {is_frozen}")
    print(f"Has _MEIPASS attribute: {has_meipass}")
    
    if has_meipass:
        print(f"_MEIPASS location: {sys._MEIPASS}")
    
    # Get base path
    base_path = get_base_path()
    print(f"\nBase path: {base_path}")
    
    # Get FFmpeg path
    try:
        ffmpeg_path = get_ffmpeg_path()
        print(f"\n✓ FFmpeg found at: {ffmpeg_path}")
        
        # Check if it's bundled (not from system PATH)
        if is_frozen and has_meipass:
            if sys._MEIPASS in ffmpeg_path:
                print("  ✓ Using BUNDLED FFmpeg from _MEIPASS")
            else:
                print("  ⚠ WARNING: Using FFmpeg from outside bundle!")
                print(f"    Expected path to contain: {sys._MEIPASS}")
        else:
            # Development mode
            if 'bin' in ffmpeg_path and ('windows' in ffmpeg_path or 'macos' in ffmpeg_path):
                print("  ✓ Using LOCAL FFmpeg from bin/ directory")
            else:
                print(f"  ℹ Using system FFmpeg (development mode)")
        
        # Check if file exists
        if os.path.exists(ffmpeg_path):
            file_size = os.path.getsize(ffmpeg_path) / (1024 * 1024)
            print(f"  File size: {file_size:.1f} MB")
        else:
            print("  ✗ ERROR: File does not exist!")
            
    except Exception as e:
        print(f"\n✗ FFmpeg not found: {e}")
    
    # Get FFprobe path
    try:
        ffprobe_path = get_ffprobe_path()
        print(f"\n✓ FFprobe found at: {ffprobe_path}")
        
        # Check if it's bundled
        if is_frozen and has_meipass:
            if sys._MEIPASS in ffprobe_path:
                print("  ✓ Using BUNDLED FFprobe from _MEIPASS")
            else:
                print("  ⚠ WARNING: Using FFprobe from outside bundle!")
                print(f"    Expected path to contain: {sys._MEIPASS}")
        else:
            # Development mode
            if 'bin' in ffprobe_path and ('windows' in ffprobe_path or 'macos' in ffprobe_path):
                print("  ✓ Using LOCAL FFprobe from bin/ directory")
            else:
                print(f"  ℹ Using system FFprobe (development mode)")
        
        # Check if file exists
        if os.path.exists(ffprobe_path):
            file_size = os.path.getsize(ffprobe_path) / (1024 * 1024)
            print(f"  File size: {file_size:.1f} MB")
        else:
            print("  ✗ ERROR: File does not exist!")
            
    except Exception as e:
        print(f"\n✗ FFprobe not found: {e}")
    
    print("\n" + "=" * 60)
    
    # Final verdict
    if is_frozen and has_meipass:
        try:
            ffmpeg_ok = sys._MEIPASS in get_ffmpeg_path()
            ffprobe_ok = sys._MEIPASS in get_ffprobe_path()
            
            if ffmpeg_ok and ffprobe_ok:
                print("RESULT: ✓ PASS - Using bundled FFmpeg binaries")
                return True
            else:
                print("RESULT: ✗ FAIL - Not using bundled FFmpeg binaries")
                return False
        except Exception as e:
            print(f"RESULT: ✗ FAIL - {e}")
            return False
    else:
        print("RESULT: ℹ Running in development mode (not frozen)")
        return True

if __name__ == '__main__':
    success = test_bundled_ffmpeg()
    sys.exit(0 if success else 1)
