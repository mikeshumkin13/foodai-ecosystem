from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nutrition.models import FoodItem


class Command(BaseCommand):
    help = "Load local demo foods without overwriting existing catalog entries."

    def handle(self, *args: Any, **options: Any) -> None:
        if not settings.DEBUG or settings.SETTINGS_MODULE != "config.settings.local":
            raise CommandError("Demo seeding is allowed only with local settings and DEBUG=true.")
        fixture = Path(__file__).resolve().parents[2] / "fixtures/demo_nutrition_catalog.json"
        records = json.loads(fixture.read_text())
        references: dict[tuple[str, str], Any] = {}
        created_count = 0
        with transaction.atomic():
            for record in records:
                label = record["model"]
                model = apps.get_model(label)
                fields = {
                    key: value
                    for key, value in record["fields"].items()
                    if key not in {"created_at", "updated_at"}
                }
                for field in model._meta.fields:
                    if field.is_relation and fields.get(field.name) is not None:
                        fields[field.name] = references[
                            (field.related_model._meta.label_lower, str(fields[field.name]))
                        ]
                if label == "nutrition.foodcategory":
                    lookup = {"slug": fields.pop("slug")}
                elif label in {"nutrition.fooddatasource", "nutrition.nutrient"}:
                    lookup = {"code": fields.pop("code")}
                elif label == "nutrition.foodnutrient":
                    lookup = {name: fields.pop(name) for name in ("food_item", "nutrient")}
                else:
                    lookup = {"pk": record["pk"]}
                instance, created = model.objects.get_or_create(**lookup, defaults=fields)
                if label == "nutrition.nutrient" and instance.unit != fields["unit"]:
                    raise CommandError("Existing nutrient unit differs from the demo dataset.")
                references[(label, record["pk"])] = instance
                created_count += int(created)
        self.stdout.write(
            f"Demo catalog ready; created {created_count} records; "
            f"foods: {FoodItem.objects.count()}. "
            "Existing records preserved. Demo values are not production nutrition guidance."
        )
