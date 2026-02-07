from rest_framework import serializers

from .models import Alert
from .models import AlertEscalation
from .models import AlertNote
from .models import AlertStatus


class AlertStatusSerializer(serializers.ModelSerializer):
    """Serializer for AlertStatus model."""

    class Meta:
        model = AlertStatus
        fields = "__all__"
        read_only_fields = ["created_at"]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for Alert model."""

    class Meta:
        model = Alert
        fields = "__all__"
        read_only_fields = ["created_at"]


class AlertNoteSerializer(serializers.ModelSerializer):
    """Serializer for AlertNote model."""

    class Meta:
        model = AlertNote
        fields = "__all__"
        read_only_fields = ["noted_at"]


class AlertEscalationSerializer(serializers.ModelSerializer):
    """Serializer for AlertEscalation model."""

    class Meta:
        model = AlertEscalation
        fields = "__all__"
        read_only_fields = ["escalated_at"]

