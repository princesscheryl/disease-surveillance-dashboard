from rest_framework import serializers

from .models import AuditLog
from .models import Export


class ExportSerializer(serializers.ModelSerializer):
    """Serializer for Export model."""

    class Meta:
        model = Export
        fields = "__all__"
        read_only_fields = ["generated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model."""

    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = ["timestamp"]

