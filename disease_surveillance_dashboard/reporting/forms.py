"""Forms for reporting app."""

from django import forms

from reference_data.models import Disease
from reference_data.models import Location

from .models import Report


REPORT_SOURCE_CHOICES = [
    ("FACILITY", "Facility"),
    ("LAB", "Lab"),
    ("COMMUNITY", "Community"),
    ("OTHER", "Other"),
]

# ---------------------------------------------------------------------------
# Shared field definitions — single source of truth for both Create and Update
# ---------------------------------------------------------------------------

def _report_fields() -> dict:
    """Return field definitions shared by ReportForm and ReportUpdateForm."""
    return {
        "disease": forms.ModelChoiceField(
            queryset=Disease.objects.filter(is_active=True).order_by("disease_name"),
            required=True,
            label="Disease",
            empty_label="--------- Select disease ---------",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "location": forms.ModelChoiceField(
            queryset=Location.objects.filter(is_active=True).order_by("district_name"),
            required=True,
            label="Reporting District",
            empty_label="--------- Select district ---------",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "observed_date": forms.DateField(
            required=True,
            label="Observed Date",
            widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        ),
        "observed_time": forms.TimeField(
            required=False,
            label="Observed Time (Optional)",
            widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
        ),
        # ── Case Details ──────────────────────────────────────────────────
        "report_type": forms.ChoiceField(
            choices=Report.ReportType.choices,
            required=True,
            initial=Report.ReportType.WEEKLY,
            label="Report Type",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "case_count": forms.IntegerField(
            required=True,
            initial=1,
            min_value=1,
            label="Case Count",
            widget=forms.NumberInput(attrs={"class": "form-control"}),
        ),
        "death_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Deaths",
            widget=forms.NumberInput(attrs={"class": "form-control"}),
        ),
        "report_source": forms.ChoiceField(
            choices=[("", "---------")] + REPORT_SOURCE_CHOICES,
            required=False,
            label="Report Source",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        # ── Epidemiological Classification ────────────────────────────────
        "case_classification": forms.ChoiceField(
            choices=Report.CaseClassification.choices,
            required=True,
            initial=Report.CaseClassification.UNKNOWN,
            label="Case Classification",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "severity_level": forms.ChoiceField(
            choices=Report.SeverityLevel.choices,
            required=False,
            initial=Report.SeverityLevel.UNKNOWN,
            label="Severity Level",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        # ── Sex breakdown counts ──────────────────────────────────────────
        "male_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Male",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "female_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Female",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "unknown_sex_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Unknown Sex",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        # ── Age breakdown counts ──────────────────────────────────────────
        "age_under5_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Under 5",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "age_5_17_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="5–17",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "age_18_59_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="18–59",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "age_60plus_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="60+",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        "unknown_age_count": forms.IntegerField(
            required=True,
            initial=0,
            min_value=0,
            label="Unknown Age",
            widget=forms.NumberInput(attrs={"class": "form-control text-center", "min": "0"}),
        ),
        # ── Additional Information ────────────────────────────────────────
        "health_facility": forms.CharField(
            required=False,
            max_length=255,
            label="Reporting Facility",
            widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Korle Bu Teaching Hospital"}),
        ),
        "case_notes": forms.CharField(
            required=False,
            label="Case Notes",
            widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        ),
    }


# ---------------------------------------------------------------------------
# Shared validation mixin
# ---------------------------------------------------------------------------

class ReportValidationMixin:
    """Cross-field validation rules shared by both report forms."""

    def clean(self):
        cleaned = super().clean()
        case_count = cleaned.get("case_count") or 0
        death_count = cleaned.get("death_count") or 0

        # Deaths cannot exceed total cases
        if death_count > case_count:
            self.add_error(
                "death_count",
                f"Deaths ({death_count}) cannot exceed case count ({case_count}).",
            )

        # Sex counts: if any are non-zero, they must sum to case_count
        male = cleaned.get("male_count") or 0
        female = cleaned.get("female_count") or 0
        unknown_sex = cleaned.get("unknown_sex_count") or 0
        sex_total = male + female + unknown_sex
        if sex_total != 0 and sex_total != case_count:
            self.add_error(
                "unknown_sex_count",
                f"Sex counts total {sex_total} but case count is {case_count}. "
                "They must match, or leave all sex counts as 0.",
            )

        # Age counts: if any are non-zero, they must sum to case_count
        u5 = cleaned.get("age_under5_count") or 0
        a5_17 = cleaned.get("age_5_17_count") or 0
        a18_59 = cleaned.get("age_18_59_count") or 0
        a60 = cleaned.get("age_60plus_count") or 0
        unknown_age = cleaned.get("unknown_age_count") or 0
        age_total = u5 + a5_17 + a18_59 + a60 + unknown_age
        if age_total != 0 and age_total != case_count:
            self.add_error(
                "unknown_age_count",
                f"Age group counts total {age_total} but case count is {case_count}. "
                "They must match, or leave all age counts as 0.",
            )

        return cleaned


# ---------------------------------------------------------------------------
# ReportForm — used by ReportCreateView (no Report instance yet)
# ---------------------------------------------------------------------------

class ReportForm(ReportValidationMixin, forms.Form):
    """Form for creating a new disease report."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in _report_fields().items():
            self.fields[name] = field


# ---------------------------------------------------------------------------
# ReportUpdateForm — used by ReportUpdateView; pre-populates from a Report instance
# ---------------------------------------------------------------------------

class ReportUpdateForm(ReportValidationMixin, forms.Form):
    """Form for editing a DRAFT report."""

    def __init__(self, *args, report: Report | None = None, **kwargs):
        kwargs.pop("initial", None)
        super().__init__(*args, **kwargs)

        for name, field in _report_fields().items():
            self.fields[name] = field

        if report is not None:
            self.initial = _initial_from_report(report)


def _initial_from_report(report: Report) -> dict:
    """Derive form initial values from a saved Report instance."""
    return {
        "disease": report.disease,
        "location": report.location,
        "observed_date": report.observed_at.date(),
        "observed_time": report.observed_at.time(),
        "report_type": report.report_type,
        "case_count": report.case_count,
        "death_count": report.death_count,
        "report_source": report.report_source or "",
        "case_classification": report.case_classification,
        "severity_level": report.severity_level,
        "male_count": report.male_count,
        "female_count": report.female_count,
        "unknown_sex_count": report.unknown_sex_count,
        "age_under5_count": report.age_under5_count,
        "age_5_17_count": report.age_5_17_count,
        "age_18_59_count": report.age_18_59_count,
        "age_60plus_count": report.age_60plus_count,
        "unknown_age_count": report.unknown_age_count,
        "health_facility": report.health_facility or "",
        "case_notes": report.case_notes or "",
    }
