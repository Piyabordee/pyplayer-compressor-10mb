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

    # NOTE: This method is very long - see main.pyw for full implementation
    def open(self, *args, **kwargs):
        ''' Opens a media file, handles all the parsing and setup.
            Full implementation is in main.pyw around line 2338-3759. '''
        # This is a placeholder - the actual method is very long and complex
        pass

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
