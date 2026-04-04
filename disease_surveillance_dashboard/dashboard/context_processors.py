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
    from disease_surveillance_dashboard.dashboard.utils import user_has_role

    officer_roles = (
        "Public Health Officer",
        "System Administrator",
        "HEALTH_OFFICER",
        "ADMIN",
        "ANALYST",
        "VERIFIER",
    )
    count = 0
    unread = 0
    show_activity_log = False
    if request.user.is_authenticated:
        from disease_surveillance_dashboard.alerts.notification_utils import count_unhandled_alerts
        from disease_surveillance_dashboard.users.models import InAppNotification

        count = count_unhandled_alerts()
        unread = InAppNotification.objects.filter(
            recipient=request.user,
            read_at__isnull=True,
        ).count()
        show_activity_log = user_has_role(request.user, officer_roles)
    display = str(count) if count <= 99 else "99+"
    ndisplay = str(unread) if unread <= 99 else "99+"
    return {
        "unhandled_alert_count": count,
        "unhandled_alert_badge_display": display,
        "unread_notification_count": unread,
        "unread_notification_badge_display": ndisplay,
        "show_activity_log_link": show_activity_log,
    }
