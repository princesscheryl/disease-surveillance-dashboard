"""
celery task for automatic outbreak alert generation
runs cusum detection over the last 30 days per disease/location and then it creates
alert records when the cusum series exceeds the threshold of 5.0.
"""

import logging
from datetime import datetime
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from celery import shared_task

logger = logging.getLogger(__name__)

CUSUM_THRESHOLD = 5.0


@shared_task(name="generate-outbreak-alerts-every-30min")
def generate_outbreak_alerts(dry_run=False):
    """
    Run cusum detection for all active disease/location pairs and create
    alert records for each trigger point (date where CUSUM >= 5.0)and
    skip combinations with fewer than 10 reports so the baseline has enough data.
    returns the number of alerts created.
    """
    from disease_surveillance_dashboard.alerts.models import Alert
    from disease_surveillance_dashboard.alerts.models import AlertStatus
    from disease_surveillance_dashboard.dashboard.services import get_detection_metrics
    from reference_data.models import Disease
    from reference_data.models import Location

    logger.info("Starting outbreak alert generation (dry_run=%s).", dry_run)
    created_count = 0

    try:
        diseases = list(Disease.objects.filter(is_active=True).values_list("id", flat=True))
        locations = list(Location.objects.filter(is_active=True).values_list("id", flat=True))
        if not diseases or not locations:
            logger.info("No active diseases or locations; nothing to run.")
            return 0

        status_new = AlertStatus.objects.filter(status_name="New").first()
        if not status_new:
            logger.warning("AlertStatus 'New' not found. Run migrations (0002_populate_alert_statuses).")
            return 0

        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)

        for disease_id in diseases:
            for location_id in locations:
                try:
                    result = get_detection_metrics(
                        start_date=start_date,
                        end_date=end_date,
                        disease_id=disease_id,
                        location_id=location_id,
                    )
                except Exception as e:
                    logger.exception(
                        "get_detection_metrics failed for disease_id=%s location_id=%s: %s",
                        disease_id, location_id, e,
                    )
                    continue

                if result.get("message") or len(result.get("daily_cases") or []) < 10:
                    continue

                dates = result.get("dates") or []
                daily_cases = result.get("daily_cases") or []
                cusum_series = result.get("cusum_series") or []
                trigger_points = result.get("trigger_points") or []
                baseline_avg = result.get("baseline_avg")
                if baseline_avg is None:
                    continue

                for trigger_date_str in trigger_points:
                    try:
                        if trigger_date_str not in dates:
                            continue
                        i = dates.index(trigger_date_str)
                        observed = daily_cases[i] if i < len(daily_cases) else 0
                        cusum_val = cusum_series[i] if i < len(cusum_series) else 0

                        parsed = datetime.strptime(trigger_date_str, "%Y-%m-%d").date()
                        period_start = timezone.make_aware(
                            datetime.combine(parsed, datetime.min.time())
                        )
                        period_end = timezone.make_aware(
                            datetime.combine(parsed, datetime.max.time())
                        )

                        exists = Alert.objects.filter(
                            disease_id=disease_id,
                            location_id=location_id,
                            period_start__date=parsed,
                        ).exists()
                        if exists:
                            continue

                        if dry_run:
                            created_count += 1
                            logger.info(
                                "Would create alert: disease_id=%s location_id=%s date=%s observed=%s cusum=%.2f",
                                disease_id, location_id, trigger_date_str, observed, cusum_val,
                            )
                            continue

                        severity = "High" if cusum_val > 10 else "Medium"
                        Alert.objects.create(
                            disease_id=disease_id,
                            location_id=location_id,
                            period_start=period_start,
                            period_end=period_end,
                            baseline_value=Decimal(str(baseline_avg)),
                            observed_value=Decimal(observed),
                            threshold_rule="CUSUM threshold exceeded (5.0)",
                            severity_level=severity,
                            status=status_new,
                        )
                        created_count += 1
                    except Exception as e:
                        logger.exception(
                            "Failed to create alert for %s disease_id=%s location_id=%s: %s",
                            trigger_date_str, disease_id, location_id, e,
                        )

        logger.info("Outbreak alert generation finished. Created: %s.", created_count)
        return created_count
    except Exception as e:
        logger.exception("Outbreak alert generation failed: %s", e)
        raise
