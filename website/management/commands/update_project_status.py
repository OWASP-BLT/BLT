import requests
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Project


class Command(LoggedBaseCommand):
    help = "Update project status from GitHub"

    def handle(self, *args, **options):
        # Only get projects with GitHub URLs
        projects = Project.objects.filter(url__icontains="github.com")
        updated_projects = []
        for project in projects:
            try:
                # Convert web URL to API URL
                api_url = project.url.rstrip("/").replace("github.com", "api.github.com/repos")
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    is_archived = data.get("archived", False)
                    if is_archived:
                        new_status = "inactive"
                    elif project.status == "inactive":
                        # Reactivate previously archived projects
                        new_status = "lab"
                    else:
                        new_status = project.status
                    if new_status != project.status:
                        project.status = new_status
                        updated_projects.append(project)
            except Exception as e:
                msg = f"Error updating project {project.id}: {str(e)}"
                self.stderr.write(msg)

        if updated_projects:
            Project.objects.bulk_update(updated_projects, ["status"])
            Project.objects.filter(id__in=[p.id for p in updated_projects]).update(modified=timezone.now())

        self.stdout.write(f"Project status update completed: {len(updated_projects)} projects updated")
