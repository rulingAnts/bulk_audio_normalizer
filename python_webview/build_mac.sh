#!/bin/bash
# Build script for macOS
# Creates a .app bundle with PyInstaller

set -e

echo "🍎 Building Bulk Audio Normalizer for macOS..."

# Check if we're in the right directory
if [ ! -f "main.py" ]; then
    echo "❌ Error: Run this script from the python_webview directory"
    exit 1
fi

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null; then
    echo "📦 PyInstaller not found. Installing..."
    pip3 install pyinstaller
fi

# Check if FFmpeg binaries exist
# Built from FFmpeg's source, not taken from npm: ffmpeg-static's darwin-arm64
# ffmpeg is a nonfree build that may not be redistributed, and ffprobe-static
# has no arm64 ffprobe. See build_ffmpeg_mac.sh.
if [ ! -f "bin/macos/ffmpeg" ] || [ ! -f "bin/macos/ffprobe" ]; then
    echo "📦 macOS FFmpeg binaries not found. Running build_ffmpeg_mac.sh..."
    ./build_ffmpeg_mac.sh
fi

# Clean previous macOS builds only
echo "🧹 Cleaning previous macOS builds..."
rm -rf build/macos dist/macos

# Build with PyInstaller
echo "🔨 Building application..."
pyinstaller --distpath dist/macos --workpath build/macos bulk_audio_normalizer.spec

# Check if build was successful
if [ ! -d "dist/macos/Bulk Audio Normalizer.app" ]; then
    echo "❌ Build failed - .app bundle not created"
    exit 1
fi

echo "✅ Build complete!"
echo ""
echo "Application built at: dist/macos/Bulk Audio Normalizer.app"
echo ""
echo "To create a DMG:"
echo "  1. Install create-dmg: brew install create-dmg"
echo "  2. Run: ./create_dmg_mac.sh"
echo ""
echo "To test the app:"
echo "  open \"dist/macos/Bulk Audio Normalizer.app\""
