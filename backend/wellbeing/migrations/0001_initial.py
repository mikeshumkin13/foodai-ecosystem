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
            name="WellbeingAssistantSettings",
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
                    "history_consent_version",
                    models.CharField(
                        default="wellbeing_assistant_history_mvp_v1",
                        max_length=80,
                    ),
                ),
                ("history_consent_granted_at", models.DateTimeField(blank=True, null=True)),
                ("history_consent_revoked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wellbeing_assistant_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["user_id"],
                "permissions": [
                    ("use_wellbeing_assistant", "Can use wellbeing assistant"),
                    (
                        "view_own_wellbeingassistantsettings",
                        "Can view own wellbeing assistant settings",
                    ),
                    (
                        "change_own_wellbeingassistantsettings",
                        "Can change own wellbeing assistant settings",
                    ),
                ],
                "default_permissions": (),
            },
        ),
        migrations.CreateModel(
            name="WellbeingAssistantMessage",
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
                ("context_date", models.DateField()),
                ("request_text", models.TextField()),
                ("response_payload", models.JSONField(default=dict)),
                ("context_snapshot", models.JSONField(default=dict)),
                ("provider_name", models.CharField(max_length=80)),
                ("output_schema_version", models.CharField(max_length=80)),
                (
                    "safety_status",
                    models.CharField(
                        choices=[
                            ("passed", "Passed"),
                            ("input_blocked", "Input blocked"),
                            ("output_blocked", "Output blocked"),
                        ],
                        default="passed",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wellbeing_assistant_messages",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "default_permissions": (),
                "indexes": [
                    models.Index(
                        fields=["user", "created_at"],
                        name="wellbeing_msg_user_created_idx",
                    ),
                ],
            },
        ),
    ]
