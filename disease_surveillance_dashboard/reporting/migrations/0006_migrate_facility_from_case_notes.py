"""Data migration: move facility name out of case_notes into health_facility.

Previously, the create/update views prepended the facility name to case_notes
as:  "Facility/Unit: <name>\n\n<rest of notes>"

This migration extracts that prefix into the new health_facility field and
leaves case_notes containing only the actual notes text.
"""

from django.db import migrations


def extract_facility_from_notes(apps, schema_editor):
    Report = apps.get_model("reporting", "Report")
    to_update = []
    for report in Report.objects.all():
        notes = report.case_notes or ""
        if notes.startswith("Facility/Unit: "):
            first_line, _, remainder = notes.partition("\n\n")
            facility = first_line.removeprefix("Facility/Unit: ").strip()
            report.health_facility = facility
            report.case_notes = remainder
            to_update.append(report)
    if to_update:
        Report.objects.bulk_update(to_update, ["health_facility", "case_notes"])


def reverse_extract(apps, schema_editor):
    """Put the facility name back into case_notes on rollback."""
    Report = apps.get_model("reporting", "Report")
    to_update = []
    for report in Report.objects.exclude(health_facility=""):
        case_notes = report.case_notes or ""
        if case_notes:
            report.case_notes = f"Facility/Unit: {report.health_facility}\n\n{case_notes}"
        else:
            report.case_notes = f"Facility/Unit: {report.health_facility}"
        report.health_facility = ""
        to_update.append(report)
    if to_update:
        Report.objects.bulk_update(to_update, ["health_facility", "case_notes"])


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0005_report_idsr_fields"),
    ]

    operations = [
        migrations.RunPython(extract_facility_from_notes, reverse_extract),
    ]
