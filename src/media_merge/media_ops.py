import hashlib
import shutil
import uuid
from pathlib import Path
from typing import Callable

from .config import (
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
)
from .i18n import t_identity
from .media_ordering import (
    build_output_name,
    collect_source_media,
    dedupe_key,
    is_media_file,
    normalize_prefix,
    organize_output,
)


class Logger:
    def __init__(self, writer: Callable[[str], None]):
        self.writer = writer

    def write(self, text: str):
        self.writer(text)


def sha256_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


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
    allow_duplicate_files: bool,
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
        skipped = 0
        deleted_sources = 0
        failed = 0
        if remove_duplicates_in_place and not allow_duplicate_files:
            ordered_files = organize_output(
                active_output_dir,
                logger=logger,
                tr=tr,
                minimal_rename=True,
                sort_by_file_mtime=True,
            )
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
    if not allow_duplicate_files:
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
    existing_output_paths = set(existing_output_files)

    for file_path, _, prefix in source_items:
        if allow_duplicate_files and mode == MODE_MAIN_FOLDER and file_path in existing_output_paths:
            continue

        ext = file_path.suffix.lower()
        file_key: tuple[str, str] | None = None
        if not allow_duplicate_files:
            try:
                file_hash = sha256_file(file_path)
            except Exception as exc:
                failed += 1
                logger.write(tr("log_hash_failed", path=file_path, error=exc))
                continue
            file_key = dedupe_key(file_hash, ext)

        if file_key is not None and file_key in existing_hashes:
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

            if file_key is not None:
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
