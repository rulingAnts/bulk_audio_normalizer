#!/bin/bash
# Build the ffmpeg.exe and ffprobe.exe that the Windows app bundles, from FFmpeg's
# own source, cross-compiled for 64-bit Windows (x86-64) on Linux with mingw-w64.
# build-windows.yml runs it on ubuntu-latest; the Windows job then tests and bundles
# the result.
#
# Why not the npm packages? ffmpeg-static's Windows ffmpeg (gyan.dev 6.1.1) and
# ffprobe-static's ffprobe (4.0.2) are GPLv3 builds that link dozens of GPL
# libraries, whose complete source we would have to offer; and they are two
# different FFmpeg versions. This build matches the macOS one (build_ffmpeg_mac.sh):
#   - LGPL v2.1+ only: no --enable-gpl, --enable-version3 or --enable-nonfree;
#   - no external libraries (--disable-autodetect); statically linked against the
#     mingw-w64 runtime and libgcc (runtime exception), so the .exe files need only
#     DLLs that ship with Windows;
#   - every native FFmpeg decoder, demuxer and filter, which covers what the app
#     runs (WAV in, PCM WAV out; loudnorm, alimiter, volume, volumedetect,
#     silencedetect, highpass).
#
# Usage (from python_webview/, on Linux with mingw-w64 and nasm installed:
#   sudo apt-get install gcc-mingw-w64-x86-64 nasm):
#   ./build_ffmpeg_windows.sh
# Environment: FFMPEG_TAG, FFMPEG_COMMIT, FFMPEG_GIT, FFMPEG_SRC as in
#   build_ffmpeg_mac.sh; FFMPEG_WORK (default build/ffmpeg-windows).
#
# Redistribution (the LGPL, and FFmpeg's checklist at ffmpeg.org/legal.html):
#   - bin/windows/ also gets COPYING.LGPLv2.1 and FFMPEG-NOTICE.txt, which the
#     app bundles next to the binaries;
#   - the exact source that was built, plus BUILD-INFO.txt with the configure
#     line, is written to $FFMPEG_WORK/ffmpeg-<version>-source-windows.tar.xz.
#     Attach it to the same GitHub release as the .exe.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
FFMPEG_TAG="${FFMPEG_TAG:-n6.1.6}"
FFMPEG_GIT="${FFMPEG_GIT:-https://git.ffmpeg.org/ffmpeg.git}"
if [ -z "${FFMPEG_COMMIT+set}" ] && [ "$FFMPEG_TAG" = n6.1.6 ]; then
    FFMPEG_COMMIT=f1e3a2bf7a2f2cde936d1ed97f09a26853d20125
fi
FFMPEG_WORK="${FFMPEG_WORK:-$SCRIPT_DIR/build/ffmpeg-windows}"
OUT_DIR="$SCRIPT_DIR/bin/windows"
CROSS=x86_64-w64-mingw32-

# The "win32" threading flavor of mingw-w64 gcc, so nothing from winpthreads is linked in
# (FFmpeg uses its own Windows threads, --enable-w32threads).
CC_WIN="${CROSS}gcc-win32"
command -v "$CC_WIN" > /dev/null || CC_WIN="${CROSS}gcc"
command -v "$CC_WIN" > /dev/null || { echo "${CROSS}gcc not found (apt-get install gcc-mingw-w64-x86-64)" >&2; exit 1; }
# (output captured first: an early-exiting grep -q could SIGPIPE gcc under pipefail)
cc_info="$("$CC_WIN" -v 2>&1)"
grep -q 'Thread model: win32' <<< "$cc_info" \
    || { echo "$CC_WIN is not the win32-threads flavor of mingw-w64 gcc" >&2; exit 1; }
command -v nasm > /dev/null || { echo "nasm not found (apt-get install nasm)" >&2; exit 1; }

mkdir -p "$FFMPEG_WORK"
FFMPEG_WORK="$(cd "$FFMPEG_WORK" && pwd)"

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

