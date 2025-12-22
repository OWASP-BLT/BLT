"""
Django management command to demonstrate trademark matching.
Usage: python manage.py trademark_demo
"""

from django.core.management.base import BaseCommand

from website.services.trademark_matching import get_trademark_matches


class Command(BaseCommand):
    """Management command for trademark matching demo."""

    help = "Demo trademark matching functionality for issue #1926"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--company",
            type=str,
            default="BugHeist",
            help="Company name to search for (default: BugHeist)",
        )
        parser.add_argument(
            "--threshold",
            type=float,
            default=85.0,
            help="Match threshold 0-100 (default: 85.0)",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        company = options["company"]

        self.stdout.write(self.style.SUCCESS(f"\n🔍 Searching for trademark matches for: '{company}'"))
        self.stdout.write("=" * 60)

        matches = get_trademark_matches(company)

        if not matches:
            self.stdout.write(self.style.WARNING(f"❌ No matches found for '{company}'"))
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ Found {len(matches)} potential match(es):\n"))
            for i, match in enumerate(matches, 1):
                score_color = (
                    self.style.SUCCESS
                    if match.score >= 95
                    else self.style.WARNING
                    if match.score >= 85
                    else self.style.ERROR
                )
                self.stdout.write(f"  {i}. {match.name:<30} " f"Score: {score_color(f'{match.score}%')}")

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(
            self.style.HTTP_INFO(
                "💡 Tip: To check a different company, use:\n"
                "   python manage.py trademark_demo --company 'YourCompanyName'"
            )
        )
        self.stdout.write("")
