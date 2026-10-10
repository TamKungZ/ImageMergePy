"""Bottom action bar: status, results, Start / Cancel, and a collapsible log."""
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .theme import C_DANGER, C_SUCCESS, C_TEXT, C_WARNING
from .widgets import StatChip, make_button, styled

_LOG_HEIGHT = 190


class RunPanelMixin:
    def _build_action_bar(self) -> QWidget:
        bar = styled(QWidget(), "actionBar")
        root = QVBoxLayout(bar)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # thin progress line on the top edge (busy animation until the first tick)
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        root.addWidget(self.progress_bar)

        root.addWidget(self._build_log_panel())

        row = QHBoxLayout()
        row.setContentsMargins(32, 14, 32, 14)
        row.setSpacing(10)

        info = QVBoxLayout()
        info.setSpacing(8)
        self.status_label = QLabel()
        self.status_label.setObjectName("statusText")
        self.status_label.setWordWrap(True)
        info.addWidget(self.status_label)

        self.stat_added = StatChip(C_SUCCESS)
        self.stat_skipped = StatChip(C_WARNING)
        self.stat_total = StatChip(C_TEXT)
        self.stat_failed = StatChip(C_DANGER)
        self.stats_row = QWidget()
        stats_lay = QHBoxLayout(self.stats_row)
        stats_lay.setContentsMargins(0, 0, 0, 0)
        stats_lay.setSpacing(6)
        for chip in (self.stat_added, self.stat_skipped, self.stat_total, self.stat_failed):
            stats_lay.addWidget(chip)
        stats_lay.addStretch(1)
        self.stats_row.setVisible(False)
        info.addWidget(self.stats_row)
        row.addLayout(info, 1)

        self.log_toggle_btn = make_button("quietBtn", self._toggle_log)
        self.open_btn = make_button("secondaryBtn", self.open_output_folder)
        self.open_btn.setVisible(False)
        self.cancel_btn = make_button("secondaryBtn", self.cancel_process)
        self.cancel_btn.setVisible(False)
        self.start_btn = make_button("startBtn", self.start_process)
        for widget in (self.log_toggle_btn, self.open_btn, self.cancel_btn, self.start_btn):
            row.addWidget(widget)

        row_host = QWidget()
        row_host.setLayout(row)
        root.addWidget(row_host)
        return bar

    def _build_log_panel(self) -> QWidget:
        panel = styled(QWidget(), "logPanel")
        panel.setFixedHeight(_LOG_HEIGHT)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 8, 8, 0)
        lay.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(18, 0, 0, 0)
        self.log_title_label = QLabel()
        self.log_title_label.setObjectName("logTitle")
        header.addWidget(self.log_title_label)
        header.addStretch(1)
        self.clear_log_btn = QPushButton()
        self.clear_log_btn.setObjectName("logClearBtn")
        self.clear_log_btn.clicked.connect(lambda _checked=False: self.log_text.clear())
        header.addWidget(self.clear_log_btn)
        lay.addLayout(header)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        lay.addWidget(self.log_text, 1)

        panel.setVisible(False)
        self.log_panel = panel
        return panel

    def _toggle_log(self):
        self._set_log_visible(not self.log_panel.isVisible())

    def _set_log_visible(self, visible: bool):
        self.log_panel.setVisible(visible)
        self.log_toggle_btn.setText(self.t("btn_hide_log") if visible else self.t("btn_show_log"))
