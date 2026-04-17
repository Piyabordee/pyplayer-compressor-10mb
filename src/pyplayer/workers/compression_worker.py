"""QThread-based worker for video compression.

Runs FFmpeg compression off the main thread, communicating
progress and completion via Qt signals."""
from __future__ import annotations

import logging

from PyQt5 import QtCore

from pyplayer.core import compression

logger = logging.getLogger('pyplayer.workers.compression')


class CompressionWorker(QtCore.QObject):
    """Worker object that runs video compression in a QThread.

    Usage:
        thread = QtCore.QThread()
        worker = CompressionWorker(...)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda: thread.quit())
        thread.start()
    """

    progress = QtCore.pyqtSignal(int)           # 0–100 percent
    finished = QtCore.pyqtSignal(bool, str)     # success, error_message

    def __init__(
        self,
        ffmpeg_path: str,
        ffprobe_path: str,
        input_path: str,
        output_path: str,
        parent: QtCore.QObject | None = None,
    ):
        super().__init__(parent)
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.input_path = input_path
        self.output_path = output_path
        self._cancelled = False

    def run(self) -> None:
        """Execute compression. Emits progress and finished signals."""
        def progress_callback(percent: int) -> None:
            if not self._cancelled:
                self.progress.emit(percent)

        try:
            success, error = compression.compress_video(
                ffmpeg_path=self.ffmpeg_path,
                ffprobe_path=self.ffprobe_path,
                input_path=self.input_path,
                output_path=self.output_path,
                progress_callback=progress_callback,
            )
            if self._cancelled:
                self.finished.emit(False, 'Cancelled')
            else:
                self.finished.emit(success, error)
        except Exception as e:
            logger.error(f'Compression worker error: {e}')
            self.finished.emit(False, str(e))

    def cancel(self) -> None:
        """Request cancellation. The running FFmpeg process will be
        terminated on its next progress callback."""
        self._cancelled = True
