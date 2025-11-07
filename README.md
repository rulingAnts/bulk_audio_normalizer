# Bulk Audio Normalizer

Electron app to batch‑process WAV files for linguistics and fieldwork. Supports two normalization intents — Peak dBFS (default, for acoustic analysis) and LUFS (for consistent listening) — plus flexible bit‑depth output (16‑bit, 24‑bit, or preserve original) with a safety limiter available in LUFS mode. Built for very large batches of short files with responsive UI and careful performance controls.

## What it does

- Scans an input folder (recursively) for `.wav`/`.wave` files
- Normalizes audio using one of two intents:
  - Peak dBFS (Acoustic analysis / Language documentation): analyze peak and apply gain to a target (default −9 dBFS; typical range −12 to −6 dBFS) to preserve headroom for tools like Praat; no limiter is applied in this mode by default.
  - LUFS (Participatory listening / Human ears): two‑pass EBU R128 `loudnorm` to −16 LUFS with a post‑limiter (default ceiling 0.97) to guarantee no clipping.
- Output bit depth options:
  - 16‑bit PCM WAV (`pcm_s16le`)
  - 24‑bit PCM WAV (`pcm_s24le`) without up‑converting 16‑bit inputs
  - Original (preserve source format/bit‑depth; e.g., 32‑bit float stays float)
- Writes to a separate, empty output folder (never in‑place)
- Optional auto‑trim of leading/trailing silence
	- Fast trim (edge scan) avoids an extra FFmpeg pass
	- Or precise FFmpeg‑based detect with optional HPF and conservative mode
- Responsive UI with:
	- Overall progress + elapsed time and ETA, plus live throttle status
	- Per‑file phase bars (Detect / Analyze / Render)
	- Live log panel (collapsible) and a friendly intro banner

## Requirements

- macOS, Windows, or Linux
- No external FFmpeg install required: the app uses `ffmpeg-static` and `ffprobe-static`
- Node.js 18+

## Run it

```bash
npm install
npm start
```

This launches the Electron app in development mode.

## Preview mode (random spot check)

- Use the Preview section to process a true random sample of files from your input folder with the current settings (capped at 50 files per run to keep it responsive).
- A/B playback with waveforms, seek, select/loop a region, and reveal files in Finder/Explorer.
- Previews are written to a temporary folder and do not touch your originals.

## Build distributables

Builds use electron‑builder and include FFmpeg/FFprobe (unpacked from ASAR for runtime execution).

Basic:

```bash
npm run dist
```

Platform‑specific:

```bash
# macOS universal DMG (runs on Apple Silicon + Intel)
npm run dist -- --mac

# Windows portable (from macOS requires Wine; from Windows needs no Wine)
npm run dist -- --win
```

Outputs are written to `dist/`, e.g.:

- `dist/Bulk Audio Normalizer-<version>-universal.dmg`
- `dist/Bulk Audio Normalizer <version>.exe`

Notes:

- Unsigned builds: these are not code‑signed. On macOS, you may need to right‑click → Open the first time and approve running from an unidentified developer.
- Windows ffmpeg correctness: The `ffmpeg-static` install must run on the target platform to fetch a native binary. If cross-building, provide a real Windows PE executable via env `FFMPEG_WIN64` (path to ffmpeg.exe) or rely on CI Windows runner.
- Cross‑building Windows on macOS: Recommended to use CI (GitHub Actions `windows-latest`). Local cross-builds will not produce a valid Windows ffmpeg unless the above env override is used.

### Advanced: Windows ffmpeg bundling via repo zip

For cross‑building Windows from macOS without making network requests, this repo assumes there's a pre‑downloaded Windows `ffmpeg-static` package as a zip at `build/win32-resources/ffmpeg-static.zip`. Since GitHub limits file sizes to 25mb, that is .gitignore-d on our online version of the repository, and so you would need to run npm install ffmpeg-static@5.2.0 (or higher) on a windows machine to get that binary, then zip the ffmpeg-static node_modules folder and put it in build/win32-resources in your offline copy of this repository.

- Our packaging hook (`scripts/afterPack.cjs`) extracts `ffmpeg.exe` from that zip and places it at:
	`app.asar.unpacked/node_modules/ffmpeg-static/bin/win32/x64/ffmpeg.exe`
- This path matches what the app resolves at runtime, alongside `ffprobe-static`.
- If the zip is missing or extraction fails, the hook falls back to any existing PE `ffmpeg*` file in `node_modules/ffmpeg-static/` (rare during cross‑builds).

