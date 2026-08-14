from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from celery.exceptions import Retry
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tests.factories import make_user
from diary.models import Meal, MealItem
from food_scans.jobs import enqueue_food_scan_analysis
from food_scans.models import FoodScan
from food_scans.orchestration import add_manual_detected_item
from food_scans.tasks import process_food_scan_analysis_task
from integrations.vision.client import VisionAnalyzeResult, VisionDetectedItem, VisionTimeoutError
from nutrition.models import FoodItem, FoodNutrient, Nutrient
from nutrition.tests.factories import make_food_category, make_food_data_source, make_food_item

pytestmark = pytest.mark.django_db


def _retry_url(food_scan_id: object) -> str:
    return reverse("food-scan-retry", kwargs={"id": food_scan_id})


def _results_url(food_scan_id: object) -> str:
    return reverse("food-scan-results", kwargs={"id": food_scan_id})


def _confirm_url(food_scan_id: object) -> str:
    return reverse("food-scan-confirm", kwargs={"id": food_scan_id})


def test_enqueue_food_scan_analysis_sets_idempotency_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    food_scan = _make_food_scan()
    scheduled_tasks: list[dict[str, object]] = []

    def fake_apply_async(*, args: list[str], task_id: str) -> None:
        scheduled_tasks.append({"args": args, "task_id": task_id})

    monkeypatch.setattr(
        "food_scans.jobs.process_food_scan_analysis_task.apply_async",
        fake_apply_async,
    )

    enqueued_scan = enqueue_food_scan_analysis(food_scan=food_scan)

    assert enqueued_scan.status == FoodScan.Status.UPLOADED
    assert enqueued_scan.failure_code == ""
    assert enqueued_scan.analysis_run_id is not None
    assert enqueued_scan.analysis_attempt_count == 0
    assert scheduled_tasks == [
        {
            "args": [str(food_scan.id), str(enqueued_scan.analysis_run_id)],
            "task_id": enqueued_scan.analysis_task_id,
        }
    ]
    assert food_scan.object_key not in str(scheduled_tasks)


