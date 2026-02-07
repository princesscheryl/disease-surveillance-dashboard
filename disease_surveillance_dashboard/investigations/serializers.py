from rest_framework import serializers

from .models import InvestigationTask


class InvestigationTaskSerializer(serializers.ModelSerializer):
    """Serializer for InvestigationTask model."""

    class Meta:
        model = InvestigationTask
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]

