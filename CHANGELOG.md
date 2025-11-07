# Changelog

All notable changes to this project will be documented in this file.

## [1.5.1] - 2025-11-07

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
