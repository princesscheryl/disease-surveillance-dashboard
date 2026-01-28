"""Tests for access control models."""

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from ..models import Role
from ..models import UserRole

User = get_user_model()


class RoleModelTestCase(TestCase):
    """Test cases for Role model."""

    def setUp(self):
        """Set up test data."""
        self.role = Role.objects.create(
            role_name="ADMIN",
            description="Administrator role",
        )

    def test_role_creation(self):
        """Test that a role can be created successfully."""
        self.assertIsNotNone(self.role.id)
        self.assertEqual(self.role.role_name, "ADMIN")
        self.assertEqual(self.role.description, "Administrator role")

    def test_role_string_representation(self):
        """Test the string representation of a role."""
        self.assertEqual(str(self.role), "ADMIN")

    def test_role_name_unique(self):
        """Test that role names are unique."""
        with self.assertRaises(IntegrityError):
            Role.objects.create(role_name="ADMIN")

    def test_role_created_at_auto_set(self):
        """Test that created_at is automatically set."""
        self.assertIsNotNone(self.role.created_at)


class UserRoleModelTestCase(TestCase):
    """Test cases for UserRole model."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create(
            email="testuser@example.com",
            full_name="Test User",
        )
        self.role = Role.objects.create(
            role_name="VERIFIER",
            description="Verifier role",
        )

    def test_user_role_creation(self):
        """Test that a user role assignment can be created successfully."""
        user_role = UserRole.objects.create(user=self.user, role=self.role)

        self.assertIsNotNone(user_role.id)
        self.assertEqual(user_role.user, self.user)
        self.assertEqual(user_role.role, self.role)

    def test_user_role_string_representation(self):
        """Test the string representation of a user role assignment."""
        user_role = UserRole.objects.create(user=self.user, role=self.role)

        expected_str = f"{self.user.email} - {self.role.role_name}"
        self.assertEqual(str(user_role), expected_str)

    def test_user_role_unique_constraint(self):
        """Test that the same role cannot be assigned twice to the same user."""
        UserRole.objects.create(user=self.user, role=self.role)

        with self.assertRaises(IntegrityError):
            UserRole.objects.create(user=self.user, role=self.role)

    def test_user_role_assigned_at_auto_set(self):
        """Test that assigned_at is automatically set."""
        user_role = UserRole.objects.create(user=self.user, role=self.role)

        self.assertIsNotNone(user_role.assigned_at)

    def test_user_can_have_multiple_roles(self):
        """Test that a user can be assigned multiple different roles."""
        role2 = Role.objects.create(role_name="ANALYST")
        user_role1 = UserRole.objects.create(user=self.user, role=self.role)
        user_role2 = UserRole.objects.create(user=self.user, role=role2)

        user_roles = UserRole.objects.filter(user=self.user)
        self.assertEqual(user_roles.count(), 2)
