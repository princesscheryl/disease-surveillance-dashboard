from django.contrib import admin
from .models import Disease

@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
    list_display = ('disease_name', 'is_active', 'created_at')
    search_fields = ('disease_name',)
    list_filter = ('is_active',)