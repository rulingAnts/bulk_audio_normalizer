"""
File names with every character Windows allows (issue #2, follow-up).

BlackBrix (Windows 11) pointed out that Windows forbids only \\ / : * ? " < > |
in file names, so a name like "öüäß€@ . _'#+~²!³ÜÖÄ.txt" is valid. These
tests send such names through every place a name or path travels:

  Python -> JS     js_call (batch and preview window), checked in node
  JS -> Python     the exact strings JS received are handed back to
                   get_audio_file / reveal_path
  path -> URL      renderer.js toFileUrl, run in node
  path -> HTML     no file name is ever interpolated into innerHTML
  path -> FFmpeg   the real batch and preview workers with real ffmpeg
  logging          a strict cp1252 log stream cannot stop a batch

Run from the repository root:
    python3 -m unittest discover -s python_webview/tests -v

Standard library only. Node checks run when `node` is on PATH; FFmpeg runs
use whatever ffmpeg/ffprobe the app itself finds (bin/<platform>/, then
PATH). CI sets BAN_REQUIRE_FFMPEG=1 / BAN_REQUIRE_NODE=1 so a missing tool
fails the run instead of skipping, and BAN_REQUIRE_BUNDLED_FFMPEG=1 so the
FFmpeg under test is the one that gets bundled into the exe.
"""
import base64
import io
import json
import logging
import ntpath
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_js_bridge import (  # noqa: E402  (also stubs webview/psutil when missing)
    APP_DIR, FFMPEG_READY, FFMPEG_PATHS, NODE, FakeWindow, main, parse_call,
    run_in_node, write_wav,
)

# BlackBrix's example, exactly as written in the issue, as a .wav name.
BLACKBRIX = "öüäß€@ . _'#+~²!³ÜÖÄ.wav"
# Each distinct character of it on its own.
BLACKBRIX_CHARS = list(dict.fromkeys("öüäß€@ . _'#+~²!³ÜÖÄ"))

OTHER_NAMES = [
    "07 Johnny Don't Go.wav",
    'a.b.c.wav',
    '.hidden.wav',
    'R&B.wav',
    '100%.wav',
    '%d take %03d.wav',
    'Take1,Tom.wav',
    'semi;colon=equals.wav',
    '[brackets] (parens) {braces}.wav',
    'caret^ backtick`.wav',
    'tune \U0001F3B5.wav',
    '  two  spaces .wav',
    'UPPER.WAV',
    'old take.wave',
]
# Legal on macOS/Linux, not on Windows.
POSIX_ONLY_NAMES = [
    'He said "hi".wav',
    'back\\slash \\u\\x.wav',
    'pipe|lt<gt>?star*.wav',
    'colon: yes.wav',
    'line one\nline two.wav',
]

REQUIRE_FFMPEG = os.environ.get('BAN_REQUIRE_FFMPEG') == '1'
REQUIRE_NODE = os.environ.get('BAN_REQUIRE_NODE') == '1'
REQUIRE_BUNDLED = os.environ.get('BAN_REQUIRE_BUNDLED_FFMPEG') == '1'


def char_names():
    """
    'x?y NN.wav' for each of BlackBrix's characters ('x y 06.wav', ...).

    The number keeps 'xäy' and 'xÄy' apart: NTFS and APFS compare names
    without case, so they would be the same file.
    """
    return [f'x{c}y {i:02d}.wav' for i, c in enumerate(BLACKBRIX_CHARS)]


def all_flat_names():
    names = [BLACKBRIX] + char_names() + OTHER_NAMES
    if os.name != 'nt':
        names += POSIX_ONLY_NAMES
    return names


