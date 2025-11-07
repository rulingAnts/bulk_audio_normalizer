'use strict';

// electron-builder afterPack hook.
// - Normalizes ffmpeg/ffprobe binaries per target platform into bin/{platform}/{arch}/
// - Prunes unused platform binaries.
// - For Windows target built on non-Windows host, can fetch a real Windows ffmpeg.exe if the bundled one is non-PE.

const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');
const os = require('os');

function isPEExecutable(filePath) {
  try {
    const fd = fs.openSync(filePath, 'r');
    const buf = Buffer.alloc(2);
    fs.readSync(fd, buf, 0, 2, 0);
    fs.closeSync(fd);
    return buf[0] === 0x4d && buf[1] === 0x5a; // 'MZ'
  } catch (e) {
    return false;
  }
}

// Removed network download logic; we now rely solely on a repo-local zip for Windows builds.

async function ensureWindowsFfmpegFromZip(projectDir, ffmpegStaticDir) {
  const zipPath = path.join(projectDir, 'build', 'win32-resources', 'ffmpeg-static.zip');
  if (!fs.existsSync(zipPath)) {
    console.warn('[afterPack] ffmpeg-static.zip not found at', zipPath);
    return false;
  }
  const winBinDir = path.join(ffmpegStaticDir, 'bin', 'win32', 'x64');
  try { fs.mkdirSync(winBinDir, { recursive: true }); } catch (e) {}
  const destExe = path.join(winBinDir, 'ffmpeg.exe');
  // If already valid, skip.
  if (fs.existsSync(destExe) && isPEExecutable(destExe)) {
    console.log('[afterPack] Existing ffmpeg.exe already valid (from previous step)');
    return true;
  }
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ban-ffmpeg-zip-'));
  const extractDir = path.join(tmpDir, 'extract');
  try { fs.mkdirSync(extractDir, { recursive: true }); } catch (e) {}
  const unzipCmd = process.platform === 'win32' ? 'powershell' : 'unzip';
  const unzipArgs = process.platform === 'win32'
    ? ['-Command', `Expand-Archive -Path '${zipPath}' -DestinationPath '${extractDir}' -Force`]
    : [zipPath, '-d', extractDir];
  await new Promise((resolve) => {
    try {
      const proc = spawn(unzipCmd, unzipArgs, { stdio: 'ignore' });
      proc.on('close', () => resolve());
      proc.on('error', () => resolve());
    } catch (e) { resolve(); }
  });
  let found = null;
  const walk = (p) => {
    let list = [];
    try { list = fs.readdirSync(p); } catch (e) { return; }
    for (const entry of list) {
      const full = path.join(p, entry);
      try {
        const st = fs.statSync(full);
        if (st.isDirectory()) walk(full); else if (/^ffmpeg\.exe$/i.test(entry)) { found = full; return; }
      } catch (e) {}
      if (found) return;
    }
  };
  walk(extractDir);
  if (!found) {
    console.warn('[afterPack] ffmpeg.exe not found inside ffmpeg-static.zip');
    return false;
  }
  try {
    fs.copyFileSync(found, destExe);
    if (!isPEExecutable(destExe)) {
      console.warn('[afterPack] Extracted ffmpeg.exe is not a valid PE');
      return false;
    }
    console.log('[afterPack] Extracted ffmpeg.exe from ffmpeg-static.zip into bin/win32/x64');
    return true;
  } catch (e) {
    console.warn('[afterPack] Failed copying ffmpeg.exe from zip:', e && e.message ? e.message : e);
    return false;
  }
}

function ensureWindowsFfmpegFallback(ffmpegStaticDir) {
  // Attempt to locate an existing PE ffmpeg* file in ffmpeg-static root.
  try {
    const entries = fs.existsSync(ffmpegStaticDir) ? fs.readdirSync(ffmpegStaticDir) : [];
    const winBinDir = path.join(ffmpegStaticDir, 'bin', 'win32', 'x64');
    try { fs.mkdirSync(winBinDir, { recursive: true }); } catch (e) {}
    const destExe = path.join(winBinDir, 'ffmpeg.exe');
    for (const name of entries) {
      if (!name.toLowerCase().startsWith('ffmpeg')) continue;
      const p = path.join(ffmpegStaticDir, name);
      try {
        if (fs.statSync(p).isFile() && isPEExecutable(p)) {
          fs.copyFileSync(p, destExe);
          console.log('[afterPack] Fallback copied existing PE ffmpeg into bin/win32/x64');
          return true;
        }
      } catch (e) {}
    }
  } catch (e) {}
  return false;
}

