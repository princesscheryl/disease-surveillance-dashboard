from django.contrib import admin

from .models import Alert
from .models import AlertEscalation
from .models import AlertNote
from .models import AlertStatus


@admin.register(AlertStatus)
class AlertStatusAdmin(admin.ModelAdmin):
    """Admin interface for AlertStatus model."""

    list_display = ["status_name", "description", "created_at"]
    search_fields = ["status_name"]
    ordering = ["status_name"]
    readonly_fields = ["created_at"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    """Admin interface for Alert model."""

    list_display = [
        "id",
        "disease",
        "location",
        "period_start",
        "period_end",
        "baseline_value",
        "observed_value",
        "severity_level",
        "status",
        "created_at",
    ]
    list_filter = ["status", "severity_level", "disease", "created_at"]
    search_fields = [
        "disease__disease_name",
        "location__district_name",
        "location__area_name",
        "threshold_rule",
    ]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]


@admin.register(AlertNote)
class AlertNoteAdmin(admin.ModelAdmin):
    """Admin interface for AlertNote model."""

    list_display = [
        "id",
        "alert",
        "noted_by",
        "note_text",
        "noted_at",
    ]
    list_filter = ["noted_at"]
    search_fields = ["note_text", "alert__disease__disease_name"]
    ordering = ["-noted_at"]
    readonly_fields = ["noted_at"]


@admin.register(AlertEscalation)
class AlertEscalationAdmin(admin.ModelAdmin):
    """Admin interface for AlertEscalation model."""

    list_display = [
        "id",
        "alert",
        "escalated_from_role",
        "escalated_to_role",
        "escalated_at",
    ]
    list_filter = ["escalated_from_role", "escalated_to_role", "escalated_at"]
    search_fields = ["escalation_reason", "alert__disease__disease_name"]
    ordering = ["-escalated_at"]
    readonly_fields = ["escalated_at"]