class RequiredToolsTests(unittest.TestCase):
    """In CI the end-to-end checks must run, not skip."""

    def test_required_tools_are_present(self):
        if REQUIRE_FFMPEG:
            self.assertTrue(FFMPEG_READY, 'BAN_REQUIRE_FFMPEG=1 but the app finds no ffmpeg/ffprobe')
        if REQUIRE_NODE:
            self.assertTrue(NODE, 'BAN_REQUIRE_NODE=1 but node is not on PATH')
        if REQUIRE_BUNDLED:
            self.assertTrue(FFMPEG_READY)
            bin_dir = (APP_DIR / 'bin').resolve()
            for exe in FFMPEG_PATHS:
                self.assertTrue(Path(exe).resolve().is_relative_to(bin_dir),
                                f'{exe} is not the bundled binary under {bin_dir}')


class JsCallNameTests(unittest.TestCase):
    """Python -> JS: every name arrives in JavaScript unchanged."""

    def values(self):
        vals = [BLACKBRIX] + BLACKBRIX_CHARS + char_names() + OTHER_NAMES + POSIX_ONLY_NAMES
        vals += [
            ' ', '   ', '.', '..', '...wav',
            'C:\\Users\\Black Brix\\Music\\' + BLACKBRIX,
            '\\\\nas\\share #1\\' + BLACKBRIX,
            '/Users/seth/Music/' + BLACKBRIX,
        ]
        return vals

    def test_round_trip(self):
        for value in self.values():
            with self.subTest(value=value):
                w = FakeWindow()
                main.js_call(w, 'triggerFileStart', value, value)
                self.assertEqual(parse_call(w.scripts[0]), ('triggerFileStart', [value, value]))
                self.assertTrue(w.scripts[0].isascii())

    @unittest.skipUnless(NODE, 'node not on PATH')
    def test_node_receives_exact_values(self):
        values = self.values()
        w = FakeWindow()
        for value in values:
            main.js_call(w, 'triggerPreviewFile', value, value + '.out', value, 'C:\\tmp\\ban-preview-x')
        for wrap in (False, True):
            results = run_in_node(w.scripts, wrap=wrap)
            for value, result in zip(values, results):
                with self.subTest(value=value, wrap=wrap):
                    self.assertTrue(result['ok'], result.get('error'))
                    self.assertEqual(result['args'],
                                     [value, value + '.out', value, 'C:\\tmp\\ban-preview-x'])


# --------------------------------------------------------------------------
# path -> file:// URL (renderer.js toFileUrl)

def extract_js_function(source: str, name: str) -> str:
    m = re.search(rf'^function {name}\(.*?^\}}\n', source, re.MULTILINE | re.DOTALL)
    if not m:
        raise AssertionError(f'function {name} not found')
    return m.group(0)


URL_HARNESS = r"""
const fs = require('fs');
const { fileURLToPath } = require('url');
const src = fs.readFileSync(process.argv[2], 'utf8');
const cases = JSON.parse(fs.readFileSync(process.argv[3], 'utf8'));
const toFileUrl = new Function(src + '\nreturn toFileUrl;')();
const out = cases.map((p) => {
  const href = toFileUrl(p);
  const u = new URL(href);
  let viaNode = null;
  try {
    viaNode = /^[A-Za-z]:|^[\\/]{2}/.test(p) ? fileURLToPath(href, { windows: true }) : fileURLToPath(href, { windows: false });
  } catch (e) { viaNode = 'unsupported: ' + e.message; }
  return { href, protocol: u.protocol, host: u.host, pathname: u.pathname,
           decoded: decodeURIComponent(u.pathname), hash: u.hash, search: u.search, viaNode };
});
process.stdout.write(JSON.stringify(out));
"""


