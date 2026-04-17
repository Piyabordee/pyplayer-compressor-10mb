"""Tests for pyplayer.core.file_ops."""
from __future__ import annotations

from unittest.mock import patch

from pyplayer.core.file_ops import (
    add_path_suffix,
    get_from_PATH,
    get_unique_path,
    sanitize,
)


class TestSanitize:
    def test_normal_filename(self):
        assert sanitize('hello.txt') == 'hello.txt'

    def test_removes_blacklist_chars(self):
        result = sanitize('file<>:|?.txt')
        assert '<' not in result
        assert '>' not in result
        assert ':' not in result
        assert '|' not in result

    def test_removes_trailing_dots(self):
        assert sanitize('file.') == 'file'

    def test_removes_trailing_spaces(self):
        assert sanitize('file ') == 'file'

    def test_empty_returns_default(self):
        assert sanitize('') == ''
        assert sanitize('', default='unnamed') == 'unnamed'

    def test_all_invalid_returns_default(self):
        result = sanitize('<<<>>>', default='fallback')
        assert result == 'fallback'

    def test_reserved_word_con(self):
        assert sanitize('CON') == '__CON'

    def test_reserved_word_without_allow(self):
        assert sanitize('CON', allow_reserved_words=False) == ''

    def test_reserved_word_with_default(self):
        assert sanitize('CON', allow_reserved_words=False, default='file') == 'file'

    def test_unicode_normalization(self):
        # NFKD decomposition: e + combining accent
        result = sanitize('cafe\u0301')
        assert result == 'cafe\u0301'

    def test_control_chars_removed(self):
        result = sanitize('file\x00\x01\x1f.txt')
        assert '\x00' not in result
        assert '\x01' not in result
        assert '\x1f' not in result
        assert 'file' in result

    def test_reserved_words_all(self):
        for word in ('CON', 'PRN', 'AUX', 'NUL', 'COM1', 'LPT1'):
            assert sanitize(word) == f'__{word}'

    def test_normal_name_not_reserved(self):
        assert sanitize('config.ini') == 'config.ini'


class TestAddPathSuffix:
    def test_simple_suffix(self):
        result = add_path_suffix('/path/video.mp4', '_compressed')
        assert result == '/path/video_compressed.mp4'

    def test_no_extension(self):
        result = add_path_suffix('/path/README', '_v2')
        assert result == '/path/README_v2'

    @patch('pyplayer.core.file_ops.os.path.exists', return_value=False)
    def test_unique_no_conflict(self, mock_exists):
        result = add_path_suffix('/path/video.mp4', '_compressed', unique=True)
        assert result == '/path/video_compressed.mp4'


class TestGetUniquePath:
    @patch('pyplayer.core.file_ops.os.path.exists', return_value=False)
    def test_path_does_not_exist(self, mock_exists):
        result = get_unique_path('/path/video.mp4')
        assert result == '/path/video.mp4'

    @patch('pyplayer.core.file_ops.os.path.exists', side_effect=[True, True, False])
    def test_windows_style_naming(self, mock_exists):
        # 1st True: initial check (line 67)
        # 2nd True: while loop condition (line 71) → enters loop
        # 3rd False: while loop re-check → exits
        result = get_unique_path('/path/video.mp4')
        assert result == '/path/video (2).mp4'

    @patch('pyplayer.core.file_ops.os.path.exists', side_effect=[True, True, True, False])
    def test_increments_version(self, mock_exists):
        result = get_unique_path('/path/video.mp4')
        assert result == '/path/video (3).mp4'

    @patch('pyplayer.core.file_ops.os.path.exists', side_effect=[True, False])
    def test_key_replacement(self, mock_exists):
        # key not strict: first replaces key with '', checks exists
        # 1st True: path with key exists → enters while loop
        # Wait, key path: first check is on path WITHOUT key → True means that exists
        # Actually: line 62 checks `os.path.exists(path)` where path = key_path.replace(key, '')
        result = get_unique_path('/path/video_#.mp4', key='#')
        # path becomes '/path/video_.mp4' first (key removed), then True → loop continues
        assert result == '/path/video_2.mp4'

    @patch('pyplayer.core.file_ops.os.path.exists', side_effect=[True, True, False])
    def test_key_replacement_with_version(self, mock_exists):
        result = get_unique_path('/path/video_#.mp4', key='#')
        # path without key exists → try version 2, which also exists → try version 3
        assert result == '/path/video_3.mp4'

    @patch('pyplayer.core.file_ops.os.path.exists', side_effect=[False])
    def test_strict_mode_first_version(self, mock_exists):
        result = get_unique_path('/path/video_#.mp4', key='#', strict=True, start=1)
        # Strict: always includes version number, checks once
        assert result == '/path/video_1.mp4'


class TestGetFromPATH:
    @patch('pyplayer.core.file_ops.os.listdir')
    @patch('pyplayer.core.file_ops.os.environ', {'PATH': '/usr/bin;/usr/local/bin'})
    def test_found(self, mock_listdir):
        mock_listdir.return_value = ['python.exe', 'ffmpeg.exe']
        result = get_from_PATH('ffmpeg.exe')
        assert 'ffmpeg.exe' in result

    @patch('pyplayer.core.file_ops.os.listdir')
    @patch('pyplayer.core.file_ops.os.environ', {'PATH': '/usr/bin'})
    def test_not_found(self, mock_listdir):
        mock_listdir.return_value = ['python.exe']
        result = get_from_PATH('ffmpeg.exe')
        assert result == ''

    @patch('pyplayer.core.file_ops.os.environ', {'PATH': ''})
    def test_empty_path(self):
        result = get_from_PATH('ffmpeg.exe')
        assert result == ''
