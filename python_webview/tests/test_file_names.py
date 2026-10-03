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
import types
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
    'open { brace.wav',
    'close } brace.wav',
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
        '/\\x/folder starts with a backslash #1.wav',
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

    def test_long_path_prefixes(self):
        drive, unc = self.run_cases(['\\\\?\\C:\\Music\\Track #2.wav',
                                     '\\\\?\\UNC\\nas\\share #1\\Track #2.wav'])
        self.assertEqual((drive['host'], drive['decoded'], drive['hash']), ('', '/C:/Music/Track #2.wav', ''))
        self.assertEqual((unc['host'], unc['decoded'], unc['hash']), ('nas', '/share #1/Track #2.wav', ''))

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
        self.assertRegex(renderer, r'\bnameEl\.textContent\s*=')
        for js in ('renderer.js', 'preview.js'):
            src = (APP_DIR / 'frontend' / js).read_text(encoding='utf-8')
            with self.subTest(file=js):
                self.assertRegex(src, r'\bpathEl\.textContent\s*=')
                # Nothing but the static templates and '' is ever assigned as HTML.
                for rhs in re.findall(r'\.(?:innerHTML|outerHTML)\s*=\s*(\S)', src):
                    self.assertIn(rhs, "`'")
                self.assertNotRegex(src, r'insertAdjacentHTML|document\.write')


@unittest.skipUnless(NODE, 'node not on PATH')
class CardLabelTests(unittest.TestCase):
    """The label over a preview card uses the separator of the platform's paths."""

    CASES = [
        ('C:\\Music\\sub dir #1\\01.wav', 'sub dir #1\\01.wav', '\u2026\\sub dir #1\\01.wav'),
        ('\\\\nas\\share\\' + BLACKBRIX, BLACKBRIX, '\u2026\\' + BLACKBRIX),
        ('/Users/seth/sub dir #1/01.wav', 'sub dir #1/01.wav', '\u2026/sub dir #1/01.wav'),
        ('/Users/seth/back\\slash.wav', '', '\u2026/back\\slash.wav'),
        ('C:\\Music\\R&B <live>.wav', '', '\u2026\\R&B <live>.wav'),
    ]

    def test_both_windows(self):
        for js in ('renderer.js', 'preview.js'):
            src = extract_js_function((APP_DIR / 'frontend' / js).read_text(encoding='utf-8'), 'cardLabel')
            script = (src + '\nconst cases = JSON.parse(process.argv[1]);\n'
                      'process.stdout.write(JSON.stringify(cases.map(([o, r]) => cardLabel(o, r).text)));')
            proc = subprocess.run([NODE, '-e', script, json.dumps([c[:2] for c in self.CASES])],
                                  capture_output=True, text=True, encoding='utf-8', timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout), [c[2] for c in self.CASES], js)


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

    def test_loudnorm_json_after_a_name_with_braces(self):
        # FFmpeg prints "Input #0, wav, from '<name>':" before loudnorm's JSON.
        from backend.audio_processor import parse_loudnorm_json
        block = ('[Parsed_loudnorm_0 @ 0x1] \n{\n\t"input_i" : "-27.47",\n\t"input_tp" : "-4.47",\n'
                 '\t"input_lra" : "0.00",\n\t"input_thresh" : "-37.47",\n\t"target_offset" : "0.53"\n}\n')
        for name in ['x{y 02.wav', 'x}y.wav', '[brackets] (parens) {braces}.wav',
                     'x{"input_i" : "1"}y.wav', BLACKBRIX]:
            with self.subTest(name=name):
                text = (f"Input #0, wav, from 'C:\\Music\\{name}':\n  Duration: 00:00:00.50\n"
                        f"{block}[out#0/null @ 0x2] audio:0KiB\n")
                self.assertEqual(parse_loudnorm_json(text)['input_i'], '-27.47')
        self.assertIsNone(parse_loudnorm_json("Input #0, wav, from 'x{y.wav':\n"))
        self.assertIsNone(parse_loudnorm_json(''))

    def test_ffmpeg_error_tail(self):
        from backend.audio_processor import ffmpeg_error_tail
        err = 'one\n\ntwo\nC:\\x\\öü.wav: Invalid data\n'.encode('utf-8') + b'\xff bad byte\n'
        self.assertEqual(ffmpeg_error_tail(err), 'two | C:\\x\\öü.wav: Invalid data | \ufffd bad byte')
        self.assertEqual(ffmpeg_error_tail(b''), 'no error message')