module.exports = async function afterPack(context) {
  try {
    const target = context.electronPlatformName; // 'win32' | 'darwin' | 'linux'
    const appOutDir = context.appOutDir; // e.g. dist/win-unpacked
    const unpackedRoot = path.join(appOutDir, 'resources', 'app.asar.unpacked', 'node_modules');

    if (target === 'darwin') {
      // Prune ffprobe to darwin only
      const ffprobeRoot = path.join(unpackedRoot, 'ffprobe-static', 'bin');
      if (fs.existsSync(ffprobeRoot)) {
        for (const sub of fs.readdirSync(ffprobeRoot)) {
          const full = path.join(ffprobeRoot, sub);
          try {
            if (fs.statSync(full).isDirectory() && sub !== 'darwin') {
              fs.rmSync(full, { recursive: true, force: true });
              console.log('[afterPack] (mac) Removed ffprobe non-darwin:', sub);
            }
          } catch (e) {}
        }
      }
      // Normalize ffmpeg layout to bin/darwin/universal/ffmpeg
      const ffmpegStaticDir = path.join(unpackedRoot, 'ffmpeg-static');
      if (fs.existsSync(ffmpegStaticDir)) {
        const binDir = path.join(ffmpegStaticDir, 'bin', 'darwin', 'universal');
        try {
          fs.mkdirSync(binDir, { recursive: true });
        } catch (e) {}
        let src = null;
        try {
          for (const name of fs.readdirSync(ffmpegStaticDir)) {
            if (!name.toLowerCase().startsWith('ffmpeg')) continue;
            const p = path.join(ffmpegStaticDir, name);
            try {
              if (fs.statSync(p).isFile()) {
                src = p;
                break;
              }
            } catch (e) {}
          }
        } catch (e) {}
        if (src) {
          try {
            fs.copyFileSync(src, path.join(binDir, 'ffmpeg'));
            console.log('[afterPack] (mac) Placed ffmpeg into bin/darwin/universal/ffmpeg');
          } catch (e) {
            console.warn('[afterPack] (mac) Failed to place ffmpeg into bin layout:', e && e.message ? e.message : e);
          }
        }
      }
      return;
    }

    if (target === 'win32') {
      // Ensure a valid Windows ffmpeg.exe exists and is in structured location
      const ffmpegStaticDir = path.join(unpackedRoot, 'ffmpeg-static');
      if (fs.existsSync(ffmpegStaticDir)) {
        const usedZip = await ensureWindowsFfmpegFromZip(context.packager.projectDir, ffmpegStaticDir);
        if (!usedZip) {
          ensureWindowsFfmpegFallback(ffmpegStaticDir);
        }
      } else {
        console.warn('[afterPack] ffmpeg-static directory not found at', ffmpegStaticDir);
      }

      // Prune ffprobe-static non-win32/x64 binaries
      const ffprobeRoot = path.join(unpackedRoot, 'ffprobe-static', 'bin');
      if (fs.existsSync(ffprobeRoot)) {
        for (const sub of fs.readdirSync(ffprobeRoot)) {
          const full = path.join(ffprobeRoot, sub);
          try {
            if (fs.statSync(full).isDirectory() && sub !== 'win32') {
              fs.rmSync(full, { recursive: true, force: true });
              console.log('[afterPack] Removed ffprobe non-win32:', sub);
            }
          } catch (e) {}
        }
        const winDir = path.join(ffprobeRoot, 'win32');
        if (fs.existsSync(winDir)) {
          for (const arch of fs.readdirSync(winDir)) {
            const archPath = path.join(winDir, arch);
            try {
              if (fs.statSync(archPath).isDirectory() && arch !== 'x64') {
                fs.rmSync(archPath, { recursive: true, force: true });
                console.log('[afterPack] Removed ffprobe win32 arch:', arch);
              }
            } catch (e) {}
          }
        }
      }
      return;
    }

    // Other targets: no-op for now
  } catch (err) {
    console.warn('[afterPack] hook error:', err);
  }
};
