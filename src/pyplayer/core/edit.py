"""Edit queue management — Edit and Undo classes for tracking media edit operations.

Extracted from main.pyw. These classes reference runtime globals (gui, settings,
log_on_statusbar, etc.) that must be set before use. The main entry point
assigns these at startup via the module-level names below.
"""
from __future__ import annotations

import os
import subprocess
import logging
from time import sleep, time as get_time
from traceback import format_exc

from pyplayer import constants
from pyplayer.core.file_ops import add_path_suffix
from pyplayer.core.ffmpeg import ffmpeg_async, kill_process
from pyplayer.core.media_utils import get_verbose_timestamp, remove_dict_value
from pyplayer.gui import helpers as qthelpers


# ---------------------------------------------------------------------------
# Runtime globals — set by the application entry point at startup.
# These mirror the aliases created in main.pyw's ``if __name__ == '__main__'``
# block.  Until they are populated, attribute access will raise
# ``RuntimeError`` so that missing initialisation is detected early.
# ---------------------------------------------------------------------------

def _make_placeholder(name: str):
    """Return a callable that raises ``RuntimeError`` when accessed."""
    def _raise(*args, **kwargs):
        raise RuntimeError(
            f'{name} has not been initialised. '
            f'Call pyplayer.core.edit.init_globals() from the application entry point.'
        )
    return _raise


# Module-level references populated at startup
gui = _make_placeholder('edit.gui')
settings = _make_placeholder('edit.settings')
refresh_title = _make_placeholder('edit.refresh_title')
log_on_statusbar = _make_placeholder('edit.log_on_statusbar')


def init_globals(
    gui_obj,
    settings_obj,
    refresh_title_fn,
    log_on_statusbar_fn,
):
    """Populate module-level globals needed by Edit and Undo.

    This must be called once during application startup (from the
    ``if __name__ == '__main__'`` block in the entry point).
    """
    global gui, settings, refresh_title, log_on_statusbar
    gui = gui_obj
    settings = settings_obj
    refresh_title = refresh_title_fn
    log_on_statusbar = log_on_statusbar_fn


