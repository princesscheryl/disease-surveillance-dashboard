"""URL configuration for access control API."""

from rest_framework.routers import DefaultRouter

from .views import RoleViewSet
from .views import UserRoleViewSet

router = DefaultRouter()
router.register(r"roles", RoleViewSet, basename="role")
router.register(r"user-roles", UserRoleViewSet, basename="user-role")

app_name = "access_control_api"
urlpatterns = router.urls
