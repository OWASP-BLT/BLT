from django.db import migrations, models
from django.utils.text import slugify


def drop_index_if_exists(apps, schema_editor):
    # Only run on PostgreSQL
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            """
            DO $$
            BEGIN
              IF EXISTS (
                  SELECT 1 FROM pg_class WHERE relname = 'website_organization_slug_334d1fac_like'
              ) THEN
                  EXECUTE 'DROP INDEX website_organization_slug_334d1fac_like CASCADE';
              END IF;
            END $$;
        """
        )


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
        # Drop any leftover problematic index using a Python function
        migrations.RunPython(
            drop_index_if_exists,
            reverse_code=migrations.RunPython.noop,
        ),
        # Add the slug field without unique=True initially
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
        # First, alter the field to be non-null (without the unique constraint)
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(max_length=255),
        ),
        # Then add a unique constraint with a custom name.
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(fields=["slug"], name="unique_organization_slug"),
        ),
    ]
