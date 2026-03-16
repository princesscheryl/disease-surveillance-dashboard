from typing import ClassVar

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import EmailField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager

POSITION_CHOICES = [
    ("CHW", "Community Health Worker"),
    ("CH_NURSE", "Community Health Nurse"),
    ("PH_NURSE", "Public Health Nurse"),
    ("DISEASE_CONTROL", "Disease Control Officer"),
    ("SURVEILLANCE", "Surveillance Officer"),
    ("ENV_HEALTH", "Environmental Health Officer"),
    ("DISTRICT_DIR", "District Director"),
    ("OTHER", "Other"),
]

FACILITY_TYPE_CHOICES = [
    ("TEACHING_HOSPITAL", "Teaching Hospital"),
    ("REGIONAL_HOSPITAL", "Regional Hospital"),
    ("DISTRICT_HOSPITAL", "District Hospital"),
    ("POLYCLINIC", "Polyclinic"),
    ("HEALTH_CENTRE", "Health Centre"),
    ("CHPS", "CHPS Compound"),
    ("DISTRICT_OFFICE", "District Health Directorate"),
    ("OTHER", "Other"),
]


class User(AbstractUser):
    first_name = CharField(_("first name"), max_length=150, blank=False)
    last_name = CharField(_("last name"), max_length=150, blank=False)
    email = EmailField(_("email address"), unique=True)
    phone = CharField(max_length=20, null=True, blank=True)
    username = None  # type: ignore[assignment]
    created_at = DateTimeField(auto_now_add=True)
    health_facility = CharField(max_length=255, blank=True)
    district = models.ForeignKey(
        "reference_data.Location",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="health_workers",
    )
    position = CharField(max_length=50, blank=True, choices=POSITION_CHOICES)
    facility_type = CharField(max_length=50, blank=True, choices=FACILITY_TYPE_CHOICES)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def get_absolute_url(self) -> str:
        return reverse("users:detail", kwargs={"pk": self.id})
