from django.contrib import admin

from .models import Disease
from .models import Location


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ("disease_name", "is_active", "created_at")
    search_fields = ("disease_name",)
    list_filter = ("is_active",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # Show population right in the list so we can quickly spot locations
    # that still need census data filled in (they'll show "-" for population).
    list_display = ("district_name", "area_name", "population", "population_year", "is_active")
    search_fields = ("district_name", "area_name", "population")
    list_filter = ("is_active", "population_year")
