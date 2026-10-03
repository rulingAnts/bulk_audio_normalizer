#!/bin/bash
# Build the ffmpeg and ffprobe that the macOS app bundles, from FFmpeg's own
# source, for this Mac's architecture (arm64 on Apple silicon).
#
# Why not the npm packages? ffmpeg-static's darwin-arm64 ffmpeg (FFmpeg 6.0)
# is configured with --enable-nonfree, and "ffmpeg -L" says it is "not legally
# redistributable"; ffprobe-static has no arm64 ffprobe at all (its
# bin/darwin/arm64/ffprobe is an x86_64 file, which needs Rosetta).
#
# This build:
#   - LGPL v2.1+ only: no --enable-gpl, --enable-version3 or --enable-nonfree;
#   - no external libraries (--disable-autodetect), so nothing from Homebrew
#     is linked in; the binaries depend only on macOS system libraries;
#   - every native FFmpeg decoder, demuxer and filter, which covers what the
#     app runs (WAV in, PCM WAV out; loudnorm, alimiter, volume, volumedetect,
#     silencedetect, highpass).
#
# Usage (from python_webview/):
#   ./build_ffmpeg_mac.sh
# Environment:
#   FFMPEG_TAG     FFmpeg release tag to build (default n6.1.6)
#   FFMPEG_COMMIT  the commit that tag must point at; the build stops if the
#                  checkout differs (default: f1e3a2bf..., FFmpeg's n6.1.6)
#   FFMPEG_GIT     where to clone from (default https://git.ffmpeg.org/ffmpeg.git;
#                  https://github.com/FFmpeg/FFmpeg.git is FFmpeg's own mirror)
#   FFMPEG_SRC     an existing checkout of that tag (default: clone one)
#   FFMPEG_WORK    scratch directory (default build/ffmpeg)
#   MACOS_MIN      minimum macOS version (default 11.0, the app's own minimum)
#
# Redistribution (the LGPL, and FFmpeg's checklist at ffmpeg.org/legal.html):
#   - bin/macos/ also gets COPYING.LGPLv2.1 and FFMPEG-NOTICE.txt, which the
#     app bundles next to the binaries;
#   - the exact source that was built, plus BUILD-INFO.txt with the configure
#     line, is written to $FFMPEG_WORK/ffmpeg-<version>-source.tar.xz. Attach it
#     to the same GitHub release as the .dmg (same place as the binary).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FFMPEG_TAG="${FFMPEG_TAG:-n6.1.6}"
FFMPEG_GIT="${FFMPEG_GIT:-https://git.ffmpeg.org/ffmpeg.git}"
if [ -z "${FFMPEG_COMMIT+set}" ] && [ "$FFMPEG_TAG" = n6.1.6 ]; then
    FFMPEG_COMMIT=f1e3a2bf7a2f2cde936d1ed97f09a26853d20125
fi
FFMPEG_WORK="${FFMPEG_WORK:-$SCRIPT_DIR/build/ffmpeg}"
MACOS_MIN="${MACOS_MIN:-11.0}"
OUT_DIR="$SCRIPT_DIR/bin/macos"
ARCH="$(uname -m)"   # arm64 or x86_64

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script builds the macOS binaries; run it on a Mac." >&2
    exit 1
fi

mkdir -p "$FFMPEG_WORK"

if [ -z "${FFMPEG_SRC:-}" ]; then
    FFMPEG_SRC="$FFMPEG_WORK/src-$FFMPEG_TAG"
    if [ ! -f "$FFMPEG_SRC/configure" ]; then
        echo "Fetching FFmpeg $FFMPEG_TAG source..."
        git -c advice.detachedHead=false clone --depth 1 --branch "$FFMPEG_TAG" \
            "$FFMPEG_GIT" "$FFMPEG_SRC"
    fi
fi
FFMPEG_SRC="$(cd "$FFMPEG_SRC" && pwd)"

