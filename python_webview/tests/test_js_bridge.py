"""
Tests for the Python -> JavaScript bridge (issue #2).

A file named "07 Johnny Don't Go.wav" stopped the batch: values were pasted
into single-quoted JS string literals by hand, so the apostrophe ended the
literal, evaluate_js raised, and the batch broke out of its loop and then
reported "Completed" anyway.

Run from the repository root:
    python3 -m unittest discover -s python_webview/tests -v

Needs only the standard library. The node checks run when `node` is on PATH;
the end-to-end ffmpeg run happens when the app finds ffmpeg and ffprobe (its
own bin/<platform>/ folder first, then PATH, as in the built app).
"""
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest import mock

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

# main.py imports pywebview (and the backend imports psutil) at module level.
# Neither is needed to test the bridge, so stand in for them when missing.
for _name in ('webview', 'psutil'):
    try:
        __import__(_name)
    except ImportError:
        sys.modules[_name] = types.ModuleType(_name)

import main  # noqa: E402

try:
    from webview.util import escape_string as pywebview_escape_string
except ImportError:
    pywebview_escape_string = None


def wrap_like_pywebview(script: str) -> str:
    """The eval("...") wrapper pywebview's Window.evaluate_js puts around a script."""
    if pywebview_escape_string is not None:
        escaped = pywebview_escape_string(script)
    else:  # copy of webview.util.escape_string (pywebview 5.x / 6.x)
        escaped = (script.replace('\\', '\\\\').replace('"', r'\"')
                   .replace('\n', r'\n').replace('\r', r'\r').replace("'", r"\'"))
    return f'eval("{escaped}")'


TRICKY_STRINGS = [
    "07 Johnny Don't Go.wav",
    'He said "hi".wav',
    'a\\u\\x\\0.wav',
    'Rock & Roll 100%.wav',
    'line one\nline two.wav',
    'para\u2028sep.wav',
    'tune \U0001F3B5.wav',
    'Completed: D:\\audio\\upload\\xavier\\x.wav',
    'tab\there\r\n</script>.wav',
    '\udc80 undecodable byte.wav',  # how POSIX shows a non-UTF-8 file name
]

CALL_RE = re.compile(r'^window\.([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$', re.DOTALL)

NODE = shutil.which('node')


def _app_ffmpeg_paths():
    """The ffmpeg/ffprobe the app itself would run, or None."""
    try:
        return main.get_ffmpeg_path(), main.get_ffprobe_path()
    except RuntimeError:
        return None


FFMPEG_PATHS = _app_ffmpeg_paths()
FFMPEG_READY = FFMPEG_PATHS is not None


class FakeWindow:
    """Records every script handed to evaluate_js."""

    def __init__(self):
        self.scripts = []

    def evaluate_js(self, script):
        self.scripts.append(script)


class RaisingWindow(FakeWindow):
    """Like pywebview when the page throws: evaluate_js raises."""

    def evaluate_js(self, script):
        self.scripts.append(script)
        raise RuntimeError('JavascriptException: SyntaxError')


def parse_call(script):
    """Split 'window.fn(a, b)' into ('fn', [a, b]) by reading the args as JSON."""
    m = CALL_RE.match(script)
    if not m:
        raise AssertionError(f'not a window.<fn>(...) call: {script!r}')
    return m.group(1), json.loads('[' + m.group(2) + ']')


