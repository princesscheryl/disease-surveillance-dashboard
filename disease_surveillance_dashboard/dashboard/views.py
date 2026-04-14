import csv
from datetime import date as dt_date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .decorators import require_role

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.exports.models import Export
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


@method_decorator(require_role(*ALL_DASHBOARD_ROLES), name="dispatch")
class ExportReportsPageView(DashboardBaseMixin, TemplateView):
    """Filter and download reports as CSV."""
    template_name = "dashboard/export_reports_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["export_url"] = reverse("dashboard:reports_export")
        return context


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ReviewReportsView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/review_reports.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ExportReviewReportsPageView(DashboardBaseMixin, TemplateView):
    """Filter and download review reports as CSV."""
    template_name = "dashboard/export_review_reports_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["export_url"] = reverse("dashboard:review_reports_export")
        return context


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ExportAlertsPageView(DashboardBaseMixin, TemplateView):
    """Filter and download alerts as CSV."""
    template_name = "dashboard/export_alerts_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["export_url"] = reverse("dashboard:alerts_export")
        return context


# ---------------------------------------------------------------------------
# Legacy alias — keeps the old /dashboard/ URL working by redirecting to
# the new Overview page so existing bookmarks and tests do not break.
# ---------------------------------------------------------------------------
@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class DashboardView(DashboardBaseMixin, TemplateView):
    template_name = "dashboard/overview.html"


# ---------------------------------------------------------------------------
# Export helpers — shared by all three export functions below
# ---------------------------------------------------------------------------

def _epi_week(dt):
    """Return the ISO epi week for a datetime, formatted as '2024W14'."""
    iso = dt.isocalendar()
    return f"{iso.year}W{iso.week:02d}"


def _stamped_filename(base):
    """Attach today's date to a filename so downloads don't overwrite each other."""
    return f"{base}_{dt_date.today().isoformat()}.csv"


def _filter_reports(queryset, request):
    """
    Apply optional query-parameter filters to a Report queryset.

    Supported params:
      from      — submitted_at on or after this date (YYYY-MM-DD)
      to        — submitted_at on or before this date (YYYY-MM-DD)
      disease   — disease primary key
      location  — location primary key
      status    — report status primary key
    """
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    disease_id = request.GET.get("disease")
    location_id = request.GET.get("location")
    status_id = request.GET.get("status")

    if date_from:
        try:
            queryset = queryset.filter(submitted_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            queryset = queryset.filter(submitted_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    if disease_id:
        queryset = queryset.filter(disease_id=disease_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    if status_id:
        queryset = queryset.filter(status_id=status_id)

    return queryset


def _filter_alerts(queryset, request):
    """
    Apply optional query-parameter filters to an Alert queryset.

    Supported params:
      from      — created_at on or after this date (YYYY-MM-DD)
      to        — created_at on or before this date (YYYY-MM-DD)
      disease   — disease primary key
      location  — location primary key
      severity  — severity level string (e.g. Low, High)
    """
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    disease_id = request.GET.get("disease")
    location_id = request.GET.get("location")
    severity = request.GET.get("severity")

    if date_from:
        try:
            queryset = queryset.filter(created_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            queryset = queryset.filter(created_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    if disease_id:
        queryset = queryset.filter(disease_id=disease_id)
    if location_id:
        queryset = queryset.filter(location_id=location_id)
    if severity:
        queryset = queryset.filter(severity_level=severity)

    return queryset


def _active_filters(request, keys):
    """Return only the filter params that were actually supplied in the request."""
    return {k: request.GET[k] for k in keys if request.GET.get(k)}


def _record_export(user, entity_type, row_count, filters):
    """
    Write to both the AuditLog and the Export table.

    AuditLog records who did what and when.
    Export records the download as a completed synchronous export so the
    export history page has something to show.
    """
    record_audit_event(
        actor=user,
        action_type="DATA_EXPORT",
        entity_type=entity_type,
        entity_id="bulk",
        details={"row_count": row_count, "filters": filters},
    )
    Export.objects.create(
        export_type=Export.ExportType.CSV,
        generated_by=user if getattr(user, "is_authenticated", False) else None,
        filters_used=filters,
        status=Export.ExportStatus.COMPLETED,
    )


# ---------------------------------------------------------------------------
# Export views
# ---------------------------------------------------------------------------

REPORT_CSV_HEADERS = [
    "Report ID",
    "Epi Week",
    "Disease",
    "Report Type",
    "Case Classification",
    "Location",
    "Health Facility",
    "Cases",
    "Deaths",
    "Severity",
    "Report Source",
    "Male Cases",
    "Female Cases",
    "Unknown Sex",
    "Under 5",
    "Age 5-17",
    "Age 18-59",
    "Age 60+",
    "Unknown Age",
    "Observed Date",
    "Submitted Date",
    "Submitter",
    "Status",
]


def _report_row(report):
    """Turn a Report instance into a CSV row matching REPORT_CSV_HEADERS."""
    location_name = report.location.district_name
    if report.location.area_name:
        location_name = f"{location_name} - {report.location.area_name}"
    return [
        report.id,
        _epi_week(report.observed_at),
        report.disease.disease_name,
        report.get_report_type_display() if hasattr(report, "get_report_type_display") else report.report_type,
        report.get_case_classification_display() if hasattr(report, "get_case_classification_display") else report.case_classification,
        location_name,
        report.health_facility or "",
        report.case_count,
        report.death_count,
        report.severity_level,
        report.report_source or "",
        report.male_count,
        report.female_count,
        report.unknown_sex_count,
        report.age_under5_count,
        report.age_5_17_count,
        report.age_18_59_count,
        report.age_60plus_count,
        report.unknown_age_count,
        report.observed_at.strftime("%Y-%m-%d"),
        report.submitted_at.strftime("%Y-%m-%d"),
        report.reported_by.email if report.reported_by else "",
        report.status.status_name if report.status else "",
    ]


@require_role(*ALL_DASHBOARD_ROLES)
def export_reports(request):
    """
    Download all reports as CSV.

    Accepts optional query params: from, to, disease, location, status
    Example: /dashboard/reports/export/?from=2024-01-01&to=2024-03-31&disease=5
    """
    filename = _stamped_filename("reports")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

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

    row_count = 0
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
    """
    Download all reports with their verification status as CSV.

    This is the officer-facing export — same fields as the general reports
    export. Accepts the same filter params: from, to, disease, location, status
    """
    filename = _stamped_filename("review_reports")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

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

    row_count = 0
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
    """
    Download all alerts as CSV.

    Accepts optional query params: from, to, disease, location, severity
    Example: /dashboard/alerts/export/?from=2024-01-01&severity=High
    """
    filename = _stamped_filename("alerts")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

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

    row_count = 0
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
        row_count += 1
    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="AlertsCSV",
        entity_id="bulk",
        details={"row_count": row_count},
    )
    return response
