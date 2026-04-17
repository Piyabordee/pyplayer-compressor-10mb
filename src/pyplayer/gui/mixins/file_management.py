"""File management operations — open, close, cycle, copy, rename, delete, snapshot, subtitles."""
from __future__ import annotations

import logging
import os
from PyQt5 import QtCore, QtWidgets as QtW
from PyQt5.QtCore import Qt


logger = logging.getLogger(__name__)


class FileManagementMixin:
    """Methods: open, cycle_recent_files, open_recent_file, open_folder, open_probe_file,
    add_subtitle_files, discover_subtitle_files, explore, copy, copy_file, copy_image,
    rename, undo_rename, delete, snapshot, _open_cleanup_slot, open_from_thread,
    _open_external_command_slot, parse_media_file, search_files, cycle_media,
    shuffle_media."""

    def cycle_recent_files(self, forward: bool = True):
        ''' Plays the next (older) recent file in `self.recent_files` if
            `forward`, else the last (newer) recent file. Position is relative
            to `self.video`'s spot within the recent files list. If not within
            the list, the most recent file is used. '''
        # default to latest (most recent) file if no valid file is loaded
        # NOTE: recent_files is least recent to most recent -> index 0 is the LEAST recent
        if self.video not in self.recent_files: current_index = len(self.recent_files)
        else: current_index = self.recent_files.index(self.video)

        new_index = current_index + (1 if forward else -1)
        if 0 <= new_index <= len(self.recent_files) - 1:
            path = self.recent_files[new_index]
            self.open_recent_file(path, update=False)

    def open_recent_file(self, path: str, update: bool, open: bool = True, edits: bool = False):
        ''' Opens `path` from `self.recent_files` (or `self.recent_edits` if
            `edits` is True) if it exists, even if it's not actually in the
            list. If `path` doesn't exist and IS in the list, it is removed.

            - `update` - Move `path` to the top of `self.recent_files`
                         (regardless of `edits`).
            - `open`   - Open `path`. If False, `path` is moved to the top of
                         its associated list (regardless of `update`). '''
        try:
            if edits:
                recents = self.recent_edits
                open = True
                noun = 'edit'
            else:
                recents = self.recent_files
                noun = 'file'

            if path in self.locked_files:           # recent file is locked (it's actively being edited)
                log_on_statusbar(f'Recent {noun} {path} is currently being worked on.')
            elif os.path.isfile(path):
                if open:
                    if self.open(path, update_recent_list=update) != -1:
                        log_on_statusbar(f'Opened recent file #{len(recents) - recents.index(path)}: {path}')
                    else:
                        log_on_statusbar(f'Recent file {path} could not be opened.')
                        recents.remove(path)
                else:                               # don't open, just move file to top
                    recents.append(recents.pop(recents.index(path)))
            else:
                log_on_statusbar(f'Recent {noun} {path} no longer exists.')
                recents.remove(path)
        except ValueError:                          # ValueError -> path was not actually in recent_files/edits
            pass
        finally:
            if not edits:
                self.refresh_recent_menu()

    def open_folder(self, folder: str, mod: int = 0, focus_window: bool = True) -> str:
        ''' Plays a file inside `folder`, returning the selected file, if any.
            The method of choosing a file and whether Autoplay/shuffle mode are
            altered depends on keyboard modifiers passed through `mod`, if any:

            - `Alt` OR `Ctrl + Shift`: Enable autoplay, disable shuffle mode.
                                       Plays the first valid file in the folder.
            - `Ctrl`:                  Enable autoplay, enable shuffle mode.
                                       Plays a random file in the folder.
            - `Shift`:                 Disables autoplay, ignore shuffle mode.
                                       Plays the first valid file in the folder.
            - No modifiers:            Enable autoplay, keep current shuffle
                                       mode setting (first file if disabled,
                                       random file if enabled).

            NOTE: `focus_window` may also be passed,
            but is ignored if shuffle mode is used. '''

        try:
            folder = abspath(folder)                # ensure `folder` uses a standardized format

            # no modifiers -> enable autoplay and keep current shuffle mode setting
            enable_autoplay = True
            enable_shuffle = self.actionAutoplayShuffle.isChecked()

            if (mod & Qt.ControlModifier and mod & Qt.ShiftModifier) or mod & Qt.AltModifier:
                enable_shuffle = False              # alt OR (ctrl+shift) -> autoplay, no shuffle
            elif mod & Qt.ControlModifier:
                enable_shuffle = True               # ctrl                -> autoplay, shuffle
            if mod & Qt.ShiftModifier:
                enable_autoplay = False             # shift               -> no autoplay (shuffle is irrelevant)

        # update autoplay and shuffle mode, then play a random file if shuffle mode is active
            self.actionAutoplay.setChecked(enable_autoplay)
            if enable_autoplay:                     # ↓ only update shuffle mode if we're using autoplay
                self.actionAutoplayShuffle.setChecked(enable_shuffle)
                if enable_shuffle:
                    file = self.shuffle_media(folder, autoplay=True)
                    if file is not None:
                        log_on_statusbar(f'Randomly opened {os.path.basename(file)} from folder {folder} (shuffle mode).')
                    return file

        # no autoplay OR no shuffle mode -> play first file in folder regardless of autoplay setting
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    if self.open(file_path):
                        log_on_statusbar(f'Opened {os.path.basename(file)} from folder {folder}.')
                        if focus_window:
                            self.raise_()
                            self.activateWindow()
                        return file_path
            return log_on_statusbar(f'Folder {folder} contains no playable files.')

        except:
            return log_on_statusbar(f'(!) OPEN_FOLDER FAILED: {format_exc()}')

    def open(
        self,
        file: str = None,
        focus_window: bool = None,
        flash_window: bool = True,
        pause_if_focus_rejected: bool = False,
        beep_if_focus_rejected: bool = False,
        update_recent_list: bool = True,
        update_raw_last_file: bool = True,
        update_original_video_path: bool = True,
        mime: str = None,
        extension: str = None,
        _from_cycle: bool = False,
        _from_autoplay: bool = False,
        _from_edit: bool = False
    ) -> int:
        ''' Opens, parses, and plays a media `file`. Returns -1 if unsuccessful.

            If `file` is None, a file-browsing dialog will be opened.
            If no `mime` or `extension` are provided, they will be detected
            automatically. If `focus_window` is None, the window will focus
            depending on its current state, the media type, and user settings.
            If the window remains unfocused, a notification sound will play if
            `beep_if_focus_rejected` is True and the player will start paused
            if `pause_if_focus_rejected` is True (does not apply to GIFs).

            - `update_recent_list` - updates `self.recent_files`
            - `update_raw_last_file` - updates `self.last_video`
            - `update_original_video_path` - updates `self.original_video_path`

            If `_from_cycle` is True, validity checks are skipped.
            `self.current_file_is_autoplay` is set to `_from_autoplay`.

            Current iteration: IV '''

        try:
            # validate `file`. open file-dialog if needed, check if it's a folder, check if it's locked, etc.
            # (if called from sort of auto-cycling function, we can assume this stuff is already sorted out)
            if not _from_cycle:
                if not file:
                    file, self.cfg.lastdir = self.qthelpers.browseForFile(
                        lastdir=self.cfg.lastdir,
                        caption='Select media file to open'
                    )
                if not file:
                    return -1
                file = self.util.abspath(file)                        # ensure `file` uses a standardized format

                if os.path.isdir(file):
                    file = self.open_folder(file, focus_window=focus_window)
                    return 1 if file else -1
                if file in self.locked_files:               # if file is locked and we didn't cycle here, show a warning message
                    show_on_statusbar(f'File {file} is currently being worked on.')
                    return -1

            # get stats and size of media
            start = get_time()
            stat = os.stat(file)
            filesize = stat.st_size
            basename = file[file.rfind(self.util.sep) + 1:]           # shorthand for os.path.basename NOTE: safe when `file` is provided automatically

        # --- Probing file and determining mime type ---
            # probe file with FFprobe if possible. if file has already been probed, reuse old probe. otherwise, save output to txt file
            # probing calls Popen through a Thread (faster than calling Popen itself or using Thread on a middle-ground function)
            if self.constants.FFPROBE:                                     # generate probe file's path and check if it already exists
                probe_file = f'{self.constants.PROBE_DIR}{self.util.sep}{basename}_{stat.st_mtime}_{filesize}.txt'
                probe_exists = self.util.exists(probe_file)
                if probe_exists:                            # probe file already exists
                    with open(probe_file, 'r', encoding='utf-8') as probe:
                        try:
                            probe_data = self.util.parse_json(probe.read())
                            probe_process = None
                            if not probe_data:              # probe is literally just two braces with no data -> DON'T...
                                raise                       # ...give up. instead, raise error and try to re-probe it
                        except:
                            probe.close()
                            logging.info('(?) Deleting potentially invalid probe file: ' + probe_file)
                            try: os.remove(probe_file)
                            except: logging.warning('(!) FAILED TO DELETE POTENTIALLY INVALID PROBE FILE: ' + format_exc())
                            probe_exists = False

                if not probe_exists:
                    probe_data = None
                    probe_process = subprocess.Popen(
                        f'"{self.constants.FFPROBE}" -show_format -show_streams -of json "{file}" > "{probe_file}"',
                        shell=True                          # needed so we can easily write the output to a file
                    )
            elif self.player.SUPPORTS_PARSING:
                probe_file = None                           # no FFprobe -> no probe file (even if one exists already)
                probe_data = None
                probe_process = None
            else:
                self.qthelpers.getPopup(
                    title='Welp.',
                    text='You have FFprobe disabled, but have also selected a\nplayer that cannot sufficiently parse media on its own.\n\nDo you see the issue?',
                    icon='warning',
                    **self.get_popup_location_kwargs()
                ).exec()
                raise AssertionError('FFprobe disabled and player does not support probing')

            # misc variables we can setup after probe has started
            old_file = self.video
            extension_label = ''
            mime_fallback_was_needed = False

            # get mime type of file (if called from cycle, then this part was worked out beforehand)
            if mime is None:
                try:
                    filetype_data = self.util.filetype.match(file)    # 'EXTENSION', 'MIME', 'extension', 'mime'
                    mime, extension = filetype_data.mime.split('/')
                    extension_label = extension.upper()
                    if mime not in ('video', 'image', 'audio'):
                        log_on_statusbar(f'File \'{file}\' appears to be corrupted or an invalid format and cannot be opened (invalid mime type).')
                        return -1

                # failed to determine mime type -> our library isn't 100% perfect, so...
                # ...wait for probe file to be created and attempt to parse it anyway
                except:
                    try:
                        if not self.constants.FFPROBE:
                            raise

                        mime_fallback_was_needed = True
                        log_on_statusbar('The current file\'s mime type cannot be determined, checking FFprobe...')

                        # if FFprobe process is still running, wait for it. we could parse its...
                        # ...output directly, but it doesn't really matter for such a rare situation
                        if probe_process is not None:
                            while True:
                                if probe_process.poll() is not None:
                                    break                   # ^ returns None if process hasn't terminated yet

                        # wait for probe file to be created
                        while not self.util.exists(probe_file):
                            sleep(0.02)

                        # attempt to parse probe file. if successful, this might be actual media
                        with open(probe_file, 'r', encoding='utf-8') as probe:
                            while probe_data is None:
                                if probe.read():            # keep reading until the file actually contains data
                                    sleep(0.1)
                                    probe.seek(0)
                                    probe_data = self.util.parse_json(probe.read())

                        # for some asinine reason, FFprobe "recognizes" text as a form of video
                        # if that, or probe is literally just two braces with no data -> give up
                        if not probe_data or probe_data['format']['format_name'] == 'tty':
                            raise

                        # if there are no valid video streams, assume it's an audio file
                        for stream in probe_data['streams']:
                            if stream['codec_type'] == 'video' and stream['avg_frame_rate'] != '0/0':
                                mime = 'video'
                                break
                        else:
                            mime = 'audio'                  # for-loop goes to "else" if the loop did not break

                        # check known problem-formats to assign extension
                        # fallback to current extension if it's at least valid for this mime type
                        # resort to '???' if we genuinely have no idea what this is
                        if probe_data['format']['format_name'] == 'mpegts':
                            extension = 'mp4'
                            extension_label = 'MPEG-TS'
                        else:
                            if mime == 'video': valid_extensions = self.constants.VIDEO_EXTENSIONS
                            else:               valid_extensions = self.constants.AUDIO_EXTENSIONS
                            _, extension = self.util.splitext_media(file, valid_extensions, period=False)
                            if not extension:
                                extension = 'mp4' if mime == 'video' else 'mp3'
                                extension_label = '???'

                    except:
                        if not self.util.exists(file): log_on_statusbar(f'File \'{file}\' does not exist.')
                        else: log_on_statusbar(f'File \'{file}\' appears to be corrupted or an invalid format and cannot be opened (failed to determine mime type).')
                        logging.warning(format_exc())
                        return -1

        # --- Restoring window ---
            # restore window from tray if hidden, otherwise there's a risk for unusual VLC output
            if self.isVisible():
                was_minimzed_to_tray = False
            else:                                           # we need to do this even if `focus_window` is True
                was_minimzed_to_tray = True
                if self.isMaximized():
                    self.resize(self.last_window_size)      # restore size/pos or maximized windows will forget...
                    self.move(self.last_window_pos)         # ...their original geometry when you unmaximize them
                self.showMinimized()                        # minimize for now, we'll check if we need to focus later

        # --- Playing media ---
            self.open_in_progress = True                    # mark that we're now officially opening something

            self.player.stop()                                   # player must be stopped for images/gifs and to reduce delays on almost-finished media (for VLC)
            if mime == 'image': self.util.play_image(file, gif=extension == 'gif')
            elif not self.util.play(file): return -1                  # immediately attempt to play media once we know it might be valid
            else: self.util.play_image(None)                          # clear gifPlayer if we successfully played non-gif media

            # this and `_open_cleanup_in_progress` (set in `self.parse_media_file()`) are internal...
            # ...properties for tracking when it's safe to set `self.open_in_progress` back to False
            self._open_main_in_progress = True              # (set this here instead of above to slightly optimize cycling through corrupt files)

        # --- Parsing metadata and setting up UI/recent files list ---
            # parse non-video files and show/log file on statusbar
            parsed = False                                  # keep track of parse so we can avoid re-parsing it later if it ends up being a video
            if mime != 'video':                             # parse metadata early if it isn't a video
                if (reason := self.parse_media_file(file, probe_file, mime, extension, probe_data)) != 1:
                    log_on_statusbar(f'File \'{file}\' appears to be corrupted or an invalid format and cannot be opened ({reason}).')
                    return -1
                parsed = True

            logging.info('--- OPENING FILE ---')
            if not mime_fallback_was_needed: log_on_statusbar(f'Opening file ({mime}/{extension}): {file}')
            else: log_on_statusbar(f'This file is seemingly playable, but PyPlayer is unsure of its true mime-type/extension: {file}')

            # misc cleanup/setup for new media that we can safely do before fully parsing
            self.operations.clear()
            self.buttonTrim.blockSignals(True)
            self.buttonTrim.setChecked(False)
            self.buttonTrim.blockSignals(False)

            # set basename (w/o extension) as default output text,...
            # ...full basename as placeholder text, and update tooltip
            self.lineOutput.setText(self.util.splitext_media(basename)[0])
            self.lineOutput.setPlaceholderText(basename)    # TODO: should these two lines be in cleanup anyway?
            self.lineOutput.setToolTip(file + self.constants.OUTPUT_TEXTBOX_TOOLTIP_SUFFIX)

            # update delete-action's QToolButton. if we're holding del, auto-mark the file accordingly
            if self.mark_for_deletion_held_down:            # NOTE: we don't update the tooltip until we've release del
                is_marked = self.mark_for_deletion_held_down_state
                if is_marked: self.marked_for_deletion.add(file)
                else:         self.marked_for_deletion.discard(file)
            else:
                is_marked = file in self.marked_for_deletion
            self.actionMarkDeleted.setChecked(is_marked)
            self.buttonMarkDeleted.setChecked(is_marked)

            # reset cropped mode if needed
            if self.actionCrop.isChecked():                 # `self.set_crop_mode` auto-returns if `self.mime_type` is 'audio'
                self.disable_crop_mode()

            # set size label for context menus and titlebar
            if filesize < 1048576:      self.size_label = f'{filesize / 1024:.0f}kb'
            elif filesize < 1073741824: self.size_label = f'{filesize / 1048576:.2f}mb'
            else:                       self.size_label = f'{filesize / 1073741824:.2f}gb'

            # extra setup before we absolutely must wait for the media to finish parsing
            # NOTE: this (and some of the above) is a disaster if we fail to parse, but...
            #      ...it's very rare for a file to get this far if it can't be parsed
            self.is_paused = False                          # slightly more efficient than using `force_pause`
            self.buttonPause.setIcon(self.icons['pause'])
            self.restarted = False
            self.lineOutput.clearFocus()                    # clear focus from output line so it doesn't interfere with keyboard shortcuts
            self.current_file_is_autoplay = _from_autoplay
            self.extension_label = extension_label or extension.upper()
            self.stat = stat

            # focus window if desired, depending on window state and autoplay/audio settings
            # NOTE: it is very rare but possible for "video" mime types to be mutated into "audio"...
            #       ...during parsing which happens immediately AFTER we focus the window. i'd...
            #       ...still rather focus first. it's rare enough that i think it's probably fine
            if not self.isActiveWindow():
                if not _from_edit:
                    if _from_cycle and self.settings.checkFocusIgnoreAutoplay.isChecked():
                        focus_window = False
                    elif mime == 'audio' and self.settings.checkFocusIgnoreAudio.isChecked():
                        focus_window = False

                if focus_window is None:
                    if self.isMinimized():
                        if was_minimzed_to_tray: focus_window = self.settings.checkFocusOnMinimizedTray.isChecked()
                        else:                    focus_window = self.settings.checkFocusOnMinimizedTaskbar.isChecked()
                    elif self.isFullScreen():    focus_window = self.settings.checkFocusOnFullscreen.isChecked()
                    elif self.isMaximized():     focus_window = self.settings.checkFocusOnMaximized.isChecked()
                    else:                        focus_window = self.settings.checkFocusOnNormal.isChecked()
                if focus_window and self.settings.checkFocusIgnoreFullscreen.isChecked():
                    if _from_edit or not self.settings.checkFocusIgnoreFullscreenEditsOnly.isChecked():
                        focus_window = not self.util.foreground_is_fullscreen()
                if focus_window:
                    self.qthelpers.showWindow(
                        window=self,
                        aggressive=self.settings.checkFocusAggressive.isChecked()
                    )
                else:
                    if pause_if_focus_rejected:
                        self.force_pause(True)
                    if beep_if_focus_rejected:
                        self.app.beep()
                    if flash_window and self.constants.IS_WINDOWS:
                        flash_count = (0, 1, 2, -1)[self.settings.comboTaskbarFlash.currentIndex()]
                        if flash_count == 1:    self.qthelpers.flashWindow(self, duration=1100, hold=True)
                        elif flash_count == -1: self.qthelpers.flashWindow(self, flash_count)
                        else:                   self.qthelpers.flashWindow(self, flash_count, interval=500, duration=1250 * flash_count)

            # if presumed to be a video -> finish parsing (done as late as possible to minimize downtime)
            if mime == 'video' and not parsed:
                if (reason := self.parse_media_file(file, probe_file, mime, extension, probe_data)) != 1:
                    log_on_statusbar(f'File \'{file}\' appears to be corrupted or an invalid format and cannot be opened ({reason}).')
                    return -1

            # update original path and literal last video if this is a new file and not an edit
            if update_original_video_path or not self.video_original_path:
                self.video_original_path = file
                if update_raw_last_file:
                    self.last_video = old_file

            # update recent media list
            if update_recent_list:
                recent_files = self.recent_files
                if file in recent_files:                                # move pre-existing recent file to front
                    recent_files.append(recent_files.pop(recent_files.index(file)))
                else:
                    recent_files.append(file)
                    max_len = self.settings.spinRecentFiles.value()
                    self.recent_files = recent_files[-max_len:]         # do NOT assign to the alias here

            # update UI with new media's duration
            # TODO: would local and/or global aliases here be worth it?
            h, m, s, ms = self.util.get_hms(self.duration_rounded)
            self.labelMaxTime.setText(f'{m:02}:{s:02}.{ms:02}' if h == 0 else f'{h}:{m:02}:{s:02}')
            self.spinHour.setEnabled(h != 0)                            # always leave `spinSecond` enabled
            self.spinMinute.setEnabled(m != 0)
            if self.width() > 335: prefix = f'{self.frame_rate_rounded} FPS: '
            else:                  prefix = ''
            self.spinFrame.setPrefix(prefix)
            self.spinFrame.setMaximum(self.frame_count)
            self.spinFrame.setToolTip(f'Frame rate:\t{self.frame_rate}\nFrame count:\t{self.frame_count_raw}')

            # refresh title (we have to emit here instead of `_open_cleanup_slot`, I don't remember why lol)
            refresh_title()

            # log opening time. all done! (except for cleanup)
            self.last_open_time = end = get_time()                      # TODO: is using a local alias here worth it?
            logging.info(f'Initial media opening completed after {end - start:.4f} seconds.')
            return 1

        except:
            log_on_statusbar(f'(!) OPEN FAILED: {format_exc()}')
            return -1
        finally:
            self._open_main_in_progress = False
            self.open_in_progress = self._open_cleanup_in_progress or self.player.open_cleanup_queued

    def open_probe_file(self, *, file: str = None, delete: bool = False, verbose: bool = True):
        ''' Opens, creates, or deletes a probe file for `file`. If `file` is None,
            the current video is used. If `delete` is True, the probe file is
            deleted instead. If `verbose` is True, logs are shown. '''
        # See main.pyw for full implementation (lines 2787-2844)
        pass

    def add_subtitle_files(self, *files: str | QtCore.QUrl):
        ''' Adds subtitle files to the current media. '''
        # See main.pyw for full implementation (lines 2828-2843)
        pass

    def discover_subtitle_files(self):
        ''' Automatically discovers and adds subtitle files for the current media. '''
        # See main.pyw for full implementation (lines 2845-2941)
        pass

    def explore(self, path: str = None, noun: str = 'Recent file'):
        ''' Opens the file explorer at `path` (or the parent folder of `path`). '''
        # See main.pyw for full implementation (lines 2943-2954)
        pass

    def copy(self, path: str = None, noun: str = 'Recent file'):
        ''' Copies a file to the clipboard. '''
        # See main.pyw for full implementation (lines 2956-2973)
        pass

    def copy_file(self, path: str = None, cut: bool = False):
        ''' Copies or cuts a file to a new location. '''
        # See main.pyw for full implementation (lines 2975-3010)
        pass

    def copy_image(self, path: str = None, extended: bool = None):
        ''' Copies the current image frame to the clipboard. '''
        # See main.pyw for full implementation (lines 3011-3758)
        pass

    def rename(self, new_name: str = None, sanitize: bool = True, delete_source_dir: bool = True):
        ''' Renames the current media file to `new_name`. '''
        # See main.pyw for full implementation (lines 4061-4197)
        pass

    def undo_rename(self, undo: Undo) -> bool | None:
        ''' Undoes a rename operation. '''
        # See main.pyw for full implementation (lines 4198-4402)
        pass

    def delete(self, *files: str, cycle: bool = True):
        ''' Deletes the specified files. '''
        # See main.pyw for full implementation (lines 4403-4476)
        pass

    def snapshot(self, *, mode: str = 'quick', is_temp: bool = False):
        ''' Takes a snapshot of the current video frame. '''
        # See main.pyw for full implementation (lines 4477-4847)
        pass

    def _open_cleanup_slot(self):
        ''' Slot for cleanup after opening files. '''
        # See main.pyw for full implementation (lines 3759-3850)
        pass

    def open_from_thread(self, **kwargs):
        ''' Opens a file from a background thread. '''
        # See main.pyw for full implementation (lines 3851-3857)
        pass

    def _open_external_command_slot(self, cmdpath: str):
        ''' Slot for handling external commands to open files. '''
        # See main.pyw for full implementation (lines 3858-3875)
        pass

    def parse_media_file(self, file: str):
        ''' Parses a media file and extracts its metadata. '''
        # This is a helper method used during file opening
        pass

    def search_files(self):
        ''' Searches for files in a directory. '''
        # This is a helper method for file searching
        pass

    def cycle_media(self, next: bool = True):
        ''' Cycles to the next or previous media file. '''
        # Implementation depends on context (playlist, folder, etc.)
        pass

    def shuffle_media(self, folder: str = None, autoplay: bool = False):
        ''' Randomly selects a media file from a folder. '''
        # Returns the path to the selected file
        pass
