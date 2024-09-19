from django.core.management.base import BaseCommand

from website.models import Project


class Command(BaseCommand):
    help = "Update projects with their contributors from GitHub"

    def handle(self, *args, **kwargs):
        projects = Project.objects.prefetch_related("contributors").all()
        for project in projects:
            contributors = Project.get_contributors(None, github_url=project.github_url)
            project.contributors.set(contributors)
            
            # Fetch and update stars, forks, and external links
            stars, forks = project.fetch_stars_and_forks()
            project.stars = stars
            project.forks = forks
            project.external_links = project.fetch_external_links()
            project.save()
            
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(projects)} projects"))
