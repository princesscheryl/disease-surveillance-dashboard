# Generated migration: replace full_name with first_name/last_name and add health worker fields

from django.db import migrations, models
import django.db.models.deletion


def split_full_name(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        full = getattr(user, "full_name", None) or ""
        user.first_name = full
        user.last_name = ""
        user.save(update_fields=["first_name", "last_name"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_user_full_name"),
        ("reference_data", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="first_name",
            field=models.CharField(max_length=150, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="last_name",
            field=models.CharField(max_length=150, blank=True),
        ),
        migrations.AddField(
            model_name="user",
            name="health_facility",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="user",
            name="district",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="health_workers",
                to="reference_data.location",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="position",
            field=models.CharField(
                blank=True,
                choices=[
                    ("CHW", "Community Health Worker"),
                    ("CH_NURSE", "Community Health Nurse"),
                    ("PH_NURSE", "Public Health Nurse"),
                    ("DISEASE_CONTROL", "Disease Control Officer"),
                    ("SURVEILLANCE", "Surveillance Officer"),
                    ("ENV_HEALTH", "Environmental Health Officer"),
                    ("DISTRICT_DIR", "District Director"),
                    ("OTHER", "Other"),
                ],
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="facility_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("TEACHING_HOSPITAL", "Teaching Hospital"),
                    ("REGIONAL_HOSPITAL", "Regional Hospital"),
                    ("DISTRICT_HOSPITAL", "District Hospital"),
                    ("POLYCLINIC", "Polyclinic"),
                    ("HEALTH_CENTRE", "Health Centre"),
                    ("CHPS", "CHPS Compound"),
                    ("DISTRICT_OFFICE", "District Health Directorate"),
                    ("OTHER", "Other"),
                ],
                max_length=50,
            ),
        ),
        migrations.RunPython(split_full_name, noop),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(max_length=150, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(max_length=150, verbose_name="last name"),
        ),
        migrations.RemoveField(
            model_name="user",
            name="full_name",
        ),
    ]
