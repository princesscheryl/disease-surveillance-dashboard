from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Role(models.Model):
    """Model representing a user role for access control."""

    role_name = models.CharField(
        _("Role Name"),
        max_length=255,
        unique=True,
        db_index=True,
    )
    description = models.TextField(_("Description"), blank=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)

    class Meta:
        db_table = "roles"
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")
        ordering = ["role_name"]
        indexes = [
            models.Index(fields=["role_name"]),
        ]

    def __str__(self) -> str:
        """Return role name as string representation."""
        return self.role_name


class UserRole(models.Model):
    """Model representing the assignment of a role to a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("User"),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_assignments",
        verbose_name=_("Role"),
    )
    assigned_at = models.DateTimeField(_("Assigned At"), auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        verbose_name = _("User Role")
        verbose_name_plural = _("User Roles")
        ordering = ["-assigned_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "role"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        """Return user role assignment as string representation."""
        return f"{self.user.email} - {self.role.role_name}"
