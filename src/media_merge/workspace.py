import os
import shutil
import uuid
from pathlib import Path

from .constants import TEMP_ROOT_NAME
from .fileops import link_or_copy
from .media_ordering import is_media_file


class SafeWorkspace:
    """Stage all changes in a temp folder and apply them only on ``commit()``.

    Leaving the ``with`` block without committing (error, cancel, Ctrl+C) simply
    discards the staging folder, so the real output folder is never half-written.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.session_dir: Path | None = None
        self.work_dir: Path | None = None

    def __enter__(self) -> "SafeWorkspace":
        self.session_dir = self.output_dir / TEMP_ROOT_NAME / f"session-{uuid.uuid4().hex}"
        self.work_dir = self.session_dir / "output"
        self.work_dir.mkdir(parents=True, exist_ok=True)
        for path in self.output_dir.iterdir():
            if is_media_file(path):
                link_or_copy(path, self.work_dir / path.name)
        return self

    def commit(self) -> None:
        assert self.work_dir is not None
        kept: set[str] = set()
        for path in self.work_dir.iterdir():
            if not is_media_file(path):
                continue
            target = self.output_dir / path.name
            try:
                os.replace(path, target)
            except OSError:
                shutil.move(str(path), str(target))
            kept.add(path.name.casefold())
        for path in self.output_dir.iterdir():
            if is_media_file(path) and path.name.casefold() not in kept:
                path.unlink()

    def __exit__(self, exc_type, exc, tb) -> bool:
        if self.session_dir is not None:
            shutil.rmtree(self.session_dir, ignore_errors=True)
            try:
                self.session_dir.parent.rmdir()  # only succeeds when no other session is left
            except OSError:
                pass
        return False
