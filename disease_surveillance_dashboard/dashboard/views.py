"""
Dashboard UI views.

Server-rendered pages for the monitoring dashboard with role-based access control.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from .utils import user_can_access_dashboard


class DashboardView(LoginRequiredMixin, TemplateView):
    """Main dashboard page with monitoring overview."""

    template_name = "dashboard/dashboard.html"

    def dispatch(self, request, *args, **kwargs):
        """Check dashboard access before rendering."""
        if not user_can_access_dashboard(request.user):
            return render(request, "dashboard/403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Add context data for dashboard template."""
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context

