from calendar import monthrange
from datetime import date
from decimal import Decimal
from decimal import ROUND_HALF_UP

from django.db import IntegrityError
from django.db import transaction
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertPerformance
from disease_surveillance_dashboard.alerts.models import AlertStatus
from disease_surveillance_dashboard.alerts.models import resolve_cusum_config

_prev_alert_status_id = {}


def _month_range_for(day: date):
    last = monthrange(day.year, day.month)[1]
    return date(day.year, day.month, 1), date(day.year, day.month, last)


def _status_name(status_id):
    if status_id is None:
        return None
    return AlertStatus.objects.filter(pk=status_id).values_list(
        "status_name",
        flat=True,
    ).first()


def _recompute_false_alarm_rate(row):
    denom = row.alerts_confirmed + row.false_alarms
    if denom:
        rate = Decimal(row.false_alarms) / Decimal(denom)
        row.false_alarm_rate = rate.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    else:
        row.false_alarm_rate = Decimal("0.000")


def _lock_performance_row(alert, period_start, period_end):
    try:
        return AlertPerformance.objects.select_for_update().get(
            disease_id=alert.disease_id,
            location_id=alert.location_id,
            period_start=period_start,
        )
    except AlertPerformance.DoesNotExist:
        h, k, _, _ = resolve_cusum_config(alert.disease_id, alert.location_id)
        try:
            return AlertPerformance.objects.create(
                disease_id=alert.disease_id,
                location_id=alert.location_id,
                period_start=period_start,
                period_end=period_end,
                threshold_used=Decimal(str(h)),
                k_value_used=Decimal(str(k)),
            )
        except IntegrityError:
            return AlertPerformance.objects.select_for_update().get(
                disease_id=alert.disease_id,
                location_id=alert.location_id,
                period_start=period_start,
            )


def _bump_generated(alert):
    d = timezone.localdate(alert.created_at)
    start, end = _month_range_for(d)
    with transaction.atomic():
        row = _lock_performance_row(alert, start, end)
        row.period_end = end
        row.alerts_generated += 1
        h, k, _, _ = resolve_cusum_config(alert.disease_id, alert.location_id)
        row.threshold_used = Decimal(str(h))
        row.k_value_used = Decimal(str(k))
        row.save()


def _record_outcome(alert, old_status_id):
    if old_status_id == alert.status_id:
        return
    old_name = _status_name(old_status_id)
    new_name = _status_name(alert.status_id)
    if new_name not in ("Resolved", "False Alarm"):
        return
    if old_name in ("Resolved", "False Alarm"):
        return

    d = timezone.localdate()
    start, end = _month_range_for(d)
    with transaction.atomic():
        row = _lock_performance_row(alert, start, end)
        row.period_end = end
        if new_name == "Resolved":
            row.alerts_confirmed += 1
        else:
            row.false_alarms += 1
        _recompute_false_alarm_rate(row)
        h, k, _, _ = resolve_cusum_config(alert.disease_id, alert.location_id)
        row.threshold_used = Decimal(str(h))
        row.k_value_used = Decimal(str(k))
        row.save()


@receiver(pre_save, sender=Alert)
def cache_alert_status_before_save(sender, instance, **kwargs):
    if not instance.pk:
        return
    prev_id = Alert.objects.filter(pk=instance.pk).values_list(
        "status_id",
        flat=True,
    ).first()
    if prev_id is not None:
        _prev_alert_status_id[instance.pk] = prev_id


@receiver(post_save, sender=Alert)
def alert_post_save(sender, instance, created, **kwargs):
    if created:
        _bump_generated(instance)

        from disease_surveillance_dashboard.exports.models import record_audit_event
        record_audit_event(
            actor=None,
            action_type="ALERT_CREATED",
            entity_type="Alert",
            entity_id=str(instance.pk),
            details={
                "disease_id": instance.disease_id,
                "location_id": instance.location_id,
                "severity": instance.severity_level,
                "observed": float(instance.observed_value) if instance.observed_value is not None else None,
                "baseline": float(instance.baseline_value) if instance.baseline_value is not None else None,
            },
        )

        def enqueue():
            from disease_surveillance_dashboard.alerts.tasks import send_immediate_alert_email
            send_immediate_alert_email.delay(instance.pk)

        transaction.on_commit(enqueue)
    else:
        old_id = _prev_alert_status_id.pop(instance.pk, None)
        if old_id is not None:
            _record_outcome(instance, old_id)
