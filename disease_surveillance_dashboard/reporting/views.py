"""Views for the reporting app.

Web views
---------
  ReportCreateView   — POST /reports/new/
  ReportUpdateView   — POST /reports/<pk>/edit/
  MySubmissionsView  — GET  /reports/my-submissions/

DRF ViewSets (unchanged, mobile / API consumers)
-------------------------------------------------
  ReportStatusViewSet
  ReportViewSet
  DuplicateFlagViewSet
"""

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
from disease_surveillance_dashboard.exports.models import record_audit_event

from .serializers import DuplicateFlagSerializer
from .serializers import ReportSerializer
from .serializers import ReportStatusSerializer


# ---------------------------------------------------------------------------
# DRF ViewSets — untouched; mobile / API layer
# ---------------------------------------------------------------------------

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
    """Return a ReportStatus by name, creating it if it doesn't yet exist.

    Using get_or_create means the view is self-healing: even if migration
    0003 has not been applied to the current database (e.g. a fresh dev
    container that hasn't run `migrate` yet) the row is created on first use
    rather than returning a 404.

    Production databases will already have the row from the migration, so the
    CREATE path is only ever hit in misconfigured dev environments.
    """
    status, _ = ReportStatus.objects.get_or_create(
        status_name=name,
        defaults={"description": _STATUS_DESCRIPTIONS.get(name, "")},
    )
    return status


def _build_report_kwargs(form_data: dict) -> dict:
    """Translate cleaned form data into Report model field values."""
    observed_date = form_data["observed_date"]
    observed_time = form_data.get("observed_time") or dt_time(12, 0)
    observed_at = timezone.make_aware(datetime.combine(observed_date, observed_time))

    case_notes = (form_data.get("case_notes") or "").strip()
    facility_unit_name = (form_data.get("facility_unit_name") or "").strip()
    if facility_unit_name:
        case_notes = (
            f"Facility/Unit: {facility_unit_name}\n\n{case_notes}"
            if case_notes
            else f"Facility/Unit: {facility_unit_name}"
        )

    return {
        "disease": form_data["disease"],
        "location": form_data["location"],
        "observed_at": observed_at,
        "case_count": form_data["case_count"],
        "report_source": form_data.get("report_source") or None,
        "sex": form_data.get("sex") or Report.Sex.UNKNOWN,
        "age_group": form_data.get("age_group") or Report.AgeGroup.UNKNOWN,
        "severity_level": form_data.get("severity_level") or Report.SeverityLevel.UNKNOWN,
        "case_notes": case_notes,
    }


# ---------------------------------------------------------------------------
# A) ReportCreateView — web form, two-button submit
# ---------------------------------------------------------------------------

class ReportCreateView(LoginRequiredMixin, FormView):
    """Create a new disease report.

    Two submit buttons are supported:
    - ``action=draft``   → saves with status DRAFT and redirects to My Submissions
    - ``action=submit``  → saves with status SUBMITTED and redirects to dashboard
    """

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


# ---------------------------------------------------------------------------
# B) ReportUpdateView — edit a DRAFT report only
# ---------------------------------------------------------------------------

class ReportUpdateView(LoginRequiredMixin, FormView):
    """Edit an existing DRAFT report.

    Access rules (enforced in Python, not just templates):
    - Only the report owner can access this view.
    - Only DRAFT reports can be edited; attempts to edit a SUBMITTED report
      return 403.

    Same two-button semantics as ReportCreateView.
    """

    template_name = "reporting/report_update.html"
    form_class = ReportUpdateForm

    # NOTE: _report is set as an *instance* attribute inside dispatch() so it
    # is never shared between concurrent requests.  Do NOT declare it as a
    # class attribute here.

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Resolve the report once, store on self for all subsequent methods.
        report = get_object_or_404(
            Report.objects.select_related("status", "disease", "location"),
            pk=kwargs["pk"],
        )

        # Ownership check — return 404 so non-owners can't probe for IDs.
        if report.reported_by_id != request.user.pk:
            raise Http404

        # Draft-only check — hard 403 for submitted reports.
        if report.is_submitted:
            return HttpResponseForbidden(
                "This report has already been submitted and cannot be edited."
            )

        self._report = report  # instance attribute, safe per-request
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        """Inject the report instance into the form so it can pre-populate."""
        kwargs = super().get_form_kwargs()
        # Only pass report on GET (unbound form) so the form uses initial
        # values.  On POST the form is bound to request.POST and initial
        # values are intentionally ignored by Django — the user's submitted
        # data takes precedence.
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
                    "source": "web_draft_edit",
                },
            )

        if is_submitting:
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


# ---------------------------------------------------------------------------
# C) MySubmissionsView — list the current user's own reports
# ---------------------------------------------------------------------------

class MySubmissionsView(LoginRequiredMixin, ListView):
    """Show all reports belonging to the logged-in user, newest first.

    Drafts use ``submitted_at`` (which is set at creation time via
    auto_now_add=True) as their sort key, consistent with the model's
    default ordering.
    """

    template_name = "reporting/my_submissions.html"
    context_object_name = "reports"
    paginate_by = 20

    def get_queryset(self):
        return (
            Report.objects.filter(reported_by=self.request.user)
            .select_related("disease", "location", "status")
            .order_by("-submitted_at")
        )


@login_required
def export_my_submissions(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="my_reports.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Report ID",
            "Disease",
            "Location",
            "Cases",
            "Observed Date",
            "Created Date",
            "Status",
        ]
    )
    reports = (
        Report.objects.filter(reported_by=request.user)
        .select_related("disease", "location", "status")
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
                report.submitted_at.strftime("%Y-%m-%d"),
                report.status.status_name if report.status else "",
            ]
        )
        row_count += 1
    record_audit_event(
        actor=request.user,
        action_type="DATA_EXPORT",
        entity_type="MySubmissionsCSV",
        entity_id="bulk",
        details={"row_count": row_count},
    )
    return response
