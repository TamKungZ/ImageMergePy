import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QObject, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QFontMetrics, QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from embedded_fonts import EMBEDDED_FONTS
from embedded_locales import EMBEDDED_LOCALES as FILE_EMBEDDED_LOCALES

APP_FALLBACK_TITLE = "ImageMerge"
APP_DIR = Path(__file__).resolve().parent
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

C_BG        = "#f4f6fb"
C_SURFACE   = "#ffffff"
C_SURFACE2  = "#f7f9fd"
C_SURFACE3  = "#e8eef8"
C_BORDER    = "rgba(39,61,97,0.12)"
C_BORDER2   = "rgba(39,61,97,0.22)"
C_ACCENT    = "#2f6fed"
C_ACCENT_DIM= "rgba(47,111,237,0.12)"
C_TEXT      = "#1f2a3d"
C_TEXT2     = "#4a5a76"
C_TEXT3     = "#6f7f99"
C_SUCCESS   = "#1ca46f"
C_WARNING   = "#bc8500"
C_DANGER    = "#d54949"

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


def normalize_prefix(prefix: str) -> str:
    prefix = prefix.strip()
    if not prefix:
        return ""
    prefix = prefix.replace(" ", "-")
    prefix = PREFIX_ALLOWED_RE.sub("-", prefix)
    prefix = re.sub(r"-+", "-", prefix).strip("-_")
    return prefix.lower()


def build_output_name(index: int, ext: str, prefix: str = "") -> str:
    prefix = normalize_prefix(prefix)
    if prefix:
        return f"{prefix}-{index:04d}{ext.lower()}"
    return f"{index:04d}{ext.lower()}"


def split_existing_prefix_and_number(path: Path) -> tuple[str, int]:
    stem = path.stem
    match = re.match(r"^(?:(.+?)-)?(\d+)$", stem)
    if match:
        prefix = normalize_prefix(match.group(1) or "")
        return prefix, int(match.group(2))
    match_number = re.match(r"^(\d+)", stem)
    if match_number:
        return "", int(match_number.group(1))
    return "", 99999999


def dedupe_key(file_hash: str, ext: str) -> tuple[str, str]:
    return file_hash, ext.lower()


def detect_language() -> str:
    env_lang = os.environ.get("IMAGEMERGE_LANG", "").strip().lower()
    if env_lang in SUPPORTED_LANGS:
        return env_lang
    if "-" in env_lang or "_" in env_lang:
        base = re.split(r"[-_]", env_lang)[0]
        if base in SUPPORTED_LANGS:
            return base
    return DEFAULT_LANG


class I18n:
    def __init__(self, lang: str):
        self.catalogs: dict[str, dict[str, str]] = {}
        for code in sorted(SUPPORTED_LANGS):
            self._load_catalog(code)
        if not self.catalogs.get(DEFAULT_LANG):
            self.catalogs[DEFAULT_LANG] = {}
        self.lang = lang if lang in self.catalogs else DEFAULT_LANG

    def _load_catalog(self, lang: str):
        catalog: dict[str, str] = {}
        locale_file = LOCALES_DIR / f"{lang}.json"
        if locale_file.exists():
            try:
                parsed = json.loads(locale_file.read_text(encoding="utf-8"))
                if isinstance(parsed, dict):
                    catalog = {str(key): str(value) for key, value in parsed.items()}
            except Exception:
                catalog = {}
        if not catalog:
            embedded = FILE_EMBEDDED_LOCALES.get(lang, {})
            catalog = {str(key): str(value) for key, value in embedded.items()}
        self.catalogs[lang] = catalog

    def t(self, key: str, **kwargs) -> str:
        text = self.catalogs.get(self.lang, {}).get(key)
        if text is None:
            text = self.catalogs.get(DEFAULT_LANG, {}).get(key, key)
        try:
            return text.format(**kwargs)
        except Exception:
            return text


def t_identity(key: str, **kwargs) -> str:
    if not kwargs:
        return key
    try:
        return key.format(**kwargs)
    except Exception:
        return key


class Logger:
    def __init__(self, writer: Callable[[str], None]):
        self.writer = writer

    def write(self, text: str):
        self.writer(text)


def sha256_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def classify_source_name(path: Path) -> tuple[str, int | None]:
    stem = path.stem.strip()
    img_match = IMG_NUMBER_RE.match(stem)
    if img_match:
        return "img_number", int(img_match.group(2))
    if UUID_LIKE_RE.match(stem) or HEX_HASH_RE.match(stem):
        return "time_only", None
    return "default", None


def source_sort_key(item):
    file_path, ctime, _prefix = item
    stem_lower = file_path.stem.lower()
    ext_lower = file_path.suffix.lower()
    group_type, value = classify_source_name(file_path)

    if group_type == "img_number":
        return (0, int(value), ctime, stem_lower, ext_lower)
    if group_type == "time_only":
        return (1, ctime, stem_lower, ext_lower)
    return (2, ctime, stem_lower, ext_lower)


def is_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MEDIA_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def iter_media_files(root_dir: Path):
    for root, _, filenames in os.walk(root_dir):
        for name in filenames:
            file_path = Path(root) / name
            if file_path.suffix.lower() in MEDIA_EXTS:
                yield file_path


