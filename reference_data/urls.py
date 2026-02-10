from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DiseaseViewSet

router = DefaultRouter()
router.register(r"diseases", DiseaseViewSet)

urlpatterns = [
    path("reference-data/", include(router.urls)),
]
