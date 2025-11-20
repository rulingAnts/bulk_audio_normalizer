"""
Flask API backend for the Bulk Audio Normalizer.

Provides REST API endpoints that replace Electron IPC.
"""
import os
import logging
import threading
from pathlib import Path
from typing import Dict, List
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from .audio_processor import normalize_file, get_duration_seconds
from .process_manager import process_manager
from .ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global state
processing_state = {
    'running': False,
    'files': {},  # file_id -> status
    'settings': {},
    'callbacks': {}  # For WebSocket-like updates (stored by main.py)
}


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


@app.route('/api/ffmpeg-info', methods=['GET'])
def ffmpeg_info():
    """Get FFmpeg/FFprobe binary paths."""
    try:
        ffmpeg = get_ffmpeg_path()
        ffprobe = get_ffprobe_path()
        return jsonify({
            'ffmpegPath': ffmpeg,
            'ffprobePath': ffprobe,
            'ffmpegExists': os.path.exists(ffmpeg),
            'ffprobeExists': os.path.exists(ffprobe)
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'ffmpegPath': None,
            'ffprobePath': None,
            'ffmpegExists': False,
            'ffprobeExists': False
        }), 500


@app.route('/api/scan-files', methods=['POST'])
def scan_files():
    """
    Scan input directory for WAV files.
    
    Request body:
        {
            "inputPath": "/path/to/input"
        }
    
    Response:
        {
            "files": ["file1.wav", "file2.wav", ...]
        }
    """
    data = request.json
    input_path = data.get('inputPath')
    
    if not input_path or not os.path.isdir(input_path):
        return jsonify({'error': 'Invalid input path'}), 400
        
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
    return jsonify({'files': wav_files})


@app.route('/api/check-output-empty', methods=['POST'])
def check_output_empty():
    """
    Check if output directory is empty.
    
    Request body:
        {
            "outputPath": "/path/to/output"
        }
    
    Response:
        {
            "isEmpty": true/false
        }
    """
    data = request.json
    output_path = data.get('outputPath')
    
    if not output_path or not os.path.exists(output_path):
        return jsonify({'isEmpty': True})
        
    try:
        items = [f for f in os.listdir(output_path) if not f.startswith('.')]
        return jsonify({'isEmpty': len(items) == 0})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/create-output-dir', methods=['POST'])
def create_output_dir():
    """
    Create output directory if it doesn't exist.
    
    Request body:
        {
            "outputPath": "/path/to/output"
        }
    """
    data = request.json
    output_path = data.get('outputPath')
    
    if not output_path:
        return jsonify({'error': 'No output path provided'}), 400
        
    try:
        os.makedirs(output_path, exist_ok=True)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/process-batch', methods=['POST'])
def process_batch():
    """
    Start batch processing.
    
    Request body:
        {
            "inputPath": "/path/to/input",
            "outputPath": "/path/to/output",
            "settings": {...}
        }
    """
    data = request.json
    input_path = data.get('inputPath')
    output_path = data.get('outputPath')
    settings = data.get('settings', {})
    
    if not input_path or not output_path:
        return jsonify({'error': 'Missing paths'}), 400
        
    processing_state['running'] = True
    processing_state['settings'] = settings
    
    # Start processing in background thread
    thread = threading.Thread(
        target=_process_batch_worker,
        args=(input_path, output_path, settings)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True})


def _process_batch_worker(input_path: str, output_path: str, settings: Dict):
    """Worker thread for batch processing."""
    try:
        # Scan for files
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
        
        # Process each file
        total = len(wav_files)
        completed = 0
        
        for file_path in wav_files:
            if not processing_state['running']:
                break
                
            try:
                # Generate output path
                rel_path = os.path.relpath(file_path, input_path)
                out_path = os.path.join(output_path, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                
                file_id = os.path.basename(file_path)
                
                def progress_cb(job_id, phase, status, pct):
                    # Send progress update via callback
                    if 'progress_callback' in processing_state['callbacks']:
                        processing_state['callbacks']['progress_callback'](
                            job_id, phase, status, pct
                        )
                        
                def log_cb(job_id, phase, message):
                    # Send log update via callback
                    if 'log_callback' in processing_state['callbacks']:
                        processing_state['callbacks']['log_callback'](
                            job_id, phase, message
                        )
                        
                normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)
                completed += 1
                
                # Send completion update
                if 'completion_callback' in processing_state['callbacks']:
                    processing_state['callbacks']['completion_callback'](
                        completed, total
                    )
                    
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
                if 'error_callback' in processing_state['callbacks']:
                    processing_state['callbacks']['error_callback'](file_path, str(e))
                break
                
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
    finally:
        processing_state['running'] = False