def test_retry_endpoint_requeues_failed_scan_and_clears_failure(
    api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.FAILED)
    food_scan.failure_code = "vision_timeout"
    food_scan.save(update_fields=["failure_code", "updated_at"])
    scheduled_tasks: list[dict[str, object]] = []

    def fake_apply_async(*, args: list[str], task_id: str) -> None:
        scheduled_tasks.append({"args": args, "task_id": task_id})

    monkeypatch.setattr(
        "food_scans.jobs.process_food_scan_analysis_task.apply_async",
        fake_apply_async,
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(_retry_url(food_scan.id), {}, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["scan_id"] == str(food_scan.id)
    assert payload["status"] == FoodScan.Status.UPLOADED

    food_scan.refresh_from_db()
    assert food_scan.failure_code == ""
    assert food_scan.analysis_run_id is not None
    assert food_scan.analysis_attempt_count == 0
    assert len(scheduled_tasks) == 1


def test_retry_hides_previous_detected_items_while_new_analysis_is_pending(
    api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.NEEDS_CONFIRMATION)
    add_manual_detected_item(
        food_scan=food_scan,
        matched_food=rice,
        mass_g=Decimal("100.00"),
        label="rice",
    )

    def fake_apply_async(*, args: list[str], task_id: str) -> None:
        return None

    monkeypatch.setattr(
        "food_scans.jobs.process_food_scan_analysis_task.apply_async",
        fake_apply_async,
    )
    api_client.force_authenticate(user=user)

    retry_response = api_client.post(_retry_url(food_scan.id), {}, format="json")
    results_response = api_client.get(_results_url(food_scan.id))

    assert retry_response.status_code == status.HTTP_202_ACCEPTED
    assert results_response.status_code == status.HTTP_200_OK
    assert results_response.json()["status"] == FoodScan.Status.UPLOADED
    assert results_response.json()["detected_items"] == []


def test_retry_endpoint_does_not_enqueue_duplicate_when_scan_is_processing(
    api_client: APIClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = make_user()
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.PROCESSING)

    def fail_apply_async(*args: object, **kwargs: object) -> None:
        raise AssertionError("processing scan must not enqueue a duplicate task")

    monkeypatch.setattr(
        "food_scans.jobs.process_food_scan_analysis_task.apply_async",
        fail_apply_async,
    )
    api_client.force_authenticate(user=user)

    response = api_client.post(_retry_url(food_scan.id), {}, format="json")

    assert response.status_code == status.HTTP_202_ACCEPTED
    assert response.json() == {"scan_id": str(food_scan.id), "status": FoodScan.Status.PROCESSING}


def test_retry_endpoint_rejects_confirmed_scan(api_client: APIClient) -> None:
    user = make_user()
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.CONFIRMED)
    api_client.force_authenticate(user=user)

    response = api_client.post(_retry_url(food_scan.id), {}, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == ["confirmed_scan_cannot_be_reprocessed"]


def test_food_scan_analysis_task_processes_current_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    run_id = uuid.uuid4()
    task_id = f"food-scan-analysis-test-{run_id}"
    food_scan = _make_food_scan(analysis_run_id=run_id, analysis_task_id=task_id)

    def fake_analyze_food_scan(*args: object, **kwargs: object) -> VisionAnalyzeResult:
        return VisionAnalyzeResult(items=(VisionDetectedItem(label="rice", confidence=0.92),))

    monkeypatch.setattr("food_scans.orchestration.analyze_food_scan", fake_analyze_food_scan)

    result = process_food_scan_analysis_task.apply(
        args=[str(food_scan.id), str(run_id)],
        task_id=task_id,
    ).get()

    food_scan.refresh_from_db()
    assert result == {"status": FoodScan.Status.NEEDS_CONFIRMATION, "scan_id": str(food_scan.id)}
    assert food_scan.status == FoodScan.Status.NEEDS_CONFIRMATION
    assert food_scan.failure_code == ""
    assert food_scan.analysis_attempt_count == 1
    detected_item = food_scan.detected_items.get()
    assert detected_item.matched_food == rice
    assert detected_item.estimated_mass_g == Decimal("144.00")
    assert detected_item.calories_kcal == Decimal("187.2000")


def test_food_scan_analysis_task_skips_stale_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_run_id = uuid.uuid4()
    current_run_id = uuid.uuid4()
    food_scan = _make_food_scan(analysis_run_id=current_run_id)

    def fail_analyze_food_scan(*args: object, **kwargs: object) -> VisionAnalyzeResult:
        raise AssertionError("stale task must not call Vision")

    monkeypatch.setattr("food_scans.orchestration.analyze_food_scan", fail_analyze_food_scan)

    result = process_food_scan_analysis_task.apply(
        args=[str(food_scan.id), str(old_run_id)],
        task_id=f"food-scan-analysis-test-{old_run_id}",
    ).get()

    food_scan.refresh_from_db()
    assert result == {"status": "skipped", "reason": "stale_or_confirmed_scan"}
    assert food_scan.status == FoodScan.Status.UPLOADED
    assert food_scan.analysis_run_id == current_run_id
    assert food_scan.detected_items.count() == 0


def test_food_scan_analysis_task_retries_transient_timeout(
    settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES = 2
    settings.FOOD_SCAN_ANALYSIS_RETRY_BACKOFF_SECONDS = 3
    run_id = uuid.uuid4()
    task_id = f"food-scan-analysis-test-{run_id}"
    food_scan = _make_food_scan(analysis_run_id=run_id, analysis_task_id=task_id)

    def fake_analyze_food_scan(*args: object, **kwargs: object) -> VisionAnalyzeResult:
        raise VisionTimeoutError

    monkeypatch.setattr("food_scans.orchestration.analyze_food_scan", fake_analyze_food_scan)

    with pytest.raises(Retry) as exc_info:
        process_food_scan_analysis_task.apply(
            args=[str(food_scan.id), str(run_id)],
            task_id=task_id,
            throw=True,
        )

    food_scan.refresh_from_db()
    assert exc_info.value.when == 3
    assert food_scan.status == FoodScan.Status.PROCESSING
    assert food_scan.failure_code == ""
    assert food_scan.analysis_attempt_count == 1


def test_food_scan_analysis_task_marks_scan_failed_after_max_retries(
    settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES = 1
    run_id = uuid.uuid4()
    task_id = f"food-scan-analysis-test-{run_id}"
    food_scan = _make_food_scan(analysis_run_id=run_id, analysis_task_id=task_id)

    def fake_analyze_food_scan(*args: object, **kwargs: object) -> VisionAnalyzeResult:
        raise VisionTimeoutError

    monkeypatch.setattr("food_scans.orchestration.analyze_food_scan", fake_analyze_food_scan)

    result = process_food_scan_analysis_task.apply(
        args=[str(food_scan.id), str(run_id)],
        task_id=task_id,
        retries=1,
    ).get()

    food_scan.refresh_from_db()
    assert result == {
        "status": FoodScan.Status.FAILED,
        "scan_id": str(food_scan.id),
        "failure_code": "vision_timeout",
    }
    assert food_scan.status == FoodScan.Status.FAILED
    assert food_scan.failure_code == "vision_timeout"
    assert food_scan.analysis_attempt_count == 2


def test_scan_confirmation_remains_idempotent_and_does_not_duplicate_meal_items(
    api_client: APIClient,
) -> None:
    user = make_user()
    rice = _food_with_nutrients(name="Rice, cooked", synonyms=["rice"], energy="130.0000")
    food_scan = _make_food_scan(user=user, status=FoodScan.Status.NEEDS_CONFIRMATION)
    add_manual_detected_item(
        food_scan=food_scan,
        matched_food=rice,
        mass_g=Decimal("100.00"),
        label="rice",
    )
    api_client.force_authenticate(user=user)

    first_response = api_client.post(
        _confirm_url(food_scan.id),
        {"meal_type": Meal.MealType.LUNCH, "logged_at": "2026-08-14T12:30:00Z"},
        format="json",
    )
    second_response = api_client.post(
        _confirm_url(food_scan.id),
        {"meal_type": Meal.MealType.LUNCH, "logged_at": "2026-08-14T12:30:00Z"},
        format="json",
    )

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_200_OK
    assert first_response.json()["meal"]["id"] == second_response.json()["meal"]["id"]
    assert Meal.objects.count() == 1
    assert MealItem.objects.count() == 1


def _make_food_scan(
    *,
    user: User | None = None,
    status: str = FoodScan.Status.UPLOADED,
    analysis_run_id: uuid.UUID | None = None,
    analysis_task_id: str = "",
) -> FoodScan:
    scan_id = uuid.uuid4()
    return FoodScan.objects.create(
        id=scan_id,
        user=user or make_user(),
        status=status,
        storage_backend="local",
        object_key=f"food-scans/test/{scan_id.hex}.jpg",
        image_format=FoodScan.ImageFormat.JPEG,
        content_type="image/jpeg",
        uploaded_byte_size=128,
        stored_byte_size=120,
        width=12,
        height=10,
        checksum_sha256="b" * 64,
        analysis_run_id=analysis_run_id,
        analysis_task_id=analysis_task_id,
    )


def _food_with_nutrients(
    *,
    name: str,
    synonyms: list[str],
    energy: str,
    protein: str = "2.7000",
    fat: str = "0.3000",
    carbs: str = "28.0000",
) -> FoodItem:
    suffix = uuid.uuid4().hex[:8]
    category = make_food_category(slug=f"category-{suffix}", name=f"{name} category")
    data_source = make_food_data_source(code=f"source-{suffix}")
    food_item = make_food_item(
        category=category,
        data_source=data_source,
        name=name,
        name_ru="",
        name_en=name,
        synonyms=synonyms,
        source_reference=f"{name} demo values per 100 g",
    )
    _make_food_nutrient(food_item, code="energy_kcal", amount=energy)
    _make_food_nutrient(food_item, code="protein", amount=protein)
    _make_food_nutrient(food_item, code="fat", amount=fat)
    _make_food_nutrient(food_item, code="carbohydrate", amount=carbs)
    return food_item


def _make_food_nutrient(food_item: FoodItem, *, code: str, amount: str) -> None:
    nutrient = _get_or_create_nutrient(code)
    FoodNutrient.objects.create(
        food_item=food_item,
        nutrient=nutrient,
        amount_per_100g=Decimal(amount),
        source_reference="Demo values per 100 g",
    )


def _get_or_create_nutrient(code: str) -> Nutrient:
    nutrient_defaults = {
        "energy_kcal": {
            "name": "Energy",
            "name_ru": "Энергия",
            "name_en": "Energy",
            "unit": "kcal",
            "nutrient_type": Nutrient.NutrientType.ENERGY,
        },
        "protein": {
            "name": "Protein",
            "name_ru": "Белки",
            "name_en": "Protein",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
        "fat": {
            "name": "Fat",
            "name_ru": "Жиры",
            "name_en": "Fat",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
        "carbohydrate": {
            "name": "Carbohydrate",
            "name_ru": "Углеводы",
            "name_en": "Carbohydrate",
            "unit": "g",
            "nutrient_type": Nutrient.NutrientType.MACRONUTRIENT,
        },
    }
    return Nutrient.objects.get_or_create(code=code, defaults=nutrient_defaults[code])[0]
