const $ = (sel) => document.querySelector(sel);
const previewList = $('#previewList');
const previewInfo = $('#previewInfo');
const btnRevealFolder = $('#btnRevealFolder');
let lastTmpBase = '';

btnRevealFolder.addEventListener('click', () => {
  if (lastTmpBase) window.api.revealPath(lastTmpBase);
});

function addCard({ original, preview, rel }) {
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
        WaveSurfer.regions.create({ dragSelection: true }),
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
      if (r) ws.play(r.start, r.end); else ws.play();
    });
    ws.on('region-in', (rgn) => { if (chkLoop.checked) rgn.playLoop(); });
    ws.on('region-update-end', (rgn) => {
      const all = Object.values(ws.regions.list || {});
      for (const other of all) { if (other.id !== rgn.id) other.remove(); }
    });
  };

  bindControls('o', wsO);
  bindControls('p', wsP);
}

window.api.onPreviewFileDone(({ original, preview, rel, tmpBase }) => {
  if (tmpBase) lastTmpBase = tmpBase;
  addCard({ original, preview, rel });
});

window.api.onPreviewDone(({ count, tmpBase }) => {
  if (tmpBase) lastTmpBase = tmpBase;
  previewInfo.textContent = `Preview complete: ${count} files${lastTmpBase ? ` → ${lastTmpBase}` : ''}`;
});
