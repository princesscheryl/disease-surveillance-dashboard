from rest_framework import viewsets

from .models import InvestigationTask
from .serializers import InvestigationTaskSerializer


class InvestigationTaskViewSet(viewsets.ModelViewSet):
    """ViewSet for InvestigationTask model."""

    queryset = InvestigationTask.objects.select_related(
        "alert", "assigned_to", "assigned_by"
    )
    serializer_class = InvestigationTaskSerializer
    filterset_fields = ["task_status", "assigned_to", "alert"]
    search_fields = ["outcome"]

    def get_queryset(self):
        """Apply filters from query parameters."""
        queryset = super().get_queryset()
        
        # Filter by task_status
        task_status = self.request.query_params.get("task_status")
        if task_status:
            queryset = queryset.filter(task_status=task_status)
        
        # Filter by assigned_to
        assigned_to = self.request.query_params.get("assigned_to")
        if assigned_to:
            queryset = queryset.filter(assigned_to_id=assigned_to)
        
        # Filter by alert
        alert = self.request.query_params.get("alert")
        if alert:
            queryset = queryset.filter(alert_id=alert)
        
        return queryset

