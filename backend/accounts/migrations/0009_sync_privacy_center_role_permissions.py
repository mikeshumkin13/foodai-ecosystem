from __future__ import annotations

from django.db import migrations


def sync_role_groups(apps, schema_editor):  # noqa: ANN001
    from accounts.rbac import ensure_role_groups

    ensure_role_groups(using=schema_editor.connection.alias)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0008_alter_rolepermission_options"),
        ("privacy", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_role_groups, migrations.RunPython.noop),
    ]
