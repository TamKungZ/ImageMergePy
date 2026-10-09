"""Plain data objects shared by the pipeline, the CLI and the UI (no Qt)."""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .i18n import t_identity

ProgressFn = Callable[[int, int], None]


@dataclass
class SourceFolder:
    path: Path
    prefix: str = ""


@dataclass
class ProcessOptions:
    mode: str
    output_dir: Path
    inputs: list[SourceFolder] = field(default_factory=list)
    clear_output_first: bool = False
    remove_duplicates_in_place: bool = False
    allow_duplicate_files: bool = False
    use_safe_temp_workspace: bool = True


@dataclass
class ProcessStats:
    added: int = 0
    skipped: int = 0
    moved: int = 0
    copied: int = 0
    deleted_sources: int = 0
    failed: int = 0
    total_output: int = 0
    cancelled: bool = False


class OperationCancelled(Exception):
    """Raised inside the pipeline when the user cancelled the job."""


class CancelToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self._event.is_set():
            raise OperationCancelled()


class Logger:
    def __init__(self, writer: Callable[[str], None]):
        self.writer = writer

    def write(self, text: str) -> None:
        self.writer(text)


@dataclass
class JobContext:
    """Everything one pipeline run needs, passed to merger / inside_organizer."""

    options: ProcessOptions
    work_dir: Path  # folder that is actually modified (workspace copy or the real output)
    logger: Logger
    tr: Callable[..., str] = t_identity
    cancel: CancelToken = field(default_factory=CancelToken)
    progress: ProgressFn = lambda done, total: None
    stats: ProcessStats = field(default_factory=ProcessStats)
    defer_deletes: bool = False  # safe mode: delete sources only after the commit
    pending_deletes: list[Path] = field(default_factory=list)
    scan_folders: list[SourceFolder] = field(default_factory=list)
