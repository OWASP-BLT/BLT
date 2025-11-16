from django.core.management.base import BaseCommand

from sportscaster.models import AICommentaryTemplate, MonitoredEntity


class Command(BaseCommand):
    help = "Seed initial data for sportscaster app"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Seeding sportscaster data..."))

        # Create AI Commentary Templates
        templates = [
            {
                "event_type": "star",
                "template": "INCREDIBLE! {repo} just gained {count} stars! The crowd is on their feet!",
            },
            {
                "event_type": "fork",
                "template": "WOW! {repo} has been forked {count} times! Developers are going wild!",
            },
            {
                "event_type": "pull_request",
                "template": "BREAKING: New pull request on {repo} by {user}! This could be a game changer!",
            },
            {
                "event_type": "commit",
                "template": "{user} commits to {repo}! The momentum is building!",
            },
            {
                "event_type": "release",
                "template": "MAJOR ANNOUNCEMENT! {repo} version {version} just LAUNCHED! History in the making!",
            },
            {
                "event_type": "issue",
                "template": "New issue reported on {repo} by {user}! The team is on it!",
            },
        ]

        for template_data in templates:
            template, created = AICommentaryTemplate.objects.get_or_create(
                event_type=template_data["event_type"],
                defaults={"template": template_data["template"], "is_active": True},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created template for {template.event_type}"))
            else:
                self.stdout.write(f"Template for {template.event_type} already exists")

        # Create sample monitored entities (popular repos)
        sample_repos = [
            {
                "name": "facebook/react",
                "scope": "repository",
                "github_url": "https://github.com/facebook/react",
            },
            {
                "name": "microsoft/vscode",
                "scope": "repository",
                "github_url": "https://github.com/microsoft/vscode",
            },
            {
                "name": "torvalds/linux",
                "scope": "repository",
                "github_url": "https://github.com/torvalds/linux",
            },
            {
                "name": "OWASP-BLT/BLT",
                "scope": "repository",
                "github_url": "https://github.com/OWASP-BLT/BLT",
            },
        ]

        for repo_data in sample_repos:
            entity, created = MonitoredEntity.objects.get_or_create(
                github_url=repo_data["github_url"],
                defaults={
                    "name": repo_data["name"],
                    "scope": repo_data["scope"],
                    "is_active": True,
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created monitored entity: {entity.name}"))
            else:
                self.stdout.write(f"Entity {entity.name} already exists")

        self.stdout.write(self.style.SUCCESS("\nSeeding complete!"))
        self.stdout.write(
            self.style.SUCCESS("You can now run 'python manage.py process_github_events' to start processing events")
        )
