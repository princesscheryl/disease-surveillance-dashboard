import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="send-pho-alert-digest-daily")
def send_pho_alert_digest_daily():
    from disease_surveillance_dashboard.alerts.email_notifications import send_pho_daily_digest

    try:
        return send_pho_daily_digest()
    except Exception:
        logger.exception("PHO daily alert digest task failed.")
        raise


@shared_task(name="send-immediate-alert-email")
def send_immediate_alert_email(alert_id):
    from disease_surveillance_dashboard.alerts.email_notifications import send_immediate_alert_email as send_fn

    try:
        return send_fn(alert_id)
    except Exception:
        logger.exception("Immediate alert email task failed for alert id=%s.", alert_id)
        raise