Updating the zip:

- Replace `build/win32-resources/ffmpeg-static.zip` with a zip that contains a valid Windows PE `ffmpeg.exe` (for example, by installing `ffmpeg-static` on a Windows machine and zipping its folder that contains `ffmpeg.exe`).
- No version pin is enforced by the hook; use a version compatible with the app’s FFmpeg CLI flags (FFmpeg ≥ 5.x is fine; 6.x recommended).

Behavior on macOS vs Windows:

- macOS builds do NOT use this zip and will not overwrite the macOS ffmpeg binary; the mac path is normalized under `bin/darwin/universal/ffmpeg`.
- Windows builds use the zip on macOS cross‑builds. On a native Windows machine, you may prefer to disable the zip step and let `ffmpeg-static` provide `ffmpeg.exe` directly.

### Known issues (Windows dev machines)

- These build scripts and the packaging hook are designed and tested primarily on macOS, including cross‑building the Windows portable.
- Running the packaging hook as‑is on Windows may require adjustments (e.g., using `Expand-Archive` or 7‑Zip with correct paths). The current hook attempts PowerShell `Expand-Archive` when available, and `unzip` on Unix‑like hosts.
- If you’re developing on Windows, consider one of the following:
	- Remove/skip the zip extraction path and rely on `ffmpeg-static` to provide `ffmpeg.exe` natively on Windows.
	- Or change the extraction command to use a tool you have installed (e.g., 7‑Zip) and keep the `build/win32-resources/ffmpeg-static.zip` flow.
	- Or build Windows artifacts in CI on `windows-latest`, which avoids cross‑build quirks entirely.
 
In short: macOS can cross‑build both platforms with this repo’s zip‑based approach; Windows developers may need to adapt `scripts/afterPack.cjs` to their environment before `npm run dist -- --win` works locally.

## Icons

Prebuilt platform icons are committed under `build/icons/` and used directly by packaging. The icon generation pipeline and any font files are not included in this repository. See `THIRD_PARTY_NOTICES.md` for icon artwork credit.

## Normalization intent: Peak dBFS vs LUFS (guidance)

- Peak dBFS mode is intended for linguistic/acoustic analysis. It boosts quiet files so their highest peak reaches a chosen target (default −9 dBFS; typical −12 to −6 dBFS), without attenuating already‑loud files and without any limiter/compressor. This preserves amplitude relationships and headroom, making files suitable for tools like Praat.
- LUFS mode targets how loud speech sounds to people. It uses EBU R128 `loudnorm` (two‑pass by default) and then a brick‑wall limiter to ensure zero clipping. This is great for consistent listening and participatory review.

Tip: For language documentation workflows, default to Peak dBFS. For outreach or teaching materials where consistency of perceived loudness matters, use LUFS.

## Notes on loudness and clipping safety (LUFS mode)

- Loudness normalization uses FFmpeg `loudnorm` (EBU R128) with user‑adjustable targets (default `I=-16, TP=-1.0, LRA=11`).
- After normalization, a brick‑wall safety limiter (`alimiter`) is applied with an adjustable ceiling (default `limit=0.97`, ≈ −0.27 dBFS) to prevent any clipping.
- Output bit depth is controlled by the Bit depth setting (16/24/Original). When converting from float/high bit depth to 16/24‑bit PCM, FFmpeg handles dithering/quantization.

## Bit depth policy

- 16‑bit: Always write 16‑bit PCM WAV (`pcm_s16le`).
- 24‑bit: Write 24‑bit PCM WAV (`pcm_s24le`) when the source is >16‑bit; 16‑bit inputs remain 16‑bit (no up‑convert).
- Original (no limit): Preserve the source format and bit‑depth (e.g., 32‑bit float remains float). This is useful for analysis workflows but results in larger files.

## Settings

- Normalization intent: Peak dBFS or LUFS
  - Peak target (dBFS): default −9; recommended range −12 to −6
	- Only boost (don’t attenuate) in Peak mode: ON by default
  - LUFS target (I): default −16 LUFS
  - Limiter ceiling (LUFS mode): linear amplitude 0..1 (default 0.97)
