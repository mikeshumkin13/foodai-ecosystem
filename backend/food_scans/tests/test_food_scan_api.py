from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from accounts.tests.factories import make_user
from food_scans.image_processing import image_has_exif
from food_scans.models import FoodScan
from food_scans.storage import get_private_object_storage

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def food_scan_storage_settings(
    settings: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.FOOD_SCAN_ALLOWED_FORMATS = ("JPEG", "PNG")
    settings.FOOD_SCAN_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
    settings.FOOD_SCAN_MAX_IMAGE_PIXELS = 20_000_000
    settings.FOOD_SCAN_PRIVATE_STORAGE_BACKEND = "local"
    settings.FOOD_SCAN_PRIVATE_MEDIA_ROOT = str(tmp_path / "private")
    monkeypatch.setattr("food_scans.views.start_scan_analysis", lambda food_scan: food_scan)


def _food_scan_detail_url(food_scan_id: object) -> str:
    return reverse("food-scan-detail", kwargs={"id": food_scan_id})


def _image_upload(
    *,
    image_format: str,
    filename: str,
    content_type: str,
    with_exif: bool = False,
) -> SimpleUploadedFile:
    image = Image.new("RGB", (12, 10), color=(120, 30, 20))
    buffer = BytesIO()
    save_kwargs: dict[str, object] = {}
    if image_format == "JPEG" and with_exif:
        exif = Image.Exif()
        exif[271] = "FoodAI test camera"
        save_kwargs["exif"] = exif
    image.save(buffer, format=image_format, **save_kwargs)
    return SimpleUploadedFile(filename, buffer.getvalue(), content_type=content_type)


def test_user_can_upload_valid_jpeg_and_exif_is_stripped(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="JPEG",
                filename="../../unsafe-name.jpeg",
                content_type="image/jpeg",
                with_exif=True,
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["user_id"] == str(user.id)
    assert payload["image_format"] == FoodScan.ImageFormat.JPEG
    assert payload["content_type"] == "image/jpeg"
    assert payload["width"] == 12
    assert payload["height"] == 10
    assert payload["exif_stripped"] is True
    assert "object_key" not in payload
    assert "url" not in payload

    food_scan = FoodScan.objects.get(id=payload["id"])
    assert food_scan.object_key.startswith("food-scans/")
    assert food_scan.object_key.endswith(".jpg")
    assert ".." not in food_scan.object_key
    assert "unsafe-name" not in food_scan.object_key

    storage = get_private_object_storage()
    assert storage.exists(food_scan.object_key) is True
    with storage.open_binary(food_scan.object_key) as stored_image:
        assert image_has_exif(stored_image) is False


def test_user_can_upload_valid_png_even_when_filename_and_content_type_lie(
    api_client: APIClient,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="PNG",
                filename="meal.jpg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["image_format"] == FoodScan.ImageFormat.PNG
    assert payload["content_type"] == "image/png"

    food_scan = FoodScan.objects.get(id=payload["id"])
    assert food_scan.object_key.endswith(".png")


def test_upload_initiates_scan_analysis(
    api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)
    analyzed_scan_ids: list[str] = []

    def fake_start_scan_analysis(food_scan: FoodScan) -> FoodScan:
        analyzed_scan_ids.append(str(food_scan.id))
        food_scan.status = FoodScan.Status.NEEDS_CONFIRMATION
        food_scan.save(update_fields=["status", "updated_at"])
        return food_scan

    monkeypatch.setattr("food_scans.views.start_scan_analysis", fake_start_scan_analysis)

    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="JPEG",
                filename="meal.jpg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_201_CREATED
    payload = response.json()
    assert payload["status"] == FoodScan.Status.NEEDS_CONFIRMATION
    assert analyzed_scan_ids == [payload["id"]]


def test_fake_jpeg_is_rejected(api_client: APIClient) -> None:
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": SimpleUploadedFile(
                "fake.jpg",
                b"\xff\xd8not-a-real-jpeg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["photo"] == ["invalid_image_file"]
    assert FoodScan.objects.count() == 0


def test_oversized_file_is_rejected(api_client: APIClient, settings: Any) -> None:
    settings.FOOD_SCAN_MAX_UPLOAD_BYTES = 100
    user = make_user()
    api_client.force_authenticate(user=user)

    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="JPEG",
                filename="large.jpg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["photo"] == ["file_too_large"]
    assert FoodScan.objects.count() == 0


def test_upload_requires_authentication(api_client: APIClient) -> None:
    response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="JPEG",
                filename="meal.jpg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert FoodScan.objects.count() == 0


def test_user_cannot_access_another_users_food_scan(api_client: APIClient) -> None:
    user_a = make_user()
    user_b = make_user()
    api_client.force_authenticate(user=user_a)
    create_response = api_client.post(
        reverse("food-scan-list"),
        {
            "photo": _image_upload(
                image_format="JPEG",
                filename="meal.jpg",
                content_type="image/jpeg",
            )
        },
        format="multipart",
    )
    food_scan_id = create_response.json()["id"]

    api_client.force_authenticate(user=user_b)
    detail_response = api_client.get(_food_scan_detail_url(food_scan_id))
    list_response = api_client.get(reverse("food-scan-list"))

    assert detail_response.status_code == status.HTTP_404_NOT_FOUND
    assert list_response.status_code == status.HTTP_200_OK
    assert list_response.json() == []
