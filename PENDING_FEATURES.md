# Pending Features & Work Items

## ⏸ PAUSED 2026-10-02: ship v2.0.2 (the issue #2 fix) through a Windows x64 build workflow

**Status:** requested by Seth, not started. The #2 fix itself is on `dev` (cdec538, 9aa4f74) and
tested from source. The work was paused before anything was built.

**Asked for:** a GitHub Actions workflow that builds the x64 Windows `.exe` and publishes it as a
**pre-release**. Seth promotes it to a full release himself after testing the fix.

**What the build must match (read from the repo):**
- **Artifact:** a single **portable** onefile `.exe`, not an installer. `bulk_audio_normalizer.spec`
  bundles everything into one `EXE(...)` on Windows, and `build_windows.bat` says "Creates a portable
  .exe". v2.0.1 shipped `Bulk.Audio.Normalizer.exe`; GitHub turned the spaces in
  `dist/windows/Bulk Audio Normalizer.exe` into dots.
- **Runner and Python:** `runs-on: windows-latest` with `actions/setup-python` `architecture: x64`.
  Assert `platform.machine() == 'AMD64'` before building. Then pip install
  `requirements.txt` + `requirements-build.txt`; consider pinning pywebview, which is unpinned and
  would pull 6.x.
- **FFmpeg:** must be in `python_webview/bin/windows/` before PyInstaller runs, and those files are
  gitignored. `setup_ffmpeg.py` copies them from the npm package `ffmpeg-static` (`npm install`
  first). Check that the ffmpeg-static Windows binary is x64, and check its licence note in
  THIRD_PARTY_NOTICES.md.
- **Tests:** run `python -m unittest discover -s python_webview/tests` before building.
- **Trigger and release:** a `v*` tag push (plus `workflow_dispatch`). Create a GitHub release with
  `prerelease: true` and attach the `.exe`.
- **The website is safe:** `docs/script.js` reads `releases/latest`, which never returns a
  pre-release. Before promoting to a full release, attach the macOS `.dmg` (`build_mac.sh` +
  `create_dmg_mac.sh` on Seth's Mac), or the site's Mac button falls back to the release page.
- **Cost and policy:** free, because the repo is public and `windows-latest` is a standard runner.
  Seth approved adding it on 2026-10-02. The push needs `ALLOW_WORKFLOW_PUSH=1` (pre-push hook).
  Work on `dev`; `main` only with Seth's OK. Bump to `v2.0.2` (already in the spec, README and
  CHANGELOG on `dev`). Reply on issue #2 once the pre-release exists. Workaround meanwhile: rename
  files to remove the apostrophe.

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