def organize_output(output_dir: Path, logger: Logger | None = None, tr=t_identity):
    media_files = [path for path in output_dir.iterdir() if is_media_file(path)]

    image_files = sorted(
        [path for path in media_files if is_image(path)],
        key=lambda path: split_existing_prefix_and_number(path)[1],
    )
    video_files = sorted(
        [path for path in media_files if is_video(path)],
        key=lambda path: split_existing_prefix_and_number(path)[1],
    )
    ordered_files = image_files + video_files

    temp_files: list[tuple[Path, str]] = []
    for file_path in ordered_files:
        prefix, _ = split_existing_prefix_and_number(file_path)
        temp_name = f"__temp__{uuid.uuid4().hex}{file_path.suffix.lower()}"
        temp_path = output_dir / temp_name
        file_path.rename(temp_path)
        temp_files.append((temp_path, prefix))

    renamed_files: list[Path] = []
    for index, (temp_path, prefix) in enumerate(temp_files, start=1):
        new_path = output_dir / build_output_name(index, temp_path.suffix, prefix)
        temp_path.rename(new_path)
        renamed_files.append(new_path)

    if logger:
        logger.write(tr("log_output_organized", count=len(renamed_files)))

    return renamed_files


def collect_source_media(input_dir_configs: list[dict]):
    image_files = []
    video_files = []

    for config in input_dir_configs:
        source_path: Path = config["path"]
        prefix: str = config.get("prefix", "")
        for file_path in iter_media_files(source_path):
            try:
                ctime = os.path.getctime(file_path)
            except OSError:
                ctime = 0
            item = (file_path, ctime, prefix)
            if is_image(file_path):
                image_files.append(item)
            elif is_video(file_path):
                video_files.append(item)

    image_files.sort(key=source_sort_key)
    video_files.sort(key=source_sort_key)
    return image_files + video_files


def safe_delete_file(path: Path, logger: Logger | None = None, tr=t_identity):
    try:
        if path.exists():
            path.unlink()
            if logger:
                logger.write(tr("log_source_deleted", path=path))
    except Exception as exc:
        if logger:
            logger.write(tr("log_source_delete_failed", path=path, error=exc))


def process_media(
    input_dir_configs: list[dict],
    output_dir: Path,
    mode: str,
    clear_output_first: bool,
    logger: Logger,
    tr=t_identity,
):
    if not input_dir_configs:
        raise ValueError(tr("error_no_input"))

    input_paths = [config["path"] for config in input_dir_configs]
    if output_dir in input_paths:
        raise ValueError(tr("error_output_same_as_input"))

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.write(tr("log_start"))
    logger.write(tr("log_mode", mode=mode))
    logger.write(tr("log_output_dir", output=output_dir))
    for config in input_dir_configs:
        logger.write(
            tr(
                "log_input_entry",
                input_path=config["path"],
                prefix=normalize_prefix(config.get("prefix", "")) or "-",
            )
        )

    if clear_output_first:
        logger.write(tr("log_clearing_output"))
        removed = 0
        for path in list(output_dir.iterdir()):
            if is_media_file(path):
                path.unlink()
                removed += 1
        logger.write(tr("log_cleared_output", count=removed))

    existing_output_files = organize_output(output_dir, logger=logger, tr=tr)
    existing_hashes: dict[tuple[str, str], Path] = {}
    for file_path in existing_output_files:
        try:
            file_hash = sha256_file(file_path)
            existing_hashes[dedupe_key(file_hash, file_path.suffix)] = file_path
        except Exception as exc:
            logger.write(tr("log_skip_unreadable_output", path=file_path, error=exc))

    source_items = collect_source_media(input_dir_configs)
    logger.write(tr("log_found_media", count=len(source_items)))

    added = 0
    skipped = 0
    moved = 0
    copied = 0
    deleted_sources = 0
    failed = 0
    current_index = len(existing_output_files)

    for file_path, _ctime, prefix in source_items:
        try:
            file_hash = sha256_file(file_path)
        except Exception as exc:
            failed += 1
            logger.write(tr("log_hash_failed", path=file_path, error=exc))
            continue

        ext = file_path.suffix.lower()
        file_key = dedupe_key(file_hash, ext)

        if file_key in existing_hashes:
            skipped += 1
            logger.write(tr("log_duplicate_skip", path=file_path))
            if mode in {MODE_MOVE, MODE_COPY_DELETE}:
                safe_delete_file(file_path, logger, tr)
                deleted_sources += 1
            continue

        current_index += 1
        dest_path = output_dir / build_output_name(current_index, ext, prefix)

        try:
            if mode == MODE_MOVE:
                shutil.move(str(file_path), str(dest_path))
                moved += 1
                logger.write(tr("log_moved", source=file_path, dest=dest_path.name))
            elif mode == MODE_COPY_DELETE:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(tr("log_copied", source=file_path, dest=dest_path.name))
                safe_delete_file(file_path, logger, tr)
                deleted_sources += 1
            elif mode == MODE_COPY_KEEP:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(tr("log_copied", source=file_path, dest=dest_path.name))
            else:
                raise ValueError(tr("error_unknown_mode", mode=mode))

            existing_hashes[file_key] = dest_path
            added += 1
        except Exception as exc:
            failed += 1
            logger.write(tr("log_process_failed", path=file_path, error=exc))

    final_files = organize_output(output_dir, logger=logger, tr=tr)

    logger.write("=" * 50)
    logger.write(tr("log_added", count=added))
    logger.write(tr("log_skipped", count=skipped))
    logger.write(tr("log_moved_count", count=moved))
    logger.write(tr("log_copied_count", count=copied))
    logger.write(tr("log_deleted_sources", count=deleted_sources))
    logger.write(tr("log_failed", count=failed))
    logger.write(tr("log_total_output", count=len(final_files)))
    logger.write(tr("log_done"))


