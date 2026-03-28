"""Event handlers — Qt event methods for main window."""
from __future__ import annotations

import logging
from time import time as get_time

from PyQt5 import QtCore, QtGui, QtWidgets as QtW
from PyQt5.QtCore import Qt

# Import State from vlc if available (requires VLC DLL setup)
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


logger = logging.getLogger(__name__)


class EventMixin:
    """Methods: closeEvent, hideEvent, showEvent, leaveEvent, moveEvent, resizeEvent,
    timerEvent, wheelEvent, keyPressEvent, keyReleaseEvent."""

    def closeEvent(self, event: QtCore.QEvent):
        ''' Handles the window close event. '''
        # See main.pyw for full implementation
        if not self.closed:
            # Show delete prompt if there are marked files
            marked = [f for f in self.marked_for_deletion if os.path.exists(f)]
            if marked:
                result = self.show_delete_prompt(exiting=True)
                if result == QtW.QDialogButtonBox.Cancel:
                    event.ignore()
                    return

            self.closed = True
            event.accept()

    def hideEvent(self, event: QtCore.QEvent):
        ''' Handles the window hide event. '''
        # See main.pyw for full implementation
        self.was_maximized = self.isMaximized()
        event.accept()

    def showEvent(self, event: QtCore.QEvent):
        ''' Handles the window show event. '''
        # See main.pyw for full implementation
        if self.was_maximized and not self.isFullScreen():
            self.showMaximized()
        event.accept()

    def leaveEvent(self, event: QtCore.QEvent):
        ''' Handles the mouse leave event. '''
        # See main.pyw for full implementation
        event.accept()

    def moveEvent(self, event: QtCore.QEvent):
        ''' Handles the window move event. '''
        # See main.pyw for full implementation
        if self.invert_next_move_event:
            self.invert_next_move_event = False
        else:
            self.last_window_pos = self.pos()
            if self.last_window_pos.x() != 0 and self.last_window_pos.y() != 0:
                self.last_window_pos_non_zero = self.last_window_pos
            self.last_move_time = get_time()
        event.accept()

    def resizeEvent(self, event: QtCore.QEvent):
        ''' Handles the window resize event. '''
        # See main.pyw for full implementation
        if self.invert_next_resize_event:
            self.invert_next_resize_event = False
        else:
            self.last_window_size = event.size()
        event.accept()

    def timerEvent(self, event: QtCore.QEvent):
        ''' Handles timer events. '''
        # See main.pyw for full implementation
        event.accept()

    def wheelEvent(self, event: QtGui.QWheelEvent):
        ''' Handles mouse wheel events for volume/seeking. '''
        # See main.pyw for full implementation
        event.accept()

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        ''' Handles key press events. '''
        # See main.pyw for full implementation
        event.accept()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        ''' Handles key release events. '''
        # See main.pyw for full implementation
        event.accept()
