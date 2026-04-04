from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse


def open_alert_status_names():
    return ("New", "Acknowledged", "Under Investigation")


def count_unhandled_alerts():
    Alert = apps.get_model("alerts", "Alert")
    AlertStatus = apps.get_model("alerts", "AlertStatus")
    statuses = AlertStatus.objects.filter(status_name__in=open_alert_status_names())
    return Alert.objects.filter(status__in=statuses).count()


def open_alerts_queryset():
    Alert = apps.get_model("alerts", "Alert")
    AlertStatus = apps.get_model("alerts", "AlertStatus")
    statuses = AlertStatus.objects.filter(status_name__in=open_alert_status_names())
    return (
        Alert.objects.filter(status__in=statuses)
        .select_related("disease", "location", "status")
        .order_by("-severity_level", "-created_at")
    )


def dashboard_alerts_absolute_url():
    path = reverse("dashboard:alerts")
    try:
        domain = Site.objects.get_current().domain
    except Exception:
        hosts = getattr(settings, "ALLOWED_HOSTS", ())
        domain = hosts[0] if hosts else "localhost"
    scheme = "http" if settings.DEBUG else "https"
    return f"{scheme}://{domain}{path}"


def recipient_emails_for_roles(role_names):
    UserRole = apps.get_model("access_control", "UserRole")
    if not role_names:
        return []
    return list(
        UserRole.objects.filter(role__role_name__in=role_names, user__is_active=True)
        .exclude(user__email="")
        .values_list("user__email", flat=True)
        .distinct(),
    )


def immediate_alert_recipient_emails():
    extra = [e.strip() for e in getattr(settings, "ALERT_IMMEDIATE_EXTRA_EMAILS", ()) if e.strip()]
    roles = getattr(settings, "ALERT_IMMEDIATE_NOTIFY_ROLE_NAMES", ())
    from_roles = recipient_emails_for_roles(roles)
    combined = list(dict.fromkeys(extra + from_roles))
    return combined


def pho_digest_recipient_emails():
    roles = getattr(settings, "ALERT_DAILY_DIGEST_ROLE_NAMES", ())
    return recipient_emails_for_roles(roles)


def format_alert_location(alert):
    name = alert.location.district_name
    if alert.location.area_name:
        name = f"{name} — {alert.location.area_name}"
    return name
