import faulthandler
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _log_file_path() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(base) / "ImageMerge" / "error.log"


def _setup_gui_diagnostics():
    """The GUI build has no console, so crashes would otherwise be silent.

    Log Qt messages (including qFatal, which aborts the process), Python
    tracebacks and native crashes to error.log.
    """
    try:
        path = _log_file_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.exists() and path.stat().st_size > 1_000_000:
                path.replace(path.with_suffix(".log.old"))
        except OSError:
            pass
        log = open(path, "a", encoding="utf-8", buffering=1)
        log.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} start (argv={sys.argv}) ===\n")
        faulthandler.enable(file=log, all_threads=True)
        return log
    except Exception:
        return None


def _report_fatal(log, text: str) -> None:
    if log is not None:
        try:
            log.write(text + "\n")
        except Exception:
            pass
    if os.name == "nt":
        try:
            import ctypes

            where = f"\n\nLog: {_log_file_path()}"
            ctypes.windll.user32.MessageBoxW(0, text[-1500:] + where, "ImageMerge", 0x10)
        except Exception:
            pass


def main() -> int:
    if len(sys.argv) > 1:
        from .cli import run_cli

        try:
            return run_cli(sys.argv[1:])
        except SystemExit:
            raise
        except KeyboardInterrupt:
            print("Cancelled.", file=sys.stderr, flush=True)
            return 130
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)
            if os.environ.get("IMAGEMERGE_DEBUG"):
                import traceback

                traceback.print_exc()
            return 1

    log = _setup_gui_diagnostics()
    try:
        # The native "windows11" style plugin of Qt 6.12 segfaults in the Nuitka build
        # on Windows; Fusion is stable and matches the app's own stylesheet/palette.
        os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

        from PySide6.QtCore import qInstallMessageHandler
        from PySide6.QtWidgets import QApplication

        def _qt_message(mode, context, message):
            if log is not None:
                try:
                    log.write(f"[Qt {mode.name}] {message}\n")
                except Exception:
                    pass

        qInstallMessageHandler(_qt_message)

        from .ui.app import App

        qt_app = QApplication(sys.argv)
        qt_app.setStyle("Fusion")
        window = App()
        window.show()
        if os.environ.get("IMAGEMERGE_GUI_SMOKE") == "1":
            # CI / install smoke test: prove the real GUI starts, then exit cleanly.
            from PySide6.QtCore import QTimer

            QTimer.singleShot(2000, qt_app.quit)
        return qt_app.exec()
    except Exception:
        _report_fatal(log, traceback.format_exc())
        return 1