def run_in_node(scripts, wrap=False):
    """
    Evaluate each script in node against stub window.trigger* functions.
    Returns one entry per script: {'ok': True, 'fn': ..., 'args': [...]}
    or {'ok': False, 'error': 'SyntaxError: ...'}.
    """
    sources = [wrap_like_pywebview(s) if wrap else s for s in scripts]
    harness = r"""
const fs = require('fs');
const sources = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
globalThis.window = globalThis;
let last = null;
const names = ['triggerFileStart', 'triggerBatchStart', 'triggerFileDone',
  'triggerFileFailed', 'triggerAllDone', 'triggerStopped', 'triggerError',
  'triggerProgress', 'triggerLog', 'triggerPhaseEvent', 'triggerPreviewFile',
  'triggerPreviewDone', 'triggerUnderTest'];
for (const n of names) {
  window[n] = function () { last = { fn: n, args: Array.from(arguments) }; };
}
const out = [];
for (const src of sources) {
  last = null;
  try {
    (0, eval)(src);
    out.push(last ? { ok: true, fn: last.fn, args: last.args }
                  : { ok: false, error: 'no trigger function was called' });
  } catch (e) {
    out.push({ ok: false, error: String(e) });
  }
}
process.stdout.write(JSON.stringify(out));
"""
    with tempfile.TemporaryDirectory() as tmp:
        src_file = Path(tmp) / 'scripts.json'
        js_file = Path(tmp) / 'harness.js'
        src_file.write_text(json.dumps(sources), encoding='utf-8')
        js_file.write_text(harness, encoding='utf-8')
        proc = subprocess.run([NODE, str(js_file), str(src_file)],
                              capture_output=True, text=True, encoding='utf-8',
                              timeout=60)
    if proc.returncode != 0:
        raise AssertionError(f'node failed: {proc.stderr}')
    return json.loads(proc.stdout)


class JsCallTests(unittest.TestCase):

    def test_call_form_and_round_trip(self):
        for value in TRICKY_STRINGS:
            with self.subTest(value=value):
                w = FakeWindow()
                main.js_call(w, 'triggerLog', value, 'render', value)
                self.assertEqual(len(w.scripts), 1)
                fn, args = parse_call(w.scripts[0])
                self.assertEqual(fn, 'triggerLog')
                self.assertEqual(args, [value, 'render', value])

    def test_script_is_ascii(self):
        w = FakeWindow()
        for value in TRICKY_STRINGS:
            main.js_call(w, 'triggerFileStart', value, value)
        for script in w.scripts:
            self.assertTrue(script.isascii(), script)
            self.assertNotIn('\n', script)

    def test_numbers_stay_numbers(self):
        w = FakeWindow()
        main.js_call(w, 'triggerBatchStart', 3)
        main.js_call(w, 'triggerProgress', "Don't.wav", 100, 33.33, 1, 3)
        main.js_call(w, 'triggerPhaseEvent', "Don't.wav", 'render', 'done', 100)
        main.js_call(w, 'triggerAllDone')
        self.assertEqual(w.scripts[0], 'window.triggerBatchStart(3)')
        self.assertEqual(parse_call(w.scripts[1]), ('triggerProgress', ["Don't.wav", 100, 33.33, 1, 3]))
        _, args = parse_call(w.scripts[1])
        self.assertIsInstance(args[1], int)
        self.assertIsInstance(args[2], float)
        self.assertEqual(parse_call(w.scripts[2])[1][3], 100)
        self.assertEqual(w.scripts[3], 'window.triggerAllDone()')

    def test_evaluate_js_exception_is_swallowed(self):
        w = RaisingWindow()
        with self.assertLogs(main.logger, level='WARNING') as logs:
            result = main.js_call(w, 'triggerPhaseEvent', "07 Johnny Don't Go.wav", 'detect', 'start', 0)
        self.assertIsNone(result)
        self.assertEqual(len(w.scripts), 1)
        self.assertIn('triggerPhaseEvent', logs.output[0])

    def test_unserializable_argument_is_swallowed(self):
        w = FakeWindow()
        with self.assertLogs(main.logger, level='WARNING'):
            main.js_call(w, 'triggerLog', object())
        self.assertEqual(w.scripts, [])

    def test_no_window_is_a_no_op(self):
        self.assertIsNone(main.js_call(None, 'triggerAllDone'))


