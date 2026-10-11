"""A GUI start-up failure must be written to error.log, not hidden by a second error."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src.media_merge import entry


@unittest.skipIf(os.name == "nt", "Windows shows a modal MessageBox on fatal errors")
class GuiStartupFailureIsReported(unittest.TestCase):
    def test_import_error_is_logged_and_returns_1(self):
        with tempfile.TemporaryDirectory() as state:
            env = {"LOCALAPPDATA": "", "XDG_STATE_HOME": state}
            # sys.modules[name] = None makes `import name` raise ImportError.
            with mock.patch.dict(os.environ, env), \
                 mock.patch.dict(sys.modules, {"PySide6": None, "PySide6.QtCore": None, "PySide6.QtWidgets": None}), \
                 mock.patch.object(sys, "argv", ["ImageMerge"]):
                self.assertEqual(entry.main(), 1)
            log = (Path(state) / "ImageMerge" / "error.log").read_text(encoding="utf-8")
            self.assertIn("PySide6", log)  # the real import error, with its traceback
            self.assertNotIn("UnboundLocalError", log)


if __name__ == "__main__":
    unittest.main()
