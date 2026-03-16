"""
Dashboard UI views.

Each view is a LoginRequiredMixin TemplateView with role-based access.
Overview, Analytics, Live Map, and Alerts require Officer or Admin.
Reports allows all users with a role. All data loading is done client-side
via the Alpine dashboardData() component.
"""

import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .decorators import require_role

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.reporting.models import Report

# Role names for access control. Include legacy names (ADMIN, HEALTH_OFFICER, etc.)
# for backward compatibility with existing Role records.
OFFICER_OR_ADMIN_ROLES = (
    "Public Health Officer",
    "System Administrator",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
)
ALL_DASHBOARD_ROLES = (
    "Community Health Worker",
    "Public Health Officer",
    "System Administrator",
    "CHW",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
)


class DashboardBaseMixin(LoginRequiredMixin):
    """Adds user to context for all dashboard views."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class OverviewView(DashboardBaseMixin, TemplateView):
    """KPI cards + at-a-glance chart tiles."""
    template_name = "dashboard/overview.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AnalyticsView(DashboardBaseMixin, TemplateView):
    """Full chart suite: timeseries, forecast, anomalies, top diseases."""
    template_name = "dashboard/analytics.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class LiveMapView(DashboardBaseMixin, TemplateView):
    """Leaflet map with disease distribution markers."""
    template_name = "dashboard/live_map.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AlertsView(DashboardBaseMixin, TemplateView):
    """Recent alerts table + investigation tasks table."""
    template_name = "dashboard/alerts.html"


@method_decorator(require_role(*ALL_DASHBOARD_ROLES), name="dispatch")
class ReportsView(DashboardBaseMixin, TemplateView):
    """Report list placeholder with future export button."""
    template_name = "dashboard/reports.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ReviewReportsView(DashboardBaseMixin, TemplateView):
    """Officer report verification — all reports with status update actions."""
    template_name = "dashboard/review_reports.html"


# ---------------------------------------------------------------------------
# Legacy alias — keeps the old /dashboard/ URL working by redirecting to
# the new Overview page so existing bookmarks and tests do not break.
# ---------------------------------------------------------------------------
@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class DashboardView(DashboardBaseMixin, TemplateView):
    """Legacy entry point — alias for OverviewView."""
    template_name = "dashboard/overview.html"


@require_role(*ALL_DASHBOARD_ROLES)
def export_reports(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="reports.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Report ID",
            "Disease",
            "Location",
            "Cases",
            "Observed Date",
            "Submitter",
            "Status",
        ]
    )
    reports = (
        Report.objects.all()
        .select_related("disease", "location", "status", "reported_by")
        .order_by("-submitted_at")
    )
    for report in reports:
        location_name = report.location.district_name
        if report.location.area_name:
            location_name = f"{location_name} - {report.location.area_name}"
        writer.writerow(
            [
                report.id,
                report.disease.disease_name,
                location_name,
                report.case_count,
                report.observed_at.strftime("%Y-%m-%d"),
                report.reported_by.email if report.reported_by else "",
                report.status.status_name if report.status else "",
            ]
        )
    return response


@require_role(*OFFICER_OR_ADMIN_ROLES)
def export_review_reports(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="review_reports.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Report ID",
            "Disease",
            "Location",
            "Cases",
            "Observed Date",
            "Submitter",
            "Status",
            "Verification Status",
        ]
    )
    reports = (
        Report.objects.all()
        .select_related("disease", "location", "status", "reported_by")
        .order_by("-submitted_at")
    )
    for report in reports:
        location_name = report.location.district_name
        if report.location.area_name:
            location_name = f"{location_name} - {report.location.area_name}"
        status_name = report.status.status_name if report.status else ""
        writer.writerow(
            [
                report.id,
                report.disease.disease_name,
                location_name,
                report.case_count,
                report.observed_at.strftime("%Y-%m-%d"),
                report.reported_by.email if report.reported_by else "",
                status_name,
                status_name,
            ]
        )
    return response


@require_role(*OFFICER_OR_ADMIN_ROLES)
def export_alerts(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="alerts.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Alert ID",
            "Disease",
            "Location",
            "Date Detected",
            "Severity",
            "Status",
            "Baseline",
            "Observed",
        ]
    )
    alerts = (
        Alert.objects.all()
        .select_related("disease", "location", "status")
        .order_by("-created_at")
    )
    for alert in alerts:
        location_name = alert.location.district_name
        if alert.location.area_name:
            location_name = f"{location_name} - {alert.location.area_name}"
        writer.writerow(
            [
                alert.id,
                alert.disease.disease_name,
                location_name,
                alert.created_at.strftime("%Y-%m-%d"),
                alert.severity_level,
                alert.status.status_name if alert.status else "",
                alert.baseline_value,
                alert.observed_value,
            ]
        )
    return response
