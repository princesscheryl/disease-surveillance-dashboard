"""
Decorators for dashboard view access control.

Role-based checks that return 403 Forbidden when the user lacks
the required role.
"""

from functools import wraps

from django.shortcuts import render

from .utils import user_has_role


def require_role(*allowed_roles):
    """
    Decorator that restricts view access to users with one of the allowed roles.

    Returns 403 Forbidden if the user is anonymous or does not have any
    of the specified roles. Use with function-based views or
    @method_decorator(require_role(...), name='dispatch') for class-based views.

    Args:
        allowed_roles: Role name strings (e.g. 'Public Health Officer', 'System Administrator')
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return render(request, "dashboard/403.html", status=403)
            if not user_has_role(request.user, list(allowed_roles)):
                return render(request, "dashboard/403.html", status=403)
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
