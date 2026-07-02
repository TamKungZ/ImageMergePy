import re
from pathlib import Path

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
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
    APP_DIR,
    APP_FALLBACK_TITLE,
    APP_METADATA,
    C_ACCENT,
    C_ACCENT_DIM,
    C_BG,
    C_BORDER,
    C_BORDER2,
    C_DANGER,
    C_SUCCESS,
    C_SURFACE,
    C_SURFACE2,
    C_SURFACE3,
    C_TEXT,
    C_TEXT2,
    C_TEXT3,
    C_WARNING,
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
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
    normalize_prefix,
)
from ..worker import ProcessWorker
from .widgets import FolderOnlyRow, ModeCard, SourceRow, StatCard, _h_sep, _section_label

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n(detect_language())
        self.t = self.i18n.t

        icon_path = APP_DIR / "assets" / "icon.ico"
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

    def _global_stylesheet(self) -> str:
        ff = self.font_family
        return f"""
        * {{ font-family: "{ff}"; }}
        QMainWindow, QWidget#central {{ background: {C_BG}; }}

        /* Titlebar */
        QWidget#titlebar {{ background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER2}; }}
        QWidget#workflowBar {{ background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER2}; }}
        QWidget#contentCard {{
            background: {C_SURFACE};
            border: 1px solid {C_BORDER2};
            border-radius: 12px;
        }}
        QLabel#pageTitle {{ color:{C_TEXT}; font-size:24px; font-weight:700; }}
        QLabel#pageDescription {{ color:{C_TEXT3}; font-size:13px; }}
        QLabel#runTitle {{ color:{C_TEXT}; font-size:18px; font-weight:700; }}
        QLabel#runSummary {{ color:{C_TEXT3}; font-size:13px; }}

        /* Scroll areas */
        QScrollArea {{ background: transparent; border: none; }}
        QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {C_SURFACE3}; border-radius: 4px; min-height: 28px; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

        /* Source list container */
        QWidget#sourceContainer {{ background: {C_SURFACE}; border: 1px solid {C_BORDER2}; border-radius: 10px; }}
        QWidget#sourceHeaderBar  {{ background: transparent; border-bottom: 1px solid {C_BORDER2}; }}

        /* Output path input */
        QLineEdit#outputPath {{
            background: {C_SURFACE}; border: 1px solid {C_BORDER2}; border-radius: 8px;
            color: {C_TEXT}; padding: 10px 12px; font-size: 15px;
        }}
        QLineEdit#outputPath:focus {{ border-color: {C_ACCENT}; }}

        QComboBox#langSelector {{
            background: {C_SURFACE2};
            color: {C_TEXT};
            border: 1px solid {C_BORDER2};
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 13px;
            min-width: 92px;
        }}
        QComboBox#langSelector::drop-down {{ border: none; width: 22px; }}
        QComboBox#langSelector QAbstractItemView {{
            border: 1px solid {C_BORDER2};
            background: {C_SURFACE};
            color: {C_TEXT};
            selection-background-color: {C_ACCENT_DIM};
        }}

        QPushButton#infoBtn {{
            background: {C_SURFACE2};
            color: {C_TEXT2};
            border: 1px solid {C_BORDER2};
            border-radius: 14px;
            font-size: 15px;
            font-weight: 700;
            min-width: 28px;
            min-height: 28px;
            max-width: 28px;
            max-height: 28px;
        }}
        QPushButton#infoBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; border-color: {C_ACCENT}; }}
        QPushButton#infoBtn:pressed {{ background: {C_ACCENT_DIM}; }}

        /* Log area */
        QTextEdit#logText {{
            background: {C_SURFACE}; border: none; border-radius: 0;
            color: {C_TEXT2}; font-size: 13px;
            font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
        }}

        /* Right panel */
        QWidget#rightPanel {{ background: {C_SURFACE}; border-left: 1px solid {C_BORDER2}; }}

        /* Start button */
        QPushButton#startBtn {{
            background: {C_ACCENT}; color: #ffffff; border: none;
            border-radius: 10px; font-size: 20px; font-weight: 700; padding: 14px;
        }}
        QPushButton#startBtn:hover {{ background: #242424; }}
        QPushButton#startBtn:pressed {{ background: #000000; }}
        QPushButton#startBtn:disabled {{
            background: #4a4a4a; color: #f2f2f2; border: 1px solid #4a4a4a;
        }}

        /* Secondary buttons */
        QPushButton#primaryBtn {{
            background-color: #1b1b1b; color: #ffffff; border: 1px solid #1b1b1b;
            border-radius: 7px; padding: 8px 14px; font-size: 14px; font-weight: 600;
        }}
        QPushButton#primaryBtn:hover {{ background-color: #000000; border-color: #000000; }}
        QPushButton#primaryBtn:pressed {{ background-color: #343434; border-color: #343434; }}
        QPushButton#primaryBtn:disabled {{ background-color: #4a4a4a; color: #f2f2f2; border-color: #4a4a4a; }}

        QPushButton#ghostBtn {{
            background: {C_SURFACE2}; color: {C_TEXT}; border: 1px solid {C_BORDER2};
            border-radius: 7px; padding: 8px 12px; font-size: 14px;
        }}
        QPushButton#ghostBtn:hover {{ background: {C_SURFACE3}; }}
        QPushButton#ghostBtn:disabled {{ color: {C_TEXT3}; }}

        QPushButton#dangerGhostBtn {{
            background: transparent; color: {C_TEXT3}; border: 1px solid {C_BORDER};
            border-radius: 7px; padding: 8px 12px; font-size: 14px;
        }}
        QPushButton#dangerGhostBtn:hover {{ background: rgba(20,20,20,0.08); color: {C_DANGER}; border-color: {C_BORDER2}; }}
        QPushButton#dangerGhostBtn:disabled {{ color: {C_TEXT3}; }}

        QPushButton#tinyBtn {{
            background: transparent; color: {C_TEXT3}; border: none;
            border-radius: 5px; padding: 3px 8px; font-size: 12px;
        }}
        QPushButton#tinyBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; }}

        QPushButton#pageModeBtn {{
            background: transparent; color: {C_TEXT2}; border: 1px solid transparent;
            border-radius: 9px; padding: 9px 14px; font-size: 13px; font-weight: 600;
        }}
        QPushButton#pageModeBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; }}
        QPushButton#pageModeBtn[active="true"] {{
            background: {C_ACCENT}; color: #ffffff; border: 1px solid {C_ACCENT};
        }}

        /* Checkbox */
        QCheckBox {{ color: {C_TEXT2}; font-size: 14px; spacing: 8px; }}
        QCheckBox::indicator {{
            width: 18px; height: 18px; border-radius: 4px;
            border: 1.5px solid {C_BORDER2}; background: {C_SURFACE};
        }}
        QCheckBox::indicator:checked {{
            background: {C_ACCENT}; border-color: {C_ACCENT};
            image: none;
        }}
        QCheckBox::indicator:hover {{ border-color: {C_ACCENT}; }}

        /* Splitter */
        QSplitter::handle {{ background: {C_BORDER2}; width: 1px; }}

        /* Note label */
        QLabel#noteLabel {{ color: {C_TEXT3}; font-size: 13px; line-height: 1.5; }}
        """

    def _build_ui(self):
        self.setStyleSheet(self._global_stylesheet())

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


