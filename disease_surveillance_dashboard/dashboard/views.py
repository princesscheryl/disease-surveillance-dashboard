"""
Dashboard UI views.

Each view is a LoginRequiredMixin TemplateView that checks dashboard
access via user_can_access_dashboard() before rendering.  All data
loading is done client-side via the Alpine dashboardData() component.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views.generic import TemplateView

from .utils import user_can_access_dashboard


class DashboardAccessMixin(LoginRequiredMixin):
    """
    Mixin shared by all dashboard views.
    Checks role-based access and renders 403 for unauthorised users.
    """

    def dispatch(self, request, *args, **kwargs):
        if not user_can_access_dashboard(request.user):
            return render(request, "dashboard/403.html", status=403)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class OverviewView(DashboardAccessMixin, TemplateView):
    """KPI cards + at-a-glance chart tiles."""
    template_name = "dashboard/overview.html"


class AnalyticsView(DashboardAccessMixin, TemplateView):
    """Full chart suite: timeseries, forecast, anomalies, top diseases."""
    template_name = "dashboard/analytics.html"


class LiveMapView(DashboardAccessMixin, TemplateView):
    """Leaflet map with disease distribution markers."""
    template_name = "dashboard/live_map.html"


class AlertsView(DashboardAccessMixin, TemplateView):
    """Recent alerts table + investigation tasks table."""
    template_name = "dashboard/alerts.html"


class ReportsView(DashboardAccessMixin, TemplateView):
    """Report list placeholder with future export button."""
    template_name = "dashboard/reports.html"


# ---------------------------------------------------------------------------
# Legacy alias — keeps the old /dashboard/ URL working by redirecting to
# the new Overview page so existing bookmarks and tests do not break.
# ---------------------------------------------------------------------------
class DashboardView(DashboardAccessMixin, TemplateView):
    """Legacy entry point — alias for OverviewView."""
    template_name = "dashboard/overview.html"
