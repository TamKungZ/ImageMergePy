"""Qt-free configuration facade.

Importing this module must stay cheap and must not import PySide6, so the CLI can
run headless. UI-only things live in ``ui/theme.py`` and ``ui/fonts.py``.
"""
import os
import re

from .constants import (  # noqa: F401  (re-exported for convenience)
    ALL_MODES,
    APP_FALLBACK_TITLE,
    DEFAULT_LANG,
    HEX_HASH_RE,
    IMAGE_EXTS,
    IMG_NUMBER_RE,
    LANGUAGE_NATIVE_NAMES,
    MEDIA_EXTS,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
    ORGANIZER_MODES,
    PREFIX_ALLOWED_RE,
    TEMP_ROOT_NAME,
    UUID_LIKE_RE,
    VIDEO_EXTS,
    WORKFLOW_INSIDE_FOLDER,
    WORKFLOW_MAIN_FOLDER,
    WORKFLOW_MERGE,
)
from .metadata import APP_DIR, APP_METADATA, APP_METADATA_PATH, load_app_metadata  # noqa: F401

LOCALES_DIR = APP_DIR / "locales"


def discover_supported_langs() -> set[str]:
    langs = {DEFAULT_LANG}
    if LOCALES_DIR.is_dir():
        langs.update(f.stem.lower() for f in LOCALES_DIR.glob("*.json") if f.stem)
    if len(langs) == 1:
        # Packaged build without loose locale files: fall back to the embedded copy.
        try:
            from ._embedded_locales import EMBEDDED_LOCALES
        except ImportError:  # neither loose nor embedded locales: English keys only
            return langs
        langs.update(EMBEDDED_LOCALES)
    return langs


SUPPORTED_LANGS = discover_supported_langs()


def detect_language() -> str:
    env_lang = os.environ.get("IMAGEMERGE_LANG", "").strip().lower()
    if env_lang in SUPPORTED_LANGS:
        return env_lang
    if "-" in env_lang or "_" in env_lang:
        base = re.split(r"[-_]", env_lang)[0]
        if base in SUPPORTED_LANGS:
            return base
    return DEFAULT_LANG
