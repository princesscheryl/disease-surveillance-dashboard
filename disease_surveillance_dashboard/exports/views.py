from rest_framework import viewsets

from .models import AuditLog
from .models import Export
from .serializers import AuditLogSerializer
from .serializers import ExportSerializer


class ExportViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Export model.

    Provides CRUD operations for export metadata.
    Supports filtering by export_type and status for dashboard views.
    """

    queryset = Export.objects.select_related("generated_by")
    serializer_class = ExportSerializer
    filterset_fields = ["export_type", "status", "generated_by"]
    search_fields = ["file_path"]

    def get_queryset(self):
        """Apply filters from query parameters."""
        queryset = super().get_queryset()

        export_type = self.request.query_params.get("export_type")
        if export_type:
            queryset = queryset.filter(export_type=export_type)

        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)

        generated_by = self.request.query_params.get("generated_by")
        if generated_by:
            queryset = queryset.filter(generated_by_id=generated_by)

        return queryset


class AuditLogViewSet(viewsets.ModelViewSet):
    """
    ViewSet for AuditLog model.

    Provides CRUD operations for audit log entries.
    Supports filtering by entity_type and actor_user for compliance queries.
    """

    queryset = AuditLog.objects.select_related("actor_user")
    serializer_class = AuditLogSerializer
    filterset_fields = ["entity_type", "action_type", "actor_user"]
    search_fields = ["action_type", "entity_type", "entity_id"]

    def get_queryset(self):
        """Apply filters from query parameters."""
        queryset = super().get_queryset()

        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        action_type = self.request.query_params.get("action_type")
        if action_type:
            queryset = queryset.filter(action_type=action_type)

        actor_user = self.request.query_params.get("actor_user")
        if actor_user:
            queryset = queryset.filter(actor_user_id=actor_user)

        return queryset

