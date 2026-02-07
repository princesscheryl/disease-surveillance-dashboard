from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AlertStatus(models.Model):
    """Model representing the status of an alert."""

    status_name = models.CharField(
        _("Status Name"),
        max_length=255,
        unique=True,
        db_index=True,
    )
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        db_table = "alert_status"
        verbose_name = _("Alert Status")
        verbose_name_plural = _("Alert Statuses")
        ordering = ["status_name"]
        indexes = [
            models.Index(fields=["status_name"]),
        ]

    def __str__(self) -> str:
        """Return status name as string representation."""
        return self.status_name


class Alert(models.Model):
    """Model representing a disease surveillance alert."""

    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.PROTECT,
        related_name="alerts",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.PROTECT,
        related_name="alerts",
        verbose_name=_("Location"),
    )
    period_start = models.DateTimeField(_("Period Start"))
    period_end = models.DateTimeField(_("Period End"))
    baseline_value = models.DecimalField(
        _("Baseline Value"),
        max_digits=12,
        decimal_places=4,
    )
    observed_value = models.DecimalField(
        _("Observed Value"),
        max_digits=12,
        decimal_places=4,
    )
    threshold_rule = models.TextField(_("Threshold Rule"))
    severity_level = models.CharField(
        _("Severity Level"),
        max_length=50,
    )
    status = models.ForeignKey(
        "alerts.AlertStatus",
        on_delete=models.PROTECT,
        related_name="alerts",
        verbose_name=_("Status"),
    )
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        db_table = "alerts"
        verbose_name = _("Alert")
        verbose_name_plural = _("Alerts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["disease", "location"]),
            models.Index(fields=["status", "severity_level"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        """Return readable string representation."""
        return f"{self.disease} - {self.location} ({self.severity_level})"


class AlertNote(models.Model):
    """Model representing a note attached to an alert."""

    alert = models.ForeignKey(
        "alerts.Alert",
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name=_("Alert"),
    )
    noted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="alert_notes",
        verbose_name=_("Noted By"),
    )
    note_text = models.TextField(_("Note Text"))
    noted_at = models.DateTimeField(_("Noted At"), auto_now_add=True)

    class Meta:
        db_table = "alert_notes"
        verbose_name = _("Alert Note")
        verbose_name_plural = _("Alert Notes")
        ordering = ["-noted_at"]
        indexes = [
            models.Index(fields=["alert"]),
            models.Index(fields=["noted_by"]),
        ]

    def __str__(self) -> str:
        """Return first 30 characters of note text."""
        return self.note_text[:30] if len(self.note_text) > 30 else self.note_text


class AlertEscalation(models.Model):
    """Model representing an escalation of an alert to a different role."""

    alert = models.ForeignKey(
        "alerts.Alert",
        on_delete=models.CASCADE,
        related_name="escalations",
        verbose_name=_("Alert"),
    )
    escalated_from_role = models.ForeignKey(
        "access_control.Role",
        on_delete=models.PROTECT,
        related_name="escalations_from",
        verbose_name=_("Escalated From Role"),
    )
    escalated_to_role = models.ForeignKey(
        "access_control.Role",
        on_delete=models.PROTECT,
        related_name="escalations_to",
        verbose_name=_("Escalated To Role"),
    )
    escalation_reason = models.TextField(_("Escalation Reason"))
    escalated_at = models.DateTimeField(_("Escalated At"), auto_now_add=True)

    class Meta:
        db_table = "alert_escalations"
        verbose_name = _("Alert Escalation")
        verbose_name_plural = _("Alert Escalations")
        ordering = ["-escalated_at"]
        indexes = [
            models.Index(fields=["alert", "escalated_at"]),
        ]

    def __str__(self) -> str:
        """Return string representation."""
        return f"Escalation for alert {self.alert.id} from {self.escalated_from_role} to {self.escalated_to_role}"

