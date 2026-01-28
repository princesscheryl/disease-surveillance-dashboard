from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DiseaseViewSet

router = DefaultRouter()
router.register(r'diseases', DiseaseViewSet)

urlpatterns = [
    path('reference-data/', include(router.urls)),
]