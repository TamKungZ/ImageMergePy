import sys


def main() -> int:
    if len(sys.argv) > 1:
        # CLI path: must never import Qt, so it starts instantly and runs headless.
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
            return 1

    from PySide6.QtWidgets import QApplication

    from .ui.app import App

    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    return qt_app.exec()
