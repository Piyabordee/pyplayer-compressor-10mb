"""Tests for pyplayer.core.compression."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from pyplayer.core.compression import (
    AUDIO_BITRATE_KBPS,
    MIN_VIDEO_BITRATE_KBPS,
    TARGET_FILESIZE_MB,
    calculate_video_bitrate,
    compress_video,
    get_video_duration,
)


class TestCalculateVideoBitrate:
    def test_normal_duration(self):
        # 60s video → target ~8.2MB
        bitrate = calculate_video_bitrate(60.0)
        expected_total = (TARGET_FILESIZE_MB * 8 * 1024) / 60.0
        expected_video = int(expected_total - AUDIO_BITRATE_KBPS)
        assert bitrate == expected_video

    def test_long_video(self):
        # 600s (10 min) → low bitrate, may hit minimum
        bitrate = calculate_video_bitrate(600.0)
        assert bitrate >= MIN_VIDEO_BITRATE_KBPS

    def test_very_short_video_clamped(self):
        # 0.01s → would give huge bitrate, but clamped by calculation
        bitrate = calculate_video_bitrate(0.01)
        # Formula: (8.2 * 8 * 1024) / 0.01 - 128 = very high, no clamping needed
        assert bitrate > 10000

    def test_extremely_short_video_clamped_to_min(self):
        # Duration so short that bitrate goes negative → clamped to MIN
        # Need: total_kbps < AUDIO_BITRATE_KBPS
        # (8.2 * 8 * 1024) / d < 128 → d > 524.8
        # Actually 8.2*8*1024 = 67584, so 67584/d < 128 → d > 528
        bitrate = calculate_video_bitrate(1000.0)
        assert bitrate >= MIN_VIDEO_BITRATE_KBPS

    def test_exact_one_minute(self):
        bitrate = calculate_video_bitrate(60.0)
        total_kbps = (TARGET_FILESIZE_MB * 8 * 1024) / 60.0
        assert bitrate == int(total_kbps - AUDIO_BITRATE_KBPS)


class TestGetVideoDuration:
    @patch('pyplayer.core.compression.subprocess.run')
    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    def test_success(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='65.123456\n'
        )
        result = get_video_duration('ffprobe', 'video.mp4')
        assert result == pytest.approx(65.123456)

    @patch('pyplayer.core.compression.subprocess.run')
    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    def test_empty_ffprobe_path(self, mock_exists, mock_run):
        result = get_video_duration('', 'video.mp4')
        assert result is None
        mock_run.assert_not_called()

    @patch('pyplayer.core.compression.os.path.exists', return_value=False)
    def test_missing_input_file(self, mock_exists):
        result = get_video_duration('ffprobe', 'nonexistent.mp4')
        assert result is None

    @patch('pyplayer.core.compression.subprocess.run')
    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    def test_ffprobe_failure(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='error')
        result = get_video_duration('ffprobe', 'video.mp4')
        assert result is None

    @patch('pyplayer.core.compression.subprocess.run')
    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    def test_timeout(self, mock_exists, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired('ffprobe', 30)
        result = get_video_duration('ffprobe', 'video.mp4')
        assert result is None

    @patch('pyplayer.core.compression.subprocess.run')
    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    def test_empty_output(self, mock_exists, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout='\n')
        result = get_video_duration('ffprobe', 'video.mp4')
        assert result is None


class TestCompressVideo:
    @patch('pyplayer.core.compression.os.path.getsize', return_value=5 * 1024 * 1024)
    @patch('pyplayer.core.compression.os.path.exists', side_effect=lambda p: True)
    @patch('pyplayer.core.compression.subprocess.Popen')
    @patch('pyplayer.core.compression.get_video_duration', return_value=60.0)
    def test_success_with_progress(self, mock_duration, mock_popen, mock_exists, mock_getsize):
        # Simulate FFmpeg output with progress
        mock_process = MagicMock()
        mock_process.stderr = [
            'frame=  10 fps=25 q=28.0 size=  512kB time=00:00:00.40 bitrate=10485.8kbits/s',
            'frame= 100 fps=25 q=28.0 size= 5120kB time=00:00:04.00 bitrate=10485.8kbits/s',
        ]
        mock_process.wait.return_value = 0
        mock_popen.return_value = mock_process

        progress_calls = []
        success, error = compress_video(
            'ffmpeg', 'ffprobe', 'input.mp4', 'output.mp4',
            progress_callback=lambda p: progress_calls.append(p)
        )

        assert success is True
        assert error == ''
        assert len(progress_calls) > 0

    @patch('pyplayer.core.compression.os.path.exists', return_value=False)
    def test_empty_ffmpeg_path(self, mock_exists):
        success, error = compress_video('', 'ffprobe', 'input.mp4', 'output.mp4')
        assert success is False
        assert 'FFmpeg' in error

    @patch('pyplayer.core.compression.os.path.exists', side_effect=lambda p: p == 'input.mp4')
    def test_missing_input_file(self, mock_exists):
        # ffmpeg exists but input doesn't → second call returns False
        success, error = compress_video('ffmpeg', 'ffprobe', 'input.mp4', 'output.mp4')
        assert success is False

    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    @patch('pyplayer.core.compression.get_video_duration', return_value=None)
    def test_duration_detection_fails(self, mock_duration, mock_exists):
        success, error = compress_video('ffmpeg', 'ffprobe', 'input.mp4', 'output.mp4')
        assert success is False
        assert 'duration' in error.lower()

    @patch('pyplayer.core.compression.os.path.exists', return_value=True)
    @patch('pyplayer.core.compression.subprocess.Popen')
    @patch('pyplayer.core.compression.get_video_duration', return_value=60.0)
    def test_ffmpeg_nonzero_return(self, mock_duration, mock_popen, mock_exists):
        mock_process = MagicMock()
        mock_process.stderr = []
        mock_process.wait.return_value = 1
        mock_popen.return_value = mock_process

        success, error = compress_video('ffmpeg', 'ffprobe', 'input.mp4', 'output.mp4')
        assert success is False
        assert 'return code' in error.lower()