- Bit depth: 16‑bit, 24‑bit (no 16→24 up‑convert), or Original (preserve)
- Concurrency (number of files processed in parallel)
- Fast normalize (single pass) — skips the loudnorm analysis pass for speed
- FFmpeg threads per process (optional) — cap per‑process threads when using high concurrency
- Auto‑trim leading/trailing silence with adjustable parameters:
	- Keep padding on each side (default 800 ms)
	- Silence threshold in dBFS (default −50 dB; conservative mode uses −60 dB)
	- Minimum silence duration (default 200 ms; conservative mode uses 300 ms)
	- Only trim if file longer than (default 800 ms)
	- Conservative trim (safer for soft voices)
	- Pre‑filter rumble (HPF 80 Hz)
	- Fast trim (edge scan) — trims without running an FFmpeg detect pass (default ON)

Settings are persisted locally per machine.

## Adaptive throttling and performance

- The app monitors CPU load and memory and dynamically reduces concurrency (“throttling”) to keep your computer responsive on heavy settings. Live status is shown near overall progress.
- Throughput tuning: use higher concurrency with fewer FFmpeg threads per process; or lower concurrency with more threads per process. Preview first, then scale.

## Speed vs. quality: recommended profiles (plain language)

Pick the set of options that fits your situation. You can always preview a random sample first.

- Fastest processing (lots of files, short clips):
	- Auto‑trim: OFF (or ON if you need it) — if ON, keep Fast trim ON
	- Fast trim (edge scan): ON
	- Fast normalize (single pass): ON
	- Concurrency (how many files at the same time): your computer’s CPU cores minus one
	- FFmpeg threads per process (power per file): 1–2
	- Debug/verbose logs: OFF; keep the log panel collapsed

- Balanced (good speed, safe defaults):
	- Auto‑trim: ON
	- Fast trim (edge scan): ON
	- Fast normalize (single pass): OFF (use the more precise 2‑pass)
	- Concurrency (how many files at once): cores − 1
	- FFmpeg threads per process: 1–2
	- Silence threshold: around −40 to −50 dBFS depending on noise level; Keep padding: 800 ms

- Highest caution/quality (safest, slightly slower):
	- Auto‑trim: ON
	- Fast trim (edge scan): OFF (use the more careful FFmpeg detect)
	- Pre‑filter rumble (HPF 80 Hz): ON
	- Conservative trim: ON (treats softer sounds as “voice” so less gets trimmed)
	- Fast normalize (single pass): OFF (use full 2‑pass)
	- Concurrency: moderate (fewer files at once to keep the computer calm)
	- Limiter ceiling (LUFS mode): 0.97 or lower for extra headroom

Tip: If ends with white noise aren’t trimmed, make the silence threshold a larger number (e.g., −35 dBFS), or turn OFF “Conservative trim.” The Debug log shows what was detected (start/end) and whether trimming was applied.

## Caveats

- Output folder must be empty before starting (the app enforces this).
- Settings like concurrency and threads interact with your CPU; monitor system responsiveness and adjust.

## Troubleshooting

- If you see errors, open the Debug log panel for details. You can also open DevTools via the app menu.
- If trimming doesn’t apply, check the log for “Detect config” and “Trim applied” lines, and adjust threshold/padding.
- If Peak dBFS mode appears to do nothing, check the Debug log for a line like “Peak mode: measuredMax=… dB, target=… dB, gain=… dB”. If measuredMax is n/a, ensure the analysis pass ran (it should). If gain is 0.00 dB with a quiet file, verify the “Only boost (don’t attenuate)” toggle and your target (e.g., −9 dBFS).
- If a file fails to process, the batch will stop and report the error; re‑run after addressing the issue.

## Glossary (simple explanations)

- LUFS: a way to measure how loud speech/music sounds to people. Target is −16 (spoken audio standard in many tools).
- True‑peak (TP): the highest “in‑between” peak after converting to the final format. LUFS mode aims for −1.0 dBFS TP to be safe.
- Limiter (LUFS mode): a safety ceiling so loud bits don’t clip (distort). We use 0.97 (just below 0 dB) by default.
- Auto‑trim: cut silence (or steady noise) at the beginning and end of a clip. You can keep some padding so speech isn’t cut too tight.
- Silence threshold (dBFS): how quiet is considered “silence.” A larger number (e.g., −35) means more gets treated as silence.
- Concurrency: how many files are processed at the same time.
- Threads per process: how much CPU a single file is allowed to use. Fewer threads per file can help when many files run in parallel.

## Attribution

Code generated almost entirely by VS Code Copilot (GPT-5), with some consultation with Claude/Sonet 4.5 about ideal settings for acoustic analysis / language documentation.

## License and third‑party notices

- Copyright © 2025 Seth Johnston
- License: AGPL‑3.0 (see `LICENSE`)
- Third‑party notices: see `THIRD_PARTY_NOTICES.md`
