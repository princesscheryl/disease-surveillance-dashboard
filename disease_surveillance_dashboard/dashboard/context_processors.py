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
