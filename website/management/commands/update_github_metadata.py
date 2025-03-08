import logging

from django.core.management.base import BaseCommand

from website.models import Issue

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Updates GitHub metadata for issues linked to GitHub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of issues to update",
        )

    def handle(self, *args, **options):
        issues = Issue.objects.filter(github_url__icontains="github.com/OWASP-BLT/BLT/issues")

        limit = options.get("limit")
        if limit:
            issues = issues[:limit]

        count = issues.count()
        self.stdout.write(f"Updating GitHub metadata for {count} issues...")

        for i, issue in enumerate(issues):
            issue.update_github_metadata()
            if (i + 1) % 10 == 0:
                self.stdout.write(f"Processed {i + 1}/{count} issues")

        self.stdout.write(self.style.SUCCESS(f"Successfully updated GitHub metadata for {count} issues"))
