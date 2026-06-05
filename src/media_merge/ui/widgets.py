from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from ..config import (
    C_ACCENT,
    C_ACCENT_DIM,
    C_BORDER,
    C_BORDER2,
    C_DANGER,
    C_SURFACE,
    C_SURFACE2,
    C_TEXT,
    C_TEXT2,
    C_TEXT3,
)

def _h_sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{C_BORDER2}; border:none;")
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color:{C_TEXT3}; font-size:11px; font-weight:700; letter-spacing:1.1px;"
    )
    return lbl


class ModeCard(QWidget):
    clicked = Signal(str)

    def __init__(self, mode_key: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.mode_key = mode_key
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(120)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_TEXT};")
        lay.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet(f"font-size:13px; color:{C_TEXT2};")
        lay.addWidget(self.desc_lbl)
        lay.addStretch()

        self._refresh_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()
        if selected:
            self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_ACCENT};")
        else:
            self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_TEXT};")

    def _refresh_style(self):
        if self._selected:
            self.setStyleSheet(
                f"background:{C_ACCENT_DIM}; border:2px solid {C_ACCENT}; border-radius:10px;"
            )
        else:
            self.setStyleSheet(f"background:{C_SURFACE}; border:1px solid {C_BORDER2}; border-radius:10px;")

    def mousePressEvent(self, _event):
        self.clicked.emit(self.mode_key)


class SourceRow(QWidget):
    remove_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, path: str, prefix: str, parent=None):
        super().__init__(parent)
        self.path_str = path
        self._selected = False
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(10)

        self.path_lbl = QLabel(path)
        self.path_lbl.setStyleSheet(f"font-size:14px; color:{C_TEXT};")
        self.path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(self.path_lbl)

        self.prefix_lbl = QLabel(prefix if prefix else "—")
        if prefix:
            self.prefix_lbl.setStyleSheet(
                f"font-size:12px; font-weight:700; color:{C_ACCENT};"
                f" background:{C_ACCENT_DIM}; border:1px solid rgba(17,17,17,0.35);"
                f" border-radius:10px; padding:1px 8px;"
            )
        else:
            self.prefix_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3}; padding:1px 8px;")
        self.prefix_lbl.setFixedWidth(110)
        self.prefix_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.prefix_lbl)

        rm_btn = QPushButton("✕")
        rm_btn.setFixedSize(24, 24)
        rm_btn.setCursor(Qt.PointingHandCursor)
        rm_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{C_TEXT3};"
            f" border-radius:5px; font-size:12px; }}"
            f"QPushButton:hover {{ background:rgba(30,30,30,0.12); color:{C_DANGER}; }}"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self.path_str))
        lay.addWidget(rm_btn)

        self._refresh_style()

    def update_prefix(self, prefix: str):
        self.prefix_lbl.setText(prefix if prefix else "—")
        if prefix:
            self.prefix_lbl.setStyleSheet(
                f"font-size:12px; font-weight:700; color:{C_ACCENT};"
                f" background:{C_ACCENT_DIM}; border:1px solid rgba(17,17,17,0.35);"
                f" border-radius:10px; padding:1px 8px;"
            )
        else:
            self.prefix_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3}; padding:1px 8px;")

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self):
        if self._selected:
            self.setStyleSheet(f"background:{C_ACCENT_DIM};")
        else:
            self.setStyleSheet("background:transparent;")

    def mouseDoubleClickEvent(self, _event):
        self.edit_requested.emit(self.path_str)

    def mousePressEvent(self, _event):
        self.edit_requested.emit(self.path_str)


class FolderOnlyRow(QWidget):
    remove_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path_str = path
        self._selected = False
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(10)

        self.path_lbl = QLabel(path)
        self.path_lbl.setStyleSheet(f"font-size:14px; color:{C_TEXT};")
        self.path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(self.path_lbl)

        rm_btn = QPushButton("✕")
        rm_btn.setFixedSize(24, 24)
        rm_btn.setCursor(Qt.PointingHandCursor)
        rm_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{C_TEXT3};"
            f" border-radius:5px; font-size:12px; }}"
            f"QPushButton:hover {{ background:rgba(30,30,30,0.12); color:{C_DANGER}; }}"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self.path_str))
        lay.addWidget(rm_btn)

        self._refresh_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self):
        if self._selected:
            self.setStyleSheet(f"background:{C_ACCENT_DIM};")
        else:
            self.setStyleSheet("background:transparent;")

    def mouseDoubleClickEvent(self, _event):
        self.edit_requested.emit(self.path_str)

    def mousePressEvent(self, _event):
        self.edit_requested.emit(self.path_str)


class StatCard(QWidget):
    def __init__(self, label: str, color: str = C_TEXT, parent=None):
        super().__init__(parent)
        self._color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self.value_lbl = QLabel("—")
        self.value_lbl.setStyleSheet(f"font-size:26px; font-weight:700; color:{color};")
        lay.addWidget(self.value_lbl)

        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setStyleSheet(
            f"font-size:11px; font-weight:700; letter-spacing:0.6px; color:{C_TEXT3};"
        )
        lay.addWidget(self.label_lbl)
        self.setStyleSheet(f"background:{C_SURFACE2}; border-radius:8px;")

    def set_value(self, val):
        self.value_lbl.setText(str(val))

    def set_label(self, text: str):
        self.label_lbl.setText(text.upper())


