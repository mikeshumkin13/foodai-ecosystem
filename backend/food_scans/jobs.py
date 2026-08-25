from __future__ import annotations

import uuid
from time import time

from django.db import transaction

from food_scans.models import FoodScan
from food_scans.tasks import process_food_scan_analysis_task
from observability.metrics import CELERY_ENQUEUED_AT_HEADER


class FoodScanJobError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def enqueue_food_scan_analysis(*, food_scan: FoodScan, force: bool = False) -> FoodScan:
    run_id = uuid.uuid4()
    task_id = _build_food_scan_analysis_task_id(food_scan_id=food_scan.id, run_id=run_id)

    with transaction.atomic():
        locked_scan = FoodScan.objects.select_for_update().get(id=food_scan.id)
        if locked_scan.status == FoodScan.Status.CONFIRMED:
            raise FoodScanJobError("confirmed_scan_cannot_be_reprocessed")
        if locked_scan.status == FoodScan.Status.PROCESSING:
            return locked_scan
        if locked_scan.status == FoodScan.Status.NEEDS_CONFIRMATION and not force:
            return locked_scan

        locked_scan.status = FoodScan.Status.UPLOADED
        locked_scan.failure_code = ""
        locked_scan.analysis_run_id = run_id
        locked_scan.analysis_task_id = task_id
        locked_scan.analysis_attempt_count = 0
        locked_scan.save(
            update_fields=[
                "status",
                "failure_code",
                "analysis_run_id",
                "analysis_task_id",
                "analysis_attempt_count",
                "updated_at",
            ],
        )

    process_food_scan_analysis_task.apply_async(
        args=[str(food_scan.id), str(run_id)],
        task_id=task_id,
        headers={CELERY_ENQUEUED_AT_HEADER: time()},
    )
    food_scan.refresh_from_db()
    return food_scan


def _build_food_scan_analysis_task_id(*, food_scan_id: uuid.UUID, run_id: uuid.UUID) -> str:
    return f"food-scan-analysis-{food_scan_id}-{run_id}"
