from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    list_filter = [
        "is_active",
        "user_roles__role__role_name",
        "district",
        "position",
    ]
    list_display = [
        "email",
        "first_name",
        "last_name",
        "position",
        "health_facility",
        "district",
        "is_active",
        "get_roles",
    ]
    search_fields = ["email", "first_name", "last_name", "health_facility"]
    readonly_fields = [
        "health_facility",
        "district",
        "position",
        "facility_type",
        "created_at",
    ]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "phone")}),
        (
            _("Health worker details"),
            {"fields": ("health_facility", "district", "position", "facility_type")},
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined", "created_at")}),
    )
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )

    def get_roles(self, obj):
        if not obj.pk:
            return ""
        roles = obj.user_roles.select_related("role").all()
        return ", ".join(ur.role.role_name for ur in roles)

    get_roles.short_description = "Roles"

    @admin.action(description="Activate selected users")
    def activate_users(self, request, queryset):
        queryset.update(is_active=True)

    actions = [activate_users]
