"""
Diagnostic script to test FFmpeg path resolution in the bundle.
Run this with the bundled executable to see what's happening.
"""
import sys
import os
from pathlib import Path

print("=" * 80)
print("FFmpeg Bundle Diagnostic")
print("=" * 80)

# Check frozen state
is_frozen = getattr(sys, 'frozen', False)
has_meipass = hasattr(sys, '_MEIPASS')

print(f"\n1. Python Environment:")
print(f"   - Frozen: {is_frozen}")
print(f"   - Has _MEIPASS: {has_meipass}")

if has_meipass:
    meipass = sys._MEIPASS
    print(f"   - _MEIPASS: {meipass}")
    
    print(f"\n2. Contents of _MEIPASS:")
    try:
        items = sorted(os.listdir(meipass))
        for item in items[:20]:  # First 20 items
            item_path = os.path.join(meipass, item)
            if os.path.isdir(item_path):
                print(f"   - {item}/ (directory)")
            else:
                print(f"   - {item}")
        if len(items) > 20:
            print(f"   ... and {len(items) - 20} more items")
    except Exception as e:
        print(f"   ERROR listing _MEIPASS: {e}")
    
    print(f"\n3. Looking for bin directory:")
    bin_dir = os.path.join(meipass, 'bin')
    print(f"   - Path: {bin_dir}")
    print(f"   - Exists: {os.path.exists(bin_dir)}")
    
    if os.path.exists(bin_dir):
        print(f"   - Contents:")
        try:
            for item in os.listdir(bin_dir):
                item_path = os.path.join(bin_dir, item)
                if os.path.isdir(item_path):
                    print(f"     - {item}/ (directory)")
                    # List contents of subdirectory
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        size = os.path.getsize(subitem_path) if os.path.isfile(subitem_path) else 0
                        print(f"       - {subitem} ({size:,} bytes)")
                else:
                    size = os.path.getsize(item_path)
                    print(f"     - {item} ({size:,} bytes)")
        except Exception as e:
            print(f"     ERROR: {e}")
    
    print(f"\n4. Looking for bin/windows directory:")
    bin_windows = os.path.join(meipass, 'bin', 'windows')
    print(f"   - Path: {bin_windows}")
    print(f"   - Exists: {os.path.exists(bin_windows)}")
    
    if os.path.exists(bin_windows):
        print(f"   - Contents:")
        try:
            for item in os.listdir(bin_windows):
                item_path = os.path.join(bin_windows, item)
                size = os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                print(f"     - {item} ({size:,} bytes)")
        except Exception as e:
            print(f"     ERROR: {e}")
    
    print(f"\n5. Direct FFmpeg check:")
    ffmpeg_path = os.path.join(meipass, 'bin', 'windows', 'ffmpeg.exe')
    ffprobe_path = os.path.join(meipass, 'bin', 'windows', 'ffprobe.exe')
    print(f"   - ffmpeg.exe: {os.path.exists(ffmpeg_path)} ({ffmpeg_path})")
    print(f"   - ffprobe.exe: {os.path.exists(ffprobe_path)} ({ffprobe_path})")

else:
    print(f"\n   Not running in bundle (development mode)")
    script_dir = Path(__file__).parent
    print(f"   Script directory: {script_dir}")
    bin_dir = script_dir / 'bin' / 'windows'
    print(f"   Expected bin/windows: {bin_dir}")
    print(f"   Exists: {bin_dir.exists()}")

print(f"\n6. Testing backend.ffmpeg_paths module:")
try:
    from backend.ffmpeg_paths import get_base_path, find_local_ffmpeg, find_local_ffprobe
    
    base_path = get_base_path()
    print(f"   - get_base_path(): {base_path}")
    
    ffmpeg = find_local_ffmpeg()
    print(f"   - find_local_ffmpeg(): {ffmpeg}")
    if ffmpeg:
        print(f"     - Exists: {os.path.exists(ffmpeg)}")
        if os.path.exists(ffmpeg):
            print(f"     - Size: {os.path.getsize(ffmpeg):,} bytes")
    
    ffprobe = find_local_ffprobe()
    print(f"   - find_local_ffprobe(): {ffprobe}")
    if ffprobe:
        print(f"     - Exists: {os.path.exists(ffprobe)}")
        if os.path.exists(ffprobe):
            print(f"     - Size: {os.path.getsize(ffprobe):,} bytes")
            
except Exception as e:
    print(f"   ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
input("\nPress Enter to exit...")
