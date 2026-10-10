"""Application metadata (app_metadata.json) and project paths."""
import json
import sys
from pathlib import Path

from .constants import APP_FALLBACK_TITLE



def _resolve_app_dir() -> Path:
    here = Path(__file__).resolve()
    if "__compiled__" in globals() or getattr(sys, "frozen", False):
        return here.parents[__name__.count(".")]
    return here.parents[2]


APP_DIR = _resolve_app_dir()
APP_METADATA_PATH = APP_DIR / "app_metadata.json"


def load_app_metadata() -> dict[str, str]:
    metadata = {
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
                metadata.update({str(key): str(value) for key, value in parsed.items()})
        except (OSError, ValueError):
            pass
    return metadata


APP_METADATA = load_app_metadata()