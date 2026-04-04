import django.db.models.deletion
from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_first_last_health_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="InAppNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("TASK_ASSIGNED", "Task assigned"), ("ALERT_ESCALATED", "Alert escalated")], max_length=32, verbose_name="Kind")),
                ("title", models.CharField(max_length=200, verbose_name="Title")),
                ("body", models.TextField(blank=True, verbose_name="Body")),
                ("link_path", models.CharField(blank=True, max_length=500, verbose_name="Link path")),
                ("read_at", models.DateTimeField(blank=True, null=True, verbose_name="Read at")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                (
                    "recipient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="in_app_notifications",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Recipient",
                    ),
                ),
            ],
            options={
                "db_table": "in_app_notifications",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="inappnotification",
            index=models.Index(fields=["recipient", "read_at"], name="in_app_notif_recipient_read_idx"),
        ),
    ]
