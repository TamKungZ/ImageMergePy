from .theme import (
    C_ACCENT,
    C_ACCENT_HOVER,
    C_ACCENT_PRESSED,
    C_ACCENT_SOFT,
    C_BG,
    C_BORDER,
    C_BORDER2,
    C_DANGER,
    C_DANGER_SOFT,
    C_DISABLED,
    C_LOG_BG,
    C_LOG_TEXT,
    C_SIDEBAR,
    C_SIDEBAR,
    C_SIDEBAR_ACTIVE,
    C_SIDEBAR_HOVER,
    C_SIDEBAR_MUTED,
    C_SIDEBAR_TEXT,
    C_SIDEBAR_HOVER,
    C_SIDEBAR_MUTED,
    C_SIDEBAR_TEXT,
    C_SURFACE,
    C_SURFACE2,
    C_SURFACE3,
    C_TEXT,
    C_TEXT2,
    C_TEXT3,
)


def global_stylesheet(font_family: str) -> str:
    ff = font_family
    return f"""
    * {{ font-family: "{ff}"; }}
    QMainWindow, QWidget#central {{ background: {C_BG}; }}
    QToolTip {{ background: {C_TEXT}; color: #ffffff; border: none; padding: 5px 8px; }}

    /* ---------- sidebar ---------- */
    QWidget#sidebar {{ background: {C_SIDEBAR}; }}
    QLabel#brandName {{ color: {C_SIDEBAR_TEXT}; font-size: 22px; font-weight: 700; }}
    QLabel#brandTag {{ color: {C_SIDEBAR_MUTED}; font-size: 12px; }}
    QLabel#sidebarCaption {{ color: {C_SIDEBAR_MUTED}; font-size: 11px; font-weight: 700; }}
    QWidget#navItem {{ background: transparent; border-radius: 10px; }}
    QWidget#navItem:hover {{ background: {C_SIDEBAR_HOVER}; }}
    QWidget#navItem[active="true"] {{ background: {C_SIDEBAR_ACTIVE}; }}
    QComboBox#langSelector {{
        background: {C_SURFACE}; color: {C_TEXT}; border: 1px solid {C_BORDER2};
        border-radius: 8px; padding: 6px 10px; font-size: 13px;
    }}
    QComboBox#langSelector QAbstractItemView {{
        background: {C_SURFACE}; color: {C_TEXT}; border: 1px solid {C_BORDER2};
        selection-background-color: {C_ACCENT_SOFT}; selection-color: {C_TEXT};
    }}
    QPushButton#sidebarBtn {{
        background: transparent; color: {C_SIDEBAR_MUTED}; border: none; border-radius: 8px;
        padding: 8px 10px; font-size: 13px; font-weight: 600; text-align: left;
    }}
    QPushButton#sidebarBtn:hover {{ background: {C_SIDEBAR_HOVER}; color: {C_SIDEBAR_TEXT}; }}

    /* ---------- pages ---------- */
    QScrollArea#pageScroll {{ background: {C_BG}; border: none; }}
    QWidget#pageBody {{ background: {C_BG}; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {C_BORDER2}; border-radius: 4px; min-height: 28px; }}
    QScrollBar::handle:vertical:hover {{ background: {C_TEXT3}; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    QLabel#pageTitle {{ color: {C_TEXT}; font-size: 26px; font-weight: 700; }}
    QLabel#pageDesc {{ color: {C_TEXT3}; font-size: 14px; }}
    QFrame#card {{ background: {C_SURFACE}; border: 1px solid {C_BORDER}; border-radius: 12px; }}
    QLabel#stepBadge {{
        background: {C_ACCENT_SOFT}; color: {C_ACCENT}; border-radius: 12px;
        font-size: 12px; font-weight: 700;
    }}
    QLabel#stepTitle {{ color: {C_TEXT}; font-size: 15px; font-weight: 700; }}
    QLabel#hint {{ color: {C_TEXT3}; font-size: 12px; }}
    QLabel#optionTitle {{ color: {C_TEXT}; font-size: 14px; font-weight: 600; }}
    QLabel#optionTitle:disabled {{ color: {C_DISABLED}; }}
    QLabel#hint:disabled {{ color: {C_DISABLED}; }}

    QLineEdit#pathInput {{
        background: {C_SURFACE2}; border: 1px solid {C_BORDER2}; border-radius: 8px;
        color: {C_TEXT}; padding: 9px 12px; font-size: 14px;
    }}

    /* ---------- folder list ---------- */
    QFrame#listBox {{ background: {C_SURFACE}; border: 1px solid {C_BORDER2}; border-radius: 10px; }}
    QFrame#listBox[dragOver="true"] {{ background: {C_ACCENT_SOFT}; border: 1px dashed {C_ACCENT}; }}
    QWidget#listHeader {{ background: {C_SURFACE2}; border-top-left-radius: 10px; border-top-right-radius: 10px; }}
    QLabel#listHeaderText {{ color: {C_TEXT3}; font-size: 12px; font-weight: 700; }}
    QLabel#listEmpty {{ color: {C_TEXT3}; font-size: 14px; }}
    QWidget#sourceRow {{ background: transparent; border-bottom: 1px solid {C_BORDER}; }}
    QWidget#sourceRow:hover {{ background: {C_SURFACE2}; }}
    QWidget#sourceRow[selected="true"] {{ background: {C_ACCENT_SOFT}; }}
    QLabel#rowPath {{ color: {C_TEXT}; font-size: 14px; }}
    QPushButton#rowRemoveBtn {{
        background: transparent; color: {C_TEXT3}; border: none; border-radius: 6px; font-size: 12px;
    }}
    QPushButton#rowRemoveBtn:hover {{ background: {C_DANGER_SOFT}; color: {C_DANGER}; }}

    /* ---------- buttons ---------- */
    QPushButton#primaryBtn {{
        background: {C_ACCENT}; color: #ffffff; border: 1px solid {C_ACCENT}; border-radius: 8px;
        padding: 7px 14px; font-size: 13px; font-weight: 600;
    }}
    QPushButton#primaryBtn:hover {{ background: {C_ACCENT_HOVER}; border-color: {C_ACCENT_HOVER}; }}
    QPushButton#primaryBtn:pressed {{ background: {C_ACCENT_PRESSED}; border-color: {C_ACCENT_PRESSED}; }}
    QPushButton#primaryBtn:disabled {{ background: {C_SURFACE3}; border-color: {C_SURFACE3}; color: {C_DISABLED}; }}

    QPushButton#secondaryBtn {{
        background: {C_SURFACE}; color: {C_TEXT}; border: 1px solid {C_BORDER2}; border-radius: 8px;
        padding: 7px 14px; font-size: 13px; font-weight: 600;
    }}
    QPushButton#secondaryBtn:hover {{ background: {C_SURFACE2}; }}
    QPushButton#secondaryBtn:pressed {{ background: {C_SURFACE3}; }}
    QPushButton#secondaryBtn:disabled {{ color: {C_DISABLED}; border-color: {C_BORDER}; }}

    QPushButton#quietBtn, QPushButton#dangerQuietBtn {{
        background: transparent; color: {C_TEXT2}; border: none; border-radius: 8px;
        padding: 7px 10px; font-size: 13px; font-weight: 600;
    }}
    QPushButton#quietBtn:hover {{ background: {C_SURFACE2}; color: {C_TEXT}; }}
    QPushButton#dangerQuietBtn:hover {{ background: {C_DANGER_SOFT}; color: {C_DANGER}; }}
    QPushButton#quietBtn:disabled, QPushButton#dangerQuietBtn:disabled {{ color: {C_DISABLED}; }}

    QPushButton#startBtn {{
        background: {C_ACCENT}; color: #ffffff; border: 1px solid {C_ACCENT}; border-radius: 10px;
        padding: 11px 28px; font-size: 16px; font-weight: 700; min-width: 150px;
    }}
    QPushButton#startBtn:hover {{ background: {C_ACCENT_HOVER}; border-color: {C_ACCENT_HOVER}; }}
    QPushButton#startBtn:pressed {{ background: {C_ACCENT_PRESSED}; border-color: {C_ACCENT_PRESSED}; }}
    QPushButton#startBtn:disabled {{ background: {C_SURFACE3}; border-color: {C_SURFACE3}; color: {C_DISABLED}; }}

    /* ---------- action bar + log ---------- */
    QWidget#actionBar {{ background: {C_SURFACE}; border-top: 1px solid {C_BORDER}; }}
    QLabel#statusText {{ color: {C_TEXT}; font-size: 14px; font-weight: 600; }}
    QWidget#statChip {{ background: {C_SURFACE2}; border-radius: 12px; }}
    QLabel#chipLabel {{ color: {C_TEXT3}; font-size: 12px; }}
    QProgressBar {{ background: transparent; border: none; }}
    QProgressBar::chunk {{ background: {C_ACCENT}; }}
    QWidget#logPanel {{ background: {C_LOG_BG}; }}
    QLabel#logTitle {{ color: {C_LOG_TEXT}; font-size: 12px; font-weight: 700; }}
    QPushButton#logClearBtn {{
        background: transparent; color: {C_LOG_TEXT}; border: none; border-radius: 6px;
        padding: 3px 8px; font-size: 12px;
    }}
    QPushButton#logClearBtn:hover {{ background: #1f2736; }}
    QTextEdit#logText {{
        background: {C_LOG_BG}; color: {C_LOG_TEXT}; border: none; padding: 4px 18px 10px 18px; font-size: 12px;
        font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
    }}
    """
