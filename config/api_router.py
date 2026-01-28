from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter
from reference_data.views import DiseaseViewSet

from disease_surveillance_dashboard.access_control.api.views import RoleViewSet
from disease_surveillance_dashboard.access_control.api.views import UserRoleViewSet
from disease_surveillance_dashboard.users.api.views import UserViewSet


router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("access-control/roles", RoleViewSet)
router.register("access-control/user-roles", UserRoleViewSet)
router.register("diseases", DiseaseViewSet, basename="disease")

app_name = "api"
urlpatterns = router.urls
