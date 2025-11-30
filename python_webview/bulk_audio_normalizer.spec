# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Bulk Audio Normalizer
Builds for both Windows and macOS
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Detect platform
is_windows = sys.platform.startswith('win')
is_macos = sys.platform == 'darwin'

# Platform-specific output directories
if is_windows:
    DISTPATH = 'dist/windows'
    BUILDPATH = 'build/windows'
else:
    DISTPATH = 'dist/macos'
    BUILDPATH = 'build/macos'

# Collect all frontend files
frontend_datas = []
frontend_dir = 'frontend'
for root, dirs, files in os.walk(frontend_dir):
    for file in files:
        src = os.path.join(root, file)
        dst = os.path.dirname(src)
        frontend_datas.append((src, dst))

# Collect FFmpeg binaries (platform-specific, preserving directory structure)
ffmpeg_datas = []
if is_windows:
    # Use Windows binaries - keep them in bin/windows/
    if os.path.exists('bin/windows/ffmpeg.exe'):
        ffmpeg_datas.append(('bin/windows/ffmpeg.exe', 'bin/windows'))
    if os.path.exists('bin/windows/ffprobe.exe'):
        ffmpeg_datas.append(('bin/windows/ffprobe.exe', 'bin/windows'))
else:
    # Use macOS/Linux binaries - keep them in bin/macos/
    if os.path.exists('bin/macos/ffmpeg'):
        ffmpeg_datas.append(('bin/macos/ffmpeg', 'bin/macos'))
    if os.path.exists('bin/macos/ffprobe'):
        ffmpeg_datas.append(('bin/macos/ffprobe', 'bin/macos'))

# Collect all backend modules
backend_modules = collect_submodules('backend')

# Hidden imports
hidden_imports = [
    'webview',
    'webview.platforms.cocoa',
    'webview.platforms.winforms',
    'bottle',
    'backend.audio_processor',
    'backend.process_manager',
    'backend.ffmpeg_paths',
] + backend_modules

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=frontend_datas + ffmpeg_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Set platform-specific paths
a.distpath = DISTPATH
a.buildpath = BUILDPATH

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if is_windows:
    # Windows: single executable file
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='Bulk Audio Normalizer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,  # No console window for production
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None,
    )
else:
    # macOS: app bundle (onedir)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='Bulk Audio Normalizer',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,  # No console window
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='Bulk Audio Normalizer',
    )
    
    app = BUNDLE(
        coll,
        name='Bulk Audio Normalizer.app',
        icon='assets/icon.icns' if os.path.exists('assets/icon.icns') else None,
        bundle_identifier='com.bulkaudionormalizer.app',
        info_plist={
            'NSPrincipleClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleName': 'Bulk Audio Normalizer',
            'CFBundleDisplayName': 'Bulk Audio Normalizer',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSRequiresAquaSystemAppearance': 'False',
        },
    )
