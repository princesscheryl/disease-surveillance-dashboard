from django.apps import AppConfig


class AlertsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "disease_surveillance_dashboard.alerts"
    verbose_name = "Alerts"

    def ready(self):
        import disease_surveillance_dashboard.alerts.signals  # noqa: F401

