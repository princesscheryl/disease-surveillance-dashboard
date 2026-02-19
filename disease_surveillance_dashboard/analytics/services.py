"""
Analytics service layer for computing baseline metrics and statistical indicators.

This module provides functions for calculating moving averages and CUSUM values
used in outbreak detection algorithms. These services are designed to be called
synchronously but can be adapted for asynchronous processing via Celery in the future.
"""

from datetime import datetime as dt
from datetime import timedelta

import numpy as np
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from disease_surveillance_dashboard.reporting.models import Report


def compute_moving_average(disease_id, location_id, window_days=30):
    """
    Compute moving average baseline for a disease-location pair.

    Calculates the average daily case count over the past N days by:
    1. Fetching all reports for the disease and location in the time window
    2. Grouping by date (observed_at) and summing case_count per day
    3. Computing average daily case count

    Args:
        disease_id: Primary key of Disease model
        location_id: Primary key of Location model
        window_days: Number of days to look back (default: 30)

    Returns:
        float: Average daily case count (sum of case_count values), or 0.0 if no reports found

    Note:
        Uses SUM(case_count) instead of COUNT(id) to account for reports
        that may represent multiple cases. This provides accurate epidemiological
        baseline calculations when reports aggregate multiple cases.
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=window_days)

    # Fetch reports in the time window
    reports = Report.objects.filter(
        disease_id=disease_id,
        location_id=location_id,
        observed_at__gte=start_date,
        observed_at__lte=end_date,
    )

    if not reports.exists():
        return 0.0

    # Group reports by date and sum case_count per day
    # This accounts for reports that may represent multiple cases
    daily_totals = (
        reports.annotate(date=TruncDate("observed_at"))
        .values("date")
        .annotate(total_cases=Sum("case_count"))
        .values_list("total_cases", flat=True)
    )

    if not daily_totals:
        return 0.0

    # Calculate average daily case count
    total_cases = sum(daily_totals)
    num_days = len(daily_totals)
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


def compute_isolation_forest_anomalies(series, contamination=0.05, random_state=42):
    """
    Run Isolation Forest anomaly detection on a daily case time-series.

    Args:
        series: List of dicts with "date" and "cases" keys (e.g. from get_cases_timeseries).
        contamination: Expected proportion of outliers (0 to 0.5). Default 0.05.
        random_state: Seed for reproducible fits. Default 42.

    Returns:
        List of dicts: {"date", "cases", "anomaly_score", "is_anomaly"}.
        If fewer than 10 points, all items have is_anomaly=False and anomaly_score=0.0.
    """
    MIN_POINTS = 10
    if not series or len(series) < MIN_POINTS:
        return [
            {"date": item["date"], "cases": item["cases"], "anomaly_score": 0.0, "is_anomaly": False}
            for item in series
        ]

    from sklearn.ensemble import IsolationForest

    X = np.array([[item["cases"]] for item in series])
    clf = IsolationForest(contamination=contamination, random_state=random_state)
    clf.fit(X)
    pred = clf.predict(X)  # -1 = anomaly, 1 = inlier
    scores = clf.decision_function(X)  # lower = more anomalous

    result = []
    for i, item in enumerate(series):
        result.append({
            "date": item["date"],
            "cases": item["cases"],
            "anomaly_score": float(scores[i]),
            "is_anomaly": bool(pred[i] == -1),
        })
    return result


def compute_arima_forecast(series, horizon=14, seasonal=False):
    """
    Produce ARIMA(1,1,1) point forecast and 95% CI for the next horizon days.

    Args:
        series: List of dicts with "date" and "cases" keys (e.g. from get_cases_timeseries).
        horizon: Number of days to forecast. Default 14.
        seasonal: Reserved for future seasonal ARIMA; currently ignored.

    Returns:
        dict with "forecast" (list of {"date", "forecast", "lower_ci", "upper_ci"})
        and optional "message" when series is too short. Empty forecast list and
        message when too short.
    """
    MIN_POINTS = 7
    if not series or len(series) < MIN_POINTS:
        return {
            "forecast": [],
            "message": f"Not enough data for forecasting (need at least {MIN_POINTS} points, got {len(series) if series else 0}).",
        }

    from statsmodels.tsa.arima.model import ARIMA

    dates = [item["date"] for item in series]
    y = np.array([item["cases"] for item in series], dtype=float)
    last_date = dt.strptime(dates[-1], "%Y-%m-%d").date()

    model = ARIMA(y, order=(1, 1, 1))
    fitted = model.fit()
    fcast = fitted.get_forecast(steps=horizon)
    pred_mean = fcast.predicted_mean
    conf = fcast.conf_int(alpha=0.05)

    forecast_list = []
    for i in range(horizon):
        day = last_date + timedelta(days=i + 1)
        forecast_list.append({
            "date": day.strftime("%Y-%m-%d"),
            "forecast": float(pred_mean.iloc[i]),
            "lower_ci": float(conf.iloc[i, 0]),
            "upper_ci": float(conf.iloc[i, 1]),
        })
    return {"forecast": forecast_list}

