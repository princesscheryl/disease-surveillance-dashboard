from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ReportStatus(models.Model):
    """Model representing the status of a disease report."""

    status_name = models.CharField(
        _("Status Name"),
        max_length=255,
        unique=True,
        db_index=True,
    )
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        db_table = "report_status"
        verbose_name = _("Report Status")
        verbose_name_plural = _("Report Statuses")
        ordering = ["status_name"]
        indexes = [
            models.Index(fields=["status_name"]),
        ]

    def __str__(self) -> str:
        """Return status name as string representation."""
        return self.status_name


class Report(models.Model):
    """Model representing a disease report submitted by a health worker."""

    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name=_("Location"),
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_reports",
        verbose_name=_("Reported By"),
    )
    observed_at = models.DateTimeField(_("Observed At"))
    submitted_at = models.DateTimeField(_("Submitted At"), auto_now_add=True)
    case_notes = models.TextField(_("Case Notes"), blank=True)
    status = models.ForeignKey(
        "reporting.ReportStatus",
        on_delete=models.PROTECT,
        related_name="reports",
        verbose_name=_("Status"),
    )
    report_source = models.CharField(
        _("Report Source"),
        max_length=20,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "reports"
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["disease", "location", "observed_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reported_by"]),
        ]

    def __str__(self) -> str:
        """Return readable string representation."""
        observed_date = self.observed_at.date() if self.observed_at else "Unknown"
        return f"{self.disease.disease_name} @ {self.location.district_name} ({observed_date})"


class DuplicateFlag(models.Model):
    """Model representing a flag for a potentially duplicate report."""

    report = models.ForeignKey(
        "reporting.Report",
        on_delete=models.CASCADE,
        related_name="duplicate_flags",
        verbose_name=_("Report"),
    )
    flagged_reason = models.TextField(_("Flagged Reason"))
    flagged_at = models.DateTimeField(_("Flagged At"), auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_duplicate_flags",
        verbose_name=_("Reviewed By"),
    )
    review_outcome = models.CharField(
        _("Review Outcome"),
        max_length=50,
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(_("Reviewed At"), null=True, blank=True)

    class Meta:
        db_table = "duplicate_flags"
        verbose_name = _("Duplicate Flag")
        verbose_name_plural = _("Duplicate Flags")
        ordering = ["-flagged_at"]
        indexes = [
            models.Index(fields=["report"]),
            models.Index(fields=["reviewed_by"]),
        ]

    def __str__(self) -> str:
        """Return string representation."""
        return f"DuplicateFlag for report {self.report.id}"

