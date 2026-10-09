from ..config import (
    APP_FALLBACK_TITLE,
    LANGUAGE_NATIVE_NAMES,
    WORKFLOW_INSIDE_FOLDER,
)
from ..media_ops import (
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_MOVE,
)

class AppLocalizationMixin:
    def _retranslate_ui(self):
        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.app_name_label.setText(self.t("app_title") or APP_FALLBACK_TITLE)

        self._title_desc_full = self.t("app_desc")
        self._refresh_title_desc()
        self.lang_label.setText(self.t("label_language"))
        current_code = self.lang_selector.currentData()
        self.lang_selector.blockSignals(True)
        for i, code in enumerate(self._lang_codes):
            language_name = LANGUAGE_NATIVE_NAMES.get(code, code.upper())
            self.lang_selector.setItemText(i, language_name)
        selected_index = self.lang_selector.findData(self.i18n.lang)
        if selected_index >= 0:
            self.lang_selector.setCurrentIndex(selected_index)
        elif current_code in self._lang_codes:
            self.lang_selector.setCurrentIndex(self.lang_selector.findData(current_code))
        self.lang_selector.blockSignals(False)

        self.source_section_label.setText("1  " + self.t("section_input").upper())
        self.output_section_label.setText("2  " + self.t("section_output").upper())
        self.mode_section_label.setText("3  " + self.t("section_mode").upper())
        self.opt_section_label.setText("4  " + self.t("section_options").upper())
        self.log_section_label.setText(self.t("section_log").upper())
        self.main_output_section_label.setText(self.t("main_page_target").upper())
        self.main_import_section_label.setText(self.t("main_page_import_section").upper())
        self.merge_page_title.setText(self.t("merge_page_title"))
        self.merge_page_desc.setText(self.t("merge_page_desc"))

        self.page_btn_merge.setText(self.t("page_mode_merge"))
        self.page_btn_main.setText(self.t("page_mode_main_folder"))
        self.page_btn_inside.setText(self.t("page_mode_inside_folder"))

        self.add_folder_btn.setText("+ " + self.t("btn_add_folder"))
        self.edit_prefix_btn.setText(self.t("btn_edit_prefix"))
        self.remove_btn.setText(self.t("btn_remove_selected"))
        self.clear_btn.setText(self.t("btn_clear_all"))
        self.output_btn.setText(self.t("btn_select_output"))
        self.main_output_btn.setText(self.t("btn_select_output"))
        self.main_add_folder_btn.setText("+ " + self.t("btn_add_folder"))
        self.main_remove_btn.setText(self.t("btn_remove_selected"))
        self.main_clear_btn.setText(self.t("btn_clear_all"))
        self.start_btn.setText(self.t("btn_start"))
        self._clear_log_btn.setText(self.t("btn_clear_log"))

        self.col_folder_lbl.setText(self.t("col_folder"))
        self.col_prefix_lbl.setText(self.t("col_prefix"))
        self.main_col_folder_lbl.setText(self.t("col_folder"))

        self.output_input.setPlaceholderText(self.t("section_output"))
        self.main_output_input.setPlaceholderText(self.t("main_page_target"))

        mode_data = {
            MODE_COPY_KEEP: self.t("mode_copy_keep"),
            MODE_COPY_DELETE: self.t("mode_copy_delete"),
            MODE_MOVE: self.t("mode_move"),
        }
        short_desc = {
            MODE_COPY_KEEP:   self.t("mode_desc_copy_keep"),
            MODE_COPY_DELETE: self.t("mode_desc_copy_delete"),
            MODE_MOVE:        self.t("mode_desc_move"),
        }
        for key, full in mode_data.items():
            card = self.mode_cards[key]
            card.title_lbl.setText(full)
            card.desc_lbl.setText(short_desc[key])

        self.clear_output_checkbox.setText(self.t("opt_clear_output"))
        self.main_clear_output_checkbox.setText(self.t("opt_clear_output"))
        self.allow_duplicates_checkbox.setText(self.t("opt_allow_duplicates"))
        self.main_allow_duplicates_checkbox.setText(self.t("opt_allow_duplicates"))
        self.safe_temp_checkbox.setText(self.t("opt_safe_temp_workspace"))
        self.main_safe_temp_checkbox.setText(self.t("opt_safe_temp_workspace"))
        self.main_remove_duplicates_checkbox.setText(self.t("opt_remove_duplicates"))
        self.mode_note_label.setText(self.t("mode_note"))
        if self._current_workflow == WORKFLOW_INSIDE_FOLDER:
            self.main_page_title.setText(self.t("inside_page_title"))
            self.main_page_desc.setText(self.t("inside_page_desc"))
            self.main_page_note_label.setText(self.t("inside_page_note"))
            self.main_import_section_label.setText(self.t("inside_page_import_section").upper())
        else:
            self.main_page_title.setText(self.t("main_page_title"))
            self.main_page_desc.setText(self.t("main_page_desc"))
            self.main_page_note_label.setText(self.t("main_page_note"))
            self.main_import_section_label.setText(self.t("main_page_import_section").upper())
        self.info_btn.setToolTip("About this app")
        self.info_btn_main.setToolTip("About this app")

        self.stat_added.set_label(self.t("stat_added"))
        self.stat_skipped.set_label(self.t("stat_skipped"))
        self.stat_total.set_label(self.t("stat_total_out"))
        self.stat_failed.set_label(self.t("stat_failed"))

        self._refresh_empty_label()
        self._apply_workflow_button_state()
        self._refresh_run_summary()
