"""
Management command to seed Disease and Location (district) reference data.

Idempotent: uses get_or_create; safe to run multiple times.
"""

from django.core.management.base import BaseCommand

from reference_data.constants import GREATER_ACCRA_DISTRICT_NAMES
from reference_data.models import Disease
from reference_data.models import Location


DISEASES = [
    "Malaria",
    "Cholera",
    "Typhoid Fever",
    "Measles",
    "Influenza-like Illness (ILI)",
    "COVID-19",
    "Meningitis",
    "Diarrhea (Acute Watery)",
    "Tuberculosis",
    "Yellow Fever",
]

class Command(BaseCommand):
    help = "Seed Disease and Location (district) reference data for Greater Accra. Idempotent."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without writing to DB",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run - no changes will be made"))

        created_diseases = 0
        for name in DISEASES:
            if dry_run:
                if not Disease.objects.filter(disease_name=name).exists():
                    created_diseases += 1
                    self.stdout.write(f"  Would create Disease: {name}")
            else:
                _, created = Disease.objects.get_or_create(
                    disease_name=name,
                    defaults={"is_active": True},
                )
                if created:
                    created_diseases += 1
                    self.stdout.write(f"  Created Disease: {name}")

        created_locations = 0
        for district_name in GREATER_ACCRA_DISTRICT_NAMES:
            # Location required fields: district_name only (area_name, lat/long are optional)
            # Match district-level entries (area_name is null) for idempotency
            exists = Location.objects.filter(
                district_name=district_name, area_name__isnull=True
            ).exists()
            if dry_run:
                if not exists:
                    created_locations += 1
                    self.stdout.write(f"  Would create Location: {district_name}")
            else:
                if not exists:
                    Location.objects.create(
                        district_name=district_name,
                        area_name=None,
                        is_active=True,
                    )
                    created_locations += 1
                    self.stdout.write(f"  Created Location: {district_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Diseases: {created_diseases} created. Locations: {created_locations} created."
            )
        )
