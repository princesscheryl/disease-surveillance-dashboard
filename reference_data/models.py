from django.db import models

class Disease(models.Model):
    disease_name = models.CharField(max_length=255, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'diseases'
        indexes = [
            models.Index(fields=['disease_name']),
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

    class Meta:
        db_table = 'locations'
        indexes = [
            models.Index(fields=['district_name', 'area_name']),
        ]

    def __str__(self):
        if self.area_name:
            return f"{self.district_name} - {self.area_name}"
        return self.district_name