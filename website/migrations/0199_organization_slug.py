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
        # Drop the problematic index with CASCADE so that any references are also removed.
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
              IF EXISTS (
                  SELECT 1 FROM pg_class WHERE relname = 'website_organization_slug_334d1fac_like'
              ) THEN
                  EXECUTE 'DROP INDEX website_organization_slug_334d1fac_like CASCADE';
              END IF;
            END $$;
            """,
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
        # Set the column as NOT NULL and add a unique constraint.
        migrations.RunSQL(
            sql="""
            DO $$ 
            BEGIN
                ALTER TABLE website_organization 
                ALTER COLUMN slug SET NOT NULL;
                
                IF NOT EXISTS (
                    SELECT 1 
                    FROM pg_constraint 
                    WHERE conname = 'website_organization_slug_unique'
                ) THEN
                    ALTER TABLE website_organization 
                    ADD CONSTRAINT website_organization_slug_unique 
                    UNIQUE (slug);
                END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE website_organization 
            ALTER COLUMN slug DROP NOT NULL;
            ALTER TABLE website_organization 
            DROP CONSTRAINT IF EXISTS website_organization_slug_unique;
            """,
        ),
        # Finally, update the Django model to match.
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(unique=True, max_length=255),
        ),
    ]