class NestedOutputTests(unittest.TestCase):
    """
    An output folder inside the input folder.

    The UI only refuses the very same folder, and an empty subfolder passes
    validate_output_empty, so "Music" -> "Music/normalized" is allowed. The
    outputs written there must never be taken for inputs: not while the batch
    runs, and not by the check at the end (v2.0.2 pre-review: every file was
    reported as not written because that check rescanned the input folder).
    """

    NAMES = ["07 Johnny Don't Go.wav", BLACKBRIX]

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.in_dir = Path(tmp.name) / 'nested' / 'Music'
        self.out_dir = self.in_dir / 'normalized'
        self.out_dir.mkdir(parents=True)
        for name in self.NAMES:
            (self.in_dir / name).write_bytes(b'RIFF')
        self.addCleanup(setattr, main, 'main_window', main.main_window)

    def run_worker(self, fake, out_dir):
        w = FakeWindow()
        main.main_window = w
        main.processing_state.update(running=True, paused=False, total_files=0)
        main.processing_state['processed_files'].clear()
        with mock.patch.object(main, 'normalize_file', side_effect=fake) as nf:
            main.API()._process_batch_worker(str(self.in_dir), out_dir, {})
        return [parse_call(s) for s in w.scripts], nf

    @staticmethod
    def write_output(input_path, output_path, settings, job_id, progress_cb, log_cb):
        Path(output_path).write_bytes(b'RIFF')
        return True

    def check_all_done(self, calls, nf):
        self.assertNotIn('triggerError', [fn for fn, _ in calls])
        self.assertEqual(calls[-1], ('triggerAllDone', []))
        started = [args[0] for fn, args in calls if fn == 'triggerFileStart']
        self.assertEqual(sorted(started), sorted(self.NAMES))
        self.assertEqual(nf.call_count, len(self.NAMES))
        for name in self.NAMES:
            self.assertTrue((self.out_dir / name).is_file(), name)
        self.assertFalse((self.out_dir / 'normalized').exists())

    def test_outputs_are_not_reported_or_processed_as_inputs(self):
        # validate_output_empty ignores dot names, so this can be there at the start.
        (self.out_dir / '.left over.wav').write_bytes(b'RIFF')
        self.assertTrue(main.API().validate_output_empty(str(self.out_dir)))
        self.check_all_done(*self.run_worker(self.write_output, str(self.out_dir)))

    def test_output_path_with_a_trailing_separator(self):
        self.check_all_done(*self.run_worker(self.write_output, str(self.out_dir) + os.sep))

    def test_output_folder_next_to_the_input_is_unaffected(self):
        sibling = self.in_dir.parent / 'Music normalized'
        sibling.mkdir()
        self.out_dir = sibling
        self.check_all_done(*self.run_worker(self.write_output, str(sibling)))

    def test_subfolder_inside(self):
        music, out = str(self.in_dir), str(self.out_dir)
        self.assertEqual(main.subfolder_inside(out, music), os.path.normcase('normalized'))
        self.assertEqual(main.subfolder_inside(out + os.sep, music + os.sep), os.path.normcase('normalized'))
        self.assertIsNone(main.subfolder_inside(music, music))   # same folder: the UI refuses it
        self.assertIsNone(main.subfolder_inside(music, out))     # input inside output
        self.assertIsNone(main.subfolder_inside(str(self.in_dir.parent / 'Music2'), music))
        files = [str(self.in_dir / n) for n in self.NAMES] + [str(self.out_dir / 'x.wav')]
        self.assertEqual(main.without_output_folder(files, music, out), files[:2])
        self.assertEqual(main.without_output_folder(files, music, music), files)

    def test_an_output_that_was_not_written_is_still_reported(self):
        def fake(input_path, output_path, settings, job_id, progress_cb, log_cb):
            if job_id != BLACKBRIX:
                Path(output_path).write_bytes(b'RIFF')
            return True

        calls, _ = self.run_worker(fake, str(self.out_dir))
        self.assertEqual(calls[-1], ('triggerError', [main.not_written_message([BLACKBRIX], 2)]))


class FakeProc:
    """What process_manager.spawn returns, as far as normalize_file uses it."""

    def __init__(self, returncode, stderr=b''):
        self.returncode, self.stderr, self.pid = returncode, stderr, None

    def communicate(self, timeout=None):
        return b'', self.stderr

    def poll(self):
        return self.returncode


