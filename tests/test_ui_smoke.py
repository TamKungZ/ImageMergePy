import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from src.media_merge.config import (
    SUPPORTED_LANGS,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)
from src.media_merge.ui.app import App
from src.media_merge.ui.styles import global_stylesheet


class UiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_app_builds_pages_and_reuses_central_stylesheet(self):
        window = App()
        self.addCleanup(window.close)

        self.assertEqual(window.left_page_stack.count(), 2)
        self.assertEqual(window.styleSheet(), global_stylesheet(window.font_family))

        for workflow, expected_page in (
            (WORKFLOW_MERGE, 0),
            (WORKFLOW_MAIN_FOLDER, 1),
            (WORKFLOW_INSIDE_FOLDER, 1),
        ):
            with self.subTest(workflow=workflow):
                window._set_workflow(workflow)
                self.assertEqual(window.left_page_stack.currentIndex(), expected_page)

        current_language = window.i18n.lang
        alternate_index = next(
            (
                index
                for index in range(window.lang_selector.count())
                if window.lang_selector.itemData(index) != current_language
                and window.lang_selector.itemData(index) in SUPPORTED_LANGS
            ),
            None,
        )
        if alternate_index is not None:
            window.lang_selector.setCurrentIndex(alternate_index)
            self.assertEqual(window.i18n.lang, window.lang_selector.itemData(alternate_index))
            self.assertEqual(window.styleSheet(), global_stylesheet(window.font_family))


if __name__ == "__main__":
    unittest.main()
