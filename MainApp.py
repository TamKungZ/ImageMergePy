import base64
import hashlib
import os
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from embedded_fonts import EMBEDDED_FONTS

APP_FALLBACK_TITLE = "ImageMerge"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mts"}
MEDIA_EXTS = IMAGE_EXTS | VIDEO_EXTS

MODE_MOVE = "move"
MODE_COPY_DELETE = "copy_delete"
MODE_COPY_KEEP = "copy_keep"

DEFAULT_LANG = "en"
SUPPORTED_LANGS = {"en", "th"}

EMBEDDED_LOCALES: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "ImageMerge",
        "app_header": "ImageMerge / Dedupe Tool",
        "app_desc": "Merge media from multiple folders, de-duplicate by SHA-256 + extension, rename with sequence numbers, keep images first and videos last, and set a per-folder prefix.",
        "label_language": "Language",
        "lang_en": "English",
        "lang_th": "Thai",
        "section_input": "Input folders + prefix",
        "section_output": "Output folder",
        "section_mode": "Mode",
        "section_log": "Log",
        "btn_add_folder": "Add folder",
        "btn_edit_prefix": "Edit prefix",
        "btn_remove_selected": "Remove selected",
        "btn_clear_all": "Clear all",
        "btn_select_output": "Select output",
        "btn_start": "Start",
        "col_folder": "Folder",
        "col_prefix": "Prefix",
        "mode_copy_keep": "Copy only (keep source files)",
        "mode_copy_delete": "Copy then delete source files",
        "mode_move": "Move files from input to output",
        "opt_clear_output": "Clear existing media in output before starting",
        "mode_note": "Notes: Duplicate files are skipped when both file hash and extension match. Names like IMG_0072 are sorted by number first. UUID-like and long-hash names are sorted by creation time.",
        "prompt_prefix": "Set a prefix for this folder. Leave empty if not needed (example: full, short, ref).",
        "dlg_select_input": "Select input folder",
        "dlg_select_output": "Select output folder",
        "msg_folder_exists": "This folder has already been added.",
        "msg_select_folder_first": "Please select a folder first.",
        "msg_edit_one_at_a_time": "You can edit one prefix at a time.",
        "msg_need_input": "Please add at least one input folder.",
        "msg_need_output": "Please select an output folder.",
        "msg_done": "Completed.",
        "error_no_input": "No input folder selected.",
        "error_output_same_as_input": "Output folder cannot be the same as an input folder.",
        "error_unknown_mode": "Unknown mode: {mode}",
        "log_start": "Starting...",
        "log_mode": "Mode: {mode}",
        "log_output_dir": "Output: {output}",
        "log_input_entry": "Input: {input_path} | prefix: {prefix}",
        "log_clearing_output": "Clearing existing media in output...",
        "log_cleared_output": "Cleared {count} media files from output.",
        "log_output_organized": "Organized output: {count} files (images first, videos last).",
        "log_skip_unreadable_output": "Skip unreadable output file: {path} -> {error}",
        "log_found_media": "Found {count} media files in input.",
        "log_hash_failed": "Cannot compute hash: {path} -> {error}",
        "log_duplicate_skip": "Duplicate skipped: {path}",
        "log_source_deleted": "Deleted source: {path}",
        "log_source_delete_failed": "Cannot delete source: {path} -> {error}",
        "log_moved": "Moved: {source} -> {dest}",
        "log_copied": "Copied: {source} -> {dest}",
        "log_process_failed": "Failed to process: {path} -> {error}",
        "log_added": "Added: {count}",
        "log_skipped": "Skipped duplicates: {count}",
        "log_moved_count": "Moved: {count}",
        "log_copied_count": "Copied: {count}",
        "log_deleted_sources": "Deleted sources: {count}",
        "log_failed": "Failed: {count}",
        "log_total_output": "Total output files: {count}",
        "log_done": "Done",
    },
    "th": {
        "app_title": "ImageMerge",
        "app_header": "ImageMerge / เครื่องมือรวมและกันไฟล์ซ้ำ",
        "app_desc": "รวมไฟล์รูปและวิดีโอจากหลายโฟลเดอร์, กันไฟล์ซ้ำด้วย SHA-256 + นามสกุลไฟล์, ตั้งชื่อใหม่แบบลำดับเลข, จัดรูปไว้ก่อนและวิดีโอไว้ท้าย, และตั้ง prefix แยกตามโฟลเดอร์ได้",
        "label_language": "ภาษา",
        "lang_en": "อังกฤษ",
        "lang_th": "ไทย",
        "section_input": "โฟลเดอร์ต้นทาง + prefix",
        "section_output": "โฟลเดอร์ปลายทาง",
        "section_mode": "โหมดการทำงาน",
        "section_log": "บันทึกการทำงาน",
        "btn_add_folder": "เพิ่มโฟลเดอร์",
        "btn_edit_prefix": "แก้ prefix",
        "btn_remove_selected": "ลบที่เลือก",
        "btn_clear_all": "ล้างทั้งหมด",
        "btn_select_output": "เลือก output",
        "btn_start": "เริ่ม",
        "col_folder": "โฟลเดอร์",
        "col_prefix": "Prefix",
        "mode_copy_keep": "คัดลอกอย่างเดียว (ไม่ลบต้นฉบับ)",
        "mode_copy_delete": "คัดลอกแล้วลบต้นฉบับ",
        "mode_move": "ย้ายไฟล์จาก input ไป output",
        "opt_clear_output": "ล้างไฟล์ media เดิมใน output ก่อนเริ่ม",
        "mode_note": "หมายเหตุ: ไฟล์ซ้ำจะถูกข้ามเมื่อ hash และนามสกุลตรงกัน ชื่อแนว IMG_0072 จะเรียงตามเลขก่อน ส่วนชื่อแนว UUID หรือ hash ยาวจะเรียงตามเวลา",
        "prompt_prefix": "ตั้ง prefix สำหรับโฟลเดอร์นี้ (ปล่อยว่างได้) เช่น full, short, ref",
        "dlg_select_input": "เลือก input folder",
        "dlg_select_output": "เลือก output folder",
        "msg_folder_exists": "โฟลเดอร์นี้ถูกเพิ่มแล้ว",
        "msg_select_folder_first": "กรุณาเลือกโฟลเดอร์ก่อน",
        "msg_edit_one_at_a_time": "แก้ prefix ได้ครั้งละ 1 โฟลเดอร์",
        "msg_need_input": "กรุณาเลือก input folder อย่างน้อย 1 โฟลเดอร์",
        "msg_need_output": "กรุณาเลือก output folder",
        "msg_done": "ทำเสร็จแล้ว",
        "error_no_input": "ยังไม่ได้เลือก input folder",
        "error_output_same_as_input": "output folder ห้ามซ้ำกับ input folder",
        "error_unknown_mode": "ไม่รู้จักโหมด: {mode}",
        "log_start": "เริ่มทำงาน...",
        "log_mode": "โหมด: {mode}",
        "log_output_dir": "Output: {output}",
        "log_input_entry": "Input: {input_path} | prefix: {prefix}",
        "log_clearing_output": "กำลังล้างไฟล์ media เดิมใน output...",
        "log_cleared_output": "ล้าง output media เดิมแล้ว {count} ไฟล์",
        "log_output_organized": "จัดระเบียบ output เสร็จ {count} ไฟล์ (รูปก่อน วิดีโอท้ายสุด)",
        "log_skip_unreadable_output": "ข้ามไฟล์ output ที่อ่านไม่ได้: {path} -> {error}",
        "log_found_media": "พบ media ใน input ทั้งหมด {count} ไฟล์",
        "log_hash_failed": "อ่าน hash ไม่ได้: {path} -> {error}",
        "log_duplicate_skip": "ซ้ำ ข้าม: {path}",
        "log_source_deleted": "ลบต้นฉบับ: {path}",
        "log_source_delete_failed": "ลบไม่ได้: {path} -> {error}",
        "log_moved": "ย้าย: {source} -> {dest}",
        "log_copied": "คัดลอก: {source} -> {dest}",
        "log_process_failed": "ทำไม่สำเร็จ: {path} -> {error}",
        "log_added": "เพิ่มใหม่: {count}",
        "log_skipped": "ซ้ำข้ามไป: {count}",
        "log_moved_count": "ย้าย: {count}",
        "log_copied_count": "คัดลอก: {count}",
        "log_deleted_sources": "ลบต้นฉบับ: {count}",
        "log_failed": "ผิดพลาด: {count}",
        "log_total_output": "รวม output ตอนนี้: {count} ไฟล์",
        "log_done": "เสร็จแล้ว",
    },
}

