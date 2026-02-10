from django.db import models
from django.utils.translation import gettext_lazy as _


class BaselineMetric(models.Model):
    """Model representing computed baseline metrics for disease surveillance."""

    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.PROTECT,
        related_name="baseline_metrics",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.PROTECT,
        related_name="baseline_metrics",
        verbose_name=_("Location"),
    )
    period_type = models.CharField(
        _("Period Type"),
        max_length=50,
    )
    baseline_method = models.CharField(
        _("Baseline Method"),
        max_length=50,
    )
    baseline_value = models.DecimalField(
        _("Baseline Value"),
        max_digits=12,
        decimal_places=4,
    )
    computed_for_start = models.DateField(_("Computed For Start"))
    computed_for_end = models.DateField(_("Computed For End"))
    computed_at = models.DateTimeField(_("Computed At"), auto_now_add=True)

    class Meta:
        db_table = "baseline_metrics"
        verbose_name = _("Baseline Metric")
        verbose_name_plural = _("Baseline Metrics")
        ordering = ["-computed_for_end", "disease_id", "location_id"]
        indexes = [
            models.Index(
                fields=["disease", "location", "computed_for_start", "computed_for_end"],
            ),
            models.Index(fields=["period_type", "baseline_method"]),
        ]

    def __str__(self) -> str:
        """Return readable string representation."""
        return f"{self.disease} @ {self.location} ({self.period_type})"


class TrendMetric(models.Model):
    """Model representing computed trend metrics for disease surveillance."""

    disease = models.ForeignKey(
        "reference_data.Disease",
        on_delete=models.PROTECT,
        related_name="trend_metrics",
        verbose_name=_("Disease"),
    )
    location = models.ForeignKey(
        "reference_data.Location",
        on_delete=models.PROTECT,
        related_name="trend_metrics",
        verbose_name=_("Location"),
    )
    period_start = models.DateField(_("Period Start"))
    period_end = models.DateField(_("Period End"))
    total_cases = models.PositiveIntegerField(_("Total Cases"))
    moving_avg = models.DecimalField(
        _("Moving Average"),
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
    )
    pct_change = models.DecimalField(
        _("Percent Change"),
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
    )
    computed_at = models.DateTimeField(_("Computed At"), auto_now_add=True)

    class Meta:
        db_table = "trend_metrics"
        verbose_name = _("Trend Metric")
        verbose_name_plural = _("Trend Metrics")
        ordering = ["-period_end", "disease_id", "location_id"]
        indexes = [
            models.Index(fields=["disease", "location", "period_start", "period_end"]),
            models.Index(fields=["computed_at"]),
        ]

    def __str__(self) -> str:
        """Return readable string representation."""
        return f"{self.disease} @ {self.location} [{self.period_start} - {self.period_end}]"

