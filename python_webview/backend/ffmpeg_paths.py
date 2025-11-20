"""
FFmpeg binary path resolution.

Tries to find FFmpeg and FFprobe from:
1. npm ffmpeg-static/ffprobe-static packages (from Electron version)
2. System PATH
"""
import os
import sys
import shutil
import platform
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


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
    # Try npm package first
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
        "ffmpeg not found. Please install ffmpeg or run 'npm install' "
        "in the parent directory to install ffmpeg-static package."
    )


def get_ffprobe_path() -> str:
    """
    Get ffprobe binary path.
    
    Returns:
        Path to ffprobe binary
        
    Raises:
        RuntimeError: If ffprobe not found
    """
    # Try npm package first
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
        "ffprobe not found. Please install ffmpeg or run 'npm install' "
        "in the parent directory to install ffprobe-static package."
    )
