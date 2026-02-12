"""
Management command to perform trademark checks on all organizations and websites.
Usage: python manage.py check_all_trademarks
"""

from django.core.management.base import BaseCommand

from website.models import Organization
from website.signals import _perform_trademark_check


class Command(BaseCommand):
    """Management command to bulk check trademarks."""

    help = "Perform trademark checks on all organizations and websites"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--orgs-only",
            action="store_true",
            help="Check only organizations",
        )
        parser.add_argument(
            "--websites-only",
            action="store_true",
            help="Check only websites",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(self.style.SUCCESS("🔍 Starting bulk trademark checks..."))

        orgs_only = options["orgs_only"]
        websites_only = options["websites_only"]

        org_count = 0
        website_count = 0

        # Check organizations
        if not websites_only:
            orgs = Organization.objects.filter(name__isnull=False).exclude(name="")
            for org in orgs:
                try:
                    _perform_trademark_check(name=org.name, organization=org)
                    org_count += 1
                    self.stdout.write(f"  ✓ {org.name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ {org.name}: {str(e)}"))

        # Check websites
        if not orgs_only:
            websites = Website.objects.filter(name__isnull=False).exclude(name="")
            for website in websites:
                try:
                    org = None
                    if hasattr(website, "organization"):
                        org = website.organization
                    _perform_trademark_check(name=website.name, website=website, organization=org)
                    website_count += 1
                    self.stdout.write(f"  ✓ {website.name}")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ✗ {website.name}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Bulk check complete!\n"
                f"  Organizations checked: {org_count}\n"
                f"  Websites checked: {website_count}"
            )
        )