# The source archive must be exactly what is built: a git checkout with no local changes.
# (Checked before building, so a failed check never leaves binaries or notices behind.)
IS_GIT=0
if git -C "$FFMPEG_SRC" rev-parse --git-dir > /dev/null 2>&1; then
    IS_GIT=1
    if [ -n "$(git -C "$FFMPEG_SRC" status --porcelain --untracked-files=no)" ]; then
        echo "The FFmpeg checkout has local changes; the source archive must match the build." >&2
        exit 1
    fi
fi
rm -f "$FFMPEG_WORK"/ffmpeg-*-source-windows.tar.xz

BUILD_DIR="$FFMPEG_WORK/build-$FFMPEG_TAG-win64"
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

CONFIGURE_FLAGS=(
    --enable-cross-compile
    --cross-prefix="$CROSS"
    --cc="$CC_WIN"
    --target-os=mingw32
    --arch=x86_64
    --disable-autodetect
    --enable-w32threads
    --disable-ffplay
    --disable-doc
    --extra-ldflags=-static
)
echo "Configuring FFmpeg $FFMPEG_TAG for Windows x86-64..."
"$FFMPEG_SRC/configure" "${CONFIGURE_FLAGS[@]}" | tee configure.log

echo "Building..."
make -j"$(nproc)" ffmpeg.exe ffprobe.exe > make.log 2>&1 || {
    tail -40 make.log >&2
    exit 1
}

# ---- checks: refuse to hand over anything we would not ship ----
# (The .exe files cannot run here; build-windows.yml runs them on Windows and
# checks "ffmpeg -L" and "-buildconf" there too.)
fail() { echo "FAILED: $*" >&2; exit 1; }
has() { grep -q -E -- "$2" <<< "$1"; }

mak="$(cat ffbuild/config.mak)"
for flag in GPL NONFREE VERSION3; do
    if has "$mak" "^CONFIG_$flag=yes"; then fail "configured with $flag parts"; fi
done
components="$(cat config_components.h)"
for f in loudnorm alimiter volume volumedetect silencedetect highpass aresample; do
    has "$components" "^#define CONFIG_$(tr '[:lower:]' '[:upper:]' <<< "$f")_FILTER 1" || fail "filter $f missing"
done
for e in pcm_u8 pcm_s16le pcm_s24le pcm_s32le pcm_f32le pcm_f64le; do
    has "$components" "^#define CONFIG_$(tr '[:lower:]' '[:upper:]' <<< "$e")_ENCODER 1" || fail "encoder $e missing"
done
for m in WAV_MUXER NULL_MUXER WAV_DEMUXER; do
    has "$components" "^#define CONFIG_$m 1" || fail "$m missing"
done

# Only DLLs that come with Windows itself.
SYSTEM_DLLS='^(KERNEL32|msvcrt|ucrtbase|api-ms-win-[a-z0-9-]+|ADVAPI32|bcrypt|USER32|GDI32|SHELL32|ole32|OLEAUT32|WS2_32|SHLWAPI|PSAPI|AVICAP32|secur32|CRYPT32|ncrypt|mfplat|mfuuid|strmiids|dxgi|d3d11)\.dll$'
for bin in ffmpeg ffprobe; do
    desc="$(file "$bin.exe")"
    has "$desc" 'PE32\+ executable.*x86-64' || fail "$bin.exe is not a 64-bit x86-64 executable: $desc"
    dlls="$("${CROSS}objdump" -p "$bin.exe" | awk '/DLL Name:/{print $3}')"
    echo "$bin.exe imports: $(tr '\n' ' ' <<< "$dlls")"
    other="$(grep -v -i -E "$SYSTEM_DLLS" <<< "$dlls" || true)"
    [ -z "$other" ] || fail "$bin.exe needs a DLL that is not part of Windows: $other"
done

mkdir -p "$OUT_DIR"
rm -f "$OUT_DIR/ffmpeg.exe" "$OUT_DIR/ffprobe.exe"
cp ffmpeg.exe ffprobe.exe "$OUT_DIR/"

