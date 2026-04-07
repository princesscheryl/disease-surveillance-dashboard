"""URL configuration for dashboard API endpoints."""

from django.urls import path

from .api import dashboard_alert_details
from .api import dashboard_alert_statuses
from .api import dashboard_alert_update_status
from .api import dashboard_assignable_users
from .api import dashboard_audit_log
from .api import dashboard_notifications_list
from .api import dashboard_notifications_mark_read
from .api import dashboard_report_details
from .api import dashboard_report_update_status
from .api import dashboard_reports_count
from .api import dashboard_review_reports
from .api import dashboard_anomalies
from .api import dashboard_choropleth_data
from .api import dashboard_cases_timeseries
from .api import dashboard_data_quality
from .api import dashboard_detection_metrics
from .api import dashboard_district_summary
from .api import dashboard_evaluate
from .api import dashboard_forecast
from .api import dashboard_map_points
from .api import dashboard_recent_alerts
from .api import dashboard_recent_investigations
from .api import dashboard_situation_overview
from .api import dashboard_summary
from .api import dashboard_top_diseases

app_name = "dashboard_api"

urlpatterns = [
    # Existing endpoints — unchanged
    path("summary/",                dashboard_summary,               name="summary"),
    path("cases-timeseries/",       dashboard_cases_timeseries,      name="cases-timeseries"),
    path("anomalies/",              dashboard_anomalies,             name="anomalies"),
    path("forecast/",               dashboard_forecast,              name="forecast"),
    path("top-diseases/",           dashboard_top_diseases,          name="top-diseases"),
    path("map-points/",             dashboard_map_points,            name="map-points"),
    path("recent-alerts/",          dashboard_recent_alerts,         name="recent-alerts"),
    path("recent-investigations/",  dashboard_recent_investigations, name="recent-investigations"),
    path("assignable-users/",       dashboard_assignable_users,      name="assignable-users"),
    path("notifications/",         dashboard_notifications_list,      name="notifications-list"),
    path("notifications/mark-read/", dashboard_notifications_mark_read, name="notifications-mark-read"),
    path("audit-log/",             dashboard_audit_log,             name="audit-log"),
    path("alert-statuses/",        dashboard_alert_statuses,         name="alert-statuses"),
    path("alerts/<int:alert_id>/details/", dashboard_alert_details, name="alert-details"),
    path("alerts/<int:alert_id>/update-status/", dashboard_alert_update_status, name="alert-update-status"),
    path("review-reports/",         dashboard_review_reports,        name="review-reports"),
    path("reports/<int:report_id>/details/", dashboard_report_details, name="report-details"),
    path("reports/<int:report_id>/update-status/", dashboard_report_update_status, name="report-update-status"),
    path("evaluate/",               dashboard_evaluate,              name="evaluate"),
    # New epidemiological analytics endpoints
    path("situation-overview/",     dashboard_situation_overview,    name="situation-overview"),
    path("detection-metrics/",      dashboard_detection_metrics,     name="detection-metrics"),
    path("data-quality/",           dashboard_data_quality,          name="data-quality"),
    path("district-summary/",       dashboard_district_summary,      name="district-summary"),
    path("choropleth-data/",        dashboard_choropleth_data,      name="choropleth-data"),
    # Export filter count endpoint
    path("reports-count/",          dashboard_reports_count,         name="reports-count"),
]

