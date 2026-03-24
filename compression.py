''' Video compression module for Discord upload.
    Calculates optimal bitrate to achieve ~8.2MB file size.
    Based on: https://github.com/Piyabordee/discord-video-compressor

    Claude + User 3/24/26 '''

import subprocess
import logging
import os
import re
from typing import Callable, Optional, Tuple

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


# Import constants at module level for STARTUPINFO
import constants
