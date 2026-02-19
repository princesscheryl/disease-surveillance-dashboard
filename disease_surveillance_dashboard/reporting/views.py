from datetime import datetime
from datetime import time as dt_time

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import FormView
from rest_framework import viewsets

from .forms import ReportForm
from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus
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


class DuplicateFlagViewSet(viewsets.ModelViewSet):
    """ViewSet for DuplicateFlag model."""

    queryset = DuplicateFlag.objects.select_related("report", "reviewed_by")
    serializer_class = DuplicateFlagSerializer
    filterset_fields = ["report", "reviewed_by", "review_outcome"]
    search_fields = ["flagged_reason"]


class ReportCreateView(LoginRequiredMixin, FormView):
    """View for creating a new disease report."""

    template_name = "reporting/report_form.html"
    form_class = ReportForm
    success_url = "/dashboard/"

    def form_valid(self, form):
        """Process valid form submission."""
        # Get or create SUBMITTED status
        status, _ = ReportStatus.objects.get_or_create(
            status_name="SUBMITTED",
            defaults={"description": "Report submitted by health worker"},
        )

        # Combine observed_date and observed_time into timezone-aware datetime
        observed_date = form.cleaned_data["observed_date"]
        observed_time = form.cleaned_data.get("observed_time") or dt_time(12, 0)
        observed_at = timezone.make_aware(
            datetime.combine(observed_date, observed_time),
        )

        # Handle facility_unit_name prepending to case_notes
        case_notes = form.cleaned_data.get("case_notes", "").strip()
        facility_unit_name = form.cleaned_data.get("facility_unit_name", "").strip()
        if facility_unit_name:
            if case_notes:
                case_notes = f"Facility/Unit: {facility_unit_name}\n\n{case_notes}"
            else:
                case_notes = f"Facility/Unit: {facility_unit_name}"

        # Create Report
        report = Report.objects.create(
            disease=form.cleaned_data["disease"],
            location=form.cleaned_data["location"],
            reported_by=self.request.user,
            observed_at=observed_at,
            case_count=form.cleaned_data["case_count"],
            status=status,
            report_source=form.cleaned_data.get("report_source") or None,
            sex=form.cleaned_data.get("sex") or Report.Sex.UNKNOWN,
            age_group=form.cleaned_data.get("age_group") or Report.AgeGroup.UNKNOWN,
            severity_level=form.cleaned_data.get("severity_level") or Report.SeverityLevel.UNKNOWN,
            case_notes=case_notes,
        )

        messages.success(
            self.request,
            f"Report submitted successfully for {report.disease.disease_name} at {report.location.district_name}.",
        )
        return redirect(self.success_url)

