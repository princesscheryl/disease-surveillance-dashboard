"""
Management command to set latitude and longitude on Location records using
the center point of each district polygon from the Greater Accra GeoJSON.

The Live Map needs coordinates to place markers; without them it shows
"No location data".  This command computes a simple centroid (average of
all polygon vertices) per district and updates matching Location rows.

Run after seeding locations and whenever the GeoJSON boundaries change:
    python manage.py update_district_coordinates
    python manage.py update_district_coordinates --dry-run
"""

import json
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from reference_data.models import Location


def get_geojson_path():
    """Same path as the dashboard choropleth API so we stay in sync."""
    return os.path.join(
        settings.BASE_DIR,
        "disease_surveillance_dashboard",
        "static",
        "geojson",
        "greater_accra_districts.geojson",
    )


def centroid_from_polygon(coordinates):
    """
    Calculate the center point by averaging all coordinates in the
    polygon's exterior ring.  GeoJSON uses [lon, lat] per point.

    Returns (lat, lon) rounded to 6 decimal places, or (None, None)
    if the ring is empty or malformed.
    """
    if not coordinates or not isinstance(coordinates, list):
        return None, None
    # First ring is the exterior boundary; inner rings are holes
    ring = coordinates[0]
    if not ring or len(ring) < 3:
        return None, None
    try:
        lons = [float(p[0]) for p in ring]
        lats = [float(p[1]) for p in ring]
    except (IndexError, TypeError, ValueError):
        return None, None
    n = len(lons)
    if n == 0:
        return None, None
    lat = round(sum(lats) / n, 6)
    lon = round(sum(lons) / n, 6)
    return lat, lon


class Command(BaseCommand):
    help = (
        "Update Location latitude/longitude from Greater Accra district "
        "GeoJSON polygon centroids so the Live Map can show markers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be updated without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run — no changes will be saved."))

        geojson_path = get_geojson_path()
        if not os.path.isfile(geojson_path):
            self.stderr.write(
                self.style.ERROR(
                    f"GeoJSON file not found: {geojson_path}\n"
                    "Ensure the file exists under static/geojson/."
                )
            )
            return

        try:
            with open(geojson_path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            self.stderr.write(self.style.ERROR(f"Could not read GeoJSON: {e}"))
            return

        features = data.get("features") or []
        if not features:
            self.stdout.write(self.style.WARNING("GeoJSON has no features."))
            return

        updated_count = 0
        not_found = []

        for feature in features:
            props = feature.get("properties") or {}
            shape_name = (props.get("shapeName") or "").strip()
            if not shape_name:
                self.stdout.write(
                    self.style.WARNING("  Skipping feature with no shapeName.")
                )
                continue

            geometry = feature.get("geometry")
            if not geometry:
                self.stdout.write(
                    self.style.WARNING(f"  Skipping '{shape_name}': no geometry.")
                )
                continue

            gtype = geometry.get("type")
            if gtype != "Polygon":
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping '{shape_name}': geometry type is '{gtype}', not Polygon."
                    )
                )
                continue

            coords = geometry.get("coordinates")
            lat, lon = centroid_from_polygon(coords)
            if lat is None or lon is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"  Skipping '{shape_name}': could not compute centroid."
                    )
                )
                continue

            # Match district by name (case-insensitive) so small spelling
            # differences between GeoJSON and the database don't break updates.
            locations = list(
                Location.objects.filter(district_name__iexact=shape_name)
            )
            if not locations:
                not_found.append(shape_name)
                self.stdout.write(self.style.WARNING(f"  Not found: {shape_name}"))
                continue

            if not dry_run:
                for loc in locations:
                    loc.latitude = lat
                    loc.longitude = lon
                    loc.save(update_fields=["latitude", "longitude"])

            updated_count += len(locations)
            self.stdout.write(
                f"  Updated: {shape_name} -> ({lat}, {lon})"
                + (f" ({len(locations)} location(s))" if len(locations) > 1 else "")
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Updated: {updated_count} district(s).")
        )
        if not_found:
            self.stdout.write(
                self.style.WARNING(f"Not found: {len(not_found)} district(s).")
            )
            for name in not_found:
                self.stdout.write(f"  - {name}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("Dry run — no coordinates were saved.")
            )
