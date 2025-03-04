from django.core.management.base import BaseCommand
from django.utils.text import slugify

from website.models import Project


class Command(BaseCommand):
    help = "Fix projects with empty slugs by generating a valid slug for them"

    def handle(self, *args, **options):
        projects_with_empty_slugs = Project.objects.filter(slug="") | Project.objects.filter(slug__isnull=True)
        count = projects_with_empty_slugs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No projects with empty slugs found."))
            return

        self.stdout.write(f"Found {count} projects with empty slugs. Fixing...")

        for project in projects_with_empty_slugs:
            # Generate a slug based on the project name here
            if project.name:
                base_slug = slugify(project.name)
                if not base_slug:
                    base_slug = f"project-{project.id}"
            else:
                base_slug = f"project-{project.id}"

            # Ensure the slug is unique
            unique_slug = base_slug
            counter = 1
            while Project.objects.filter(slug=unique_slug).exclude(id=project.id).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1

            # Update the project with the new slug
            project.slug = unique_slug
            project.save(update_fields=["slug"])

            self.stdout.write(f"  • Fixed project ID {project.id} ({project.name}): slug set to '{unique_slug}'")

        self.stdout.write(self.style.SUCCESS(f"Successfully fixed {count} projects with empty slugs."))
