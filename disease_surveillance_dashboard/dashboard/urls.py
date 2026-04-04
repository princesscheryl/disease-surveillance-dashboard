"""URL configuration for dashboard app.

Pages:
  /dashboard/           → overview (legacy alias, keeps old links working)
  /dashboard/overview/  → overview
  /dashboard/analytics/ → analytics
  /dashboard/map/       → live map
  /dashboard/alerts/    → alerts & investigations
  /dashboard/reports/   → reports list
"""

from django.urls import path

from .views import (
    AlertsView,
    AnalyticsView,
    AuditLogView,
    DashboardView,
    LiveMapView,
    NotificationsView,
    OverviewView,
    ReportsView,
    ReviewReportsView,
    export_alerts,
    export_reports,
    export_review_reports,
)

app_name = "dashboard"

urlpatterns = [
    # Legacy URL — kept so existing bookmarks and template {% url 'dashboard:dashboard' %} still work
    path("", DashboardView.as_view(), name="dashboard"),

    # New named pages
    path("overview/",  OverviewView.as_view(),  name="overview"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("map/",       LiveMapView.as_view(),   name="live_map"),
    path("alerts/",         AlertsView.as_view(),         name="alerts"),
    path("notifications/",  NotificationsView.as_view(),  name="notifications"),
    path("activity/",       AuditLogView.as_view(),       name="activity_log"),
    path("alerts/export/",   export_alerts,               name="alerts_export"),
    path("reports/review/", ReviewReportsView.as_view(), name="review_reports"),
    path("reports/review/export/", export_review_reports, name="review_reports_export"),
    path("reports/",        ReportsView.as_view(),       name="reports"),
    path("reports/export/",  export_reports,              name="reports_export"),
]
