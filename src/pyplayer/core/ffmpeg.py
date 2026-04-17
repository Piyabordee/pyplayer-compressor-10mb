"""FFmpeg subprocess wrappers and process management."""
from __future__ import annotations

import os
import sys
import time
import logging
import subprocess
from traceback import format_exc

from pyplayer import constants

logger = logging.getLogger('pyplayer.core.ffmpeg')


def ffmpeg(cmd: str) -> None:
    """Run FFmpeg command synchronously."""
    cmd = f'"{constants.FFMPEG}" -y {cmd} -progress pipe:1 -hide_banner -loglevel warning'.replace('""', '"')
    logger.info('FFmpeg command: ' + cmd)
    if not constants.IS_WINDOWS:
        import shlex
        cmd = shlex.split(cmd)                  # w/o `shell=True`, linux will try to read the entire `cmd` like a file

    subprocess.run(
        cmd,
        startupinfo=constants.STARTUPINFO       # hides command prompt that appears w/o `shell=True`
    )


def ffmpeg_async(cmd: str, priority: int = None, niceness: int = None, threads: int = 0) -> subprocess.Popen:
    ''' Valid `priority` level aliases and their associated nice value on Unix:
        - 0 - High (-10)
        - 1 - Above normal (-5)
        - 2 - Normal (0)
        - 3 - Below normal (5)
        - 4 - Low (10)

        On Windows, `priority` > 4 is treated as an actual Windows constant,
        and on Linux `niceness` is treated as a raw niceness value.

        NOTE: From what I've read, "niceness" does literally nothing on Mac.
        NOTE: Negative niceness requires root. Otherwise, 0 is used.
        NOTE: `threads` expects `cmd` to end with a quoted output path.
        NOTE: `threads` will be ignored if "-threads" is already in `cmd`. '''

    # add "-threads" parameter just before `cmd`'s output path if desired
    if threads and cmd[-1] == '"' and ' -threads ' not in cmd:
        output_index = cmd.rfind(' "', 0, -1)
        cmd = f'{cmd[:output_index]} -threads {threads} {cmd[output_index:]}'

    # add extra supplemental parameters to formatting, piping, and overwriting
    cmd = f'"{constants.FFMPEG}" -y {cmd} -progress pipe:1 -hide_banner -loglevel warning'.replace('""', '"')
    logger.info('FFmpeg command: ' + cmd)

    # set priority on Windows
    if constants.IS_WINDOWS:
        if priority is not None:
            if priority < 5:                    # <5 means we want to use it like an index (0-4)
                priority = (                    # otherwise it might be a raw value, like 64
                    subprocess.HIGH_PRIORITY_CLASS,
                    subprocess.ABOVE_NORMAL_PRIORITY_CLASS,
                    subprocess.NORMAL_PRIORITY_CLASS,
                    subprocess.BELOW_NORMAL_PRIORITY_CLASS,
                    subprocess.IDLE_PRIORITY_CLASS,
                )[priority]
        else:
            priority = 0

    # split `cmd` and calculate priority ("niceness") on Linux
    else:
        import shlex
        cmd = shlex.split(cmd)                  # w/o `shell=True`, linux will try to read the entire `cmd` like a file

        # calculate priority
        if niceness is not None:                # raw `niceness` value was provided, just use that
            priority = niceness
        elif priority is not None:              # no `niceness` -> calculate it from `priority`
            priority = -10 + (priority * 5)     # 0 = -10, 1 = -5, 2 = 0, 3 = 5, 4 = 10

        # prepend niceness command to our ffmpeg command (doesn't do anything on macOS apparently)
        if constants.IS_LINUX and priority:     # who's really gonna use PyPlayer on a Mac anyways?
            cmd = ['nice', '-n', str(priority)] + cmd
        priority = 0                            # creationflags must be 0, not None

    # open process
    return subprocess.Popen(
        cmd,
        bufsize=1,                              # line-by-line buffering (helps us with parsing in batches)
        stdout=subprocess.PIPE,                 # pipes stdout so that we can read the output in real time
        stderr=subprocess.STDOUT,               # pipes errors to stdout so we can read both (keeping them separate is hard)
        startupinfo=constants.STARTUPINFO,      # hides command prompt that appears w/o `shell=True`
        creationflags=priority,                 # sets the priority level ffmpeg will start with
        start_new_session=True,                 # this allows us to more easily kill the ffmpeg process if needed
        text=True,                              # turns stdout into easily parsible lines of text rather than a byte stream
        encoding='utf-8',                       # ffmpeg/ffprobe output text in utf-8 encoding
        errors='ignore'                         # if there are encoding errors anyway, just drop the bad characters
    )


