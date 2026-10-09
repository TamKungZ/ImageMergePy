"""All user-visible text assignment. Single source of truth (the old layout.py copy is gone)."""
from ..constants import (
    APP_FALLBACK_TITLE,
    LANGUAGE_NATIVE_NAMES,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_MOVE,
    WORKFLOW_INSIDE_FOLDER,
)


class AppLocalizationMixin:
    def _retranslate_language_selector(self):
        selector = self.lang_selector
        selector.blockSignals(True)
        for index, code in enumerate(self._lang_codes):
            selector.setItemText(index, LANGUAGE_NATIVE_NAMES.get(code, code.upper()))
        selected = selector.findData(self.i18n.lang)
        if selected >= 0:
            selector.setCurrentIndex(selected)
        selector.blockSignals(False)

    def _retranslate_ui(self):
        t = self.t
        self.setWindowTitle(t("app_title") or APP_FALLBACK_TITLE)
        self.app_name_label.setText(t("app_title") or APP_FALLBACK_TITLE)
        self._title_desc_full = t("app_desc")
        self._refresh_title_desc()
        self.lang_label.setText(t("label_language"))
        self._retranslate_language_selector()

        # section headings
        self.source_section_label.setText("1  " + t("section_input").upper())
        self.output_section_label.setText("2  " + t("section_output").upper())
        self.mode_section_label.setText("3  " + t("section_mode").upper())
        self.opt_section_label.setText("4  " + t("section_options").upper())
        self.log_section_label.setText(t("section_log").upper())
        self.main_output_section_label.setText(t("main_page_target").upper())
        self.merge_page_title.setText(t("merge_page_title"))
        self.merge_page_desc.setText(t("merge_page_desc"))

        # workflow tabs
        self.page_btn_merge.setText(t("page_mode_merge"))
        self.page_btn_main.setText(t("page_mode_main_folder"))
        self.page_btn_inside.setText(t("page_mode_inside_folder"))

        # buttons
        add_text = "+ " + t("btn_add_folder")
        self.add_folder_btn.setText(add_text)
        self.main_add_folder_btn.setText(add_text)
        self.edit_prefix_btn.setText(t("btn_edit_prefix"))
        for btn in (self.remove_btn, self.main_remove_btn):
            btn.setText(t("btn_remove_selected"))
        for btn in (self.clear_btn, self.main_clear_btn):
            btn.setText(t("btn_clear_all"))
        for btn in (self.output_btn, self.main_output_btn):
            btn.setText(t("btn_select_output"))
        self.start_btn.setText(t("status_processing") if self.is_running else t("btn_start"))
        self.cancel_btn.setText(t("btn_cancel"))
        self._clear_log_btn.setText(t("btn_clear_log"))

        # source lists
        self.merge_sources.retranslate(t("col_folder"), t("col_prefix"), t("empty_no_source"))
        self.main_sources.retranslate(t("col_folder"), "", t("empty_no_main_source"))
        self.output_input.setPlaceholderText(t("section_output"))
        self.main_output_input.setPlaceholderText(t("main_page_target"))

        # mode cards
        mode_text = {
            MODE_COPY_KEEP: (t("mode_copy_keep"), t("mode_desc_copy_keep")),
            MODE_COPY_DELETE: (t("mode_copy_delete"), t("mode_desc_copy_delete")),
            MODE_MOVE: (t("mode_move"), t("mode_desc_move")),
        }
        for key, (title, desc) in mode_text.items():
            self.mode_cards[key].title_lbl.setText(title)
            self.mode_cards[key].desc_lbl.setText(desc)

        # options
        for box in (self.clear_output_checkbox, self.main_clear_output_checkbox):
            box.setText(t("opt_clear_output"))
        for box in (self.allow_duplicates_checkbox, self.main_allow_duplicates_checkbox):
            box.setText(t("opt_allow_duplicates"))
        for box in (self.safe_temp_checkbox, self.main_safe_temp_checkbox):
            box.setText(t("opt_safe_temp_workspace"))
        self.main_remove_duplicates_checkbox.setText(t("opt_remove_duplicates"))
        self.mode_note_label.setText(t("mode_note"))

        # organizer page text depends on the workflow
        prefix = "inside" if self._current_workflow == WORKFLOW_INSIDE_FOLDER else "main"
        self.main_page_title.setText(t(f"{prefix}_page_title"))
        self.main_page_desc.setText(t(f"{prefix}_page_desc"))
        self.main_page_note_label.setText(t(f"{prefix}_page_note"))
        self.main_import_section_label.setText(t(f"{prefix}_page_import_section").upper())

        self.info_btn.setToolTip("About this app")
        self.info_btn_main.setToolTip("About this app")

        self.stat_added.set_label(t("stat_added"))
        self.stat_skipped.set_label(t("stat_skipped"))
        self.stat_total.set_label(t("stat_total_out"))
        self.stat_failed.set_label(t("stat_failed"))

        self._refresh_main_sources_hint()
        self._apply_workflow_button_state()
        self._refresh_run_summary()
