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


class InAppNotification(models.Model):
    class Kind(models.TextChoices):
        TASK_ASSIGNED = "TASK_ASSIGNED", _("Task assigned")
        ALERT_ESCALATED = "ALERT_ESCALATED", _("Alert escalated")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
        verbose_name=_("Recipient"),
    )
    kind = models.CharField(_("Kind"), max_length=32, choices=Kind.choices)
    title = models.CharField(_("Title"), max_length=200)
    body = models.TextField(_("Body"), blank=True)
    link_path = models.CharField(_("Link path"), max_length=500, blank=True)
    read_at = models.DateTimeField(_("Read at"), null=True, blank=True)
    created_at = models.DateTimeField(_("Created at"), auto_now_add=True)

    class Meta:
        db_table = "in_app_notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} → {self.recipient.email}"


def create_task_assigned_notification(assignee, *, alert_id, disease_name, assigner_email):
    if not assignee:
        return None
    return InAppNotification.objects.create(
        recipient=assignee,
        kind=InAppNotification.Kind.TASK_ASSIGNED,
        title="Investigation task assigned",
        body=(
            f"{assigner_email} assigned you a task for alert #{alert_id} "
            f"({disease_name})."
        ),
        link_path="/dashboard/alerts/",
    )


def create_escalation_notifications(escalation):
    from disease_surveillance_dashboard.access_control.models import UserRole

    role = escalation.escalated_to_role
    alert = escalation.alert
    disease_name = alert.disease.disease_name if alert and alert.disease_id else ""
    user_ids = (
        UserRole.objects.filter(role=role)
        .values_list("user_id", flat=True)
        .distinct()
    )
    rows = []
    for uid in user_ids:
        u = User.objects.filter(pk=uid, is_active=True).first()
        if not u:
            continue
        rows.append(
            InAppNotification(
                recipient=u,
                kind=InAppNotification.Kind.ALERT_ESCALATED,
                title="Alert escalated",
                body=(
                    f"Alert #{alert.id} ({disease_name}) was escalated to "
                    f"{role.role_name}."
                ),
                link_path="/dashboard/alerts/",
            ),
        )
    if rows:
        InAppNotification.objects.bulk_create(rows)
    return len(rows)
