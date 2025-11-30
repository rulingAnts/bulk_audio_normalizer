# Bulk Audio Normalizer

Python application to batch-process WAV files for linguistics and fieldwork. Supports two normalization intents — Peak dBFS (default, for acoustic analysis) and LUFS (for consistent listening) — plus flexible bit-depth output (16-bit, 24-bit, or preserve original) with a safety limiter available in LUFS mode. Built for very large batches of short files with responsive UI and careful performance controls.

> **📦 Download Ready-to-Use Builds:** Visit [releases](https://github.com/rulingAnts/bulk_audio_normalizer/releases/latest) for macOS (.dmg) and Windows (.exe) downloads — no Python installation required!

> **🌐 User Documentation:** Visit the [project website](https://rulingAnts.github.io/bulk_audio_normalizer/) for screenshots, quick start guide, and direct download buttons.

> **Note:** Version 2.0.0 represents a complete rewrite from v1.x. The application is now stable, efficient, and production-ready, fixing the resource-intensive issues and frequent crashes that made v1.x unusable.

## What it does

- Scans an input folder (recursively) for `.wav`/`.wave` files
- Normalizes audio using one of two intents:
  - Peak dBFS (Acoustic analysis / Language documentation): analyze peak and apply gain to a target (default −2 dBFS; typical range −12 to −2 dBFS) to preserve headroom for tools like Praat; no limiter is applied in this mode by default.
  - LUFS (Participatory listening / Human ears): two-pass EBU R128 `loudnorm` to −16 LUFS with a post-limiter (default ceiling 0.97) to guarantee no clipping.
- Output bit depth options:
  - 16-bit PCM WAV (`pcm_s16le`)
  - 24-bit PCM WAV (`pcm_s24le`) without up-converting 16-bit inputs
  - Original (preserve source format/bit-depth; e.g., 32-bit float stays float)
- Writes to a separate, empty output folder (never in-place)
- Optional auto-trim of leading/trailing silence
  - Fast trim (edge scan) avoids an extra FFmpeg pass
  - Or precise FFmpeg-based detect with optional HPF and conservative mode
- Responsive UI with:
  - Overall progress + elapsed time and ETA, plus live throttle status
  - Per-file phase bars (Detect / Analyze / Render)
  - Pause/Resume/Cancel processing controls
  - Preview mode with A/B waveform comparison
  - Live log panel (collapsible)

## Requirements

- Python 3.8 or higher
- FFmpeg and FFprobe binaries (included for macOS and Windows builds)
- macOS, Windows, or Linux

## Quick Start

### Running from Source

```bash
cd python_webview
pip install -r requirements.txt
python3 setup_ffmpeg.py  # Downloads FFmpeg binaries
python3 main.py
```

**Documentation:**
- [python_webview/QUICKSTART.md](python_webview/QUICKSTART.md) - Quick reference for running from source
- [python_webview/README.md](python_webview/README.md) - Detailed setup and usage instructions

### Building Executables

Create standalone applications that don't require Python installation:

**macOS:**
```bash
cd python_webview
pip3 install -r requirements-build.txt
./build_mac.sh              # Creates .app bundle
./create_dmg_mac.sh         # Creates DMG installer (optional)
```

**Windows:**
```batch
cd python_webview
pip install -r requirements-build.txt
build_windows.bat           # Creates portable .exe
```

**Documentation:**
- [python_webview/FIRST_TIME_BUILD.md](python_webview/FIRST_TIME_BUILD.md) - Step-by-step guide for first-time builders
- [python_webview/BUILD_QUICK.md](python_webview/BUILD_QUICK.md) - Quick reference for experienced developers
- [python_webview/BUILD.md](python_webview/BUILD.md) - Comprehensive build documentation
- [python_webview/BUILD_CHECKLIST.md](python_webview/BUILD_CHECKLIST.md) - Pre-build verification checklist

## Preview mode (random spot check)

- Use the Preview section to process a true random sample of files from your input folder with the current settings (capped at 50 files per run to keep it responsive).
- A/B playback with waveforms, seek, select/loop a region, and reveal files in Finder/Explorer.
- Previews are written to a temporary folder and do not touch your originals.

## Processing Controls

- **Start**: Begin processing the batch
- **Pause**: Pause processing (can be resumed)
- **Resume**: Continue from where you paused
- **Cancel**: Stop processing and clear output folder
- Settings are locked during processing to prevent mid-batch changes

## Normalization intent: Peak dBFS vs LUFS (guidance)

- Peak dBFS mode is intended for linguistic/acoustic analysis. It boosts quiet files so their highest peak reaches a chosen target (default −2 dBFS; typical −12 to −2 dBFS), without attenuating already-loud files and without any limiter/compressor. This preserves amplitude relationships and headroom, making files suitable for tools like Praat.
- LUFS mode targets how loud speech sounds to people. It uses EBU R128 `loudnorm` (two-pass by default) and then a brick-wall limiter to ensure zero clipping. This is great for consistent listening and participatory review.

Tip: For language documentation workflows, default to Peak dBFS. For outreach or teaching materials where consistency of perceived loudness matters, use LUFS.

## Notes on loudness and clipping safety (LUFS mode)

- Loudness normalization uses FFmpeg `loudnorm` (EBU R128) with user-adjustable targets (default `I=-16, TP=-1.0, LRA=11`).
- After normalization, a brick-wall safety limiter (`alimiter`) is applied with an adjustable ceiling (default `limit=0.97`, ≈ −0.27 dBFS) to prevent any clipping.
- Output bit depth is controlled by the Bit depth setting (16/24/Original). When converting from float/high bit depth to 16/24-bit PCM, FFmpeg handles dithering/quantization.

## Bit depth policy

- 16-bit: Always write 16-bit PCM WAV (`pcm_s16le`).
- 24-bit: Write 24-bit PCM WAV (`pcm_s24le`) when the source is >16-bit; 16-bit inputs remain 16-bit (no up-convert).
- Original (no limit): Preserve the source format and bit-depth (e.g., 32-bit float remains float). This is useful for analysis workflows but results in larger files.

## Settings

- Normalization intent: Peak dBFS or LUFS
  - Peak target (dBFS): default −2; recommended range −12 to −2
  - Only boost (don't attenuate) in Peak mode: ON by default
  - LUFS target (I): default −16 LUFS
  - Limiter ceiling (LUFS mode): linear amplitude 0..1 (default 0.97)
- Bit depth: 16-bit, 24-bit (no 16→24 up-convert), or Original (preserve)
- Concurrency (number of files processed in parallel)
- Fast normalize (single pass) — skips the loudnorm analysis pass for speed
- FFmpeg threads per process (optional) — cap per-process threads when using high concurrency
- Auto-trim leading/trailing silence with adjustable parameters:
  - Keep padding on each side (default 800 ms)
  - Silence threshold in dBFS (default −50 dB; conservative mode uses −60 dB)
  - Minimum silence duration (default 200 ms; conservative mode uses 300 ms)
  - Only trim if file longer than (default 800 ms)
  - Conservative trim (safer for soft voices)
  - Pre-filter rumble (HPF 80 Hz)
  - Fast trim (edge scan) — trims without running an FFmpeg detect pass (default ON)

Settings are persisted locally per machine.

## Speed vs. quality: recommended profiles (plain language)

Pick the set of options that fits your situation. You can always preview a random sample first.

- Fastest processing (lots of files, short clips):
  - Auto-trim: OFF (or ON if you need it) — if ON, keep Fast trim ON
  - Fast trim (edge scan): ON
  - Fast normalize (single pass): ON
  - Concurrency (how many files at the same time): your computer's CPU cores minus one
  - FFmpeg threads per process (power per file): 1–2
  - Debug/verbose logs: OFF; keep the log panel collapsed

- Balanced (good speed, safe defaults):
  - Auto-trim: ON
  - Fast trim (edge scan): ON
  - Fast normalize (single pass): OFF (use the more precise 2-pass)
  - Concurrency (how many files at once): cores − 1
  - FFmpeg threads per process: 1–2
  - Silence threshold: around −40 to −50 dBFS depending on noise level; Keep padding: 800 ms

- Highest caution/quality (safest, slightly slower):
  - Auto-trim: ON
  - Fast trim (edge scan): OFF (use the more careful FFmpeg detect)
  - Pre-filter rumble (HPF 80 Hz): ON
  - Conservative trim: ON (treats softer sounds as "voice" so less gets trimmed)
  - Fast normalize (single pass): OFF (use full 2-pass)
  - Concurrency: moderate (fewer files at once to keep the computer calm)
  - Limiter ceiling (LUFS mode): 0.97 or lower for extra headroom

Tip: If ends with white noise aren't trimmed, make the silence threshold a larger number (e.g., −35 dBFS), or turn OFF "Conservative trim." The Debug log shows what was detected (start/end) and whether trimming was applied.

## Caveats

- Output folder must be empty before starting (the app enforces this).
- Settings like concurrency and threads interact with your CPU; monitor system responsiveness and adjust.

## Troubleshooting

- If you see errors, open the Debug log panel for details.
- If trimming doesn't apply, check the log for "Detect config" and "Trim applied" lines, and adjust threshold/padding.
- If Peak dBFS mode appears to do nothing, check the Debug log for a line like "Peak mode: measuredMax=… dB, target=… dB, gain=… dB". If measuredMax is n/a, ensure the analysis pass ran (it should). If gain is 0.00 dB with a quiet file, verify the "Only boost (don't attenuate)" toggle and your target (e.g., −2 dBFS).
- If a file fails to process, the batch will stop and report the error; re-run after addressing the issue.

## Glossary (simple explanations)

- LUFS: a way to measure how loud speech/music sounds to people. Target is −16 (spoken audio standard in many tools).
- True-peak (TP): the highest "in-between" peak after converting to the final format. LUFS mode aims for −1.0 dBFS TP to be safe.
- Limiter (LUFS mode): a safety ceiling so loud bits don't clip (distort). We use 0.97 (just below 0 dB) by default.
- Auto-trim: cut silence (or steady noise) at the beginning and end of a clip. You can keep some padding so speech isn't cut too tight.
- Silence threshold (dBFS): how quiet is considered "silence." A larger number (e.g., −35) means more gets treated as silence.
- Concurrency: how many files are processed at the same time.
- Threads per process: how much CPU a single file is allowed to use. Fewer threads per file can help when many files run in parallel.

## Project Structure

```
bulk_audio_normalizer/
├── python_webview/          # Main application
│   ├── main.py             # Entry point
│   ├── backend/            # Audio processing logic
│   ├── frontend/           # HTML/CSS/JS UI
│   ├── bin/                # FFmpeg binaries (platform-specific)
│   ├── BUILD.md            # Build documentation
│   └── README.md           # Python app documentation
├── docs/                   # GitHub Pages user documentation
├── LICENSE                 # AGPL-3.0
└── README.md              # This file
```

## Distribution

PyInstaller builds create standalone executables:

- **macOS:** `.app` bundle (onedir) and optional DMG installer
- **Windows:** Portable `.exe` (onefile)
- No Python installation required for end users
- FFmpeg binaries bundled automatically
- ~20-30 MB total size per platform

See [python_webview/BUILD.md](python_webview/BUILD.md) for complete build and distribution instructions.

## Attribution

Code generated almost entirely by VS Code Copilot (GPT-5), with some consultation with Claude/Sonnet 4.5 about ideal settings for acoustic analysis / language documentation.

## License and third-party notices

- Copyright © 2025 Seth Johnston
- License: AGPL-3.0 (see `LICENSE`)
- Third-party notices: see `THIRD_PARTY_NOTICES.md`
