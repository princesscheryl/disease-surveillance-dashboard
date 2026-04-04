"""Tests for alert email notifications and unhandled alert counting."""

from datetime import UTC
from datetime import datetime

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.test import override_settings

from disease_surveillance_dashboard.access_control.models import Role
from disease_surveillance_dashboard.access_control.models import UserRole
from disease_surveillance_dashboard.alerts.email_notifications import send_immediate_alert_email
from disease_surveillance_dashboard.alerts.email_notifications import send_pho_daily_digest
from disease_surveillance_dashboard.alerts.models import Alert
from disease_surveillance_dashboard.alerts.models import AlertImmediateEmailLog
from disease_surveillance_dashboard.alerts.models import AlertStatus
from disease_surveillance_dashboard.alerts.notification_utils import count_unhandled_alerts
from disease_surveillance_dashboard.alerts.tasks import send_immediate_alert_email as send_immediate_task
from reference_data.models import Disease
from reference_data.models import Location

User = get_user_model()


@override_settings(
    ALERT_IMMEDIATE_EXTRA_EMAILS=["duty@example.com"],
    ALERT_IMMEDIATE_NOTIFY_ROLE_NAMES=[],
    ALERT_DAILY_DIGEST_ROLE_NAMES=[],
)
class ImmediateAlertEmailTests(TestCase):
    def setUp(self):
        self.disease = Disease.objects.create(disease_name="Malaria")
        self.location = Location.objects.create(district_name="Accra Metro")
        self.status_new, _ = AlertStatus.objects.get_or_create(
            status_name="New",
            defaults={"description": "New"},
        )

    def test_immediate_email_sent_once_and_idempotent(self):
        alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="High",
            status=self.status_new,
        )
        self.assertTrue(send_immediate_alert_email(alert.pk))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Malaria", mail.outbox[0].subject)
        self.assertIn("duty@example.com", mail.outbox[0].to)

        mail.outbox.clear()
        self.assertFalse(send_immediate_alert_email(alert.pk))
        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(AlertImmediateEmailLog.objects.filter(alert=alert).exists())

    def test_signal_queues_task_with_capture_on_commit(self):
        with self.captureOnCommitCallbacks(execute=True):
            Alert.objects.create(
                disease=self.disease,
                location=self.location,
                period_start=datetime.now(UTC),
                period_end=datetime.now(UTC),
                baseline_value="1.0000",
                observed_value="5.0000",
                threshold_rule="test",
                severity_level="Medium",
                status=self.status_new,
            )
        self.assertEqual(len(mail.outbox), 1)

    def test_task_wrapper_calls_core_sender(self):
        alert = Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="Low",
            status=self.status_new,
        )
        send_immediate_task.run(alert.pk)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(
    ALERT_IMMEDIATE_EXTRA_EMAILS=[],
    ALERT_IMMEDIATE_NOTIFY_ROLE_NAMES=["DIGEST_ROLE"],
    ALERT_DAILY_DIGEST_ROLE_NAMES=["DIGEST_ROLE"],
)
class PhoDigestTests(TestCase):
    def setUp(self):
        self.disease = Disease.objects.create(disease_name="Cholera")
        self.location = Location.objects.create(district_name="Tema Metro")
        self.status_new, _ = AlertStatus.objects.get_or_create(
            status_name="New",
            defaults={"description": "New"},
        )
        self.user = User.objects.create_user(
            email="pho@example.com",
            password="x",
            first_name="Test",
            last_name="PHO",
        )
        role = Role.objects.create(role_name="DIGEST_ROLE", description="")
        UserRole.objects.create(user=self.user, role=role)

    def test_daily_digest_lists_open_alerts(self):
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="High",
            status=self.status_new,
        )
        n = send_pho_daily_digest()
        self.assertGreaterEqual(n, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("pho@example.com", mail.outbox[0].to)
        self.assertIn("Cholera", mail.outbox[0].body)

    def test_daily_digest_skips_when_already_sent_for_date(self):
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="High",
            status=self.status_new,
        )
        send_pho_daily_digest()
        mail.outbox.clear()
        self.assertEqual(send_pho_daily_digest(), 0)
        self.assertEqual(len(mail.outbox), 0)


class UnhandledAlertCountTests(TestCase):
    def setUp(self):
        self.disease = Disease.objects.create(disease_name="Dengue")
        self.location = Location.objects.create(district_name="Ga West")
        self.status_new, _ = AlertStatus.objects.get_or_create(
            status_name="New",
            defaults={"description": "New"},
        )
        self.status_resolved, _ = AlertStatus.objects.get_or_create(
            status_name="Resolved",
            defaults={"description": "Resolved"},
        )

    def test_counts_only_non_terminal_statuses(self):
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="Medium",
            status=self.status_new,
        )
        Alert.objects.create(
            disease=self.disease,
            location=self.location,
            period_start=datetime.now(UTC),
            period_end=datetime.now(UTC),
            baseline_value="1.0000",
            observed_value="5.0000",
            threshold_rule="test",
            severity_level="Medium",
            status=self.status_resolved,
        )
        self.assertEqual(count_unhandled_alerts(), 1)
