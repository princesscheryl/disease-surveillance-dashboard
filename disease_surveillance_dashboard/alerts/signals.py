from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from disease_surveillance_dashboard.alerts.models import Alert


@receiver(post_save, sender=Alert)
def queue_immediate_alert_email(sender, instance, created, **kwargs):
    if not created:
        return

    def enqueue():
        from disease_surveillance_dashboard.alerts.tasks import send_immediate_alert_email

        send_immediate_alert_email.delay(instance.pk)

    transaction.on_commit(enqueue)