class Edit:
    ''' A class for handling, executing, and tracking edits in progress. '''

    __slots__ = (
        'dest', 'temp_dest', 'process', '_is_paused', '_is_cancelled',
        '_threads', 'has_priority', 'frame_rate', 'frame_count',
        'audio_track_titles', 'operation_count', 'operations_started', 'frame',
        'value', 'text', 'percent_format', 'start_text', 'override_text'
    )

    def __init__(self, dest: str = ''):
        self.dest = dest
        self.temp_dest = ''
        self.process: subprocess.Popen = None
        self._is_paused = False
        self._is_cancelled = False
        self._threads = 0
        self.has_priority = False
        self.frame_rate = 0.0
        self.frame_count = 0
        self.audio_track_titles: list[str] = []
        self.operation_count = 1
        self.operations_started = 0
        self.frame = 0
        self.value = 0
        self.text = 'Saving'
        self.percent_format = '(%p%)'
        self.start_text = 'Saving'
        self.override_text = False


    @property
    def is_paused(self) -> bool:
        ''' Use `self.pause()` to safely alter this property. '''
        return self._is_paused


    @property
    def is_cancelled(self) -> bool:
        ''' Use `self.cancel()` to safely cancel. '''
        return self._is_cancelled


    def pause(self, paused: bool = None) -> bool:
        ''' Suspends or resumes the edit's FFmpeg process. If `paused` is
            not provided, the current pause-state is toggled instead. '''

        # if `paused` is not provided, just toggle our current pause state
        will_pause = (not self._is_paused) if paused is None else paused

        # NOTE: on Windows, suspending a process STACKS!!! i.e. if you suspend a process...
        # ...twice, you must resume it twice -> ONLY suspend if `self._is_paused` will change
        if will_pause != self._is_paused:
            self._is_paused = will_pause                # ↓ returns None if process hasn't terminated yet
            if self.process and self.process.poll() is None:
                from pyplayer.core.ffmpeg import suspend_process
                suspend_process(self.process, suspend=will_pause)
                if self.has_priority:
                    self.set_progress_bar(value=self.value)

        return will_pause


    def cancel(self):
        ''' Cancels this edit by killing its current FFmpeg process.
            Resumes process first if it was previously suspended. '''
        self._is_cancelled = True
        if constants.IS_WINDOWS:                        # NOTE: don't have to actually unpause on Windows...
            self._is_paused = False                     # ...since we don't rely on stdout buffering
        else:
            self.pause(paused=False)


    def give_priority(self, update_others: bool = True, ignore_lock: bool = False, conditional: bool = False):
        ''' Refreshes progress bar/taskbar to this edit's values if we've been
            given priority over updating the progress bar. If `update_others`
            is True, all other edits in `gui.edits_in_progress` will set their
            `has_priority` property to False. This method returns immediately
            if `gui.lock_edit_priority` is True and `ignore_lock` is False,
            or if `conditional` is True and any other edit has priority. '''

        # return immediately if desired
        if gui.lock_edit_priority and not ignore_lock:
            return
        if conditional:
            for edit in gui.edits_in_progress:
                if edit.has_priority:
                    return

        # ensure priority is disabled on everything else
        if update_others:
            for edit in gui.edits_in_progress:
                edit.has_priority = False

        self.has_priority = True
        if self.frame == 0:                             # assume we haven't parsed any output yet
            gui.set_save_progress_value_and_format_signal.emit(0, self.start_text)
            refresh_title()
        else:
            self.set_progress_bar(value=self.value)
        gui.set_save_progress_max_signal.emit(100 if self.frame_count else 0)


    def get_progress_text(self, frame: int = 0, simple: bool = False) -> str:
        ''' Returns `self.text` surrounded by relevant information, e.g. "2
            edits in progress - Trimming [1/3] (25%)". Manually replaces %v/%m
            with `frame`/`self.frame_count`. If `self.frame_count` is 0, "?" is
            used instead. If `simple` is provided, a standardized format that
            ignores edit counts/percent formats/text overrides is returned. '''

        if simple:
            text = self.text
            percent_format = f'({self.value}%)'
        elif self.override_text:
            return self.text
        else:
            percent_format = self.percent_format
            save_count = len(gui.edits_in_progress)
            if save_count > 1:
                text = f'{save_count} edits in progress - {self.text}'
            else:
                text = self.text

        # handle operation count and pause symbol for this edit
        operation_count = self.operation_count
        if operation_count > 1:
            pause = '\U0001D5D8\U0001D5DA, ' if self._is_paused else ''
            text = f'{text} [{pause}{self.operations_started}/{operation_count}] {percent_format}'
        else:
            pause = ' [\U0001D5D8\U0001D5DA] ' if self._is_paused else ' '
            text = f'{text}{pause}{percent_format}'

        # return with `QProgressBar` variables manually replaced TODO: never used, no plans -> why even bother?
        return text.replace('%v', str(frame)).replace('%m', str(self.frame_count or '?'))


    def set_progress_bar(self, frame: int = None, value: int = None) -> int:
        ''' Sets the progress bar/taskbar button to `frame`/`Edit.frame_count`.
            Updates the progress bar's text and puts the average progress of all
            edits/operations in the titlebar. Returns the new percentage. '''
        if value is None:
            value = int((frame / max(1, self.frame_count)) * 100)
        self.value = value
        self.frame = frame or self.frame

        # update progress bar, taskbar, and titlebar with our current value/text
        if self.has_priority:
            gui.set_save_progress_value_and_format_signal.emit(value, self.get_progress_text(frame))
            if constants.IS_WINDOWS and settings.checkTaskbarProgressEdit.isChecked():
                gui.taskbar_progress.setValue(value)
            refresh_title()

        return value


    def ffmpeg(
        self,
        infile: str,
        cmd: str,
        outfile: str = None,
        text: str = None,
        start_text: str = None,
        percent_format: str = None,
        text_override: str = None,
        auto_map_tracks: bool = True,
        audio_track_titles: list[str] = None
    ) -> str:
        ''' Executes an FFmpeg `cmd` on `infile` and outputs to `outfile`,
            showing a progress bar on both the statusbar and the taskbar icon
            (on Windows) by parsing FFmpeg's output. "%in" and "%out" will be
            replaced within `cmd` if provided. "%out" will be appended to the
            end of `cmd` automatically if needed. If `auto_map_tracks` is True,
            "-map 0" will be inserted before "%out" if "-map" is not present.
            the appropriate metadata arguments for `audio_track_titles` (or
            `self.audio_track_titles`) will also be inserted.

            NOTE: `infile` and "%in" do not necessarily need to be included, but
            if you don't providing `infile`, you shouldn't provide "%in" either.
            NOTE: If `outfile` is not provided, `infile` is overwritten instead.
            If neither was provided, an exception is raised.
            NOTE: This method will only update the progress bar if this edit
            has priority. Priority may change mid-operation and is gained
            whenever `len(gui.edits_in_progress) == 1`.

            `Edit.frame_rate` is a hint for the progress bar as to what frame
            rate to use when normal frame-output from FFmpeg is not available
            (such as for audio files) and we must convert timestamp-output to
            frames instead. If not provided, `gui.frame_rate` is used.

            `Edit.frame_count` is the target value that is used to calculate
            our current progress percentage. If not provided and this operation
            has priority, the progress bar switches to an indeterminate bar.

            `text` specifies the main text that will appear on the progress bar
            (while this edit has priority), surrounded by relevant information
            such as how many other edits are in progress and how many operations
            this edit has left. `start_text` (if provided) overrides `text`
            until the first progress update is parsed, and `percent_format` is
            the suffix that will be added to the end of `text`. It does not have
            to be an actual percentage. `QProgressBar`'s format variables:
            - %p - percent complete
            - %v - raw current value (frame)
            - %m - raw max value (frame count, or "?" if frame count is 0).

            If `text_override` is provided (and this edit has priority), `text`,
            `percent_format`, and `start_text` are all ignored, no other
            information is added, and `Edit.override_text` is set to True.

            NOTE: Temporary paths will be locked/unlocked if `infile` is
            already locked when you call this method.
            NOTE: This method used to optionally handle locking/unlocking and
            cleanup, but these features have since been removed. Please handle
            these things before/after calling this method (see: `gui._save()`).

            Returns the actual final output path. '''

        start = get_time()
        locked_files = gui.locked_files
        edits_in_progress = gui.edits_in_progress
        had_priority = len(edits_in_progress) == 1
        is_windows = constants.IS_WINDOWS
        logging.info(f'Performing FFmpeg operation (infile={infile} | outfile={outfile} | cmd={cmd})')

        # set title/text-format-related properties based on parameters and existing values
        self.override_text = bool(text_override)
        self.start_text = start_text or text_override or self.get_progress_text()
        self.text = text_override or text or self.text
        self.audio_track_titles = audio_track_titles or self.audio_track_titles
        if percent_format is not None:
            self.percent_format = percent_format

        # prepare the progress bar/taskbar/titlebar if no other edits are active
        if had_priority:
            self.has_priority = True                                # ↓ must set value to actually show the progress bar
            gui.set_save_progress_value_and_format_signal.emit(0, self.start_text)
            gui.set_save_progress_max_signal.emit(100 if self.frame_count else 0)
            gui.set_save_progress_visible_signal.emit(True)
            if is_windows and settings.checkTaskbarProgressEdit.isChecked():
                gui.taskbar_progress.reset()
            refresh_title()

        # validate `infile` if it was provided
        if infile:
            assert os.path.exists(infile), f'`infile` "{infile}" does not exist.'
            if not outfile:
                outfile = infile
                logging.info(f'`outfile` not provided, setting to `infile`: {infile}')
        elif not outfile:
            raise AssertionError('Both `infile` and `outfile` are invalid. This FFmpeg command is impossible.')

        try:
            # create temp file if `infile` and `outfile` are the same (ffmpeg can't edit files in-place)
            editing_in_place = False
            if infile:
                if infile == outfile:                               # NOTE: this happens in `gui._save()` w/ multiple operations
                    editing_in_place = True
                    temp_infile = add_path_suffix(infile, '_temp', unique=True)
                    if infile in locked_files:                      # if `infile` is already locked, lock the temp...
                        locked_files.add(temp_infile)               # ...path too, regardless of our `lock` parameter
                    os.rename(infile, temp_infile)                  # rename `infile` to our temporary name
                    logging.info(f'Renamed "{infile}" to temporary FFmpeg file "{temp_infile}"')
                else:
                    temp_infile = infile
            else:                                                   # no infile provided at all, so no temp path either
                temp_infile = ''

            # replace %in and %out with their respective (quote-surrounded) paths
            if '%out' not in cmd:                                   # ensure %out is present so we have a spot to insert `outfile`
                cmd += ' %out'

            # insert `-map 0` so all tracks are "mapped" to the final output
            # TODO: ffprobe can't parse track titles (LOL), so we need mediainfo if we want...
            # ...to get them on the fly, especially for edits like concatenation. incredible.
            if auto_map_tracks and '-map ' not in cmd:
                out = cmd.find(' %out')
                if self.audio_track_titles:                         # ffmpeg drops the track titles, so insert garbage metadata arguments
                    titles = ' '.join(                              # ↓ replace empty titles with something generic, like "Track 2"
                        f'-metadata:s:a:{index} title="{title.strip() or f"Track {index + 1}"}"'
                        for index, title in enumerate(self.audio_track_titles)
                    )
                    cmd = f'{cmd[:out]} -map 0 {titles}{cmd[out:]}'
                else:
                    cmd = f'{cmd[:out]} -map 0{cmd[out:]}'

            # run final ffmpeg command
            try:
                self._threads = settings.spinFFmpegThreads.value() if settings.checkFFmpegThreadOverride.isChecked() else 0
                process: subprocess.Popen = ffmpeg_async(
                    cmd=cmd.replace('%in', f'"{temp_infile}"').replace('%out', f'"{outfile}"'),
                    priority=settings.comboFFmpegPriority.currentIndex(),
                    threads=self._threads
                )
            except:
                logging.error(f'(!) FFMPEG FAILED TO OPEN: {format_exc()}')
                raise                                               # raise anyway so cleanup can occur

            self.process = process
            self.temp_dest = outfile
            self.operations_started += 1

            # update progress bar using the 'frame=???' lines from ffmpeg's stdout until ffmpeg is finished
            # https://stackoverflow.com/questions/67386981/ffmpeg-python-tracking-transcoding-process/67409107#67409107
            # TODO: 'total_size=', time spent, and operations remaining could also be shown (save_progress_bar.setFormat())
            frame_rate = max(1, self.frame_rate or gui.frame_rate)  # used when ffmpeg provides `out_time_ms` instead of `frame`
            use_outtime = True
            last_frame = 0
            lines_read = 0
            lines_to_log = []
            while True:
                if process.poll() is not None:                      # returns None if process hasn't terminated yet
                    break

                # if we're paused, continue sleeping but refresh title every second if necessary
                while self._is_paused:
                    sleep(1.0)
                    if len(edits_in_progress) > 1 and self.has_priority:
                        refresh_title()

                # edit cancelled -> kill this thread's ffmpeg process and cleanup
                if self._is_cancelled:
                    raise AssertionError('Cancelled.')

                # check if this thread lost priority
                if had_priority and not self.has_priority:
                    had_priority = False

                # check if this thread was manually set to control the progress bar
                if not had_priority and self.has_priority:
                    had_priority = True
                    self.give_priority()

                # check if this thread should automatically start controlling the progress bar, then...
                # ...sleep before parsing output -> sleep longer (update less frequently) while not visible
                if self.has_priority:
                    sleep(0.5)
                elif len(edits_in_progress) == 1:                   # NOTE: this doesn't actually get reached anymore i think
                    logging.info('(?) Old auto-priority-update code reached. This probably shouldn\'t be possible.')
                    had_priority = True
                    self.give_priority()
                    sleep(0.5)
                else:
                    sleep(0.5)                                      # split non-priority sleep into two parts so users can...
                    if not self.has_priority:                       # ...switch priority w/o too much delay before updates resume
                        sleep(0.5)

                # seek to end of current stdout output then back again to calculate how much data...
                # ...we'll need to read (we have to do it this way to get around pipe buffering)
                if is_windows:
                    start_index = process.stdout.tell()
                    process.stdout.seek(0, 2)
                    end_index = process.stdout.tell()
                    try:
                        process.stdout.seek(start_index, 0)         # seeking back sometimes throws an error?
                        progress_lines = process.stdout.read(end_index - start_index).split('\n')
                    except OSError:
                        logging.warning(f'(!) Failed to seek backwards from index {end_index} to index {start_index} in FFmpeg\'s stdout pipe, retrying...')
                        continue
                    except:
                        logging.warning('(!) Unexpected error while seeking or reading from FFmpeg\'s stdout pipe: ' + format_exc())
                        progress_lines = []

                # can't seek in streams on linux -> call & measure readline()'s delay until it buffers
                # NOTE: this is WAY less efficient and updates noticably slower when sleeping for the same duration. too bad lol
                else:
                    progress_lines = []
                    while process.poll() is None:                   # ensure we don't try to read a new line if process already ended
                        line_read_start = get_time()
                        progress_lines.append(process.stdout.readline().strip())
                        if not progress_lines[-1] or get_time() - line_read_start > 0.05:
                            break

            # >>> parse ffmpeg output <<<
                # loop over new stdout output without waiting for buffer so we can read output in...
                # ...batches and sleep between loops without falling behind, saving a lot of resources
                new_frame = last_frame
                for progress_line in progress_lines:
                    lines_read += 1
                    lines_to_log.append(f'FFmpeg output line #{lines_read}: {progress_line}')
                    if not progress_line:
                        logging.debug('FFmpeg output a blank progress line to STDOUT, leaving progress loop...')
                        break

                    # check for common errors
                    if progress_line[-6:] == 'failed':              # "malloc of size ___ failed"
                        if 'malloc of size' in progress_line:
                            raise AssertionError(progress_line)
                    elif 'do not match the corresponding output link' in progress_line:
                        raise AssertionError(progress_line)         # ^ concating videos with different dimensions

                    # normal videos will have a "frame=" progress string
                    if progress_line[:6] == 'frame=':
                        frame = min(int(progress_line[6:].strip()), self.frame_count)
                        if last_frame == frame and frame == 1:      # specific edits will constantly spit out "frame=1"...
                            use_outtime = True                      # ...for these scenarios, we should ignore frame output
                        else:
                            use_outtime = False                     # if we ARE using frames, don't use "out_time_ms" (less accurate)
                            new_frame = frame

                    # ffmpeg usually uses "out_time_ms" for audio files
                    elif use_outtime and progress_line[:12] == 'out_time_ms=':
                        try:
                            seconds = int(progress_line.strip()[12:-6])
                            new_frame = min(int(seconds * frame_rate), self.frame_count)
                        except ValueError:
                            pass

                # update progress bar to latest new frame (so we don't spam updates while parsing stdout)
                if new_frame != last_frame:
                    self.set_progress_bar(new_frame)
                last_frame = new_frame

                # batch-log all our newly read lines at once
                if lines_to_log:
                    progress_lines = '\n'.join(lines_to_log)
                    logging.debug(f'New FFmpeg output from {self}:\n{progress_lines}')
                    lines_to_log.clear()

            # terminate process just in case ffmpeg got locked up at the end
            try: process.terminate()
            except: pass

            # cleanup temp file, if needed (editing in place means we had to rename `infile`)
            if editing_in_place:
                qthelpers.deleteTempPath(temp_infile)

            log_on_statusbar(f'FFmpeg operation succeeded after {get_verbose_timestamp(get_time() - start)}.')
            return outfile

        except Exception as error:
            if lines_to_log:
                progress_lines = '\n'.join(lines_to_log)
                logging.debug(f'Final FFmpeg output leading up to error {self}:\n{progress_lines}')

            if str(error) == 'Cancelled.':
                log_on_statusbar('Cancelling...')
                logging.info(f'FFmpeg operation cancelled after {get_time() - start:.1f} seconds. Cleaning up...')
            else:
                log_on_statusbar(f'(!) FFmpeg operation failed after {get_verbose_timestamp(get_time() - start)}: {format_exc()}')

            # TODO: is there ever a scenario we DON'T want to kill ffmpeg here? doing this lets us delete `temp_infile`
            # TODO: add setting to NOT delete `temp_infile` on error? (here + `self._save()`)
            if self.process:
                kill_process(process)           # aggressively terminate ffmpeg process in case it's still running
            if editing_in_place:
                qthelpers.deleteTempPath(temp_infile, 'FFmpeg file')
            raise                               # raise exception anyway (we'll still go to the finally-statement)

        finally:
            if editing_in_place:                # always unlock our temporary path if necessary
                try:
                    locked_files.discard(temp_infile)
                except:
                    pass


class Undo:
    __slots__ = 'type', 'label', 'description', 'data'

    def __init__(self, type_: constants.UndoType, label: str, description: str, data: dict):
        self.type = type_
        self.label = label
        self.description = description
        self.data = data

        # TODO: add setting for max undos?
        if len(gui.undo_dict) > 50:
            for key in tuple(gui.undo_dict.items())[50:]:
                try: del gui.undo_dict[key]
                except: pass

    # TODO: should we do this here, in `gui.refresh_undo_menu`, or save lambdas as a property (`undo.action()`)?
    def execute(self):
        ''' Uses `self.data` to undo an action as defined by `self.type`.
            If successful, we remove ourselves from `gui.undo_dict`. '''
        try:
            if self.type == constants.UndoType.RENAME:
                if gui.undo_rename(self):
                    remove_dict_value(gui.undo_dict, self)
        except:
            log_on_statusbar(f'(!) Unexpected error while attempting undo: {format_exc()}')
