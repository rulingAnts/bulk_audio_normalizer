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
let previewWindow;
let activeJobs = new Map(); // key: fileId -> { procs: [ChildProcess], canceled: boolean }
let cancelAll = false; // batch-level cancel flag for immediate stop

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

function createPreviewWindow() {
  if (previewWindow && !previewWindow.isDestroyed()) {
    previewWindow.focus();
    return previewWindow;
  }
  previewWindow = new BrowserWindow({
    width: 1000,
    height: 800,
    title: 'Preview',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  previewWindow.on('closed', () => { previewWindow = null; });
  previewWindow.loadFile(path.join(__dirname, 'renderer', 'preview.html'));
  return previewWindow;
}

function sendToPreview(channel, data) {
  try {
    if (previewWindow && !previewWindow.isDestroyed()) {
      previewWindow.webContents.send(channel, data);
      return true;
    }
  } catch {}
  try { mainWindow.webContents.send(channel, data); } catch {}
  return false;
}

// Utilities
function selectDirectoryDialog(defaultPath, allowCreate = false) {
  const props = ['openDirectory'];
  if (allowCreate) props.push('createDirectory');
  return dialog.showOpenDialog(mainWindow, {
    title: 'Select folder',
    defaultPath: defaultPath || os.homedir(),
    properties: props,
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

function ffVerbosityArgs(verbose) {
  // Keep periodic progress stats available even when not verbose (no -nostats),
  // otherwise we can't parse time=... for progress bars.
  return verbose ? ['-v', 'info'] : ['-hide_banner', '-v', 'error'];
}

function parseFfmpegTimeToSeconds(t) {
  // t like HH:MM:SS.xx
  const [hh, mm, ss] = t.split(':');
  return parseInt(hh) * 3600 + parseInt(mm) * 60 + parseFloat(ss);
}

function getDurationSeconds(filePath, fileId = null) {
  if (cancelAll) return Promise.resolve(1);
  // Fast path for WAV: parse header to avoid spawning ffprobe
  try {
    const fd = fs.openSync(filePath, 'r');
    try {
      const maxBytes = 512 * 1024; // read up to 512KB
      const buf = Buffer.allocUnsafe(maxBytes);
      const bytesRead = fs.readSync(fd, buf, 0, maxBytes, 0);
      const b = buf.subarray(0, bytesRead);
      if (b.length >= 44 && b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WAVE') {
        let pos = 12;
        let byteRate = 0;
        let dataSize = 0;
        while (pos + 8 <= b.length) {
          const id = b.toString('ascii', pos, pos + 4);
          const size = b.readUInt32LE(pos + 4);
          const next = pos + 8 + size + (size % 2); // chunks are word-aligned
          if (id === 'fmt ') {
            if (pos + 8 + 16 <= b.length) {
              // WAVEFORMAT structure
              // const audioFormat = b.readUInt16LE(pos + 8);
              // const channels = b.readUInt16LE(pos + 10);
              const sampleRate = b.readUInt32LE(pos + 12);
              byteRate = b.readUInt32LE(pos + 16);
              // const blockAlign = b.readUInt16LE(pos + 20);
              // const bitsPerSample = b.readUInt16LE(pos + 22);
              // If byteRate is zero but sampleRate is present, try to infer later
              if (!byteRate && sampleRate) {
                // fallback later using blockAlign if present (not implemented here)
              }
            }
          } else if (id === 'data') {
            dataSize = size;
            break;
          }
          pos = next;
        }
        if (byteRate > 0 && dataSize > 0) {
          const dur = dataSize / byteRate;
          if (Number.isFinite(dur) && dur > 0) return Promise.resolve(dur);
        }
      }
    } finally {
      try { fs.closeSync(fd); } catch {}
    }
  } catch {}

  // Fallback to ffprobe for non-WAV or edge cases
  return new Promise((resolve) => {
    const proc = run(ffprobeStatic.path, [
      '-v', 'error',
      '-show_entries', 'format=duration',
      '-of', 'default=noprint_wrappers=1:nokey=1',
      filePath,
    ]);
    if (fileId) {
      const job = activeJobs.get(fileId);
      if (job) job.procs.push(proc);
    }

    let buf = '';
    proc.stdout.on('data', (d) => (buf += d.toString()));
    proc.on('close', () => {
      const num = parseFloat(buf.trim());
      resolve(Number.isFinite(num) ? num : 0);
    });
    if (cancelAll) {
      try { proc.kill('SIGKILL'); } catch {}
    }
  });
}

// Read WAV header to get bit depth and audio format quickly
function getWavFormatInfo(filePath) {
  try {
    const fd = fs.openSync(filePath, 'r');
    try {
      const buf = Buffer.allocUnsafe(128);
      const bytes = fs.readSync(fd, buf, 0, 128, 0);
      const b = buf.subarray(0, bytes);
      if (b.length >= 44 && b.toString('ascii', 0, 4) === 'RIFF' && b.toString('ascii', 8, 12) === 'WAVE') {
        let pos = 12;
        while (pos + 8 <= b.length) {
          const id = b.toString('ascii', pos, pos + 4);
          const size = b.readUInt32LE(pos + 4);
          const next = pos + 8 + size + (size % 2);
          if (id === 'fmt ') {
            const audioFormat = b.readUInt16LE(pos + 8); // 1=PCM, 3=float
            const bitsPerSample = b.readUInt16LE(pos + 22);
            return { audioFormat, bitsPerSample };
          }
          pos = next;
        }
      }
    } finally { try { fs.closeSync(fd); } catch {} }
  } catch {}
  return null;
}

function chooseOutputCodec({ targetBitDepth = 16, inputFmt }) {
  // Preserve original bit depth when 'original' is selected
  if (targetBitDepth === 'original') {
    const bits = inputFmt?.bitsPerSample || 0;
    const fmt = inputFmt?.audioFormat || 1; // 1=PCM int, 3=float
    if (fmt === 3) {
      // Float WAV
      if (bits >= 64) return 'pcm_f64le';
      return 'pcm_f32le';
    }
    if (bits <= 8) return 'pcm_u8';
    if (bits <= 16) return 'pcm_s16le';
    if (bits <= 24) return 'pcm_s24le';
    if (bits <= 32) return 'pcm_s32le';
    return 'pcm_s16le';
  }

  const tgt = Number(targetBitDepth) === 24 ? 24 : 16;
  if (tgt === 16) return 'pcm_s16le';
  // tgt === 24: do not up-convert 16-bit
  const bits = inputFmt?.bitsPerSample || 0;
  if (bits > 0 && bits <= 16) return 'pcm_s16le';
  // Limit higher bit depths (and float) to 24-bit
  return 'pcm_s24le';
}

// Fast WAV edge scan: find first/last non-silent regions by peak threshold with a required sustain duration.
// Supports PCM (format 1) and IEEE float (format 3). Falls back by throwing if unsupported or too large.
async function fastScanWavEdges({ input, durationSec, settings, fileId }) {
  const MAX_BYTES = 50 * 1024 * 1024; // 50MB safety
  const buf = fs.readFileSync(input);
  if (buf.length < 44) throw new Error('file too small');
  if (buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') throw new Error('not a WAV');
  if (buf.length > MAX_BYTES) throw new Error('file too large for fast scan');

  // Parse chunks
  let pos = 12;
  let fmt = null;
  let dataOff = -1;
  let dataSize = 0;
  while (pos + 8 <= buf.length) {
    const id = buf.toString('ascii', pos, pos + 4);
    const size = buf.readUInt32LE(pos + 4);
    const next = pos + 8 + size + (size % 2);
    if (id === 'fmt ') {
      fmt = {
        audioFormat: buf.readUInt16LE(pos + 8),
        numChannels: buf.readUInt16LE(pos + 10),
        sampleRate: buf.readUInt32LE(pos + 12),
        byteRate: buf.readUInt32LE(pos + 16),
        blockAlign: buf.readUInt16LE(pos + 20),
        bitsPerSample: buf.readUInt16LE(pos + 22),
      };
    } else if (id === 'data') {
      dataOff = pos + 8;
      dataSize = size;
      break;
    }
    pos = next;
  }
  if (!fmt || dataOff < 0 || dataSize <= 0) throw new Error('bad WAV structure');
  const { audioFormat, numChannels, sampleRate, bitsPerSample, blockAlign } = fmt;
  const bytesPerSample = Math.floor(blockAlign / Math.max(1, numChannels));
  const isFloat = audioFormat === 3; // IEEE float
  const data = buf.subarray(dataOff, dataOff + dataSize);
  const totalFrames = Math.floor(data.length / blockAlign);
  if (totalFrames <= 0) throw new Error('no audio frames');

  // Threshold
  const thDb = Number(settings.trimThresholdDb ?? -50);
  const lin = Math.pow(10, thDb / 20);
  const reqSustainMs = Math.max(1, Number(settings.trimMinDurationMs ?? 200));
  const reqFrames = Math.ceil((reqSustainMs / 1000) * sampleRate);

  const getPeak = (frameIndex) => {
    const off = frameIndex * blockAlign;
    let peak = 0;
    for (let ch = 0; ch < numChannels; ch++) {
      const sOff = off + ch * bytesPerSample;
      let v = 0;
      if (isFloat && bytesPerSample >= 4) {
        v = Math.abs(buf.readFloatLE(dataOff + sOff));
      } else {
        // signed integer
        if (bytesPerSample === 2) v = Math.abs(buf.readInt16LE(dataOff + sOff)) / 32768;
        else if (bytesPerSample === 3) {
          // 24-bit signed
          let x = buf.readIntLE(dataOff + sOff, 3);
          const max = 8388608; // 2^23
          v = Math.abs(x) / max;
        } else if (bytesPerSample === 4) v = Math.abs(buf.readInt32LE(dataOff + sOff)) / 2147483648;
        else v = 0;
      }
      if (v > peak) peak = v;
    }
    return peak;
  };

  // Scan from start: require sustained above-threshold run
  let startFrame = 0;
  let run = 0;
  let runStart = 0;
  for (let i = 0; i < totalFrames; i++) {
    const pk = getPeak(i);
    if (pk >= lin) {
      if (run === 0) runStart = i;
      run++;
      if (run >= reqFrames) { startFrame = runStart; break; }
    } else {
      run = 0;
    }
  }

  // Scan from end
  let endFrame = totalFrames;
  run = 0;
  let runEnd = totalFrames;
  for (let i = totalFrames - 1; i >= 0; i--) {
    const pk = getPeak(i);
    if (pk >= lin) {
      if (run === 0) runEnd = i + 1;
      run++;
      if (run >= reqFrames) { endFrame = runEnd; break; }
    } else {
      run = 0;
    }
  }

  const startSec = startFrame / sampleRate;
  const endSec = endFrame / sampleRate;
  if (endSec <= startSec) return null;

  try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: `Fast trim (edge scan): start=${startSec.toFixed(3)}s end=${endSec.toFixed(3)}s` }); } catch {}
  return { start: startSec, end: endSec };
}

function buildTrimFilter(settings, durationSeconds) {
  if (!settings?.autoTrim) return null;
  const minFileMs = Math.max(0, Number(settings.trimMinFileMs ?? 800));
  if ((durationSeconds || 0) * 1000 < minFileMs) return null; // skip trimming very short files

  // Start with user-provided values
  let padMs = Math.max(0, Number(settings.trimPadMs ?? 800));
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

async function detectVoiceRegion({ input, durationSec, settings, fileId }) {
  // Build silencedetect filter (optional HPF first for robustness)
  const thDb = Number(settings.trimThresholdDb ?? -50);
  const minDurSec = Math.max(0.01, Number(settings.trimMinDurationMs ?? 200) / 1000);
  const conservative = !!settings.trimConservative;
  const hpf = !!settings.trimHPF;
  const n = conservative ? Math.min(thDb, -60) : thDb;
  const d = conservative ? Math.max(minDurSec, 0.3) : minDurSec;
  const filters = [];
  if (hpf) filters.push('highpass=f=80');
  filters.push(`silencedetect=n=${n}dB:d=${d}`);

  try {
    mainWindow.webContents.send('log', {
      fileId,
      phase: 'trim',
      line: `Detect config: threshold=${n}dB, minDur=${d}s, HPF=${hpf ? 'on' : 'off'}, conservative=${conservative ? 'on' : 'off'}`,
    });
  } catch {}

  if (cancelAll) return null;
  return await new Promise((resolve) => {
    // Force info verbosity for silencedetect so it emits silence_start/end lines
    const args = [
      '-hide_banner', '-nostats', '-v', 'info',
      '-i', input,
      '-af', filters.join(','),
      '-f', 'null', '-'
    ];
    const p = run(ffmpegStatic, args);
    const job = activeJobs.get(fileId);
    if (job) job.procs.push(p);
    let stderr = '';
    p.stderr.on('data', (data) => {
      const s = data.toString();
      stderr += s;
      try { mainWindow.webContents.send('log', { fileId, phase: 'detect', line: s }); } catch {}
    });
    p.on('close', () => {
      const reStart = /silence_start: ([0-9]+\.?[0-9]*)/g;
      const reEnd = /silence_end: ([0-9]+\.?[0-9]*)/g;
      const silence = [];
      let curStart = null;
      let m;
      while ((m = reStart.exec(stderr)) !== null) {
        curStart = parseFloat(m[1]);
        // try to find the next end from current index
        const endMatch = reEnd.exec(stderr);
        if (endMatch) {
          const e = parseFloat(endMatch[1]);
          const sVal = curStart ?? 0;
          silence.push([Math.max(0, sVal), Math.min(durationSec, e)]);
          curStart = null;
        } else {
          // will close at end with duration
          break;
        }
      }
      if (curStart != null) {
        silence.push([Math.max(0, curStart), Math.max(curStart, durationSec)]);
      }

      // Normalize and merge overlaps
      silence.sort((a, b) => a[0] - b[0]);
      const merged = [];
      for (const seg of silence) {
        if (!merged.length || seg[0] > merged[merged.length - 1][1]) {
          merged.push(seg.slice());
        } else {
          merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], seg[1]);
        }
      }

      // Complement to get non-silent intervals
      const nonSilent = [];
      let prev = 0;
      for (const [s, e] of merged) {
        if (s > prev) nonSilent.push([prev, s]);
        prev = Math.max(prev, e);
      }
      if (prev < durationSec) nonSilent.push([prev, durationSec]);

      if (nonSilent.length === 0) {
        resolve(null);
        return;
      }
      const start = nonSilent[0][0];
      const end = nonSilent[nonSilent.length - 1][1];
      resolve({ start, end });
    });
    if (cancelAll) {
      try { p.kill('SIGKILL'); } catch {}
    }
  });
}

async function loudnormTwoPassWithLimiter({ input, output, fileId, onProgress, settings }) {
  const inputFmt = getWavFormatInfo(input);
  const outCodec = chooseOutputCodec({ targetBitDepth: settings?.targetBitDepth ?? 16, inputFmt });
  const targetI = Number(settings?.lufsTarget ?? -16);
  const targetTP = Number(settings?.tpMargin ?? -1.0);
  const limiter = Number(settings?.limiterLimit ?? 0.97);
  const normMode = (settings?.normMode === 'lufs') ? 'lufs' : 'peak';
  const peakTargetDb = Number(settings?.peakTargetDb ?? -9);
  const durationSec = Number(settings?.currentFileDurationSec || 0) || 0;
  const threads = Number(settings?.ffmpegThreads || 0);
  const fastNormalize = !!settings?.fastNormalize;

  let trimFilter = null;
  let seekStart = 0;
  let seekEnd = durationSec;
  try { mainWindow.webContents.send('phase-event', { fileId, phase: 'detect', status: 'start' }); } catch {}
  if (settings?.autoTrim) {
    const minFileMs = Math.max(0, Number(settings.trimMinFileMs ?? 800));
    if (durationSec * 1000 >= minFileMs) {
      let region = null;
      if (settings.fastTrim) {
        try {
          region = await fastScanWavEdges({ input, durationSec, settings, fileId });
        } catch (e) {
          try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: `Fast trim scan failed, falling back to FFmpeg detect: ${e.message}` }); } catch {}
        }
      }
      if (!region) {
        if (!cancelAll) {
          region = await detectVoiceRegion({ input, durationSec, settings, fileId });
        }
      }
      if (region) {
  const padSec = Math.max(0, Number(settings.trimPadMs ?? 800) / 1000);
        const start = Math.max(0, region.start - padSec);
        const end = Math.min(durationSec, region.end + padSec);
        if (end > start) {
          // Prefer input seeking over atrim to avoid decoding unused audio
          seekStart = start;
          seekEnd = end;
          trimFilter = null; // we will not use atrim when we can seek at demux stage
          const kept = (end - start).toFixed(3);
          const padInfo = (padSec * 1000).toFixed(0);
          try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: `Trim applied: start=${start.toFixed(3)}s end=${end.toFixed(3)}s (kept ${kept}s of ${durationSec.toFixed(3)}s, pad=${padInfo}ms)` }); } catch {}
        } else {
          try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: `No trimming applied: computed end <= start after padding (start=${start.toFixed(3)}s end=${end.toFixed(3)}s)` }); } catch {}
        }
      } else {
        try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: 'No trimming applied: could not detect a non-silent region.' }); } catch {}
      }
    } else {
      try { mainWindow.webContents.send('log', { fileId, phase: 'trim', line: `No trimming applied: file shorter than minimum ${minFileMs}ms.` }); } catch {}
    }
  }
  try { mainWindow.webContents.send('phase-event', { fileId, phase: 'detect', status: 'done' }); } catch {}
  // Pass 1: analyze
  const seekArgs = (seekStart > 0 || seekEnd < durationSec)
    ? ['-ss', seekStart.toFixed(3), '-to', seekEnd.toFixed(3)]
    : [];
  let params = null;
  let measuredMaxVolume = null;
  if (normMode === 'lufs' && !fastNormalize) {
    try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'start' }); } catch {}
    const pass1FilterParts = [];
    if (trimFilter) pass1FilterParts.push(trimFilter);
    pass1FilterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:print_format=json`);

    const pass1Args = [
      ...ffVerbosityArgs(settings?.verboseLogs),
      ...seekArgs,
      '-i', input,
      ...(threads > 0 ? ['-threads', String(threads)] : []),
      '-af', pass1FilterParts.join(','),
      '-f', 'null', '-'
    ];

    let analysisJson = '';
    await new Promise((resolve, reject) => {
      const p1 = run(ffmpegStatic, pass1Args);

      const job = activeJobs.get(fileId);
      if (job) job.procs.push(p1);

      p1.stderr.on('data', (data) => {
        const s = data.toString();
        analysisJson += s;
        try { mainWindow.webContents.send('log', { fileId, phase: 'analyze', line: s }); } catch {}
        const m = s.match(/time=(\d{2}:\d{2}:\d{2}\.\d{2})/);
        if (m && Number.isFinite(durationSec) && durationSec > 0) {
          const sec = parseFloat(parseFfmpegTimeToSeconds(m[1]).toFixed(2));
          const pct = Math.max(0, Math.min(100, (sec / durationSec) * 100));
          try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'progress', pct }); } catch {}
        }
      });
      p1.on('error', reject);
      p1.on('close', (code) => {
        if (code !== 0 && !(activeJobs.get(fileId)?.canceled)) {
          return reject(new Error(`ffmpeg pass1 failed (${code})`));
        }
        try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'done', pct: 100 }); } catch {}
        resolve();
      });
    });

    const jsonMatch = analysisJson.match(/\{[\s\S]*?\}/g);
    try {
      const parsed = jsonMatch ? JSON.parse(jsonMatch.slice(-1)[0]) : null;
      if (parsed) {
        params = {
          measured_I: parsed.input_i,
          measured_LRA: parsed.input_lra,
          measured_TP: parsed.input_tp,
          measured_thresh: parsed.input_thresh,
          offset: parsed.target_offset,
        };
      }
    } catch {}
  } else if (normMode === 'peak') {
    try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'start' }); } catch {}
    const pass1FilterParts = [];
    if (trimFilter) pass1FilterParts.push(trimFilter);
    pass1FilterParts.push('volumedetect');

    const pass1Args = [
      // Force info level so volumedetect prints its summary
      '-hide_banner', '-v', 'info',
      ...seekArgs,
      '-i', input,
      ...(threads > 0 ? ['-threads', String(threads)] : []),
      '-af', pass1FilterParts.join(','),
      '-f', 'null', '-'
    ];

    await new Promise((resolve, reject) => {
      const p1 = run(ffmpegStatic, pass1Args);

      const job = activeJobs.get(fileId);
      if (job) job.procs.push(p1);

      let lastMax = null;
      p1.stderr.on('data', (data) => {
        const s = data.toString();
        try { mainWindow.webContents.send('log', { fileId, phase: 'analyze', line: s }); } catch {}
        const m = s.match(/max_volume:\s*(-?\d+\.?\d*) dB/);
        if (m) lastMax = parseFloat(m[1]);
        const t = s.match(/time=(\d{2}:\d{2}:\d{2}\.\d{2})/);
        if (t && Number.isFinite(durationSec) && durationSec > 0) {
          const sec = parseFloat(parseFfmpegTimeToSeconds(t[1]).toFixed(2));
          const pct = Math.max(0, Math.min(100, (sec / durationSec) * 100));
          try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'progress', pct }); } catch {}
        }
      });
      p1.on('error', reject);
      p1.on('close', (code) => {
        if (code !== 0 && !(activeJobs.get(fileId)?.canceled)) {
          return reject(new Error(`ffmpeg peak analysis failed (${code})`));
        }
        measuredMaxVolume = (typeof lastMax === 'number') ? lastMax : null;
        try { mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'done', pct: 100 }); } catch {}
        resolve();
      });
    });
  } else {
    // Keep UI consistent: mark analyze as instant-done in fast mode
    try {
      mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'start' });
      mainWindow.webContents.send('phase-event', { fileId, phase: 'analyze', status: 'done', pct: 100 });
    } catch {}
  }

  // Pass 2: apply normalization + limiter and force 16-bit PCM
  try { mainWindow.webContents.send('phase-event', { fileId, phase: 'render', status: 'start' }); } catch {}
  const filterParts = [];
  if (trimFilter) filterParts.push(trimFilter);
  if (normMode === 'lufs') {
    if (params) {
      filterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:measured_I=${params.measured_I}:measured_LRA=${params.measured_LRA}:measured_TP=${params.measured_TP}:measured_thresh=${params.measured_thresh}:offset=${params.offset}:linear=true:print_format=summary`);
    } else {
      filterParts.push(`loudnorm=I=${targetI}:TP=${targetTP}:LRA=11:print_format=summary`);
    }
    // Hard limiter slightly below 0 dBFS to guarantee no digital clipping
    filterParts.push(`alimiter=limit=${limiter}:level_in=1.0:level_out=1.0`);
  } else {
    // Peak mode: compute gain to hit target peak while staying below 0 dBFS
    let gainDb = 0;
    if (typeof measuredMaxVolume === 'number' && Number.isFinite(measuredMaxVolume)) {
      const ideal = peakTargetDb - measuredMaxVolume; // e.g., -9 - (-18) = +9 dB; -9 - (-6) = -3 dB
      const onlyBoost = settings?.peakOnlyBoost !== false; // default true
      gainDb = onlyBoost ? Math.max(0, ideal) : ideal;
    }
    if (!Number.isFinite(gainDb)) gainDb = 0;
    gainDb = Math.max(-30, Math.min(30, gainDb));
    try {
      const msg = `Peak mode: measuredMax=${measuredMaxVolume ?? 'n/a'} dB, target=${peakTargetDb} dB, gain=${gainDb.toFixed(2)} dB, onlyBoost=${settings?.peakOnlyBoost !== false}`;
      mainWindow.webContents.send('log', { fileId, phase: 'analyze', line: msg });
    } catch {}
    filterParts.push(`volume=${gainDb.toFixed(2)}dB`);
  }

  const pass2Args = [
    ...ffVerbosityArgs(settings?.verboseLogs),
    ...seekArgs,
    '-y',
    '-i', input,
    ...(threads > 0 ? ['-threads', String(threads)] : []),
    '-af', filterParts.join(','),
    '-acodec', outCodec,
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
      if (m && Number.isFinite(durationSec) && durationSec > 0) {
        const sec = parseFloat(parseFfmpegTimeToSeconds(m[1]).toFixed(2));
        const pct = Math.max(0, Math.min(100, (sec / durationSec) * 100));
        try { mainWindow.webContents.send('phase-event', { fileId, phase: 'render', status: 'progress', pct }); } catch {}
      }
      try { mainWindow.webContents.send('log', { fileId, phase: 'render', line: s }); } catch {}
    });

    p2.on('error', reject);
    p2.on('close', (code) => {
      if (code !== 0 && !(activeJobs.get(fileId)?.canceled)) {
        return reject(new Error(`ffmpeg pass2 failed (${code})`));
      }
      try { mainWindow.webContents.send('phase-event', { fileId, phase: 'render', status: 'done', pct: 100 }); } catch {}
      resolve();
    });
    if (cancelAll) {
      try { p2.kill('SIGKILL'); } catch {}
    }
  });
}

