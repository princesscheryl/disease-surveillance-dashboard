from rest_framework import serializers

from disease_surveillance_dashboard.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    name = serializers.CharField(source="full_name", required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }
