"""Window shell: palette, navigation sidebar, page stack and the action bar."""
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QComboBox, QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from ..constants import WORKFLOW_INSIDE_FOLDER, WORKFLOW_MAIN_FOLDER, WORKFLOW_MERGE
from .styles import global_stylesheet
from .theme import C_ACCENT, C_BG, C_DISABLED, C_SURFACE, C_SURFACE2, C_TEXT, C_TEXT3
from .widgets import NavItem, make_button, styled


class AppLayoutMixin:
    def _apply_palette(self):
        app = QApplication.instance()
        palette = QPalette()
        text = QColor(C_TEXT)
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
            palette.setColor(QPalette.Disabled, role, QColor(C_DISABLED))
        app.setPalette(palette)

        app_font = QFont(self.font_family, 11)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(app_font)

    def _build_sidebar(self) -> QWidget:
        side = styled(QWidget(), "sidebar")
        side.setFixedWidth(244)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(16, 26, 16, 16)
        lay.setSpacing(4)

        self.app_name_label = QLabel()
        self.app_name_label.setObjectName("brandName")
        lay.addWidget(self.app_name_label)
        self.app_tagline_label = QLabel()
        self.app_tagline_label.setObjectName("brandTag")
        self.app_tagline_label.setWordWrap(True)
        lay.addWidget(self.app_tagline_label)
        lay.addSpacing(28)

        self.nav_caption_label = QLabel()
        self.nav_caption_label.setObjectName("sidebarCaption")
        lay.addWidget(self.nav_caption_label)
        lay.addSpacing(6)

        self._nav_items: dict[str, NavItem] = {}
        for workflow in (WORKFLOW_MERGE, WORKFLOW_MAIN_FOLDER, WORKFLOW_INSIDE_FOLDER):
            item = NavItem(workflow)
            item.clicked.connect(self._on_nav_clicked)
            self._nav_items[workflow] = item
            lay.addWidget(item)

        lay.addStretch(1)

        self.lang_label = QLabel()
        self.lang_label.setObjectName("sidebarCaption")
        lay.addWidget(self.lang_label)
        self.lang_selector = QComboBox()
        self.lang_selector.setObjectName("langSelector")
        for code in self._lang_codes:
            self.lang_selector.addItem("", code)
        self.lang_selector.currentIndexChanged.connect(self._on_lang_selector_changed)
        lay.addWidget(self.lang_selector)
        lay.addSpacing(8)

        self.about_btn = make_button("sidebarBtn", self.show_about_popup)
        lay.addWidget(self.about_btn)
        return side

    def _build_ui(self):
        self.setStyleSheet(global_stylesheet(self.font_family))

        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_sidebar())

        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(0)
        self.page_stack = QStackedWidget()
        self.page_stack.addWidget(self._build_merge_page())
        self.page_stack.addWidget(self._build_organizer_page())
        main.addWidget(self.page_stack, 1)
        main.addWidget(self._build_action_bar())
        root.addLayout(main, 1)

        self._set_output_path("")
        self._set_workflow(self._current_workflow)

        lang_index = self.lang_selector.findData(self.i18n.lang)
        if lang_index >= 0:
            self.lang_selector.setCurrentIndex(lang_index)