@unittest.skipUnless(NODE, 'node not on PATH')
class JsCallInNodeTests(unittest.TestCase):
    """Prove the produced scripts are valid JavaScript that delivers the same values."""

    def _scripts_and_expected(self):
        w = FakeWindow()
        expected = []
        for value in TRICKY_STRINGS:
            for fn, args in [
                ('triggerFileStart', [value, value]),
                ('triggerPhaseEvent', [value, 'render', 'done', 100]),
                ('triggerLog', [value, 'render', f'Completed: {value}']),
                ('triggerProgress', [value, 100, 33.33, 1, 3]),
                ('triggerError', [f'Failed to process {value}: boom']),
            ]:
                main.js_call(w, fn, *args)
                expected.append((fn, args))
        main.js_call(w, 'triggerBatchStart', 12)
        expected.append(('triggerBatchStart', [12]))
        main.js_call(w, 'triggerAllDone')
        expected.append(('triggerAllDone', []))
        return w.scripts, expected

    def _check(self, wrap):
        scripts, expected = self._scripts_and_expected()
        results = run_in_node(scripts, wrap=wrap)
        self.assertEqual(len(results), len(expected))
        for script, result, (fn, args) in zip(scripts, results, expected):
            with self.subTest(script=script):
                self.assertTrue(result['ok'], result.get('error'))
                self.assertEqual(result['fn'], fn)
                self.assertEqual(result['args'], args)

    def test_scripts_are_valid_js(self):
        self._check(wrap=False)

    def test_scripts_survive_pywebview_eval_wrapper(self):
        self._check(wrap=True)

    def test_old_hand_escaped_form_was_broken(self):
        """Control: the pre-fix progress call really is a SyntaxError for the issue's file."""
        job_id = "07 Johnny Don't Go.wav"
        old = f"window.triggerPhaseEvent('{job_id}', 'detect', 'start', 0)"
        old_log = "window.triggerLog('x.wav', 'render', 'Completed: D:\\audio\\upload\\xavier\\x.wav')"
        for wrap in (False, True):
            results = run_in_node([old, old_log], wrap=wrap)
            self.assertFalse(results[0]['ok'])
            self.assertIn('SyntaxError', results[0]['error'])
            self.assertFalse(results[1]['ok'])
            self.assertIn('SyntaxError', results[1]['error'])


def write_wav(path, seconds=0.5, rate=16000):
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b''.join(
            struct.pack('<h', int(8000 * math.sin(2 * math.pi * 440 * i / rate)))
            for i in range(int(seconds * rate))
        )
        w.writeframes(frames)


