from django.contrib import admin

from .models import InvestigationTask


@admin.register(InvestigationTask)
class InvestigationTaskAdmin(admin.ModelAdmin):
    """Admin interface for InvestigationTask model."""

    list_display = [
        "id",
        "alert",
        "assigned_to",
        "task_status",
        "due_at",
        "created_at",
    ]
    list_filter = ["task_status", "created_at"]
    search_fields = ["outcome"]
    autocomplete_fields = ["alert", "assigned_to", "assigned_by"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

