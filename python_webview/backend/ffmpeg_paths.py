"""
FFmpeg binary path resolution.

Tries to find FFmpeg and FFprobe from:
1. Local python_webview/bin/ directory (copied by setup_ffmpeg.py)
2. PyInstaller bundle (_MEIPASS temporary directory)
3. npm ffmpeg-static/ffprobe-static packages (from Electron version)
4. System PATH
"""
import os
import sys
import shutil
import platform
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def get_base_path():
    """
    Get the base path for the application.
    
    Returns the correct path whether running as:
    - Python script (development)
    - PyInstaller onefile bundle (Windows)
    - PyInstaller onedir bundle (macOS .app)
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in PyInstaller bundle
        return Path(sys._MEIPASS)
    else:
        # Running as normal Python script
        return Path(__file__).parent.parent


def find_local_ffmpeg() -> str:
    """
    Find ffmpeg binary in local bin directory.
    
    Returns:
        Path to ffmpeg binary or None
    """
    # Look in platform-specific bin directory (handles both development and PyInstaller bundle)
    base_path = get_base_path()
    bin_dir = base_path / 'bin'
    
    # Use platform-specific directory
    if platform.system() == 'Darwin':
        platform_dir = bin_dir / 'macos'
        ffmpeg_path = platform_dir / 'ffmpeg'
        if ffmpeg_path.exists() and os.access(ffmpeg_path, os.X_OK):
            return str(ffmpeg_path)
    elif platform.system() == 'Windows':
        platform_dir = bin_dir / 'windows'
        ffmpeg_path = platform_dir / 'ffmpeg.exe'
        if ffmpeg_path.exists():
            return str(ffmpeg_path)
    else:  # Linux
        platform_dir = bin_dir / 'linux'
        ffmpeg_path = platform_dir / 'ffmpeg'
        if ffmpeg_path.exists() and os.access(ffmpeg_path, os.X_OK):
            return str(ffmpeg_path)
    
    return None


def find_local_ffprobe() -> str:
    """
    Find ffprobe binary in local bin directory.
    
    Returns:
        Path to ffprobe binary or None
    """
    # Look in platform-specific bin directory (handles both development and PyInstaller bundle)
    base_path = get_base_path()
    bin_dir = base_path / 'bin'
    
    # Use platform-specific directory
    if platform.system() == 'Darwin':
        platform_dir = bin_dir / 'macos'
        ffprobe_path = platform_dir / 'ffprobe'
        if ffprobe_path.exists() and os.access(ffprobe_path, os.X_OK):
            return str(ffprobe_path)
    elif platform.system() == 'Windows':
        platform_dir = bin_dir / 'windows'
        ffprobe_path = platform_dir / 'ffprobe.exe'
        if ffprobe_path.exists():
            return str(ffprobe_path)
    else:  # Linux
        platform_dir = bin_dir / 'linux'
        ffprobe_path = platform_dir / 'ffprobe'
        if ffprobe_path.exists() and os.access(ffprobe_path, os.X_OK):
            return str(ffprobe_path)
    
    return None


def find_npm_ffmpeg() -> str:
    """
    Find ffmpeg binary from npm ffmpeg-static package.
    
    Returns:
        Path to ffmpeg binary or None
    """
    # Look for node_modules in parent directory (where Electron version is)
    base_dir = Path(__file__).parent.parent.parent
    node_modules = base_dir / 'node_modules'
    
    if not node_modules.exists():
        return None
        
    ffmpeg_static = node_modules / 'ffmpeg-static'
    if not ffmpeg_static.exists():
        return None
        
    # Platform-specific paths
    system = platform.system()
    
    if system == 'Windows':
        # Check structured path first
        structured = ffmpeg_static / 'bin' / 'win32' / 'x64' / 'ffmpeg.exe'
        if structured.exists():
            return str(structured)
        # Fallback to any ffmpeg.exe in the directory
        for path in ffmpeg_static.rglob('ffmpeg.exe'):
            return str(path)
    elif system == 'Darwin':  # macOS
        structured = ffmpeg_static / 'bin' / 'darwin' / 'universal' / 'ffmpeg'
        if structured.exists():
            return str(structured)
        # Fallback
        for path in ffmpeg_static.rglob('ffmpeg'):
            if os.access(path, os.X_OK):
                return str(path)
    else:  # Linux
        for path in ffmpeg_static.rglob('ffmpeg'):
            if os.access(path, os.X_OK):
                return str(path)
                
    return None


def find_npm_ffprobe() -> str:
    """
    Find ffprobe binary from npm ffprobe-static package.
    
    Returns:
        Path to ffprobe binary or None
    """
    base_dir = Path(__file__).parent.parent.parent
    node_modules = base_dir / 'node_modules'
    
    if not node_modules.exists():
        return None
        
    ffprobe_static = node_modules / 'ffprobe-static'
    if not ffprobe_static.exists():
        return None
        
    system = platform.system()
    
    if system == 'Windows':
        structured = ffprobe_static / 'bin' / 'win32' / 'x64' / 'ffprobe.exe'
        if structured.exists():
            return str(structured)
        for path in ffprobe_static.rglob('ffprobe.exe'):
            return str(path)
    elif system == 'Darwin':
        structured = ffprobe_static / 'bin' / 'darwin' / 'universal' / 'ffprobe'
        if structured.exists():
            return str(structured)
        for path in ffprobe_static.rglob('ffprobe'):
            if os.access(path, os.X_OK):
                return str(path)
    else:  # Linux
        for path in ffprobe_static.rglob('ffprobe'):
            if os.access(path, os.X_OK):
                return str(path)
                
    return None


def get_ffmpeg_path() -> str:
    """
    Get ffmpeg binary path.
    
    Returns:
        Path to ffmpeg binary
        
    Raises:
        RuntimeError: If ffmpeg not found
    """
    # Try local bin directory first
    local_path = find_local_ffmpeg()
    if local_path:
        logger.info(f"Using local ffmpeg: {local_path}")
        return local_path
    
    # Try npm package
    npm_path = find_npm_ffmpeg()
    if npm_path:
        logger.info(f"Using npm ffmpeg: {npm_path}")
        return npm_path
        
    # Try system PATH
    system_path = shutil.which('ffmpeg')
    if system_path:
        logger.info(f"Using system ffmpeg: {system_path}")
        return system_path
        
    raise RuntimeError(
        "ffmpeg not found. Please run 'python3 python_webview/setup_ffmpeg.py' "
        "or install ffmpeg on your system."
    )


def get_ffprobe_path() -> str:
    """
    Get ffprobe binary path.
    
    Returns:
        Path to ffprobe binary
        
    Raises:
        RuntimeError: If ffprobe not found
    """
    # Try local bin directory first
    local_path = find_local_ffprobe()
    if local_path:
        logger.info(f"Using local ffprobe: {local_path}")
        return local_path
    
    # Try npm package
    npm_path = find_npm_ffprobe()
    if npm_path:
        logger.info(f"Using npm ffprobe: {npm_path}")
        return npm_path
        
    # Try system PATH
    system_path = shutil.which('ffprobe')
    if system_path:
        logger.info(f"Using system ffprobe: {system_path}")
        return system_path
        
    raise RuntimeError(
        "ffprobe not found. Please run 'python3 python_webview/setup_ffmpeg.py' "
        "or install ffmpeg on your system."
    )
