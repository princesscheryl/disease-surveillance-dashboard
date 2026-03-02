"""
Management command to import 2021 census population figures into the
Location model from a CSV file.

The CSV should have these columns:
    district_name, population_2021, notes

Matching works in two passes — exact name first, then case-insensitive
— so minor capitalisation differences in the CSV don't cause unnecessary
new records to be created.

The command is idempotent: running it twice on the same CSV just updates
the same rows again, so it's safe to re-run after fixing the source file.
"""

import csv
import os
import sys

from django.core.management.base import BaseCommand
from django.db import transaction

from reference_data.models import Location

# Default CSV location — the project root, which is one level above the
# manage.py file.  Users can override this with --csv-path.
DEFAULT_CSV_PATH = os.path.join(
    os.path.dirname(sys.argv[0]),  # directory that contains manage.py
    "greater_accra_population_2021.csv",
)

CENSUS_YEAR = 2021


class Command(BaseCommand):
    help = (
        "Import 2021 census population data from a CSV file into the Location model. "
        "Matches by district_name (exact, then case-insensitive). "
        "Creates new Location records for districts not yet in the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-path",
            default=DEFAULT_CSV_PATH,
            help=(
                "Path to the CSV file.  Defaults to "
                "greater_accra_population_2021.csv in the project root."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without writing anything to the database.",
        )

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be written."))

        # Make sure the file actually exists before we do anything else.
        if not os.path.isfile(csv_path):
            self.stderr.write(
                self.style.ERROR(
                    f"File not found: {csv_path}\n"
                    f"Pass the correct path with --csv-path=<path>"
                )
            )
            return

        rows = self._read_csv(csv_path)
        if rows is None:
            # _read_csv already printed the error, so we just stop here.
            return

        self.stdout.write(f"Processing {len(rows)} rows from {csv_path} ...")

        updated = 0
        created = 0
        skipped = 0

        # Build a lookup of all existing locations keyed by normalised name
        # (lowercase + stripped) so the case-insensitive fallback is fast and
        # doesn't fire a query per row.
        existing = {
            loc.district_name.strip().lower(): loc
            for loc in Location.objects.all()
        }
        # We also keep the exact-name index for the fast path.
        existing_exact = {
            loc.district_name.strip(): loc
            for loc in Location.objects.all()
        }

        with transaction.atomic():
            for row_num, row in enumerate(rows, start=2):  # start=2 because row 1 is the header
                district_raw = row.get("district_name", "").strip()
                population_raw = row.get("population_2021", "").strip()

                # Skip completely empty rows — these sometimes appear at the
                # end of CSV files exported from spreadsheets.
                if not district_raw and not population_raw:
                    continue

                if not district_raw:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Row {row_num}: missing district_name — skipped"
                        )
                    )
                    skipped += 1
                    continue

                # Try to parse the population figure.  We skip rows where
                # it's missing or not a valid integer rather than storing a
                # potentially wrong value.
                population = self._parse_population(population_raw, district_raw, row_num)
                if population is None:
                    skipped += 1
                    continue

                # --- Match to an existing Location ---
                location = self._find_location(district_raw, existing_exact, existing)

                if location is not None:
                    # We found a match, so just update the population fields.
                    if not dry_run:
                        location.population = population
                        location.population_year = CENSUS_YEAR
                        location.save(update_fields=["population", "population_year"])
                    self.stdout.write(
                        f"  ✓ Updated: {location.district_name} → {population:,}"
                    )
                    updated += 1

                else:
                    # No existing record found, so we create one.  It will
                    # only have district_name and population for now — other
                    # fields like latitude/longitude can be filled in later.
                    if not dry_run:
                        location = Location.objects.create(
                            district_name=district_raw,
                            is_active=True,
                            population=population,
                            population_year=CENSUS_YEAR,
                        )
                        # Add the new record to our local lookups so that if
                        # the same district appears twice in the CSV we handle
                        # the second occurrence as an update rather than
                        # creating another duplicate.
                        existing_exact[district_raw] = location
                        existing[district_raw.lower()] = location
                    self.stdout.write(
                        f"  ✓ Created: {district_raw} → {population:,}"
                    )
                    created += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\nDry run complete — nothing was saved. "
                    f"Would have: Updated {updated}, Created {created}, Skipped {skipped}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nDone. Updated: {updated}, Created: {created}, Skipped: {skipped}"
                )
            )

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    def _read_csv(self, csv_path):
        """Read the CSV into a list of dicts and handle any parsing errors up front."""
        try:
            with open(csv_path, newline="", encoding="utf-8-sig") as fh:
                # utf-8-sig strips the BOM that Excel sometimes adds to
                # CSV files exported on Windows.
                reader = csv.DictReader(fh)

                # Make sure the required columns are actually there.
                required_columns = {"district_name", "population_2021"}
                if reader.fieldnames is None:
                    self.stderr.write(self.style.ERROR("CSV file is empty."))
                    return None

                actual_columns = {c.strip().lower() for c in reader.fieldnames}
                missing = required_columns - actual_columns
                if missing:
                    self.stderr.write(
                        self.style.ERROR(
                            f"CSV is missing required columns: {', '.join(sorted(missing))}\n"
                            f"Found columns: {', '.join(reader.fieldnames)}"
                        )
                    )
                    return None

                rows = []
                for i, row in enumerate(reader, start=2):
                    try:
                        # Normalise column names so we're not sensitive to
                        # extra spaces the user might have left in the header.
                        rows.append({k.strip().lower(): v for k, v in row.items()})
                    except Exception as exc:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  Row {i}: could not parse — {exc} — skipped"
                            )
                        )
                return rows

        except FileNotFoundError:
            # This shouldn't happen because we check above, but better safe.
            self.stderr.write(self.style.ERROR(f"File not found: {csv_path}"))
            return None
        except UnicodeDecodeError:
            self.stderr.write(
                self.style.ERROR(
                    f"Could not read {csv_path} as UTF-8.  "
                    f"Try re-saving the CSV with UTF-8 encoding."
                )
            )
            return None
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"Failed to read CSV: {exc}"))
            return None

    def _parse_population(self, raw_value, district_name, row_num):
        """
        Turn the raw CSV string into an integer.
        Returns None (and prints a warning) if the value can't be used.
        """
        if not raw_value:
            self.stdout.write(
                self.style.WARNING(
                    f"  Row {row_num} ({district_name}): population is empty — skipped"
                )
            )
            return None

        # Some spreadsheets export numbers with commas or spaces as thousands
        # separators (e.g. "1,234,567"), so we strip those before parsing.
        cleaned = raw_value.replace(",", "").replace(" ", "").replace("\xa0", "")

        try:
            value = int(float(cleaned))  # float() first handles "12345.0" style values
        except ValueError:
            self.stdout.write(
                self.style.WARNING(
                    f"  Row {row_num} ({district_name}): "
                    f"'{raw_value}' is not a valid number — skipped"
                )
            )
            return None

        if value < 0:
            self.stdout.write(
                self.style.WARNING(
                    f"  Row {row_num} ({district_name}): "
                    f"population can't be negative ({value}) — skipped"
                )
            )
            return None

        return value

    def _find_location(self, district_name, exact_index, icase_index):
        """
        Try to find an existing Location record.

        First we do an exact match, then fall back to a case-insensitive
        comparison.  If either index holds multiple records for the same
        name (which shouldn't happen but might in messy data), we use the
        first one and log a warning so someone knows to clean it up.
        """
        # Exact match is the fast path and handles most cases.
        location = exact_index.get(district_name)
        if location is not None:
            return location

        # Case-insensitive fallback — catches things like "Ga East" vs
        # "GA East" that are clearly the same district.
        location = icase_index.get(district_name.lower())
        if location is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"  Note: '{district_name}' matched '{location.district_name}' "
                    f"via case-insensitive lookup — consider fixing the CSV spelling."
                )
            )
            return location

        # Check the database directly for multiple records with the same
        # district name so we can warn about duplicates.
        duplicates = list(
            Location.objects.filter(
                district_name__iexact=district_name
            ).order_by("id")
        )
        if len(duplicates) > 1:
            self.stdout.write(
                self.style.WARNING(
                    f"  Warning: {len(duplicates)} Location records match "
                    f"'{district_name}' — updating the oldest one (id={duplicates[0].id})."
                )
            )
            return duplicates[0]

        if len(duplicates) == 1:
            return duplicates[0]

        return None
