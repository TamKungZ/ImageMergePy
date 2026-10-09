"""Pure constants shared by the core, the CLI and the UI (no Qt, no I/O)."""
import re

APP_FALLBACK_TITLE = "ImageMerge"
DEFAULT_LANG = "en"

# Hidden folder created inside the output folder for "safe mode" staging.
TEMP_ROOT_NAME = ".imagemerge_temp"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mts"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

MODE_MOVE = "move"
MODE_COPY_DELETE = "copy_delete"
MODE_COPY_KEEP = "copy_keep"
MODE_MAIN_FOLDER = "main_folder"
MODE_INSIDE_FOLDER = "inside_folder"
ALL_MODES = frozenset(
    {MODE_MOVE, MODE_COPY_DELETE, MODE_COPY_KEEP, MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER}
)
ORGANIZER_MODES = frozenset({MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER})

WORKFLOW_MERGE = "merge"
WORKFLOW_MAIN_FOLDER = "main_folder"
WORKFLOW_INSIDE_FOLDER = "inside_folder"

UUID_LIKE_RE = re.compile(
    r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?: \(\d+\))?$"
)
HEX_HASH_RE = re.compile(r"^[0-9a-fA-F]{24,}(?: \(\d+\))?$")
IMG_NUMBER_RE = re.compile(r"^(IMG)[ _-]?(\d+)(?:\s*\(\d+\))?$", re.IGNORECASE)
PREFIX_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9_-]+")

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
