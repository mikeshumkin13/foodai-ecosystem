from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from typing import BinaryIO

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError


class FoodPhotoValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ProcessedFoodPhoto:
    image_format: str
    extension: str
    content_type: str
    width: int
    height: int
    uploaded_byte_size: int
    stored_bytes: bytes
    checksum_sha256: str

    @property
    def stored_byte_size(self) -> int:
        return len(self.stored_bytes)


FORMAT_CONFIG = {
    "JPEG": {"extension": "jpg", "content_type": "image/jpeg"},
    "PNG": {"extension": "png", "content_type": "image/png"},
}


def process_uploaded_food_photo(uploaded_file: UploadedFile) -> ProcessedFoodPhoto:
    uploaded_bytes = _read_limited_upload(
        uploaded_file,
        max_size_bytes=int(settings.FOOD_SCAN_MAX_UPLOAD_BYTES),
    )
    image = _open_verified_image(uploaded_bytes)
    image_format = str(image.format or "").upper()

    if image_format not in _allowed_formats():
        raise FoodPhotoValidationError("unsupported_image_format")
    if image_format not in FORMAT_CONFIG:
        raise FoodPhotoValidationError("unsupported_image_format")

    image = ImageOps.exif_transpose(image)
    image.load()
    _validate_pixel_count(image.width, image.height)

    stored_bytes = _strip_metadata_and_encode(image, image_format=image_format)
    config = FORMAT_CONFIG[image_format]
    return ProcessedFoodPhoto(
        image_format=image_format,
        extension=config["extension"],
        content_type=config["content_type"],
        width=image.width,
        height=image.height,
        uploaded_byte_size=len(uploaded_bytes),
        stored_bytes=stored_bytes,
        checksum_sha256=sha256(stored_bytes).hexdigest(),
    )


def _read_limited_upload(uploaded_file: UploadedFile, *, max_size_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total_size = 0
    for chunk in uploaded_file.chunks():
        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise FoodPhotoValidationError("file_too_large")
        chunks.append(chunk)

    if total_size == 0:
        raise FoodPhotoValidationError("empty_file")
    return b"".join(chunks)


def _allowed_formats() -> frozenset[str]:
    return frozenset(str(item).upper() for item in settings.FOOD_SCAN_ALLOWED_FORMATS)


def _open_verified_image(uploaded_bytes: bytes) -> Image.Image:
    try:
        with Image.open(BytesIO(uploaded_bytes)) as image:
            image.verify()
        return Image.open(BytesIO(uploaded_bytes))
    except (OSError, UnidentifiedImageError) as exc:
        raise FoodPhotoValidationError("invalid_image_file") from exc


def _validate_pixel_count(width: int, height: int) -> None:
    max_pixels = int(settings.FOOD_SCAN_MAX_IMAGE_PIXELS)
    if width * height > max_pixels:
        raise FoodPhotoValidationError("image_dimensions_too_large")


def _strip_metadata_and_encode(image: Image.Image, *, image_format: str) -> bytes:
    buffer = BytesIO()
    sanitized_image = _copy_pixels_without_info(image)

    if image_format == "JPEG":
        if sanitized_image.mode not in {"RGB", "L"}:
            sanitized_image = sanitized_image.convert("RGB")
        sanitized_image.save(buffer, format="JPEG", quality=95, optimize=True)
        return buffer.getvalue()

    if image_format == "PNG":
        sanitized_image.save(buffer, format="PNG", optimize=True)
        return buffer.getvalue()

    raise FoodPhotoValidationError("unsupported_image_format")


def _copy_pixels_without_info(image: Image.Image) -> Image.Image:
    sanitized_image = image.copy()
    sanitized_image.info.clear()
    return sanitized_image


def image_has_exif(image_file: BinaryIO) -> bool:
    with Image.open(image_file) as image:
        return bool(image.getexif())
