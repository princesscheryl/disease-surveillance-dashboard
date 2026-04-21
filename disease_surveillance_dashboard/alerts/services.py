"""
Alert evaluation service for outbreak detection using CUSUM algorithm.

This module provides functions for evaluating trend metrics and generating
alerts when statistical thresholds are exceeded. The service implements
the CUSUM (Cumulative Sum) method for detecting sustained increases in
disease incidence that may indicate an outbreak.
"""

from datetime import UTC
from datetime import datetime
from decimal import Decimal

from django.db import transaction

from disease_surveillance_dashboard.analytics.models import TrendMetric
from disease_surveillance_dashboard.analytics.services import compute_cusum

from .models import Alert
from .models import AlertStatus
from .models import resolve_cusum_config

SEVERITY_MEDIUM_THRESHOLD = 10.0
SEVERITY_HIGH_THRESHOLD = 15.0


def evaluate_trend_and_generate_alert(trend_metric_id):
    """
    Evaluate a trend metric and generate an alert if CUSUM exceeds threshold.

    This function:
    1. Retrieves the TrendMetric by ID
    2. Uses moving_avg as baseline_value (or calculates if missing)
    3. Computes CUSUM using total_cases as observed_value
    4. If CUSUM > threshold, creates an Alert with appropriate severity

    Args:
        trend_metric_id: Primary key of TrendMetric to evaluate

    Returns:
        tuple: (alert_created: bool, alert: Alert or None, cusum_value: float)

    Note:
        This function runs synchronously. For production use with large datasets,
        consider moving this to a Celery task to avoid blocking web requests.
    """
    try:
        trend_metric = TrendMetric.objects.select_related(
            "disease",
            "location",
        ).get(id=trend_metric_id)
    except TrendMetric.DoesNotExist:
        return False, None, 0.0

    baseline_value = float(trend_metric.moving_avg) if trend_metric.moving_avg else 0.0
    observed_value = float(trend_metric.total_cases)

    cusum_threshold, k_val, _, _ = resolve_cusum_config(
        trend_metric.disease_id,
        trend_metric.location_id,
    )

    # get all earlier trend metrics for the same disease and location, oldest first
    # so we can roll the cusum forward and carry state into the current evaluation
    prior_metrics = TrendMetric.objects.filter(
        disease_id=trend_metric.disease_id,
        location_id=trend_metric.location_id,
        period_start__lt=trend_metric.period_start,
    ).order_by("period_start")

    previous_cusum = 0.0
    for prior in prior_metrics:
        prior_baseline = float(prior.moving_avg) if prior.moving_avg else 0.0
        prior_observed = float(prior.total_cases)
        previous_cusum = compute_cusum(
            observed_value=prior_observed,
            baseline_value=prior_baseline,
            previous_cusum=previous_cusum,
            k=k_val,
        )

    cusum_value = compute_cusum(
        observed_value=observed_value,
        baseline_value=baseline_value,
        previous_cusum=previous_cusum,
        k=k_val,
    )

    if cusum_value <= cusum_threshold:
        return False, None, cusum_value

    # Determine severity level based on CUSUM magnitude
    if cusum_value >= SEVERITY_HIGH_THRESHOLD:
        severity_level = "High"
    elif cusum_value >= SEVERITY_MEDIUM_THRESHOLD:
        severity_level = "Medium"
    else:
        severity_level = "Low"

    # Get or create "New" alert status
    alert_status, _ = AlertStatus.objects.get_or_create(
        status_name="New",
        defaults={"description": "Newly generated alert"},
    )

    # Create period timestamps from TrendMetric dates
    period_start = datetime.combine(
        trend_metric.period_start,
        datetime.min.time(),
        tzinfo=UTC,
    )
    period_end = datetime.combine(
        trend_metric.period_end,
        datetime.max.time(),
        tzinfo=UTC,
    )

    # Generate threshold rule description
    threshold_rule = (
        f"CUSUM = {cusum_value:.2f} (observed={observed_value:.2f}, "
        f"baseline={baseline_value:.2f}, threshold={cusum_threshold})"
    )

    # Create alert within transaction to ensure data consistency
    with transaction.atomic():
        alert = Alert.objects.create(
            disease=trend_metric.disease,
            location=trend_metric.location,
            period_start=period_start,
            period_end=period_end,
            baseline_value=Decimal(str(baseline_value)),
            observed_value=Decimal(str(observed_value)),
            threshold_rule=threshold_rule,
            severity_level=severity_level,
            status=alert_status,
        )

    return True, alert, cusum_value

