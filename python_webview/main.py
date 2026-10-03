#!/usr/bin/env python3
"""
Main entry point for the Python WebView version of Bulk Audio Normalizer.

This replaces Electron with pywebview (no HTTP server needed).
Uses pywebview's JS API bridge for direct Python<->JavaScript communication.
"""
import os
import sys
import json
import ntpath
import logging
import threading
import tempfile
import random
import shutil
import webview
from pathlib import Path
from typing import Dict, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.audio_processor import normalize_file, get_duration_seconds
from backend.process_manager import process_manager
from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global state
preview_window = None
main_window = None
processing_state = {
    'running': False,
    'paused': False,
    'preview_running': False,
    'files': {},
    'settings': {},
    'processed_files': set(),  # Track completed files for resume
    'total_files': 0
}


def js_call(window, fn: str, *args) -> None:
    """
    Call ``window.<fn>(*args)`` in a webview window.

    Each argument is encoded with json.dumps, so any Python str, int, float,
    bool or None arrives in JavaScript with the same value and type. File
    names with quotes, Windows paths with backslashes, newlines, U+2028 and
    emoji are all safe; the default ensure_ascii=True also keeps the whole
    script ASCII. Never build these calls by pasting values into a quoted JS
    string by hand: an apostrophe ("Don't") or a backslash sequence
    (C:\\x...) breaks the literal (issue #2).

    A failed UI update is logged and swallowed: it must never stop audio
    processing.
    """
    if window is None:
        return
    try:
        script = f"window.{fn}({', '.join(json.dumps(a) for a in args)})"
        window.evaluate_js(script)
    except Exception as e:
        logger.warning(f"UI update {fn} failed: {e}")


APPLEDOUBLE_MAGIC = b'\x00\x05\x16\x07'


def is_appledouble(path: str) -> bool:
    """
    True for a macOS AppleDouble metadata file such as "._07 Song.wav".

    macOS writes one next to every file it copies to a FAT/exFAT/network
    drive. Windows shows them, they end in .wav, but they hold Finder
    metadata, not audio, so FFmpeg can only fail on them. Both the "._"
    prefix and the AppleDouble magic number must match, so a real
    recording whose name merely starts with "._" is still processed.
    """
    if not os.path.basename(path).startswith('._'):
        return False
    try:
        with open(path, 'rb') as f:
            return f.read(4) == APPLEDOUBLE_MAGIC
    except OSError:
        return False


def reveal_command(file_path: str, system: str):
    """
    The command that shows file_path selected in the OS file manager.

    A list is run without a shell, so any character in the name is passed
    as is. Explorer is the exception: it parses its own command line and
    treats commas as separators, while Popen only quotes list items that
    contain a space or tab, so a name like "Take1,Tom.wav" reached Explorer
    unquoted. It gets one string instead, with the whole path in double
    quotes. Windows names cannot contain '"', and Popen hands a string to
    CreateProcess unchanged.
    """
    if system == 'Darwin':
        return ['open', '-R', file_path]
    if system == 'Windows':
        return f'explorer /select,"{ntpath.normpath(file_path)}"'
    return ['xdg-open', os.path.dirname(file_path)]


def reveal_in_file_manager(file_path) -> bool:
    """Show a file or folder in Finder / Explorer / the Linux file manager."""
    import subprocess
    import platform

    if not file_path or not os.path.exists(file_path):
        return False
    try:
        subprocess.Popen(reveal_command(file_path, platform.system()))
        return True
    except Exception as e:
        logger.error(f"Failed to reveal path: {e}")
        return False


def subfolder_inside(folder: str, parent: str) -> Optional[str]:
    """
    folder's path relative to parent when folder is inside parent, else None.

    None too when they are the same folder. Links are resolved and names are
    compared the way the OS does (normcase), so "C:\\Music\\Normalized\\" is
    inside "c:\\music". The result is normcased.
    """
    try:
        f = os.path.normcase(os.path.realpath(folder))
        p = os.path.normcase(os.path.realpath(parent))
        if f != p and os.path.commonpath([f, p]) == p:
            return os.path.relpath(f, p)
    except (ValueError, OSError):  # e.g. different drives on Windows
        pass
    return None


