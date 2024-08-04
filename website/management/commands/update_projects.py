from django.core.management.base import BaseCommand

from website.models import Project


class Command(BaseCommand):
    help = "Update projects with their contributors from GitHub"

    def handle(self, *args, **kwargs):
        projects = Project.objects.prefetch_related("contributors").all()
        for project in projects:
            contributors = Project.get_contributors(None, github_url=project.github_url)
            project.contributors.set(contributors)
        # serializer = ProjectSerializer(projects, many=True)
        # projects_data = json.dumps(serializer.data, indent=4) # serialize the data to be printed
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(projects)} projects"))
        # self.stdout.write(projects_data) # if need to return the data too in the terminal
