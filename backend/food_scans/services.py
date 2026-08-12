from __future__ import annotations

import uuid
from typing import cast

from django.core.files.uploadedfile import UploadedFile

from accounts.models import User
from food_scans.image_processing import ProcessedFoodPhoto, process_uploaded_food_photo
from food_scans.models import FoodScan
from food_scans.storage import get_private_object_storage


def create_food_scan(*, user: User, uploaded_file: UploadedFile) -> FoodScan:
    processed_photo = process_uploaded_food_photo(uploaded_file)
    scan_id = uuid.uuid4()
    object_key = _build_food_scan_object_key(scan_id=scan_id, processed_photo=processed_photo)
    storage = get_private_object_storage()

    storage.save(object_key, processed_photo.stored_bytes)
    try:
        return FoodScan.objects.create(
            id=scan_id,
            user=user,
            status=FoodScan.Status.UPLOADED,
            storage_backend=storage.backend_name,
            object_key=object_key,
            image_format=cast(FoodScan.ImageFormat, processed_photo.image_format),
            content_type=processed_photo.content_type,
            uploaded_byte_size=processed_photo.uploaded_byte_size,
            stored_byte_size=processed_photo.stored_byte_size,
            width=processed_photo.width,
            height=processed_photo.height,
            checksum_sha256=processed_photo.checksum_sha256,
            exif_stripped=True,
        )
    except Exception:
        storage.delete(object_key)
        raise


def _build_food_scan_object_key(*, scan_id: uuid.UUID, processed_photo: ProcessedFoodPhoto) -> str:
    scan_token = scan_id.hex
    return f"food-scans/{scan_token[:2]}/{scan_token}.{processed_photo.extension}"
