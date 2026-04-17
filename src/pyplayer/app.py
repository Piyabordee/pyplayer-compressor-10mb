"""Application startup - QApplication creation, argument parsing, main()."""
from __future__ import annotations

import gc
import logging
import os
import sys
import argparse
from threading import Thread
from time import time as get_time
from traceback import format_exc

# Setup VLC DLL paths BEFORE importing VLC-dependent modules
# This allows running from source without needing VLC in PATH
# __file__ = src/pyplayer/app.py, so project root is 2 levels up
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_VLC_PATH = os.path.join(_PROJECT_ROOT, 'executable', 'include', 'vlc-windows')
_LIB_PATH = os.path.join(_VLC_PATH, 'libvlc.dll')
_MODULE_PATH = os.path.join(_VLC_PATH, 'plugins')
if 'PYTHON_VLC_LIB_PATH' not in os.environ and os.path.exists(_LIB_PATH):
    os.environ['PYTHON_VLC_LIB_PATH'] = _LIB_PATH
if 'PYTHON_VLC_MODULE_PATH' not in os.environ and os.path.exists(_MODULE_PATH):
    os.environ['PYTHON_VLC_MODULE_PATH'] = _MODULE_PATH

from PyQt5 import QtGui, QtWidgets as QtW

from pyplayer import config, constants
from pyplayer.gui.main_window import MainWindow
from pyplayer.gui.signals import connect_widget_signals
from pyplayer.gui.shortcuts import connect_shortcuts
from pyplayer.gui.tray import exit as app_exit, get_tray_icon
from pyplayer.widgets import helpers
from pyplayer.widgets.helpers import set_aliases

# Module-level args - accessed by update.py via lazy import
# This is a contract with update.py
args = None


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', help='Specifies a filepath to open')
    parser.add_argument('--exit', action='store_true', help='Instantly exits. Used when sending media to other instances')
    parser.add_argument('--play-and-exit', action='store_true', help='Automatically exits at the conclusion of a media file')
    parser.add_argument('--minimized', action='store_true', help='Start minimized (to the tray, if enabled). Useful when used as a startup program')
    parser.add_argument('-v', '--vlc', default='--gain=2.0', help='Specifies arguments to pass to the underlying VLC instance (if enabled)')
    parser.add_argument('-d', '--debug', action='store_true', help='Outputs debug messages to the log file.')
    return parser.parse_args()


def after_show_setup(gui):
    """Post-show initialization - recent files, tray icon, hotkeys.

    This is called after the main window is shown to perform final setup steps.
    """
    # check for/download/validate pending updates
    gui.handle_updates_signal.emit(True)

    # open file if desired (we only get this far if no other sessions were open)
    if args.file:
        if not os.path.exists(args.file):
            gui.refresh_title_signal.emit()
            gui.log_on_statusbar_signal.emit(f'Command-line file {args.file} does not exist.')
        else:
            try:
                logging.debug(f'Opening pre-selected path: {args.file}')
                gui.open(args.file)
                gui.log_on_statusbar_signal.emit(f'Command-line path opened: {args.file}')
            except:
                gui.refresh_title_signal.emit()
                gui.log_on_statusbar_signal.emit(f'Failed to open pre-selected path: {args.file}')
                logging.error(format_exc())
    else:
        gui.refresh_title_signal.emit()

    # set last window size/pos if window still has default geometry after loading config
    if gui.last_window_size is None: gui.last_window_size = gui.size()
    if gui.last_window_pos is None: gui.last_window_pos = gui.pos()

    # populate recent files list
    recent_files_count = gui.dialog_settings.spinRecentFiles.value()
    files = config.cfg.load('recent_files', '', '<|>', section='general')
    if recent_files_count > 25:
        gui.recent_files += files[-recent_files_count:]
    else:
        recent_files = gui.recent_files
        append = recent_files.append
        abspath = os.path.abspath
        for file in files:
            if os.path.isfile(file) and file not in recent_files:
                append(abspath(file))
            if len(recent_files) == recent_files_count:
                break

    # start system tray icon
    if config.cfg.grouptray:
        logging.debug('Creating system tray icon...')
        gui.app.setQuitOnLastWindowClosed(False)   # ensure qt does not exit until we tell it to
        gui.tray_icon = get_tray_icon(gui)

    # enable taskbar extensions if desired
    if constants.IS_WINDOWS:
        gui.taskbar.setWindow(gui.windowHandle())
        gui.enable_taskbar_controls(checked=config.cfg.checktaskbarcontrols)

    # manually refresh various settings after config is fully loaded
    settings = gui.dialog_settings
    gui.set_trim_mode(gui.trim_mode_action_group.checkedAction())
    gui.gifPlayer._imageScale = settings.comboScaleImages.currentIndex()
    gui.gifPlayer._artScale = settings.comboScaleArt.currentIndex()
    gui.gifPlayer._gifScale = settings.comboScaleGifs.currentIndex() + 1
    gui.player.set_text_height(settings.spinTextHeight.value())
    gui.player.set_text_x(settings.spinTextX.value())
    gui.player.set_text_y(settings.spinTextY.value())

    # setup/connect hotkeys, manually refresh various parts of UI
    connect_shortcuts(gui)
    gui.refresh_shortcuts()
    gui.refresh_volume_tooltip()
    gui.refresh_autoplay_button()
    gui.refresh_snapshot_button_controls()
    gui.refresh_confusing_zoom_setting_tooltip(settings.spinZoomMinimumFactor.value())

    # start command interface thread
    Thread(target=gui.external_command_interface_thread, daemon=True).start()


