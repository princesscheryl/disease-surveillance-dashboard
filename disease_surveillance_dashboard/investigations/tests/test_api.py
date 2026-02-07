"""Tests for investigations API endpoints."""

from datetime import datetime
from datetime import timezone

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertStatus
from reference_data.models import Disease
from reference_data.models import Location

from ..models import InvestigationTask

User = get_user_model()


class InvestigationTaskAPITestCase(APITestCase):
    """Test cases for InvestigationTask API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="investigator@example.com",
            password="testpass123",
            full_name="Test Investigator",
        )
        self.assigner = User.objects.create_user(
            email="assigner@example.com",
            password="testpass123",
            full_name="Test Assigner",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.alert_status = AlertStatus.objects.create(
            status_name="New",
            description="New alert",
        )
        self.alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(timezone.utc),
            period_end=datetime.now(timezone.utc),
            baseline_value=10.5000,
            observed_value=25.7500,
            threshold_rule="observed > 1.5x baseline",
            severity_level="High",
            status=self.alert_status,
        )
        self.api_url = "/api/v1/investigations/tasks/"

    def test_investigation_task_create(self):
        """Test creating a new investigation task."""
        data = {
            "alert": self.alert.id,
            "assigned_to": self.user.id,
            "assigned_by": self.assigner.id,
            "task_status": "OPEN",
            "due_at": "2025-02-15T23:59:59Z",
            "outcome": None,
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(InvestigationTask.objects.count(), 1)

    def test_investigation_task_list(self):
        """Test retrieving list of investigation tasks."""
        InvestigationTask.objects.create(
            alert=self.alert,
            assigned_to=self.user,
            assigned_by=self.assigner,
            task_status="OPEN",
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_investigation_task_filter_by_status(self):
        """Test filtering investigation tasks by task_status."""
        InvestigationTask.objects.create(
            alert=self.alert,
            assigned_to=self.user,
            assigned_by=self.assigner,
            task_status="OPEN",
        )
        InvestigationTask.objects.create(
            alert=self.alert,
            assigned_to=self.user,
            assigned_by=self.assigner,
            task_status="IN_PROGRESS",
        )
        response = self.client.get(self.api_url, {"task_status": "OPEN"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Handle pagination if response is paginated
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        
        # Verify we only get OPEN tasks
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["task_status"], "OPEN")
        
        # Verify all returned tasks have the filtered status
        for task in data:
            self.assertEqual(task["task_status"], "OPEN")

    def test_investigation_task_nullable_fields(self):
        """Test that nullable fields can be null/blank."""
        data = {
            "alert": self.alert.id,
            "task_status": "OPEN",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("assigned_to"))
        self.assertIsNone(response.data.get("assigned_by"))
        self.assertIsNone(response.data.get("due_at"))
        self.assertIsNone(response.data.get("outcome"))

