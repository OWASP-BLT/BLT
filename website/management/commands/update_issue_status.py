import requests

from website.management.base import LoggedBaseCommand
from website.models import Issue


class Command(LoggedBaseCommand):
    help = "Update issue status from GitHub"

    def handle(self, *args, **options):
        issues = Issue.objects.filter(github_url__isnull=False)
        for issue in issues:
            try:
                response = requests.get(issue.github_url)
                if response.status_code == 200:
                    data = response.json()
                    issue.status = data.get("state", "open")
                    issue.save()
            except Exception as e:
                self.stderr.write(f"Error updating issue {issue.id}: {str(e)}")

        self.stdout.write("Issue status update completed")

