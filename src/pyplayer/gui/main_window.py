"""Main application window - composed from functional mixins."""
from __future__ import annotations

import gc
import json
import logging
import os
import random
from threading import Thread
from time import sleep
from traceback import format_exc

from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from PyQt5.QtCore import Qt

from pyplayer import config, constants, qthelpers

# Import State from vlc if available (requires VLC DLL setup)
# This will work at runtime when main.pyw/pyplayer.pyw sets up VLC paths
try:
    from vlc import State
except (ImportError, OSError):
    # Create a stub State for testing/migration when VLC isn't available
    class State:
        Stopped = 0
        Opening = 1
        Buffering = 2
        Playing = 3
        Paused = 4
        Ended = 5
        Error = 6

from pyplayer.constants import SetProgressContext
from pyplayer import util  # util.py contains file operations, ffmpeg wrappers, etc.
from pyplayer.gui.mixins.dialogs import DialogMixin
from pyplayer.gui.mixins.editing import EditingMixin
from pyplayer.gui.mixins.events import EventMixin
from pyplayer.gui.mixins.file_management import FileManagementMixin
from pyplayer.gui.mixins.menus import MenuMixin
from pyplayer.gui.mixins.playback import PlaybackMixin
from pyplayer.gui.mixins.saving import SavingMixin
from pyplayer.gui.mixins.themes import ThemeMixin
from pyplayer.gui.mixins.ui_state import UIStateMixin
from pyplayer.ui.window_pyplayer import Ui_MainWindow
from pyplayer.ui.window_settings import Ui_settingsDialog

WindowStateChange = QtCore.QEvent.WindowStateChange


