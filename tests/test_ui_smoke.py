import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QApplication, QMessageBox

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

    def test_close_during_job_is_deferred_until_worker_stops(self):
        window = App()
        worker_thread = QThread(window)
        worker_thread.finished.connect(window._on_process_finished)

        def close_window():
            if worker_thread.isRunning():
                worker_thread.quit()
                worker_thread.wait(1000)
            window.is_running = False
            window.worker_thread = None
            window._close_when_worker_stops = False
            window.close()

        self.addCleanup(close_window)
        worker = Mock()
        window.worker = worker
        window.worker_thread = worker_thread
        window.is_running = True
        window.show()
        worker_thread.start()
        self.qt_app.processEvents()

        with patch.object(QMessageBox, "question", return_value=QMessageBox.Yes) as question:
            first_event = QCloseEvent()
            window.closeEvent(first_event)

            self.assertFalse(first_event.isAccepted())
            worker.request_cancel.assert_called_once()
            self.assertTrue(worker_thread.isRunning())

            second_event = QCloseEvent()
            window.closeEvent(second_event)
            self.assertFalse(second_event.isAccepted())
            question.assert_called_once()

            worker_thread.quit()
            self.assertTrue(worker_thread.wait(1000))
            self.qt_app.processEvents()
            self.assertFalse(window.isVisible())


if __name__ == "__main__":
    unittest.main()
