''' Video compression module for Discord upload.
    Calculates optimal bitrate to achieve ~8.2MB file size.
    Based on: https://github.com/Piyabordee/discord-video-compressor

    Claude + User 3/24/26 '''

import subprocess
import logging
import os
import re
from typing import Callable, Optional, Tuple

import constants

logger = logging.getLogger('compression.py')

# ---------------------
# Constants

TARGET_FILESIZE_MB = 8.2
AUDIO_BITRATE_KBPS = 128
MIN_VIDEO_BITRATE_KBPS = 64

# ---------------------
# Duration Detection


def get_video_duration(ffprobe_path: str, input_path: str) -> Optional[float]:
    '''
    Get video duration in seconds using ffprobe.

    Args:
        ffprobe_path: Path to ffprobe executable
        input_path: Path to video file

    Returns:
        Duration in seconds, or None if failed
    '''
    if not ffprobe_path:
        logger.error('FFprobe path is empty')
        return None

    if not os.path.exists(input_path):
        logger.error(f'Input file does not exist: {input_path}')
        return None

    try:
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-i', input_path,
            '-show_entries', 'format=duration',
            '-of', 'csv=p=0'
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            startupinfo=constants.STARTUPINFO if constants.IS_WINDOWS else None
        )

        if result.returncode == 0:
            duration_str = result.stdout.strip()
            if duration_str:
                duration = float(duration_str)
                logger.info(f'Duration detected: {duration:.2f}s')
                return duration
            else:
                logger.error('FFprobe returned empty duration')
                return None
        else:
            logger.error(f'FFprobe failed: {result.stderr}')
            return None

    except subprocess.TimeoutExpired:
        logger.error('FFprobe timed out')
        return None
    except ValueError:
        logger.error(f'Could not parse duration from: {result.stdout}')
        return None
    except Exception as e:
        logger.error(f'Error getting duration: {e}')
        return None


def calculate_video_bitrate(duration_seconds: float) -> int:
    '''
    Calculate video bitrate to achieve target file size.

    Formula: video_bitrate = (target_size_mb * 8 * 1024) / duration - audio_bitrate

    Args:
        duration_seconds: Video duration in seconds

    Returns:
        Video bitrate in kbps (minimum 64 kbps)
    '''
    target_total_kbps = (TARGET_FILESIZE_MB * 8 * 1024) / duration_seconds
    video_bitrate = int(target_total_kbps - AUDIO_BITRATE_KBPS)

    # Enforce minimum bitrate
    if video_bitrate < MIN_VIDEO_BITRATE_KBPS:
        logger.warning(
            f'Calculated bitrate {video_bitrate}k is below minimum. '
            f'Using {MIN_VIDEO_BITRATE_KBPS}k instead.'
        )
        video_bitrate = MIN_VIDEO_BITRATE_KBPS

    logger.info(f'Bitrate calculated: {video_bitrate}k for {duration_seconds:.2f}s video')
    return video_bitrate

# ---------------------
# Main Compression Function


def compress_video(
    ffmpeg_path: str,
    ffprobe_path: str,
    input_path: str,
    output_path: str,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Tuple[bool, str]:
    '''
    Compress video to ~8.2MB for Discord upload.

    Args:
        ffmpeg_path: Path to ffmpeg executable
        ffprobe_path: Path to ffprobe executable
        input_path: Path to input video file
        output_path: Path to output compressed video
        progress_callback: Optional callback(int) for progress updates (0-100)

    Returns:
        Tuple of (success: bool, error_message: str)
    '''
    # Validate FFmpeg
    if not ffmpeg_path:
        error = 'FFmpeg path is empty'
        logger.error(error)
        return False, error

    if not os.path.exists(input_path):
        error = f'Input file does not exist: {input_path}'
        logger.error(error)
        return False, error

    # Get duration
    duration = get_video_duration(ffprobe_path, input_path)
    if duration is None or duration <= 0:
        error = 'Could not determine video duration'
        logger.error(error)
        return False, error

    # Calculate bitrate
    video_bitrate_kbps = calculate_video_bitrate(duration)

    # Build FFmpeg command
    cmd = [
        ffmpeg_path,
        '-y',  # Overwrite output file
        '-i', input_path,
        '-c:v', 'libx264',
        '-b:v', f'{video_bitrate_kbps}k',
        '-preset', 'medium',
        '-vsync', '0',
        '-c:a', 'aac',
        '-b:a', f'{AUDIO_BITRATE_KBPS}k',
        output_path
    ]

    logger.info(f'Running compression: {input_path} -> {output_path}')

    try:
        # Run FFmpeg and parse progress
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            startupinfo=constants.STARTUPINFO if constants.IS_WINDOWS else None
        )

        # Parse stderr for progress (FFmpeg writes progress to stderr)
        duration_ms = int(duration * 1000)
        last_progress = 0

        for line in process.stderr:
            # Parse time from FFmpeg output: "time=00:00:15.23"
            time_match = re.search(r'time=(\d+):(\d+):(\d+)\.(\d+)', line)
            if time_match:
                hours = int(time_match.group(1))
                minutes = int(time_match.group(2))
                seconds = int(time_match.group(3))
                centiseconds = int(time_match.group(4))

                current_ms = (hours * 3600000 + minutes * 60000 +
                             seconds * 1000 + centiseconds * 10)

                progress = min(100, int((current_ms / duration_ms) * 100))

                # Only update on significant changes
                if progress > last_progress:
                    if progress_callback:
                        progress_callback(progress)
                    last_progress = progress

        # Wait for process to complete
        returncode = process.wait()

        if returncode == 0:
            # Verify output file exists and has reasonable size
            if os.path.exists(output_path):
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                logger.info(f'Compression complete. Output size: {file_size_mb:.2f}MB')

                if progress_callback:
                    progress_callback(100)

                return True, ''
            else:
                error = 'Output file was not created'
                logger.error(error)
                return False, error
        else:
            error = f'FFmpeg failed with return code {returncode}'
            logger.error(error)
            return False, error

    except Exception as e:
        error = f'Compression error: {str(e)}'
        logger.error(error)
        return False, error
