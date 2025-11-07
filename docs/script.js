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
