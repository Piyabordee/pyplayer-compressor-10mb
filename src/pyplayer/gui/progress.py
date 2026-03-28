"""Compression progress dialog widget.

Extracted from main.pyw. Provides CompressProgressDialog for showing
video compression progress with cancel support.
"""
from __future__ import annotations

import os
import subprocess
import logging

from PyQt5 import QtCore
from PyQt5 import QtWidgets as QtW


class CompressProgressDialog(QtW.QDialog):
    '''
    Dialog showing compression progress with percentage bar
    and cancel button.
    '''

    def __init__(self, parent, input_path: str):
        super().__init__(parent)
        self.setWindowTitle('Compressing for Discord')
        self.setModal(False)  # Modeless - allows user to move window
        self.setMinimumWidth(400)

        # Style all text as black
        self.setStyleSheet('''
            QLabel { color: black; }
            QPushButton { color: black; }
            QProgressBar { color: black; }
        ''')

        layout = QtW.QVBoxLayout(self)

        # File name label
        self.label = QtW.QLabel(f'Compressing for Discord...\n\n{os.path.basename(input_path)}')
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.label)

        # Progress bar
        self.progressBar = QtW.QProgressBar()
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)

        # Buttons
        buttonLayout = QtW.QHBoxLayout()
        buttonLayout.addStretch()

        self.btnCancel = QtW.QPushButton('Cancel')
        self.btnCancel.clicked.connect(self.reject)
        buttonLayout.addWidget(self.btnCancel)

        layout.addLayout(buttonLayout)

        # Store process reference for cancellation
        self.process = None

    def update_progress(self, percent: int):
        '''Update progress bar percentage.'''
        self.progressBar.setValue(percent)

    def set_process(self, process):
        '''Store the FFmpeg process for cancellation.'''
        self.process = process

    def reject(self):
        '''Handle dialog rejection (cancel button or close).'''
        if self.process and self.process.poll() is None:
            # Process is still running - terminate it
            try:
                self.process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    self.process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.process.kill()
            except Exception as e:
                logging.getLogger('pyplayer.gui.progress').warning(f'Error terminating FFmpeg: {e}')

        super().reject()
