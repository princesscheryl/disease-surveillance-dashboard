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
    DashboardView,
    LiveMapView,
    OverviewView,
    ReportsView,
)

app_name = "dashboard"

urlpatterns = [
    # Legacy URL — kept so existing bookmarks and template {% url 'dashboard:dashboard' %} still work
    path("", DashboardView.as_view(), name="dashboard"),

    # New named pages
    path("overview/",  OverviewView.as_view(),  name="overview"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("map/",       LiveMapView.as_view(),   name="live_map"),
    path("alerts/",    AlertsView.as_view(),    name="alerts"),
    path("reports/",   ReportsView.as_view(),   name="reports"),
]
