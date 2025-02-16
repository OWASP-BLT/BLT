from django.db import migrations, models
from django.utils.text import slugify


def generate_unique_slugs(apps, schema_editor):
    Organization = apps.get_model("website", "Organization")
    used_slugs = set(Organization.objects.exclude(slug__isnull=True).values_list("slug", flat=True))
    for org in Organization.objects.filter(slug__isnull=True):
        base_slug = slugify(org.name) or f"org-{org.id}"
        slug = base_slug
        counter = 1
        while slug in used_slugs:
            slug = f"{base_slug}-{counter}"
            counter += 1
        used_slugs.add(slug)
        org.slug = slug
        org.save()


def reverse_slug_generation(apps, schema_editor):
    Organization = apps.get_model("website", "Organization")
    Organization.objects.all().update(slug=None)


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0198_alter_githubissue_issue_id"),
    ]

    operations = [
        # Drop the problematic index if it exists.
        migrations.RunSQL(
            sql="DROP INDEX IF EXISTS website_organization_slug_334d1fac_like;",
            reverse_sql="",
        ),
        migrations.AddField(
            model_name="organization",
            name="slug",
            field=models.SlugField(null=True, blank=True, max_length=255),
        ),
        migrations.RunPython(
            generate_unique_slugs,
            reverse_slug_generation,
            elidable=False,
        ),
        # Let Django create the unique constraint/index automatically.
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(unique=True, max_length=255),
        ),
    ]
