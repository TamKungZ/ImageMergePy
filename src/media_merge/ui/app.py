from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFontMetrics, QIcon
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

from ..config import SUPPORTED_LANGS, detect_language
from ..constants import (
    APP_FALLBACK_TITLE,
    DEFAULT_LANG,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)
from ..i18n import I18n
from ..media_ordering import normalize_prefix
from ..metadata import APP_DIR
from ..models import ProcessOptions, ProcessStats, SourceFolder
from ..worker import ProcessWorker
from .dialogs import show_about_dialog
from .fonts import setup_app_fonts
from .layout import AppLayoutMixin
from .localization import AppLocalizationMixin
from .pages import PagesMixin
from .run_panel import RunPanelMixin
from .styles import global_stylesheet


class App(AppLayoutMixin, PagesMixin, RunPanelMixin, AppLocalizationMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n(detect_language())
        self.t = self.i18n.t

        icon_path = APP_DIR / "assets" / "icons" / "app-icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.resize(1280, 720)
        self.setMinimumSize(1024, 640)

        self._current_mode: str = MODE_COPY_KEEP
        self._current_workflow: str = WORKFLOW_MERGE
        self._output_path: str = ""

        self.is_running = False
        self.worker_thread: QThread | None = None
        self.worker: ProcessWorker | None = None

        self.font_family = setup_app_fonts(self.i18n.lang)
        self._lang_codes = sorted(SUPPORTED_LANGS, key=lambda code: (code != DEFAULT_LANG, code))
        self._title_desc_full = ""
        self._apply_dark_palette()
        self._build_ui()

    # ------------------------------------------------------------ title / language
    def _refresh_title_desc(self):
        if not self._title_desc_full:
            self.desc_label.setText("")
            self.desc_label.setToolTip("")
            return
        text_width = max(40, self.desc_label.width() - 4)
        fm = QFontMetrics(self.desc_label.font())
        self.desc_label.setText(fm.elidedText(self._title_desc_full, Qt.ElideRight, text_width))
        self.desc_label.setToolTip(self._title_desc_full)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_title_desc()

    def _on_lang_selector_changed(self):
        lang = self.lang_selector.currentData()
        if lang not in SUPPORTED_LANGS or lang == self.i18n.lang:
            return
        self.i18n.lang = lang
        self.font_family = setup_app_fonts(lang)
        self._apply_dark_palette()
        self.setStyleSheet(global_stylesheet(self.font_family))
        self._retranslate_ui()

    def show_about_popup(self):
        show_about_dialog(self, self.t, self._lang_codes)

    # ------------------------------------------------------------ workflow / mode
    def _on_mode_card_clicked(self, mode_key: str):
        self._current_mode = mode_key
        for key, card in self.mode_cards.items():
            card.set_selected(key == mode_key)
        self._refresh_run_summary()

    def _apply_workflow_button_state(self):
        for workflow, btn in self._workflow_buttons.items():
            btn.setProperty("active", self._current_workflow == workflow)
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _apply_organizer_page_state(self):
        is_inside = self._current_workflow == WORKFLOW_INSIDE_FOLDER
        self.main_import_card.setVisible(not is_inside)
        self.main_sources_hint_label.setVisible(not is_inside)
        self.main_clear_output_checkbox.setVisible(not is_inside)
        self.main_remove_duplicates_checkbox.setVisible(is_inside)
        self._sync_duplicate_option_state()

    def _sync_duplicate_option_state(self):
        if hasattr(self, "main_remove_duplicates_checkbox"):
            self.main_remove_duplicates_checkbox.setEnabled(
                not self.main_allow_duplicates_checkbox.isChecked()
            )

    def _set_workflow(self, workflow: str):
        if workflow not in self._workflow_buttons:
            workflow = WORKFLOW_MERGE
        self._current_workflow = workflow
        self.left_page_stack.setCurrentIndex(0 if workflow == WORKFLOW_MERGE else 1)
        self._apply_organizer_page_state()
        self._retranslate_ui()

    # ------------------------------------------------------------ run summary
    def _refresh_main_sources_hint(self):
        count = self.main_sources.count()
        if count:
            self.main_sources_hint_label.setText(self.t("main_page_sources_hint", count=count))
        else:
            self.main_sources_hint_label.setText(self.t("main_page_no_sources_hint"))

    def _refresh_run_summary(self):
        if not hasattr(self, "run_title_label"):
            return
        t, workflow = self.t, self._current_workflow
        titles = {
            WORKFLOW_MERGE: t("page_mode_merge"),
            WORKFLOW_MAIN_FOLDER: t("page_mode_main_folder"),
            WORKFLOW_INSIDE_FOLDER: t("page_mode_inside_folder"),
        }
        self.run_title_label.setText(titles.get(workflow, ""))

        merge_count = self.merge_sources.count()
        is_ready = bool(self._output_path) and (workflow != WORKFLOW_MERGE or merge_count > 0)
        if not self.is_running:
            self.start_btn.setEnabled(is_ready)

        if not self._output_path:
            summary = t("run_select_output")
        elif workflow == WORKFLOW_MERGE:
            summary = t("run_ready_merge", count=merge_count) if merge_count else t("run_add_source")
        elif workflow == WORKFLOW_MAIN_FOLDER:
            summary = t("run_ready_main", count=self.main_sources.count())
        else:
            summary = t("run_ready_inside")
        self.run_summary_label.setText(summary)

    def _on_sources_changed(self):
        self._refresh_main_sources_hint()
        self._refresh_run_summary()

    # ------------------------------------------------------------ folders
    def _on_merge_selection_changed(self, has_selection: bool):
        self.edit_prefix_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)

    def _on_main_selection_changed(self, has_selection: bool):
        self.main_remove_btn.setEnabled(has_selection)

    def _add_source_folder(self, panel):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_input"))
        if not folder:
            return
        if not panel.add(Path(folder).expanduser().resolve()):
            QMessageBox.information(self, self.t("app_title"), self.t("msg_folder_exists"))

    def prompt_prefix(self, initial: str = "") -> str | None:
        value, accepted = QInputDialog.getText(
            self, self.t("app_title"), self.t("prompt_prefix"), text=initial,
        )
        return normalize_prefix(value) if accepted else None

    def edit_selected_prefix(self):
        if not self.merge_sources.selected_path:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_select_folder_first"))
            return
        new_prefix = self.prompt_prefix(self.merge_sources.selected_prefix())
        if new_prefix is not None:
            self.merge_sources.set_selected_prefix(new_prefix)

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_output"))
        if folder:
            self._set_output_path(folder)

    def _set_output_path(self, path_text: str):
        self._output_path = path_text.strip()
        self.output_input.setText(self._output_path)
        self.main_output_input.setText(self._output_path)
        self._refresh_run_summary()

    # ------------------------------------------------------------ running a job
    def _collect_options(self) -> ProcessOptions | None:
        workflow = self._current_workflow
        if workflow == WORKFLOW_MERGE and not self.merge_sources.count():
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_input"))
            return None
        if not self._output_path:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_output"))
            return None
        output_dir = Path(self._output_path)

        if workflow == WORKFLOW_MAIN_FOLDER:
            return ProcessOptions(
                mode=MODE_MAIN_FOLDER,
                output_dir=output_dir,
                inputs=[SourceFolder(f.path) for f in self.main_sources.folders()],
                clear_output_first=self.main_clear_output_checkbox.isChecked(),
                allow_duplicate_files=self.main_allow_duplicates_checkbox.isChecked(),
                use_safe_temp_workspace=self.main_safe_temp_checkbox.isChecked(),
            )
        if workflow == WORKFLOW_INSIDE_FOLDER:
            allow_duplicates = self.main_allow_duplicates_checkbox.isChecked()
            return ProcessOptions(
                mode=MODE_INSIDE_FOLDER,
                output_dir=output_dir,
                remove_duplicates_in_place=(
                    self.main_remove_duplicates_checkbox.isChecked() and not allow_duplicates
                ),
                allow_duplicate_files=allow_duplicates,
                use_safe_temp_workspace=self.main_safe_temp_checkbox.isChecked(),
            )
        return ProcessOptions(
            mode=self._current_mode,
            output_dir=output_dir,
            inputs=self.merge_sources.folders(),
            clear_output_first=self.clear_output_checkbox.isChecked(),
            allow_duplicate_files=self.allow_duplicates_checkbox.isChecked(),
            use_safe_temp_workspace=self.safe_temp_checkbox.isChecked(),
        )

    def _set_running_ui(self, running: bool):
        self.is_running = running
        self.progress_bar.setVisible(running)
        self.cancel_btn.setVisible(running)
        self.cancel_btn.setEnabled(running)
        self.cancel_btn.setText(self.t("btn_cancel"))
        self.start_btn.setText(self.t("status_processing") if running else self.t("btn_start"))
        if running:
            self.start_btn.setEnabled(False)
            self.progress_bar.setRange(0, 0)  # busy indicator until the first progress tick
        else:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
            self._refresh_run_summary()

    def start_process(self):
        if self.is_running:
            return
        options = self._collect_options()
        if options is None:
            return

        self.log_text.clear()
        for card in (self.stat_added, self.stat_skipped, self.stat_total, self.stat_failed):
            card.set_value("—")
        self._set_running_ui(True)

        self.worker_thread = QThread(self)
        self.worker = ProcessWorker(options, self.t)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_line.connect(self.log_text.append)
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.stats_ready.connect(self._apply_stats)
        self.worker.process_done.connect(self._on_worker_process_done)
        self.worker.process_cancelled.connect(self._on_worker_process_cancelled)
        self.worker.process_error.connect(self._on_worker_process_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_process_finished)
        self.worker_thread.start()

    def cancel_process(self):
        if self.worker is not None:
            self.worker.request_cancel()
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText(self.t("status_cancelling"))

    def _on_progress(self, done: int, total: int):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(done)

    def _apply_stats(self, stats: ProcessStats):
        self.stat_added.set_value(stats.added)
        self.stat_skipped.set_value(stats.skipped)
        self.stat_total.set_value(stats.total_output)
        self.stat_failed.set_value(stats.failed)

    def _on_process_finished(self):
        self.worker = None
        self.worker_thread = None
        self._set_running_ui(False)

    def _on_worker_process_done(self):
        QMessageBox.information(self, self.t("app_title"), self.t("msg_done"))

    def _on_worker_process_cancelled(self):
        QMessageBox.information(self, self.t("app_title"), self.t("msg_cancelled"))

    def _on_worker_process_error(self, msg: str):
        QMessageBox.critical(self, self.t("app_title"), msg)

    def closeEvent(self, event):
        # Closing mid-job used to destroy a running QThread (crash). Cancel and wait instead.
        if self.is_running and self.worker_thread is not None:
            answer = QMessageBox.question(
                self, self.t("app_title"), self.t("msg_busy_close"),
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            if self.worker is not None:
                self.worker.request_cancel()
            self.worker_thread.quit()
            self.worker_thread.wait(15000)
        event.accept()