if [ -n "${FFMPEG_COMMIT:-}" ]; then
    head="$(git -C "$FFMPEG_SRC" rev-parse HEAD 2>/dev/null || echo none)"
    if [ "$head" != "$FFMPEG_COMMIT" ]; then
        echo "FFmpeg checkout is at $head, expected $FFMPEG_COMMIT for $FFMPEG_TAG." >&2
        exit 1
    fi
fi

BUILD_DIR="$FFMPEG_WORK/build-$FFMPEG_TAG-$ARCH"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

CONFIGURE_FLAGS=(
    --cc=clang
    --arch="$ARCH"
    --disable-autodetect
    --enable-pthreads
    --disable-ffplay
    --disable-doc
    --extra-cflags="-mmacosx-version-min=$MACOS_MIN"
    --extra-ldflags="-mmacosx-version-min=$MACOS_MIN"
)
echo "Configuring FFmpeg $FFMPEG_TAG for $ARCH (macOS $MACOS_MIN+)..."
"$FFMPEG_SRC/configure" "${CONFIGURE_FLAGS[@]}" | tee configure.log

echo "Building..."
make -j"$(sysctl -n hw.ncpu)" ffmpeg ffprobe > make.log 2>&1 || {
    tail -40 make.log >&2
    exit 1
}

# ---- checks: refuse to hand over anything we would not ship ----
# Each tool's output is captured before grepping it, so an early-exiting
# "grep -q" can never SIGPIPE the producer and flip a check under pipefail.
fail() { echo "FAILED: $*" >&2; exit 1; }
has() { grep -q -E -- "$2" <<< "$1"; }

for bin in ffmpeg ffprobe; do
    desc="$(file "$bin")"
    has "$desc" "Mach-O 64-bit executable $ARCH\$" \
        || fail "$bin is not a thin $ARCH executable: $desc"
    libs="$(otool -L "$bin" | tail -n +2 | awk '{print $1}')"
    other="$(grep -v -E '^(/usr/lib/|/System/Library/)' <<< "$libs" || true)"
    if [ -n "$other" ]; then
        fail "$bin links a library outside /usr/lib and /System/Library: $other"
    fi
    lic="$("./$bin" -hide_banner -L 2>&1)"
    if has "$lic" '[Nn]onfree'; then fail "$bin reports nonfree parts"; fi
    conf="$("./$bin" -hide_banner -buildconf 2>&1)"
    if has "$conf" '--enable-(nonfree|gpl|version3)'; then
        fail "$bin was configured with a GPL/version3/nonfree flag"
    fi
done

has "$("./ffmpeg" -hide_banner -L 2>&1)" 'GNU Lesser General Public' \
    || fail "ffmpeg does not report the LGPL"

filters="$(./ffmpeg -hide_banner -filters 2>/dev/null)"
for f in loudnorm alimiter volume volumedetect silencedetect highpass aresample; do
    has "$filters" "^ [^ ]+ $f " || fail "filter $f missing"
done
encoders="$(./ffmpeg -hide_banner -encoders 2>/dev/null)"
for e in pcm_u8 pcm_s16le pcm_s24le pcm_s32le pcm_f32le pcm_f64le; do
    has "$encoders" "^ [^ ]+ $e " || fail "encoder $e missing"
done
muxers="$(./ffmpeg -hide_banner -muxers 2>/dev/null)"
has "$muxers" '^ +E +wav ' || fail "wav muxer missing"
has "$muxers" '^ +E +null ' || fail "null muxer missing"
has "$(./ffmpeg -hide_banner -demuxers 2>/dev/null)" '^ +D +wav ' || fail "wav demuxer missing"
has "$(./ffprobe -hide_banner -demuxers 2>/dev/null)" '^ +D +wav ' || fail "ffprobe: wav demuxer missing"

