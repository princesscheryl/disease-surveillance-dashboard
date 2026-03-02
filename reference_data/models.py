from django.core.validators import MinValueValidator
from django.db import models


class Disease(models.Model):
    disease_name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "diseases"
        indexes = [
            models.Index(fields=["disease_name"]),
        ]

    def __str__(self):
        return self.disease_name

class Location(models.Model):
    district_name = models.CharField(max_length=255)
    area_name = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Population figures come from the 2021 Ghana census.  We need these so
    # we can compute incidence rates (cases per 100k population) on the
    # dashboard.  Both fields are nullable so existing location records are
    # not broken before the data is imported.
    population = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="District population from 2021 census",
    )
    # We store the census year separately because population data changes
    # with each census cycle — this makes it easy to update later without
    # touching the population figure itself.
    population_year = models.IntegerField(
        default=2021,
        help_text="Census year for the population figure",
    )

    class Meta:
        db_table = "locations"
        indexes = [
            models.Index(fields=["district_name", "area_name"]),
        ]

    def __str__(self):
        if self.area_name:
            return f"{self.district_name} - {self.area_name}"
        return self.district_name
