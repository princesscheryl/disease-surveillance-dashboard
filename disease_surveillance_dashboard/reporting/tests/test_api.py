"""Tests for reporting API endpoints."""

from datetime import UTC
from datetime import datetime

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from reference_data.models import Disease
from reference_data.models import Location

from ..models import DuplicateFlag
from ..models import Report
from ..models import ReportStatus

User = get_user_model()


class ReportStatusAPITestCase(APITestCase):
    """Test cases for ReportStatus API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.status = ReportStatus.objects.create(
            status_name="PENDING",
            description="Report pending verification",
        )
        self.api_url = "/api/v1/reporting/statuses/"

    def test_report_status_list(self):
        """Test retrieving list of report statuses."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        status_names = [s["status_name"] for s in response.data]
        self.assertIn(self.status.status_name, status_names)


class ReportAPITestCase(APITestCase):
    """Test cases for Report API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="reporter@example.com",
            password="testpass123",
            first_name="Test",
            last_name="Reporter",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.status = ReportStatus.objects.create(status_name="PENDING")
        self.api_url = "/api/v1/reporting/reports/"

    def test_report_create(self):
        """Test creating a new report."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "reported_by": self.user.id,
            "observed_at": "2025-01-27T10:00:00Z",
            "case_notes": "Patient presented with fever and chills",
            "status": self.status.id,
            "report_source": "WEB",
            "case_count": 3,
            "sex": "FEMALE",
            "age_group": "AGE_18_59",
            "severity_level": "MODERATE",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Report.objects.count(), 1)
        self.assertEqual(response.data["case_count"], 3)
        self.assertEqual(response.data["sex"], "FEMALE")
        self.assertEqual(response.data["age_group"], "AGE_18_59")
        self.assertEqual(response.data["severity_level"], "MODERATE")

    def test_report_list(self):
        """Test retrieving list of reports."""
        Report.objects.create(
            disease=self.disease,
            location=self.location,
            reported_by=self.user,
            observed_at=datetime.now(UTC),
            status=self.status,
            case_count=2,
            sex="MALE",
            age_group="AGE_5_17",
            severity_level="MILD",
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_report_source_can_be_null(self):
        """Test that report_source can be null/blank."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "reported_by": self.user.id,
            "observed_at": "2025-01-27T10:00:00Z",
            "case_notes": "Test case without source",
            "status": self.status.id,
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("report_source"))
        # Verify defaults are applied
        self.assertEqual(response.data.get("case_count"), 1)
        self.assertEqual(response.data.get("sex"), "UNKNOWN")
        self.assertEqual(response.data.get("age_group"), "UNKNOWN")
        self.assertEqual(response.data.get("severity_level"), "UNKNOWN")


class DuplicateFlagAPITestCase(APITestCase):
    """Test cases for DuplicateFlag API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="reviewer@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Cholera")
        self.location = Location.objects.create(district_name="Tema")
        self.status = ReportStatus.objects.create(status_name="VERIFIED")
        self.report = Report.objects.create(
            disease=self.disease,
            location=self.location,
            reported_by=self.user,
            observed_at=datetime.now(UTC),
            status=self.status,
            case_count=1,
        )
        self.api_url = "/api/v1/reporting/duplicate-flags/"

    def test_duplicate_flag_create(self):
        """Test creating a new duplicate flag."""
        data = {
            "report": self.report.id,
            "flagged_reason": "Similar report found with same disease and location",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DuplicateFlag.objects.count(), 1)

