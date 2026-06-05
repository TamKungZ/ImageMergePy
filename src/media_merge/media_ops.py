import hashlib
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Callable

from .config import (
    HEX_HASH_RE,
    IMAGE_EXTS,
    IMG_NUMBER_RE,
    MEDIA_EXTS,
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
    PREFIX_ALLOWED_RE,
    UUID_LIKE_RE,
    VIDEO_EXTS,
)
from .i18n import t_identity

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
    for root, _, filenames in os.walk(root_dir):
        for name in filenames:
            file_path = Path(root) / name
            if file_path.suffix.lower() in MEDIA_EXTS:
                yield file_path


def organize_output(
    output_dir: Path,
    logger: Logger | None = None,
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


def create_safe_workspace(output_dir: Path) -> tuple[Path, Path]:
    root = output_dir / ".imagemerge_temp"
    session_dir = root / f"session-{uuid.uuid4().hex}"
    workspace_output_dir = session_dir / "output"
    workspace_output_dir.mkdir(parents=True, exist_ok=True)
    return session_dir, workspace_output_dir


def copy_media_to_workspace(output_dir: Path, workspace_output_dir: Path):
    for path in output_dir.iterdir():
        if is_media_file(path):
            shutil.copy2(path, workspace_output_dir / path.name)


def apply_workspace_to_output(output_dir: Path, workspace_output_dir: Path):
    for path in list(output_dir.iterdir()):
        if is_media_file(path):
            path.unlink()
    for path in workspace_output_dir.iterdir():
        if is_media_file(path):
            shutil.move(str(path), str(output_dir / path.name))


def process_media(
    input_dir_configs: list[dict],
    output_dir: Path,
    mode: str,
    clear_output_first: bool,
    remove_duplicates_in_place: bool,
    use_safe_temp_workspace: bool,
    logger: Logger,
    tr=t_identity,
):
    if not input_dir_configs and mode not in {MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER}:
        raise ValueError(tr("error_no_input"))

    input_paths = [config["path"] for config in input_dir_configs]
    if mode not in {MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER} and output_dir in input_paths:
        raise ValueError(tr("error_output_same_as_input"))

    output_dir.mkdir(parents=True, exist_ok=True)
    active_output_dir = output_dir
    session_dir: Path | None = None
    pending_source_deletes: list[Path] = []

    if use_safe_temp_workspace:
        session_dir, workspace_output_dir = create_safe_workspace(output_dir)
        copy_media_to_workspace(output_dir, workspace_output_dir)
        active_output_dir = workspace_output_dir
        logger.write(f"Safe workspace: {session_dir}")

    logger.write(tr("log_start"))
    logger.write(tr("log_mode", mode=mode))
    logger.write(tr("log_output_dir", output=output_dir))
    source_scan_configs: list[dict] = []
    if mode == MODE_MAIN_FOLDER:
        seen_paths: set[Path] = set()
        source_scan_configs.append({"path": active_output_dir, "prefix": ""})
        seen_paths.add(active_output_dir)
        for config in input_dir_configs:
            scan_path = config["path"]
            if scan_path in seen_paths:
                continue
            source_scan_configs.append({"path": scan_path, "prefix": config.get("prefix", "")})
            seen_paths.add(scan_path)
    elif mode == MODE_INSIDE_FOLDER:
        source_scan_configs.append({"path": active_output_dir, "prefix": ""})
    else:
        source_scan_configs = list(input_dir_configs)

    for config in source_scan_configs:
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
        for path in list(active_output_dir.iterdir()):
            if is_media_file(path):
                path.unlink()
                removed += 1
        logger.write(tr("log_cleared_output", count=removed))

    if mode == MODE_INSIDE_FOLDER:
        ordered_files = organize_output(
            active_output_dir,
            logger=logger,
            tr=tr,
            minimal_rename=True,
            sort_by_file_mtime=True,
        )
        skipped = 0
        deleted_sources = 0
        failed = 0
        if remove_duplicates_in_place:
            seen_hashes: set[tuple[str, str]] = set()
            for file_path in ordered_files:
                try:
                    file_hash = sha256_file(file_path)
                    file_key = dedupe_key(file_hash, file_path.suffix)
                    if file_key in seen_hashes:
                        safe_delete_file(file_path, logger, tr)
                        deleted_sources += 1
                        skipped += 1
                        continue
                    seen_hashes.add(file_key)
                except Exception as exc:
                    failed += 1
                    logger.write(tr("log_hash_failed", path=file_path, error=exc))

        final_files = organize_output(
            active_output_dir,
            logger=logger,
            tr=tr,
            minimal_rename=True,
            sort_by_file_mtime=True,
        )
        if use_safe_temp_workspace and session_dir:
            apply_workspace_to_output(output_dir, active_output_dir)
            shutil.rmtree(session_dir, ignore_errors=True)
        logger.write("=" * 50)
        logger.write(tr("log_added", count=0))
        logger.write(tr("log_skipped", count=skipped))
        logger.write(tr("log_moved_count", count=0))
        logger.write(tr("log_copied_count", count=0))
        logger.write(tr("log_deleted_sources", count=deleted_sources))
        logger.write(tr("log_failed", count=failed))
        logger.write(tr("log_total_output", count=len(final_files)))
        logger.write(tr("log_done"))
        return

    existing_output_files = organize_output(active_output_dir, logger=logger, tr=tr)
    existing_hashes: dict[tuple[str, str], Path] = {}
    for file_path in existing_output_files:
        try:
            file_hash = sha256_file(file_path)
            existing_hashes[dedupe_key(file_hash, file_path.suffix)] = file_path
        except Exception as exc:
            logger.write(tr("log_skip_unreadable_output", path=file_path, error=exc))

    source_items = collect_source_media(source_scan_configs)
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
                if use_safe_temp_workspace:
                    pending_source_deletes.append(file_path)
                else:
                    safe_delete_file(file_path, logger, tr)
                    deleted_sources += 1
            continue

        current_index += 1
        dest_path = active_output_dir / build_output_name(current_index, ext, prefix)

        try:
            if mode == MODE_MOVE:
                if use_safe_temp_workspace:
                    shutil.copy2(file_path, dest_path)
                    pending_source_deletes.append(file_path)
                else:
                    shutil.move(str(file_path), str(dest_path))
                moved += 1
                logger.write(tr("log_moved", source=file_path, dest=dest_path.name))
            elif mode == MODE_COPY_DELETE:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(tr("log_copied", source=file_path, dest=dest_path.name))
                if use_safe_temp_workspace:
                    pending_source_deletes.append(file_path)
                else:
                    safe_delete_file(file_path, logger, tr)
                    deleted_sources += 1
            elif mode == MODE_COPY_KEEP:
                shutil.copy2(file_path, dest_path)
                copied += 1
                logger.write(tr("log_copied", source=file_path, dest=dest_path.name))
            elif mode in {MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER}:
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

    final_files = organize_output(active_output_dir, logger=logger, tr=tr)

    if use_safe_temp_workspace and session_dir:
        apply_workspace_to_output(output_dir, active_output_dir)
        unique_deletes: list[Path] = []
        seen_del: set[Path] = set()
        for path in pending_source_deletes:
            if path not in seen_del:
                seen_del.add(path)
                unique_deletes.append(path)
        for path in unique_deletes:
            if path.exists():
                safe_delete_file(path, logger, tr)
                deleted_sources += 1
        shutil.rmtree(session_dir, ignore_errors=True)

    logger.write("=" * 50)
    logger.write(tr("log_added", count=added))
    logger.write(tr("log_skipped", count=skipped))
    logger.write(tr("log_moved_count", count=moved))
    logger.write(tr("log_copied_count", count=copied))
    logger.write(tr("log_deleted_sources", count=deleted_sources))
    logger.write(tr("log_failed", count=failed))
    logger.write(tr("log_total_output", count=len(final_files)))
    logger.write(tr("log_done"))


