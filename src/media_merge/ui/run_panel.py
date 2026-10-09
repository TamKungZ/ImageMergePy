"""Right-hand panel: Start / Cancel, progress, statistics and the log."""
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget

from .theme import C_DANGER, C_SUCCESS, C_SURFACE, C_TEXT, C_WARNING
from .widgets import START_BTN_STYLE, StatCard, _h_sep, _section_label, make_button

_PROGRESS_STYLE = (
    "QProgressBar { background:#e4e4e4; border:none; border-radius:3px; }"
    "QProgressBar::chunk { background:#111111; border-radius:3px; }"
)


class RunPanelMixin:
    def _build_run_panel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("rightPanel")
        panel.setMinimumWidth(330)
        panel.setMaximumWidth(410)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # start / cancel / progress
        top = QWidget()
        top.setStyleSheet(f"background:{C_SURFACE};")
        top_lay = QVBoxLayout(top)
        top_lay.setContentsMargins(18, 18, 18, 18)
        top_lay.setSpacing(7)

        self.run_title_label = QLabel()
        self.run_title_label.setObjectName("runTitle")
        top_lay.addWidget(self.run_title_label)
        self.run_summary_label = QLabel()
        self.run_summary_label.setObjectName("runSummary")
        self.run_summary_label.setWordWrap(True)
        top_lay.addWidget(self.run_summary_label)
        top_lay.addSpacing(6)

        self.start_btn = make_button("startBtn", self.start_process, style=START_BTN_STYLE)
        top_lay.addWidget(self.start_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(_PROGRESS_STYLE)
        self.progress_bar.setVisible(False)
        top_lay.addWidget(self.progress_bar)

        self.cancel_btn = make_button("ghostBtn", self.cancel_process)
        self.cancel_btn.setVisible(False)
        top_lay.addWidget(self.cancel_btn)
        lay.addWidget(top)
        lay.addWidget(_h_sep())

        # statistics
        stats = QWidget()
        stats.setStyleSheet(f"background:{C_SURFACE};")
        stats_lay = QVBoxLayout(stats)
        stats_lay.setContentsMargins(16, 16, 16, 16)
        stats_lay.setSpacing(8)
        self.stat_added = StatCard(self.t("stat_added"), C_SUCCESS)
        self.stat_skipped = StatCard(self.t("stat_skipped"), C_WARNING)
        self.stat_total = StatCard(self.t("stat_total_out"), C_TEXT)
        self.stat_failed = StatCard(self.t("stat_failed"), C_DANGER)
        for left, right in ((self.stat_added, self.stat_skipped), (self.stat_total, self.stat_failed)):
            row = QHBoxLayout()
            row.setSpacing(8)
            row.addWidget(left)
            row.addWidget(right)
            stats_lay.addLayout(row)
        lay.addWidget(stats)
        lay.addWidget(_h_sep())

        # log
        log_header = QWidget()
        log_header.setStyleSheet(f"background:{C_SURFACE};")
        log_header_lay = QHBoxLayout(log_header)
        log_header_lay.setContentsMargins(16, 10, 10, 6)
        self.log_section_label = _section_label("")
        log_header_lay.addWidget(self.log_section_label)
        log_header_lay.addStretch()
        self._clear_log_btn = QPushButton()
        self._clear_log_btn.setObjectName("tinyBtn")
        self._clear_log_btn.setCursor(self.start_btn.cursor())
        self._clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        log_header_lay.addWidget(self._clear_log_btn)
        lay.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        lay.addWidget(self.log_text, 1)
        return panel
