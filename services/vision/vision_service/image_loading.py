from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path
from typing import cast

from PIL import Image, UnidentifiedImageError

from vision_service.config import get_env_path
from vision_service.schemas import InternalObjectReference

CONTENT_TYPE_FORMATS = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
}


class VisionImageLoadError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def load_prepared_image(object_reference: InternalObjectReference) -> Image.Image:
    if object_reference.storage_backend != "local":
        raise VisionImageLoadError("unsupported_storage_backend")

    image_path = _resolve_private_object_path(
        root=_local_private_media_root(),
        object_key=object_reference.object_key,
    )

    try:
        image_bytes = image_path.read_bytes()
    except OSError as exc:
        raise VisionImageLoadError("image_object_not_found") from exc

    checksum = hashlib.sha256(image_bytes).hexdigest()
    if checksum != object_reference.checksum_sha256:
        raise VisionImageLoadError("image_checksum_mismatch")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            actual_format = image.format
            expected_format = CONTENT_TYPE_FORMATS[object_reference.content_type]
            if actual_format != expected_format:
                raise VisionImageLoadError("image_format_mismatch")
            return cast(Image.Image, image.convert("RGB"))
    except UnidentifiedImageError as exc:
        raise VisionImageLoadError("invalid_image_object") from exc


def _resolve_private_object_path(*, root: Path, object_key: str) -> Path:
    resolved_root = root.resolve()
    resolved_path = (resolved_root / object_key).resolve()
    if not resolved_path.is_relative_to(resolved_root):
        raise VisionImageLoadError("unsafe_object_key")
    return resolved_path


def _local_private_media_root() -> Path:
    return get_env_path("VISION_LOCAL_PRIVATE_MEDIA_ROOT", default="/app/local_uploads/private")
