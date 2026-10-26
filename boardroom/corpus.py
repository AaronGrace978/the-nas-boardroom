"""Read an authorized folder. Symlinks are ignored. Hashes are exact."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from boardroom.models import FileRec

DOC_EXT = {".txt", ".md", ".markdown", ".text"}
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp", ".tif", ".tiff"}
_TEXT_LIMIT = 200_000


def kind_of(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in PHOTO_EXT:
        return "photo"
    if extension in DOC_EXT:
        return "document"
    return "other"


def scan(root: Path) -> tuple[FileRec, ...]:
    """Inventory `root`. Paths are relative and POSIX-style."""
    base = root.resolve()
    records: list[FileRec] = []
    for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
        dirnames[:] = [
            name
            for name in dirnames
            if not name.startswith(".") and not (Path(dirpath) / name).is_symlink()
        ]
        for name in sorted(filenames):
            if name.startswith("."):
                continue
            path = Path(dirpath) / name
            if path.is_symlink() or not path.is_file():
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(base)
            except (OSError, ValueError):
                continue
            try:
                stat = path.stat()
                digest = _hash(path)
                kind = kind_of(path)
                header = _sniff(path)
                text = _read_text(path) if kind == "document" and stat.st_size <= _TEXT_LIMIT else None
            except OSError:
                continue
            records.append(
                FileRec(
                    rel_path=path.relative_to(base).as_posix(),
                    size=stat.st_size,
                    mtime=stat.st_mtime,
                    sha256=digest,
                    kind=kind,
                    header=header,
                    text=text,
                )
            )
    records.sort(key=lambda item: item.rel_path.lower())
    return tuple(records)


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sniff(path: Path) -> str:
    with path.open("rb") as handle:
        head = handle.read(8)
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if b"\x00" in head:
        return "binary"
    return "text"


def _read_text(path: Path) -> str | None:
    data = path.read_bytes()
    if b"\x00" in data[:1024]:
        return None
    return data.decode("utf-8", errors="replace")
