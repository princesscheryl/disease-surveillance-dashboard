"""
Utility functions for dashboard access control.

This module provides role-based access control helpers that check user roles
without modifying global DRF permission settings.
"""

from disease_surveillance_dashboard.access_control.models import Role


def user_has_role(user, role_names):
    """
    Check if user has any of the specified roles.

    Args:
        user: User instance to check
        role_names: List of role name strings (e.g., ["ADMIN", "HEALTH_OFFICER"])

    Returns:
        bool: True if user has at least one of the specified roles, False otherwise
    """
    if not user or not user.is_authenticated:
        return False

    # Get all role names for this user
    user_role_names = Role.objects.filter(
        user_assignments__user=user,
    ).values_list("role_name", flat=True)

    # Check if any user role matches any of the required roles
    return any(role_name in role_names for role_name in user_role_names)


# Dashboard access allowed roles. API endpoints accept any user with one of these.
# Includes new role names and legacy names for backward compatibility.
DASHBOARD_ALLOWED_ROLES = [
    "Community Health Worker",
    "Public Health Officer",
    "System Administrator",
    "CHW",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
]


def user_can_access_dashboard(user):
    """
    Check if user can access the monitoring dashboard.

    Args:
        user: User instance to check

    Returns:
        bool: True if user has dashboard access, False otherwise
    """
    return user_has_role(user, DASHBOARD_ALLOWED_ROLES)

