"""QDraggableWindowFrame — frame that moves a target widget on drag."""
from __future__ import annotations

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW


class QDraggableWindowFrame(QtW.QFrame):
    ''' `QFrame` which moves a separate widget called `dragTarget` when dragging
        on empty spaces using `button` (if None, any button works). `dragTarget`
        is moved relative to this frame, and does not move while fullscreen or
        maximized. If no `dragTarget` is specified, `parent()` is used instead
        and persists through `setParent()` until a unique dragTarget is set. '''
    def __init__(
        self,
        *args,
        dragTarget: QtW.QWidget = None,
        button: int = Qt.LeftButton,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        if dragTarget:
            self._dragTarget = dragTarget
            self._dragTargetIsParent = False
        else:
            self._dragTarget = self.parent()
            self._dragTargetIsParent = True
        self._button = button
        self._validDrag = False
        self._draggingOffset: QtCore.QPoint = None

    def dragTarget(self) -> QtW.QWidget:    # pointless, but consistent with Qt
        return self._dragTarget

    def setDragTarget(self, widget: QtW.QWidget):
        ''' Manually sets `dragTarget`. The drag target is the
            `widget` that gets moved while dragging `self`. '''
        self._dragTarget = widget
        self._dragTargetIsParent = widget is self.parent()

    def button(self) -> int:                # pointless, but consistent with Qt
        return self._button

    def setButton(self, button: int):
        self._button = button

    def setParent(self, parent: QtW.QWidget):
        ''' Captures `QFrame.setParent()` and sets `parent` as our
            new `self._dragTarget` if our drag target and parent are
            expected to be linked (`self._dragTargetIsParent`). '''
        super().setParent(parent)
        if self._dragTargetIsParent:
            self._dragTarget = parent

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        ''' Confirms that a mouse press is valid for dragging and obtains the
            offset between the click and the top-left corner of our target.
            Ignores clicks while our target is fullscreened or maximized. This
            event does not fire if we've clicked one of our child widgets. '''
        valid_button = self._button is None or event.button() == self._button
        self._validDrag = not self._dragTarget.isFullScreen() and not self._dragTarget.isMaximized() and valid_button
        self._draggingOffset = event.globalPos() - self._dragTarget.pos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        ''' If valid, moves our target relative to our mouse's
            movement using the offset obtained in `mousePressEvent`. '''
        if not self._validDrag: return      # don't move dragTarget if we're dragging a child widget
        self._dragTarget.move(event.globalPos() - self._draggingOffset)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._validDrag = False

