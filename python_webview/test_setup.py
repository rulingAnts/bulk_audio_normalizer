#!/usr/bin/env python3
"""
Simple test script to verify FFmpeg path resolution.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ffmpeg_paths():
    """Test FFmpeg path resolution."""
    print("Testing FFmpeg path resolution...")
    
    try:
        from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path
        
        ffmpeg = get_ffmpeg_path()
        print(f"✓ FFmpeg found: {ffmpeg}")
        
        ffprobe = get_ffprobe_path()
        print(f"✓ FFprobe found: {ffprobe}")
        
        # Check if files exist
        import os
        if os.path.exists(ffmpeg):
            print(f"✓ FFmpeg file exists")
        else:
            print(f"✗ FFmpeg file not found at {ffmpeg}")
            
        if os.path.exists(ffprobe):
            print(f"✓ FFprobe file exists")
        else:
            print(f"✗ FFprobe file not found at {ffprobe}")
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTo fix this, either:")
        print("1. Run 'npm install' in the parent directory to install ffmpeg-static")
        print("2. Install FFmpeg on your system (apt install ffmpeg, brew install ffmpeg, etc.)")
        return False


def test_imports():
    """Test that all modules can be imported."""
    print("\nTesting module imports...")
    
    modules = [
        'backend.process_manager',
        'backend.audio_processor',
        'backend.ffmpeg_paths',
        'backend.api',
    ]
    
    all_ok = True
    for module in modules:
        try:
            __import__(module)
            print(f"✓ {module}")
        except Exception as e:
            print(f"✗ {module}: {e}")
            all_ok = False
            
    return all_ok


def test_process_manager():
    """Test process manager."""
    print("\nTesting process manager...")
    
    try:
        from backend.process_manager import process_manager
        
        # Test basic functionality
        print("✓ ProcessManager imported")
        print(f"✓ Cancel flag: {process_manager.cancel_all}")
        print(f"✓ Active processes: {len(process_manager.active_processes)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


if __name__ == '__main__':
    print("Bulk Audio Normalizer - Python WebView Version")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Module imports", test_imports()))
    results.append(("Process manager", test_process_manager()))
    results.append(("FFmpeg paths", test_ffmpeg_paths()))
    
    print()
    print("=" * 50)
    print("Test Results:")
    print()
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
            
    print()
    if all_passed:
        print("All tests passed! The Python version should work correctly.")
    else:
        print("Some tests failed. Please fix the issues above.")
        sys.exit(1)
