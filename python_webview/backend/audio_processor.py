"""
Audio processing module for normalization, trimming, and analysis.

Implements the same FFmpeg-based processing as the Electron version
but with Python subprocess management.
"""
import os
import re
import json
import struct
import logging
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Callable

from .process_manager import process_manager
from .ffmpeg_paths import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger(__name__)


def parse_ffmpeg_time(time_str: str) -> float:
    """Parse FFmpeg time format HH:MM:SS.xx to seconds."""
    parts = time_str.split(':')
    if len(parts) != 3:
        return 0.0
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def get_duration_seconds(file_path: str, job_id: Optional[str] = None) -> float:
    """
    Get audio duration in seconds.
    Fast path: parse WAV header. Fallback: use ffprobe.
    
    Args:
        file_path: Path to audio file
        job_id: Optional job ID for tracking
        
    Returns:
        Duration in seconds
    """
    # Fast path: parse WAV header
    try:
        with open(file_path, 'rb') as f:
            data = f.read(512 * 1024)  # Read up to 512KB
            
        if len(data) >= 44 and data[0:4] == b'RIFF' and data[8:12] == b'WAVE':
            pos = 12
            byte_rate = 0
            data_size = 0
            
            while pos + 8 <= len(data):
                chunk_id = data[pos:pos+4]
                chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
                next_pos = pos + 8 + chunk_size + (chunk_size % 2)
                
                if chunk_id == b'fmt ':
                    if pos + 8 + 16 <= len(data):
                        byte_rate = struct.unpack('<I', data[pos+16:pos+20])[0]
                elif chunk_id == b'data':
                    data_size = chunk_size
                    break
                    
                pos = next_pos
                
            if byte_rate > 0 and data_size > 0:
                duration = data_size / byte_rate
                if duration > 0:
                    return duration
    except Exception as e:
        logger.debug(f"WAV header parse failed: {e}")
        
    # Fallback: use ffprobe
    try:
        ffprobe = get_ffprobe_path()
        proc = process_manager.spawn(
            [ffprobe, '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', file_path],
            job_id=job_id
        )
        
        stdout, _ = proc.communicate(timeout=10)
        duration = float(stdout.decode().strip())
        return duration if duration > 0 else 0.0
    except Exception as e:
        logger.error(f"Failed to get duration for {file_path}: {e}")
        return 0.0


