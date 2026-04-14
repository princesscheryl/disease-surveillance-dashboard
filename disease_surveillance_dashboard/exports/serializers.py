from rest_framework import serializers

from .models import AuditLog
from .models import Export


class ExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Export
        fields = "__all__"
        read_only_fields = ["generated_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = [
            "actor_user", "action_type", "entity_type",
            "entity_id", "timestamp", "details",
        ]
