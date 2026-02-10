"""Tests for alerts API endpoints."""

from datetime import UTC
from datetime import date
from datetime import datetime

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from disease_surveillance_dashboard.access_control.models import Role
from disease_surveillance_dashboard.analytics.models import TrendMetric
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
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
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
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
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
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
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


class AlertEvaluationAPITestCase(APITestCase):
    """Test cases for alert evaluation endpoint."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="evaluator@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.alert_status = AlertStatus.objects.create(
            status_name="New",
            description="New alert",
        )
        self.api_url = "/api/v1/alerts/alerts/evaluate/"

    def test_evaluate_no_alert_below_threshold(self):
        """Test that no alert is generated when CUSUM is below threshold."""
        # Create trend metric with low observed value (below threshold)
        # CUSUM = max(0, 0 + (5 - 4.0 - 0.5)) = 0.5, which is below threshold of 5.0
        trend_metric = TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 7),
            total_cases=5,  # Low case count
            moving_avg=4.0,  # Baseline close to observed
        )

        data = {"trend_metric_id": trend_metric.id}
        response = self.client.post(self.api_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("No alert generated", response.data["message"])
        self.assertEqual(Alert.objects.count(), 0)

    def test_evaluate_alert_when_cusum_exceeds_threshold(self):
        """Test that alert is generated when CUSUM exceeds threshold."""
        # Create trend metric with high observed value (will exceed threshold)
        # CUSUM = max(0, 0 + (20 - 4.0 - 0.5)) = 15.5, which exceeds threshold of 5.0
        trend_metric = TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 7),
            total_cases=20,  # High case count
            moving_avg=4.0,  # Low baseline
        )

        data = {"trend_metric_id": trend_metric.id}
        response = self.client.post(self.api_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("Alert generated", response.data["message"])
        self.assertEqual(Alert.objects.count(), 1)

        alert = Alert.objects.first()
        self.assertEqual(alert.disease, self.disease)
        self.assertEqual(alert.location, self.location)
        self.assertEqual(alert.severity_level, "High")  # CUSUM 15.5 >= 15.0

    def test_evaluate_alert_severity_levels(self):
        """Test that alert severity is set correctly based on CUSUM magnitude."""
        # Test Low severity (CUSUM between 5 and 10)
        # CUSUM = max(0, 0 + (10 - 4.0 - 0.5)) = 5.5
        trend_metric_low = TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 7),
            total_cases=10,  # Will give CUSUM = 5.5
            moving_avg=4.0,
        )

        data = {"trend_metric_id": trend_metric_low.id}
        response = self.client.post(self.api_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert = Alert.objects.first()
        # CUSUM = 10 - 4.0 - 0.5 = 5.5, so it's Low severity (5 <= CUSUM < 10)
        self.assertEqual(alert.severity_level, "Low")

    def test_evaluate_alert_linked_to_disease_and_location(self):
        """Test that generated alert is correctly linked to disease and location."""
        trend_metric = TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 7),
            total_cases=25,  # High enough to trigger alert
            moving_avg=5.0,
        )

        data = {"trend_metric_id": trend_metric.id}
        response = self.client.post(self.api_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        alert = Alert.objects.first()
        self.assertEqual(alert.disease, self.disease)
        self.assertEqual(alert.location, self.location)
        self.assertIsNotNone(alert.threshold_rule)
        self.assertIn("CUSUM", alert.threshold_rule)

