import time

from PySide6.QtCore import QObject, Signal

from .models import CancelToken, Logger, ProcessOptions
from .pipeline import process_media


class ProcessWorker(QObject):
    log_line = Signal(str)
    progress_changed = Signal(int, int)
    stats_ready = Signal(object)
    process_done = Signal()
    process_cancelled = Signal()
    process_error = Signal(str)
    finished = Signal()

    PROGRESS_INTERVAL = 0.1  # seconds; keeps the UI responsive on huge libraries

    def __init__(self, options: ProcessOptions, tr):
        super().__init__()
        self.options = options
        self.tr = tr
        self._cancel = CancelToken()
        self._last_progress = 0.0

    def request_cancel(self) -> None:
        self._cancel.cancel()  # thread-safe (threading.Event)

    def _on_progress(self, done: int, total: int) -> None:
        now = time.monotonic()
        if done >= total or now - self._last_progress >= self.PROGRESS_INTERVAL:
            self._last_progress = now
            self.progress_changed.emit(done, total)

    def run(self):
        logger = Logger(self.log_line.emit)
        try:
            stats = process_media(
                self.options, logger, self.tr, cancel=self._cancel, progress=self._on_progress
            )
            self.stats_ready.emit(stats)
            if stats.cancelled:
                self.process_cancelled.emit()
            else:
                self.process_done.emit()
        except Exception as exc:
            logger.write(f"ERROR: {exc}")
            self.process_error.emit(str(exc))
        finally:
            self.finished.emit()
