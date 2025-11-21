#!/usr/bin/env python3
"""
Setup script to copy FFmpeg binaries into python_webview folder.

This ensures the Python version has its own FFmpeg binaries that can be:
1. Bundled with PyInstaller
2. Used independently from the Electron version
3. Easily located for the app
"""
import os
import sys
import shutil
import platform
from pathlib import Path

def main():
    """Copy FFmpeg binaries from node_modules to python_webview/bin/"""
    
    # Get paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    node_modules = project_root / 'node_modules'
    
    # Create bin directory and platform-specific subdirectory
    bin_dir = script_dir / 'bin'
    bin_dir.mkdir(exist_ok=True)
    
    system = platform.system()
    
    # Create platform-specific directory
    if system == 'Darwin':
        platform_dir = bin_dir / 'macos'
    elif system == 'Windows':
        platform_dir = bin_dir / 'windows'
    else:
        platform_dir = bin_dir / 'linux'
    platform_dir.mkdir(exist_ok=True)
    
    print(f"Platform: {system}")
    print(f"Setting up FFmpeg binaries in: {platform_dir}")
    
    # Find and copy ffmpeg
    ffmpeg_static = node_modules / 'ffmpeg-static'
    if not ffmpeg_static.exists():
        print("ERROR: ffmpeg-static not found in node_modules")
        print("Please run: npm install")
        return 1
    
    # Platform-specific paths
    if system == 'Darwin':  # macOS
        ffmpeg_src = ffmpeg_static / 'ffmpeg'
        ffmpeg_dst = platform_dir / 'ffmpeg'
        
        if not ffmpeg_src.exists():
            # Try structured path
            ffmpeg_src = ffmpeg_static / 'bin' / 'darwin' / 'universal' / 'ffmpeg'
            if not ffmpeg_src.exists():
                # Search for it
                for path in ffmpeg_static.rglob('ffmpeg'):
                    if os.access(path, os.X_OK):
                        ffmpeg_src = path
                        break
        
    elif system == 'Windows':
        ffmpeg_src = ffmpeg_static / 'ffmpeg.exe'
        ffmpeg_dst = platform_dir / 'ffmpeg.exe'
        
        if not ffmpeg_src.exists():
            # Try structured path
            ffmpeg_src = ffmpeg_static / 'bin' / 'win32' / 'x64' / 'ffmpeg.exe'
            if not ffmpeg_src.exists():
                # Search for it
                for path in ffmpeg_static.rglob('ffmpeg.exe'):
                    ffmpeg_src = path
                    break
                    
    elif system == 'Linux':
        ffmpeg_src = ffmpeg_static / 'ffmpeg'
        ffmpeg_dst = platform_dir / 'ffmpeg'
        
        if not ffmpeg_src.exists():
            for path in ffmpeg_static.rglob('ffmpeg'):
                if os.access(path, os.X_OK):
                    ffmpeg_src = path
                    break
    else:
        print(f"ERROR: Unsupported platform: {system}")
        return 1
    
    if not ffmpeg_src.exists():
        print(f"ERROR: Could not find ffmpeg binary in {ffmpeg_static}")
        return 1
    
    # Copy ffmpeg
    print(f"Copying ffmpeg: {ffmpeg_src} -> {ffmpeg_dst}")
    shutil.copy2(ffmpeg_src, ffmpeg_dst)
    
    # Make executable on Unix
    if system in ('Darwin', 'Linux'):
        os.chmod(ffmpeg_dst, 0o755)
    
    print(f"✓ FFmpeg copied successfully")
    
    # Find and copy ffprobe
    ffprobe_static = node_modules / 'ffprobe-static'
    if not ffprobe_static.exists():
        print("WARNING: ffprobe-static not found in node_modules")
        print("Trying to use system ffprobe or continuing without it")
        return 0
    
    if system == 'Darwin':
        ffprobe_src = ffprobe_static / 'bin' / 'darwin' / 'x64' / 'ffprobe'
        ffprobe_dst = platform_dir / 'ffprobe'
        
        if not ffprobe_src.exists():
            for path in ffprobe_static.rglob('ffprobe'):
                if os.access(path, os.X_OK):
                    ffprobe_src = path
                    break
                    
    elif system == 'Windows':
        ffprobe_src = ffprobe_static / 'bin' / 'win32' / 'x64' / 'ffprobe.exe'
        ffprobe_dst = platform_dir / 'ffprobe.exe'
        
        if not ffprobe_src.exists():
            for path in ffprobe_static.rglob('ffprobe.exe'):
                ffprobe_src = path
                break
                
    elif system == 'Linux':
        for path in ffprobe_static.rglob('ffprobe'):
            if os.access(path, os.X_OK):
                ffprobe_src = path
                ffprobe_dst = platform_dir / 'ffprobe'
                break
    
    if not ffprobe_src.exists():
        print(f"WARNING: Could not find ffprobe binary in {ffprobe_static}")
        return 0
    
    # Copy ffprobe
    print(f"Copying ffprobe: {ffprobe_src} -> {ffprobe_dst}")
    shutil.copy2(ffprobe_src, ffprobe_dst)
    
    # Make executable on Unix
    if system in ('Darwin', 'Linux'):
        os.chmod(ffprobe_dst, 0o755)
    
    print(f"✓ FFprobe copied successfully")
    print(f"\nSetup complete! Binaries are in: {platform_dir}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
