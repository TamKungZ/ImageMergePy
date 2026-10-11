from __future__ import annotations

import os
import re
import uuid
from pathlib import Path
from typing import Protocol

from .constants import (
    HEX_HASH_RE,
    IMAGE_EXTS,
    IMG_NUMBER_RE,
    MEDIA_EXTS,
    PREFIX_ALLOWED_RE,
    TEMP_ROOT_NAME,
    UUID_LIKE_RE,
    VIDEO_EXTS,
)
from .i18n import t_identity
from .models import SourceFolder


class LogWriter(Protocol):
    def write(self, text: str) -> None: ...


IMAGE_EXT_ORDER = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tiff")
VIDEO_EXT_ORDER = (".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mts")
IMAGE_EXT_PRIORITY = {ext: index for index, ext in enumerate(IMAGE_EXT_ORDER)}
VIDEO_EXT_PRIORITY = {ext: index for index, ext in enumerate(VIDEO_EXT_ORDER)}


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


def split_numbered_stem(path: Path) -> tuple[int, int]:
    stem = path.stem.strip()
    match = re.match(r"^(?:(.+?)-)?(\d+)(?:\s*\((\d+)\))?$", stem)
    if match:
        duplicate_index = int(match.group(3) or 0)
        return int(match.group(2)), duplicate_index
    match_number = re.match(r"^(\d+)(?:\s*\((\d+)\))?", stem)
    if match_number:
        duplicate_index = int(match_number.group(2) or 0)
        return int(match_number.group(1)), duplicate_index
    return 99999999, 99999999


def dedupe_key(file_hash: str, ext: str) -> tuple[str, str]:
    return file_hash, ext.lower()


def classify_source_name(path: Path) -> tuple[str, int | None]:
    stem = path.stem.strip()
    img_match = IMG_NUMBER_RE.match(stem)
    if img_match:
        return "img_number", int(img_match.group(2))
    if UUID_LIKE_RE.match(stem) or HEX_HASH_RE.match(stem):
        return "time_only", None
    return "default", None


def source_sort_key(item):
    file_path, ctime, _ = item
    stem_lower = file_path.stem.lower()
    ext_lower = file_path.suffix.lower()
    group_type, value = classify_source_name(file_path)
    ext_priority = IMAGE_EXT_PRIORITY.get(ext_lower, VIDEO_EXT_PRIORITY.get(ext_lower, 999999))
    number, duplicate_index = split_numbered_stem(file_path)

    if group_type == "img_number":
        return (ext_priority, 0, int(value), duplicate_index, ctime, stem_lower)
    if group_type == "time_only":
        return (ext_priority, 1, ctime, stem_lower)
    return (ext_priority, 2, number, duplicate_index, ctime, stem_lower)


FORMATTED_STEM_RE = re.compile(r"^(?:(?P<prefix>[A-Za-z0-9_-]+?)-)?(?P<number>\d{4,})$")


def media_ext_priority(ext: str) -> int:
    """Images first, then videos; each in the documented extension order."""
    ext = ext.lower()
    if ext in IMAGE_EXT_PRIORITY:
        return IMAGE_EXT_PRIORITY[ext]
    if ext in VIDEO_EXT_PRIORITY:
        return len(IMAGE_EXT_ORDER) + VIDEO_EXT_PRIORITY[ext]
    return 999999


def formatted_sequence_number(path: Path) -> int | None:
    """Sequence number if the name already follows the output format, else None."""
    match = FORMATTED_STEM_RE.match(path.stem.strip())
    return int(match.group("number")) if match else None


def output_sort_key(path: Path, sort_by_file_mtime: bool = False):
    """Sort key for files already sitting in the output folder.

    Files whose names already follow the output format come first and keep their
    existing order (the sequence number decides, nothing else), so an organized
    folder stays where it is and gaps simply close up. Everything else (new or
    hand-named files) follows, ordered by media type -> extension -> (mtime ->)
    number -> duplicate suffix -> prefix -> name.
    """
    stem_lower = path.stem.lower()
    ext_priority = media_ext_priority(path.suffix)
    prefix, existing_number = split_existing_prefix_and_number(path)
    mtime = 0.0
    if sort_by_file_mtime:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0.0

    formatted_number = formatted_sequence_number(path)
    if formatted_number is not None:
        return (0, formatted_number, ext_priority, mtime, prefix, stem_lower)

    number, duplicate_index = split_numbered_stem(path)
    if sort_by_file_mtime:
        return (1, ext_priority, mtime, number, duplicate_index, stem_lower)
    sort_number = number if number != 99999999 else existing_number
    return (1, ext_priority, 0.0, sort_number, duplicate_index, prefix, stem_lower)


def is_media_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in MEDIA_EXTS


def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def iter_media_files(root_dir: Path):
    for root, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [name for name in dirnames if name != TEMP_ROOT_NAME]
        base = Path(root)
        for name in filenames:
            if os.path.splitext(name)[1].lower() in MEDIA_EXTS:
                yield base / name


def organize_output(
    output_dir: Path,
    logger: LogWriter | None = None,
    tr=t_identity,
    minimal_rename: bool = True,
    sort_by_file_mtime: bool = False,
):
    """Re-index the media in ``output_dir`` as one gapless 0001.. sequence.

    Only files whose name differs from their target are touched, so an already
    organized folder is left exactly as it is. ``minimal_rename`` is kept for
    backwards compatibility and no longer changes behaviour.
    """
    media_files = [path for path in output_dir.iterdir() if is_media_file(path)]
    ordered_files = sorted(
        media_files, key=lambda path: output_sort_key(path, sort_by_file_mtime)
    )

    planned: list[tuple[Path, Path]] = []
    final_files: list[Path] = []
    for index, file_path in enumerate(ordered_files, start=1):
        prefix, _ = split_existing_prefix_and_number(file_path)
        desired = output_dir / build_output_name(index, file_path.suffix, prefix)
        final_files.append(desired)
        if file_path.name != desired.name:
            planned.append((file_path, desired))

    if planned:
        temp_pairs: list[tuple[Path, Path]] = []
        for src_path, dst_path in planned:
            temp_path = output_dir / f"__temp__{uuid.uuid4().hex}{src_path.suffix.lower()}"
            src_path.rename(temp_path)
            temp_pairs.append((temp_path, dst_path))
        for temp_path, dst_path in temp_pairs:
            temp_path.rename(dst_path)

    if logger:
        logger.write(tr("log_output_organized", count=len(final_files)))

    return final_files


def collect_source_media(folders: list[SourceFolder]) -> list[tuple[Path, float, str]]:
    image_files = []
    video_files = []
    seen: set[str] = set()

    for folder in folders:
        for file_path in iter_media_files(folder.path):
            identity = os.path.normcase(os.path.abspath(file_path))
            if identity in seen:
                continue
            seen.add(identity)
            try:
                ctime = os.path.getctime(file_path)
            except OSError:
                ctime = 0
            item = (file_path, ctime, folder.prefix)
            if is_image(file_path):
                image_files.append(item)
            elif is_video(file_path):
                video_files.append(item)

    image_files.sort(key=source_sort_key)
    video_files.sort(key=source_sort_key)
    return image_files + video_files