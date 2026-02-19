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


class ReportForm(forms.Form):
    """Form for creating a new disease report."""

    disease = forms.ModelChoiceField(
        queryset=Disease.objects.filter(is_active=True).order_by("disease_name"),
        required=True,
        label="Disease",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    location = forms.ModelChoiceField(
        queryset=Location.objects.filter(is_active=True).order_by("district_name", "area_name"),
        required=True,
        label="Reporting District",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    observed_date = forms.DateField(
        required=True,
        label="Observed Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    observed_time = forms.TimeField(
        required=False,
        label="Observed Time (Optional)",
        widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
    )
    case_count = forms.IntegerField(
        required=True,
        initial=1,
        min_value=1,
        label="Case Count",
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )
    report_source = forms.ChoiceField(
        choices=[("", "---------")] + REPORT_SOURCE_CHOICES,
        required=False,
        label="Report Source",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    sex = forms.ChoiceField(
        choices=Report.Sex.choices,
        required=False,
        initial=Report.Sex.UNKNOWN,
        label="Sex",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    age_group = forms.ChoiceField(
        choices=Report.AgeGroup.choices,
        required=False,
        initial=Report.AgeGroup.UNKNOWN,
        label="Age Group",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    severity_level = forms.ChoiceField(
        choices=Report.SeverityLevel.choices,
        required=False,
        initial=Report.SeverityLevel.UNKNOWN,
        label="Severity Level",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    facility_unit_name = forms.CharField(
        required=False,
        max_length=255,
        label="Facility/Unit Name",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    case_notes = forms.CharField(
        required=False,
        label="Case Notes",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )
