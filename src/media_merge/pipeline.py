"""Orchestrates one job: validation -> (safe workspace) -> merge / organize -> summary."""
from pathlib import Path

from .constants import ALL_MODES, MODE_INSIDE_FOLDER, MODE_MAIN_FOLDER, ORGANIZER_MODES
from .fileops import remove_media_files, safe_delete_file
from .i18n import t_identity
from .inside_organizer import run_inside
from .media_ordering import normalize_prefix
from .merger import run_merge
from .models import (
    CancelToken,
    JobContext,
    Logger,
    OperationCancelled,
    ProcessOptions,
    ProcessStats,
    ProgressFn,
    SourceFolder,
)
from .workspace import SafeWorkspace


def validate_options(options: ProcessOptions, tr=t_identity) -> None:
    if options.mode not in ALL_MODES:
        raise ValueError(tr("error_unknown_mode", mode=options.mode))
    if options.mode in ORGANIZER_MODES:
        return
    if not options.inputs:
        raise ValueError(tr("error_no_input"))
    output = options.output_dir.resolve()
    for folder in options.inputs:
        source = folder.path.resolve()
        if source == output:
            raise ValueError(tr("error_output_same_as_input"))
        # An output inside an input would be re-scanned, and in move/copy_delete mode
        # the freshly written files would be deleted as "duplicates of themselves".
        if source in output.parents:
            raise ValueError(tr("error_output_inside_input"))


def _scan_folders(options: ProcessOptions) -> list[SourceFolder]:
    if options.mode == MODE_INSIDE_FOLDER:
        return []
    if options.mode == MODE_MAIN_FOLDER:
        output = options.output_dir.resolve()
        seen: set[Path] = {output}
        folders: list[SourceFolder] = []
        for folder in options.inputs:
            resolved = folder.path.resolve()
            if resolved not in seen:
                seen.add(resolved)
                folders.append(folder)
        return folders
    return list(options.inputs)


def _execute(ctx: JobContext) -> None:
    opts, logger, tr = ctx.options, ctx.logger, ctx.tr
    logger.write(tr("log_start"))
    logger.write(tr("log_mode", mode=opts.mode))
    logger.write(tr("log_output_dir", output=opts.output_dir))

    ctx.scan_folders = _scan_folders(opts)
    for folder in ctx.scan_folders:
        logger.write(
            tr("log_input_entry", input_path=folder.path, prefix=normalize_prefix(folder.prefix) or "-")
        )

    if opts.clear_output_first:
        logger.write(tr("log_clearing_output"))
        logger.write(tr("log_cleared_output", count=remove_media_files(ctx.work_dir)))
    ctx.cancel.raise_if_cancelled()

    if opts.mode == MODE_INSIDE_FOLDER:
        run_inside(ctx)
    else:
        run_merge(ctx)


def _delete_pending_sources(ctx: JobContext) -> None:
    for path in dict.fromkeys(ctx.pending_deletes):  # unique, order preserved
        if safe_delete_file(path, ctx.logger, ctx.tr):
            ctx.stats.deleted_sources += 1


def _log_summary(logger: Logger, tr, stats: ProcessStats) -> None:
    logger.write("=" * 50)
    logger.write(tr("log_added", count=stats.added))
    logger.write(tr("log_skipped", count=stats.skipped))
    logger.write(tr("log_moved_count", count=stats.moved))
    logger.write(tr("log_copied_count", count=stats.copied))
    logger.write(tr("log_deleted_sources", count=stats.deleted_sources))
    logger.write(tr("log_failed", count=stats.failed))
    logger.write(tr("log_total_output", count=stats.total_output))
    logger.write(tr("log_done"))


def process_media(
    options: ProcessOptions,
    logger: Logger,
    tr=t_identity,
    cancel: CancelToken | None = None,
    progress: ProgressFn | None = None,
) -> ProcessStats:
    validate_options(options, tr)
    options.output_dir.mkdir(parents=True, exist_ok=True)

    stats = ProcessStats()
    common = dict(
        options=options,
        logger=logger,
        tr=tr,
        cancel=cancel or CancelToken(),
        progress=progress or (lambda done, total: None),
        stats=stats,
    )
    try:
        if options.use_safe_temp_workspace:
            with SafeWorkspace(options.output_dir) as workspace:
                logger.write(f"Safe workspace: {workspace.session_dir}")
                ctx = JobContext(work_dir=workspace.work_dir, defer_deletes=True, **common)
                _execute(ctx)
                ctx.cancel.raise_if_cancelled()
                workspace.commit()
                _delete_pending_sources(ctx)
        else:
            ctx = JobContext(work_dir=options.output_dir, **common)
            _execute(ctx)
    except OperationCancelled:
        stats.cancelled = True
        logger.write(
            tr("log_cancelled_safe" if options.use_safe_temp_workspace else "log_cancelled_partial")
        )
        return stats

    _log_summary(logger, tr, stats)
    return stats
