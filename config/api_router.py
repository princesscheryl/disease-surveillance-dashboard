from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from reference_data.views import DiseaseViewSet, LocationViewSet
from disease_surveillance_dashboard.access_control.api.views import (
    RoleViewSet,
    UserRoleViewSet,
)
from disease_surveillance_dashboard.alerts.views import (
    AlertEscalationViewSet,
    AlertNoteViewSet,
    AlertStatusViewSet,
    AlertViewSet,
)
from disease_surveillance_dashboard.analytics.views import (
    BaselineMetricViewSet,
    TrendMetricViewSet,
)
from disease_surveillance_dashboard.reporting.views import (
    DuplicateFlagViewSet,
    ReportStatusViewSet,
    ReportViewSet,
)
from disease_surveillance_dashboard.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("access-control/roles", RoleViewSet)
router.register("access-control/user-roles", UserRoleViewSet)
router.register("reporting/statuses", ReportStatusViewSet, basename="report-status")
router.register("reporting/reports", ReportViewSet, basename="report")
router.register("reporting/duplicate-flags", DuplicateFlagViewSet, basename="duplicate-flag")
router.register("analytics/baselines", BaselineMetricViewSet, basename="baseline-metric")
router.register("analytics/trends", TrendMetricViewSet, basename="trend-metric")
router.register("alerts/statuses", AlertStatusViewSet, basename="alert-status")
router.register("alerts/alerts", AlertViewSet, basename="alert")
router.register("alerts/notes", AlertNoteViewSet, basename="alert-note")
router.register("alerts/escalations", AlertEscalationViewSet, basename="alert-escalation")
router.register("diseases", DiseaseViewSet, basename="disease")
router.register("locations", LocationViewSet, basename="location")

app_name = "api"
urlpatterns = router.urls