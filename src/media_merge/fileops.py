import os
import shutil
from pathlib import Path

from .i18n import t_identity
from .media_ordering import is_media_file
from .models import Logger


def safe_delete_file(path: Path, logger: Logger | None = None, tr=t_identity) -> bool:
    try:
        if path.exists():
            path.unlink()
            if logger:
                logger.write(tr("log_source_deleted", path=path))
            return True
    except OSError as exc:
        if logger:
            logger.write(tr("log_source_delete_failed", path=path, error=exc))
    return False


def remove_media_files(directory: Path) -> int:
    removed = 0
    for path in list(directory.iterdir()):
        if is_media_file(path):
            path.unlink()
            removed += 1
    return removed


def link_or_copy(src: Path, dst: Path) -> None:
    """Stage a file without duplicating its bytes when the filesystem allows it."""
    try:
        os.link(src, dst)
    except (OSError, NotImplementedError):
        shutil.copy2(src, dst)