class BatchWorkerTests(unittest.TestCase):
    """Drive API._process_batch_worker with a fake window and a fake normalize_file."""

    NAMES = ['01 plain.wav', "07 Johnny Don't Go.wav", '09 last.wav']

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.in_dir = Path(self.tmp.name) / 'in'
        self.out_dir = Path(self.tmp.name) / 'out'
        self.in_dir.mkdir()
        self.out_dir.mkdir()
        for name in self.NAMES:
            (self.in_dir / name).write_bytes(b'RIFF')
        self.saved_window = main.main_window
        self.addCleanup(setattr, main, 'main_window', self.saved_window)

    def run_worker(self, window, fake_normalize):
        main.main_window = window
        main.processing_state['running'] = True
        main.processing_state['paused'] = False
        main.processing_state['processed_files'].clear()
        main.processing_state['total_files'] = 0
        with mock.patch.object(main, 'normalize_file', side_effect=fake_normalize) as nf:
            main.API()._process_batch_worker(str(self.in_dir), str(self.out_dir), {})
        self.assertFalse(main.processing_state['running'])
        return nf

    @staticmethod
    def fake_success(input_path, output_path, settings, job_id, progress_cb, log_cb):
        progress_cb(job_id, 'detect', 'start', 0)
        progress_cb(job_id, 'detect', 'done', 100)
        log_cb(job_id, 'analyze', 'Peak mode: measuredMax=-12.0 dB, target=-2 dB')
        Path(output_path).write_bytes(b'RIFF')
        progress_cb(job_id, 'render', 'done', 100)
        # What audio_processor logs on Windows, backslashes and all
        log_cb(job_id, 'render', f'Completed: D:\\audio\\upload\\xavier\\{job_id}')

    def fns(self, window):
        return [parse_call(s)[0] for s in window.scripts]

    def test_apostrophe_file_completes_batch(self):
        w = FakeWindow()
        nf = self.run_worker(w, self.fake_success)
        self.assertEqual(nf.call_count, len(self.NAMES))
        fns = self.fns(w)
        self.assertEqual(fns[0], 'triggerBatchStart')
        self.assertEqual(fns[-1], 'triggerAllDone')
        self.assertNotIn('triggerError', fns)
        started = [parse_call(s)[1] for s in w.scripts if s.startswith('window.triggerFileStart(')]
        self.assertIn(["07 Johnny Don't Go.wav", "07 Johnny Don't Go.wav"], started)
        logs = [parse_call(s)[1] for s in w.scripts if s.startswith('window.triggerLog(')]
        self.assertIn(["07 Johnny Don't Go.wav", 'render',
                       "Completed: D:\\audio\\upload\\xavier\\07 Johnny Don't Go.wav"], logs)
        progress = [parse_call(s)[1] for s in w.scripts if s.startswith('window.triggerProgress(')]
        self.assertEqual([p[3:] for p in progress], [[1, 3], [2, 3], [3, 3]])
        self.assertEqual(progress[-1][2], 100.0)
        if NODE:
            for result in run_in_node(w.scripts, wrap=True):
                self.assertTrue(result['ok'], result.get('error'))

    def test_ui_failures_never_stop_processing(self):
        w = RaisingWindow()
        with self.assertLogs(main.logger, level='WARNING'):
            nf = self.run_worker(w, self.fake_success)
        self.assertEqual(nf.call_count, len(self.NAMES))
        self.assertEqual(len(list(self.out_dir.iterdir())), len(self.NAMES))

    def test_failed_file_does_not_report_completed(self):
        def fake(input_path, output_path, settings, job_id, progress_cb, log_cb):
            if "Don't" in job_id:
                raise RuntimeError('ffmpeg exited with code 1')
            self.fake_success(input_path, output_path, settings, job_id, progress_cb, log_cb)

        w = FakeWindow()
        self.run_worker(w, fake)
        fns = self.fns(w)
        self.assertIn('triggerError', fns)
        self.assertNotIn('triggerAllDone', fns)
        self.assertEqual(fns[-1], 'triggerError')
        _, args = parse_call(w.scripts[-1])
        self.assertIn("07 Johnny Don't Go.wav", args[0])
        self.assertIn('ffmpeg exited with code 1', args[0])


@unittest.skipUnless(FFMPEG_READY, 'the app finds no ffmpeg/ffprobe')
class EndToEndFfmpegTests(unittest.TestCase):
    """Real normalize_file on tiny WAVs whose names broke v2.0.1."""

    def test_real_batch(self):
        names = ["07 Johnny Don't Go.wav", 'He said "hi".wav', 'back\\slash \\u\\x.wav',
                 'Rock & Roll 100%.wav']
        if os.name == 'nt':  # quotes and backslashes are not legal there
            names = ["07 Johnny Don't Go.wav", 'Rock & Roll 100%.wav']
        with tempfile.TemporaryDirectory() as tmp:
            in_dir = Path(tmp) / 'in'
            out_dir = Path(tmp) / 'out'
            in_dir.mkdir()
            out_dir.mkdir()
            for name in names:
                write_wav(in_dir / name)
            saved_window = main.main_window
            w = FakeWindow()
            try:
                main.main_window = w
                main.process_manager.cancel_all = False
                main.processing_state.update(running=True, paused=False, total_files=0)
                main.processing_state['processed_files'].clear()
                main.API()._process_batch_worker(str(in_dir), str(out_dir), {})
            finally:
                main.main_window = saved_window
            fns = [parse_call(s)[0] for s in w.scripts]
            self.assertNotIn('triggerError', fns)
            self.assertEqual(fns[-1], 'triggerAllDone')
            for name in names:
                out = out_dir / name
                self.assertTrue(out.is_file(), name)
                self.assertGreater(out.stat().st_size, 44)
            if NODE:
                for result in run_in_node(w.scripts, wrap=True):
                    self.assertTrue(result['ok'], result.get('error'))


if __name__ == '__main__':
    unittest.main()
