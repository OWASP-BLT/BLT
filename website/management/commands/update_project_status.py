import requests

from website.management.base import LoggedBaseCommand
from website.models import Project


class Command(LoggedBaseCommand):
    help = "Update project status from GitHub"

    def handle(self, *args, **options):
        projects = Project.objects.filter(github_url__isnull=False)
        for project in projects:
            try:
                response = requests.get(project.github_url)
                if response.status_code == 200:
                    data = response.json()
                    project.status = data.get("archived", False)
                    project.save()
            except Exception as e:
                msg = f"Error updating project {project.id}: {str(e)}"
                self.stderr.write(msg)

        self.stdout.write("Project status update completed")
