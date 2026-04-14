from disease_surveillance_dashboard.access_control.models import Role

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

ADMIN_ROLES = ["System Administrator", "ADMIN"]


def user_has_role(user, role_names):
    if not user or not user.is_authenticated:
        return False
    user_role_names = Role.objects.filter(
        user_assignments__user=user,
    ).values_list("role_name", flat=True)
    return any(role_name in role_names for role_name in user_role_names)


def user_can_access_dashboard(user):
    return user_has_role(user, DASHBOARD_ALLOWED_ROLES)


def user_is_admin(user):
    return user_has_role(user, ADMIN_ROLES)
