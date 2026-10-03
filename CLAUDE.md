# bulk_audio_normalizer — Claude Code notes

## Branches: `main` is production, work happens on `dev` (firm policy, 2026-07-07)

People download releases built from `main`. Do all work on `dev`, push `dev` freely, and merge
`dev` into `main` only after Seth has tested it and said so. The local `.git/hooks/pre-push` blocks
pushes to `main` unless `ALLOW_MAIN_PUSH=1` is set; hooks are per-clone, so recreate it after a new
clone (copy it from `mac-audio-player-loader/.git/hooks/pre-push`).

Windows: `.github/workflows/build-windows.yml` (added 2026-10-03, approved by Seth on 2026-10-02) builds
the x64 portable `.exe` on `windows-latest` when a `v*` tag is pushed. It runs the unit tests against the
FFmpeg it bundles and publishes the exe as a **pre-release** only (never "latest"). Pinned build
versions are in `python_webview/constraints-windows-build.txt`. By hand, `build_windows.bat` still works
(see `WINDOWS_BUILD_GUIDE.md`). ⚠ A hand-built `.exe` must come from an x64 (AMD64) Python; an ARM64
Windows VM on Apple silicon produces an exe that will not run on most users' PCs. Check
`python -c "import platform; print(platform.machine())"` says `AMD64` first.
macOS is built by hand: `python_webview/build_mac.sh` plus `create_dmg_mac.sh`. Pushing tags, promoting a
pre-release to a full release and uploading the `.dmg` are Seth's steps.

## ⚠️ GitHub costs — ask before anything billable (firm policy, 2026-07-07)

**Claude: never trigger anything that can incur GitHub charges without Seth's explicit approval AND a
stated cost estimate first.**

- FREE, always: Actions on **public** repos with **standard** GitHub-hosted runners; self-hosted
  runners; GitHub Pages.
- METERED (free monthly quota, then paid): Actions in **private** repos (2,000 min/mo; **Windows
  counts 2×, macOS 10×**); Codespaces; Packages; Git LFS.
- **ALWAYS billable, even on public repos: larger / GPU runners** (anything beyond the standard
  `ubuntu-latest` / `windows-latest` / `macos-latest` tiers).
- Safety valve: with **no payment method on file, GitHub blocks usage at the quota and cannot bill**
  — keep it that way, or set stop-usage budgets.

So WITHOUT Seth's explicit OK (and cost), do **not**: add or change `.github/workflows/**`; use a
non-standard `runs-on:`; add a `schedule:` (cron) trigger; create Codespaces; use Git LFS; publish
private Packages; or change the plan / budgets. The local `.git/hooks/pre-push` also blocks workflow
pushes (override `ALLOW_WORKFLOW_PUSH=1`) — set that flag only after Seth approves that specific change.
