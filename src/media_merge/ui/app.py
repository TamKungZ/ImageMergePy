from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QFontMetrics, QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from ..config import (
    APP_DIR,
    APP_FALLBACK_TITLE,
    APP_METADATA,
    C_BORDER,
    DEFAULT_LANG,
    IMAGE_EXTS,
    LANGUAGE_NATIVE_NAMES,
    SUPPORTED_LANGS,
    VIDEO_EXTS,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
    detect_language,
    setup_app_fonts,
)
from ..i18n import I18n
from ..media_ops import (
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    normalize_prefix,
)
from ..worker import ProcessWorker
from .layout import AppLayoutMixin
from .widgets import FolderOnlyRow, SourceRow

class App(AppLayoutMixin, QMainWindow):
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

        self.input_entries: list[dict] = []
        self._source_rows: dict[str, SourceRow] = {}
        self._selected_path: str | None = None
        self.main_input_entries: list[dict] = []
        self._main_source_rows: dict[str, FolderOnlyRow] = {}
        self._main_selected_path: str | None = None
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

    def _refresh_title_desc(self):
        if not self._title_desc_full:
            self.desc_label.setText("")
            self.desc_label.setToolTip("")
            return
        text_width = max(40, self.desc_label.width() - 4)
        fm = QFontMetrics(self.desc_label.font())
        self.desc_label.setText(fm.elidedText(self._title_desc_full, Qt.ElideRight, text_width))
        self.desc_label.setToolTip(self._title_desc_full)

    def _refresh_empty_label(self):
        if not self.input_entries:
            self.empty_label.setText(self.t("empty_no_source"))
            self.empty_label.show()
        else:
            self.empty_label.hide()
        self._refresh_main_empty_label()
        self._refresh_main_sources_hint()
        self._refresh_run_summary()

    def _refresh_main_empty_label(self):
        if not self.main_input_entries:
            self.main_empty_label.setText(self.t("empty_no_main_source"))
            self.main_empty_label.show()
        else:
            self.main_empty_label.hide()

    def _on_lang_selector_changed(self, _index: int):
        lang = self.lang_selector.currentData()
        if lang not in SUPPORTED_LANGS or lang == self.i18n.lang:
            return
        self.i18n.lang = lang
        self.font_family = setup_app_fonts(lang)
        self._apply_dark_palette()
        self.setStyleSheet(self._global_stylesheet())
        self._retranslate_ui()

    def _build_about_text(self) -> str:
        app_name = APP_METADATA.get("app_name") or APP_FALLBACK_TITLE
        app_desc = self.t("app_desc")
        version = APP_METADATA.get("product_version") or APP_METADATA.get("file_version") or "-"
        company = APP_METADATA.get("company_name") or "-"
        license_note = APP_METADATA.get("copyright") or "MIT License"
        images = ", ".join(sorted(IMAGE_EXTS))
        videos = ", ".join(sorted(VIDEO_EXTS))
        modes = " | ".join(
            [
                self.t("mode_copy_keep"),
                self.t("mode_copy_delete"),
                self.t("mode_move"),
                self.t("mode_main_folder"),
                self.t("mode_inside_folder"),
            ]
        )
        langs = ", ".join(LANGUAGE_NATIVE_NAMES.get(code, code.upper()) for code in self._lang_codes)

        return """\
<div style="line-height:1.45;">
  <h2 style="margin:0 0 6px 0;">{app_name}</h2>
  <p style="margin:0 0 12px 0; color:#4a5a76;">{app_desc}</p>

  <table style="margin:0 0 12px 0;" cellpadding="2" cellspacing="0">
    <tr><td><b>Version:</b></td><td>{version}</td></tr>
    <tr><td><b>Developer:</b></td><td>{company}</td></tr>
    <tr><td><b>License:</b></td><td>{license_note}</td></tr>
  </table>

  <b>Main features</b>
  <ul style="margin:6px 0 12px 18px; padding:0;">
    <li>Merge media from multiple folders</li>
    <li>De-duplicate by SHA-256 hash + extension</li>
    <li>Keep images first and videos last</li>
    <li>Rename output files as sequence numbers with optional per-folder prefix</li>
  </ul>

  <p style="margin:0 0 6px 0;"><b>Operation modes:</b> {modes}</p>
  <p style="margin:0 0 6px 0;"><b>Supported image formats:</b> {images}</p>
  <p style="margin:0 0 6px 0;"><b>Supported video formats:</b> {videos}</p>
  <p style="margin:0;"><b>UI languages:</b> {langs}</p>
</div>
""".format(
            app_name=app_name,
            app_desc=app_desc,
            version=version,
            company=company,
            license_note=license_note,
            modes=modes,
            images=images,
            videos=videos,
            langs=langs,
        )

    def show_about_popup(self):
        dialog = QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        dialog.resize(700, 520)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        about_text = QTextEdit(dialog)
        about_text.setReadOnly(True)
        about_text.setFrameShape(QFrame.NoFrame)
        about_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        about_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        about_text.setHtml(self._build_about_text())
        layout.addWidget(about_text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok_button = QPushButton("OK", dialog)
        ok_button.setFixedWidth(104)
        ok_button.clicked.connect(dialog.accept)
        buttons.addWidget(ok_button)
        layout.addLayout(buttons)

        dialog.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_title_desc()

    def _on_mode_card_clicked(self, mode_key: str):
        self._current_mode = mode_key
        for key, card in self.mode_cards.items():
            card.set_selected(key == mode_key)
        self._refresh_run_summary()

    def _selected_mode(self) -> str:
        return self._current_mode

    def _apply_workflow_button_state(self):
        self.page_btn_merge.setProperty("active", self._current_workflow == WORKFLOW_MERGE)
        self.page_btn_main.setProperty("active", self._current_workflow == WORKFLOW_MAIN_FOLDER)
        self.page_btn_inside.setProperty("active", self._current_workflow == WORKFLOW_INSIDE_FOLDER)
        for btn in (self.page_btn_merge, self.page_btn_main, self.page_btn_inside):
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _apply_main_page_mode_state(self):
        is_inside = self._current_workflow == WORKFLOW_INSIDE_FOLDER
        self.main_import_card.setVisible(not is_inside)
        self.main_sources_hint_label.setVisible(not is_inside)
        self.main_import_section_label.setVisible(not is_inside)
        self.main_source_container.setVisible(not is_inside)
        self.main_add_folder_btn.setVisible(not is_inside)
        self.main_remove_btn.setVisible(not is_inside)
        self.main_clear_btn.setVisible(not is_inside)
        self.main_add_folder_btn.setEnabled(not is_inside)
        self.main_remove_btn.setEnabled((not is_inside) and (self._main_selected_path is not None))
        self.main_clear_btn.setEnabled(not is_inside)
        self.main_clear_output_checkbox.setVisible(not is_inside)
        self.main_remove_duplicates_checkbox.setVisible(is_inside)
        self._sync_duplicate_option_state()

    def _sync_duplicate_option_state(self):
        if not hasattr(self, "main_remove_duplicates_checkbox"):
            return
        allow_duplicates = self.main_allow_duplicates_checkbox.isChecked()
        self.main_remove_duplicates_checkbox.setEnabled(not allow_duplicates)

    def _set_workflow(self, workflow: str):
        if workflow not in {WORKFLOW_MERGE, WORKFLOW_MAIN_FOLDER, WORKFLOW_INSIDE_FOLDER}:
            workflow = WORKFLOW_MERGE
        self._current_workflow = workflow
        self.left_page_stack.setCurrentIndex(0 if workflow == WORKFLOW_MERGE else 1)
        self._apply_main_page_mode_state()
        self._retranslate_ui()
        self._apply_workflow_button_state()
        self._refresh_run_summary()

    def _set_output_path(self, path_text: str):
        self._output_path = path_text.strip()
        self.output_input.setText(self._output_path)
        self.main_output_input.setText(self._output_path)
        self._refresh_run_summary()

    def _refresh_run_summary(self):
        if not hasattr(self, "run_title_label"):
            return

        workflow_names = {
            WORKFLOW_MERGE: self.t("page_mode_merge"),
            WORKFLOW_MAIN_FOLDER: self.t("page_mode_main_folder"),
            WORKFLOW_INSIDE_FOLDER: self.t("page_mode_inside_folder"),
        }
        self.run_title_label.setText(workflow_names.get(self._current_workflow, ""))

        is_ready = bool(self._output_path) and (
            self._current_workflow != WORKFLOW_MERGE or bool(self.input_entries)
        )
        if not self.is_running:
            self.start_btn.setEnabled(is_ready)

        if not self._output_path:
            self.run_summary_label.setText(self.t("run_select_output"))
        elif self._current_workflow == WORKFLOW_MERGE:
            if self.input_entries:
                self.run_summary_label.setText(
                    self.t("run_ready_merge", count=len(self.input_entries))
                )
            else:
                self.run_summary_label.setText(self.t("run_add_source"))
        elif self._current_workflow == WORKFLOW_MAIN_FOLDER:
            self.run_summary_label.setText(
                self.t("run_ready_main", count=len(self.main_input_entries))
            )
        else:
            self.run_summary_label.setText(self.t("run_ready_inside"))

    def _refresh_main_sources_hint(self):
        if self.main_input_entries:
            self.main_sources_hint_label.setText(
                self.t("main_page_sources_hint", count=len(self.main_input_entries))
            )
        else:
            self.main_sources_hint_label.setText(self.t("main_page_no_sources_hint"))

    def prompt_prefix(self, initial: str = "") -> str | None:
        value, accepted = QInputDialog.getText(
            self, self.t("app_title"), self.t("prompt_prefix"), text=initial,
        )
        if not accepted:
            return None
        return normalize_prefix(value)

    def _add_source_row(self, path_str: str, prefix: str):
        row = SourceRow(path_str, prefix)
        row.remove_requested.connect(self._remove_by_path)
        row.edit_requested.connect(self._select_row)
        self._source_rows[path_str] = row
        self.rows_layout.addWidget(row)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BORDER}; border:none;")
        sep.setObjectName(f"sep_{path_str}")
        self.rows_layout.addWidget(sep)

    def _clear_source_rows(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget() and item.widget() is not self.empty_label:
                item.widget().deleteLater()
        self._source_rows.clear()
        self.rows_layout.addWidget(self.empty_label)

    def _select_row(self, path_str: str):
        if self._selected_path == path_str:
            self._selected_path = None
            if path_str in self._source_rows:
                self._source_rows[path_str].set_selected(False)
        else:
            if self._selected_path and self._selected_path in self._source_rows:
                self._source_rows[self._selected_path].set_selected(False)
            self._selected_path = path_str
            if path_str in self._source_rows:
                self._source_rows[path_str].set_selected(True)
        has_sel = self._selected_path is not None
        self.edit_prefix_btn.setEnabled(has_sel)
        self.remove_btn.setEnabled(has_sel)

    def _remove_by_path(self, path_str: str):
        self.input_entries = [e for e in self.input_entries if str(e["path"]) != path_str]
        if self._selected_path == path_str:
            self._selected_path = None
            self.edit_prefix_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
        self._clear_source_rows()
        for entry in self.input_entries:
            self._add_source_row(str(entry["path"]), entry.get("prefix", ""))
        self._refresh_empty_label()

    def add_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_input"))
        if not folder:
            return
        path = Path(folder).expanduser().resolve()
        if any(entry["path"] == path for entry in self.input_entries):
            QMessageBox.information(self, self.t("app_title"), self.t("msg_folder_exists"))
            return
        entry = {"path": path, "prefix": ""}
        self.input_entries.append(entry)
        self._add_source_row(str(path), "")
        self._refresh_empty_label()

    def edit_selected_prefix(self):
        if not self._selected_path:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_select_folder_first"))
            return
        for entry in self.input_entries:
            if str(entry["path"]) == self._selected_path:
                new_prefix = self.prompt_prefix(entry.get("prefix", ""))
                if new_prefix is None:
                    return
                entry["prefix"] = new_prefix
                if self._selected_path in self._source_rows:
                    self._source_rows[self._selected_path].update_prefix(new_prefix)
                return

    def remove_selected_input(self):
        if self._selected_path:
            self._remove_by_path(self._selected_path)

    def clear_inputs(self):
        self.input_entries.clear()
        self._selected_path = None
        self.edit_prefix_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self._clear_source_rows()
        self._refresh_empty_label()

    def _add_main_source_row(self, path_str: str):
        row = FolderOnlyRow(path_str)
        row.remove_requested.connect(self._remove_main_by_path)
        row.edit_requested.connect(self._select_main_row)
        self._main_source_rows[path_str] = row
        self.main_rows_layout.addWidget(row)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BORDER}; border:none;")
        sep.setObjectName(f"main_sep_{path_str}")
        self.main_rows_layout.addWidget(sep)

    def _clear_main_source_rows(self):
        while self.main_rows_layout.count():
            item = self.main_rows_layout.takeAt(0)
            if item.widget() and item.widget() is not self.main_empty_label:
                item.widget().deleteLater()
        self._main_source_rows.clear()
        self.main_rows_layout.addWidget(self.main_empty_label)

    def _select_main_row(self, path_str: str):
        if self._main_selected_path == path_str:
            self._main_selected_path = None
            if path_str in self._main_source_rows:
                self._main_source_rows[path_str].set_selected(False)
        else:
            if self._main_selected_path and self._main_selected_path in self._main_source_rows:
                self._main_source_rows[self._main_selected_path].set_selected(False)
            self._main_selected_path = path_str
            if path_str in self._main_source_rows:
                self._main_source_rows[path_str].set_selected(True)
        self.main_remove_btn.setEnabled(self._main_selected_path is not None)

    def _remove_main_by_path(self, path_str: str):
        self.main_input_entries = [e for e in self.main_input_entries if str(e["path"]) != path_str]
        if self._main_selected_path == path_str:
            self._main_selected_path = None
            self.main_remove_btn.setEnabled(False)
        self._clear_main_source_rows()
        for entry in self.main_input_entries:
            self._add_main_source_row(str(entry["path"]))
        self._refresh_empty_label()

    def add_main_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_input"))
        if not folder:
            return
        path = Path(folder).expanduser().resolve()
        if any(entry["path"] == path for entry in self.main_input_entries):
            QMessageBox.information(self, self.t("app_title"), self.t("msg_folder_exists"))
            return
        entry = {"path": path, "prefix": ""}
        self.main_input_entries.append(entry)
        self._add_main_source_row(str(path))
        self._refresh_empty_label()

    def remove_selected_main_input(self):
        if self._main_selected_path:
            self._remove_main_by_path(self._main_selected_path)

    def clear_main_inputs(self):
        self.main_input_entries.clear()
        self._main_selected_path = None
        self.main_remove_btn.setEnabled(False)
        self._clear_main_source_rows()
        self._refresh_empty_label()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_output"))
        if folder:
            self._set_output_path(folder)

    def choose_main_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_output"))
        if folder:
            self._set_output_path(folder)

    def append_log(self, text: str):
        self.log_text.append(text)

    def start_process(self):
        if self.is_running:
            return

        input_configs = [{"path": e["path"], "prefix": e.get("prefix", "")} for e in self.input_entries]
        output_dir_text = self._output_path
        if self._current_workflow == WORKFLOW_MAIN_FOLDER:
            mode = MODE_MAIN_FOLDER
            clear_output_first = self.main_clear_output_checkbox.isChecked()
            remove_duplicates_in_place = False
            allow_duplicate_files = self.main_allow_duplicates_checkbox.isChecked()
            use_safe_temp_workspace = self.main_safe_temp_checkbox.isChecked()
            input_configs = [{"path": e["path"], "prefix": ""} for e in self.main_input_entries]
        elif self._current_workflow == WORKFLOW_INSIDE_FOLDER:
            mode = MODE_INSIDE_FOLDER
            clear_output_first = False
            allow_duplicate_files = self.main_allow_duplicates_checkbox.isChecked()
            remove_duplicates_in_place = (
                self.main_remove_duplicates_checkbox.isChecked() and not allow_duplicate_files
            )
            use_safe_temp_workspace = self.main_safe_temp_checkbox.isChecked()
            input_configs = []
        else:
            mode = self._selected_mode()
            clear_output_first = self.clear_output_checkbox.isChecked()
            remove_duplicates_in_place = False
            allow_duplicate_files = self.allow_duplicates_checkbox.isChecked()
            use_safe_temp_workspace = self.safe_temp_checkbox.isChecked()

        if self._current_workflow == WORKFLOW_MERGE and not input_configs:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_input"))
            return
        if not output_dir_text:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_output"))
            return

        self.log_text.clear()
        self.stat_added.set_value("—")
        self.stat_skipped.set_value("—")
        self.stat_total.set_value("—")
        self.stat_failed.set_value("—")

        self.start_btn.setEnabled(False)
        self.start_btn.setText(self.t("status_processing"))
        self.is_running = True

        output_dir = Path(output_dir_text)

        self.worker_thread = QThread(self)
        self.worker = ProcessWorker(
            input_configs,
            output_dir,
            mode,
            clear_output_first,
            remove_duplicates_in_place,
            allow_duplicate_files,
            use_safe_temp_workspace,
            self.t,
        )
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_line.connect(self.append_log)
        self.worker.log_line.connect(self._parse_log_for_stats)
        self.worker.process_done.connect(self._on_worker_process_done)
        self.worker.process_error.connect(self._on_worker_process_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_process_finished)

        self.worker_thread.start()

    def _parse_log_for_stats(self, text: str):
        import re as _re
        def _pattern_from_i18n(key: str) -> str:
            template = self.t(key, count="{count}")
            escaped = _re.escape(template)
            return escaped.replace(_re.escape("{count}"), r"(\d+)")

        pairs = [
            (self.stat_added, _pattern_from_i18n("log_added")),
            (self.stat_skipped, _pattern_from_i18n("log_skipped")),
            (self.stat_total, _pattern_from_i18n("log_total_output")),
            (self.stat_failed, _pattern_from_i18n("log_failed")),
        ]
        for card, pattern in pairs:
            m = _re.search(pattern, text)
            if m:
                card.set_value(m.group(1))

    def _on_process_finished(self):
        self.is_running = False
        self.start_btn.setText(self.t("btn_start"))
        self.worker = None
        self.worker_thread = None
        self._refresh_run_summary()

    def _on_worker_process_done(self):
        QMessageBox.information(self, self.t("app_title"), self.t("msg_done"))

    def _on_worker_process_error(self, msg: str):
        QMessageBox.critical(self, self.t("app_title"), msg)

