from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from disease_surveillance_dashboard.access_control.api.views import RoleViewSet
from disease_surveillance_dashboard.access_control.api.views import UserRoleViewSet
from disease_surveillance_dashboard.alerts.views import AlertEscalationViewSet
from disease_surveillance_dashboard.alerts.views import AlertNoteViewSet
from disease_surveillance_dashboard.alerts.views import AlertStatusViewSet
from disease_surveillance_dashboard.alerts.views import AlertViewSet
from disease_surveillance_dashboard.analytics.views import BaselineMetricViewSet
from disease_surveillance_dashboard.analytics.views import TrendMetricViewSet
from disease_surveillance_dashboard.exports.views import AuditLogViewSet
from disease_surveillance_dashboard.exports.views import ExportViewSet
from disease_surveillance_dashboard.investigations.views import InvestigationTaskViewSet
from disease_surveillance_dashboard.reporting.views import DuplicateFlagViewSet
from disease_surveillance_dashboard.reporting.views import ReportStatusViewSet
from disease_surveillance_dashboard.reporting.views import ReportViewSet
from disease_surveillance_dashboard.users.api.views import UserViewSet
from reference_data.views import DiseaseViewSet
from reference_data.views import LocationViewSet

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
router.register("investigations/tasks", InvestigationTaskViewSet, basename="investigation-task")
router.register("exports", ExportViewSet, basename="export")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")
router.register("diseases", DiseaseViewSet, basename="disease")
router.register("locations", LocationViewSet, basename="location")

app_name = "api"
urlpatterns = router.urls
