"""Input widgets — key sequence edit, passthrough widgets, spinbox signals."""
from __future__ import annotations

import logging
from traceback import format_exc

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets as QtW

from pyplayer.widgets import helpers as _helpers


logger = logging.getLogger('widgets.py')


class QKeySequenceFlexibleEdit(QtW.QKeySequenceEdit):
    ''' `QKeySequenceEdit` with support for ignorable sequences, limiting to a
        single sequence, custom edit delays, clearing focus/sequences with Esc,
        a clear button, and easy access to the underlying `QLineEdit`. '''
    def __init__(
        self,
        *args,
        singleSequence: bool = True,
        escClearsFocus: bool = True,
        escClearsSequence: bool = True,
        clearButton: bool = False,
        delay: int = 200,
        ignored: tuple = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._timerID = None
        self._editing = False
        self.lineEdit = self.children()[0]
        self.setClearButtonEnabled(clearButton)
        self.singleSequence = singleSequence
        self.escClearsFocus = escClearsFocus
        self.escClearsSequence = escClearsSequence
        self.editDelay = delay
        self.ignoredSequences = (           # like the other utility widgets, we manually set this here for simplicity
            QtGui.QKeySequence('Ctrl+O'),
            QtGui.QKeySequence('Ctrl+S'),
            QtGui.QKeySequence('Ctrl+Shift+S'),
            QtGui.QKeySequence('Alt+Q')
        )


    def setSingleSequence(self, enabled: bool): self.singleSequence = enabled
    def setEscClearsFocus(self, enabled: bool): self.escClearsFocus = enabled
    def setEscClearsSequence(self, enabled: bool): self.escClearsSequence = enabled
    def setEditDelay(self, delay: int): self.editDelay = delay
    def setIgnoredSequences(self, *args: QtGui.QKeySequence): self.ignoredSequences = args


    def setClearButtonEnabled(self, enabled: bool):
        ''' Toggles/connects the clear button for the underlying `QLineEdit`
            (`self.lineEdit`). When disabling, the `QAction` and `QToolButton`
            that make up the clear button are automatically discarded by Qt. '''
        self.lineEdit.setClearButtonEnabled(enabled)
        if enabled:
            self.lineEdit.children()[1].triggered.connect(self.clear)


    def clear(self):
        ''' Overrides clearing to manually emit `keySequenceChanged` and
            `editingFinished` signals (assuming it was not called as part of an
            editing timer), allowing clearing to actually trigger updates. '''
        super().clear()
        if self._timerID is None:           # timerID means a custom timer active
            self.keySequenceChanged.emit(self.keySequence())
            self.editingFinished.emit()


    def keyPressEvent(self, event: QtGui.QKeyEvent):
        ''' If `self.escClearsFocus` is set, focus is cleared and returned
            after Esc is pressed. If `self.singleSequence` is set, sequences
            are truncated to their last sequence, and ", ..." is stripped from
            the underlying `QLineEdit` (`self.lineEdit`). '''
        if event.key() == Qt.Key_Escape:                        # clear text/focus on Esc
            if self.escClearsSequence: self.clear()
            if self.escClearsFocus: return self.clearFocus()    # do NOT use event.ignore() here

        if self.singleSequence:             # single sequence only
            super().keyPressEvent(event)    # run built-in keyPressEvent first (this emits keySequenceChanged)
            if self.keySequence().count() > 1:
                self.setKeySequence(QtGui.QKeySequence(self.keySequence()[-1]))  # truncate sequence to last sequence
            return self.lineEdit.setText(self.keySequence().toString())          # strip ", ..." from underlying QLineEdit and return

        elif self.editDelay != 1000:        # not a single sequence, but a custom editing delay (reimplement timer behavior)
            if self._timerID is None:       # no timer running + not actively editing -> clear existing sequence for incoming sequence
                if not self._editing:
                    self.clear()
            else:                           # timer running + actively editing the sequence -> kill/reset timer (we're still editing)
                self._timerID = self.killTimer(self._timerID)
            self._editing = True            # mark that we're actively editing
        super().keyPressEvent(event)        # run built-in keyPressEvent last (this emits the first keySequenceChanged signal)


    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        ''' Clears the entire field if it contains an ignored sequence. If
            `self.singleSequence` is set, the `editingFinished` signal is
            emitted immediately and the normal timer is skipped. Otherwise,
            if a custom `self.editDelay` is set, then `QKeySequenceEdit`'s
            edit-finished-timer is reimplemented in `timerEvent`. '''
        if self.ignoredSequences and self.keySequence() in self.ignoredSequences:
            self.clear()

        if self.singleSequence:
            return self.editingFinished.emit()
        elif self.editDelay != 1000:
            self._editing = False
            if self._timerID is not None:
                self.killTimer(self._timerID)
            self._timerID = self.startTimer(self.editDelay, Qt.CoarseTimer)
        else:
            return super().keyReleaseEvent(event)


    def timerEvent(self, event: QtCore.QTimerEvent):
        ''' Finishes the reimplementation of `QKeySequenceEdit`'s
            edit-finished-timer for custom `self.editDelay` values.
            This doesn't fire if `self.singleSequence` is set. '''
        if self._timerID is not None:                           # timerID means a custom timer active
            self.keySequenceChanged.emit(self.keySequence())    # emit second keySequenceChanged signal
            self.editingFinished.emit()
            self._timerID = self.killTimer(self._timerID)       # kill timer and remove ID
            self.lineEdit.setText(self.keySequence().toString())
        return super().timerEvent(event)                        # ^ strip ", ..." from underlying QLineEdit


    def toString(
        self,
        format: QtGui.QKeySequence.SequenceFormat = QtGui.QKeySequence.SequenceFormat.PortableText
    ) -> str:
        ''' Returns the embedded key sequence as a string. '''
        return self.keySequence().toString(format)


    def __repr__(self) -> str:
        ''' Returns the embedded key sequence as a string. '''
        return self.keySequence().toString()




class QWidgetPassthrough(QtW.QWidget):
    ''' `QWidget` which passes desired keypresses to its parent. Specific
        characters can be ignored, and specific categories (such as letters,
        integers, and punctuation) can be toggled. The option to clear or
        optionally "pass" focus when Esc is pressed is also included. '''
    base = QtW.QWidget      # TODO semi-bandaid fix. without this, we can't access the correct keyPressEvent in subclasses(...?)

    # TODO make the getting/setting syntax fully Qt-like or make it fully normal
    def __init__(
        self,
        *args,
        proxy: QtW.QWidget = None,
        escClearsFocus: bool = True,
        passFocus: bool = True,
        alpha: bool = True,
        punctuation: bool = True,
        numeric: bool = False,
        ignored: tuple[int] = tuple(),
        **kwargs
    ):
        super().__init__(*args, **kwargs)   # normally these kwargs are True, False, False, False
        self.escClearsFocus = escClearsFocus
        self.passFocus = passFocus
        self.ignoreAlpha = alpha
        self.ignorePunctuation = punctuation
        self.ignoreNumeric = numeric
        self.ignoredKeys = ignored
        if proxy:
            self._proxyWidget = proxy
            self._proxyWidgetIsParent = False
        else:
            self._proxyWidget = self.parent()
            self._proxyWidgetIsParent = True

    def proxyWidget(self) -> QtW.QWidget:   # pointless, but consistent with Qt
        return self._proxyWidget

    def setProxyWidget(self, widget: QtW.QWidget):
        ''' Sets `self.proxyWidget` to `widget`, which will receive any
            keypresses from this widget that would otherwise be discarded.
            If `widget` is our parent, the parent will be tracked until this
            method is called again with a unique `widget`. '''
        self._proxyWidget = widget
        self._proxyWidgetIsParent = widget is self.parent()

    def setParent(self, parent: QtW.QWidget):
        ''' Captures setParent and sets `proxyWidget` to the new `parent`
            if our proxy widget and parent are expected to be linked. '''
        super().setParent(parent)
        if self._proxyWidgetIsParent:
            self._proxyWidget = parent

    def setIgnoreAll(self, ignore: bool):
        self.ignoreAlpha = ignore
        self.ignorePunctuation = ignore
        self.ignoreNumeric = ignore

    def setEscClearsFocus(self, enabled: bool): self.escClearsFocus = enabled
    def setPassFocus(self, enabled: bool): self.passFocus = enabled
    def setIgnoreAlpha(self, ignore: bool): self.ignoreAlpha = ignore
    def setIgnorePunctuation(self, ignore: bool): self.ignorePunctuation = ignore
    def setIgnoreNumeric(self, ignore: bool): self.ignoreNumeric = ignore
    def setIgnoredKeys(self, *keys: int): self.ignoredKeys = tuple(int(key) for key in keys)

    def focusNextPrevChild(self, next: bool) -> bool:           # https://stackoverflow.com/a/21351638
        ''' Don't change focus if we're ignoring the Tab key (16777217).
            Not the best solution, but I don't want to use an event filter. '''
        return False if 16777217 in self.ignoredKeys else super().focusNextPrevChild(next)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> QtGui.QKeyEvent:
        key = event.key()                   # ↓ esc (clear/pass focus)
        if self.escClearsFocus and key == 16777216:
            if self.passFocus: return self._proxyWidget.setFocus()
            else: return self.clearFocus()
        text = event.text()
        if (
            key in self.ignoredKeys
            or (self.ignoreAlpha and text.isalpha())
            or (self.ignorePunctuation and text in '!"#$%&\'()*+, -./:;<=>?@[\\]^_`{|}~')
            or (self.ignoreNumeric and text.isnumeric())
        ):
            return self._proxyWidget.keyPressEvent(event)
        return self.base.keyPressEvent(self, event)




class QSpinBoxPassthrough(QtW.QSpinBox, QWidgetPassthrough): base = QtW.QSpinBox
class QDockWidgetPassthrough(QtW.QDockWidget, QWidgetPassthrough): base = QtW.QDockWidget
class QLineEditPassthrough(QtW.QLineEdit, QWidgetPassthrough): base = QtW.QLineEdit




class QSpinBoxInputSignals(QSpinBoxPassthrough):
    ''' `QSpinBoxPassthrough` that emits a `valueEdited` signal when the
        value changes as a result of user input and a `valueStepped` signal
        when `stepBy()` is called. Useful when you want a signal for value
        changes that ignores programmatic changes. '''
    valueEdited = QtCore.pyqtSignal(int)    # mirrors the `QLineEdit.textEdited` signal
    valueStepped = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        self._hasSuffix = False             # used for minor optimization
        super().__init__(*args, **kwargs)
        self.lineEdit().textEdited.connect(self._detectManualEdit)

    def _detectManualEdit(self, text: str):
        if self._hasSuffix:
            real = text[len(self.prefix()):-len(self.suffix())]
        else:                               # slicing to :0 results in an empty string
            real = text[len(self.prefix()):]
        if real and int(real) != self.value():
            self.valueEdited.emit(int(real))

    def setSuffix(self, suffix: str):
        super().setSuffix(suffix)
        self._hasSuffix = len(suffix) > 0

    def stepBy(self, steps: int):
        super().stepBy(steps)               # this updates `self.value()` immediately
        self.valueStepped.emit(self.value())


