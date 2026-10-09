from ..config import (
    C_ACCENT,
    C_ACCENT_DIM,
    C_BG,
    C_BORDER,
    C_BORDER2,
    C_DANGER,
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

    /* Titlebar */
    QWidget#titlebar {{ background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER2}; }}
    QWidget#workflowBar {{ background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER2}; }}
    QWidget#contentCard {{
        background: {C_SURFACE};
        border: 1px solid {C_BORDER2};
        border-radius: 12px;
    }}
    QLabel#pageTitle {{ color:{C_TEXT}; font-size:24px; font-weight:700; }}
    QLabel#pageDescription {{ color:{C_TEXT3}; font-size:13px; }}
    QLabel#runTitle {{ color:{C_TEXT}; font-size:18px; font-weight:700; }}
    QLabel#runSummary {{ color:{C_TEXT3}; font-size:13px; }}

    /* Scroll areas */
    QScrollArea {{ background: transparent; border: none; }}
    QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {C_SURFACE3}; border-radius: 4px; min-height: 28px; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

    /* Source list container */
    QWidget#sourceContainer {{ background: {C_SURFACE}; border: 1px solid {C_BORDER2}; border-radius: 10px; }}
    QWidget#sourceHeaderBar  {{ background: transparent; border-bottom: 1px solid {C_BORDER2}; }}

    /* Output path input */
    QLineEdit#outputPath {{
        background: {C_SURFACE}; border: 1px solid {C_BORDER2}; border-radius: 8px;
        color: {C_TEXT}; padding: 10px 12px; font-size: 15px;
    }}
    QLineEdit#outputPath:focus {{ border-color: {C_ACCENT}; }}

    QComboBox#langSelector {{
        background: {C_SURFACE2};
        color: {C_TEXT};
        border: 1px solid {C_BORDER2};
        border-radius: 8px;
        padding: 6px 10px;
        font-size: 13px;
        min-width: 92px;
    }}
    QComboBox#langSelector::drop-down {{ border: none; width: 22px; }}
    QComboBox#langSelector QAbstractItemView {{
        border: 1px solid {C_BORDER2};
        background: {C_SURFACE};
        color: {C_TEXT};
        selection-background-color: {C_ACCENT_DIM};
    }}

    QPushButton#infoBtn {{
        background: {C_SURFACE2};
        color: {C_TEXT2};
        border: 1px solid {C_BORDER2};
        border-radius: 14px;
        font-size: 15px;
        font-weight: 700;
        min-width: 28px;
        min-height: 28px;
        max-width: 28px;
        max-height: 28px;
    }}
    QPushButton#infoBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; border-color: {C_ACCENT}; }}
    QPushButton#infoBtn:pressed {{ background: {C_ACCENT_DIM}; }}

    /* Log area */
    QTextEdit#logText {{
        background: {C_SURFACE}; border: none; border-radius: 0;
        color: {C_TEXT2}; font-size: 13px;
        font-family: "JetBrains Mono", "Cascadia Code", "Fira Code", "Consolas", "Courier New", monospace;
    }}

    /* Right panel */
    QWidget#rightPanel {{ background: {C_SURFACE}; border-left: 1px solid {C_BORDER2}; }}

    /* Start button */
    QPushButton#startBtn {{
        background: {C_ACCENT}; color: #ffffff; border: none;
        border-radius: 10px; font-size: 20px; font-weight: 700; padding: 14px;
    }}
    QPushButton#startBtn:hover {{ background: #242424; }}
    QPushButton#startBtn:pressed {{ background: #000000; }}
    QPushButton#startBtn:disabled {{
        background: #4a4a4a; color: #f2f2f2; border: 1px solid #4a4a4a;
    }}

    /* Secondary buttons */
    QPushButton#primaryBtn {{
        background-color: #1b1b1b; color: #ffffff; border: 1px solid #1b1b1b;
        border-radius: 7px; padding: 8px 14px; font-size: 14px; font-weight: 600;
    }}
    QPushButton#primaryBtn:hover {{ background-color: #000000; border-color: #000000; }}
    QPushButton#primaryBtn:pressed {{ background-color: #343434; border-color: #343434; }}
    QPushButton#primaryBtn:disabled {{ background-color: #4a4a4a; color: #f2f2f2; border-color: #4a4a4a; }}

    QPushButton#ghostBtn {{
        background: {C_SURFACE2}; color: {C_TEXT}; border: 1px solid {C_BORDER2};
        border-radius: 7px; padding: 8px 12px; font-size: 14px;
    }}
    QPushButton#ghostBtn:hover {{ background: {C_SURFACE3}; }}
    QPushButton#ghostBtn:disabled {{ color: {C_TEXT3}; }}

    QPushButton#dangerGhostBtn {{
        background: transparent; color: {C_TEXT3}; border: 1px solid {C_BORDER};
        border-radius: 7px; padding: 8px 12px; font-size: 14px;
    }}
    QPushButton#dangerGhostBtn:hover {{ background: rgba(20,20,20,0.08); color: {C_DANGER}; border-color: {C_BORDER2}; }}
    QPushButton#dangerGhostBtn:disabled {{ color: {C_TEXT3}; }}

    QPushButton#tinyBtn {{
        background: transparent; color: {C_TEXT3}; border: none;
        border-radius: 5px; padding: 3px 8px; font-size: 12px;
    }}
    QPushButton#tinyBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; }}

    QPushButton#pageModeBtn {{
        background: transparent; color: {C_TEXT2}; border: 1px solid transparent;
        border-radius: 9px; padding: 9px 14px; font-size: 13px; font-weight: 600;
    }}
    QPushButton#pageModeBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; }}
    QPushButton#pageModeBtn[active="true"] {{
        background: {C_ACCENT}; color: #ffffff; border: 1px solid {C_ACCENT};
    }}

    /* Checkbox */
    QCheckBox {{ color: {C_TEXT2}; font-size: 14px; spacing: 8px; }}
    QCheckBox::indicator {{
        width: 18px; height: 18px; border-radius: 4px;
        border: 1.5px solid {C_BORDER2}; background: {C_SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {C_ACCENT}; border-color: {C_ACCENT};
        image: none;
    }}
    QCheckBox::indicator:hover {{ border-color: {C_ACCENT}; }}

    /* Splitter */
    QSplitter::handle {{ background: {C_BORDER2}; width: 1px; }}

    /* Note label */
    QLabel#noteLabel {{ color: {C_TEXT3}; font-size: 13px; line-height: 1.5; }}
    """
