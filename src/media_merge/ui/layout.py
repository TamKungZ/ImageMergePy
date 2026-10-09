from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    C_ACCENT,
    C_BG,
    C_DANGER,
    C_SUCCESS,
    C_SURFACE,
    C_SURFACE2,
    C_TEXT,
    C_TEXT2,
    C_TEXT3,
    C_WARNING,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)
from ..media_ops import (
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_MOVE,
)
from .localization import AppLocalizationMixin
from .styles import global_stylesheet
from .widgets import ModeCard, StatCard, _h_sep, _section_label

class AppLayoutMixin(AppLocalizationMixin):
    def _apply_dark_palette(self):
        app = QApplication.instance()
        palette = QPalette()
        bg = QColor(C_BG)
        surface = QColor(C_SURFACE)
        text = QColor(C_TEXT)
        text2 = QColor(C_TEXT2)
        accent = QColor(C_ACCENT)

        palette.setColor(QPalette.Window, bg)
        palette.setColor(QPalette.WindowText, text)
        palette.setColor(QPalette.Base, surface)
        palette.setColor(QPalette.AlternateBase, QColor(C_SURFACE2))
        palette.setColor(QPalette.Text, text)
        palette.setColor(QPalette.Button, QColor(C_SURFACE2))
        palette.setColor(QPalette.ButtonText, text)
        palette.setColor(QPalette.Highlight, accent)
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.PlaceholderText, QColor(C_TEXT3))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, text2)
        palette.setColor(QPalette.Disabled, QPalette.Text, text2)
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, text2)
        app.setPalette(palette)

        app_font = QFont(self.font_family, 11)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(app_font)

    def _build_ui(self):
        self.setStyleSheet(global_stylesheet(self.font_family))

        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        titlebar = QWidget()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(66)
        tb_lay = QHBoxLayout(titlebar)
        tb_lay.setContentsMargins(24, 0, 24, 0)
        tb_lay.setSpacing(10)

        self.app_name_label = QLabel()
        self.app_name_label.setStyleSheet(f"color:{C_TEXT}; font-size:23px; font-weight:700;")

        tb_lay.addWidget(self.app_name_label)
        tb_lay.addStretch()

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(f"color:{C_TEXT3}; font-size:13px;")
        self.desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.desc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        tb_lay.addWidget(self.desc_label)

        tb_lay.addSpacing(16)

        self.lang_label = QLabel()
        self.lang_label.setStyleSheet(f"color:{C_TEXT2}; font-size:13px;")
        tb_lay.addWidget(self.lang_label)

        self.lang_selector = QComboBox()
        self.lang_selector.setObjectName("langSelector")
        for code in self._lang_codes:
            self.lang_selector.addItem("", code)
        self.lang_selector.currentIndexChanged.connect(self._on_lang_selector_changed)
        tb_lay.addWidget(self.lang_selector)

        root_lay.addWidget(titlebar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        root_lay.addWidget(splitter, 1)

        mode_switch = QWidget()
        mode_switch.setObjectName("workflowBar")
        mode_switch_lay = QHBoxLayout(mode_switch)
        mode_switch_lay.setContentsMargins(20, 7, 20, 7)
        mode_switch_lay.setSpacing(8)

        self.page_btn_merge = QPushButton()
        self.page_btn_merge.setObjectName("pageModeBtn")
        self.page_btn_merge.setCursor(Qt.PointingHandCursor)
        self.page_btn_merge.clicked.connect(lambda: self._set_workflow(WORKFLOW_MERGE))
        mode_switch_lay.addWidget(self.page_btn_merge)

        self.page_btn_main = QPushButton()
        self.page_btn_main.setObjectName("pageModeBtn")
        self.page_btn_main.setCursor(Qt.PointingHandCursor)
        self.page_btn_main.clicked.connect(lambda: self._set_workflow(WORKFLOW_MAIN_FOLDER))
        mode_switch_lay.addWidget(self.page_btn_main)

        self.page_btn_inside = QPushButton()
        self.page_btn_inside.setObjectName("pageModeBtn")
        self.page_btn_inside.setCursor(Qt.PointingHandCursor)
        self.page_btn_inside.clicked.connect(lambda: self._set_workflow(WORKFLOW_INSIDE_FOLDER))
        mode_switch_lay.addWidget(self.page_btn_inside)
        mode_switch_lay.addStretch()
        root_lay.insertWidget(1, mode_switch)

        self.left_page_stack = QStackedWidget()
        self.left_page_stack.setStyleSheet(f"background:{C_BG};")

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setStyleSheet(f"background:{C_BG};")

        left_widget = QWidget()
        left_widget.setStyleSheet(f"background:{C_BG};")
        left_lay = QVBoxLayout(left_widget)
        left_lay.setContentsMargins(22, 20, 22, 22)
        left_lay.setSpacing(14)

        self.merge_page_title = QLabel()
        self.merge_page_title.setObjectName("pageTitle")
        left_lay.addWidget(self.merge_page_title)

        self.merge_page_desc = QLabel()
        self.merge_page_desc.setObjectName("pageDescription")
        self.merge_page_desc.setWordWrap(True)
        left_lay.addWidget(self.merge_page_desc)

        self.source_section_label = _section_label("")
        source_card = QWidget()
        source_card.setObjectName("contentCard")
        source_card_lay = QVBoxLayout(source_card)
        source_card_lay.setContentsMargins(16, 14, 16, 16)
        source_card_lay.setSpacing(12)
        src_hdr = QHBoxLayout()
        src_hdr.addWidget(self.source_section_label)
        src_hdr.addStretch()

        self.add_folder_btn = QPushButton()
        self.add_folder_btn.setObjectName("primaryBtn")
        self.add_folder_btn.setCursor(Qt.PointingHandCursor)
        self.add_folder_btn.setEnabled(True)
        self.add_folder_btn.setStyleSheet(
            "QPushButton { background:#1b1b1b; color:#ffffff; border:1px solid #1b1b1b; border-radius:7px; padding:8px 14px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#000000; border-color:#000000; }"
            "QPushButton:pressed { background:#343434; border-color:#343434; }"
            "QPushButton:disabled { background:#4a4a4a; color:#f2f2f2; border-color:#4a4a4a; }"
        )
        self.add_folder_btn.clicked.connect(self.add_input_folder)

        self.edit_prefix_btn = QPushButton()
        self.edit_prefix_btn.setObjectName("ghostBtn")
        self.edit_prefix_btn.setCursor(Qt.PointingHandCursor)
        self.edit_prefix_btn.setEnabled(False)
        self.edit_prefix_btn.clicked.connect(self.edit_selected_prefix)

        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("dangerGhostBtn")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_selected_input)

        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("dangerGhostBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_inputs)

        src_hdr.addWidget(self.add_folder_btn)
        src_hdr.addWidget(self.edit_prefix_btn)
        src_hdr.addWidget(self.remove_btn)
        src_hdr.addWidget(self.clear_btn)
        source_card_lay.addLayout(src_hdr)

        src_container = QWidget()
        src_container.setObjectName("sourceContainer")
        src_container_lay = QVBoxLayout(src_container)
        src_container_lay.setContentsMargins(0, 0, 0, 0)
        src_container_lay.setSpacing(0)

        src_header_bar = QWidget()
        src_header_bar.setObjectName("sourceHeaderBar")
        src_header_bar.setFixedHeight(30)
        shb_lay = QHBoxLayout(src_header_bar)
        shb_lay.setContentsMargins(14, 0, 10, 0)
        shb_lay.setSpacing(10)

        self.col_folder_lbl = QLabel()
        self.col_folder_lbl.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"
        )
        shb_lay.addWidget(self.col_folder_lbl, 1)

        self.col_prefix_lbl = QLabel()
        self.col_prefix_lbl.setFixedWidth(90)
        self.col_prefix_lbl.setAlignment(Qt.AlignCenter)
        self.col_prefix_lbl.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"
        )
        shb_lay.addWidget(self.col_prefix_lbl)
        shb_lay.addSpacing(34)

        src_container_lay.addWidget(src_header_bar)

        self.rows_scroll = QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rows_scroll.setFrameShape(QFrame.NoFrame)
        self.rows_scroll.setFixedHeight(132)
        self.rows_scroll.setStyleSheet("background:transparent;")

        self.rows_widget = QWidget()
        self.rows_widget.setStyleSheet("background:transparent;")
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.setAlignment(Qt.AlignTop)

        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; padding:28px;")
        self.rows_layout.addWidget(self.empty_label)

        self.rows_scroll.setWidget(self.rows_widget)
        src_container_lay.addWidget(self.rows_scroll)
        source_card_lay.addWidget(src_container)
        left_lay.addWidget(source_card)

        self.output_section_label = _section_label("")
        output_card = QWidget()
        output_card.setObjectName("contentCard")
        output_card_lay = QVBoxLayout(output_card)
        output_card_lay.setContentsMargins(16, 14, 16, 16)
        output_card_lay.setSpacing(10)
        output_card_lay.addWidget(self.output_section_label)

        out_row = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setObjectName("outputPath")
        self.output_input.setReadOnly(True)
        out_row.addWidget(self.output_input)

        self.output_btn = QPushButton()
        self.output_btn.setObjectName("ghostBtn")
        self.output_btn.setCursor(Qt.PointingHandCursor)
        self.output_btn.clicked.connect(self.choose_output_folder)
        out_row.addWidget(self.output_btn)
        output_card_lay.addLayout(out_row)
        left_lay.addWidget(output_card)

        self.mode_section_label = _section_label("")
        mode_card_container = QWidget()
        mode_card_container.setObjectName("contentCard")
        mode_card_container_lay = QVBoxLayout(mode_card_container)
        mode_card_container_lay.setContentsMargins(16, 14, 16, 16)
        mode_card_container_lay.setSpacing(12)
        mode_card_container_lay.addWidget(self.mode_section_label)

        mode_grid = QHBoxLayout()
        mode_grid.setSpacing(12)

        self.mode_cards: dict[str, ModeCard] = {}
        for key in [MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE]:
            card = ModeCard(key, "", "")
            card.clicked.connect(self._on_mode_card_clicked)
            self.mode_cards[key] = card
            mode_grid.addWidget(card)

        self.mode_cards[MODE_COPY_KEEP].set_selected(True)
        mode_card_container_lay.addLayout(mode_grid)
        left_lay.addWidget(mode_card_container)

        self.opt_section_label = _section_label("")
        options_card = QWidget()
        options_card.setObjectName("contentCard")
        options_card_lay = QVBoxLayout(options_card)
        options_card_lay.setContentsMargins(16, 14, 16, 16)
        options_card_lay.setSpacing(10)
        options_card_lay.addWidget(self.opt_section_label)

        self.clear_output_checkbox = QCheckBox()
        self.clear_output_checkbox.setChecked(True)
        options_card_lay.addWidget(self.clear_output_checkbox)

        self.allow_duplicates_checkbox = QCheckBox()
        options_card_lay.addWidget(self.allow_duplicates_checkbox)

        self.safe_temp_checkbox = QCheckBox()
        self.safe_temp_checkbox.setChecked(True)
        options_card_lay.addWidget(self.safe_temp_checkbox)

        self.mode_note_label = QLabel()
        self.mode_note_label.setObjectName("noteLabel")
        self.mode_note_label.setWordWrap(True)
        options_card_lay.addWidget(self.mode_note_label)
        left_lay.addWidget(options_card)
        left_lay.addStretch()

        footer_lay = QHBoxLayout()
        footer_lay.setContentsMargins(0, 0, 0, 0)
        footer_lay.setSpacing(8)
        self.info_btn = QPushButton("i")
        self.info_btn.setObjectName("infoBtn")
        self.info_btn.setCursor(Qt.PointingHandCursor)
        self.info_btn.clicked.connect(self.show_about_popup)
        footer_lay.addWidget(self.info_btn, 0, Qt.AlignLeft | Qt.AlignBottom)
        footer_lay.addStretch()
        left_lay.addLayout(footer_lay)

        left_scroll.setWidget(left_widget)
        self.left_page_stack.addWidget(left_scroll)

        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_scroll.setFrameShape(QFrame.NoFrame)
        main_scroll.setStyleSheet(f"background:{C_BG};")

        main_widget = QWidget()
        main_widget.setStyleSheet(f"background:{C_BG};")
        main_lay = QVBoxLayout(main_widget)
        main_lay.setContentsMargins(22, 20, 22, 22)
        main_lay.setSpacing(14)

        self.main_page_title = QLabel()
        self.main_page_title.setObjectName("pageTitle")
        main_lay.addWidget(self.main_page_title)

        self.main_page_desc = QLabel()
        self.main_page_desc.setObjectName("pageDescription")
        self.main_page_desc.setWordWrap(True)
        main_lay.addWidget(self.main_page_desc)

        main_target_card = QWidget()
        main_target_card.setObjectName("contentCard")
        main_target_card_lay = QVBoxLayout(main_target_card)
        main_target_card_lay.setContentsMargins(16, 14, 16, 16)
        main_target_card_lay.setSpacing(10)

        self.main_output_section_label = _section_label("")
        main_target_card_lay.addWidget(self.main_output_section_label)

        main_out_row = QHBoxLayout()
        self.main_output_input = QLineEdit()
        self.main_output_input.setObjectName("outputPath")
        self.main_output_input.setReadOnly(True)
        main_out_row.addWidget(self.main_output_input)

        self.main_output_btn = QPushButton()
        self.main_output_btn.setObjectName("ghostBtn")
        self.main_output_btn.setCursor(Qt.PointingHandCursor)
        self.main_output_btn.clicked.connect(self.choose_main_output_folder)
        main_out_row.addWidget(self.main_output_btn)
        main_target_card_lay.addLayout(main_out_row)

        self.main_clear_output_checkbox = QCheckBox()
        self.main_clear_output_checkbox.setChecked(True)
        main_target_card_lay.addWidget(self.main_clear_output_checkbox)

        self.main_remove_duplicates_checkbox = QCheckBox()
        main_target_card_lay.addWidget(self.main_remove_duplicates_checkbox)

        self.main_allow_duplicates_checkbox = QCheckBox()
        self.main_allow_duplicates_checkbox.stateChanged.connect(self._sync_duplicate_option_state)
        main_target_card_lay.addWidget(self.main_allow_duplicates_checkbox)

        self.main_safe_temp_checkbox = QCheckBox()
        self.main_safe_temp_checkbox.setChecked(True)
        main_target_card_lay.addWidget(self.main_safe_temp_checkbox)

        self.main_sources_hint_label = QLabel()
        self.main_sources_hint_label.setObjectName("noteLabel")
        self.main_sources_hint_label.setWordWrap(True)
        main_target_card_lay.addWidget(self.main_sources_hint_label)

        self.main_page_note_label = QLabel()
        self.main_page_note_label.setObjectName("noteLabel")
        self.main_page_note_label.setWordWrap(True)
        main_target_card_lay.addWidget(self.main_page_note_label)
        main_lay.addWidget(main_target_card)

        self.main_import_card = QWidget()
        self.main_import_card.setObjectName("contentCard")
        main_import_card_lay = QVBoxLayout(self.main_import_card)
        main_import_card_lay.setContentsMargins(16, 14, 16, 16)
        main_import_card_lay.setSpacing(10)
        self.main_import_section_label = _section_label("")
        main_import_card_lay.addWidget(self.main_import_section_label)

        main_src_hdr = QHBoxLayout()
        main_src_hdr.setContentsMargins(0, 0, 0, 0)
        main_src_hdr.setSpacing(8)
        main_src_hdr.addStretch()

        self.main_add_folder_btn = QPushButton()
        self.main_add_folder_btn.setObjectName("primaryBtn")
        self.main_add_folder_btn.setCursor(Qt.PointingHandCursor)
        self.main_add_folder_btn.setStyleSheet(
            "QPushButton { background:#1b1b1b; color:#ffffff; border:1px solid #1b1b1b; border-radius:7px; padding:8px 14px; font-size:14px; font-weight:600; }"
            "QPushButton:hover { background:#000000; border-color:#000000; }"
            "QPushButton:pressed { background:#343434; border-color:#343434; }"
            "QPushButton:disabled { background:#4a4a4a; color:#f2f2f2; border-color:#4a4a4a; }"
        )
        self.main_add_folder_btn.clicked.connect(self.add_main_input_folder)

        self.main_remove_btn = QPushButton()
        self.main_remove_btn.setObjectName("dangerGhostBtn")
        self.main_remove_btn.setCursor(Qt.PointingHandCursor)
        self.main_remove_btn.setEnabled(False)
        self.main_remove_btn.clicked.connect(self.remove_selected_main_input)

        self.main_clear_btn = QPushButton()
        self.main_clear_btn.setObjectName("dangerGhostBtn")
        self.main_clear_btn.setCursor(Qt.PointingHandCursor)
        self.main_clear_btn.clicked.connect(self.clear_main_inputs)

        main_src_hdr.addWidget(self.main_add_folder_btn)
        main_src_hdr.addWidget(self.main_remove_btn)
        main_src_hdr.addWidget(self.main_clear_btn)
        main_import_card_lay.addLayout(main_src_hdr)

        self.main_source_container = QWidget()
        self.main_source_container.setObjectName("sourceContainer")
        main_source_container_lay = QVBoxLayout(self.main_source_container)
        main_source_container_lay.setContentsMargins(0, 0, 0, 0)
        main_source_container_lay.setSpacing(0)

        main_src_header_bar = QWidget()
        main_src_header_bar.setObjectName("sourceHeaderBar")
        main_src_header_bar.setFixedHeight(30)
        main_shb_lay = QHBoxLayout(main_src_header_bar)
        main_shb_lay.setContentsMargins(14, 0, 10, 0)
        main_shb_lay.setSpacing(10)

        self.main_col_folder_lbl = QLabel()
        self.main_col_folder_lbl.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"
        )
        main_shb_lay.addWidget(self.main_col_folder_lbl, 1)
        main_shb_lay.addSpacing(34)
        main_source_container_lay.addWidget(main_src_header_bar)

        self.main_rows_scroll = QScrollArea()
        self.main_rows_scroll.setWidgetResizable(True)
        self.main_rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_rows_scroll.setFrameShape(QFrame.NoFrame)
        self.main_rows_scroll.setFixedHeight(132)
        self.main_rows_scroll.setStyleSheet("background:transparent;")

        self.main_rows_widget = QWidget()
        self.main_rows_widget.setStyleSheet("background:transparent;")
        self.main_rows_layout = QVBoxLayout(self.main_rows_widget)
        self.main_rows_layout.setContentsMargins(0, 0, 0, 0)
        self.main_rows_layout.setSpacing(0)
        self.main_rows_layout.setAlignment(Qt.AlignTop)

        self.main_empty_label = QLabel()
        self.main_empty_label.setAlignment(Qt.AlignCenter)
        self.main_empty_label.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; padding:28px;")
        self.main_rows_layout.addWidget(self.main_empty_label)

        self.main_rows_scroll.setWidget(self.main_rows_widget)
        main_source_container_lay.addWidget(self.main_rows_scroll)
        main_import_card_lay.addWidget(self.main_source_container)
        main_lay.addWidget(self.main_import_card)

        main_lay.addStretch()

        main_footer_lay = QHBoxLayout()
        main_footer_lay.setContentsMargins(0, 0, 0, 0)
        self.info_btn_main = QPushButton("i")
        self.info_btn_main.setObjectName("infoBtn")
        self.info_btn_main.setCursor(Qt.PointingHandCursor)
        self.info_btn_main.clicked.connect(self.show_about_popup)
        main_footer_lay.addWidget(self.info_btn_main, 0, Qt.AlignLeft | Qt.AlignBottom)
        main_footer_lay.addStretch()
        main_lay.addLayout(main_footer_lay)

        main_scroll.setWidget(main_widget)
        self.left_page_stack.addWidget(main_scroll)

        splitter.addWidget(self.left_page_stack)

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel.setMinimumWidth(330)
        right_panel.setMaximumWidth(410)
        rp_lay = QVBoxLayout(right_panel)
        rp_lay.setContentsMargins(0, 0, 0, 0)
        rp_lay.setSpacing(0)

        btn_area = QWidget()
        btn_area.setStyleSheet(f"background:{C_SURFACE};")
        btn_area_lay = QVBoxLayout(btn_area)
        btn_area_lay.setContentsMargins(18, 18, 18, 18)
        btn_area_lay.setSpacing(7)

        self.run_title_label = QLabel()
        self.run_title_label.setObjectName("runTitle")
        btn_area_lay.addWidget(self.run_title_label)

        self.run_summary_label = QLabel()
        self.run_summary_label.setObjectName("runSummary")
        self.run_summary_label.setWordWrap(True)
        btn_area_lay.addWidget(self.run_summary_label)
        btn_area_lay.addSpacing(6)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(
            "QPushButton { background:#111111; color:#ffffff; border:1px solid #111111; border-radius:10px; font-size:20px; font-weight:700; padding:14px; }"
            "QPushButton:hover { background:#242424; border-color:#242424; }"
            "QPushButton:pressed { background:#000000; border-color:#000000; }"
            "QPushButton:disabled { background:#4a4a4a; color:#f2f2f2; border-color:#4a4a4a; }"
        )
        self.start_btn.clicked.connect(self.start_process)
        btn_area_lay.addWidget(self.start_btn)
        rp_lay.addWidget(btn_area)

        rp_lay.addWidget(_h_sep())

        stats_widget = QWidget()
        stats_widget.setStyleSheet(f"background:{C_SURFACE};")
        stats_lay = QVBoxLayout(stats_widget)
        stats_lay.setContentsMargins(16, 16, 16, 16)
        stats_lay.setSpacing(8)

        grid1 = QHBoxLayout()
        grid1.setSpacing(8)
        self.stat_added   = StatCard(self.t("stat_added"),   C_SUCCESS)
        self.stat_skipped = StatCard(self.t("stat_skipped"), C_WARNING)
        grid1.addWidget(self.stat_added)
        grid1.addWidget(self.stat_skipped)

        grid2 = QHBoxLayout()
        grid2.setSpacing(8)
        self.stat_total  = StatCard(self.t("stat_total_out"), C_TEXT)
        self.stat_failed = StatCard(self.t("stat_failed"),    C_DANGER)
        grid2.addWidget(self.stat_total)
        grid2.addWidget(self.stat_failed)

        stats_lay.addLayout(grid1)
        stats_lay.addLayout(grid2)
        rp_lay.addWidget(stats_widget)

        rp_lay.addWidget(_h_sep())

        log_hdr = QWidget()
        log_hdr.setStyleSheet(f"background:{C_SURFACE};")
        log_hdr_lay = QHBoxLayout(log_hdr)
        log_hdr_lay.setContentsMargins(16, 10, 10, 6)

        self.log_section_label = _section_label("")
        log_hdr_lay.addWidget(self.log_section_label)
        log_hdr_lay.addStretch()

        clear_log_btn = QPushButton()
        clear_log_btn.setObjectName("tinyBtn")
        clear_log_btn.setCursor(Qt.PointingHandCursor)
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        self._clear_log_btn = clear_log_btn
        log_hdr_lay.addWidget(clear_log_btn)
        rp_lay.addWidget(log_hdr)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        rp_lay.addWidget(self.log_text, 1)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 380])

        self._retranslate_ui()
        self._set_output_path("")
        self._set_workflow(self._current_workflow)

        lang_index = self.lang_selector.findData(self.i18n.lang)
        if lang_index >= 0:
            self.lang_selector.setCurrentIndex(lang_index)
