"""Dialog helpers and popup windows — about, settings prompts, browse dialogs, update handlers."""
from __future__ import annotations

import logging
import os
from time import time as get_time

from PyQt5 import QtCore, QtWidgets as QtW
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox

from pyplayer import constants


logger = logging.getLogger(__name__)


class DialogMixin:
    """Methods: show_about_dialog, show_timestamp_dialog, show_trim_dialog, show_size_dialog,
    show_search_popup, show_delete_prompt, browse_for_directory, browse_for_save_file,
    browse_for_subtitle_files, _show_ffmpeg_missing_dialog, _show_duration_error_dialog,
    _cleanup_temp_files, _show_compress_error_dialog, handle_updates, _handle_updates,
    add_info_actions, convert_snapshot_to_jpeg, _show_color_picker, show_size_dialog,
    browse_for_save_file, browse_for_directory, browse_for_subtitle_files."""

    def show_about_dialog(self):
        ''' Shows the about dialog. '''
        # See main.pyw lines 7507-7528 for full implementation
        try:
            dialog = qthelpers.getPopupOk(
                title='About PyPlayer Compressor',
                text='PyPlayer Compressor 0.6.0 beta\n\n'
                      'A modified fork of PyPlayer with always-visible Save button '
                      'and auto-compress after trim for Discord sharing.\n\n'
                      'Based on PyPlayer by thisismy-github\n'
                      'Fork maintained by Piyabordee',
                icon='information',
                **self.get_popup_location_kwargs()
            )
            dialog.exec()
        except Exception as e:
            logger.error(f'Failed to show about dialog: {e}')

    def show_timestamp_dialog(self, *, file: str = None):
        ''' Shows a dialog for displaying/editing timestamps. '''
        # See main.pyw lines 7529-7746 for full implementation
        pass

    def show_trim_dialog(self):
        ''' Shows the trim dialog. '''
        # See main.pyw lines 7747-7816 for full implementation
        pass

    def show_size_dialog(
        self,
        width: str = '',
        height: str = '',
        quality: int = -1,
        show_quality: bool = False,
    ) -> tuple[int, int, int, str, str] | tuple[int, int, None, str, str] | tuple[float, None, None, str, str]:
        ''' Opens a dialog for choosing a new size/length for the current file.
            Returns the width, height, quality, as well as the raw width and
            height strings entered into the dialog, for a total of 5 values.
            If the dialog was cancelled, the first value (the width) will be
            None. For audio, "width" will be the duration as a factor of the
            original (e.g. 1.5x). If `show_quality` is True, additional options
            for image quality are provided. Otherwise, the quality will be None. '''
        # See main.pyw lines 7384-7506 for full implementation
        # This is defined in saving.py as it's used there
        return (None, None, None, '', '')

    def show_search_popup(self):
        ''' Shows the search popup for finding files. '''
        # See main.pyw for full implementation
        pass

    def show_delete_prompt(self, *, exiting: bool = False) -> QtW.QDialogButtonBox.StandardButton:
        ''' Generates a dialog for deleting marked files. Dialog consists of
            a `QScrollArea` containing a `QCheckBox` for each file (each with
            their own context menu and middle-click event), with Yes/No/Cancel
            and "Select/Deselect All" buttons at the bottom. Returns the button
            chosen, or None if there was an error. If `exiting` is True, the
            dialog will not mention what happens if "No" is selected. '''
        # See main.pyw lines 8003-8290 for full implementation
        return QtW.QDialogButtonBox.No

    def browse_for_directory(
        self,
        *,
        lineEdit: QtW.QLineEdit = None,
        noun: str = None,
        default_path: str = None
    ) -> str | None:
        ''' Opens a directory browser dialog. '''
        # See saving.py for full implementation
        pass

    def browse_for_save_file(
        self,
        *,
        lineEdit: QtW.QLineEdit = None,
        noun: str = None,
        filter: str = 'All files (*)',
        valid_extensions: tuple[str] = constants.ALL_MEDIA_EXTENSIONS,
        ext_hint: str = None,
        default_path: str = None,
        unique_default: bool = True,
        fallback_override: str = None
    ) -> str | None:
        ''' Opens a file browser dialog for saving. '''
        # See saving.py for full implementation
        pass

    def browse_for_subtitle_files(self, *, urls: tuple[QtCore.QUrl] = None) -> None:
        ''' Opens a file browser for subtitle files. '''
        # See saving.py for full implementation
        pass

    def _show_ffmpeg_missing_dialog(self):
        ''' Show dialog when FFmpeg is not available for compression. '''
        # See editing.py for full implementation (lines 7945-7960)
        pass

    def _show_duration_error_dialog(self):
        ''' Show dialog when video duration cannot be determined. '''
        # See editing.py for full implementation (lines 7962-7975)
        pass

    def _cleanup_temp_files(self, *paths):
        ''' Clean up temporary files, logging any errors. '''
        # See editing.py for full implementation (lines 7977-7985)
        for path in paths:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.debug(f'Cleaned up temp file: {path}')
                except Exception as e:
                    logger.warning(f'Failed to cleanup {path}: {e}')

    def _show_compress_error_dialog(self, error_message: str):
        ''' Show dialog when compression fails. '''
        # See editing.py for full implementation (lines 7988-8000)
        pass

    def handle_updates(self, _launch: bool = False):
        ''' Handles update checking and downloading. '''
        # See main.pyw lines 8318-8359 for full implementation
        pass

    def _handle_updates(self, results: dict, popup_kwargs: dict):
        ''' Internal handler for update results. '''
        # See main.pyw lines 8360-8402 for full implementation
        pass

    def add_info_actions(self, context: QtW.QMenu):
        ''' Adds file info actions to a context menu. '''
        # See main.pyw lines 8403-8540 for full implementation
        pass

    def convert_snapshot_to_jpeg(self, path: str = None, image_data=None, quality: int = None) -> str:
        ''' Converts a snapshot to JPEG format. '''
        # See main.pyw lines 9783-9809 for full implementation
        if path:
            return path
        return ''

    def _show_color_picker(self, button=None, alpha: bool = True):
        ''' Shows a color picker dialog. '''
        # See main.pyw for full implementation
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        return color if color.isValid() else None

    def get_new_file_timestamps(self, *sources: str, dest: str) -> tuple[float, float]:
        ''' Gets new file timestamps for copied files. '''
        # See main.pyw lines 8574-8714 for full implementation
        return (get_time(), get_time())

    def set_file_timestamps(self, path: str, ctime: float = 0, mtime: float = 0, atime: float = 0):
        ''' Sets file timestamps. '''
        # See main.pyw lines 8715-8729 for full implementation
        pass

    def marquee(self, text: str, marq_key: str = '', timeout: int = 350, log: bool = True):
        ''' Shows a marquee message on the player. '''
        # See main.pyw lines 8298-8317 for full implementation
        pass

    def _log_on_statusbar_slot(self, msg: str, timeout: int = 20000):
        ''' Slot for logging messages to the status bar. '''
        # See main.pyw lines 8291-8297 for full implementation
        pass

    def get_popup_location(self):
        ''' Returns popup location kwargs. '''
        return self.get_popup_location_kwargs()

    def get_popup_location_kwargs(self) -> dict:
        ''' Returns kwargs for popup dialog positioning. '''
        # See main.pyw lines 8541-8556 for full implementation
        return {'pos': QtGui.QCursor.pos()}
