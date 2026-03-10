from rest_framework import serializers

from .models import InvestigationTask


class InvestigationTaskSerializer(serializers.ModelSerializer):
    """Serializer for InvestigationTask model."""

    assigned_to_email = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = InvestigationTask
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at", "assigned_by"]

    def get_assigned_to_email(self, obj):
        return obj.assigned_to.email if obj.assigned_to else None

