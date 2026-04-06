"""
Dashboard aggregation services.

This module provides server-side aggregation logic for dashboard metrics.
All data computation happens here to ensure consistency and enable future
Celery-based scheduled updates. Frontend only displays pre-computed data.
"""

from datetime import date
from datetime import datetime
from datetime import timedelta

from django.db.models import Q
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertStatus
from disease_surveillance_dashboard.investigations.models import InvestigationTask
from disease_surveillance_dashboard.reporting.models import DuplicateFlag
from disease_surveillance_dashboard.reporting.models import Report


def get_summary_metrics(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Compute summary KPIs for dashboard overview cards.

    Args:
        start_date: datetime or date object (will be converted to timezone-aware datetime)
        end_date: datetime or date object (will be converted to timezone-aware datetime)
        disease_id: Optional disease filter
        location_id: Optional location filter

    Returns:
        dict: {
            "cases_7d": int,
            "cases_30d": int,
            "reports_7d": int,
            "active_alerts": int
        }
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        # Convert date to datetime at end of day
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        # Convert date to datetime at start of day
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    # Base queryset with filters
    report_filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if disease_id:
        report_filters &= Q(disease_id=disease_id)
    if location_id:
        report_filters &= Q(location_id=location_id)

    reports = Report.objects.filter(report_filters)

    # Cases in last 7 days (sum of case_count)
    cases_7d = reports.filter(
        observed_at__gte=end_date - timedelta(days=7),
    ).aggregate(total=Sum("case_count"))["total"] or 0

    # Cases in last 30 days (sum of case_count)
    cases_30d = reports.aggregate(total=Sum("case_count"))["total"] or 0

    # Reports submitted in last 7 days (count of reports)
    reports_7d = reports.filter(
        observed_at__gte=end_date - timedelta(days=7),
    ).count()

    # Active alerts (status in New/Acknowledged/Under Investigation)
    alert_filters = Q()
    if disease_id:
        alert_filters &= Q(disease_id=disease_id)
    if location_id:
        alert_filters &= Q(location_id=location_id)

    active_statuses = AlertStatus.objects.filter(
        status_name__in=["New", "Acknowledged", "Under Investigation"],
    )
    active_alerts = Alert.objects.filter(
        alert_filters,
        status__in=active_statuses,
    ).count()

    return {
        "cases_7d": int(cases_7d),
        "cases_30d": int(cases_30d),
        "reports_7d": int(reports_7d),
        "active_alerts": int(active_alerts),
    }


def get_cases_timeseries(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Get daily case counts for line chart.

    Args:
        start_date: datetime or date object
        end_date: datetime or date object
        disease_id: Optional disease filter
        location_id: Optional location filter

    Returns:
        list: [{"date": "YYYY-MM-DD", "cases": int}, ...]
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if disease_id:
        filters &= Q(disease_id=disease_id)
    if location_id:
        filters &= Q(location_id=location_id)

    # Group by date and sum case_count per day
    daily_data = (
        Report.objects.filter(filters)
        .annotate(date=TruncDate("observed_at"))
        .values("date")
        .annotate(cases=Sum("case_count"))
        .order_by("date")
    )

    # Convert to list of dicts with string dates
    result = []
    for item in daily_data:
        result.append({
            "date": item["date"].strftime("%Y-%m-%d"),
            "cases": int(item["cases"]),
        })

    return result


def get_top_diseases(start_date=None, end_date=None, location_id=None, limit=10):
    """
    Get top diseases by case count for bar chart.

    Args:
        start_date: datetime or date object
        end_date: datetime or date object
        location_id: Optional location filter
        limit: Maximum number of diseases to return

    Returns:
        list: [{"disease_id": int, "disease_name": str, "cases": int}, ...]
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if location_id:
        filters &= Q(location_id=location_id)

    # Group by disease and sum case_count
    disease_data = (
        Report.objects.filter(filters)
        .values("disease_id", "disease__disease_name")
        .annotate(cases=Sum("case_count"))
        .order_by("-cases")[:limit]
    )

    result = []
    for item in disease_data:
        result.append({
            "disease_id": item["disease_id"],
            "disease_name": item["disease__disease_name"],
            "cases": int(item["cases"]),
        })

    return result


def get_map_points(start_date=None, end_date=None, disease_id=None):
    """
    Get location points with case counts and alert info for map.

    Only includes locations with valid coordinates.

    Args:
        start_date: datetime or date object
        end_date: datetime or date object
        disease_id: Optional disease filter

    Returns:
        list: [{
            "location_id": int,
            "district_name": str,
            "area_name": str,
            "latitude": float,
            "longitude": float,
            "cases": int,
            "has_alert": bool,
            "alert_severity": str or None,
            "alert_status": str or None
        }, ...]
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    from reference_data.models import Location

    # Get locations with coordinates
    locations = Location.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False,
        is_active=True,
    )

    if disease_id:
        # Filter locations that have reports for this disease
        locations = locations.filter(
            reports__disease_id=disease_id,
            reports__observed_at__gte=start_date,
            reports__observed_at__lte=end_date,
        ).distinct()

    result = []

    for location in locations:
        # Get case count for this location in date range
        report_filters = Q(
            location_id=location.id,
            observed_at__gte=start_date,
            observed_at__lte=end_date,
        )
        if disease_id:
            report_filters &= Q(disease_id=disease_id)

        cases = Report.objects.filter(report_filters).aggregate(
            total=Sum("case_count"),
        )["total"] or 0

        # Check for active alerts
        alert_filters = Q(location_id=location.id)
        if disease_id:
            alert_filters &= Q(disease_id=disease_id)

        active_statuses = AlertStatus.objects.filter(
            status_name__in=["New", "Acknowledged", "Investigating"],
        )
        alert = Alert.objects.filter(
            alert_filters,
            status__in=active_statuses,
        ).select_related("status").first()

        result.append({
            "location_id": location.id,
            "district_name": location.district_name,
            "area_name": location.area_name or "",
            "latitude": float(location.latitude),
            "longitude": float(location.longitude),
            "cases": int(cases),
            "has_alert": alert is not None,
            "alert_severity": alert.severity_level if alert else None,
            "alert_status": alert.status.status_name if alert else None,
        })

    return result


def get_recent_alerts(limit=10, disease_id=None, location_id=None):
    """
    Get recent alerts for operational response table.

    Returns:
        list: [{
            "id": int,
            "disease_name": str,
            "location_name": str,
            "severity_level": str,
            "status_name": str,
            "created_at": str
        }, ...]
    """
    filters = Q()
    if disease_id:
        filters &= Q(disease_id=disease_id)
    if location_id:
        filters &= Q(location_id=location_id)

    alerts = (
        Alert.objects.filter(filters)
        .select_related("disease", "location", "status")
        .order_by("-created_at")[:limit]
    )

    result = []
    for alert in alerts:
        location_name = alert.location.district_name
        if alert.location.area_name:
            location_name = f"{location_name} - {alert.location.area_name}"

        result.append({
            "id": alert.id,
            "disease_name": alert.disease.disease_name,
            "location_name": location_name,
            "severity_level": alert.severity_level,
            "status_name": alert.status.status_name,
            "status_id": alert.status_id,
            "created_at": alert.created_at.isoformat(),
        })

    return result


def get_recent_investigations(limit=10, alert_id=None):
    """
    Get recent investigation tasks for operational response table.

    Returns:
        list: [{
            "id": int,
            "alert_id": int,
            "assigned_to_name": str or None,
            "task_status": str,
            "due_at": str or None
        }, ...]
    """
    filters = Q()
    if alert_id:
        filters &= Q(alert_id=alert_id)

    tasks = (
        InvestigationTask.objects.filter(filters)
        .select_related("alert", "assigned_to")
        .order_by("-created_at")[:limit]
    )

    result = []
    for task in tasks:
        result.append({
            "id": task.id,  # Use default pk field, not task_id
            "alert_id": task.alert.id,
            "assigned_to_name": task.assigned_to.name if task.assigned_to else None,
            "task_status": task.task_status,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        })

    return result


# ---------------------------------------------------------------------------
# Situation Overview
# ---------------------------------------------------------------------------

def get_situation_overview(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Compute week-over-week epidemiological situation metrics.

    Compares total cases in the most recent 7-day window against the preceding
    7-day window. The resulting growth factor and percentage change are used to
    assign a signal status that drives the alerting colour in the UI.

    Signal thresholds are intentionally conservative so that a Watch state
    prompts review before a full Alert is declared.

    Returns:
        dict with keys:
            current_cases_7d (int)
            previous_cases_7d (int)
            wow_pct_change (float | None)  -- None when baseline is zero
            growth_factor (float | None)   -- None when baseline is zero
            signal_status (str)            -- "Normal" | "Watch" | "Alert"
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    base_filters = Q()
    if disease_id:
        base_filters &= Q(disease_id=disease_id)
    if location_id:
        base_filters &= Q(location_id=location_id)

    # Current window: most recent 7 days up to end_date
    current_start = end_date - timedelta(days=7)
    current_qs = Report.objects.filter(
        base_filters,
        observed_at__gte=current_start,
        observed_at__lte=end_date,
    )
    current_cases = current_qs.aggregate(total=Sum("case_count"))["total"] or 0

    # Previous window: the 7 days immediately before the current window
    previous_end = current_start
    previous_start = previous_end - timedelta(days=7)
    previous_qs = Report.objects.filter(
        base_filters,
        observed_at__gte=previous_start,
        observed_at__lt=previous_end,
    )
    previous_cases = previous_qs.aggregate(total=Sum("case_count"))["total"] or 0

    # Percentage change and growth factor; guard against division by zero
    if previous_cases > 0:
        wow_pct_change = round(((current_cases - previous_cases) / previous_cases) * 100, 1)
        growth_factor  = round(current_cases / previous_cases, 2)
    else:
        wow_pct_change = None
        growth_factor  = None

    # Signal classification based on agreed epidemiological thresholds
    signal_status = "Normal"
    if wow_pct_change is not None:
        if wow_pct_change >= 100 or (growth_factor is not None and growth_factor >= 2.0):
            signal_status = "Alert"
        elif wow_pct_change >= 50 or (growth_factor is not None and growth_factor >= 1.5):
            signal_status = "Watch"
    # When there is no previous baseline we cannot classify; leave as Normal
    # so the dashboard does not falsely alarm on the first week of data.

    # Pull the population figures for every location that had cases in the
    # current window.  We sum the population across those locations so we
    # can express case counts as a rate per 100k people.  If no population
    # data has been imported yet, both rate fields will just be None.
    current_location_ids = list(
        current_qs.values_list("location_id", flat=True).distinct()
    )
    total_population = 0
    if current_location_ids:
        from reference_data.models import Location  # local import avoids circular dependency
        pop_agg = (
            Location.objects
            .filter(id__in=current_location_ids, population__isnull=False)
            .aggregate(total=Sum("population"))
        )
        total_population = pop_agg["total"] or 0

    if total_population > 0:
        incidence_rate_current  = round((current_cases  / total_population) * 100_000, 1)
        incidence_rate_previous = round((previous_cases / total_population) * 100_000, 1)
    else:
        incidence_rate_current  = None
        incidence_rate_previous = None

    return {
        "current_cases_7d":       int(current_cases),
        "previous_cases_7d":      int(previous_cases),
        "wow_pct_change":         wow_pct_change,
        "growth_factor":          growth_factor,
        "signal_status":          signal_status,
        "incidence_rate_current":  incidence_rate_current,
        "incidence_rate_previous": incidence_rate_previous,
        "total_population":        int(total_population) if total_population else None,
    }


# ---------------------------------------------------------------------------
# Detection Metrics (moving average + CUSUM series)
# ---------------------------------------------------------------------------

def _simple_moving_average(values, window):
    """
    Compute a simple moving average over a list of numeric values.

    Each position i in the result is the mean of values[max(0, i-window+1):i+1].
    This deliberately avoids numpy so the service has no external dependencies.

    Args:
        values: list of numbers
        window: integer lookback size

    Returns:
        list of floats, same length as values
    """
    result = []
    for i in range(len(values)):
        start  = max(0, i - window + 1)
        window_values = values[start : i + 1]
        result.append(sum(window_values) / len(window_values))
    return result


def get_detection_metrics(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Return the statistical detection series used in the Analytics page.

    Computes:
      - A 7-day simple moving average over the daily case counts in the
        requested date range.
      - A CUSUM series using the 30-day rolling average as the baseline.
        The CUSUM resets to zero where observed cases fall below baseline,
        which is the standard one-sided upper CUSUM formulation for detecting
        upward shifts in disease incidence.
      - The list of dates where CUSUM exceeds the configured threshold
        (disease/location settings in admin, default 5.0).

    Args:
        start_date: optional timezone-aware datetime or date
        end_date:   optional timezone-aware datetime or date
        disease_id: optional int
        location_id: optional int

    Returns:
        dict with keys:
            dates (list[str])
            daily_cases (list[int])
            moving_avg_7d (list[float])
            cusum_series (list[float])
            cusum_threshold (float)
            trigger_points (list[str])  -- dates where cusum >= threshold
            baseline_avg (float | None) -- 30-day prior average used as baseline
            message (str | None)        -- populated when data is insufficient
    """
    from disease_surveillance_dashboard.analytics.services import compute_cusum

    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if disease_id:
        filters &= Q(disease_id=disease_id)
    if location_id:
        filters &= Q(location_id=location_id)

    daily_qs = (
        Report.objects.filter(filters)
        .annotate(day=TruncDate("observed_at"))
        .values("day")
        .annotate(cases=Sum("case_count"))
        .order_by("day")
    )

    dates       = []
    daily_cases = []
    for row in daily_qs:
        dates.append(row["day"].strftime("%Y-%m-%d"))
        daily_cases.append(int(row["cases"]))

    cusum_threshold = 5.0
    cusum_k = 0.5
    use_seasonal = False
    if disease_id and location_id:
        from disease_surveillance_dashboard.alerts.models import resolve_cusum_config

        cusum_threshold, cusum_k, use_seasonal, _ = resolve_cusum_config(
            disease_id,
            location_id,
        )

    if len(daily_cases) < 3:
        return {
            "dates":           dates,
            "daily_cases":     daily_cases,
            "moving_avg_7d":   [],
            "cusum_series":    [],
            "cusum_threshold": cusum_threshold,
            "trigger_points":  [],
            "baseline_avg":    None,
            "message":         "Insufficient data for statistical detection (minimum 3 days required).",
        }

    # 7-day simple moving average over the selected window
    moving_avg_7d = [round(v, 2) for v in _simple_moving_average(daily_cases, window=7)]

    # Compute baseline as average daily cases in the 30 days prior to start_date.
    # If no prior data exist we fall back to the mean of the current window.
    prior_start = start_date - timedelta(days=30)
    prior_filters = Q(observed_at__gte=prior_start, observed_at__lt=start_date)
    if disease_id:
        prior_filters &= Q(disease_id=disease_id)
    if location_id:
        prior_filters &= Q(location_id=location_id)

    prior_total = (
        Report.objects.filter(prior_filters)
        .aggregate(total=Sum("case_count"))["total"] or 0
    )
    baseline_avg = round(prior_total / 30, 4) if prior_total > 0 else round(
        sum(daily_cases) / len(daily_cases), 4
    )

    cusum_series = []
    cusum_current = 0.0
    for idx, cases in enumerate(daily_cases):
        if use_seasonal and idx < len(moving_avg_7d):
            baseline_day = moving_avg_7d[idx]
            if baseline_day is None or baseline_day <= 0:
                baseline_day = baseline_avg
        else:
            baseline_day = baseline_avg
        cusum_current = compute_cusum(
            observed_value=cases,
            baseline_value=float(baseline_day),
            previous_cusum=cusum_current,
            k=cusum_k,
        )
        cusum_series.append(round(cusum_current, 4))

    trigger_points = [
        dates[i]
        for i, v in enumerate(cusum_series)
        if v >= cusum_threshold
    ]

    return {
        "dates":           dates,
        "daily_cases":     daily_cases,
        "moving_avg_7d":   moving_avg_7d,
        "cusum_series":    cusum_series,
        "cusum_threshold": cusum_threshold,
        "trigger_points":  trigger_points,
        "baseline_avg":    float(baseline_avg),
        "message":         None,
    }


# ---------------------------------------------------------------------------
# Data Quality
# ---------------------------------------------------------------------------

def get_data_quality(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Assess the quality of submitted reports in the requested date range.

    Metrics returned:
      - reporting_delay_avg_hours:    Mean lag between observation and submission.
      - reporting_delay_median_hours: Median lag (computed in Python from the
                                      full queryset to avoid raw SQL).
      - missingness_summary:          Proportion of UNKNOWN values per field
                                      as a fraction 0.0-1.0.
      - duplicate_flags_count:        Number of flagged duplicate reports.
      - completeness_score:           Composite 0-100 score; penalties applied
                                      for high missingness, reporting delay, and
                                      duplicate flags.

    The completeness score is intended as a high-level indicator for field
    coordinators, not a strict audit measure.

    Returns:
        dict
    """
    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if disease_id:
        filters &= Q(disease_id=disease_id)
    if location_id:
        filters &= Q(location_id=location_id)

    reports_qs = Report.objects.filter(filters)
    total = reports_qs.count()

    if total == 0:
        return {
            "total_reports":               0,
            "reporting_delay_avg_hours":   None,
            "reporting_delay_median_hours": None,
            "missingness_summary": {
                "sex":            0.0,
                "age_group":      0.0,
                "severity_level": 0.0,
            },
            "duplicate_flags_count": 0,
            "completeness_score":    100,
            "message": "No reports found for the selected period.",
        }

    # Reporting delay: pull both timestamps and compute the difference in Python.
    # Django ORM datetime subtraction returns a timedelta object in most backends,
    # not a numeric value, so we cannot reliably annotate a FloatField directly.
    # Iterating here is fine because this query is bounded by the date range filter.
    raw_pairs = reports_qs.values_list("observed_at", "submitted_at")
    delay_values_hours = []
    for observed, submitted in raw_pairs:
        if observed is None or submitted is None:
            continue
        delta = submitted - observed
        hours = delta.total_seconds() / 3600.0
        if hours >= 0:
            delay_values_hours.append(hours)

    if delay_values_hours:
        avg_delay = round(sum(delay_values_hours) / len(delay_values_hours), 2)
        sorted_delays = sorted(delay_values_hours)
        mid = len(sorted_delays) // 2
        if len(sorted_delays) % 2 == 1:
            median_delay = round(sorted_delays[mid], 2)
        else:
            median_delay = round((sorted_delays[mid - 1] + sorted_delays[mid]) / 2, 2)
    else:
        avg_delay    = None
        median_delay = None

    # Missingness: count reports where each field is "UNKNOWN"
    unknown_sex      = reports_qs.filter(sex="UNKNOWN").count()
    unknown_age      = reports_qs.filter(age_group="UNKNOWN").count()
    unknown_severity = reports_qs.filter(severity_level="UNKNOWN").count()

    missingness_summary = {
        "sex":            round(unknown_sex      / total, 4),
        "age_group":      round(unknown_age      / total, 4),
        "severity_level": round(unknown_severity / total, 4),
    }

    # Duplicate flags: count records linked to reports in the date range
    dup_count = DuplicateFlag.objects.filter(
        report__in=reports_qs,
    ).count()

    # Completeness score: start at 100 and apply penalties
    score = 100
    missingness_threshold = 0.30  # 30 percent

    if missingness_summary["sex"]            > missingness_threshold: score -= 20
    if missingness_summary["age_group"]      > missingness_threshold: score -= 20
    if missingness_summary["severity_level"] > missingness_threshold: score -= 20
    if avg_delay is not None and avg_delay > 48:                       score -= 20
    if dup_count > 0:                                                  score -= 20

    score = max(0, min(100, score))

    return {
        "total_reports":               total,
        "reporting_delay_avg_hours":   avg_delay,
        "reporting_delay_median_hours": median_delay,
        "missingness_summary":         missingness_summary,
        "duplicate_flags_count":       dup_count,
        "completeness_score":          score,
        "message":                     None,
    }


# ---------------------------------------------------------------------------
# District-Level Incidence Summary
# ---------------------------------------------------------------------------

def get_district_summary(start_date=None, end_date=None, disease_id=None, location_id=None):
    """
    Aggregate case counts and incidence rates by district for the given filters.

    We group reports by Location (i.e. district) and join in the population
    figure so we can calculate how many cases there were per 100,000 people.
    Districts that have no population data still appear in the results — they
    just won't have a rate.  The list is sorted so high-incidence districts
    bubble up to the top, with unpopulated districts at the end.

    Returns:
        list of dicts:
            district         (str)
            location_id      (int)
            cases            (int)
            population       (int | None)
            incidence_per_100k (float | None)
    """
    from reference_data.models import Location  # local import avoids circular dependency

    if end_date is None:
        end_date = timezone.now()
    elif isinstance(end_date, date) and not isinstance(end_date, datetime):
        end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))

    if start_date is None:
        start_date = end_date - timedelta(days=30)
    elif isinstance(start_date, date) and not isinstance(start_date, datetime):
        start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))

    filters = Q(observed_at__gte=start_date, observed_at__lte=end_date)
    if disease_id:
        filters &= Q(disease_id=disease_id)
    if location_id:
        filters &= Q(location_id=location_id)

    # Sum case_count per location so we get one row per district regardless
    # of how many individual report records exist.
    rows = (
        Report.objects.filter(filters)
        .values("location_id", "location__district_name")
        .annotate(cases=Sum("case_count"))
        .order_by("location_id")
    )

    # Pull populations in one query and build a fast lookup dict.
    location_ids = [r["location_id"] for r in rows]
    pop_lookup = {}
    if location_ids:
        for loc in Location.objects.filter(id__in=location_ids).only("id", "population"):
            pop_lookup[loc.id] = loc.population  # will be None if not imported yet

    result = []
    for row in rows:
        loc_id    = row["location_id"]
        cases     = int(row["cases"])
        population = pop_lookup.get(loc_id)  # None if location not found or no data

        # We only calculate the rate when population is a positive integer.
        # Division by zero or by None would produce garbage, so we guard here.
        if population and population > 0:
            incidence = round((cases / population) * 100_000, 1)
        else:
            incidence = None

        result.append({
            "district":           row["location__district_name"],
            "location_id":        loc_id,
            "cases":              cases,
            "population":         population,
            "incidence_per_100k": incidence,
        })

    # Sort by incidence rate descending so the hottest districts come first.
    # Districts with no population data go to the bottom since None sorts
    # differently depending on Python version, so we handle it explicitly.
    result.sort(
        key=lambda x: (x["incidence_per_100k"] is None, -(x["incidence_per_100k"] or 0))
    )

    return result