def without_output_folder(files: List[str], input_path: str, output_path: str) -> List[str]:
    """
    The scanned input files minus any inside the output folder.

    The UI only refuses an output folder that IS the input folder; an empty
    one inside it ("Music" -> "Music/normalized") is allowed. What is, or
    will be, written there is output, never input.
    """
    sub = subfolder_inside(output_path, input_path) if output_path else None
    if not sub:
        return files
    prefix = sub + os.sep
    kept = []
    for f in files:
        rel = os.path.normcase(os.path.relpath(f, input_path))
        if rel != sub and not rel.startswith(prefix):
            kept.append(f)
    return kept


def not_written_message(rel_paths: List[str], total: int, limit: int = 5) -> str:
    """The end-of-batch error for files FFmpeg could not write, naming a few."""
    names = ', '.join(rel_paths[:limit])
    more = f" and {len(rel_paths) - limit} more" if len(rel_paths) > limit else ''
    return (f"{len(rel_paths)} of {total} files could not be processed: {names}{more}. "
            f"The log shows FFmpeg's message for each one; the other files were written.")


class API:
    """
    API class exposed to JavaScript via pywebview.
    
    All methods are directly callable from JavaScript without HTTP.
    """
    
    def select_folder(self, title='Select Folder'):
        """Show folder selection dialog."""
        result = webview.windows[0].create_file_dialog(
            dialog_type=webview.FOLDER_DIALOG,
            directory='',
            allow_multiple=False
        )
        if result and len(result) > 0:
            return result[0]
        return None
    
    def get_ffmpeg_info(self):
        """Get FFmpeg/FFprobe binary paths and existence."""
        try:
            ffmpeg = get_ffmpeg_path()
            ffprobe = get_ffprobe_path()
            return {
                'ffmpegPath': ffmpeg,
                'ffprobePath': ffprobe,
                'ffmpegExists': os.path.exists(ffmpeg),
                'ffprobeExists': os.path.exists(ffprobe)
            }
        except Exception as e:
            logger.error(f"FFmpeg info error: {e}")
            return {
                'error': str(e),
                'ffmpegPath': None,
                'ffprobePath': None,
                'ffmpegExists': False,
                'ffprobeExists': False
            }
    
    def scan_files(self, input_path):
        """Scan input directory for WAV files."""
        if not input_path or not os.path.isdir(input_path):
            return []
            
        wav_files = []
        
        def walk_dir(dirpath):
            try:
                for entry in os.scandir(dirpath):
                    if entry.is_dir(follow_symlinks=False):
                        walk_dir(entry.path)
                    elif entry.is_file() and entry.name.lower().endswith(('.wav', '.wave')):
                        if is_appledouble(entry.path):
                            logger.info(f"Skipping macOS metadata file: {entry.path}")
                            continue
                        wav_files.append(entry.path)
            except PermissionError:
                pass
                
        walk_dir(input_path)
        return wav_files
    
    def validate_output_empty(self, output_path):
        """Check if output directory is empty."""
        if not output_path or not os.path.exists(output_path):
            return True
            
        try:
            items = [f for f in os.listdir(output_path) if not f.startswith('.')]
            return len(items) == 0
        except Exception:
            return False
    
    def clear_output_folder(self, output_path):
        """Delete all contents of output folder."""
        if not output_path or not os.path.exists(output_path):
            return False
            
        try:
            for item in os.listdir(output_path):
                if item.startswith('.'):
                    continue
                item_path = os.path.join(output_path, item)
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            return True
        except Exception as e:
            logger.error(f"Failed to clear output folder: {e}")
            return False
    
    def start_processing(self, input_path, output_path, settings):
        """Start batch processing."""
        global main_window
        
        logger.info("="*80)
        logger.info("START_PROCESSING CALLED")
        logger.info(f"  input_path: {input_path}")
        logger.info(f"  output_path: {output_path}")
        logger.info(f"  settings: {settings}")
        logger.info(f"  main_window: {'SET' if main_window else 'NOT SET'}")
        
        if not input_path or not output_path:
            logger.error("Missing paths!")
            return {'ok': False, 'error': 'Missing paths'}
        
        # Reset processing state for new batch
        processing_state['running'] = True
        processing_state['paused'] = False
        processing_state['processed_files'].clear()
        processing_state['total_files'] = 0
        processing_state['settings'] = settings
        
        logger.info("Starting background thread...")
        # Start processing in background thread
        thread = threading.Thread(
            target=self._process_batch_worker,
            args=(input_path, output_path, settings)
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Background thread started: {thread.name}")
        logger.info("="*80)
        return {'ok': True}
    
    def cancel_processing(self):
        """Cancel batch processing."""
        processing_state['running'] = False
        processing_state['paused'] = False
        processing_state['processed_files'].clear()
        process_manager.kill_all()
        return {'ok': True}
    
    def pause_processing(self):
        """Pause batch processing."""
        logger.info("Pausing batch processing...")
        processing_state['paused'] = True
        process_manager.kill_all()  # Stop current FFmpeg processes
        return {'ok': True}
    
    def resume_processing(self):
        """Resume paused batch processing."""
        logger.info("Resuming batch processing...")
        processing_state['paused'] = False
        return {'ok': True}
    
    def start_preview(self, input_path, settings, sample_size=5, concurrency=2):
        """Start preview processing."""
        logger.info("="*80)
        logger.info("START_PREVIEW CALLED")
        logger.info(f"  input_path: {input_path}")
        logger.info(f"  sample_size: {sample_size}")
        logger.info(f"  settings: {settings}")
        
        if not input_path or not os.path.isdir(input_path):
            logger.error(f"Invalid input path: {input_path}")
            return {'ok': False, 'error': 'Invalid input path'}
        
        # Clean up old preview folders
        logger.info("Cleaning up old preview folders...")
        try:
            import tempfile
            temp_dir = tempfile.gettempdir()
            for item in os.listdir(temp_dir):
                if item.startswith('ban-preview-'):
                    old_preview = os.path.join(temp_dir, item)
                    try:
                        shutil.rmtree(old_preview)
                        logger.info(f"  Deleted old preview: {old_preview}")
                    except Exception as e:
                        logger.warning(f"  Could not delete {old_preview}: {e}")
        except Exception as e:
            logger.warning(f"Error cleaning up old previews: {e}")
            
        # Scan for WAV files
        wav_files = self.scan_files(input_path)
        
        logger.info(f"Found {len(wav_files)} WAV files for preview")
        
        if not wav_files:
            return {'ok': False, 'error': 'No WAV files found for preview'}
            
        # Random sample
        sample_size = min(50, max(1, sample_size))
        sample = random.sample(wav_files, min(sample_size, len(wav_files)))
        
        logger.info(f"Selected {len(sample)} files for preview")
        
        # Create temp directory
        tmp_base = tempfile.mkdtemp(prefix='ban-preview-')
        
        logger.info(f"Created temp directory: {tmp_base}")
        
        # Store preview state
        processing_state['preview_running'] = True
        processing_state['preview_tmp'] = tmp_base
        
        # Start preview processing in background
        thread = threading.Thread(
            target=self._preview_worker,
            args=(sample, tmp_base, input_path, settings)
        )
        thread.daemon = True
        thread.start()
        
        logger.info("Preview worker thread started")
        
        return {'ok': True, 'tmpBase': tmp_base}
        
    def reveal_path(self, file_path):
        """Reveal file in file manager."""
        return reveal_in_file_manager(file_path)
    
    def _process_batch_worker(self, input_path: str, output_path: str, settings: Dict):
        """Worker thread for batch processing."""
        global main_window
        
        try:
            logger.info(f"Batch worker started: input_path={input_path}, output_path={output_path}")
            
            # Scan for files (never inside an output folder that sits in the input folder)
            wav_files = without_output_folder(self.scan_files(input_path), input_path, output_path)
            logger.info(f"Found {len(wav_files)} WAV files")
            
            # Filter out already processed files (for resume)
            if processing_state['processed_files']:
                unprocessed = [f for f in wav_files if f not in processing_state['processed_files']]
                logger.info(f"Resuming: {len(unprocessed)} files remaining (already processed: {len(processing_state['processed_files'])})")
                wav_files = unprocessed
            
            # Check if there are files to process
            if not wav_files:
                logger.warning("No files to process (all may have been processed already)")
                js_call(main_window, 'triggerAllDone')
                return
            
            # Process each file
            total = processing_state.get('total_files', 0)
            if not total or total == 0:
                total = len(wav_files)
                processing_state['total_files'] = total
            
            completed = len(processing_state['processed_files'])
            # Set when a file fails: the user has already been sent
            # triggerError, so the batch must not then report "Completed".
            failed = False
            # Files FFmpeg could not write. The batch carries on with the
            # rest and reports these at the end instead of "Completed".
            not_written = []

            # Trigger batch start event
            logger.info(f"Triggering batch start event with {total} files (starting at {completed})")
            js_call(main_window, 'triggerBatchStart', total)

            for file_path in wav_files:
                # Check for stop
                if not processing_state['running']:
                    logger.info("Processing stopped by user")
                    js_call(main_window, 'triggerStopped')
                    break
                
                # Check for pause
                while processing_state['paused']:
                    if not processing_state['running']:  # Stop requested during pause
                        break
                    import time
                    time.sleep(0.5)
                
                if not processing_state['running']:
                    break
                    
                try:
                    # Generate output path
                    rel_path = os.path.relpath(file_path, input_path)
                    out_path = os.path.join(output_path, rel_path)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    
                    # The relative path, not the bare name: "A/01.wav" and
                    # "B/01.wav" are different files and need their own row.
                    # It is the exact native string; js_call delivers it as is.
                    file_id = rel_path
                    file_name = rel_path
                    
                    logger.info(f"Processing file {completed + 1}/{total}: {file_name}")
                    
                    # Trigger file start event
                    js_call(main_window, 'triggerFileStart', file_id, file_name)

                    def progress_cb(job_id, phase, status, pct):
                        js_call(main_window, 'triggerPhaseEvent', job_id, phase, status, pct)

                    def log_cb(job_id, phase, message):
                        js_call(main_window, 'triggerLog', job_id, phase, message)

                    ok = normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)

                    # Mark file as processed
                    processing_state['processed_files'].add(file_path)
                    completed += 1

                    if ok is False:
                        not_written.append(rel_path)
                        logger.error(f"FFmpeg could not write: {file_name} ({completed}/{total})")
                        js_call(main_window, 'triggerFileFailed', file_id)
                    else:
                        logger.info(f"File complete: {file_name} ({completed}/{total})")
                        js_call(main_window, 'triggerFileDone', file_id)

                    # Send progress update
                    overall_pct = round((completed / total) * 100, 2)  # Keep as float
                    js_call(main_window, 'triggerProgress', file_id, 100, overall_pct, completed, total)

                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    failed = True
                    js_call(main_window, 'triggerError',
                            f"Failed to process {os.path.relpath(file_path, input_path)}: {e}")
                    break

            if failed:
                logger.info(f"Batch stopped after an error: {completed}/{total} files processed")
            # Processing complete - verify all files
            elif processing_state['running'] and not processing_state['paused']:
                logger.info(f"Batch processing complete: {completed}/{total} files")
                logger.info("Verifying output files...")
                
                # Verify the files this batch set out to process (not a rescan:
                # the outputs may now be inside the input folder).
                batch_files = sorted(set(wav_files) | processing_state['processed_files'])
                verification_results = self._verify_batch_output(input_path, output_path, batch_files)
                problems = sorted(set(not_written) | set(verification_results['missing_files']))

                if problems:
                    logger.error(f"✗ Verification failed: {len(problems)} files not written")
                    js_call(main_window, 'triggerError', not_written_message(problems, total))
                else:
                    logger.info(f"✓ Verification passed: {verification_results['matched']} files processed")
                    js_call(main_window, 'triggerAllDone')

        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            js_call(main_window, 'triggerError', str(e))
        finally:
            if not processing_state['paused']:
                processing_state['running'] = False
                processing_state['processed_files'].clear()
                processing_state['total_files'] = 0
    
    def _verify_batch_output(self, input_path: str, output_path: str, input_files: List[str]) -> Dict:
        """
        Check that each of input_files has a non-empty output file.

        input_files are the files the batch processed. The input folder is
        not scanned again: an output folder inside it would by now hold the
        outputs, and they would be taken for inputs without outputs.

        Until v2.0.2 this imported a get_audio_info that never existed, so
        the ImportError was swallowed and verification passed without
        checking anything.
        """
        results = {'matched': 0, 'missing': 0, 'missing_files': []}
        try:
            for input_file in input_files:
                rel_path = os.path.relpath(input_file, input_path)
                output_file = os.path.join(output_path, rel_path)
                try:
                    written = os.path.getsize(output_file) > 0
                except OSError:
                    written = False
                if written:
                    results['matched'] += 1
                else:
                    logger.error(f"Missing output file: {rel_path}")
                    results['missing'] += 1
                    results['missing_files'].append(rel_path)
        except Exception as e:
            logger.error(f"Verification error: {e}")
        return results

    def _preview_worker(self, files: List[str], tmp_base: str, input_base: str, settings: Dict):
        """Worker thread for preview processing."""
        global preview_window
        
        logger.info(f"Preview worker starting: {len(files)} files to process")
        logger.info(f"Preview temp directory: {tmp_base}")
        logger.info(f"Input base: {input_base}")
        
        try:
            for idx, file_path in enumerate(files):
                if not processing_state.get('preview_running', False):
                    logger.info("Preview canceled by user")
                    break
                    
                try:
                    logger.info(f"Processing preview file {idx+1}/{len(files)}: {file_path}")
                    
                    # Generate output path
                    rel_path = os.path.relpath(file_path, input_base)
                    out_path = os.path.join(tmp_base, rel_path)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                    
                    logger.info(f"Output path: {out_path}")
                    
                    file_id = f"preview_{idx}"
                    
                    def progress_cb(job_id, phase, status, pct):
                        logger.debug(f"Preview {job_id} {phase}: {status} {pct}%")
                        
                    def log_cb(job_id, phase, message):
                        logger.debug(f"Preview {job_id} {phase}: {message}")
                    
                    logger.info(f"Calling normalize_file for {file_id}...")
                    ok = normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)
                    logger.info(f"normalize_file completed for {file_id}")

                    # Verify output file was created
                    if ok is False or not os.path.exists(out_path):
                        logger.error(f"Output file not created: {out_path}")
                        continue
                    
                    out_size = os.path.getsize(out_path)
                    logger.info(f"Output file created: {out_path} ({out_size} bytes)")
                    
                    # Send completion to preview window. The exact native
                    # paths go across (js_call JSON-encodes them), so the
                    # preview window can hand them straight back to
                    # get_audio_file and reveal_path.
                    if preview_window:
                        js_call(preview_window, 'triggerPreviewFile',
                                file_path, out_path, rel_path, tmp_base)
                    else:
                        logger.warning("Preview window is None, cannot send update")
                        
                except Exception as e:
                    logger.error(f"Preview failed for {file_path}: {e}", exc_info=True)
                    
            # Send completion
            js_call(preview_window, 'triggerPreviewDone', len(files), tmp_base)
                    
        except Exception as e:
            logger.error(f"Preview worker error: {e}")
        finally:
            processing_state['preview_running'] = False
    
    def open_preview_window(self):
        """Open the preview window."""
        global preview_window
        
        logger.info("open_preview_window called")
        
        # If preview window already exists, check if it's still valid
        if preview_window is not None:
            try:
                # Try to interact with window to see if it's still open
                # If this fails, the window was closed
                if hasattr(preview_window, 'evaluate_js'):
                    logger.info("Preview window already exists and is valid")
                    return True
            except:
                logger.info("Preview window exists but is closed, will create new one")
                preview_window = None
        
        # Create new preview window
        frontend_dir = Path(__file__).parent / 'frontend'
        preview_html = frontend_dir / 'preview.html'
        
        logger.info(f"Checking for preview HTML at: {preview_html}")
        
        if not preview_html.exists():
            logger.error(f"Preview HTML not found: {preview_html}")
            return False
        
        # Create preview API instance
        preview_api = PreviewAPI()
        
        logger.info("Creating preview window...")
        
        # Create window on main thread
        try:
            preview_window = webview.create_window(
                'Preview',
                str(preview_html.absolute()),
                width=900,
                height=700,
                resizable=True,
                js_api=preview_api
            )
            
            # Add event handler to reset preview_window when closed
            def on_closing():
                global preview_window
                logger.info("Preview window closing, resetting preview_window variable")
                preview_window = None
            
            preview_window.events.closing += on_closing
            
            logger.info("Preview window created successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to create preview window: {e}")
            return False


