from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Protocol

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation


class PrivateObjectStorage(Protocol):
    @property
    def backend_name(self) -> str: ...

    def save(self, object_key: str, content: bytes) -> None: ...

    def open_binary(self, object_key: str) -> BinaryIO: ...

    def exists(self, object_key: str) -> bool: ...

    def delete(self, object_key: str) -> None: ...


@dataclass(frozen=True)
class LocalPrivateObjectStorage:
    root: Path
    backend_name: str = "local"

    def save(self, object_key: str, content: bytes) -> None:
        target_path = self._path_for_key(object_key)
        target_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        file_descriptor = os.open(target_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(file_descriptor, "wb") as stored_file:
            stored_file.write(content)

    def open_binary(self, object_key: str) -> BinaryIO:
        return self._path_for_key(object_key).open("rb")

    def exists(self, object_key: str) -> bool:
        return self._path_for_key(object_key).exists()

    def delete(self, object_key: str) -> None:
        self._path_for_key(object_key).unlink(missing_ok=True)

    def _path_for_key(self, object_key: str) -> Path:
        key_path = validate_object_key(object_key)
        root = self.root.resolve()
        resolved_path = root.joinpath(*key_path.parts).resolve()
        try:
            resolved_path.relative_to(root)
        except ValueError as exc:
            raise SuspiciousFileOperation("invalid_private_object_key") from exc
        return resolved_path


def get_private_object_storage() -> PrivateObjectStorage:
    backend = str(settings.FOOD_SCAN_PRIVATE_STORAGE_BACKEND).strip().lower()
    if backend == "local":
        return LocalPrivateObjectStorage(root=Path(settings.FOOD_SCAN_PRIVATE_MEDIA_ROOT))

    msg = (
        f"Unsupported FOOD_SCAN_PRIVATE_STORAGE_BACKEND={backend!r}. "
        "Only local private storage is implemented in MVP; S3-compatible storage must use "
        "the same PrivateObjectStorage interface."
    )
    raise ImproperlyConfigured(msg)


def validate_object_key(object_key: str) -> PurePosixPath:
    if "\\" in object_key:
        raise SuspiciousFileOperation("invalid_private_object_key")

    key_path = PurePosixPath(object_key)
    if key_path.is_absolute() or not key_path.parts:
        raise SuspiciousFileOperation("invalid_private_object_key")
    if any(part in {"", ".", ".."} for part in key_path.parts):
        raise SuspiciousFileOperation("invalid_private_object_key")
    return key_path
