from django.core.management.base import BaseCommand
from django.db.models import Q

from website.models import Repo


class Command(BaseCommand):
    help = "Removes AI summaries from repositories that contain 'gpt-3.5-turbo'"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without making changes to the database",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry-run", False)

        # Find repos with AI summaries containing "gpt-3.5-turbo"
        repos_with_gpt35 = Repo.objects.filter(~Q(ai_summary=None) & Q(ai_summary__icontains="gpt-3.5-turbo"))

        count = repos_with_gpt35.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No repositories found with 'gpt-3.5-turbo' in AI summaries."))
            return

        self.stdout.write(f"Found {count} repositories with 'gpt-3.5-turbo' in AI summaries.")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN: No changes will be made."))
            for repo in repos_with_gpt35:
                self.stdout.write(f"Would clear AI summary for: {repo.name} (ID: {repo.id})")
        else:
            # Update all matching repos to clear their AI summaries
            updated = repos_with_gpt35.update(ai_summary=None)

            self.stdout.write(self.style.SUCCESS(f"Successfully cleared AI summaries for {updated} repositories."))

            # List the repositories that were updated
            self.stdout.write("Repositories updated:")
            for repo in repos_with_gpt35:
                self.stdout.write(f"- {repo.name} (ID: {repo.id})")
