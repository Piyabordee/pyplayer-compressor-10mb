"""Shared test fixtures for PyPlayer test suite."""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_constants(monkeypatch):
    """Provide a mocked constants module for tests that need it."""
    mock = MagicMock()
    mock.IS_WINDOWS = sys.platform == 'win32'
    mock.IS_COMPILED = False
    mock.FFMPEG = 'ffmpeg'
    mock.FFPROBE = 'ffprobe'
    mock.STARTUPINFO = None
    mock.TARGET_FILESIZE_MB = 8.2
    mock.AUDIO_BITRATE_KBPS = 128
    mock.MIN_VIDEO_BITRATE_KBPS = 64
    return mock


@pytest.fixture
def sample_ffprobe_duration_output():
    """Return typical ffprobe duration output."""
    return '65.123456\n'


@pytest.fixture
def sample_ffmpeg_progress_lines():
    """Return typical FFmpeg stderr lines for progress parsing."""
    return [
        'frame=   10 fps=0.0 q=28.0 size=     512kB time=00:00:00.40 bitrate=10485.8kbits/s speed=1.0x',
        'frame=   50 fps= 25 q=28.0 size=    2560kB time=00:00:02.00 bitrate=10485.8kbits/s speed=1.0x',
        'frame=  100 fps= 33 q=28.0 size=    5120kB time=00:00:04.00 bitrate=10485.8kbits/s speed=1.3x',
    ]
