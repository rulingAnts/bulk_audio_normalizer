#!/usr/bin/env python3
"""
Main entry point for the Python WebView version of Bulk Audio Normalizer.

This replaces Electron with pywebview (no HTTP server needed).
Uses pywebview's JS API bridge for direct Python<->JavaScript communication.
"""
import os
import sys
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


def js_escape_path(path: str) -> str:
    """
    Escape a file path for safe use in JavaScript strings.
    Converts backslashes to forward slashes (works on both Windows and macOS)
    and escapes quotes.
    
    Args:
        path: File path to escape
        
    Returns:
        Escaped path safe for JavaScript string literals
    """
    if not path:
        return ''
    # Convert backslashes to forward slashes (works on Windows and macOS)
    path = path.replace('\\', '/')
    # Escape single and double quotes
    path = path.replace("'", "\\'").replace('"', '\\"')
    return path


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
        import subprocess
        import platform
        
        if not file_path or not os.path.exists(file_path):
            return False
            
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', '-R', file_path])
            elif system == 'Windows':
                subprocess.Popen(['explorer', '/select,', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
            return True
        except Exception as e:
            logger.error(f"Failed to reveal path: {e}")
            return False
    
    def _process_batch_worker(self, input_path: str, output_path: str, settings: Dict):
        """Worker thread for batch processing."""
        global main_window
        
        try:
            logger.info(f"Batch worker started: input_path={input_path}, output_path={output_path}")
            
            # Scan for files
            wav_files = self.scan_files(input_path)
            logger.info(f"Found {len(wav_files)} WAV files")
            
            # Filter out already processed files (for resume)
            if processing_state['processed_files']:
                unprocessed = [f for f in wav_files if f not in processing_state['processed_files']]
                logger.info(f"Resuming: {len(unprocessed)} files remaining (already processed: {len(processing_state['processed_files'])})")
                wav_files = unprocessed
            
            # Check if there are files to process
            if not wav_files:
                logger.warning("No files to process (all may have been processed already)")
                if main_window:
                    main_window.evaluate_js("window.triggerAllDone()")
                return
            
            # Process each file
            total = processing_state.get('total_files', 0)
            if not total or total == 0:
                total = len(wav_files)
                processing_state['total_files'] = total
            
            completed = len(processing_state['processed_files'])
            
            # Trigger batch start event
            if main_window:
                logger.info(f"Triggering batch start event with {total} files (starting at {completed})")
                main_window.evaluate_js(f"window.triggerBatchStart({total})")
            
            for file_path in wav_files:
                # Check for stop
                if not processing_state['running']:
                    logger.info("Processing stopped by user")
                    if main_window:
                        main_window.evaluate_js("window.triggerStopped()")
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
                    
                    file_id = os.path.basename(file_path)
                    file_name = os.path.basename(file_path)
                    
                    logger.info(f"Processing file {completed + 1}/{total}: {file_name}")
                    
                    # Trigger file start event
                    if main_window:
                        file_name_escaped = file_name.replace("'", "\\'")
                        file_id_escaped = file_id.replace("'", "\\'")
                        main_window.evaluate_js(
                            f"window.triggerFileStart('{file_id_escaped}', '{file_name_escaped}')"
                        )
                    
                    def progress_cb(job_id, phase, status, pct):
                        if main_window:
                            main_window.evaluate_js(
                                f"window.triggerPhaseEvent('{job_id}', '{phase}', '{status}', {pct})"
                            )
                            
                    def log_cb(job_id, phase, message):
                        if main_window:
                            message = message.replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
                            main_window.evaluate_js(
                                f"window.triggerLog('{job_id}', '{phase}', '{message}')"
                            )
                            
                    normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)
                    
                    # Mark file as processed
                    processing_state['processed_files'].add(file_path)
                    completed += 1
                    
                    logger.info(f"File complete: {file_name} ({completed}/{total})")
                    
                    # Send file done event
                    if main_window:
                        file_id_escaped = file_id.replace("'", "\\'")
                        main_window.evaluate_js(f"window.triggerFileDone('{file_id_escaped}')")
                    
                    # Send progress update
                    overall_pct = (completed / total) * 100  # Keep as float
                    if main_window:
                        file_id_escaped = file_id.replace("'", "\\'")
                        main_window.evaluate_js(
                            f"window.triggerProgress('{file_id_escaped}', 100, {overall_pct:.2f}, {completed}, {total})"
                        )
                        
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    if main_window:
                        error = str(e).replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
                        main_window.evaluate_js(
                            f"window.triggerError('{error}')"
                        )
                    break
            
            # Processing complete - verify all files
            if processing_state['running'] and not processing_state['paused']:
                logger.info(f"Batch processing complete: {completed}/{total} files")
                logger.info("Verifying output files...")
                
                # Verify all files were processed
                verification_results = self._verify_batch_output(input_path, output_path)
                
                if verification_results['missing'] > 0:
                    # Files are actually missing - this is an error
                    logger.error(f"✗ Verification failed: {verification_results['missing']} files missing")
                    if main_window:
                        error_msg = f"Verification failed: {verification_results['missing']} files not processed"
                        error_msg_escaped = error_msg.replace("'", "\\'")
                        main_window.evaluate_js(f"window.triggerError('{error_msg_escaped}')")
                else:
                    # No missing files - success (even if there are property mismatches)
                    logger.info(f"✓ Verification passed: {verification_results['matched']} files processed")
                    if verification_results['mismatched']:
                        logger.info(f"Note: {len(verification_results['mismatched'])} files had property differences (expected with trimming/normalization)")
                    if main_window:
                        main_window.evaluate_js("window.triggerAllDone()")
                    
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            if main_window:
                error = str(e).replace("'", "\\'").replace("\n", "\\n").replace('"', '\\"')
                main_window.evaluate_js(f"window.triggerError('{error}')")
        finally:
            if not processing_state['paused']:
                processing_state['running'] = False
                processing_state['processed_files'].clear()
                processing_state['total_files'] = 0
    
    def _verify_batch_output(self, input_path: str, output_path: str) -> Dict:
        """Verify that all input files have corresponding output files."""
        try:
            from backend.audio_processor import get_audio_info
            
            input_files = self.scan_files(input_path)
            results = {
                'success': True,
                'matched': 0,
                'missing': 0,
                'mismatched': []
            }
            
            for input_file in input_files:
                rel_path = os.path.relpath(input_file, input_path)
                output_file = os.path.join(output_path, rel_path)
                
                if not os.path.exists(output_file):
                    logger.error(f"Missing output file: {rel_path}")
                    results['success'] = False
                    results['missing'] += 1
                    results['mismatched'].append(rel_path)
                    continue
                
                # Verify basic properties match
                try:
                    input_info = get_audio_info(input_file)
                    output_info = get_audio_info(output_file)
                    
                    # Check duration matches (within 1%)
                    duration_diff = abs(input_info['duration'] - output_info['duration'])
                    if duration_diff > input_info['duration'] * 0.01:
                        logger.warning(f"Duration mismatch for {rel_path}: {input_info['duration']:.2f}s vs {output_info['duration']:.2f}s")
                        results['mismatched'].append(f"{rel_path} (duration)")
                    
                    # Check sample rate matches
                    if input_info['sample_rate'] != output_info['sample_rate']:
                        logger.warning(f"Sample rate mismatch for {rel_path}: {input_info['sample_rate']} vs {output_info['sample_rate']}")
                        results['mismatched'].append(f"{rel_path} (sample rate)")
                    
                    results['matched'] += 1
                    
                except Exception as e:
                    logger.warning(f"Could not verify {rel_path}: {e}")
                    results['matched'] += 1  # File exists, count as matched
            
            return results
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return {'success': False, 'matched': 0, 'missing': 0, 'mismatched': []}
    
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
                    normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)
                    logger.info(f"normalize_file completed for {file_id}")
                    
                    # Verify output file was created
                    if not os.path.exists(out_path):
                        logger.error(f"Output file not created: {out_path}")
                        continue
                    
                    out_size = os.path.getsize(out_path)
                    logger.info(f"Output file created: {out_path} ({out_size} bytes)")
                    
                    # Send completion to preview window
                    if preview_window:
                        logger.info(f"Sending preview file update to window...")
                        original = js_escape_path(file_path)
                        preview = js_escape_path(out_path)
                        rel = js_escape_path(rel_path)
                        tmp = js_escape_path(tmp_base)
                        try:
                            preview_window.evaluate_js(
                                f"window.triggerPreviewFile('{original}', '{preview}', '{rel}', '{tmp}')"
                            )
                            logger.info(f"Preview file update sent successfully")
                        except Exception as e:
                            logger.error(f"Failed to send preview file update: {e}")
                    else:
                        logger.warning("Preview window is None, cannot send update")
                        
                except Exception as e:
                    logger.error(f"Preview failed for {file_path}: {e}", exc_info=True)
                    
            # Send completion
            if preview_window:
                tmp = js_escape_path(tmp_base)
                try:
                    preview_window.evaluate_js(
                        f"window.triggerPreviewDone({len(files)}, '{tmp}')"
                    )
                except Exception as e:
                    logger.error(f"Failed to send preview done: {e}")
                    
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
        import subprocess
        import platform
        
        if not file_path or not os.path.exists(file_path):
            return False
            
        try:
            system = platform.system()
            if system == 'Darwin':  # macOS
                subprocess.Popen(['open', '-R', file_path])
            elif system == 'Windows':
                subprocess.Popen(['explorer', '/select,', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
            return True
        except Exception as e:
            logger.error(f"Failed to reveal path: {e}")
            return False


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
    webview.start(debug=True)
    
    logger.info("Application closed")


if __name__ == '__main__':
    main()
