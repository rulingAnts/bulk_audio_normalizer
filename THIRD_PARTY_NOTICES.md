Third-Party Notices

This project bundles the following third-party components:

- FFmpeg (https://ffmpeg.org): the `ffmpeg` and `ffprobe` programs inside the apps. They are separate programs that the app runs; they are not linked into it. Which build is inside depends on the platform:
  - **macOS app (v2.0.2 and later):** This software uses code of FFmpeg licensed under the LGPLv2.1, and its source can be downloaded from the same release page as the app (`ffmpeg-6.1.6-source.tar.xz`). It is FFmpeg 6.1.6, unmodified, built from FFmpeg's own source by `python_webview/build_ffmpeg_mac.sh` with no GPL, version3 or nonfree parts and no external libraries. The license text (`COPYING.LGPLv2.1`) and a notice with the exact configure line ship inside the app, in `Contents/Frameworks/bin/macos/`. The same source is also at https://ffmpeg.org/releases/ffmpeg-6.1.6.tar.xz.
  - **Windows app:** `ffmpeg.exe` is FFmpeg 6.1.1 built by gyan.dev (installed by the npm package ffmpeg-static 5.3.0), and `ffprobe.exe` is FFmpeg 4.0.2 (from the npm package ffprobe-static 3.1.0). Both are GPLv3 builds (`--enable-gpl --enable-version3`). FFmpeg's source: https://ffmpeg.org/download.html#sources. See ffmpeg.org/legal.html.
  - **Withdrawn downloads:** on 3 October 2026 the macOS downloads of v1.5.1, v2.0.0 and v2.0.1, and the v1.5.1 Windows installer, were removed from the releases page. The macOS `ffmpeg` in them came from ffmpeg-static and was built with `--enable-nonfree`, which FFmpeg marks as not legally redistributable.
  - FFmpeg is a trademark of Fabrice Bellard, originator of the FFmpeg project.
  - This project is licensed under AGPL-3.0, which is compatible with both the LGPL build (macOS) and the GPLv3 builds (Windows).

- ffmpeg-static and ffprobe-static (Windows build only; used to fetch the binaries above)
  - NPM: https://www.npmjs.com/package/ffmpeg-static and https://www.npmjs.com/package/ffprobe-static
  - License: Refer to the package pages for license and attribution.

Icon artwork credit (prebuilt assets only):

- App icon artwork incorporates glyph outlines originally derived from the Charis SIL typeface by SIL International. The repository ships only prebuilt raster/vector icons (no font files or build pipeline). Use of font glyphs in static images is permitted by the SIL Open Font License (OFL 1.1); attribution is appreciated but not required for such artwork.
  - Charis SIL: https://software.sil.org/charis/
  - SIL Open Font License 1.1: https://scripts.sil.org/OFL

If you are distributing binaries of this application, ensure that:

- You include this NOTICE file and the full text of the AGPL-3.0 license.
- You provide access to the complete Corresponding Source for this application, as required by the AGPL.
- You preserve all copyright and license notices for the included components.