def suspend_process(process: subprocess.Popen, suspend: bool = True) -> int:
    ''' Cross-platform way of suspending or resuming a `process`. On Linux/Mac,
        SIGSTOP/SIGCONT signals are sent. On Windows, the undocumented
        `ntdll.NtSuspendProcess()` and `ntdll.NtResumeProcess()` APIs are
        used. Returns 0 on success (this does not inherently mean `process`
        was actually suspended, just that the calls did not fail).

        Windows notes:
        - `ntdll.NtSuspendProcess` calls stack (i.e. each suspend call must
        have a corresponding resume call before `process` actually resumes)!
        This method does not check if `process` is already suspended or not.
        - Suspend/resume calls will be sent to the parent shell rather than
        the actual process if `process` was created using `shell=True`!
        - This is based on `psutil`'s `psutil_proc_suspend_or_resume()`
        function, recreated from scratch in "pure" Python. '''

    if not constants.IS_WINDOWS:
        import signal
        process.send_signal(signal.SIGSTOP if suspend else signal.SIGCONT)
        return 0

    # NOTE: this is all just security theater and could reduced to 7 lines, but whatever
    from ctypes import wintypes, WinDLL

    try:
        # dll and function definitions
        ntdll = WinDLL("ntdll", use_last_error=True)
        kernel32 = WinDLL("kernel32", use_last_error=True)
        CloseHandle = kernel32.CloseHandle
        OpenProcess = kernel32.OpenProcess

        # defining return/argument types for the above functions for type-safety
        CloseHandle.restype = wintypes.LONG
        CloseHandle.argtypes = (wintypes.HANDLE,)
        OpenProcess.restype = wintypes.HANDLE
        OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )

        # open limited handle to process using its pid (closed in the finally-statement)
        access_flags = 2048 | 4096      # PROCESS_SUSPEND_RESUME | PROCESS_QUERY_LIMITED_INFORMATION
        process_handle = OpenProcess(access_flags, False, process.pid)

        # define and call either ntdll.NtSuspendProcess or ntdll.NtResumeProcess
        if suspend:
            logger.info(f'Suspending process {process} at handle {process_handle}...')
            NtSuspendProcess = ntdll.NtSuspendProcess
            NtSuspendProcess.argtypes = (wintypes.HANDLE,)
            NtSuspendProcess.restype = wintypes.LONG
            return NtSuspendProcess(process_handle)
        else:
            logger.info(f'Resuming process {process} at handle {process_handle}...')
            NtResumeProcess = ntdll.NtResumeProcess
            NtResumeProcess.argtypes = (wintypes.HANDLE,)
            NtResumeProcess.restype = wintypes.LONG
            return NtResumeProcess(process_handle)
    except:
        logger.info(f'(!) Failed to {"suspend" if suspend else "resume"} process: {format_exc()}')
        return -1
    finally:
        CloseHandle(process_handle)


def kill_process(process: subprocess.Popen, wait: bool = True, wait_after: float = 0.0) -> None:
    ''' Cross-platform way of killing a `process`. On Windows, taskkill is used.
        On Linux/Mac, a SIGTERM signal is sent to `process`'s group pid. If
        `wait` is True, this function blocks until `process` is gone, then waits
        `wait_after` seconds afterwards to allow any handles to be released. '''
    try:
        if constants.IS_WINDOWS:                # why bother with signals when you can just nuke it from orbit?
            subprocess.call(
                f'taskkill /F /T /PID {process.pid}',
                startupinfo=constants.STARTUPINFO
            )                                   # ^ hides command prompt that appears if called while compiled
        else:
            try:
                import signal
                group_pid = os.getpgid(process.pid)
                os.killpg(group_pid, signal.SIGTERM)
                process.wait(timeout=0.25)      # wait briefly to see if it terminates peacefully
            except subprocess.TimeoutExpired:   # it's is still alive. old yeller it
                os.killpg(group_pid, signal.SIGKILL)
        if wait:
            process.wait(timeout=3)             # give it up to 3 seconds to actually close before giving up
            time.sleep(wait_after)              # wait for any handles to (hopefully) be released
    except:
        logger.warning(f'(!) Failed to terminate process: {format_exc()}')
