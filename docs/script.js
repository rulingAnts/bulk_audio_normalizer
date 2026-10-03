// The newest releases (pre-releases included), fetched once and shared by both blocks
// below. It rejects when the GitHub API cannot be reached; each block handles that itself.
const releaseList = fetch('https://api.github.com/repos/rulingAnts/bulk_audio_normalizer/releases?per_page=10',
  { headers: { 'Accept': 'application/vnd.github+json' } })
  .then(res => { if (!res.ok) throw new Error('HTTP ' + res.status); return res.json(); })
  .then(list => { if (!Array.isArray(list)) throw new Error('unexpected response'); return list; });
releaseList.catch(() => {});

// Wire up latest release asset links using the GitHub API
(function() {
  const owner = 'rulingAnts';
  const repo = 'bulk_audio_normalizer';
  const latest = `https://github.com/${owner}/${repo}/releases/latest`;
  const relApi = `https://api.github.com/repos/${owner}/${repo}/releases/latest`;

  function enable(link, href) {
    if (!link) return;
    link.href = href;
    link.classList.remove('disabled');
    link.removeAttribute('aria-disabled');
  }

  function fallbackAll() {
    const mac = document.getElementById('download-mac');
    const win = document.getElementById('download-win');
    const rel = document.getElementById('release-page-link');
    const rel2 = document.getElementById('release-page-link-footer');
    // enable() also lifts the "disabled" look, which otherwise blocks clicks
    enable(mac, `https://github.com/${owner}/${repo}/releases`);
    enable(win, latest);
    if (rel) rel.href = latest;
    if (rel2) rel2.href = latest;
  }

  async function init() {
    try {
      const res = await fetch(relApi, { headers: { 'Accept': 'application/vnd.github+json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const release = await res.json();
      const assets = Array.isArray(release.assets) ? release.assets : [];
      const macAsset = assets.find(a => a && a.browser_download_url && /\.dmg$/i.test(a.browser_download_url));
      const winAsset = assets.find(a => a && a.browser_download_url && /\.exe$/i.test(a.browser_download_url));
      const macLink = document.getElementById('download-mac');
      const winLink = document.getElementById('download-win');
      const rel = document.getElementById('release-page-link');
      const rel2 = document.getElementById('release-page-link-footer');

      // Display tag name in buttons if available
      const tag = release.tag_name || release.name || '';
      if (tag) {
        if (macLink) macLink.textContent = `Download macOS (${tag})`;
        if (winLink) winLink.textContent = `Download Windows (${tag})`;
      }

  if (macAsset) enable(macLink, macAsset.browser_download_url);
  if (winAsset) enable(winLink, winAsset.browser_download_url);
      if (release.html_url) {
        if (rel) rel.href = release.html_url;
        if (rel2) rel2.href = release.html_url;
      }

      // No .dmg on the latest full release: the macOS downloads of v2.0.1 and older were
      // withdrawn (their FFmpeg could not be passed on). Offer the newest release that has
      // one instead, pre-releases included, and say when it is a pre-release.
      let macFound = !!macAsset;
      if (!macAsset && macLink) {
        try {
          const time = (r) => Date.parse(r.published_at || r.created_at || '') || 0;
          const dmgOf = (r) => (Array.isArray(r.assets) ? r.assets : [])
            .find(a => a && a.browser_download_url && /\.dmg$/i.test(a.browser_download_url));
          const withDmg = (await releaseList)
            .filter(r => r && !r.draft && dmgOf(r))
            .sort((a, b) => time(b) - time(a))[0];
          if (withDmg) {
            enable(macLink, dmgOf(withDmg).browser_download_url);
            const name = withDmg.tag_name || withDmg.name || '';
            macLink.textContent = withDmg.prerelease
              ? `Download macOS (${name} pre-release)` : `Download macOS (${name})`;
            if (withDmg.prerelease) macLink.title = 'A pre-release: it still needs testing';
            macFound = true;
          }
        } catch (e) { /* fall through to the releases page */ }
      }

  if (!macFound && macLink) macLink.title = 'No direct DMG asset found; click to view the releases';
  if (!winAsset && winLink) winLink.title = 'No direct EXE asset found; click to view latest releases';

      // Ensure we still have a working path: a button with no asset goes to a releases page
      // (href is "#" in index.html until a download is found).
      if (!macFound && macLink) enable(macLink, `https://github.com/${owner}/${repo}/releases`);
      if (!winAsset && winLink) enable(winLink, latest);
    } catch (e) {
      fallbackAll();
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

// Pre-release notice. The main buttons above always use releases/latest, which never
// returns a pre-release. This only updates the notice under them: it points at the newest
// published pre-release that is newer than the latest full release, and hides the notice
// when there is none (e.g. once that pre-release has been promoted), so the site never
// advertises a stale pre-release. If the API cannot be reached, the notice stays as
// written in index.html.
(function() {
  const time = (r) => Date.parse(r.published_at || r.created_at || '') || 0;
  const assetUrl = (r, re) => {
    const a = (Array.isArray(r.assets) ? r.assets : [])
      .find(x => x && x.browser_download_url && re.test(x.browser_download_url));
    return a ? a.browser_download_url : '';
  };

  async function initPrerelease() {
    const notice = document.getElementById('prerelease-notice');
    if (!notice) return;
    let releases;
    try {
      releases = await releaseList;
    } catch (e) {
      return; // leave the static notice as written
    }
    const published = releases.filter(r => r && !r.draft);
    const latestFull = published.filter(r => !r.prerelease).sort((a, b) => time(b) - time(a))[0];
    const pre = published
      .filter(r => r.prerelease && (!latestFull || time(r) > time(latestFull)))
      .sort((a, b) => time(b) - time(a))[0];
    if (!pre) {
      notice.hidden = true;
      return;
    }
    const exe = assetUrl(pre, /\.exe$/i);
    const dmg = assetUrl(pre, /\.dmg$/i);
    const platforms = exe && dmg ? ' for Windows and macOS' : exe ? ' for Windows' : dmg ? ' for macOS' : '';
    const tag = document.getElementById('prerelease-tag');
    const plat = document.getElementById('prerelease-platforms');
    const link = document.getElementById('prerelease-link');
    const direct = document.getElementById('prerelease-direct');
    const exeLink = document.getElementById('prerelease-exe');
    const dmgLink = document.getElementById('prerelease-dmg');
    const sep = document.getElementById('prerelease-sep');
    if (tag) tag.textContent = pre.tag_name || pre.name || 'pre-release';
    if (plat) plat.textContent = platforms;
    if (link && pre.html_url) link.href = pre.html_url;
    if (exeLink) { exeLink.hidden = !exe; if (exe) exeLink.href = exe; }
    if (dmgLink) { dmgLink.hidden = !dmg; if (dmg) dmgLink.href = dmg; }
    if (sep) sep.hidden = !(exe && dmg);
    if (direct) direct.hidden = !(exe || dmg);
    notice.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPrerelease);
  } else {
    initPrerelease();
  }
})();
