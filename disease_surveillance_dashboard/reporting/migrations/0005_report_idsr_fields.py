"""Schema migration: add IDSR fields to Report model.

New fields:
  - case_classification  (Suspected / Probable / Confirmed / Unknown)
  - death_count          (number of deaths among reported cases)
  - report_type          (Immediate / Weekly / Outbreak)
  - health_facility      (proper field replacing the case_notes hack)
  - male_count, female_count, unknown_sex_count
  - age_under5_count, age_5_17_count, age_18_59_count, age_60plus_count, unknown_age_count
"""

from django.db import migrations
import django.core.validators
import django.db.models.deletion
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ("reporting", "0004_seed_verification_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="report",
            name="case_classification",
            field=django.db.models.CharField(
                choices=[
                    ("SUSPECTED", "Suspected"),
                    ("PROBABLE", "Probable"),
                    ("CONFIRMED", "Confirmed"),
                    ("UNKNOWN", "Unknown"),
                ],
                default="UNKNOWN",
                max_length=20,
                verbose_name="Case Classification",
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="death_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                help_text="Number of deaths among the reported cases",
                verbose_name="Deaths",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="report_type",
            field=django.db.models.CharField(
                choices=[
                    ("IMMEDIATE", "Immediate Notification"),
                    ("WEEKLY", "Weekly Aggregate"),
                    ("OUTBREAK", "Outbreak Report"),
                ],
                default="WEEKLY",
                max_length=20,
                verbose_name="Report Type",
                db_index=True,
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="health_facility",
            field=django.db.models.CharField(
                blank=True,
                help_text="Name of the health facility or unit submitting this report",
                max_length=255,
                verbose_name="Reporting Facility",
            ),
        ),
        # Sex breakdown counts
        migrations.AddField(
            model_name="report",
            name="male_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Male Cases",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="female_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Female Cases",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="unknown_sex_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Unknown Sex Cases",
            ),
        ),
        # Age breakdown counts
        migrations.AddField(
            model_name="report",
            name="age_under5_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Cases Under 5",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="age_5_17_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Cases Age 5\u201317",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="age_18_59_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Cases Age 18\u201359",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="age_60plus_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Cases Age 60+",
            ),
        ),
        migrations.AddField(
            model_name="report",
            name="unknown_age_count",
            field=django.db.models.PositiveIntegerField(
                default=0,
                verbose_name="Unknown Age Cases",
            ),
        ),
    ]
