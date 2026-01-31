import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Refresh GSoC leaderboard data (PRs then reviews) with proper dependency ordering"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )
        parser.add_argument(
            "--skip-prs",
            action="store_true",
            help="Skip fetching PRs (only fetch reviews)",
        )
        parser.add_argument(
            "--skip-reviews",
            action="store_true",
            help="Skip fetching reviews (only fetch PRs)",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        skip_prs = options.get("skip_prs", False)
        skip_reviews = options.get("skip_reviews", False)

        start_time = timezone.now()
        self.stdout.write(f"Starting GSoC data refresh at {start_time}")

        prs_success = True
        reviews_success = True

        # Step 1: Fetch PRs (must run before reviews)
        if not skip_prs:
            try:
                self.stdout.write("Step 1/2: Fetching GSoC pull requests")
                call_command("fetch_gsoc_prs", verbose=verbose)
                self.stdout.write(self.style.SUCCESS("✓ Successfully fetched PRs"))
            except Exception as e:
                prs_success = False
                logger.error("Error fetching GSoC PRs: %s", str(e), exc_info=True)
                self.stdout.write(self.style.ERROR(f"✗ Error fetching PRs: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Skipping PR fetch"))

        # Step 2: Fetch PR reviews (depends on PRs existing)
        if not skip_reviews:
            try:
                self.stdout.write("Step 2/2: Fetching PR reviews")
                call_command("fetch_pr_reviews", verbose=verbose)
                self.stdout.write(self.style.SUCCESS("✓ Successfully fetched reviews"))
            except Exception as e:
                reviews_success = False
                logger.error("Error fetching PR reviews: %s", str(e), exc_info=True)
                self.stdout.write(self.style.ERROR(f"✗ Error fetching reviews: {e}"))
        else:
            self.stdout.write(self.style.WARNING("Skipping review fetch"))

        # Summary
        elapsed = (timezone.now() - start_time).total_seconds()
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"GSoC data refresh completed in {elapsed:.1f}s")
        self.stdout.write(f"PRs: {'✓' if prs_success else '✗'}")
        self.stdout.write(f"Reviews: {'✓' if reviews_success else '✗'}")

        if prs_success and reviews_success:
            self.stdout.write(self.style.SUCCESS("All operations completed successfully"))
            return

        if not prs_success and not reviews_success:
            self.stdout.write(self.style.ERROR("Both operations failed"))
            raise Exception("GSoC data refresh failed")

        self.stdout.write(self.style.WARNING("Partial success"))