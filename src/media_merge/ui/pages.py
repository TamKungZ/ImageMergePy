"""The two workspace pages: Merge folders, and the folder organizer (Add to library / Tidy a folder)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..constants import MODE_COPY_DELETE, MODE_COPY_KEEP, MODE_MOVE
from .source_list import SourceListPanel
from .widgets import ChoiceCard, OptionRow, StepCard, make_button, make_hint, make_path_row, styled

_CONTENT_MAX_WIDTH = 920


def _make_page() -> tuple[QScrollArea, QVBoxLayout]:
    """Scrollable page with a centred, width-limited content column."""
    body = styled(QWidget(), "pageBody")
    outer = QHBoxLayout(body)
    outer.setContentsMargins(32, 28, 32, 28)
    outer.setSpacing(0)

    content = QWidget()
    content.setMaximumWidth(_CONTENT_MAX_WIDTH)
    lay = QVBoxLayout(content)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)

    outer.addStretch(1)
    outer.addWidget(content, 100)
    outer.addStretch(1)

    scroll = QScrollArea()
    scroll.setObjectName("pageScroll")
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(body)
    return scroll, lay


def _page_header(lay: QVBoxLayout) -> tuple[QLabel, QLabel]:
    title = QLabel()
    title.setObjectName("pageTitle")
    lay.addWidget(title)
    desc = QLabel()
    desc.setObjectName("pageDesc")
    desc.setWordWrap(True)
    lay.addWidget(desc)
    lay.addSpacing(4)
    return title, desc


class PagesMixin:
    # ------------------------------------------------------------------ merge
    def _build_merge_page(self) -> QScrollArea:
        scroll, lay = _make_page()
        self.merge_page_title, self.merge_page_desc = _page_header(lay)

        # 1 · source folders
        self.merge_sources = SourceListPanel(with_prefix=True)
        self.merge_sources.selection_changed.connect(self._on_merge_selection_changed)
        self.merge_sources.changed.connect(self._on_sources_changed)
        self.merge_sources.paths_dropped.connect(lambda paths: self._add_dropped(self.merge_sources, paths))
        self.merge_sources.activated.connect(lambda _path: self.edit_selected_prefix())

        self.merge_step_sources = StepCard(1)
        self.add_folder_btn = make_button("primaryBtn", lambda: self._add_source_folder(self.merge_sources))
        self.edit_prefix_btn = make_button("secondaryBtn", self.edit_selected_prefix, enabled=False)
        self.remove_btn = make_button("dangerQuietBtn", self.merge_sources.remove_selected, enabled=False)
        self.clear_btn = make_button("dangerQuietBtn", self.merge_sources.clear)
        for btn in (self.add_folder_btn, self.edit_prefix_btn, self.remove_btn, self.clear_btn):
            self.merge_step_sources.add_action(btn)
        self.merge_step_sources.body.addWidget(self.merge_sources)
        lay.addWidget(self.merge_step_sources)

        # 2 · output folder
        self.merge_step_output = StepCard(2)
        row, self.output_input, self.output_btn = make_path_row(self.choose_output_folder)
        self.merge_step_output.body.addLayout(row)
        lay.addWidget(self.merge_step_output)

        # 3 · what happens to the originals
        self.merge_step_mode = StepCard(3)
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.mode_cards: dict[str, ChoiceCard] = {}
        for key, danger in ((MODE_COPY_KEEP, False), (MODE_COPY_DELETE, True), (MODE_MOVE, False)):
            card = ChoiceCard(key, danger=danger)
            card.clicked.connect(self._on_mode_card_clicked)
            self.mode_cards[key] = card
            cards.addWidget(card, 1)
        self.mode_cards[MODE_COPY_KEEP].set_selected(True)
        self.merge_step_mode.body.addLayout(cards)
        lay.addWidget(self.merge_step_mode)

        # 4 · options
        self.merge_step_options = StepCard(4)
        self.clear_output_opt = OptionRow(checked=False)
        self.allow_duplicates_opt = OptionRow()
        self.safe_temp_opt = OptionRow(checked=True)
        for opt in (self.clear_output_opt, self.allow_duplicates_opt, self.safe_temp_opt):
            self.merge_step_options.body.addWidget(opt)
        self.mode_note_label = make_hint()
        self.merge_step_options.body.addWidget(self.mode_note_label)
        lay.addWidget(self.merge_step_options)

        lay.addStretch(1)
        return scroll

    # -------------------------------------------------------------- organizer
    def _build_organizer_page(self) -> QScrollArea:
        scroll, lay = _make_page()
        self.main_page_title, self.main_page_desc = _page_header(lay)

        # 1 · target folder
        self.org_step_target = StepCard(1)
        row, self.main_output_input, self.main_output_btn = make_path_row(self.choose_output_folder)
        self.org_step_target.body.addLayout(row)
        lay.addWidget(self.org_step_target)

        # 2 · folders to import (library workflow only)
        self.main_sources = SourceListPanel(with_prefix=False)
        self.main_sources.selection_changed.connect(self._on_main_selection_changed)
        self.main_sources.changed.connect(self._on_sources_changed)
        self.main_sources.paths_dropped.connect(lambda paths: self._add_dropped(self.main_sources, paths))

        self.org_step_import = StepCard(2)
        self.main_add_folder_btn = make_button("primaryBtn", lambda: self._add_source_folder(self.main_sources))
        self.main_remove_btn = make_button("dangerQuietBtn", self.main_sources.remove_selected, enabled=False)
        self.main_clear_btn = make_button("dangerQuietBtn", self.main_sources.clear)
        for btn in (self.main_add_folder_btn, self.main_remove_btn, self.main_clear_btn):
            self.org_step_import.add_action(btn)
        self.org_step_import.body.addWidget(self.main_sources)
        lay.addWidget(self.org_step_import)

        # 3 · options
        self.org_step_options = StepCard(3)
        self.org_remove_duplicates_opt = OptionRow()
        self.org_allow_duplicates_opt = OptionRow()
        self.org_allow_duplicates_opt.toggled.connect(self._sync_duplicate_option_state)
        self.org_safe_temp_opt = OptionRow(checked=True)
        for opt in (self.org_remove_duplicates_opt, self.org_allow_duplicates_opt, self.org_safe_temp_opt):
            self.org_step_options.body.addWidget(opt)
        self.main_page_note_label = make_hint()
        self.org_step_options.body.addWidget(self.main_page_note_label)
        lay.addWidget(self.org_step_options)

        lay.addStretch(1)
        return scroll
