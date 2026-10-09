from abc import ABC, abstractmethod
from pathlib import Path


class StorageError(Exception):
    pass


class StorageService(ABC):
    """Replaceable storage backend. LocalStorageService implements this for
    local development; an S3-backed implementation can be dropped in later
    without touching any caller."""

    @abstractmethod
    def save(self, key: str, content: bytes) -> str: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...


class LocalStorageService(StorageService):
    def __init__(self, root_dir: str) -> None:
        self.root = Path(root_dir).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if not candidate.is_relative_to(self.root):
            raise StorageError(f"storage key escapes storage root: {key!r}")
        return candidate

    def save(self, key: str, content: bytes) -> str:
        path = self._resolve_safe_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_bytes(content)
        except OSError as exc:
            raise StorageError(f"failed to write {key!r}: {exc}") from exc
        return key

    def get(self, key: str) -> bytes:
        path = self._resolve_safe_path(key)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise StorageError(f"failed to read {key!r}: {exc}") from exc

    def exists(self, key: str) -> bool:
        try:
            path = self._resolve_safe_path(key)
        except StorageError:
            return False
        return path.is_file()
