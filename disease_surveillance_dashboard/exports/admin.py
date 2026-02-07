from django.contrib import admin

from .models import AuditLog
from .models import Export


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    """Admin interface for Export model."""

    list_display = [
        "id",
        "export_type",
        "generated_by",
        "status",
        "generated_at",
        "file_path",
    ]
    list_filter = ["export_type", "status", "generated_at"]
    search_fields = ["file_path"]
    ordering = ["-generated_at"]
    readonly_fields = ["generated_at"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog model."""

    list_display = [
        "id",
        "actor_user",
        "action_type",
        "entity_type",
        "entity_id",
        "timestamp",
    ]
    list_filter = ["action_type", "entity_type", "timestamp"]
    search_fields = ["action_type", "entity_type", "entity_id"]
    ordering = ["-timestamp"]
    readonly_fields = ["timestamp"]

