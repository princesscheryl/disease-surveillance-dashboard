import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .decorators import require_role

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.exports.models import record_audit_event
from disease_surveillance_dashboard.reporting.models import Report

OFFICER_OR_ADMIN_ROLES = (
    "Public Health Officer",
    "System Administrator",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
)

ADMIN_ONLY_ROLES = (
    "System Administrator",
    "ADMIN",
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
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class OverviewView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/overview.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AnalyticsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/analytics.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class LiveMapView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/live_map.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AlertsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/alerts.html"


@method_decorator(require_role(*ALL_DASHBOARD_ROLES), name="dispatch")
class NotificationsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/notifications.html"


@method_decorator(require_role(*ADMIN_ONLY_ROLES), name="dispatch")
class AuditLogView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/audit_log.html"


@method_decorator(require_role(*ALL_DASHBOARD_ROLES), name="dispatch")
class ReportsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/reports.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ReviewReportsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/review_reports.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class DashboardView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/overview.html"


@require_role(*ALL_DASHBOARD_ROLES)
def export_reports(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="reports.csv"'
    writer = csv.writer(response)
    writer.writerow(["Report ID", "Disease", "Location", "Cases", "Observed Date", "Submitter", "Status"])

    reports = (
        Report.objects.all()
        .select_related("disease", "location", "status", "reported_by")
        .order_by("-submitted_at")
    )
    row_count = 0
    for report in reports:
        location_name = report.location.district_name
        if report.location.area_name:
            location_name = f"{location_name} - {report.location.area_name}"
        writer.writerow([
            report.id,
            report.disease.disease_name,
            location_name,
            report.case_count,
            report.observed_at.strftime("%Y-%m-%d"),
            report.reported_by.email if report.reported_by else "",
            report.status.status_name if report.status else "",
        ])
        row_count += 1

    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="ReportsCSV",
        entity_id="bulk",
        details={"row_count": row_count},
    )
    return response


@require_role(*OFFICER_OR_ADMIN_ROLES)
def export_review_reports(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="review_reports.csv"'
    writer = csv.writer(response)
    writer.writerow(["Report ID", "Disease", "Location", "Cases", "Observed Date", "Submitter", "Status"])

    reports = (
        Report.objects.all()
        .select_related("disease", "location", "status", "reported_by")
        .order_by("-submitted_at")
    )
    row_count = 0
    for report in reports:
        location_name = report.location.district_name
        if report.location.area_name:
            location_name = f"{location_name} - {report.location.area_name}"
        writer.writerow([
            report.id,
            report.disease.disease_name,
            location_name,
            report.case_count,
            report.observed_at.strftime("%Y-%m-%d"),
            report.reported_by.email if report.reported_by else "",
            report.status.status_name if report.status else "",
        ])
        row_count += 1

    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="ReviewReportsCSV",
        entity_id="bulk",
        details={"row_count": row_count},
    )
    return response


@require_role(*OFFICER_OR_ADMIN_ROLES)
def export_alerts(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="alerts.csv"'
    writer = csv.writer(response)
    writer.writerow(["Alert ID", "Disease", "Location", "Date Detected", "Severity", "Status", "Baseline", "Observed"])

    alerts = (
        Alert.objects.all()
        .select_related("disease", "location", "status")
        .order_by("-created_at")
    )
    row_count = 0
    for alert in alerts:
        location_name = alert.location.district_name
        if alert.location.area_name:
            location_name = f"{location_name} - {alert.location.area_name}"
        writer.writerow([
            alert.id,
            alert.disease.disease_name,
            location_name,
            alert.created_at.strftime("%Y-%m-%d"),
            alert.severity_level,
            alert.status.status_name if alert.status else "",
            alert.baseline_value,
            alert.observed_value,
        ])
        row_count += 1

    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="AlertsCSV",
        entity_id="bulk",
        details={"row_count": row_count},
    )
    return response