def get_wav_format_info(file_path: str) -> Optional[Dict]:
    """
    Read WAV header to get bit depth and format.
    
    Args:
        file_path: Path to WAV file
        
    Returns:
        Dict with audioFormat and bitsPerSample, or None
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read(128)
            
        if len(data) < 44 or data[0:4] != b'RIFF' or data[8:12] != b'WAVE':
            return None
            
        pos = 12
        while pos + 8 <= len(data):
            chunk_id = data[pos:pos+4]
            chunk_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            if chunk_id == b'fmt ':
                audio_format = struct.unpack('<H', data[pos+8:pos+10])[0]
                bits_per_sample = struct.unpack('<H', data[pos+22:pos+24])[0]
                return {
                    'audioFormat': audio_format,
                    'bitsPerSample': bits_per_sample
                }
                
            pos = pos + 8 + chunk_size + (chunk_size % 2)
            
        return None
    except Exception as e:
        logger.debug(f"Failed to read WAV format: {e}")
        return None


def choose_output_codec(target_bit_depth, input_fmt: Optional[Dict]) -> str:
    """
    Choose output codec based on target bit depth and input format.
    
    Args:
        target_bit_depth: 16, 24, or 'original'
        input_fmt: Input format dict with audioFormat and bitsPerSample
        
    Returns:
        FFmpeg codec name
    """
    if target_bit_depth == 'original':
        if not input_fmt:
            return 'pcm_s16le'
            
        bits = input_fmt.get('bitsPerSample', 0)
        fmt = input_fmt.get('audioFormat', 1)  # 1=PCM, 3=float
        
        if fmt == 3:  # Float
            if bits >= 64:
                return 'pcm_f64le'
            return 'pcm_f32le'
            
        if bits <= 8:
            return 'pcm_u8'
        elif bits <= 16:
            return 'pcm_s16le'
        elif bits <= 24:
            return 'pcm_s24le'
        elif bits <= 32:
            return 'pcm_s32le'
        return 'pcm_s16le'
        
    target = 24 if target_bit_depth == 24 else 16
    if target == 16:
        return 'pcm_s16le'
        
    # 24-bit: don't up-convert 16-bit
    if input_fmt:
        bits = input_fmt.get('bitsPerSample', 0)
        if bits > 0 and bits <= 16:
            return 'pcm_s16le'
            
    return 'pcm_s24le'


def detect_voice_region(input_path: str, duration_sec: float, settings: Dict,
                       job_id: str, log_callback: Callable) -> Optional[Dict]:
    """
    Detect voice region using FFmpeg silencedetect.
    
    Args:
        input_path: Input file path
        duration_sec: File duration
        settings: Processing settings
        job_id: Job ID
        log_callback: Logging callback
        
    Returns:
        Dict with 'start' and 'end' times, or None
    """
    if process_manager.is_canceled():
        return None
        
    threshold_db = settings.get('trimThresholdDb', -50)
    min_dur_sec = max(0.01, settings.get('trimMinDurationMs', 200) / 1000)
    conservative = settings.get('trimConservative', False)
    use_hpf = settings.get('trimHPF', False)
    
    if conservative:
        threshold_db = min(threshold_db, -60)
        min_dur_sec = max(min_dur_sec, 0.3)
        
    filters = []
    if use_hpf:
        filters.append('highpass=f=80')
    filters.append(f'silencedetect=n={threshold_db}dB:d={min_dur_sec}')
    
    log_callback(job_id, 'trim', f"Detect config: threshold={threshold_db}dB, minDur={min_dur_sec}s, HPF={'on' if use_hpf else 'off'}, conservative={'on' if conservative else 'off'}")
    
    try:
        ffmpeg = get_ffmpeg_path()
        proc = process_manager.spawn(
            [ffmpeg, '-hide_banner', '-nostats', '-v', 'info',
             '-i', input_path, '-af', ','.join(filters),
             '-f', 'null', '-'],
            job_id=job_id
        )
        
        _, stderr = proc.communicate(timeout=120)
        stderr_text = stderr.decode('utf-8', errors='ignore')
        
        # Parse silence_start and silence_end
        silence_intervals = []
        start_pattern = re.compile(r'silence_start: ([0-9.]+)')
        end_pattern = re.compile(r'silence_end: ([0-9.]+)')
        
        starts = [float(m.group(1)) for m in start_pattern.finditer(stderr_text)]
        ends = [float(m.group(1)) for m in end_pattern.finditer(stderr_text)]
        
        # Pair up starts and ends
        for i in range(min(len(starts), len(ends))):
            silence_intervals.append([starts[i], ends[i]])
            
        # Handle case where file ends with silence
        if len(starts) > len(ends):
            silence_intervals.append([starts[-1], duration_sec])
            
        # Merge overlapping intervals
        silence_intervals.sort()
        merged = []
        for start, end in silence_intervals:
            if not merged or start > merged[-1][1]:
                merged.append([start, end])
            else:
                merged[-1][1] = max(merged[-1][1], end)
                
        # Get non-silent intervals
        non_silent = []
        prev = 0
        for start, end in merged:
            if start > prev:
                non_silent.append([prev, start])
            prev = max(prev, end)
        if prev < duration_sec:
            non_silent.append([prev, duration_sec])
            
        if not non_silent:
            return None
            
        voice_start = non_silent[0][0]
        voice_end = non_silent[-1][1]
        
        return {'start': voice_start, 'end': voice_end}
        
    except Exception as e:
        logger.error(f"Voice detection failed: {e}")
        return None


def normalize_file(input_path: str, output_path: str, settings: Dict,
                  job_id: str, progress_callback: Callable, log_callback: Callable) -> None:
    """
    Normalize an audio file with trimming and normalization.
    
    Args:
        input_path: Input file path
        output_path: Output file path
        settings: Processing settings
        job_id: Job ID
        progress_callback: Progress callback(job_id, phase, status, pct)
        log_callback: Log callback(job_id, phase, message)
    """
    if process_manager.is_canceled():
        return
        
    # Get file info
    duration_sec = get_duration_seconds(input_path, job_id)
    input_fmt = get_wav_format_info(input_path)
    out_codec = choose_output_codec(settings.get('targetBitDepth', 16), input_fmt)
    
    norm_mode = settings.get('normMode', 'peak')
    target_lufs = settings.get('lufsTarget', -16)
    target_tp = settings.get('tpMargin', -1.0)
    limiter = settings.get('limiterLimit', 0.97)
    peak_target_db = settings.get('peakTargetDb', -2)
    threads = settings.get('ffmpegThreads', 0)
    fast_normalize = settings.get('fastNormalize', False)
    verbose = settings.get('verboseLogs', False)
    
    # Trimming detection
    progress_callback(job_id, 'detect', 'start', 0)
    seek_start = 0
    seek_end = duration_sec
    
    if settings.get('autoTrim', False):
        min_file_ms = settings.get('trimMinFileMs', 800)
        if duration_sec * 1000 >= min_file_ms:
            region = detect_voice_region(input_path, duration_sec, settings, job_id, log_callback)
            if region:
                pad_sec = settings.get('trimPadMs', 800) / 1000
                seek_start = max(0, region['start'] - pad_sec)
                seek_end = min(duration_sec, region['end'] + pad_sec)
                log_callback(job_id, 'trim', f"Trim applied: start={seek_start:.3f}s end={seek_end:.3f}s")
            else:
                log_callback(job_id, 'trim', "No trimming applied: could not detect non-silent region")
        else:
            log_callback(job_id, 'trim', f"No trimming applied: file shorter than minimum {min_file_ms}ms")
            
    progress_callback(job_id, 'detect', 'done', 100)
    
    if process_manager.is_canceled():
        return
        
    # Analysis pass
    progress_callback(job_id, 'analyze', 'start', 0)
    
    seek_args = []
    if seek_start > 0 or seek_end < duration_sec:
        seek_args = ['-ss', f'{seek_start:.3f}', '-to', f'{seek_end:.3f}']
        
    params = None
    measured_max_volume = None
    
    if norm_mode == 'lufs' and not fast_normalize:
        # Two-pass loudnorm analysis
        filter_parts = [f'loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json']
        
        ffmpeg = get_ffmpeg_path()
        verbosity = ['-v', 'info'] if verbose else ['-hide_banner', '-v', 'error']
        thread_args = ['-threads', str(threads)] if threads > 0 else []
        
        cmd = [ffmpeg] + verbosity + seek_args + ['-i', input_path] + thread_args + \
              ['-af', ','.join(filter_parts), '-f', 'null', '-']
              
        proc = process_manager.spawn(cmd, job_id=job_id)
        _, stderr = proc.communicate()
        stderr_text = stderr.decode('utf-8', errors='ignore')
        
        # Parse JSON output
        json_match = re.findall(r'\{[\s\S]*?\}', stderr_text)
        if json_match:
            try:
                parsed = json.loads(json_match[-1])
                params = {
                    'measured_I': parsed.get('input_i'),
                    'measured_LRA': parsed.get('input_lra'),
                    'measured_TP': parsed.get('input_tp'),
                    'measured_thresh': parsed.get('input_thresh'),
                    'offset': parsed.get('target_offset')
                }
            except json.JSONDecodeError:
                pass
                
    elif norm_mode == 'peak':
        # Peak analysis with volumedetect
        ffmpeg = get_ffmpeg_path()
        thread_args = ['-threads', str(threads)] if threads > 0 else []
        
        cmd = [ffmpeg, '-hide_banner', '-v', 'info'] + seek_args + \
              ['-i', input_path] + thread_args + \
              ['-af', 'volumedetect', '-f', 'null', '-']
              
        proc = process_manager.spawn(cmd, job_id=job_id)
        _, stderr = proc.communicate()
        stderr_text = stderr.decode('utf-8', errors='ignore')
        
        # Parse max_volume
        match = re.search(r'max_volume:\s*(-?[0-9.]+)\s*dB', stderr_text)
        if match:
            measured_max_volume = float(match.group(1))
            
    progress_callback(job_id, 'analyze', 'done', 100)
    
    if process_manager.is_canceled():
        return
        
    # Render pass
    progress_callback(job_id, 'render', 'start', 0)
    
    filter_parts = []
    
    if norm_mode == 'lufs':
        if params:
            filter_parts.append(
                f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:"
                f"measured_I={params['measured_I']}:measured_LRA={params['measured_LRA']}:"
                f"measured_TP={params['measured_TP']}:measured_thresh={params['measured_thresh']}:"
                f"offset={params['offset']}:linear=true:print_format=summary"
            )
        else:
            filter_parts.append(f'loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=summary')
        filter_parts.append(f'alimiter=limit={limiter}:level_in=1.0:level_out=1.0')
    else:
        # Peak mode
        gain_db = 0
        if measured_max_volume is not None:
            ideal_gain = peak_target_db - measured_max_volume
            only_boost = settings.get('peakOnlyBoost', True)
            gain_db = max(0, ideal_gain) if only_boost else ideal_gain
            gain_db = max(-30, min(30, gain_db))
            
        log_callback(job_id, 'analyze', f"Peak mode: measuredMax={measured_max_volume if measured_max_volume is not None else 'n/a'} dB, target={peak_target_db} dB, gain={gain_db:.2f} dB, onlyBoost={settings.get('peakOnlyBoost', True)}")
        filter_parts.append(f'volume={gain_db:.2f}dB')
        
    ffmpeg = get_ffmpeg_path()
    verbosity = ['-v', 'info'] if verbose else ['-hide_banner', '-v', 'error']
    thread_args = ['-threads', str(threads)] if threads > 0 else []
    
    cmd = [ffmpeg] + verbosity + seek_args + ['-y', '-i', input_path] + thread_args + \
          ['-af', ','.join(filter_parts), '-acodec', out_codec, '-map_metadata', '-1', output_path]
          
    proc = process_manager.spawn(cmd, job_id=job_id)
    _, stderr = proc.communicate()
    
    progress_callback(job_id, 'render', 'done', 100)
    log_callback(job_id, 'render', f"Completed: {output_path}")
