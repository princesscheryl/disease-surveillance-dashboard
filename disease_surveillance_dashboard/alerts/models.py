from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class AlertStatus(models.Model):
    """Model representing the status of an alert"""

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
        """Return status name as string representation """
        return self.status_name


class Alert(models.Model):
    """Model representing a disease surveillance alert """

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
        """Return readable string representation"""
        return f"{self.disease} - {self.location} ({self.severity_level})"


class AlertNote(models.Model):
    """Model representing a note attached to an alert"""

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
        """Return first 30 characters of note text"""
        return self.note_text[:30] if len(self.note_text) > 30 else self.note_text


class AlertEscalation(models.Model):
    """Model representing an escalation of an alert to a different role """

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


class AlertImmediateEmailLog(models.Model):
    alert = models.OneToOneField(
        Alert,
        on_delete=models.CASCADE,
        related_name="immediate_email_log",
        verbose_name=_("Alert"),
    )
    sent_at = models.DateTimeField(_("Sent At"), auto_now_add=True)

    class Meta:
        db_table = "alert_immediate_email_log"
        verbose_name = _("Alert immediate email log")
        verbose_name_plural = _("Alert immediate email logs")


class PhoAlertDigestSend(models.Model):
    digest_for_date = models.DateField(_("Digest date"), unique=True, db_index=True)
    sent_at = models.DateTimeField(_("Sent At"), auto_now_add=True)

    class Meta:
        db_table = "pho_alert_digest_sends"
        verbose_name = _("PHO alert digest send")
        verbose_name_plural = _("PHO alert digest sends")


class CusumThreshold(models.Model):
    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.CASCADE,
        related_name="cusum_thresholds",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="cusum_thresholds",
        verbose_name=_("Location"),
    )
    threshold = models.DecimalField(
        _("CUSUM threshold (h)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
    )
    k_value = models.DecimalField(
        _("CUSUM slack (k)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.50"),
    )
    use_seasonal_baseline = models.BooleanField(
        _("Use 7-day moving average as daily baseline"),
        default=False,
        help_text=_(
            "When enabled, each day uses its 7-day moving average as the CUSUM baseline "
            "instead of a single prior-window average."
        ),
    )
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        db_table = "cusum_thresholds"
        verbose_name = _("CUSUM threshold")
        verbose_name_plural = _("CUSUM thresholds")
        unique_together = [["disease", "location"]]

    def __str__(self) -> str:
        loc = str(self.location) if self.location_id else "All locations"
        return f"{self.disease} — {loc}: h={self.threshold} k={self.k_value}"


class AlertPerformance(models.Model):
    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.CASCADE,
        related_name="alert_performance_rows",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.CASCADE,
        related_name="alert_performance_rows",
        verbose_name=_("Location"),
    )
    period_start = models.DateField(_("Period start"), db_index=True)
    period_end = models.DateField(_("Period end"))
    alerts_generated = models.PositiveIntegerField(_("Alerts generated"), default=0)
    alerts_confirmed = models.PositiveIntegerField(
        _("Resolved (confirmed)"),
        default=0,
        help_text=_("Alerts closed as Resolved in this period."),
    )
    false_alarms = models.PositiveIntegerField(_("False alarms"), default=0)
    false_alarm_rate = models.DecimalField(
        _("False alarm rate"),
        max_digits=6,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text=_("false_alarms / (confirmed + false_alarms) when denominator is positive"),
    )
    threshold_used = models.DecimalField(
        _("Threshold (h) at last update"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("5.00"),
    )
    k_value_used = models.DecimalField(
        _("k at last update"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.50"),
    )
    updated_at = models.DateTimeField(_("Updated at"), auto_now=True)

    class Meta:
        db_table = "alert_performance"
        verbose_name = _("Alert performance")
        verbose_name_plural = _("Alert performance")
        ordering = ["-period_start", "disease", "location"]
        constraints = [
            models.UniqueConstraint(
                fields=["disease", "location", "period_start"],
                name="alertperf_disease_location_period_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.disease} @ {self.location} {self.period_start}: gen={self.alerts_generated}"


DEFAULT_CUSUM_THRESHOLD = Decimal("5.00")
DEFAULT_CUSUM_K = Decimal("0.50")


def resolve_cusum_config(disease_id, location_id):
    """
    Return (threshold, k, use_seasonal_baseline, CusumThreshold | None)
     disease+location row, then disease-wide (location null), else defaults
    """
    specific = CusumThreshold.objects.filter(
        disease_id=disease_id,
        location_id=location_id,
    ).first()
    if specific:
        return (
            float(specific.threshold),
            float(specific.k_value),
            specific.use_seasonal_baseline,
            specific,
        )
    disease_wide = CusumThreshold.objects.filter(
        disease_id=disease_id,
        location__isnull=True,
    ).first()
    if disease_wide:
        return (
            float(disease_wide.threshold),
            float(disease_wide.k_value),
            disease_wide.use_seasonal_baseline,
            disease_wide,
        )
    return (
        float(DEFAULT_CUSUM_THRESHOLD),
        float(DEFAULT_CUSUM_K),
        False,
        None,
    )

