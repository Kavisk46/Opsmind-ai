from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    """The shape any storage backend must provide. Services depend on this,
    never on a concrete backend — swapping LocalStorage for an S3/MinIO
    implementation later means writing one new class, not touching
    DocumentService or the routes that use it.

    `key` is an opaque identifier from the caller's point of view, but by
    convention (see DocumentService.upload_document) it's a forward-slash
    path like "{owner_id}/{uuid}{ext}" — every implementation of this
    Protocol MUST treat `/` in a key as a hierarchy separator (a "folder"),
    not part of a literal filename, since that's what makes an S3/GCS
    implementation later a drop-in replacement: those services already
    treat key prefixes as folder-like namespaces natively, and a
    filesystem-backed implementation has to create the matching
    subdirectories itself to behave the same way.
    """

    def save(self, *, key: str, data: bytes) -> str: ...
    def open(self, *, key: str) -> bytes: ...
    def delete(self, *, key: str) -> None: ...


class LocalStorage:
    """Writes files to a directory on local disk. The right choice for a
    single-instance deployment; the wrong choice the moment you run more
    than one backend process (each would see a different disk) — that's
    the trigger for swapping in an S3-backed Storage later, not a rewrite.
    """

    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, *, key: str, data: bytes) -> str:
        path = self.base_dir / key
        # Keys are namespaced per owner ("{owner_id}/{uuid}{ext}" — see
        # this class's Storage Protocol docstring), so the parent directory
        # genuinely may not exist yet on a brand new owner's first upload.
        # exist_ok=True makes this safe to call unconditionally on every
        # save rather than checking "is this owner's first upload" first.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def open(self, *, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    def delete(self, *, key: str) -> None:
        (self.base_dir / key).unlink(missing_ok=True)
