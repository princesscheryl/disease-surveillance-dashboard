"""Tests for reporting views."""

from datetime import date
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from reference_data.models import Disease
from reference_data.models import Location

from ..models import Report
from ..models import ReportStatus

User = get_user_model()


class ReportCreateViewTestCase(TestCase):
    """Test cases for ReportCreateView."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="reporter@example.com",
            password="testpass123",
            full_name="Test Reporter",
        )
        self.disease = Disease.objects.create(disease_name="Malaria", is_active=True)
        self.location = Location.objects.create(district_name="Accra Metro", is_active=True)
        self.url = reverse("reporting:report_new")

    def test_get_redirects_when_anonymous(self):
        """Test that GET /reports/new/ redirects when anonymous."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_get_returns_200_when_logged_in(self):
        """Test that GET /reports/new/ returns 200 when logged in."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Report Case")
        self.assertContains(response, "Disease")
        self.assertContains(response, "Reporting District")

    def test_post_creates_report_with_correct_fields(self):
        """Test POST creates a Report row with correct fields."""
        self.client.force_login(self.user)
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "observed_date": "2025-02-17",
            "observed_time": "14:30",
            "case_count": 2,
            "report_source": "FACILITY",
            "sex": "FEMALE",
            "age_group": "AGE_18_59",
            "severity_level": "MODERATE",
            "facility_unit_name": "Emergency Unit",
            "case_notes": "Patient presented with symptoms",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/dashboard/")

        # Verify Report was created
        self.assertEqual(Report.objects.count(), 1)
        report = Report.objects.first()
        self.assertEqual(report.disease, self.disease)
        self.assertEqual(report.location, self.location)
        self.assertEqual(report.reported_by, self.user)
        self.assertEqual(report.case_count, 2)
        self.assertEqual(report.report_source, "FACILITY")
        self.assertEqual(report.sex, Report.Sex.FEMALE)
        self.assertEqual(report.age_group, Report.AgeGroup.AGE_18_59)
        self.assertEqual(report.severity_level, Report.SeverityLevel.MODERATE)
        self.assertEqual(report.observed_at.date(), date(2025, 2, 17))
        self.assertEqual(report.observed_at.time(), time(14, 30))

        # Verify status is SUBMITTED
        self.assertEqual(report.status.status_name, "SUBMITTED")

        # Verify facility_unit_name was prepended to case_notes
        self.assertIn("Facility/Unit: Emergency Unit", report.case_notes)
        self.assertIn("Patient presented with symptoms", report.case_notes)

    def test_post_creates_report_with_defaults(self):
        """Test POST creates report with default values when optional fields omitted."""
        self.client.force_login(self.user)
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "observed_date": "2025-02-17",
            "case_count": 1,
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)

        report = Report.objects.first()
        self.assertEqual(report.case_count, 1)
        self.assertEqual(report.sex, Report.Sex.UNKNOWN)
        self.assertEqual(report.age_group, Report.AgeGroup.UNKNOWN)
        self.assertEqual(report.severity_level, Report.SeverityLevel.UNKNOWN)
        self.assertIsNone(report.report_source)
        # observed_time defaults to 12:00
        self.assertEqual(report.observed_at.time(), time(12, 0))

    def test_post_with_facility_unit_name_only(self):
        """Test facility_unit_name prepending when case_notes is empty."""
        self.client.force_login(self.user)
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "observed_date": "2025-02-17",
            "case_count": 1,
            "facility_unit_name": "Outpatient Clinic",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)

        report = Report.objects.first()
        self.assertEqual(report.case_notes, "Facility/Unit: Outpatient Clinic")
