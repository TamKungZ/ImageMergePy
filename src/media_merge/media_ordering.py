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


def output_sort_key(path: Path, sort_by_file_mtime: bool = False):
    ext_lower = path.suffix.lower()
    ext_priority = IMAGE_EXT_PRIORITY.get(ext_lower, VIDEO_EXT_PRIORITY.get(ext_lower, 999999))
    stem_lower = path.stem.lower()

    if sort_by_file_mtime:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        number, duplicate_index = split_numbered_stem(path)
        return (ext_priority, mtime, number, duplicate_index, stem_lower)

    number, duplicate_index = split_numbered_stem(path)
    prefix, existing_number = split_existing_prefix_and_number(path)
    sort_number = number if number != 99999999 else existing_number
    return (ext_priority, sort_number, duplicate_index, prefix, stem_lower)


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
    minimal_rename: bool = False,
    sort_by_file_mtime: bool = False,
):
    media_files = [path for path in output_dir.iterdir() if is_media_file(path)]

    image_files = sorted(
        [path for path in media_files if is_image(path)],
        key=lambda path: output_sort_key(path, sort_by_file_mtime),
    )
    video_files = sorted(
        [path for path in media_files if is_video(path)],
        key=lambda path: output_sort_key(path, sort_by_file_mtime),
    )
    ordered_files = image_files + video_files

    if minimal_rename:
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
                temp_name = f"__temp__{uuid.uuid4().hex}{src_path.suffix.lower()}"
                temp_path = output_dir / temp_name
                src_path.rename(temp_path)
                temp_pairs.append((temp_path, dst_path))

            for temp_path, dst_path in temp_pairs:
                temp_path.rename(dst_path)

        renamed_files = final_files
    else:
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