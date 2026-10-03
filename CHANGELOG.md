# Changelog

All notable changes to this project will be documented in this file.

## [2.0.2] - 2026-10-03 (pre-release, still being tested)

### Fixed
- Files whose names contain an apostrophe (e.g. "Don't") stopped the batch with an error ([#2](https://github.com/rulingAnts/bulk_audio_normalizer/issues/2))
- File names with any character Windows allows (accents and umlauts, ß, €, @, #, +, ~, ², ³, !, &, %, commas, spaces, several dots) work in the batch and the preview window; names are shown literally
- Windows output paths with backslash sequences (e.g. `\x`, `\u`) garbled the log or stopped the batch
- A batch that stopped on an error no longer reports "Completed"; the error is shown, the status stays "Error", and the controls unlock
- A file FFmpeg cannot process is marked red, the batch goes on, and the end of the batch lists the files that were not written, instead of "Completed" (the end-of-batch check never ran before)
- `.wave` files were scanned but could not be written
- Files with the same name in different subfolders shared one row in the progress list; rows and preview cards now show the path within the input folder
- LUFS mode (two-pass, with verbose logs on): a file whose name contains `{` silently got single-pass normalization
- macOS `._` metadata files on USB drives and memory cards are skipped instead of processed as audio

### Added
- Windows x64 builds are made by a GitHub Actions workflow and published as pre-releases first
- macOS (Apple silicon) .dmg, built by a GitHub Actions workflow (`build-macos.yml`). Its FFmpeg
  and FFprobe are FFmpeg 6.1.6 compiled from FFmpeg's source with no external libraries, under
  the LGPLv2.1 (`build_ffmpeg_mac.sh`); the license text and a notice ship inside the app, and the
  exact source is attached to the release
- The Windows exe uses the same FFmpeg 6.1.6, LGPL build, cross-compiled from source
  (`build_ffmpeg_windows.sh`) instead of the npm ffmpeg-static (gyan.dev 6.1.1, GPLv3) and
  ffprobe-static (4.0.2, GPLv3) binaries, with its license text, notice and source the same way
- The app's footer says which FFmpeg it uses and under which license

### Changed
- `setup_ffmpeg.py` refuses to run on macOS and points to `build_ffmpeg_mac.sh`; on Windows it is
  for local development only (its npm builds are GPL)

### Removed
- The macOS downloads of v1.5.1, v2.0.0 and v2.0.1, and the v1.5.1 Windows installer, were taken
  off the releases page: their macOS ffmpeg (from npm ffmpeg-static) was built with
  `--enable-nonfree`, which FFmpeg marks as not legally redistributable. The v2.0.1 macOS app also
  bundled an Intel-only ffprobe that needed Rosetta 2

## [2.0.1] - 2025-11-30

### Changed
- Version bump

## [2.0.0] - 2025-11-30

### 🎉 Major Stability Release

This version represents a **complete rewrite** from v1.x that makes the application actually usable in production.

**Before (v1.x):** Extremely resource-intensive, error-prone, and frequently crashed during processing.

**Now (v2.0):** Complete architectural overhaul resulting in a stable, efficient, and reliable audio normalization tool.

### Changed
- **BREAKING:** Migrated from Electron to Python with pywebview for better subprocess management
- Removed all Node.js/Electron dependencies and build infrastructure
- Improved process control with proper pause/resume/cancel functionality
- Settings now locked during processing to prevent mid-batch changes
- Default peak target changed from -9 dBFS to -2 dBFS
- Platform-specific FFmpeg binary organization (bin/macos/, bin/windows/, bin/linux/)
- PyInstaller-based builds: macOS .app bundle and Windows portable .exe
- Builds now only include platform-specific binaries (no cross-platform bloat)
- **Platform-specific build directories:** macOS builds to `dist/macos/`, Windows to `dist/windows/`
- Dramatically reduced memory and CPU consumption
- Stable processing with no crashes during batch operations

### Added
- Pause processing capability with resume from where you left off
- Cancel button with output folder cleanup
- File tracking to prevent re-processing on resume
- Batch verification after completion to ensure all files processed correctly
- Preview window with A/B waveform comparison
- Comprehensive build documentation (BUILD.md, BUILD_QUICK.md, BUILD_CHECKLIST.md, FIRST_TIME_BUILD.md)
- Platform-specific build scripts (build_mac.sh, build_windows.bat)
- Automated build verification scripts (test_build.sh, test_build.bat)
- Windows build guide (WINDOWS_BUILD_GUIDE.md) for cross-platform development
- Professional app naming with spaces ("Bulk Audio Normalizer")

### Fixed
- Process tree cleanup now properly handles FFmpeg subprocess termination
- Preview window can be closed and reopened multiple times
- Progress tracking no longer shows incorrect file counts
- Completion status correctly shows "All Done" instead of "Error" on success
- Bundled FFmpeg binaries now properly used instead of system PATH
- Icon management for both macOS (.icns) and Windows (.ico)
- Debug mode disabled for production builds

### Known Issues
- **Pause/Resume functionality temporarily disabled:** Some users reported missing output files after using pause/resume. The feature has been disabled until the underlying issue can be identified and resolved. The batch processor will run to completion once started. To stop processing, close the application window.
- **Verification of missing files needed:** In rare cases, some audio files may not be processed. The cause is under investigation and may be related to the disabled pause/resume functionality or concurrent processing edge cases. Check the output folder and debug log if you suspect files are missing.

## [1.5.1] - 2025-11-07 (Electron - deprecated)

### Changed
- Packaging: Windows build now sources `ffmpeg.exe` from a repo‑local zip (`build/win32-resources/ffmpeg-static.zip`) when cross‑building from macOS; no network calls required.
- Packaging: Removed network download logic from `afterPack.cjs`; added fallback to any existing Windows PE binary in `ffmpeg-static`.
- Docs: Added advanced packaging notes, Windows developer guidance, and known issues about macOS‑first build scripts.

### Fixed
- Ensured macOS build normalization does not overwrite Windows binaries and vice versa.

## [0.3.0] - 2025-11-07

### Added
- Normalization intent selector with two modes:
	- Peak dBFS (default) for acoustic analysis; analyzes peak and applies gain to a target (default −9 dBFS; typical −12 to −6).
	- LUFS (EBU R128) for consistent listening; two‑pass loudnorm with a safety limiter.
- Bit depth control: 16‑bit, 24‑bit (no 16→24 up‑convert), or Original (preserve source format/bit‑depth).
- Adaptive throttling based on CPU load and free memory, with live status in the UI.
- Elapsed time and ETA on overall progress.
- Intro banner and UX polish: simplified per‑file progress (phase bars), improved warnings, tooltips, and layout.

### Changed
- Render pipeline branches for Peak vs LUFS, including volumedetect + gain path for Peak mode and limiter only applied in LUFS mode.
- Output codec selection now considers source format when Bit depth is set to Original.

### Fixed
- Stability and responsiveness when running high concurrency with large batches via adaptive throttling.

## [0.2.0] - 2025-11-07

### Added
- Fast trim (edge scan) that trims without running an FFmpeg detect pass (default ON when Auto-trim is ON).
- Fast normalize (single pass) option to skip the loudnorm analysis pass.
- Per-pass mini progress bars (Detect / Analyze / Render) for each file.
- Batch status line (Detecting / Analyzing / Rendering / Completed).
- Optional FFmpeg threads-per-process control for better throughput tuning.
- Collapsible File status and Debug log panels (log collapsed by default).
- Bigger log view and more informative logs (detect config, trim applied/why not).

### Changed
- Auto-trim pad default increased to 800 ms each side.
- Trim pipeline now uses input-level seeking (-ss/-to) for heavy passes to avoid decoding trimmed regions.
- Duration prefetch uses a fast WAV header parser; falls back to ffprobe only when needed.
- Build docs updated to match packaging targets (mac DMG, Windows Portable).

### Fixed
- Progress bars update in non-verbose mode (removed -nostats so time= lines are visible).
- Detect logs forced to -v info so silencedetect events are reliably emitted.

## [0.1.0] - 2025-10-??
- Initial release.
