"""Inside-folder pipeline: re-index (and optionally de-duplicate) media in place."""
from .fileops import safe_delete_file
from .hashing import DuplicateIndex
from .media_ordering import organize_output
from .models import JobContext


def run_inside(ctx: JobContext) -> None:
    opts, stats, logger, tr = ctx.options, ctx.stats, ctx.logger, ctx.tr

    if opts.remove_duplicates_in_place and not opts.allow_duplicate_files:
        ordered = organize_output(
            ctx.work_dir, logger=logger, tr=tr, minimal_rename=True, sort_by_file_mtime=True
        )
        index = DuplicateIndex(
            on_error=lambda path, exc: logger.write(
                tr("log_skip_unreadable_output", path=path, error=exc)
            )
        )
        total = len(ordered)
        for position, file_path in enumerate(ordered, start=1):
            ctx.cancel.raise_if_cancelled()
            ctx.progress(position - 1, total)
            try:
                duplicate_of = index.find(file_path)
            except OSError as exc:
                stats.failed += 1
                logger.write(tr("log_hash_failed", path=file_path, error=exc))
                continue
            if duplicate_of is not None:
                if safe_delete_file(file_path, logger, tr):
                    stats.deleted_sources += 1
                stats.skipped += 1
                continue
            index.add(file_path)
        ctx.progress(total, total)

    final_files = organize_output(
        ctx.work_dir, logger=logger, tr=tr, minimal_rename=True, sort_by_file_mtime=True
    )
    stats.total_output = len(final_files)
