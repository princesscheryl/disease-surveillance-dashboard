"""
Dashboard API endpoints.

These endpoints provide aggregated data for the monitoring dashboard.
All endpoints require authentication and dashboard access role.
"""

import json
import os
from datetime import datetime

from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from disease_surveillance_dashboard.alerts.services import (
    evaluate_trend_and_generate_alert,
)
from disease_surveillance_dashboard.analytics.services import (
    compute_arima_forecast,
    compute_isolation_forest_anomalies,
)

from .services import get_cases_timeseries
from .services import get_data_quality
from .services import get_detection_metrics
from .services import get_district_summary
from .services import get_map_points
from .services import get_recent_alerts
from .services import get_recent_investigations
from .services import get_situation_overview
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
def dashboard_anomalies(request):
    """Get Isolation Forest anomaly detection results for the cases time-series."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    disease_id = request.query_params.get("disease_id")
    location_id = request.query_params.get("location_id")
    contamination = request.query_params.get("contamination", "0.05")

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

    try:
        contamination = float(contamination)
        if not (0 < contamination <= 0.5):
            contamination = 0.05
    except (ValueError, TypeError):
        contamination = 0.05

    series = get_cases_timeseries(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
    data = compute_isolation_forest_anomalies(
        series,
        contamination=contamination,
        random_state=42,
    )
    return Response(data)


@api_view(["GET"])
def dashboard_forecast(request):
    """Get ARIMA forecast for the cases time-series."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date = parse_date_param(request, "start_date")
    end_date = parse_date_param(request, "end_date")
    disease_id = request.query_params.get("disease_id")
    location_id = request.query_params.get("location_id")
    horizon = request.query_params.get("horizon", "14")

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

    try:
        horizon = int(horizon)
        if horizon < 1:
            horizon = 14
    except (ValueError, TypeError):
        horizon = 14

    series = get_cases_timeseries(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
    data = compute_arima_forecast(series, horizon=horizon, seasonal=False)
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


@api_view(["GET"])
def dashboard_situation_overview(request):
    """
    Return week-over-week situation metrics.

    Intended for the Situation Overview KPI row shown at the top of both
    the Overview and Analytics pages. The signal_status field drives the
    colour-coded status badge in the UI.
    """
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date  = parse_date_param(request, "start_date")
    end_date    = parse_date_param(request, "end_date")
    disease_id  = request.query_params.get("disease_id")
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

    data = get_situation_overview(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
    return Response(data)


@api_view(["GET"])
def dashboard_detection_metrics(request):
    """
    Return the moving average and CUSUM series for statistical outbreak detection.

    The CUSUM series and trigger point list are used to render the two-panel
    Statistical Detection section on the Analytics page. When data are
    insufficient the service returns a message field that the UI displays
    instead of empty charts.
    """
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date  = parse_date_param(request, "start_date")
    end_date    = parse_date_param(request, "end_date")
    disease_id  = request.query_params.get("disease_id")
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

    data = get_detection_metrics(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
    return Response(data)


@api_view(["GET"])
def dashboard_data_quality(request):
    """
    Return data quality metrics for the selected report set.

    The completeness score and missingness breakdown give field coordinators
    an at-a-glance view of reporting discipline without exposing individual
    report data.
    """
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date  = parse_date_param(request, "start_date")
    end_date    = parse_date_param(request, "end_date")
    disease_id  = request.query_params.get("disease_id")
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

    data = get_data_quality(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
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


@api_view(["GET"])
def dashboard_district_summary(request):
    """
    Return case counts and incidence rates (per 100k) aggregated by district.

    Districts with no population data are still included — they just won't
    have an incidence_per_100k value.  The list is sorted high-to-low by
    incidence rate so the dashboard can display it directly.
    """
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    start_date  = parse_date_param(request, "start_date")
    end_date    = parse_date_param(request, "end_date")
    disease_id  = request.query_params.get("disease_id")
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

    data = get_district_summary(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )
    return Response(data)


@api_view(["GET"])
def dashboard_choropleth_data(request):
    """
    Return GeoJSON for Greater Accra districts with case counts and
    incidence rates attached to each feature so the frontend can draw
    a choropleth map.

    We load the static GeoJSON once, then merge in the district summary
    from get_district_summary().  If a district in the GeoJSON has no
    reports in the date range, we still include it with cases=0 and
    no rate — that way the map shows all districts, not just the ones
    with data.
    """
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    geojson_path = os.path.join(
        settings.BASE_DIR,
        "disease_surveillance_dashboard",
        "static",
        "geojson",
        "greater_accra_districts.geojson",
    )

    if not os.path.isfile(geojson_path):
        return Response(
            {"error": "GeoJSON file not found. Run collectstatic or check static path."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        with open(geojson_path, encoding="utf-8") as f:
            geojson = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        return Response(
            {"error": f"Could not read or parse GeoJSON: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Same filters as the rest of the dashboard so the map and tables stay in sync
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

    summary = get_district_summary(
        start_date=start_date,
        end_date=end_date,
        disease_id=disease_id,
        location_id=location_id,
    )

    # Build a lookup by district name so we can attach data to each GeoJSON
    # feature.  If multiple locations share a district name (e.g. sub-areas),
    # we take the first match — get_district_summary returns one row per
    # location, so we key by district name and keep the first we see.
    by_district = {}
    for row in summary:
        name = row.get("district")
        if name and name not in by_district:
            by_district[name] = {
                "cases": row.get("cases", 0),
                "population": row.get("population"),
                "incidence_per_100k": row.get("incidence_per_100k"),
            }

    # Walk the features and add our stats to each one.  We're matching on
    # shapeName; if a district has no data we still add the keys so the
    # frontend can rely on them being present.
    for feature in geojson.get("features", []):
        props = feature.get("properties") or {}
        shape_name = props.get("shapeName")
        data = by_district.get(shape_name) if shape_name else None

        if data is not None:
            props["cases"] = data["cases"]
            props["population"] = data["population"]
            props["incidence_per_100k"] = data["incidence_per_100k"]
        else:
            props["cases"] = 0
            props["population"] = None
            props["incidence_per_100k"] = None

        feature["properties"] = props

    return Response(geojson)
