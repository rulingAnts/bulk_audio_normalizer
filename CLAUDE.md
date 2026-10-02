# bulk_audio_normalizer — Claude Code notes

## Branches: `main` is production, work happens on `dev` (firm policy, 2026-07-07)

People download releases built from `main`. Do all work on `dev`, push `dev` freely, and merge
`dev` into `main` only after Seth has tested it and said so. The local `.git/hooks/pre-push` blocks
pushes to `main` unless `ALLOW_MAIN_PUSH=1` is set; hooks are per-clone, so recreate it after a new
clone (copy it from `mac-audio-player-loader/.git/hooks/pre-push`).

Releases are built by hand, not in CI: `python_webview/build_mac.sh` plus `create_dmg_mac.sh` on macOS,
and `build_windows.bat` on Windows (see `WINDOWS_BUILD_GUIDE.md`). ⚠ The Windows `.exe` must be built
with an x64 (AMD64) Python; an ARM64 Windows VM on Apple silicon produces an exe that will not run on
most users' PCs. Check `python -c "import platform; print(platform.machine())"` says `AMD64` first.
Tagging, creating the GitHub release and uploading the `.dmg` and `.exe` are Seth's steps.

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
