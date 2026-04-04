import django.db.models.deletion
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0003_add_acknowledged_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="AlertImmediateEmailLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="Sent At")),
                (
                    "alert",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="immediate_email_log",
                        to="alerts.alert",
                        verbose_name="Alert",
                    ),
                ),
            ],
            options={
                "verbose_name": "Alert immediate email log",
                "verbose_name_plural": "Alert immediate email logs",
                "db_table": "alert_immediate_email_log",
            },
        ),
        migrations.CreateModel(
            name="PhoAlertDigestSend",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("digest_for_date", models.DateField(db_index=True, unique=True, verbose_name="Digest date")),
                ("sent_at", models.DateTimeField(auto_now_add=True, verbose_name="Sent At")),
            ],
            options={
                "verbose_name": "PHO alert digest send",
                "verbose_name_plural": "PHO alert digest sends",
                "db_table": "pho_alert_digest_sends",
            },
        ),
    ]
