"""Application metadata (app_metadata.json) and project paths."""
import json
from pathlib import Path

from .constants import APP_FALLBACK_TITLE

APP_DIR = Path(__file__).resolve().parents[2]
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
