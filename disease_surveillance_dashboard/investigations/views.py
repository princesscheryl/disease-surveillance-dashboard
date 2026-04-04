from rest_framework import viewsets

from disease_surveillance_dashboard.exports.models import record_audit_event
from disease_surveillance_dashboard.users.models import create_task_assigned_notification

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
        task = serializer.save(assigned_by=self.request.user)
        if task.assigned_to_id:
            alert = task.alert
            disease_name = alert.disease.disease_name if alert.disease_id else ""
            create_task_assigned_notification(
                task.assigned_to,
                alert_id=task.alert_id,
                disease_name=disease_name,
                assigner_email=self.request.user.email,
            )
        record_audit_event(
            actor=self.request.user,
            action_type="INVESTIGATION_TASK_CREATED",
            entity_type="InvestigationTask",
            entity_id=str(task.id),
            details={
                "alert_id": task.alert_id,
                "assigned_to_id": task.assigned_to_id,
            },
        )

    def perform_update(self, serializer):
        prev = self.get_object()
        prev_assignee_id = prev.assigned_to_id
        prev_status = prev.task_status
        task = serializer.save()
        if task.assigned_to_id and task.assigned_to_id != prev_assignee_id:
            alert = task.alert
            disease_name = alert.disease.disease_name if alert.disease_id else ""
            create_task_assigned_notification(
                task.assigned_to,
                alert_id=task.alert_id,
                disease_name=disease_name,
                assigner_email=self.request.user.email,
            )
        if (
            task.assigned_to_id != prev_assignee_id
            or task.task_status != prev_status
        ):
            record_audit_event(
                actor=self.request.user,
                action_type="INVESTIGATION_TASK_UPDATED",
                entity_type="InvestigationTask",
                entity_id=str(task.id),
                details={
                    "alert_id": task.alert_id,
                    "assigned_to_id": task.assigned_to_id,
                    "task_status": task.task_status,
                    "previous_assigned_to_id": prev_assignee_id,
                    "previous_task_status": prev_status,
                },
            )

