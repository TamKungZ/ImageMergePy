from PySide6.QtCore import QObject, Signal

from .media_ops import Logger, process_media

class ProcessWorker(QObject):
    log_line = Signal(str)
    process_done = Signal()
    process_error = Signal(str)
    finished = Signal()

    def __init__(
        self,
        input_configs,
        output_dir,
        mode,
        clear_output_first,
        remove_duplicates_in_place,
        allow_duplicate_files,
        use_safe_temp_workspace,
        tr,
    ):
        super().__init__()
        self.input_configs = input_configs
        self.output_dir = output_dir
        self.mode = mode
        self.clear_output_first = clear_output_first
        self.remove_duplicates_in_place = remove_duplicates_in_place
        self.allow_duplicate_files = allow_duplicate_files
        self.use_safe_temp_workspace = use_safe_temp_workspace
        self.tr = tr

    def run(self):
        logger = Logger(self.log_line.emit)
        try:
            process_media(
                self.input_configs,
                self.output_dir,
                self.mode,
                self.clear_output_first,
                self.remove_duplicates_in_place,
                self.allow_duplicate_files,
                self.use_safe_temp_workspace,
                logger,
                self.tr,
            )
            self.process_done.emit()
        except Exception as exc:
            logger.write(f"ERROR: {exc}")
            self.process_error.emit(str(exc))
        finally:
            self.finished.emit()


