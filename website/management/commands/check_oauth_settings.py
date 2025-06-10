from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check OAuth settings configuration"

    def handle(self, *args, **options):
        self.stdout.write("Checking OAuth settings...")

        # Check GitHub settings
        github_key = getattr(settings, "SOCIAL_AUTH_GITHUB_KEY", None)
        github_secret = getattr(settings, "SOCIAL_AUTH_GITHUB_SECRET", None)

        self.stdout.write(f"GitHub Client ID: {'✓ Set' if github_key else '✗ Missing'}")
        self.stdout.write(f"GitHub Secret: {'✓ Set' if github_secret else '✗ Missing'}")

        # Check Site ID
        site_id = getattr(settings, "SITE_ID", None)
        self.stdout.write(f"Site ID: {site_id if site_id else '✗ Missing'}")
