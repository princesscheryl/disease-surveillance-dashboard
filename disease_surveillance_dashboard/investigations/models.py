from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class InvestigationTask(models.Model):
    """
    Model representing an investigation task assigned to follow up on an alert.

    Investigation tasks track the operational workflow after an alert is generated,
    allowing assignment to specific users and tracking of task completion status.
    """

    class TaskStatus(models.TextChoices):
        """Task lifecycle status choices."""

        OPEN = "OPEN", _("Open")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")

    alert = models.ForeignKey(
        "alerts.Alert",
        on_delete=models.CASCADE,
        related_name="investigation_tasks",
        verbose_name=_("Alert"),
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        verbose_name=_("Assigned To"),
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
        verbose_name=_("Assigned By"),
    )
    due_at = models.DateTimeField(_("Due At"), null=True, blank=True)
    task_status = models.CharField(
        _("Task Status"),
        max_length=20,
        choices=TaskStatus.choices,
    )
    outcome = models.CharField(_("Outcome"), max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)

    class Meta:
        db_table = "investigation_tasks"
        verbose_name = _("Investigation Task")
        verbose_name_plural = _("Investigation Tasks")
        ordering = ["-created_at"]
        indexes = [
            # Index on alert for efficient filtering by alert
            models.Index(fields=["alert"]),
            # Index on assigned_to for user task queries
            models.Index(fields=["assigned_to"]),
            # Index on task_status for filtering by status
            models.Index(fields=["task_status"]),
        ]

    def __str__(self) -> str:
        """Return readable string representation."""
        alert_str = f"Alert {self.alert.id}" if self.alert else "Unknown Alert"
        assigned_str = (
            f" -> {self.assigned_to.email}" if self.assigned_to else " (unassigned)"
        )
        return f"{alert_str}{assigned_str} - {self.task_status}"

