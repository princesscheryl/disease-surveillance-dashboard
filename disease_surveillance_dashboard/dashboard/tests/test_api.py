"""Tests for dashboard API endpoints."""

from datetime import UTC
from datetime import date
from datetime import datetime
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from disease_surveillance_dashboard.access_control.models import Role
from disease_surveillance_dashboard.access_control.models import UserRole
from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertStatus
from disease_surveillance_dashboard.investigations.models import InvestigationTask
from disease_surveillance_dashboard.reporting.models import Report
from disease_surveillance_dashboard.reporting.models import ReportStatus
from reference_data.models import Disease
from reference_data.models import Location

User = get_user_model()


class DashboardAPITestCase(APITestCase):
    """Base test case for dashboard API endpoints."""

    def setUp(self):
        """Set up test data."""
        # Create user with dashboard access role
        self.user = User.objects.create_user(
            email="analyst@example.com",
            password="testpass123",
            full_name="Test Analyst",
        )
        self.role = Role.objects.create(
            role_name="ANALYST",
            description="Analyst role",
        )
        UserRole.objects.create(user=self.user, role=self.role)

        # Create user without dashboard access
        self.chw_user = User.objects.create_user(
            email="chw@example.com",
            password="testpass123",
            full_name="CHW User",
        )
        chw_role = Role.objects.create(
            role_name="CHW",
            description="Community Health Worker",
        )
        UserRole.objects.create(user=self.chw_user, role=chw_role)

        # Create test data
        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(
            district_name="Accra Metro",
            latitude=5.6037,
            longitude=-0.1870,
        )
        self.location_no_coords = Location.objects.create(
            district_name="Tema",
            latitude=None,
            longitude=None,
        )
        self.report_status = ReportStatus.objects.create(status_name="VERIFIED")
        self.alert_status = AlertStatus.objects.create(status_name="New")

        # Create reports with case_count
        now = timezone.now()
        for i in range(5):
            Report.objects.create(
                disease=self.disease,
                location=self.location,
                reported_by=self.user,
                observed_at=now - timedelta(days=i),
                status=self.report_status,
                case_count=2 + i,  # Varying case counts
            )

        self.client.force_authenticate(user=self.user)

    def test_dashboard_summary_authenticated_with_role(self):
        """Test summary endpoint returns 200 for user with dashboard role."""
        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("cases_7d", response.data)
        self.assertIn("cases_30d", response.data)
        self.assertIn("reports_7d", response.data)
        self.assertIn("active_alerts", response.data)

    def test_dashboard_summary_403_without_role(self):
        """Test summary endpoint returns 403 for user without dashboard role."""
        self.client.force_authenticate(user=self.chw_user)
        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_summary_aggregation_correct(self):
        """Test summary aggregation uses case_count correctly."""
        # We created 5 reports with case_count 2, 3, 4, 5, 6 = total 20 cases
        response = self.client.get("/api/v1/dashboard/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # All 5 reports are within 30 days, so cases_30d should be 20
        self.assertGreaterEqual(response.data["cases_30d"], 20)

    def test_dashboard_cases_timeseries(self):
        """Test cases timeseries endpoint."""
        response = self.client.get("/api/v1/dashboard/cases-timeseries/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        if len(response.data) > 0:
            self.assertIn("date", response.data[0])
            self.assertIn("cases", response.data[0])

    def test_dashboard_top_diseases(self):
        """Test top diseases endpoint."""
        response = self.client.get("/api/v1/dashboard/top-diseases/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_dashboard_map_points_skips_no_coords(self):
        """Test map points endpoint skips locations without coordinates."""
        response = self.client.get("/api/v1/dashboard/map-points/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        # Should only include location with coordinates
        location_ids = [p["location_id"] for p in response.data]
        self.assertIn(self.location.id, location_ids)
        self.assertNotIn(self.location_no_coords.id, location_ids)

    def test_dashboard_recent_alerts(self):
        """Test recent alerts endpoint."""
        # Create an alert
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value=10.0,
            observed_value=25.0,
            threshold_rule="CUSUM > 5",
            severity_level="High",
            status=self.alert_status,
        )

        response = self.client.get("/api/v1/dashboard/recent-alerts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_dashboard_recent_investigations(self):
        """Test recent investigations endpoint."""
        alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value=10.0,
            observed_value=25.0,
            threshold_rule="CUSUM > 5",
            severity_level="High",
            status=self.alert_status,
        )
        InvestigationTask.objects.create(
            alert=alert,
            assigned_to=self.user,
            task_status="OPEN",
        )

        response = self.client.get("/api/v1/dashboard/recent-investigations/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_dashboard_evaluate_role_restricted(self):
        """Test evaluate endpoint is role restricted."""
        # CHW user should not be able to evaluate
        self.client.force_authenticate(user=self.chw_user)
        response = self.client.post(
            "/api/v1/dashboard/evaluate/",
            {"trend_metric_id": 1},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_evaluate_returns_expected_shape(self):
        """Test evaluate endpoint returns expected response shape."""
        from disease_surveillance_dashboard.analytics.models import TrendMetric

        trend_metric = TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date.today() - timedelta(days=7),
            period_end=date.today(),
            total_cases=5,
            moving_avg=2.0,
        )

        response = self.client.post(
            "/api/v1/dashboard/evaluate/",
            {"trend_metric_id": trend_metric.id},
            format="json",
        )

        # Should return 200 (no alert) or 201 (alert created)
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        self.assertIn("message", response.data)
        self.assertIn("cusum_value", response.data)

