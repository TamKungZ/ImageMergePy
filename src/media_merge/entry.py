import sys

from PySide6.QtWidgets import QApplication

from .cli import run_cli
from .ui.app import App


def main() -> int:
    if len(sys.argv) > 1:
        try:
            return run_cli(sys.argv[1:])
        except SystemExit:
            raise
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)
            return 1

    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    return qt_app.exec()