@app.route('/api/cancel-batch', methods=['POST'])
def cancel_batch():
    """Cancel batch processing."""
    processing_state['running'] = False
    process_manager.kill_all()
    return jsonify({'success': True})


@app.route('/api/reveal-file', methods=['POST'])
def reveal_file():
    """
    Reveal file in file manager.
    
    Request body:
        {
            "filePath": "/path/to/file"
        }
    """
    import subprocess
    import platform
    
    data = request.json
    file_path = data.get('filePath')
    
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 400
        
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.Popen(['open', '-R', file_path])
        elif system == 'Windows':
            subprocess.Popen(['explorer', '/select,', file_path])
        else:  # Linux
            # Try to open containing directory
            subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/start-preview', methods=['POST'])
def start_preview():
    """
    Start preview processing.
    
    Request body:
        {
            "inputPath": "/path/to/input",
            "settings": {...},
            "sampleSize": 5,
            "concurrency": 2
        }
    
    Response:
        {
            "ok": true,
            "tmpBase": "/tmp/preview-xxx"
        }
    """
    import tempfile
    import random
    
    data = request.json
    input_path = data.get('inputPath')
    settings = data.get('settings', {})
    sample_size = min(50, max(1, data.get('sampleSize', 5)))
    concurrency = min(2, data.get('concurrency', 2))
    
    if not input_path or not os.path.isdir(input_path):
        return jsonify({'ok': False, 'error': 'Invalid input path'}), 400
        
    # Scan for WAV files
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
    
    if not wav_files:
        return jsonify({'ok': False, 'error': 'No WAV files found for preview.'})
        
    # Random sample
    sample = random.sample(wav_files, min(sample_size, len(wav_files)))
    
    # Create temp directory
    tmp_base = tempfile.mkdtemp(prefix='ban-preview-')
    
    # Store preview state
    processing_state['preview_running'] = True
    processing_state['preview_tmp'] = tmp_base
    
    # Start preview processing in background
    thread = threading.Thread(
        target=_preview_worker,
        args=(sample, tmp_base, input_path, settings)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'ok': True, 'tmpBase': tmp_base})


def _preview_worker(files: List[str], tmp_base: str, input_base: str, settings: Dict):
    """Worker thread for preview processing."""
    try:
        for idx, file_path in enumerate(files):
            if not processing_state.get('preview_running', False):
                break
                
            try:
                # Generate output path
                rel_path = os.path.relpath(file_path, input_base)
                out_path = os.path.join(tmp_base, rel_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                
                file_id = f"preview_{idx}"
                
                def progress_cb(job_id, phase, status, pct):
                    pass  # Preview doesn't need progress updates
                    
                def log_cb(job_id, phase, message):
                    pass  # Preview doesn't need logs
                    
                normalize_file(file_path, out_path, settings, file_id, progress_cb, log_cb)
                
                # Send completion to preview window
                if 'preview_file_callback' in processing_state['callbacks']:
                    processing_state['callbacks']['preview_file_callback'](
                        file_path, out_path, rel_path, tmp_base
                    )
                    
            except Exception as e:
                logger.error(f"Preview failed for {file_path}: {e}")
                
        # Send completion
        if 'preview_done_callback' in processing_state['callbacks']:
            processing_state['callbacks']['preview_done_callback'](
                len(files), tmp_base
            )
            
    except Exception as e:
        logger.error(f"Preview worker error: {e}")
    finally:
        processing_state['preview_running'] = False


# Serve frontend files
@app.route('/')
def index():
    """Serve index.html."""
    return send_from_directory('../frontend', 'index.html')


@app.route('/<path:path>')
def serve_frontend(path):
    """Serve frontend static files."""
    return send_from_directory('../frontend', path)


def set_callbacks(progress_cb, log_cb, completion_cb, error_cb, preview_file_cb=None, preview_done_cb=None):
    """Set callbacks for processing updates."""
    processing_state['callbacks'] = {
        'progress_callback': progress_cb,
        'log_callback': log_cb,
        'completion_callback': completion_cb,
        'error_callback': error_cb,
        'preview_file_callback': preview_file_cb,
        'preview_done_callback': preview_done_cb
    }