# ---- what the LGPL asks to travel with the binaries ----
VERSION="$(tr -d '[:space:]' < "$FFMPEG_SRC/RELEASE")"
COMMIT="$(git -C "$FFMPEG_SRC" rev-parse HEAD 2>/dev/null || echo unknown)"
CONFIG_LINE="./configure ${CONFIGURE_FLAGS[*]}"
THIS_YEAR="$(awk '/#define CONFIG_THIS_YEAR/{print $3}' "$BUILD_DIR/config.h")"
RELEASE_URL="${RELEASE_URL:-https://github.com/rulingAnts/bulk_audio_normalizer/releases}"
APP_COMMIT="${GITHUB_SHA:-$(git -C "$SCRIPT_DIR" rev-parse HEAD 2>/dev/null || echo unknown)}"
SOURCE_NAME="ffmpeg-$VERSION-source-windows.tar.xz"
GCC_VERSION="$("$CC_WIN" --version)"
GCC_VERSION="${GCC_VERSION%%$'\n'*}"
CC_DESC="$GCC_VERSION"

cp "$FFMPEG_SRC/COPYING.LGPLv2.1" "$OUT_DIR/COPYING.LGPLv2.1"
cat > "$OUT_DIR/FFMPEG-NOTICE.txt" <<NOTICE
FFmpeg in Bulk Audio Normalizer for Windows

This software uses code of FFmpeg (https://ffmpeg.org), licensed under the
GNU Lesser General Public License, version 2.1 or later. Its source can be
downloaded from the release page this app came from, as $SOURCE_NAME:
  $RELEASE_URL
and from https://ffmpeg.org/releases/ffmpeg-$VERSION.tar.xz.

FFmpeg is copyright (c) 2000-$THIS_YEAR the FFmpeg developers. It comes with
ABSOLUTELY NO WARRANTY; see COPYING.LGPLv2.1.

ffmpeg.exe and ffprobe.exe are FFmpeg $VERSION (git tag $FFMPEG_TAG,
commit $COMMIT), unmodified, cross-compiled for 64-bit Windows with
$GCC_VERSION and:

  $CONFIG_LINE

No external libraries are linked in. The full license text is in
COPYING.LGPLv2.1 next to this file.

FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.
NOTICE

# The exact source that was built, with the configure line at its root.
if [ "$IS_GIT" = 1 ]; then
    cat > "$BUILD_DIR/BUILD-INFO.txt" <<INFO
FFmpeg $VERSION (git tag $FFMPEG_TAG, commit $COMMIT), unmodified.

Built for 64-bit Windows (x86-64) by build_ffmpeg_windows.sh in
https://github.com/rulingAnts/bulk_audio_normalizer (python_webview/),
cross-compiled on Linux with $GCC_VERSION, with:

  $CONFIG_LINE
  make ffmpeg.exe ffprobe.exe

Compiler: $CC_DESC
App source this was built for: https://github.com/rulingAnts/bulk_audio_normalizer/tree/$APP_COMMIT
(The app bundler, PyInstaller, may re-sign or compress the programs; they are otherwise
the build output of the line above.)

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
    echo "  $(file "$OUT_DIR/$bin.exe" | sed "s#$OUT_DIR/##")"
done
echo "  License: LGPL version 2.1 or later (no GPL, version3 or nonfree parts)"
echo "  Notices: $OUT_DIR/COPYING.LGPLv2.1, $OUT_DIR/FFMPEG-NOTICE.txt"
if [ -f "$FFMPEG_WORK/$SOURCE_NAME" ]; then
    echo ""
    echo "Source to attach to the release (next to the .exe):"
    echo "  $FFMPEG_WORK/$SOURCE_NAME"
    echo "  sha256 $(sha256sum "$FFMPEG_WORK/$SOURCE_NAME" | cut -d' ' -f1)"
fi
