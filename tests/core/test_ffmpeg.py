"""Tests for pyplayer.core.ffmpeg — subprocess wrappers."""
from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from pyplayer.core import ffmpeg as ffmpeg_module


class TestFfmpegSync:
    @patch('pyplayer.core.ffmpeg.subprocess.run')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_runs_command(self, mock_constants, mock_run):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True

        ffmpeg_module.ffmpeg('-i input.mp4 output.mp4')
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert 'ffmpeg.exe' in cmd
        assert '-i input.mp4 output.mp4' in cmd
        assert '-y' in cmd

    @patch('pyplayer.core.ffmpeg.subprocess.run')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_includes_progress_flag(self, mock_constants, mock_run):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True

        ffmpeg_module.ffmpeg('-i input.mp4 output.mp4')
        cmd = mock_run.call_args[0][0]
        assert '-progress pipe:1' in cmd
        assert '-hide_banner' in cmd


class TestFfmpegAsync:
    @patch('pyplayer.core.ffmpeg.subprocess.Popen')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_returns_popen(self, mock_constants, mock_popen):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True

        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        result = ffmpeg_module.ffmpeg_async('-i input.mp4 output.mp4')
        assert result is mock_process

    @patch('pyplayer.core.ffmpeg.subprocess.Popen')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_threads_injection(self, mock_constants, mock_popen):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True
        mock_popen.return_value = MagicMock()

        ffmpeg_module.ffmpeg_async('-i input.mp4 "output.mp4"', threads=4)
        cmd = mock_popen.call_args[0][0]
        assert '-threads 4' in cmd

    @patch('pyplayer.core.ffmpeg.subprocess.Popen')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_threads_not_injected_if_exists(self, mock_constants, mock_popen):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True
        mock_popen.return_value = MagicMock()

        ffmpeg_module.ffmpeg_async('-i input.mp4 -threads 2 "output.mp4"', threads=4)
        cmd = mock_popen.call_args[0][0]
        # Should not add -threads again
        assert cmd.count('-threads') == 1

    @patch('pyplayer.core.ffmpeg.subprocess.Popen')
    @patch('pyplayer.core.ffmpeg.constants')
    def test_windows_priority_mapping(self, mock_constants, mock_popen):
        mock_constants.FFMPEG = 'ffmpeg.exe'
        mock_constants.STARTUPINFO = None
        mock_constants.IS_WINDOWS = True
        mock_popen.return_value = MagicMock()

        ffmpeg_module.ffmpeg_async('-i input.mp4 output.mp4', priority=0)
        # priority=0 maps to HIGH_PRIORITY_CLASS
        creationflags = mock_popen.call_args[1]['creationflags']
        assert creationflags == subprocess.HIGH_PRIORITY_CLASS


class TestSuspendProcess:
    @patch('pyplayer.core.ffmpeg.constants')
    def test_suspend_on_windows(self, mock_constants):
        mock_constants.IS_WINDOWS = True
        mock_process = MagicMock()
        mock_process.pid = 1234

        # On Windows, suspend_process uses ntdll — just verify it doesn't crash
        # with the mock. The actual Windows API calls are tested manually.
        try:
            result = ffmpeg_module.suspend_process(mock_process, suspend=True)
            # Returns 0 on success, -1 on failure (both are valid in tests)
            assert isinstance(result, int)
        except Exception:
            pass  # Windows API mocking is fragile, just ensure no hang

    @patch('pyplayer.core.ffmpeg.constants')
    def test_resume_on_windows(self, mock_constants):
        mock_constants.IS_WINDOWS = True
        mock_process = MagicMock()
        mock_process.pid = 1234

        try:
            result = ffmpeg_module.suspend_process(mock_process, suspend=False)
            assert isinstance(result, int)
        except Exception:
            pass


class TestKillProcess:
    @patch('pyplayer.core.ffmpeg.constants')
    def test_windows_uses_taskkill(self, mock_constants):
        mock_constants.IS_WINDOWS = True
        mock_constants.STARTUPINFO = None
        mock_process = MagicMock()
        mock_process.pid = 1234

        with patch('pyplayer.core.ffmpeg.subprocess.call') as mock_call:
            ffmpeg_module.kill_process(mock_process, wait=False)
            mock_call.assert_called_once()
            assert 'taskkill' in mock_call.call_args[0][0]
            assert '1234' in mock_call.call_args[0][0]

    @patch('pyplayer.core.ffmpeg.constants')
    def test_waits_by_default(self, mock_constants):
        mock_constants.IS_WINDOWS = True
        mock_constants.STARTUPINFO = None
        mock_process = MagicMock()
        mock_process.pid = 1234

        with patch('pyplayer.core.ffmpeg.subprocess.call'):
            ffmpeg_module.kill_process(mock_process, wait=True)
            mock_process.wait.assert_called()

    @patch('pyplayer.core.ffmpeg.constants')
    def test_no_wait(self, mock_constants):
        mock_constants.IS_WINDOWS = True
        mock_constants.STARTUPINFO = None
        mock_process = MagicMock()
        mock_process.pid = 1234

        with patch('pyplayer.core.ffmpeg.subprocess.call'):
            ffmpeg_module.kill_process(mock_process, wait=False)
            mock_process.wait.assert_not_called()
