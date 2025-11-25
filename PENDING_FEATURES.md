# Pending Features & Work Items

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
