"""Data migration: guarantee DRAFT and SUBMITTED rows exist in report_status."""

from django.db import migrations


def seed_statuses(apps, schema_editor):
    ReportStatus = apps.get_model("reporting", "ReportStatus")
    statuses = [
        ("DRAFT", "Report saved as a draft; not yet submitted for surveillance."),
        ("SUBMITTED", "Report submitted by health worker and ready for review."),
    ]
    for name, description in statuses:
        ReportStatus.objects.get_or_create(
            status_name=name,
            defaults={"description": description},
        )


def remove_draft_status(apps, schema_editor):
    """Reverse: remove DRAFT only if no reports reference it."""
    ReportStatus = apps.get_model("reporting", "ReportStatus")
    Report = apps.get_model("reporting", "Report")
    try:
        draft = ReportStatus.objects.get(status_name="DRAFT")
        if not Report.objects.filter(status=draft).exists():
            draft.delete()
    except ReportStatus.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0002_report_age_group_report_case_count_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_statuses, reverse_code=remove_draft_status),
    ]
