"""
Management command to run outbreak alert generation synchronously.

Use for manual testing or one-off runs. With --dry-run, no alerts are
saved; the command only prints what would be created.

Run with:
    python manage.py generate_alerts
    python manage.py generate_alerts --dry-run
"""

from django.core.management.base import BaseCommand

from disease_surveillance_dashboard.dashboard.tasks import generate_outbreak_alerts


class Command(BaseCommand):
    help = "Run CUSUM-based outbreak alert generation (same logic as the Celery beat task)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not create alerts; only report what would be created.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write("Dry run: no alerts will be saved.")
        count = generate_outbreak_alerts.apply(kwargs={"dry_run": dry_run}).get()
        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"Would create {count} alert(s)."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Created {count} alert(s)."))
