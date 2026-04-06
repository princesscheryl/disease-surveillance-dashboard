import django.db.models.deletion
from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("alerts", "0004_alert_email_notification_models"),
        ("reference_data", "0004_location_population_location_population_year"),
    ]

    operations = [
        migrations.CreateModel(
            name="CusumThreshold",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("threshold", models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=5, verbose_name="CUSUM threshold (h)")),
                ("k_value", models.DecimalField(decimal_places=2, default=Decimal("0.50"), max_digits=5, verbose_name="CUSUM slack (k)")),
                ("use_seasonal_baseline", models.BooleanField(default=False, help_text="When enabled, each day uses its 7-day moving average as the CUSUM baseline instead of a single prior-window average.", verbose_name="Use 7-day moving average as daily baseline")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                ("disease", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cusum_thresholds", to="reference_data.disease", verbose_name="Disease")),
                ("location", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="cusum_thresholds", to="reference_data.location", verbose_name="Location")),
            ],
            options={
                "verbose_name": "CUSUM threshold",
                "verbose_name_plural": "CUSUM thresholds",
                "db_table": "cusum_thresholds",
                "unique_together": {("disease", "location")},
            },
        ),
        migrations.CreateModel(
            name="AlertPerformance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("period_start", models.DateField(db_index=True, verbose_name="Period start")),
                ("period_end", models.DateField(verbose_name="Period end")),
                ("alerts_generated", models.PositiveIntegerField(default=0, verbose_name="Alerts generated")),
                ("alerts_confirmed", models.PositiveIntegerField(default=0, help_text="Alerts closed as Resolved in this period.", verbose_name="Resolved (confirmed)")),
                ("false_alarms", models.PositiveIntegerField(default=0, verbose_name="False alarms")),
                ("false_alarm_rate", models.DecimalField(decimal_places=3, default=Decimal("0.000"), help_text="false_alarms / (confirmed + false_alarms) when denominator is positive.", max_digits=6, verbose_name="False alarm rate")),
                ("threshold_used", models.DecimalField(decimal_places=2, default=Decimal("5.00"), max_digits=5, verbose_name="Threshold (h) at last update")),
                ("k_value_used", models.DecimalField(decimal_places=2, default=Decimal("0.50"), max_digits=5, verbose_name="k at last update")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                ("disease", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_performance_rows", to="reference_data.disease", verbose_name="Disease")),
                ("location", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_performance_rows", to="reference_data.location", verbose_name="Location")),
            ],
            options={
                "verbose_name": "Alert performance",
                "verbose_name_plural": "Alert performance",
                "db_table": "alert_performance",
                "ordering": ["-period_start", "disease", "location"],
            },
        ),
        migrations.AddConstraint(
            model_name="alertperformance",
            constraint=models.UniqueConstraint(fields=("disease", "location", "period_start"), name="alertperf_disease_location_period_uniq"),
        ),
    ]
