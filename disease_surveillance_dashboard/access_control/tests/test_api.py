"""Tests for access control API endpoints."""

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from ..models import Role
from ..models import UserRole

User = get_user_model()


class RoleAPITestCase(APITestCase):
    """Test cases for Role API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="tester@example.com",
            password="testpass123",
        )
        self.client.force_authenticate(user=self.user)

        self.role = Role.objects.create(
            role_name="ADMIN",
            description="Administrator role",
        )
        self.api_url = "/api/v1/access-control/roles/"

    def test_role_list(self):
        """Test retrieving list of roles."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_role_create(self):
        """Test creating a new role."""
        data = {
            "role_name": "VERIFIER",
            "description": "Verifier role",
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Role.objects.count(), 2)

    def test_role_retrieve(self):
        """Test retrieving a specific role."""
        url = f"{self.api_url}{self.role.id}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["role_name"], "ADMIN")


class UserRoleAPITestCase(APITestCase):
    """Test cases for UserRole API endpoints."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpass123",
            full_name="Test User",
        )
        self.client.force_authenticate(user=self.user)

        self.role = Role.objects.create(
            role_name="HEALTH_OFFICER",
            description="Health Officer role",
        )
        self.user_role = UserRole.objects.create(user=self.user, role=self.role)
        self.api_url = "/api/v1/access-control/user-roles/"

    def test_user_role_list(self):
        """Test retrieving list of user roles."""
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_user_role_create(self):
        """Test creating a new user role assignment."""
        role2 = Role.objects.create(role_name="ANALYST")
        data = {
            "user": self.user.id,
            "role": role2.id,
        }
        response = self.client.post(self.api_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(UserRole.objects.count(), 2)

    def test_user_roles_endpoint(self):
        """Test the custom user roles endpoint."""
        url = f"{self.api_url}user_roles/?user_id={self.user.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["user"], self.user.id)
        self.assertEqual(response.data[0]["role"], self.role.id)

    def test_user_roles_endpoint_missing_user_id(self):
        """Test user roles endpoint without user_id parameter."""
        url = f"{self.api_url}user_roles/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)