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
if [ ! -f "bin/macos/ffmpeg" ] || [ ! -f "bin/macos/ffprobe" ]; then
    echo "📦 macOS FFmpeg binaries not found. Running setup_ffmpeg.py..."
    python3 setup_ffmpeg.py
    # Move binaries to macos directory if they were created in bin/
    if [ -f "bin/ffmpeg" ] && [ ! -f "bin/macos/ffmpeg" ]; then
        mkdir -p bin/macos
        cp bin/ffmpeg bin/macos/
        cp bin/ffprobe bin/macos/
    fi
fi

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf build dist

# Build with PyInstaller
echo "🔨 Building application..."
pyinstaller bulk_audio_normalizer.spec

# Check if build was successful
if [ ! -d "dist/BulkAudioNormalizer.app" ]; then
    echo "❌ Build failed - .app bundle not created"
    exit 1
fi

echo "✅ Build complete!"
echo ""
echo "Application built at: dist/BulkAudioNormalizer.app"
echo ""
echo "To create a DMG:"
echo "  1. Install create-dmg: brew install create-dmg"
echo "  2. Run: ./create_dmg_mac.sh"
echo ""
echo "To test the app:"
echo "  open dist/BulkAudioNormalizer.app"