mkdir -p "$OUT_DIR"
# Remove, then copy: "cp -f" over a binary that has already run rewrites it
# in place (same inode), and macOS then kills the new one on launch (exit 137)
# because the kernel still holds the old code signature for that file.
rm -f "$OUT_DIR/ffmpeg" "$OUT_DIR/ffprobe"
cp ffmpeg ffprobe "$OUT_DIR/"
chmod 755 "$OUT_DIR/ffmpeg" "$OUT_DIR/ffprobe"

# ---- what the LGPL asks to travel with the binaries ----
VERSION="$(tr -d '[:space:]' < "$FFMPEG_SRC/RELEASE")"
COMMIT="$(git -C "$FFMPEG_SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
CONFIG_LINE="./configure ${CONFIGURE_FLAGS[*]}"
SOURCE_NAME="ffmpeg-$VERSION-source.tar.xz"

cp "$FFMPEG_SRC/COPYING.LGPLv2.1" "$OUT_DIR/COPYING.LGPLv2.1"
cat > "$OUT_DIR/FFMPEG-NOTICE.txt" <<NOTICE
FFmpeg in Bulk Audio Normalizer for macOS

This software uses code of FFmpeg (https://ffmpeg.org), licensed under the
GNU Lesser General Public License, version 2.1 or later. Its source can be
downloaded from the release page this app came from, as $SOURCE_NAME,
and from https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz.

The ffmpeg and ffprobe programs next to this file are FFmpeg $VERSION
(git tag $FFMPEG_TAG, commit $COMMIT), unmodified, built for $ARCH with:

  $CONFIG_LINE

No external libraries are linked in. The full license text is in
COPYING.LGPLv2.1 next to this file.

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.
NOTICE

# The exact source that was built, with the configure line at its root.
if git -C "$FFMPEG_SRC" rev-parse --git-dir > /dev/null 2>&1; then
    changes="$(git -C "$FFMPEG_SRC" status --porcelain --untracked-files=no)"
    [ -z "$changes" ] || fail "the FFmpeg checkout has local changes; the source archive must match the build"
    cat > "$BUILD_DIR/BUILD-INFO.txt" <<INFO
FFmpeg $VERSION (git tag $FFMPEG_TAG, commit $COMMIT), unmodified.

Built for macOS ($ARCH, macOS $MACOS_MIN or later) by build_ffmpeg_mac.sh in
https://github.com/rulingAnts/bulk_audio_normalizer (python_webview/), with:

  $CONFIG_LINE
  make ffmpeg ffprobe

License: GNU Lesser General Public License, version 2.1 or later.
INFO
    git -C "$FFMPEG_SRC" archive --format=tar --prefix="ffmpeg-$VERSION/" \
        --add-file="$BUILD_DIR/BUILD-INFO.txt" HEAD | xz -9 > "$FFMPEG_WORK/$SOURCE_NAME"
else
    echo "WARNING: $FFMPEG_SRC is not a git checkout; make $SOURCE_NAME by hand." >&2
fi

echo ""
echo "Installed to $OUT_DIR:"
for bin in ffmpeg ffprobe; do
    ver="$("$OUT_DIR/$bin" -hide_banner -version)" || fail "installed $bin does not run"
    echo "  $(file "$OUT_DIR/$bin" | sed "s#$OUT_DIR/##")"
    echo "    $(head -1 <<< "$ver")"
done
echo "  License: LGPL version 2.1 or later (no GPL, version3 or nonfree parts)"
echo "  Notices: $OUT_DIR/COPYING.LGPLv2.1, $OUT_DIR/FFMPEG-NOTICE.txt"
if [ -f "$FFMPEG_WORK/$SOURCE_NAME" ]; then
    echo ""
    echo "Source to attach to the release (next to the .dmg):"
    echo "  $FFMPEG_WORK/$SOURCE_NAME"
    echo "  sha256 $(shasum -a 256 "$FFMPEG_WORK/$SOURCE_NAME" | cut -d' ' -f1)"
fi