class CancelTests(unittest.TestCase):
    """Cancel/pause are hidden in the UI today; these keep their plumbing honest."""

    def setUp(self):
        self.addCleanup(setattr, main.process_manager, 'cancel_all', False)
        self.addCleanup(setattr, main, 'main_window', main.main_window)

    def test_a_render_killed_by_cancel_is_not_completed(self):
        from backend.audio_processor import normalize_file
        with tempfile.TemporaryDirectory() as tmp:
            src, out = Path(tmp) / BLACKBRIX, Path(tmp) / 'out' / BLACKBRIX
            write_wav(src, seconds=0.1)
            out.parent.mkdir()

            def spawn(cmd, job_id=None, **kwargs):
                if cmd[-1] == str(out):  # the render, killed half way
                    out.write_bytes(b'RIFF cut short')
                    main.process_manager.cancel_all = True
                    return FakeProc(1, b'Exiting normally, received signal 2.')
                return FakeProc(0, b'[Parsed_volumedetect_0] max_volume: -6.0 dB')

            logs = []
            with mock.patch.object(main.process_manager, 'spawn', side_effect=spawn):
                ok = normalize_file(str(src), str(out), {}, 'j', lambda *a: None, lambda *a: logs.append(a))
            self.assertIsNone(ok)
            self.assertEqual(logs[-1], ('j', 'render', 'Canceled'))
            self.assertFalse(out.exists())

    def test_a_canceled_file_is_not_marked_done_and_stopped_is_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_dir, out_dir = Path(tmp) / 'in', Path(tmp) / 'out'
            in_dir.mkdir()
            out_dir.mkdir()
            (in_dir / BLACKBRIX).write_bytes(b'RIFF')

            def fake(input_path, output_path, settings, job_id, progress_cb, log_cb):
                main.processing_state['running'] = False  # what cancel_processing does
                main.process_manager.kill_all()
                return None

            w = FakeWindow()
            main.main_window = w
            main.processing_state.update(running=True, paused=False, total_files=0)
            main.processing_state['processed_files'].clear()
            with mock.patch.object(main, 'normalize_file', side_effect=fake):
                main.API()._process_batch_worker(str(in_dir), str(out_dir), {})
        fns = [parse_call(s)[0] for s in w.scripts]
        self.assertEqual(fns, ['triggerBatchStart', 'triggerFileStart', 'triggerStopped'])

    def test_the_cancel_flag_is_reset_for_the_next_batch_and_on_resume(self):
        api = main.API()
        with mock.patch.object(main.threading, 'Thread'):
            main.process_manager.cancel_all = True
            self.assertTrue(api.start_processing('in', 'out', {})['ok'])
            self.assertFalse(main.process_manager.is_canceled())
            api.pause_processing()
            self.assertTrue(main.process_manager.is_canceled())
            api.resume_processing()
            self.assertFalse(main.process_manager.is_canceled())
        main.processing_state.update(running=False, paused=False)


class FolderDialogTests(unittest.TestCase):

    def test_folder_dialog_type(self):
        new = types.SimpleNamespace(FileDialog=types.SimpleNamespace(FOLDER=20))
        with mock.patch.object(main, 'webview', new):
            self.assertEqual(main.folder_dialog_type(), 20)
        with mock.patch.object(main, 'webview', types.SimpleNamespace(FOLDER_DIALOG=20)):  # pywebview 5.x
            self.assertEqual(main.folder_dialog_type(), 20)

    @unittest.skipUnless(hasattr(main.webview, 'FileDialog'), 'pywebview 6+ not installed')
    def test_installed_pywebview_gives_no_deprecation_warning(self):
        with self.assertNoLogs('pywebview', level='WARNING'):
            self.assertEqual(int(main.folder_dialog_type()), 20)


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
        on_disk = sum(len(files) for _, _, files in os.walk(self.in_dir))
        self.assertEqual(on_disk, len(self.rels) + 1)
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
        # The names first, so a failure elsewhere does not hide them.
        started = [args for fn, args in calls if fn == 'triggerFileStart']
        for rel in self.rels:
            with self.subTest(rel=rel):
                self.assertIn([rel, rel], started)
                out = self.out_dir / rel
                self.assertTrue(out.is_file(), rel)
                self.assertGreater(wav_data_bytes(out), 0)
        errors = [args for fn, args in calls if fn == 'triggerError']
        self.assertEqual(errors, [])
        self.assertNotIn('triggerFileFailed', fns)
        self.assertEqual(fns[-1], 'triggerAllDone')
        self.assertTrue(all(a[0] == a[1] for a in started))
        self.assertNotIn("._07 Johnny Don't Go.wav", [a[0] for a in started])
        self.assertEqual(sorted(a[0] for a in started), sorted(self.rels))
        self.assertEqual(calls[0], ('triggerBatchStart', [len(self.rels)]))
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
        # loudnorm analysis + render. Two-pass needs verboseLogs (FFmpeg prints
        # the measurement at -v info only).
        w = self.run_batch({'normMode': 'lufs', 'verboseLogs': True, 'targetBitDepth': 'original'})
        self.check_batch(w)
        measured = {args[0] for fn, args in map(parse_call, w.scripts)
                    if fn == 'triggerLog' and args[1] == 'analyze' and args[2].startswith('LUFS measured: ')}
        # Every file got two-pass loudnorm, including names with a lone '{' or '}'.
        self.assertEqual(sorted(measured), sorted(self.rels))

    def test_batch_into_an_output_folder_inside_the_input_folder(self):
        # "Music" -> "Music/normalized": allowed by the UI when it is empty.
        self.out_dir = self.in_dir / 'normalized #1 ö'
        self.out_dir.mkdir()
        self.check_batch(self.run_batch({}))
        self.assertFalse((self.out_dir / 'normalized #1 ö').exists())

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
