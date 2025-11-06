const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

const inputPath = $('#inputPath');
const outputPath = $('#outputPath');
const btnInput = $('#btnInput');
const btnOutput = $('#btnOutput');
const btnStart = $('#btnStart');
const btnCancel = $('#btnCancel');
const outputValidation = $('#outputValidation');
const overallBar = $('#overallBar');
const overallPct = $('#overallPct');
const fileList = $('#fileList');
const logView = $('#logView');
const btnClearLog = $('#btnClearLog');

// Settings inputs
const inLufs = $('#lufsTarget');
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

let inputDir = '';
let outputDir = '';
let running = false;
let fileItems = new Map(); // id -> DOM refs

const SETTINGS_KEY = 'ban_settings_v1';

function loadSettings() {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return;
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
  } catch {}
}

function saveSettings() {
  const s = currentSettings();
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(s));
}

function currentSettings() {
  return {
    lufsTarget: Number(inLufs.value),
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
  };
}

function setRunning(state) {
  running = state;
  btnStart.disabled = running || !inputDir || !outputDir;
  btnCancel.disabled = !running;
  btnInput.disabled = running;
  btnOutput.disabled = running;
}

// Persist settings on change
;[inLufs, inTP, inLimiter, inConc, chkAutoTrim, inTrimPadMs, inTrimThresholdDb, inTrimMinDurMs, inTrimMinFileMs, chkTrimConservative, chkTrimHPF].forEach((el) => el.addEventListener('change', saveSettings));
loadSettings();

btnInput.addEventListener('click', async () => {
  const dir = await window.api.selectInputFolder(inputDir);
  if (dir) {
    inputDir = dir;
    inputPath.value = dir;
  }
  btnStart.disabled = running || !inputDir || !outputDir;
});

btnOutput.addEventListener('click', async () => {
  const dir = await window.api.selectOutputFolder(outputDir);
  if (dir) {
    outputDir = dir;
    outputPath.value = dir;
    const empty = await window.api.validateOutputEmpty(dir);
    outputValidation.textContent = empty ? 'Output folder is empty ✓' : 'Output folder must be empty.';
    outputValidation.style.color = empty ? '#2ea043' : '#d1242f';
    btnStart.disabled = running || !inputDir || !outputDir || !empty;
  }
});

btnStart.addEventListener('click', async () => {
  if (!inputDir || !outputDir) return;
  const empty = await window.api.validateOutputEmpty(outputDir);
  if (!empty) {
    outputValidation.textContent = 'Output folder must be empty.';
    outputValidation.style.color = '#d1242f';
    return;
  }

  fileList.innerHTML = '';
  overallBar.style.width = '0%';
  overallPct.textContent = '0%';
  fileItems.clear();
  logView.textContent = '';

  setRunning(true);
  const s = currentSettings();
  const res = await window.api.startProcessing({ inputDir, outputDir, settings: s, concurrency: s.concurrency });
  if (!res.ok) {
    alert(res.error || 'Failed to start processing');
    setRunning(false);
  }
});

btnCancel.addEventListener('click', async () => {
  await window.api.cancelProcessing();
  setRunning(false);
});

function ensureFileItem(id, name) {
  if (fileItems.has(id)) return fileItems.get(id);
  const el = document.createElement('div');
  el.className = 'file-item';
  el.innerHTML = `
    <div class="top">
      <div class="name" title="${name}">${name}</div>
      <div class="pct" data-role="pct">0%</div>
    </div>
    <div class="progress"><div class="bar" data-role="bar" style="width:0%"></div></div>
  `;
  fileList.appendChild(el);
  fileItems.set(id, el);
  return el;
}

window.api.onFileStart(({ fileId, name }) => {
  ensureFileItem(fileId, name);
});

window.api.onProgress(({ fileId, filePct, overallPct: oPct }) => {
  overallBar.style.width = `${oPct.toFixed(1)}%`;
  overallPct.textContent = `${oPct.toFixed(1)}%`;

  // Lazily create item on first progress signal if needed
  let itemEl = fileItems.get(fileId);
  if (!itemEl) itemEl = ensureFileItem(fileId, `File ${fileId}`);
  const pctEl = itemEl.querySelector('[data-role="pct"]');
  const barEl = itemEl.querySelector('[data-role="bar"]');
  pctEl.textContent = `${filePct.toFixed(1)}%`;
  barEl.style.width = `${filePct.toFixed(1)}%`;
});

window.api.onFileDone(({ fileId }) => {
  const itemEl = fileItems.get(fileId);
  if (itemEl) {
    itemEl.classList.add('done');
    const pctEl = itemEl.querySelector('[data-role="pct"]');
    const barEl = itemEl.querySelector('[data-role="bar"]');
    pctEl.textContent = '100%';
    barEl.style.width = '100%';
  }
});

window.api.onAllDone(() => {
  setRunning(false);
});

window.api.onError(({ message }) => {
  alert(message);
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
