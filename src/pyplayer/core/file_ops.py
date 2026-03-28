"""File system operations and path utilities."""
from __future__ import annotations

import os
import logging
import unicodedata

from pyplayer import constants

logger = logging.getLogger('pyplayer.core.file_ops')


# reserved words/characters on Windows
_SANITIZE_BLACKLIST = ('\\', '/', ':', '*', '?', '"', '<', '>', '|', '\0')
_SANITIZE_RESERVED = (
    'CON', 'PRN', 'AUX', 'NUL', 'COM0', 'COM1', 'COM2', 'COM3',
    'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT0', 'LPT1',
    'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9',
)


def add_path_suffix(path: str, suffix: str, unique: bool = False) -> str:
    ''' Returns a path with `suffix` added between the basename and extension.
        If `unique` is True, the new path will be run through get_unique_path()
        with default arguments before returning. '''
    from pyplayer.core.file_ops import get_unique_path
    base, ext = os.path.splitext(path)
    return f'{base}{suffix}{ext}' if not unique else get_unique_path(f'{base}{suffix}{ext}')


def get_from_PATH(filename: str) -> str:
    ''' Returns the full path to a `filename` if it exists in
        the user's PATH, otherwise returns an empty string. '''
    sep = ';' if constants.IS_WINDOWS else ':'
    for path in os.environ.get('PATH', '').split(sep):
        try:
            if filename in os.listdir(path):
                return os.path.join(path, filename)
        except:
            pass
    return ''


def get_unique_path(path: str, start: int = 2, key: str = None, zeros: int = 0, strict: bool = False) -> str:
    ''' Returns a unique `path`. If `path` already exists, version-numbers
        starting from `start` are added. If a keyword `key` is provided and
        is a substring within `path`, it is replaced with the version number
        with `zeros` padded zeros. Otherwise, Windows-style naming is used
        with no padding: "(base) (version).(ext)". `strict` forces paths
        with non-Windows-style naming to always include a version number,
        even if `path` was unique to begin with. '''
    # TODO: add ignore_extensions parameter that uses os.path.splitext and glob(basepath.*)
    version = start
    if key and key in path:                     # if key and key exists in path -> replace key in path with padded version number
        print(f'Replacing key "{key}" in path: {path}')
        key_path = path
        if strict:                              # if strict, replace key with first version number
            path = key_path.replace(key, str(version).zfill(zeros if version >= 0 else zeros + 1))  # +1 zero if version is negative
            version += 1                        # increment version here to avoid checking this first path twice when we start looping
        else:
            path = key_path.replace(key, '')    # if not strict, replace key with nothing first to see if original name is unique
        while os.path.exists(path):
            path = key_path.replace(key, str(version).zfill(zeros if version >= 0 else zeros + 1))
            version += 1
    else:                                       # no key -> use windows-style unique paths
        base, ext = os.path.splitext(path)
        if os.path.exists(path):                # if path exists, check if it's already using window-style names
            parts = base.split()
            if parts[-1][0] == '(' and parts[-1][-1] == ')' and parts[-1][1:-1].isnumeric():
                base = ' '.join(parts[:-1])     # path is using window-style names, remove pre-existing version string from basename
            while os.path.exists(path):
                path = f'{base} ({version}){ext}'
                version += 1
    return path


def open_properties(path: str):
    ''' Opens a properties dialog for `path`. Windows only. If `path` is
        empty, the current working directory is used instead. If `path`
        is invalid, Windows will display a warning dialog. '''
    if not constants.IS_WINDOWS: return
    from win32com.shell import shell, shellcon

    logger.info(f'Opening properties dialog for "{path}"')
    shell.ShellExecuteEx(
        nShow=1,
        fMask=shellcon.SEE_MASK_NOCLOSEPROCESS | shellcon.SEE_MASK_INVOKEIDLIST,
        lpVerb='properties',
        lpFile=path
    )


def sanitize(filename: str, allow_reserved_words: bool = True, default: str = '') -> str:
    ''' A slightly more optimized version of `sanitize_filename.sanitize()`,
        with added parameters.

        Returns a fairly safe version of `filename` (which should not be a
        full path). If `filename` is completely invalid, `default` is used.
        If `allow_reserved_words` is True, filenames such as "CON" will be
        returned as "__CON". Otherwise, `default` is returned. '''

    # remove blacklisted characters and charcters below code point 32
    filename = ''.join(c for c in filename if c not in _SANITIZE_BLACKLIST and ord(c) > 31)
    filename = unicodedata.normalize('NFKD', filename)
    filename = filename.strip().rstrip('. ')    # cannot end with spaces or periods on Windows

    if len(filename) == 0:
        filename = default
    elif filename in _SANITIZE_RESERVED:        # check for reserved filenames such as CON
        filename = default if not allow_reserved_words else ('__' + filename)
    return filename


def setctime(path: str, ctime: int) -> None:
    ''' A slightly stripped down version of the `win32_setctime` library,
        which I had trouble importing correctly after compiling. Sets the
        creation time of `path` to `ctime` seconds (a unix timestamp). To
        set last modified time or last accessed time, use `os.utime()`.
        Windows-only. https://github.com/Delgan/win32-setctime '''

    if not constants.IS_WINDOWS: return
    from ctypes import byref, get_last_error, wintypes, WinDLL, WinError

    # dll and function definitions
    kernel32 = WinDLL("kernel32", use_last_error=True)
    CreateFileW = kernel32.CreateFileW
    SetFileTime = kernel32.SetFileTime
    CloseHandle = kernel32.CloseHandle

    # defining return/argument types for the above functions for type-safety
    CreateFileW.restype = wintypes.HANDLE
    CreateFileW.argtypes = (
        wintypes.LPWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    )

    SetFileTime.restype = wintypes.BOOL
    SetFileTime.argtypes = (
        wintypes.HANDLE,
        wintypes.PFILETIME,
        wintypes.PFILETIME,
        wintypes.PFILETIME,
    )

    CloseHandle.restype = wintypes.BOOL
    CloseHandle.argtypes = (wintypes.HANDLE,)

    # ---

    path = os.path.normpath(os.path.abspath(path))
    ctime = int(ctime * 10000000) + 116444736000000000
    if not 0 < ctime < (1 << 64):
        raise ValueError("The system value of the timestamp exceeds u64 size: %d" % ctime)

    atime = wintypes.FILETIME(0xFFFFFFFF, 0xFFFFFFFF)
    mtime = wintypes.FILETIME(0xFFFFFFFF, 0xFFFFFFFF)
    ctime = wintypes.FILETIME(ctime & 0xFFFFFFFF, ctime >> 32)

    flags = 128 | 0x02000000
    handle = wintypes.HANDLE(CreateFileW(path, 256, 0, None, 3, flags, None))

    if handle.value == wintypes.HANDLE(-1).value:
        raise WinError(get_last_error())
    if not wintypes.BOOL(SetFileTime(handle, byref(ctime), byref(atime), byref(mtime))):
        raise WinError(get_last_error())
    if not wintypes.BOOL(CloseHandle(handle)):
        raise WinError(get_last_error())


if constants.IS_WINDOWS:
    file_is_hidden = lambda path: os.stat(path).st_file_attributes & 2
else:
    file_is_hidden = lambda path: os.path.basename(path)[0] == '.'
