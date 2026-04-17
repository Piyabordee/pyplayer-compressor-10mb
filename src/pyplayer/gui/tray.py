"""System tray icon and exit handling.

Extracted from qtstart.py exit() and get_tray_icon().
"""
from __future__ import annotations

import logging
from traceback import format_exc

from PyQt5 import QtGui
from PyQt5 import QtWidgets as QtW
from PyQt5.QtCore import Qt

from pyplayer import config, constants, qthelpers


def exit(self: QtW.QMainWindow):
    """Handle application exit.

    Saves config, disables player, hides tray icon, and quits application.
    """
    try:
        self.closed = True
        self.player.disable(wait=False)
        logging.debug('Exiting. self.closed set to True and player disabled.')

        if self.tray_icon is not None:
            self.tray_icon.setVisible(False)
            logging.debug('System tray icon stopped.')

        self.app.quit()
        logging.debug('QApplication quit.')

        try: config.saveConfig(self, constants.CONFIG_PATH)
        except: logging.warning(f'Error saving configuration: {format_exc()}')
        logging.debug('Configuration has been saved. Goodbye.')

    except:
        logging.critical(f'\n\n(!)QTSTART.EXIT FAILED: {format_exc()}')
    finally:
        self.closed = True                              # absolutely must be True or else daemon threads will never close
        self.player.enabled = False


def get_tray_icon(self: QtW.QMainWindow) -> QtW.QSystemTrayIcon:
    ''' Generates a system tray icon. Uses `QSystemTrayIcon`, which has issues:
        - If the icon is in the overflow menu on Windows, the overflow menu will
          close itself while the icon's context menu is open.
        - Some Linux distros seem to not show this icon at all. Cause unknown.

        Originally the `pystray` library was used (I forgot `QSystemTrayIcon`
        existed) and may work as a decent (albeit heavy) fallback if the above
        issues cannot be resolved or we expand upon our barebones icon. '''

    def handle_click(reason: QtW.QSystemTrayIcon.ActivationReason):
        if reason == QtW.QSystemTrayIcon.Context:       # right-click
            action_show = QtW.QAction('&PyPlayer')
            action_show.triggered.connect(lambda: qthelpers.showWindow(self))
            menu = QtW.QMenu()
            menu.addAction(action_show)
            menu.addAction(self.actionSettings)
            menu.addMenu(self.menuRecent)
            menu.addSeparator()
            menu.addAction(self.actionViewLog)
            menu.addAction(self.actionViewInstallFolder)
            menu.addAction(self.actionViewLastDirectory)
            menu.addSeparator()
            menu.addAction(self.actionStop)
            menu.addAction(self.actionExit)
            return menu.exec(QtGui.QCursor.pos())
        if reason == QtW.QSystemTrayIcon.Trigger:       # left-click
            return qthelpers.showWindow(self)
        if reason == QtW.QSystemTrayIcon.MiddleClick:   # middle-click
            index = self.dialog_settings.comboTrayMiddleClick.currentIndex()
            return self.middle_click_tray_actions[index]()

    tray = QtW.QSystemTrayIcon(self.icons['window'])
    tray.setToolTip('PyPlayer')
    tray.setVisible(True)
    tray.activated.connect(handle_click)
    return tray
