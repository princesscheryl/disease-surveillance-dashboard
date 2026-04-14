import csv
import json
import os
from datetime import datetime

from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from disease_surveillance_dashboard.alerts.services import (
    evaluate_trend_and_generate_alert,
)
from disease_surveillance_dashboard.exports.models import AuditLog
from disease_surveillance_dashboard.exports.models import record_audit_event
from disease_surveillance_dashboard.users.models import InAppNotification
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
from .utils import user_has_role
from .utils import user_is_admin

OFFICER_ROLES = [
    "Public Health Officer",
    "System Administrator",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
]

ACTION_LABELS = {
    "REPORT_SUBMITTED": "Report submitted",
    "REPORT_DRAFT_SAVED": "Draft saved",
    "REPORT_CASE_COUNT_CHANGED": "Case count updated",
    "REPORT_STATUS_CHANGED": "Report status changed",
    "ALERT_CREATED": "Alert generated",
    "ALERT_STATUS_CHANGED": "Alert status changed",
    "ALERT_ESCALATED": "Alert escalated",
    "INVESTIGATION_TASK_CREATED": "Investigation task created",
    "INVESTIGATION_TASK_UPDATED": "Investigation task updated",
    "DATA_EXPORT": "Data exported",
}


def check_dashboard_access(user):
    """Helper to check dashboard access and return 403 if denied."""
    if not user_can_access_dashboard(user):
        return Response(
            {"error": "You do not have permission to access the dashboard."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def check_officer_access(user):
    if not user or not user.is_authenticated:
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if not user_has_role(user, OFFICER_ROLES):
        return Response(
            {"error": "You do not have permission to access this."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def check_admin_access(user):
    if not user or not user.is_authenticated:
        return Response(
            {"error": "Authentication required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    if not user_is_admin(user):
        return Response(
            {"error": "Administrator access required."},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def parse_date_param(request, param_name, default=None):
    date_str = request.query_params.get(param_name)
    if date_str:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
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
def dashboard_assignable_users(request):
    """Return active users for the Investigate task assignment dropdown."""
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    from django.contrib.auth import get_user_model

    User = get_user_model()
    users = User.objects.filter(is_active=True).order_by("email").values("id", "email")
    data = list(users)
    return Response(data)


@api_view(["GET"])
def dashboard_alert_statuses(request):
    """Return alert statuses for status update dropdowns. Officer access."""
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from disease_surveillance_dashboard.alerts.models import AlertStatus

    statuses = list(
        AlertStatus.objects.values("id", "status_name").order_by("status_name")
    )
    return Response(statuses)


@api_view(["POST"])
def dashboard_alert_update_status(request, alert_id):
    """
    Update an alert's status. Officer and Admin roles only.
    If notes are provided, creates an AlertNote record.
    """
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from disease_surveillance_dashboard.alerts.models import Alert
    from disease_surveillance_dashboard.alerts.models import AlertNote
    from disease_surveillance_dashboard.alerts.models import AlertStatus

    alert = Alert.objects.filter(pk=alert_id).select_related("status").first()
    if not alert:
        return Response(
            {"error": "Alert not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    status_id = request.data.get("status_id")
    if not status_id:
        return Response(
            {"error": "status_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        new_status = AlertStatus.objects.get(pk=status_id)
    except AlertStatus.DoesNotExist:
        return Response(
            {"error": "Invalid status_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    notes = (request.data.get("notes") or "").strip()
    old_status_name = alert.status.status_name
    alert.status = new_status
    alert.save()

    record_audit_event(
        actor=request.user,
        action_type="ALERT_STATUS_CHANGED",
        entity_type="Alert",
        entity_id=str(alert.id),
        details={
            "from_status": old_status_name,
            "to_status": new_status.status_name,
            "notes": notes or None,
        },
    )

    if notes:
        AlertNote.objects.create(
            alert=alert,
            noted_by=request.user,
            note_text=notes,
        )

    return Response({
        "success": True,
        "message": f"Alert status updated to {new_status.status_name}.",
        "status_name": new_status.status_name,
        "status_id": new_status.id,
    })


@api_view(["GET"])
def dashboard_alert_details(request, alert_id):
    """
    Return full alert details for the Alert Details modal.
    Officer and Admin only. Includes related reports, tasks, notes, and status history.
    """
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from disease_surveillance_dashboard.alerts.models import Alert
    from disease_surveillance_dashboard.alerts.models import AlertNote
    from disease_surveillance_dashboard.reporting.models import Report
    from disease_surveillance_dashboard.investigations.models import InvestigationTask

    alert = (
        Alert.objects.filter(pk=alert_id)
        .select_related("disease", "location", "status")
        .first()
    )
    if not alert:
        return Response(
            {"error": "Alert not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    # Related reports: same disease + location, observed in alert period
    reports = (
        Report.objects.filter(
            disease=alert.disease,
            location=alert.location,
            observed_at__gte=alert.period_start,
            observed_at__lte=alert.period_end,
        )
        .select_related("status", "reported_by")
        .order_by("-observed_at")
    )
    related_reports = []
    total_cases = 0
    for r in reports:
        total_cases += r.case_count
        related_reports.append({
            "id": r.id,
            "case_count": r.case_count,
            "observed_at": r.observed_at.isoformat(),
            "reported_by_email": r.reported_by.email if r.reported_by else None,
            "status_name": r.status.status_name if r.status else None,
        })

    # Investigation tasks for this alert
    tasks = (
        InvestigationTask.objects.filter(alert=alert)
        .select_related("assigned_to")
        .order_by("-created_at")
    )
    investigation_tasks = [
        {
            "id": t.id,
            "assigned_to_email": t.assigned_to.email if t.assigned_to else None,
            "task_status": t.task_status,
            "due_at": t.due_at.isoformat() if t.due_at else None,
        }
        for t in tasks
    ]

    # Alert notes (newest first)
    notes_qs = AlertNote.objects.filter(alert=alert).select_related("noted_by").order_by("-noted_at")
    alert_notes = [
        {
            "note_text": n.note_text,
            "noted_by_email": n.noted_by.email if n.noted_by else None,
            "noted_at": n.noted_at.isoformat(),
        }
        for n in notes_qs
    ]

    # Status history: Created (New) + current status (exact change time not stored)
    status_history = [
        {"status_name": "New", "at": alert.created_at.isoformat(), "actor": None},
    ]
    if alert.status.status_name != "New":
        status_history.append({
            "status_name": alert.status.status_name,
            "at": alert.created_at.isoformat(),
            "actor": None,
        })

    location_name = alert.location.district_name
    if alert.location.area_name:
        location_name = f"{location_name} - {alert.location.area_name}"

    return Response({
        "id": alert.id,
        "disease_name": alert.disease.disease_name,
        "location_name": location_name,
        "severity_level": alert.severity_level,
        "status_name": alert.status.status_name,
        "created_at": alert.created_at.isoformat(),
        "period_start": alert.period_start.isoformat(),
        "period_end": alert.period_end.isoformat(),
        "baseline_value": float(alert.baseline_value),
        "observed_value": float(alert.observed_value),
        "threshold_rule": alert.threshold_rule or "",
        "related_reports": related_reports,
        "related_reports_total_cases": total_cases,
        "investigation_tasks": investigation_tasks,
        "alert_notes": alert_notes,
        "status_history": status_history,
    })


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


# ---------------------------------------------------------------------------
# Report Verification (Officer-only)
# ---------------------------------------------------------------------------

@api_view(["GET"])
def dashboard_review_reports(request):
    """
    List all reports for officer verification. Supports filters and pagination.
    Officer and Admin roles only.
    """
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from django.db.models import Q

    from disease_surveillance_dashboard.reporting.models import Report
    from disease_surveillance_dashboard.reporting.models import ReportStatus

    queryset = (
        Report.objects.select_related("disease", "location", "reported_by", "status")
        .order_by("-submitted_at")
    )

    status_filter = request.query_params.get("status")
    if status_filter:
        if status_filter == "pending":
            queryset = queryset.filter(
                Q(status__status_name="SUBMITTED") | Q(status__status_name="Pending Review")
            )
        else:
            queryset = queryset.filter(status__status_name=status_filter)

    disease_id = request.query_params.get("disease_id")
    if disease_id:
        try:
            queryset = queryset.filter(disease_id=int(disease_id))
        except ValueError:
            pass

    location_id = request.query_params.get("location_id")
    if location_id:
        try:
            queryset = queryset.filter(location_id=int(location_id))
        except ValueError:
            pass

    start_date = parse_date_param(request, "start_date")
    if start_date:
        queryset = queryset.filter(observed_at__gte=start_date)

    end_date = parse_date_param(request, "end_date")
    if end_date:
        end_dt = timezone.make_aware(
            datetime.combine(end_date.date(), datetime.max.time())
        )
        queryset = queryset.filter(observed_at__lte=end_dt)

    page_size = min(int(request.query_params.get("page_size", 50)), 100)
    page = int(request.query_params.get("page", 1))
    start = (page - 1) * page_size
    end = start + page_size
    total = queryset.count()
    reports = queryset[start:end]

    results = []
    for r in reports:
        location_name = r.location.district_name
        if r.location.area_name:
            location_name = f"{location_name} - {r.location.area_name}"
        results.append({
            "id": r.id,
            "disease_name": r.disease.disease_name,
            "location_name": location_name,
            "case_count": r.case_count,
            "reported_by_email": r.reported_by.email if r.reported_by else None,
            "observed_at": r.observed_at.isoformat() if r.observed_at else None,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "status_name": r.status.status_name if r.status else None,
            "status_id": r.status_id,
        })

    statuses = list(
        ReportStatus.objects.values("id", "status_name").order_by("status_name")
    )

    return Response({
        "results": results,
        "count": total,
        "page": page,
        "page_size": page_size,
        "statuses": statuses,
    })


@api_view(["GET"])
def dashboard_report_details(request, report_id):
    """
    Return full report details for the officer review modal.
    Officer and Admin roles only.
    """
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from disease_surveillance_dashboard.reporting.models import Report

    report = (
        Report.objects.filter(pk=report_id)
        .select_related("disease", "location", "reported_by", "status")
        .first()
    )
    if not report:
        return Response(
            {"error": "Report not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    location_name = report.location.district_name
    if report.location.area_name:
        location_name = f"{location_name} - {report.location.area_name}"

    return Response({
        "id": report.id,
        "disease_name": report.disease.disease_name,
        "location_name": location_name,
        "case_count": report.case_count,
        "reported_by_email": report.reported_by.email if report.reported_by else None,
        "observed_at": report.observed_at.isoformat() if report.observed_at else None,
        "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
        "report_source": report.report_source or None,
        "status_name": report.status.status_name if report.status else None,
        "status_id": report.status_id,
        "sex": report.sex or None,
        "age_group": report.age_group or None,
        "severity_level": report.severity_level or None,
        "case_notes": report.case_notes or "",
    })


@api_view(["POST"])
def dashboard_report_update_status(request, report_id):
    """
    Update a report's status (Verify, Duplicate, Invalid, Pending).
    Officer and Admin roles only.
    """
    access_check = check_officer_access(request.user)
    if access_check:
        return access_check

    from disease_surveillance_dashboard.reporting.models import Report
    from disease_surveillance_dashboard.reporting.models import ReportStatus

    report = Report.objects.filter(pk=report_id).select_related("status").first()
    if not report:
        return Response(
            {"error": "Report not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    status_id = request.data.get("status_id")
    if not status_id:
        return Response(
            {"error": "status_id is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        new_status = ReportStatus.objects.get(pk=status_id)
    except ReportStatus.DoesNotExist:
        return Response(
            {"error": "Invalid status_id."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    old_status_name = report.status.status_name if report.status_id else None
    report.status = new_status
    report.save()

    record_audit_event(
        actor=request.user,
        action_type="REPORT_STATUS_CHANGED",
        entity_type="Report",
        entity_id=str(report.id),
        details={
            "from_status": old_status_name,
            "to_status": new_status.status_name,
        },
    )

    return Response({
        "success": True,
        "message": f"Report status updated to {new_status.status_name}.",
        "status_name": new_status.status_name,
        "status_id": new_status.id,
    })


@api_view(["GET"])
def dashboard_notifications_list(request):
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    qs = (
        InAppNotification.objects.filter(recipient=request.user)
        .order_by("-created_at")[:100]
    )
    data = [
        {
            "id": n.id,
            "kind": n.kind,
            "title": n.title,
            "body": n.body,
            "link_path": n.link_path,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "created_at": n.created_at.isoformat(),
        }
        for n in qs
    ]
    return Response({"results": data})


@api_view(["POST"])
def dashboard_notifications_mark_read(request):
    access_check = check_dashboard_access(request.user)
    if access_check:
        return access_check

    raw_id = request.data.get("id")
    now = timezone.now()
    if raw_id is not None and raw_id != "":
        try:
            nid = int(raw_id)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid id."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        updated = InAppNotification.objects.filter(
            recipient=request.user,
            pk=nid,
            read_at__isnull=True,
        ).update(read_at=now)
        return Response({"updated": updated})
    updated = InAppNotification.objects.filter(
        recipient=request.user,
        read_at__isnull=True,
    ).update(read_at=now)
    return Response({"updated": updated})


def _build_audit_queryset(params):
    qs = AuditLog.objects.select_related("actor_user").order_by("-timestamp")
    from_date = params.get("from")
    to_date = params.get("to")
    action_filter = params.get("action")
    user_filter = params.get("user")

    if from_date:
        try:
            d = datetime.strptime(from_date, "%Y-%m-%d").date()
            qs = qs.filter(timestamp__date__gte=d)
        except ValueError:
            pass

    if to_date:
        try:
            d = datetime.strptime(to_date, "%Y-%m-%d").date()
            qs = qs.filter(timestamp__date__lte=d)
        except ValueError:
            pass

    if action_filter:
        qs = qs.filter(action_type=action_filter)

    if user_filter:
        qs = qs.filter(actor_user__email__icontains=user_filter)

    return qs


def _serialize_audit_entry(entry):
    return {
        "id": entry.id,
        "action_type": entry.action_type,
        "action_label": ACTION_LABELS.get(entry.action_type, entry.action_type.replace("_", " ").title()),
        "entity_type": entry.entity_type,
        "entity_id": entry.entity_id,
        "actor_email": entry.actor_user.email if entry.actor_user else None,
        "timestamp": entry.timestamp.isoformat(),
        "details": entry.details or {},
    }


@api_view(["GET"])
def dashboard_audit_log(request):
    access_check = check_admin_access(request.user)
    if access_check:
        return access_check

    page_size = min(int(request.query_params.get("page_size", 50)), 100)
    page = max(int(request.query_params.get("page", 1)), 1)
    start = (page - 1) * page_size

    qs = _build_audit_queryset(request.query_params)
    total = qs.count()
    results = [_serialize_audit_entry(e) for e in qs[start: start + page_size]]

    return Response({
        "results": results,
        "count": total,
        "page": page,
        "page_size": page_size,
        "action_choices": [
            {"value": k, "label": v} for k, v in ACTION_LABELS.items()
        ],
    })


@api_view(["GET"])
def dashboard_audit_log_export(request):
    access_check = check_admin_access(request.user)
    if access_check:
        return access_check

    qs = _build_audit_queryset(request.query_params)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="audit_log.csv"'
    writer = csv.writer(response)
    writer.writerow(["Timestamp", "Action", "Entity", "Entity ID", "User", "Details"])

    for entry in qs:
        label = ACTION_LABELS.get(entry.action_type, entry.action_type.replace("_", " ").title())
        details_str = json.dumps(entry.details) if entry.details else ""
        writer.writerow([
            timezone.localtime(entry.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            label,
            entry.entity_type,
            entry.entity_id,
            entry.actor_user.email if entry.actor_user else "System",
            details_str,
        ])

    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="AuditLogCSV",
        entity_id="bulk",
        details={},
    )

    return response
