#!/bin/bash
# Test script to verify PyInstaller build
# Tests FFmpeg detection in bundled environment

echo "🧪 Testing PyInstaller Build Configuration"
echo "=========================================="
echo ""

# Check Python
echo "1. Checking Python..."
python3 --version || { echo "❌ Python 3 not found"; exit 1; }
echo "✅ Python OK"
echo ""

# Check PyInstaller
echo "2. Checking PyInstaller..."
pyinstaller --version || { echo "❌ PyInstaller not found. Run: pip3 install pyinstaller"; exit 1; }
echo "✅ PyInstaller OK"
echo ""

# Check FFmpeg binaries
echo "3. Checking FFmpeg binaries..."
if [ ! -f "bin/macos/ffmpeg" ]; then
    echo "⚠️  bin/macos/ffmpeg not found"
    echo "   Run: python3 setup_ffmpeg.py"
    MISSING_FFMPEG=1
else
    echo "✅ bin/macos/ffmpeg found"
fi

if [ ! -f "bin/macos/ffprobe" ]; then
    echo "⚠️  bin/macos/ffprobe not found"
    echo "   Run: python3 setup_ffmpeg.py"
    MISSING_FFMPEG=1
else
    echo "✅ bin/macos/ffprobe found"
fi

if [ -n "$MISSING_FFMPEG" ]; then
    echo ""
    echo "Setting up FFmpeg..."
    python3 setup_ffmpeg.py || { echo "❌ FFmpeg setup failed"; exit 1; }
    # Move binaries to macos directory
    mkdir -p bin/macos
    if [ -f "bin/ffmpeg" ]; then
        cp bin/ffmpeg bin/macos/
        cp bin/ffprobe bin/macos/
    fi
fi
echo ""

# Check frontend files
echo "4. Checking frontend files..."
FRONTEND_FILES=(
    "frontend/index.html"
    "frontend/styles.css"
    "frontend/renderer.js"
    "frontend/api_adapter.js"
    "frontend/preview.html"
    "frontend/preview.js"
    "frontend/preview_adapter.js"
)

for file in "${FRONTEND_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        exit 1
    fi
done
echo "✅ All frontend files present"
echo ""

# Check backend files
echo "5. Checking backend files..."
BACKEND_FILES=(
    "backend/__init__.py"
    "backend/audio_processor.py"
    "backend/process_manager.py"
    "backend/ffmpeg_paths.py"
)

for file in "${BACKEND_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing: $file"
        exit 1
    fi
done
echo "✅ All backend files present"
echo ""

# Check spec file
echo "6. Checking spec file..."
if [ ! -f "bulk_audio_normalizer.spec" ]; then
    echo "❌ bulk_audio_normalizer.spec not found"
    exit 1
fi
echo "✅ Spec file present"
echo ""

# Test FFmpeg path resolution
echo "7. Testing FFmpeg path resolution..."
python3 -c "
from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path
try:
    ffmpeg = get_ffmpeg_path()
    ffprobe = get_ffprobe_path()
    print(f'✅ FFmpeg: {ffmpeg}')
    print(f'✅ FFprobe: {ffprobe}')
except Exception as e:
    print(f'❌ Error: {e}')
    exit(1)
" || exit 1
echo ""

# Summary
echo "=========================================="
echo "✅ All checks passed!"
echo ""
echo "Ready to build:"
echo "  macOS:   ./build_mac.sh"
echo "  Windows: build_windows.bat"
echo ""
