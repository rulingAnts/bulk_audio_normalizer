# Pending Features & Work Items

## v2.0.2: published as a pre-release on 2026-10-03 — what is left

**Status:** the `v2.0.2` tag built on GitHub Actions (run 37088902886): 48/48 tests passed on Windows
with real FFmpeg and BlackBrix's file names, and the portable x64 `Bulk.Audio.Normalizer.exe`
(64 MB, PE32+ x86-64 GUI) is on the **pre-release**
https://github.com/rulingAnts/bulk_audio_normalizer/releases/tag/v2.0.2. `v2.0.1` is still
"latest", so the site's main download buttons are unchanged. The home page shows a "Testing a fix?"
notice linking to the pre-release (`main`, fb03689).

**Before promoting v2.0.2 to a full release:**
- Confirm the fix on a real Windows PC (ask on issue #2; the exe itself is never launched in CI).
- Try the macOS `.dmg` on a real Mac. It is built by `.github/workflows/build-macos.yml` (Apple
  silicon only; FFmpeg 6.1.6 from source, LGPLv2.1) and attached with
  `ffmpeg-6.1.6-source.tar.xz`, which must stay next to it (the LGPL asks for the source in the
  same place). Until a full release has a `.dmg`, the site's Mac button offers the newest release
  that has one and says "pre-release".
- Promoting it also fixes the README's download line, which points at the v2.0.2 pre-release for
  macOS for now.
- Delete `#prerelease-notice` from `docs/index.html` when you promote it. `docs/script.js` hides it
  once no newer pre-release exists, but visitors without JavaScript or GitHub API access still see
  it.
- Merge `dev` into `main`.

**Re-running the build:** push the tag again, or use "Run workflow" once the workflow is on `main`
(GitHub offers workflow_dispatch only for workflows on the default branch). An existing release
keeps its notes and pre-release flag; only the exe is replaced.

**Found while reviewing v2.0.2, not fixed (none of them is new in 2.0.2):**
- **LUFS two-pass almost never runs:** with verbose logs off (the default), the analysis pass runs
  at `-v error` and loudnorm prints its measurement at info level. Every file falls back to
  single-pass while the UI says "2-pass (high quality)". Fix: run the analysis pass at
  `-v info -hide_banner -nostats` whatever the verbose setting.
- **LUFS output is 192 kHz** (a 16 kHz input came out at 192000 Hz). loudnorm upsamples; keep the
  input's rate (`-ar` from ffprobe) — this matters for linguistic recordings.
- **Very short clips (< 0.4 s) measure "-inf" in LUFS mode** and the render fails; they are now
  listed at the end instead of failing silently.
- **Pause/resume (buttons hidden today):** the file interrupted by a pause is skipped, not redone,
  after resume; two small races on that path (a resume between the render returning and the
  canceled check; `kill_job` vs `cleanup_job` deleting the same key). Fix before showing the
  buttons again.
- **Outputs from an earlier batch inside the input folder are processed again** by later batches
  (only the current batch's output folder is excluded); the preview samples from them too.
- **Releases ship the exe only:** THIRD_PARTY_NOTICES.md's terms (ship the notice, the AGPL text
  and the corresponding source, including FFmpeg's) are not met by an exe-only release — same as
  v2.0.1.
- **Windows FFmpeg is a GPLv3 build with no source offer.** `ffmpeg.exe` (gyan.dev 6.1.1 via
  ffmpeg-static) and `ffprobe.exe` (4.0.2, an old zeranoe build via ffprobe-static) link many
  GPL libraries, whose complete source the GPL asks us to offer. Simplest fix: build Windows'
  FFmpeg from source the way the Mac's is (LGPL, no external libraries; cross-compile with
  mingw on ubuntu-latest, or MSYS2 on windows-latest), attach its source the same way, and drop
  ffprobe-static.
- **No Intel Mac build.** The Mac app is arm64 only (macos-15 runner). An x86_64 build
  (`macos-15-intel` runner, standard and free on this public repo) or a universal one would cover
  older Macs.
- **Not notarized:** first launch needs Privacy & Security → "Open Anyway". Notarizing needs an
  Apple Developer account (99 USD a year).

## 🔥 PRIORITY: Clipped/Chopped Recording Detection Tool

**Status:** Design phase - awaiting user decisions before implementation

**User Request:** Add an optional tool (near Preview section) to detect recordings that are suspected of being "chopped off" - recordings where the record button was pushed too late (missing audio at start) or stop button pushed too soon (audio cut off at end).

### Design Questions to Answer:

1. **Detection Method:**
   - What signals indicate a "chopped" recording?
   - Sudden onset at full amplitude vs. natural fade-in?
   - Audio cutting off mid-word/mid-phoneme at end?
   - Analyze waveform envelope (starts/ends above threshold)?
   - Check zero-crossing patterns or spectral content at edges?

2. **Threshold Preferences:**
   - What amplitude threshold indicates "starts too abruptly"? (e.g., >-20 dB within first 50ms?)
   - What duration to check at edges? (50ms? 100ms? 200ms?)
   - Configurable or smart defaults?

3. **UI/UX Approach:**
   - Separate "Detect Chopped Recordings" button near Preview?
   - Integrate into Preview (highlight chopped files)?
   - Scan all files or just sample?
   - Display as list with confidence scores?

4. **Action Options:**
   - Just flag/report for manual review?
   - Option to exclude flagged files from batch?
   - Generate report file (CSV/JSON)?
   - Show waveform previews of flagged edges?

### Proposed Implementation (Initial Suggestion):

**Detection Logic:**
- Analyze first 100ms and last 100ms of each recording
- Flag "possibly chopped start" if audio begins above -15 dB within first 50ms
- Flag "possibly chopped end" if audio ends above -15 dB in final 50ms
- Check for abrupt spectral changes (voice suddenly appearing/disappearing)

**UI Placement:**
- Add "Check for Clipped Edges" button in Preview section
- Scans all input files with progress indicator
- Shows results in modal/panel with:
  - List of flagged files
  - Issue type (start/end/both)
  - Severity indicator (mild/moderate/severe)
  - Play button to preview each file's edges
  - Option to open file location in Finder/Explorer

**Output:**
- Visual list in the app
- Optional: Export findings to CSV for record-keeping

### Next Steps:
1. User to review and approve/modify design approach
2. Create detailed prompt for GitHub Copilot coding agent
3. Implement feature with proper testing

---

## Other Known Issues

See CHANGELOG.md "Known Issues" section for:
- Pause/Resume functionality disabled (missing files reported)
- Verification of missing files needed (rare edge cases)

---

**Last Updated:** 2025-11-24
**Context:** User pausing this project to work on other tasks
