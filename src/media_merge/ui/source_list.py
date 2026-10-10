from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

from ..models import SourceFolder
from .theme import C_ACCENT, C_ACCENT_SOFT, C_TEXT3
from .widgets import ElidedLabel, repolish, styled

_PREFIX_WIDTH = 108


class SourceRow(QWidget):
    clicked = Signal(str)
    activated = Signal(str)  # double click
    remove_requested = Signal(str)

    def __init__(self, path: str, prefix: str, with_prefix: bool, parent=None):
        super().__init__(parent)
        styled(self, "sourceRow")
        self.path_str = path
        self.setFixedHeight(44)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 8, 0)
        lay.setSpacing(10)

        self.path_lbl = ElidedLabel(path)
        self.path_lbl.setObjectName("rowPath")
        lay.addWidget(self.path_lbl, 1)

        self.prefix_lbl: QLabel | None = None
        if with_prefix:
            self.prefix_lbl = QLabel()
            self.prefix_lbl.setFixedWidth(_PREFIX_WIDTH)
            self.prefix_lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(self.prefix_lbl)
            self.update_prefix(prefix)

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("rowRemoveBtn")
        remove_btn.setFixedSize(26, 26)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(lambda _checked=False: self.remove_requested.emit(self.path_str))
        lay.addWidget(remove_btn)

    def update_prefix(self, prefix: str) -> None:
        if self.prefix_lbl is None:
            return
        self.prefix_lbl.setText(prefix if prefix else "—")
        self.prefix_lbl.setToolTip(prefix)
        if prefix:
            self.prefix_lbl.setStyleSheet(
                f"font-size:12px; font-weight:700; color:{C_ACCENT}; background:{C_ACCENT_SOFT};"
                " border-radius:10px; padding:2px 8px;"
            )
        else:
            self.prefix_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3}; padding:2px 8px;")

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        repolish(self)

    def mousePressEvent(self, _event):
        self.clicked.emit(self.path_str)

    def mouseDoubleClickEvent(self, _event):
        self.activated.emit(self.path_str)


class SourceListPanel(QFrame):
    """Folder list with an optional prefix column, single selection, an empty state and
    drag-and-drop of folders from the file manager."""

    changed = Signal()                # entries were added / removed
    selection_changed = Signal(bool)  # True when a row is selected
    activated = Signal(str)           # row double-clicked
    paths_dropped = Signal(list)      # list[Path] of folders dropped onto the list

    def __init__(self, with_prefix: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("listBox")
        self.setAcceptDrops(True)
        self._with_prefix = with_prefix
        self._folders: dict[str, SourceFolder] = {}
        self._rows: dict[str, SourceRow] = {}
        self._selected: str | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        header = styled(QWidget(), "listHeader")
        header.setFixedHeight(32)
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(14, 0, 8, 0)
        header_lay.setSpacing(10)
        self.folder_header = QLabel()
        self.folder_header.setObjectName("listHeaderText")
        header_lay.addWidget(self.folder_header, 1)
        self.prefix_header: QLabel | None = None
        if with_prefix:
            self.prefix_header = QLabel()
            self.prefix_header.setObjectName("listHeaderText")
            self.prefix_header.setFixedWidth(_PREFIX_WIDTH)
            self.prefix_header.setAlignment(Qt.AlignCenter)
            header_lay.addWidget(self.prefix_header)
        header_lay.addSpacing(26)
        root.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(150)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        self._rows_layout = QVBoxLayout()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        body_lay.addLayout(self._rows_layout)

        self._empty = QLabel()
        self._empty.setObjectName("listEmpty")
        self._empty.setAlignment(Qt.AlignCenter)
        self._empty.setWordWrap(True)
        body_lay.addWidget(self._empty, 1)
        body_lay.addStretch(0)

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

        row = SourceRow(key, prefix, self._with_prefix)
        row.clicked.connect(self._select)
        row.activated.connect(self.activated)
        row.remove_requested.connect(self.remove)
        self._rows_layout.addWidget(row)
        self._rows[key] = row

        self._empty.setVisible(False)
        self._select(key)
        self.changed.emit()
        return True

    def _drop(self, key: str) -> None:
        self._folders.pop(key, None)
        row = self._rows.pop(key, None)
        if row is not None:
            self._rows_layout.removeWidget(row)
            row.hide()
            row.deleteLater()
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
        self._rows[self._selected].update_prefix(prefix)

    def _select(self, path_str: str) -> None:
        if path_str == self._selected or path_str not in self._rows:
            return
        if self._selected and self._selected in self._rows:
            self._rows[self._selected].set_selected(False)
        self._selected = path_str
        self._rows[path_str].set_selected(True)
        self.selection_changed.emit(True)

    # ---- drag and drop -------------------------------------------------
    @staticmethod
    def _dropped_dirs(mime) -> list[Path]:
        if not mime.hasUrls():
            return []
        paths = [Path(url.toLocalFile()) for url in mime.urls() if url.isLocalFile()]
        return [p for p in paths if p.is_dir()]

    def _set_drag_over(self, active: bool) -> None:
        self.setProperty("dragOver", active)
        repolish(self)

    def dragEnterEvent(self, event):
        if self._dropped_dirs(event.mimeData()):
            event.acceptProposedAction()
            self._set_drag_over(True)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self._set_drag_over(False)
        event.accept()

    def dropEvent(self, event):
        self._set_drag_over(False)
        dirs = self._dropped_dirs(event.mimeData())
        if dirs:
            event.acceptProposedAction()
            self.paths_dropped.emit(dirs)
        else:
            event.ignore()
