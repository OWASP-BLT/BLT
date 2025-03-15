import requests

from website.management.base import LoggedBaseCommand
from website.models import Project


class Command(LoggedBaseCommand):
    help = "Update project status from GitHub"

    def handle(self, *args, **options):
        # Only get projects with GitHub URLs
        projects = Project.objects.filter(url__icontains="github.com")
        for project in projects:
            try:
                # Convert web URL to API URL
                api_url = project.url.replace("github.com", "api.github.com/repos")
                response = requests.get(api_url)
                if response.status_code == 200:
                    data = response.json()
                    project.status = data.get("archived", False)
                    project.save()
            except Exception as e:
                msg = f"Error updating project {project.id}: {str(e)}"
                self.stderr.write(msg)

        self.stdout.write("Project status update completed")

