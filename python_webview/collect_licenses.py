#!/usr/bin/env python3
"""
Write build/licenses/: the license texts of everything the app bundles, which the
PyInstaller spec puts inside the app (folder "licenses").

PyInstaller bundles the Python runtime, its libraries (OpenSSL, expat, libffi, ncurses...)
and the Python packages below into the app. Their licenses (PSF, BSD, MIT, Apache-2.0)
ask that their notices travel with every copy, so this collects them, with the app's own
AGPL license and a pointer to the app's source:

  build/licenses/LICENSE.txt                 the app's license (AGPL-3.0), ../LICENSE
  build/licenses/COPYRIGHT.txt               ../COPYRIGHT
  build/licenses/THIRD_PARTY_NOTICES.md      ../THIRD_PARTY_NOTICES.md (FFmpeg etc.)
  build/licenses/SOURCE.txt                  where this build's source is (repo + commit)
  build/licenses/THIRD-PARTY-LICENSES.txt    Python, its libraries, every bundled package

FFmpeg's own license and notice travel separately, next to ffmpeg (bin/<platform>/).

Run it with the Python that builds the app, after installing the build requirements and
before PyInstaller (build_mac.sh and build-windows.yml do). It stops with an error if a
bundled package has no license text it can find, so nothing is shipped without one.
Texts for parts that ship none are kept in licenses/ (see licenses/README.md).
"""
from __future__ import annotations

import importlib.metadata as md
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
STATIC = HERE / 'licenses'
OUT = HERE / 'build' / 'licenses'
REPO_URL = 'https://github.com/rulingAnts/bulk_audio_normalizer'

# Build tools that PyInstaller never puts in the app. Everything else installed is listed:
# what gets bundled varies by platform (on Windows, setuptools and packaging are bundled),
# and listing a package that was not bundled is harmless, while missing one is not.
BUILD_ONLY = {
    'pip', 'pyinstaller', 'pyinstaller-hooks-contrib', 'altgraph', 'macholib', 'pefile',
    'pywin32-ctypes',
}
# Where the license text says something other than the package metadata.
LICENSE_NOTE = {'proxy-tools': 'BSD, per its LICENSE.txt (its metadata says MIT)'}
# License texts kept in licenses/ for packages that ship none.
STATIC_FOR = {'proxy-tools': 'proxy_tools.txt', 'pythonnet': 'pythonnet.txt',
              'clr-loader': 'clr_loader.txt'}
# License-like file names, also inside the package (e.g. pywebview's
# webview/lib/Microsoft.Web.WebView2.LICENSE.md, setuptools' vendored packages).
LICENSE_NAME = re.compile(r'(^|/)[^/]*(LICEN[CS]E|COPYING|NOTICE|AUTHORS)[^/]*$', re.IGNORECASE)
TEXT_SUFFIXES = {'', '.txt', '.md', '.rst', '.apache', '.bsd', '.mit', '.psf'}

RULE = '=' * 78


def norm(name: str) -> str:
    return re.sub(r'[-_.]+', '-', name).lower()


def license_files(dist: md.Distribution) -> list[Path]:
    found = []
    for f in dist.files or []:
        s = str(f)
        if not LICENSE_NAME.search(s) or Path(s).suffix.lower() not in TEXT_SUFFIXES:
            continue
        if '.dSYM/' in s:
            continue
        path = Path(dist.locate_file(f))
        if path.is_file():
            found.append(path)
    return sorted(set(found))


def python_license() -> Path:
    base = Path(sys.base_prefix)
    candidates = [
        base / 'LICENSE.txt',  # Windows (python.org)
        base / 'lib' / f'python{sys.version_info[0]}.{sys.version_info[1]}' / 'LICENSE.txt',  # macOS/Unix
    ]
    for c in candidates:
        if c.is_file():
            return c
    sys.exit(f'Python LICENSE.txt not found under {base}')


def app_commit() -> str:
    sha = os.environ.get('GITHUB_SHA', '').strip()
    if sha:
        return sha
    try:
        return subprocess.run(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], capture_output=True,
                              text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return 'unknown'