class MainWindow(
    PlaybackMixin,
    EditingMixin,
    SavingMixin,
    FileManagementMixin,
    MenuMixin,
    ThemeMixin,
    EventMixin,
    DialogMixin,
    UIStateMixin,
    Ui_MainWindow,
    QtW.QMainWindow,
):
    """Main application window - composed from functional mixins."""

    def __init__(self, app, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app = app
        self.setupUi(self)

        # Dummy widgets for removed UI elements (to prevent AttributeError)
        # These widgets were removed from the UI but code still references them

        # Dummy button class with no-op methods
        class DummyPushButton(QtW.QPushButton):
            def setIcon(self, *args): pass
            def setChecked(self, *args): pass
            def isChecked(self): return False
            def setVisible(self, *args): super().setVisible(False)
            def setToolTip(self, *args): pass
            def contextMenuEvent(self, *args): pass
            def setCheckable(self, *args): pass
            def setText(self, *args): pass
            def text(self): return ""

        # Dummy line edit class with no-op methods
        class DummyLineEdit(QtW.QLineEdit):
            def __init__(self, parent=None):
                super().__init__(parent)
                self._text = ''
                self._placeholder = ''
                self._tooltip = ''
                self._minimum_width = 0
                self._ignored_keys = set()
                self._ignore_all = False
                self._proxy_widget = None
            def setProxyWidget(self, *args): pass
            def setIgnoredKeys(self, *args): pass
            def setIgnoreAll(self, *args): pass
            def setMinimumWidth(self, w): self._minimum_width = w
            def minimumWidth(self): return self._minimum_width
            def setPlaceholderText(self, text): self._placeholder = text
            def setToolTip(self, text): self._tooltip = text
            def clearFocus(self): pass
            def clear(self): self._text = ''
            def setText(self, text): self._text = text
            def text(self): return self._text
            def height(self): return 18
            def setVisible(self, *args): super().setVisible(False)
            def hasFocus(self): return False

        self.buttonExploreMediaPath = DummyPushButton(self)
        self.buttonExploreMediaPath.setVisible(False)
        self.buttonMarkDeleted = DummyPushButton(self)
        self.buttonMarkDeleted.setVisible(False)
        self.buttonSnapshot = DummyPushButton(self)
        self.buttonSnapshot.setVisible(False)
        self.buttonLoop = DummyPushButton(self)
        self.buttonLoop.setVisible(False)
        self.buttonAutoplay = DummyPushButton(self)
        self.buttonAutoplay.setVisible(False)
        self.buttonPrevious = DummyPushButton(self)
        self.buttonPrevious.setVisible(False)
        self.buttonNext = DummyPushButton(self)
        self.buttonNext.setVisible(False)
        self.buttonTrimSave = DummyPushButton(self)
        self.buttonTrimSave.setVisible(False)
        self.lineOutput = DummyLineEdit(self)
        self.lineOutput.setVisible(False)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)             # this allows easier clicking off of lineEdits
        self.save_progress_bar = QtW.QProgressBar(self.statusbar)
        self.dialog_settings = qthelpers.getDialogFromUiClass(Ui_settingsDialog, parent=self, flags=Qt.WindowStaysOnTopHint)
        if not constants.IS_WINDOWS:                                # settings dialog was designed around Windows UI
            self.dialog_settings.resize(self.dialog_settings.tabWidget.sizeHint().width() + 32,
                                        self.dialog_settings.height())
        self.icons = {
            'window':            QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}logo.ico'),
            'settings':          QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}settings.png'),
            'play':              QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}play.png'),
            'pause':             QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}pause.png'),
            'stop':              QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}stop.png'),
            'restart':           QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}restart.png'),
            'x':                 QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}x.png'),
            'loop':              QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}loop.png'),
            'autoplay':          QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}autoplay.png'),
            'autoplay_backward': QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}autoplay_backward.png'),
            'autoplay_shuffle':  QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}autoplay_shuffle.png'),
            'cycle_forward':     QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}cycle_forward.png'),
            'cycle_backward':    QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}cycle_backward.png'),
            'reverse_vertical':  QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}reverse_vertical.png'),
            'recent':            QtGui.QIcon(f'{constants.RESOURCE_DIR}{os.sep}recent.png'),
        }
        self.setWindowIcon(self.icons['window'])
        app.setWindowIcon(self.icons['window'])

    def setup(self):
        self.first_video_fully_loaded = False   # NOTE: this can reset! use `videos_opened` to !00% know if files were opened this session
        self.closed = False
        self.restarted = False
        self.is_paused = False
        self.close_cancel_selected = False
        self.checking_for_updates = False
        self.timer_id_resize_snap: int = None
        self.close_was_spontaneous = False
        self.was_maximized = False
        self.was_paused = False
        self.crop_restore_state = {}

        self.last_window_size: QtCore.QSize = None
        self.last_window_pos: QtCore.QPoint = None
        self.last_window_pos_non_zero: QtCore.QPoint = None
        self.last_move_time = 0.0
        self.last_cycle_was_forward = True
        self.last_cycle_index: int = None
        self.last_amplify_audio_value = 100
        self.last_resize_media_values: tuple[str, str] = ('50%', '50%')
        self.last_resize_media_base_size: tuple[int, int] = (-1, -1)
        self.last_concat_files: list[str] = []
        self.last_concat_output = ''
        self.last_video_track: int | None = None
        self.last_audio_track: int | None = None
        self.last_subtitle_track: int | None = None
        self.last_subtitle_delay: int | None = None
        self.last_audio_delay: int | None = None
        self.tracks_were_changed = False
        self.invert_next_move_event = False
        self.invert_next_resize_event = False
        self.ignore_next_fullscreen_move_event = False
        self.ignore_next_right_click = False
        self.ignore_next_alt = False
        self.ignore_imminent_restart = False

        self.video = ''
        self.video_original_path = ''
        self.locked_files: set[str] = set()
        self.videos_opened = 0                          # the actual number of files that have been opened this session
        self.last_video = ''                            # the actual last non-edited file played
        self.recent_files: list[str] = []               # the user-friendly list of recent files
        self.recent_edits: list[str] = []               # a list of recent edit output destinations
        self.recent_searches: dict[str, int] = {}       # recent searches in the output textbox and the last selected index for that search
        self.last_search_open_prompt = ''               # the last prompt used to open a file through search
        self.last_search_open_output = ''               # the text in the output textbox following our last search
        self.last_search_open_time = 1.0                # the last time we opened a file through search
        self.last_open_time = 0.0                       # the last time we COMPLETED opening a file (`end`)
        self.move_destinations: list[str] = []          # a list of destinations for the "Move to..." and "Open..." context menu actions
        self.undo_dict: dict[str, Undo] = {}            # filenames with actions that can be undone (renaming, moving, etc.) to undo actions they're associated with
        self.mime_type = 'image'                        # NOTE: defaults to 'image' so that pausing is disabled
        self.extension = 'mp4'                          # NOTE: should be lower and not include the period (i.e. "mp4", not ".MP4")
        self.extension_label = '?'                      # the string used on the titlebar to reprsent the extension
        self.is_gif = False
        self.is_static_image = True
        self.is_audio_with_cover_art = False            # NOTE: True if cover art is present in buffer, even if it's hidden
        self.is_audio_without_cover_art = False
        self.clipboard_image_buffer: bytes = None
        self.cover_art_buffer: bytes = None             # used to store cover art in memory in case we want to load but not display it
        #self.PIL_image = None                          # TODO: store images in memory for quick copying?

        self.delay = 0.0
        self.frame_count = 1                            # the frame count from 0, i.e. 8999 frames (never actually 0 though)
        self.frame_count_raw = 1                        # the actual frame count, i.e. 9000 frames (DON'T use for calculations)
        self.frame_rate = 1
        self.frame_rate_rounded = 1
        self.duration = 0.0
        self.duration_rounded = 0.0
        self.current_time = 1
        self.minimum = 1
        self.maximum = 1
        self.vwidth = 1000
        self.vheight = 1000
        self.vsize = QtCore.QSize(1000, 1000)
        #self.resolution_label = '0x0'
        self.ratio = '0:0'
        self.size_label = '0.00mb'                      # NOTE: do NOT use `self.size` - this is reserved for Qt
        self.stat: os.stat_result = None

        self.frame_override = -1
        self.lock_progress_updates = False
        self.lock_edit_priority = False

        self.open_in_progress = False
        self._open_main_in_progress = False
        self._open_cleanup_in_progress = False
        self.external_command_in_progress = False
        self.player_swap_in_progress = False
        self.edits_in_progress: list[Edit] = []

        self.current_file_is_autoplay = False
        self.shuffle_folder = ''
        self.shuffle_ignore_order = []
        self.shuffle_ignore_unique: set[str] = set()
        self.marked_for_deletion: set[str] = set()
        self.mark_for_deletion_held_down = False
        self.mark_for_deletion_held_down_state = False
        self.shortcuts: dict = None
        self.operations = {}
        self.save_remnants: dict[float, dict] = {}
        self.playback_rate = 1.0
        self.volume_boost = 1
        self.volume_startup_correction_needed = True

        # misc setup
        self.menuRecent.setToolTipsVisible(True)
        self.menuAudio.insertMenu(self.menuAudio.actions()[2], self.menuTrimMode)
        self.menuAudio.insertAction(self.menuAudio.actions()[-1], self.actionResize)
        self.dockControls.setTitleBarWidget(QtW.QWidget(self.dockControls))  # disables QDockWidget's unique titlebar
        self.lineOutput.setProxyWidget(self)                                 # pass output text box's non-essential key events to ourselves
        self.lineOutput.setIgnoredKeys(Qt.Key_Tab)                           # ignore tab presses, we're using them for something else
        self.lineOutput.setIgnoreAll(False)                                  # but DON'T ignore normal stuff (letters, numbers, punctuation)
        # checkDeleteOriginal and checkSkipMarked removed from UI
        # frameCropInfo removed from UI (gridLayout_6 removed)
        self.frameAdvancedControls.setDragTarget(self)
        # self.frameCropInfo.setVisible(False)                                 # ensure crop info panel is hidden on startup
        self.dialog_settings.checkContextShowSubmenus.setCheckState(1)       # can't make checkboxes default to partially checked in Qt Designer :(
        for spin in (self.spinHour, self.spinMinute, self.spinSecond, self.spinFrame):
            spin.setProxyWidget(self)

        # setup progress bar embedded within the status bar
        self.statusbar.addPermanentWidget(self.save_progress_bar)            # TODO could QWIDGETMAXSIZE be used to span the widget across the entire statusbar?
        self.save_progress_bar.setMaximum(0)
        self.save_progress_bar.setMaximumHeight(16)
        self.save_progress_bar.setFormat('Saving (%p%)')                     # TODO add "(%v/%m frames)"?
        self.save_progress_bar.setAlignment(Qt.AlignCenter)
        self.save_progress_bar.setSizePolicy(QtW.QSizePolicy.Expanding, QtW.QSizePolicy.Expanding)
        self.save_progress_bar.setCursor(Qt.PointingHandCursor)
        self.save_progress_bar.hide()

        # set custom one-off event handlers for various widgets
        self.sliderVolume.keyPressEvent = self.keyPressEvent                 # pass sliderVolume key presses directly to GUI_Instance
        self.sliderVolume.keyReleaseEvent = self.keyReleaseEvent
        self.sliderVolume.valueChanged.connect(lambda: self.labelVolumePercent.setText(f'{int(self.sliderVolume.value() * self.volume_boost)}%'))
        self.sliderProgress.dragEnterEvent = self.vlc.dragEnterEvent         # reuse player's drag-and-drop code for slider
        self.sliderProgress.dropEvent = self.vlc.dropEvent
        self.dockControls.leaveEvent = self.leaveEvent                       # ensures leaving dockControls hides cursor/controls in fullscreen
        self.dockControls.resizeEvent = self.dockControlsResizeEvent         # ensures dockControls correctly hides/shows widgets in fullscreen
        self.dockControls.keyPressEvent = self.keyPressEvent                 # pass dockControls key presses directly to GUI_Instance
        self.dockControls.keyReleaseEvent = self.keyReleaseEvent
        self.dockControls.enterEvent = lambda e: self.dockControls.unsetCursor()
        self.menubar.enterEvent = lambda e: self.menubar.unsetCursor()

        self.buttonTrim.contextMenuEvent = self.trimButtonContextMenuEvent
        self.buttonExploreMediaPath.contextMenuEvent = self.buttonMediaLocationContextMenuEvent
        self.buttonMarkDeleted.contextMenuEvent = self.buttonMarkDeletedContextMenuEvent
        self.buttonSnapshot.contextMenuEvent = self.buttonSnapshotContextMenuEvent
        self.buttonAutoplay.contextMenuEvent = self.buttonAutoplayContextMenuEvent
        self.buttonNext.contextMenuEvent = self.cycleButtonContextMenuEvent
        self.buttonPrevious.contextMenuEvent = self.cycleButtonContextMenuEvent
        self.menuRecent.contextMenuEvent = self.menuRecentContextMenuEvent
        self.frameProgress.contextMenuEvent = self.frameProgressContextMenuEvent
        self.frameVolume.contextMenuEvent = self.frameVolumeContextMenuEvent
        self.frameVolume.mousePressEvent = self.frameVolumeMousePressEvent
        self.buttonPause.contextMenuEvent = self.buttonPauseContextMenuEvent
        self.buttonPause.mousePressEvent = self.buttonPauseMousePressEvent
        self.statusbar.contextMenuEvent = self.editProgressBarContextMenuEvent
        self.save_progress_bar.mouseReleaseEvent = self.editProgressBarMouseReleaseEvent

        # set default icons for various buttons
        self.buttonPause.setIcon(self.icons['pause'])
        self.buttonLoop.setIcon(self.icons['loop'])
        self.buttonNext.setIcon(self.icons['cycle_forward'])
        self.buttonPrevious.setIcon(self.icons['cycle_backward'])

        # secondary aliases (mostly for other files to use)
        self.player = self.vlc.player
        self.is_trim_mode = lambda: self.trim_mode_action_group.checkedAction() in (self.actionTrimAuto, self.actionTrimPrecise)

        # all possible snapshot button actions and tooltips, ordered by their appearance in the settings
        self.snapshot_actions = (
            (self.snapshot,                                                          'Takes and saves a snapshot immediately using your presets.'),
            (lambda: self.snapshot(mode='full'),                                     'Opens size/quality, and save dialogs for your snapshot.'),
            (lambda: self.copy_image(extended=False),                                'Copy the current frame data directly to your clipboard.'),
            (lambda: self.copy_image(extended=True),                                 'Copy the current frame data using a custom size and quality.'),
            (lambda: self.snapshot(mode='undo'),                                     'Delete the most recently saved snapshot.'),
            (lambda: self.snapshot(mode='open'),                                     'Opens the last snapshot in PyPlayer.'),
            (lambda: self.snapshot(mode='view'),                                     'Opens the last snapshot in your default program.'),
            (lambda: self.explore(config.cfg.last_snapshot_path, 'Last snapshot'),   'Open the last snapshot in explorer.'),
            (lambda: self.copy(config.cfg.last_snapshot_path, 'Last snapshot'),      'Copy the last snapshot\'s path to your clipboard.'),
            (lambda: self.copy_file(config.cfg.last_snapshot_path),                  'Copy the last snapshot\'s file to your clipboard.'),
            (lambda: self.copy_file(config.cfg.last_snapshot_path, cut=True),        'Cut the last snapshot\'s file to your clipboard.'),
            (lambda: self.copy_image(config.cfg.last_snapshot_path, extended=False), 'Copy the last snapshot\'s image data to your clipboard.'),
        )

        # all possible double-click actions, ordered by their appearance in the settings
        self.double_click_player_actions = (
            self.dialog_settings.exec,
            self.toggle_mute,
            self.actionFullscreen.trigger,
            self.toggle_maximized,
            lambda: self.set_playback_rate(1.0)
        )

        # all possible middle-click actions, ordered by their appearance in the settings
        self.middle_click_player_actions = (
            self.dialog_settings.exec,
            self.stop,
            self.toggle_mute,
            self.actionFullscreen.trigger,
            self.toggle_maximized,
            lambda: self.set_playback_rate(1.0)
        )

        # all possible tray middle-click actions, ordered by their appearance in the settings
        # Note: qtstart.exit will be replaced after import
        self.middle_click_tray_actions = (
            None,  # qtstart.exit - to be set by tray module
            self.dialog_settings.exec,
            self.stop,
            self.toggle_mute,
        )

        # create all taskbar-extensions-related widgets for windows 7-11
        self.create_taskbar_controls()

        # HACK: if you switch players at least once, libVLC will no longer be able to...
        # ...track `QVideoPlayer.underMouse()` immediately after a menu is shown???????
        # -> monkeypatch `QMenu` itself to always correct this issue (simple and performant)
        def hideEvent(menu: QtW.QMenu, event: QtGui.QHideEvent):
            QtW.QMenu._hideEvent(menu, event)
            self.vlc.reset_undermouse_state()           # updates `underMouse()` and hides cursor if over player
        QtW.QMenu._hideEvent = QtW.QMenu.hideEvent      # save real hideEvent to separate property
        QtW.QMenu.hideEvent = hideEvent

        self.menuPlayer.addAction('Set player to VLC', lambda: self.set_player('VLC'))
        self.menuPlayer.addAction('Set player to Qt', lambda: self.set_player('Qt'))

    def external_command_interface_thread(
        self,
        cmdpath: str = None,
        once: bool = False,
        delete: bool = True,
        timeout: float = 0
    ):
        ''' Simple interface for detecting and reading cmd.txt files. Used for
            instantly playing new media upon double-click if we're already open
            (cmd.txt contains the path to the media) or closing in preparation
            for an update (cmd.txt contains the word "EXIT").

            NOTE: This can be started multiple times if, for whatever reason,
            you have alternative command files you want to watch for. Just pass
            a `cmdpath` parameter. If `once` is True, this thread will auto-exit
            after its first successful command. If `delete` is True, `cmdpath`
            will be deleted after reading. If `timeout` is greater than 0,
            this thread will auto-exit after `timeout` seconds. '''

        if cmdpath is None: cmdpath = f'{constants.TEMP_DIR}{os.sep}cmd.{os.getpid()}.txt'
        try: os.makedirs(os.path.dirname(cmdpath))
        except: pass
        try: os.remove(cmdpath)
        except: pass
        logging.debug(f'Fast-start connection established. Will listen for commands at {cmdpath}.')
        use_timeout = timeout > 0

        while not self.closed:
            try:
                if os.path.exists(cmdpath):
                    self.external_command_in_progress = True
                    self._open_external_command_signal.emit(cmdpath)
                    logging.info(f'(CMD) Command file detected: {cmdpath}')
                    while self.external_command_in_progress and not self.closed:
                        sleep(0.05)
                    if delete:
                        os.remove(cmdpath)
                    if once:
                        break
            except:
                self.log_on_statusbar_signal.emit(f'(!) EXTERNAL COMMAND INTERFACE FAILED: {format_exc()}')
            finally:
                if use_timeout:
                    timeout -= 0.1
                    if timeout < 0:
                        break
                sleep(0.1)

    def event(self, event: QtCore.QEvent) -> bool:
        ''' A global event callback. Used to detect `windowStateChange` events,
            so we can save/remember the maximized state when necessary. '''
        if event.type() == WindowStateChange:           # alias used for speed
            if not (self.windowState() & Qt.WindowMinimized or self.windowState() & Qt.WindowFullScreen):
                self.was_maximized = bool(self.windowState() & Qt.WindowMaximized)
        return super().event(event)

    def restart(self) -> int:
        ''' "Restarts" media to circumvent strange behavior across multiple
            players when they "finish" media. Returns -1 if unsuccessful, else
            None. This took far more effort to figure out than you'd think.
            If `--play-and-exit` was specified in the command line arguments,
            this function closes PyPlayer. This is connected to libVLC's event
            manager in a similar manner to signals/slots in `widgets.py`. '''
        try:
            logging.info('Restarting media (Restart VI)')
            video = self.video

            if not self.player.can_restart():
                return

            # ensure media still exists, otherwise warn user
            if not os.path.exists(video):
                if video:                           # certain corrupt files will trigger a false restart
                    self.log_on_statusbar_signal.emit('Current media no longer exists. You likely renamed, moved, or deleted it from outside PyPlayer.')
                self.stop(icon='x')                 # use X-icon as visual clue that something is preventing playback
                return -1

            # if we want to loop, reload video, reset UI, and return immediately
            if self.actionLoop.isChecked():
                return self.player.loop()

            # if we want autoplay/shuffle, don't reload -> switch immediately
            if self.actionAutoplay.isChecked():
                self.update_progress(0)                  # [VLC] required due to audio issue side-effect? (1st video after audio file ends instantly)
                if self.actionAutoplayShuffle.isChecked(): return self.shuffle_media(autoplay=True)
                if self.actionAutoplayDirectionDynamic.isChecked(): next = self.last_cycle_was_forward
                else: next = self.actionAutoplayDirectionForwards.isChecked()
                return self.cycle_media(
                    next=next,
                    update_recent_list=self.dialog_settings.checkAutoplayAddToRecents.isChecked(),
                    autoplay=True
                )

            # if we want to stop, don't reload -> stop the player and return immediately
            want_to_stop = self.mime_type == 'audio' or self.dialog_settings.checkStopOnFinish.isChecked()
            if want_to_stop and self.player.get_state() != State.Stopped:
                self.update_progress(self.frame_count)   # ensure UI is visually at the end
                return self.stop(icon='restart')

            # reload video in player and restore position
            self.player.on_restart()
            self.restarted = True

            # forcibly re-pause player if necessary (slightly more efficient than using `force_pause`)
            self.player.set_pause(True)
            self.is_paused = True
            self.buttonPause.setIcon(self.icons['restart'])
            self.refresh_title_signal.emit()
            self.refresh_taskbar()
            self.player.show_text('')                      # VLC auto-shows last marq on restart -> this trick hides it

            # ensure this is True (it resets depending on settings)
            self.first_video_fully_loaded = True

            # force-close if requested. done here so as to slightly optimize normal restarts
            # Note: args.play_and_exit will be checked from app module
            from pyplayer.app import args
            if args.play_and_exit:
                logging.info('Play-and-exit requested. Closing.')
                from pyplayer.gui.tray import exit as app_exit
                return app_exit(self)
        except:
            logging.error(f'(!) RESTART FAILED: {format_exc()}')

    def restore(self, frame: int, was_paused: bool = None):
        ''' Replays the current file & immediately restores progress to `frame`,
            pausing if the media `was_paused`. Restores tracks if supported by
            the current player. Returns immediately for images. '''
        if was_paused is None:
            was_paused = self.is_paused
        if self.mime_type == 'image':
            if self.is_gif:
                self.gifPlayer.gif.setFileName(self.video)
                self.set_gif_position(frame)             # ^ don't need to play new path - just update filename
                if not was_paused:                  # only unpause gif if it wasn't paused before
                    self.force_pause_signal.emit(False)
                self.gifPlayer.filename = self.video  # also set our custom `filename` property (needed...
            return                                  # ...in `self.pause()` but I don't remember why)

        self.player.play(self.video, will_restore=True)
        self.player.set_and_update_progress(frame, SetProgressContext.RESTORE)
        if frame >= self.frame_count:               # if the media is over, stop player again immediately since most players...
            self.stop(icon='restart')               # ...will be blacked out anyway, so we might as well release the lock
        else:                                       # this can be called from a thread -> pause with a signal
            self.force_pause_signal.emit(was_paused)
            if self.player.ENABLE_AUTOMATIC_TRACK_RESTORATION:
                self.restore_tracks_signal.emit(True)


# Classes from main.pyw that are used by MainWindow
class Undo:
    """Represents an undoable action."""
    def __init__(self, type_: constants.UndoType, label: str, description: str, data: dict):
        self.type = type_
        self.label = label
        self.description = description
        self.data = data


class Edit:
    """Represents an in-progress edit operation."""
    def __init__(self, dest: str = ''):
        self.dest = dest
        self.temp_dest = ''
