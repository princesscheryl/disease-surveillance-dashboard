"""
Dashboard API endpoints.

These endpoints provide aggregated data for the monitoring dashboard.
All endpoints require authentication and dashboard access role.
"""

from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from disease_surveillance_dashboard.alerts.services import (
    evaluate_trend_and_generate_alert,
)

from .services import get_cases_timeseries
from .services import get_map_points
from .services import get_recent_alerts
from .services import get_recent_investigations
from .services import get_summary_metrics
from .services import get_top_diseases
from .utils import user_can_access_dashboard


def check_dashboard_access(user):
    """Helper to check dashboard access and return 403 if denied."""
    if not user_can_access_dashboard(user):
        return Response(
            {"error": "You do not have permission to access the dashboard."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def parse_date_param(request, param_name, default=None):
    """
    Parse date parameter from query string and convert to timezone-aware datetime.

    Returns timezone-aware datetime for use in service layer queries.
    """
    date_str = request.query_params.get(param_name)
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            # Convert to timezone-aware datetime at start of day
            return timezone.make_aware(datetime.combine(parsed_date, datetime.min.time()))
        except ValueError:
            return None
    return default


@api_view(["GET"])
def dashboard_summary(request):
    """Get summary KPIs for dashboard overview."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    disease_id = request.query_params.get("disease_id")
    location_id = request.query_params.get("location_id")

    if disease_id:
        try:
            disease_id = int(disease_id)
        except ValueError:
            disease_id = None

    if location_id:
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = None

    metrics = get_summary_metrics(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )

    return Response(metrics)


@api_view(["GET"])
def dashboard_cases_timeseries(request):
    """Get daily case counts for line chart."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    disease_id = request.query_params.get("disease_id")
    location_id = request.query_params.get("location_id")

    if disease_id:
        try:
            disease_id = int(disease_id)
        except ValueError:
            disease_id = None

    if location_id:
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = None

    data = get_cases_timeseries(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )

    return Response(data)


@api_view(["GET"])
def dashboard_top_diseases(request):
    """Get top diseases by case count for bar chart."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    location_id = request.query_params.get("location_id")
    limit = request.query_params.get("limit", 10)

    if location_id:
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = None

    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    data = get_top_diseases(
        start_date=start_date,
        end_date=end_date,
        location_id=location_id,
        limit=limit,
    )

    return Response(data)


@api_view(["GET"])
def dashboard_map_points(request):
    """Get location points with case counts for map."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    disease_id = request.query_params.get("disease_id")

    if disease_id:
        try:
            disease_id = int(disease_id)
        except ValueError:
            disease_id = None

    data = get_map_points(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
    )

    return Response(data)


@api_view(["GET"])
def dashboard_recent_alerts(request):
    """Get recent alerts for operational response table."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    limit = request.query_params.get("limit", 10)
    disease_id = request.query_params.get("disease_id")
    location_id = request.query_params.get("location_id")

    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    if disease_id:
        try:
            disease_id = int(disease_id)
        except ValueError:
            disease_id = None

    if location_id:
        try:
            location_id = int(location_id)
        except ValueError:
            location_id = None

    data = get_recent_alerts(
        limit=limit,
        disease_id=disease_id,
        location_id=location_id,
    )

    return Response(data)


@api_view(["GET"])
def dashboard_recent_investigations(request):
    """Get recent investigation tasks for operational response table."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    limit = request.query_params.get("limit", 10)
    alert_id = request.query_params.get("alert_id")

    try:
        limit = int(limit)
    except ValueError:
        limit = 10

    if alert_id:
        try:
            alert_id = int(alert_id)
        except ValueError:
            alert_id = None

    data = get_recent_investigations(limit=limit, alert_id=alert_id)

    return Response(data)


@api_view(["POST"])
def dashboard_evaluate(request):
    """
    Trigger early warning evaluation for a trend metric.

    Role-restricted: Only ADMIN, ANALYST, HEALTH_OFFICER can trigger evaluation.
    """
    from .utils import user_has_role

    # Check for evaluation permission (more restrictive than dashboard access)
    if not user_has_role(request.user, ["ADMIN", "ANALYST", "HEALTH_OFFICER"]):
        return Response(
            {"error": "You do not have permission to trigger evaluation."},
            status=status.HTTP_403_FORBIDDEN,
        )

    trend_metric_id = request.data.get("trend_metric_id")
    if not trend_metric_id:
        return Response(
            {"error": "trend_metric_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        trend_metric_id = int(trend_metric_id)
    except (ValueError, TypeError):
        return Response(
            {"error": "trend_metric_id must be an integer"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    alert_created, new_alert, cusum_value = evaluate_trend_and_generate_alert(
        trend_metric_id,
    )

    if not alert_created:
        return Response(
            {
                "message": "No alert generated",
                "cusum_value": cusum_value,
                "threshold": 5.0,
            },
            status=status.HTTP_200_OK,
        )

    return Response(
        {
            "message": "Alert generated",
            "alert_id": new_alert.id,
            "cusum_value": cusum_value,
        },
        status=status.HTTP_201_CREATED,
    )

