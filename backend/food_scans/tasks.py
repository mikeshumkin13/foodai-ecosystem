from __future__ import annotations

import logging
import uuid
from typing import Any, cast

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from food_scans.models import FoodScan
from food_scans.orchestration import RetryableFoodScanAnalysisError, process_scan_analysis

logger = logging.getLogger(__name__)

SCAN_TASK_FAILURE_CODE = "scan_task_failed"


@shared_task(bind=True, name="food_scans.process_food_scan_analysis")
def process_food_scan_analysis_task(
    self: Any,
    food_scan_id: str,
    analysis_run_id: str,
) -> dict[str, str]:
    scan_uuid = uuid.UUID(food_scan_id)
    run_uuid = uuid.UUID(analysis_run_id)
    retry_count = int(getattr(self.request, "retries", 0) or 0)
    task_id = str(getattr(self.request, "id", "") or "")

    food_scan = _claim_scan_for_analysis(
        food_scan_id=scan_uuid,
        analysis_run_id=run_uuid,
        task_id=task_id,
        retry_count=retry_count,
    )
    if food_scan is None:
        return {"status": "skipped", "reason": "stale_or_confirmed_scan"}

    try:
        processed_scan = process_scan_analysis(
            food_scan,
            analysis_run_id=run_uuid,
            retry_transient_errors=True,
        )
    except RetryableFoodScanAnalysisError as exc:
        if retry_count >= settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES:
            _mark_scan_failed_if_current(
                food_scan_id=scan_uuid,
                analysis_run_id=run_uuid,
                failure_code=exc.failure_code,
            )
            return {
                "status": FoodScan.Status.FAILED,
                "scan_id": food_scan_id,
                "failure_code": exc.failure_code,
            }

        countdown = _retry_countdown(retry_count=retry_count)
        logger.info(
            "food_scan_analysis_retry_scheduled",
            extra={
                "food_scan_id": food_scan_id,
                "failure_code": exc.failure_code,
                "retry_count": retry_count + 1,
            },
        )
        raise self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES,
        ) from exc
    except Exception:
        _mark_scan_failed_if_current(
            food_scan_id=scan_uuid,
            analysis_run_id=run_uuid,
            failure_code=SCAN_TASK_FAILURE_CODE,
        )
        logger.exception("food_scan_analysis_task_failed", extra={"food_scan_id": food_scan_id})
        raise

    return {
        "status": processed_scan.status,
        "scan_id": str(processed_scan.id),
    }


def _claim_scan_for_analysis(
    *,
    food_scan_id: uuid.UUID,
    analysis_run_id: uuid.UUID,
    task_id: str,
    retry_count: int,
) -> FoodScan | None:
    with transaction.atomic():
        try:
            food_scan = FoodScan.objects.select_for_update().get(id=food_scan_id)
        except FoodScan.DoesNotExist:
            return None

        if food_scan.status == FoodScan.Status.CONFIRMED:
            return None
        if food_scan.analysis_run_id != analysis_run_id:
            return None
        if food_scan.analysis_task_id and task_id and food_scan.analysis_task_id != task_id:
            return None

        food_scan.status = FoodScan.Status.PROCESSING
        food_scan.failure_code = ""
        food_scan.analysis_attempt_count = retry_count + 1
        if task_id and not food_scan.analysis_task_id:
            food_scan.analysis_task_id = task_id
        food_scan.save(
            update_fields=[
                "status",
                "failure_code",
                "analysis_attempt_count",
                "analysis_task_id",
                "updated_at",
            ],
        )
        return food_scan


def _mark_scan_failed_if_current(
    *,
    food_scan_id: uuid.UUID,
    analysis_run_id: uuid.UUID,
    failure_code: str,
) -> None:
    FoodScan.objects.filter(
        id=food_scan_id,
        analysis_run_id=analysis_run_id,
    ).exclude(status=FoodScan.Status.CONFIRMED).update(
        status=FoodScan.Status.FAILED,
        failure_code=failure_code,
        updated_at=timezone.now(),
    )


def _retry_countdown(*, retry_count: int) -> int:
    raw_base_seconds = cast(int | str, settings.FOOD_SCAN_ANALYSIS_RETRY_BACKOFF_SECONDS)
    base_seconds = max(1, int(raw_base_seconds))
    return int(base_seconds * (2**retry_count))
