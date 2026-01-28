from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ..models import Role
from ..models import UserRole
from .serializers import RoleSerializer
from .serializers import UserRoleSerializer


class RoleViewSet(ModelViewSet):
    """ViewSet for Role model."""

    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    filterset_fields = ["role_name"]
    search_fields = ["role_name", "description"]


class UserRoleViewSet(ModelViewSet):
    """ViewSet for UserRole model with custom endpoint for user roles."""

    queryset = UserRole.objects.select_related("user", "role")
    serializer_class = UserRoleSerializer
    filterset_fields = ["user", "role"]
    search_fields = ["user__email", "user__full_name", "role__role_name"]

    @action(detail=False, methods=["get"])
    def user_roles(self, request):
        """
        Custom endpoint to get all roles for a specific user.

        Usage: GET /access-control/user-roles/user_roles/?user_id=<user_id>
        """
        user_id = request.query_params.get("user_id")

        if not user_id:
            return Response(
                {"error": "user_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = int(user_id)
        except ValueError:
            return Response(
                {"error": "user_id must be an integer"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_roles = UserRole.objects.filter(user_id=user_id).select_related(
            "user", "role"
        )
        serializer = self.get_serializer(user_roles, many=True)
        return Response(serializer.data)
