from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QPushButton, QTextEdit, QVBoxLayout

from ..constants import APP_FALLBACK_TITLE, IMAGE_EXTS, LANGUAGE_NATIVE_NAMES, VIDEO_EXTS
from ..metadata import APP_METADATA

_ABOUT_TEMPLATE = """\
<div style="line-height:1.45;">
  <h2 style="margin:0 0 6px 0;">{app_name}</h2>
  <p style="margin:0 0 12px 0; color:#4a5a76;">{app_desc}</p>

  <table style="margin:0 0 12px 0;" cellpadding="2" cellspacing="0">
    <tr><td><b>Version:</b></td><td>{version}</td></tr>
    <tr><td><b>Developer:</b></td><td>{company}</td></tr>
    <tr><td><b>License:</b></td><td>{license_note}</td></tr>
  </table>

  <b>Main features</b>
  <ul style="margin:6px 0 12px 18px; padding:0;">
    <li>Merge media from multiple folders</li>
    <li>De-duplicate by SHA-256 hash + extension</li>
    <li>Keep images first and videos last</li>
    <li>Rename output files as sequence numbers with optional per-folder prefix</li>
  </ul>

  <p style="margin:0 0 6px 0;"><b>Operation modes:</b> {modes}</p>
  <p style="margin:0 0 6px 0;"><b>Supported image formats:</b> {images}</p>
  <p style="margin:0 0 6px 0;"><b>Supported video formats:</b> {videos}</p>
  <p style="margin:0;"><b>UI languages:</b> {langs}</p>
</div>
"""


def build_about_html(t, lang_codes) -> str:
    modes = " | ".join(
        t(key)
        for key in ("mode_copy_keep", "mode_copy_delete", "mode_move", "mode_main_folder", "mode_inside_folder")
    )
    return _ABOUT_TEMPLATE.format(
        app_name=APP_METADATA.get("app_name") or APP_FALLBACK_TITLE,
        app_desc=t("app_desc"),
        version=APP_METADATA.get("product_version") or APP_METADATA.get("file_version") or "-",
        company=APP_METADATA.get("company_name") or "-",
        license_note=APP_METADATA.get("copyright") or "MIT License",
        modes=modes,
        images=", ".join(sorted(IMAGE_EXTS)),
        videos=", ".join(sorted(VIDEO_EXTS)),
        langs=", ".join(LANGUAGE_NATIVE_NAMES.get(code, code.upper()) for code in lang_codes),
    )


def show_about_dialog(parent, t, lang_codes) -> None:
    dialog = QDialog(parent)
    dialog.setModal(True)
    dialog.setWindowTitle(t("app_title") or APP_FALLBACK_TITLE)
    dialog.resize(700, 520)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)

    about_text = QTextEdit(dialog)
    about_text.setReadOnly(True)
    about_text.setFrameShape(QFrame.NoFrame)
    about_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    about_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    about_text.setHtml(build_about_html(t, lang_codes))
    layout.addWidget(about_text, 1)

    buttons = QHBoxLayout()
    buttons.addStretch(1)
    ok_button = QPushButton("OK", dialog)
    ok_button.setFixedWidth(104)
    ok_button.clicked.connect(dialog.accept)
    buttons.addWidget(ok_button)
    layout.addLayout(buttons)

    dialog.exec()
