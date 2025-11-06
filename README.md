# Bulk Audio Normalizer

Electron app to batch-convert WAV files to 16‑bit PCM and loudness-normalize to −16 LUFS with a safety limiter to prevent clipping.

## What it does

- Scans an input folder (recursively) for `.wav`/`.wave` files
- For each file, performs a 2‑pass EBU R128 loudness normalization to −16 LUFS
- Applies a hard limiter after normalization to guarantee no digital clipping
- Writes new files to an (empty) output folder, leaving originals unchanged
- Forces 16‑bit PCM WAV output (`pcm_s16le`)
- Shows an overall progress bar and per‑file progress with a responsive UI

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

## Build distributables

```bash
npm run dist
```

This will package the app using electron-builder into platform-specific artifacts (DMG on macOS, NSIS on Windows, AppImage on Linux). The build is configured to include the FFmpeg/FFprobe binaries and unpack them from the ASAR so they are executable at runtime.

## Notes on loudness and clipping safety

- The app uses FFmpeg's `loudnorm` filter (EBU R128) in 2‑pass mode with user-adjustable targets (default `I=-16, TP=-1.0, LRA=11`).
- After loudness normalization, it applies `alimiter` with adjustable ceiling (default `limit=0.97`, ≈ −0.27 dBFS) as a brick‑wall safety to avoid any inter‑sample or rounding peaks when converting to 16‑bit.
- Output is encoded as 16‑bit PCM WAV. If your source is higher bit depth or float, it will be dithered/quantized by FFmpeg during conversion.

## Settings

- LUFS target (default −16 LUFS)
- True-peak target in dBFS (default −1.0 dBFS)
- Limiter ceiling as linear amplitude 0..1 (default 0.97)
- Concurrency (number of files processed in parallel)
- Auto-trim leading/trailing silence with adjustable parameters:
	- Keep padding on each side (default 500 ms)
	- Silence threshold in dBFS (default −50 dB)
	- Minimum silence duration (default 200 ms)

Settings are persisted locally per machine.

## Caveats

- Output folder must be empty before starting (the app enforces this).
- Hundreds of short files are fine; you can tune concurrency in code (default up to 4 simultaneous jobs based on CPU count).

## Troubleshooting

- If you see errors, open the DevTools via the Electron app menu and check the console for details.
- If a file fails to process, the batch will stop and report the error; re‑run after addressing the issue.

## License and third‑party notices

- License: AGPL‑3.0‑or‑later (see `LICENSE`)
- Third‑party notices: see `THIRD_PARTY_NOTICES.md`
