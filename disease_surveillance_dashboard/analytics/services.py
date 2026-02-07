"""
Analytics service layer for computing baseline metrics and statistical indicators.

This module provides functions for calculating moving averages and CUSUM values
used in outbreak detection algorithms. These services are designed to be called
synchronously but can be adapted for asynchronous processing via Celery in the future.
"""

from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from disease_surveillance_dashboard.reporting.models import Report


def compute_moving_average(disease_id, location_id, window_days=30):
    """
    Compute moving average baseline for a disease-location pair.

    Calculates the average daily case count over the past N days by:
    1. Fetching all verified reports for the disease and location
    2. Grouping by date (observed_at)
    3. Computing average daily count

    Args:
        disease_id: Primary key of Disease model
        location_id: Primary key of Location model
        window_days: Number of days to look back (default: 30)

    Returns:
        float: Average daily case count, or 0.0 if no reports found

    Note:
        This function only considers reports with verified status.
        Future enhancements could filter by report status more flexibly.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=window_days)

    # Fetch verified reports in the time window
    # Note: We assume reports with status containing "VERIFIED" are valid
    # In production, you may want to filter by specific status IDs
    reports = Report.objects.filter(
        disease_id=disease_id,
        location_id=location_id,
        observed_at__gte=start_date,
        observed_at__lte=end_date,
    )

    if not reports.exists():
        return 0.0

    # Group reports by date and count per day
    daily_counts = (
        reports.annotate(date=TruncDate("observed_at"))
        .values("date")
        .annotate(count=Count("id"))
        .values_list("count", flat=True)
    )

    if not daily_counts:
        return 0.0

    # Calculate average daily count
    total_cases = sum(daily_counts)
    num_days = len(daily_counts)
    average = total_cases / num_days if num_days > 0 else 0.0

    return float(average)


def compute_cusum(observed_value, baseline_value, previous_cusum=0.0, k=0.5):
    """
    Compute CUSUM (Cumulative Sum) value for outbreak detection.

    CUSUM is a statistical process control method that accumulates deviations
    from a baseline. It detects sustained increases in case counts that may
    indicate an outbreak.

    Formula: CUSUM_t = max(0, previous_cusum + (observed_value - baseline_value - k))

    Where:
    - k is the slack parameter (typically 0.5) that determines sensitivity
    - When CUSUM exceeds a threshold (e.g., 5), an alert is triggered

    Args:
        observed_value: Current observed case count or value
        baseline_value: Expected baseline value
        previous_cusum: Previous CUSUM value (default: 0.0)
        k: Slack parameter controlling sensitivity (default: 0.5)

    Returns:
        float: New CUSUM value

    Note:
        CUSUM resets to 0 when the calculation would be negative, meaning
        it only accumulates positive deviations above baseline + k.
    """
    deviation = float(observed_value) - float(baseline_value) - float(k)
    return max(0.0, float(previous_cusum) + deviation)

