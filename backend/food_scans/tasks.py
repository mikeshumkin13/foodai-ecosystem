from __future__ import annotations

import uuid
from time import monotonic, time
from typing import Any, cast

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from food_scans.models import FoodScan
from food_scans.orchestration import RetryableFoodScanAnalysisError, process_scan_analysis
from observability.events import report_application_error
from observability.metrics import (
    CELERY_ENQUEUED_AT_HEADER,
    CELERY_QUEUE_LATENCY_SECONDS,
    SCAN_PROCESSING_SECONDS,
    observe_metric,
)

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
    _record_queue_latency(request=self.request, retry_count=retry_count)

    food_scan = _claim_scan_for_analysis(
        food_scan_id=scan_uuid,
        analysis_run_id=run_uuid,
        task_id=task_id,
        retry_count=retry_count,
    )
    if food_scan is None:
        return {"status": "skipped", "reason": "stale_or_confirmed_scan"}

    processing_started_at = monotonic()
    processing_outcome = "success"
    try:
        processed_scan = process_scan_analysis(
            food_scan,
            analysis_run_id=run_uuid,
            retry_transient_errors=True,
        )
    except RetryableFoodScanAnalysisError as exc:
        if retry_count >= settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES:
            processing_outcome = "failed"
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
        processing_outcome = "retry"
        raise self.retry(
            exc=exc,
            countdown=countdown,
            max_retries=settings.FOOD_SCAN_ANALYSIS_MAX_RETRIES,
        ) from exc
    except Exception as exc:
        processing_outcome = "error"
        _mark_scan_failed_if_current(
            food_scan_id=scan_uuid,
            analysis_run_id=run_uuid,
            failure_code=SCAN_TASK_FAILURE_CODE,
        )
        report_application_error(
            event_name="food_scan_analysis_task_failed",
            error=exc,
            metadata={"component": "celery", "task": "food_scan_analysis"},
        )
        raise
    finally:
        observe_metric(
            SCAN_PROCESSING_SECONDS,
            monotonic() - processing_started_at,
            tags={"outcome": processing_outcome},
        )

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


def _record_queue_latency(*, request: Any, retry_count: int) -> None:
    if retry_count != 0:
        return
    headers = getattr(request, "headers", None)
    if not isinstance(headers, dict):
        return
    raw_enqueued_at = headers.get(CELERY_ENQUEUED_AT_HEADER)
    if isinstance(raw_enqueued_at, bool) or not isinstance(raw_enqueued_at, int | float):
        return
    queue_latency = time() - float(raw_enqueued_at)
    if queue_latency < 0 or queue_latency > 86_400:
        return
    observe_metric(
        CELERY_QUEUE_LATENCY_SECONDS,
        queue_latency,
        tags={"task": "food_scan_analysis", "outcome": "started"},
    )
