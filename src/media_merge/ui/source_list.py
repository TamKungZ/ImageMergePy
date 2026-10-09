from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..models import SourceFolder
from .theme import C_BORDER, C_TEXT3
from .widgets import FolderOnlyRow, SourceRow

_HEADER_LABEL_STYLE = f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"


class SourceListPanel(QWidget):
    """Folder list with optional prefix column, single selection and an empty-state label.

    Used by both the merge page (with prefixes) and the main-folder page (folders only).
    """

    changed = Signal()               # entries were added / removed
    selection_changed = Signal(bool)  # True when a row is selected

    def __init__(self, with_prefix: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("sourceContainer")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._with_prefix = with_prefix
        self._folders: dict[str, SourceFolder] = {}
        self._rows: dict[str, tuple[QWidget, QFrame]] = {}
        self._selected: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("sourceHeaderBar")
        header.setFixedHeight(30)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(14, 0, 10, 0)
        header_lay.setSpacing(10)
        self.folder_header = QLabel()
        self.folder_header.setStyleSheet(_HEADER_LABEL_STYLE)
        header_lay.addWidget(self.folder_header, 1)
        self.prefix_header: QLabel | None = None
        if with_prefix:
            self.prefix_header = QLabel()
            self.prefix_header.setFixedWidth(110)
            self.prefix_header.setAlignment(Qt.AlignCenter)
            self.prefix_header.setStyleSheet(_HEADER_LABEL_STYLE)
            header_lay.addWidget(self.prefix_header)
        header_lay.addSpacing(34)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(132)
        scroll.setStyleSheet("background:transparent;")

        body = QWidget()
        body.setStyleSheet("background:transparent;")
        self._rows_layout = QVBoxLayout(body)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.setAlignment(Qt.AlignTop)

        self._empty = QLabel()
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; padding:28px;")
        self._rows_layout.addWidget(self._empty)

        scroll.setWidget(body)
        root.addWidget(scroll)

    # ---- queries -------------------------------------------------------
    def folders(self) -> list[SourceFolder]:
        return list(self._folders.values())

    def count(self) -> int:
        return len(self._folders)

    @property
    def selected_path(self) -> str | None:
        return self._selected

    def selected_prefix(self) -> str:
        folder = self._folders.get(self._selected or "")
        return folder.prefix if folder else ""

    # ---- text ----------------------------------------------------------
    def retranslate(self, folder_text: str, prefix_text: str, empty_text: str) -> None:
        self.folder_header.setText(folder_text)
        if self.prefix_header is not None:
            self.prefix_header.setText(prefix_text)
        self._empty.setText(empty_text)

    # ---- mutations -----------------------------------------------------
    def add(self, path: Path, prefix: str = "") -> bool:
        key = str(path)
        if key in self._folders:
            return False
        self._folders[key] = SourceFolder(path, prefix)

        row = SourceRow(key, prefix) if self._with_prefix else FolderOnlyRow(key)
        row.remove_requested.connect(self.remove)
        row.edit_requested.connect(self._toggle_selection)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BORDER}; border:none;")
        self._rows_layout.addWidget(row)
        self._rows_layout.addWidget(sep)
        self._rows[key] = (row, sep)

        self._empty.setVisible(False)
        self.changed.emit()
        return True

    def _drop(self, key: str) -> None:
        self._folders.pop(key, None)
        row, sep = self._rows.pop(key)
        for widget in (row, sep):
            self._rows_layout.removeWidget(widget)
            widget.hide()
            widget.deleteLater()
        if self._selected == key:
            self._selected = None

    def remove(self, path_str: str) -> None:
        if path_str not in self._rows:
            return
        was_selected = self._selected == path_str
        self._drop(path_str)
        self._empty.setVisible(not self._folders)
        if was_selected:
            self.selection_changed.emit(False)
        self.changed.emit()

    def remove_selected(self) -> None:
        if self._selected:
            self.remove(self._selected)

    def clear(self) -> None:
        if not self._rows:
            return
        for key in list(self._rows):
            self._drop(key)
        self._empty.setVisible(True)
        self.selection_changed.emit(False)
        self.changed.emit()

    def set_selected_prefix(self, prefix: str) -> None:
        folder = self._folders.get(self._selected or "")
        if folder is None or not self._with_prefix:
            return
        folder.prefix = prefix
        self._rows[self._selected][0].update_prefix(prefix)

    def _toggle_selection(self, path_str: str) -> None:
        previous = self._selected
        if previous and previous in self._rows:
            self._rows[previous][0].set_selected(False)
        self._selected = None if previous == path_str else path_str
        if self._selected:
            self._rows[self._selected][0].set_selected(True)
        self.selection_changed.emit(self._selected is not None)
