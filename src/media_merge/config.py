import base64
import json
import os
import re
import sys
from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QFontDatabase

from embedded_fonts import EMBEDDED_FONTS
from embedded_locales import EMBEDDED_LOCALES as FILE_EMBEDDED_LOCALES

APP_FALLBACK_TITLE = "ImageMerge"
APP_DIR = Path(__file__).resolve().parents[2]
APP_METADATA_PATH = APP_DIR / "app_metadata.json"


def load_app_metadata() -> dict[str, str]:
    defaults = {
        "app_name": APP_FALLBACK_TITLE,
        "company_name": "TamKungZ_",
        "file_description": "Open-source image and video merge tool",
        "file_version": "",
        "product_version": "",
        "copyright": "",
    }
    if APP_METADATA_PATH.exists():
        try:
            parsed = json.loads(APP_METADATA_PATH.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    defaults[str(key)] = str(value)
        except Exception:
            pass
    return defaults


APP_METADATA = load_app_metadata()

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mts"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

MODE_MOVE = "move"
MODE_COPY_DELETE = "copy_delete"
MODE_COPY_KEEP = "copy_keep"
MODE_MAIN_FOLDER = "main_folder"
MODE_INSIDE_FOLDER = "inside_folder"

WORKFLOW_MERGE = "merge"
WORKFLOW_MAIN_FOLDER = "main_folder"
WORKFLOW_INSIDE_FOLDER = "inside_folder"

DEFAULT_LANG = "en"
LOCALES_DIR = APP_DIR / "locales"


def discover_supported_langs() -> set[str]:
    langs = set(FILE_EMBEDDED_LOCALES.keys())
    if LOCALES_DIR.exists():
        for locale_file in LOCALES_DIR.glob("*.json"):
            if locale_file.stem:
                langs.add(locale_file.stem.lower())
    if DEFAULT_LANG not in langs:
        langs.add(DEFAULT_LANG)
    return langs


SUPPORTED_LANGS = discover_supported_langs()

UUID_LIKE_RE = re.compile(
    r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?: \(\d+\))?$"
)
HEX_HASH_RE = re.compile(r"^[0-9a-fA-F]{24,}(?: \(\d+\))?$")
IMG_NUMBER_RE = re.compile(r"^(IMG)[ _-]?(\d+)(?:\s*\(\d+\))?$", re.IGNORECASE)
PREFIX_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9_-]+")

C_BG        = "#efefef"
C_SURFACE   = "#ffffff"
C_SURFACE2  = "#f4f4f4"
C_SURFACE3  = "#e4e4e4"
C_BORDER    = "rgba(20,20,20,0.12)"
C_BORDER2   = "rgba(20,20,20,0.22)"
C_ACCENT    = "#111111"
C_ACCENT_DIM= "rgba(17,17,17,0.12)"
C_TEXT      = "#111111"
C_TEXT2     = "#222222"
C_TEXT3     = "#444444"
C_SUCCESS   = "#1b1b1b"
C_WARNING   = "#4f4f4f"
C_DANGER    = "#2b2b2b"

LANGUAGE_NATIVE_NAMES = {
    "ar": "العربية",
    "de": "Deutsch",
    "en": "English",
    "es": "Español",
    "fr": "Français",
    "id": "Bahasa Indonesia",
    "ja": "日本語",
    "ko": "한국어",
    "ru": "Русский",
    "th": "ไทย",
    "vi": "Tiếng Việt",
    "zh": "中文",
}


def setup_app_fonts(lang: str = DEFAULT_LANG) -> str:
    lang = (lang or DEFAULT_LANG).lower()
    db = QFontDatabase()

    loaded_family = None
    for encoded_data in EMBEDDED_FONTS.values():
        try:
            font_bytes = base64.b64decode(encoded_data)
            font_id = QFontDatabase.addApplicationFontFromData(QByteArray(font_bytes))
            if font_id == -1:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families and loaded_family is None:
                loaded_family = families[0]
        except Exception:
            continue

    script_font_candidates: dict[str, tuple[str, ...]] = {
        "th": ("Leelawadee UI", "Tahoma", "Noto Sans Thai", "Noto Sans"),
        "ja": ("Yu Gothic UI", "Meiryo", "Noto Sans CJK JP", "MS UI Gothic", "Noto Sans"),
        "ko": ("Malgun Gothic", "Noto Sans CJK KR", "Apple SD Gothic Neo", "Noto Sans"),
        "zh": ("Microsoft YaHei UI", "PingFang SC", "Noto Sans CJK SC", "SimHei", "Noto Sans"),
        "ar": ("Segoe UI", "Tahoma", "Noto Naskh Arabic", "Noto Sans Arabic", "Noto Sans", "Arial"),
        "ru": ("Segoe UI", "Arial", "Noto Sans", "DejaVu Sans"),
        "vi": ("Segoe UI", "Arial", "Noto Sans", "DejaVu Sans"),
    }

    if loaded_family and lang == "th":
        return loaded_family

    for font in script_font_candidates.get(lang, ()):
        if db.hasFamily(font):
            return font

    if loaded_family:
        return loaded_family

    if os.name == "nt":
        for font in ("Segoe UI", "Arial"):
            if db.hasFamily(font):
                return font
    elif sys.platform == "darwin":
        for font in ("SF Pro Text", "Helvetica Neue", "Helvetica", "Arial"):
            if db.hasFamily(font):
                return font
    else:
        for font in ("Noto Sans", "DejaVu Sans", "Liberation Sans", "FreeSans"):
            if db.hasFamily(font):
                return font

    return "Sans Serif"


def detect_language() -> str:
    env_lang = os.environ.get("IMAGEMERGE_LANG", "").strip().lower()
    if env_lang in SUPPORTED_LANGS:
        return env_lang
    if "-" in env_lang or "_" in env_lang:
        base = re.split(r"[-_]", env_lang)[0]
        if base in SUPPORTED_LANGS:
            return base
    return DEFAULT_LANG