def section(title: str, body: str) -> str:
    return f'{RULE}\n{title}\n{RULE}\n\n{body.rstrip()}\n\n'


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for src, dst in (('LICENSE', 'LICENSE.txt'), ('COPYRIGHT', 'COPYRIGHT.txt'),
                     ('THIRD_PARTY_NOTICES.md', 'THIRD_PARTY_NOTICES.md')):
        (OUT / dst).write_bytes((REPO / src).read_bytes())

    commit = app_commit()
    (OUT / 'SOURCE.txt').write_text(
        'Bulk Audio Normalizer is free software under the GNU Affero General Public License,\n'
        'version 3 (LICENSE.txt). It comes with NO WARRANTY.\n\n'
        f'Source code: {REPO_URL}\n'
        f'This build was made from commit {commit}:\n'
        f'  {REPO_URL}/tree/{commit}\n'
        f'  {REPO_URL}/archive/{commit}.zip\n\n'
        "FFmpeg's license, notice and source: see FFMPEG-NOTICE.txt next to ffmpeg\n"
        '(bin/macos or bin/windows inside the app) and THIRD_PARTY_NOTICES.md.\n',
        encoding='utf-8')

    parts = [
        'Third-party licenses for the software bundled inside Bulk Audio Normalizer\n'
        f'(built on {platform.system()} {platform.machine()} with Python {platform.python_version()}).\n'
        'FFmpeg is listed in THIRD_PARTY_NOTICES.md; its license travels next to ffmpeg.\n'
        'Every package installed in the build environment is listed except pure build tools, so a\n'
        'few entries may be for packages the app does not actually include.\n\n'
    ]
    parts.append(section(f'Python {platform.python_version()} (the Python runtime)',
                         python_license().read_text(encoding='utf-8', errors='replace')))
    major_minor = f'{sys.version_info[0]}.{sys.version_info[1]}'
    incorporated = STATIC / f'python-{major_minor}-incorporated-software.txt'
    if not incorporated.is_file():
        sys.exit(f'{incorporated.name} missing: add the "Licenses and Acknowledgements for '
                 f'Incorporated Software" section of CPython {major_minor}\'s Doc/license.rst')
    parts.append(section('Software incorporated in Python (OpenSSL, expat, libffi, zlib, libmpdec, ...)',
                         incorporated.read_text(encoding='utf-8')))
    if sys.platform == 'darwin':
        parts.append(section('ncurses (bundled with the python.org macOS Python)',
                             (STATIC / 'ncurses.txt').read_text(encoding='utf-8')))
    if sys.platform == 'win32':
        parts.append(section('Microsoft runtime files (Windows)', (
            'vcruntime140.dll / vcruntime140_1.dll (the Microsoft Visual C++ runtime) and\n'
            'ucrtbase.dll / api-ms-win-*.dll (the Universal C Runtime): Microsoft runtime files that\n'
            'Python for Windows ships, redistributable with applications under Microsoft\'s terms\n'
            '(https://learn.microsoft.com/cpp/windows/redistributing-visual-cpp-files and\n'
            'https://learn.microsoft.com/cpp/windows/universal-crt-deployment).\n\n'
            'Microsoft.Web.WebView2.*.dll (inside pywebview): the Microsoft Edge WebView2 SDK; its\n'
            'license is in the pywebview section below (Microsoft.Web.WebView2.LICENSE.md).')))

    pyinstaller = md.distribution('pyinstaller')
    parts.append(section(
        f'PyInstaller {pyinstaller.version} (its bootloader starts the app)',
        '\n\n'.join(p.read_text(encoding='utf-8', errors='replace') for p in license_files(pyinstaller))))

    missing = []
    pyobjc_text = (STATIC / 'pyobjc.txt').read_text(encoding='utf-8')
    for dist in sorted(md.distributions(), key=lambda d: norm(d.metadata['Name'])):
        name = dist.metadata['Name']
        if norm(name) in BUILD_ONLY:
            continue
        meta_license = dist.metadata.get('License-Expression') or dist.metadata.get('License') or ''
        head = f'{name} {dist.version}'
        if norm(name) in LICENSE_NOTE:
            head += f'  (license: {LICENSE_NOTE[norm(name)]})'
        elif meta_license and '\n' not in meta_license.strip():
            head += f'  (license: {meta_license.strip()})'
        home = dist.metadata.get('Home-page') or ''
        files = license_files(dist)
        if files:
            body = '\n\n'.join(f'--- {p.name} ---\n' + p.read_text(encoding='utf-8', errors='replace')
                               for p in files)
        elif norm(name).startswith('pyobjc'):
            body = pyobjc_text
        elif norm(name) in STATIC_FOR:
            body = (STATIC / STATIC_FOR[norm(name)]).read_text(encoding='utf-8')
        else:
            missing.append(head)
            continue
        if norm(name) == 'pywebview':
            body += '\n\n' + (STATIC / 'pywebview-js.txt').read_text(encoding='utf-8')
        if home:
            body = f'{home}\n\n{body}'
        parts.append(section(head, body))

    if missing:
        print('No license text found for: ' + ', '.join(missing), file=sys.stderr)
        print(f'Add one to {STATIC} and to STATIC_FOR in {Path(__file__).name}.', file=sys.stderr)
        return 1

    out = OUT / 'THIRD-PARTY-LICENSES.txt'
    out.write_text(''.join(parts), encoding='utf-8')
    print(f'Wrote {OUT}: ' + ', '.join(sorted(p.name for p in OUT.iterdir())))
    print(f'  {out.name}: {out.stat().st_size // 1024} KB, '
          f'{sum(1 for p in parts if p.startswith(RULE))} sections; app commit {commit}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
