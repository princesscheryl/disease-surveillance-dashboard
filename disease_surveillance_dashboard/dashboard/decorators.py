from functools import wraps

from django.shortcuts import render

from .utils import user_has_role


def require_role(*allowed_roles):
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
