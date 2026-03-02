"""
Management command to generate realistic test reports for the disease
surveillance dashboard.

The data simulates a malaria outbreak building over 30 days — starting
at a low baseline and climbing to peak levels that should trigger the
CUSUM alert threshold.  We mix in Typhoid, COVID-19, and Cholera to
keep the top-diseases chart interesting too.

Run with:
    python manage.py generate_test_reports
    python manage.py generate_test_reports --count=200
    python manage.py generate_test_reports --clear  # wipe existing reports first
"""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from disease_surveillance_dashboard.reporting.models import Report
from disease_surveillance_dashboard.reporting.models import ReportStatus
from reference_data.models import Disease
from reference_data.models import Location

User = get_user_model()

# ---------------------------------------------------------------------------
# Demographic distribution weights — these match real GHS reporting patterns
# for Greater Accra as closely as we can without actual census breakdowns.
# ---------------------------------------------------------------------------

SEX_CHOICES   = ["MALE",    "FEMALE",    "UNKNOWN"]
SEX_WEIGHTS   = [45,        45,          10]

AGE_CHOICES   = ["UNDER_5", "AGE_5_17",  "AGE_18_59", "AGE_60_PLUS", "UNKNOWN"]
AGE_WEIGHTS   = [30,        25,          30,          10,             5]

SEV_CHOICES   = ["MILD",    "MODERATE",  "SEVERE",    "CRITICAL",    "UNKNOWN"]
SEV_WEIGHTS   = [50,        30,          15,          4,              1]

SRC_CHOICES   = ["FACILITY", "COMMUNITY", "LAB",     "OTHER"]
SRC_WEIGHTS   = [60,         25,          10,         5]


# ---------------------------------------------------------------------------
# Outbreak curve for Malaria
# Day index (0 = today - 30 days) → (min_cases, max_cases) per report.
# The idea is to have a quiet start that builds into a clear alert signal
# by the final week so CUSUM has enough to detect.
# ---------------------------------------------------------------------------

def _malaria_case_range(day_offset: int):
    """
    Return (min, max) case count range for a Malaria report based on how
    many days ago the observation was made.  day_offset=0 means 30 days
    ago; day_offset=29 means today.
    """
    if day_offset < 7:
        return (1, 2)   # quiet baseline at the start
    if day_offset < 14:
        return (2, 4)   # slow rise — something is building
    if day_offset < 21:
        return (4, 7)   # visible trend, should trigger Watch
    return (6, 10)      # peak — should cross the CUSUM alert threshold


