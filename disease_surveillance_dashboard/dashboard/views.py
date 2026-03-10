"""
Dashboard UI views.

Each view is a LoginRequiredMixin TemplateView with role-based access.
Overview, Analytics, Live Map, and Alerts require Officer or Admin.
Reports allows all users with a role. All data loading is done client-side
via the Alpine dashboardData() component.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

from .decorators import require_role

# Role names for access control. Include legacy names (ADMIN, HEALTH_OFFICER, etc.)
# for backward compatibility with existing Role records.
OFFICER_OR_ADMIN_ROLES = (
    "Public Health Officer",
    "System Administrator",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
)
ALL_DASHBOARD_ROLES = (
    "Community Health Worker",
    "Public Health Officer",
    "System Administrator",
    "CHW",
    "HEALTH_OFFICER",
    "ADMIN",
    "ANALYST",
    "VERIFIER",
)


class DashboardBaseMixin(LoginRequiredMixin):
    """Adds user to context for all dashboard views."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class OverviewView(DashboardBaseMixin, TemplateView):
    """KPI cards + at-a-glance chart tiles."""
    template_name = "dashboard/overview.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AnalyticsView(DashboardBaseMixin, TemplateView):
    """Full chart suite: timeseries, forecast, anomalies, top diseases."""
    template_name = "dashboard/analytics.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class LiveMapView(DashboardBaseMixin, TemplateView):
    """Leaflet map with disease distribution markers."""
    template_name = "dashboard/live_map.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class AlertsView(DashboardBaseMixin, TemplateView):
    """Recent alerts table + investigation tasks table."""
    template_name = "dashboard/alerts.html"


@method_decorator(require_role(*ALL_DASHBOARD_ROLES), name="dispatch")
class ReportsView(DashboardBaseMixin, TemplateView):
    """Report list placeholder with future export button."""
    template_name = "dashboard/reports.html"


@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class ReviewReportsView(DashboardBaseMixin, TemplateView):
    """Officer report verification — all reports with status update actions."""
    template_name = "dashboard/review_reports.html"


# ---------------------------------------------------------------------------
# Legacy alias — keeps the old /dashboard/ URL working by redirecting to
# the new Overview page so existing bookmarks and tests do not break.
# ---------------------------------------------------------------------------
@method_decorator(require_role(*OFFICER_OR_ADMIN_ROLES), name="dispatch")
class DashboardView(DashboardBaseMixin, TemplateView):
    """Legacy entry point — alias for OverviewView."""
    template_name = "dashboard/overview.html"
