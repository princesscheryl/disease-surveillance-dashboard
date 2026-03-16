from rest_framework import serializers

from disease_surveillance_dashboard.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    name = serializers.SerializerMethodField()

    def get_name(self, obj):
        return obj.name

    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }
