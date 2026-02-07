from rest_framework import serializers

from .models import BaselineMetric
from .models import TrendMetric


class BaselineMetricSerializer(serializers.ModelSerializer):
    """Serializer for BaselineMetric model."""

    class Meta:
        model = BaselineMetric
        fields = "__all__"
        read_only_fields = ["computed_at"]


class TrendMetricSerializer(serializers.ModelSerializer):
    """Serializer for TrendMetric model."""

    class Meta:
        model = TrendMetric
        fields = "__all__"
        read_only_fields = ["computed_at"]

