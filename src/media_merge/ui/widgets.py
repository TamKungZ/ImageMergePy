"""Small reusable widgets. Colours and fonts come from styles.py via object names."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import C_ACCENT, C_DANGER, C_DISABLED, C_SIDEBAR_MUTED, C_TEXT, C_TEXT3


def styled(widget: QWidget, object_name: str) -> QWidget:
    """Give a plain QWidget an object name that the stylesheet can paint (background/border)."""
    widget.setObjectName(object_name)
    widget.setAttribute(Qt.WA_StyledBackground, True)
    return widget


def repolish(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def make_button(object_name: str, handler=None, enabled: bool = True) -> QPushButton:
    btn = QPushButton()
    btn.setObjectName(object_name)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setEnabled(enabled)
    if handler is not None:
        btn.clicked.connect(lambda _checked=False: handler())
    return btn


def make_hint() -> QLabel:
    label = QLabel()
    label.setObjectName("hint")
    label.setWordWrap(True)
    return label


def make_path_row(on_browse) -> tuple[QHBoxLayout, QLineEdit, QPushButton]:
    row = QHBoxLayout()
    row.setSpacing(8)
    edit = QLineEdit()
    edit.setObjectName("pathInput")
    edit.setReadOnly(True)
    row.addWidget(edit, 1)
    button = make_button("secondaryBtn", on_browse)
    row.addWidget(button)
    return row, edit, button


class ElidedLabel(QLabel):
    """Single-line label that shortens long text (e.g. paths) instead of widening the layout."""

    def __init__(self, text: str = "", mode=Qt.ElideMiddle, parent=None):
        super().__init__(parent)
        self._full = text
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)
        self.set_full_text(text)

    def set_full_text(self, text: str) -> None:
        self._full = text
        self.setToolTip(text)
        self._apply()

    def _apply(self) -> None:
        fm = QFontMetrics(self.font())
        self.setText(fm.elidedText(self._full, self._mode, max(20, self.width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply()


class StepCard(QFrame):
    """White card with a numbered title and optional action buttons on the right."""

    def __init__(self, number: int, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(10)
        self.badge = QLabel(str(number))
        self.badge.setObjectName("stepBadge")
        self.badge.setFixedSize(24, 24)
        self.badge.setAlignment(Qt.AlignCenter)
        header.addWidget(self.badge)
        self.title_lbl = QLabel()
        self.title_lbl.setObjectName("stepTitle")
        header.addWidget(self.title_lbl)
        header.addStretch(1)
        self._actions = QHBoxLayout()
        self._actions.setSpacing(6)
        header.addLayout(self._actions)
        root.addLayout(header)

        self.body = QVBoxLayout()
        self.body.setSpacing(10)
        root.addLayout(self.body)

    def set_title(self, text: str) -> None:
        self.title_lbl.setText(text)

    def set_number(self, number: int) -> None:
        self.badge.setText(str(number))

    def add_action(self, widget: QWidget) -> None:
        self._actions.addWidget(widget)


class Switch(QAbstractButton):
    """Painted on/off switch (no dependency on the platform style)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFixedSize(40, 22)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track = QColor(C_ACCENT if self.isChecked() else "#c3cad8")
        if not self.isEnabled():
            track = QColor(C_DISABLED)
            track.setAlpha(120)
        painter.setPen(Qt.NoPen)
        painter.setBrush(track)
        painter.drawRoundedRect(self.rect(), 11, 11)
        knob = 16
        x = self.width() - knob - 3 if self.isChecked() else 3
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(x, 3, knob, knob)


class OptionRow(QWidget):
    """Switch + short title + optional one-line hint. Click anywhere on the row to toggle."""

    toggled = Signal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(12)

        self.switch = Switch()
        self.switch.setChecked(checked)
        self.switch.toggled.connect(self.toggled)
        lay.addWidget(self.switch, 0, Qt.AlignTop)

        text = QVBoxLayout()
        text.setSpacing(1)
        self.title_lbl = QLabel()
        self.title_lbl.setObjectName("optionTitle")
        self.title_lbl.setWordWrap(True)
        text.addWidget(self.title_lbl)
        self.hint_lbl = make_hint()
        text.addWidget(self.hint_lbl)
        lay.addLayout(text, 1)
        self.setCursor(Qt.PointingHandCursor)

    def set_texts(self, title: str, hint: str = "") -> None:
        self.title_lbl.setText(title)
        self.hint_lbl.setText(hint)
        self.hint_lbl.setVisible(bool(hint))

    def isChecked(self) -> bool:
        return self.switch.isChecked()

    def setChecked(self, checked: bool) -> None:
        self.switch.setChecked(checked)

    def mousePressEvent(self, event):
        if self.isEnabled() and event.button() == Qt.LeftButton:
            self.switch.toggle()


