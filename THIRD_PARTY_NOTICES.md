Third-Party Notices

This project bundles the following third-party components:

- FFmpeg (https://ffmpeg.org): the `ffmpeg` and `ffprobe` programs inside the apps. They are separate programs that the app runs; they are not linked into it.
  - **From v2.0.2, both apps:** This software uses code of FFmpeg licensed under the LGPLv2.1, and its source can be downloaded from the same release page as the app: `ffmpeg-6.1.6-source-macos.tar.xz` next to the macOS `.dmg`, and `ffmpeg-6.1.6-source-windows.tar.xz` next to the Windows `.exe`. Both hold the same unmodified FFmpeg 6.1.6 source, with a `BUILD-INFO.txt` giving that platform's exact configure line. It is built from FFmpeg's own source with no GPL, version3 or nonfree parts and no external libraries, by `python_webview/build_ffmpeg_mac.sh` (macOS, Apple silicon) and `python_webview/build_ffmpeg_windows.sh` (Windows x64, cross-compiled with mingw-w64). The license text (`COPYING.LGPLv2.1`) and a notice ship inside each app, in its `bin/macos` or `bin/windows` folder (on macOS: `Contents/Resources/bin/macos/`). The same source is also at https://ffmpeg.org/releases/ffmpeg-6.1.6.tar.xz.
  - **Windows releases up to v2.0.1:** `ffmpeg.exe` came from the npm package ffmpeg-static and `ffprobe.exe` from ffprobe-static; both were GPLv3 builds. FFmpeg's source: https://ffmpeg.org/download.html#sources.
  - **Withdrawn downloads:** on October 3, 2026, the macOS downloads of v1.5.1, v2.0.0 and v2.0.1, and the v1.5.1 Windows installer, were removed from the releases page. The macOS `ffmpeg` in them came from ffmpeg-static and was built with `--enable-nonfree`, which FFmpeg marks as not legally redistributable.
  - FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.
  - This project is licensed under AGPL-3.0, which is compatible with the LGPL.

- Python and the Python packages inside the apps (from v2.0.2): the Python runtime and the libraries it includes (OpenSSL, expat, libffi, zlib, libmpdec and others; ncurses on macOS), PyInstaller's bootloader, pywebview, psutil, bottle, proxy_tools, typing_extensions and, on macOS, PyObjC (on Windows, pywebview's .NET and WebView2 components). Their full license texts are in the `licenses` folder inside each app (`THIRD-PARTY-LICENSES.txt`), written at build time by `python_webview/collect_licenses.py`, with this file, the app's own license and `SOURCE.txt`, which names the exact commit the app was built from.

Icon artwork credit (prebuilt assets only):

- App icon artwork incorporates glyph outlines originally derived from the Charis SIL typeface by SIL International. The repository ships only prebuilt raster/vector icons (no font files or build pipeline). Use of font glyphs in static images is permitted by the SIL Open Font License (OFL 1.1); attribution is appreciated but not required for such artwork.
  - Charis SIL: https://software.sil.org/charis/
  - SIL Open Font License 1.1: https://scripts.sil.org/OFL

If you are distributing binaries of this application, ensure that:

- You include this NOTICE file and the full text of the AGPL-3.0 license.
- You provide access to the complete Corresponding Source for this application, as required by the AGPL.
- You preserve all copyright and license notices for the included components.
