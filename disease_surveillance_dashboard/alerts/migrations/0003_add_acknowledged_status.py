"""Data migration: add Acknowledged status to alert workflow."""

from django.db import migrations


def add_acknowledged_status(apps, schema_editor):
    AlertStatus = apps.get_model("alerts", "AlertStatus")
    AlertStatus.objects.get_or_create(
        status_name="Acknowledged",
        defaults={
            "description": "Alert has been seen and acknowledged by an officer.",
        },
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0002_populate_alert_statuses"),
    ]

    operations = [
        migrations.RunPython(add_acknowledged_status, noop),
    ]
