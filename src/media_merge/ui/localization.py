"""All user-visible text assignment. Single source of truth for UI strings."""
from ..constants import (
    APP_FALLBACK_TITLE,
    LANGUAGE_NATIVE_NAMES,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_MOVE,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)

_NAV_TEXT = {
    WORKFLOW_MERGE: ("page_mode_merge", "nav_desc_merge"),
    WORKFLOW_MAIN_FOLDER: ("page_mode_main_folder", "nav_desc_main"),
    WORKFLOW_INSIDE_FOLDER: ("page_mode_inside_folder", "nav_desc_inside"),
}

_START_TEXT = {
    WORKFLOW_MERGE: "btn_start_merge",
    WORKFLOW_MAIN_FOLDER: "btn_start_main",
    WORKFLOW_INSIDE_FOLDER: "btn_start_inside",
}


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

    def _update_start_text(self):
        key = "status_processing" if self.is_running else _START_TEXT[self._current_workflow]
        self.start_btn.setText(self.t(key))

    def _retranslate_ui(self):
        t = self.t
        title = t("app_title") or APP_FALLBACK_TITLE
        self.setWindowTitle(title)

        # sidebar
        self.app_name_label.setText(title)
        self.app_tagline_label.setText(t("app_tagline"))
        self.nav_caption_label.setText(t("nav_caption").upper())
        for workflow, (name_key, desc_key) in _NAV_TEXT.items():
            self._nav_items[workflow].set_texts(t(name_key), t(desc_key))
        self.lang_label.setText(t("label_language").upper())
        self._retranslate_language_selector()
        self.about_btn.setText(t("btn_about"))

        is_inside = self._current_workflow == WORKFLOW_INSIDE_FOLDER

        # merge page
        self.merge_page_title.setText(t("merge_page_title"))
        self.merge_page_desc.setText(t("merge_page_desc"))
        self.merge_step_sources.set_title(t("section_input"))
        self.merge_step_output.set_title(t("section_output"))
        self.merge_step_mode.set_title(t("section_mode"))
        self.merge_step_options.set_title(t("section_options"))
        self.add_folder_btn.setText("+  " + t("btn_add_folder"))
        self.edit_prefix_btn.setText(t("btn_edit_prefix"))
        self.remove_btn.setText(t("btn_remove_selected"))
        self.clear_btn.setText(t("btn_clear_all"))
        self.merge_sources.retranslate(t("col_folder"), t("col_prefix"), t("empty_no_source"))
        self.output_btn.setText(t("btn_select_output"))
        self.output_input.setPlaceholderText(t("placeholder_no_folder"))

        mode_text = {
            MODE_COPY_KEEP: ("mode_copy_keep", "mode_desc_copy_keep"),
            MODE_COPY_DELETE: ("mode_copy_delete", "mode_desc_copy_delete"),
            MODE_MOVE: ("mode_move", "mode_desc_move"),
        }
        for key, (name_key, desc_key) in mode_text.items():
            self.mode_cards[key].set_texts(t(name_key), t(desc_key))

        self.clear_output_opt.set_texts(t("opt_clear_output"), t("opt_clear_output_hint"))
        self.allow_duplicates_opt.set_texts(t("opt_allow_duplicates"), t("opt_allow_duplicates_hint"))
        self.safe_temp_opt.set_texts(t("opt_safe_temp_workspace"), t("opt_safe_temp_workspace_hint"))
        self.mode_note_label.setText(t("mode_note"))

        # organizer page (text depends on the workflow)
        prefix = "inside" if is_inside else "main"
        self.main_page_title.setText(t(f"{prefix}_page_title"))
        self.main_page_desc.setText(t(f"{prefix}_page_desc"))
        self.main_page_note_label.setText(t(f"{prefix}_page_note"))
        self.org_step_target.set_title(t(f"{prefix}_page_target"))
        self.org_step_import.set_title(t("main_page_import_section"))
        self.org_step_options.set_title(t("section_options"))
        self.main_output_btn.setText(t("btn_select_output"))
        self.main_output_input.setPlaceholderText(t("placeholder_no_folder"))
        self.main_add_folder_btn.setText("+  " + t("btn_add_folder"))
        self.main_remove_btn.setText(t("btn_remove_selected"))
        self.main_clear_btn.setText(t("btn_clear_all"))
        self.main_sources.retranslate(t("col_folder"), "", t("empty_no_main_source"))
        self.org_remove_duplicates_opt.set_texts(t("opt_remove_duplicates"), t("opt_remove_duplicates_hint"))
        self.org_allow_duplicates_opt.set_texts(t("opt_allow_duplicates"), t("opt_allow_duplicates_hint"))
        self.org_safe_temp_opt.set_texts(t("opt_safe_temp_workspace"), t("opt_safe_temp_workspace_hint"))

        # action bar
        self._update_start_text()
        self.cancel_btn.setText(t("status_cancelling") if self._cancelling else t("btn_cancel"))
        self.open_btn.setText(t("btn_open_output"))
        self.log_title_label.setText(t("section_log").upper())
        self.clear_log_btn.setText(t("btn_clear_log"))
        self.log_toggle_btn.setText(t("btn_hide_log") if self.log_panel.isVisible() else t("btn_show_log"))
        self.stat_added.set_label(t("stat_added"))
        self.stat_skipped.set_label(t("stat_skipped"))
        self.stat_total.set_label(t("stat_total_out"))
        self.stat_failed.set_label(t("stat_failed"))

        self._apply_nav_state()
        self._refresh_run_summary()
