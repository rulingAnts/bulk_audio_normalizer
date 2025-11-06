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
const chkVerbose = $('#verboseLogs');

let inputDir = '';
let outputDir = '';
let running = false;
let fileItems = new Map(); // id -> DOM refs
let autoScrollFiles = true;

// Auto-scroll file list to bottom unless the user scrolls up
fileList.addEventListener('scroll', () => {
  const nearBottom = fileList.scrollTop + fileList.clientHeight >= fileList.scrollHeight - 24;
  autoScrollFiles = nearBottom;
});
const phaseActive = { detect: 0, analyze: 0, render: 0 };

function updateBatchStatus() {
  if (phaseActive.render > 0) {
    batchStatus.textContent = 'Rendering…';
  } else if (phaseActive.analyze > 0) {
    batchStatus.textContent = 'Analyzing…';
  } else if (phaseActive.detect > 0) {
    batchStatus.textContent = 'Detecting…';
  } else if (running) {
    batchStatus.textContent = 'Queued…';
  } else {
    // idle
  }
}

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
    if (typeof s.verboseLogs === 'boolean') chkVerbose.checked = s.verboseLogs;
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
    verboseLogs: !!chkVerbose.checked,
  };
}

function setRunning(state) {
  running = state;
  btnStart.disabled = running || !inputDir || !outputDir;
  btnCancel.disabled = !running;
  btnInput.disabled = running;
  btnOutput.disabled = running;
  btnPreview.disabled = running || !inputDir; // can preview without output
}

// Persist settings on change
;[inLufs, inTP, inLimiter, inConc, chkAutoTrim, inTrimPadMs, inTrimThresholdDb, inTrimMinDurMs, inTrimMinFileMs, chkTrimConservative, chkTrimHPF, chkVerbose].forEach((el) => el.addEventListener('change', saveSettings));
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
  overallCount.textContent = '0/0';
  fileItems.clear();
  logView.textContent = '';
  // Clear any existing previews
  if (typeof previewList !== 'undefined') previewList.innerHTML = '';
  if (typeof previewInfo !== 'undefined') previewInfo.textContent = '';
  // Reset batch status
  phaseActive.detect = phaseActive.analyze = phaseActive.render = 0;
  batchStatus.textContent = 'Preparing…';

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
  batchStatus.textContent = 'Canceled';
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

window.api.onBatchStart(({ total }) => {
  if (Number.isFinite(total)) {
    overallCount.textContent = `0/${total}`;
  }
  if (running) batchStatus.textContent = 'Queued…';
});

window.api.onProgress(({ fileId, filePct, overallPct: oPct, completed, total }) => {
  overallBar.style.width = `${oPct.toFixed(1)}%`;
  overallPct.textContent = `${oPct.toFixed(1)}%`;
  if (Number.isFinite(completed) && Number.isFinite(total)) {
    overallCount.textContent = `${completed}/${total}`;
  }

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

// Preview handling
btnPreview.addEventListener('click', async () => {
  if (!inputDir) {
    alert('Select an input folder first.');
    return;
  }
  previewList.innerHTML = '';
  previewInfo.textContent = 'Running preview…';
  const s = currentSettings();
  const count = Math.max(1, Math.min(50, Number(previewCount.value || 5)));
  const res = await window.api.startPreview({ inputDir, settings: s, sampleSize: count, concurrency: Math.min(2, s.concurrency || 2) });
  if (!res.ok) {
    alert(res.error || 'Preview failed to start');
    previewInfo.textContent = '';
  } else {
    previewInfo.textContent = `Preview folder: ${res.tmpBase}`;
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
    ws.load('file://' + url);
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
