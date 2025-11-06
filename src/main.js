import { app, BrowserWindow, dialog, ipcMain, shell } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';
import os from 'os';
import { spawn } from 'child_process';
import ffmpegStatic from 'ffmpeg-static';
import ffprobeStatic from 'ffprobe-static';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// App state
let mainWindow;
let activeJobs = new Map(); // key: fileId -> { procs: [ChildProcess], canceled: boolean }

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1100,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// Utilities
function selectDirectoryDialog(defaultPath) {
  return dialog.showOpenDialog(mainWindow, {
    title: 'Select folder',
    defaultPath: defaultPath || os.homedir(),
    properties: ['openDirectory'],
  });
}

function listWavFilesRecursive(dirPath) {
  const results = [];
  function walk(p) {
    const entries = fs.readdirSync(p, { withFileTypes: true });
    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue; // skip hidden
      const full = path.join(p, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (/\.(wav|wave)$/i.test(entry.name)) {
        results.push(full);
      }
    }
  }
  walk(dirPath);
  return results;
}

function isDirectoryEmpty(dirPath) {
  try {
    const items = fs.readdirSync(dirPath).filter((n) => !n.startsWith('.'));
    return items.length === 0;
  } catch (e) {
    return false;
  }
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function run(cmd, args, options = {}) {
  const child = spawn(cmd, args, { ...options });
  return child;
}

function parseFfmpegTimeToSeconds(t) {
  // t like HH:MM:SS.xx
  const [hh, mm, ss] = t.split(':');
  return parseInt(hh) * 3600 + parseInt(mm) * 60 + parseFloat(ss);
}

function getDurationSeconds(filePath) {
  return new Promise((resolve) => {
    const proc = run(ffprobeStatic.path, [
      '-v', 'error',
      '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1',
      filePath,
    ]);

    let buf = '';
    proc.stdout.on('data', (d) => (buf += d.toString()));
    proc.on('close', () => {
      const num = parseFloat(buf.trim());
      resolve(Number.isFinite(num) ? num : 0);
    });
  });
}

function buildTrimFilter(settings, durationSeconds) {
  if (!settings?.autoTrim) return null;
  const minFileMs = Math.max(0, Number(settings.trimMinFileMs ?? 800));
  if ((durationSeconds || 0) * 1000 < minFileMs) return null; // skip trimming very short files

  // Start with user-provided values
  let padMs = Math.max(0, Number(settings.trimPadMs ?? 500));
  let minDurMs = Math.max(10, Number(settings.trimMinDurationMs ?? 200));
  let thDb = Number(settings.trimThresholdDb ?? -50);
  const detect = (settings.trimDetect || 'rms') === 'peak' ? 'peak' : 'rms';
  const useHPF = !!settings.trimHPF;

  // Conservative mode raises safety margins for soft voices
  if (settings.trimConservative) {
    padMs = Math.max(padMs, 800);
    minDurMs = Math.max(minDurMs, 300);
    thDb = Math.min(thDb, -60); // lower threshold (more permissive to consider content as non-silence)
  }

  const padSec = padMs / 1000;
  const minDurSec = minDurMs / 1000;

  const trim = `silenceremove=start_periods=1:start_duration=${minDurSec}:start_threshold=${thDb}dB:stop_periods=1:stop_duration=${minDurSec}:stop_threshold=${thDb}dB:leave_silence=${padSec}:detection=${detect}`;
  if (useHPF) {
    // Remove low-frequency rumble that can confuse silence detection; 80 Hz is a common cutoff for speech
    return `highpass=f=80,${trim}`;
  }
  return trim;
}

async function loudnormTwoPassWithLimiter({ input, output, fileId, onProgress, settings }) {
  const targetI = Number(settings?.lufsTarget ?? -16);
  const targetTP = Number(settings?.tpMargin ?? -1.0);
  const limiter = Number(settings?.limiterLimit ?? 0.97);
  const trimFilter = buildTrimFilter(settings, Number(settings?.currentFileDurationSec || 0));
  // Pass 1: analyze loudness
  const pass1FilterParts = [];
  if (trimFilter) pass1FilterParts.push(trimFilter);
  pass1FilterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:print_format=json`);

  const pass1Args = [
    '-hide_banner',
    '-nostats',
    '-i', input,
    '-af', pass1FilterParts.join(','),
    '-f', 'null', '-'
  ];

  let analysisJson = '';
  await new Promise((resolve, reject) => {
    const p1 = run(ffmpegStatic, pass1Args);

    // Track for cancel
    const job = activeJobs.get(fileId);
    if (job) job.procs.push(p1);

    p1.stderr.on('data', (data) => {
      const s = data.toString();
      analysisJson += s;
      // stream logs
      try { mainWindow.webContents.send('log', { fileId, phase: 'analyze', line: s }); } catch {}
    });
    p1.on('error', reject);
    p1.on('close', (code) => {
      if (code !== 0 && !(activeJobs.get(fileId)?.canceled)) {
        return reject(new Error(`ffmpeg pass1 failed (${code})`));
      }
      resolve();
    });
  });

  // Extract JSON block
  const jsonMatch = analysisJson.match(/\{[\s\S]*?\}/g);
  let params;
  try {
    const parsed = jsonMatch ? JSON.parse(jsonMatch.slice(-1)[0]) : null;
    if (!parsed) throw new Error('No loudnorm analysis JSON found');
    params = {
      measured_I: parsed.input_i,
      measured_LRA: parsed.input_lra,
      measured_TP: parsed.input_tp,
      measured_thresh: parsed.input_thresh,
      offset: parsed.target_offset,
    };
  } catch (e) {
    // Fallback: single pass
    params = null;
  }

  // Pass 2: apply normalization + limiter and force 16-bit PCM
  const filterParts = [];
  if (trimFilter) filterParts.push(trimFilter);
  if (params) {
    filterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:measured_I=${params.measured_I}:measured_LRA=${params.measured_LRA}:measured_TP=${params.measured_TP}:measured_thresh=${params.measured_thresh}:offset=${params.offset}:linear=true:print_format=summary`);
  } else {
    filterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:print_format=summary`);
  }
  // Hard limiter slightly below 0 dBFS to guarantee no digital clipping
  filterParts.push(`alimiter=limit=${limiter}:level_in=1.0:level_out=1.0`);

  const pass2Args = [
    '-hide_banner',
    '-y',
    '-i', input,
    '-af', filterParts.join(','),
    '-acodec', 'pcm_s16le',
    '-map_metadata', '-1', // drop metadata to avoid surprises
    output,
  ];

  await new Promise((resolve, reject) => {
    const p2 = run(ffmpegStatic, pass2Args);

    const job = activeJobs.get(fileId);
    if (job) job.procs.push(p2);

    p2.stderr.on('data', (data) => {
      const s = data.toString();
      const m = s.match(/time=(\d{2}:\d{2}:\d{2}\.\d{2})/);
      if (m && onProgress) {
        onProgress(m[1]);
      }
      try { mainWindow.webContents.send('log', { fileId, phase: 'render', line: s }); } catch {}
    });

    p2.on('error', reject);
    p2.on('close', (code) => {
      if (code !== 0 && !(activeJobs.get(fileId)?.canceled)) {
        return reject(new Error(`ffmpeg pass2 failed (${code})`));
      }
      resolve();
    });
  });
}

function limitConcurrency(items, limit, worker) {
  return new Promise((resolve, reject) => {
    let i = 0;
    let inFlight = 0;
    let rejected = false;

    const results = new Array(items.length);

    const next = () => {
      if (rejected) return;
      while (inFlight < limit && i < items.length) {
        const idx = i++;
        inFlight++;
        worker(items[idx], idx)
          .then((res) => {
            results[idx] = res;
          })
          .catch((err) => {
            rejected = true;
            reject(err);
          })
          .finally(() => {
            inFlight--;
            if (i === items.length && inFlight === 0 && !rejected) {
              resolve(results);
            } else {
              next();
            }
          });
      }
    };

    next();
  });
}

function sampleRandom(items, count) {
  const n = Math.min(count, items.length);
  const arr = items.slice();
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, n);
}

// IPC handlers
ipcMain.handle('select-input-folder', async (evt, lastPath) => {
  const res = await selectDirectoryDialog(lastPath);
  return res.canceled ? null : res.filePaths[0];
});

ipcMain.handle('select-output-folder', async (evt, lastPath) => {
  const res = await selectDirectoryDialog(lastPath);
  return res.canceled ? null : res.filePaths[0];
});

ipcMain.handle('validate-output-empty', (evt, outDir) => {
  try {
    ensureDir(outDir);
    return isDirectoryEmpty(outDir);
  } catch (e) {
    return false;
  }
});

ipcMain.handle('start-processing', async (evt, { inputDir, outputDir, settings, concurrency = Math.max(1, Math.min(os.cpus().length - 1, 4)) }) => {
  // Discover files
  const files = listWavFilesRecursive(inputDir);
  const total = files.length;
  if (total === 0) {
    return { ok: false, error: 'No WAV files found in input folder.' };
  }

  // Clear state
  activeJobs.clear();

  // Prepare items with IDs
  const items = files.map((filePath, idx) => {
    const rel = path.relative(inputDir, filePath);
    const outPath = path.join(outputDir, rel).replace(/\.(wav|wave)$/i, '.wav');
    ensureDir(path.dirname(outPath));
    const id = `${Date.now()}_${idx}`;
    activeJobs.set(id, { procs: [], canceled: false });
    return { id, in: filePath, out: outPath };
  });

  // Track progress
  const perFileDuration = new Map();
  const perFileProgress = new Map(); // seconds processed

  // Pre-fetch durations in parallel (but not too many at once)
  await limitConcurrency(items, concurrency, async (item) => {
    const dur = await getDurationSeconds(item.in);
    perFileDuration.set(item.id, dur > 0 ? dur : 1);
  });

  let completed = 0;

  const notifyProgress = (fileId) => {
    const dur = perFileDuration.get(fileId) || 1;
    const cur = perFileProgress.get(fileId) || 0;
    const filePct = Math.max(0, Math.min(100, (cur / dur) * 100));

    // Compute overall by summing each file's fractional completion
    let sumFrac = 0;
    for (const [id, prog] of perFileProgress.entries()) {
      const d = perFileDuration.get(id) || 1;
      sumFrac += Math.max(0, Math.min(1, prog / d));
    }
    const overallPct = Math.max(0, Math.min(100, (sumFrac / total) * 100));

    mainWindow.webContents.send('progress-update', { fileId, filePct, overallPct });
  };

  try {
    await limitConcurrency(items, concurrency, async (item) => {
      // Notify renderer this file is starting
      const displayName = path.relative(inputDir, item.in);
      mainWindow.webContents.send('file-start', { fileId: item.id, name: displayName });
      const dur = perFileDuration.get(item.id) || 1;

      await loudnormTwoPassWithLimiter({
        input: item.in,
        output: item.out,
        fileId: item.id,
        settings: { ...settings, currentFileDurationSec: dur },
        onProgress: (timeStr) => {
          const sec = parseFloat(parseFfmpegTimeToSeconds(timeStr).toFixed(2));
          perFileProgress.set(item.id, Math.min(sec, dur));
          notifyProgress(item.id);
        },
      });

      completed += 1;
      perFileProgress.set(item.id, dur);
      notifyProgress(item.id);
      mainWindow.webContents.send('file-done', { fileId: item.id, out: item.out });
    });

    mainWindow.webContents.send('all-done', { total });
    return { ok: true, total };
  } catch (err) {
    mainWindow.webContents.send('error', { message: err.message });
    return { ok: false, error: err.message };
  } finally {
    activeJobs.clear();
  }
});

ipcMain.handle('cancel-processing', () => {
  for (const [, job] of activeJobs) {
    job.canceled = true;
    for (const p of job.procs) {
      try { p.kill('SIGKILL'); } catch {}
    }
  }
  activeJobs.clear();
  return true;
});

ipcMain.handle('reveal-path', (evt, filePath) => {
  try { shell.showItemInFolder(filePath); return true; } catch { return false; }
});

ipcMain.handle('start-preview', async (evt, { inputDir, sampleSize = 5, settings, concurrency = 2 }) => {
  const allFiles = listWavFilesRecursive(inputDir);
  if (allFiles.length === 0) {
    return { ok: false, error: 'No WAV files found for preview.' };
  }
  const files = sampleRandom(allFiles, sampleSize);

  const tmpBase = fs.mkdtempSync(path.join(os.tmpdir(), 'ban-preview-'));
  const items = files.map((filePath, idx) => {
    const rel = path.relative(inputDir, filePath);
    const outPath = path.join(tmpBase, rel).replace(/\.(wav|wave)$/i, '.wav');
    ensureDir(path.dirname(outPath));
    const id = `preview_${Date.now()}_${idx}`;
    activeJobs.set(id, { procs: [], canceled: false });
    return { id, in: filePath, out: outPath, rel };
  });

  // Pre-fetch durations to inform trimming safety
  const durations = new Map();
  await limitConcurrency(items, concurrency, async (item) => {
    const dur = await getDurationSeconds(item.in);
    durations.set(item.id, dur > 0 ? dur : 1);
  });

  try {
    await limitConcurrency(items, concurrency, async (item) => {
      const dur = durations.get(item.id) || 1;
      await loudnormTwoPassWithLimiter({
        input: item.in,
        output: item.out,
        fileId: item.id,
        settings: { ...settings, currentFileDurationSec: dur },
        onProgress: () => {},
      });
      mainWindow.webContents.send('preview-file-done', { id: item.id, original: item.in, preview: item.out, rel: item.rel, tmpBase });
    });
    mainWindow.webContents.send('preview-done', { count: items.length, tmpBase });
    return { ok: true, count: items.length, tmpBase };
  } catch (err) {
    mainWindow.webContents.send('error', { message: `Preview failed: ${err.message}` });
    return { ok: false, error: err.message };
  } finally {
    activeJobs.clear();
  }
});
