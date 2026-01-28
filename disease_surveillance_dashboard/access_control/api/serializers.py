from rest_framework import serializers

from ..models import Role
from ..models import UserRole


class RoleSerializer(serializers.ModelSerializer):
    """Serializer for Role model."""

    class Meta:
        model = Role
        fields = ["id", "role_name", "description", "created_at"]
        read_only_fields = ["created_at"]


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model."""

    role_detail = RoleSerializer(source="role", read_only=True)
    user_email = serializers.CharField(source="user.email", read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "user", "user_email", "role", "role_detail", "assigned_at"]
        read_only_fields = ["assigned_at"]
