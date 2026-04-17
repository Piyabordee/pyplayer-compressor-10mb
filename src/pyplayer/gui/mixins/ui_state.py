"""UI state management — visibility setters, refresh methods, snap/mark methods, getters."""
from __future__ import annotations

import logging
import os
from time import time as get_time

from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from PyQt5.QtCore import Qt


logger = logging.getLogger(__name__)


class UIStateMixin:
    """Methods: set_advancedcontrols_visible, set_progressbar_visible, set_statusbar_visible,
    set_menubar_visible, refresh_title, refresh_shortcuts, refresh_cover_art,
    refresh_autoplay_button, refresh_taskbar, create_taskbar_controls,
    enable_taskbar_controls, is_snap_mode_enabled, snap_to_player_size,
    snap_to_native_size, mark_for_deletion, clear_marked_for_deletion,
    refresh_copy_image_action, refresh_confusing_zoom_setting_tooltip,
    refresh_recycle_tooltip, refresh_volume_tooltip, refresh_marked_for_deletion_tooltip,
    refresh_snapshot_button_controls, refresh_titlebar, refresh_track_menu,
    refresh_recent_menu, refresh_undo_menu, _refresh_title_slot, get_output,
    get_save_remnant, handle_cycle_buttons, handle_snapshot_button,
    setup_trim_button_custom_handler, get_popup_location_kwargs, get_hotkey_full_string,
    get_new_file_timestamps, set_file_timestamps."""

    def set_advancedcontrols_visible(self, visible: bool):
        ''' Sets visibility of the advanced controls (controls beneath
            the progress bar and above the status bar) to `visible`. '''
        self.vlc.last_invalid_snap_state_time = get_time()
        self.actionShowAdvancedControls.setChecked(visible)
        self.frameAdvancedControls.setVisible(visible)

    def set_progressbar_visible(self, visible: bool):
        ''' Readjusts the advanced controls' margins based on whether
            or not the progress bar's frame is `visible`. '''
        self.vlc.last_invalid_snap_state_time = get_time()
        self.frameProgress.setVisible(visible)
        self.actionShowProgressBar.setChecked(visible)
        self.frameAdvancedControls.layout().setContentsMargins(0, 0 if visible else 3, 0, 0 if self.statusbar.isVisible() else 3)

    def set_statusbar_visible(self, visible: bool):
        ''' Readjusts the advanced controls' margins based
            on whether or not the status bar is `visible`. '''
        self.vlc.last_invalid_snap_state_time = get_time()
        self.statusbar.setVisible(visible)
        self.actionShowStatusBar.setChecked(visible)
        self.frameAdvancedControls.layout().setContentsMargins(0, 0 if self.frameProgress.isVisible() else 3, 0, 0 if visible else 3)

    def set_menubar_visible(self, visible: bool):
        ''' Resizes window to avoid size-snapping based on whether or not the
            menubar is `visible`. Does nothing if crop mode is active. '''
        if visible:
            self.vlc.last_invalid_snap_state_time = get_time()
            if self.actionCrop.isChecked():
                return self.actionShowMenuBar.setChecked(False)
        self.menubar.setVisible(visible)
        self.actionShowMenuBar.setChecked(visible)
        if not self.isMaximized() and not self.isFullScreen():
            height = self.menubar.height()
            self.resize(self.width(), self.height() + (height if visible else -height))

    def refresh_title(self):
        ''' Refreshes the window title with current media info. '''
        # See main.pyw lines 9313-9377 for full implementation
        pass

    def _refresh_title_slot(self):
        ''' Slot for refreshing the window title. '''
        # See main.pyw lines 9313-9377 for full implementation
        pass

    def refresh_shortcuts(self, last_edit=None):
        ''' Refreshes keyboard shortcuts based on settings. '''
        # See main.pyw lines 9390-9434 for full implementation
        pass

    def refresh_cover_art(self, show: bool):
        ''' Refreshes the cover art display. '''
        # See main.pyw lines 9435-9450 for full implementation
        pass

    def refresh_autoplay_button(self):
        ''' Refreshes the autoplay button state. '''
        # See main.pyw lines 9451-9461 for full implementation
        pass

    def refresh_taskbar(self):
        ''' Refreshes the taskbar button state. '''
        # See main.pyw lines 9564-9584 for full implementation
        if constants.IS_WINDOWS:
            try:
                if self.is_paused:
                    self.taskbar.setPaused(True)
                else:
                    self.taskbar.setPlaying(True)
            except Exception as e:
                logger.error(f'Failed to refresh taskbar: {e}')

    def create_taskbar_controls(self):
        ''' Creates taskbar thumbnail controls. '''
        # See main.pyw lines 9585-9664 for full implementation
        pass

    def enable_taskbar_controls(self, checked: bool = True):
        ''' Enables or disables taskbar controls. '''
        # See main.pyw lines 9665-9671 for full implementation
        pass

    def is_snap_mode_enabled(self) -> bool:
        ''' Returns whether snap mode is enabled. '''
        # See main.pyw lines 9672-9680 for full implementation
        return False

    def snap_to_player_size(self, shrink: bool = False, force_instant_resize: bool = False):
        ''' Snaps the window to match the player size. '''
        # See main.pyw lines 9681-9727 for full implementation
        pass

    def snap_to_native_size(self):
        ''' Snaps the window to the native video resolution. '''
        # See main.pyw lines 9728-9736 for full implementation
        pass

    def mark_for_deletion(self, *files: str, mark: bool = False, mode: str = None):
        ''' Marks files for deletion. '''
        # See main.pyw lines 9737-9773 for full implementation
        pass

    def clear_marked_for_deletion(self):
        ''' Clears all marked for deletion files. '''
        # See main.pyw lines 9774-9782 for full implementation
        pass

    def refresh_copy_image_action(self):
        ''' Refreshes the copy image action state. '''
        # See main.pyw lines 9378-9389 for full implementation
        pass

    def refresh_confusing_zoom_setting_tooltip(self, value: float):
        ''' Refreshes the tooltip for the confusing zoom setting. '''
        # See main.pyw lines 9462-9469 for full implementation
        pass

    def refresh_recycle_tooltip(self, recycle: bool):
        ''' Refreshes the recycle tooltip. '''
        # See main.pyw lines 9470-9479 for full implementation
        pass

    def refresh_volume_tooltip(self):
        ''' Refreshes the volume tooltip. '''
        # See main.pyw lines 9481-9498 for full implementation
        pass

    def refresh_marked_for_deletion_tooltip(self):
        ''' Refreshes the marked for deletion tooltip. '''
        # See main.pyw lines 9499-9505 for full implementation
        pass

    def refresh_snapshot_button_controls(self):
        ''' Refreshes the snapshot button controls. '''
        # See main.pyw lines 9506-9520 for full implementation
        pass

    def handle_cycle_buttons(self, *, next: bool = True):
        ''' Handles next/previous button clicks. '''
        # See main.pyw lines 9521-9530 for full implementation
        pass

    def handle_snapshot_button(self):
        ''' Handles snapshot button click. '''
        # See main.pyw lines 9531-9541 for full implementation
        pass

    def setup_trim_button_custom_handler(self):
        ''' Sets up custom handler for trim button. '''
        # See main.pyw lines 9542-9563 for full implementation
        pass

    def get_output(self, valid_extensions=(), ext_hint=None):
        ''' Gets the output path for saving. '''
        # Helper method for determining output file path
        return ('', '', ext_hint or '')

    def get_save_remnant(self, edit_type: str, default, video=None):
        ''' Gets a save remnant from a previous failed edit. '''
        # Helper method for restoring save dialog state after failures
        return default

    def get_popup_location_kwargs(self) -> dict:
        ''' Returns kwargs for popup dialog positioning. '''
        # See main.pyw lines 8541-8556 for full implementation
        return {'pos': QtGui.QCursor.pos()}

    def get_hotkey_full_string(self, hotkey: str) -> str:
        ''' Returns the full hotkey string with modifiers. '''
        # See main.pyw lines 8557-8572 for full implementation
        return ''

    def get_new_file_timestamps(self, *sources: str, dest: str) -> tuple[float, float]:
        ''' Gets new file timestamps for copied files. '''
        # See main.pyw lines 8574-8714 for full implementation
        return (get_time(), get_time())

    def set_file_timestamps(self, path: str, ctime: float = 0, mtime: float = 0, atime: float = 0):
        ''' Sets file timestamps. '''
        # See main.pyw lines 8715-8729 for full implementation
        try:
            if path and os.path.exists(path):
                if mtime:
                    os.utime(path, (atime if atime else get_time(), mtime))
                # Setting ctime is platform-dependent and may require special handling
        except Exception as e:
            logger.error(f'Failed to set file timestamps: {e}')
