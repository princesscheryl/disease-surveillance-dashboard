from rest_framework import viewsets
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import BasePermission
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from disease_surveillance_dashboard.dashboard.utils import user_is_admin

from .models import AuditLog
from .models import Export
from .serializers import AuditLogSerializer
from .serializers import ExportSerializer


class IsAdminRole(BasePermission):
    # the audit log contains all system actions so only admins should access it
    def has_permission(self, request, view):
        return user_is_admin(request.user)


class ExportViewSet(viewsets.ModelViewSet):
    queryset = Export.objects.select_related("generated_by")
    serializer_class = ExportSerializer
    filterset_fields = ["export_type", "status", "generated_by"]
    search_fields = ["file_path"]

    def get_queryset(self):
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


class AuditLogViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated, IsAdminRole]
    queryset = AuditLog.objects.select_related("actor_user")
    serializer_class = AuditLogSerializer
    filterset_fields = ["entity_type", "action_type", "actor_user"]
    search_fields = ["action_type", "entity_type", "entity_id"]

    def get_queryset(self):
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
