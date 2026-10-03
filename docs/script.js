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
    if (mac) mac.href = latest;
    if (win) win.href = latest;
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

  if (!macAsset && macLink) macLink.title = 'No direct DMG asset found; click to view latest releases';
  if (!winAsset && winLink) winLink.title = 'No direct EXE asset found; click to view latest releases';

      if (!macAsset || !winAsset) {
        // Ensure we still have a working path
        if (macLink && !macLink.href) macLink.href = latest;
        if (winLink && !winLink.href) winLink.href = latest;
      }
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
  const owner = 'rulingAnts';
  const repo = 'bulk_audio_normalizer';
  const listApi = `https://api.github.com/repos/${owner}/${repo}/releases?per_page=10`;

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
      const res = await fetch(listApi, { headers: { 'Accept': 'application/vnd.github+json' } });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      releases = await res.json();
      if (!Array.isArray(releases)) throw new Error('unexpected response');
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
    if (tag) tag.textContent = pre.tag_name || pre.name || 'pre-release';
    if (plat) plat.textContent = platforms;
    if (link && pre.html_url) link.href = pre.html_url;
    if (direct && exeLink && exe) {
      exeLink.href = exe;
      direct.hidden = false;
    } else if (direct) {
      direct.hidden = true;
    }
    notice.hidden = false;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initPrerelease);
  } else {
    initPrerelease();
  }
})();
