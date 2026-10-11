from pathlib import Path

from PySide6.QtCore import QThread, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMainWindow, QMessageBox

from ..config import SUPPORTED_LANGS, detect_language
from ..constants import (
    APP_FALLBACK_TITLE,
    DEFAULT_LANG,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)
from ..i18n import I18n
from ..media_ordering import normalize_prefix
from ..models import ProcessOptions, ProcessStats, SourceFolder
from ..worker import ProcessWorker
from .dialogs import show_about_dialog
from .fonts import setup_app_fonts
from .layout import AppLayoutMixin
from .localization import AppLocalizationMixin
from .pages import PagesMixin
from .run_panel import RunPanelMixin
from .styles import global_stylesheet
from .theme import C_DANGER, C_SUCCESS, C_TEXT, C_WARNING

_STATUS_COLORS = {"idle": C_TEXT, "info": C_TEXT, "success": C_SUCCESS, "warning": C_WARNING, "error": C_DANGER}


class App(AppLayoutMixin, PagesMixin, RunPanelMixin, AppLocalizationMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n(detect_language())
        self.t = self.i18n.t

        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(1000, 660)

        self._current_mode: str = MODE_COPY_KEEP
        self._current_workflow: str = WORKFLOW_MERGE
        self._output_path: str = ""
        self._last_stats: ProcessStats | None = None
        self._cancelling = False

        self.is_running = False
        self.worker_thread: QThread | None = None
        self.worker: ProcessWorker | None = None

        self.font_family = setup_app_fonts(self.i18n.lang)
        self._lang_codes = sorted(SUPPORTED_LANGS, key=lambda code: (code != DEFAULT_LANG, code))
        self._apply_palette()
        self._build_ui()

    # ------------------------------------------------------------ language / about
    def _on_lang_selector_changed(self):
        lang = self.lang_selector.currentData()
        if lang not in SUPPORTED_LANGS or lang == self.i18n.lang:
            return
        self.i18n.lang = lang
        self.font_family = setup_app_fonts(lang)
        self._apply_palette()
        self.setStyleSheet(global_stylesheet(self.font_family))
        self._retranslate_ui()

    def show_about_popup(self):
        show_about_dialog(self, self.t, self._lang_codes)

    # ------------------------------------------------------------ workflow / mode
    def _on_nav_clicked(self, workflow: str):
        if not self.is_running:
            self._set_workflow(workflow)

    def _apply_nav_state(self):
        for workflow, item in self._nav_items.items():
            item.set_active(workflow == self._current_workflow)

    def _apply_organizer_state(self):
        is_inside = self._current_workflow == WORKFLOW_INSIDE_FOLDER
        self.org_step_import.setVisible(not is_inside)
        self.org_remove_duplicates_opt.setVisible(is_inside)
        self.org_step_options.set_number(2 if is_inside else 3)
        self._sync_duplicate_option_state()

    def _sync_duplicate_option_state(self, *_args):
        if hasattr(self, "org_remove_duplicates_opt"):
            self.org_remove_duplicates_opt.setEnabled(not self.org_allow_duplicates_opt.isChecked())

    def _set_workflow(self, workflow: str):
        if workflow not in self._nav_items:
            workflow = WORKFLOW_MERGE
        self._current_workflow = workflow
        self.page_stack.setCurrentIndex(0 if workflow == WORKFLOW_MERGE else 1)
        self.open_btn.setVisible(False)
        self._apply_organizer_state()
        self._retranslate_ui()

    def _on_mode_card_clicked(self, mode_key: str):
        self._current_mode = mode_key
        for key, card in self.mode_cards.items():
            card.set_selected(key == mode_key)

    # ------------------------------------------------------------ status / readiness
    def _is_ready(self) -> bool:
        if not self._output_path:
            return False
        return self._current_workflow != WORKFLOW_MERGE or self.merge_sources.count() > 0

    def _update_start_state(self):
        self.start_btn.setEnabled(self._is_ready() and not self.is_running)

    def _set_status(self, text: str, kind: str = "idle"):
        color = _STATUS_COLORS.get(kind, C_TEXT)
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"font-size:14px; font-weight:600; color:{color};")

    def _idle_summary(self) -> str:
        t, workflow = self.t, self._current_workflow
        if workflow == WORKFLOW_MERGE:
            count = self.merge_sources.count()
            if not count:
                return t("run_add_source")
            if not self._output_path:
                return t("run_select_output")
            return t("run_ready_merge", count=count)
        if not self._output_path:
            return t("run_select_target")
        if workflow == WORKFLOW_MAIN_FOLDER:
            count = self.main_sources.count()
            return t("run_ready_main", count=count) if count else t("run_ready_main_none")
        return t("run_ready_inside")

    def _refresh_run_summary(self):
        if not hasattr(self, "status_label"):
            return
        if not self.is_running:
            self._set_status(self._idle_summary(), "idle")
        self._update_start_state()

    def _on_sources_changed(self):
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

    def _add_dropped(self, panel, paths):
        for path in paths:
            panel.add(Path(path).expanduser().resolve())  # duplicates are ignored silently

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
        key = "dlg_select_output" if self._current_workflow == WORKFLOW_MERGE else "dlg_select_target"
        folder = QFileDialog.getExistingDirectory(self, self.t(key))
        if folder:
            self._set_output_path(folder)

    def _set_output_path(self, path_text: str):
        self._output_path = path_text.strip()
        self.output_input.setText(self._output_path)
        self.main_output_input.setText(self._output_path)
        if hasattr(self, "open_btn"):
            self.open_btn.setVisible(False)
        self._refresh_run_summary()

    def open_output_folder(self):
        if self._output_path:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._output_path))

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
            # Never clear the library first: this workflow keeps and re-sorts what is already there.
            return ProcessOptions(
                mode=MODE_MAIN_FOLDER,
                output_dir=output_dir,
                inputs=[SourceFolder(f.path) for f in self.main_sources.folders()],
                clear_output_first=False,
                allow_duplicate_files=self.org_allow_duplicates_opt.isChecked(),
                use_safe_temp_workspace=self.org_safe_temp_opt.isChecked(),
            )
        if workflow == WORKFLOW_INSIDE_FOLDER:
            allow_duplicates = self.org_allow_duplicates_opt.isChecked()
            return ProcessOptions(
                mode=MODE_INSIDE_FOLDER,
                output_dir=output_dir,
                remove_duplicates_in_place=self.org_remove_duplicates_opt.isChecked() and not allow_duplicates,
                allow_duplicate_files=allow_duplicates,
                use_safe_temp_workspace=self.org_safe_temp_opt.isChecked(),
            )
        return ProcessOptions(
            mode=self._current_mode,
            output_dir=output_dir,
            inputs=self.merge_sources.folders(),
            clear_output_first=self.clear_output_opt.isChecked(),
            allow_duplicate_files=self.allow_duplicates_opt.isChecked(),
            use_safe_temp_workspace=self.safe_temp_opt.isChecked(),
        )

    @staticmethod
    def _folder_has_content(path: Path) -> bool:
        try:
            return path.is_dir() and any(path.iterdir())
        except OSError:
            return False

    def _confirm_destructive(self, options: ProcessOptions) -> bool:
        """Ask once before anything that deletes files. Safe, non-destructive runs never prompt."""
        t = self.t
        lines = []
        if options.mode == MODE_COPY_DELETE:
            lines.append(t("confirm_delete_sources"))
        if options.clear_output_first and self._folder_has_content(options.output_dir):
            lines.append(t("confirm_clear_output"))
        if options.remove_duplicates_in_place:
            lines.append(t("confirm_remove_duplicates"))
        if not lines:
            return True

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(t("confirm_title"))
        box.setText("\n\n".join(lines))
        proceed = box.addButton(t("btn_continue"), QMessageBox.AcceptRole)
        cancel = box.addButton(t("btn_cancel"), QMessageBox.RejectRole)
        box.setDefaultButton(cancel)
        box.exec()
        return box.clickedButton() is proceed

    def _set_running_ui(self, running: bool):
        self.is_running = running
        self._cancelling = False
        self.page_stack.setEnabled(not running)
        self.cancel_btn.setVisible(running)
        self.cancel_btn.setEnabled(running)
        self.cancel_btn.setText(self.t("btn_cancel"))
        if running:
            self.open_btn.setVisible(False)
            self.progress_bar.setRange(0, 0)  # busy indicator until the first progress tick
            self._set_status(self.t("status_processing"), "info")
        else:
            self.progress_bar.setRange(0, 1)
            self.progress_bar.setValue(0)
        self._update_start_text()
        self._update_start_state()

    def start_process(self):
        if self.is_running:
            return
        options = self._collect_options()
        if options is None or not self._confirm_destructive(options):
            return

        self.log_text.clear()
        self._last_stats = None
        for chip in (self.stat_added, self.stat_skipped, self.stat_total, self.stat_failed):
            chip.set_value("—")
        self.stats_row.setVisible(True)
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
            self._cancelling = True
            self.cancel_btn.setEnabled(False)
            self.cancel_btn.setText(self.t("status_cancelling"))

    def _on_progress(self, done: int, total: int):
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(done)

    def _apply_stats(self, stats: ProcessStats):
        self._last_stats = stats
        self.stat_added.set_value(stats.added)
        self.stat_skipped.set_value(stats.skipped)
        self.stat_total.set_value(stats.total_output)
        self.stat_failed.set_value(stats.failed)

    def _on_process_finished(self):
        self.worker = None
        self.worker_thread = None
        self._set_running_ui(False)

    def _on_worker_process_done(self):
        stats = self._last_stats
        if stats is None:
            self._set_status(self.t("msg_done"), "success")
        else:
            text = self.t("msg_done_summary", added=stats.added, skipped=stats.skipped, failed=stats.failed)
            self._set_status(text, "warning" if stats.failed else "success")
            if stats.failed:
                self._set_log_visible(True)
        self.open_btn.setVisible(True)

    def _on_worker_process_cancelled(self):
        self._set_status(self.t("msg_cancelled"), "info")

    def _on_worker_process_error(self, msg: str):
        self._set_status(msg, "error")
        self._set_log_visible(True)
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
            if not self.worker_thread.wait(15000):
                # A large file copy is still in flight; destroying the thread now would crash.
                event.ignore()
                return
        event.accept()
