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
        "case_count": forms.IntegerField(
            required=True,
            initial=1,
            min_value=1,
            label="Case Count",
            widget=forms.NumberInput(attrs={"class": "form-control"}),
        ),
        "report_source": forms.ChoiceField(
            choices=[("", "---------")] + REPORT_SOURCE_CHOICES,
            required=False,
            label="Report Source",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "sex": forms.ChoiceField(
            choices=Report.Sex.choices,
            required=False,
            initial=Report.Sex.UNKNOWN,
            label="Sex",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "age_group": forms.ChoiceField(
            choices=Report.AgeGroup.choices,
            required=False,
            initial=Report.AgeGroup.UNKNOWN,
            label="Age Group",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "severity_level": forms.ChoiceField(
            choices=Report.SeverityLevel.choices,
            required=False,
            initial=Report.SeverityLevel.UNKNOWN,
            label="Severity Level",
            widget=forms.Select(attrs={"class": "form-select"}),
        ),
        "facility_unit_name": forms.CharField(
            required=False,
            max_length=255,
            label="Facility/Unit Name",
            widget=forms.TextInput(attrs={"class": "form-control"}),
        ),
        "case_notes": forms.CharField(
            required=False,
            label="Case Notes",
            widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        ),
    }


# ---------------------------------------------------------------------------
# ReportForm — used by ReportCreateView (no Report instance yet)
# ---------------------------------------------------------------------------

class ReportForm(forms.Form):
    """Form for creating a new disease report."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in _report_fields().items():
            self.fields[name] = field


# ---------------------------------------------------------------------------
# ReportUpdateForm — used by ReportUpdateView; pre-populates from a Report instance
# ---------------------------------------------------------------------------

class ReportUpdateForm(forms.Form):
    """Form for editing a DRAFT report.

    Accepts an optional ``report`` keyword argument.  When supplied the form
    pre-populates every field from the existing Report instance so the user
    never sees a blank edit form.

    Why initial is applied AFTER super().__init__
    ----------------------------------------------
    Django resolves initial values during widget rendering, which happens
    when the template calls {{ field }}.  The form's ``initial`` dict is
    consulted per-field at that point.  However, for an unbound form Django
    also calls get_initial_for_field() inside BoundField.value(), which
    reads from self.initial — this works fine as long as self.initial is
    populated before the template renders.

    The important constraint is that fields must exist in self.fields before
    we write to self.initial for them, otherwise BoundField.value() will
    never be called for those keys (the fields don't exist to iterate over).
    We therefore:
      1. Call super().__init__() with NO initial kwarg — this sets up the
         form machinery (self.data, self.files, self.initial = {}, etc.).
      2. Add all field objects to self.fields.
      3. Then overwrite self.initial with the report-derived values.
    This guarantees every field exists when the initial dict is read.
    """

    def __init__(self, *args, report: Report | None = None, **kwargs):
        # Strip 'report' out of kwargs before passing to super — Django's
        # Form.__init__ does not accept unknown keyword arguments.
        # Also strip any caller-supplied 'initial' so we control it fully.
        kwargs.pop("initial", None)

        super().__init__(*args, **kwargs)

        # Step 1: register all fields on this form instance.
        for name, field in _report_fields().items():
            self.fields[name] = field

        # Step 2: overwrite self.initial AFTER fields are attached.
        # This is safe because initial values are only consumed during
        # template rendering (BoundField.value()), which happens after
        # __init__ returns.
        if report is not None:
            self.initial = _initial_from_report(report)


def _initial_from_report(report: Report) -> dict:
    """Derive form initial values from a saved Report instance."""
    # Extract facility_unit_name back out of case_notes if it was prepended.
    case_notes = report.case_notes or ""
    facility_unit_name = ""
    if case_notes.startswith("Facility/Unit: "):
        first_line, _, remainder = case_notes.partition("\n\n")
        facility_unit_name = first_line.removeprefix("Facility/Unit: ")
        case_notes = remainder

    return {
        "disease": report.disease,
        "location": report.location,
        "observed_date": report.observed_at.date(),
        "observed_time": report.observed_at.time(),
        "case_count": report.case_count,
        "report_source": report.report_source or "",
        "sex": report.sex,
        "age_group": report.age_group,
        "severity_level": report.severity_level,
        "facility_unit_name": facility_unit_name,
        "case_notes": case_notes,
    }
