from django.contrib import admin
from .models import Disease, Location

@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('disease_name', 'is_active', 'created_at')
    search_fields = ('disease_name',)
    list_filter = ('is_active',)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('district_name', 'area_name', 'is_active')
    search_fields = ('district_name', 'area_name')
    list_filter = ('is_active',)