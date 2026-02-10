"""Tests for exports API endpoints."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import AuditLog
from ..models import Export

User = get_user_model()


class ExportAPITestCase(APITestCase):
    """Test cases for Export API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="exporter@example.com",
            password="testpass123",
            full_name="Test Exporter",
        )
        self.client.force_authenticate(user=self.user)
        self.api_url = "/api/v1/exports/"

    def test_export_create(self):
        """Test creating a new export."""
        data = {
            "export_type": "CSV",
            "generated_by": self.user.id,
            "filters_used": {"disease": 1, "location": 2},
            "status": "PENDING",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Export.objects.count(), 1)

    def test_export_list(self):
        """Test retrieving list of exports."""
        Export.objects.create(
            export_type="PDF",
            generated_by=self.user,
            status="COMPLETED",
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle pagination if response is paginated
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data

        self.assertEqual(len(data), 1)

    def test_export_filter_by_type(self):
        """Test filtering exports by export_type."""
        Export.objects.create(
            export_type="CSV",
            generated_by=self.user,
            status="PENDING",
        )
        Export.objects.create(
            export_type="PDF",
            generated_by=self.user,
            status="COMPLETED",
        )
        response = self.client.get(self.api_url, {"export_type": "CSV"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle pagination if response is paginated
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["export_type"], "CSV")


class AuditLogAPITestCase(APITestCase):
    """Test cases for AuditLog API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="auditor@example.com",
            password="testpass123",
            full_name="Test Auditor",
        )
        self.client.force_authenticate(user=self.user)
        self.api_url = "/api/v1/audit-logs/"

    def test_audit_log_create(self):
        """Test creating a new audit log."""
        data = {
            "actor_user": self.user.id,
            "action_type": "CREATE",
            "entity_type": "Report",
            "entity_id": "123",
            "details": {"field": "value"},
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AuditLog.objects.count(), 1)

    def test_audit_log_list(self):
        """Test retrieving list of audit logs."""
        AuditLog.objects.create(
            actor_user=self.user,
            action_type="UPDATE",
            entity_type="Alert",
            entity_id="456",
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle pagination if response is paginated
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data

        self.assertEqual(len(data), 1)

    def test_audit_log_filter_by_entity_type(self):
        """Test filtering audit logs by entity_type."""
        AuditLog.objects.create(
            actor_user=self.user,
            action_type="CREATE",
            entity_type="Report",
            entity_id="123",
        )
        AuditLog.objects.create(
            actor_user=self.user,
            action_type="DELETE",
            entity_type="Alert",
            entity_id="456",
        )
        response = self.client.get(self.api_url, {"entity_type": "Report"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle pagination if response is paginated
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data

        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["entity_type"], "Report")

