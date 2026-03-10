# Data migration: populate AlertStatus for the outbreak alert workflow.

from django.db import migrations


def create_alert_statuses(apps, schema_editor):
    AlertStatus = apps.get_model("alerts", "AlertStatus")
    statuses = [
        ("New", "Alert just created, not yet reviewed."),
        ("Under Investigation", "Alert being actively investigated."),
        ("Resolved", "Alert addressed and closed."),
        ("False Alarm", "Alert determined to be non-issue."),
    ]
    for name, desc in statuses:
        AlertStatus.objects.get_or_create(
            status_name=name,
            defaults={"description": desc},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_alert_statuses, noop),
    ]
