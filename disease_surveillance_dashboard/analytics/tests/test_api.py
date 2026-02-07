"""Tests for analytics API endpoints."""

from datetime import date

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from reference_data.models import Disease
from reference_data.models import Location

from ..models import BaselineMetric
from ..models import TrendMetric

User = get_user_model()


class BaselineMetricAPITestCase(APITestCase):
    """Test cases for BaselineMetric API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="analyst@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.api_url = "/api/v1/analytics/baselines/"

    def test_baseline_metric_create(self):
        """Test creating a new baseline metric."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "period_type": "weekly",
            "baseline_method": "moving_average",
            "baseline_value": "15.5000",
            "computed_for_start": "2025-01-01",
            "computed_for_end": "2025-01-07",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BaselineMetric.objects.count(), 1)

    def test_baseline_metric_list(self):
        """Test retrieving list of baseline metrics."""
        BaselineMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_type="daily",
            baseline_method="cusum",
            baseline_value=10.2500,
            computed_for_start=date(2025, 1, 1),
            computed_for_end=date(2025, 1, 31),
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class TrendMetricAPITestCase(APITestCase):
    """Test cases for TrendMetric API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="trendanalyst@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.disease = Disease.objects.create(disease_name="Cholera")
        self.location = Location.objects.create(district_name="Tema")
        self.api_url = "/api/v1/analytics/trends/"

    def test_trend_metric_create(self):
        """Test creating a new trend metric."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "period_start": "2025-01-01",
            "period_end": "2025-01-07",
            "total_cases": 42,
            "moving_avg": "6.0000",
            "pct_change": "15.5000",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TrendMetric.objects.count(), 1)

    def test_trend_metric_list(self):
        """Test retrieving list of trend metrics."""
        TrendMetric.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=date(2025, 1, 1),
            period_end=date(2025, 1, 7),
            total_cases=25,
        )
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_trend_metric_nullable_fields(self):
        """Test that moving_avg and pct_change can be null/blank."""
        data = {
            "disease": self.disease.id,
            "location": self.location.id,
            "period_start": "2025-01-08",
            "period_end": "2025-01-14",
            "total_cases": 30,
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(response.data.get("moving_avg"))
        self.assertIsNone(response.data.get("pct_change"))

