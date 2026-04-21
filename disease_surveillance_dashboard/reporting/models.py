from django.conf import settings
from django.core.exceptions import ValidationError
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

    class Sex(models.TextChoices):
        """Sex choices for epidemiological reporting."""

        MALE = "MALE", _("Male")
        FEMALE = "FEMALE", _("Female")
        OTHER = "OTHER", _("Other")
        UNKNOWN = "UNKNOWN", _("Unknown")

    class AgeGroup(models.TextChoices):
        """Age group choices for epidemiological reporting."""

        UNDER_5 = "UNDER_5", _("Under 5")
        AGE_5_17 = "AGE_5_17", _("5-17")
        AGE_18_59 = "AGE_18_59", _("18-59")
        AGE_60_PLUS = "AGE_60_PLUS", _("60+")
        UNKNOWN = "UNKNOWN", _("Unknown")

    class SeverityLevel(models.TextChoices):
        """Severity level choices for case classification."""

        MILD = "MILD", _("Mild")
        MODERATE = "MODERATE", _("Moderate")
        SEVERE = "SEVERE", _("Severe")
        CRITICAL = "CRITICAL", _("Critical")
        UNKNOWN = "UNKNOWN", _("Unknown")

    class CaseClassification(models.TextChoices):
        """IDSR case classification."""

        SUSPECTED = "SUSPECTED", _("Suspected")
        PROBABLE = "PROBABLE", _("Probable")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        UNKNOWN = "UNKNOWN", _("Unknown")

    class ReportType(models.TextChoices):
        """IDSR report type — drives urgency and timeliness rules."""

        IMMEDIATE = "IMMEDIATE", _("Immediate Notification")
        WEEKLY = "WEEKLY", _("Weekly Aggregate")
        OUTBREAK = "OUTBREAK", _("Outbreak Report")

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
    observed_at = models.DateTimeField(_("Observed At"), db_index=True)
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
    case_count = models.PositiveIntegerField(
        _("Case Count"),
        default=1,
        help_text=_("Number of suspected cases in this report"),
    )
    sex = models.CharField(
        _("Sex"),
        max_length=20,
        choices=Sex.choices,
        default=Sex.UNKNOWN,
        db_index=True,
    )
    age_group = models.CharField(
        _("Age Group"),
        max_length=20,
        choices=AgeGroup.choices,
        default=AgeGroup.UNKNOWN,
        db_index=True,
    )
    severity_level = models.CharField(
        _("Severity Level"),
        max_length=20,
        choices=SeverityLevel.choices,
        default=SeverityLevel.UNKNOWN,
    )

    # ------------------------------------------------------------------
    # IDSR fields added to close the surveillance gap
    # ------------------------------------------------------------------

    case_classification = models.CharField(
        _("Case Classification"),
        max_length=20,
        choices=CaseClassification.choices,
        default=CaseClassification.UNKNOWN,
        db_index=True,
    )
    death_count = models.PositiveIntegerField(
        _("Deaths"),
        default=0,
        help_text=_("Number of deaths among the reported cases"),
    )
    report_type = models.CharField(
        _("Report Type"),
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.WEEKLY,
        db_index=True,
    )
    health_facility = models.CharField(
        _("Reporting Facility"),
        max_length=255,
        blank=True,
        help_text=_("Name of the health facility or unit submitting this report"),
    )

    # Sex breakdown counts — sum should equal case_count when provided
    male_count = models.PositiveIntegerField(_("Male Cases"), default=0)
    female_count = models.PositiveIntegerField(_("Female Cases"), default=0)
    unknown_sex_count = models.PositiveIntegerField(_("Unknown Sex Cases"), default=0)

    # Age breakdown counts — sum should equal case_count when provided
    age_under5_count = models.PositiveIntegerField(_("Cases Under 5"), default=0)
    age_5_17_count = models.PositiveIntegerField(_("Cases Age 5–17"), default=0)
    age_18_59_count = models.PositiveIntegerField(_("Cases Age 18–59"), default=0)
    age_60plus_count = models.PositiveIntegerField(_("Cases Age 60+"), default=0)
    unknown_age_count = models.PositiveIntegerField(_("Unknown Age Cases"), default=0)

    class Meta:
        db_table = "reports"
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["disease", "location", "observed_at"]),
            models.Index(fields=["status"]),
            models.Index(fields=["reported_by"]),
            models.Index(fields=["sex"]),
            models.Index(fields=["age_group"]),
        ]

    # ------------------------------------------------------------------
    # Convenience properties — keeps status-check logic out of views/templates
    # ------------------------------------------------------------------

    @property
    def is_draft(self) -> bool:
        """True when this report has DRAFT status."""
        return self.status.status_name == "DRAFT"

    @property
    def is_submitted(self) -> bool:
        """True when this report has SUBMITTED status."""
        return self.status.status_name == "SUBMITTED"

    def clean(self):
        errors = {}

        # deaths can't be more than the total number of cases
        if self.death_count > self.case_count:
            errors["death_count"] = "Deaths cannot exceed the total case count."

        # only check sex breakdown if the user actually filled in the counts
        # (if they are all zero, it just means the breakdown was not provided)
        sex_total = self.male_count + self.female_count + self.unknown_sex_count
        if sex_total > 0 and sex_total != self.case_count:
            errors["male_count"] = (
                "Sex breakdown counts must add up to the total case count."
            )

        # same logic for age breakdown
        age_total = (
            self.age_under5_count
            + self.age_5_17_count
            + self.age_18_59_count
            + self.age_60plus_count
            + self.unknown_age_count
        )
        if age_total > 0 and age_total != self.case_count:
            errors["age_under5_count"] = (
                "Age breakdown counts must add up to the total case count."
            )

        if errors:
            raise ValidationError(errors)

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

    def clean(self):
        # reviewed_by, review_outcome, and reviewed_at all go together
        # if one is filled in, all three should be filled in
        review_fields = [self.reviewed_by_id, self.review_outcome, self.reviewed_at]
        if any(review_fields) and not all(review_fields):
            raise ValidationError(
                "reviewed_by, review_outcome, and reviewed_at must all be set together."
            )

    def __str__(self) -> str:
        """Return string representation."""
        return f"DuplicateFlag for report {self.report.id}"