class ProcessWorker(QObject):
    log_line = Signal(str)
    process_done = Signal()
    process_error = Signal(str)
    finished = Signal()

    def __init__(self, input_configs, output_dir, mode, clear_output_first, tr):
        super().__init__()
        self.input_configs = input_configs
        self.output_dir = output_dir
        self.mode = mode
        self.clear_output_first = clear_output_first
        self.tr = tr

    def run(self):
        logger = Logger(self.log_line.emit)
        try:
            process_media(
                self.input_configs,
                self.output_dir,
                self.mode,
                self.clear_output_first,
                logger,
                self.tr,
            )
            self.process_done.emit()
        except Exception as exc:
            logger.write(f"ERROR: {exc}")
            self.process_error.emit(str(exc))
        finally:
            self.finished.emit()


def parse_cli_input(entry: str) -> dict:
    raw = (entry or "").strip()
    if not raw:
        raise ValueError("Input entry cannot be empty")

    if "::" in raw:
        path_text, prefix_text = raw.rsplit("::", 1)
    else:
        path_text, prefix_text = raw, ""

    path = Path(path_text).expanduser().resolve()
    prefix = normalize_prefix(prefix_text)
    return {"path": path, "prefix": prefix}


def create_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=APP_FALLBACK_TITLE,
        description="ImageMerge CLI mode",
    )
    parser.add_argument("--cli", action="store_true", help="Run in CLI mode without opening GUI")
    parser.add_argument("--input", action="append", default=[], metavar="PATH[::PREFIX]",
                        help="Input folder entry, repeatable.")
    parser.add_argument("--output", default="", metavar="PATH", help="Output folder path")
    parser.add_argument("--mode", default=MODE_COPY_KEEP,
                        choices=[MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE], help="Process mode")
    parser.add_argument("--clear-output", action="store_true",
                        help="Clear media files in output before processing")
    parser.add_argument("--lang", default="", choices=sorted(SUPPORTED_LANGS), help="CLI log language")
    return parser


def run_cli(argv: list[str]) -> int:
    parser = create_cli_parser()
    args = parser.parse_args(argv)

    run_cli_mode = args.cli or bool(args.input) or bool(args.output)
    if not run_cli_mode:
        parser.print_help()
        return 0

    if not args.input:
        parser.error("--input is required in CLI mode")
    if not args.output:
        parser.error("--output is required in CLI mode")

    input_configs = [parse_cli_input(entry) for entry in args.input]
    lang = args.lang or detect_language()
    tr = I18n(lang).t
    output_dir = Path(args.output).expanduser().resolve()
    logger = Logger(lambda text: print(text, flush=True))

    process_media(
        input_configs=input_configs,
        output_dir=output_dir,
        mode=args.mode,
        clear_output_first=args.clear_output,
        logger=logger,
        tr=tr,
    )
    return 0


def _h_sep() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{C_BORDER2}; border:none;")
    return line


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text.upper())
    lbl.setStyleSheet(
        f"color:{C_TEXT3}; font-size:11px; font-weight:700; letter-spacing:1.1px;"
    )
    return lbl


class ModeCard(QWidget):
    clicked = Signal(str)

    def __init__(self, mode_key: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.mode_key = mode_key
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(120)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(6)

        self.title_lbl = QLabel(title)
        self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_TEXT};")
        lay.addWidget(self.title_lbl)

        self.desc_lbl = QLabel(desc)
        self.desc_lbl.setWordWrap(True)
        self.desc_lbl.setStyleSheet(f"font-size:13px; color:{C_TEXT2};")
        lay.addWidget(self.desc_lbl)
        lay.addStretch()

        self._refresh_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()
        if selected:
            self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_ACCENT};")
        else:
            self.title_lbl.setStyleSheet(f"font-size:17px; font-weight:700; color:{C_TEXT};")

    def _refresh_style(self):
        if self._selected:
            self.setStyleSheet(
                f"background:{C_ACCENT_DIM}; border:2px solid {C_ACCENT}; border-radius:10px;"
            )
        else:
            self.setStyleSheet(f"background:{C_SURFACE}; border:1px solid {C_BORDER2}; border-radius:10px;")

    def mousePressEvent(self, _event):
        self.clicked.emit(self.mode_key)


class SourceRow(QWidget):
    remove_requested = Signal(str)
    edit_requested = Signal(str)

    def __init__(self, path: str, prefix: str, parent=None):
        super().__init__(parent)
        self.path_str = path
        self._selected = False
        self.setFixedHeight(46)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 10, 0)
        lay.setSpacing(10)

        self.path_lbl = QLabel(path)
        self.path_lbl.setStyleSheet(f"font-size:14px; color:{C_TEXT};")
        self.path_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lay.addWidget(self.path_lbl)

        self.prefix_lbl = QLabel(prefix if prefix else "—")
        if prefix:
            self.prefix_lbl.setStyleSheet(
                f"font-size:12px; font-weight:700; color:{C_ACCENT};"
                f" background:{C_ACCENT_DIM}; border:1px solid rgba(47,111,237,0.35);"
                f" border-radius:10px; padding:1px 8px;"
            )
        else:
            self.prefix_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3}; padding:1px 8px;")
        self.prefix_lbl.setFixedWidth(110)
        self.prefix_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.prefix_lbl)

        rm_btn = QPushButton("✕")
        rm_btn.setFixedSize(24, 24)
        rm_btn.setCursor(Qt.PointingHandCursor)
        rm_btn.setStyleSheet(
            f"QPushButton {{ background:transparent; border:none; color:{C_TEXT3};"
            f" border-radius:5px; font-size:12px; }}"
            f"QPushButton:hover {{ background:rgba(240,96,96,0.15); color:{C_DANGER}; }}"
        )
        rm_btn.clicked.connect(lambda: self.remove_requested.emit(self.path_str))
        lay.addWidget(rm_btn)

        self._refresh_style()

    def update_prefix(self, prefix: str):
        self.prefix_lbl.setText(prefix if prefix else "—")
        if prefix:
            self.prefix_lbl.setStyleSheet(
                f"font-size:12px; font-weight:700; color:{C_ACCENT};"
                f" background:{C_ACCENT_DIM}; border:1px solid rgba(47,111,237,0.35);"
                f" border-radius:10px; padding:1px 8px;"
            )
        else:
            self.prefix_lbl.setStyleSheet(f"font-size:12px; color:{C_TEXT3}; padding:1px 8px;")

    def set_selected(self, selected: bool):
        self._selected = selected
        self._refresh_style()

    def _refresh_style(self):
        if self._selected:
            self.setStyleSheet(f"background:{C_ACCENT_DIM};")
        else:
            self.setStyleSheet("background:transparent;")

    def mouseDoubleClickEvent(self, _event):
        self.edit_requested.emit(self.path_str)

    def mousePressEvent(self, _event):
        self.edit_requested.emit(self.path_str)


