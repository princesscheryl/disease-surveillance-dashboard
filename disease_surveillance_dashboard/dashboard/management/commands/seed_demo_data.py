"""
Management command to seed the database with realistic demo data.

Run this once before recording the demo video. It will:
  1. Ensure all reference data exists (diseases, locations)
  2. Clear old reports and generate 200 fresh ones over 30 days
  3. Run CUSUM detection to generate alerts
  4. Set some alerts to Acknowledged and Under Investigation
  5. Create investigation tasks so the investigations table is populated
  6. Add a note to one alert

Run with:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --clear-alerts
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Seed the database with realistic demo data for the presentation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-alerts",
            action="store_true",
            help="Delete existing alerts and investigation tasks before seeding.",
        )

    def handle(self, *args, **options):
        clear_alerts = options["clear_alerts"]

        self.stdout.write("Step 1: Ensuring reference data exists...")
        call_command("seed_reference_data", verbosity=0)
        self.stdout.write(self.style.SUCCESS("  Reference data ready."))

        self.stdout.write("Step 2: Seeding report statuses...")
        self._seed_report_statuses()

        self.stdout.write("Step 3: Seeding alert statuses...")
        self._seed_alert_statuses()

        self.stdout.write("Step 4: Generating reports (this replaces existing reports)...")
        call_command("generate_test_reports", clear=True, count=200, verbosity=0)
        self.stdout.write(self.style.SUCCESS("  200 reports generated."))

        if clear_alerts:
            self.stdout.write("Step 5: Clearing existing alerts and tasks...")
            self._clear_alerts()

        self.stdout.write("Step 6: Running CUSUM detection to generate alerts...")
        call_command("generate_alerts", verbosity=0)

        from disease_surveillance_dashboard.alerts.models import Alert
        alert_count = Alert.objects.count()
        self.stdout.write(self.style.SUCCESS(f"  {alert_count} alerts now in the system."))

        if alert_count == 0:
            self.stdout.write(self.style.WARNING(
                "  No alerts were generated. The CUSUM threshold may not have been crossed. "
                "Try running: python manage.py generate_test_reports --clear --count=300 "
                "then python manage.py generate_alerts"
            ))
            return

        self.stdout.write("Step 7: Setting alert statuses for a realistic demo...")
        self._set_alert_statuses()

        self.stdout.write("Step 8: Creating investigation tasks...")
        self._create_investigation_tasks()

        self.stdout.write("Step 9: Adding an alert note...")
        self._add_alert_note()

        self.stdout.write(self.style.SUCCESS(
            "\nDemo data seeded successfully. The dashboard is ready for recording."
        ))

    # ------------------------------------------------------------------

    def _seed_report_statuses(self):
        from disease_surveillance_dashboard.reporting.models import ReportStatus

        statuses = [
            ("SUBMITTED", "Report has been submitted for review"),
            ("DRAFT", "Report saved as draft, not yet submitted"),
            ("Verified", "Report verified by a public health officer"),
            ("Pending Review", "Report awaiting officer verification"),
            ("Duplicate", "Report flagged as a duplicate"),
            ("Invalid", "Report flagged as invalid"),
        ]
        for name, desc in statuses:
            ReportStatus.objects.get_or_create(
                status_name=name,
                defaults={"description": desc},
            )
        self.stdout.write(self.style.SUCCESS("  Report statuses ready."))

    def _seed_alert_statuses(self):
        from disease_surveillance_dashboard.alerts.models import AlertStatus

        statuses = [
            ("New", "Newly generated alert awaiting acknowledgement"),
            ("Acknowledged", "Alert has been seen and acknowledged by an officer"),
            ("Under Investigation", "Field investigation is underway"),
            ("Resolved", "Alert has been resolved"),
            ("False Alarm", "Alert was reviewed and determined to be a false alarm"),
        ]
        for name, desc in statuses:
            AlertStatus.objects.get_or_create(
                status_name=name,
                defaults={"description": desc},
            )
        self.stdout.write(self.style.SUCCESS("  Alert statuses ready."))

    def _clear_alerts(self):
        from disease_surveillance_dashboard.alerts.models import Alert
        from disease_surveillance_dashboard.investigations.models import InvestigationTask

        InvestigationTask.objects.all().delete()
        deleted, _ = Alert.objects.all().delete()
        self.stdout.write(self.style.WARNING(f"  Cleared {deleted} alert(s) and related tasks."))

    def _set_alert_statuses(self):
        from disease_surveillance_dashboard.alerts.models import Alert
        from disease_surveillance_dashboard.alerts.models import AlertStatus

        alerts = list(Alert.objects.order_by("-created_at"))
        if not alerts:
            return

        acknowledged_status = AlertStatus.objects.filter(status_name="Acknowledged").first()
        investigating_status = AlertStatus.objects.filter(status_name="Under Investigation").first()
        resolved_status = AlertStatus.objects.filter(status_name="Resolved").first()

        # Split alerts across statuses so the demo looks active
        # Keep at least 2 as New for demonstration
        # Move 1-2 to Acknowledged, 1-2 to Under Investigation, 1 to Resolved

        new_count = max(2, len(alerts) - 4)
        acknowledged_count = min(2, len(alerts))
        investigating_count = min(2, len(alerts))
        resolved_count = min(1, len(alerts))

        idx = 0
        total = len(alerts)

        # First chunk stays as New
        idx = min(new_count, total)

        # Next chunk to Acknowledged
        if acknowledged_status:
            for i in range(idx, min(idx + acknowledged_count, total)):
                Alert.objects.filter(pk=alerts[i].pk).update(status=acknowledged_status)
            idx = min(idx + acknowledged_count, total)

        # Next chunk to Under Investigation
        if investigating_status:
            for i in range(idx, min(idx + investigating_count, total)):
                Alert.objects.filter(pk=alerts[i].pk).update(status=investigating_status)
            idx = min(idx + investigating_count, total)

        # One alert to Resolved to show the full lifecycle
        if resolved_status and idx < total:
            Alert.objects.filter(pk=alerts[idx].pk).update(status=resolved_status)

        self.stdout.write(self.style.SUCCESS("  Alert statuses updated for demo variety."))

    def _create_investigation_tasks(self):
        from disease_surveillance_dashboard.alerts.models import Alert
        from disease_surveillance_dashboard.alerts.models import AlertStatus
        from disease_surveillance_dashboard.investigations.models import InvestigationTask

        if InvestigationTask.objects.exists():
            self.stdout.write("  Investigation tasks already exist, skipping.")
            return

        officer = User.objects.filter(is_superuser=True).first()
        if officer is None:
            officer = User.objects.first()
        if officer is None:
            self.stdout.write(self.style.WARNING("  No user found — skipping task creation."))
            return

        # Create tasks only for alerts that are Under Investigation or Acknowledged
        active_statuses = AlertStatus.objects.filter(
            status_name__in=["Under Investigation", "Acknowledged"]
        )
        alerts_for_tasks = Alert.objects.filter(status__in=active_statuses).order_by("-created_at")[:4]

        now = timezone.now()
        task_configs = [
            ("OPEN",        now + timedelta(days=3),  None),
            ("IN_PROGRESS", now + timedelta(days=1),  None),
            ("IN_PROGRESS", now - timedelta(days=1),  None),   # overdue — good for demo
            ("COMPLETED",   now - timedelta(days=2),  "Investigation completed. Source confirmed as contaminated water supply near Ayawaso market area."),
        ]

        created = 0
        for alert, (status, due_at, outcome) in zip(alerts_for_tasks, task_configs):
            InvestigationTask.objects.create(
                alert=alert,
                assigned_to=officer,
                assigned_by=officer,
                due_at=due_at,
                task_status=status,
                outcome=outcome,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"  Created {created} investigation task(s)."))

    def _add_alert_note(self):
        from disease_surveillance_dashboard.alerts.models import Alert
        from disease_surveillance_dashboard.alerts.models import AlertNote
        from disease_surveillance_dashboard.alerts.models import AlertStatus

        if AlertNote.objects.exists():
            self.stdout.write("  Alert notes already exist, skipping.")
            return

        officer = User.objects.filter(is_superuser=True).first()
        if officer is None:
            officer = User.objects.first()
        if officer is None:
            return

        investigating_status = AlertStatus.objects.filter(status_name="Under Investigation").first()
        alert = Alert.objects.filter(status=investigating_status).first()
        if alert is None:
            alert = Alert.objects.first()
        if alert is None:
            return

        AlertNote.objects.create(
            alert=alert,
            noted_by=officer,
            note_text=(
                "Initial field report received from Ayawaso district team. "
                "Cases concentrated around community water points. "
                "Environmental health team dispatched for water sample collection."
            ),
        )
        self.stdout.write(self.style.SUCCESS("  Alert note added."))
