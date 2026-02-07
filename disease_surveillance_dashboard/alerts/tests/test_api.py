"""Tests for alerts API endpoints."""

from datetime import datetime
from datetime import timezone

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from disease_surveillance_dashboard.access_control.models import Role
from reference_data.models import Disease
from reference_data.models import Location

from ..models import Alert
from ..models import AlertEscalation
from ..models import AlertNote
from ..models import AlertStatus

User = get_user_model()


class AlertStatusAPITestCase(APITestCase):
    """Test cases for AlertStatus API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="alertsadmin@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)
        self.api_url = "/api/v1/alerts/statuses/"

    def test_alert_status_create(self):
        """Test creating a new alert status."""
        data = {
            "status_name": "New",
            "description": "Newly created alert",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertStatus.objects.count(), 1)


class AlertAPITestCase(APITestCase):
    """Test cases for Alert API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="alertcreator@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.alert_status = AlertStatus.objects.create(
            status_name="New",
            description="New alert",
        )
        self.api_url = "/api/v1/alerts/alerts/"

    def test_alert_create(self):
        """Test creating a new alert."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "period_start": "2025-01-01T00:00:00Z",
            "period_end": "2025-01-07T23:59:59Z",
            "baseline_value": "10.5000",
            "observed_value": "25.7500",
            "threshold_rule": "observed > 1.5x baseline",
            "severity_level": "High",
            "status": self.alert_status.id,
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Alert.objects.count(), 1)

    def test_alert_list(self):
        """Test retrieving list of alerts."""
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            baseline_value=10.5000,
            observed_value=20.0000,
            threshold_rule="CUSUM > h",
            severity_level="Medium",
            status=self.alert_status,
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class AlertNoteAPITestCase(APITestCase):
    """Test cases for AlertNote API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="notetaker@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Cholera")
        self.location = Location.objects.create(district_name="Tema")
        self.alert_status = AlertStatus.objects.create(status_name="Investigating")
        self.alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            baseline_value=5.0000,
            observed_value=15.0000,
            threshold_rule="observed > 2x baseline",
            severity_level="High",
            status=self.alert_status,
        )
        self.api_url = "/api/v1/alerts/notes/"

    def test_alert_note_create(self):
        """Test creating a new alert note."""
        data = {
            "alert": self.alert.id,
            "noted_by": self.user.id,
            "note_text": "Initial investigation started. Contacting local health facilities.",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertNote.objects.count(), 1)


class AlertEscalationAPITestCase(APITestCase):
    """Test cases for AlertEscalation API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="escalator@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Dengue")
        self.location = Location.objects.create(district_name="Kumasi")
        self.alert_status = AlertStatus.objects.create(status_name="New")
        self.alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            baseline_value=3.0000,
            observed_value=12.0000,
            threshold_rule="observed > 3x baseline",
            severity_level="High",
            status=self.alert_status,
        )
        self.from_role = Role.objects.create(
            role_name="HEALTH_OFFICER",
            description="Health Officer role",
        )
        self.to_role = Role.objects.create(
            role_name="PUBLIC_HEALTH_DIRECTOR",
            description="Public Health Director role",
        )
        self.api_url = "/api/v1/alerts/escalations/"

    def test_alert_escalation_create(self):
        """Test creating a new alert escalation."""
        data = {
            "alert": self.alert.id,
            "escalated_from_role": self.from_role.id,
            "escalated_to_role": self.to_role.id,
            "escalation_reason": "Severity level requires director approval for resource allocation",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AlertEscalation.objects.count(), 1)

