# Generated migration for access_control app initial models

from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Role",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role_name",
                    models.CharField(
                        db_index=True,
                        max_length=255,
                        unique=True,
                        verbose_name="Role Name",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        verbose_name="Description",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Created At",
                    ),
                ),
            ],
            options={
                "verbose_name": "Role",
                "verbose_name_plural": "Roles",
                "db_table": "roles",
                "ordering": ["role_name"],
            },
        ),
        migrations.CreateModel(
            name="UserRole",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "assigned_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name="Assigned At",
                    ),
                ),
                (
                    "role",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="user_assignments",
                        to="access_control.role",
                        verbose_name="Role",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        related_name="user_roles",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="User",
                    ),
                ),
            ],
            options={
                "verbose_name": "User Role",
                "verbose_name_plural": "User Roles",
                "db_table": "user_roles",
                "ordering": ["-assigned_at"],
            },
        ),
        migrations.AddIndex(
            model_name="role",
            index=models.Index(
                fields=["role_name"],
                name="roles_role_n_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(
                fields=["user", "role"],
                name="user_roles_user_id_role_id_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userrole",
            index=models.Index(
                fields=["role"],
                name="user_roles_role_id_idx",
            ),
        ),
        migrations.AddConstraint(
            model_name="userrole",
            constraint=models.UniqueConstraint(
                fields=["user", "role"],
                name="unique_user_role",
            ),
        ),
    ]
