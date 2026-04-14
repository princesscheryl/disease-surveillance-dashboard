
from datetime import date as dt_date
from datetime import datetime
from datetime import time as dt_time

import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView
from django.views.generic import ListView
from rest_framework import viewsets

from .forms import ReportForm
from .forms import ReportUpdateForm
from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus
from disease_surveillance_dashboard.exports.models import Export
from disease_surveillance_dashboard.exports.models import record_audit_event

from .serializers import DuplicateFlagSerializer
from .serializers import ReportSerializer
from .serializers import ReportStatusSerializer


class ReportStatusViewSet(viewsets.ModelViewSet):
    """ViewSet for ReportStatus model."""

    queryset = ReportStatus.objects.all()
    serializer_class = ReportStatusSerializer
    filterset_fields = ["status_name"]
    search_fields = ["status_name", "description"]


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for Report model."""

    queryset = Report.objects.select_related(
        "disease", "location", "reported_by", "status",
    )
    serializer_class = ReportSerializer
    filterset_fields = ["disease", "location", "status", "reported_by", "report_source"]
    search_fields = ["case_notes"]

    def perform_update(self, serializer):
        prev = self.get_object()
        prev_count = prev.case_count
        report = serializer.save()
        if report.case_count != prev_count:
            record_audit_event(
                actor=self.request.user,
                action_type="REPORT_CASE_COUNT_CHANGED",
                entity_type="Report",
                entity_id=str(report.id),
                details={
                    "previous_case_count": prev_count,
                    "new_case_count": report.case_count,
                },
            )


class DuplicateFlagViewSet(viewsets.ModelViewSet):
    """ViewSet for DuplicateFlag model."""

    queryset = DuplicateFlag.objects.select_related("report", "reviewed_by")
    serializer_class = DuplicateFlagSerializer
    filterset_fields = ["report", "reviewed_by", "review_outcome"]
    search_fields = ["flagged_reason"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_DESCRIPTIONS: dict[str, str] = {
    "DRAFT": "Report saved as a draft; not yet submitted for surveillance.",
    "SUBMITTED": "Report submitted by health worker and ready for review.",
}


def _get_status(name: str) -> ReportStatus:
    status, _ = ReportStatus.objects.get_or_create(
        status_name=name,
        defaults={"description": _STATUS_DESCRIPTIONS.get(name, "")},
    )
    return status


def _build_report_kwargs(form_data: dict) -> dict:
    observed_date = form_data["observed_date"]
    observed_time = form_data.get("observed_time") or dt_time(12, 0)
    observed_at = timezone.make_aware(datetime.combine(observed_date, observed_time))

    return {
        "disease": form_data["disease"],
        "location": form_data["location"],
        "observed_at": observed_at,
        "report_type": form_data.get("report_type") or Report.ReportType.WEEKLY,
        "case_count": form_data["case_count"],
        "death_count": form_data.get("death_count") or 0,
        "report_source": form_data.get("report_source") or None,
        "case_classification": form_data.get("case_classification") or Report.CaseClassification.UNKNOWN,
        "severity_level": form_data.get("severity_level") or Report.SeverityLevel.UNKNOWN,
        "male_count": form_data.get("male_count") or 0,
        "female_count": form_data.get("female_count") or 0,
        "unknown_sex_count": form_data.get("unknown_sex_count") or 0,
        "age_under5_count": form_data.get("age_under5_count") or 0,
        "age_5_17_count": form_data.get("age_5_17_count") or 0,
        "age_18_59_count": form_data.get("age_18_59_count") or 0,
        "age_60plus_count": form_data.get("age_60plus_count") or 0,
        "unknown_age_count": form_data.get("unknown_age_count") or 0,
        "health_facility": (form_data.get("health_facility") or "").strip(),
        "case_notes": (form_data.get("case_notes") or "").strip(),
    }


class ReportCreateView(LoginRequiredMixin, FormView):
    template_name = "reporting/report_form.html"
    form_class = ReportForm

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Report Case"
        ctx["page_subtitle"] = "Submit a new disease case report for surveillance tracking."
        ctx["cancel_url"] = "dashboard:overview"
        return ctx

    def form_valid(self, form):
        action = self.request.POST.get("action", "submit")
        is_draft = action == "draft"

        status = _get_status("DRAFT" if is_draft else "SUBMITTED")
        kwargs = _build_report_kwargs(form.cleaned_data)

        report = Report.objects.create(
            reported_by=self.request.user,
            status=status,
            **kwargs,
        )

        record_audit_event(
            actor=self.request.user,
            action_type="REPORT_DRAFT_SAVED" if is_draft else "REPORT_SUBMITTED",
            entity_type="Report",
            entity_id=str(report.id),
            details={
                "disease": report.disease.disease_name,
                "location": report.location.district_name,
                "case_count": report.case_count,
            },
        )

        if is_draft:
            messages.info(
                self.request,
                f"Draft saved for {report.disease.disease_name} at {report.location.district_name}. "
                "You can continue editing it from My Submissions.",
            )
            return redirect("reporting:my_submissions")

        messages.success(
            self.request,
            f"Report submitted successfully for {report.disease.disease_name} "
            f"at {report.location.district_name}.",
        )
        return redirect("dashboard:overview")


class ReportUpdateView(LoginRequiredMixin, FormView):
    template_name = "reporting/report_update.html"
    form_class = ReportUpdateForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        report = get_object_or_404(
            Report.objects.select_related("status", "disease", "location"),
            pk=kwargs["pk"],
        )

        if report.reported_by_id != request.user.pk:
            raise Http404

        if report.is_submitted:
            return HttpResponseForbidden(
                "This report has already been submitted and cannot be edited."
            )

        self._report = report
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if self.request.method == "GET":
            kwargs["report"] = self._report
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["report"] = self._report
        ctx["page_title"] = "Edit Draft Report"
        ctx["page_subtitle"] = (
            f"Editing draft: {self._report.disease.disease_name} — "
            f"{self._report.location.district_name}"
        )
        return ctx

    def form_valid(self, form):
        report = self._report
        action = self.request.POST.get("action", "draft")
        is_submitting = action == "submit"

        fields = _build_report_kwargs(form.cleaned_data)
        previous_case_count = report.case_count
        for field, value in fields.items():
            setattr(report, field, value)

        report.status = _get_status("SUBMITTED" if is_submitting else "DRAFT")
        report.save()

        if report.case_count != previous_case_count:
            record_audit_event(
                actor=self.request.user,
                action_type="REPORT_CASE_COUNT_CHANGED",
                entity_type="Report",
                entity_id=str(report.id),
                details={
                    "previous_case_count": previous_case_count,
                    "new_case_count": report.case_count,
                },
            )

        if is_submitting:
            record_audit_event(
                actor=self.request.user,
                action_type="REPORT_SUBMITTED",
                entity_type="Report",
                entity_id=str(report.id),
                details={
                    "disease": report.disease.disease_name,
                    "location": report.location.district_name,
                    "case_count": report.case_count,
                },
            )
            messages.success(
                self.request,
                f"Report submitted successfully for {report.disease.disease_name} "
                f"at {report.location.district_name}.",
            )
            return redirect("dashboard:overview")

        messages.info(
            self.request,
            "Draft updated. You can continue editing it from My Submissions.",
        )
        return redirect("reporting:my_submissions")


class MySubmissionsView(LoginRequiredMixin, ListView):
    template_name = "reporting/my_submissions.html"
    context_object_name = "reports"
    paginate_by = 20

    def get_queryset(self):
        return (
            Report.objects.filter(reported_by=self.request.user)
            .select_related("disease", "location", "status")
            .order_by("-submitted_at")
        )


def _epi_week(dt):
    """Return the ISO epi week for a datetime, formatted as '2024W14'."""
    iso = dt.isocalendar()
    return f"{iso.year}W{iso.week:02d}"


@login_required
def export_my_submissions(request):
    """
    Download the logged-in user's own reports as CSV.

    Accepts optional query params: from, to, disease
    Example: /reports/my-submissions/export/?from=2024-01-01&to=2024-03-31
    """
    filename = f"my_reports_{dt_date.today().isoformat()}.csv"
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
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
        "Status",
    ])

    reports = (
        Report.objects.filter(reported_by=request.user)
        .select_related("disease", "location", "status")
        .order_by("-submitted_at")
    )

    date_from = request.GET.get("from")
    date_to = request.GET.get("to")
    disease_id = request.GET.get("disease")

    if date_from:
        try:
            reports = reports.filter(observed_at__date__gte=date_from)
        except (ValueError, TypeError):
            pass
    if date_to:
        try:
            reports = reports.filter(observed_at__date__lte=date_to)
        except (ValueError, TypeError):
            pass
    if disease_id:
        reports = reports.filter(disease_id=disease_id)

    row_count = 0
    for report in reports:
        location_name = report.location.district_name
        if report.location.area_name:
            location_name = f"{location_name} - {report.location.area_name}"
        writer.writerow([
            report.id,
            _epi_week(report.observed_at),
            report.disease.disease_name,
            report.report_type,
            report.case_classification,
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
            report.status.status_name if report.status else "",
        ])
        row_count += 1

    filters = {k: request.GET[k] for k in ["from", "to", "disease"] if request.GET.get(k)}
    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="MySubmissionsCSV",
        entity_id="bulk",
        details={"row_count": row_count, "filters": filters},
    )
    Export.objects.create(
        export_type=Export.ExportType.CSV,
        generated_by=request.user,
        filters_used=filters,
        status=Export.ExportStatus.COMPLETED,
    )
    return response
