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
