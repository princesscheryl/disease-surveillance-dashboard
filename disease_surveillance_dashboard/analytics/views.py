from rest_framework import viewsets

from .models import BaselineMetric
from .models import TrendMetric
from .serializers import BaselineMetricSerializer
from .serializers import TrendMetricSerializer


class BaselineMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for BaselineMetric model."""

    queryset = BaselineMetric.objects.select_related("disease", "location")
    serializer_class = BaselineMetricSerializer
    filterset_fields = ["disease", "location", "period_type", "baseline_method"]
    search_fields = ["disease__disease_name", "location__district_name", "location__area_name"]


class TrendMetricViewSet(viewsets.ModelViewSet):
    """ViewSet for TrendMetric model."""

    queryset = TrendMetric.objects.select_related("disease", "location")
    serializer_class = TrendMetricSerializer
    filterset_fields = ["disease", "location"]
    search_fields = ["disease__disease_name", "location__district_name", "location__area_name"]

