from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Role
from .models import UserRole


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""

    list_display = ["role_name", "description", "created_at"]
    search_fields = ["role_name"]
    ordering = ["role_name"]
    readonly_fields = ["created_at"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for UserRole model."""

    list_display = ["user", "role", "assigned_at"]
    list_filter = ["role"]
    search_fields = ["user__email", "user__full_name"]
    ordering = ["-assigned_at"]
    readonly_fields = ["assigned_at"]
