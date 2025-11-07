const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const inputPath = $('#inputPath');
const outputPath = $('#outputPath');
const btnInput = $('#btnInput');
const btnOutput = $('#btnOutput');
const btnStart = $('#btnStart');
const btnCancel = $('#btnCancel');
const btnClearOutput = $('#btnClearOutput');
const stopStatus = $('#stopStatus');
const outputValidation = $('#outputValidation');
// Notice elements
const noticeMin = $('#noticeMin');
const noticeBrief = $('#noticeBrief');
const noticeFull = $('#noticeFull');
// Notice controls (top-right +/- only)
const btnNoticePlusMin = $('#btnNoticePlusMin');
const btnNoticePlusBrief = $('#btnNoticePlusBrief');
const btnNoticeMinusBrief = $('#btnNoticeMinusBrief');
const btnNoticeMinusFull = $('#btnNoticeMinusFull');
const btnNoticeCollapseMin2 = $('#btnNoticeCollapseMin2');
const profileSelect = $('#profileSelect');
const profileDesc = $('#profileDesc');
const bitDepthSelect = $('#bitDepth');
const normModeSelect = $('#normMode');
const overallBar = $('#overallBar');
const overallPct = $('#overallPct');
const overallCount = $('#overallCount');
const batchStatus = $('#batchStatus');
const fileList = $('#fileList');
const logView = $('#logView');
const btnClearLog = $('#btnClearLog');
// Preview elements
const btnPreview = $('#btnPreview');
const previewCount = $('#previewCount');
const previewList = $('#previewList');
const previewInfo = $('#previewInfo');
// Cross-platform converter for local file paths to file:// URLs
function toFileUrl(p) {
  if (!p) return '';
  if (p.startsWith('file://')) return p;
  let pathStr = String(p);
  // Normalize Windows backslashes to forward slashes
  pathStr = pathStr.replace(/\\/g, '/');
  // Ensure drive letter has a preceding slash on Windows (e.g., C:/ -> /C:/)
  if (/^[A-Za-z]:\//.test(pathStr)) pathStr = '/' + pathStr;
  return 'file://' + encodeURI(pathStr);
}

// Settings inputs
const inLufs = $('#lufsTarget');
const inPeakTarget = $('#peakTargetDb');
const chkPeakOnlyBoost = $('#peakOnlyBoost');
const inTP = $('#tpMargin');
const inLimiter = $('#limiterLimit');
const inConc = $('#concurrency');
const chkAutoTrim = $('#autoTrim');
const inTrimPadMs = $('#trimPadMs');
const inTrimThresholdDb = $('#trimThresholdDb');
const inTrimMinDurMs = $('#trimMinDurationMs');
const inTrimMinFileMs = $('#trimMinFileMs');
const chkTrimConservative = $('#trimConservative');
const chkTrimHPF = $('#trimHPF');
const chkVerbose = $('#verboseLogs');
const chkFastNormalize = $('#fastNormalize');
const inFfmpegThreads = $('#ffmpegThreads');
const chkFastTrim = $('#fastTrim');

let inputDir = '';
let outputDir = '';
let running = false;
let stopping = false;
let fileItems = new Map(); // id -> DOM refs
let autoScrollFiles = true;
// Resume/session state
// No resume mode: each Start requires an empty output folder and resets UI

function setSettingsLocked(locked) {
  const ctrls = [
    profileSelect, bitDepthSelect, normModeSelect, inLufs, inPeakTarget, chkPeakOnlyBoost, inTP, inLimiter,
    inConc, chkAutoTrim, inTrimPadMs, inTrimThresholdDb, inTrimMinDurMs, inTrimMinFileMs, chkTrimConservative,
    chkTrimHPF, chkVerbose, chkFastNormalize, inFfmpegThreads, chkFastTrim
  ];
  ctrls.forEach((el) => { if (el) el.disabled = !!locked; });
}

function clearUI() {
  fileList.innerHTML = '';
  overallBar.style.width = '0%';
  overallPct.textContent = '0%';
  overallCount.textContent = '0/0';
  fileItems.clear();
  logView.textContent = '';
  if (typeof previewList !== 'undefined') previewList.innerHTML = '';
  if (typeof previewInfo !== 'undefined') previewInfo.textContent = '';
  phaseActive.detect = phaseActive.analyze = phaseActive.render = 0;
  batchStatus.textContent = '';
  if (stopStatus) stopStatus.textContent = '';
}

function resetSessionAndUI() {
  setSettingsLocked(false);
  btnStart.textContent = 'Start';
  clearUI();
}

// Auto-scroll file list to bottom unless the user scrolls up
fileList.addEventListener('scroll', () => {
  const nearBottom = fileList.scrollTop + fileList.clientHeight >= fileList.scrollHeight - 24;
  autoScrollFiles = nearBottom;
});
const phaseActive = { detect: 0, analyze: 0, render: 0 };
let throttleInfo = '';

function updateBatchStatus() {
  let msg = '';
  if (phaseActive.render > 0) msg = 'Rendering…';
  else if (phaseActive.analyze > 0) msg = 'Analyzing…';
  else if (phaseActive.detect > 0) msg = 'Detecting…';
  else if (running) msg = 'Queued…';
  if (throttleInfo) msg = msg ? `${msg} • ${throttleInfo}` : throttleInfo;
  if (msg) batchStatus.textContent = msg;
}

const SETTINGS_KEY = 'ban_settings_v1';

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) {
      // No saved settings: set smart defaults
      const cores = navigator.hardwareConcurrency || 4;
      inConc.value = Math.max(1, cores - 1);
      if (normModeSelect) normModeSelect.value = 'peak';
      return;
    }
    const s = JSON.parse(raw);
    if (s.lufsTarget != null) inLufs.value = s.lufsTarget;
    if (s.tpMargin != null) inTP.value = s.tpMargin;
    if (s.limiterLimit != null) inLimiter.value = s.limiterLimit;
    if (s.concurrency != null) inConc.value = s.concurrency;
    if (typeof s.autoTrim === 'boolean') chkAutoTrim.checked = s.autoTrim;
    if (s.trimPadMs != null) inTrimPadMs.value = s.trimPadMs;
    if (s.trimThresholdDb != null) inTrimThresholdDb.value = s.trimThresholdDb;
    if (s.trimMinDurationMs != null) inTrimMinDurMs.value = s.trimMinDurationMs;
    if (s.trimMinFileMs != null) inTrimMinFileMs.value = s.trimMinFileMs;
    if (typeof s.trimConservative === 'boolean') chkTrimConservative.checked = s.trimConservative;
    if (typeof s.trimHPF === 'boolean') chkTrimHPF.checked = s.trimHPF;
    if (typeof s.verboseLogs === 'boolean') chkVerbose.checked = s.verboseLogs;
    if (typeof s.fastNormalize === 'boolean') chkFastNormalize.checked = s.fastNormalize;
    if (s.ffmpegThreads != null) inFfmpegThreads.value = String(s.ffmpegThreads);
    if (typeof s.fastTrim === 'boolean') chkFastTrim.checked = s.fastTrim; else chkFastTrim.checked = true;
    if (s.targetBitDepth != null) bitDepthSelect.value = String(s.targetBitDepth);
    if (s.normMode) normModeSelect.value = s.normMode;
    if (s.peakTargetDb != null) inPeakTarget.value = String(s.peakTargetDb);
    if (typeof s.peakOnlyBoost === 'boolean') chkPeakOnlyBoost.checked = s.peakOnlyBoost; else chkPeakOnlyBoost.checked = true;
  } catch {}
  // If settings exist but concurrency not set, set smart default
  try {
    const saved = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
    if (saved && saved.concurrency == null) {
      const cores = navigator.hardwareConcurrency || 4;
      inConc.value = Math.max(1, cores - 1);
    }
  } catch {}
}

