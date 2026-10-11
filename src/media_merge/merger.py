"""Merge / main-folder pipeline: import media from source folders into the work dir."""
import errno
import shutil
from pathlib import Path

from .constants import (
    MODE_COPY_DELETE,
    MODE_COPY_KEEP,
    MODE_INSIDE_FOLDER,
    MODE_MAIN_FOLDER,
    MODE_MOVE,
)
from .fileops import safe_delete_file
from .hashing import DuplicateIndex
from .media_ordering import build_output_name, collect_source_media, organize_output
from .models import JobContext

_DISK_FULL = {code for code in (getattr(errno, "ENOSPC", None), getattr(errno, "EDQUOT", None)) if code}


def _remove_source(ctx: JobContext, path: Path) -> None:
    if ctx.defer_deletes:
        ctx.pending_deletes.append(path)
    elif safe_delete_file(path, ctx.logger, ctx.tr):
        ctx.stats.deleted_sources += 1


def _transfer(ctx: JobContext, src: Path, dest: Path) -> None:
    mode, stats, logger, tr = ctx.options.mode, ctx.stats, ctx.logger, ctx.tr
    if mode == MODE_MOVE:
        if ctx.defer_deletes:
            shutil.copy2(src, dest)
            ctx.pending_deletes.append(src)
        else:
            shutil.move(str(src), str(dest))
        stats.moved += 1
        logger.write(tr("log_moved", source=src, dest=dest.name))
    elif mode == MODE_COPY_DELETE:
        shutil.copy2(src, dest)
        stats.copied += 1
        logger.write(tr("log_copied", source=src, dest=dest.name))
        _remove_source(ctx, src)
    elif mode in (MODE_COPY_KEEP, MODE_MAIN_FOLDER, MODE_INSIDE_FOLDER):
        shutil.copy2(src, dest)
        stats.copied += 1
        logger.write(tr("log_copied", source=src, dest=dest.name))
    else:
        raise ValueError(tr("error_unknown_mode", mode=mode))


def run_merge(ctx: JobContext) -> None:
    opts, stats, logger, tr = ctx.options, ctx.stats, ctx.logger, ctx.tr

    existing_files = organize_output(ctx.work_dir, logger=logger, tr=tr)

    index: DuplicateIndex | None = None
    if not opts.allow_duplicate_files:
        index = DuplicateIndex(
            on_error=lambda path, exc: logger.write(
                tr("log_skip_unreadable_output", path=path, error=exc)
            )
        )
        for path in existing_files:
            index.add(path)

    items = collect_source_media(ctx.scan_folders, exclude_dirs=[ctx.options.output_dir])
    total = len(items)
    logger.write(tr("log_found_media", count=total))

    next_number = len(existing_files)
    for position, (src, _ctime, prefix) in enumerate(items, start=1):
        ctx.cancel.raise_if_cancelled()
        ctx.progress(position - 1, total)

        if index is not None:
            try:
                duplicate_of = index.find(src)
            except OSError as exc:
                stats.failed += 1
                logger.write(tr("log_hash_failed", path=src, error=exc))
                continue
            if duplicate_of is not None:
                stats.skipped += 1
                logger.write(tr("log_duplicate_skip", path=src))
                if opts.mode in (MODE_MOVE, MODE_COPY_DELETE):
                    _remove_source(ctx, src)
                continue

        next_number += 1
        dest = ctx.work_dir / build_output_name(next_number, src.suffix.lower(), prefix)
        try:
            _transfer(ctx, src, dest)
            if index is not None:
                index.add(dest, hash_from=src)
            stats.added += 1
        except Exception as exc:
            stats.failed += 1
            logger.write(tr("log_process_failed", path=src, error=exc))
            if src.exists():  # never leave a half-written file behind
                try:
                    dest.unlink(missing_ok=True)
                except OSError:
                    pass
            if isinstance(exc, OSError) and exc.errno in _DISK_FULL:
                raise  # disk full: every remaining file would fail too; abort (safe mode discards staging)

    ctx.progress(total, total)
    stats.total_output = len(organize_output(ctx.work_dir, logger=logger, tr=tr))
