#!/usr/bin/env python3
"""
Main entry point for the Python WebView version of Bulk Audio Normalizer.

This replaces Electron with pywebview and Node.js with Python/Flask.
"""
import os
import sys
import logging
import threading
import webview
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.api import app, set_callbacks

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class API:
    """
    API class exposed to JavaScript via pywebview.
    
    This provides file dialogs and other system integration
    that can't be done via REST API.
    """
    
    def select_folder(self, title='Select Folder'):
        """
        Show folder selection dialog.
        
        Args:
            title: Dialog title
            
        Returns:
            Selected folder path or None
        """
        result = webview.windows[0].create_file_dialog(
            webview.FOLDER_DIALOG,
            directory='',
            allow_multiple=False
        )
        if result and len(result) > 0:
            return result[0]
        return None
        
    def select_file(self, title='Select File', file_types=()):
        """
        Show file selection dialog.
        
        Args:
            title: Dialog title
            file_types: Tuple of file type filters
            
        Returns:
            Selected file path or None
        """
        result = webview.windows[0].create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=False,
            file_types=file_types
        )
        if result and len(result) > 0:
            return result[0]
        return None


def start_flask():
    """Start Flask server in a separate thread."""
    app.run(host='localhost', port=5000, debug=False, use_reloader=False)


def setup_callbacks(window):
    """
    Setup callbacks for processing updates.
    
    These callbacks allow the backend to communicate with the frontend.
    """
    def progress_callback(job_id, phase, status, pct):
        """Send progress update to frontend."""
        window.evaluate_js(
            f"window.triggerPhaseEvent('{job_id}', '{phase}', '{status}', {pct})"
        )
        
    def log_callback(job_id, phase, message):
        """Send log message to frontend."""
        # Escape message for JavaScript
        message = message.replace("'", "\\'").replace("\n", "\\n")
        window.evaluate_js(
            f"window.triggerLog('{job_id}', '{phase}', '{message}')"
        )
        
    def completion_callback(completed, total):
        """Send completion update to frontend."""
        window.evaluate_js(
            f"window.triggerProgress('batch', {completed}, {total})"
        )
        
    def error_callback(file_path, error):
        """Send error to frontend."""
        error = error.replace("'", "\\'").replace("\n", "\\n")
        window.evaluate_js(
            f"window.triggerBatchError('{error}')"
        )
        
    set_callbacks(progress_callback, log_callback, completion_callback, error_callback)


def main():
    """Main entry point."""
    logger.info("Starting Bulk Audio Normalizer - Python WebView version")
    
    # Check for FFmpeg
    try:
        from backend.ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path
        ffmpeg = get_ffmpeg_path()
        ffprobe = get_ffprobe_path()
        logger.info(f"Using FFmpeg: {ffmpeg}")
        logger.info(f"Using FFprobe: {ffprobe}")
    except Exception as e:
        logger.error(f"FFmpeg not found: {e}")
        logger.error("Please install FFmpeg or run 'npm install' in the parent directory")
        # Continue anyway - the UI will show the error
    
    # Start Flask in background
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    # Give Flask time to start
    import time
    time.sleep(1)
    
    # Get frontend directory
    frontend_dir = Path(__file__).parent / 'frontend'
    index_html = frontend_dir / 'index.html'
    
    if not index_html.exists():
        logger.error(f"Frontend not found: {index_html}")
        sys.exit(1)
    
    # Create API instance
    api = API()
    
    # Create window
    window = webview.create_window(
        'Bulk Audio Normalizer',
        f'file://{index_html.absolute()}',
        width=1100,
        height=800,
        resizable=True,
        js_api=api
    )
    
    # Setup callbacks after window is created
    setup_callbacks(window)
    
    # Start webview
    logger.info("Starting WebView...")
    webview.start(debug=False)
    
    logger.info("Application closed")


if __name__ == '__main__':
    main()
