from django.contrib import admin

from .models import Alert
from .models import AlertEscalation
from .models import AlertImmediateEmailLog
from .models import AlertNote
from .models import AlertPerformance
from .models import AlertStatus
from .models import CusumThreshold
from .models import PhoAlertDigestSend


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


@admin.register(AlertImmediateEmailLog)
class AlertImmediateEmailLogAdmin(admin.ModelAdmin):
    list_display = ["alert", "sent_at"]
    readonly_fields = ["alert", "sent_at"]
    ordering = ["-sent_at"]


@admin.register(PhoAlertDigestSend)
class PhoAlertDigestSendAdmin(admin.ModelAdmin):
    list_display = ["digest_for_date", "sent_at"]
    readonly_fields = ["digest_for_date", "sent_at"]
    ordering = ["-digest_for_date"]


@admin.register(CusumThreshold)
class CusumThresholdAdmin(admin.ModelAdmin):
    list_display = [
        "disease",
        "location",
        "threshold",
        "k_value",
        "use_seasonal_baseline",
        "updated_at",
    ]
    list_filter = ["disease", "use_seasonal_baseline"]
    search_fields = [
        "disease__disease_name",
        "location__district_name",
        "location__area_name",
    ]
    list_editable = ["threshold", "k_value", "use_seasonal_baseline"]
    ordering = ["disease", "location"]


@admin.register(AlertPerformance)
class AlertPerformanceAdmin(admin.ModelAdmin):
    list_display = [
        "disease",
        "location",
        "period_start",
        "period_end",
        "alerts_generated",
        "alerts_confirmed",
        "false_alarms",
        "false_alarm_rate",
        "threshold_used",
        "k_value_used",
        "updated_at",
    ]
    list_filter = ["disease", "period_start"]
    search_fields = ["disease__disease_name", "location__district_name"]
    ordering = ["-period_start", "disease", "location"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]


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

