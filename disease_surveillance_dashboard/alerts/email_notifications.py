import logging

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertImmediateEmailLog
from disease_surveillance_dashboard.alerts.models import PhoAlertDigestSend

from .notification_utils import dashboard_alerts_absolute_url
from .notification_utils import format_alert_location
from .notification_utils import immediate_alert_recipient_emails
from .notification_utils import open_alerts_queryset
from .notification_utils import pho_digest_recipient_emails

logger = logging.getLogger(__name__)


def send_immediate_alert_email(alert_id):
    try:
        alert = Alert.objects.select_related("disease", "location", "status").get(pk=alert_id)
    except Alert.DoesNotExist:
        logger.warning("Immediate alert email skipped: alert id=%s not found.", alert_id)
        return False

    if AlertImmediateEmailLog.objects.filter(alert=alert).exists():
        return False

    recipients = immediate_alert_recipient_emails()
    if not recipients:
        logger.warning("Immediate alert email skipped: no recipients configured for alert id=%s.", alert_id)
        return False

    AlertImmediateEmailLog.objects.create(alert=alert)

    dashboard_url = dashboard_alerts_absolute_url()
    period = timezone.localtime(alert.period_start)
    context = {
        "alert": alert,
        "disease_name": alert.disease.disease_name,
        "district_label": format_alert_location(alert),
        "severity": alert.severity_level,
        "status_name": alert.status.status_name,
        "period_label": period.strftime("%Y-%m-%d %H:%M %Z"),
        "created_label": timezone.localtime(alert.created_at).strftime("%Y-%m-%d %H:%M %Z"),
        "dashboard_url": dashboard_url,
    }
    subject = (
        f"[Surveillance] New alert: {context['disease_name']} — "
        f"{context['district_label']} ({context['severity']})"
    )
    body = render_to_string("alerts/email/immediate_alert.txt", context)
    html_body = render_to_string("alerts/email/immediate_alert.html", context)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_body,
            fail_silently=False,
        )
    except Exception:
        logger.exception("Immediate alert email failed for alert id=%s.", alert_id)
        AlertImmediateEmailLog.objects.filter(alert=alert).delete()
        raise

    return True


def send_pho_daily_digest():
    digest_date = timezone.localdate()
    if PhoAlertDigestSend.objects.filter(digest_for_date=digest_date).exists():
        return 0

    alerts = list(open_alerts_queryset())
    if not alerts:
        return 0

    recipients = pho_digest_recipient_emails()
    if not recipients:
        logger.warning("PHO daily digest skipped: no recipients configured.")
        return 0

    dashboard_url = dashboard_alerts_absolute_url()
    rows = []
    for alert in alerts:
        period = timezone.localtime(alert.period_start)
        rows.append({
            "id": alert.id,
            "disease_name": alert.disease.disease_name,
            "district_label": format_alert_location(alert),
            "severity": alert.severity_level,
            "status_name": alert.status.status_name,
            "period_label": period.strftime("%Y-%m-%d"),
        })

    context = {
        "digest_date": digest_date.strftime("%Y-%m-%d"),
        "alert_rows": rows,
        "dashboard_url": dashboard_url,
        "total": len(rows),
    }
    subject = f"[Surveillance] Daily alert summary — {context['digest_date']}"
    body = render_to_string("alerts/email/daily_digest.txt", context)
    html_body = render_to_string("alerts/email/daily_digest.html", context)


    PhoAlertDigestSend.objects.create(digest_for_date=digest_date)

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            html_message=html_body,
            fail_silently=False,
        )
    except Exception:
        logger.exception("PHO daily digest email failed for %s — recipients were not notified.", digest_date)
        PhoAlertDigestSend.objects.filter(digest_for_date=digest_date).delete()
        raise

    return len(recipients)
