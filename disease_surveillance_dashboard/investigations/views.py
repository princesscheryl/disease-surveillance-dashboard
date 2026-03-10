from rest_framework import viewsets

from .models import InvestigationTask
from .serializers import InvestigationTaskSerializer


class InvestigationTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for InvestigationTask model."""

    queryset = InvestigationTask.objects.select_related(
        "alert", "assigned_to", "assigned_by",
    )
    serializer_class = InvestigationTaskSerializer
    filterset_fields = ["task_status", "assigned_to", "alert"]
    search_fields = ["outcome"]

    def get_queryset(self):
        """Apply filters from query parameters."""
        queryset = super().get_queryset()

        # Show only OPEN and IN_PROGRESS when status=active
        status_param = self.request.query_params.get("status")
        if status_param == "active":
            queryset = queryset.filter(
                task_status__in=[
                    InvestigationTask.TaskStatus.OPEN,
                    InvestigationTask.TaskStatus.IN_PROGRESS,
                ]
            )

        task_status = self.request.query_params.get("task_status")
        if task_status:
            queryset = queryset.filter(task_status=task_status)

        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)

        alert = self.request.query_params.get("alert")
        if alert:
            queryset = queryset.filter(alert_id=alert)

        return queryset

    def perform_create(self, serializer):
        """Set assigned_by to the current user when creating a task."""
        serializer.save(assigned_by=self.request.user)

