"""Application font selection (needs Qt, so it lives in the UI package)."""
import os
import sys

from PySide6.QtGui import QFontDatabase

from ..constants import DEFAULT_LANG
from ..metadata import APP_DIR

_SCRIPT_FONT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "th": ("Noto Sans Thai", "Noto Sans"),
    "ja": ("Noto Sans JP", "Noto Sans CJK JP", "Noto Sans"),
    "ko": ("Noto Sans KR", "Noto Sans CJK KR", "Noto Sans"),
    "zh": ("Noto Sans SC", "Noto Sans CJK SC", "Noto Sans"),
    "ar": ("Noto Sans Arabic", "Noto Sans"),
}

_LANGUAGE_FONT_FAMILY = {
    "th": "Noto Sans Thai",
    "ja": "Noto Sans JP",
    "ko": "Noto Sans KR",
    "zh": "Noto Sans SC",
    "ar": "Noto Sans Arabic",
}
_FONT_FILE_NAMES = {
    "Noto Sans": "NotoSans[wdth,wght].ttf",
    "Noto Sans Thai": "NotoSansThai[wdth,wght].ttf",
    "Noto Sans JP": "NotoSansJP[wght].ttf",
    "Noto Sans KR": "NotoSansKR[wght].ttf",
    "Noto Sans SC": "NotoSansSC[wght].ttf",
    "Noto Sans Arabic": "NotoSansArabic[wdth,wght].ttf",
}
_registered_families: dict[str, str] = {}


def _load_bundled_font(family: str) -> str | None:
    """Register only the selected bundled locale font, once."""
    if family in _registered_families:
        return _registered_families[family]
    file_name = _FONT_FILE_NAMES.get(family)
    if file_name is None:
        return None
    font_path = APP_DIR / "fonts" / file_name
    if not font_path.is_file():
        return None
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id == -1:
        return None
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        return None
    _registered_families[family] = families[0]
    return families[0]


def _first_available(candidates, available) -> str | None:
    return next((font for font in candidates if font in available), None)


def setup_app_fonts(lang: str = DEFAULT_LANG) -> str:
    lang = (lang or DEFAULT_LANG).lower()
    available = set(QFontDatabase.families())
    preferred_family = _LANGUAGE_FONT_FAMILY.get(lang, "Noto Sans")
    bundled = _load_bundled_font(preferred_family)
    if bundled:
        return bundled

    candidates = _SCRIPT_FONT_CANDIDATES.get(lang, ("Noto Sans",))
    font = _first_available(candidates, available)
    if font:
        return font

    if os.name == "nt":
        platform_fonts = ("Noto Sans", "Segoe UI", "Arial")
    elif sys.platform == "darwin":
        platform_fonts = ("Noto Sans", "SF Pro Text", "Helvetica Neue", "Helvetica", "Arial")
    else:
        platform_fonts = ("Noto Sans", "DejaVu Sans", "Liberation Sans", "FreeSans")
    return _first_available(platform_fonts, available) or "Sans Serif"