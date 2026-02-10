from rest_framework import viewsets

from .models import Disease
from .models import Location
from .serializers import DiseaseSerializer
from .serializers import LocationSerializer


class DiseaseViewSet(viewsets.ModelViewSet):
    queryset = Disease.objects.all()
    serializer_class = DiseaseSerializer


class LocationViewSet(viewsets.ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