def main():
    """Application entry point.

    Creates QApplication, initializes MainWindow, sets up aliases,
    and starts the event loop.
    """
    global args
    args = parse_args()
    if args.exit:
        sys.exit(100)

    # ---------------------
    # Logging
    # ---------------------
    if os.path.exists(constants.LOG_PATH):                  # backup existing log and delete outdated logs
        sep = os.sep
        log_path = constants.LOG_PATH
        temp_dir = f'{constants.TEMP_DIR}{sep}logs'
        prefix, suffix = os.path.splitext(os.path.basename(log_path))
        p_len = len(prefix)
        s_len = len(suffix)
        if os.path.isdir(temp_dir):
            logs = [f for f in os.listdir(temp_dir) if f[:p_len] == prefix and f[-s_len:] == suffix]
            for outdated_log in logs[:-9]:
                try: os.remove(f'{temp_dir}{sep}{outdated_log}')
                except: pass
        new_name = f'{prefix}.{os.stat(log_path).st_mtime_ns}{suffix}'
        try: os.renames(log_path, f'{temp_dir}{sep}{new_name}')
        except: pass

    file_handler = logging.FileHandler(constants.LOG_PATH, 'w', delay=False)
    if not args.debug:                                      # don't save debug messages to file (if desired)
        file_handler.setLevel(logging.INFO)

    logging.basicConfig(
        level=logging.DEBUG,
        force=True,
        format='{asctime} {lineno:<3} {levelname} {funcName}: {message}',
        datefmt='%m/%d/%y | %I:%M:%S%p',
        style='{',
        handlers=(file_handler, logging.StreamHandler())
    )

    logging.info(f'Logger initalized at {constants.LOG_PATH}.')
    logging.debug(f'Arguments: {args}')

    try:
        logging.debug(f'PyPlayer opened at {constants.SCRIPT_PATH} with executable {sys.executable}')
        logging.debug('Creating QApplication and GUI...')
        app = QtW.QApplication(sys.argv)                # init qt
        gui = helpers.gui = MainWindow(app)             # init empty GUI instance
        gui.setup()                                     # setup gui's variables, widgets, and threads (0.3mb)

        # --------------------------------------------------------
        # Aliases for common/time-sensitive functions & variables
        # --------------------------------------------------------
        # Note: These aliases are used throughout the codebase
        # We populate the helpers module with these references
        player = gui.vlc.player
        image_player = gui.gifPlayer
        play = player.play
        play_image = gui.gifPlayer.play
        settings = gui.dialog_settings
        refresh_title = gui.refresh_title_signal.emit
        marquee = gui.marquee
        show_on_player = player.show_text
        log_on_statusbar = gui.log_on_statusbar_signal.emit
        show_on_statusbar = gui.statusbar.showMessage
        update_progress = gui.update_progress
        set_and_update_progress = player.set_and_update_progress
        set_volume_slider = gui.sliderVolume.setValue
        get_volume_slider = gui.sliderVolume.value
        get_volume_scroll_increment = settings.spinScrollVolume.value
        get_ui_frame = gui.sliderProgress.value
        set_progress_slider = gui.sliderProgress.setValue
        set_hour_spin = gui.spinHour.setValue
        set_minute_spin = gui.spinMinute.setValue
        set_second_spin = gui.spinSecond.setValue
        set_frame_spin = gui.spinFrame.setValue
        set_player_position = player.set_position
        set_gif_position = image_player.gif.jumpToFrame
        set_current_time_text = gui.lineCurrentTime.setText
        current_time_lineedit_has_focus = gui.lineCurrentTime.hasFocus
        can_load_cover_art = settings.checkLoadCoverArt.isChecked
        can_show_cover_art = settings.checkShowCoverArt.isChecked
        parse_json = lambda s: __import__('json').JSONDecoder(object_hook=None, object_pairs_hook=None).decode(s)
        abspath = os.path.abspath
        exists = os.path.exists
        sep = os.sep

        # Set global aliases in helpers module for backward compatibility
        helpers.settings = settings                     # set settings dialog as global object
        helpers.player = player
        helpers.image_player = image_player
        helpers.play = play
        helpers.play_image = play_image
        helpers.refresh_title = refresh_title
        helpers.marquee = marquee
        helpers.show_on_player = show_on_player
        helpers.log_on_statusbar = log_on_statusbar
        helpers.show_on_statusbar = show_on_statusbar
        helpers.update_progress = update_progress
        helpers.set_and_update_progress = set_and_update_progress
        helpers.set_volume_slider = set_volume_slider
        helpers.get_volume_slider = get_volume_slider
        helpers.get_volume_scroll_increment = get_volume_scroll_increment
        helpers.get_ui_frame = get_ui_frame
        helpers.set_progress_slider = set_progress_slider
        helpers.set_hour_spin = set_hour_spin
        helpers.set_minute_spin = set_minute_spin
        helpers.set_second_spin = set_second_spin
        helpers.set_frame_spin = set_frame_spin
        helpers.set_player_position = set_player_position
        helpers.set_gif_position = set_gif_position
        helpers.set_current_time_text = set_current_time_text
        helpers.current_time_lineedit_has_focus = current_time_lineedit_has_focus
        helpers.can_load_cover_art = can_load_cover_art
        helpers.can_show_cover_art = can_show_cover_art
        helpers.parse_json = parse_json
        helpers.abspath = abspath
        helpers.exists = exists
        helpers.sep = sep

        # Populate helpers module
        set_aliases(gui, app, config.cfg, settings)

        connect_widget_signals(gui)             # connect signals and slots
        cfg = helpers.cfg = config.loadConfig(gui)      # create and load config (uses constants.CONFIG_PATH)

        # Ensure auto-compress setting is synced between config and settings checkbox
        if hasattr(settings, 'checkAutoCompress'):
            gui.auto_compress_after_trim = settings.checkAutoCompress.isChecked()

        if not args.minimized:                  # show UI
            gui.show()
        else:
            check_tray = settings.groupTray
            if not check_tray.isChecked():              # if tray icon is enabled, don't show UI at all
                gui.showMinimized()                     # otherwise, start with window minimized

        constants.verify_ffmpeg(gui)                    # confirm/look for valid ffmpeg path if needed
        FFPROBE = constants.verify_ffprobe(gui)         # confirm/look/return valid ffprobe path if needed
        after_show_setup(gui)                   # perform final bits of misc setup before showing UI

        with open(constants.PID_PATH, 'w'):             # create PID file
            gc.collect(generation=2)                    # final garbage collection before starting
            constants.APP_RUNNING = True
            logging.debug(f'Starting GUI after {get_time() - constants.SCRIPT_START_TIME:.2f} seconds.')
            try: app.exec()
            except: logging.critical(f'(!) GUI FAILED TO EXECUTE: {format_exc()}')
            logging.debug('Application execution has finished.')
        try: os.remove(constants.PID_PATH)
        except: logging.warning(f'(!) Failed to delete PID file: {format_exc()}')
    except: logging.critical(f'(!) SCRIPT FAILED TO INITIALIZE: {format_exc()}')

    return 0