class ChoiceCard(QWidget):
    """Radio-style card used for the 'what happens to the originals' choice."""

    clicked = Signal(str)

    def __init__(self, key: str, danger: bool = False, parent=None):
        super().__init__(parent)
        styled(self, "choiceCard")
        self.key = key
        self._danger = danger
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(92)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(5)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.title_lbl = QLabel()
        self.title_lbl.setWordWrap(True)
        row.addWidget(self.title_lbl, 1)
        self.radio = QLabel()
        self.radio.setFixedSize(18, 18)
        row.addWidget(self.radio, 0, Qt.AlignTop)
        lay.addLayout(row)

        self.desc_lbl = QLabel()
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3};")
        lay.addWidget(self.desc_lbl)
        lay.addStretch(1)
        self.set_selected(False)

    def set_texts(self, title: str, desc: str) -> None:
        self.title_lbl.setText(title)
        self.desc_lbl.setText(desc)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        tone = C_DANGER if self._danger else C_ACCENT
        soft = "#fdf3f3" if self._danger else "#eef2ff"
        if selected:
            self.setStyleSheet(
                f"QWidget#choiceCard {{ background:{soft}; border:2px solid {tone}; border-radius:12px; }}"
            )
            self.radio.setStyleSheet(f"background:#ffffff; border:5px solid {tone}; border-radius:9px;")
            self.title_lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{tone};")
        else:
            self.setStyleSheet(
                "QWidget#choiceCard { background:#ffffff; border:1px solid #cdd3de; border-radius:12px; }"
                "QWidget#choiceCard:hover { border-color:#8e98af; }"
            )
            self.radio.setStyleSheet("background:#ffffff; border:2px solid #cdd3de; border-radius:9px;")
            self.title_lbl.setStyleSheet(f"font-size:15px; font-weight:700; color:{C_TEXT};")

    def mousePressEvent(self, _event):
        self.clicked.emit(self.key)


class NavItem(QWidget):
    """Sidebar entry: action name + one-line description."""

    clicked = Signal(str)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        styled(self, "navItem")
        self.key = key
        self.setCursor(Qt.PointingHandCursor)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 11)
        lay.setSpacing(2)
        self.title_lbl = QLabel()
        lay.addWidget(self.title_lbl)
        self.sub_lbl = QLabel()
        self.sub_lbl.setWordWrap(True)
        lay.addWidget(self.sub_lbl)
        self.set_active(False)

    def set_texts(self, title: str, sub: str) -> None:
        self.title_lbl.setText(title)
        self.sub_lbl.setText(sub)

    def set_active(self, active: bool) -> None:
        self.setProperty("active", active)
        repolish(self)
        title_color = "#ffffff" if active else "#e8ecf5"
        sub_color = "#b6c0d9" if active else C_SIDEBAR_MUTED
        self.title_lbl.setStyleSheet(f"font-size:14px; font-weight:700; color:{title_color};")
        self.sub_lbl.setStyleSheet(f"font-size:12px; color:{sub_color};")

    def mousePressEvent(self, _event):
        self.clicked.emit(self.key)


class StatChip(QWidget):
    """Compact 'value label' pill shown after a run."""

    def __init__(self, color: str = C_TEXT, parent=None):
        super().__init__(parent)
        styled(self, "statChip")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(11, 4, 11, 4)
        lay.setSpacing(6)
        self.value_lbl = QLabel("—")
        self.value_lbl.setStyleSheet(f"font-size:13px; font-weight:700; color:{color};")
        lay.addWidget(self.value_lbl)
        self.label_lbl = QLabel()
        self.label_lbl.setObjectName("chipLabel")
        lay.addWidget(self.label_lbl)

    def set_value(self, value) -> None:
        self.value_lbl.setText(str(value))

    def set_label(self, text: str) -> None:
        self.label_lbl.setText(text)
