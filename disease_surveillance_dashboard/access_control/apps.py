from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AccessControlConfig(AppConfig):
    """App configuration for Access Control."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "disease_surveillance_dashboard.access_control"
    verbose_name = _("Access Control")