function saveSettings() {
  const s = currentSettings();
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function currentSettings() {
  return {
    lufsTarget: Number(inLufs.value),
    peakTargetDb: Number(inPeakTarget.value),
    tpMargin: Number(inTP.value),
    limiterLimit: Number(inLimiter.value),
    concurrency: Math.max(1, Number(inConc.value || 1)),
    autoTrim: !!chkAutoTrim.checked,
    trimPadMs: Math.max(0, Number(inTrimPadMs.value || 0)),
    trimThresholdDb: Number(inTrimThresholdDb.value),
    trimMinDurationMs: Math.max(0, Number(inTrimMinDurMs.value || 0)),
    trimDetect: 'rms',
    trimMinFileMs: Math.max(0, Number(inTrimMinFileMs.value || 0)),
    trimConservative: !!chkTrimConservative.checked,
    trimHPF: !!chkTrimHPF.checked,
    verboseLogs: !!chkVerbose.checked,
    fastNormalize: !!chkFastNormalize.checked,
    ffmpegThreads: Math.max(0, Number(inFfmpegThreads.value || 0)) || 0,
    fastTrim: !!chkFastTrim.checked,
    peakOnlyBoost: !!chkPeakOnlyBoost.checked,
    targetBitDepth: (() => {
      const v = (bitDepthSelect?.value || '16');
      if (v === 'original') return 'original';
      const n = Number(v);
      if (Number.isFinite(n)) return Math.max(16, Math.min(24, n));
      return 16;
    })(),
    normMode: ((normModeSelect && normModeSelect.value) === 'lufs') ? 'lufs' : 'peak',
  };
}

function recommendedConcurrency() {
  const cores = navigator.hardwareConcurrency || 4;
  return Math.max(1, cores - 1);
}

function applyPreset(name) {
  const recConc = recommendedConcurrency();
  let desc = '';
  if (name === 'fast') {
    // Fastest processing
    chkAutoTrim.checked = false; // absolute fastest; user can switch to Balanced for trimming
    chkFastTrim.checked = true;
    chkFastNormalize.checked = true;
    inTrimThresholdDb.value = '-35';
    inTrimPadMs.value = '400';
    inConc.value = recConc;
    inFfmpegThreads.value = '1';
    desc = 'Fastest: focus on speed. Trimming off; single-pass normalize; many files at once.';
  } else if (name === 'balanced') {
    chkAutoTrim.checked = true;
    chkFastTrim.checked = true;
    chkFastNormalize.checked = false;
    inTrimThresholdDb.value = '-45';
    inTrimPadMs.value = '800';
    inConc.value = recConc;
    inFfmpegThreads.value = '1';
    desc = 'Balanced: good speed and safe defaults. Fast trim on; precise 2-pass normalize.';
  } else if (name === 'quality') {
    chkAutoTrim.checked = true;
    chkFastTrim.checked = false; // use FFmpeg detect
    chkTrimHPF.checked = true;
    chkTrimConservative.checked = true;
    chkFastNormalize.checked = false;
    inTrimThresholdDb.value = '-50';
    inTrimPadMs.value = '800';
    inConc.value = String(Math.max(1, Math.floor(recommendedConcurrency() / 2)));
    inFfmpegThreads.value = '0'; // auto
    desc = 'Highest quality/safety: most cautious trimming and full accuracy; CPU/RAM heavy. Adaptive throttling will protect your system.';
  } else {
    desc = 'Custom: your own combination. Open Advanced… to tweak.';
  }
  profileDesc.textContent = desc;
  saveSettings();
}

function describePresetForCurrent() {
  const s = currentSettings();
  const recConc = recommendedConcurrency();
  const isFast = !s.autoTrim && s.fastTrim && s.fastNormalize && Number(s.concurrency) === recConc && Number(s.ffmpegThreads) === 1;
  const isBalanced = s.autoTrim && s.fastTrim && !s.fastNormalize && Number(s.concurrency) === recConc && Number(s.ffmpegThreads) === 1;
  const isQuality = s.autoTrim && !s.fastTrim && s.trimHPF && s.trimConservative && !s.fastNormalize && Number(s.concurrency) === Math.max(1, Math.floor(recConc / 2)) && Number(s.ffmpegThreads) === 0;
  if (isFast) return 'fast';
  if (isBalanced) return 'balanced';
  if (isQuality) return 'quality';
  return 'custom';
}

function setRunning(state) {
  running = state;
  const disableAll = running || stopping;
  btnStart.disabled = disableAll || !inputDir || !outputDir;
  btnCancel.disabled = !running;
  btnInput.disabled = disableAll;
  btnOutput.disabled = disableAll;
  btnClearOutput.disabled = disableAll || !outputDir;
  btnPreview.disabled = disableAll || !inputDir; // can preview without output
}

// Persist settings on change
[inLufs, inPeakTarget, chkPeakOnlyBoost, inTP, inLimiter, inConc, chkAutoTrim, inTrimPadMs, inTrimThresholdDb, inTrimMinDurMs, inTrimMinFileMs, chkTrimConservative, chkTrimHPF, chkVerbose, chkFastNormalize, inFfmpegThreads, chkFastTrim, bitDepthSelect, normModeSelect].forEach((el) => el.addEventListener('change', () => {
  saveSettings();
  const p = describePresetForCurrent();
  profileSelect.value = p;
  if (p === 'fast') profileDesc.textContent = 'Fastest: focus on speed. Trimming off; single-pass normalize; many files at once.';
  else if (p === 'balanced') profileDesc.textContent = 'Balanced: good speed and safe defaults. Fast trim on; precise 2-pass normalize.';
  else if (p === 'quality') profileDesc.textContent = 'Highest quality/safety: most cautious trimming and full accuracy; slightly slower.';
  else profileDesc.textContent = 'Custom: your own combination. Open Advanced… to tweak.';
  updateAdvancedVisibility();
}));
loadSettings();
updateAdvancedVisibility();

function updateAdvancedVisibility() {
  const mode = (normModeSelect && normModeSelect.value) === 'lufs' ? 'lufs' : 'peak';
  const isPeak = mode === 'peak';
  const advPill = document.querySelector('#advModePill');
  if (advPill) advPill.textContent = isPeak ? 'Mode: Peak dBFS' : 'Mode: LUFS';

  const showGroup = (selector, show) => {
    document.querySelectorAll(selector).forEach((el) => {
      el.style.display = show ? '' : 'none';
    });
  };
  const labelFor = (id) => document.querySelector(`label[for="${id}"]`);
  const enableDim = (id, on, reason) => {
    const el = document.getElementById(id);
    const lab = labelFor(id);
    if (!el) return;
    el.disabled = !on;
    if (lab) {
      if (!on) lab.classList.add('dimmed'); else lab.classList.remove('dimmed');
    }
    if (!on && reason) {
      if (!el.dataset.originalTitle) el.dataset.originalTitle = el.getAttribute('title') || '';
      el.setAttribute('title', reason);
    } else if (on && el.dataset.originalTitle !== undefined) {
      el.setAttribute('title', el.dataset.originalTitle);
      delete el.dataset.originalTitle;
    }
  };

  // Hide/show mode-specific controls via wrappers
  showGroup('.adv-lufs', !isPeak);
  showGroup('.adv-peak', isPeak);

  // Trimming controls group
  const trimOn = !!chkAutoTrim.checked;
  enableDim('trimPadMs', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('trimThresholdDb', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('trimMinDurationMs', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('trimMinFileMs', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('trimConservative', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('trimHPF', trimOn, 'Disabled because Auto-trim is OFF');
  enableDim('fastTrim', trimOn, 'Disabled because Auto-trim is OFF');
}

// Notice behavior (three levels: min <-> brief <-> full)
const NOTICE_STATE_KEY = 'ban_notice_state'; // 'min' | 'brief' | 'full'
function setNoticeState(state) {
  localStorage.setItem(NOTICE_STATE_KEY, state);
  if (state === 'min') {
    noticeMin.classList.remove('hidden');
    noticeBrief.classList.add('hidden');
    noticeFull.classList.add('hidden');
  } else if (state === 'brief') {
    noticeMin.classList.add('hidden');
    noticeBrief.classList.remove('hidden');
    noticeFull.classList.add('hidden');
  } else if (state === 'full') {
    noticeMin.classList.add('hidden');
    noticeBrief.classList.add('hidden');
    noticeFull.classList.remove('hidden');
  }
}

btnNoticePlusMin?.addEventListener('click', () => setNoticeState('brief'));
btnNoticePlusBrief?.addEventListener('click', () => setNoticeState('full'));
btnNoticeMinusBrief?.addEventListener('click', () => setNoticeState('min'));
btnNoticeMinusFull?.addEventListener('click', () => setNoticeState('brief'));
btnNoticeCollapseMin2?.addEventListener('click', () => setNoticeState('min'));

// Initialize notice state (default brief)
setNoticeState(localStorage.getItem(NOTICE_STATE_KEY) || 'brief');

// Initialize preset selector based on current settings
profileSelect.value = describePresetForCurrent();
if (profileSelect.value === 'custom') profileDesc.textContent = 'Custom: your own combination. Open Advanced… to tweak.';
profileSelect.addEventListener('change', () => {
  applyPreset(profileSelect.value);
});

btnInput.addEventListener('click', async () => {
  const dir = await window.api.selectInputFolder(inputDir);
  if (dir) {
    inputDir = dir;
    inputPath.value = dir;
    // Changing input requires empty output before new start and clears UI
    resetSessionAndUI();
    if (outputDir) {
      const empty = await window.api.validateOutputEmpty(outputDir);
      outputValidation.textContent = empty ? 'Output folder is empty ✓' : 'Output folder must be empty.';
      outputValidation.style.color = empty ? '#2ea043' : '#d1242f';
      btnStart.disabled = (running || stopping) || !inputDir || !outputDir || !empty;
    }
  }
  btnStart.disabled = running || !inputDir || !outputDir;
});

btnOutput.addEventListener('click', async () => {
  const dir = await window.api.selectOutputFolder(outputDir);
  if (dir) {
    outputDir = dir;
    outputPath.value = dir;
    // Selecting a new output enforces empty before (re)starting and clears UI
    resetSessionAndUI();
    const empty = await window.api.validateOutputEmpty(dir);
    outputValidation.textContent = empty ? 'Output folder is empty ✓' : 'Output folder must be empty.';
    outputValidation.style.color = empty ? '#2ea043' : '#d1242f';
    btnStart.disabled = (running || stopping) || !inputDir || !outputDir || !empty;
  }
});

btnClearOutput.addEventListener('click', async () => {
  if (!outputDir) return;
  const ok = confirm(`Delete ALL contents of:\n${outputDir}\n\nThis cannot be undone.`);
  if (!ok) return;
  const res = await window.api.clearOutputFolder(outputDir);
  if (res) {
    outputValidation.textContent = 'Output folder is empty ✓';
    outputValidation.style.color = '#2ea043';
    // Clearing output resets session and UI
    resetSessionAndUI();
  } else {
    outputValidation.textContent = 'Could not clear output folder.';
    outputValidation.style.color = '#d1242f';
  }
  btnStart.disabled = (running || stopping) || !inputDir || !outputDir;
});

btnStart.addEventListener('click', async () => {
  if (!inputDir || !outputDir) return;
  // Enforce empty output before starting; no resume support
  const empty = await window.api.validateOutputEmpty(outputDir);
  if (!empty) {
    outputValidation.textContent = 'Output folder must be empty.';
    outputValidation.style.color = '#d1242f';
    return;
  }
  // Clear UI for a fresh run
  fileList.innerHTML = '';
  overallBar.style.width = '0%';
  overallPct.textContent = '0%';
  overallCount.textContent = '0/0';
  fileItems.clear();
  logView.textContent = '';
  if (typeof previewList !== 'undefined') previewList.innerHTML = '';
  if (typeof previewInfo !== 'undefined') previewInfo.textContent = '';
  phaseActive.detect = phaseActive.analyze = phaseActive.render = 0;
  batchStatus.textContent = 'Preparing…';
  if (stopStatus) stopStatus.textContent = '';

  setRunning(true);
  const s = currentSettings();
  const res = await window.api.startProcessing({ inputDir, outputDir, settings: s, concurrency: s.concurrency });
  if (!res.ok) {
    alert(res.error || 'Failed to start processing');
    setRunning(false);
  }
});

btnCancel.addEventListener('click', () => {
  // Show stopping state immediately; actual "stopped" will be signaled from main
  stopping = true;
  if (stopStatus) stopStatus.textContent = 'Stopping…';
  setRunning(true); // disables controls while stopping
  try { window.api.cancelProcessing(); } catch {}
});

function ensureFileItem(id, name) {
  if (fileItems.has(id)) return fileItems.get(id);
  const el = document.createElement('div');
  el.className = 'file-item';
  el.innerHTML = `
    <div class="top">
      <div class="name" title="${name}">${name}</div>
    </div>
    <div class="phase-bars">
      <div class="phase">
        <span class="label">Detect</span>
        <div class="progress small"><div class="bar" data-role="phase-detect" style="width:0%"></div></div>
      </div>
      <div class="phase">
        <span class="label">Analyze</span>
        <div class="progress small"><div class="bar" data-role="phase-analyze" style="width:0%"></div></div>
      </div>
      <div class="phase">
        <span class="label">Render</span>
        <div class="progress small"><div class="bar" data-role="phase-render" style="width:0%"></div></div>
      </div>
    </div>
  `;
  fileList.appendChild(el);
  fileItems.set(id, el);
  if (autoScrollFiles) {
    fileList.scrollTop = fileList.scrollHeight;
  }
  return el;
}

window.api.onFileStart(({ fileId, name }) => {
  ensureFileItem(fileId, name);
});

let batchStartTs = 0;
window.api.onBatchStart(({ total }) => {
  if (Number.isFinite(total)) {
    overallCount.textContent = `0/${total}`;
  }
  batchStartTs = Date.now();
  if (running) batchStatus.textContent = 'Queued…';
});

function fmtHMS(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const hh = Math.floor(s / 3600).toString().padStart(2, '0');
  const mm = Math.floor((s % 3600) / 60).toString().padStart(2, '0');
  const ss = Math.floor(s % 60).toString().padStart(2, '0');
  return (hh !== '00' ? hh + ':' : '') + mm + ':' + ss;
}

window.api.onProgress(({ fileId, filePct, overallPct: oPct, completed, total }) => {
  const pctVal = Number.isFinite(oPct) ? oPct : 0;
  overallBar.style.width = `${pctVal.toFixed(1)}%`;
  overallPct.textContent = `${pctVal.toFixed(1)}%`;
  if (Number.isFinite(completed) && Number.isFinite(total)) {
    overallCount.textContent = `${completed}/${total}`;
  }
  // Time estimates
  if (batchStartTs) {
    const elapsed = Date.now() - batchStartTs;
    const pct = Math.max(0.1, Math.min(99.9, pctVal));
    const eta = elapsed * (100 / pct - 1);
    const overallTime = document.querySelector('#overallTime');
    if (overallTime) overallTime.textContent = `Elapsed ${fmtHMS(elapsed)} • ETA ${fmtHMS(eta)}`;
  }

  // Lazily create item on first progress signal if needed
  let itemEl = fileItems.get(fileId);
  if (!itemEl) itemEl = ensureFileItem(fileId, `File ${fileId}`);
  // No per-file overall bar; only phase bars are shown now
});

window.api.onFileDone(({ fileId }) => {
  const itemEl = fileItems.get(fileId);
  if (itemEl) {
    itemEl.classList.add('done');
    // Mark all phases complete if not already
    ['phase-detect','phase-analyze','phase-render'].forEach((role) => {
      const b = itemEl.querySelector(`[data-role="${role}"]`);
      if (b) b.style.width = '100%';
    });
  }
});

window.api.onAllDone(() => {
  setRunning(false);
  batchStatus.textContent = 'Completed';
  throttleInfo = '';
});

window.api.onStopped(() => {
  stopping = false;
  setRunning(false);
  batchStatus.textContent = 'Stopped';
  if (stopStatus) stopStatus.textContent = '';
  throttleInfo = '';
  // Enforce empty output before allowing new Start (no resume)
  (async () => {
    if (outputDir) {
      const empty = await window.api.validateOutputEmpty(outputDir);
      outputValidation.textContent = empty ? 'Output folder is empty ✓' : 'Output folder must be empty.';
      outputValidation.style.color = empty ? '#2ea043' : '#d1242f';
      btnStart.disabled = !empty || !inputDir || !outputDir;
    } else {
      btnStart.disabled = !inputDir || !outputDir;
    }
  })();
});

window.api.onError(({ message }) => {
  alert(message);
  batchStatus.textContent = 'Error';
});

window.api.onPhaseEvent(({ fileId, phase, status, pct }) => {
  const itemEl = fileItems.get(fileId);
  if (!itemEl) return;
  const roleMap = { detect: 'phase-detect', analyze: 'phase-analyze', render: 'phase-render' };
  const role = roleMap[phase];
  if (!role) return;
  const bar = itemEl.querySelector(`[data-role="${role}"]`);
  if (!bar) return;
  if (status === 'start') {
    bar.style.width = '0%';
    bar.classList.add('active');
    if (phase in phaseActive) phaseActive[phase] = Math.max(0, (phaseActive[phase] || 0) + 1);
    updateBatchStatus();
  } else if (status === 'progress' && Number.isFinite(pct)) {
    bar.style.width = `${pct.toFixed(1)}%`;
  } else if (status === 'done') {
    bar.style.width = '100%';
    bar.classList.remove('active');
    if (phase in phaseActive) phaseActive[phase] = Math.max(0, (phaseActive[phase] || 0) - 1);
    updateBatchStatus();
  }
});

window.api.onLog(({ fileId, phase, line }) => {
  // Throttle append by batching might be ideal; for simplicity append directly
  const trimmed = String(line).replace(/\u0000/g, '').trimEnd();
  if (!trimmed) return;
  logView.textContent += `[${phase}] ${fileId}: ${trimmed}\n`;
  logView.scrollTop = logView.scrollHeight;
});

btnClearLog.addEventListener('click', () => {
  logView.textContent = '';
});

// Adaptive throttling updates
window.api.onThrottleEvent?.(({ allowed, base, loadPct, freeMemPct, reason }) => {
  const load = Math.round(loadPct || 0);
  const mem = Math.round(freeMemPct || 0);
  if (allowed < base) throttleInfo = `Throttle: ${allowed}/${base} (CPU ${load}%, free ${mem}%)`;
  else throttleInfo = '';
  updateBatchStatus();
});

// Preview handling
btnPreview.addEventListener('click', async () => {
  if (!inputDir) {
    alert('Select an input folder first.');
    return;
  }
  // Open a dedicated preview window
  await window.api.openPreviewWindow();
  // Keep inline container clean if visible
  if (typeof previewList !== 'undefined') previewList.innerHTML = '';
  if (typeof previewInfo !== 'undefined') previewInfo.textContent = 'Running preview…';
  const s = currentSettings();
  const count = Math.max(1, Math.min(50, Number(previewCount.value || 5)));
  const res = await window.api.startPreview({ inputDir, settings: s, sampleSize: count, concurrency: Math.min(2, s.concurrency || 2) });
  if (!res.ok) {
    alert(res.error || 'Preview failed to start');
    if (typeof previewInfo !== 'undefined') previewInfo.textContent = '';
  } else {
    if (typeof previewInfo !== 'undefined') previewInfo.textContent = `Preview folder: ${res.tmpBase}`;
  }
});

window.api.onPreviewFileDone(({ original, preview, rel }) => {
  const card = document.createElement('div');
  card.className = 'preview-card';
  const display = rel || original.split('/').slice(-1)[0];
  const originalId = `wave_o_${Math.random().toString(36).slice(2)}`;
  const previewId = `wave_p_${Math.random().toString(36).slice(2)}`;
  card.innerHTML = `
    <div class="path" title="${display}">…/${display}</div>
    <div class="players">
      <div class="wave-wrap">
        <strong>Original</strong>
        <div id="${originalId}" class="wave"><div class="loading">Loading…</div></div>
        <div class="controls">
          <button data-role="play-o">Play/Pause</button>
          <button data-role="stop-o">Stop</button>
          <button data-role="play-region-o">Play Region</button>
          <label><input type="checkbox" data-role="loop-o"/> Loop region</label>
          <div class="spacer"></div>
          <button data-role="reveal-original">Reveal original</button>
        </div>
      </div>
      <div class="wave-wrap">
        <strong>Preview</strong>
        <div id="${previewId}" class="wave"><div class="loading">Loading…</div></div>
        <div class="controls">
          <button data-role="play-p">Play/Pause</button>
          <button data-role="stop-p">Stop</button>
          <button data-role="play-region-p">Play Region</button>
          <label><input type="checkbox" data-role="loop-p"/> Loop region</label>
          <div class="spacer"></div>
          <button data-role="reveal-preview">Reveal preview</button>
        </div>
      </div>
    </div>
  `;
  previewList.appendChild(card);

  // Init WaveSurfer instances with regions and dragSelection
  const makeWS = (containerId, url) => {
    const ws = WaveSurfer.create({
      container: '#' + containerId,
      backend: 'MediaElement',
      height: 96,
      waveColor: '#9ecbff',
      progressColor: '#1f6feb',
      cursorColor: '#333',
      responsive: true,
      plugins: [
        WaveSurfer.regions.create({
          dragSelection: true,
        }),
      ],
    });
    ws.load(toFileUrl(url));
    return ws;
  };

  const wsO = makeWS(originalId, original);
  const wsP = makeWS(previewId, preview);

  const btnRO = card.querySelector('[data-role="reveal-original"]');
  const btnRP = card.querySelector('[data-role="reveal-preview"]');
  btnRO.addEventListener('click', () => window.api.revealPath(original));
  btnRP.addEventListener('click', () => window.api.revealPath(preview));

  const getRegion = (ws) => {
    const regions = Object.values(ws.regions.list || {});
    return regions[regions.length - 1];
  };

  const bindControls = (prefix, ws) => {
    const btnPlay = card.querySelector(`[data-role="play-${prefix}"]`);
    const btnStop = card.querySelector(`[data-role="stop-${prefix}"]`);
    const btnPlayRegion = card.querySelector(`[data-role="play-region-${prefix}"]`);
    const chkLoop = card.querySelector(`[data-role="loop-${prefix}"]`);
    btnPlay.addEventListener('click', () => ws.playPause());
    btnStop.addEventListener('click', () => ws.stop());
    btnPlayRegion.addEventListener('click', () => {
      const r = getRegion(ws);
      if (r) {
        ws.play(r.start, r.end);
      } else {
        ws.play();
      }
    });
    ws.on('region-in', (rgn) => {
      if (chkLoop.checked) rgn.playLoop();
    });
    ws.on('region-update-end', (rgn) => {
      // Ensure only one region kept (latest)
      const all = Object.values(ws.regions.list || {});
      for (const other of all) {
        if (other.id !== rgn.id) other.remove();
      }
    });
  };
  bindControls('o', wsO);
  bindControls('p', wsP);
});

window.api.onPreviewDone(({ count, tmpBase }) => {
  previewInfo.textContent = `Preview complete: ${count} files -> ${tmpBase}`;
});
