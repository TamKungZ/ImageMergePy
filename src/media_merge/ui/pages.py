"""The two left-hand pages: Merge, and Organizer (main-folder / inside-folder)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ..constants import MODE_COPY_DELETE, MODE_COPY_KEEP, MODE_MOVE
from .source_list import SourceListPanel
from .theme import C_BG
from .widgets import (
    PRIMARY_BTN_STYLE,
    ModeCard,
    _section_label,
    make_button,
    make_card,
    make_output_row,
)


def _make_page_body() -> tuple[QWidget, QVBoxLayout]:
    body = QWidget()
    body.setStyleSheet(f"background:{C_BG};")
    lay = QVBoxLayout(body)
    lay.setContentsMargins(22, 20, 22, 22)
    lay.setSpacing(14)
    return body, lay


def _wrap_in_scroll(body: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setStyleSheet(f"background:{C_BG};")
    scroll.setWidget(body)
    return scroll


def _page_header(lay: QVBoxLayout) -> tuple[QLabel, QLabel]:
    title = QLabel()
    title.setObjectName("pageTitle")
    lay.addWidget(title)
    desc = QLabel()
    desc.setObjectName("pageDescription")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    return title, desc


def _note_label() -> QLabel:
    label = QLabel()
    label.setObjectName("noteLabel")
    label.setWordWrap(True)
    return label


class PagesMixin:
    def _make_info_footer(self, lay: QVBoxLayout) -> QPushButton:
        footer = QHBoxLayout()
        footer.setContentsMargins(0, 0, 0, 0)
        footer.setSpacing(8)
        btn = QPushButton("i")
        btn.setObjectName("infoBtn")
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.show_about_popup)
        footer.addWidget(btn, 0, Qt.AlignLeft | Qt.AlignBottom)
        footer.addStretch()
        lay.addLayout(footer)
        return btn

    # ------------------------------------------------------------------ merge
    def _build_merge_page(self) -> QScrollArea:
        body, lay = _make_page_body()
        self.merge_page_title, self.merge_page_desc = _page_header(lay)

        # 1 · sources
        self.merge_sources = SourceListPanel(with_prefix=True)
        self.merge_sources.selection_changed.connect(self._on_merge_selection_changed)
        self.merge_sources.changed.connect(self._on_sources_changed)

        card, card_lay = make_card()
        header = QHBoxLayout()
        self.source_section_label = _section_label("")
        header.addWidget(self.source_section_label)
        header.addStretch()
        self.add_folder_btn = make_button(
            "primaryBtn", lambda: self._add_source_folder(self.merge_sources), style=PRIMARY_BTN_STYLE
        )
        self.edit_prefix_btn = make_button("ghostBtn", self.edit_selected_prefix, enabled=False)
        self.remove_btn = make_button("dangerGhostBtn", self.merge_sources.remove_selected, enabled=False)
        self.clear_btn = make_button("dangerGhostBtn", self.merge_sources.clear)
        for btn in (self.add_folder_btn, self.edit_prefix_btn, self.remove_btn, self.clear_btn):
            header.addWidget(btn)
        card_lay.addLayout(header)
        card_lay.addWidget(self.merge_sources)
        lay.addWidget(card)

        # 2 · output
        card, card_lay = make_card(spacing=10)
        self.output_section_label = _section_label("")
        card_lay.addWidget(self.output_section_label)
        row, self.output_input, self.output_btn = make_output_row(self.choose_output_folder)
        card_lay.addLayout(row)
        lay.addWidget(card)

        # 3 · mode
        card, card_lay = make_card()
        self.mode_section_label = _section_label("")
        card_lay.addWidget(self.mode_section_label)
        grid = QHBoxLayout()
        grid.setSpacing(12)
        self.mode_cards: dict[str, ModeCard] = {}
        for key in (MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE):
            mode_card = ModeCard(key, "", "")
            mode_card.clicked.connect(self._on_mode_card_clicked)
            self.mode_cards[key] = mode_card
            grid.addWidget(mode_card)
        self.mode_cards[MODE_COPY_KEEP].set_selected(True)
        card_lay.addLayout(grid)
        lay.addWidget(card)

        # 4 · options
        card, card_lay = make_card(spacing=10)
        self.opt_section_label = _section_label("")
        card_lay.addWidget(self.opt_section_label)
        self.clear_output_checkbox = QCheckBox()
        self.clear_output_checkbox.setChecked(True)
        self.allow_duplicates_checkbox = QCheckBox()
        self.safe_temp_checkbox = QCheckBox()
        self.safe_temp_checkbox.setChecked(True)
        for box in (self.clear_output_checkbox, self.allow_duplicates_checkbox, self.safe_temp_checkbox):
            card_lay.addWidget(box)
        self.mode_note_label = _note_label()
        card_lay.addWidget(self.mode_note_label)
        lay.addWidget(card)

        lay.addStretch()
        self.info_btn = self._make_info_footer(lay)
        return _wrap_in_scroll(body)

    # -------------------------------------------------------------- organizer
    def _build_organizer_page(self) -> QScrollArea:
        body, lay = _make_page_body()
        self.main_page_title, self.main_page_desc = _page_header(lay)

        # target folder + options
        card, card_lay = make_card(spacing=10)
        self.main_output_section_label = _section_label("")
        card_lay.addWidget(self.main_output_section_label)
        row, self.main_output_input, self.main_output_btn = make_output_row(self.choose_output_folder)
        card_lay.addLayout(row)

        self.main_clear_output_checkbox = QCheckBox()
        self.main_clear_output_checkbox.setChecked(True)
        self.main_remove_duplicates_checkbox = QCheckBox()
        self.main_allow_duplicates_checkbox = QCheckBox()
        self.main_allow_duplicates_checkbox.stateChanged.connect(self._sync_duplicate_option_state)
        self.main_safe_temp_checkbox = QCheckBox()
        self.main_safe_temp_checkbox.setChecked(True)
        for box in (
            self.main_clear_output_checkbox,
            self.main_remove_duplicates_checkbox,
            self.main_allow_duplicates_checkbox,
            self.main_safe_temp_checkbox,
        ):
            card_lay.addWidget(box)

        self.main_sources_hint_label = _note_label()
        card_lay.addWidget(self.main_sources_hint_label)
        self.main_page_note_label = _note_label()
        card_lay.addWidget(self.main_page_note_label)
        lay.addWidget(card)

        # import folders (hidden for the inside-folder workflow)
        self.main_sources = SourceListPanel(with_prefix=False)
        self.main_sources.selection_changed.connect(self._on_main_selection_changed)
        self.main_sources.changed.connect(self._on_sources_changed)

        self.main_import_card, card_lay = make_card(spacing=10)
        self.main_import_section_label = _section_label("")
        card_lay.addWidget(self.main_import_section_label)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        header.addStretch()
        self.main_add_folder_btn = make_button(
            "primaryBtn", lambda: self._add_source_folder(self.main_sources), style=PRIMARY_BTN_STYLE
        )
        self.main_remove_btn = make_button("dangerGhostBtn", self.main_sources.remove_selected, enabled=False)
        self.main_clear_btn = make_button("dangerGhostBtn", self.main_sources.clear)
        for btn in (self.main_add_folder_btn, self.main_remove_btn, self.main_clear_btn):
            header.addWidget(btn)
        card_lay.addLayout(header)
        card_lay.addWidget(self.main_sources)
        lay.addWidget(self.main_import_card)

        lay.addStretch()
        self.info_btn_main = self._make_info_footer(lay)
        return _wrap_in_scroll(body)
