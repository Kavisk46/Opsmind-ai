from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    """The shape any storage backend must provide. Services depend on this,
    never on a concrete backend — swapping LocalStorage for an S3/MinIO
    implementation later means writing one new class, not touching
    DocumentService or the routes that use it.
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
        path.write_bytes(data)
        return str(path)

    def open(self, *, key: str) -> bytes:
        return (self.base_dir / key).read_bytes()

    def delete(self, *, key: str) -> None:
        (self.base_dir / key).unlink(missing_ok=True)
