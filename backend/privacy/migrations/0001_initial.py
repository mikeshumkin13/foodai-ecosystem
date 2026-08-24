from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="PrivacySettings",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "model_improvement_consent_version",
                    models.CharField(default="model_improvement_mvp_v1", max_length=80),
                ),
                (
                    "model_improvement_consent_granted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "model_improvement_consent_revoked_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "food_photo_training_consent_version",
                    models.CharField(default="food_photo_training_mvp_v1", max_length=80),
                ),
                (
                    "food_photo_training_consent_granted_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                (
                    "food_photo_training_consent_revoked_at",
                    models.DateTimeField(blank=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="privacy_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user_id"],
                "default_permissions": (),
                "permissions": [
                    ("view_own_privacysettings", "Can view own privacy settings"),
                    ("change_own_privacysettings", "Can change own privacy settings"),
                    ("export_own_data", "Can export own data"),
                    ("delete_own_data", "Can delete own data"),
                ],
            },
        ),
    ]
