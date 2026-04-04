"""
Context processors for dashboard templates.

Exposes user role and other request-scoped data to templates.
"""


def user_role(request):
    """
    Add the current user's primary role name to template context.

    Uses the first assigned role from user.user_roles. Returns None if
    the user is anonymous or has no role assigned.
    """
    user_role_name = None
    if request.user.is_authenticated:
        first_assignment = request.user.user_roles.select_related("role").first()
        if first_assignment:
            user_role_name = first_assignment.role.role_name
    return {"user_role": user_role_name}


def unhandled_alert_count(request):
    count = 0
    if request.user.is_authenticated:
        from disease_surveillance_dashboard.alerts.notification_utils import count_unhandled_alerts

        count = count_unhandled_alerts()
    display = str(count) if count <= 99 else "99+"
    return {"unhandled_alert_count": count, "unhandled_alert_badge_display": display}