class Command(BaseCommand):
    help = (
        "Generate realistic test disease reports over the last 30 days, "
        "simulating a malaria outbreak alongside background diseases."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--count",
            type=int,
            default=150,
            help="Total number of reports to generate (default: 150).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing Report records before generating new ones.",
        )

    def handle(self, *args, **options):
        count   = options["count"]
        do_clear = options["clear"]

        if do_clear:
            deleted, _ = Report.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Cleared {deleted} existing report(s)."))

        # We need a real user to attach to reported_by.  We'll use the first
        # superuser or staff account we find — this is test data so any
        # existing user is fine.
        reporter = self._get_reporter()
        if reporter is None:
            self.stderr.write(
                self.style.ERROR(
                    "No user found in the database.  "
                    "Run 'python manage.py createsuperuser' first, "
                    "then re-run this command."
                )
            )
            return

        # We also need a ReportStatus to attach.  "Pending" or the first one
        # available works fine for test data.
        report_status = self._get_report_status()
        if report_status is None:
            self.stderr.write(
                self.style.ERROR(
                    "No ReportStatus records found.  "
                    "Run 'python manage.py seed_reference_data' first."
                )
            )
            return

        # Build location and disease lookup dicts so we don't query per report.
        diseases  = self._load_diseases()
        locations = self._load_locations()

        if not diseases or not locations:
            self.stderr.write(
                self.style.ERROR(
                    "Reference data is missing.  "
                    "Run 'python manage.py seed_reference_data' first."
                )
            )
            return

        # Work out how many reports each disease gets based on the requested
        # total — Malaria leads, everything else fills in behind.
        disease_counts = self._split_by_disease(count)

        now = timezone.now()
        created_total = 0
        errors = 0

        self.stdout.write(f"Generating {count} reports over the last 30 days ...")

        for disease_name, n in disease_counts.items():
            disease = diseases.get(disease_name)
            if disease is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Disease '{disease_name}' not found — skipping {n} reports."
                    )
                )
                errors += n
                continue

            for _ in range(n):
                # Pick a random day in the last 30 days.  day_offset=0 is the
                # oldest point; day_offset=29 is today.
                day_offset = random.randint(0, 29)
                observed_at = self._random_time_on_day(now, days_ago=(29 - day_offset))

                # Pick a location appropriate for this disease.
                location = self._pick_location(disease_name, locations)
                if location is None:
                    errors += 1
                    continue

                # Case count follows the outbreak curve for Malaria; other
                # diseases just have a flat low-to-medium range.
                if disease_name == "Malaria":
                    lo, hi = _malaria_case_range(day_offset)
                else:
                    lo, hi = (1, 4)
                case_count = random.randint(lo, hi)

                # Decide if this report has data quality issues — 35% of
                # reports get at least one UNKNOWN field to simulate the
                # incomplete reporting that happens in real surveillance.
                has_quality_gap = random.random() < 0.35

                sex           = self._pick_sex(has_quality_gap)
                age_group     = self._pick_age_group(has_quality_gap)
                severity      = self._pick_severity(has_quality_gap)
                report_source = random.choices(SRC_CHOICES, weights=SRC_WEIGHTS)[0]

                # Create the report.  submitted_at is auto_now_add so Django
                # sets it to now — we'll fix it right after creation.
                try:
                    report = Report(
                        disease=disease,
                        location=location,
                        reported_by=reporter,
                        observed_at=observed_at,
                        status=report_status,
                        case_count=case_count,
                        sex=sex,
                        age_group=age_group,
                        severity_level=severity,
                        report_source=report_source,
                        case_notes="",
                    )
                    report.save()

                    # Now backfill submitted_at with a realistic reporting delay.
                    # We're bypassing auto_now_add by writing directly to the field
                    # and using update_fields so Django doesn't override it.
                    report.submitted_at = self._add_reporting_delay(observed_at)
                    report.save(update_fields=["submitted_at"])

                    created_total += 1

                except Exception as exc:  # noqa: BLE001
                    self.stdout.write(
                        self.style.WARNING(f"  ⚠ Could not save report: {exc}")
                    )
                    errors += 1
                    continue

                if created_total % 50 == 0:
                    self.stdout.write(f"  Generated {created_total}/{count} reports ...")

        # Final summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Created {created_total} reports across 30 days"
                + (f" ({errors} skipped due to missing reference data)" if errors else "")
            )
        )
        self._print_breakdown(disease_counts, diseases)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _get_reporter(self):
        """Grab any existing user — preference for superusers, but any will do."""
        user = User.objects.filter(is_superuser=True).first()
        if user is None:
            user = User.objects.filter(is_staff=True).first()
        if user is None:
            user = User.objects.first()
        return user

    def _get_report_status(self):
        """Try to get 'Pending', then fall back to whatever status exists first."""
        status = ReportStatus.objects.filter(status_name__iexact="Pending").first()
        if status is None:
            status = ReportStatus.objects.first()
        return status

    def _load_diseases(self):
        """
        Load diseases we care about into a name → object dict so we don't
        query on every iteration of the loop.
        """
        names = ["Malaria", "Typhoid Fever", "COVID-19", "Cholera"]
        qs = Disease.objects.filter(disease_name__in=names)
        return {d.disease_name: d for d in qs}

    def _load_locations(self):
        """
        Load all active district-level locations into a name → object dict.
        We filter to area_name__isnull=True to get the district records rather
        than sub-area records.
        """
        qs = Location.objects.filter(is_active=True, area_name__isnull=True)
        return {loc.district_name: loc for loc in qs}

    def _split_by_disease(self, total):
        """
        Divide the total report count across diseases using the target
        percentages.  Any rounding remainder goes to Malaria.
        """
        malaria_n  = int(total * 0.60)
        typhoid_n  = int(total * 0.20)
        covid_n    = int(total * 0.15)
        cholera_n  = total - malaria_n - typhoid_n - covid_n  # catches the remainder
        return {
            "Malaria":      malaria_n,
            "Typhoid Fever": typhoid_n,
            "COVID-19":     covid_n,
            "Cholera":      cholera_n,
        }

    def _pick_location(self, disease_name, locations):
        """
        Choose a location that makes geographic sense for the disease.
        Each disease has its own district preferences, and we fall back
        gracefully if the preferred districts aren't in the database.
        """
        if disease_name == "Malaria":
            preferred = [
                ("Ayawaso West Municipal",    40),
                ("Ayawaso Central Municipal", 30),
                ("Ayawaso East Municipal",    20),
                ("Ayawaso North Municipal",    5),
                ("Adenta Municipal",           5),
            ]
        elif disease_name == "Typhoid Fever":
            preferred = [
                ("Accra Metropolitan",  50),
                ("Tema Metropolitan",   30),
                ("Ashaiman Municipal",  10),
                ("Ga East Municipal",   10),
            ]
        elif disease_name == "COVID-19":
            # COVID spreads everywhere, so just pick from whatever we have.
            all_locs = list(locations.values())
            return random.choice(all_locs) if all_locs else None
        else:  # Cholera — coastal districts
            preferred = [
                ("Tema Metropolitan",       40),
                ("Kpone Katamanso Municipal", 30),
                ("Ningo-Prampram District",  30),
            ]

        # Build weighted list from the preferences that actually exist.
        options = [(locations[name], weight)
                   for name, weight in preferred
                   if name in locations]

        if not options:
            # None of the preferred districts exist — fall back to any location.
            all_locs = list(locations.values())
            if not all_locs:
                return None
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ No preferred {disease_name} locations found — using random district."
                )
            )
            return random.choice(all_locs)

        locs, weights = zip(*options)
        return random.choices(locs, weights=weights)[0]

    def _random_time_on_day(self, reference_now, days_ago):
        """
        Pick a random moment on the calendar day that was `days_ago` days
        before the reference datetime.  The result is timezone-aware.
        """
        base = reference_now - timedelta(days=days_ago)
        # Replace time with midnight, then add a random number of seconds
        # spread across the whole 24-hour window.
        midnight = base.replace(hour=0, minute=0, second=0, microsecond=0)
        offset_seconds = random.randint(0, 86399)
        return midnight + timedelta(seconds=offset_seconds)

    def _add_reporting_delay(self, observed_at):
        """
        Add a realistic reporting delay on top of the observation time.
        We're adding a random delay here to simulate how long it actually
        takes for a health worker to get the report submitted after seeing
        a patient — sometimes same day, sometimes a day or two later.
        """
        roll = random.random()
        if roll < 0.60:
            # Same-day reporting — most facilities are reasonably prompt.
            delay_hours = random.uniform(0, 8)
        elif roll < 0.90:
            # Next-day or day-after — common in community settings.
            delay_hours = random.uniform(8, 36)
        else:
            # Late submission — happens with paper-to-digital backlogs.
            delay_hours = random.uniform(36, 72)

        return observed_at + timedelta(hours=delay_hours)

    def _pick_sex(self, has_quality_gap):
        """
        If we've decided this report has a quality gap, there's a 40% chance
        the sex field ends up as UNKNOWN rather than a real value.
        """
        if has_quality_gap and random.random() < 0.40:
            return "UNKNOWN"
        return random.choices(["MALE", "FEMALE"], weights=[50, 50])[0]

    def _pick_age_group(self, has_quality_gap):
        """Same idea as sex — quality gap reports have a chance of UNKNOWN."""
        if has_quality_gap and random.random() < 0.40:
            return "UNKNOWN"
        return random.choices(
            ["UNDER_5", "AGE_5_17", "AGE_18_59", "AGE_60_PLUS"],
            weights=[30, 25, 30, 10],
        )[0]

    def _pick_severity(self, has_quality_gap):
        """Severity is often missing in community-level reports, so it gets
        a slightly higher Unknown rate."""
        if has_quality_gap and random.random() < 0.50:
            return "UNKNOWN"
        return random.choices(SEV_CHOICES[:-1], weights=SEV_WEIGHTS[:-1])[0]

    def _print_breakdown(self, disease_counts, diseases):
        """Print a compact per-disease summary so we can sanity-check the output."""
        self.stdout.write("\nBreakdown by disease:")
        for name, target in disease_counts.items():
            if name in diseases:
                actual = Report.objects.filter(disease=diseases[name]).count()
                self.stdout.write(f"  {name:<22} {actual:>4} reports")
            else:
                self.stdout.write(
                    self.style.WARNING(f"  {name:<22} — not in database")
                )
