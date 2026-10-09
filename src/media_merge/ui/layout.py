"""Window shell: palette, title bar, workflow tabs, splitter. Pages live in pages.py / run_panel.py."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..constants import WORKFLOW_INSIDE_FOLDER, WORKFLOW_MAIN_FOLDER, WORKFLOW_MERGE
from .styles import global_stylesheet
from .theme import C_ACCENT, C_BG, C_SURFACE, C_SURFACE2, C_TEXT, C_TEXT2, C_TEXT3


class AppLayoutMixin:
    def _apply_dark_palette(self):
        app = QApplication.instance()
        palette = QPalette()
        text, text2 = QColor(C_TEXT), QColor(C_TEXT2)

        palette.setColor(QPalette.Window, QColor(C_BG))
        palette.setColor(QPalette.WindowText, text)
        palette.setColor(QPalette.Base, QColor(C_SURFACE))
        palette.setColor(QPalette.AlternateBase, QColor(C_SURFACE2))
        palette.setColor(QPalette.Text, text)
        palette.setColor(QPalette.Button, QColor(C_SURFACE2))
        palette.setColor(QPalette.ButtonText, text)
        palette.setColor(QPalette.Highlight, QColor(C_ACCENT))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        palette.setColor(QPalette.PlaceholderText, QColor(C_TEXT3))
        for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
            palette.setColor(QPalette.Disabled, role, text2)
        app.setPalette(palette)

        app_font = QFont(self.font_family, 11)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(app_font)

    def _build_titlebar(self) -> QWidget:
        titlebar = QWidget()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(66)
        lay = QHBoxLayout(titlebar)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(10)

        self.app_name_label = QLabel()
        self.app_name_label.setStyleSheet(f"color:{C_TEXT}; font-size:23px; font-weight:700;")
        lay.addWidget(self.app_name_label)
        lay.addStretch()

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(f"color:{C_TEXT3}; font-size:13px;")
        self.desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.desc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.desc_label)
        lay.addSpacing(16)

        self.lang_label = QLabel()
        self.lang_label.setStyleSheet(f"color:{C_TEXT2}; font-size:13px;")
        lay.addWidget(self.lang_label)

        self.lang_selector = QComboBox()
        self.lang_selector.setObjectName("langSelector")
        for code in self._lang_codes:
            self.lang_selector.addItem("", code)
        self.lang_selector.currentIndexChanged.connect(self._on_lang_selector_changed)
        lay.addWidget(self.lang_selector)
        return titlebar

    def _build_workflow_bar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("workflowBar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(20, 7, 20, 7)
        lay.setSpacing(8)

        self.page_btn_merge = QPushButton()
        self.page_btn_main = QPushButton()
        self.page_btn_inside = QPushButton()
        self._workflow_buttons = {
            WORKFLOW_MERGE: self.page_btn_merge,
            WORKFLOW_MAIN_FOLDER: self.page_btn_main,
            WORKFLOW_INSIDE_FOLDER: self.page_btn_inside,
        }
        for workflow, btn in self._workflow_buttons.items():
            btn.setObjectName("pageModeBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _checked=False, wf=workflow: self._set_workflow(wf))
            lay.addWidget(btn)
        lay.addStretch()
        return bar

    def _build_ui(self):
        self.setStyleSheet(global_stylesheet(self.font_family))

        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_titlebar())
        root.addWidget(self._build_workflow_bar())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        self.left_page_stack = QStackedWidget()
        self.left_page_stack.setStyleSheet(f"background:{C_BG};")
        self.left_page_stack.addWidget(self._build_merge_page())
        self.left_page_stack.addWidget(self._build_organizer_page())
        splitter.addWidget(self.left_page_stack)
        splitter.addWidget(self._build_run_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([900, 380])

        self._retranslate_ui()
        self._set_output_path("")
        self._set_workflow(self._current_workflow)

        lang_index = self.lang_selector.findData(self.i18n.lang)
        if lang_index >= 0:
            self.lang_selector.setCurrentIndex(lang_index)
