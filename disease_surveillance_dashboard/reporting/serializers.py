from rest_framework import serializers

from .models import DuplicateFlag
from .models import Report
from .models import ReportStatus


class ReportStatusSerializer(serializers.ModelSerializer):
    """Serializer for ReportStatus model."""

    class Meta:
        model = ReportStatus
        fields = "__all__"
        read_only_fields = ["created_at"]


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model."""

    class Meta:
        model = Report
        fields = "__all__"
        read_only_fields = ["submitted_at"]


class DuplicateFlagSerializer(serializers.ModelSerializer):
    """Serializer for DuplicateFlag model."""

    class Meta:
        model = DuplicateFlag
        fields = "__all__"
        read_only_fields = ["flagged_at"]