class StatCard(QWidget):
    def __init__(self, label: str, color: str = C_TEXT, parent=None):
        super().__init__(parent)
        self._color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self.value_lbl = QLabel("—")
        self.value_lbl.setStyleSheet(f"font-size:26px; font-weight:700; color:{color};")
        lay.addWidget(self.value_lbl)

        self.label_lbl = QLabel(label.upper())
        self.label_lbl.setStyleSheet(
            f"font-size:11px; font-weight:700; letter-spacing:0.6px; color:{C_TEXT3};"
        )
        lay.addWidget(self.label_lbl)
        self.setStyleSheet(f"background:{C_SURFACE2}; border-radius:8px;")

    def set_value(self, val):
        self.value_lbl.setText(str(val))

    def set_label(self, text: str):
        self.label_lbl.setText(text.upper())


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n(detect_language())
        self.t = self.i18n.t

        icon_path = Path(__file__).resolve().parent / "assets" / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.resize(1160, 780)
        self.setMinimumSize(960, 640)

        self.input_entries: list[dict] = []
        self._source_rows: dict[str, SourceRow] = {}
        self._selected_path: str | None = None
        self._current_mode: str = MODE_COPY_KEEP

        self.is_running = False
        self.worker_thread: QThread | None = None
        self.worker: ProcessWorker | None = None

        self.font_family = setup_app_fonts(self.i18n.lang)
        self._lang_codes = sorted(SUPPORTED_LANGS, key=lambda code: (code != DEFAULT_LANG, code))
        self._title_desc_full = ""
        self._apply_dark_palette()
        self._build_ui()

    def _apply_dark_palette(self):
        app = QApplication.instance()
        palette = QPalette()
        bg = QColor(C_BG)
        surface = QColor(C_SURFACE)
        text = QColor(C_TEXT)
        text2 = QColor(C_TEXT2)
        accent = QColor(C_ACCENT)

        palette.setColor(QPalette.Window, bg)
        palette.setColor(QPalette.WindowText, text)
        palette.setColor(QPalette.Base, surface)
        palette.setColor(QPalette.AlternateBase, QColor(C_SURFACE2))
        palette.setColor(QPalette.Text, text)
        palette.setColor(QPalette.Button, QColor(C_SURFACE2))
        palette.setColor(QPalette.ButtonText, text)
        palette.setColor(QPalette.Highlight, accent)
        palette.setColor(QPalette.HighlightedText, QColor("#0f1728"))
        palette.setColor(QPalette.PlaceholderText, QColor(C_TEXT3))
        palette.setColor(QPalette.Disabled, QPalette.WindowText, text2)
        palette.setColor(QPalette.Disabled, QPalette.Text, text2)
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, text2)
        app.setPalette(palette)

        app_font = QFont(self.font_family, 11)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        app.setFont(app_font)

    def _global_stylesheet(self) -> str:
        ff = self.font_family
        return f"""
        * {{ font-family: "{ff}"; }}
        QMainWindow, QWidget#central {{ background: {C_BG}; }}

        /* Titlebar */
        QWidget#titlebar {{ background: {C_SURFACE}; border-bottom: 1px solid {C_BORDER2}; }}

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
            background: {C_ACCENT}; color: #0f1728; border: none;
            border-radius: 10px; font-size: 20px; font-weight: 700; padding: 14px;
        }}
        QPushButton#startBtn:hover {{ background: #2b62cc; }}
        QPushButton#startBtn:pressed {{ background: #2356b7; }}
        QPushButton#startBtn:disabled {{
            background: #dbe7ff; color: #314666;
        }}

        /* Secondary buttons */
        QPushButton#primaryBtn {{
            background-color: {C_ACCENT}; color: #0f1728; border: none;
            border-radius: 7px; padding: 8px 14px; font-size: 14px; font-weight: 600;
        }}
        QPushButton#primaryBtn:hover {{ background-color: #2458bd; }}
        QPushButton#primaryBtn:pressed {{ background-color: #1f4da6; }}
        QPushButton#primaryBtn:disabled {{ background-color: #d8e3fb; color: #6f7f99; border-color: {C_BORDER2}; }}

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
        QPushButton#dangerGhostBtn:hover {{ background: rgba(213,73,73,0.1); color: {C_DANGER}; border-color: rgba(213,73,73,0.35); }}
        QPushButton#dangerGhostBtn:disabled {{ color: {C_TEXT3}; }}

        QPushButton#tinyBtn {{
            background: transparent; color: {C_TEXT3}; border: none;
            border-radius: 5px; padding: 3px 8px; font-size: 12px;
        }}
        QPushButton#tinyBtn:hover {{ background: {C_SURFACE3}; color: {C_TEXT}; }}

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

    def _build_ui(self):
        self.setStyleSheet(self._global_stylesheet())

        central = QWidget(self)
        central.setObjectName("central")
        self.setCentralWidget(central)

        root_lay = QVBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        titlebar = QWidget()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(58)
        tb_lay = QHBoxLayout(titlebar)
        tb_lay.setContentsMargins(20, 0, 20, 0)
        tb_lay.setSpacing(10)

        self.app_name_label = QLabel()
        self.app_name_label.setStyleSheet(f"color:{C_TEXT}; font-size:22px; font-weight:700;")

        tb_lay.addWidget(self.app_name_label)
        tb_lay.addStretch()

        self.desc_label = QLabel()
        self.desc_label.setStyleSheet(f"color:{C_TEXT3}; font-size:13px;")
        self.desc_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.desc_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        tb_lay.addWidget(self.desc_label)

        tb_lay.addSpacing(16)

        self.lang_label = QLabel()
        self.lang_label.setStyleSheet(f"color:{C_TEXT2}; font-size:13px;")
        tb_lay.addWidget(self.lang_label)

        self.lang_selector = QComboBox()
        self.lang_selector.setObjectName("langSelector")
        for code in self._lang_codes:
            self.lang_selector.addItem("", code)
        self.lang_selector.currentIndexChanged.connect(self._on_lang_selector_changed)
        tb_lay.addWidget(self.lang_selector)

        root_lay.addWidget(titlebar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setChildrenCollapsible(False)
        root_lay.addWidget(splitter, 1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setStyleSheet(f"background:{C_BG};")

        left_widget = QWidget()
        left_widget.setStyleSheet(f"background:{C_BG};")
        left_lay = QVBoxLayout(left_widget)
        left_lay.setContentsMargins(20, 20, 20, 20)
        left_lay.setSpacing(20)

        self.source_section_label = _section_label("")
        src_hdr = QHBoxLayout()
        src_hdr.addWidget(self.source_section_label)
        src_hdr.addStretch()

        self.add_folder_btn = QPushButton()
        self.add_folder_btn.setObjectName("primaryBtn")
        self.add_folder_btn.setCursor(Qt.PointingHandCursor)
        self.add_folder_btn.setEnabled(True)
        self.add_folder_btn.clicked.connect(self.add_input_folder)

        self.edit_prefix_btn = QPushButton()
        self.edit_prefix_btn.setObjectName("ghostBtn")
        self.edit_prefix_btn.setCursor(Qt.PointingHandCursor)
        self.edit_prefix_btn.setEnabled(False)
        self.edit_prefix_btn.clicked.connect(self.edit_selected_prefix)

        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("dangerGhostBtn")
        self.remove_btn.setCursor(Qt.PointingHandCursor)
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_selected_input)

        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("dangerGhostBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_inputs)

        src_hdr.addWidget(self.add_folder_btn)
        src_hdr.addWidget(self.edit_prefix_btn)
        src_hdr.addWidget(self.remove_btn)
        src_hdr.addWidget(self.clear_btn)
        left_lay.addLayout(src_hdr)

        src_container = QWidget()
        src_container.setObjectName("sourceContainer")
        src_container_lay = QVBoxLayout(src_container)
        src_container_lay.setContentsMargins(0, 0, 0, 0)
        src_container_lay.setSpacing(0)

        src_header_bar = QWidget()
        src_header_bar.setObjectName("sourceHeaderBar")
        src_header_bar.setFixedHeight(30)
        shb_lay = QHBoxLayout(src_header_bar)
        shb_lay.setContentsMargins(14, 0, 10, 0)
        shb_lay.setSpacing(10)

        self.col_folder_lbl = QLabel()
        self.col_folder_lbl.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"
        )
        shb_lay.addWidget(self.col_folder_lbl, 1)

        self.col_prefix_lbl = QLabel()
        self.col_prefix_lbl.setFixedWidth(90)
        self.col_prefix_lbl.setAlignment(Qt.AlignCenter)
        self.col_prefix_lbl.setStyleSheet(
            f"font-size:13px; font-weight:600; color:{C_TEXT3}; letter-spacing:0.2px;"
        )
        shb_lay.addWidget(self.col_prefix_lbl)
        shb_lay.addSpacing(34)  # room for ✕ button

        src_container_lay.addWidget(src_header_bar)

        self.rows_scroll = QScrollArea()
        self.rows_scroll.setWidgetResizable(True)
        self.rows_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.rows_scroll.setFrameShape(QFrame.NoFrame)
        self.rows_scroll.setFixedHeight(170)
        self.rows_scroll.setStyleSheet("background:transparent;")

        self.rows_widget = QWidget()
        self.rows_widget.setStyleSheet("background:transparent;")
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.setSpacing(0)
        self.rows_layout.setAlignment(Qt.AlignTop)

        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color:{C_TEXT3}; font-size:14px; padding:28px;")
        self.rows_layout.addWidget(self.empty_label)

        self.rows_scroll.setWidget(self.rows_widget)
        src_container_lay.addWidget(self.rows_scroll)

        left_lay.addWidget(src_container)

        self.output_section_label = _section_label("")
        left_lay.addWidget(self.output_section_label)

        out_row = QHBoxLayout()
        self.output_input = QLineEdit()
        self.output_input.setObjectName("outputPath")
        self.output_input.setReadOnly(True)
        out_row.addWidget(self.output_input)

        self.output_btn = QPushButton()
        self.output_btn.setObjectName("ghostBtn")
        self.output_btn.setCursor(Qt.PointingHandCursor)
        self.output_btn.clicked.connect(self.choose_output_folder)
        out_row.addWidget(self.output_btn)
        left_lay.addLayout(out_row)

        self.mode_section_label = _section_label("")
        left_lay.addWidget(self.mode_section_label)

        mode_grid = QHBoxLayout()
        mode_grid.setSpacing(12)

        self.mode_cards: dict[str, ModeCard] = {}
        for key in [MODE_COPY_KEEP, MODE_COPY_DELETE, MODE_MOVE]:
            card = ModeCard(key, "", "")
            card.clicked.connect(self._on_mode_card_clicked)
            self.mode_cards[key] = card
            mode_grid.addWidget(card)

        self.mode_cards[MODE_COPY_KEEP].set_selected(True)
        left_lay.addLayout(mode_grid)

        self.opt_section_label = _section_label("")
        left_lay.addWidget(self.opt_section_label)

        self.clear_output_checkbox = QCheckBox()
        left_lay.addWidget(self.clear_output_checkbox)

        self.mode_note_label = QLabel()
        self.mode_note_label.setObjectName("noteLabel")
        self.mode_note_label.setWordWrap(True)
        left_lay.addWidget(self.mode_note_label)

        left_lay.addStretch()

        footer_lay = QHBoxLayout()
        footer_lay.setContentsMargins(0, 0, 0, 0)
        footer_lay.setSpacing(8)
        self.info_btn = QPushButton("i")
        self.info_btn.setObjectName("infoBtn")
        self.info_btn.setCursor(Qt.PointingHandCursor)
        self.info_btn.clicked.connect(self.show_about_popup)
        footer_lay.addWidget(self.info_btn, 0, Qt.AlignLeft | Qt.AlignBottom)
        footer_lay.addStretch()
        left_lay.addLayout(footer_lay)

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel.setMinimumWidth(260)
        right_panel.setMaximumWidth(320)
        rp_lay = QVBoxLayout(right_panel)
        rp_lay.setContentsMargins(0, 0, 0, 0)
        rp_lay.setSpacing(0)

        btn_area = QWidget()
        btn_area.setStyleSheet(f"background:{C_SURFACE};")
        btn_area_lay = QVBoxLayout(btn_area)
        btn_area_lay.setContentsMargins(16, 16, 16, 16)
        btn_area_lay.setSpacing(0)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("startBtn")
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.clicked.connect(self.start_process)
        btn_area_lay.addWidget(self.start_btn)
        rp_lay.addWidget(btn_area)

        rp_lay.addWidget(_h_sep())

        stats_widget = QWidget()
        stats_widget.setStyleSheet(f"background:{C_SURFACE};")
        stats_lay = QVBoxLayout(stats_widget)
        stats_lay.setContentsMargins(16, 16, 16, 16)
        stats_lay.setSpacing(8)

        grid1 = QHBoxLayout()
        grid1.setSpacing(8)
        self.stat_added   = StatCard(self.t("stat_added"),   C_SUCCESS)
        self.stat_skipped = StatCard(self.t("stat_skipped"), C_WARNING)
        grid1.addWidget(self.stat_added)
        grid1.addWidget(self.stat_skipped)

        grid2 = QHBoxLayout()
        grid2.setSpacing(8)
        self.stat_total  = StatCard(self.t("stat_total_out"), C_TEXT)
        self.stat_failed = StatCard(self.t("stat_failed"),    C_DANGER)
        grid2.addWidget(self.stat_total)
        grid2.addWidget(self.stat_failed)

        stats_lay.addLayout(grid1)
        stats_lay.addLayout(grid2)
        rp_lay.addWidget(stats_widget)

        rp_lay.addWidget(_h_sep())

        log_hdr = QWidget()
        log_hdr.setStyleSheet(f"background:{C_SURFACE};")
        log_hdr_lay = QHBoxLayout(log_hdr)
        log_hdr_lay.setContentsMargins(16, 10, 10, 6)

        self.log_section_label = _section_label("")
        log_hdr_lay.addWidget(self.log_section_label)
        log_hdr_lay.addStretch()

        clear_log_btn = QPushButton()
        clear_log_btn.setObjectName("tinyBtn")
        clear_log_btn.setCursor(Qt.PointingHandCursor)
        clear_log_btn.clicked.connect(lambda: self.log_text.clear())
        self._clear_log_btn = clear_log_btn
        log_hdr_lay.addWidget(clear_log_btn)
        rp_lay.addWidget(log_hdr)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        rp_lay.addWidget(self.log_text, 1)

        splitter.addWidget(right_panel)
        splitter.setSizes([860, 300])

        self._retranslate_ui()

        lang_index = self.lang_selector.findData(self.i18n.lang)
        if lang_index >= 0:
            self.lang_selector.setCurrentIndex(lang_index)

    def _retranslate_ui(self):
        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.app_name_label.setText(self.t("app_title") or APP_FALLBACK_TITLE)

        self._title_desc_full = self.t("app_desc")
        self._refresh_title_desc()
        self.lang_label.setText(self.t("label_language"))
        current_code = self.lang_selector.currentData()
        self.lang_selector.blockSignals(True)
        for i, code in enumerate(self._lang_codes):
            language_name = LANGUAGE_NATIVE_NAMES.get(code, code.upper())
            self.lang_selector.setItemText(i, language_name)
        selected_index = self.lang_selector.findData(self.i18n.lang)
        if selected_index >= 0:
            self.lang_selector.setCurrentIndex(selected_index)
        elif current_code in self._lang_codes:
            self.lang_selector.setCurrentIndex(self.lang_selector.findData(current_code))
        self.lang_selector.blockSignals(False)

        self.source_section_label.setText(self.t("section_input").upper())
        self.output_section_label.setText(self.t("section_output").upper())
        self.mode_section_label.setText(self.t("section_mode").upper())
        self.opt_section_label.setText(self.t("section_options").upper())
        self.log_section_label.setText(self.t("section_log").upper())

        self.add_folder_btn.setText("+ " + self.t("btn_add_folder"))
        self.edit_prefix_btn.setText(self.t("btn_edit_prefix"))
        self.remove_btn.setText(self.t("btn_remove_selected"))
        self.clear_btn.setText(self.t("btn_clear_all"))
        self.output_btn.setText(self.t("btn_select_output"))
        self.start_btn.setText(self.t("btn_start"))
        self._clear_log_btn.setText(self.t("btn_clear_log"))

        self.col_folder_lbl.setText(self.t("col_folder"))
        self.col_prefix_lbl.setText(self.t("col_prefix"))

        self.output_input.setPlaceholderText(self.t("section_output"))

        mode_data = {
            MODE_COPY_KEEP: self.t("mode_copy_keep"),
            MODE_COPY_DELETE: self.t("mode_copy_delete"),
            MODE_MOVE: self.t("mode_move"),
        }
        short_desc = {
            MODE_COPY_KEEP:   self.t("mode_desc_copy_keep"),
            MODE_COPY_DELETE: self.t("mode_desc_copy_delete"),
            MODE_MOVE:        self.t("mode_desc_move"),
        }
        for key, full in mode_data.items():
            card = self.mode_cards[key]
            card.title_lbl.setText(full)
            card.desc_lbl.setText(short_desc[key])

        self.clear_output_checkbox.setText(self.t("opt_clear_output"))
        self.mode_note_label.setText(self.t("mode_note"))
        self.info_btn.setToolTip("About this app")

        self.stat_added.set_label(self.t("stat_added"))
        self.stat_skipped.set_label(self.t("stat_skipped"))
        self.stat_total.set_label(self.t("stat_total_out"))
        self.stat_failed.set_label(self.t("stat_failed"))

        self._refresh_empty_label()

    def _refresh_title_desc(self):
        if not self._title_desc_full:
            self.desc_label.setText("")
            self.desc_label.setToolTip("")
            return
        text_width = max(40, self.desc_label.width() - 4)
        fm = QFontMetrics(self.desc_label.font())
        self.desc_label.setText(fm.elidedText(self._title_desc_full, Qt.ElideRight, text_width))
        self.desc_label.setToolTip(self._title_desc_full)

    def _refresh_empty_label(self):
        if not self.input_entries:
            self.empty_label.setText(self.t("empty_no_source"))
            self.empty_label.show()
        else:
            self.empty_label.hide()

    def _on_lang_selector_changed(self, _index: int):
        lang = self.lang_selector.currentData()
        if lang not in SUPPORTED_LANGS or lang == self.i18n.lang:
            return
        self.i18n.lang = lang
        self.font_family = setup_app_fonts(lang)
        self._apply_dark_palette()
        self.setStyleSheet(self._global_stylesheet())
        self._retranslate_ui()

    def _build_about_text(self) -> str:
        app_name = APP_METADATA.get("app_name") or APP_FALLBACK_TITLE
        app_desc = self.t("app_desc")
        version = APP_METADATA.get("product_version") or APP_METADATA.get("file_version") or "-"
        company = APP_METADATA.get("company_name") or "-"
        license_note = APP_METADATA.get("copyright") or "MIT License"
        images = ", ".join(sorted(IMAGE_EXTS))
        videos = ", ".join(sorted(VIDEO_EXTS))
        modes = " | ".join(
            [
                self.t("mode_copy_keep"),
                self.t("mode_copy_delete"),
                self.t("mode_move"),
            ]
        )
        langs = ", ".join(LANGUAGE_NATIVE_NAMES.get(code, code.upper()) for code in self._lang_codes)

        return """\
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
""".format(
            app_name=app_name,
            app_desc=app_desc,
            version=version,
            company=company,
            license_note=license_note,
            modes=modes,
            images=images,
            videos=videos,
            langs=langs,
        )

    def show_about_popup(self):
        dialog = QDialog(self)
        dialog.setModal(True)
        dialog.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        dialog.resize(700, 520)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        about_text = QTextEdit(dialog)
        about_text.setReadOnly(True)
        about_text.setFrameShape(QFrame.NoFrame)
        about_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        about_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        about_text.setHtml(self._build_about_text())
        layout.addWidget(about_text, 1)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        ok_button = QPushButton("OK", dialog)
        ok_button.setFixedWidth(104)
        ok_button.clicked.connect(dialog.accept)
        buttons.addWidget(ok_button)
        layout.addLayout(buttons)

        dialog.exec()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_title_desc()

    def _on_mode_card_clicked(self, mode_key: str):
        self._current_mode = mode_key
        for key, card in self.mode_cards.items():
            card.set_selected(key == mode_key)

    def _selected_mode(self) -> str:
        return self._current_mode

    def prompt_prefix(self, initial: str = "") -> str | None:
        value, accepted = QInputDialog.getText(
            self, self.t("app_title"), self.t("prompt_prefix"), text=initial,
        )
        if not accepted:
            return None
        return normalize_prefix(value)

    def _add_source_row(self, path_str: str, prefix: str):
        row = SourceRow(path_str, prefix)
        row.remove_requested.connect(self._remove_by_path)
        row.edit_requested.connect(self._select_row)
        self._source_rows[path_str] = row
        self.rows_layout.addWidget(row)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{C_BORDER}; border:none;")
        sep.setObjectName(f"sep_{path_str}")
        self.rows_layout.addWidget(sep)

    def _clear_source_rows(self):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget() and item.widget() is not self.empty_label:
                item.widget().deleteLater()
        self._source_rows.clear()
        self.rows_layout.addWidget(self.empty_label)

    def _select_row(self, path_str: str):
        if self._selected_path == path_str:
            self._selected_path = None
            if path_str in self._source_rows:
                self._source_rows[path_str].set_selected(False)
        else:
            if self._selected_path and self._selected_path in self._source_rows:
                self._source_rows[self._selected_path].set_selected(False)
            self._selected_path = path_str
            if path_str in self._source_rows:
                self._source_rows[path_str].set_selected(True)
        has_sel = self._selected_path is not None
        self.edit_prefix_btn.setEnabled(has_sel)
        self.remove_btn.setEnabled(has_sel)

    def _remove_by_path(self, path_str: str):
        self.input_entries = [e for e in self.input_entries if str(e["path"]) != path_str]
        if self._selected_path == path_str:
            self._selected_path = None
            self.edit_prefix_btn.setEnabled(False)
            self.remove_btn.setEnabled(False)
        self._clear_source_rows()
        for entry in self.input_entries:
            self._add_source_row(str(entry["path"]), entry.get("prefix", ""))
        self._refresh_empty_label()

    def add_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_input"))
        if not folder:
            return
        path = Path(folder).expanduser().resolve()
        if any(entry["path"] == path for entry in self.input_entries):
            QMessageBox.information(self, self.t("app_title"), self.t("msg_folder_exists"))
            return
        entry = {"path": path, "prefix": ""}
        self.input_entries.append(entry)
        self._add_source_row(str(path), "")
        self._refresh_empty_label()

    def edit_selected_prefix(self):
        if not self._selected_path:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_select_folder_first"))
            return
        for entry in self.input_entries:
            if str(entry["path"]) == self._selected_path:
                new_prefix = self.prompt_prefix(entry.get("prefix", ""))
                if new_prefix is None:
                    return
                entry["prefix"] = new_prefix
                if self._selected_path in self._source_rows:
                    self._source_rows[self._selected_path].update_prefix(new_prefix)
                return

    def remove_selected_input(self):
        if self._selected_path:
            self._remove_by_path(self._selected_path)

    def clear_inputs(self):
        self.input_entries.clear()
        self._selected_path = None
        self.edit_prefix_btn.setEnabled(False)
        self.remove_btn.setEnabled(False)
        self._clear_source_rows()
        self._refresh_empty_label()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_output"))
        if folder:
            self.output_input.setText(folder)

    def append_log(self, text: str):
        self.log_text.append(text)

    def start_process(self):
        if self.is_running:
            return

        input_configs = [{"path": e["path"], "prefix": e.get("prefix", "")} for e in self.input_entries]
        output_dir_text = self.output_input.text().strip()
        mode = self._selected_mode()
        clear_output_first = self.clear_output_checkbox.isChecked()

        if not input_configs:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_input"))
            return
        if not output_dir_text:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_need_output"))
            return

        self.log_text.clear()
        self.stat_added.set_value("—")
        self.stat_skipped.set_value("—")
        self.stat_total.set_value("—")
        self.stat_failed.set_value("—")

        self.start_btn.setEnabled(False)
        self.start_btn.setText(self.t("status_processing"))
        self.is_running = True

        output_dir = Path(output_dir_text)

        self.worker_thread = QThread(self)
        self.worker = ProcessWorker(input_configs, output_dir, mode, clear_output_first, self.t)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_line.connect(self.append_log)
        self.worker.log_line.connect(self._parse_log_for_stats)
        self.worker.process_done.connect(self._on_worker_process_done)
        self.worker.process_error.connect(self._on_worker_process_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_process_finished)

        self.worker_thread.start()

    def _parse_log_for_stats(self, text: str):
        import re as _re
        def _pattern_from_i18n(key: str) -> str:
            template = self.t(key, count="{count}")
            escaped = _re.escape(template)
            return escaped.replace(_re.escape("{count}"), r"(\d+)")

        pairs = [
            (self.stat_added, _pattern_from_i18n("log_added")),
            (self.stat_skipped, _pattern_from_i18n("log_skipped")),
            (self.stat_total, _pattern_from_i18n("log_total_output")),
            (self.stat_failed, _pattern_from_i18n("log_failed")),
        ]
        for card, pattern in pairs:
            m = _re.search(pattern, text)
            if m:
                card.set_value(m.group(1))

    def _on_process_finished(self):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.start_btn.setText(self.t("btn_start"))
        self.worker = None
        self.worker_thread = None

    def _on_worker_process_done(self):
        QMessageBox.information(self, self.t("app_title"), self.t("msg_done"))

    def _on_worker_process_error(self, msg: str):
        QMessageBox.critical(self, self.t("app_title"), msg)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        try:
            sys.exit(run_cli(sys.argv[1:]))
        except SystemExit:
            raise
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr, flush=True)
            sys.exit(1)

    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(qt_app.exec())
