# Changelog

All notable changes to this project will be documented in this file.

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
