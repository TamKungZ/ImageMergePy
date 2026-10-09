import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Callable

CHUNK_SIZE = 4 * 1024 * 1024


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    buffer = bytearray(CHUNK_SIZE)
    view = memoryview(buffer)
    with open(path, "rb", buffering=0) as file:
        while True:
            read = file.readinto(view)
            if not read:
                break
            digest.update(view[:read])
    return digest.hexdigest()


class DuplicateIndex:
    """Content-duplicate detection (same SHA-256 + same extension).

    Files are bucketed by (size, extension) first. A file is only hashed when
    another indexed file shares its bucket, so unique files never get read.
    Hashes are cached, and a freshly copied file can inherit its source's hash.
    """

    def __init__(self, on_error: Callable[[Path, Exception], None] | None = None):
        self._buckets: dict[tuple[int, str], list[Path]] = defaultdict(list)
        self._hashes: dict[Path, str] = {}
        self._broken: set[Path] = set()
        self._on_error = on_error

    @staticmethod
    def _key(path: Path) -> tuple[int, str]:
        return path.stat().st_size, path.suffix.lower()

    def _report(self, path: Path, exc: Exception) -> None:
        if path not in self._broken:
            self._broken.add(path)
            if self._on_error:
                self._on_error(path, exc)

    def _digest(self, path: Path) -> str:
        digest = self._hashes.get(path)
        if digest is None:
            digest = sha256_file(path)
            self._hashes[path] = digest
        return digest

    def add(self, path: Path, hash_from: Path | None = None) -> None:
        try:
            key = self._key(path)
        except OSError as exc:
            self._report(path, exc)
            return
        self._buckets[key].append(path)
        if hash_from is not None and hash_from in self._hashes:
            self._hashes[path] = self._hashes[hash_from]

    def find(self, path: Path) -> Path | None:
        """Return an indexed file identical to ``path`` or None.

        Raises OSError if ``path`` itself cannot be read.
        """
        bucket = self._buckets.get(self._key(path))
        if not bucket:
            return None
        digest = self._digest(path)
        for other in bucket:
            if other == path or other in self._broken:
                continue
            try:
                if self._digest(other) == digest:
                    return other
            except OSError as exc:
                self._report(other, exc)
        return None
