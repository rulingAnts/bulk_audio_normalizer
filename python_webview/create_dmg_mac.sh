#!/bin/bash
# Create DMG installer for macOS
# Requires create-dmg: brew install create-dmg

set -e

echo "💿 Creating DMG installer for macOS..."

# Check if .app bundle exists
if [ ! -d "dist/Bulk Audio Normalizer.app" ]; then
    echo "❌ Error: dist/Bulk Audio Normalizer.app not found"
    echo "Run ./build_mac.sh first"
    exit 1
fi

# Check if create-dmg is installed
if ! command -v create-dmg &> /dev/null; then
    echo "❌ create-dmg not found"
    echo "Install with: brew install create-dmg"
    exit 1
fi

# Clean previous DMG
rm -f dist/BulkAudioNormalizer.dmg

# Create DMG
echo "🔨 Creating DMG..."
create-dmg \
  --volname "Bulk Audio Normalizer" \
  --volicon "assets/icon.icns" \
  --window-pos 200 120 \
  --window-size 600 400 \
  --icon-size 100 \
  --icon "Bulk Audio Normalizer.app" 175 120 \
  --hide-extension "Bulk Audio Normalizer.app" \
  --app-drop-link 425 120 \
  "dist/Bulk Audio Normalizer.dmg" \
  "dist/Bulk Audio Normalizer.app" \
  || true  # create-dmg returns non-zero even on success sometimes

# Check if DMG was created
if [ -f "dist/Bulk Audio Normalizer.dmg" ]; then
    echo "✅ DMG created successfully!"
    echo ""
    echo "DMG location: dist/Bulk Audio Normalizer.dmg"
    echo "Size: $(du -h "dist/Bulk Audio Normalizer.dmg" | cut -f1)"
else
    echo "❌ DMG creation failed"
    exit 1
fi
