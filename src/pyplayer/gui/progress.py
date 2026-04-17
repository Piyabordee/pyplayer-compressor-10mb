"""Compression progress dialog widget.

Provides CompressProgressDialog for showing video compression
progress with cancel support. Emits a cancelled signal when
the user requests cancellation.
"""
from __future__ import annotations

import os

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtW


class CompressProgressDialog(QtW.QDialog):
    '''Dialog showing compression progress with percentage bar
    and cancel button.'''

    cancelled = QtCore.pyqtSignal()

    def __init__(self, parent, input_path: str):
        super().__init__(parent)
        self.setWindowTitle('Compressing for Discord')
        self.setModal(False)
        self.setMinimumWidth(400)

        self.setStyleSheet('''
            QLabel { color: black; }
            QPushButton { color: black; }
            QProgressBar { color: black; }
        ''')

        layout = QtW.QVBoxLayout(self)

        self.label = QtW.QLabel(f'Compressing for Discord...\n\n{os.path.basename(input_path)}')
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label)

        self.progressBar = QtW.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)

        buttonLayout = QtW.QHBoxLayout()
        buttonLayout.addStretch()

        self.btnCancel = QtW.QPushButton('Cancel')
        self.btnCancel.clicked.connect(self._on_cancel)
        buttonLayout.addWidget(self.btnCancel)

        layout.addLayout(buttonLayout)

        self._already_cancelled = False

    def _on_cancel(self):
        '''Handle cancel button click.'''
        if not self._already_cancelled:
            self._already_cancelled = True
            self.btnCancel.setEnabled(False)
            self.btnCancel.setText('Cancelling...')
            self.cancelled.emit()