UUID_LIKE_RE = re.compile(
    r"^(?:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?: \(\d+\))?$"
)
HEX_HASH_RE = re.compile(r"^[0-9a-fA-F]{24,}(?: \(\d+\))?$")
IMG_NUMBER_RE = re.compile(r"^(IMG)[ _-]?(\d+)(?:\s*\(\d+\))?$", re.IGNORECASE)
PREFIX_ALLOWED_RE = re.compile(r"[^a-zA-Z0-9_-]+")


def setup_app_fonts() -> str:
    for encoded_data in EMBEDDED_FONTS.values():
        try:
            font_bytes = base64.b64decode(encoded_data)
            font_id = QFontDatabase.addApplicationFontFromData(QByteArray(font_bytes))
            if font_id == -1:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]
        except Exception:
            continue

    if os.name == "nt":
        return "Leelawadee UI"
    if sys.platform == "darwin":
        return "SF Pro Text"
    return "Noto Sans"


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
    return DEFAULT_LANG


class I18n:
    def __init__(self, lang: str):
        self.catalogs: dict[str, dict[str, str]] = {}
        self._load_catalog(DEFAULT_LANG)
        self._load_catalog("th")
        self.lang = lang if lang in self.catalogs else DEFAULT_LANG

    def _load_catalog(self, lang: str):
        embedded = EMBEDDED_LOCALES.get(lang, {})
        self.catalogs[lang] = {str(key): str(value) for key, value in embedded.items()}

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


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.i18n = I18n(detect_language())
        self.t = self.i18n.t

        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.resize(1120, 780)
        self.setMinimumSize(980, 680)

        self.input_entries: list[dict] = []
        self.is_running = False
        self.worker_thread: QThread | None = None
        self.worker: ProcessWorker | None = None

        self.font_family = setup_app_fonts()
        self._build_ui()

    def _build_ui(self):
        app_font = QFont(self.font_family, 10)
        app_font.setStyleStrategy(QFont.PreferAntialias)
        QApplication.instance().setFont(app_font)

        central = QWidget(self)
        self.setCentralWidget(central)

        outer = QVBoxLayout(central)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        self.setStyleSheet(
            """
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #f7f9fc, stop:1 #eef3f8);
            }
            * {
                font-family: "%s";
            }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #d2dae5;
                border-radius: 10px;
                margin-top: 8px;
                padding-top: 10px;
                background-color: rgba(255, 255, 255, 0.8);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
                color: #1e2b3a;
            }
            QLabel#header {
                font-size: 20px;
                font-weight: 700;
                color: #1f3146;
            }
            QLabel#desc {
                color: #3a4a5a;
            }
            QPushButton {
                background-color: #1f6aa5;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #185684;
            }
            QPushButton:disabled {
                background-color: #9fb7cb;
                color: #e8eff5;
            }
            QLineEdit, QTextEdit, QTreeWidget {
                border: 1px solid #cdd7e3;
                border-radius: 8px;
                background-color: #ffffff;
                selection-background-color: #d7e9ff;
            }
            """
            % self.font_family
        )

        top_row = QHBoxLayout()
        self.header_label = QLabel(self.t("app_header"))
        self.header_label.setObjectName("header")
        top_row.addWidget(self.header_label)
        top_row.addStretch(1)
        self.language_label = QLabel(self.t("label_language"))
        top_row.addWidget(self.language_label)
        self.language_selector = QComboBox()
        self.language_selector.addItem("", "en")
        self.language_selector.addItem("", "th")
        self.language_selector.currentIndexChanged.connect(self._on_language_changed)
        top_row.addWidget(self.language_selector)
        outer.addLayout(top_row)

        self.desc_label = QLabel(self.t("app_desc"))
        self.desc_label.setObjectName("desc")
        self.desc_label.setWordWrap(True)
        outer.addWidget(self.desc_label)

        self.input_group = QGroupBox(self.t("section_input"))
        input_layout = QVBoxLayout(self.input_group)
        input_layout.setSpacing(8)

        input_btn_row = QHBoxLayout()
        self.add_folder_btn = QPushButton(self.t("btn_add_folder"))
        self.add_folder_btn.clicked.connect(self.add_input_folder)
        self.edit_prefix_btn = QPushButton(self.t("btn_edit_prefix"))
        self.edit_prefix_btn.clicked.connect(self.edit_selected_prefix)
        self.remove_btn = QPushButton(self.t("btn_remove_selected"))
        self.remove_btn.clicked.connect(self.remove_selected_input)
        self.clear_btn = QPushButton(self.t("btn_clear_all"))
        self.clear_btn.clicked.connect(self.clear_inputs)

        input_btn_row.addWidget(self.add_folder_btn)
        input_btn_row.addWidget(self.edit_prefix_btn)
        input_btn_row.addWidget(self.remove_btn)
        input_btn_row.addWidget(self.clear_btn)
        input_btn_row.addStretch(1)
        input_layout.addLayout(input_btn_row)

        self.input_tree = QTreeWidget()
        self.input_tree.setColumnCount(2)
        self.input_tree.setHeaderLabels([self.t("col_folder"), self.t("col_prefix")])
        self.input_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.input_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.input_tree.setAlternatingRowColors(True)
        self.input_tree.itemDoubleClicked.connect(lambda _item, _col: self.edit_selected_prefix())
        input_layout.addWidget(self.input_tree)
        outer.addWidget(self.input_group)

        self.output_group = QGroupBox(self.t("section_output"))
        output_layout = QHBoxLayout(self.output_group)
        self.output_input = QLineEdit()
        self.output_input.setPlaceholderText(self.t("section_output"))
        self.output_btn = QPushButton(self.t("btn_select_output"))
        self.output_btn.clicked.connect(self.choose_output_folder)
        output_layout.addWidget(self.output_input)
        output_layout.addWidget(self.output_btn)
        outer.addWidget(self.output_group)

        self.mode_group = QGroupBox(self.t("section_mode"))
        mode_layout = QVBoxLayout(self.mode_group)

        self.radio_copy_keep = QRadioButton(self.t("mode_copy_keep"))
        self.radio_copy_keep.setChecked(True)
        self.radio_copy_delete = QRadioButton(self.t("mode_copy_delete"))
        self.radio_move = QRadioButton(self.t("mode_move"))

        mode_layout.addWidget(self.radio_copy_keep)
        mode_layout.addWidget(self.radio_copy_delete)
        mode_layout.addWidget(self.radio_move)

        self.clear_output_checkbox = QCheckBox(self.t("opt_clear_output"))
        mode_layout.addWidget(self.clear_output_checkbox)

        self.mode_note_label = QLabel(self.t("mode_note"))
        self.mode_note_label.setWordWrap(True)
        mode_layout.addWidget(self.mode_note_label)

        outer.addWidget(self.mode_group)

        action_row = QHBoxLayout()
        self.start_btn = QPushButton(self.t("btn_start"))
        self.start_btn.clicked.connect(self.start_process)
        action_row.addWidget(self.start_btn)
        action_row.addStretch(1)
        outer.addLayout(action_row)

        self.log_group = QGroupBox(self.t("section_log"))
        log_layout = QVBoxLayout(self.log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        outer.addWidget(self.log_group, 1)

        lang_index = self.language_selector.findData(self.i18n.lang)
        if lang_index >= 0:
            self.language_selector.setCurrentIndex(lang_index)

        self._retranslate_ui()

    def _retranslate_ui(self):
        self.setWindowTitle(self.t("app_title") or APP_FALLBACK_TITLE)
        self.header_label.setText(self.t("app_header"))
        self.desc_label.setText(self.t("app_desc"))
        self.language_label.setText(self.t("label_language"))
        self.language_selector.setItemText(0, self.t("lang_en"))
        self.language_selector.setItemText(1, self.t("lang_th"))

        self.input_group.setTitle(self.t("section_input"))
        self.output_group.setTitle(self.t("section_output"))
        self.mode_group.setTitle(self.t("section_mode"))
        self.log_group.setTitle(self.t("section_log"))

        self.add_folder_btn.setText(self.t("btn_add_folder"))
        self.edit_prefix_btn.setText(self.t("btn_edit_prefix"))
        self.remove_btn.setText(self.t("btn_remove_selected"))
        self.clear_btn.setText(self.t("btn_clear_all"))
        self.output_btn.setText(self.t("btn_select_output"))
        self.start_btn.setText(self.t("btn_start"))

        self.input_tree.setHeaderLabels([self.t("col_folder"), self.t("col_prefix")])
        self.output_input.setPlaceholderText(self.t("section_output"))
        self.radio_copy_keep.setText(self.t("mode_copy_keep"))
        self.radio_copy_delete.setText(self.t("mode_copy_delete"))
        self.radio_move.setText(self.t("mode_move"))
        self.clear_output_checkbox.setText(self.t("opt_clear_output"))
        self.mode_note_label.setText(self.t("mode_note"))

    def _on_language_changed(self, _index: int):
        lang_code = self.language_selector.currentData()
        if lang_code not in SUPPORTED_LANGS or lang_code == self.i18n.lang:
            return
        self.i18n.lang = lang_code
        self._retranslate_ui()

    def prompt_prefix(self, initial: str = "") -> str | None:
        value, accepted = QInputDialog.getText(
            self,
            self.t("app_title"),
            self.t("prompt_prefix"),
            text=initial,
        )
        if not accepted:
            return None
        return normalize_prefix(value)

    def append_log(self, text: str):
        self.log_text.append(text)

    def add_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_input"))
        if not folder:
            return

        path = Path(folder)
        if any(entry["path"] == path for entry in self.input_entries):
            QMessageBox.information(self, self.t("app_title"), self.t("msg_folder_exists"))
            return

        prefix = self.prompt_prefix(path.name)
        if prefix is None:
            return

        entry = {"path": path, "prefix": prefix}
        self.input_entries.append(entry)

        item = QTreeWidgetItem([str(path), prefix or "-"])
        item.setData(0, Qt.UserRole, str(path))
        self.input_tree.addTopLevelItem(item)

    def _selected_item_paths(self) -> list[str]:
        return [item.data(0, Qt.UserRole) for item in self.input_tree.selectedItems()]

    def edit_selected_prefix(self):
        selected_paths = self._selected_item_paths()
        if not selected_paths:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_select_folder_first"))
            return
        if len(selected_paths) > 1:
            QMessageBox.warning(self, self.t("app_title"), self.t("msg_edit_one_at_a_time"))
            return

        selected_path = selected_paths[0]
        for entry in self.input_entries:
            if str(entry["path"]) == selected_path:
                new_prefix = self.prompt_prefix(entry.get("prefix", ""))
                if new_prefix is None:
                    return

                entry["prefix"] = new_prefix
                for idx in range(self.input_tree.topLevelItemCount()):
                    item = self.input_tree.topLevelItem(idx)
                    if item.data(0, Qt.UserRole) == selected_path:
                        item.setText(1, new_prefix or "-")
                        return

    def remove_selected_input(self):
        selected_items = self.input_tree.selectedItems()
        if not selected_items:
            return

        selected_paths = {item.data(0, Qt.UserRole) for item in selected_items}
        self.input_entries = [entry for entry in self.input_entries if str(entry["path"]) not in selected_paths]

        for item in selected_items:
            index = self.input_tree.indexOfTopLevelItem(item)
            if index >= 0:
                self.input_tree.takeTopLevelItem(index)

    def clear_inputs(self):
        self.input_entries.clear()
        self.input_tree.clear()

    def choose_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.t("dlg_select_output"))
        if folder:
            self.output_input.setText(folder)

    def _selected_mode(self) -> str:
        if self.radio_move.isChecked():
            return MODE_MOVE
        if self.radio_copy_delete.isChecked():
            return MODE_COPY_DELETE
        return MODE_COPY_KEEP

    def start_process(self):
        if self.is_running:
            return

        input_configs = [{"path": entry["path"], "prefix": entry.get("prefix", "")} for entry in self.input_entries]
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
        self.start_btn.setEnabled(False)
        self.is_running = True

        output_dir = Path(output_dir_text)

        self.worker_thread = QThread(self)
        self.worker = ProcessWorker(input_configs, output_dir, mode, clear_output_first, self.t)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_line.connect(self.append_log)
        self.worker.process_done.connect(
            lambda: QMessageBox.information(self, self.t("app_title"), self.t("msg_done"))
        )
        self.worker.process_error.connect(
            lambda message: QMessageBox.critical(self, self.t("app_title"), message)
        )
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.finished.connect(self._on_process_finished)

        self.worker_thread.start()

    def _on_process_finished(self):
        self.is_running = False
        self.start_btn.setEnabled(True)
        self.worker = None
        self.worker_thread = None


if __name__ == "__main__":
    qt_app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(qt_app.exec())
