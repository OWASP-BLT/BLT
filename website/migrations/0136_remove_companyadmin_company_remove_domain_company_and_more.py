import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0135_add_project_metadata"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name="companyadmin",
            name="company",
        ),
        migrations.RemoveField(
            model_name="domain",
            name="company",
        ),
        migrations.RemoveField(
            model_name="companyadmin",
            name="domain",
        ),
        migrations.RemoveField(
            model_name="companyadmin",
            name="user",
        ),
        migrations.CreateModel(
            name="Organization",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "description",
                    models.CharField(blank=True, max_length=500, null=True),
                ),
                (
                    "logo",
                    models.ImageField(blank=True, null=True, upload_to="organization_logos"),
                ),
                ("url", models.URLField()),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("twitter", models.CharField(blank=True, max_length=30, null=True)),
                ("facebook", models.URLField(blank=True, null=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=False)),
                (
                    "admin",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "managers",
                    models.ManyToManyField(
                        related_name="user_organizations", to=settings.AUTH_USER_MODEL
                    ),
                ),
                (
                    "subscription",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="website.subscription",
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, to="website.tag")),
            ],
        ),
        migrations.AddField(
            model_name="domain",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="website.organization",
            ),
        ),
        migrations.CreateModel(
            name="OrganizationAdmin",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "role",
                    models.IntegerField(choices=[(0, "Admin"), (1, "Moderator")], default=0),
                ),
                ("is_active", models.BooleanField(default=True)),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "domain",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="website.domain",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="website.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.DeleteModel(
            name="Company",
        ),
        migrations.DeleteModel(
            name="CompanyAdmin",
        ),
    ]
