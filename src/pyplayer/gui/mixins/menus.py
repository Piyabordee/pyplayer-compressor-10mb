"""Menu and context menu handling — context menus, mouse events, menu refresh, taskbar."""
from __future__ import annotations

import logging
import os
from traceback import format_exc

from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from PyQt5.QtCore import Qt

from pyplayer.core.media_utils import get_hms
from pyplayer.gui.helpers import openPath
from pyplayer.constants import SetProgressContext


logger = logging.getLogger(__name__)


class MenuMixin:
    """Methods: All *ContextMenuEvent, *MousePressEvent, *MouseReleaseEvent methods,
    taskbar methods, menu refresh methods."""

    # ------------------------------------------------------------------
    # Progress frame context menu
    # ------------------------------------------------------------------
    def frameProgressContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the progress slider. '''
        settings = self.dialog_settings
        precision_action = QtW.QAction(settings.checkHighPrecisionProgress.text())
        precision_action.setCheckable(True)
        precision_action.setChecked(settings.checkHighPrecisionProgress.isChecked())
        precision_action.setToolTip(settings.checkHighPrecisionProgress.toolTip())
        precision_action.toggled.connect(settings.checkHighPrecisionProgress.setChecked)

        context = QtW.QMenu(self)
        context.setToolTipsVisible(True)
        context.addAction(precision_action)
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Trim button context menu
    # ------------------------------------------------------------------
    def trimButtonContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the trim button.
            Includes trim info display and options. '''
        is_trim_mode = self.is_trim_mode()
        is_trim_active = self.buttonTrim.isChecked()

        context = QtW.QMenu(self)

        # Show current trim status if active
        if is_trim_active:
            start_ms = self.minimum * (1000 / self.fps)
            remaining_ms = (self.maximum - self.minimum) * (1000 / self.fps)

            h, m, s, ms = get_hms(start_ms)
            if self.duration_rounded < 3600:
                start_label = f'Start: {m}:{s:02}.{ms:02}'
            else:
                start_label = f'Start: {h}:{m:02}:{s:02}'

            h, m, s, ms = get_hms(remaining_ms)
            if remaining_ms < 3600:
                length_label = f'Length: {m}:{s:02}.{ms:02}'
            else:
                length_label = f'Length: {h}:{m:02}:{s:02}'

            start_label_action = QtW.QAction(start_label, self)
            start_label_action.setEnabled(False)
            context.addAction(start_label_action)

            length_label_action = QtW.QAction(length_label, self)
            length_label_action.setEnabled(False)
            context.addAction(length_label_action)
            context.addSeparator()

        # Set start action (for consistency with old workflow)
        set_start_action = QtW.QAction('Set &start to current position', self)
        set_start_action.triggered.connect(lambda: self.set_trim(enabled=True))
        if not self.video or self.is_static_image:
            set_start_action.setEnabled(False)
        context.addAction(set_start_action)

        # Cancel trim action if active
        if is_trim_active:
            cancel_action = QtW.QAction('&Cancel trim', self)
            cancel_action.triggered.connect(lambda: self.set_trim(enabled=False))
            context.addAction(cancel_action)

        context.addSeparator()
        context.addMenu(self.menuTrimMode)
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Media location button context menu
    # ------------------------------------------------------------------
    def buttonMediaLocationContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click)
            menu for the media location button. '''
        if not self.video: return                           # do not render context menu if no media is playing

        context = QtW.QMenu(self)
        context.addAction(self.actionExploreMediaPath)
        context.addAction(self.actionCopyMediaPath)
        context.addAction(self.actionCopyFile)
        context.addAction(self.actionCutFile)

        def menuMoveContextMenuEvent(menu: QtW.QMenu, event: QtGui.QContextMenuEvent):
            ''' Handles the context (right-click) menus for
                individual "Move to..." and "Open..." destinations. '''
            if action := menu.actionAt(event.pos()):
                sub_context = QtW.QMenu(self)
                sub_context.addAction('&Remove destination', lambda: self.move_destinations.remove(action.toolTip()))
                sub_context.exec(event.globalPos())

        def move(folder: str):
            ''' Moves the current media to `folder`, retaining its basename.
                Warns on replacement or if `folder` is on a different drive. '''
            try:
                if not os.path.isdir(folder) and os.path.exists(folder):
                    folder = os.path.dirname(folder)        # if folder is actually a file, use ITS folder

                # TODO: show saveFile prompt like rename does when the path already exists
                new_name = os.path.join(folder, os.path.basename(self.video))
                self.rename(
                    new_name=new_name,
                    sanitize=False,
                    delete_source_dir=False,
                    warn_on_replace=True,
                    warn_on_drive=True
                )
            except:
                self.log_on_statusbar_signal.emit(f'(!) Move failed: {format_exc()}')

        def generate_menu(label: str) -> QtW.QMenu:
            menu = context.addMenu(label)
            menu.setToolTipsVisible(True)
            menu.contextMenuEvent = menuMoveContextMenuEvent
            return menu

        # create "Open" and "Move to" submenus for quickly sorting files
        context.addSeparator()
        open_menu = generate_menu('&Open...')
        move_menu = generate_menu('&Move to...')
        add_destination_action = QtW.QAction('&Add destination...')
        add_destination_action.triggered.connect(lambda: self.browse_for_directory(noun='destination'))

        # add all existing destinations to the top of each submenu
        for folder in self.move_destinations:
            label = os.path.basename(folder)
            open_menu.addAction(label, lambda f=folder: openPath(f)).setToolTip(folder)
            move_menu.addAction(label, lambda f=folder: move(f)).setToolTip(folder)

        # add a separator and an action for adding new destinations to each submenu
        for menu in (open_menu, move_menu):
            menu.addSeparator()
            menu.addAction(add_destination_action)

        # add labels with info about the current media, then show context menu
        self.add_info_actions(context)
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Mark-deleted button context menu
    # ------------------------------------------------------------------
    def buttonMarkDeletedContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the deletion button. '''
        self.menuDelete.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Snapshot button context menu
    # ------------------------------------------------------------------
    def buttonSnapshotContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the snapshot button.
            Side note: PyQt does NOT like it if you do `QMenu.exec()` in a
            lambda. As soon as it returns, you get: `TypeError: invalid
            argument to sipBadCatcherResult()`. And it's uncatchable. '''
        context = QtW.QMenu(self)
        for index, action in enumerate(self.menuSnapshots.actions()):
            if index == 2 and not self.is_audio_without_cover_art:
                self.refresh_copy_image_action()            # add "Copy image" action if there's something to copy
                context.addAction(self.actionCopyImage)
            context.addAction(action)
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Autoplay button context menu
    # ------------------------------------------------------------------
    def buttonAutoplayContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the autoplay button. '''
        context = QtW.QMenu(self)
        context.setToolTipsVisible(True)
        context.addActions(self.menuAutoplay.actions()[1:])
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Cycle button context menu
    # ------------------------------------------------------------------
    def cycleButtonContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the cycle buttons. '''
        mime = self.mime_type

        context = QtW.QMenu(self)
        context.addAction('Open random file', lambda: self.shuffle_media())
        context.addAction('Open next file', self.cycle_media)
        context.addAction('Open previous file', lambda: self.cycle_media(next=False))
        context.addSeparator()
        context.addAction(f'Open random {mime} file', lambda: self.shuffle_media(valid_mime_types=(mime,)))
        context.addAction(f'Open next {mime} file', lambda: self.cycle_media(valid_mime_types=(mime,)))
        context.addAction(f'Open previous {mime} file', lambda: self.cycle_media(next=False, valid_mime_types=(mime,)))
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Recent files menu context menu
    # ------------------------------------------------------------------
    def menuRecentContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click)
            menus for individual recent files. '''
        action = self.menuRecent.actionAt(event.pos())
        if action is self.actionClearRecent or not action: return
        path = action.toolTip()

        context = QtW.QMenu(self)
        context.addAction('&Remove from recent files', lambda: (self.recent_files.remove(path), self.refresh_recent_menu()))
        context.addSeparator()
        context.addAction('M&edia location', lambda: self.explore(path))
        context.addAction('&Copy media path', lambda: self.copy(path))
        context.addSeparator()
        context.addAction('&Move to top', lambda: self.open_recent_file(path, update=True, open=False))
        context.addAction('&Open and move to top', lambda: self.open_recent_file(path, update=True))
        context.addAction('&Open without moving to top', lambda: self.open_recent_file(path, update=False))
        context.exec(event.globalPos())

    # ------------------------------------------------------------------
    # Volume frame context menu and mouse press
    # ------------------------------------------------------------------
    def frameVolumeContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the volume slider's
            frame. A frame is used since the slider can be disabled.'''
        mute_action = QtW.QAction('Mute')
        mute_action.setCheckable(True)
        mute_action.setChecked(not self.sliderVolume.isEnabled())
        mute_action.toggled.connect(self.toggle_mute)

        next_boost = min(self.volume_boost + 0.5, 5)
        last_boost = min(self.volume_boost - 0.5, 5)
        inc_boost_action = QtW.QAction(f'Increase boost to {next_boost:.1f}x')
        inc_boost_action.triggered.connect(lambda: self.set_volume_boost(next_boost))
        dec_boost_action = QtW.QAction(f'Decrease boost to {last_boost:.1f}x')
        dec_boost_action.triggered.connect(lambda: self.set_volume_boost(last_boost))
        reset_boost_action = QtW.QAction('Reset boost')
        reset_boost_action.triggered.connect(self.set_volume_boost)

        context = QtW.QMenu(self)
        context.addAction(mute_action)
        context.addSeparator()
        context.addAction(inc_boost_action)
        context.addAction(dec_boost_action)
        context.addAction(reset_boost_action)
        context.exec(event.globalPos())

    def frameVolumeMousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Handles clicking on the volume slider's frame. A frame is used
            since the slider can be disabled. Unmutes on left-click. '''
        if event.button() == Qt.LeftButton:
            self.set_mute(False)

    # ------------------------------------------------------------------
    # Pause button context menu and mouse press
    # ------------------------------------------------------------------
    def buttonPauseContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the pause button. '''
        context = QtW.QMenu(self)
        context.addAction(self.actionStop)
        context.addAction('Restart', lambda: self.player.set_and_update_progress(0, SetProgressContext.RESET_TO_MIN))
        context.exec(event.globalPos())

    def buttonPauseMousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Handles clicking on the pause button. Unmutes on left-click. '''
        if event.button() == Qt.MiddleButton: self.stop()
        else: QtW.QPushButton.mousePressEvent(self.buttonPause, event)

    # ------------------------------------------------------------------
    # Edit progress bar context menu and mouse release
    # ------------------------------------------------------------------
    def editProgressBarContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context (right-click) menu for the edit progress bar,
            allowing you to see, display, and cancel all active edits. '''
        settings = self.dialog_settings
        context = QtW.QMenu(self)
        context.setToolTipsVisible(True)

        # add recent edits submenu + separator to top of menu if desired
        if settings.spinRecentEdits.value():
            menu_recent = QtW.QMenu('Recent edits', context)
            menu_recent.setToolTipsVisible(True)
            if self.recent_edits:
                menu_recent.triggered.connect(lambda action: self.open_recent_file(action.toolTip(), update=True, edits=True))
                for path in reversed(self.recent_edits):
                    menu_recent.addAction(os.path.basename(path)).setToolTip(path)
            else:
                menu_recent.addAction('No edits this session').setEnabled(False)
            context.addMenu(menu_recent)
            context.addSeparator()

        # return early if no edits are actually active
        total_edits = len(self.edits_in_progress)
        if not total_edits:
            context.addAction('No edits in progress').setEnabled(False)
            context.exec(event.globalPos())
            return

        # workarounds for python bug/oddity involving creating lambdas in iterables
        # (needed for the actions to actually remember which edit they belong to)
        get_cancel_lambda =   lambda edit: lambda: edit.cancel()
        get_pause_lambda =    lambda edit: lambda: edit.pause(paused=True)
        get_resume_lambda =   lambda edit: lambda: edit.pause(paused=False)
        get_priority_lambda = lambda edit: lambda: edit.give_priority()

        for edit in self.edits_in_progress:

            # set edit's menu title with text, operation count, and (operation) progress
            if total_edits > 1:
                submenu = QtW.QMenu(edit.get_progress_text(simple=True), context)
                context.addMenu(submenu)
            else:
                submenu = context

            # resume/pause selected edit
            if not edit._is_paused:
                action_suspend = submenu.addAction('Pause')
                action_suspend.triggered.connect(get_pause_lambda(edit))
            else:
                action_suspend = submenu.addAction('Resume')
                action_suspend.triggered.connect(get_resume_lambda(edit))

            # cancel selected edit
            action_cancel = submenu.addAction('Cancel')
            action_cancel.triggered.connect(get_cancel_lambda(edit))
            submenu.addSeparator()

            # give priority to selected edit (if possible)
            if total_edits > 1:
                action_priority = submenu.addAction('Display')
                if edit.has_priority:
                    action_priority.setEnabled(False)
                else:
                    action_priority.triggered.connect(get_priority_lambda(edit))

            # show dest's basename as disabled action so edits can be distinguished
            if edit.dest:
                action_outfile = submenu.addAction(os.path.basename(edit.dest))
                action_outfile.setEnabled(False)
                if edit.temp_dest == edit.dest:
                    action_outfile.setToolTip(edit.dest)
                else:
                    action_outfile.setToolTip(f'Final destination:\t {edit.dest}\n'
                                              f'Temp destination:\t {edit.temp_dest}')

            # show "-threads" override if one was used
            if edit._threads:
                text = f'Using {edit._threads} thread{"s" if edit._threads != 1 else ""}'
                submenu.addAction(text).setEnabled(False)

        # add "Pause/Resume/Cancel all" actions, if appropriate
        if total_edits > 1:
            context.addSeparator()
            context.addAction('Pause all', lambda: self.pause_all(paused=True))
            context.addAction('Resume all', lambda: self.pause_all(paused=False))
            context.addAction('Cancel all', self.cancel_all)

        context.exec(event.globalPos())

    def editProgressBarMouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Handles clicking (and releasing) over the edit progress bar. Cycles
            which edit currently has priority on left-click, toggles pause-state
            for the current edit with priority on middle-click. '''
        if len(self.edits_in_progress) > 1 and event.button() == Qt.LeftButton:
            self.cycle_edit_priority()
        elif event.button() == Qt.MiddleButton:
            edit = self.get_edit_with_priority()
            edit.pause()

    # ------------------------------------------------------------------
    # Main window context menu / mouse events (stubs — to be filled later)
    # ------------------------------------------------------------------
    def contextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Handles the context menu event for the main window. '''
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Handles mouse press events. '''
        event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Handles mouse release events. '''
        event.accept()

    # Player/video slider context menu events
    def playerContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Context menu for the video player. '''
        event.accept()

    def playerMousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse press on video player. '''
        event.accept()

    def playerMouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse release on video player. '''
        event.accept()

    # Slider context menu events
    def sliderContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Context menu for the progress slider. '''
        event.accept()

    def sliderMousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse press on progress slider. '''
        event.accept()

    def sliderMouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse release on progress slider. '''
        event.accept()

    # Image context menu events
    def imageContextMenuEvent(self, event: QtGui.QContextMenuEvent):
        ''' Context menu for image player. '''
        event.accept()

    def imageMousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse press on image player. '''
        event.accept()

    def imageMouseReleaseEvent(self, event: QtGui.QMouseEvent):
        ''' Mouse release on image player. '''
        event.accept()

    # ------------------------------------------------------------------
    # Taskbar methods (stubs)
    # ------------------------------------------------------------------
    def refresh_taskbar(self):
        ''' Refreshes the taskbar button state. '''
        pass

    def create_taskbar_controls(self):
        ''' Creates taskbar thumbnail controls. '''
        pass

    def enable_taskbar_controls(self, checked: bool = True):
        ''' Enables or disables taskbar controls. '''
        pass

    # ------------------------------------------------------------------
    # Menu refresh methods (stubs)
    # ------------------------------------------------------------------
    def refresh_track_menu(self, menu: QtW.QMenu):
        ''' Refreshes the track menu with current tracks. '''
        pass

    def refresh_recent_menu(self):
        ''' Refreshes the recent files menu. '''
        pass

    def refresh_undo_menu(self):
        ''' Refreshes the undo menu with undoable actions. '''
        pass

    # ------------------------------------------------------------------
    # Additional context menu / helper methods (stubs)
    # ------------------------------------------------------------------
    def show_context_menu(self, pos: QtCore.QPoint):
        ''' Shows the context menu at the specified position. '''
        pass

    def add_info_actions(self, context: QtW.QMenu):
        ''' Adds info actions to a context menu. '''
        pass

    def get_popup_location_kwargs(self) -> dict:
        ''' Returns kwargs for popup dialog positioning. '''
        return {'pos': QtGui.QCursor.pos()}

    def handle_cycle_buttons(self, *, next: bool = True):
        ''' Handles next/previous button clicks. '''
        pass

    def handle_snapshot_button(self):
        ''' Handles snapshot button click. '''
        pass

    def setup_trim_button_custom_handler(self):
        ''' Sets up custom handler for trim button. '''
        pass

    def get_hotkey_full_string(self, hotkey: str) -> str:
        ''' Returns the full hotkey string with modifiers. '''
        return ''
