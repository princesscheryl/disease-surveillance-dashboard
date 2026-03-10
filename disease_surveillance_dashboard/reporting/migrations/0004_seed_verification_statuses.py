"""Data migration: add verification statuses for officer review workflow."""

from django.db import migrations


def seed_verification_statuses(apps, schema_editor):
    ReportStatus = apps.get_model("reporting", "ReportStatus")
    statuses = [
        ("Pending Review", "Report awaiting officer verification."),
        ("Verified", "Report validated by a public health officer."),
        ("Duplicate", "Report marked as duplicate of another."),
        ("Invalid", "Report marked as invalid or erroneous."),
    ]
    for name, description in statuses:
        ReportStatus.objects.get_or_create(
            status_name=name,
            defaults={"description": description},
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0003_seed_draft_status"),
    ]

    operations = [
        migrations.RunPython(seed_verification_statuses, noop),
    ]