function limitConcurrency(items, limitOrFn, worker) {
  return new Promise((resolve, reject) => {
    let i = 0;
    let inFlight = 0;
    let rejected = false;

    const results = new Array(items.length);
    const limitFn = (typeof limitOrFn === 'function') ? limitOrFn : (() => limitOrFn);

    const next = () => {
      if (rejected) return;
      while (inFlight < Math.max(1, Number(limitFn())) && i < items.length) {
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
  const res = await selectDirectoryDialog(lastPath, false);
  return res.canceled ? null : res.filePaths[0];
});

ipcMain.handle('select-output-folder', async (evt, lastPath) => {
  const res = await selectDirectoryDialog(lastPath, true);
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
  cancelAll = false; // reset batch cancel state
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

  // Notify renderer about batch start so it can show 0/N immediately
  try { mainWindow.webContents.send('batch-start', { total }); } catch {}
  try { mainWindow.webContents.send('log', { fileId: 'batch', phase: 'info', line: `Discovered ${total} WAV file(s).` }); } catch {}

  // Pre-fetch durations in parallel (but not too many at once)
  await limitConcurrency(items, Math.min(concurrency, 4), async (item) => {
    if (cancelAll) return; // skip work when canceled
    const dur = await getDurationSeconds(item.in, item.id);
    perFileDuration.set(item.id, dur > 0 ? dur : 1);
  });
  try { mainWindow.webContents.send('log', { fileId: 'batch', phase: 'info', line: `Got durations for all files. Starting processing with concurrency=${concurrency}.` }); } catch {}

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

    mainWindow.webContents.send('progress-update', { fileId, filePct, overallPct, completed, total });
  };

  // Adaptive throttling based on system load and memory
  const cores = Math.max(1, os.cpus().length || 1);
  let allowed = Math.max(1, concurrency);
  const base = allowed;
  let lastAnnounce = '';
  const monitor = setInterval(() => {
    try {
      const [l1] = os.loadavg();
      const loadNorm = (l1 || 0) / cores; // ~1.0 means fully loaded
      const freeMem = os.freemem();
      const totalMem = os.totalmem();
      const freePct = totalMem > 0 ? freeMem / totalMem : 1;
      let changed = false;
      let reason = '';
      // Reduce quickly if overloaded
      if ((loadNorm > 0.9 || freePct < 0.10) && allowed > 1) {
        allowed = Math.max(1, allowed - 1);
        changed = true;
        reason = loadNorm > 0.9 ? 'high CPU load' : 'low memory';
      } else if ((loadNorm < 0.6 && freePct > 0.20) && allowed < base) {
        // Recover slowly when system is comfortable
        allowed = Math.min(base, allowed + 1);
        changed = true;
        reason = 'resources recovered';
      }
      if (changed) {
        const msg = `allowed=${allowed}, base=${base}, load=${(loadNorm*100).toFixed(0)}%, freeMem=${(freePct*100).toFixed(0)}% (${reason})`;
        if (msg !== lastAnnounce) {
          lastAnnounce = msg;
          try { mainWindow.webContents.send('throttle-event', { allowed, base, loadPct: loadNorm*100, freeMemPct: freePct*100, reason }); } catch {}
          try { mainWindow.webContents.send('log', { fileId: 'batch', phase: 'throttle', line: `Adaptive throttling: ${msg}` }); } catch {}
        }
      }
    } catch {}
  }, 1500);

  try {
    await limitConcurrency(items, () => allowed, async (item) => {
      if (cancelAll) return; // do not start new items after cancel
      // Notify renderer this file is starting
  const displayName = path.relative(inputDir, item.in);
      mainWindow.webContents.send('file-start', { fileId: item.id, name: displayName });
  try { mainWindow.webContents.send('log', { fileId: item.id, phase: 'start', line: `Processing ${displayName}` }); } catch {}
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

    if (!cancelAll) {
      mainWindow.webContents.send('all-done', { total });
    }
    return { ok: true, total };
  } catch (err) {
    mainWindow.webContents.send('error', { message: err.message });
    return { ok: false, error: err.message };
  } finally {
    activeJobs.clear();
    try { clearInterval(monitor); } catch {}
  }
});

ipcMain.handle('cancel-processing', () => {
  cancelAll = true;
  for (const [, job] of activeJobs) {
    job.canceled = true;
    for (const p of job.procs) {
      try { p.kill('SIGKILL'); } catch {}
    }
  }
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
  // Clamp preview size to a sane, responsive limit
  const size = Math.max(1, Math.min(50, Number(sampleSize || 5)));
  const files = sampleRandom(allFiles, size);

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
    if (cancelAll) return;
    const dur = await getDurationSeconds(item.in, item.id);
    durations.set(item.id, dur > 0 ? dur : 1);
  });

  try {
    await limitConcurrency(items, concurrency, async (item) => {
      if (cancelAll) return;
      const dur = durations.get(item.id) || 1;
      await loudnormTwoPassWithLimiter({
        input: item.in,
        output: item.out,
        fileId: item.id,
        settings: { ...settings, currentFileDurationSec: dur },
        onProgress: () => {},
      });
      sendToPreview('preview-file-done', { id: item.id, original: item.in, preview: item.out, rel: item.rel, tmpBase });
    });
    if (!cancelAll) sendToPreview('preview-done', { count: items.length, tmpBase });
    return { ok: true, count: items.length, tmpBase };
  } catch (err) {
    sendToPreview('error', { message: `Preview failed: ${err.message}` });
    return { ok: false, error: err.message };
  } finally {
    activeJobs.clear();
  }
});

ipcMain.handle('open-preview-window', async () => {
  createPreviewWindow();
  return true;
});