class PreviewAPI:
    """API for the preview window."""
    
    def get_audio_file(self, file_path):
        """Read audio file and return as base64 data URL."""
        import base64
        import mimetypes
        
        if not file_path or not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return None
        
        try:
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'audio/wav'  # Default for WAV files
            
            # Read file
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Convert to base64 data URL
            b64_data = base64.b64encode(data).decode('utf-8')
            data_url = f"data:{mime_type};base64,{b64_data}"
            
            logger.debug(f"Loaded audio file: {file_path} ({len(data)} bytes)")
            return data_url
            
        except Exception as e:
            logger.error(f"Failed to read audio file {file_path}: {e}")
            return None
    
    def reveal_path(self, file_path):
        """Reveal file in file manager."""
        return reveal_in_file_manager(file_path)


def main():
    """Main entry point."""
    global main_window
    
    logger.info("Starting Bulk Audio Normalizer - Python WebView version")
    
    # Check for FFmpeg
    try:
        ffmpeg = get_ffmpeg_path()
        ffprobe = get_ffprobe_path()
        logger.info(f"Using FFmpeg: {ffmpeg}")
        logger.info(f"Using FFprobe: {ffprobe}")
    except Exception as e:
        logger.error(f"FFmpeg not found: {e}")
        logger.error("Please install FFmpeg or run 'npm install' in the parent directory")
    
    # Get frontend directory
    frontend_dir = Path(__file__).parent / 'frontend'
    index_html = frontend_dir / 'index.html'
    
    if not index_html.exists():
        logger.error(f"Frontend not found: {index_html}")
        sys.exit(1)
    
    # Create API instance
    api = API()
    
    # Create main window
    main_window = webview.create_window(
        'Bulk Audio Normalizer',
        str(index_html.absolute()),
        width=1100,
        height=800,
        resizable=True,
        js_api=api
    )
    
    # Start webview
    logger.info("Starting WebView...")
    webview.start(debug=False)
    
    logger.info("Application closed")


if __name__ == '__main__':
    main()
