"""Application font selection (needs Qt, so it lives in the UI package)."""
import base64
import os
import sys

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFontDatabase

from ..constants import DEFAULT_LANG

try:
    from .._embedded_fonts import EMBEDDED_FONTS
except ModuleNotFoundError as exc:
    if not (exc.name or "").endswith("_embedded_fonts"):
        raise
    EMBEDDED_FONTS: dict[str, str] = {}

_SCRIPT_FONT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "th": ("Leelawadee UI", "Tahoma", "Noto Sans Thai", "Noto Sans"),
    "ja": ("Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "MS UI Gothic", "Noto Sans"),
    "ko": ("Malgun Gothic", "Noto Sans CJK KR", "Apple SD Gothic Neo", "Noto Sans"),
    "zh": ("Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "SimHei", "Noto Sans"),
    "ar": ("Segoe UI", "Tahoma", "Noto Naskh Arabic", "Noto Sans Arabic", "Noto Sans", "Arial"),
    "ru": ("Segoe UI", "Arial", "Noto Sans", "DejaVu Sans"),
    "vi": ("Segoe UI", "Arial", "Noto Sans", "DejaVu Sans"),
}

_embedded_family: str | None = None
_embedded_loaded = False


def _load_embedded_fonts() -> str | None:
    """Register the embedded fonts once (language switches used to re-decode them every time)."""
    global _embedded_family, _embedded_loaded
    if _embedded_loaded:
        return _embedded_family
    _embedded_loaded = True
    for encoded in EMBEDDED_FONTS.values():
        font_id = QFontDatabase.addApplicationFontFromData(QByteArray(base64.b64decode(encoded)))
        if font_id == -1:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and _embedded_family is None:
            _embedded_family = families[0]
    return _embedded_family


def _first_available(candidates, available) -> str | None:
    return next((font for font in candidates if font in available), None)


def setup_app_fonts(lang: str = DEFAULT_LANG) -> str:
    lang = (lang or DEFAULT_LANG).lower()
    available = set(QFontDatabase.families())
    embedded = _load_embedded_fonts()

    if embedded and lang == "th":
        return embedded

    font = _first_available(_SCRIPT_FONT_CANDIDATES.get(lang, ()), available)
    if font:
        return font
    if embedded:
        return embedded

    if os.name == "nt":
        platform_fonts = ("Segoe UI", "Arial")
    elif sys.platform == "darwin":
        platform_fonts = ("SF Pro Text", "Helvetica Neue", "Helvetica", "Arial")
    else:
        platform_fonts = ("Noto Sans", "DejaVu Sans", "Liberation Sans", "FreeSans")
    return _first_available(platform_fonts, available) or "Sans Serif"
