from django.contrib import admin

from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus


@admin.register(ReportStatus)
class ReportStatusAdmin(admin.ModelAdmin):
    """Admin interface for ReportStatus model."""

    list_display = ["status_name"]
    search_fields = ["status_name"]
    ordering = ["status_name"]
    readonly_fields = ["created_at"]


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Admin interface for Report model."""

    list_display = [
        "id",
        "disease",
        "location",
        "reported_by",
        "status",
        "observed_at",
        "submitted_at",
        "report_source",
    ]
    list_filter = ["status", "disease", "report_source"]
    search_fields = ["case_notes"]
    ordering = ["-submitted_at"]
    readonly_fields = ["submitted_at"]


@admin.register(DuplicateFlag)
class DuplicateFlagAdmin(admin.ModelAdmin):
    """Admin interface for DuplicateFlag model."""

    list_display = [
        "id",
        "report",
        "flagged_at",
        "reviewed_by",
        "review_outcome",
    ]
    list_filter = ["review_outcome"]
    search_fields = ["flagged_reason"]
    ordering = ["-flagged_at"]
    readonly_fields = ["flagged_at"]

