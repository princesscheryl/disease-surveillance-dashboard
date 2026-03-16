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
            first_name="Test",
            last_name="Analyst",
        )
        self.role = Role.objects.create(
            role_name="ANALYST",
            description="Analyst role",
        )
        UserRole.objects.create(user=self.user, role=self.role)

        # Create user without dashboard access (role not in DASHBOARD_ALLOWED_ROLES)
        self.chw_user = User.objects.create_user(
            email="chw@example.com",
            password="testpass123",
            first_name="CHW",
            last_name="User",
        )
        no_dash_role = Role.objects.create(
            role_name="REPORTER",
            description="Reporter only; no dashboard access",
        )
        UserRole.objects.create(user=self.chw_user, role=no_dash_role)

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
        self.report_status, _ = ReportStatus.objects.get_or_create(
            status_name="VERIFIED",
            defaults={"description": "Verified report"},
        )
        self.alert_status, _ = AlertStatus.objects.get_or_create(
            status_name="New",
            defaults={"description": "New alert"},
        )

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

    def test_dashboard_anomalies_returns_correct_shape(self):
        """Test anomalies endpoint returns list with date, cases, anomaly_score, is_anomaly."""
        response = self.client.get("/api/v1/dashboard/anomalies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        for item in response.data:
            self.assertIn("date", item)
            self.assertIn("cases", item)
            self.assertIn("anomaly_score", item)
            self.assertIn("is_anomaly", item)

    def test_dashboard_anomalies_deterministic_with_random_state(self):
        """Test that calling anomalies twice with same params yields same results."""
        params = "start_date=2020-01-01&end_date=2020-02-01"
        r1 = self.client.get(f"/api/v1/dashboard/anomalies/?{params}")
        r2 = self.client.get(f"/api/v1/dashboard/anomalies/?{params}")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r1.data), len(r2.data))
        for i, (a, b) in enumerate(zip(r1.data, r2.data)):
            self.assertEqual(a["date"], b["date"])
            self.assertEqual(a["is_anomaly"], b["is_anomaly"])
            self.assertAlmostEqual(a["anomaly_score"], b["anomaly_score"], places=5)

    def test_dashboard_forecast_returns_correct_shape(self):
        """Test forecast endpoint returns forecast list with date, forecast, lower_ci, upper_ci."""
        response = self.client.get("/api/v1/dashboard/forecast/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("forecast", response.data)
        self.assertIsInstance(response.data["forecast"], list)
        for item in response.data["forecast"]:
            self.assertIn("date", item)
            self.assertIn("forecast", item)
            self.assertIn("lower_ci", item)
            self.assertIn("upper_ci", item)

    def test_dashboard_forecast_horizon_param(self):
        """Test forecast endpoint returns horizon items when enough data."""
        response = self.client.get("/api/v1/dashboard/forecast/?horizon=7")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("forecast", response.data)
        # With few points we may get message and empty forecast; with enough we get 7 items
        if response.data["forecast"]:
            self.assertEqual(len(response.data["forecast"]), 7)

    def test_dashboard_forecast_short_series_returns_message(self):
        """Test forecast endpoint returns friendly message when series too short."""
        # Default test data has only 5 reports -> 5 daily points; ARIMA needs at least 7
        response = self.client.get("/api/v1/dashboard/forecast/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["forecast"], [])
        self.assertIn("message", response.data)
        self.assertIn("Not enough data", response.data["message"])