@unittest.skipUnless(NODE, 'node not on PATH')
class FileUrlTests(unittest.TestCase):

    WINDOWS = [
        'C:\\Music\\Track #2.wav',
        'C:\\Music\\what?.wav',
        'C:\\Music\\100%.wav',
        'C:\\Music\\a+b & c.wav',
        'D:\\Aufnahmen\\Ünïcode Földer\\' + BLACKBRIX,
        'C:/Music/forward #slashes.wav',
        'c:\\lower\\%20 not a space.wav',
    ]
    POSIX = [
        '/Users/seth/Music/Track #2.wav',
        '/Users/seth/Music/what?.wav',
        '/Users/seth/Music/100%.wav',
        '/Users/seth/Music/' + BLACKBRIX,
        '/tmp/back\\slash #1.wav',
        '/tmp/%2F not a slash.wav',
    ]
    UNC = '\\\\nas\\share #1\\Track #2.wav'

    def run_cases(self, cases):
        src = extract_js_function(
            (APP_DIR / 'frontend' / 'renderer.js').read_text(encoding='utf-8'), 'toFileUrl')
        with tempfile.TemporaryDirectory() as tmp:
            src_file = Path(tmp) / 'fn.js'
            cases_file = Path(tmp) / 'cases.json'
            harness = Path(tmp) / 'harness.js'
            src_file.write_text(src, encoding='utf-8')
            cases_file.write_text(json.dumps(cases), encoding='utf-8')
            harness.write_text(URL_HARNESS, encoding='utf-8')
            proc = subprocess.run([NODE, str(harness), str(src_file), str(cases_file)],
                                  capture_output=True, text=True, encoding='utf-8', timeout=60)
        if proc.returncode != 0:
            raise AssertionError(f'node failed: {proc.stderr}')
        return json.loads(proc.stdout)

    def test_windows_paths(self):
        for path, r in zip(self.WINDOWS, self.run_cases(self.WINDOWS)):
            with self.subTest(path=path):
                self.assertEqual(r['protocol'], 'file:')
                self.assertEqual(r['hash'], '')
                self.assertEqual(r['search'], '')
                self.assertEqual(r['decoded'], '/' + path.replace('\\', '/'))
                if not r['viaNode'].startswith('unsupported'):
                    self.assertEqual(r['viaNode'], path.replace('/', '\\'))

    def test_posix_paths(self):
        for path, r in zip(self.POSIX, self.run_cases(self.POSIX)):
            with self.subTest(path=path):
                self.assertEqual(r['protocol'], 'file:')
                self.assertEqual(r['host'], '')
                self.assertEqual(r['hash'], '')
                self.assertEqual(r['search'], '')
                self.assertEqual(r['decoded'], path)
                if not r['viaNode'].startswith('unsupported'):
                    self.assertEqual(r['viaNode'], path)

    def test_unc_path(self):
        r = self.run_cases([self.UNC])[0]
        self.assertEqual(r['host'], 'nas')
        self.assertEqual(r['decoded'], '/share #1/Track #2.wav')
        self.assertEqual(r['hash'], '')

    def test_old_encodeURI_version_was_broken(self):
        """Control: encodeURI leaves '#' alone, so the old URL lost the name's tail."""
        proc = subprocess.run(
            [NODE, '-e', "process.stdout.write(new URL('file://' + encodeURI('/C:/Music/Track #2.wav')).hash)"],
            capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(proc.stdout, '#2.wav')


# --------------------------------------------------------------------------
# path -> HTML

class NoNamesInHtmlTests(unittest.TestCase):
    """File names must reach the page as text, never as HTML."""

    ALLOWED = {'originalId', 'previewId'}  # random [a-z0-9] ids made in JS

    def test_innerhtml_templates_only_interpolate_ids(self):
        for js in ('renderer.js', 'preview.js'):
            src = (APP_DIR / 'frontend' / js).read_text(encoding='utf-8')
            templates = re.findall(r'innerHTML\s*=\s*`(.*?)`', src, re.DOTALL)
            self.assertTrue(templates, js)
            for t in templates:
                for expr in re.findall(r'\$\{(.*?)\}', t):
                    with self.subTest(file=js, expr=expr):
                        self.assertIn(expr.strip(), self.ALLOWED)

    def test_names_are_set_with_textcontent(self):
        renderer = (APP_DIR / 'frontend' / 'renderer.js').read_text(encoding='utf-8')
        self.assertIn('nameEl.textContent = String(name);', renderer)
        for js in ('renderer.js', 'preview.js'):
            src = (APP_DIR / 'frontend' / js).read_text(encoding='utf-8')
            self.assertIn('pathEl.textContent = `…/${display}`;', src, js)


# --------------------------------------------------------------------------
# path -> subprocess (Explorer / Finder)

class RevealTests(unittest.TestCase):

    def test_windows_command_quotes_the_whole_path(self):
        cmd = main.reveal_command('C:\\Music\\Take1,Tom ' + BLACKBRIX, 'Windows')
        self.assertEqual(cmd, 'explorer /select,"C:\\Music\\Take1,Tom ' + BLACKBRIX + '"')

    def test_windows_command_uses_backslashes(self):
        self.assertEqual(main.reveal_command('C:/Music/a b/x.wav', 'Windows'),
                         'explorer /select,"C:\\Music\\a b\\x.wav"')

    def test_mac_and_linux_pass_the_path_as_one_argument(self):
        path = '/Users/seth/' + BLACKBRIX
        self.assertEqual(main.reveal_command(path, 'Darwin'), ['open', '-R', path])
        self.assertEqual(main.reveal_command(path, 'Linux'), ['xdg-open', '/Users/seth'])

    def test_reveal_runs_the_command_for_a_real_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / BLACKBRIX
            target.write_bytes(b'RIFF')
            for api in (main.API(), main.PreviewAPI()):
                with mock.patch('subprocess.Popen') as popen, \
                        mock.patch('platform.system', return_value='Windows'):
                    self.assertTrue(api.reveal_path(str(target)))
                popen.assert_called_once_with(f'explorer /select,"{ntpath.normpath(str(target))}"')
            self.assertFalse(main.reveal_in_file_manager(str(Path(tmp) / 'missing.wav')))


# --------------------------------------------------------------------------
# scanning, output naming, messages

def write_appledouble(path):
    Path(path).write_bytes(main.APPLEDOUBLE_MAGIC + b'\x00\x02\x00\x00' + b'\x00' * 74)


class ScanTests(unittest.TestCase):

    def test_appledouble_is_skipped_but_dot_names_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            write_wav(d / "07 Johnny Don't Go.wav", seconds=0.05)
            write_appledouble(d / "._07 Johnny Don't Go.wav")
            write_wav(d / '._not metadata.wav', seconds=0.05)  # real audio, "._" name
            write_wav(d / '.hidden.wav', seconds=0.05)
            found = sorted(os.path.basename(p) for p in main.API().scan_files(tmp))
        self.assertEqual(found, sorted(['._not metadata.wav', "07 Johnny Don't Go.wav", '.hidden.wav']))

    def test_not_written_message_names_files(self):
        msg = main.not_written_message([BLACKBRIX, "07 Johnny Don't Go.wav"], 10)
        self.assertTrue(msg.startswith('2 of 10 files could not be processed: '))
        self.assertIn(BLACKBRIX, msg)
        many = main.not_written_message([f'{i}.wav' for i in range(8)], 8)
        self.assertIn('0.wav, 1.wav, 2.wav, 3.wav, 4.wav and 3 more.', many)

    def test_ffmpeg_error_tail(self):
        from backend.audio_processor import ffmpeg_error_tail
        err = 'one\n\ntwo\nC:\\x\\öü.wav: Invalid data\n'.encode('utf-8') + b'\xff bad byte\n'
        self.assertEqual(ffmpeg_error_tail(err), 'two | C:\\x\\öü.wav: Invalid data | \ufffd bad byte')
        self.assertEqual(ffmpeg_error_tail(b''), 'no error message')


class StrictLogStreamTests(unittest.TestCase):
    """A log stream that cannot encode a name must not stop the batch."""

    def test_batch_survives_cp1252_strict_log_stream(self):
        stream = io.TextIOWrapper(io.BytesIO(), encoding='cp1252', errors='strict')
        handler = logging.StreamHandler(stream)
        root = logging.getLogger()
        root.addHandler(handler)
        self.addCleanup(root.removeHandler, handler)
        names = [BLACKBRIX, 'tune \U0001F3B5.wav', 'Ω omega.wav']

        def fake(input_path, output_path, settings, job_id, progress_cb, log_cb):
            Path(output_path).write_bytes(b'RIFF')
            log_cb(job_id, 'render', f'Completed: {output_path}')
            return True

        with tempfile.TemporaryDirectory() as tmp:
            in_dir, out_dir = Path(tmp) / 'in', Path(tmp) / 'out'
            in_dir.mkdir()
            out_dir.mkdir()
            for n in names:
                (in_dir / n).write_bytes(b'RIFF')
            w = FakeWindow()
            saved = main.main_window
            try:
                main.main_window = w
                main.processing_state.update(running=True, paused=False, total_files=0)
                main.processing_state['processed_files'].clear()
                with mock.patch.object(logging, 'raiseExceptions', False), \
                        mock.patch.object(main, 'normalize_file', side_effect=fake):
                    main.API()._process_batch_worker(str(in_dir), str(out_dir), {})
            finally:
                main.main_window = saved
        self.assertEqual(parse_call(w.scripts[-1])[0], 'triggerAllDone')


# --------------------------------------------------------------------------
# end to end with real FFmpeg

def wav_data_bytes(path):
    """Size of the data chunk of a RIFF/WAVE file (0 if it is not one).

    Not the wave module: LUFS output is WAVE_FORMAT_EXTENSIBLE, which
    Python's wave module reads only from 3.12 on.
    """
    data = Path(path).read_bytes()
    if data[:4] != b'RIFF' or data[8:12] != b'WAVE':
        return 0
    pos = 12
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack('<I', data[pos + 4:pos + 8])[0]
        if cid == b'data':
            return size
        pos += 8 + size + (size % 2)
    return 0


@unittest.skipUnless(FFMPEG_READY, 'the app finds no ffmpeg/ffprobe')
class EndToEndNameTests(unittest.TestCase):
    """The real batch and preview workers, real FFmpeg, every kind of name."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.in_dir, self.out_dir = root / 'in', root / 'out'
        self.in_dir.mkdir()
        self.out_dir.mkdir()
        self.rels = []
        # 0.5 s: LUFS analysis of a clip shorter than one 0.4 s loudness block
        # measures -inf and the render then fails (not a file-name problem).
        for name in all_flat_names():
            write_wav(self.in_dir / name, seconds=0.5)
            self.rels.append(name)
        # Same name at the top level and in a subfolder; a Unicode folder.
        for sub, name in [('sub dir #1', '01.wav'), ('', '01.wav'), ('Ünïcode Földer', BLACKBRIX)]:
            (self.in_dir / sub).mkdir(exist_ok=True)
            write_wav(self.in_dir / sub / name, seconds=0.5)
            self.rels.append(os.path.join(sub, name) if sub else name)
        # macOS metadata twin of the issue's file: must be skipped.
        write_appledouble(self.in_dir / "._07 Johnny Don't Go.wav")
        # Every name made its own file (no case or normalization collisions).
        self.assertEqual(len(main.API().scan_files(str(self.in_dir))), len(self.rels))
        self.saved_main, self.saved_preview = main.main_window, main.preview_window
        self.addCleanup(setattr, main, 'main_window', self.saved_main)
        self.addCleanup(setattr, main, 'preview_window', self.saved_preview)
        main.process_manager.cancel_all = False

    def run_batch(self, settings):
        w = FakeWindow()
        main.main_window = w
        main.processing_state.update(running=True, paused=False, total_files=0)
        main.processing_state['processed_files'].clear()
        main.API()._process_batch_worker(str(self.in_dir), str(self.out_dir), settings)
        return w

    def check_batch(self, w):
        calls = [parse_call(s) for s in w.scripts]
        fns = [fn for fn, _ in calls]
        errors = [args for fn, args in calls if fn == 'triggerError']
        self.assertEqual(errors, [])
        self.assertNotIn('triggerFileFailed', fns)
        self.assertEqual(fns[-1], 'triggerAllDone')
        started = [args for fn, args in calls if fn == 'triggerFileStart']
        self.assertEqual(sorted(a[0] for a in started), sorted(self.rels))
        self.assertTrue(all(a[0] == a[1] for a in started))
        self.assertNotIn("._07 Johnny Don't Go.wav", [a[0] for a in started])
        self.assertEqual(calls[0], ('triggerBatchStart', [len(self.rels)]))
        for rel in self.rels:
            with self.subTest(rel=rel):
                out = self.out_dir / rel
                self.assertTrue(out.is_file(), rel)
                self.assertGreater(wav_data_bytes(out), 0)
        self.assertFalse((self.out_dir / "._07 Johnny Don't Go.wav").exists())
        if NODE:
            for (fn, args), result in zip(calls, run_in_node(w.scripts, wrap=True)):
                with self.subTest(fn=fn, args=args):
                    self.assertTrue(result['ok'], result.get('error'))
                    self.assertEqual((result['fn'], result['args']), (fn, args))

    def test_batch_peak_with_auto_trim(self):
        # detect (silencedetect) + analyze (volumedetect) + render
        self.check_batch(self.run_batch({'autoTrim': True, 'trimMinFileMs': 0, 'trimHPF': True}))

    def test_batch_lufs(self):
        # loudnorm analysis + render
        self.check_batch(self.run_batch({'normMode': 'lufs', 'verboseLogs': True,
                                         'targetBitDepth': 'original'}))

    def test_unreadable_file_is_reported_and_the_rest_are_written(self):
        bad = 'bad #1 ' + BLACKBRIX
        (self.in_dir / bad).write_bytes(b'this is not audio ' * 50)
        w = self.run_batch({})
        calls = [parse_call(s) for s in w.scripts]
        fns = [fn for fn, _ in calls]
        self.assertNotIn('triggerAllDone', fns)
        self.assertIn(('triggerFileFailed', [bad]), calls)
        self.assertEqual(fns[-1], 'triggerError')
        message = calls[-1][1][0]
        self.assertTrue(message.startswith(f'1 of {len(self.rels) + 1} files could not be processed: '), message)
        self.assertIn(bad, message)
        logs = [args for fn, args in calls if fn == 'triggerLog' and args[0] == bad]
        self.assertTrue(any(a[2].startswith('FFmpeg failed (exit code') for a in logs), logs)
        for rel in self.rels:
            self.assertTrue((self.out_dir / rel).is_file(), rel)

    def test_preview_worker_and_audio_round_trip(self):
        sample = [str(self.in_dir / rel) for rel in self.rels]
        tmp_base = tempfile.mkdtemp(prefix='ban-preview-test-')
        self.addCleanup(shutil.rmtree, tmp_base, ignore_errors=True)
        w = FakeWindow()
        main.preview_window = w
        main.processing_state['preview_running'] = True
        main.API()._preview_worker(sample, tmp_base, str(self.in_dir), {})
        calls = [parse_call(s) for s in w.scripts]
        self.assertEqual(calls[-1], ('triggerPreviewDone', [len(sample), tmp_base]))
        sent = [args for fn, args in calls if fn == 'triggerPreviewFile']
        self.assertEqual(len(sent), len(sample))
        expected = {s: [s, os.path.join(tmp_base, os.path.relpath(s, self.in_dir)),
                        os.path.relpath(s, self.in_dir), tmp_base] for s in sample}
        for args in sent:
            self.assertEqual(args, expected[args[0]])
        # What JavaScript received is what it hands back to Python.
        received = sent
        if NODE:
            results = run_in_node(w.scripts, wrap=True)
            self.assertTrue(all(r['ok'] for r in results))
            received = [r['args'] for r in results if r['fn'] == 'triggerPreviewFile']
            self.assertEqual(received, sent)
        papi = main.PreviewAPI()
        for original, preview, rel, _ in received:
            with self.subTest(rel=rel):
                for path in (original, preview):
                    url = papi.get_audio_file(path)
                    self.assertIsNotNone(url, path)
                    head, data = url.split(',', 1)
                    self.assertTrue(head.startswith('data:audio/'), head)
                    self.assertEqual(base64.b64decode(data), Path(path).read_bytes())


if __name__ == '__main__':
    unittest.main()
