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

    # Active alerts (status in New/Acknowledged/Investigating)
    alert_filters = Q()
    if disease_id:
        alert_filters &= Q(disease_id=disease_id)
    if location_id:
        alert_filters &= Q(location_id=location_id)

    active_statuses = AlertStatus.objects.filter(
        status_name__in=["New", "Acknowledged", "Investigating"],
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
            "assigned_to_name": task.assigned_to.full_name if task.assigned_to else None,
            "task_status": task.task_status,
            "due_at": task.due_at.isoformat() if task.due_at else None,
        })

    return result

